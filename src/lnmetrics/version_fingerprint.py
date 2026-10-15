"""
version_fingerprint.py — which software release could have produced a node's announced feature bits.

Companion to client_fingerprint.py, which decides the implementation. This module only answers: "given the client,
which release lines are consistent with these node_announcement bits?" It never changes a client label.

Data: ln_release_features.json (next to this file), one entry per release line — a run of releases whose default
node_announcement bits are identical, so gossip cannot tell them apart. Per line: default bits, bits an operator
can add (options, flags, plugins, bLIP custom bits) and default bits an operator can remove, each cited to the
source file at the release tag. Frozen for this paper at rules_version v1.1-2026-10-15 (v1 bits; release dates =
publication dates).

Two answers per node:
  strict  every line consistent with the bits under any non-developer configuration, released by `as_of`:
              default - removable  ⊆  bits  ⊆  default ∪ optional_add
          Contains the running line under any non-developer configuration (validated: 99.99% of node-days of CLN
          nodes whose alias states the version)
          but wide when options let an old line imitate a newer one.
  likely  the consistent line(s) needing the fewest non-default bits (added + removed). Exact on 98% of the same
          node-days; the misses are a 24.05 node with the onion-messages option (indistinguishable from 24.08), two
          nodes with switched-off options and an rc build (data/validation.json).

Limits: never a patch version (e.g. CLN 26.06.7 vs 26.06.8 advertise identical bits); a node that upgraded but
has not re-announced still shows its old bits; developer overrides and forks can imitate anything; bits seen
before a line's release date are reported as a pre-release build.

Usage:
    from lnmetrics.version_fingerprint import infer_version
    v = infer_version("LND", [0, 5, 7, 8, 12, 14, 17, 23, 25, 27, 31, 35, 45, 55, 261, 2023], as_of="20261007")
    v.display   # "LND 0.20"     v.low / v.high  # "0.20.0" / "0.20.5"
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

TABLE_PATH = Path(__file__).with_name("ln_release_features.json")


@dataclass(frozen=True)
class Line:
    client: str
    index: int
    label: str
    first: str
    last: str
    released: str          # YYYYMMDD
    default: frozenset
    optional_add: frozenset
    removable: frozenset


@dataclass(frozen=True)
class VersionInference:
    low: Optional[str]         # first release of the oldest consistent line, e.g. "0.18.0"
    high: Optional[str]        # last known release of the newest consistent line, e.g. "0.19.3"
    likely: Optional[str]      # label of the most likely line (or a span of tied lines), e.g. "0.18"
    display: Optional[str]     # strict range for display, e.g. "LND 0.18–0.19"; None when unrecognised
    basis: str                 # human-readable reason
    status: str                # "ok" | "pre-release" | "unrecognised"


def _date(d: Optional[str]) -> Optional[str]:
    return d.replace("-", "") if d else None


@lru_cache(maxsize=1)
def _table() -> Tuple[str, Dict[str, List[Line]]]:
    raw = json.loads(TABLE_PATH.read_text(encoding="utf-8"))
    lines = {}
    for client, spec in raw["implementations"].items():
        lines[client] = [Line(client, i, l["line"], l["first"], l["last"], _date(l["released"]),
                              frozenset(l["default"]), frozenset(l["optional_add"]), frozenset(l["removable"]))
                         for i, l in enumerate(spec["lines"])]
    return raw["rules_version"], lines


VERSION_RULES_VERSION = _table()[0]
CLIENTS = tuple(_table()[1])


def lines(client: str) -> List[Line]:
    return _table()[1].get(client, [])


def line_index(client: str, release: Optional[str]) -> Optional[int]:
    """Index of the line containing a release string produced by infer_version (its `low` or `high`)."""
    for ln in lines(client):
        if release in (ln.first, ln.last):
            return ln.index
    return None


def _span(ls: List[Line]) -> str:
    if len(ls) == 1:
        return ls[0].label
    return f"{ls[0].label.split('–')[0]}–{ls[-1].label.split('–')[-1]}"


def _consistent(bits: frozenset, ln: Line) -> bool:
    return (ln.default - ln.removable) <= bits <= (ln.default | ln.optional_add)


def _cost(bits: frozenset, ln: Line) -> int:
    return len(bits - ln.default) + len(ln.default - bits)


def _fmt(b: Iterable[int]) -> str:
    return ", ".join(map(str, sorted(b)))


@lru_cache(maxsize=65536)
def _infer(client: str, bits: frozenset, as_of: Optional[str]) -> Optional[VersionInference]:
    all_lines = lines(client)
    if not all_lines:
        return None
    cands = [ln for ln in all_lines if _consistent(bits, ln)]
    if not cands:
        return VersionInference(None, None, None, None,
                                f"feature set matches no {client} release (table {VERSION_RULES_VERSION})", "unrecognised")
    released = [ln for ln in cands if as_of is None or ln.released <= as_of]
    if not released:
        ln = cands[0]
        return VersionInference(ln.first, ln.last, ln.label, f"{client} {ln.label} (pre-release)",
                                f"{client} {ln.label} bits seen before its release on {ln.released}: pre-release build",
                                "pre-release")
    best = min(_cost(bits, ln) for ln in released)
    likely = [ln for ln in released if _cost(bits, ln) == best]
    ref = likely[-1]
    basis = f"matches {client} {_span(likely)} defaults"
    if bits - ref.default:
        basis += f" + options {_fmt(bits - ref.default)}"
    if ref.default - bits:
        basis += f" − switched off {_fmt(ref.default - bits)}"
    if len(released) > len(likely):
        basis += f"; {_span(released)} possible with non-default options"
    return VersionInference(released[0].first, released[-1].last, _span(likely),
                            f"{client} {_span(released)}", basis, "ok")


def infer_version(client: str, feature_bits: Optional[Iterable[int]],
                  as_of: Optional[str] = None) -> Optional[VersionInference]:
    """Release-line range for `client` from node_announcement bits seen on `as_of` (YYYYMMDD or YYYY-MM-DD;
    None = ignore release dates). Returns None for clients without a release table (e.g. "Unknown")."""
    if client not in CLIENTS:
        return None
    bits = frozenset(int(b) for b in (feature_bits if feature_bits is not None else []))
    return _infer(client, bits, _date(as_of))


@lru_cache(maxsize=262144)
def line_indices(client: str, bits: frozenset, as_of: Optional[str]) -> Tuple[int, int, int, int]:
    """The same inference as infer_version, as positions in lines(client):
    (strict_lo, strict_hi, likely_lo, likely_hi); -1 everywhere when the set matches no line.
    A pre-release set returns its first consistent line for all four."""
    cands = [ln for ln in lines(client) if _consistent(bits, ln)]
    if not cands:
        return -1, -1, -1, -1
    released = [ln for ln in cands if as_of is None or ln.released <= as_of]
    if not released:
        i = cands[0].index
        return i, i, i, i
    best = min(_cost(bits, ln) for ln in released)
    likely = [ln for ln in released if _cost(bits, ln) == best]
    return released[0].index, released[-1].index, likely[0].index, likely[-1].index


@lru_cache(maxsize=65536)
def consistent_clients(bits: frozenset) -> Tuple[str, ...]:
    """Clients with at least one release line that can produce these bits (release dates ignored)."""
    return tuple(c for c in CLIENTS if any(_consistent(bits, ln) for ln in lines(c)))


@lru_cache(maxsize=65536)
def is_exact_default(client: str, bits: frozenset) -> bool:
    """True when the bits equal the default set of one of the client's lines."""
    return any(bits == ln.default for ln in lines(client))
