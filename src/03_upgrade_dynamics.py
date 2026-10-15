"""
03_upgrade_dynamics.py — RQ2: how fast do Lightning nodes move to new release lines, and who lags?

Population: live nodes (src/lnmetrics/panel.py) running LND or CLN with an inferred release line (operator/high
client label, a matching line); a node's line on a day is its likely line. The managed fleet (panel column `fleet`,
config.FLEET_ALIAS_PREFIX) is one operator's decision repeated over hundreds of nodes: it is excluded from every
per-node statistic and described separately (size, lines, its upgrade waves); adoption is also given with it.

  line mix     share of live nodes (and of their live capacity) on each line, per day
  adoption     for each line released while daily data is dense: share of live nodes on that line or later vs days
               since release; days until 10% / 50% of nodes and of capacity; first live node seen on the line
  time to      nodes live on the release day and on an older line are followed until first seen on the new line or
  upgrade      later. Gossip snapshots have gaps, so the upgrade day is only known to lie in (last day seen on the
               old line, first day seen on the new one]: the share upgraded by day t is the nonparametric maximum
               likelihood (Turnbull) estimate for interval-censored times. Nodes that stop being live before
               upgrading are right-censored at their last live day (their count is reported).
  hazard       discrete-time logit on node-weeks after each release (week and release fixed effects): capacity,
               channel count, Tor-only, LND default colour (an unconfigured node), first seen before 2024
  waves        days on which unusually many nodes move to one line, merged into events when consecutive: count,
               dominant feature set, size and age of the nodes involved compared with other upgraders (a wave of new,
               empty nodes would point to a fleet), when the nodes signed their new announcements, and whether a
               dated platform release (src/lnmetrics/platforms.py) shipping that line preceded the signatures
  platforms    share of all upgrades whose new announcement was signed within 48 h after such a platform release

Outputs
  data/upgrade_dynamics.json
  paper/figures/fig1_line_mix.pdf, fig3_adoption.pdf, fig4_time_to_upgrade.pdf, fig5_waves.pdf
  paper/tables/table_hazard.tex

Usage:  python src/03_upgrade_dynamics.py
"""

import json
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CLIENT_PALETTE, DATA_CUTOFF, DATA_DIR, FIGURES_DIR, TABLES_DIR  # noqa: E402
from lnmetrics import panel as pn  # noqa: E402
from lnmetrics import platforms as pf  # noqa: E402
from lnmetrics import version_fingerprint as vf  # noqa: E402

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

CLIENTS = ["LND", "CLN"]
DENSE_FROM = pd.Timestamp("2023-11-01")      # daily coverage is dense from here (spec §4)
HORIZON_DAYS = 365
PLATFORM_HOURS = 48                          # an upgrade signed this soon after a platform release is attributed to it
COLS = ["date", "pub_key", "client", "client_confidence", "likely_lo", "live_cap_14", "n_channels", "has_tor",
        "has_clearnet", "color", "feature_sig", "fleet", "ann_age_days"]

plt.rcParams.update({"font.family": "serif", "font.size": 8.5, "axes.titlesize": 9, "xtick.labelsize": 7.5,
                     "ytick.labelsize": 7.5, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})


def load() -> pd.DataFrame:
    p = pn.load(COLS, where=lambda p: pn.live(p) & p["client"].isin(CLIENTS)
                & p["client_confidence"].isin(["high", "operator"]) & (p["likely_lo"] >= 0))
    p["date"] = pd.to_datetime(p["date"])
    for c in ["client", "color", "feature_sig"]:
        p[c] = p[c].astype("category")
    p["tor_only"] = p["has_tor"].fillna(False).astype(bool) & ~p["has_clearnet"].fillna(False).astype(bool)
    return p.sort_values(["pub_key", "date"]).reset_index(drop=True)


def releases(client: str):
    return [ln for ln in vf.lines(client) if pd.Timestamp(ln.released) >= DENSE_FROM - pd.Timedelta(days=60)]


