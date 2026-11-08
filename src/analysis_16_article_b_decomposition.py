"""Common-weight standardisation and composition decomposition for Article B."""

from __future__ import annotations

import argparse
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from .analysis_08_origin_composition import concentration
from .analysis_common import (
    PROJECT_ROOT,
    display_path,
    quantile_type7,
    read_csv_rows,
    read_json,
    require_columns,
    require_passed_blocking_checks,
    sha256,
    utc_timestamp,
    write_csv,
    write_json,
)


STANDARDISATION_COLUMNS = [
    "scope", "year", "support_rule", "minimum_decisions_each", "weight_scheme",
    "n_origins", "au_support_decisions", "nz_support_decisions",
    "au_full_decisions", "nz_full_decisions", "au_decision_coverage",
    "nz_decision_coverage", "au_standardised_rate", "nz_standardised_rate",
    "au_minus_nz_difference", "difference_ci_lower", "difference_ci_upper",
    "difference_bootstrap_p_value", "confidence_level", "bootstrap_replicates",
    "bootstrap_seed",
]
DECOMPOSITION_COLUMNS = [
    "scope", "year", "support_rule", "minimum_decisions_each", "n_origins",
    "au_support_decisions", "nz_support_decisions", "au_full_decisions",
    "nz_full_decisions", "au_decision_coverage", "nz_decision_coverage",
    "au_observed_rate", "nz_observed_rate", "observed_gap",
    "observed_gap_ci_lower", "observed_gap_ci_upper", "observed_gap_bootstrap_p_value",
    "rate_component", "rate_component_ci_lower", "rate_component_ci_upper",
    "rate_component_bootstrap_p_value", "composition_component",
    "composition_component_ci_lower", "composition_component_ci_upper",
    "composition_component_bootstrap_p_value",
    "reconstructed_gap", "identity_error", "confidence_level",
    "bootstrap_replicates", "bootstrap_seed",
]
ANNUAL_COMPOSITION_COLUMNS = [
    "year", "destination_code", "destination_country", "represented_origins",
    "destination_decision_total", "top_1_share", "top_5_share", "top_10_share",
    "median_origin_share", "hhi_0_1", "gini",
]


def _matched_rows(path: Path, *, annual: bool) -> list[dict[str, Any]]:
    source = read_csv_rows(path)
    required = {
        "country", "au_number_approved", "au_number_declined", "au_decision_total",
        "au_approval_rate", "nz_number_approved", "nz_number_declined",
        "nz_decision_total", "nz_approval_rate",
    }
    if annual:
        required.add("year")
    require_columns(path, source, required)
    parsed: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for line_number, row in enumerate(source, start=2):
        key = (row["country"], int(row["year"])) if annual else (row["country"],)
        if not row["country"] or key in seen:
            raise ValueError(f"{path}:{line_number}: empty or duplicate matched key")
        seen.add(key)
        item: dict[str, Any] = {"country": row["country"]}
        if annual:
            item["year"] = int(row["year"])
        for prefix in ("au", "nz"):
            approved = int(row[f"{prefix}_number_approved"])
            declined = int(row[f"{prefix}_number_declined"])
            total = int(row[f"{prefix}_decision_total"])
            rate = float(row[f"{prefix}_approval_rate"])
            if min(approved, declined) < 0 or total <= 0 or approved + declined != total:
                raise ValueError(f"{path}:{line_number}: invalid {prefix.upper()} counts")
            if not math.isclose(rate, approved / total, rel_tol=0.0, abs_tol=1e-15):
                raise ValueError(f"{path}:{line_number}: invalid {prefix.upper()} rate")
            item[f"{prefix}_approved"] = approved
            item[f"{prefix}_decisions"] = total
            item[f"{prefix}_rate"] = rate
        parsed.append(item)
    return parsed


