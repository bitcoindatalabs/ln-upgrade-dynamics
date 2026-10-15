# Advisory audit: LN security disclosures 2022-01-01 to 2026-10-14, and their gossip visibility

Audit date: 2026-10-14. Scope: LND, Core Lightning (CLN), Eclair and LDK (rust-lightning), plus the BTCPay 2.4.2 advisory, which affected LND deployments. Line definitions come from `python/automation/docs/ln_release_features/*.md` and `LN_DATA_LAKE_AND_FINDINGS.md` §3b.

**Counts.** The table below has **75 rows**: one per advisory per implementation. A batch release that fixed several bugs without per-bug write-ups counts as one row.

| Implementation | Rows | LINE | PARTIAL (of which weak) | PATCH | N/A |
|---|---|---|---|---|---|
| LND | 26 | 13 | 12 (2) | 1 | 0 |
| CLN | 14 | 5 | 5 (0) | 3 | 1 |
| Eclair | 10 | 4 | 2 (0) | 4 | 0 |
| LDK | 24 | 3 | 17 (13) | 4 | 0 |
| BTCPay (LND deployments) | 1 | 0 | 0 | 0 | 1 |
| **Total** | **75** | **25** | **36 (15)** | **12** | **2** |

**Formal identifiers are rare.**
- Only 5 CVEs exist across the four implementations: CVE-2022-44797, CVE-2022-39389 and CVE-2024-38359 (each with a GHSA, all LND), plus the replacement-cycling IDs CVE-2023-40231..40234. The replacement-cycling IDs are still RESERVED at MITRE and were never published.
- CLN, Eclair and LDK have published no GHSA in the window.
- Most disclosures are Delving Bitcoin or blog write-ups, changelog "Security" sections, or Lightning Labs' advisory page.

## Classification rules

The paper measures whether a node has upgraded past a fix, so the class asks one question: can we see that crossing in gossip?

- **LINE.** The first fixed release is the first release of a gossip-separable line, and the affected set is exactly a union of whole lines (for example "all lines before X", or exactly one line), with no backport into an earlier line. Crossing the fix shows up as a line change.
- **PARTIAL.** The fix boundary, or a backport, falls inside a line, but exposure can still be bounded:
  - lines that are wholly affected give a lower bound;
  - a wholly fixed separable line existing by 2026-10-14 gives an upper bound and a "definitely patched" state.
  - **PARTIAL (weak)** means the mixed line held most of the relevant population. Examples are the LDK 0.0.120–0.1.x line, which spans Jan 2024 to Oct 2026, and the LND 2022 fixes, whose wholly fixed line (0.18) shipped about 19 months later.
- **PATCH.** The fix sits inside the newest line, and no wholly fixed separable line exists by 2026-10-14. Gossip can only show "still on an older line", which is a lower bound on exposure, and cannot show the upgrade to the fix.
- **N/A.** The default configuration is not affected, or the fix is not in node software at all.

**Line starts used** (from §3b):
- **LND:** 0.14.0 · 0.15.1 (soft) · 0.18.0 · 0.19.0 (soft: bit 261 can be removed) · 0.20.0 · 0.21.0.
- **CLN:** 0.10.1 · 0.11 · 0.12 · 23.05 · 23.11 · 24.02 · 24.02.2 · 24.08 · 24.11 · 25.05 · 25.09 · 26.04.
- **Eclair:** 0.6 · 0.7 · 0.8 · 0.10 · 0.11 · 0.12 · 0.13 · 0.14.
- **LDK:** 0.0.113 · 0.0.116 · 0.0.117 · 0.0.120 · 0.2.0 · 0.2.2. Bits before 0.0.113 are not tabulated.

**Column legend:**
- "Reach" says who can be attacked:
  - **P** = any reachable or public node; only a peer connection is needed.
  - **CP** = the attacker needs a channel with the victim.
  - **Fwd** = routing (forwarding) nodes only.
  - **Pay** = the victim must pay or parse attacker data.
  - **Cfg** = only a non-default configuration or an exposed RPC is affected.
- "ITW" means known in-the-wild exploitation or a forced-offline event.
- Dates are UTC. "Disclosed" is the first public statement that a vulnerability existed; a later formal advisory is noted beside it.

## Table (sorted by public disclosure date)