# ---------------------------------------------------------------------------------------
# Line mix and adoption
# ---------------------------------------------------------------------------------------
def line_mix(p: pd.DataFrame, client: str) -> pd.DataFrame:
    q = p[p["client"] == client]
    n = q.groupby(["date", "likely_lo"]).size().unstack(fill_value=0)
    return n.div(n.sum(axis=1), axis=0)


def adoption(p: pd.DataFrame, client: str) -> dict:
    q = p[p["client"] == client]
    tot_n = q.groupby("date").size()
    tot_c = q.groupby("date")["live_cap_14"].sum()
    out = {}
    for ln in releases(client):
        rel = pd.Timestamp(ln.released)
        on = q["likely_lo"] >= ln.index
        sn = (q[on].groupby("date").size().reindex(tot_n.index, fill_value=0) / tot_n)
        sc = (q[on].groupby("date")["live_cap_14"].sum().reindex(tot_c.index, fill_value=0) / tot_c)
        days = (sn.index - rel).days
        first = q[(q["likely_lo"] == ln.index)]["date"].min()

        def reach(s, x):
            hit = s[(days >= 0) & (s >= x)]
            return int((hit.index[0] - rel).days) if len(hit) else None
        out[ln.label] = {"released": ln.released, "first_seen_days": int((first - rel).days) if pd.notna(first) else None,
                         "t10_nodes": reach(sn, 0.10), "t50_nodes": reach(sn, 0.50),
                         "t10_cap": reach(sc, 0.10), "t50_cap": reach(sc, 0.50),
                         "share_at_cutoff": float(sn.iloc[-1]), "cap_share_at_cutoff": float(sc.iloc[-1]),
                         "curve_days": [int(d) for d in days[(days >= -60) & (days <= HORIZON_DAYS)]],
                         "curve_nodes": [round(float(x), 4) for x in sn[(days >= -60) & (days <= HORIZON_DAYS)]],
                         "curve_cap": [round(float(x), 4) for x in sc[(days >= -60) & (days <= HORIZON_DAYS)]]}
    return out


# ---------------------------------------------------------------------------------------
# Time to upgrade (interval-censored)
# ---------------------------------------------------------------------------------------
def at_risk(p: pd.DataFrame, client: str, ln) -> pd.DataFrame:
    """One row per node live on an older line at the release: (lo, hi] upgrade interval in days, or censoring."""
    q = p[p["client"] == client]
    rel = pd.Timestamp(ln.released)
    day0 = q.loc[(q["date"] >= rel) & (q["date"] <= rel + pd.Timedelta(days=7)), "date"].min()
    if pd.isna(day0):
        return pd.DataFrame()
    start = q[(q["date"] == day0) & (q["likely_lo"] < ln.index)].set_index("pub_key")
    f = q[q["pub_key"].isin(start.index) & (q["date"] >= day0)
          & (q["date"] <= rel + pd.Timedelta(days=HORIZON_DAYS))]
    up = f[f["likely_lo"] >= ln.index].groupby("pub_key")["date"].min()
    last_old = f[f["likely_lo"] < ln.index].merge(up.rename("up"), left_on="pub_key", right_index=True, how="left")
    last_old = last_old[last_old["up"].isna() | (last_old["date"] < last_old["up"])].groupby("pub_key")["date"].max()
    rows = pd.DataFrame(index=start.index)
    rows["lo"] = (last_old.reindex(rows.index) - rel).dt.days
    rows["hi"] = (up.reindex(rows.index) - rel).dt.days
    rows["event"] = rows["hi"].notna()
    rows["cap"] = start["live_cap_14"]
    rows["n_channels"] = start["n_channels"]
    rows["tor_only"] = start["tor_only"]
    rows["default_color"] = start["color"].astype(str) == "#3399ff"
    first_seen = q.groupby("pub_key")["date"].min()
    rows["old_node"] = first_seen.reindex(rows.index) < pd.Timestamp("2024-01-01")
    rows["lines_behind"] = ln.index - start["likely_lo"]
    rows["release"] = ln.label
    return rows


