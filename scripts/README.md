# Preparation, Reproduction, and Publication Scripts

This directory is reserved for reproducible data preparation and general project tasks. Statistical research analysis belongs under `src/`, with corresponding tests under `tests/`.

Current preparation utilities are:

- `prepare_new_zealand.py` — build annual and combined New Zealand source-label decision tables;
- `prepare_australia.py` — filter and aggregate annual and combined Australian source-label decision tables;
- `extract_un_m49.py` — extract the preserved English UN M49 reference table; and
- `check_country_names.py` — normalize annual AU/NZ tables and combine the normalized years.

The repository-level entry point is:

- `reproduce_article.py` — check the required local inputs, run preparation, execute the dependency-ordered research pipeline, regenerate the manuscript-facing tables and figures, and optionally run the tests and build the PDF.

The current article-production utilities are:

- `generate_article_model_composition_outputs.py` — verify the Section 8 manifest and generate the applicant-origin composition table and ranked-share/Lorenz figure imported by the manuscript.
- `generate_article_temporal_sensitivity_outputs.py` — verify the Section 9 manifest and generate the annual destination table and annual matched-origin figure imported by the manuscript.
- `generate_article_b_decomposition_outputs.py` — verify the Section 16 manifest and generate this article's common-weight and decomposition tables, annual composition table, and annual component figure. The historical `article_b` filename is retained because it is a stable pipeline identifier.
- `generate_article_b_relative_origin_share.py` — generate the relative-representation figure from the verified matched-origin share points. The x-axis shows the geometric mean decision share and the y-axis shows the base-2 Australian/New Zealand share ratio.
- `generate_article_b_proportional_share_squares.py` — generate the manuscript's proportional-share-square figure. Each square's area is proportional to an origin's share of destination decisions, and both strips have equal total area, exposing differences in concentration rather than decision volume.

Preparation scripts produce or validate inputs for the research analysis. Article-production scripts may convert verified result artifacts into publication tables or figures, but they must not replace research analysis or calculate unrecorded statistical findings. Descriptive, inferential, and modelling logic belongs under `src/`. The planned research modules, dependencies, and outputs are documented in [`../src/README.md`](../src/README.md).

Reproduce the complete article from the selectively extracted inputs with:

```bash
python3 scripts/reproduce_article.py --run-tests --build-pdf
```

To regenerate publication outputs individually after the analysis pipeline has passed:

```bash
python3 scripts/generate_article_model_composition_outputs.py
python3 scripts/generate_article_temporal_sensitivity_outputs.py
python3 scripts/generate_article_b_decomposition_outputs.py
python3 scripts/generate_article_b_proportional_share_squares.py
python3 scripts/generate_article_b_relative_origin_share.py --no-compile
```

Preparation scripts may have regression tests under `tests/`. In particular, `tests/test_prepare_new_zealand.py` runs the New Zealand preparation entry point and compares its combined output with the previous article fixture under `tests/data/`.
