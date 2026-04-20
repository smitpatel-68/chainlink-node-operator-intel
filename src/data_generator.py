"""Generate synthetic Chainlink ETH/USD price feed submission data."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw_submissions.csv"

# ---------------------------------------------------------------------------
# Operator profiles
# ---------------------------------------------------------------------------

OPERATORS: list[dict] = [
    # High performers (3)
    {"address": "0xA1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0", "tier": "high",   "latency_mean": 220, "latency_std": 40,  "participation_rate": 0.99, "price_bias": 0.0002},
    {"address": "0xB2C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0C1", "tier": "high",   "latency_mean": 240, "latency_std": 45,  "participation_rate": 0.99, "price_bias": -0.0001},
    {"address": "0xC3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0C1D2", "tier": "high",   "latency_mean": 260, "latency_std": 50,  "participation_rate": 0.98, "price_bias": 0.0001},
    # Mid performers (14)
    {"address": "0xD4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0C1D2E3", "tier": "mid",    "latency_mean": 380, "latency_std": 120, "participation_rate": 0.97, "price_bias": 0.0003},
    {"address": "0xE5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0C1D2E3F4", "tier": "mid",    "latency_mean": 400, "latency_std": 130, "participation_rate": 0.97, "price_bias": -0.0002},
    {"address": "0xF6A7B8C9D0E1F2A3B4C5D6E7F8A9B0C1D2E3F4A5", "tier": "mid",    "latency_mean": 390, "latency_std": 125, "participation_rate": 0.96, "price_bias": 0.0001},
    {"address": "0xA7B8C9D0E1F2A3B4C5D6E7F8A9B0C1D2E3F4A5B6", "tier": "mid",    "latency_mean": 420, "latency_std": 140, "participation_rate": 0.96, "price_bias": -0.0003},
    {"address": "0xB8C9D0E1F2A3B4C5D6E7F8A9B0C1D2E3F4A5B6C7", "tier": "mid",    "latency_mean": 410, "latency_std": 135, "participation_rate": 0.97, "price_bias": 0.0002},
    {"address": "0xC9D0E1F2A3B4C5D6E7F8A9B0C1D2E3F4A5B6C7D8", "tier": "mid",    "latency_mean": 440, "latency_std": 145, "participation_rate": 0.96, "price_bias": 0.0000},
    {"address": "0xD0E1F2A3B4C5D6E7F8A9B0C1D2E3F4A5B6C7D8E9", "tier": "mid",    "latency_mean": 360, "latency_std": 115, "participation_rate": 0.97, "price_bias": -0.0001},
    {"address": "0xE1F2A3B4C5D6E7F8A9B0C1D2E3F4A5B6C7D8E9F0", "tier": "mid",    "latency_mean": 430, "latency_std": 140, "participation_rate": 0.96, "price_bias": 0.0003},
    {"address": "0xF2A3B4C5D6E7F8A9B0C1D2E3F4A5B6C7D8E9F0A1", "tier": "mid",    "latency_mean": 400, "latency_std": 130, "participation_rate": 0.95, "price_bias": -0.0002},
    {"address": "0xA3B4C5D6E7F8A9B0C1D2E3F4A5B6C7D8E9F0A1B2", "tier": "mid",    "latency_mean": 450, "latency_std": 150, "participation_rate": 0.95, "price_bias": 0.0001},
    {"address": "0xB4C5D6E7F8A9B0C1D2E3F4A5B6C7D8E9F0A1B2C3", "tier": "mid",    "latency_mean": 370, "latency_std": 120, "participation_rate": 0.97, "price_bias": 0.0000},
    {"address": "0xC5D6E7F8A9B0C1D2E3F4A5B6C7D8E9F0A1B2C3D4", "tier": "mid",    "latency_mean": 415, "latency_std": 135, "participation_rate": 0.96, "price_bias": -0.0003},
    {"address": "0xD6E7F8A9B0C1D2E3F4A5B6C7D8E9F0A1B2C3D4E5", "tier": "mid",    "latency_mean": 395, "latency_std": 128, "participation_rate": 0.96, "price_bias": 0.0002},
    {"address": "0xE7F8A9B0C1D2E3F4A5B6C7D8E9F0A1B2C3D4E5F6", "tier": "mid",    "latency_mean": 425, "latency_std": 142, "participation_rate": 0.95, "price_bias": -0.0001},
    # Poor performers (3)
    {"address": "0xF8A9B0C1D2E3F4A5B6C7D8E9F0A1B2C3D4E5F6A7", "tier": "low",    "latency_mean": 700, "latency_std": 250, "participation_rate": 0.82, "price_bias": 0.0015},
    {"address": "0xA9B0C1D2E3F4A5B6C7D8E9F0A1B2C3D4E5F6A7B8", "tier": "low",    "latency_mean": 780, "latency_std": 280, "participation_rate": 0.79, "price_bias": -0.0018},
    {"address": "0xB0C1D2E3F4A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9", "tier": "low",    "latency_mean": 650, "latency_std": 230, "participation_rate": 0.81, "price_bias": 0.0012},
]

DAYS = 30
ROUND_INTERVAL_SECONDS = 60
START_TIMESTAMP = 1_700_000_000  # ~Nov 2023
TOTAL_ROUNDS = DAYS * 24 * 60  # one round per minute


def _simulate_eth_price(n_rounds: int, seed: int = 42) -> np.ndarray:
    """Simulate ETH/USD price as a geometric Brownian motion walk around $2000."""
    rng = np.random.default_rng(seed)
    start_price = 2000.0
    mu = 0.00001      # slight upward drift per round
    sigma = 0.0008    # volatility per round
    shocks = rng.normal(mu, sigma, n_rounds)
    log_prices = np.cumsum(shocks)
    return start_price * np.exp(log_prices)


def generate(seed: int = 42, output_path: str | Path = OUTPUT_PATH) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    random.seed(seed)

    true_prices = _simulate_eth_price(TOTAL_ROUNDS, seed=seed)
    timestamps = np.arange(START_TIMESTAMP, START_TIMESTAMP + TOTAL_ROUNDS * ROUND_INTERVAL_SECONDS, ROUND_INTERVAL_SECONDS)

    rows: list[dict] = []

    for round_id, (ts, true_price) in enumerate(zip(timestamps, true_prices), start=1):
        round_submissions: list[float] = []

        for op in OPERATORS:
            participated = rng.random() < op["participation_rate"]

            if participated:
                # Price noise: per-operator systematic bias + round-level noise
                noise = rng.normal(op["price_bias"], 0.0008)
                submitted_price = round(true_price * (1 + noise), 2)

                raw_latency = rng.normal(op["latency_mean"], op["latency_std"])
                latency = max(50, int(raw_latency))

                round_submissions.append(submitted_price)
            else:
                submitted_price = None
                latency = None

            rows.append({
                "round_id": round_id,
                "timestamp": int(ts),
                "operator_address": op["address"],
                "operator_tier": op["tier"],
                "submitted_price": submitted_price,
                "submission_latency_ms": latency,
                "participated": participated,
            })

        # Aggregated price = median of submissions this round
        agg_price = round(float(np.median(round_submissions)), 2) if round_submissions else None

        # Backfill aggregated_price for all rows in this round
        for row in rows[-(len(OPERATORS)):]:
            row["aggregated_price"] = agg_price

    df = pd.DataFrame(rows)
    df["submitted_price"] = df["submitted_price"].astype("Float64")
    df["submission_latency_ms"] = df["submission_latency_ms"].astype("Int64")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    return df


def print_summary(df: pd.DataFrame) -> None:
    total_rounds = df["round_id"].nunique()
    total_rows = len(df)
    price_range = df["aggregated_price"].agg(["min", "max"])

    print("=" * 60)
    print("SYNTHETIC DATA SUMMARY")
    print("=" * 60)
    print(f"Rounds generated   : {total_rounds:,}  ({total_rounds / 1440:.1f} days)")
    print(f"Total rows         : {total_rows:,}")
    print(f"Operators          : {df['operator_address'].nunique()}")
    print(f"Aggregated price   : ${price_range['min']:.2f} – ${price_range['max']:.2f}")
    print()

    per_op = (
        df.groupby(["operator_address", "operator_tier"])
        .agg(
            participation_rate=("participated", "mean"),
            avg_latency_ms=("submission_latency_ms", "mean"),
            price_deviation_pct=(
                "submitted_price",
                lambda s: (
                    (s - df.loc[s.index, "aggregated_price"]).abs() / df.loc[s.index, "aggregated_price"] * 100
                ).mean()
            ),
            rounds_participated=("participated", "sum"),
        )
        .reset_index()
        .sort_values(["operator_tier", "participation_rate"], ascending=[True, False])
    )
    per_op["participation_rate"] = per_op["participation_rate"].map("{:.1%}".format)
    per_op["avg_latency_ms"] = per_op["avg_latency_ms"].map("{:.0f}".format)
    per_op["price_deviation_pct"] = per_op["price_deviation_pct"].map("{:.4f}%".format)
    per_op["short_addr"] = per_op["operator_address"].str[:10] + "…"

    print(
        per_op[["short_addr", "operator_tier", "participation_rate", "avg_latency_ms", "price_deviation_pct", "rounds_participated"]]
        .to_string(index=False)
    )
    print("=" * 60)


if __name__ == "__main__":
    print("Generating 30 days of ETH/USD feed submission data…")
    df = generate()
    print(f"Saved to {OUTPUT_PATH}\n")
    print_summary(df)
