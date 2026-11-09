# Understanding Australian and New Zealand Student Visa Approval Rates Through Origin Composition and Weighting

## Abstract

According to our previous study, Australia generally had higher recorded student-visa decision approval rates than New Zealand across matched applicant origins. This study tests whether that difference can be accounted for by how decisions are distributed across origins and years. Its main question is whether Australia's higher recorded rate is explained by origins with higher observed Australian rates accounting for larger shares of its decisions. The results do not support that explanation. When Australia and New Zealand were given the same distribution of decisions across origins, Australia had the higher average recorded approval rate. We used aggregate public records for 173 matched origins from 2022–2025. Using the destination-specific origin shares observed in the data, the Australian-minus-New Zealand difference was 5.3 percentage points (95% confidence interval −1.4 to 11.3; p = 0.097). In a computational comparison that applied the same average origin distribution to both destinations, the standardised rates were 88.5% for Australia and 77.6% for New Zealand. The difference therefore increased to 10.9 points (4.2–18.7; p < 0.001). The composition component was −5.6 points (−14.5 to −1.2; p = 0.005), confirming that equalising the origin distribution widened rather than removed the estimated difference. The Australian-minus-New Zealand rate component was positive in every year, but its size and the observed gap varied. The distribution of decisions therefore changed the apparent comparison, but it did not account for Australia's higher average recorded rate. These aggregate results do not explain why origin-specific rates differ or identify causal or individual effects.

The compiled manuscript is available at [article/article.pdf](article/article.pdf), with its LaTeX source at [article/article.tex](article/article.tex).

## Study design

The analysis uses the closest comparable public populations available:

- Australia: primary applicants outside Australia in the Higher Education Sector;
- New Zealand: offshore or overseas applicants in the student visa categories covered by the annual releases;
- period: calendar years 2022–2025; and
- common outcome: approvals or grants divided by approvals or grants plus refusals or declines.

The denominator is the number of recorded decisions, not the number of lodged applications. Country labels are harmonised separately within each year against the English UN M49 reference before annual records are pooled. Taiwan and Kosovo are retained where present as reviewed non-M49 exceptions. Australian `Not Specified` and `Refugee` records are excluded from country-level comparisons.

The analysis distinguishes observed decision-weighted national rates, equally weighted matched-origin summaries, common-weight standardised rates, and a symmetric decomposition of the aggregate difference into rate and composition components. The decomposition is repeated by year and checked against minimum-denominator and balanced-panel sensitivity analyses.

This is the third study in a cumulative research sequence. The preceding matched-origin comparison is available as a [Zenodo preprint](https://doi.org/10.5281/zenodo.23739706) with its own [public repository](https://github.com/vitalii-kaplan/au-nz-comparison). The present repository contains the distinct composition, weighting, decomposition, and temporal study.

## Data sources

The source records are published separately on Zenodo:

- [A Reproducible Cross-National Dataset of Public Student Visa and Study Permit Statistics](https://doi.org/10.5281/zenodo.21453632) — data paper;
- [Country-to-Visa: A Cross-National Dataset of Public Student Visa and Study Permit Statistics](https://doi.org/10.5281/zenodo.21446641) — data artifact.

The large archive and extracted source tables are intentionally not committed. [data/README.md](data/README.md) records the download checksums, selective extraction commands, source fields, population filters, annual harmonisation procedure, exclusions, and validation totals.

## Repository structure

| Path | Contents |
| --- | --- |
| [`article/`](article/) | Manuscript source, bibliography, compiled PDF, and publication tables and figures |
| [`data/`](data/) | Source documentation, schema, reviewed mappings, preparation audits, result manifests, and reproducible output layout |
| [`scripts/`](scripts/) | Data preparation, publication-output generation, and the end-to-end reproduction command |
| [`src/`](src/) | Dependency-ordered statistical analysis modules |
| [`tests/`](tests/) | Unit, contract, regression, publication-output, and pipeline tests |
| [`AU_NZ_visa_comparison_methods.md`](AU_NZ_visa_comparison_methods.md) | Statistical protocol, estimands, inferential rules, and interpretation boundaries |
| [`process_log.json`](process_log.json) | Append-only record of material repository and verification milestones |

Downloaded and extracted source files and generated prepared/intermediate tables are excluded from Git because they can be recreated using the documented pipeline. Final CSV result tables, reviewed mapping files, manifests, audit records, publication artifacts, scripts, source code, tests, and the manuscript are versioned.

## Requirements

- Python 3.10 or later. The Python pipeline uses the standard library.
- R with `Rscript`. The grouped-binomial models use base R.
- `curl` and `unzip` to retrieve and selectively extract the Zenodo inputs.
- A TeX distribution with `latexmk`, BibTeX, and PGFPlots to rebuild the manuscript.

## Reproducing the analysis

Run commands from the repository root.

1. Download and selectively extract the source files using [data/README.md](data/README.md).

2. Reproduce the prepared data, dependency-ordered analyses, verified publication tables and figures, test suite, and manuscript PDF:

```sh
python3 scripts/reproduce_article.py --run-tests --build-pdf
```

The command checks for the required source inputs, prepares and harmonises both destinations, runs the comparability gate before dependent analyses, executes all 16 analysis sections, verifies result manifests, regenerates the publication artifacts used by the manuscript, and stops if a required step fails.

To reuse already prepared inputs while regenerating the research and publication outputs:

```sh
python3 scripts/reproduce_article.py --skip-preparation
```

The analysis pipeline and test suite can also be run separately:

```sh
python3 -m src.analysis_15_run_pipeline
python3 -m unittest discover -s tests
```

Individual preparation and publication commands are documented in [scripts/README.md](scripts/README.md). Module contracts and output inventories are documented in [src/README.md](src/README.md), [data/results/README.md](data/results/README.md), and [tests/README.md](tests/README.md).

## Reproducibility and provenance

The project keeps collection, preparation, analysis, validation, and publication formatting separate:

- immutable source downloads and extracted source tables remain local and can be recreated from the published Zenodo artifact;
- `scripts/` prepares source data and converts verified results into publication formats;
- `src/` contains the statistical calculations and validation gates;
- `data/results/manifests/` records pipeline order, input and output hashes, row counts, configurations, software versions, and validation status;
- `process_log.json` records material project transitions and verification evidence; and
- `article/tables/` and `article/figures/` contain the manuscript-facing selections.

Every reported empirical value must trace to a prepared dataset and verified result artifact. Missing origins are not zero-filled, decision counts are not described as application volumes, and the aggregate findings are not interpreted causally.

## License and citation

The repository includes an [MIT License](LICENSE) for its software and associated documentation. The upstream Zenodo data artifact is distributed under CC BY 4.0; consult its record for attribution requirements. Manuscript citation details will be added when a stable publication or preprint record is available. Until then, cite the data paper and data artifact above when reusing their data.
