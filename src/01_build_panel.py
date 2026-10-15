"""
01_build_panel.py — node-day panel: which client and release line every public node announces each day, and
whether its peers treat it as live.

One pass over every usable gossip day up to DATA_CUTOFF (ok days only, src/lnmetrics/gossip.py). Per node and day:

  inputs     feature_sig, color, alias (node_announcement) and the modal CLTV of the node's own policies (ties →
             lowest). A node whose announcement is not visible that day (last_update == 0, or absent from the nodes
             extract) keeps its previous inputs; a node without policies keeps its previous CLTV mode.
  client     client_fingerprint.classify_node (rules v4)
  line       version_fingerprint.line_indices for operator/high client labels, as positions in that client's
             release-line list (-1 = no line matches): strict range [line_lo, line_hi] = every line out on the day
             that fits the bits; likely range [likely_lo, likely_hi] = the best-fitting line out on the day the node's
             current bits first appeared (sig_since) — a node cannot run a line that did not exist when it began
             announcing those bits, so a release does not relabel nodes whose bits did not change;
             line_status ok | pre-release | unrecognised (as of the day)
  fleet      one managed fleet (config.FLEET_ALIAS_PREFIX): alias prefix, or >= half its channels to a fleet hub
  network    n_channels, capacity_sat (every channel the node is party to)
  liveness   live_cap_{7,14,28}: capacity of channels whose direction toward the node, set by the peer, is enabled
             and was updated within 7/14/28 days of the end of the day (> 0 = live)
  freshness  ann_age_days: days since the node's last announcement (NaN when not announced)

Output: data/panel/date=YYYYMMDD.parquet (one file per day, not committed) and data/panel_manifest.json.

Usage:
  python src/01_build_panel.py                  # full build up to DATA_CUTOFF
  python src/01_build_panel.py --until 20240101 # partial build (testing)
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (DATA_CUTOFF, DATA_DIR, FLEET_ALIAS_PREFIX, FLEET_HUB_MIN_CHANNELS,  # noqa: E402
                    LIVE_FRESH_VARIANTS, LN_PARQUET_DIR, PANEL_DIR)
from lnmetrics import gossip  # noqa: E402
from lnmetrics import version_fingerprint as vf  # noqa: E402
from lnmetrics.client_fingerprint import KNOWN_OPERATOR_CLIENTS, RULES_VERSION, classify_node  # noqa: E402

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INPUTS = ["feature_sig", "color", "alias", "cltv_mode"]
STATE = INPUTS + ["ann_last_update", "has_tor", "has_clearnet", "sig_since"]
VERSION_CONFIDENCE = ("high", "operator")
MANIFEST_PATH = DATA_DIR / "panel_manifest.json"


def _bits(sig) -> frozenset:
    return frozenset(int(b) for b in sig.split(",")) if isinstance(sig, str) and sig else frozenset()


def observed_inputs(nodes: pd.DataFrame, pol: pd.DataFrame) -> pd.DataFrame:
    """Classifier inputs observed on one day; NaN where not observed."""
    n = nodes.drop_duplicates("pub_key").set_index("pub_key")
    announced = n["last_update"].fillna(0) > 0
    mode = (pol.dropna(subset=["time_lock_delta"])
               .groupby(["node_pub", "time_lock_delta"]).size().reset_index(name="n")
               .sort_values(["node_pub", "n", "time_lock_delta"], ascending=[True, False, True])
               .drop_duplicates("node_pub").set_index("node_pub")["time_lock_delta"])
    idx = n.index.union(pd.Index(pol["node_pub"].unique())).union(pd.Index(pol["peer_pub"].unique())) \
        .rename("pub_key")
    return pd.DataFrame({
        "feature_sig": n["feature_sig"].where(announced).reindex(idx),
        "color": n["color"].where(announced).reindex(idx),
        "alias": n["alias"].where(announced).reindex(idx),
        "cltv_mode": mode.reindex(idx).astype("float64"),
        "ann_last_update": n["last_update"].where(announced).reindex(idx).astype("float64"),
        "has_tor": n["has_tor"].reindex(idx),
        "has_clearnet": n["has_clearnet"].reindex(idx),
    }, index=idx)


def carry(state: pd.DataFrame, obs: pd.DataFrame, date: str) -> pd.DataFrame:
    """Effective inputs: observed values, else the node's previous ones; sig_since = first day of the current set."""
    prev = state.reindex(obs.index)
    eff = obs.copy()
    for c in INPUTS + ["ann_last_update", "has_tor", "has_clearnet"]:
        eff[c] = obs[c].where(obs[c].notna(), prev[c])
    eff["feature_sig"] = eff["feature_sig"].fillna("")
    same = prev["feature_sig"].notna() & (eff["feature_sig"] == prev["feature_sig"])
    eff["sig_since"] = prev["sig_since"].where(same, date)
    return eff


