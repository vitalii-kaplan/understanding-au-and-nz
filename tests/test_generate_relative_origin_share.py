"""Tests for the relative applicant-origin representation figure."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.generate_relative_origin_share import (
    generate,
    select_labels,
    transformed_rows,
)


ROOT = Path(__file__).resolve().parents[1]


class RelativeOriginShareTest(unittest.TestCase):
    def test_transformation_and_label_rule(self) -> None:
        with (ROOT / "data/results/composition/share_scatter_points.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = transformed_rows(list(csv.DictReader(handle)))
        self.assertEqual(len(rows), 173)
        self.assertEqual(
            select_labels(rows),
            [
                "China",
                "India",
                "Nepal",
                "Bhutan",
                "Germany",
                "Tonga",
                "North Macedonia",
                "Kiribati",
                "Benin",
                "Uzbekistan",
                "Democratic People's Republic of Korea",
            ],
        )

    def test_generates_separate_verified_figure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "relative.tex"
            result = generate(output_tex=output, compile_image=False)
            source = output.read_text(encoding="utf-8")
            self.assertEqual(len(result["labels"]), 11)
            self.assertIn(r"\begin{semilogxaxis}", source)
            self.assertIn(r"\log_2(\mathrm{AU\ share}/\mathrm{NZ\ share})", source)
            self.assertIn(r"Relatively larger share\\in Australia", source)
            self.assertIn(r"Relatively larger share\\in New Zealand", source)
            self.assertIn(r"\addplot[gray!70,dashed", source)
            self.assertIn("North Macedonia", source)
            self.assertIn("Kiribati", source)
            self.assertIn("DPR Korea", source)
            self.assertIn("Uzbekistan", source)
            self.assertIn("Benin", source)
            self.assertNotIn("{Kenya}", source)
            self.assertNotIn("{Brazil}", source)
            self.assertNotIn("origin_share_scatter_labeled", source)


if __name__ == "__main__":
    unittest.main()
