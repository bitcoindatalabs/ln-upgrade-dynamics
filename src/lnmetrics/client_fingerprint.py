"""
client_fingerprint.py — Lightning implementation inference from public gossip (rules v4).

Signals, strongest first:
  1. Operator attribution for nodes whose implementation is known from who runs them.
  2. node_announcement feature bits (implementation-specific bits)
       LND    : 2023 (script-enforced-lease) or 31 (amp)       — LND-only features
       Eclair : 37, or 29 together with 61 (29 alone is option_dual_fund, which CLN also advertises;
                sets carrying 51, 65 or 561 are impossible for Eclair and fall through)
       CLN    : 11 together with 39/43 and 5 — every CLN release sets 5 (upfront_shutdown_script)
       Eclair : 11 together with 39/43 without 5 — Eclair never sets 5 by default; before 2025 Eclair
                (incl. ACINQ) advertised none of 37/61
       LDK    : 39/43/63 without 11
  3. Release-table match: the bits are consistent with release lines of exactly one implementation
     (ln_release_features.json). Recovers old releases that predate the bits above, e.g. LND 0.8–0.11
     ([9,13], [0,5,7,9,13,15,17]) and CLN 0.8–23.x without 39/43. Labelled "high": no other
     implementation's release can produce the set. It also corrects the CLN/Eclair/LDK bit rules when the
     rule's implementation has no release that produces the set and exactly one other implementation does
     (e.g. pre-2025 Eclair sets with bit 5, such as a node aliased "eclair-low-fee"); the LND-only and
     Eclair-only bits are never overridden.
  4. LND defaults: color #3399ff, alias == pubkey[:20].
  5. Modal cltv_expiry_delta of the node's channel_updates (client defaults: LND 80/40, CLN 34,
     Eclair 144, LDK 72) — weak on its own because operators override it. An empty feature set is never
     labelled LDK: every LDK release announces features.

Steps 1, 2, 4 and 5 are the rules v4 of paper 01 (github.com/bitcoindatalabs/ln-client-diversity, arXiv:2610.20952v2,
Table I there); step 3, the release-table match, is new in this paper. Changes from v3 (2026-10-06): CLN/Eclair split
on bit 5 instead of keysend (55), so CLN with keysend disabled stays CLN; the 29+61 exclusion; empty set + CLTV 72 →
Unknown; release-table step added.

Returns (client, confidence, reason); confidence in {"operator", "high", "medium", "low"}.

Scope: public (announced) nodes only. Implementations used mostly behind unannounced channels
(LDK in wallets/services, Eclair in Phoenix) are under-represented in any gossip-based share.
"""

from typing import Iterable, Optional, Tuple

from .version_fingerprint import consistent_clients, is_exact_default

LND_ONLY = {2023, 31}
NOT_ECLAIR = {51, 65, 561}

# Operator attribution: nodes whose implementation is known from who runs them, used when the
# feature set alone is ambiguous.
KNOWN_OPERATOR_CLIENTS = {
    # Block maintains LDK; its routing nodes advertise an LDK-like set with non-default CLTV 144.
    "027100442c3b79f606f80f322d98d499eefcb060599efc5d4ecb00209c2cb54190": ("LDK", "block-iad-1: Block (LDK maintainer)"),
    "028a33a72ecb09967e67b08a04179fce74730bbc4cb2544c7d6876d20c6450c5eb": ("LDK", "block-pdx-1: Block (LDK maintainer)"),
    # ACINQ develops Eclair; its node advertised a CLN-like set before 2025 (no 37/61)
    "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f": ("Eclair", "ACINQ (Eclair developer)"),
}
CLTV_DEFAULT = {34: "CLN", 72: "LDK", 144: "Eclair", 80: "LND", 40: "LND"}

RULES_VERSION = "v4-2026-10-14"


def _lnd_defaults(color: Optional[str], alias: Optional[str], pub_key: Optional[str]) -> bool:
    return color == "#3399ff" or bool(alias and pub_key and alias == pub_key[:20])


def classify_node(feature_bits: Optional[Iterable[int]], color: Optional[str] = None,
                  alias: Optional[str] = None, pub_key: Optional[str] = None,
                  cltv_mode: Optional[float] = None) -> Tuple[str, str, str]:
    if pub_key in KNOWN_OPERATOR_CLIENTS:
        client, note = KNOWN_OPERATOR_CLIENTS[pub_key]
        return client, "operator", f"operator-attributed: {note}"

    bits = frozenset(int(b) for b in (feature_bits if feature_bits is not None else []))

    if bits:
        if bits & LND_ONLY:
            return "LND", "high", "lnd-only feature bit (2023 lease / 31 amp)"
        if (37 in bits or {29, 61} <= bits) and not bits & NOT_ECLAIR:
            return "Eclair", "high", "eclair feature bits (37, or 29+61)"
        match = consistent_clients(bits)
        rule = None
        if 11 in bits and bits & {39, 43}:
            rule = ("CLN", "high", "cln feature set (11 + 39/43 + 5)") if 5 in bits else \
                   ("Eclair", "medium", "11 + 39/43 without 5: eclair")
        elif bits & {39, 43, 63} and 11 not in bits:
            # Without cltv 72 (LDK default) or gossip-queries (7) this is a guess by elimination
            rule = ("LDK", "high" if cltv_mode == 72 and 7 in bits else "medium", "ldk-like feature set (39/43/63 w/o 11)")
        if rule is not None:
            if rule[0] not in match and len(match) == 1:
                # the rule's client has no release that produces this set; exactly one other client does
                return match[0], "high", f"only {match[0]} releases produce this set (overrides: {rule[2]})"
            return rule
        if len(match) == 1:
            c = match[0]
            how = "exact defaults" if is_exact_default(c, bits) else "defaults + options"
            return c, "high", f"only {c} releases produce this set ({how})"
        if _lnd_defaults(color, alias, pub_key):
            return "LND", "medium", "lnd default color/alias, generic feature set"
        if cltv_mode in CLTV_DEFAULT:
            return CLTV_DEFAULT[int(cltv_mode)], "low", f"generic feature set, cltv default {int(cltv_mode)}"
        return "Unknown", "low", "generic feature set"

    # No node_announcement features (unannounced metadata): policy defaults only
    if _lnd_defaults(color, alias, pub_key):
        return "LND", "low", "no features; lnd default color/alias"
    if cltv_mode in CLTV_DEFAULT and int(cltv_mode) != 72:
        return CLTV_DEFAULT[int(cltv_mode)], "low", f"no features; cltv default {int(cltv_mode)}"
    return "Unknown", "low", "no features"
