"""
Chainlink Node Operator Intelligence — end-to-end pipeline runner.

Usage
-----
  python main.py                          # full pipeline
  python main.py --regenerate             # force-regenerate synthetic data
  python main.py --operator 0xABC123      # single-operator report
  python main.py --real-data              # placeholder for v2 Graph integration
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

RAW_PATH    = ROOT / "data" / "raw_submissions.csv"
SCORES_PATH = ROOT / "data" / "operator_scores.csv"
OUTPUTS_DIR = ROOT / "outputs"


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

def _step(label: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")


def _done(msg: str, elapsed: float) -> None:
    print(f"  ✓ {msg}  ({elapsed:.1f}s)")


def step_generate(force: bool) -> None:
    _step("Step 1 — Synthetic data")

    if RAW_PATH.exists() and not force:
        size_mb = RAW_PATH.stat().st_size / 1_048_576
        print(f"  Found {RAW_PATH.name} ({size_mb:.1f} MB) — skipping generation.")
        print(f"  Pass --regenerate to overwrite.")
        return

    from src.data_generator import generate

    t0 = time.monotonic()
    df = generate(output_path=RAW_PATH)
    rounds = df["round_id"].nunique()
    rows   = len(df)
    _done(f"Generated {rounds:,} rounds / {rows:,} rows → {RAW_PATH}", time.monotonic() - t0)


def step_score() -> None:
    _step("Step 2 — Scoring engine")

    from src.scoring_engine import run as score_run, print_leaderboard

    t0 = time.monotonic()
    scores = score_run(raw_path=RAW_PATH, scores_path=SCORES_PATH)
    _done(f"Scored {len(scores)} operators → {SCORES_PATH}", time.monotonic() - t0)
    print()
    print_leaderboard(scores)


def step_reports() -> None:
    _step("Step 3 — Report generation")

    from src.report_generator import run as report_run

    t0 = time.monotonic()
    report_run(scores_path=SCORES_PATH, outputs_dir=OUTPUTS_DIR)
    n = len(list(OUTPUTS_DIR.glob("operator_*_report.md")))
    _done(
        f"{n} operator reports + network_summary.md → {OUTPUTS_DIR}/",
        time.monotonic() - t0,
    )


def step_operator_report(address: str) -> None:
    """Generate and print a single operator's report to stdout."""
    _step(f"Single-operator report — {address}")

    import pandas as pd
    from src.report_generator import _operator_report, _load_config

    if not SCORES_PATH.exists():
        print(f"  ERROR: {SCORES_PATH} not found. Run the full pipeline first.")
        sys.exit(1)

    net = (
        pd.read_csv(SCORES_PATH)
        .sort_values("composite_score", ascending=False)
        .reset_index(drop=True)
    )

    # Case-insensitive prefix match so short addresses work
    needle = address.lower()
    mask = net["operator_address"].str.lower().str.startswith(needle)
    matches = net[mask]

    if matches.empty:
        print(f"  ERROR: No operator found matching '{address}'.")
        print(f"  Known addresses:")
        for addr in net["operator_address"]:
            print(f"    {addr}")
        sys.exit(1)

    if len(matches) > 1:
        print(f"  ERROR: '{address}' matches {len(matches)} operators — be more specific:")
        for addr in matches["operator_address"]:
            print(f"    {addr}")
        sys.exit(1)

    row  = matches.iloc[0]
    rank = int(matches.index[0]) + 1
    cfg  = _load_config()

    content = _operator_report(row, net, rank, cfg)

    # Write file
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    short    = row["operator_address"][2:10].lower()
    out_path = OUTPUTS_DIR / f"operator_{short}_report.md"
    out_path.write_text(content, encoding="utf-8")

    # Also print to console
    print(content)
    print(f"\n  ✓ Saved to {out_path}")


def step_summary() -> None:
    _step("Pipeline complete — summary")

    import pandas as pd

    if not SCORES_PATH.exists():
        return

    scores = pd.read_csv(SCORES_PATH)
    tier_counts = scores["tier"].value_counts().reindex(["Tier 1", "Tier 2", "At Risk"], fill_value=0)
    n = len(scores)

    ICONS = {"Tier 1": "🟢", "Tier 2": "🟡", "At Risk": "🔴"}

    print(f"  Operators evaluated : {n}")
    print(f"  Median score        : {scores['composite_score'].median():.2f}")
    print(f"  Score range         : {scores['composite_score'].min():.2f} – {scores['composite_score'].max():.2f}")
    print()
    for tier in ["Tier 1", "Tier 2", "At Risk"]:
        count = tier_counts[tier]
        bar   = "█" * count + "░" * (n - count)
        print(f"  {ICONS[tier]} {tier:<10}  {count:>2} operators  {bar}")

    print()
    print(f"  Reports → {OUTPUTS_DIR}/")
    print(f"  Scores  → {SCORES_PATH}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chainlink Node Operator Intelligence pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap_dedent(
            """\
            Examples:
              python main.py
              python main.py --regenerate
              python main.py --operator 0xA1B2C3D4
              python main.py --real-data
            """
        ),
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Force re-generation of synthetic data even if raw_submissions.csv exists.",
    )
    parser.add_argument(
        "--operator",
        metavar="ADDRESS",
        help="Generate a report for a single operator (full address or unique prefix).",
    )
    parser.add_argument(
        "--real-data",
        action="store_true",
        dest="real_data",
        help="(v2 placeholder) Pull live data from The Graph instead of synthetic data.",
    )
    return parser.parse_args()


def textwrap_dedent(s: str) -> str:
    import textwrap
    return textwrap.dedent(s)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   Chainlink Node Operator Intelligence                  ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # ── Real-data placeholder ──────────────────────────────────────────────
    if args.real_data:
        _step("Data source — The Graph (v2 placeholder)")
        print("  Real data via The Graph coming in v2.")
        print()
        print("  Planned implementation:")
        print("    • Query Chainlink OCR contract events via The Graph subgraph")
        print("    • Map NewTransmission events → round submissions per operator")
        print("    • Drop result into the same DataFrame schema as raw_submissions.csv")
        print("    • The scoring and reporting pipeline is unchanged")
        print()
        print("  Track progress: src/data_sources/thegraph.py (not yet created)")
        sys.exit(0)

    # ── Single-operator mode ───────────────────────────────────────────────
    if args.operator:
        # Ensure scores exist; run pipeline silently if they don't
        if not SCORES_PATH.exists():
            print("  No scores found — running pipeline first…")
            step_generate(force=False)
            step_score()
        step_operator_report(args.operator)
        sys.exit(0)

    # ── Full pipeline ──────────────────────────────────────────────────────
    t_total = time.monotonic()

    step_generate(force=args.regenerate)
    step_score()
    step_reports()
    step_summary()

    elapsed = time.monotonic() - t_total
    print(f"  Total time: {elapsed:.1f}s")
    print()


if __name__ == "__main__":
    main()
