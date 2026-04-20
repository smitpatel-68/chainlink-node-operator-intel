"""Map performance scores to compensation tiers and multipliers."""

from __future__ import annotations

from typing import Sequence


def tier_for_score(score: float, tiers: Sequence[dict]) -> dict:
    for tier in sorted(tiers, key=lambda t: t["min_score"], reverse=True):
        if score >= tier["min_score"]:
            return tier
    return tiers[-1]
