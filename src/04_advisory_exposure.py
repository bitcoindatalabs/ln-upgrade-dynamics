"""
04_advisory_exposure.py — RQ3/RQ4: after each advisory, how many live nodes and how much capacity stayed on an
affected release line, and did exposure fall through upgrades or through nodes leaving?

Population per day: live nodes (src/lnmetrics/panel.py) of the advisory's client whose release line is inferred
(operator/high client label, a matching line), without the managed fleet (panel column `fleet`; one schedule
repeated over hundreds of nodes — reported with it as a sensitivity). Weight: capacity of the node's live
channels (live_cap_14).

Exposure of a node to an advisory (src/lnmetrics/advisories.py; W = wholly affected lines, M = mixed lines):
  definitely  every line its bits allow is in W                (lower bound)
  central     its likely line is in W                          (reported value)
  possibly    some line its bits allow is in W or M            (upper bound)

Per advisory: exposure at the fix release, at disclosure, +30 and +60 days, and at the cutoff (nearest panel day
on or after each date, within 7 days).

Case studies (dense daily data around disclosure): the cohort of live nodes centrally exposed on the last panel
day before disclosure, followed day by day: upgraded (seen on a fixed line), left (not live that day, not upgraded),
still exposed.

Response to disclosure, for every advisory with dense data around its disclosure: each week from 8 weeks before
to 4 weeks after, the share of live nodes on a wholly affected line at the start of the week that moved to a later
line during it. Rate ratio after / before (node-weeks as exposure; quasi-Poisson 95% CI, since moves cluster; exact
permutation test of the weekly rates), for all such moves and for moves not explained by a platform release: a move whose new announcement was signed within 48 h after a dated platform
release shipping that line (src/lnmetrics/platforms.py) is the platform's schedule, not the operator's response.
CLN's disclosure of 2026-07-19 is also split by how far behind a node was: nodes one line behind (25.09–25.12)
alone; the older lines (< 25.09) are the connectd row, disclosed the same day.

Robustness (case studies): exposure at disclosure and at the cutoff with 7- and 28-day liveness, the strict-range
bounds, the managed fleet counted as nodes, and how many exposed nodes signed their announcement in the last 14 days.

Who followed CLN's call of 2026-08-26 to restart offline: the live CLN nodes of 2026-08-25, split into the newest line
(26.04 on, fixed for both July disclosures) and older lines, and the share of each no longer live on 2026-08-27,
against every two-day window of August before the call; by transport (Tor-only or not), with a Fisher exact test.

Outputs
  data/advisory_exposure.json
  paper/tables/table_advisories.tex, table_response.tex, table_robustness.tex
  paper/figures/fig6_exposure_cases.pdf, fig7_response.pdf

Usage:  python src/04_advisory_exposure.py
"""

import itertools
import json
import sys
from dataclasses import replace
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402
from scipy.stats import fisher_exact  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CLIENT_PALETTE, DATA_CUTOFF, DATA_DIR, FIGURES_DIR, TABLES_DIR  # noqa: E402
from lnmetrics import panel as pn  # noqa: E402
from lnmetrics import platforms as pf  # noqa: E402
from lnmetrics.advisories import ADVISORIES  # noqa: E402

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CASES = ["lnd-2025-sweeper", "lnd-2026-ll-batch", "cln-2026-connectd", "cln-2026-gossipd"]
RESP_WEEKS = (8, 4)          # weeks before / after disclosure
RESP_MIN_WEEKS = (6, 3)      # weeks with data required before / after
PLATFORM_HOURS = 48
RESP_SERIES = ["lnd-2026-ll-batch", "cln-2026-gossipd"]
CASE_TITLES = {"lnd-2025-sweeper": "LND < 0.19\nMorehouse, 4 Dec 2025",
               "lnd-2026-ll-batch": "LND < 0.19\nLightning Labs, 11 Aug 2026",
               "cln-2026-connectd": "CLN < 25.09\nconnectd DoS, 19 Jul 2026",
               "cln-2026-gossipd": "CLN < 26.04\ngossipd DoS, 19 Jul 2026"}
