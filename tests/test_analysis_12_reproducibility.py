"""Tests for the Step 12 reproducibility consolidator."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from src.analysis_12_reproducibility import SOURCE_MANIFESTS, run


ROOT = Path(__file__).resolve().parents[1]


class ReproducibilityTest(unittest.TestCase):
    def test_registers_verified_results_and_publication_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            for name in SOURCE_MANIFESTS:
                source = ROOT / "data/results/manifests" / name
                (target / source.name).write_bytes(source.read_bytes())
            outputs = run(
                manifest_dir=target,
                table_dir=ROOT / "article/tables",
                figure_dir=ROOT / "article/figures",
            )
            with outputs["artifact_manifest"].open(newline="", encoding="utf-8") as handle:
                artifacts = list(csv.DictReader(handle))
            self.assertGreater(len(artifacts), 60)
            self.assertTrue(all(row["status"] == "verified" for row in artifacts))
            self.assertIn("data/results/models/binomial_model_coefficients.csv", {row["path"] for row in artifacts})
            self.assertIn(
                "article/figures/annual_decomposition_components.tex",
                {row["path"] for row in artifacts},
            )
            editorial = next(
                row
                for row in artifacts
                if row["path"] == "article/tables/discussion_question_answers.tex"
            )
            self.assertEqual(editorial["producer"], "editorial manuscript synthesis")
            self.assertEqual(outputs["reproducibility_issues"].read_text(encoding="utf-8").count("\n"), 1)
            self.assertIn("Rscript", outputs["software_versions"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
