"""
gossip.py — read access to the daily gossip snapshots (read-only; nothing is written next to the inputs).

Inputs (LN_PARQUET_DIR, set in src/config.py):
  gossip_daily/nodes/date=YYYYMMDD.parquet      node announcements per day
  gossip_daily/policies/date=YYYYMMDD.parquet   channel directions per day (node_pub = the node that set the
                                                policy, peer_pub = the other end; `disabled`, `last_update`)
  gossip_daily/_quality.parquet                 per-day manifest: channels, nodes, fresh share, epoch, status

Quality status (from the manifest): ok | partial (< 50% of the epoch's median channel count, or the 2024-05/06
partial dumps) | stale (< 50% of channels updated within 14 days). Only "ok" days are used.

Vantage epochs of our gossip view:
  A  ..2024-04-30  ~42k channels / ~8.4k nodes with channels
  gap 2024-05..06 partial dumps
  B  2024-07-01..  ~41–50k channels / ~11–13k nodes
Compare levels within an epoch.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pandas as pd

from config import DATA_CUTOFF, LN_PARQUET_DIR

PARQUET = Path(LN_PARQUET_DIR)
GOSSIP_NODES = PARQUET / "gossip_daily" / "nodes"
GOSSIP_POLICIES = PARQUET / "gossip_daily" / "policies"
QUALITY_PATH = PARQUET / "gossip_daily" / "_quality.parquet"


def quality() -> pd.DataFrame:
    if not QUALITY_PATH.exists():
        raise FileNotFoundError(f"gossip quality manifest missing: {QUALITY_PATH}")
    q = pd.read_parquet(QUALITY_PATH)
    return q[q["date"] <= DATA_CUTOFF].sort_values("date").reset_index(drop=True)


def gossip_dates() -> List[str]:
    """Usable days (YYYYMMDD, status ok) up to the data cutoff that have both extracts."""
    q = quality()
    ok = q.loc[q["status"] == "ok", "date"]
    return [d for d in ok if (GOSSIP_NODES / f"date={d}.parquet").exists()
            and (GOSSIP_POLICIES / f"date={d}.parquet").exists()]


def read_nodes(date: str, columns: Optional[List[str]] = None) -> pd.DataFrame:
    return pd.read_parquet(GOSSIP_NODES / f"date={date}.parquet", columns=columns)


def read_policies(date: str, columns: Optional[List[str]] = None) -> pd.DataFrame:
    return pd.read_parquet(GOSSIP_POLICIES / f"date={date}.parquet", columns=columns)