def turnbull(lo: np.ndarray, hi: np.ndarray, horizon: int, iters: int = 1000) -> np.ndarray:
    """Share upgraded by day 0..horizon: nonparametric MLE for interval-censored times (Turnbull 1976), by EM.
    Interval (lo, hi] per node in days; hi = NaN means right-censored at lo. Mass may sit only on observed upgrade
    days (right ends of event intervals) or beyond the horizon, the support of the NPMLE; elsewhere it is not
    identified."""
    grid = horizon + 2                                  # days 0..horizon, then "later"
    lo = np.nan_to_num(lo, nan=-1).astype(int)
    cens = np.isnan(hi)
    hi_f = np.where(cens, grid - 1, np.minimum(np.nan_to_num(hi, nan=0), horizon)).astype(int)
    support = np.zeros(grid, dtype=bool)
    support[np.unique(hi_f[~cens])] = True
    support[grid - 1] = True
    t = np.arange(grid)
    A = (t[None, :] > lo[:, None]) & (t[None, :] <= hi_f[:, None]) & support[None, :]
    p = support / support.sum()
    for _ in range(iters):
        w = A * p
        w /= w.sum(axis=1, keepdims=True)
        p_new = w.mean(axis=0)
        if np.abs(p_new - p).max() < 1e-7:
            p = p_new
            break
        p = p_new
    return np.cumsum(p)[:horizon + 1]


def median_day(F: np.ndarray):
    hit = np.nonzero(F >= 0.5)[0]
    return int(hit[0]) if len(hit) else None


def hazard_model(risk: pd.DataFrame) -> pd.DataFrame:
    """Discrete-time logit on node-weeks (event week = week of the first day seen upgraded)."""
    r = risk.rename_axis("node").reset_index()          # a node can be at risk for several releases
    r["end"] = np.where(r["event"], r["hi"], r["lo"].fillna(0)).clip(0, HORIZON_DAYS)
    r["weeks"] = (r["end"] // 7).astype(int) + 1
    rows = r.loc[r.index.repeat(r["weeks"])].copy()
    rows["week"] = np.concatenate([np.arange(w) for w in r["weeks"]])
    rows["y"] = (rows["event"] & (rows["week"] == rows["weeks"] - 1)).astype(int)
    X = pd.DataFrame({
        "log10_capacity": np.log10(rows["cap"].clip(lower=1e4)),
        "log10_channels": np.log10(rows["n_channels"].clip(lower=1)),
        "tor_only": rows["tor_only"].astype(int),
        "default_color": rows["default_color"].astype(int),
        "first_seen_before_2024": rows["old_node"].fillna(False).astype(int),
        "lines_behind_gt1": (rows["lines_behind"] > 1).astype(int),
    })
    wk = pd.get_dummies(np.minimum(rows["week"], 26).astype(str), prefix="wk", drop_first=True, dtype=float)
    rel = pd.get_dummies(rows["release"].astype(str), prefix="rel", drop_first=True, dtype=float)
    X = sm.add_constant(pd.concat([X.reset_index(drop=True), wk.reset_index(drop=True), rel.reset_index(drop=True)],
                                  axis=1).astype(float))
    fit = sm.GLM(rows["y"].to_numpy(), X, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(rows["node"])[0]})
    keep = ["log10_capacity", "log10_channels", "tor_only", "default_color", "first_seen_before_2024",
            "lines_behind_gt1"]
    ci = fit.conf_int().loc[keep]
    return pd.DataFrame({"odds_ratio": np.exp(fit.params[keep]), "ci_low": np.exp(ci[0]), "ci_high": np.exp(ci[1]),
                         "p": fit.pvalues[keep]}).assign(node_weeks=len(rows), nodes=r["node"].nunique(),
                                                         spells=len(r))


