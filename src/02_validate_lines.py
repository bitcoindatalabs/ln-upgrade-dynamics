"""
02_validate_lines.py — RQ1: how accurately can a node's client and release line be read from gossip?

Ground truths, neither used by the rules (src/lnmetrics/client_fingerprint.py, version_fingerprint.py):

  GT-client   self-identifying aliases ("…[LND]", "…-CLN", "c-lightning", "eclair", "ldk-node", …), evaluated per
              node on the latest panel day where it has channels and its alias still self-identifies. LND's default
              alias (pubkey prefix) is excluded — the rules use it.
  GT-version  aliases that state the running version:
                CLN  developer builds put it in the default alias (ADJECTIVENOUN-v23.08[-modded]); the alias
                     follows the binary, so it is current on every node-day it is announced
                LND  operator-set aliases naming an LND version (few; set by hand, so they can go stale)
              Graded per announced node-day: does the strict range contain the stated line, is the likely line exact?

Also, on live nodes (src/lnmetrics/panel.py): share of node-days per client and year whose strict range spans more
than one line, whose set matches no line (unrecognised), or which show a line before its release (pre-release).

Consistency checks that need no ground truth, for LND as well as CLN:
  downgrades   operators rarely go back to an older release, so a noisy inference would show many line decreases
               between consecutive observations of a live node; we count decreases against increases
  pre-release  a line assigned the wrong bits would show nodes on it long before its release; we count the nodes
               seen on each line before its publication against those seen in its first 90 days

Outputs
  data/validation.json
  paper/tables/table_validation.tex
  paper/figures/fig2_version_validation.pdf    stated vs inferred line, CLN aliases (node-days)

Usage:  python src/02_validate_lines.py
"""

import json
import os
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_DIR, FIGURES_DIR, TABLES_DIR  # noqa: E402
from lnmetrics import panel as pn  # noqa: E402
from lnmetrics import version_fingerprint as vf  # noqa: E402
from lnmetrics.client_fingerprint import KNOWN_OPERATOR_CLIENTS, RULES_VERSION  # noqa: E402

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CLIENTS = ["LND", "CLN", "Eclair", "LDK"]
ALIAS_PATTERNS = {
    "CLN": r"(?<![a-z])(?:cln|c-?lightning|core-?lightning|corelightning)(?![a-z])",
    "Eclair": r"(?<![a-z])eclair",          # word start: excludes pastry names (framboiseclair, …)
    "LDK": r"(?<![a-z])ldk(?![a-z])|ldk[-_ ]?(?:node|server)",
    "LND": r"(?<![a-z])lnd(?![a-z])",
}
CLN_VERSION_ALIAS = re.compile(r"^[A-Z]+-v(\d+\.\d+(?:\.\d+)*(?:rc\d+)?)")
LND_VERSION_ALIAS = re.compile(r"(?i)(?<![a-z])lnd[ _-]?v?(0\.\d+(?:\.\d+)?)")
OWN_NODE_PREFIX = os.environ.get("VANTAGE_NODE_PREFIX", "")   # pubkey prefix of the vantage LND node (optional)

plt.rcParams.update({"font.family": "serif", "font.size": 8.5, "axes.titlesize": 9, "xtick.labelsize": 7,
                     "ytick.labelsize": 7, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})


# ---------------------------------------------------------------------------------------
# GT-client
# ---------------------------------------------------------------------------------------
def client_anchors(dates) -> pd.DataFrame:
    rows = {}
    for d in dates:
        p = pn.read_day(d, ["pub_key", "alias", "client", "client_confidence", "n_channels", "ann_observed"])
        p = p[(p["n_channels"] > 0) & p["ann_observed"] & ~p["pub_key"].isin(KNOWN_OPERATOR_CLIENTS)]
        a = p["alias"].fillna("").str.lower()
        truth = pd.Series(None, index=p.index, dtype=object)
        hits = pd.Series(0, index=p.index)
        for c, pat in ALIAS_PATTERNS.items():
            h = a.str.contains(pat, regex=True)
            truth[h] = c
            hits += h
        sel = p[(hits == 1) & truth.notna()].assign(truth=truth)
        for r in sel.itertuples(index=False):
            rows[r.pub_key] = {"pub_key": r.pub_key, "alias": r.alias, "truth": r.truth, "pred": r.client,
                               "confidence": r.client_confidence, "date": d}
    return pd.DataFrame(rows.values())