def _long_totals_and_annual_composition(
    pooled_path: Path, annual_path: Path, years: list[int]
) -> tuple[dict[str, int], dict[tuple[int, str], int], list[dict[str, Any]]]:
    pooled = read_csv_rows(pooled_path)
    annual = read_csv_rows(annual_path)
    required = {"destination_code", "destination_country", "country", "decision_total"}
    require_columns(pooled_path, pooled, required)
    require_columns(annual_path, annual, required | {"year"})
    pooled_totals: dict[str, int] = defaultdict(int)
    for row in pooled:
        total = int(row["decision_total"])
        if row["destination_code"] not in {"AU", "NZ"} or total <= 0:
            raise ValueError(f"{pooled_path}: invalid destination or decision total")
        pooled_totals[row["destination_code"]] += total
    annual_groups: dict[tuple[int, str], list[dict[str, str]]] = defaultdict(list)
    for row in annual:
        year = int(row["year"])
        code = row["destination_code"]
        total = int(row["decision_total"])
        if year not in years or code not in {"AU", "NZ"} or total <= 0:
            raise ValueError(f"{annual_path}: invalid year, destination, or decision total")
        annual_groups[(year, code)].append(row)
    expected = {(year, code) for year in years for code in ("AU", "NZ")}
    if set(annual_groups) != expected:
        raise ValueError(f"{annual_path}: incomplete destination-year coverage")
    annual_totals: dict[tuple[int, str], int] = {}
    composition_rows: list[dict[str, Any]] = []
    for year, code in sorted(expected):
        group = annual_groups[(year, code)]
        total = sum(int(row["decision_total"]) for row in group)
        annual_totals[(year, code)] = total
        metrics = concentration([int(row["decision_total"]) / total for row in group])
        composition_rows.append({
            "year": year,
            "destination_code": code,
            "destination_country": group[0]["destination_country"],
            "represented_origins": len(group),
            "destination_decision_total": total,
            **metrics,
        })
    return dict(pooled_totals), annual_totals, composition_rows