| # | Disclosed | Impl | Identifier | Fix shipped | Affected | First fixed | Severity (as stated) | Description | Reach | ITW / offline | Class | Boundary reasoning | Src |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022-02-28 | LDK | 0.0.105 Security (2 issues) | same day | < 0.0.105 | 0.0.105 | DoS | Router panic on a crafted route hint; panic in `get_claimable_balances` | app-dependent | none reported | PARTIAL (weak) | Pre-0.0.113 lines are not tabulated; 0.0.113+ wholly fixed. No LDK public nodes of that age are expected in 2023-05+ | L1 |
| 2 | 2022-04-22 | CLN | Anchor revoked-HTLC aggregation (Teinturier) | 0.10.2, 2021-11-03 | < 0.10.2, experimental anchors only | 0.10.2 | "could be exploited to steal funds" | CLN failed to claim aggregated revoked HTLC txs | CP | none ("hasn't impacted any user") | PARTIAL | Fix is inside the 0.10.1–0.10.2 line; ≤0.10.0 wholly affected, 0.11+ wholly fixed. The secondary htlc_max signal (0.10.1 caps at 2^32-1 msat) separates 0.10.1 from 0.10.2, so it is effectively LINE. Experimental builds also announce extra bits (21, 39) | C1, O22a |
| 3 | 2022-07-01 | LDK | 0.0.109 Security | same day | < 0.0.109 | 0.0.109 | DoS | A crafted funding tx panics ChannelMonitor | CP | none reported | PARTIAL (weak) | As row 1 | L1 |
| 4 | 2022-09-12 | LDK | 0.0.111 Security (#1711) | same day | 0.0.107–0.0.110 | 0.0.111 | DoS | Panic on a block while awaiting a 0-conf funding tx | CP (0-conf) | none reported | PARTIAL (weak) | As row 1 | L1 |
| 5 | 2022-10-09 (incident); CVE/GHSA 2022-11-07 | LND | CVE-2022-44797 / GHSA-2chg-86hq-7w38 (btcd witness size) | 0.15.2 on 2022-10-10; 0.14.4 on 2022-10-14 | < 0.15.2 (btcd < 0.23.2) | 0.15.2; 0.14.4 (backport) | GitHub: critical | btcd rejected a block with a huge witness, so LND's chain sync stalled | all nodes (on-chain trigger) | **Yes: mainnet block on 2022-10-09 stalled unpatched nodes**; emergency hotfix | PARTIAL (weak) | Fix is inside the 0.15.1–0.17 line, and the backport puts 0.14.4 inside the 0.14–0.15.0 line too. Only ≤0.13 is wholly affected; 0.18+ is wholly fixed but arrived 2024-05 | N1, N2, N3, O22b |
| 6 | 2022-11-01 (incident); advisory 2022-11-17 | LND | CVE-2022-39389 / GHSA-hc82-w9v8-83pr (witness block parsing) | 0.15.4 and 0.14.5, 2022-11-01 | < 0.15.4 (btcd < 0.23.3) | 0.15.4; 0.14.5 | GitHub high; LL T1 High (CVSS 8.1) | A tx with more than 500k witness items failed to decode; nodes missed blocks and on-chain events | all nodes (on-chain trigger) | **Yes: mainnet block 761249 stalled unpatched nodes** (issue #7096) | PARTIAL (weak) | As row 5 | N1, N2, N4, O22c |
| 7 | 2023-03-03 (changelog); write-up 2023-08-23 | LDK | Fake channel DoS (#1988, Morehouse) | 0.0.114, 2023-03-03 | < 0.0.114 | 0.0.114 | DoS; funds at risk (node fell >144 blocks behind) | Unlimited unfunded channels or peers | P (accepts inbound) | none reported | PARTIAL | Fix is inside the 0.0.113–0.0.115 line; 0.0.116+ wholly fixed | L1, M1 |
| 8 | 2023-03-03 | LDK | 0.0.114 other Security (#2071, #2072) | same day | 0.0.107+ / 0.0.112+ | 0.0.114 | DoS | Second channel_ready panic; scorer divide-by-zero | CP | none reported | PARTIAL | As row 7 | L1 |
| 9 | 2023-04-24 | LDK | 0.0.115 Security (#2062) | same day | < 0.0.115 | 0.0.115 | Privacy | An intermediate hop could learn the final destination | Pay | none reported | PARTIAL | Fix is inside the 0.0.113–0.0.115 line; 0.0.116+ wholly fixed | L1 |
| 10 | 2023-07-21 | LDK | 0.0.116 Security (#2439) | same day | since 0-conf support, through 0.0.115 | 0.0.116 | DoS | Premature announcement_signatures on 0-conf channels causes a panic | CP | none reported | LINE | 0.0.116 is its own line (bit 1→0); the 0.0.113–0.0.115 line is wholly affected | L1 |
| 11 | 2023-08-23 | LND | Fake channel DoS (Morehouse) | 0.16.0, 2023-03-29 | < 0.16.0 | 0.16.0 | "funds may be at risk" | Mass fake pending channels degrade LND until it stops responding | P (accepts inbound) | none reported | PARTIAL | Fix is inside the 0.15.1–0.17 line; ≤0.15.0 wholly affected, 0.18+ wholly fixed. Secondary signal: CLTV delta 80 (≥0.16.1) implies fixed | M1 |
| 12 | 2023-08-23 | CLN | Fake channel DoS (Morehouse) | 23.02, 2023-03-01 | < 23.02 | 23.02 | "funds may be at risk"; connectd blocked | Fake-channel flood blocks connectd | P (accepts inbound) | none reported | PARTIAL | Fix is inside the 0.12–23.02 line; ≤0.11 wholly affected, 23.05+ wholly fixed (shipped before the disclosure) | M1, O23a |
| 13 | 2023-08-23 | Eclair | Fake channel DoS (Morehouse) | 0.9.0, 2023-06-19 | < 0.9.0 | 0.9.0 | "funds clearly at risk"; OOM on every restart | Fake-channel flood causes OOM | P (accepts inbound) | none reported | PARTIAL | Fix is inside the 0.8–0.9 line; ≤0.7 wholly affected, 0.10+ wholly fixed (2024-02). Weak secondary signal: the 45% htlc_max cap means ≥0.9 | M1, E1 |
| 14 | 2023-10-03 | LDK | 0.0.117 Security (#2606, #2587, #2623, #1924) | same day | ≤ 0.0.116 (anchors; reorg and coinbase cases) | 0.0.117 | "several loss-of-funds vulnerabilities" | Missed anchor HTLC claims, HTLC value spent as fee, reorg claim gap | CP | none reported | LINE | 0.0.117 starts a line (+55); all earlier lines wholly affected | L1 |
| 15 | 2023-10-16 | LDK | Replacement cycling, CVE-2023-40231 (RESERVED) | 0.0.118, 2023-10-23 (after disclosure) | < 0.0.118 | 0.0.118 (mitigation only) | loss of funds; mitigations "not robust" | HTLC-timeout replacement lets an attacker steal a forwarded HTLC | Fwd | not observed (Riard) | PARTIAL | Fix is inside the 0.0.117–0.0.119 line; ≤0.0.116 wholly affected, 0.0.120+ wholly fixed | R1, O23b, L1 |
| 16 | 2023-10-16 | Eclair | Replacement cycling, CVE-2023-40232 (RESERVED) | 0.9.0, 2023-06-19 | < 0.9.0 | 0.9.0 (mitigation only) | as row 15 | as row 15 | Fwd | not observed | PARTIAL | Fix is inside the 0.8–0.9 line; ≤0.7 affected, 0.10+ fixed | R1, O23b, E1 |
| 17 | 2023-10-16 | LND | Replacement cycling, CVE-2023-40233 (RESERVED) | Riard names 0.17.0 (2023-10-03); partial mitigations in 0.16.0 (#7448) and 0.16.1 (#7564) | < 0.17.0 (per Riard) | 0.17.0 (mitigation only) | as row 15 | as row 15 | Fwd | not observed | PARTIAL | Fix is inside the 0.15.1–0.17 line; ≤0.15.0 affected, 0.18+ fixed. The CLTV 40→80 default at 0.16.1 matches the #7564 mempool mitigation | R1, O23b, N5 |
| 18 | 2023-10-16 | CLN | Replacement cycling, CVE-2023-40234 (RESERVED) | 23.08.1, 2023-09-12 | < 23.08.1 | 23.08.1 (mitigation only) | as row 15 | as row 15 | Fwd | not observed | PARTIAL | Fix is inside the 23.05–23.08 line; ≤23.02 affected, 23.11+ fixed | R1, O23b |
| 19 | 2023-12-08 | CLN | Invoice parsing bugs, batch 1 (Morehouse, Gögge; reported Dec 2022) | 23.02, 2023-03-01 | < 23.02 | 23.02 | "relatively low" | Stack overflow, assertion and UB on a crafted BOLT11 | Pay | none | PARTIAL | Fix is inside the 0.12–23.02 line; 23.05+ wholly fixed | M2 |
| 20 | 2023-12-08 | CLN | Invoice parsing bugs, batch 2 | 23.11, 2023-11-28 | < 23.11 | 23.11 | "relatively low" (uninitialised memory) | Crafted BOLT11 crashes the node | Pay | none | LINE | 23.11 starts a line (+19; the wumbo option weakens this); all earlier lines affected | M2 |
| 21 | 2023-12-21 | LND | channel_update gossip bug 1 (Gögge): premature-update OOM | 0.14.0, 2021-11-17 | < 0.14.0 | 0.14.0 | crash, fund-loss risk | Unbounded buffer of premature channel_updates | P | none reported | LINE | 0.14.0 starts a line (+45, +2023); all earlier lines affected | D314, O24a |
| 22 | 2023-12-21 | LND | channel_update gossip bug 2: signature checked after the rate limit | 0.15.0, 2022-06-23 | < 0.15.0 | 0.15.0 | not rated | Invalid updates crowd out a victim's real updates (gossip censorship) | P | none reported | PARTIAL | Fix is inside the 0.14–0.15.0 line; ≤0.13 affected, 0.15.1+ fixed. Bit 55 (keysend) implies ≥0.15.0 | D314, O24a |
| 23 | 2024-01-08 | CLN | Channel-open race DoS (Morehouse) | 23.08, 2023-08-23 | 23.02–23.05.2 | 23.08 | "funds may be at risk"; crash in about 30 s | Race between the peer_connected hook and the open hits an assertion | P (accepts inbound) | none | PARTIAL | Upper bound only: the affected set spans the mixed 0.12–23.02 and 23.05–23.08 lines; ≤0.11 and 23.11+ are unaffected | D385, M3, O24b |
| 24 | 2024-01-17 | LDK | 0.0.120 Security (#2808, #2809) | same day | 0.0.117–0.0.119 | 0.0.120 | DoS | open_channel without channel_type causes a panic; funding-info reuse panic | CP | none reported | LINE | The affected set is exactly the 0.0.117–0.0.119 line; 0.0.120 starts a line (+25) | L1 |
| 25 | 2024-01-22 | LDK | 0.0.121 Security (#2842) | same day | 0.0.119–0.0.120 | 0.0.121 | DoS | Unwrap on a peer that never finished the handshake | P | none reported | PARTIAL (weak) | Affected set straddles two mixed lines (0.0.117–0.0.119 and 0.0.120–0.1); upper bound only; 0.2+ wholly fixed | L1 |
| 26 | 2024-05-08 | LDK | 0.0.123 Security (#3054) | same day | < 0.0.123 | 0.0.123 | DoS | Non-ASCII BOLT11 HRP causes an out-of-bounds panic | Pay | none reported | PARTIAL (weak) | Fix is inside the 0.0.120–0.1 line; ≤0.0.119 affected, 0.2+ fixed (2025-12) | L1 |
| 27 | 2024-06-18 (Morehouse); GHSA/LL 2024-06-20 | LND | CVE-2024-38359 / GHSA-9gxx-58q6-42p7 "Onion Bomb" | 0.17.0, 2023-10-03 | < 0.17.0 | 0.17.0 (no 0.16 backport) | GitHub high (CVSS 7.5); LL T3 Low | Unbounded onion payload causes OOM | P (an onion routed to the node) | none reported | PARTIAL | Fix is inside the 0.15.1–0.17 line; ≤0.15.0 affected, 0.18+ fixed (shipped before the disclosure). Bit 181 implies ≥0.17 | LL0, M4, D979, O24c |
| 28 | 2024-12-10 | LND | "Irrevocable fees" (Harding) = LL "update_fee Breach Fee-Burn Exploit" (LL 2026-08-11) | 0.18.3, 2024-09-12 | < 0.18.3 | 0.18.3 | LL T1 High | A revoked high-fee commitment burns the balance to fees; about 97% to the attacker with miner help | CP (attacker is the opener) | none reported | PARTIAL | Fix is inside the 0.18 line; ≤0.17 affected, 0.19+ fixed. Bit 2025 implies ≥0.18.4 | D1314, LL3 |
| 29 | 2024-12-10 | CLN | Irrevocable fees | n/a (default not vulnerable); 26.06.7 caps `--ignore-fee-limits` | only with `--ignore-fee-limits` | n/a | as row 28 | as row 28 | Cfg | none | N/A | Default configuration never affected | D1314 |
| 30 | 2024-12-10 | Eclair | Irrevocable fees | 0.10.0, 2024-02-29 | < 0.10.0 | 0.10.0 | as row 28 | as row 28 | CP | none | LINE | 0.10.0 starts a line (1→0, 7→6, 13→12) | D1314, E1 |
| 31 | 2024-12-10 | LDK | Irrevocable fees (#3045) | 0.0.123, 2024-05-08 (silent) | < 0.0.123 | 0.0.123 | as row 28 | as row 28 | CP | none | PARTIAL (weak) | Fix is inside the 0.0.120–0.1 line | D1314, L1 |
| 32 | 2025-01-15 | LDK | 0.1 Security: BOLT12 invoice overpay (#3535) and lightning-liquidity DoS | 0.1, 2025-01-15 | ≤ 0.0.125 | 0.1 | funds theft; DoS | Payer paid the invoice amount instead of the intended amount | Pay (wallets), LSPs | none reported | PARTIAL (weak) | 0.1 is inside the 0.0.120–0.1 line | L1 |
| 33 | 2025-01-15 (notes); write-up 2025-01-23 | LDK | Invalid claims liquidity griefing (Morehouse) | 0.1 | ≤ 0.0.125 (anchors) | 0.1 | funds lock-up | A loop `break` leaves aggregated claims invalid | Fwd | none reported | PARTIAL (weak) | As row 32 | L1, M5, D1400 |
| 34 | 2025-01-28 (notes); write-up 2025-01-29 | LDK | Duplicate HTLC force-close griefing (Morehouse) | 0.1.1, 2025-01-28 | ≤ 0.1.0 | 0.1.1 | force-closes all channels | Duplicate hash/amount HTLCs after a revoked commitment leave upstream HTLCs stuck | Fwd | none reported | PARTIAL (weak) | Fix is inside the 0.0.120–0.1 line; 0.2+ fixed | L1, M6, D1410 |
| 35 | 2025-03-04 (Morehouse); LL 2026-08-11 | LND | Excessive Failback = LL "Pending Commitment Excessive HTLC Failback Exploit" | 0.18.0, 2024-05-30 | < 0.18.0 | 0.18.0 | LL T1 High | Fails back an HTLC whose preimage is already known after a restart, enabling HTLC theft | Fwd | none reported | LINE | 0.18.0 starts a line (hard 9→8) | LL1, M7, D1493, O25a |
| 36 | 2025-04-30 | LDK | 0.1.3 Security (#3747, #3750) | same day | 0.1.0–0.1.2 | 0.1.3 | DoS | UTF-8 truncate panic in invoice_request | P (BOLT12 offers) | none reported | PARTIAL (weak) | Upper bound only (subset of the 0.0.120–0.1 line); 0.2+ fixed | L1 |
| 37 | 2025-05-23 | LDK | 0.1.4 Security (#3796) | same day | ≤ 0.1.3 | 0.1.4 | funds theft "in exceedingly rare cases" | Zero reserve on an anchor channel the LDK node funded lets a fee bump overdraw it | CP | none reported | PARTIAL (weak) | Fix is inside the 0.0.120–0.1 line | L1 |
| 38 | 2025-07-16 | LDK | 0.1.5 Security (#3933) | same day | ≤ 0.1.4 | 0.1.5 | reserve overdraw | Near-dust HTLCs not counted toward the commitment fee | CP | none reported | PARTIAL (weak) | As row 37 | L1 |
| 39 | 2025-07-22 (Morehouse); LL 2026-08-11 | LND | gossip_timestamp_filter goroutine-exhaustion DoS | 0.18.3, 2024-09-12 | < 0.18.3 | 0.18.3 | LL T3 Low | Repeated full-graph filter requests cause OOM | P | none reported | PARTIAL | Fix is inside the 0.18 line; ≤0.17 affected, 0.19+ fixed | LL4, M8, D1859, O25b |
| 40 | 2025-09-23 | Eclair | Preimage extraction exploit (Morehouse) | 0.12.0, 2025-03-11 (silent, inside the splicing PR) | ≤ 0.11.0 | 0.12.0 | critical (theft) | Preimage not extracted from an old remote commitment, so the HTLC is stolen | Fwd | none reported | LINE | 0.12.0 starts a line (+61) | M9, D2010, E1 |
| 41 | 2025-10-10 | LDK | 0.1.6 Security (#4154, #4081) | same day | ≤ 0.1.5 | 0.1.6; 0.2.0 (2025-12-02) presumably includes it (unverified) | funds theft; DoS | Invalid on-chain claims after a late preimage; unfunded monitors never archived | Fwd | none reported | PARTIAL (weak) | Fix is inside the 0.0.120–0.1 line; 0.2+ wholly fixed only if 0.2.0 carries it (unverified) | L1 |
| 42 | 2025-12-04 | LND | Replacement Stalling Attack (Morehouse; no LL advisory) | 0.19.0, 2025-05-22 | ≤ 0.18.5 (bug from the 0.18 sweeper rewrite; earlier versions unverified) | 0.19.0 | "critical" (theft) | Double-spends reset sweeper fees and delay re-aggregation, enabling channel theft | Fwd | none reported | LINE | 0.19.0 starts a line (soft: 261 removable; 161/61 imply ≥0.19) | M10, D2145, O25c |
| 43 | 2025-12-04 | LND | Excessive Failback #2 (Morehouse; no LL advisory) | 0.19.0 | ≤ 0.18.5 | 0.19.0 | "critical" (theft) | Failback variant triggered when the victim force-closes | Fwd | none reported | LINE | As row 42 | M11, D2145 |
| 44 | 2025-12-04 | LND | Infinite Inbox DoS (Morehouse) | 0.19.0 | ≤ 0.18.5 | 0.19.0 | DoS | Per-peer queues plus unlimited peers; query_short_channel_ids spam causes OOM | P | none reported | LINE | As row 42. May be the same bug as LL row 53 or 57 | M12, D2145, O25c |
| 45 | 2026-05-16 | CLN | Assertion DoS (Pratap) | **25.09** (PR #8436, 2025-08-07; tag-verified). The post says 26.04 | ≤ 25.05.x (incl. 25.05.1, released after 25.09) | 25.09 | Medium/High (DoS) | funding_created with an all-zero txid hits an hsmd assertion | P (accepts inbound) | none | LINE | 25.09 starts a line (45→44). LINE also holds if the post's 26.04 is right | D2507, O26a |
| 46 | 2026-06-18 | LND | Gossip nil-map panic on zero-timestamp messages (Bansal) | 0.20.1, 2026-02-12 | < 0.20.1 | 0.20.1 | LL T3 Low | A timestamp-0 channel_update or node_announcement crashes the node | P | none reported | PARTIAL | Fix is inside the 0.20 line; ≤0.19 affected, 0.21 wholly fixed (shipped before the disclosure) | LL5, D2621, O26b |
| 47 | 2026-06-18 | LDK | 0.2.3 / 0.1.10 Security (Project Loupe batch) | same day | ≤ 0.2.2, ≤ 0.1.9 | 0.2.3; 0.1.10 | several DoS; reserve underestimates | Panics, HashDoS, RGS memory cap, sanitisation | P / CP | none reported | PATCH | Both maintained lines are mixed; 0.2.0–0.2.1 and older lines are lower bounds only; no wholly fixed line | L1 |
| 48 | 2026-07-19 | CLN | Twin memory exhaustion, part 1: connectd queue (Pratap) | **25.09** (PR #8376, 2025-08-18; tag-verified). The post says 26.04 | ≤ 25.05.x | 25.09 | Medium/High (DoS) | A channel_update flood grows connectd's queue until OOM | P | none | LINE | 25.09 line start (also LINE if 26.04) | D2731, O26c |
| 49 | 2026-07-19 | CLN | Twin memory exhaustion, part 2: gossipd unknown-SCID map | **26.04** (PR #8903, 2026-02-16; tag-verified in v26.04, absent from 25.12.1). The post says 26.06rc2 | ≤ 25.12.x | 26.04 | Medium/High (DoS) | Bogus SCIDs grow the uintmap until RAM is exhausted | P | none | LINE | 26.04 line start (+63). It would be PATCH if the post's 26.06rc2 were correct; the tag check contradicts the post | D2731 |
| 50 | 2026-08-04 | LDK | 0.2.5 / 0.1.12 Security (Loupe) | same day | ≤ 0.2.4, ≤ 0.1.11 | 0.2.5; 0.1.12 | on-chain funds theft plus DoS | ChannelMonitor confuses equal hash/amount HTLCs (#4854); panics; the unfunded-peer limit is not enforced | Fwd | none reported | PATCH | Inside the newest lines; no wholly fixed line | L1 |
| 51 | 2026-08-07 | BTCPay | BTCPay Server < 2.4.2 Greenfield auth/TOTP bypass | 2.4.2, 2026-08-07 (ships LND 0.21.1) | BTCPay < 2.4.2 with LND | 2.4.2 | not stated; funds stolen | Unauthenticated fetch of LND macaroons through BTCPay | Cfg (BTCPay+LND hosts) | **Yes: exploited, "funds were stolen"** | N/A | Not an LN-node code fix; the bundled LND 0.21.1 is inside the 0.21 line | B1 |
| 52 | 2026-08-11 | LND | LL: Validation Barrier Map Leak via ChannelAnnouncement Spam | 0.19.0, 2025-05-22 | < 0.19.0 | 0.19.0 | LL T3 Low | Validation-barrier maps never cleaned up, so OOM | P | none stated | LINE | 0.19.0 line start | LL0, LL6 |
| 53 | 2026-08-11 | LND | LL: query_short_chan_ids Gossip Queue OOM (Morehouse) | 0.19.0 | < 0.19.0 | 0.19.0 | LL T3 Low | Stacked queues, about 140 MB per peer, so OOM | P | none stated | LINE | as row 52 | LL7 |
| 54 | 2026-08-11 | LND | LL: P2P Connection Flooding FD Exhaustion | 0.19.0 | < 0.19.0 | 0.19.0 | LL T3 Low | No limit on non-channel inbound connections | P (listening) | none stated | LINE | as row 52 | LL8 |
| 55 | 2026-08-11 | LND | LL: HTLC First-Stage Sweep Failure Due to Wallet Budget Constraint | 0.19.0 | ≥ 0.18.0, < 0.19.0 | 0.19.0 | LL T1 High | Wallet-budget guard skipped anchor HTLC sweeps; the HTLC can be claimed via timeout | Fwd | **organic (non-adversarial) failures observed in the wild** | LINE | Affected set is exactly the 0.18 line | LL9 |
| 56 | 2026-08-11 | LND | LL: Gossip ChannelUpdate Suppression via Validation Barrier Poisoning | 0.19.0 | < 0.19.0 | 0.19.0 | LL T3 Low | Wrong-chain announcements suppress updates for a chosen SCID | P | none stated | LINE | as row 52 | LL10 |
| 57 | 2026-08-11 | LND | LL: Gossip Query DoS (Morehouse, reported 2023-09-15) | 0.19.0 | < 0.19.0 | 0.19.0 | LL T3 Low | Gossip-query flood makes the node unresponsive | P | none stated | LINE | as row 52 | LL11 |
| 58 | 2026-08-11 | LND | LL: ChannelReestablish Message Queue OOM | 0.19.0 | < 0.19.0 | 0.19.0 | LL T3 Low | channel_reestablish spam on pending channels | P (accepts inbound) | none stated | LINE | as row 52 | LL12 |
| 59 | 2026-08-13 | LND | Too few confirmations when closing channels (t-bast; no LL advisory) | 0.20.1, 2026-02-12 (PR #10331; tag-verified). The post and Optech say "0.20.0" | < 0.20.1 | 0.20.1 | not stated | Coop-closed channel forgotten after 1 conf; a 1-block reorg allows an unpunished revoked state | CP | "nobody was impacted as far as we know" | PARTIAL | Fix is inside the 0.20 line; ≤0.19 affected, 0.21 fixed. It would be LINE if the fix were in 0.20.0 | D2800, O26d |
| 60 | 2026-08-25 (blog); Delving 08-27 | CLN | Ping-flood OOM (Cestari) | 25.09, 2025-09-02 (PR #8525 merge = the v25.09 tag commit) | < 25.09 (25.05.1 not patched) | 25.09 | "critical DoS" (author) | Max-size pong or query_channel_range flood while never reading; connectd outqueue OOM | P (handshake only) | none | LINE | 25.09 line start | D2846, O26e |
| 61 | 2026-08-26 (pre-announcement); source 2026-09-11 | CLN | 26.06.7 batch ("AI-generated" reports; no CVE) | 26.06.7, 2026-08-28; no 26.04.x or 25.12.x backport | ≤ 26.06.6 (older lines declared unsupported) | 26.06.7 only | none stated | Remote crashes (offers, BOLT12, DNS), unbounded peer feerates, unauthenticated clnrest crash, among others | P (mostly); clnrest = Cfg | **Forced-offline event: on 2026-08-26 operators were told to restart with `--offline` if they could not upgrade** ("restart offline", not "power off"); no exploitation known at the time | PATCH | Inside the newest line 26.04–26.06; lower bound only (pre-26.04 lines); 26.06.7 = 26.06.8 in bits | C2, C3, C4, O26f |
| 62 | 2026-08-26 | Eclair | 0.14.2 security batch (no per-issue disclosure) | 0.14.2, 2026-08-26 | ≤ 0.14.1 | 0.14.2 | Optech: "security release" | Reserve/dust checks, on-the-fly funding, reestablish, gossip-query limits, pre-auth connection cap | mixed (some Phoenix/LSP only) | none reported | PATCH | Inside the newest line (0.14); bit 67 implies ≥0.14.2 only when configured | E1, O26g |
| 63 | 2026-09-09 | LDK | 0.2.6 Security (#4905, #4982) | 0.2.6; #4982 backported in 0.1.13 (2026-10-01) | 0.2.x ≤ 0.2.5; 0.1.x ≤ 0.1.12 (#4982) | 0.2.6 / 0.1.13 | DoS plus "fee inflation" (small loss) | Splice peer over-allocates our fee; bogus same-hash HTLC leaves ChannelManager undeserialisable | CP | none reported | PATCH | Inside the newest line | L1 |
| 64 | 2026-09-14 | Eclair | 0.14.3 security hardening (Project Loupe) | 0.14.3, 2026-09-14 | ≤ 0.14.2 | 0.14.3 | Optech: "security release ... upgrading strongly recommended" | Unbounded closing fee, unpublishable splice commitment, blinded-path relay checks | P / CP; on-the-fly = LSP | none reported | PATCH | Inside the newest line | E1, O26g |
| 65 | 2026-09-21 | LND | LL: Invoice Marked Settled After HTLC Cancelled by Interceptor (lnd+tapd+litd) | lnd 0.19.0 (2025-05-22); tapd 0.5.1 (2025-02-12) | lnd 0.18.4–0.18.5 with an HtlcModifier client (tapd/litd) | 0.19.0 | LL T1 High | Invoice settled in the DB while the HTLC was failed on the wire | Cfg (litd/tapd; includes private nodes) | **organic field occurrence (2025-01-27)**, not adversarial | PARTIAL | Affected set is a subset of the 0.18 line; fix at the 0.19 line start. Bit 2025 (litd profile) implies ≥0.18.4, so it is near-exact for litd nodes | LL0, LL13 |
| 66 | 2026-09-21 | LND | LL: Gossip Stall via Malformed channel_announcement Flood | 0.20.1, 2026-02-12 | 0.19.0–0.20.0 | 0.20.1 | LL T3 Low | More than 1000 malformed announcements deadlock the gossiper; channels effectively go private | P | none stated | PARTIAL | 0.19 line wholly affected, 0.20 mixed, 0.21 wholly fixed, ≤0.18 unaffected | LL14 |
| 67 | 2026-09-21 | LND | LL: Panic on Malformed DNS Seed Response | 0.21.1 (2026-06-30); 0.20.2 (2026-07-08) | < 0.20.2, and 0.21.0 | 0.20.2 / 0.21.1 | LL T3 Low | SRV fallback type-assertion panic during bootstrap | all bootstrapping nodes (needs a malicious seed or on-path attacker) | none stated | PATCH | Both the 0.20 and 0.21 lines are mixed; no wholly fixed line | LL15 |
| 68 | 2026-09-21 | LND | LL: OOM via Brontide Write Allocations (Morehouse, Cestari) | 0.20.0, 2025-11-20 | < 0.20.0 | 0.20.0 (no 0.19 backport) | LL T3 Low | Per-write buffer allocations cause OOM | P | none stated | LINE | 0.20.0 line start (hard bit 35) | LL16 |
| 69 | 2026-09-22 | CLN | 26.06.8 batch | 26.06.8, 2026-09-22 | ≤ 26.06.7 | 26.06.8 only | none stated | Revoked-commitment broadcast after splice; onchain HTLC confusion; error-onion crash; clnrest YAML OOM; rune secret | P / CP; clnrest = Cfg | **2026-10-02: Core_LN reports attackers targeting unpatched ≤26.06.7 nodes**; no losses confirmed | PATCH | Inside the newest line; 26.06.7 and 26.06.8 have identical bits | C2, C3, C5, O26h |
| 70 | 2026-09-24 | Eclair | LNF-2026-0001 Feature-bit parsing DoS (Morehouse, smite) | 0.14.0, 2026-05-21 | ≤ 0.13.1 | 0.14.0 | Medium | Max-length `init` floods cause heap churn and OOM | P | none reported | LINE | 0.14.0 line start (+35, +63, +81) | F1, F2, D2914 |
| 71 | 2026-09-24 | Eclair | LNF-2026-0002 zlib query decompression DoS | 0.14.0 | ≤ 0.13.1 | 0.14.0 | Medium | 64 KB query inflates to 64 MB | P | none reported | LINE | as row 70 | F1, F3, D2914 |
| 72 | 2026-09-30 | Eclair | LNF-2026-0003 open_channel race actor leak | 0.14.1, 2026-07-29 | ≤ 0.14.0 | 0.14.1 | Low | TOCTOU orphans channel actors, leaking memory until OOM | P (accepts inbound) | none reported | PATCH | Inside the newest line | F1, F4, D2928 |
| 73 | 2026-09-30 (blog); Delving 10-01 | Eclair | Unfunded channel flood (Cestari; no LNF id) | 0.14.1 | ≤ 0.14.0 (how far back is unverified) | 0.14.1 | not rated | Reused channel id bypasses the pending-channel rate limiter, causing an OOM crash loop | P (accepts inbound) | none reported | PATCH | Inside the newest line | D2928, EC1 |
| 74 | 2026-10-01 | LDK | 0.2.7 / 0.1.13 Security (#5057, #5042, #4867) | same day | ≤ 0.2.6, ≤ 0.1.12 | 0.2.7 / 0.1.13 (#5042 only on 0.2.7; 0.1 exposure unverified) | two funds-theft issues plus DoS | A fake "missed update" in reestablish makes LDK sign an unmonitored commitment; LSPS2 JIT amount lie | Fwd; LSPs | none reported | PATCH | Inside the newest lines | L1 |
| 75 | 2026-10-06/07 | CLN | 26.06.9 batch | 26.06.9, 2026-10-07 | ≤ 26.06.8 | 26.06.9 only | none stated | Reestablish re-sign, splice crash, late-fulfill fund loss, rune bypasses, setconfig injection | P / CP; rune/setconfig = Cfg | no new event beyond the 10-02 warning | PATCH | Inside the newest line | C2, C3, O26i |

## Notes

**Silent fixes are the norm.** The fix often shipped months to years before anyone disclosed it. Measure upgrade timing from both the fix release and the disclosure.

Gaps between fix and disclosure:
- **Lightning Labs batch of 2026-08-11:** 10 advisories, all LND < 0.19. Fixes shipped in 0.18.0 (1), 0.18.3 (2) and 0.19.0 (7), between 14 and 26 months earlier.
- **Lightning Labs batch of 2026-09-21:** 8 advisories, but only 4 concern lnd. The other 4 are btcd-only and are not counted as rows:
  - OOM via oversized `reject` messages
  - pre-handshake tx-parser panic
  - 32 MB message payloads
  - inbound handshake exhaustion

  They could reach lnd only in neutrino mode, through `btcd/peer`. That is an inference; Lightning Labs does not list lnd as affected.
- **Other examples:**
  - Eclair preimage extraction: 6.5 months.
  - CLN 2026-07-19 disclosure: about 11 months after 25.09.
  - LND Gögge gossip bugs: 18–25 months.

**Re-publications.** Rows 28, 35 and 39 were already public through Harding and Morehouse in 2024–2025. Lightning Labs re-published them on 2026-08-11, so the paper should use the earlier date.

**Corrections to the starting premises:**
- **CLN 2026-07-19:** the fixes are in 25.09 and 26.04 (fix commits checked against tags with the GitHub compare API), not "26.04/26.06" as the post says. Both 25.09 and 26.04 are line starts, so these are LINE events.
- **CLN 2026-08-26:** operators were told to *restart with `--offline`* (no peer connections), not to shut down. A node restarted this way stops gossiping, so expect announcement gaps around 2026-08-26 to 2026-08-28.
- **Replacement cycling IDs** (from Riard's own email): LDK = CVE-2023-40231, Eclair = 40232, LND = 40233, CLN = 40234.

**No backports and no wholly fixed line yet:**
- CLN's 26.06.7, 26.06.8 and 26.06.9 have no backports; Blockstream declared everything before 26.06.7 unsupported. v26.09 has not been tagged as of 2026-10-14, so every 2026-H2 CLN batch is PATCH.
- Eclair has no maintained older lines.
- LDK maintains 0.1.x and 0.2.x in parallel, with partial backports.

**Weak bounds.** LDK 0.0.120 through 0.1.13 is one line in gossip (Jan 2024 to Oct 2026). Every LDK fix from 0.0.121 to 0.1.6 is therefore only weakly bounded. LDK and Eclair also have very few public nodes; Phoenix-style and wallet nodes are unannounced.

**Secondary signals can sharpen some PARTIAL rows:**
- LND CLTV delta 80 means ≥0.16.1. That is relevant to rows 11 and 17, but it is an operator-settable policy.
- LND bit 181 means ≥0.17 (row 27). Bit 2025 means ≥0.18.4 (rows 28, 39, 65). Both are opt-in flags.
- Eclair's 45% htlc_max cap points to ≥0.9.

**In-the-wild exploitation or forced-offline events, in total:**
- LND, 2022-10-09 and 2022-11-01: chain stalls from on-chain transactions (rows 5–6).
- BTCPay, 2026-08: funds stolen (row 51).
- CLN `--offline` advisory, 2026-08-26 (row 61).
- CLN reports of attacks on ≤26.06.7, 2026-10-02 (row 69; the bug used is unspecified).
- Organic (non-adversarial) field failures: LND rows 55 and 65.
- Nothing else reports exploitation.

**Excluded, and why:**
- Smite's public bug list (lnfuzz.org/projects/smite) lists 37 issues, including CLN subdaemon aborts. They are public bug reports, not advisories.
- Silent hardening without an advisory:
  - LND 0.20.3/0.21.2 (#10992), 0.20.4/0.21.3 (#11090 ping-reply rate limit, #11122, #11075)
  - LDK #5046/#5030 (listed as bug fixes)
  - ldk-node 0.7.1 (2026-10-12) "security-relevant hardening"
  - unreleased Eclair master fixes #3387–#3401
- btcd-only CVEs: CVE-2024-38365 (FindAndDelete), CVE-2024-34478, and the 2024-01 signed-tx-version bugs.
- Bitcoin Core CVE-2024-55563 and Riard's generic 2024–2025 relay attacks: they name no LN implementation fix.
- CVE-2024-34694 is an LNbits bug.

**Unverified items:**
- Whether LDK 0.2.0 includes the 0.1.6 fixes (row 41).
- Whether 0.1.x is exposed to LDK #5042 (row 74).
- How far back the Eclair unfunded-channel flood goes (row 73).
- Whether LND versions before 0.18 are affected by replacement stalling (row 42).
- Which bug the 2026-10-02 CLN attackers used.
- Third-party claims ("33,000 channels / 3,750 BTC at risk"; a 2026-09-13 "liquidity drain" report on 26.06.7).
- Delving t/979, t/1493 and t/1859 were confirmed through search metadata plus the matching Morehouse posts, not opened one by one.
- t/2800 was read as a summary, not verbatim.

## Sources

Every URL below was opened during this audit, either directly or by a research sub-agent that reported opening it.

**Lightning Labs and GitHub advisories**
- LL0 https://security.lightning.engineering/ (index of 21 advisories)
- LL1 https://security.lightning.engineering/2026/08/11/lnd-pending-commitment-failback-exploit
- LL3 https://security.lightning.engineering/2026/08/11/lnd-update-fee-breach-exploit
- LL4 https://security.lightning.engineering/2026/08/11/lnd-gossip-timestamp-filter-dos
- LL5 https://security.lightning.engineering/2026/06/18/lnd-zero-timestamp-gossip-dos
- LL6 https://security.lightning.engineering/2026/08/11/lnd-validation-barrier-oom
- LL7 https://security.lightning.engineering/2026/08/11/lnd-query-short-chan-ids-oom
- LL8 https://security.lightning.engineering/2026/08/11/lnd-p2p-connection-flooding
- LL9 https://security.lightning.engineering/2026/08/11/lnd-htlc-sweep-budget-failure
- LL10 https://security.lightning.engineering/2026/08/11/lnd-gossip-update-suppression
- LL11 https://security.lightning.engineering/2026/08/11/lnd-gossip-queries-dos
- LL12 https://security.lightning.engineering/2026/08/11/lnd-channel-reestablish-oom
- LL13 https://security.lightning.engineering/2026/09/21/lnd-tapd-cancelled-htlc-marked-settled
- LL14 https://security.lightning.engineering/2026/09/21/lnd-gossip-validation-barrier-stall
- LL15 https://security.lightning.engineering/2026/09/21/lnd-dns-bootstrap-type-assertion-panic
- LL16 https://security.lightning.engineering/2026/09/21/lnd-brontide-write-allocation-oom
- N1 GitHub advisory DB via `gh api advisories`: https://github.com/advisories/GHSA-2chg-86hq-7w38, https://github.com/advisories/GHSA-hc82-w9v8-83pr, https://github.com/advisories/GHSA-9gxx-58q6-42p7. Also the repo advisories API for lnd, ElementsProject/lightning, ACINQ/eclair, lightningdevkit/rust-lightning and ldk-node (empty for all except lnd).
- N2 LND release bodies and notes: https://github.com/lightningnetwork/lnd/releases (v0.14.4, v0.14.5, v0.15.2, v0.15.4, v0.20.1, v0.20.2, v0.21.1) and docs/release-notes/release-notes-0.15.2.md, 0.16.0, 0.16.1, 0.20.2, 0.21.0, 0.21.1
- N3 https://github.com/lightningnetwork/lnd/issues/7002
- N4 https://github.com/lightningnetwork/lnd/issues/7096
- N5 https://github.com/lightningnetwork/lnd/pull/10331 and the v0.20.0-beta...v0.20.1-beta compare

**CLN**
- C1 https://lists.linuxfoundation.org/pipermail/lightning-dev/2022-April/003561.html
- C2 https://github.com/ElementsProject/lightning/blob/master/CHANGELOG.md (as of v26.06.9)
- C3 https://github.com/ElementsProject/lightning/releases/tag/v26.06.7, /v26.06.8, /v26.06.9. Fix-in-tag checks used the GitHub compare API for PRs #8376, #8436, #8525 and #8903 against v25.05.1, v25.09, v25.12.1 and v26.04.
- C4 https://blog.blockstream.com/core-lightning-26-06-7/ ; https://x.com/Core_LN/status/2092755509510283423 ; https://x.com/callebtc/status/2092683963366064550
- C5 https://x.com/Core_LN/status/2105835841847242976
- https://github.com/ElementsProject/lightning/security/advisories (none published)

**Eclair, LDK, smite**
- E1 https://github.com/ACINQ/eclair/releases (v0.7.0 – v0.14.3) and https://github.com/ACINQ/eclair/tree/master/docs/release-notes
- L1 https://raw.githubusercontent.com/lightningdevkit/rust-lightning/main/CHANGELOG.md ; https://crates.io/api/v1/crates/lightning/versions
- F1 https://lnfuzz.org/advisories/
- F2 https://lnfuzz.org/advisories/eclair-feature-parsing-dos/
- F3 https://lnfuzz.org/advisories/eclair-zlib-decompression-dos/
- F4 https://lnfuzz.org/advisories/eclair-open-channel-race-dos/
- https://lnfuzz.org/projects/smite/ and https://morehouse.dev/lightning/fuzzing-lightning-with-smite/
- EC1 https://erickcestari.dev/blog/eclair-oom-pending-channels/ ; https://erickcestari.dev/blog/ping-flood-oom/

**Write-ups and mailing lists** (morehouse.github.io now redirects to morehouse.dev)
- M1 https://morehouse.dev/lightning/fake-channel-dos/
- M2 https://morehouse.dev/lightning/cln-invoice-parsing/
- M3 https://morehouse.dev/lightning/cln-channel-open-race/
- M4 https://morehouse.dev/lightning/lnd-onion-bomb/
- M5 https://morehouse.dev/lightning/ldk-invalid-claims-liquidity-griefing/
- M6 https://morehouse.dev/lightning/ldk-duplicate-htlc-force-close-griefing/
- M7 https://morehouse.dev/lightning/lnd-excessive-failback-exploit/
- M8 https://morehouse.dev/lightning/lnd-gossip-timestamp-filter-dos/
- M9 https://morehouse.dev/lightning/eclair-preimage-extraction-exploit/
- M10 https://morehouse.dev/lightning/lnd-replacement-stalling-attack/
- M11 https://morehouse.dev/lightning/lnd-excessive-failback-exploit-2/
- M12 https://morehouse.dev/lightning/lnd-infinite-inbox-dos/
- https://morehouse.dev/posts/ (index of 14 posts)
- R1 Riard's full disclosure (2023-10-16), CVE-to-implementation mapping: https://mirror.b10c.me/lists/bitcoindev/CALZpt+GdyfDotdhrrVkjTALg5DbxJyiS8ruO2S7Ggmi9Ra5B9g@mail.gmail.com ; MITRE cve-id API (40231–40234: RESERVED)
- B1 https://blog.btcpayserver.org/security-advisory-btcpay-server-2-4-2/ ; https://github.com/btcpayserver/btcpayserver/releases/tag/v2.4.2

**Delving Bitcoin** (https://delvingbitcoin.org/t/<id>)
- D314 (LND channel_update gossip DoS)
- D385 (CLN channel-open race)
- D979 (LND onion bomb)
- D1314 (irrevocable fees)
- D1400 (LDK invalid claims)
- D1410 (LDK duplicate HTLC)
- D1493 (LND excessive failback)
- D1859 (LND gossip_timestamp_filter)
- D2010 (Eclair preimage extraction)
- D2145 (critical vulnerabilities fixed in LND 0.19.0)
- D2507 (CLN assertion DoS)
- D2621 (LND zero-timestamp gossip)
- D2731 (CLN twin memory exhaustion)
- D2800 (LND close confirmations)
- D2846 (CLN ping flood)
- D2914 (Eclair v0.14.0 DoS)
- D2928 (Eclair v0.14.1 DoS)
- Plus search.json listings for "disclosure" and "vulnerability"

**Bitcoin Optech** (https://bitcoinops.org/en/newsletters/YYYY/MM/DD/)
- O22a 2022/05/04
- O22b 2022/10/12
- O22c 2022/11/02
- O23a 2023/08/30
- O23b 2023/10/18 and 2023/10/25
- O24a 2024/01/03
- O24b 2024/01/17
- O24c 2024/06/21
- O25a 2025/03/07
- O25b 2025/07/25
- O25c 2025/12/12
- O26a 2026/05/29
- O26b 2026/06/26
- O26c 2026/07/31
- O26d 2026/08/21
- O26e 2026/09/04
- O26f 2026/08/28 and 2026/09/04
- O26g 2026/08/28 – 2026/09/18
- O26h 2026/09/25 and 2026/10/09
- O26i 2026/10/09