CLN_OFFLINE_CALL = pd.Timestamp("2026-08-26")   # CLN maintainers: upgrade, or restart with --offline
OFFSETS = {"fix": None, "disclosure": 0, "+30d": 30, "+60d": 60}
COLS = ["date", "pub_key", "client", "client_confidence", "line_lo", "line_hi", "likely_lo", "likely_hi",
        "live_cap_14", "fleet", "ann_age_days"]

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
    row = {"key": a.key, "client": a.client, "title": a.title, "kind": a.kind, "count": a.count, "cite": a.cite,
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
    return {"cohort_date": d0.strftime("%Y-%m-%d"), "cohort_nodes": len(cohort),
            "cohort_cap_btc": float(cap0.sum() / 1e8), "fate": rows}


# ---------------------------------------------------------------------------------------
# Response to disclosure: weekly rate of leaving the wholly affected lines
# ---------------------------------------------------------------------------------------
def moves_out(q: pd.DataFrame, w: set, client: str) -> pd.DataFrame:
    """First observation of a node on a line above every wholly affected line, right after an observation on a
    wholly affected line at most 7 days earlier; flagged when a platform release explains it."""
    q = q.sort_values(["pub_key", "date"])
    g = q.groupby("pub_key")
    prev_lo, prev_d = g["likely_lo"].shift(), g["date"].shift()
    ev = q[(q["likely_lo"] > max(w)) & prev_lo.isin(w) & ((q["date"] - prev_d).dt.days <= 7)].copy()
    ev["platform"] = pf.after_release(client, pn.signed_at(ev), ev["likely_lo"], PLATFORM_HOURS)
    return ev


def _rate_ratio(wk: pd.DataFrame, moved: pd.Series) -> dict:
    """Rate ratio after / before disclosure from weekly counts, node-weeks as exposure. Moves cluster (a platform
    push or a group of operators moves many nodes at once), so the counts are overdispersed: the 95% CI is
    quasi-Poisson (Poisson GLM with the Pearson dispersion of the weekly counts). `p_perm` is the exact one-sided
    permutation p-value of the after-weeks' mean weekly rate exceeding the before-weeks'."""
    after = (wk["week"] >= 0).to_numpy()
    y, n = moved.to_numpy(float), wk["nodes"].to_numpy(float)
    if not y[after].sum() or not y[~after].sum():
        raise ValueError("no moves on one side of the disclosure; the rate ratio is undefined")
    m = sm.GLM(y, sm.add_constant(after.astype(float)), family=sm.families.Poisson(), offset=np.log(n)).fit(scale="X2")
    lo, hi = np.exp(m.conf_int()[1])
    rate = y / n
    obs = rate[after].mean() - rate[~after].mean()
    diffs = np.array([rate[list(c)].mean() - np.delete(rate, list(c)).mean()
                      for c in itertools.combinations(range(len(rate)), int(after.sum()))])
    return {"events_before": int(y[~after].sum()), "node_weeks_before": int(n[~after].sum()),
            "events_after": int(y[after].sum()), "node_weeks_after": int(n[after].sum()),
            "rate_before": float(y[~after].sum() / n[~after].sum()), "rate_after": float(y[after].sum() / n[after].sum()),
            "rr": float(np.exp(m.params[1])), "rr_lo": float(lo), "rr_hi": float(hi), "dispersion": float(m.scale),
            "p_perm": float(np.mean(diffs >= obs - 1e-12))}


def response(p: pd.DataFrame, a) -> dict:
    q = p[p["client"] == a.client]
    w, _ = a.indices()
    disc = pd.Timestamp(a.disclosed)
    days = pd.DatetimeIndex(sorted(q["date"].unique()))
    ev = moves_out(q, w, a.client)
    end_of_data = pd.Timestamp(DATA_CUTOFF) + pd.Timedelta(days=1)
    weeks = []
    for k in range(-RESP_WEEKS[0], RESP_WEEKS[1]):
        s, e = disc + pd.Timedelta(days=7 * k), disc + pd.Timedelta(days=7 * (k + 1))
        d0 = days[(days >= s - pd.Timedelta(days=3)) & (days <= s)]
        inside = days[(days > s) & (days <= e)]
        if e > end_of_data or len(d0) == 0 or len(inside) < 4:
            weeks.append({"week": k, "start": s.strftime("%Y-%m-%d"), "nodes": None})
            continue
        d0 = d0.max()
        cohort = set(q.loc[(q["date"] == d0) & q["likely_lo"].isin(w), "pub_key"])
        x = ev[(ev["date"] > d0) & (ev["date"] <= e) & ev["pub_key"].isin(cohort)].drop_duplicates("pub_key")
        weeks.append({"week": k, "start": s.strftime("%Y-%m-%d"), "nodes": len(cohort), "moved": len(x),
                      "moved_platform": int(x["platform"].sum())})
    wk = pd.DataFrame(weeks)
    have = wk[wk["nodes"].notna()]
    b, af = have[have["week"] < 0], have[have["week"] >= 0]
    above = pn.line_label(a.client, max(w) + 1).split("–")[0]
    span = pn.line_label(a.client, min(w)) if len(w) == 1 else f"<{above}"
    out = {"key": a.key, "client": a.client, "title": a.title, "disclosed": a.disclosed, "kind": a.kind,
           "count": a.count, "fixed_in": a.fixed_in, "affected": sorted(pn.line_label(a.client, i) for i in w),
           "affected_span": span,
           "fix_to_disclosure_days": (disc - pd.Timestamp(a.fixed)).days,
           "weeks_before": len(b), "weeks_after": len(af), "weekly": weeks,
           "ok": len(b) >= RESP_MIN_WEEKS[0] and len(af) >= RESP_MIN_WEEKS[1]}
    if out["ok"] and b["nodes"].sum() and af["nodes"].sum():
        out["at_risk_at_disclosure"] = int(af["nodes"].iloc[0])
        h = have.astype({"nodes": float, "moved": float, "moved_platform": float})
        out["all"] = _rate_ratio(h, h["moved"])
        out["operator"] = _rate_ratio(h, h["moved"] - h["moved_platform"])
    return out


# ---------------------------------------------------------------------------------------
# Robustness of the case-study exposures
# ---------------------------------------------------------------------------------------
def robustness(a) -> dict:
    cols = ["pub_key", "client", "client_confidence", "line_lo", "line_hi", "likely_lo", "likely_hi", "fleet",
            "live_cap_7", "live_cap_14", "live_cap_28", "ann_age_days"]
    dates = pd.to_datetime(pd.Series(pn.panel_dates()))
    out = {}
    for name, when in (("disclosure", pd.Timestamp(a.disclosed)), ("cutoff", pd.Timestamp(DATA_CUTOFF))):
        d = dates[(dates >= when) & (dates <= when + pd.Timedelta(days=7))]
        if d.empty:
            continue
        day = d.iloc[0].strftime("%Y%m%d")
        x = pn.read_day(day, cols)
        x = x[(x["client"] == a.client) & x["client_confidence"].isin(["high", "operator"]) & (x["likely_lo"] >= 0)]
        f = exposure_flags(x, a)

        def share(m, flag="central"):
            cap = x.loc[m, "live_cap_14"].sum()
            return {"nodes": float(f.loc[m, flag].mean()),
                    "cap": float(x.loc[m & f[flag], "live_cap_14"].sum() / cap) if cap else None}
        live14 = (x["live_cap_14"] > 0) & ~x["fleet"]
        exposed = live14 & f["central"]
        out[name] = {"date": day,
                     "live14": share(live14),
                     "live7": {"nodes": float(f.loc[(x["live_cap_7"] > 0) & ~x["fleet"], "central"].mean())},
                     "live28": {"nodes": float(f.loc[(x["live_cap_28"] > 0) & ~x["fleet"], "central"].mean())},
                     "definitely": float(f.loc[live14, "definitely"].mean()),
                     "possibly": float(f.loc[live14, "possibly"].mean()),
                     "with_fleet": float(f.loc[x["live_cap_14"] > 0, "central"].mean()),
                     "exposed_nodes": int(exposed.sum()),
                     "exposed_signed_14d": float((x.loc[exposed, "ann_age_days"] <= 14).mean()),
                     "all_live_signed_14d": float((x.loc[live14, "ann_age_days"] <= 14).mean())}
    return out


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


VIEW_WIDENED = "2024-07-01"     # our gossip view widened here; older LND releases (< 0.14) are visible only after it


# ---------------------------------------------------------------------------------------
# Who followed CLN's offline call
# ---------------------------------------------------------------------------------------
def _left_by_group(d0: str, d2: str, newest: int) -> pd.DataFrame:
    """Live CLN nodes on d0 with a release line: newest-line flag, Tor-only flag, not live on d2 (and, if so, whether
    it still has announced channels, i.e. went dark rather than lost its channels), moved to a later line by d2."""
    cols = ["pub_key", "client", "client_confidence", "likely_lo", "live_cap_14", "fleet", "has_tor", "has_clearnet",
            "n_channels"]
    a, b = pn.read_day(d0, cols), pn.read_day(d2, cols).set_index("pub_key")
    a = a[(a["client"] == "CLN") & a["client_confidence"].isin(["high", "operator"]) & (a["likely_lo"] >= 0)
          & pn.live(a) & ~a["fleet"]]
    after = b["live_cap_14"].reindex(a["pub_key"]).fillna(0).to_numpy() > 0
    lo_after = b["likely_lo"].reindex(a["pub_key"]).to_numpy()
    channels_after = b["n_channels"].reindex(a["pub_key"]).fillna(0).to_numpy()
    return pd.DataFrame({"newest": (a["likely_lo"] >= newest).to_numpy(),
                         "tor_only": (a["has_tor"] & ~a["has_clearnet"]).to_numpy(),
                         "left": ~after, "left_dark": ~after & (channels_after > 0),
                         "moved": after & (lo_after > a["likely_lo"].to_numpy())})


def offline_call() -> dict:
    newest = next(ln.index for ln in pn.vf.lines("CLN") if ln.label.startswith("26.04"))
    days = set(pn.panel_dates())
    ev = _left_by_group("20260825", "20260827", newest)
    out = {"newest_line": pn.line_label("CLN", newest), "event": {}, "ordinary": []}
    for g, m in (("newest", ev["newest"]), ("behind", ~ev["newest"])):
        out["event"][g] = {"nodes": int(m.sum()), "left": float(ev.loc[m, "left"].mean()),
                           "left_n": int(ev.loc[m, "left"].sum()), "left_dark_n": int(ev.loc[m, "left_dark"].sum()),
                           "moved": float(ev.loc[m, "moved"].mean()),
                           "left_tor_only": float(ev.loc[m & ev["tor_only"], "left"].mean()),
                           "left_other": float(ev.loc[m & ~ev["tor_only"], "left"].mean())}
    t = [[int((ev["newest"] & ev["left"]).sum()), int((ev["newest"] & ~ev["left"]).sum())],
         [int((~ev["newest"] & ev["left"]).sum()), int((~ev["newest"] & ~ev["left"]).sum())]]
    res = fisher_exact(t)
    out["fisher"] = {"table": t, "odds_ratio": float(res.statistic), "p": float(res.pvalue)}
    for d0 in pd.date_range("2026-08-01", "2026-08-21"):
        a, b = d0.strftime("%Y%m%d"), (d0 + pd.Timedelta(days=2)).strftime("%Y%m%d")
        if a in days and b in days:
            w = _left_by_group(a, b, newest)
            out["ordinary"].append({"from": a, "newest": float(w.loc[w["newest"], "left"].mean()),
                                    "behind": float(w.loc[~w["newest"], "left"].mean()),
                                    "left_n": int(w["left"].sum()), "left_dark_n": int(w["left_dark"].sum())})
    return out


def table_advisories(rows: list):
    def cell(r, k, bounds=False):
        x = r.get(k)
        if not x:
            return "--"
        s = f"{100 * x['central']:.0f}"
        if bounds and r["kind"] == "PARTIAL":
            s += f" [{100 * x['definitely']:.0f}--{100 * x['possibly']:.0f}]"
        mark = r"$^\dagger$" if r["client"] == "LND" and x["date"] < VIEW_WIDENED else ""
        return s + f" ({100 * x['central_cap']:.0f}){mark}"
    lines = [r"\begin{table*}[t]", r"\centering\footnotesize",
             r"\caption{Advisories whose fix boundary is visible in gossip (LND and CLN). Exposure = share of live "
             r"nodes of that implementation whose inferred release line is affected, in \%; share of their live "
             r"capacity in parentheses; for PARTIAL rows (the fix lands inside a line) the bounds are given in "
             r"brackets at disclosure. Fix$\to$disc.\ = days from the first fixed release to public disclosure. "
             r"\# = advisories grouped in the row.}",
             r"\label{tab:advisories}", r"\resizebox{\textwidth}{!}{%", r"\begin{tabular}{lllrlrrrr}", r"\toprule",
             r"Impl. & Advisory (disclosed) & Class & \# & Fixed in & Fix$\to$disc. & At disclosure & +60\,d & Cutoff \\",
             r"\midrule"]
    for r in sorted((r for r in rows if r["client"] in ("LND", "CLN")), key=lambda r: (r["client"], r["disclosed"])):
        t = r["title"].replace("_", r"\_").replace("&", r"\&").replace("#", r"\#")
        src = f"~\\cite{{{r['cite']}}}" if r.get("cite") else ""
        lines.append(f"{r['client']} & {t}{src} ({r['disclosed']}) & {r['kind']} & {r['count']} & {r['fixed_in']} & "
                     f"{r['fix_to_disclosure_days']} & {cell(r, 'disclosure', True)} & "
                     f"{cell(r, '+60d')} & {cell(r, 'cutoff')} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}}",
              r"\par\vspace{2pt}\parbox{\textwidth}{\footnotesize $^\dagger$Before July 2024 our view did not include the "
              r"few live nodes on LND releases older than 0.14 (\S\ref{sec:data}), so these exposures are lower bounds "
              r"and the later rise to 1\% is the wider view, not nodes moving onto affected releases. In 2023 the mixed "
              r"LND line 0.15.1--0.17 held almost every LND node, so the bounds of the 2023 LND PARTIAL rows span "
              r"0--100\%. --: no usable snapshot within 7 days.}",
              r"\end{table*}"]
    (TABLES_DIR / "table_advisories.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _short(a_title: str) -> str:
    return a_title.replace("_", r"\_").replace("&", r"\&").replace("#", r"\#")


def table_response(resp: list, recent: dict):
    """One row per testable disclosure; `recent` (the CLN gossipd cohort one line behind, 25.09–25.12) is an
    indented row under its disclosure."""
    def rr(x):
        return f"{x['rr']:.2f} [{x['rr_lo']:.2f}, {x['rr_hi']:.2f}]"

    def row(r, client, title, span):
        return (f"{client} & {title} ({r['disclosed']}; {span}) & {r['fix_to_disclosure_days']} & "
                f"{r['at_risk_at_disclosure']:,} & {r['weeks_before']}/{r['weeks_after']} & "
                f"{100 * r['all']['rate_before']:.1f} & {100 * r['all']['rate_after']:.1f} & "
                f"{rr(r['all'])} & {rr(r['operator'])} & {r['operator']['p_perm']:.3f} \\\\")
    lines = [r"\begin{table*}[t]", r"\centering\footnotesize",
             r"\caption{Did operators respond to the disclosure? Weekly share of live nodes on a wholly affected line "
             r"that moved to a later line, in the 8 weeks before and the 4 weeks after disclosure (fewer where "
             r"snapshots are missing or the cutoff intervenes), and the ratio after/before with a quasi-Poisson 95\% "
             r"CI. ``Outside platform releases'' leaves out moves signed within 48~h after an Umbrel or BTCPay "
             r"release that ships the new line (Section~\ref{sec:waves}); $p$: exact one-sided permutation test that "
             r"the weekly rates after exceed those before, outside platform releases. Indented: the nodes of the row "
             r"above that were one line behind the fix (Section~\ref{sec:response}). Managed fleet excluded.}",
             r"\label{tab:response}", r"\resizebox{\textwidth}{!}{%", r"\begin{tabular}{llrrrrrllr}", r"\toprule",
             r" & & Fix$\to$disc. & At risk & Weeks & \multicolumn{2}{c}{Weekly rate (\%)} & "
             r"\multicolumn{3}{c}{Rate ratio after/before} \\",
             r"\cmidrule(lr){6-7}\cmidrule(lr){8-10}",
             r"Impl. & Advisory (disclosed; affected lines) & (days) & nodes & bef./aft. & before & after & "
             r"all moves & outside platform releases & $p$ \\", r"\midrule"]
    for r in resp:
        span = r["affected_span"].replace("<", "$<$").replace("–", "--")
        lines.append(row(r, r["client"], _short(r["title"]), span))
        if r["key"] == "cln-2026-gossipd":
            lines.append(row(recent, "", r"\quad of which one line behind", "25.09--25.12"))
    lines += [r"\bottomrule", r"\end{tabular}}", r"\end{table*}"]
    (TABLES_DIR / "table_response.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def table_robustness(rob: dict):
    pc = lambda x: "--" if x is None else f"{100 * x:.0f}"

    def base(prefix):
        xs = [rob[k][w]["all_live_signed_14d"] for k in CASES if k.startswith(prefix) for w in rob[k]]
        return f"{pc(min(xs))}--{pc(max(xs))}"
    lines = [r"\begin{table*}[t]", r"\centering\footnotesize",
             r"\caption{Robustness of the case-study exposures: share of live nodes on an affected line (\%) at "
             r"disclosure and at the cutoff, with live capacity in parentheses for the main definition. Liveness: a "
             r"peer-set channel direction toward the node enabled and updated within 7, 14 (main) or 28 days. Strict "
             r"bounds: nodes whose every consistent line is affected, and nodes with any affected consistent line. "
             r"Last column: share of the exposed nodes whose current announcement was signed in the previous 14 days, "
             r"against " + base("lnd") + r"\% of all live LND and " + base("cln") + r"\% of all live CLN nodes on the "
             r"same days (Section~\ref{sec:robust}).}",
             r"\label{tab:robustness}", r"\resizebox{\textwidth}{!}{%", r"\begin{tabular}{lllrrrrrr}", r"\toprule",
             r"Advisory & When & Day & 14\,d (main) & 7\,d & 28\,d & Strict bounds & Fleet as nodes & "
             r"Signed $<$14\,d \\", r"\midrule"]
    for k in CASES:
        title = CASE_TITLES[k].replace("\n", ", ").replace("<", r"$<$")
        for when in ("disclosure", "cutoff"):
            x = rob[k].get(when)
            if not x:
                continue
            fleet = pc(x["with_fleet"]) if k.startswith("lnd") else "--"
            d = x["date"]
            lines.append(f"{title if when == 'disclosure' else ''} & {when} & {d[:4]}-{d[4:6]}-{d[6:]} & "
                         f"{pc(x['live14']['nodes'])} ({pc(x['live14']['cap'])}) & {pc(x['live7']['nodes'])} & "
                         f"{pc(x['live28']['nodes'])} & [{pc(x['definitely'])}, {pc(x['possibly'])}] & {fleet} & "
                         f"{pc(x['exposed_signed_14d'])} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}}", r"\end{table*}"]
    (TABLES_DIR / "table_robustness.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def fig_response(resp: list):
    """Left: weekly rate of leaving the affected lines around two disclosures. Right: rate ratios for all advisories."""
    by_key = {r["key"]: r for r in resp}
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.7), gridspec_kw={"width_ratios": [1, 1, 1.25]})
    for ax, k in zip(axes[:2], RESP_SERIES):
        r = by_key[k]
        wk = pd.DataFrame(r["weekly"]).dropna(subset=["nodes"])
        n = wk["nodes"].astype(float)
        op = (wk["moved"] - wk["moved_platform"]) / n
        plat = wk["moved_platform"] / n
        col = CLIENT_PALETTE[r["client"]]
        ax.bar(wk["week"], 100 * op, width=0.8, color=col, label="other moves")
        ax.bar(wk["week"], 100 * plat, bottom=100 * op, width=0.8, color="#b8860b", label="after a platform release")
        ax.axvline(-0.5, color="0.3", lw=0.7)
        ax.text(-0.6, 0.98, "disclosure ", transform=ax.get_xaxis_transform(), fontsize=6, va="top", ha="right",
                color="0.3")
        ax.set_ylim(0, 1.15 * float((100 * (op + plat)).max()))
        ax.set_xlabel("weeks since disclosure")
        ax.set_title(CASE_TITLES[k].replace("\n", ", "), fontsize=7)
        ax.set_xlim(-RESP_WEEKS[0] - 0.6, RESP_WEEKS[1] - 0.4)
    axes[0].set_ylabel("nodes leaving affected\nlines per week (%)")
    h, _ = axes[1].get_legend_handles_labels()      # the CLN panel's early weeks are low enough to hold the legend
    axes[1].legend(h, ["other moves", "after a platform\nrelease"], frameon=False, fontsize=6, loc="upper left",
                   bbox_to_anchor=(0.0, 0.86))
    ax = axes[2]
    ok = [r for r in resp if r.get("all")]
    ylab = []
    for i, r in enumerate(ok):
        y = len(ok) - 1 - i
        for dy, key, mk, fill in ((0.17, "all", "o", True), (-0.17, "operator", "s", False)):
            x = r[key]
            col = CLIENT_PALETTE[r["client"]]
            ax.plot([x["rr_lo"], x["rr_hi"]], [y + dy] * 2, color=col, lw=0.9)
            ax.plot(x["rr"], y + dy, marker=mk, ms=3.2, color=col, mfc=col if fill else "white", lw=0)
        ylab.append(f"{r['client']} {pd.Timestamp(r['disclosed']):%d %b %Y} ({r['affected_span']})")
    ax.axvline(1, color="0.5", lw=0.6, ls=":")
    ax.set_xscale("log")
    ax.set_xlim(0.08, 10)
    ax.set_xticks([0.1, 0.3, 1, 3, 10], ["0.1", "0.3", "1", "3", "10"])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_yticks(range(len(ok)), ylab[::-1], fontsize=5.6)
    ax.set_ylim(-0.6, len(ok) - 0.4)
    ax.set_xlabel("rate ratio after / before")
    ax.plot([], [], marker="o", ms=3.2, color="0.3", lw=0, label="all moves")
    ax.plot([], [], marker="s", ms=3.2, color="0.3", mfc="white", lw=0, label="outside platform releases")
    ax.legend(frameon=False, fontsize=5.8, loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2, handletextpad=0.2,
              columnspacing=0.8, borderaxespad=0.2)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig7_response.pdf")
    plt.close(fig)


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
    rob = {}
    for k in CASES:
        a = next(x for x in ADVISORIES if x.key == k)
        fates[k] = cohort_fate(p, a)
        rob[k] = robustness(a)
        if fates[k]:
            last = fates[k]["fate"][-1]
            print(f"case {k}: cohort {fates[k]['cohort_nodes']} on {fates[k]['cohort_date']}; at {last['date']}: "
                  f"upgraded {last['upgraded']}, not live {last['left']}, still exposed {last['exposed']}")
        print(f"  robustness: {rob[k]}")

    resp = []
    for a in sorted((x for x in ADVISORIES if x.client in ("LND", "CLN")), key=lambda x: (x.client, x.disclosed)):
        r = response(p, a)
        if r["ok"] and r.get("all"):
            resp.append(r)
            print(f"response {a.key:24s} at risk {r['at_risk_at_disclosure']:5d} weeks {r['weeks_before']}/"
                  f"{r['weeks_after']}  all RR {r['all']['rr']:.2f} [{r['all']['rr_lo']:.2f}, {r['all']['rr_hi']:.2f}]"
                  f"  outside platform RR {r['operator']['rr']:.2f} [{r['operator']['rr_lo']:.2f}, "
                  f"{r['operator']['rr_hi']:.2f}] p {r['operator']['p_perm']:.3f}  dispersion {r['all']['dispersion']:.1f}")
        else:
            print(f"response {a.key:24s} skipped: weeks with data {r['weeks_before']}/{r['weeks_after']}")
    a = next(x for x in ADVISORIES if x.key == "cln-2026-gossipd")
    recent = response(p, replace(a, key="cln-2026-gossipd-recent", affected=("25.09–25.12",)))
    print(f"response CLN 2026-07-19, nodes on 25.09–25.12 only: at risk {recent['at_risk_at_disclosure']}  all RR "
          f"{recent['all']['rr']:.2f} [{recent['all']['rr_lo']:.2f}, {recent['all']['rr_hi']:.2f}]  outside platform "
          f"RR {recent['operator']['rr']:.2f} [{recent['operator']['rr_lo']:.2f}, {recent['operator']['rr_hi']:.2f}]")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    fig_cases(series, fates)
    fig_response(resp)
    table_advisories(rows)
    table_response(resp, recent)
    table_robustness(rob)
    call = offline_call()
    e = call["event"]
    print(f"CLN offline call 08-25 -> 08-27: newest line ({call['newest_line']}) {e['newest']['nodes']} nodes, "
          f"{100 * e['newest']['left']:.1f}% not live; older lines {e['behind']['nodes']} nodes, "
          f"{100 * e['behind']['left']:.1f}%; Fisher OR {call['fisher']['odds_ratio']:.2f} p {call['fisher']['p']:.1e}; "
          f"ordinary windows: {[(w['from'], round(100 * w['newest'], 1), round(100 * w['behind'], 1)) for w in call['ordinary']]}")
    out = {"advisories": rows, "cases": fates, "response": resp, "response_cln_one_line_behind": recent,
           "cln_offline_call": call, "robustness": rob,
           "series": {k: s.reset_index().assign(date=lambda x: x["date"].dt.strftime("%Y-%m-%d"))
                         .round(5).to_dict(orient="list") for k, s in series.items() if k in CASES}}
    (DATA_DIR / "advisory_exposure.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("-> data/advisory_exposure.json, tables/table_advisories.tex, figures/fig6_exposure_cases.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
