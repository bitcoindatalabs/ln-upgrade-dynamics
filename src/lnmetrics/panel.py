"""
panel.py — read the node-day panel written by 01_build_panel.py, and release-line helpers.
"""

from __future__ import annotations

import re
from typing import Callable, Iterable, List, Optional, Tuple

import pandas as pd

from config import LIVE_FRESH_DAYS, PANEL_DIR
from . import version_fingerprint as vf


def panel_dates() -> List[str]:
    return sorted(p.stem.split("=")[1] for p in PANEL_DIR.glob("date=*.parquet"))


def read_day(date: str, columns: Optional[List[str]] = None) -> pd.DataFrame:
    return pd.read_parquet(PANEL_DIR / f"date={date}.parquet", columns=columns)


def load(columns: List[str], where: Optional[Callable[[pd.DataFrame], pd.Series]] = None,
         dates: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """Concatenate panel days (optionally filtered row-wise) with only the needed columns."""
    parts = []
    for d in (dates if dates is not None else panel_dates()):
        p = read_day(d, columns)
        parts.append(p[where(p)] if where is not None else p)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=columns)


def live(p: pd.DataFrame, days: int = LIVE_FRESH_DAYS) -> pd.Series:
    """Peers treat the node as reachable: an enabled, fresh direction toward it."""
    return p[f"live_cap_{days}"] > 0


def signed_at(p: pd.DataFrame) -> pd.Series:
    """UTC time at which the node signed the announcement it shows on that day (its `timestamp` field), from the
    panel's `date` (datetime) and `ann_age_days` (days from the signature to the end of the day)."""
    return p["date"] + pd.Timedelta(days=1) - pd.to_timedelta(p["ann_age_days"], unit="D")


# ---------------------------------------------------------------------------------------
# Release lines
# ---------------------------------------------------------------------------------------
def version_tuple(s: str) -> Tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", s.split("rc")[0].split("-")[0]))


def line_of_version(client: str, version: str) -> int:
    """Index of the release line containing a version string (e.g. "23.08.1", "0.11.0.1"); -1 if before the table."""
    v = version_tuple(version)
    idx = -1
    for ln in vf.lines(client):
        if version_tuple(ln.first) <= v:
            idx = ln.index
    return idx


def line_label(client: str, i: int) -> str:
    return vf.lines(client)[i].label if i >= 0 else "none"


def line_release(client: str, i: int) -> pd.Timestamp:
    return pd.Timestamp(vf.lines(client)[i].released)
