"""Tests for the manuscript's proportional decision-share-square figure."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.generate_article_b_proportional_share_squares import generate


class ArticleBProportionalShareSquaresTest(unittest.TestCase):
    def test_square_area_is_proportional_to_verified_share(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "share_squares.tex"
            result = generate(output_tex=output)
            self.assertAlmostEqual(result["maximum"], 0.3210514, places=6)
            self.assertAlmostEqual(result["au_area"], result["nz_area"], places=9)
            self.assertAlmostEqual(result["au_area"], 1 / result["maximum"], places=9)
            self.assertGreater(result["nz_width"], result["au_width"])
            source = output.read_text(encoding="utf-8")
            self.assertEqual(source.count(r"\filldraw["), 192 + 179)
            self.assertNotIn("Preview only", source)
            self.assertNotIn("Decision shares as proportional squares", source)


if __name__ == "__main__":
    unittest.main()