# ---------------------------------------------------------------------------------------
# Waves
# ---------------------------------------------------------------------------------------
def upgrade_events(p: pd.DataFrame) -> pd.DataFrame:
    prev = p.groupby("pub_key")[["likely_lo", "date"]].shift()
    ev = p[(p["likely_lo"] > prev["likely_lo"]) & prev["likely_lo"].notna()].copy()
    ev["from_lo"] = prev.loc[ev.index, "likely_lo"]
    ev["gap_days"] = (ev["date"] - prev.loc[ev.index, "date"]).dt.days
    first_seen = p.groupby("pub_key")["date"].min()
    ev["age_days"] = (ev["date"] - ev["pub_key"].map(first_seen)).dt.days
    ev["signed"] = pn.signed_at(ev)            # when the node signed its first announcement on the new line
    ev["platform"] = False
    for c in CLIENTS:
        m = ev["client"] == c
        ev.loc[m, "platform"] = pf.after_release(c, ev.loc[m, "signed"], ev.loc[m, "likely_lo"], PLATFORM_HOURS)
    return ev


def _platform_match(w: pd.DataFrame, client: str, line: int, first: pd.Timestamp, last: pd.Timestamp) -> dict:
    """The platform release shipping `line` that best explains a wave: most of the wave's nodes signed their new
    announcement within PLATFORM_HOURS after it. Candidates: releases from three days before the wave's first day
    to the end of its last day."""
    best = {"platform": None}
    for r in pf.releases(client):
        if r.line != pn.line_label(client, line) or not (first - pd.Timedelta(days=3) <= r.ts <= last + pd.Timedelta(days=1)):
            continue
        h = (w["signed"] - r.ts).dt.total_seconds() / 3600
        after = float(((h >= 0) & (h <= PLATFORM_HOURS)).mean())
        if best["platform"] is None or after > best["share_signed_after"]:
            best = {"platform": r.platform, "version": r.version, "utc": r.utc, "source": r.source,
                    "share_signed_after": after, "share_signed_24h_before": float(((h < 0) & (h >= -24)).mean()),
                    "median_hours_after": float(h[h >= 0].median()) if (h >= 0).any() else None}
    best["attributed"] = bool(best["platform"] is not None and best["share_signed_after"] >= 0.5)
    return best


def waves(ev: pd.DataFrame, p: pd.DataFrame, client: str) -> dict:
    """Wave days: (day, line) counts of upgrades above the 99th percentile (and at least 20). Consecutive wave days
    on the same line are one event."""
    e = ev[(ev["client"] == client) & (ev["gap_days"] <= 2)]      # upgrade day known to within two days
    daily = e.groupby(["date", "likely_lo"]).size()
    thr = float(daily.quantile(0.99))
    hot = sorted(daily[daily > max(thr, 20)].index, key=lambda x: (x[1], x[0]))
    events = []
    for d, line in hot:
        if events and events[-1]["line"] == line and (d - events[-1]["days"][-1]).days <= 2:
            events[-1]["days"].append(d)
        else:
            events.append({"line": line, "days": [d]})
    q = p[p["client"] == client]
    base_tor = q.groupby("date")["tor_only"].mean()
    out = []
    for x in events:
        line, days = int(x["line"]), x["days"]
        w = e[e["date"].isin(days) & (e["likely_lo"] == line)]
        others = e[(e["likely_lo"] == line) & ~e["date"].isin(days)]
        sig = w["feature_sig"].astype(str).value_counts()
        out.append({"first_day": days[0].strftime("%Y-%m-%d"), "last_day": days[-1].strftime("%Y-%m-%d"),
                    "days": len(days), "line": pn.line_label(client, line), "nodes": len(w),
                    "days_after_release": int((days[0] - pn.line_release(client, line)).days),
                    "from_lines": {pn.line_label(client, int(k)): int(v) for k, v in w["from_lo"].value_counts().items()},
                    "top_sig_share": float(sig.iloc[0] / len(w)),
                    "median_cap_btc": float(w["live_cap_14"].median() / 1e8),
                    "median_cap_btc_other_upgraders": float(others["live_cap_14"].median() / 1e8),
                    "median_age_days": float(w["age_days"].median()),
                    "median_age_days_other_upgraders": float(others["age_days"].median()),
                    "share_tor_only": float(w["tor_only"].mean()),
                    "share_tor_only_all_live": float(base_tor.reindex(days).mean()),
                    "share_default_color": float((w["color"].astype(str) == "#3399ff").mean()),
                    "share_signed_within_2d": float(((w["date"] + pd.Timedelta(days=1) - w["signed"]).dt.days < 2).mean()),
                    "platform": _platform_match(w, client, line, days[0], days[-1])})
    return {"threshold_p99": thr, "daily": {f"{d:%Y-%m-%d}|{int(l)}": int(n) for (d, l), n in daily.items()},
            "waves": sorted(out, key=lambda x: -x["nodes"])}


