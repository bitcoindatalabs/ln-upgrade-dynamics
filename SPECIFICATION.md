# Engineering & Research Specification (v1, draft for agreement)

> **Status 2026-10-14.** Scaffolded and due diligence done; nothing in `src/` yet. Code starts once the owner
> agrees this spec (§9 lists the open decisions). Due-diligence notes: `notes/advisory_audit.md`,
> `notes/literature.md`.

## Working title
**How Fast Does the Lightning Network Patch? Release Lines from Gossip, Upgrade Waves and Exposure after the 2026
Security Advisories**

*Alternative:* "Patched by Default: Software Upgrade Dynamics of the Lightning Network, 2023–2026"

**Target:** arXiv (`cs.CR`, cross-list `cs.NI`); then FC / AFT. Companion to paper 01
(`bitcoindatalabs/ln-client-diversity`), which asked what the network loses when a client fails; this paper asks
how fast the network leaves a vulnerable state.

---

## 1. Positioning: why this paper, why us

AI makes simulation-on-a-snapshot papers cheap. This one rests on what an agent cannot produce: three years of daily
gossip from our own node (the raw dumps cannot be regenerated), ground truth for versions, and a dated sequence of
real advisories with one forced-offline event.

**Literature check (2026-10-14, `notes/literature.md`): nobody has measured LN node versions, upgrade dynamics or
post-advisory exposure.** LN work stops at the client family: Zabka et al. (ICDCN 2021; PMC 2022) classify by default
channel parameters and note in passing that LND's 2019 CLTV-default change took ~9 months to reach most LND nodes;
Espinasa-Vilarrasa et al. (MDAI 2024) infer the implementation from feature bits, not the version; Kappos et al.
(FC 2021) state their snapshots carried no version information. The closest analogues are elsewhere and read
self-reported versions: Ethereum peers (Kim et al., IMC 2018: 68% of Geth nodes ≥ 2 releases behind) and Bitcoin
(Neudecker 2019; Eisenbarth et al. 2021). Method and framing come from patch-deployment work: windows of
vulnerability (Arbaugh et al. 2000), Rescorla 2003, Frei et al. 2009 (auto-update dominates patch levels), Heartbleed
(Durumeric et al. 2014), survival analysis of patching (Nappa et al. 2015). Our gap: versions **inferred and
validated** where none are reported, plus exposure measured on live nodes and capacity.

## 2. Contributions
- **C1 — Release-line inference from gossip, validated.** Each node's feature bits map to the release lines whose
  defaults and options can produce them (source-cited table for all four implementations, 2019–2026). Validated on
  CLN developer aliases that state the version (133 nodes, 16,748 node-days: strict range correct on 99.99%, likely
  line exact on 98.6%) and on our own LND node at every upgrade. State plainly what it cannot see: patch level.
- **C2 — Upgrade dynamics 2023–2026.** Adoption curves per release line, time-to-upgrade (interval-censored) by
  client, node size, transport and announcement signature; single-day upgrade waves that point to platform
  auto-updates; pre-release builds visible in public gossip; the lag between a release and its first appearance.
- **C3 — Exposure after advisories.** For every advisory whose fix boundary is a gossip-visible line, the share of
  *live* nodes and capacity still on an affected line, day by day, and how that share falls: upgrades vs nodes
  leaving. Two timelines matter per advisory: **fix → disclosure** (the 2026-08-11 LND batch had shipped its fixes
  14–26 months earlier) and **disclosure → upgrade**. Headline contrast (preliminary, §5): LND's lagging tail barely
  moved after Lightning Labs' 2026-08-11 advisories, while CLN exposure halved after the 2026-08-26 call to upgrade
  or restart with `--offline`.

## 3. Research questions
- **RQ1** How accurately can a node's release line be inferred from gossip, and what can't be inferred?
- **RQ2** How fast do LN nodes adopt new release lines, and what predicts lagging (size, client, transport, platform)?
- **RQ3** How many live nodes and how much capacity remained on vulnerable lines after each line-scoped advisory, and
  did the share fall through upgrades or through exits?
- **RQ4** Does the type of announcement matter: advisory only (LND, 2026-08-11) vs maintainers telling operators to
  upgrade or restart with `--offline` (CLN, 2026-08-26; Core_LN discouraged powering off)?

