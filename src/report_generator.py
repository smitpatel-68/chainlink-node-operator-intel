"""Generate per-operator markdown reports and a network-wide summary."""

from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCORES_PATH = ROOT / "data" / "operator_scores.csv"
OUTPUTS_DIR = ROOT / "outputs"
CONFIG_PATH = ROOT / "config.yaml"

METRIC_LABELS = {
    "uptime_rate":               "Uptime Rate",
    "latency_score":             "Latency Score",
    "deviation_accuracy_score":  "Deviation Accuracy",
    "round_participation_score": "Round Participation",
}

METRIC_DESCRIPTIONS = {
    "uptime_rate":               "fraction of rounds with a submission delivered within the latency benchmark",
    "latency_score":             "submission speed normalised to 0–100 (100 = at or below the 400 ms benchmark)",
    "deviation_accuracy_score":  "closeness to the aggregated median price (100 = ≤0.05% deviation)",
    "round_participation_score": "percentage of rounds where a submission was recorded",
}

TIER_MULTIPLIERS = {"Tier 1": 1.50, "Tier 2": 1.20, "At Risk": 0.75}
TIER_COLOURS = {"Tier 1": "🟢", "Tier 2": "🟡", "At Risk": "🔴"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _percentile_rank(series: pd.Series, value: float) -> float:
    """Return what percentile *value* sits at within *series* (0–100)."""
    return float((series < value).mean() * 100)


def _top_pct(series: pd.Series, value: float) -> int:
    """Return the top-N% label: e.g. value in top 15% → 15."""
    return round(100 - _percentile_rank(series, value))


def _metric_narrative(row: pd.Series, net: pd.DataFrame, cfg: dict) -> list[str]:
    """
    Return a list of plain-English sentences describing what is driving
    the operator's classification — strengths first, then concerns.
    """
    thresholds = cfg["tier_thresholds"]
    benchmark_ms = cfg["latency_benchmark_ms"]
    sentences: list[str] = []

    # Uptime
    uptime_pct = row["uptime_rate"] * 100
    uptime_top = _top_pct(net["uptime_rate"], row["uptime_rate"])
    if uptime_pct >= 95:
        sentences.append(
            f"Your uptime rate of **{uptime_pct:.1f}%** places you in the top {uptime_top}% "
            f"of the network — a strong signal of reliable availability."
        )
    elif uptime_pct >= 80:
        sentences.append(
            f"Your uptime rate of **{uptime_pct:.1f}%** is adequate but leaves room for improvement; "
            f"the Tier 1 threshold requires consistent on-time submissions."
        )
    else:
        sentences.append(
            f"Your uptime rate of **{uptime_pct:.1f}%** is below the network median, "
            f"which is the primary drag on your composite score."
        )

    # Latency
    lat_top = _top_pct(net["latency_score"], row["latency_score"])
    if row["mean_latency_ms"] <= benchmark_ms:
        sentences.append(
            f"Your average submission latency of **{row['mean_latency_ms']:.0f} ms** is within "
            f"the {benchmark_ms} ms benchmark, placing your latency score in the top {lat_top}% of the network."
        )
    else:
        over = row["mean_latency_ms"] - benchmark_ms
        sentences.append(
            f"Your average latency of **{row['mean_latency_ms']:.0f} ms** exceeds the "
            f"{benchmark_ms} ms benchmark by {over:.0f} ms, reducing your latency score significantly."
        )

    # Deviation accuracy
    dev_top = _top_pct(net["deviation_accuracy_score"], row["deviation_accuracy_score"])
    dev_threshold = cfg["deviation_threshold_pct"]
    if row["mean_deviation_pct"] <= dev_threshold:
        sentences.append(
            f"Your mean price deviation of **{row['mean_deviation_pct']:.4f}%** is within the "
            f"{dev_threshold}% accuracy threshold, ranking in the top {dev_top}% for data quality."
        )
    elif row["mean_deviation_pct"] <= dev_threshold * 2:
        sentences.append(
            f"Your mean price deviation of **{row['mean_deviation_pct']:.4f}%** is slightly above "
            f"the {dev_threshold}% target — closer data sourcing could lift your accuracy score."
        )
    else:
        sentences.append(
            f"Your mean price deviation of **{row['mean_deviation_pct']:.4f}%** is materially above "
            f"the {dev_threshold}% threshold, suggesting a data-source quality issue that warrants investigation."
        )

    # Participation
    part_pct = row["round_participation_score"]
    if part_pct >= 97:
        sentences.append(
            f"Round participation of **{part_pct:.1f}%** is excellent and fully satisfies the Tier 1 standard."
        )
    elif part_pct >= 90:
        sentences.append(
            f"Round participation of **{part_pct:.1f}%** meets the Tier 2 threshold but falls short of the "
            f"95%+ rate expected of top-tier operators."
        )
    else:
        sentences.append(
            f"Round participation of **{part_pct:.1f}%** is below network norms and is directly lowering "
            f"your composite score — investigate missed rounds for infra or connectivity issues."
        )

    # Overall classification sentence
    score = row["composite_score"]
    tier = row["tier"]
    net_median = net["composite_score"].median()
    diff = score - net_median
    direction = "above" if diff >= 0 else "below"
    sentences.append(
        f"Overall, your composite score of **{score:.2f}** is "
        f"**{abs(diff):.2f} points {direction}** the network median of {net_median:.2f}, "
        f"resulting in a **{tier}** classification."
    )

    return sentences


# ---------------------------------------------------------------------------
# Per-operator report
# ---------------------------------------------------------------------------

def _operator_report(row: pd.Series, net: pd.DataFrame, rank: int, cfg: dict) -> str:
    addr = row["operator_address"]
    tier = row["tier"]
    score = row["composite_score"]
    net_median = net["composite_score"].median()
    n_ops = len(net)
    multiplier = TIER_MULTIPLIERS[tier]
    icon = TIER_COLOURS[tier]
    weights = cfg["scoring_weights"]
    thresholds = cfg["tier_thresholds"]

    # Metric scores as 0-100 values
    metric_raw = {
        "uptime_rate":               row["uptime_rate"] * 100,
        "latency_score":             row["latency_score"],
        "deviation_accuracy_score":  row["deviation_accuracy_score"],
        "round_participation_score": row["round_participation_score"],
    }

    # Percentile ranks
    metric_pctile = {
        k: _percentile_rank(net[k], row[k])
        for k in ["uptime_rate", "latency_score", "deviation_accuracy_score", "round_participation_score"]
    }

    narrative = _metric_narrative(row, net, cfg)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []

    lines += [
        f"# Operator Report",
        f"",
        f"**Address:** `{addr}`  ",
        f"**Generated:** {now}  ",
        f"**Network rank:** {rank} / {n_ops}",
        f"",
        f"---",
        f"",
        f"## Classification",
        f"",
        f"| | |",
        f"|---|---|",
        f"| Tier | {icon} **{tier}** |",
        f"| Composite Score | **{score:.2f}** / 100 |",
        f"| Network Median | {net_median:.2f} |",
        f"| vs. Median | {'▲' if score >= net_median else '▼'} {abs(score - net_median):.2f} pts |",
        f"| Network Rank | {rank} of {n_ops} (top {round(rank / n_ops * 100)}%) |",
        f"",
        f"---",
        f"",
        f"## Metric Breakdown",
        f"",
        f"| Metric | Score | Network Percentile | Weight | Weighted Contribution |",
        f"|--------|------:|-------------------:|-------:|----------------------:|",
    ]

    weight_map = {
        "uptime_rate":               weights["uptime_rate"],
        "latency_score":             weights["latency_percentile"],
        "deviation_accuracy_score":  weights["deviation_accuracy"],
        "round_participation_score": weights["round_participation"],
    }

    for col, label in METRIC_LABELS.items():
        s = metric_raw[col]
        pct = metric_pctile[col]
        w = weight_map[col]
        contrib = s * w
        bar = "█" * int(s / 10) + "░" * (10 - int(s / 10))
        lines.append(
            f"| {label} | {s:.1f} `{bar}` | {pct:.0f}th | {w:.0%} | {contrib:.2f} |"
        )

    lines += [
        f"",
        f"### Raw Observations",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Mean submission latency | {row['mean_latency_ms']:.1f} ms |",
        f"| Mean price deviation | {row['mean_deviation_pct']:.4f}% |",
        f"| On-time participation rate | {row['participation_rate_pct']:.2f}% |",
        f"| Raw round participation | {row['round_participation_score']:.2f}% |",
        f"",
        f"---",
        f"",
        f"## Performance Analysis",
        f"",
    ]

    for sentence in narrative:
        lines.append(f"- {sentence}")

    lines += [
        f"",
        f"---",
        f"",
        f"## What This Means for Your Compensation",
        f"",
    ]

    if tier == "Tier 1":
        lines += [
            f"As a **Tier 1** operator you qualify for the **maximum performance multiplier of {multiplier}×** "
            f"on your base LINK compensation.",
            f"",
            f"This reflects the network's recognition that your submissions are fast, accurate, and highly "
            f"available — the qualities most critical to Chainlink's data-quality guarantee.",
            f"",
            f"| Scenario | Base (1.0×) | Your multiplier ({multiplier}×) |",
            f"|----------|------------|--------------------------------|",
            f"| 1,000 LINK/month | 1,000 LINK | **{1000 * multiplier:,.0f} LINK** |",
            f"| 5,000 LINK/month | 5,000 LINK | **{5000 * multiplier:,.0f} LINK** |",
            f"",
            f"**To maintain Tier 1:** sustain latency below {cfg['latency_benchmark_ms']} ms, "
            f"price deviation below {cfg['deviation_threshold_pct']}%, and participation above "
            f"{thresholds['tier_1'] - 5}%.",
        ]
    elif tier == "Tier 2":
        gap = score - thresholds["tier_1"]  # negative
        lines += [
            f"As a **Tier 2** operator you qualify for a **{multiplier}× performance multiplier** "
            f"on your base LINK compensation.",
            f"",
            f"You are **{abs(gap):.1f} points** away from the Tier 1 threshold of "
            f"{thresholds['tier_1']}. Closing this gap would increase your multiplier "
            f"from {multiplier}× to {TIER_MULTIPLIERS['Tier 1']}×.",
            f"",
            f"| Scenario | Tier 2 ({multiplier}×) | Tier 1 ({TIER_MULTIPLIERS['Tier 1']}×) | Monthly gain |",
            f"|----------|----------------------|--------------------------------------|-------------|",
            f"| 1,000 LINK/month | {1000 * multiplier:,.0f} LINK | {1000 * TIER_MULTIPLIERS['Tier 1']:,.0f} LINK | "
            f"**+{1000 * (TIER_MULTIPLIERS['Tier 1'] - multiplier):,.0f} LINK** |",
            f"| 5,000 LINK/month | {5000 * multiplier:,.0f} LINK | {5000 * TIER_MULTIPLIERS['Tier 1']:,.0f} LINK | "
            f"**+{5000 * (TIER_MULTIPLIERS['Tier 1'] - multiplier):,.0f} LINK** |",
            f"",
            f"**Priority actions to reach Tier 1:** focus on the metrics with the largest gap to "
            f"network top-quartile (see Metric Breakdown above).",
        ]
    else:
        gap_t2 = score - thresholds["tier_2"]  # negative
        lines += [
            f"As an **At Risk** operator you are currently on a **{multiplier}× multiplier**, "
            f"significantly below the standard rate paid to Tier 2 and Tier 1 operators.",
            f"",
            f"You are **{abs(gap_t2):.1f} points** below the Tier 2 threshold of "
            f"{thresholds['tier_2']}. Continued At Risk classification may result in removal "
            f"from the feed.",
            f"",
            f"| Scenario | At Risk ({multiplier}×) | Tier 2 ({TIER_MULTIPLIERS['Tier 2']}×) | Tier 1 ({TIER_MULTIPLIERS['Tier 1']}×) |",
            f"|----------|-----------------------|--------------------------------------|--------------------------------------|",
            f"| 1,000 LINK/month | {1000 * multiplier:,.0f} LINK | {1000 * TIER_MULTIPLIERS['Tier 2']:,.0f} LINK | {1000 * TIER_MULTIPLIERS['Tier 1']:,.0f} LINK |",
            f"| 5,000 LINK/month | {5000 * multiplier:,.0f} LINK | {5000 * TIER_MULTIPLIERS['Tier 2']:,.0f} LINK | {5000 * TIER_MULTIPLIERS['Tier 1']:,.0f} LINK |",
            f"",
            f"**Immediate actions required:** address the root causes identified in the Performance "
            f"Analysis section above. Operators who do not reach Tier 2 within the next review "
            f"period risk off-boarding from the feed.",
        ]

    lines += [
        f"",
        f"---",
        f"",
        f"## Network Context",
        f"",
        f"| | Value |",
        f"|---|---|",
        f"| Your rank | {rank} of {n_ops} |",
        f"| Operators above you | {rank - 1} |",
        f"| Operators below you | {n_ops - rank} |",
        f"| Network median score | {net_median:.2f} |",
        f"| Network top-quartile score | {net['composite_score'].quantile(0.75):.2f} |",
        f"| Network bottom-quartile score | {net['composite_score'].quantile(0.25):.2f} |",
        f"",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Network summary report
# ---------------------------------------------------------------------------

def _network_summary(net: pd.DataFrame, cfg: dict) -> str:
    n = len(net)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    tier_counts = net["tier"].value_counts().reindex(["Tier 1", "Tier 2", "At Risk"], fill_value=0)
    median_score = net["composite_score"].median()
    mean_score = net["composite_score"].mean()
    top5 = net.head(5).reset_index(drop=True)
    bottom5 = net.tail(5).sort_values("composite_score").reset_index(drop=True)

    # Health score: weighted combination of tier distribution and median score
    health_score = (
        tier_counts["Tier 1"] / n * 50
        + (1 - tier_counts["At Risk"] / n) * 30
        + (median_score / 100) * 20
    )
    if health_score >= 75:
        health_label = "🟢 Healthy"
    elif health_score >= 50:
        health_label = "🟡 Moderate"
    else:
        health_label = "🔴 At Risk"

    lines: list[str] = []
    lines += [
        f"# Network Summary Report",
        f"",
        f"**Generated:** {now}  ",
        f"**Operators evaluated:** {n}  ",
        f"**Network health:** {health_label} ({health_score:.1f} / 100)",
        f"",
        f"---",
        f"",
        f"## Tier Distribution",
        f"",
        f"| Tier | Operators | Share |",
        f"|------|----------:|------:|",
    ]

    for tier in ["Tier 1", "Tier 2", "At Risk"]:
        count = tier_counts[tier]
        share = count / n * 100
        icon = TIER_COLOURS[tier]
        lines.append(f"| {icon} {tier} | {count} | {share:.1f}% |")

    lines += [
        f"",
        f"---",
        f"",
        f"## Score Distribution",
        f"",
        f"| Statistic | Value |",
        f"|-----------|------:|",
        f"| Mean score | {mean_score:.2f} |",
        f"| Median score | {median_score:.2f} |",
        f"| Top-quartile (P75) | {net['composite_score'].quantile(0.75):.2f} |",
        f"| Bottom-quartile (P25) | {net['composite_score'].quantile(0.25):.2f} |",
        f"| Highest score | {net['composite_score'].max():.2f} |",
        f"| Lowest score | {net['composite_score'].min():.2f} |",
        f"| Std deviation | {net['composite_score'].std():.2f} |",
        f"",
        f"---",
        f"",
        f"## Top 5 Operators",
        f"",
        f"| Rank | Address | Score | Tier | Latency | Deviation | Participation |",
        f"|-----:|---------|------:|------|--------:|----------:|--------------:|",
    ]

    for i, row in top5.iterrows():
        icon = TIER_COLOURS[row["tier"]]
        lines.append(
            f"| {i + 1} | `{row['operator_address'][:18]}…` | **{row['composite_score']:.2f}** | "
            f"{icon} {row['tier']} | {row['mean_latency_ms']:.0f} ms | "
            f"{row['mean_deviation_pct']:.4f}% | {row['round_participation_score']:.1f}% |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## Bottom 5 Operators",
        f"",
        f"| Rank | Address | Score | Tier | Latency | Deviation | Participation |",
        f"|-----:|---------|------:|------|--------:|----------:|--------------:|",
    ]

    for i, row in bottom5.iterrows():
        rank = n - len(bottom5) + i + 1
        icon = TIER_COLOURS[row["tier"]]
        lines.append(
            f"| {rank} | `{row['operator_address'][:18]}…` | {row['composite_score']:.2f} | "
            f"{icon} {row['tier']} | {row['mean_latency_ms']:.0f} ms | "
            f"{row['mean_deviation_pct']:.4f}% | {row['round_participation_score']:.1f}% |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## Network Health Metrics",
        f"",
        f"| Metric | Value | Assessment |",
        f"|--------|------:|-----------|",
    ]

    avg_latency = net["mean_latency_ms"].mean()
    avg_deviation = net["mean_deviation_pct"].mean()
    avg_participation = net["round_participation_score"].mean()
    at_risk_pct = tier_counts["At Risk"] / n * 100
    benchmark_ms = cfg["latency_benchmark_ms"]
    dev_threshold = cfg["deviation_threshold_pct"]

    def _assess(value: float, good: float, bad: float, lower_is_better: bool = False) -> str:
        if lower_is_better:
            if value <= good:
                return "🟢 Good"
            elif value <= bad:
                return "🟡 Fair"
            return "🔴 Poor"
        else:
            if value >= good:
                return "🟢 Good"
            elif value >= bad:
                return "🟡 Fair"
            return "🔴 Poor"

    lines += [
        f"| Avg network latency | {avg_latency:.0f} ms | {_assess(avg_latency, benchmark_ms, benchmark_ms * 1.5, lower_is_better=True)} |",
        f"| Avg price deviation | {avg_deviation:.4f}% | {_assess(avg_deviation, dev_threshold, dev_threshold * 2, lower_is_better=True)} |",
        f"| Avg participation rate | {avg_participation:.1f}% | {_assess(avg_participation, 95, 85)} |",
        f"| At Risk operator share | {at_risk_pct:.1f}% | {_assess(at_risk_pct, 5, 15, lower_is_better=True)} |",
        f"| Tier 1 share | {tier_counts['Tier 1'] / n * 100:.1f}% | {_assess(tier_counts['Tier 1'] / n * 100, 50, 30)} |",
        f"",
        f"---",
        f"",
        f"## Compensation Exposure",
        f"",
        f"Assuming a 1,000 LINK/month base allocation per operator:",
        f"",
        f"| Tier | Operators | Multiplier | Total payout |",
        f"|------|----------:|----------:|-------------:|",
    ]

    base = 1000
    total = 0
    for tier in ["Tier 1", "Tier 2", "At Risk"]:
        count = int(tier_counts[tier])
        mult = TIER_MULTIPLIERS[tier]
        payout = count * base * mult
        total += payout
        lines.append(f"| {TIER_COLOURS[tier]} {tier} | {count} | {mult}× | {payout:,.0f} LINK |")

    baseline = n * base
    lines += [
        f"| **Total** | **{n}** | — | **{total:,.0f} LINK** |",
        f"",
        f"Flat baseline (all operators at 1.0×): {baseline:,} LINK/month  ",
        f"Performance-adjusted total: {total:,.0f} LINK/month  ",
        f"Delta vs. flat: **{'▲' if total >= baseline else '▼'} {abs(total - baseline):,.0f} LINK** "
        f"({'over' if total >= baseline else 'under'} flat baseline)",
        f"",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(
    scores_path: str | Path = SCORES_PATH,
    outputs_dir: str | Path = OUTPUTS_DIR,
    config_path: str | Path = CONFIG_PATH,
) -> None:
    cfg = _load_config()
    outputs_dir = Path(outputs_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    net = pd.read_csv(scores_path).sort_values("composite_score", ascending=False).reset_index(drop=True)

    print(f"Generating reports for {len(net)} operators…")

    for rank, (_, row) in enumerate(net.iterrows(), start=1):
        content = _operator_report(row, net, rank, cfg)
        short = row["operator_address"][2:10].lower()
        out = outputs_dir / f"operator_{short}_report.md"
        out.write_text(content, encoding="utf-8")

    print(f"  ✓ {len(net)} operator reports written to {outputs_dir}/")

    summary = _network_summary(net, cfg)
    summary_path = outputs_dir / "network_summary.md"
    summary_path.write_text(summary, encoding="utf-8")
    print(f"  ✓ Network summary written to {summary_path}")


if __name__ == "__main__":
    run()
