"""
advisories.py — security advisories whose fix boundary can be seen in gossip (LND, CLN, Eclair; 2023–2026).

Each entry names the release lines (labels in ln_release_features.json) that are
  affected  wholly affected: every release in the line is vulnerable
  mixed     the fix (or a backport) lands inside the line: some releases are vulnerable, some are not
Every later line is wholly fixed. "LINE" entries have no mixed line; "PARTIAL" entries do, and give bounds.

Grouped rows: advisories with the same implementation, disclosure date and line boundary are one entry
(e.g. the six Lightning Labs advisories of 2026-08-11 fixed in LND 0.19.0).

Excluded: fixes inside the newest line at the cutoff (patch releases, not visible in gossip), advisories that
affect only non-default configurations, and LDK rows (one line, 0.0.120–0.1, spans 2024-01 to 2025-12).

Dates: `disclosed` = first public statement that the vulnerability existed; `fixed` = release of the first fixed
version. Sources: release notes, Lightning Labs' advisory index, Delving Bitcoin and author write-ups (cited in the
paper's advisory table).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from . import version_fingerprint as vf


@dataclass(frozen=True)
class Advisory:
    key: str
    client: str
    title: str
    disclosed: str            # YYYY-MM-DD
    fixed: str                # YYYY-MM-DD, first fixed release
    fixed_in: str             # version string
    affected: Tuple[str, ...]  # wholly affected line labels
    mixed: Tuple[str, ...] = ()
    severity: str = ""
    count: int = 1            # advisories grouped in this entry

    @property
    def kind(self) -> str:
        return "PARTIAL" if self.mixed else "LINE"

    def indices(self) -> Tuple[set, set]:
        lab = {ln.label: ln.index for ln in vf.lines(self.client)}
        return {lab[x] for x in self.affected}, {lab[x] for x in self.mixed}


def _below(client: str, label: str) -> Tuple[str, ...]:
    """Every line before `label`."""
    ls = vf.lines(client)
    i = next(ln.index for ln in ls if ln.label == label)
    return tuple(ln.label for ln in ls[:i])


L, C, E = "LND", "CLN", "Eclair"

ADVISORIES = [
    # --- LND ---------------------------------------------------------------------------------------------------------
    Advisory("lnd-2023-fakechan", L, "Fake channel DoS", "2023-08-23", "2023-03-29", "0.16.0",
             _below(L, "0.15.1–0.17"), ("0.15.1–0.17",), "funds may be at risk"),
    Advisory("lnd-2023-replcycle", L, "Replacement cycling (CVE-2023-40233)", "2023-10-16", "2023-10-03", "0.17.0",
             _below(L, "0.15.1–0.17"), ("0.15.1–0.17",), "loss of funds"),
    Advisory("lnd-2023-chanupdate-oom", L, "Premature channel_update OOM", "2023-12-21", "2021-11-17", "0.14.0",
             _below(L, "0.14–0.15.0"), (), "crash"),
    Advisory("lnd-2023-chanupdate-sig", L, "channel_update signature after rate limit", "2023-12-21", "2022-06-23",
             "0.15.0", _below(L, "0.14–0.15.0"), ("0.14–0.15.0",), "gossip censorship"),
    Advisory("lnd-2024-onionbomb", L, "Onion bomb (CVE-2024-38359)", "2024-06-18", "2023-10-03", "0.17.0",
             _below(L, "0.15.1–0.17"), ("0.15.1–0.17",), "high (OOM)"),
    Advisory("lnd-2024-irrevocable", L, "Irrevocable fees / update_fee breach fee-burn", "2024-12-10", "2024-09-12",
             "0.18.3", _below(L, "0.18"), ("0.18",), "high (loss of funds)"),
    Advisory("lnd-2025-failback", L, "Excessive HTLC failback", "2025-03-04", "2024-05-30", "0.18.0",
             _below(L, "0.18"), (), "high (HTLC theft)"),
    Advisory("lnd-2025-gtsfilter", L, "gossip_timestamp_filter goroutine DoS", "2025-07-22", "2024-09-12", "0.18.3",
             _below(L, "0.18"), ("0.18",), "low (DoS)"),
    Advisory("lnd-2025-sweeper", L, "Replacement stalling, failback #2, infinite inbox", "2025-12-04", "2025-05-22",
             "0.19.0", _below(L, "0.19"), (), "critical (theft); DoS", count=3),
    Advisory("lnd-2026-zerots", L, "Zero-timestamp gossip panic", "2026-06-18", "2026-02-12", "0.20.1",
             _below(L, "0.20"), ("0.20",), "low (crash)"),
    Advisory("lnd-2026-ll-batch", L, "Lightning Labs batch: gossip, peer and queue DoS", "2026-08-11", "2025-05-22",
             "0.19.0", _below(L, "0.19"), (), "low (DoS)", count=6),
    Advisory("lnd-2026-sweepbudget", L, "HTLC first-stage sweep budget failure", "2026-08-11", "2025-05-22", "0.19.0",
             ("0.18",), (), "high (HTLC loss)"),
    Advisory("lnd-2026-closeconf", L, "Too few confirmations on cooperative close", "2026-08-13", "2026-02-12",
             "0.20.1", _below(L, "0.20"), ("0.20",), "revoked state after reorg"),
    Advisory("lnd-2026-gossipstall", L, "Gossip stall via malformed announcements", "2026-09-21", "2026-02-12",
             "0.20.1", ("0.19",), ("0.20",), "low (DoS)"),
    Advisory("lnd-2026-brontide", L, "Brontide write-allocation OOM", "2026-09-21", "2025-11-20", "0.20.0",
             _below(L, "0.20"), (), "low (DoS)"),
    # --- CLN ---------------------------------------------------------------------------------------------------------
    Advisory("cln-2023-fakechan", C, "Fake channel DoS", "2023-08-23", "2023-03-01", "23.02",
             _below(C, "0.12–23.02"), ("0.12–23.02",), "funds may be at risk"),
    Advisory("cln-2023-replcycle", C, "Replacement cycling (CVE-2023-40234)", "2023-10-16", "2023-09-12", "23.08.1",
             _below(C, "23.05–23.08"), ("23.05–23.08",), "loss of funds"),
    Advisory("cln-2023-invoice1", C, "BOLT11 parsing bugs, batch 1", "2023-12-08", "2023-03-01", "23.02",
             _below(C, "0.12–23.02"), ("0.12–23.02",), "low (crash)"),
    Advisory("cln-2023-invoice2", C, "BOLT11 parsing bugs, batch 2", "2023-12-08", "2023-11-28", "23.11",
             _below(C, "23.11"), (), "low (crash)"),
    Advisory("cln-2026-assert", C, "funding_created assertion DoS", "2026-05-16", "2025-09-02", "25.09",
             _below(C, "25.09–25.12"), (), "DoS"),
    Advisory("cln-2026-connectd", C, "connectd queue memory exhaustion", "2026-07-19", "2025-09-02", "25.09",
             _below(C, "25.09–25.12"), (), "DoS"),
    Advisory("cln-2026-gossipd", C, "gossipd unknown-SCID memory exhaustion", "2026-07-19", "2026-04-20", "26.04",
             _below(C, "26.04–26.06"), (), "DoS"),
    Advisory("cln-2026-pingflood", C, "Ping-flood OOM", "2026-08-25", "2025-09-02", "25.09",
             _below(C, "25.09–25.12"), (), "critical DoS"),
    # --- Eclair ------------------------------------------------------------------------------------------------------
    Advisory("eclair-2023-fakechan", E, "Fake channel DoS", "2023-08-23", "2023-06-19", "0.9.0",
             _below(E, "0.8–0.9"), ("0.8–0.9",), "funds at risk"),
    Advisory("eclair-2023-replcycle", E, "Replacement cycling (CVE-2023-40232)", "2023-10-16", "2023-06-19", "0.9.0",
             _below(E, "0.8–0.9"), ("0.8–0.9",), "loss of funds"),
    Advisory("eclair-2024-irrevocable", E, "Irrevocable fees", "2024-12-10", "2024-02-29", "0.10.0",
             _below(E, "0.10"), (), "loss of funds"),
    Advisory("eclair-2025-preimage", E, "Preimage extraction", "2025-09-23", "2025-03-11", "0.12.0",
             _below(E, "0.12"), (), "critical (theft)"),
    Advisory("eclair-2026-lnf", E, "LNF-2026-0001/0002 feature-bit and zlib DoS", "2026-09-24", "2026-05-21",
             "0.14.0", _below(E, "0.14"), (), "medium (DoS)", count=2),
]
