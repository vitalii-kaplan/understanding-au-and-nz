"""Tests for the article's Section 9 publication outputs."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.generate_article_temporal_sensitivity_outputs import generate_outputs


ROOT = Path(__file__).resolve().parents[1]


class TemporalSensitivityPublicationTest(unittest.TestCase):
    def test_generates_tables_and_figures_from_verified_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            outputs = generate_outputs(
                temporal_dir=ROOT / "data/results/temporal",
                manifest_dir=ROOT / "data/results/manifests",
                table_dir=target / "tables", figure_dir=target / "figures",
            )
            self.assertEqual(
                set(outputs), {"destination_table", "matched_differences_figure"}
            )
            for path in outputs.values():
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 100)
            destination_table = outputs["destination_table"].read_text(encoding="utf-8")
            self.assertEqual(destination_table.count(r"\begin{table}"), 1)
            self.assertIn(r"\label{tab:annual-destination-summary}", destination_table)
            self.assertIn(r"\begin{tabular*}{\textwidth}", destination_table)
            self.assertIn(r"@{\extracolsep{\fill}}", destination_table)
            self.assertIn(r"\small", destination_table)
            self.assertNotIn(r"\resizebox", destination_table)
            differences = outputs["matched_differences_figure"].read_text(
                encoding="utf-8"
            )
            self.assertIn("Mean (Student-$t$ CI)", differences)
            self.assertIn("Median (bootstrap CI)", differences)
            self.assertIn("2022", differences)
            self.assertIn("2025", differences)


if __name__ == "__main__":
    unittest.main()