## 4. Data
| Dataset | Source | Coverage |
|---|---|---|
| Node announcements (feature bits, alias, color, addresses, `last_update`) | own LND `describegraph` → `gossip_daily/nodes` | 866 daily files 2023-05-08 → 2026-10-13 |
| Channel policies (`disabled`, `last_update`, capacity, setter vs peer) | same → `gossip_daily/policies` | same |
| Snapshot quality and vantage epochs | `gossip_daily/_quality.parquet` | per day: ok / partial / stale, epoch A/B |
| Release → feature-bit table | `ln_release_features.json` + `docs/ln_release_features/*.md` (v1-2026-10-07) | LND 0.7–0.21.4, CLN 0.8.2–26.06.9, Eclair 0.3–0.14.3, LDK 0.0.113–0.2.7 |
| Advisories | `notes/advisory_audit.md` | 2022-01 → 2026-10, with fix boundary per row |
| Ground truth for versions | CLN dev aliases, our node's `getinfo` history, LND alias node | §6 |

**Coverage (usable "ok" days per month, from `_quality`):** dense from 2023-11 (17–31 days/month) except
2024-05/06 (partial dumps), 2024-08 (11 days), 2025-01 → 2025-05 (13, 20, 12, 1, 8 days; LND wallet-locked
restarts). 2023-05 → 2023-10 has 7 days in total. Upgrade times are therefore **interval-censored** between the last
day seen on the old line and the first day seen on the new one; gaps widen intervals, they don't bias them.

**Populations.** Release lines resolve well for LND (~4,000 live nodes) and CLN (~550 live). Eclair is ~120 nodes and
mostly unresolved (one operator, ACINQ, holds nearly all its capacity); LDK is integrator-driven (Block). Per-node
dynamics are an LND + CLN study; Eclair and LDK appear as release-timing facts only.

## 5. Due-diligence findings that shape the design (2026-10-14)
1. **Liveness must define the denominator.** On 2026-10-13, 2,100 of 7,737 channel-holding LND nodes advertised a line
   below 0.19, but 1,676 of them had no fresh enabled channel direction set by a peer: dark or abandoned nodes whose
   channels have not closed. Counting them gives "27% exposed"; among live nodes it is 10.4%. Of the 424 live exposed
   nodes, 326 re-announced within 14 days, so their bits are current: they really run old software.
2. **Preliminary exposure (live = ≥1 enabled direction toward the node, set by a peer, updated < 14 days ago):**

   | Date | LND live on < 0.19 (nodes / capacity) | CLN live on < 26.04 (nodes / capacity) |
   |---|---|---|
   | 2026-06-01 | 15.1% / 8.8% | 78.3% / 82.5% |
   | 2026-08-10 | 12.6% / 6.5% | 51.2% / 47.8% |
   | 2026-08-25 | 13.3% / 6.5% | 45.6% / 41.6% |
   | 2026-09-10 | 12.6% / 6.0% | 30.5% / 18.1% |
   | 2026-10-13 | 10.4% / 6.3% | 21.7% / 11.9% |

   Live CLN fell from 769 (08-01) to 554 nodes, so part of the CLN decline is exits: C3 decomposes it.
   (The CLN column used < 26.04; the audit puts the 2026-07-19 fixes at 25.09 (connectd) and 26.04 (gossipd), and
   the 2026-05-16 and 2026-08-25 fixes at 25.09. The 2026 CLN patch releases 26.06.7–.9 are not measurable.)
7. **A managed fleet (found 2026-10-14).** From Aug 2025, hundreds of small LND nodes aliased `LNT.<name>`, with 1–2
   channels each to a few `LNT.` hubs (`LNT.Thailand`, `LNT.chengdu`) and one litd feature set. Peak 1,761 nodes
   = 27% of live LND nodes on 2025-12-08 with ~1 BTC of ~9,000; 566 nodes (14%) and 0.17 BTC at the cutoff. It moved
   ~1,500 nodes to LND 0.20 on 2025-12-09..12 (the "771-node wave" in the lake doc). One operator's decision, so every
   per-node statistic excludes it (panel column `fleet`) and the paper describes it separately; adoption and
   exposure are also given with it. **It affects paper 01's node counts for 2025–2026 (LND node share, all-pair
   reachability) — raise with the owner.**
8. **Release-day relabelling (fixed 2026-10-14).** Inferring the likely line as of each day relabelled nodes whose
   bits did not change when a new line came out (233 CLN nodes "upgraded" to 24.08 on its release day: 24.05 with the
   onion option). The likely line is now inferred as of the day the node's current bits first appeared; the strict
   range stays as of the day.
