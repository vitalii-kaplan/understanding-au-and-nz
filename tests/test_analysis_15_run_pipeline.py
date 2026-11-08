"""Tests for the Step 15 dependency-ordered pipeline runner."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from src.analysis_15_run_pipeline import STAGES, execute_pipeline


class PipelineRunnerTest(unittest.TestCase):
    def write_gate(self, path: Path, *, pooled: bool = True, model: bool = True, annual: bool = True) -> None:
        path.write_text(
            "analysis_component,eligible\n"
            f"pooled_paired_analysis,{str(pooled).lower()}\n"
            f"country_year_binomial_model,{str(model).lower()}\n"
            f"annual_paired_analysis,{str(annual).lower()}\n",
            encoding="utf-8",
        )

    def test_executes_dependency_order_and_records_skips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            gate = target / "gate.csv"
            self.write_gate(gate, model=False, annual=False)
            called: list[str] = []
            passed, rows = execute_pipeline(status_path=target / "status.csv", gate_path=gate, runner=lambda module: (called.append(module) or 0, "ok"))
            self.assertTrue(passed)
            self.assertEqual([row["step"] for row in rows], [step for step, _ in STAGES])
            self.assertEqual([row["step"] for row in rows if row["status"] == "skipped"], ["07", "09", "16"])
            self.assertIn("src.analysis_08_origin_composition", called)
            self.assertNotIn("src.analysis_07_binomial_regression", called)

    def test_stops_after_first_failed_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            gate = target / "gate.csv"
            self.write_gate(gate)
            def runner(module: str) -> tuple[int, str]:
                return (2, "controlled failure") if module == "src.analysis_04_matched_comparison" else (0, "ok")
            passed, rows = execute_pipeline(status_path=target / "status.csv", gate_path=gate, runner=runner)
            self.assertFalse(passed)
            self.assertEqual(rows[-1]["step"], "04")
            self.assertEqual(rows[-1]["status"], "failed")
            with (target / "status.csv").open(newline="", encoding="utf-8") as handle:
                written = list(csv.DictReader(handle))
            self.assertEqual(len(written), len(rows))


if __name__ == "__main__":
    unittest.main()
