from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from idle_signal_scheduler import P3, P4, _rank_key


POLICY_VERSION = "R157/v1"
SCENARIO_SCHEMA = "R157RankingCalibrationScenarios/v1"
REPORT_SCHEMA = "RankingCalibrationReport/v1"
SUBJECT_REF = "coordination/CONTROL-TOWER/idle_signal_scheduler.py#_rank_key"

AUTHORITY_BOUNDARY = {
    "evaluation_only": True,
    "selects_opportunity": False,
    "releases_task": False,
    "creates_issue": False,
    "creates_route": False,
    "creates_claim": False,
    "creates_worker_slot": False,
    "grants_execution_authority": False,
    "grants_domain_write": False,
    "grants_w3_write": False,
    "grants_merge_authority": False,
    "tunes_ranking_weights": False,
}

_MONOTONIC_AXES = frozenset(
    {
        "user_value_score",
        "materiality_score",
        "dependency_readiness_score",
        "age_cycles",
        "estimated_cost_score",
    }
)
_SCORE_AXES = frozenset(
    {
        "user_value_score",
        "materiality_score",
        "dependency_readiness_score",
        "estimated_cost_score",
    }
)
_SUPPORTED_KINDS = frozenset(
    {
        "MONOTONIC_AXIS",
        "AGE_CAP_PLATEAU",
        "PRIORITY_DOMINANCE",
        "LEXICAL_TIE_BREAK",
        "PERMUTATION_INVARIANCE",
    }
)


class RankingCalibrationError(ValueError):
    """Stable fail-closed R157 evaluation error."""

    def __init__(self, code: str, path: str = "/") -> None:
        super().__init__(code)
        self.code = code
        self.path = path


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _copy(value: Any) -> Any:
    return json.loads(_canonical(value))


def _nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RankingCalibrationError("INVALID_STRING", path)
    return value


def _bounded_int(value: Any, path: str, *, high: int = 100) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > high
    ):
        raise RankingCalibrationError("INVALID_BOUNDED_INTEGER", path)
    return value


def _base_candidate(opportunity_id: str = "candidate") -> dict[str, Any]:
    return {
        "priority_class": P3,
        "user_value_score": 50,
        "materiality_score": 50,
        "dependency_readiness_score": 100,
        "age_cycles": 5,
        "estimated_cost_score": 50,
        "opportunity_id": opportunity_id,
    }


def _observed_key(candidate: Mapping[str, Any]) -> list[Any]:
    """Observe the retained R151 key directly; do not duplicate its formula."""
    return list(_rank_key(candidate))


def _validate_monotonic(scenario: Mapping[str, Any], path: str) -> dict[str, Any]:
    required = {"scenario_id", "kind", "axis", "before", "after"}
    if set(scenario) != required:
        raise RankingCalibrationError("MONOTONIC_FIELDS_INVALID", path)
    axis = _nonempty_string(scenario.get("axis"), f"{path}/axis")
    if axis not in _MONOTONIC_AXES:
        raise RankingCalibrationError("MONOTONIC_AXIS_INVALID", f"{path}/axis")
    high = 20 if axis == "age_cycles" else 100
    before = _bounded_int(scenario.get("before"), f"{path}/before", high=high)
    after = _bounded_int(scenario.get("after"), f"{path}/after", high=high)
    if axis == "estimated_cost_score":
        if after > before:
            raise RankingCalibrationError("COST_IMPROVEMENT_DIRECTION_INVALID", path)
    elif after < before:
        raise RankingCalibrationError("BENEFIT_IMPROVEMENT_DIRECTION_INVALID", path)
    return dict(scenario)


