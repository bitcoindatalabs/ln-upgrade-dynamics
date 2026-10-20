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
    lo, hi = v["node_lines_all_exact_ci95"]
    N["PctNodeLineExact"] = pct(v["node_lines_all_exact"] / v["node_lines"], 0)
    N["NodeLineCILo"], N["NodeLineCIHi"] = pct(lo, 0), pct(hi, 0)
    amb = {(r["client"], r["year"]): r for r in val["ambiguity_live"]}
    for c in ("LND", "CLN"):
        r = amb[(c, DATA_CUTOFF[:4])]
        N[f"PctStrictMulti{c}"] = pct(r["strict_multi"], 0)
        N[f"PctUnrec{c}"] = pct(r["unrecognised"])
        N[f"PctPre{c}"] = pct(r["prerelease"])
    cons = val["consistency"]
    for c in ("LND", "CLN"):
        N[f"PctDown{c}"] = pct(cons[c]["decrease_share"])
        N[f"NUp{c}"] = num(cons[c]["increases"])
    lnd_l = [cons["LND"]["lines"][x] for x in ("0.18", "0.19", "0.20", "0.21")]
    N["PreRelLndMax"] = num(max(x["nodes_before_release"] for x in lnd_l))
    N["PostRelLndMin"] = num(min(x["nodes_first_90d"] for x in lnd_l))
    N["PostRelLndMax"] = num(max(x["nodes_first_90d"] for x in lnd_l))

    # --- advisories ---------------------------------------------------------------------------------------------
    rows = {r["key"]: r for r in adv["advisories"]}
    for key, tag in [("lnd-2026-ll-batch", "LLBatch"), ("cln-2026-gossipd", "ClnGossipd"),
                     ("cln-2026-connectd", "ClnConnectd"), ("lnd-2025-sweeper", "LndSweeper"),
                     ("lnd-2026-closeconf", "LndCloseconf")]:
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
            N[f"PctCohortLeft{tag}"] = pct(last["left"] / case["cohort_nodes"], 0)
            N[f"PctCohortUp{tag}"] = pct(last["upgraded"] / case["cohort_nodes"], 0)
            N[f"CohortEnd{tag}"] = long_date(last["date"])
        rob = adv["robustness"].get(key) or {}
        for when, w in (("disclosure", "Disc"), ("cutoff", "Cutoff")):
            x = rob.get(when)
            if x:
                N[f"RobSeven{tag}{w}"] = pct(x["live7"]["nodes"])
                N[f"RobTwentyEight{tag}{w}"] = pct(x["live28"]["nodes"])
                N[f"RobSigned{tag}{w}"] = pct(x["exposed_signed_14d"], 0)
                N[f"RobSignedAll{tag}{w}"] = pct(x["all_live_signed_14d"], 0)
                N[f"RobFleet{tag}{w}"] = pct(x["with_fleet"])

    # --- response to disclosure: weekly rate of leaving affected lines, 8 weeks before vs 4 after ---------------
    resp = {r["key"]: r for r in adv["response"]}
    for key, tag in [("lnd-2026-ll-batch", "LLBatch"), ("cln-2026-gossipd", "ClnGossipd"),
                     ("cln-2026-connectd", "ClnConnectd"), ("lnd-2025-sweeper", "LndSweeper"),
                     ("cln-2026-pingflood", "ClnPing"), ("lnd-2026-zerots", "LndZerots")]:
        r = resp[key]
        for var, v in (("all", "All"), ("operator", "Op")):
            x = r[var]
            N[f"RR{v}{tag}"] = f"{x['rr']:.2f}"
            N[f"RRLo{v}{tag}"] = f"{x['rr_lo']:.2f}"
            N[f"RRHi{v}{tag}"] = f"{x['rr_hi']:.2f}"
            N[f"WkBefore{v}{tag}"] = pct(x["rate_before"])
            N[f"WkAfter{v}{tag}"] = pct(x["rate_after"])
            N[f"PPerm{v}{tag}"] = f"{x['p_perm']:.3f}"
        N[f"AtRisk{tag}"] = num(r["at_risk_at_disclosure"])
    r = adv["response_cln_one_line_behind"]          # CLN 2026-07-19, nodes on 25.09–25.12 only
    for var, v in (("all", "All"), ("operator", "Op")):
        x = r[var]
        N[f"RR{v}ClnRecent"] = f"{x['rr']:.2f}"
        N[f"RRLo{v}ClnRecent"] = f"{x['rr_lo']:.2f}"
        N[f"RRHi{v}ClnRecent"] = f"{x['rr_hi']:.2f}"
        N[f"WkBefore{v}ClnRecent"] = pct(x["rate_before"])
        N[f"WkAfter{v}ClnRecent"] = pct(x["rate_after"])
        N[f"PPerm{v}ClnRecent"] = f"{x['p_perm']:.3f}"
    N["AtRiskClnRecent"] = num(r["at_risk_at_disclosure"])
    lnd_resp = [r for r in adv["response"] if r["client"] == "LND"]
    cln_resp = [r for r in adv["response"] if r["client"] == "CLN"]
    N["NResp"], N["NRespLND"], N["NRespCLN"] = num(len(adv["response"])), num(len(lnd_resp)), num(len(cln_resp))
    N["RespLndMaxRR"] = f"{max(max(r['all']['rr'], r['operator']['rr']) for r in lnd_resp):.2f}"
    N["RespLndMinP"] = f"{min(min(r['all']['p_perm'], r['operator']['p_perm']) for r in lnd_resp):.2f}"
    N["RespMaxDisp"] = num(round(max(max(r["all"]["dispersion"], r["operator"]["dispersion"]) for r in adv["response"])))
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
    N["FleetWaveDay"] = long_date(fw["first_day"])
    N["FleetWaveHours"] = num(round(fw["platform"]["median_hours_after"]))
    N["FleetWaveSigned"] = pct(fw["platform"]["share_signed_after"], 0)

    # --- hazard model -------------------------------------------------------------------------------------------
    hz = {r["covariate"]: r for r in up["hazard_lnd"]}
    for cov, tag in [("log10_capacity", "ORCapacity"), ("log10_channels", "ORChannels"), ("tor_only", "ORTor"),
                     ("lines_behind_gt1", "ORBehind"), ("default_color", "ORDefaultColor"),
                     ("first_seen_before_2024", "OROld")]:
        N[tag] = f"{hz[cov]['odds_ratio']:.2f}"

    # --- waves (fleet excluded): events of consecutive wave days ----------------------------------------------
    wv = up["waves"]["LND"]["waves"]
    med = lambda xs: sorted(xs)[len(xs) // 2]
    N["NWaveEvents"] = num(len(wv))
    N["WaveMinNodes"], N["WaveMaxNodes"] = num(min(w["nodes"] for w in wv)), num(max(w["nodes"] for w in wv))
    N["WaveMinDays"] = num(min(w["days_after_release"] for w in wv))
    N["WaveMaxDays"] = num(max(w["days_after_release"] for w in wv))
    N["WaveMedianCap"] = f"{med([w['median_cap_btc'] for w in wv]):.3f}"
    N["WaveOtherCap"] = f"{med([w['median_cap_btc_other_upgraders'] for w in wv]):.3f}"
    N["WaveMedianAge"] = num(med([w["median_age_days"] for w in wv]))
    N["WaveMinSignedTwo"] = pct(min(w["share_signed_within_2d"] for w in wv), 0)
    umb = [w for w in wv if w["platform"]["attributed"] and w["platform"]["platform"] == "Umbrel"]
    btc = [w for w in wv if w["platform"]["attributed"] and w["platform"]["platform"] == "BTCPay"]
    una = [w for w in wv if not w["platform"]["attributed"]]
    N["NWaveUmbrel"], N["NWaveUnattributed"] = num(len(umb)), num(len(una))
    N["WaveUmbrelMinNodes"] = num(min(w["nodes"] for w in umb))
    N["WaveUmbrelMaxNodes"] = num(max(w["nodes"] for w in umb))
    N["WaveUmbrelSignedMin"] = pct(min(w["platform"]["share_signed_after"] for w in umb), 0)
    N["WaveUmbrelHoursMin"] = num(round(min(w["platform"]["median_hours_after"] for w in umb)))
    N["WaveUmbrelHoursMax"] = num(round(max(w["platform"]["median_hours_after"] for w in umb)))
    N["WaveUmbrelBeforeMax"] = pct(max(w["platform"]["share_signed_24h_before"] for w in umb), 0)
    N["WaveUmbrelTorMin"] = pct(min(w["share_tor_only"] for w in umb), 0)
    N["WaveUmbrelTorMax"] = pct(max(w["share_tor_only"] for w in umb), 0)
    N["WaveUmbrelBaseMin"] = pct(min(w["share_tor_only_all_live"] for w in umb), 0)
    N["WaveUmbrelBaseMax"] = pct(max(w["share_tor_only_all_live"] for w in umb), 0)
    N["WaveUmbrelCapMin"] = f"{min(w['median_cap_btc'] for w in umb):.3f}"
    N["WaveUmbrelCapMax"] = f"{max(w['median_cap_btc'] for w in umb):.3f}"
    N["WaveUmbrelOtherCapMin"] = f"{min(w['median_cap_btc_other_upgraders'] for w in umb):.3f}"
    N["WaveUmbrelOtherCapMax"] = f"{max(w['median_cap_btc_other_upgraders'] for w in umb):.3f}"
    N["WaveUmbrelAgeMin"] = num(min(w["median_age_days"] for w in umb))
    N["WaveUmbrelAgeMax"] = num(max(w["median_age_days"] for w in umb))
    N["WaveUmbrelDaysMin"] = num(min(w["days_after_release"] for w in umb))
    N["WaveUmbrelDaysMax"] = num(max(w["days_after_release"] for w in umb))
    if len(btc) == 1:
        b = btc[0]
        N["WaveBTCPayNodes"], N["WaveBTCPayDay"] = num(b["nodes"]), long_date(b["first_day"])
        N["WaveBTCPayTor"], N["WaveBTCPayBase"] = pct(b["share_tor_only"], 0), pct(b["share_tor_only_all_live"], 0)
        N["WaveBTCPaySigned"] = pct(b["platform"]["share_signed_after"], 0)
        N["WaveBTCPayHours"] = num(round(b["platform"]["median_hours_after"]))
        N["WaveBTCPayOlder"] = num(sum(v for k, v in b["from_lines"].items() if k != "0.20"))
    for w in una:
        if w["platform"].get("platform"):     # a platform release that came after the wave's signatures
            N["WaveEarlyNodes"], N["WaveEarlyDay"] = num(w["nodes"]), long_date(w["first_day"])
            N["WaveEarlyVersion"] = w["platform"]["version"]
            N["WaveEarlyBefore"] = pct(w["platform"]["share_signed_24h_before"], 0)
        else:
            N["WaveNoneNodes"], N["WaveNoneDay"] = num(w["nodes"]), long_date(w["first_day"])
    cw = [w for w in up["waves"]["CLN"]["waves"] if w["platform"]["attributed"]]
    if len(cw) == 1:
        N["ClnWaveNodes"], N["ClnWaveDay"] = num(cw[0]["nodes"]), long_date(cw[0]["first_day"])
        N["ClnWaveSigned"] = pct(cw[0]["platform"]["share_signed_after"], 0)
        N["ClnWaveHours"] = num(round(cw[0]["platform"]["median_hours_after"]))
    pl = up["platform_lines"]["LND"]
    N["NPlatLineReleases"] = num(len(pl))
    N["NPlatLineChanges"] = num(sum(x["changes"] for x in pl))
    N["PlatLineMin"] = pct(min(x["share_on_shipped_line"] for x in pl), 0)
    N["PlatLineMax"] = pct(max(x["share_on_shipped_line"] for x in pl), 1)
    for c in ("LND", "CLN"):
        s = up["platform_share"][c]
        N[f"PlatShare{c}"] = pct(s["share"], 0)
        N[f"PlatTime{c}"] = pct(s["time_share"])
        N[f"PlatReleases{c}"] = num(s["releases"])

    # --- who followed CLN's call of 26 August to restart offline, by release line --------------------------------
    c = adv["cln_offline_call"]
    e, o = c["event"], c["ordinary"]
    N["OffCallNewestLine"] = c["newest_line"].replace("–", "--")
    for g, k in (("newest", "Newest"), ("behind", "Behind")):
        N[f"OffCall{k}Nodes"] = num(e[g]["nodes"])
        N[f"OffCall{k}Left"] = pct(e[g]["left"])
        N[f"OffCall{k}Tor"] = pct(e[g]["left_tor_only"], 0)
        N[f"OffCall{k}Other"] = pct(e[g]["left_other"], 0)
        N[f"OffCallOrd{k}Median"] = pct(float(pd.Series([w[g] for w in o]).median()))
        N[f"OffCallOrd{k}Max"] = pct(max(w[g] for w in o))
    N["OffCallOrdWindows"] = num(len(o))
    N["OffCallNewestLeftN"] = num(e["newest"]["left_n"])
    N["OffCallNewestDarkN"] = num(e["newest"]["left_dark_n"])
    N["OffCallOrdDarkShare"] = pct(sum(w["left_dark_n"] for w in o) / sum(w["left_n"] for w in o), 0)
    top = max(o, key=lambda w: w["newest"])                       # the window with the most newest-line leavers
    N["OffCallOrdMaxDarkShare"] = pct(top["left_dark_n"] / top["left_n"], 0)
    N["OffCallOrdMaxDay"] = long_date(top["from"])
    N["OffCallMovedMax"] = pct(max(e[g]["moved"] for g in e), 0)
    N["OffCallOddsRatio"] = f"{c['fisher']['odds_ratio']:.1f}"
    m, x = f"{c['fisher']['p']:.0e}".split("e")
    N["OffCallP"] = rf"{int(m)}\times10^{{{int(x)}}}"

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
