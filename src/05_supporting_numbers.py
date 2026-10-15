"""
05_supporting_numbers.py — every number quoted in the text, recomputed from the stage outputs.

Reads data/{panel_manifest,validation,upgrade_dynamics,advisory_exposure}.json (stages 01–04) and the cutoff day of
the panel, and writes
  data/supporting_numbers.json   name → value
  paper/numbers.tex              one \\newcommand per number, used by the LaTeX sources

Usage:  python src/05_supporting_numbers.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_CUTOFF, DATA_DIR, PAPER_DIR  # noqa: E402
from lnmetrics import panel as pn  # noqa: E402
from lnmetrics.advisories import ADVISORIES  # noqa: E402

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def pct(x, nd: int = 1) -> str:
    return f"{100 * x:.{nd}f}"


def num(x) -> str:
    return f"{int(x):,}".replace(",", "{,}")


def long_date(d: str) -> str:
    """'2025-12-07' -> '7~December~2025'."""
    t = pd.Timestamp(d)
    return f"{t.day}~{t:%B}~{t.year}"


def main() -> int:
    man, val, up, adv = (load(f) for f in ("panel_manifest.json", "validation.json", "upgrade_dynamics.json",
                                           "advisory_exposure.json"))
    N = {}

    # --- data ---------------------------------------------------------------------------------------------------
    N["DataUsableDays"] = num(man["days"])
    N["DataFirstDay"] = man["first_day"]

    # --- liveness: LND nodes announcing a line older than 0.19 on the cutoff day (managed fleet excluded) --------
    p = pn.read_day(DATA_CUTOFF, ["client", "client_confidence", "likely_lo", "n_channels", "live_cap_14", "fleet"])
    lnd = p[(p["client"] == "LND") & p["client_confidence"].isin(["high", "operator"]) & (p["likely_lo"] >= 0)
            & (p["n_channels"] > 0) & ~p["fleet"]]
    old = lnd["likely_lo"] < next(ln.index for ln in pn.vf.lines("LND") if ln.label == "0.19")
    live = lnd["live_cap_14"] > 0
    N["NOldLndChan"] = num(old.sum())
    N["NOldLndLive"] = num((old & live).sum())
    N["PctOldLndNaive"] = pct(old.mean())
    N["PctOldLndLive"] = pct((old & live).sum() / live.sum())
    N["NLiveLndCutoff"] = num(live.sum())

    # --- validation ---------------------------------------------------------------------------------------------
    gc = {r["client"]: r for r in val["gt_client"]["by_client"]}
    N["NAnchorClient"] = num(val["gt_client"]["anchors"])
    for c in ("LND", "CLN"):
        N[f"Prec{c}"] = pct(gc[c]["precision"])
        N[f"Rec{c}"] = pct(gc[c]["recall"])
        N[f"NAnchor{c}"] = num(gc[c]["n"])
    v = val["gt_version"]["CLN"]
    N["NVerNodeDays"] = num(v["node_days"])
    N["NVerNodes"] = num(v["nodes"])
    N["NVerLines"] = num(v["lines"])
    N["PctVerStrict"] = pct(v["strict_contains"], 2)
    N["PctVerLikely"] = pct(v["likely_exact"])
    N["PctVerMaxOperator"] = pct(v["largest_operator_share"], 0)
    N["NVerNodeLines"] = num(v["node_lines"])
    N["NVerNodeLinesExact"] = num(v["node_lines_all_exact"])
    amb = {(r["client"], r["year"]): r for r in val["ambiguity_live"]}
    for c in ("LND", "CLN"):
        r = amb[(c, DATA_CUTOFF[:4])]
        N[f"PctStrictMulti{c}"] = pct(r["strict_multi"], 0)
        N[f"PctUnrec{c}"] = pct(r["unrecognised"])
        N[f"PctPre{c}"] = pct(r["prerelease"])

    # --- advisories ---------------------------------------------------------------------------------------------
    rows = {r["key"]: r for r in adv["advisories"]}
    for key, tag in [("lnd-2026-ll-batch", "LLBatch"), ("cln-2026-gossipd", "ClnGossipd"),
                     ("cln-2026-connectd", "ClnConnectd"), ("lnd-2025-sweeper", "LndSweeper")]:
        r = rows[key]
        N[f"FixToDisc{tag}"] = num(r["fix_to_disclosure_days"])
        for when, w in (("disclosure", "Disc"), ("+60d", "Sixty"), ("cutoff", "Cutoff")):
            x = r.get(when)
            if x:
                N[f"Exp{tag}{w}"] = pct(x["central"])
                N[f"ExpCap{tag}{w}"] = pct(x["central_cap"])
        case = adv["cases"].get(key) or {}
        if case:
            last = case["fate"][-1]
            N[f"Cohort{tag}"] = num(case["cohort_nodes"])
            N[f"CohortUp{tag}"] = num(last["upgraded"])
            N[f"CohortLeft{tag}"] = num(last["left"])
            N[f"CohortStill{tag}"] = num(last["exposed"])
            N[f"PctCohortStill{tag}"] = pct(last["exposed"] / case["cohort_nodes"], 0)
            N[f"CohortEnd{tag}"] = last["date"]
            for k in ("before", "after"):
                rr = case["upgrade_rate_30d"][k]
                if rr["rate"] is not None:
                    N[f"Rate{tag}{k.capitalize()}"] = pct(rr["rate"])
    lnd_rows = [r for r in adv["advisories"] if r["client"] in ("LND", "CLN")]
    N["NAdvRows"] = num(len(lnd_rows))
    N["NAdvTotal"] = num(sum(a.count for a in ADVISORIES if a.client in ("LND", "CLN")))
    gaps = sorted(r["fix_to_disclosure_days"] for r in lnd_rows)
    N["FixToDiscMedian"] = num(gaps[len(gaps) // 2])

    # --- upgrade dynamics ---------------------------------------------------------------------------------------
    ad = up["adoption"]
    for c, line, tag in [("LND", "0.19", "LndNineteen"), ("LND", "0.20", "LndTwenty"), ("LND", "0.21", "LndTwentyOne")]:
        a = ad[c][line]
        for k, t in (("t50_nodes", "TFifty"), ("t50_cap", "TFiftyCap"), ("first_seen_days", "FirstSeen")):
            if a[k] is not None:
                N[f"{t}{tag}"] = num(abs(a[k]))
    tt = up["time_to_upgrade"]
    for c in ("LND", "CLN"):
        for q, t in (("smallest 25%", "Small"), ("largest 25%", "Large"), ("all", "All")):
            r = tt[c][q]
            if r.get("median_days") is not None:
                N[f"Median{c}{t}"] = num(r["median_days"])
            N[f"ByNinety{c}{t}"] = pct(r["upgraded_by_90d"], 0)
            N[f"ByYear{c}{t}"] = pct(r["upgraded_by_365d"], 0)

    lnd_lines = ["0.18", "0.19", "0.20", "0.21"]
    t50 = [ad["LND"][x]["t50_nodes"] for x in lnd_lines]
    N["TFiftyLndMin"], N["TFiftyLndMax"] = num(min(t50)), num(max(t50))
    N["TFiftyCapLndEighteen"] = num(ad["LND"]["0.18"]["t50_cap"])
    N["TFiftyCapLndNineteen"] = num(ad["LND"]["0.19"]["t50_cap"])
    N["TFiftyCapLndTwenty"] = num(ad["LND"]["0.20"]["t50_cap"])
    N["TFiftyLndTwenty"] = num(ad["LND"]["0.20"]["t50_nodes"])
    N["TFiftyLndTwentyWithFleet"] = num(up["adoption_with_fleet_lnd"]["0.20"]["t50_nodes"])
    t50c = [a["t50_nodes"] for a in ad["CLN"].values() if a["t50_nodes"] is not None]
    N["TFiftyClnMin"], N["TFiftyClnMax"] = num(min(t50c)), num(max(t50c))
    fs = [-ad["LND"][x]["first_seen_days"] for x in lnd_lines]
    N["FirstSeenLndMin"], N["FirstSeenLndMax"] = num(min(fs)), num(max(fs))
    N["PctIntervalNarrow"] = pct(tt["LND"]["all"]["interval_width_le_2d_share"], 0)

    # --- the managed fleet --------------------------------------------------------------------------------------
    fl = up["fleet"]
    N["FleetFirstDay"] = long_date(fl["first_day"])
    N["FleetPeakDay"] = long_date(fl["peak_day"])
    N["FleetPeakNodes"] = num(fl["peak_nodes"])
    N["FleetPeakShare"] = pct(fl["peak_share_live_lnd"], 0)
    N["FleetPeakCap"] = f"{fl['peak_cap_btc']:.1f}"
    N["FleetPeakTotalCap"] = num(round(fl["peak_total_cap_btc"], -2))
    N["FleetCutoffNodes"] = num(fl["cutoff_nodes"])
    N["FleetCutoffShare"] = pct(fl["cutoff_share_live_lnd"], 0)
    fw = up["waves_fleet_lnd"][0]
    N["FleetWaveNodes"] = num(fw["nodes"])
    N["FleetWaveDay"] = long_date(fw["date"])

    # --- hazard model -------------------------------------------------------------------------------------------
    hz = {r["covariate"]: r for r in up["hazard_lnd"]}
    for cov, tag in [("log10_capacity", "ORCapacity"), ("log10_channels", "ORChannels"), ("tor_only", "ORTor"),
                     ("lines_behind_gt1", "ORBehind"), ("default_color", "ORDefaultColor"),
                     ("first_seen_before_2024", "OROld")]:
        N[tag] = f"{hz[cov]['odds_ratio']:.2f}"

    # --- waves (fleet excluded): days moving >= 100 LND nodes ----------------------------------------------------
    big = [w for w in up["waves"]["LND"]["waves"] if w["nodes"] >= 100]
    N["WaveMinNodes"], N["WaveMaxNodes"] = num(min(w["nodes"] for w in big)), num(max(w["nodes"] for w in big))
    N["WaveMinDays"] = num(min(w["days_after_release"] for w in big))
    N["WaveMaxDays"] = num(max(w["days_after_release"] for w in big))
    med = lambda xs: sorted(xs)[len(xs) // 2]
    N["WaveMedianCap"] = f"{med([w['median_cap_btc'] for w in big]):.3f}"
    N["WaveOtherCap"] = f"{med([w['median_cap_btc_other_upgraders'] for w in big]):.3f}"
    N["WaveMedianAge"] = num(med([w["median_age_days"] for w in big]))
    for w in big:     # Tor-only share of all live LND nodes (fleet excluded) on the wave day
        q = pn.read_day(w["date"].replace("-", ""), ["client", "live_cap_14", "fleet", "has_tor", "has_clearnet"])
        q = q[(q["client"] == "LND") & (q["live_cap_14"] > 0) & ~q["fleet"]]
        w["base_tor"] = float((q["has_tor"].fillna(False) & ~q["has_clearnet"].fillna(False)).mean())
    tor = [w for w in big if w["share_tor_only"] > w["base_tor"]]
    clear = [w for w in big if w["share_tor_only"] <= w["base_tor"]]
    N["NWaves"], N["NWavesTor"] = num(len(big)), num(len(tor))
    N["WaveTorMin"] = pct(min(w["share_tor_only"] for w in tor), 0)
    N["WaveTorMax"] = pct(max(w["share_tor_only"] for w in tor), 0)
    N["TorBaseMin"] = pct(min(w["base_tor"] for w in big), 0)
    N["TorBaseMax"] = pct(max(w["base_tor"] for w in big), 0)
    if len(clear) == 1:
        c = clear[0]
        N["ClearWaveDay"], N["ClearWaveNodes"] = long_date(c["date"]), num(c["nodes"])
        N["ClearWaveTor"], N["ClearWaveLine"] = pct(c["share_tor_only"], 0), c["line"]

    bad = [k for k in N if not k.isalpha()]
    if bad:
        raise ValueError(f"LaTeX macro names must be letters only: {bad}")
    lines = ["% Generated by src/05_supporting_numbers.py — do not edit by hand."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(N.items())]
    (PAPER_DIR / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (DATA_DIR / "supporting_numbers.json").write_text(json.dumps(N, indent=1), encoding="utf-8")
    print(f"{len(N)} numbers -> paper/numbers.tex, data/supporting_numbers.json")
    for k, v in sorted(N.items()):
        print(f"  {k} = {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
