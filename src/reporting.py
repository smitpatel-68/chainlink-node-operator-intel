"""Generate operator reports to the outputs directory."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_markdown_report(df: pd.DataFrame, path: str | Path, title: str = "Operator Report") -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(df.to_markdown(index=False))
        f.write("\n")
