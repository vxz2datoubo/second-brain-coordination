from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


CONTROL_TOWER = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(CONTROL_TOWER) not in sys.path:
    sys.path.insert(0, str(CONTROL_TOWER))

from evals.r157_ranking_calibration import (  # noqa: E402
    AUTHORITY_BOUNDARY,
    REPORT_SCHEMA,
    SCENARIO_SCHEMA,
    SUBJECT_REF,
    RankingCalibrationError,
    evaluate_corpus,
    validate_corpus,
)


SCENARIO_PATH = (
    REPO_ROOT
    / "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R157/"
    "RANKING-CALIBRATION-SCENARIOS.json"
)


def _load_corpus() -> dict:
    return json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))


class R157RankingCalibrationTests(unittest.TestCase):
    def test_canonical_scenario_corpus_passes_all_families(self) -> None:
        report = evaluate_corpus(_load_corpus())
        self.assertEqual(report["schema_version"], REPORT_SCHEMA)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["total_scenarios"], 14)
        self.assertEqual(report["passed_scenarios"], 14)
        self.assertEqual(report["failed_scenarios"], 0)
        self.assertEqual(len(report["report_digest"]), 64)

    def test_required_coverage_matrix_is_mechanically_present(self) -> None:
        normalized = validate_corpus(_load_corpus())
        scenarios = normalized["scenarios"]
        kinds = {item["kind"] for item in scenarios}
        self.assertEqual(
            kinds,
            {
                "MONOTONIC_AXIS",
                "AGE_CAP_PLATEAU",
                "PRIORITY_DOMINANCE",
                "LEXICAL_TIE_BREAK",
                "PERMUTATION_INVARIANCE",
            },
        )
        axes = {
            item["axis"]
            for item in scenarios
            if item["kind"] == "MONOTONIC_AXIS"
        }
        self.assertEqual(
            axes,
            {
                "user_value_score",
                "materiality_score",
                "dependency_readiness_score",
                "age_cycles",
                "estimated_cost_score",
            },
        )
        modes = {
            item["mode"]
            for item in scenarios
            if item["kind"] == "PERMUTATION_INVARIANCE"
        }
        self.assertEqual(modes, {"LEXICAL_TIE", "HETEROGENEOUS_RANK_KEYS"})

    def test_heterogeneous_permutation_is_order_invariant_and_nonlexical(self) -> None:
        report = evaluate_corpus(_load_corpus())
        result = next(
            item
            for item in report["results"]
            if item["scenario_id"] == "PERMUTATION-HETEROGENEOUS-001"
        )
        observed = result["observed"]
        self.assertTrue(result["passed"])
        self.assertEqual(observed["mode"], "HETEROGENEOUS_RANK_KEYS")
        self.assertEqual(observed["expected_winner"], "opportunity-z-high")
        self.assertEqual(observed["forward_winner"], "opportunity-z-high")
        self.assertEqual(observed["reverse_winner"], "opportunity-z-high")
        self.assertEqual(observed["rotated_winner"], "opportunity-z-high")
        self.assertNotEqual(observed["expected_winner"], min(observed["candidate_keys"]))
        prefixes = {tuple(key[:-1]) for key in observed["candidate_keys"].values()}
        self.assertGreater(len(prefixes), 1)

    def test_lexical_tie_permutation_remains_distinct(self) -> None:
        report = evaluate_corpus(_load_corpus())
        result = next(
            item
            for item in report["results"]
            if item["scenario_id"] == "PERMUTATION-TIE-001"
        )
        observed = result["observed"]
        self.assertTrue(result["passed"])
        self.assertEqual(observed["mode"], "LEXICAL_TIE")
        self.assertEqual(observed["expected_winner"], "opportunity-a")
        prefixes = {tuple(key[:-1]) for key in observed["candidate_keys"].values()}
        self.assertEqual(len(prefixes), 1)

    def test_missing_permutation_mode_fails_closed(self) -> None:
        corpus = _load_corpus()
        corpus["scenarios"] = [
            item
            for item in corpus["scenarios"]
            if item["scenario_id"] != "PERMUTATION-HETEROGENEOUS-001"
        ]
        with self.assertRaisesRegex(
            RankingCalibrationError, "REQUIRED_PERMUTATION_MODE_MISSING"
        ):
            validate_corpus(corpus)

    def test_heterogeneous_mode_rejects_equal_rank_key_prefixes(self) -> None:
        corpus = _load_corpus()
        target = next(
            item
            for item in corpus["scenarios"]
            if item["scenario_id"] == "PERMUTATION-HETEROGENEOUS-001"
        )
        first = target["candidates"][0]
        for candidate in target["candidates"][1:]:
            for field in (
                "priority_class",
                "user_value_score",
                "materiality_score",
                "dependency_readiness_score",
                "age_cycles",
                "estimated_cost_score",
            ):
                candidate[field] = first[field]
        with self.assertRaisesRegex(
            RankingCalibrationError, "PERMUTATION_KEYS_NOT_HETEROGENEOUS"
        ):
            validate_corpus(corpus)

    def test_report_is_repeatable_for_identical_corpus(self) -> None:
        corpus = _load_corpus()
        first = evaluate_corpus(corpus)
        second = evaluate_corpus(copy.deepcopy(corpus))
        self.assertEqual(first, second)
        self.assertEqual(first["report_digest"], second["report_digest"])

    def test_report_binds_exact_retained_r151_subject(self) -> None:
        corpus = _load_corpus()
        self.assertEqual(corpus["schema_version"], SCENARIO_SCHEMA)
        self.assertEqual(corpus["subject_ref"], SUBJECT_REF)
        report = evaluate_corpus(corpus)
        self.assertEqual(report["subject_ref"], SUBJECT_REF)

    def test_authority_boundary_is_evaluation_only(self) -> None:
        report = evaluate_corpus(_load_corpus())
        self.assertEqual(report["authority_boundary"], AUTHORITY_BOUNDARY)
        self.assertTrue(report["authority_boundary"]["evaluation_only"])
        for key, value in report["authority_boundary"].items():
            if key != "evaluation_only":
                self.assertFalse(value, key)

    def test_corpus_cannot_redirect_subject(self) -> None:
        corpus = _load_corpus()
        corpus["subject_ref"] = "caller://alternate-ranker"
        with self.assertRaisesRegex(RankingCalibrationError, "CORPUS_SUBJECT_INVALID"):
            validate_corpus(corpus)

    def test_corpus_rejects_unknown_top_level_field(self) -> None:
        corpus = _load_corpus()
        corpus["caller_weight_override"] = 999
        with self.assertRaisesRegex(RankingCalibrationError, "CORPUS_FIELDS_INVALID"):
            validate_corpus(corpus)

    def test_scenario_cannot_self_declare_expected_verdict(self) -> None:
        corpus = _load_corpus()
        corpus["scenarios"][0]["expected"] = "PASS"
        with self.assertRaisesRegex(RankingCalibrationError, "MONOTONIC_FIELDS_INVALID"):
            validate_corpus(corpus)

    def test_cost_improvement_direction_is_fail_closed(self) -> None:
        corpus = _load_corpus()
        target = next(
            item for item in corpus["scenarios"] if item["scenario_id"] == "COST-MONO-001"
        )
        target["before"] = 10
        target["after"] = 90
        with self.assertRaisesRegex(
            RankingCalibrationError, "COST_IMPROVEMENT_DIRECTION_INVALID"
        ):
            validate_corpus(corpus)

    def test_benefit_improvement_direction_is_fail_closed(self) -> None:
        corpus = _load_corpus()
        target = next(
            item for item in corpus["scenarios"] if item["scenario_id"] == "UV-MONO-001"
        )
        target["before"] = 75
        target["after"] = 25
        with self.assertRaisesRegex(
            RankingCalibrationError, "BENEFIT_IMPROVEMENT_DIRECTION_INVALID"
        ):
            validate_corpus(corpus)

    def test_age_monotonic_scenario_cannot_cross_the_policy_cap(self) -> None:
        corpus = _load_corpus()
        target = next(
            item for item in corpus["scenarios"] if item["scenario_id"] == "AGE-MONO-002"
        )
        target["after"] = 21
        with self.assertRaisesRegex(RankingCalibrationError, "INVALID_BOUNDED_INTEGER"):
            validate_corpus(corpus)

    def test_age_plateau_requires_observation_at_or_above_cap(self) -> None:
        corpus = _load_corpus()
        target = next(
            item for item in corpus["scenarios"] if item["scenario_id"] == "AGE-CAP-001"
        )
        target["before"] = 19
        with self.assertRaisesRegex(RankingCalibrationError, "AGE_CAP_RANGE_INVALID"):
            validate_corpus(corpus)

    def test_boolean_is_not_accepted_as_numeric_score(self) -> None:
        corpus = _load_corpus()
        target = next(
            item for item in corpus["scenarios"] if item["scenario_id"] == "UV-MONO-001"
        )
        target["before"] = False
        with self.assertRaisesRegex(RankingCalibrationError, "INVALID_BOUNDED_INTEGER"):
            validate_corpus(corpus)

    def test_duplicate_scenario_ids_fail_closed(self) -> None:
        corpus = _load_corpus()
        corpus["scenarios"][1]["scenario_id"] = corpus["scenarios"][0]["scenario_id"]
        with self.assertRaisesRegex(RankingCalibrationError, "SCENARIO_ID_DUPLICATE"):
            validate_corpus(corpus)

    def test_distinct_valid_corpus_changes_report_digest(self) -> None:
        first_corpus = _load_corpus()
        second_corpus = copy.deepcopy(first_corpus)
        target = next(
            item
            for item in second_corpus["scenarios"]
            if item["scenario_id"] == "DEP-MONO-001"
        )
        target["before"] = 75
        first = evaluate_corpus(first_corpus)
        second = evaluate_corpus(second_corpus)
        self.assertEqual(second["status"], "PASS")
        self.assertNotEqual(first["scenario_corpus_digest"], second["scenario_corpus_digest"])
        self.assertNotEqual(first["report_digest"], second["report_digest"])


if __name__ == "__main__":
    unittest.main()