def fleet_flags(eff: pd.DataFrame, pol: pd.DataFrame, n_channels: pd.Series) -> pd.Series:
    """Nodes of one managed fleet: alias prefix, or most channels to a fleet hub (fleet alias, many channels)."""
    alias = eff["alias"].fillna("")
    named = alias.str.startswith(FLEET_ALIAS_PREFIX)
    hubs = set(named.index[named & (n_channels.reindex(named.index).fillna(0) >= FLEET_HUB_MIN_CHANNELS)])
    ch = pol.drop_duplicates("channel_id")
    ends = pd.concat([pd.DataFrame({"pk": ch["node_pub"], "hub": ch["peer_pub"].isin(hubs)}),
                      pd.DataFrame({"pk": ch["peer_pub"], "hub": ch["node_pub"].isin(hubs)})])
    to_hub = ends.groupby("pk")["hub"].mean().reindex(eff.index).fillna(0)
    return named | (to_hub >= 0.5)


def network(pol: pd.DataFrame, day_end: float) -> pd.DataFrame:
    ch = pol.drop_duplicates("channel_id")
    ends = pd.concat([ch[["node_pub", "capacity"]].rename(columns={"node_pub": "pk"}),
                      ch[["peer_pub", "capacity"]].rename(columns={"peer_pub": "pk"})])
    out = ends.groupby("pk")["capacity"].agg(n_channels="size", capacity_sat="sum")
    age = (day_end - pol["last_update"]) / 86400
    enabled = ~pol["disabled"].astype(bool)
    for k in LIVE_FRESH_VARIANTS:
        live = pol.loc[enabled & (age < k)].drop_duplicates(["channel_id", "peer_pub"])
        out[f"live_cap_{k}"] = live.groupby("peer_pub")["capacity"].sum()
    return out.fillna({f"live_cap_{k}": 0}).rename_axis("pub_key")


RELEASES = {c: sorted({ln.released for ln in vf.lines(c)}) for c in vf.CLIENTS}


def _release_epoch(client: str, day: str) -> str:
    """Release date of the newest line of `client` out by `day`: line inference only depends on which lines exist."""
    out = "00000000"
    for r in RELEASES[client]:
        if r <= day:
            out = r
    return out


def label(eff: pd.DataFrame, date: str) -> pd.DataFrame:
    """Client and release-line labels, computed once per distinct input combination.
    Strict range as of `date` (every line out today that fits the bits); likely line as of the day the node's current
    bits first appeared, since a node cannot run a line that did not exist when it began announcing those bits."""
    pk = eff.index.to_series()
    key = pd.DataFrame({
        "op": pk.where(pk.isin(KNOWN_OPERATOR_CLIENTS), ""),
        "sig": eff["feature_sig"],
        "lnd_def": (eff["color"] == "#3399ff") | (eff["alias"] == pk.str[:20]),
        "cltv": eff["cltv_mode"].fillna(-1),          # -1 = no policies seen yet
    }, index=eff.index)
    uniq = key.drop_duplicates().reset_index(drop=True)
    cl = [classify_node(_bits(sig), "#3399ff" if lnd_def else None, None, op or None, None if cltv < 0 else float(cltv))
          for op, sig, lnd_def, cltv in uniq.itertuples(index=False)]
    uniq["client"] = [c for c, _, _ in cl]
    uniq["client_confidence"] = [f for _, f, _ in cl]
    out = key.reset_index().merge(uniq, on=["op", "sig", "lnd_def", "cltv"], how="left").set_index("pub_key")

    versioned = out["client_confidence"].isin(VERSION_CONFIDENCE) & out["client"].isin(vf.CLIENTS)
    out["epoch"] = ""
    for c in vf.CLIENTS:
        m = versioned & (out["client"] == c)
        out.loc[m, "epoch"] = eff.loc[out.index[m], "sig_since"].map(lambda d, c=c: _release_epoch(c, d)).to_numpy()
    vk = out.loc[versioned, ["client", "sig", "epoch"]].drop_duplicates()
    rows = []
    for client, sig, epoch in vk.itertuples(index=False):
        bits = _bits(sig)
        lo, hi, _, _ = vf.line_indices(client, bits, date)
        _, _, llo, lhi = vf.line_indices(client, bits, epoch)
        rows.append((client, sig, epoch, lo, hi, llo, lhi, vf.infer_version(client, bits, date).status))
    lab = pd.DataFrame(rows, columns=["client", "sig", "epoch", "line_lo", "line_hi", "likely_lo", "likely_hi",
                                      "line_status"])
    out = out.reset_index().merge(lab, on=["client", "sig", "epoch"], how="left").set_index("pub_key")
    for c in ["line_lo", "line_hi", "likely_lo", "likely_hi"]:
        out[c] = out[c].fillna(-1)
    return out[["client", "client_confidence", "line_lo", "line_hi", "likely_lo", "likely_hi", "line_status"]]