def platform_lines(p: pd.DataFrame, client: str, min_changes: int = 100) -> list:
    """An external check of the inference: every line change (up or down; day known to within two days) whose new
    announcement was signed within PLATFORM_HOURS after a platform release, and the share that landed on the line
    that release shipped. Releases followed by fewer than `min_changes` such changes are left out."""
    q = p[p["client"] == client]
    g = q.groupby("pub_key")
    prev, prev_d = g["likely_lo"].shift(), g["date"].shift()
    ch = q[(q["likely_lo"] != prev) & prev.notna() & ((q["date"] - prev_d).dt.days <= 2)]
    signed = pn.signed_at(ch)
    out = []
    for r in pf.releases(client):
        h = (signed - r.ts).dt.total_seconds() / 3600
        x = ch[(h >= 0) & (h <= PLATFORM_HOURS)]
        if len(x) < min_changes:
            continue
        on = (x["likely_lo"].map(lambda i: pn.line_label(client, int(i))) == r.line).mean()
        out.append({"platform": r.platform, "version": r.version, "utc": r.utc, "line": r.line, "changes": len(x),
                    "share_on_shipped_line": float(on)})
    return out


def platform_share(ev: pd.DataFrame, client: str, since: str) -> dict:
    """Share of upgrades (day known to within two days) signed within PLATFORM_HOURS after a platform release that
    ships the new line or a later one, against the share of time such windows cover."""
    e = ev[(ev["client"] == client) & (ev["gap_days"] <= 2) & (ev["date"] >= since)]
    start, end = pd.Timestamp(since), e["date"].max() + pd.Timedelta(days=1)
    t = pd.date_range(start, end, freq="h")
    covered = pd.Series(False, index=t)
    for r in pf.releases(client):
        covered |= (t >= r.ts) & (t <= r.ts + pd.Timedelta(hours=PLATFORM_HOURS))
    return {"since": since, "upgrades": len(e), "platform_upgrades": int(e["platform"].sum()),
            "share": float(e["platform"].mean()), "time_share": float(covered.mean()),
            "releases": len([r for r in pf.releases(client) if r.ts >= start])}


