"""Compute operator performance scores from metrics and config weights."""

from __future__ import annotations

from typing import Mapping

import pandas as pd


def weighted_score(metrics: Mapping[str, float], weights: Mapping[str, float]) -> float:
    return sum(metrics.get(k, 0.0) * w for k, w in weights.items())


def score_dataframe(df: pd.DataFrame, weights: Mapping[str, float]) -> pd.Series:
    return df.apply(lambda row: weighted_score(row.to_dict(), weights), axis=1)
