"""
04_advisory_exposure.py — RQ3/RQ4: after each advisory, how many live nodes and how much capacity stayed on an
affected release line, and did exposure fall through upgrades or through nodes leaving?

Population per day: live nodes (src/lnmetrics/panel.py) of the advisory's client whose release line is inferred
(operator/high client label, a matching line), without the managed fleet (panel column `fleet`; one operator's
decision repeated over hundreds of nodes — reported with it as a sensitivity). Weight: capacity of the node's live
channels (live_cap_14).

Exposure of a node to an advisory (src/lnmetrics/advisories.py; W = wholly affected lines, M = mixed lines):
  definitely  every line its bits allow is in W                (lower bound)
  central     its likely line is in W                          (reported value)
  possibly    some line its bits allow is in W or M            (upper bound)

Per advisory: exposure at the fix release, at disclosure, +30 and +60 days, and at the cutoff (nearest panel day
on or after each date, within 7 days).

Case studies (dense daily data around disclosure): the cohort of live nodes centrally exposed on the last panel
day before disclosure, followed day by day: upgraded (seen on a fixed line), left (not live that day, not upgraded),
still exposed. Upgrade rate out of affected lines in the 30 days before vs after disclosure.

Outputs
  data/advisory_exposure.json
  paper/tables/table_advisories.tex
  paper/figures/fig6_exposure_cases.pdf

Usage:  python src/04_advisory_exposure.py
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CLIENT_PALETTE, DATA_CUTOFF, DATA_DIR, FIGURES_DIR, TABLES_DIR  # noqa: E402
from lnmetrics import panel as pn  # noqa: E402
from lnmetrics.advisories import ADVISORIES  # noqa: E402

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CASES = ["lnd-2025-sweeper", "lnd-2026-ll-batch", "cln-2026-connectd", "cln-2026-gossipd"]
CASE_TITLES = {"lnd-2025-sweeper": "LND < 0.19\nMorehouse, 4 Dec 2025",
               "lnd-2026-ll-batch": "LND < 0.19\nLightning Labs, 11 Aug 2026",
               "cln-2026-connectd": "CLN < 25.09\nconnectd DoS, 19 Jul 2026",
               "cln-2026-gossipd": "CLN < 26.04\ngossipd DoS, 19 Jul 2026"}
CLN_OFFLINE_CALL = pd.Timestamp("2026-08-26")   # CLN maintainers: upgrade, or restart with --offline
OFFSETS = {"fix": None, "disclosure": 0, "+30d": 30, "+60d": 60}
COLS = ["date", "pub_key", "client", "client_confidence", "line_lo", "line_hi", "likely_lo", "likely_hi",
        "live_cap_14", "fleet"]

plt.rcParams.update({"font.family": "serif", "font.size": 8.5, "axes.titlesize": 9, "xtick.labelsize": 7.5,
                     "ytick.labelsize": 7.5, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})


def load_live() -> pd.DataFrame:
    clients = sorted({a.client for a in ADVISORIES})
    p = pn.load(COLS, where=lambda p: pn.live(p) & p["client"].isin(clients)
                & p["client_confidence"].isin(["high", "operator"]) & (p["likely_lo"] >= 0))
    p["date"] = pd.to_datetime(p["date"])
    return p


def _in(lo: pd.Series, hi: pd.Series, s: set, every: bool) -> pd.Series:
    """Whether every (every=True) or some line index in [lo, hi] belongs to s."""
    out = pd.Series(every, index=lo.index)
    for k in range(int(lo.min()), int(hi.max()) + 1):
        within = (lo <= k) & (k <= hi)
        out = (out & (~within | (k in s))) if every else (out | (within & (k in s)))
    return out


def exposure_flags(p: pd.DataFrame, a) -> pd.DataFrame:
    w, m = a.indices()
    return pd.DataFrame({"definitely": _in(p["line_lo"], p["line_hi"], w, every=True),
                         "central": p["likely_lo"].isin(w),
                         "possibly": _in(p["line_lo"], p["line_hi"], w | m, every=False)}, index=p.index)


def daily_series(p: pd.DataFrame, a) -> pd.DataFrame:
    q = p[p["client"] == a.client]
    f = exposure_flags(q, a)
    cap = q["live_cap_14"]
    g = pd.DataFrame({"date": q["date"], "n": 1, "cap": cap})
    for c in f:
        g[c] = f[c].astype(int)
        g[c + "_cap"] = cap.where(f[c], 0)
    d = g.groupby("date").sum()
    out = pd.DataFrame({"live_nodes": d["n"], "live_cap_btc": d["cap"] / 1e8}, index=d.index)
    for c in f:
        out[c] = d[c] / d["n"]
        out[c + "_cap"] = d[c + "_cap"] / d["cap"]
        out[c + "_nodes"] = d[c]
    return out


def at(series: pd.DataFrame, when: pd.Timestamp, tol_days: int = 7):
    later = series.index[(series.index >= when) & (series.index <= when + pd.Timedelta(days=tol_days))]
    return series.loc[later[0]] if len(later) else None


def summary_row(series: pd.DataFrame, a) -> dict:
    row = {"key": a.key, "client": a.client, "title": a.title, "kind": a.kind, "count": a.count,
           "disclosed": a.disclosed, "fixed": a.fixed, "fixed_in": a.fixed_in, "severity": a.severity,
           "fix_to_disclosure_days": (pd.Timestamp(a.disclosed) - pd.Timestamp(a.fixed)).days}
    disc = pd.Timestamp(a.disclosed)
    whens = {"fix": pd.Timestamp(a.fixed), **{k: disc + pd.Timedelta(days=v) for k, v in OFFSETS.items() if v is not None},
             "cutoff": pd.Timestamp(DATA_CUTOFF)}
    for k, when in whens.items():
        r = at(series, when) if when <= pd.Timestamp(DATA_CUTOFF) else None
        row[k] = None if r is None else {
            "date": r.name.strftime("%Y-%m-%d"), "live_nodes": int(r["live_nodes"]),
            "central": float(r["central"]), "definitely": float(r["definitely"]), "possibly": float(r["possibly"]),
            "central_cap": float(r["central_cap"]), "definitely_cap": float(r["definitely_cap"]),
            "possibly_cap": float(r["possibly_cap"]), "central_nodes": int(r["central_nodes"])}
    return row


def cohort_fate(p: pd.DataFrame, a, horizon_days: int = 120) -> dict:
    """Live nodes centrally exposed on the last panel day before disclosure, followed day by day."""
    q = p[p["client"] == a.client]
    w, m = a.indices()
    disc = pd.Timestamp(a.disclosed)
    before = q.loc[q["date"] < disc, "date"]
    if before.empty:
        return {}
    d0 = before.max()
    if (disc - d0).days > 7:
        return {}
    c0 = q[(q["date"] == d0) & q["likely_lo"].isin(w)]
    cohort = set(c0["pub_key"])
    cap0 = c0.set_index("pub_key")["live_cap_14"]
    qc = q[q["pub_key"].isin(cohort) & (q["date"] >= d0) & (q["date"] <= disc + pd.Timedelta(days=horizon_days))]
    fixed = ~qc["likely_lo"].isin(w | m) & (qc["likely_lo"] > max(w | m))
    first_fixed = qc[fixed].groupby("pub_key")["date"].min()
    days = sorted(qc["date"].unique())
    rows = []
    for d in days:
        live_today = set(qc.loc[qc["date"] == d, "pub_key"])
        up = set(first_fixed[first_fixed <= d].index)
        exposed = live_today - up
        left = cohort - up - live_today
        rows.append({"date": pd.Timestamp(d).strftime("%Y-%m-%d"), "upgraded": len(up), "left": len(left),
                     "exposed": len(exposed), "upgraded_cap": float(cap0[list(up)].sum() / cap0.sum()),
                     "left_cap": float(cap0[list(left)].sum() / cap0.sum()),
                     "exposed_cap": float(cap0[list(exposed)].sum() / cap0.sum())})
    # upgrade rate out of affected lines: per 30 days, among live exposed nodes, before vs after disclosure
    rates = {}
    for name, lo, hi in [("before", disc - pd.Timedelta(days=30), disc), ("after", disc, disc + pd.Timedelta(days=30))]:
        exp_lo = q[(q["date"] >= lo - pd.Timedelta(days=7)) & (q["date"] < lo) & q["likely_lo"].isin(w)]
        start = set(exp_lo.loc[exp_lo["date"] == exp_lo["date"].max(), "pub_key"]) if len(exp_lo) else set()
        win = q[(q["date"] >= lo) & (q["date"] < hi) & q["pub_key"].isin(start)]
        moved = win[~win["likely_lo"].isin(w | m) & (win["likely_lo"] > max(w | m))]["pub_key"].nunique()
        rates[name] = {"start_nodes": len(start), "upgraded": int(moved),
                       "rate": moved / len(start) if start else None,
                       "complete": bool(hi <= pd.Timestamp(DATA_CUTOFF))}
    return {"cohort_date": d0.strftime("%Y-%m-%d"), "cohort_nodes": len(cohort),
            "cohort_cap_btc": float(cap0.sum() / 1e8), "fate": rows, "upgrade_rate_30d": rates}


def fig_cases(series: dict, fates: dict):
    import matplotlib.dates as mdates
    keys = [k for k in CASES if k in fates and fates[k]]
    fig, axes = plt.subplots(2, len(keys), figsize=(7.0, 4.4), sharey="row", squeeze=False)
    for j, k in enumerate(keys):
        a = next(x for x in ADVISORIES if x.key == k)
        s = series[k]
        disc = pd.Timestamp(a.disclosed)
        f = pd.DataFrame(fates[k]["fate"])
        f["date"] = pd.to_datetime(f["date"])
        lo, hi = disc - pd.Timedelta(days=45), f["date"].max()
        win = s[(s.index >= lo) & (s.index <= hi)]
        col = CLIENT_PALETTE[a.client]
        ax = axes[0, j]
        ax.plot(win.index, 100 * win["central"], color=col, lw=1.4, label="nodes")
        ax.plot(win.index, 100 * win["central_cap"], color=col, lw=1.0, ls="--", label="capacity")
        ax.axvline(disc, color="0.3", lw=0.7)
        if a.client == "CLN":
            for axx in axes[:, j]:
                axx.axvline(CLN_OFFLINE_CALL, color="0.3", lw=0.7, ls=":")
            ax.text(CLN_OFFLINE_CALL, 97, " offline\n call", fontsize=5.5, va="top", color="0.3")
        ax.set_title(CASE_TITLES[k], fontsize=7)
        if j == 0:
            ax.set_ylabel("live nodes on an\naffected line (%)")
            ax.legend(frameon=False, fontsize=6.5)
        n0 = fates[k]["cohort_nodes"]
        ax = axes[1, j]
        ax.stackplot(f["date"], 100 * f["upgraded"] / n0, 100 * f["left"] / n0, 100 * f["exposed"] / n0,
                     colors=["#4a9a6e", "#c4c4c4", col], alpha=0.9, labels=["upgraded", "not live", "still exposed"])
        ax.text(0.97, 0.95, f"n = {n0:,}", transform=ax.transAxes, ha="right", va="top", fontsize=6.5, color="white")
        if j == 0:
            ax.set_ylabel("nodes exposed at\ndisclosure (%)")
            ax.legend(frameon=False, fontsize=6.5, loc="lower left", bbox_to_anchor=(0.0, 0.08))
        for ax in axes[:, j]:
            ax.set_xlim(lo, hi)
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1 if (hi - lo).days < 150 else 2))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%y"))
            ax.tick_params(axis="x", labelsize=6.5)
    axes[0, 0].set_ylim(0, 100)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig6_exposure_cases.pdf")
    plt.close(fig)


def table_advisories(rows: list):
    def cell(r, k, bounds=False):
        x = r.get(k)
        if not x:
            return "--"
        s = f"{100 * x['central']:.0f}"
        if bounds and r["kind"] == "PARTIAL":
            s += f" [{100 * x['definitely']:.0f}--{100 * x['possibly']:.0f}]"
        return s + f" ({100 * x['central_cap']:.0f})"
    lines = [r"\begin{table*}[t]", r"\centering\footnotesize",
             r"\caption{Advisories whose fix boundary is visible in gossip (LND and CLN). Exposure = share of live "
             r"nodes of that implementation whose inferred release line is affected, in \%; share of their live "
             r"capacity in parentheses; for PARTIAL rows (the fix lands inside a line) the bounds are given in "
             r"brackets at disclosure. Fix$\to$disc.\ = days from the first fixed release to public disclosure. "
             r"\# = advisories grouped in the row.}",
             r"\label{tab:advisories}", r"\resizebox{\textwidth}{!}{%", r"\begin{tabular}{lllrlrrrrr}", r"\toprule",
             r"Impl. & Advisory & Class & \# & Fixed in & Fix$\to$disc. & At fix & At disclosure & +60\,d & Cutoff \\",
             r"\midrule"]
    for r in sorted((r for r in rows if r["client"] in ("LND", "CLN")), key=lambda r: (r["client"], r["disclosed"])):
        t = r["title"].replace("_", r"\_").replace("&", r"\&").replace("#", r"\#")
        lines.append(f"{r['client']} & {t} ({r['disclosed']}) & {r['kind']} & {r['count']} & {r['fixed_in']} & "
                     f"{r['fix_to_disclosure_days']} & {cell(r, 'fix')} & {cell(r, 'disclosure', True)} & "
                     f"{cell(r, '+60d')} & {cell(r, 'cutoff')} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}}",
              r"\par\vspace{2pt}\parbox{\textwidth}{\footnotesize Before July 2024 our view did not include the few live "
              r"nodes on LND releases older than 0.14 (\S\ref{sec:data}); exposures to the 2023 LND advisories at "
              r"disclosure are lower bounds. --: no usable snapshot within 7 days.}",
              r"\end{table*}"]
    (TABLES_DIR / "table_advisories.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p_all = load_live()
    p = p_all[~p_all["fleet"]]
    print(f"live versioned node-days: {len(p_all):,}; without the managed fleet: {len(p):,}")
    series, rows, fates = {}, [], {}
    for a in ADVISORIES:
        s = daily_series(p, a)
        series[a.key] = s
        r = summary_row(s, a)
        w = summary_row(daily_series(p_all, a), a)          # sensitivity: fleet nodes counted as nodes
        r["with_fleet"] = {k: w[k] for k in ("disclosure", "+60d", "cutoff")}
        rows.append(r)
        d, c = r.get("disclosure"), r.get("cutoff")
        ds = "--" if not d else "{:.1f}% [{:.1f}, {:.1f}] cap {:.1f}%".format(
            100 * d["central"], 100 * d["definitely"], 100 * d["possibly"], 100 * d["central_cap"])
        cs = "--" if not c else "{:.1f}% cap {:.1f}%".format(100 * c["central"], 100 * c["central_cap"])
        print(f"{a.key:26s} {a.kind:7s} fix→disc {r['fix_to_disclosure_days']:4d}d  disc: {ds}  cutoff: {cs}")
    for k in CASES:
        a = next(x for x in ADVISORIES if x.key == k)
        fates[k] = cohort_fate(p, a)
        if fates[k]:
            last = fates[k]["fate"][-1]
            print(f"case {k}: cohort {fates[k]['cohort_nodes']} on {fates[k]['cohort_date']}; at {last['date']}: "
                  f"upgraded {last['upgraded']}, not live {last['left']}, still exposed {last['exposed']}; "
                  f"30d upgrade rate {fates[k]['upgrade_rate_30d']}")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    fig_cases(series, fates)
    table_advisories(rows)
    out = {"advisories": rows, "cases": fates,
           "series": {k: s.reset_index().assign(date=lambda x: x["date"].dt.strftime("%Y-%m-%d"))
                         .round(5).to_dict(orient="list") for k, s in series.items() if k in CASES}}
    (DATA_DIR / "advisory_exposure.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("-> data/advisory_exposure.json, tables/table_advisories.tex, figures/fig6_exposure_cases.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