# ---------------------------------------------------------------------------------------
# Figures and tables
# ---------------------------------------------------------------------------------------
def fig_line_mix(mixes: dict):
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.6), sharey=True)
    for ax, client in zip(axes, CLIENTS):
        m = mixes[client]
        m = m[m.index >= DENSE_FROM - pd.Timedelta(days=200)]
        cols = [c for c in m.columns if m[c].max() >= 0.02]
        other = m.drop(columns=cols).sum(axis=1)
        cmap = plt.get_cmap("viridis", len(cols) + 1)
        ax.stackplot(m.index, *[100 * m[c] for c in cols], 100 * other,
                     colors=[cmap(i) for i in range(len(cols))] + ["0.85"],
                     labels=[pn.line_label(client, int(c)) for c in cols] + ["other"], lw=0)
        for c in cols:
            rel = pn.line_release(client, int(c))
            if rel >= m.index.min():
                ax.axvline(rel, color="white", lw=0.5)
        ax.set_title(f"{client}: live nodes by inferred release line")
        ax.set_xlim(m.index.min(), m.index.max())
        ax.tick_params(axis="x", labelrotation=45)
        ax.legend(frameon=False, fontsize=5.5, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    axes[0].set_ylabel("share of live nodes (%)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig1_line_mix.pdf")
    plt.close(fig)


def _gapped(days, values, max_gap: int = 3):
    """Break a line where consecutive observations are more than max_gap days apart (snapshot gaps)."""
    d = np.asarray(days, float)
    v = np.asarray(values, float)
    brk = np.nonzero(np.diff(d) > max_gap)[0]
    return np.insert(d, brk + 1, np.nan), np.insert(v, brk + 1, np.nan)


def fig_adoption(adopt: dict):
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.6), sharey=True)
    for ax, client in zip(axes, CLIENTS):
        items = list(adopt[client].items())
        cmap = plt.get_cmap("viridis", len(items) + 1)
        for i, (label, a) in enumerate(items):
            ax.plot(*_gapped(a["curve_days"], [100 * x for x in a["curve_nodes"]]), color=cmap(i), lw=1.3, label=label)
            ax.plot(*_gapped(a["curve_days"], [100 * x for x in a["curve_cap"]]), color=cmap(i), lw=0.7, ls=":")
        ax.axvline(0, color="0.4", lw=0.6)
        ax.axhline(50, color="0.85", lw=0.5)
        ax.set_xlim(-60, HORIZON_DAYS)
        ax.set_xlabel("days since release")
        ax.set_title(client)
        ax.legend(frameon=False, fontsize=6, loc="lower right")
    axes[0].set_ylabel("live nodes on the line\nor a later one (%)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig3_adoption.pdf")
    plt.close(fig)


def fig_time_to_upgrade(curves: dict):
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.5), sharey=True)
    for ax, client in zip(axes, CLIENTS):
        cmap = plt.get_cmap("viridis", 5)
        for i, (label, F) in enumerate(curves[client].items()):
            ax.step(np.arange(len(F)), 100 * F, where="post", lw=1.2, color=cmap(3 - i), label=label)
        ax.axhline(50, color="0.85", lw=0.5)
        ax.set_xlim(0, HORIZON_DAYS)
        ax.set_ylim(0, 100)
        ax.set_xlabel("days since release")
        ax.set_title(f"{client}, by live capacity at release")
        ax.legend(frameon=False, fontsize=6, loc="upper left")
    axes[0].set_ylabel("nodes on an older line\nthat have upgraded (%)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig4_time_to_upgrade.pdf")
    plt.close(fig)


def fig_waves(ev: pd.DataFrame, days: pd.DatetimeIndex):
    days = days[days >= DENSE_FROM]
    gaps = [(a, b) for a, b in zip(days[:-1], days[1:]) if (b - a).days > 3]
    fig, axes = plt.subplots(2, 1, figsize=(7.0, 3.2), sharex=True)
    for ax, client in zip(axes, CLIENTS):
        e = ev[(ev["client"] == client) & (ev["gap_days"] <= 2) & (ev["date"] >= DENSE_FROM)]
        d = e.groupby("date").size()
        for a, b in gaps:
            ax.axvspan(a, b, color="0.92", lw=0)
        last, raised = None, False
        for ln in releases(client):
            rel = pd.Timestamp(ln.released)
            if rel >= DENSE_FROM:
                ax.axvline(rel, color="0.5", lw=0.5, ls=":")
                raised = last is not None and (rel - last).days < 60 and not raised
                ax.text(rel, 1.09 if raised else 1.0, ln.label.split("–")[0], transform=ax.get_xaxis_transform(),
                        fontsize=5.5, ha="left", va="bottom", color="0.4")
                last = rel
        ax.bar(d.index, d.values, width=1.0, color=CLIENT_PALETTE[client])
        for r in pf.releases(client):
            if r.ts >= DENSE_FROM:
                ax.plot(r.ts, 0.93, marker="v", ms=3.2, color="0.15" if r.platform == "Umbrel" else "#b8860b",
                        transform=ax.get_xaxis_transform(), clip_on=False, lw=0)
        ax.set_ylabel(f"{client}\nupgrades per day")
    axes[0].plot([], [], marker="v", ms=3.2, color="0.15", lw=0, label="Umbrel app-store release")
    axes[0].plot([], [], marker="v", ms=3.2, color="#b8860b", lw=0, label="BTCPay 2.4.2")
    axes[0].legend(frameon=False, fontsize=6, loc="upper left", bbox_to_anchor=(0.0, 0.88))
    axes[-1].set_xlim(DENSE_FROM, days.max())
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig5_waves.pdf")
    plt.close(fig)


