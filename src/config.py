"""
Paths and parameters shared by the pipeline stages.
"""

import os
from pathlib import Path

# Base Paths
SRC_DIR = Path(__file__).resolve().parent
PAPER_ROOT = SRC_DIR.parent
REPO_ROOT = PAPER_ROOT.parent.parent

# Output Paths (written directly into the LaTeX directory)
PAPER_DIR = PAPER_ROOT / "paper"
FIGURES_DIR = PAPER_DIR / "figures"
TABLES_DIR = PAPER_DIR / "tables"
DATA_DIR = PAPER_ROOT / "data"
PANEL_DIR = DATA_DIR / "panel"          # node-day panel built by 01_build_panel.py (not committed)

# Input: daily gossip snapshots as Parquet (layout in src/lnmetrics/gossip.py).
# Set LN_PARQUET_DIR to their location; the default is data/parquet inside this folder (not committed).
LN_PARQUET_DIR = Path(os.environ.get("LN_PARQUET_DIR", DATA_DIR / "parquet"))

# Data cutoff: the last gossip snapshot used in the paper. Every stage truncates its inputs here so that
# reruns reproduce the published numbers.
DATA_CUTOFF = "20261013"

# Liveness: a node is live on a day when at least one channel direction toward it, set by a peer, is enabled
# and was updated within LIVE_FRESH_DAYS. The panel also stores the 7- and 28-day variants for robustness.
LIVE_FRESH_DAYS = 14
LIVE_FRESH_VARIANTS = (7, 14, 28)

# Managed fleet: one operator running many small LND nodes (Aug 2025 on) that announce aliases "LNT.<name>" and peer
# with a few "LNT." hubs. Its nodes are one upgrade decision, so per-node statistics exclude them (panel column
# `fleet`) and report them separately. Hub = a node with the fleet alias and at least this many channels.
FLEET_ALIAS_PREFIX = "LNT."
FLEET_HUB_MIN_CHANNELS = 50

RANDOM_SEED = 42

# Client colours for the figures (paper 01 palette; series are also labelled directly)
CLIENT_PALETTE = {
    "LND": "#2a78d6",
    "CLN": "#D4603A",
    "Eclair": "#1a9e6e",
    "LDK": "#4a3aa7",
    "Unknown": "#8893A0",
}