6. **Advisory audit (`notes/advisory_audit.md`):** 75 rows 2022-01 → 2026-10; 25 LINE, 36 PARTIAL (15 weak, mostly
   LDK's single 0.0.120–0.1 line), 12 PATCH. Only 5 CVEs exist; most disclosures are blog/Delving posts. Fixes often
   ship long before disclosure, so every advisory gets both timelines.
3. **Upgrade events are plentiful:** the lake's history (rules v3 / v1) holds 16,186 upgrade changes on 9,850 nodes
   (LND 15,078, CLN 993, LDK 98, Eclair 17). Known waves: 771 nodes to LND 0.20 on 2025-12-09; 153 to 0.21 on
   2026-06-27.
4. **Vantage epoch shift in 2024-07** (≈8.4k → 11–13k nodes) inflates old-line counts from that date (e.g. LND 0.13
   from ~100 to ~400 nodes). Levels are compared within an epoch; liveness filtering removes most of it.
5. **Client rules v4 matters here:** old LND sets `[0,5,7,9,13,15,17]` and `[9,13]` (LND 0.8–0.11) are labelled
   Eclair-low under v3, which would hide the oldest LND nodes, exactly the tail this paper measures (§9 D2).

## 6. Methods

### 6.1 Release-line inference (C1 / RQ1)
- Per node-day: client (frozen rules v4), strict line range (lines out on the day) and likely line (best fit among
  lines out when the node's current bits first appeared), `version_fingerprint` logic, frozen table.
- Validation: (a) CLN dev aliases, node-days where the alias states the version; (b) our node's upgrade dates from
  `getinfo` history; (c) the LND alias node; (d) **timing check**: no node may appear on a line before its release
  except the known pre-release builds, which are reported, not dropped.
- Limits measured, not assumed: share of node-days whose strict range spans >1 line, per client; share unrecognised.

### 6.2 Upgrade events and adoption (C2 / RQ2)
- Event = first day a node is seen on a later line (`upgrade`); downgrades and client changes are reported
  separately. Interval = (last day on old line, first day on new line]; announcement flaps (`last_update` = 0)
  carry the previous state.
- Adoption curve per release line: share of live nodes of that client on that line or later vs days since release.
- Time-to-upgrade: interval-censored survival per line (Turnbull estimator), and a discrete-time hazard model with
  covariates: capacity decile, channel count, Tor-only vs clearnet, client, announcement signature (litd flags,
  default color/alias, wumbo, etc.), node age.
- Waves: days where upgrades to one line exceed the 99th percentile of daily upgrades; the signature mix of the wave
  (does one feature set dominate?) attributes it to a platform where possible. Rule out the fleet/Sybil reading
  (Neudecker 2019 saw 0 → 700+ Bitcoin ABC peers in a day): wave nodes must have distinct channel peers, ages and
  capacities comparable to non-wave nodes, and existed before the wave.
- Historical anchor: Zabka et al. report ~9 months for LND's 2019 CLTV default to reach most LND nodes; compare with
  today's line adoption times.
- Announcement lag: release date → first node seen on the line, and → 10% / 50% of live nodes.

### 6.3 Exposure after advisories (C3 / RQ3–RQ4)
- From `notes/advisory_audit.md`, keep the LINE and PARTIAL advisories; PARTIAL ones give lower and upper bounds.
- Daily series per advisory: share of live nodes and of live capacity on affected lines, from 60 days before
  disclosure to the cutoff.
- Decomposition of each day-to-day fall: upgraded (moved to a fixed line) vs exited (left the live set: dark, closed
  channels, vanished) vs entered (new live nodes on affected lines). A competing-risks view per node: upgrade vs exit.
- LND 2026-08-11 vs CLN 2026-08-26: same metrics, side by side, with the pre-advisory trend as the baseline
  (did the slope change?).
- Robustness: liveness freshness 7 / 14 / 28 days; capacity with the largest node removed (lake finding §2.9);
  strict-range vs likely line.

## 7. Figures & tables (target)
1. Release-line mix of live LND and CLN nodes over time (stacked area, one panel per client, release dates marked).
2. Validation: stated vs inferred line (CLN aliases), our node's timeline.
3. Adoption curves: share on line ≥ L vs days since release, one line per LND/CLN release line.
4. Time-to-upgrade survival by capacity quartile (and Tor vs clearnet).
5. Upgrade waves: daily upgrade counts with wave days marked and their dominant signature.
6. Exposure after advisories: live-node and capacity share on affected lines, LND 08-11 vs CLN 08-26, with the
   upgrade / exit decomposition.
Tables: line inventory and what gossip can separate; advisory list with fix boundary and measurability; hazard model.

All figures: matplotlib, vector PDF, colorblind-safe palette (paper 01's `CLIENT_PALETTE`), no dual axes.

## 8. Architecture

```
02-ln-upgrade-dynamics/
  src/config.py                 paths, DATA_CUTOFF, liveness threshold, seeds, palette
  src/lnmetrics/                FROZEN copies: client_fingerprint.py (rules v4), version_fingerprint.py,
                                ln_release_features.json (v1-2026-10-07), gossip readers from incident_metrics
  src/01_build_panel.py         gossip_daily → node-day panel: client, line range, likely line, liveness, capacity
                                → data/panel/*.parquet (git-ignored) + data/panel_summary.json
  src/02_validate_lines.py      RQ1: ground-truth checks, ambiguity rates → data/validation.json, fig 2
  src/03_upgrade_dynamics.py    RQ2: events, adoption curves, survival, hazard model, waves → figs 1, 3–5
  src/04_advisory_exposure.py   RQ3–4: exposure series + decomposition → fig 6, advisory table
  src/05_supporting_numbers.py  every in-text number → data/supporting_numbers.json
  notes/                        due diligence (local only, not published)
  paper/                        main.tex, references.bib, figures/, tables/
```
- **Input:** `LN_PARQUET_DIR` env var → `gossip_daily/{nodes,policies,_quality}`. From this machine:
  `D:\data\Lightning\Data\parquet` (the `dev/Lightning` junction target; processes started from Claude Code cannot
  traverse the junction). Nothing else from the lake; in particular not `node_client_history.parquet`, which is
  relabelled whenever the rules change.
- **Reproducibility:** rules and release table are frozen copies with their version strings recorded in every JSON
  output; `DATA_CUTOFF` truncates every input.
- **Data flow:** one expensive pass (01) builds the panel; 02–05 read only the panel. Only aggregate JSON is committed.
- **Graduation:** as paper 01 (own repo under bitcoindatalabs; spec and notes stay local).

## 9. Decisions (owner, 2026-10-14)
- **D1 — Data cutoff 2026-10-13** (`DATA_CUTOFF = "20261013"`): ~63 days after the LND advisories, ~48 after the
  CLN call. Target: arXiv in October 2026.
- **D2 — Client rules v4** in this paper's frozen copy (lake doc §3 candidates), so the oldest LND nodes stop being
  labelled Eclair. Paper 01 stays on v3; the lake can adopt v4 afterwards.
- **D3 — Disclosure.** Aggregates only (no per-node lists, no "vulnerable" labels). Share the C3 numbers with
  Lightning Labs and CLN before posting. Revised 2026-10-15: sharing is a courtesy heads-up, not a gate. Every
  advisory was public before the analysis and the paper reports no new vulnerability, so the paper does not claim
  the results were shared.
- **D5 — Own-node check (2026-10-15).** The owner does not remember which LND versions the vantage node ran
  (a disk failure on the Raspberry Pi and a rebuild around 2025-05-24, with the alias reset to default). The paper
  therefore makes no claim about it; stage 02 still writes the timeline when `VANTAGE_NODE_PREFIX` is set.
- **D6 — Paper 01 citation.** Cite paper 01 by its GitHub repo (arXiv submission submit/8231899 not yet announced).
- **D4 — Advisories.** Every LINE and non-weak PARTIAL advisory (LND/CLN/Eclair) goes in the advisory table with
  fix date, disclosure date, and live-node / capacity exposure at fix, at disclosure and at +30/+60 days where data
  allows (PARTIAL rows as bounds). Weak-PARTIAL LDK rows are summarised in one line. Full daily case studies only
  where coverage around the disclosure is dense (the 2026 LND and CLN cases at least).

## 9b. Timeline
| Date | Milestone |
|---|---|
| Oct 14–16 | 01 panel (rules v4), 02 validation |
| Oct 17–20 | 03 upgrade dynamics, 04 advisory exposure |
| Oct 21–24 | 05 numbers, full draft |
| Oct 25–27 | Courtesy note to Lightning Labs / CLN (optional); references verified; review pass |
| Oct 28–31 | Graduate to own repo, arXiv upload |

## 10. Ethics
Aggregates only. No list, filter or ranking of nodes by version or exposure. Release-line granularity only; never
claim a node is vulnerable (patch level is invisible). Data and code released as aggregates + scripts.

## 11. References
Verified list and BibTeX: `notes/literature.md`. Verify every entry against the publisher page before citing.