def build_day(state: pd.DataFrame, date: str):
    nodes = gossip.read_nodes(date, ["pub_key", "alias", "color", "last_update", "has_tor", "has_clearnet",
                                     "feature_sig"])
    pol = gossip.read_policies(date, ["channel_id", "capacity", "node_pub", "peer_pub", "disabled",
                                      "last_update", "time_lock_delta"])
    day_end = (pd.Timestamp(date) + pd.Timedelta(days=1)).timestamp()
    obs = observed_inputs(nodes, pol)
    eff = carry(state, obs, date)
    panel = eff.join(label(eff, date)).join(network(pol, day_end))
    panel["fleet"] = fleet_flags(eff, pol, panel["n_channels"])
    panel["ann_observed"] = obs["ann_last_update"].notna()
    panel["ann_age_days"] = (day_end - panel["ann_last_update"]) / 86400
    for c in ["n_channels", "capacity_sat"] + [f"live_cap_{k}" for k in LIVE_FRESH_VARIANTS]:
        panel[c] = panel[c].fillna(0).astype("int64")
    for c in ["line_lo", "line_hi", "likely_lo", "likely_hi"]:
        panel[c] = panel[c].astype("int16")
    panel.insert(0, "date", date)
    # carried state: every node ever seen keeps its last inputs
    new_state = pd.concat([state.drop(index=eff.index, errors="ignore"), eff[STATE]]) if len(state) else eff[STATE]
    return new_state, panel.drop(columns=["ann_last_update"]).reset_index()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--until", help="last day to build (YYYYMMDD), default DATA_CUTOFF")
    args = ap.parse_args()

    dates = [d for d in gossip.gossip_dates() if not args.until or d <= args.until]
    print(f"01_build_panel: {len(dates)} ok gossip days {dates[0]}..{dates[-1]} from {LN_PARQUET_DIR}; "
          f"client rules {RULES_VERSION}, version rules {vf.VERSION_RULES_VERSION}")
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    for f in PANEL_DIR.glob("date=*.parquet"):
        f.unlink()

    state = pd.DataFrame(columns=STATE)
    t0, counts = time.time(), {}
    for i, d in enumerate(dates, 1):
        state, panel = build_day(state, d)
        panel.to_parquet(PANEL_DIR / f"date={d}.parquet", index=False)
        live = panel[panel["live_cap_14"] > 0]
        counts[d] = {"nodes": len(panel), "with_channels": int((panel["n_channels"] > 0).sum()),
                     "live": len(live), "live_by_client": live["client"].value_counts().to_dict()}
        if i % 50 == 0 or i == len(dates):
            print(f"  [{i}/{len(dates)}] {d}: {len(panel):,} nodes, {len(live):,} live ({time.time() - t0:.0f}s)",
                  flush=True)

    manifest = {"data_cutoff": DATA_CUTOFF, "client_rules_version": RULES_VERSION,
                "version_rules_version": vf.VERSION_RULES_VERSION, "days": len(dates),
                "first_day": dates[0], "last_day": dates[-1],
                "built_utc": datetime.now(timezone.utc).isoformat(timespec="minutes"), "per_day": counts}
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"-> {PANEL_DIR} ({len(dates)} files), {MANIFEST_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