def _validate_scenario(scenario: Mapping[str, Any], index: int) -> dict[str, Any]:
    path = f"/scenarios/{index}"
    if not isinstance(scenario, Mapping):
        raise RankingCalibrationError("SCENARIO_NOT_OBJECT", path)
    scenario_id = _nonempty_string(scenario.get("scenario_id"), f"{path}/scenario_id")
    kind = _nonempty_string(scenario.get("kind"), f"{path}/kind")
    if kind not in _SUPPORTED_KINDS:
        raise RankingCalibrationError("SCENARIO_KIND_INVALID", f"{path}/kind")

    if kind == "MONOTONIC_AXIS":
        return _validate_monotonic(scenario, path)
    if kind == "AGE_CAP_PLATEAU":
        if set(scenario) != {"scenario_id", "kind", "before", "after"}:
            raise RankingCalibrationError("AGE_CAP_FIELDS_INVALID", path)
        before = _bounded_int(scenario.get("before"), f"{path}/before", high=1_000_000)
        after = _bounded_int(scenario.get("after"), f"{path}/after", high=1_000_000)
        if before < 20 or after < before:
            raise RankingCalibrationError("AGE_CAP_RANGE_INVALID", path)
        return dict(scenario)
    if kind == "PRIORITY_DOMINANCE":
        if set(scenario) != {"scenario_id", "kind"}:
            raise RankingCalibrationError("PRIORITY_DOMINANCE_FIELDS_INVALID", path)
        return dict(scenario)
    if kind == "LEXICAL_TIE_BREAK":
        if set(scenario) != {"scenario_id", "kind", "left_id", "right_id"}:
            raise RankingCalibrationError("LEXICAL_TIE_FIELDS_INVALID", path)
        left_id = _nonempty_string(scenario.get("left_id"), f"{path}/left_id")
        right_id = _nonempty_string(scenario.get("right_id"), f"{path}/right_id")
        if left_id == right_id:
            raise RankingCalibrationError("LEXICAL_TIE_IDS_NOT_DISTINCT", path)
        return dict(scenario)

    if set(scenario) != {"scenario_id", "kind", "candidate_ids"}:
        raise RankingCalibrationError("PERMUTATION_FIELDS_INVALID", path)
    candidate_ids = scenario.get("candidate_ids")
    if not isinstance(candidate_ids, list) or len(candidate_ids) < 2:
        raise RankingCalibrationError("PERMUTATION_IDS_INVALID", f"{path}/candidate_ids")
    normalized_ids = [
        _nonempty_string(value, f"{path}/candidate_ids/{offset}")
        for offset, value in enumerate(candidate_ids)
    ]
    if len(set(normalized_ids)) != len(normalized_ids):
        raise RankingCalibrationError("PERMUTATION_IDS_NOT_UNIQUE", path)
    return {"scenario_id": scenario_id, "kind": kind, "candidate_ids": normalized_ids}


