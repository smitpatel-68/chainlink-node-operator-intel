"""Score Chainlink node operators from raw submission data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw_submissions.csv"
SCORES_PATH = ROOT / "data" / "operator_scores.csv"
CONFIG_PATH = ROOT / "config.yaml"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Metric calculations
# ---------------------------------------------------------------------------

def _uptime_rate(df: pd.DataFrame) -> pd.Series:
    """Fraction of rounds where the operator submitted within benchmark latency."""
    benchmark = df.attrs["latency_benchmark_ms"]
    on_time = df["participated"] & (df["submission_latency_ms"] <= benchmark)
    return on_time.groupby(df["operator_address"]).mean().rename("uptime_rate")


def _latency_score(df: pd.DataFrame) -> pd.Series:
    """
    Score 0-100 based on mean latency among participated rounds.
    Operators at or below benchmark score 100; score decays linearly to 0
    at 3× benchmark, then clamps to 0.
    """
    benchmark = df.attrs["latency_benchmark_ms"]
    participated = df[df["participated"]].copy()
    mean_lat = participated.groupby("operator_address")["submission_latency_ms"].mean()
    score = (1 - (mean_lat - benchmark) / (2 * benchmark)).clip(0, 1) * 100
    return score.rename("latency_score")


def _deviation_accuracy(df: pd.DataFrame) -> pd.Series:
    """
    Score 0-100 based on mean absolute percentage deviation from aggregated price.
    Deviation at or below threshold scores 100; decays to 0 at 4× threshold.
    """
    threshold = df.attrs["deviation_threshold_pct"] / 100  # convert to fraction
    participated = df[df["participated"] & df["aggregated_price"].notna()].copy()
    participated["abs_dev"] = (
        (participated["submitted_price"] - participated["aggregated_price"]).abs()
        / participated["aggregated_price"]
    )
    mean_dev = participated.groupby("operator_address")["abs_dev"].mean()
    score = (1 - (mean_dev - threshold) / (3 * threshold)).clip(0, 1) * 100
    return score.rename("deviation_accuracy_score")


def _round_participation(df: pd.DataFrame) -> pd.Series:
    """Raw participation rate scaled to 0-100."""
    rate = df.groupby("operator_address")["participated"].mean()
    return (rate * 100).rename("round_participation_score")


# ---------------------------------------------------------------------------
# Composite scoring and classification
# ---------------------------------------------------------------------------

def _composite_score(metrics: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    score = (
        metrics["uptime_rate"] * 100 * weights["uptime_rate"]
        + metrics["latency_score"]   * weights["latency_percentile"]
        + metrics["deviation_accuracy_score"] * weights["deviation_accuracy"]
        + metrics["round_participation_score"] * weights["round_participation"]
    )
    return score.rename("composite_score")


def _classify(score: pd.Series, thresholds: dict) -> pd.Series:
    conditions = [
        score >= thresholds["tier_1"],
        score >= thresholds["tier_2"],
        score >= thresholds["at_risk"],
    ]
    choices = ["Tier 1", "Tier 2", "At Risk"]
    return pd.Series(
        np.select(conditions, choices, default="At Risk"),
        index=score.index,
        name="tier",
    )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(
    raw_path: str | Path = RAW_PATH,
    scores_path: str | Path = SCORES_PATH,
    config_path: str | Path = CONFIG_PATH,
) -> pd.DataFrame:
    cfg = _load_config()

    df = pd.read_csv(raw_path)
    df["participated"] = df["participated"].astype(bool)

    # Attach config values as DataFrame metadata for metric functions
    df.attrs["latency_benchmark_ms"] = cfg["latency_benchmark_ms"]
    df.attrs["deviation_threshold_pct"] = cfg["deviation_threshold_pct"]

    uptime     = _uptime_rate(df)
    latency    = _latency_score(df)
    deviation  = _deviation_accuracy(df)
    particip   = _round_participation(df)

    metrics = pd.concat([uptime, latency, deviation, particip], axis=1)

    weights = cfg["scoring_weights"]
    metrics["composite_score"] = _composite_score(metrics, weights).round(2)
    metrics["tier"] = _classify(metrics["composite_score"], cfg["tier_thresholds"])

    # Add human-readable participation rate and mean latency for the report
    metrics["participation_rate_pct"] = (metrics["uptime_rate"] * 100).round(2)
    participated = df[df["participated"]]
    metrics["mean_latency_ms"] = (
        participated.groupby("operator_address")["submission_latency_ms"].mean().round(1)
    )
    metrics["mean_deviation_pct"] = (
        df[df["participated"] & df["aggregated_price"].notna()]
        .assign(abs_dev=lambda d: (d["submitted_price"] - d["aggregated_price"]).abs() / d["aggregated_price"] * 100)
        .groupby("operator_address")["abs_dev"].mean()
        .round(4)
    )

    metrics = metrics.reset_index().sort_values("composite_score", ascending=False)

    Path(scores_path).parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(scores_path, index=False)

    return metrics


# ---------------------------------------------------------------------------
# Leaderboard display
# ---------------------------------------------------------------------------

def print_leaderboard(scores: pd.DataFrame) -> None:
    scores = scores.sort_values("composite_score", ascending=False).reset_index(drop=True)

    TIER_COLOUR = {"Tier 1": "\033[92m", "Tier 2": "\033[93m", "At Risk": "\033[91m"}
    RESET = "\033[0m"

    header = (
        f"{'#':<4} {'Address':<14} {'Score':>7} {'Tier':<10} "
        f"{'Participation':>14} {'Avg Latency':>12} {'Avg Dev%':>10}"
    )
    print()
    print("=" * len(header))
    print("  CHAINLINK NODE OPERATOR LEADERBOARD")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for rank, row in scores.iterrows():
        colour = TIER_COLOUR.get(row["tier"], "")
        short_addr = row["operator_address"][:10] + "…"
        print(
            f"{rank + 1:<4} {short_addr:<14} {row['composite_score']:>7.2f} "
            f"{colour}{row['tier']:<10}{RESET} "
            f"{row['participation_rate_pct']:>13.2f}% "
            f"{row['mean_latency_ms']:>11.1f}ms "
            f"{row['mean_deviation_pct']:>9.4f}%"
        )

    print("=" * len(header))

    tier_counts = scores["tier"].value_counts()
    for tier in ["Tier 1", "Tier 2", "At Risk"]:
        print(f"  {tier}: {tier_counts.get(tier, 0)} operators")
    print("=" * len(header))
    print()


if __name__ == "__main__":
    print("Loading submissions and computing scores…")
    scores = run()
    print(f"Scores saved to {SCORES_PATH}\n")
    print_leaderboard(scores)
