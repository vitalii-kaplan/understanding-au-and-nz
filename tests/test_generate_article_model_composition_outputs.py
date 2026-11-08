"""Tests for the article's Section 8 composition publication outputs."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.generate_article_model_composition_outputs import generate_outputs


class ArticleModelCompositionOutputsTest(unittest.TestCase):
    def test_outputs_use_verified_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outputs = generate_outputs(table_dir=root / "tables", figure_dir=root / "figures")
            composition = outputs["composition_table"].read_text(encoding="utf-8")
            curves = outputs["composition_curves"].read_text(encoding="utf-8")
            self.assertEqual(set(outputs), {"composition_table", "composition_curves"})
            self.assertIn("0.177", composition)
            self.assertIn("0.111", composition)
            self.assertIn("[0.805, 0.896]", composition)
            self.assertIn("Jensen--Shannon divergence was not calculated", composition)
            self.assertEqual(composition.count(r"\begin{tabular*}{\textwidth}"), 2)
            self.assertEqual(composition.count(r"@{\extracolsep{\fill}}"), 2)
            self.assertIn(r"\small", composition)
            self.assertNotIn(r"\resizebox", composition)
            self.assertIn("semilogyaxis", curves)
            self.assertIn("Lorenz curves", curves)


if __name__ == "__main__":
    unittest.main()
