# Who Patches the Lightning Network? Release Lines from Gossip, Node Platforms and Security Advisories, 2023–2026

Saurabh Kumar, Bitcoin Data Labs

Code, aggregate data and LaTeX source for the paper. arXiv categories: `cs.CR`, cross-list `cs.NI`.
Data cutoff: 2026-10-13.

## Summary
Lightning gossip carries no software version, so whether operators act on security advisories has never been
measured. The paper infers the release line of every public LND, Core Lightning, Eclair and LDK node from the feature
bits it announces, matched against the source of every release, and applies it to daily gossip snapshots from May 2023
to October 2026. The network patches on release and platform schedules, not on disclosures: half of the LND nodes on an
older line upgrade within 88 days of a release; the largest upgrade waves came about a day after the Umbrel app store
shipped a new LND version; and of 12 disclosures that can be tested, only Core Lightning's of July 2026 raised the rate
at which nodes left affected releases, and only among nodes one release line behind; Core Lightning's call to restart
offline was followed mostly by nodes already on the newest line. Two months after Lightning Labs'
August 2026 batch, 71% of the nodes exposed at disclosure still ran an affected release.

## Repository structure
* `paper/`: LaTeX source (`main.tex`, `sections/`, `references.bib`, `figures/`, `tables/`, `numbers.tex`), the
  compiled `main.pdf` and a build script.
* `src/01_*.py` … `src/05_*.py`: the five pipeline stages.
* `src/lnmetrics/`: the frozen inference rules and reference data: client rules (`client_fingerprint.py`), the
  release table with the feature bits of every release (`ln_release_features.json`, read by
  `version_fingerprint.py`), the advisory list with the public source of each disclosure (`advisories.py`), the dated
  platform releases (`platforms.py`), and the gossip reader and panel helpers (`gossip.py`, `panel.py`).
* `data/`: aggregate JSON outputs behind every figure, table and in-text number.
* `scripts/package_arxiv.py`: builds the arXiv upload bundle.

## Reproducing the results

### 1. Dependencies
```bash
pip install -r requirements.txt
```

### 2. Input data
The pipeline reads daily snapshots of the public Lightning gossip graph as Parquet files; `src/lnmetrics/gossip.py`
documents the expected layout (`gossip_daily/{nodes,policies,_quality.parquet}`). The underlying gossip data are
public; our daily snapshots are available from the author on request. Point the pipeline at them with
```bash
export LN_PARQUET_DIR=/path/to/parquet        # default: data/parquet
```

### 3. Pipeline
Each stage truncates its inputs at `DATA_CUTOFF` (`src/config.py`) and writes its figures to `paper/figures/`, its
tables to `paper/tables/` and its numbers to `data/*.json`.
```bash
python src/01_build_panel.py          # node-day panel: client, release line, liveness, fleet flag (~7 min) -> data/panel/
python src/02_validate_lines.py       # release-line validation and consistency checks                    -> Fig. 1, Table I
python src/03_upgrade_dynamics.py     # adoption, time to upgrade, hazard model, platform waves           -> Figs. 2-5, Table II
python src/04_advisory_exposure.py    # exposure per advisory, response to disclosure, robustness         -> Figs. 6-7, Tables III-V
python src/05_supporting_numbers.py   # every number quoted in the text                                    -> paper/numbers.tex
```
The node-day panel (`data/panel/`, about 1.3 GB) is not committed.

### 4. Paper
`paper/build.ps1` (Windows, MiKTeX) runs pdflatex → bibtex → pdflatex until references settle; `build.bat` runs it
from cmd. On other systems:
```bash
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main
```
`python scripts/package_arxiv.py` then writes the arXiv bundle to `dist/`.

## Data policy
Aggregates only: no list, ranking or label of individual nodes by release, platform or exposure is published, in the
paper or in `data/`.

## License
MIT (see `LICENSE`).