def validate_corpus(corpus: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(corpus, Mapping):
        raise RankingCalibrationError("CORPUS_NOT_OBJECT")
    required = {"schema_version", "subject_ref", "scenarios"}
    if set(corpus) != required:
        raise RankingCalibrationError("CORPUS_FIELDS_INVALID")
    if corpus.get("schema_version") != SCENARIO_SCHEMA:
        raise RankingCalibrationError("CORPUS_SCHEMA_INVALID", "/schema_version")
    if corpus.get("subject_ref") != SUBJECT_REF:
        raise RankingCalibrationError("CORPUS_SUBJECT_INVALID", "/subject_ref")
    scenarios = corpus.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise RankingCalibrationError("CORPUS_SCENARIOS_INVALID", "/scenarios")
    normalized = [_validate_scenario(item, index) for index, item in enumerate(scenarios)]
    ids = [item["scenario_id"] for item in normalized]
    if len(set(ids)) != len(ids):
        raise RankingCalibrationError("SCENARIO_ID_DUPLICATE", "/scenarios")
    return {
        "schema_version": SCENARIO_SCHEMA,
        "subject_ref": SUBJECT_REF,
        "scenarios": normalized,
    }


def _evaluate_monotonic(scenario: Mapping[str, Any]) -> dict[str, Any]:
    axis = str(scenario["axis"])
    before = _base_candidate()
    after = _base_candidate()
    before[axis] = scenario["before"]
    after[axis] = scenario["after"]
    before_key = _observed_key(before)
    after_key = _observed_key(after)
    return {
        "passed": tuple(after_key) <= tuple(before_key),
        "observed": {
            "axis": axis,
            "before": scenario["before"],
            "after": scenario["after"],
            "before_key": before_key,
            "after_key": after_key,
        },
    }


def _evaluate_age_cap(scenario: Mapping[str, Any]) -> dict[str, Any]:
    before = _base_candidate()
    after = _base_candidate()
    before["age_cycles"] = scenario["before"]
    after["age_cycles"] = scenario["after"]
    before_key = _observed_key(before)
    after_key = _observed_key(after)
    return {
        "passed": before_key == after_key,
        "observed": {
            "before": scenario["before"],
            "after": scenario["after"],
            "before_key": before_key,
            "after_key": after_key,
        },
    }


def _evaluate_priority_dominance() -> dict[str, Any]:
    worst_p3 = _base_candidate("z-worst-p3")
    worst_p3.update(
        {
            "priority_class": P3,
            "user_value_score": 25,
            "materiality_score": 25,
            "dependency_readiness_score": 100,
            "age_cycles": 0,
            "estimated_cost_score": 100,
        }
    )
    best_p4 = _base_candidate("a-best-p4")
    best_p4.update(
        {
            "priority_class": P4,
            "user_value_score": 75,
            "materiality_score": 50,
            "dependency_readiness_score": 100,
            "age_cycles": 20,
            "estimated_cost_score": 0,
        }
    )
    p3_key = _observed_key(worst_p3)
    p4_key = _observed_key(best_p4)
    return {
        "passed": tuple(p3_key) < tuple(p4_key),
        "observed": {"worst_p3_key": p3_key, "best_p4_key": p4_key},
    }


def _evaluate_lexical_tie(scenario: Mapping[str, Any]) -> dict[str, Any]:
    left = _base_candidate(str(scenario["left_id"]))
    right = _base_candidate(str(scenario["right_id"]))
    left_key = _observed_key(left)
    right_key = _observed_key(right)
    expected_winner = min(str(scenario["left_id"]), str(scenario["right_id"]))
    observed_winner = str(scenario["left_id"]) if tuple(left_key) < tuple(right_key) else str(scenario["right_id"])
    return {
        "passed": left_key != right_key and observed_winner == expected_winner,
        "observed": {
            "left_key": left_key,
            "right_key": right_key,
            "expected_winner": expected_winner,
            "observed_winner": observed_winner,
        },
    }


def _winner(candidate_ids: Sequence[str]) -> str:
    candidates = [_base_candidate(candidate_id) for candidate_id in candidate_ids]
    return min(candidates, key=_rank_key)["opportunity_id"]


def _evaluate_permutation(scenario: Mapping[str, Any]) -> dict[str, Any]:
    candidate_ids = list(scenario["candidate_ids"])
    forward = _winner(candidate_ids)
    reverse = _winner(list(reversed(candidate_ids)))
    rotated_ids = candidate_ids[1:] + candidate_ids[:1]
    rotated = _winner(rotated_ids)
    expected = min(candidate_ids)
    return {
        "passed": forward == reverse == rotated == expected,
        "observed": {
            "forward_winner": forward,
            "reverse_winner": reverse,
            "rotated_winner": rotated,
            "expected_winner": expected,
        },
    }


def evaluate_scenario(scenario: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(scenario["kind"])
    if kind == "MONOTONIC_AXIS":
        outcome = _evaluate_monotonic(scenario)
    elif kind == "AGE_CAP_PLATEAU":
        outcome = _evaluate_age_cap(scenario)
    elif kind == "PRIORITY_DOMINANCE":
        outcome = _evaluate_priority_dominance()
    elif kind == "LEXICAL_TIE_BREAK":
        outcome = _evaluate_lexical_tie(scenario)
    elif kind == "PERMUTATION_INVARIANCE":
        outcome = _evaluate_permutation(scenario)
    else:
        raise RankingCalibrationError("SCENARIO_KIND_INVALID")
    return {
        "scenario_id": scenario["scenario_id"],
        "kind": kind,
        "passed": bool(outcome["passed"]),
        "observed": _copy(outcome["observed"]),
    }


def evaluate_corpus(corpus: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_corpus(corpus)
    results = [evaluate_scenario(item) for item in normalized["scenarios"]]
    passed = sum(1 for item in results if item["passed"])
    failed = len(results) - passed
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "subject_ref": SUBJECT_REF,
        "scenario_corpus_digest": _digest(normalized),
        "status": "PASS" if failed == 0 else "FAIL",
        "total_scenarios": len(results),
        "passed_scenarios": passed,
        "failed_scenarios": failed,
        "results": results,
        "authority_boundary": _copy(AUTHORITY_BOUNDARY),
    }
    report["report_digest"] = _digest(report)
    return report
