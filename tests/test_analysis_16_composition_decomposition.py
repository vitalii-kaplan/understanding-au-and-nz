"""Tests for common-weight standardisation and composition decomposition."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.analysis_16_composition_decomposition import bootstrap_p_value, estimate, run


ROOT = Path(__file__).resolve().parents[1]


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class CompositionDecompositionTest(unittest.TestCase):
    def test_symmetric_identity_and_common_weights(self) -> None:
        rows = [
            {"country": "A", "au_decisions": 80, "nz_decisions": 20,
             "au_rate": 0.8, "nz_rate": 0.4},
            {"country": "B", "au_decisions": 20, "nz_decisions": 80,
             "au_rate": 0.2, "nz_rate": 0.1},
        ]
        result = estimate(rows)
        self.assertAlmostEqual(result["observed_gap"], 0.52)
        self.assertAlmostEqual(result["rate_component"], 0.25)
        self.assertAlmostEqual(result["composition_component"], 0.27)
        self.assertAlmostEqual(result["reconstructed_gap"], 0.52)
        self.assertAlmostEqual(result["identity_error"], 0.0)
        average = result["standardised"]["average_destination_shares"]
        self.assertAlmostEqual(average[0], 0.5)
        self.assertAlmostEqual(average[1], 0.25)
        self.assertAlmostEqual(average[2], result["rate_component"])

    def test_rejects_empty_support(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one"):
            estimate([])

    def test_two_sided_bootstrap_tail_p_value_uses_plus_one_correction(self) -> None:
        self.assertAlmostEqual(bootstrap_p_value([1.8, 2.0, 2.2], 2.0), 0.5)
        self.assertEqual(bootstrap_p_value([-1.0, 0.0, 1.0], 0.0), 1.0)
        with self.assertRaisesRegex(ValueError, "replicate"):
            bootstrap_p_value([], 1.0)

    def test_project_inputs_generate_deterministic_verified_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            config = json.loads((ROOT / "src/analysis_config.json").read_text(encoding="utf-8"))
            config["bootstrap_replicates"] = 100
            config_path = target / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            def execute(name: str) -> dict[str, Path]:
                base = target / name
                return run(
                    config_path=config_path,
                    pooled_long_path=ROOT / "data/prepared/comparison/destination_country_2022-2025.csv",
                    pooled_matched_path=ROOT / "data/prepared/comparison/matched_country_2022-2025.csv",
                    annual_long_path=ROOT / "data/prepared/comparison/destination_country_year.csv",
                    annual_matched_path=ROOT / "data/prepared/comparison/matched_country_year.csv",
                    validation_checks_path=ROOT / "data/results/validation/data_validation_checks.csv",
                    comparability_path=ROOT / "data/results/validation/comparability_decisions.csv",
                    output_dir=base / "results",
                    manifest_dir=base / "manifests",
                )

            first = execute("first")
            second = execute("second")
            standards = csv_rows(first["standardisation"])
            decompositions = csv_rows(first["decomposition"])
            annual_composition = csv_rows(first["annual_composition"])
            self.assertEqual(len(standards), 180)
            self.assertEqual(len(decompositions), 36)
            self.assertEqual(len(annual_composition), 8)
            self.assertTrue(all(abs(float(row["identity_error"])) < 1e-12 for row in decompositions))
            self.assertTrue(all(0 < float(row["observed_gap_bootstrap_p_value"]) <= 1 for row in decompositions))
            self.assertTrue(all(0 < float(row["difference_bootstrap_p_value"]) <= 1 for row in standards))
            self.assertEqual(
                {row["weight_scheme"] for row in standards},
                {"observed_destination_specific", "average_destination_shares",
                 "australia_shares", "new_zealand_shares", "equal_origin"},
            )
            balanced = [
                row for row in decompositions
                if row["scope"] == "annual_balanced"
                and row["year"] == "2022"
                and row["minimum_decisions_each"] == "0"
            ]
            self.assertEqual(len(balanced), 1)
            self.assertEqual(int(balanced[0]["n_origins"]), 118)
            self.assertEqual(first["standardisation"].read_bytes(), second["standardisation"].read_bytes())
            self.assertEqual(first["decomposition"].read_bytes(), second["decomposition"].read_bytes())
            manifest = json.loads(first["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "passed")
            self.assertFalse(manifest["validation"]["missing_origins_zero_filled"])


if __name__ == "__main__":
    unittest.main()
