"""Load raw operator performance data into processed DataFrames."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_raw_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def save_processed(df: pd.DataFrame, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