def table_hazard(h: pd.DataFrame):
    names = {"log10_capacity": "Capacity ($\\times$10)", "log10_channels": "Channels ($\\times$10)",
             "tor_only": "Tor-only", "default_color": "LND default colour",
             "first_seen_before_2024": "Seen before 2024", "lines_behind_gt1": "$>$1 line behind"}
    lines = [r"\begin{table}[t]", r"\centering\small",
             r"\caption{What predicts upgrading: discrete-time logit on node-weeks after each LND release "
             r"(week and release fixed effects; standard errors clustered by node). Odds ratios with 95\% CI.}",
             r"\label{tab:hazard}", r"\begin{tabular}{lrr}", r"\toprule", r"Covariate & Odds ratio & 95\% CI \\",
             r"\midrule"]
    for k, r in h.iterrows():
        lines.append(f"{names[k]} & {r.odds_ratio:.2f} & [{r.ci_low:.2f}, {r.ci_high:.2f}] \\\\")
    lines += [r"\midrule", f"Nodes / node-weeks & \\multicolumn{{2}}{{r}}{{{int(h['nodes'].iloc[0]):,} / "
              f"{int(h['node_weeks'].iloc[0]):,}}} \\\\", r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (TABLES_DIR / "table_hazard.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def fleet_summary(p_all: pd.DataFrame) -> dict:
    """The managed fleet (config.FLEET_ALIAS_PREFIX) among live LND nodes: size over time and its lines."""
    q = p_all[p_all["client"] == "LND"]
    n = q.groupby("date")["fleet"].agg(["sum", "size"])
    cap = q.groupby(["date", "fleet"])["live_cap_14"].sum().unstack(fill_value=0)
    peak = n["sum"].idxmax()
    first = n.index[n["sum"] > 0].min()
    lines = (q[q["fleet"]].groupby(["date", "likely_lo"]).size().unstack(fill_value=0))
    monthly = lines.groupby(lines.index.to_period("M")).last()
    return {"first_day": first.strftime("%Y-%m-%d"), "peak_day": peak.strftime("%Y-%m-%d"),
            "peak_nodes": int(n.loc[peak, "sum"]), "peak_share_live_lnd": float(n.loc[peak, "sum"] / n.loc[peak, "size"]),
            "peak_cap_btc": float(cap.loc[peak, True] / 1e8), "peak_total_cap_btc": float(cap.loc[peak].sum() / 1e8),
            "cutoff_nodes": int(n["sum"].iloc[-1]), "cutoff_share_live_lnd": float(n["sum"].iloc[-1] / n["size"].iloc[-1]),
            "cutoff_cap_btc": float(cap[True].iloc[-1] / 1e8),
            "monthly_lines": {str(k): {pn.line_label("LND", int(c)): int(v) for c, v in row.items() if v}
                              for k, row in monthly.iterrows()}}


def main() -> int:
    p_all = load()
    p = p_all[~p_all["fleet"]]
    print(f"live versioned node-days: {len(p_all):,} ({p_all['pub_key'].nunique():,} nodes); "
          f"without the managed fleet: {len(p):,} ({p['pub_key'].nunique():,} nodes)")
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = {"data_cutoff": DATA_CUTOFF, "fleet": fleet_summary(p_all)}
    print("fleet:", {k: v for k, v in out["fleet"].items() if k != "monthly_lines"})

    mixes = {c: line_mix(p, c) for c in CLIENTS}
    fig_line_mix(mixes)
    adopt = {c: adoption(p, c) for c in CLIENTS}
    fig_adoption(adopt)
    out["adoption"] = adopt
    out["adoption_with_fleet_lnd"] = {k: {x: v[x] for x in ("t10_nodes", "t50_nodes", "t10_cap", "t50_cap",
                                                            "share_at_cutoff")}
                                      for k, v in adoption(p_all, "LND").items()}
    for c in CLIENTS:
        for label, a in adopt[c].items():
            print(f"{c} {label:14s} released {a['released']}: first seen {a['first_seen_days']}d, "
                  f"10%/50% nodes {a['t10_nodes']}/{a['t50_nodes']}d, capacity {a['t10_cap']}/{a['t50_cap']}d, "
                  f"at cutoff {100 * a['share_at_cutoff']:.0f}% ({100 * a['cap_share_at_cutoff']:.0f}% cap)")

    curves, ttu, risks = {}, {}, {}
    for c in CLIENTS:
        rs = [at_risk(p, c, ln) for ln in releases(c) if pd.Timestamp(ln.released) >= DENSE_FROM]
        risk = pd.concat([r for r in rs if len(r)])
        risks[c] = risk
        risk["cap_q"] = risk.groupby("release")["cap"].transform(lambda s: pd.qcut(s, 4, labels=False, duplicates="drop"))
        curves[c], ttu[c] = {}, {}
        for qi, g in risk.groupby("cap_q"):
            F = turnbull(g["lo"].to_numpy(float), g["hi"].to_numpy(float), HORIZON_DAYS)
            label = ["smallest 25%", "Q2", "Q3", "largest 25%"][int(qi)]
            curves[c][label] = F
            ttu[c][label] = {"nodes": len(g), "upgraded_share": float(g["event"].mean()), "median_days": median_day(F),
                             "upgraded_by_90d": float(F[90]), "upgraded_by_180d": float(F[180]),
                             "upgraded_by_365d": float(F[-1])}
        F = turnbull(risk["lo"].to_numpy(float), risk["hi"].to_numpy(float), HORIZON_DAYS)
        censored_left = int((~risk["event"]).sum())
        ttu[c]["all"] = {"nodes": len(risk), "releases": sorted(risk["release"].unique().tolist()),
                         "median_days": median_day(F), "upgraded_by_90d": float(F[90]),
                         "upgraded_by_180d": float(F[180]), "upgraded_by_365d": float(F[-1]),
                         "not_observed_upgrading": censored_left,
                         "interval_width_le_2d_share": float(((risk["hi"] - risk["lo"]) <= 2)[risk["event"]].mean())}
        print(f"{c} time to upgrade: {json.dumps(ttu[c], default=str)}")
    fig_time_to_upgrade(curves)
    out["time_to_upgrade"] = ttu

    h = hazard_model(risks["LND"])
    print(h.round(3).to_string())
    table_hazard(h)
    out["hazard_lnd"] = h.reset_index().rename(columns={"index": "covariate"}).to_dict(orient="records")

    ev = upgrade_events(p)
    out["waves"] = {c: waves(ev, p, c) for c in CLIENTS}
    out["waves_fleet_lnd"] = waves(upgrade_events(p_all[p_all["fleet"]]), p_all[p_all["fleet"]], "LND")["waves"][:5]
    out["platform_share"] = {c: platform_share(ev, c, "2025-06-01") for c in CLIENTS}
    out["platform_lines"] = {c: platform_lines(p, c) for c in CLIENTS}
    print("line changes after platform releases:", out["platform_lines"])
    for c in CLIENTS:
        print(f"{c} waves (p99 = {out['waves'][c]['threshold_p99']:.0f}/day):")
        for w in out["waves"][c]["waves"][:8]:
            print("  ", w)
        print(f"{c} upgrades after platform releases: {out['platform_share'][c]}")
    fig_waves(ev, pd.DatetimeIndex(sorted(p_all["date"].unique())))

    (DATA_DIR / "upgrade_dynamics.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("-> data/upgrade_dynamics.json, figures fig1/fig3/fig4/fig5, tables/table_hazard.tex")
    return 0


if __name__ == "__main__":
    sys.exit(main())