def prf(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for c in CLIENTS:
        tp = ((df["truth"] == c) & (df["pred"] == c)).sum()
        fp = ((df["truth"] != c) & (df["pred"] == c)).sum()
        fn = ((df["truth"] == c) & (df["pred"] != c)).sum()
        out.append({"client": c, "n": int((df["truth"] == c).sum()),
                    "precision": tp / (tp + fp) if tp + fp else np.nan,
                    "recall": tp / (tp + fn) if tp + fn else np.nan,
                    "unknown": int(((df["truth"] == c) & (df["pred"] == "Unknown")).sum())})
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------------------
# GT-version
# ---------------------------------------------------------------------------------------
def version_anchors() -> pd.DataFrame:
    cols = ["date", "pub_key", "alias", "client", "line_lo", "line_hi", "likely_lo", "likely_hi", "line_status",
            "ann_observed", "n_channels"]
    p = pn.load(cols, where=lambda p: p["ann_observed"] & p["alias"].fillna("").str.contains(
        r"^[A-Z]+-v\d|(?i:(?<![a-z])lnd[ _-]?v?0\.\d)", regex=True))
    rows = []
    for r in p.itertuples(index=False):
        m = CLN_VERSION_ALIAS.match(r.alias or "")
        stated_client = "CLN" if m else "LND"
        if not m:
            m = LND_VERSION_ALIAS.search(r.alias or "")
            if not m:
                continue
        stated = pn.line_of_version(stated_client, m.group(1))
        rows.append({**r._asdict(), "stated_client": stated_client, "stated_version": m.group(1),
                     "stated_line": stated})
    v = pd.DataFrame(rows)
    v["client_ok"] = v["client"] == v["stated_client"]
    v["in_strict"] = v["client_ok"] & (v["line_lo"] <= v["stated_line"]) & (v["stated_line"] <= v["line_hi"])
    v["likely_exact"] = v["client_ok"] & (v["likely_lo"] == v["stated_line"]) & (v["likely_hi"] == v["stated_line"])
    v["likely_contains"] = v["client_ok"] & (v["likely_lo"] <= v["stated_line"]) & (v["stated_line"] <= v["likely_hi"])
    return v


def wilson(k: int, n: int, z: float = 1.96):
    """95% Wilson score interval for a proportion k/n."""
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return float(c - h), float(c + h)


def version_summary(v: pd.DataFrame) -> dict:
    out = {}
    for c, g in v.groupby("stated_client"):
        g = g[g["stated_line"] >= 0]
        per_node = g.groupby(["pub_key", "stated_line"]).agg(exact=("likely_exact", "mean"), strict=("in_strict", "mean"))
        k, n = int((per_node["exact"] == 1).sum()), len(per_node)
        out[c] = {"nodes": int(g["pub_key"].nunique()), "node_days": len(g), "lines": int(g["stated_line"].nunique()),
                  "client_correct": float(g["client_ok"].mean()), "strict_contains": float(g["in_strict"].mean()),
                  "likely_exact": float(g["likely_exact"].mean()), "likely_contains": float(g["likely_contains"].mean()),
                  "node_lines": n, "node_lines_all_exact": k, "node_lines_all_exact_ci95": wilson(k, n),
                  "node_lines_strict_always": int((per_node["strict"] == 1).sum()),
                  "largest_operator_share": float(g.groupby("pub_key").size().max() / len(g))}
        miss = g[~g["likely_exact"]]
        out[c]["misses"] = (miss.groupby(["stated_version", "client", "likely_lo", "likely_hi", "line_status"])
                                .size().sort_values(ascending=False).head(10).reset_index(name="node_days")
                                .to_dict(orient="records"))
    return out


def own_node_timeline() -> list:
    """Inferred line of the vantage node itself, at every change (checked against its operator's upgrade log)."""
    if not OWN_NODE_PREFIX:
        return []
    p = pn.load(["date", "pub_key", "client", "likely_lo", "line_status"],
                where=lambda p: p["pub_key"].str.startswith(OWN_NODE_PREFIX))
    p = p[p["likely_lo"] != p["likely_lo"].shift()]
    return [{"first_day": r.date, "client": r.client, "line": pn.line_label(r.client, int(r.likely_lo)),
             "status": r.line_status} for r in p.itertuples(index=False)]


# ---------------------------------------------------------------------------------------
# Ambiguity on live nodes
# ---------------------------------------------------------------------------------------
def ambiguity() -> pd.DataFrame:
    p = pn.load(["date", "client", "client_confidence", "line_lo", "line_hi", "likely_lo", "likely_hi",
                 "line_status", "live_cap_14"],
                where=lambda p: pn.live(p) & p["client"].isin(CLIENTS))
    p["year"] = p["date"].str[:4]
    has = p["client_confidence"].isin(["high", "operator"])
    g = p.assign(versioned=has,
                 unrecognised=has & (p["line_status"] == "unrecognised"),
                 prerelease=has & (p["line_status"] == "pre-release"),
                 strict_multi=has & (p["line_lo"] >= 0) & (p["line_hi"] > p["line_lo"]),
                 likely_multi=has & (p["likely_lo"] >= 0) & (p["likely_hi"] > p["likely_lo"]))
    t = g.groupby(["client", "year"])[["versioned", "unrecognised", "prerelease", "strict_multi", "likely_multi"]].mean()
    t["node_days"] = g.groupby(["client", "year"]).size()
    return t.reset_index()


def consistency() -> dict:
    """Line decreases vs increases between consecutive observations of live nodes (managed fleet excluded), and nodes
    seen on each line before its publication vs in its first 90 days."""
    p = pn.load(["date", "pub_key", "client", "client_confidence", "likely_lo", "line_status", "live_cap_14", "fleet"],
                where=lambda p: pn.live(p) & p["client"].isin(["LND", "CLN"]) & ~p["fleet"]
                & p["client_confidence"].isin(["high", "operator"]) & (p["likely_lo"] >= 0))
    p["date"] = pd.to_datetime(p["date"])
    p = p.sort_values(["pub_key", "date"])
    prev = p.groupby("pub_key")["likely_lo"].shift()
    out = {}
    for c in ("LND", "CLN"):
        m = (p["client"] == c) & prev.notna()
        up, down = int((m & (p["likely_lo"] > prev)).sum()), int((m & (p["likely_lo"] < prev)).sum())
        lines = {}
        for ln in vf.lines(c):
            rel = pd.Timestamp(ln.released)
            if rel < pd.Timestamp("2023-11-01"):
                continue
            q = p[(p["client"] == c) & (p["likely_lo"] == ln.index)]
            pre = q[(q["date"] < rel) & (q["line_status"] == "pre-release")]["pub_key"].nunique()
            post = q[(q["date"] >= rel) & (q["date"] < rel + pd.Timedelta(days=90))]["pub_key"].nunique()
            lines[ln.label] = {"released": ln.released, "nodes_before_release": int(pre), "nodes_first_90d": int(post)}
        out[c] = {"increases": up, "decreases": down, "decrease_share": down / (up + down) if up + down else None,
                  "nodes_with_decrease": int(p.loc[m & (p["likely_lo"] < prev), "pub_key"].nunique()),
                  "lines": lines}
    return out


# ---------------------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------------------
def fig_validation(v: pd.DataFrame):
    g = v[(v["stated_client"] == "CLN") & (v["stated_line"] >= 0)]
    n = len(vf.lines("CLN"))
    m = np.zeros((n, n + 1))
    for r in g.itertuples(index=False):
        col = r.likely_lo if (r.client == "CLN" and r.likely_lo == r.likely_hi and r.likely_lo >= 0) else n
        m[r.stated_line, col] += 1
    used = sorted(set(g["stated_line"]) | set(g.loc[g["likely_lo"] >= 0, "likely_lo"]))
    rows = [i for i in used if m[i].sum() > 0]
    cols = used + ([n] if m[:, n].sum() else [])
    sub = m[np.ix_(rows, cols)]
    share = sub / sub.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots(figsize=(3.5, 3.0))
    ax.imshow(share, cmap="Blues", vmin=0, vmax=1)
    labels = [pn.line_label("CLN", i) for i in cols[:-1]] + (["other"] if cols[-1] == n else [pn.line_label("CLN", cols[-1])])
    ax.set_xticks(range(len(cols)), labels, rotation=60, ha="right")
    ax.set_yticks(range(len(rows)), [pn.line_label("CLN", i) for i in rows])
    def compact(x):
        if x >= 10000:
            return f"{x / 1000:.0f}k"
        return f"{x / 1000:.1f}k" if x >= 1000 else f"{int(x)}"
    for i in range(len(rows)):
        for j in range(len(cols)):
            if sub[i, j]:
                ax.text(j, i, compact(sub[i, j]), ha="center", va="center", fontsize=4.8,
                        color="white" if share[i, j] > 0.6 else "black")
    ax.set_xlabel("inferred (likely) line")
    ax.set_ylabel("line stated in alias")
    ax.spines[:].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig2_version_validation.pdf")
    plt.close(fig)


def table_validation(cp: pd.DataFrame, vs: dict, n_anchor: int):
    pct = lambda x, nd=1: "--" if pd.isna(x) else f"{100 * x:.{nd}f}"
    lines = [r"\begin{table}[t]", r"\centering\small",
             r"\caption{Validation against self-identifying aliases. Top: client labels of " + f"{n_anchor:,}" +
             r" nodes whose alias names their implementation. Bottom: release lines of CLN nodes whose alias states "
             r"the running version, graded on every announced node-day.}",
             r"\label{tab:validation}", r"\begin{tabular}{lrrr}", r"\toprule",
             r"Client & Nodes & Precision (\%) & Recall (\%) \\", r"\midrule"]
    for r in cp.itertuples(index=False):
        lines.append(f"{r.client} & {r.n:,} & {pct(r.precision)} & {pct(r.recall)} \\\\")
    s = vs["CLN"]
    lines += [r"\midrule", r"\multicolumn{3}{l}{CLN nodes / lines with a stated version} & "
              f"{s['nodes']:,} / {s['lines']} \\\\",
              r"\multicolumn{3}{l}{Node-days graded} & " + f"{s['node_days']:,} \\\\",
              r"\multicolumn{3}{l}{Strict range contains the stated line (\%)} & " + f"{pct(s['strict_contains'], 2)} \\\\",
              r"\multicolumn{3}{l}{Likely line equals the stated line (\%)} & " + f"{pct(s['likely_exact'])} \\\\",
              r"\multicolumn{3}{l}{Node--line pairs exact on every day} & " +
              f"{s['node_lines_all_exact']} / {s['node_lines']} \\\\",
              r"\multicolumn{3}{l}{\quad 95\% CI (\%)} & " + "[{:.0f}, {:.0f}] \\\\".format(
                  *(100 * x for x in s["node_lines_all_exact_ci95"])),
              r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (TABLES_DIR / "table_validation.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    dates = pn.panel_dates()
    monthly = sorted({d[:6]: d for d in dates}.values())        # last panel day of each month
    anchors = client_anchors(monthly)
    cp = prf(anchors)
    print("GT-client (rules", RULES_VERSION + "):")
    print(cp.to_string(index=False))
    wrong = anchors[(anchors["truth"] != anchors["pred"]) & (anchors["pred"] != "Unknown")]
    print(f"misclassified (excl. Unknown): {len(wrong)}")
    print(wrong[["alias", "truth", "pred", "confidence"]].head(20).to_string(index=False))

    v = version_anchors()
    vs = version_summary(v)
    print("GT-version:", json.dumps({c: {k: x for k, x in s.items() if k != "misses"} for c, s in vs.items()}, indent=1))
    for c, s in vs.items():
        print(c, "misses:", s["misses"])

    own = own_node_timeline()
    print("vantage node, inferred line at each change:", own)

    amb = ambiguity()
    print(amb.to_string(index=False))

    cons = consistency()
    print("consistency:", json.dumps(cons, indent=1))

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    fig_validation(v)
    table_validation(cp, vs, len(anchors))
    out = {"client_rules_version": RULES_VERSION, "version_rules_version": vf.VERSION_RULES_VERSION,
           "gt_client": {"anchors": len(anchors), "by_client": cp.to_dict(orient="records"),
                         "misclassified": wrong[["alias", "truth", "pred", "confidence"]].to_dict(orient="records")},
           "gt_version": vs, "own_node": own, "ambiguity_live": amb.to_dict(orient="records"),
           "consistency": cons}
    (DATA_DIR / "validation.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("-> data/validation.json, tables/table_validation.tex, figures/fig2_version_validation.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
