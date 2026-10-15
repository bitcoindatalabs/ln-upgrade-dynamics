# How Fast Does the Lightning Network Patch?

*Release Lines from Gossip and Exposure after Security Advisories, 2023–2026* — Saurabh Kumar, Bitcoin Data Labs.

The release line of a public Lightning node is inferred from the feature bits it announces, matched against the
source of every release of LND, Core Lightning, Eclair and LDK. Applied to daily gossip snapshots from May 2023 to
October 2026, it measures how fast nodes upgrade and how many stayed on vulnerable releases after each security
advisory whose fix boundary gossip can see.

## Pipeline

| Stage | Output |
|---|---|
| `src/01_build_panel.py` | node-day panel: client, release-line range, liveness, managed-fleet flag (`data/panel/`, not committed) |
| `src/02_validate_lines.py` | validation against self-identifying aliases and consistency checks: `data/validation.json`, Table I, Fig. 1 |
| `src/03_upgrade_dynamics.py` | line mix, adoption, time to upgrade, hazard model, upgrade waves and their platform releases, the fleet: `data/upgrade_dynamics.json`, Figs. 2–5, Table II |
| `src/04_advisory_exposure.py` | exposure per advisory, case studies, response to disclosure, robustness: `data/advisory_exposure.json`, Tables III–V, Figs. 6–7 |
| `src/05_supporting_numbers.py` | every number quoted in the text: `data/supporting_numbers.json`, `paper/numbers.tex` |

`src/lnmetrics/` holds the frozen inference rules (client rules v4, release table v1.1-2026-10-15), the advisory
list (with the public source of each disclosure) and the dated platform releases (Umbrel app store, BTCPay). All stages truncate their inputs at the data cutoff, 13 October 2026.

## Reproduce

```
pip install -r requirements.txt
set LN_PARQUET_DIR=<folder with gossip_daily/{nodes,policies,_quality.parquet}>
python src/01_build_panel.py        # ~7 min
python src/02_validate_lines.py
python src/03_upgrade_dynamics.py
python src/04_advisory_exposure.py
python src/05_supporting_numbers.py
paper\build.ps1                     # main.pdf
```

`VANTAGE_NODE_PREFIX` (optional) names the pubkey prefix of the vantage node for the own-node check in stage 02.

## Data policy
Aggregates only: no list, ranking or label of individual nodes by release, platform or exposure is published.