def estimate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return exact observed, common-weight, and symmetric decomposition estimates."""
    if not rows:
        raise ValueError("standardisation requires at least one matched origin")
    au_total = sum(int(row["au_decisions"]) for row in rows)
    nz_total = sum(int(row["nz_decisions"]) for row in rows)
    if min(au_total, nz_total) <= 0:
        raise ValueError("standardisation requires positive destination totals")
    w_au = [int(row["au_decisions"]) / au_total for row in rows]
    w_nz = [int(row["nz_decisions"]) / nz_total for row in rows]
    p_au = [float(row["au_rate"]) for row in rows]
    p_nz = [float(row["nz_rate"]) for row in rows]
    schemes = {
        "observed_destination_specific": (w_au, w_nz),
        "average_destination_shares": (
            [(a + n) / 2.0 for a, n in zip(w_au, w_nz)],
            [(a + n) / 2.0 for a, n in zip(w_au, w_nz)],
        ),
        "australia_shares": (w_au, w_au),
        "new_zealand_shares": (w_nz, w_nz),
        "equal_origin": ([1.0 / len(rows)] * len(rows), [1.0 / len(rows)] * len(rows)),
    }
    standardised: dict[str, tuple[float, float, float]] = {}
    for name, (q_au, q_nz) in schemes.items():
        au_rate = sum(weight * rate for weight, rate in zip(q_au, p_au))
        nz_rate = sum(weight * rate for weight, rate in zip(q_nz, p_nz))
        standardised[name] = (au_rate, nz_rate, au_rate - nz_rate)
    observed_gap = standardised["observed_destination_specific"][2]
    rate_component = sum(
        ((a + n) / 2.0) * (pa - pn)
        for a, n, pa, pn in zip(w_au, w_nz, p_au, p_nz)
    )
    composition_component = sum(
        (a - n) * ((pa + pn) / 2.0)
        for a, n, pa, pn in zip(w_au, w_nz, p_au, p_nz)
    )
    reconstructed = rate_component + composition_component
    if not math.isclose(observed_gap, reconstructed, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("symmetric decomposition identity did not reconcile")
    return {
        "au_support_decisions": au_total,
        "nz_support_decisions": nz_total,
        "standardised": standardised,
        "observed_gap": observed_gap,
        "rate_component": rate_component,
        "composition_component": composition_component,
        "reconstructed_gap": reconstructed,
        "identity_error": observed_gap - reconstructed,
    }


def bootstrap_p_value(values: list[float], observed: float) -> float:
    """Return a two-sided bootstrap tail p-value around zero."""
    if not values:
        raise ValueError("bootstrap p-value requires replicate estimates")
    if observed == 0:
        return 1.0
    lower = (sum(value <= 0 for value in values) + 1.0) / (len(values) + 1.0)
    upper = (sum(value >= 0 for value in values) + 1.0) / (len(values) + 1.0)
    return min(1.0, 2.0 * min(lower, upper))


def _bootstrap(
    rows: list[dict[str, Any]], *, replicates: int, seed: int, confidence: float
) -> tuple[
    dict[str, tuple[float, float]], dict[str, float],
    dict[str, tuple[float, float]], dict[str, float],
]:
    if replicates <= 0:
        raise ValueError("bootstrap replicate count must be positive")
    generator = random.Random(seed)
    n = len(rows)
    scheme_values = {name: [] for name in (
        "observed_destination_specific", "average_destination_shares",
        "australia_shares", "new_zealand_shares", "equal_origin",
    )}
    component_values = {name: [] for name in (
        "observed_gap", "rate_component", "composition_component",
    )}
    for _ in range(replicates):
        sample = [rows[generator.randrange(n)] for _ in range(n)]
        value = estimate(sample)
        for name in scheme_values:
            scheme_values[name].append(value["standardised"][name][2])
        for name in component_values:
            component_values[name].append(value[name])
    alpha = 1.0 - confidence
    interval = lambda values: (
        quantile_type7(values, alpha / 2.0),
        quantile_type7(values, 1.0 - alpha / 2.0),
    )
    point = estimate(rows)
    return (
        {name: interval(values) for name, values in scheme_values.items()},
        {name: bootstrap_p_value(values, point["standardised"][name][2]) for name, values in scheme_values.items()},
        {name: interval(values) for name, values in component_values.items()},
        {name: bootstrap_p_value(values, point[name]) for name, values in component_values.items()},
    )


def _analysis_rows(
    rows: list[dict[str, Any]], *, scope: str, year: str | int,
    support_rule: str, threshold: int, full_totals: dict[str, int],
    confidence: float, replicates: int, seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected = [
        row for row in rows
        if int(row["au_decisions"]) >= threshold and int(row["nz_decisions"]) >= threshold
    ]
    if len(selected) < 2:
        raise ValueError(f"{scope} {year} threshold {threshold}: fewer than two origins")
    point = estimate(selected)
    scheme_ci, scheme_p, component_ci, component_p = _bootstrap(
        selected, replicates=replicates, seed=seed, confidence=confidence
    )
    common = {
        "scope": scope,
        "year": year,
        "support_rule": support_rule,
        "minimum_decisions_each": threshold,
        "n_origins": len(selected),
        "au_support_decisions": point["au_support_decisions"],
        "nz_support_decisions": point["nz_support_decisions"],
        "au_full_decisions": full_totals["AU"],
        "nz_full_decisions": full_totals["NZ"],
        "au_decision_coverage": point["au_support_decisions"] / full_totals["AU"],
        "nz_decision_coverage": point["nz_support_decisions"] / full_totals["NZ"],
        "confidence_level": confidence,
        "bootstrap_replicates": replicates,
        "bootstrap_seed": seed,
    }
    standards: list[dict[str, Any]] = []
    for scheme, values in point["standardised"].items():
        standards.append({
            **common,
            "weight_scheme": scheme,
            "au_standardised_rate": values[0],
            "nz_standardised_rate": values[1],
            "au_minus_nz_difference": values[2],
            "difference_ci_lower": scheme_ci[scheme][0],
            "difference_ci_upper": scheme_ci[scheme][1],
            "difference_bootstrap_p_value": scheme_p[scheme],
        })
    decomposition = {
        **common,
        "au_observed_rate": point["standardised"]["observed_destination_specific"][0],
        "nz_observed_rate": point["standardised"]["observed_destination_specific"][1],
        "observed_gap": point["observed_gap"],
        "observed_gap_ci_lower": component_ci["observed_gap"][0],
        "observed_gap_ci_upper": component_ci["observed_gap"][1],
        "observed_gap_bootstrap_p_value": component_p["observed_gap"],
        "rate_component": point["rate_component"],
        "rate_component_ci_lower": component_ci["rate_component"][0],
        "rate_component_ci_upper": component_ci["rate_component"][1],
        "rate_component_bootstrap_p_value": component_p["rate_component"],
        "composition_component": point["composition_component"],
        "composition_component_ci_lower": component_ci["composition_component"][0],
        "composition_component_ci_upper": component_ci["composition_component"][1],
        "composition_component_bootstrap_p_value": component_p["composition_component"],
        "reconstructed_gap": point["reconstructed_gap"],
        "identity_error": point["identity_error"],
    }
    return standards, decomposition


def run(
    *, config_path: Path, pooled_long_path: Path, pooled_matched_path: Path,
    annual_long_path: Path, annual_matched_path: Path, validation_checks_path: Path,
    comparability_path: Path, output_dir: Path, manifest_dir: Path,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Path]:
    config = read_json(config_path)
    require_passed_blocking_checks(validation_checks_path)
    gate_rows = read_csv_rows(comparability_path)
    gate = {row["analysis_component"]: row["eligible"].lower() == "true" for row in gate_rows}
    if not gate.get("pooled_paired_analysis") or not gate.get("annual_paired_analysis"):
        raise ValueError("comparability gate rejected a required matched analysis")
    years = [int(year) for year in config["years"]]
    thresholds = [int(value) for value in config["sensitivity_denominator_thresholds"]]
    if thresholds != [0, 20, 50, 100]:
        raise ValueError("Article B decomposition requires thresholds [0, 20, 50, 100]")
    confidence = float(config["confidence_level"])
    replicates = int(config["bootstrap_replicates"])
    base_seed = int(config["bootstrap_seed"])
    method = config.get("article_b_decomposition", {})
    expected_schemes = [
        "observed_destination_specific", "average_destination_shares",
        "australia_shares", "new_zealand_shares", "equal_origin",
    ]
    if (
        method.get("primary_common_weight") != "average_destination_shares"
        or method.get("weight_schemes") != expected_schemes
        or method.get("primary_annual_support") != "year_specific_matched"
        or method.get("temporal_sensitivity_support") != "balanced_four_year_matched"
        or method.get("bootstrap_unit") != "origin_country"
    ):
        raise ValueError("Article B decomposition configuration is incomplete or unsupported")
    pooled = _matched_rows(pooled_matched_path, annual=False)
    annual = _matched_rows(annual_matched_path, annual=True)
    pooled_totals, annual_totals, annual_composition = _long_totals_and_annual_composition(
        pooled_long_path, annual_long_path, years
    )
    if {int(row["year"]) for row in annual} != set(years):
        raise ValueError("matched annual input does not cover every configured year")

    standardisation_rows: list[dict[str, Any]] = []
    decomposition_rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        standards, decomposition = _analysis_rows(
            pooled, scope="pooled", year=config["period"],
            support_rule="origins observed in both destinations in pooled data",
            threshold=threshold, full_totals=pooled_totals, confidence=confidence,
            replicates=replicates, seed=base_seed + threshold,
        )
        standardisation_rows.extend(standards)
        decomposition_rows.append(decomposition)

    by_country: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in annual:
        by_country[row["country"]][int(row["year"])] = row
    balanced_by_threshold: dict[int, set[str]] = {}
    for threshold in thresholds:
        balanced_by_threshold[threshold] = {
            country for country, observations in by_country.items()
            if set(observations) == set(years)
            and all(
                int(row["au_decisions"]) >= threshold
                and int(row["nz_decisions"]) >= threshold
                for row in observations.values()
            )
        }
    for year in years:
        year_rows = [row for row in annual if int(row["year"]) == year]
        full = {code: annual_totals[(year, code)] for code in ("AU", "NZ")}
        for threshold in thresholds:
            standards, decomposition = _analysis_rows(
                year_rows, scope="annual_year_specific", year=year,
                support_rule="origins observed in both destinations in the stated year",
                threshold=threshold, full_totals=full, confidence=confidence,
                replicates=replicates, seed=base_seed + year * 100 + threshold + 1,
            )
            standardisation_rows.extend(standards)
            decomposition_rows.append(decomposition)
            balanced = [row for row in year_rows if row["country"] in balanced_by_threshold[threshold]]
            standards, decomposition = _analysis_rows(
                balanced, scope="annual_balanced", year=year,
                support_rule="origins observed in both destinations in all four years and meeting the threshold in every year",
                threshold=threshold, full_totals=full, confidence=confidence,
                replicates=replicates, seed=base_seed + year * 100 + threshold + 2,
            )
            standardisation_rows.extend(standards)
            decomposition_rows.append(decomposition)

    outputs = {
        "standardisation": output_dir / "common_weight_standardisation.csv",
        "decomposition": output_dir / "rate_composition_decomposition.csv",
        "annual_composition": output_dir / "annual_composition_statistics.csv",
        "manifest": manifest_dir / "16_article_b_decomposition.json",
    }
    write_csv(outputs["standardisation"], STANDARDISATION_COLUMNS, standardisation_rows)
    write_csv(outputs["decomposition"], DECOMPOSITION_COLUMNS, decomposition_rows)
    write_csv(outputs["annual_composition"], ANNUAL_COMPOSITION_COLUMNS, annual_composition)
    input_paths = (
        config_path, pooled_long_path, pooled_matched_path, annual_long_path,
        annual_matched_path, validation_checks_path, comparability_path,
    )
    write_json(outputs["manifest"], {
        "module": "src.analysis_16_article_b_decomposition",
        "status": "passed",
        "analysis_timestamp_utc": utc_timestamp(),
        "configuration": {
            "years": years,
            "thresholds": thresholds,
            "primary_common_weight": method["primary_common_weight"],
            "weight_schemes": method["weight_schemes"],
            "primary_annual_support": method["primary_annual_support"],
            "temporal_sensitivity_support": method["temporal_sensitivity_support"],
            "decomposition": "symmetric two-factor rate and composition identity",
            "bootstrap_unit": method["bootstrap_unit"],
            "bootstrap_p_value": "two-sided bootstrap tail probability around zero with plus-one correction in each tail",
            "confidence_level": confidence,
            "bootstrap_replicates": replicates,
            "bootstrap_seed": base_seed,
        },
        "inputs": [
            {"path": display_path(path, project_root), "sha256": sha256(path)}
            for path in input_paths
        ],
        "outputs": [
            {"name": name, "path": display_path(path, project_root), "sha256": sha256(path)}
            for name, path in outputs.items() if name != "manifest"
        ],
        "row_counts": {
            "common_weight_standardisation": len(standardisation_rows),
            "rate_composition_decomposition": len(decomposition_rows),
            "annual_composition_statistics": len(annual_composition),
        },
        "validation": {
            "maximum_absolute_identity_error": max(abs(float(row["identity_error"])) for row in decomposition_rows),
            "balanced_origins_threshold_0": len(balanced_by_threshold[0]),
            "missing_origins_zero_filled": False,
        },
        "interpretation_warning": "Components are descriptive accounting relationships under specified supports and weights; they are not causal effects.",
    })
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "src/analysis_config.json")
    parser.add_argument("--pooled-long", type=Path, default=PROJECT_ROOT / "data/prepared/comparison/destination_country_2022-2025.csv")
    parser.add_argument("--pooled-matched", type=Path, default=PROJECT_ROOT / "data/prepared/comparison/matched_country_2022-2025.csv")
    parser.add_argument("--annual-long", type=Path, default=PROJECT_ROOT / "data/prepared/comparison/destination_country_year.csv")
    parser.add_argument("--annual-matched", type=Path, default=PROJECT_ROOT / "data/prepared/comparison/matched_country_year.csv")
    parser.add_argument("--validation-checks", type=Path, default=PROJECT_ROOT / "data/results/validation/data_validation_checks.csv")
    parser.add_argument("--comparability", type=Path, default=PROJECT_ROOT / "data/results/validation/comparability_decisions.csv")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data/results/decomposition")
    parser.add_argument("--manifest-dir", type=Path, default=PROJECT_ROOT / "data/results/manifests")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outputs = run(
        config_path=args.config, pooled_long_path=args.pooled_long,
        pooled_matched_path=args.pooled_matched, annual_long_path=args.annual_long,
        annual_matched_path=args.annual_matched,
        validation_checks_path=args.validation_checks,
        comparability_path=args.comparability, output_dir=args.output_dir,
        manifest_dir=args.manifest_dir,
    )
    print("Article B decomposition artifacts written:")
    for path in outputs.values():
        print(f"- {display_path(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
