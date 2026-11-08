#!/usr/bin/env python3
"""Reproduce the analysis and manuscript from selectively extracted inputs."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_INITIAL_INPUTS = (
    ROOT / "data/original/australia/student_visa_grant_rates_2005_2026-02-28.csv",
    ROOT / "data/original/new-zealand/student_visa_decisions_2022.csv",
    ROOT / "data/original/new-zealand/student_visa_decisions_2023.csv",
    ROOT / "data/original/new-zealand/student_visa_decisions_2024.csv",
    ROOT / "data/original/new-zealand/student_visa_decisions_2025.csv",
    ROOT / "data/original/reference/un-m49-overview.html",
    ROOT / "data/reference/country_aliases.csv",
)
PREPARATION_MODULES = (
    "scripts.prepare_new_zealand",
    "scripts.prepare_australia",
    "scripts.extract_un_m49",
    "scripts.check_country_names",
)
PUBLICATION_MODULES = (
    "scripts.generate_article_model_composition_outputs",
    "scripts.generate_article_temporal_sensitivity_outputs",
    "scripts.generate_article_b_decomposition_outputs",
    "scripts.generate_article_b_proportional_share_squares",
)
PUBLICATION_COMMANDS = (
    ("scripts.generate_article_b_relative_origin_share", "--no-compile"),
)


def require_initial_inputs() -> None:
    missing = [path.relative_to(ROOT) for path in REQUIRED_INITIAL_INPUTS if not path.exists()]
    if missing:
        listing = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Required source inputs are missing. Follow data/README.md to download "
            f"and selectively extract them:\n{listing}"
        )


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def generate_publication_outputs() -> None:
    for module in PUBLICATION_MODULES:
        run([sys.executable, "-m", module])
    for module, option in PUBLICATION_COMMANDS:
        run([sys.executable, "-m", module, option])


def run_research_pipeline() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.analysis_15_run_pipeline import run as run_pipeline
    from src.analysis_15_run_pipeline import subprocess_runner

    publication_generated = False

    def runner(module: str) -> tuple[int, str]:
        nonlocal publication_generated
        if module == "src.analysis_12_reproducibility" and not publication_generated:
            try:
                generate_publication_outputs()
            except subprocess.CalledProcessError as error:
                return error.returncode, "publication-output generation failed"
            publication_generated = True
        return subprocess_runner(module)

    run_pipeline(
        status_path=ROOT / "data/results/manifests/pipeline_stage_status.csv",
        gate_path=ROOT / "data/results/validation/comparability_decisions.csv",
        manifest_dir=ROOT / "data/results/manifests",
        runner=runner,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-preparation",
        action="store_true",
        help="reuse existing prepared inputs and begin with the analysis pipeline",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="run the complete unittest suite after reproducing the outputs",
    )
    parser.add_argument(
        "--build-pdf",
        action="store_true",
        help="compile article/article.pdf with latexmk after regenerating outputs",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.skip_preparation:
        require_initial_inputs()
        for module in PREPARATION_MODULES:
            run([sys.executable, "-m", module])

    run_research_pipeline()

    if args.run_tests:
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
    if args.build_pdf:
        run(
            [
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "article.tex",
            ],
            cwd=ROOT / "article",
        )

    print("Article reproduction completed successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Reproduction failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
