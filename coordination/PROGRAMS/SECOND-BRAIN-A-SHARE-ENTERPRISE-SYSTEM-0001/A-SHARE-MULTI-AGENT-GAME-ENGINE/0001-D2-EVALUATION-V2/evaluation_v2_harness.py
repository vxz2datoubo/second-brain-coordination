"""Deterministic E23 Evaluation V2 harness over synthetic source-derived SUTs."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import importlib

from catalog_validation import assert_catalogs_distinct
from evaluation_v2_contract import EXPECTED_D2_CORE_SHA256, canonical_sha256, report_row
from independent_oracle import evaluate_episode
from metamorphic_properties import property_function_map, run_metamorphic_properties
from mutation_registry import execute_mutation, execute_mutation_registry, mutation_property_pairs, mutation_registry
from synthetic_cases import (
    counterfactual_catalog,
    cross_family_catalog,
    episode_catalog,
    execute_counterfactual,
    execute_episode,
    execute_negative,
    execute_scenario,
    invariant_catalog,
    negative_catalog,
    scenario_catalog,
)


@dataclass(frozen=True)
class EvaluationSummary:
    sut_fingerprint: str
    scenario_count: int
    invariant_count: int
    negative_count: int
    episode_count: int
    counterfactual_count: int
    cross_family_count: int
    mutation_score: float
    survivors: tuple[str, ...]
    property_failures: tuple[str, ...]
    canonical_report_sha256: str


def assert_accepted_sut_fingerprint() -> str:
    module = importlib.import_module("d2_game_core")
    actual = sha256(Path(module.__file__).read_bytes()).hexdigest()
    if actual != EXPECTED_D2_CORE_SHA256:
        raise RuntimeError("E23_SUT_FINGERPRINT_MISMATCH:" + actual)
    return actual


def _invariant_passes(predicate_id: str, run) -> bool:
    episode = run.episode_state
    report = evaluate_episode(episode)
    if predicate_id == "HAS_EPISODE":
        return episode is not None and episode.step_index >= 1
    if predicate_id == "NONEMPTY_EVENTS":
        return bool(run.events)
    if predicate_id == "UNIQUE_EVENT_IDS":
        return len({event.event_id for event in episode.event_dag}) == len(episode.event_dag)
    if predicate_id == "ACTION_EVENT_BINDING":
        actions = {action.action_id: action for action in episode.action_registry}
        return all(actions.get(event.action_id) is not None and actions[event.action_id].agent_id == event.agent_id for event in episode.event_dag)
    if predicate_id == "INDEPENDENT_ACCOUNTING":
        return report.valid
    if predicate_id == "BOUNDARY_ORDER":
        return "ORACLE_ARRIVAL_SEQUENCE_ORDER" not in report.reason_codes
    if predicate_id == "NO_UNEXPLAINED_FLOW":
        return not any(code.startswith("ORACLE_EXTERNAL_FLOW") or code == "ORACLE_UNEXPLAINED_EXTERNAL_FLOW" for code in report.reason_codes)
    if predicate_id == "TERMINAL_ACTION_COVERAGE":
        return "ORACLE_ACTION_EVENT_COVERAGE_MISMATCH" not in report.reason_codes
    if predicate_id == "STEP_MONOTONIC":
        return tuple(item.step_index for item in episode.step_boundaries) == tuple(range(1, episode.step_index + 1))
    if predicate_id == "PORTFOLIO_DELTA_EXPLAINED":
        return "ORACLE_INVENTORY_DELTA_MISMATCH" not in report.reason_codes
    raise ValueError("UNKNOWN_INVARIANT_PREDICATE:" + predicate_id)


def _signature_row(spec: object) -> dict[str, object]:
    input_signature, relation_signature = spec.signatures
    identifier = next(value for name, value in vars(spec).items() if name.endswith("_id"))
    return {"id": identifier, "input_signature": input_signature, "expected_relation_signature": relation_signature}


def run_evaluation() -> tuple[EvaluationSummary, dict[str, object]]:
    fingerprint = assert_accepted_sut_fingerprint()
    scenarios = scenario_catalog()
    invariants = invariant_catalog()
    negatives = negative_catalog()
    episodes = episode_catalog()
    counterfactuals = counterfactual_catalog()
    cross_family = cross_family_catalog(mutation_property_pairs())
    assert_catalogs_distinct(scenarios, invariants, negatives, episodes, counterfactuals, cross_family)

    outcomes = {spec.scenario_id: execute_scenario(spec) for spec in scenarios}
    scenario_results = tuple({"scenario_id": spec.scenario_id, "passed": evaluate_episode(outcomes[spec.scenario_id].episode_state).valid} for spec in scenarios)
    if not all(row["passed"] for row in scenario_results):
        raise AssertionError("E23_SCENARIO_ORACLE_FAILURE")

    invariant_results = tuple({
        "invariant_id": spec.invariant_id,
        "fixture_id": spec.fixture_id,
        "predicate_id": spec.predicate_id,
        "failure_oracle_id": spec.failure_oracle_id,
        "test_id": spec.test_id,
        "passed": _invariant_passes(spec.predicate_id, outcomes[spec.fixture_id]),
    } for spec in invariants)
    if not all(row["passed"] for row in invariant_results):
        raise AssertionError("E23_INVARIANT_FAILURE")

    negative_results = []
    for spec in negatives:
        try:
            execute_negative(spec)
        except ValueError as error:
            negative_results.append({"negative_id": spec.negative_id, "raised": type(error).__name__, "passed": type(error).__name__ == spec.expected_failure_class})
        else:
            negative_results.append({"negative_id": spec.negative_id, "raised": "NONE", "passed": False})
    if not all(row["passed"] for row in negative_results):
        raise AssertionError("E23_NEGATIVE_CASE_ACCEPTED")

    episode_results = []
    for spec in episodes:
        one, two = execute_episode(spec)
        report = evaluate_episode(two.episode_state)
        episode_results.append({"episode_id": spec.episode_id, "passed": one.episode_state.step_index == 1 and two.episode_state.step_index == 2 and report.valid})
    if not all(row["passed"] for row in episode_results):
        raise AssertionError("E23_EPISODE_FAILURE")

    counterfactual_results = []
    for spec in counterfactuals:
        result = execute_counterfactual(spec)
        counterfactual_results.append({"pair_id": spec.pair_id, "passed": len(result.changed_action_ids) == 1})
    if not all(row["passed"] for row in counterfactual_results):
        raise AssertionError("E23_COUNTERFACTUAL_FAILURE")

    activations, kills = execute_mutation_registry()
    if not all(item.behavior_changed for item in activations):
        raise AssertionError("E23_DECORATIVE_MUTANT")
    survivors = tuple(item.mutant_id for item in activations if item.status != "KILLED")
    if survivors or not all(item.killed and not item.digest_only for item in kills):
        raise AssertionError("E23_SURVIVING_OR_DIGEST_ONLY_MUTANT")

    properties = run_metamorphic_properties()
    property_failures = tuple(item.property_id for item in properties if not item.passed)
    if property_failures:
        raise AssertionError("E23_METAMORPHIC_FAILURE:" + ",".join(property_failures))

    definitions = {item.mutant_id: item for item in mutation_registry()}
    property_functions = property_function_map()
    cross_results = []
    for spec in cross_family:
        mutation_execution = execute_mutation(definitions[spec.mutant_id], spec.fixture_variant)
        property_result = property_functions[spec.property_id](spec.fixture_variant)
        cross_results.append({
            "interaction_id": spec.interaction_id,
            "mutant_id": spec.mutant_id,
            "property_id": spec.property_id,
            "fixture_variant": spec.fixture_variant,
            "passed": mutation_execution.activation.behavior_changed and mutation_execution.kill.killed and property_result.passed,
        })
    if not all(row["passed"] for row in cross_results):
        raise AssertionError("E23_CROSS_FAMILY_FAILURE")

    report = {
        "boundary": "PUBLIC_SAFE_SYNTHETIC_ONLY_CANDIDATE_ONLY",
        "sut_fingerprint": fingerprint,
        "catalog_counts": {
            "scenarios": len(scenarios), "invariants": len(invariants), "negatives": len(negatives),
            "episodes": len(episodes), "counterfactuals": len(counterfactuals), "cross_family": len(cross_family),
        },
        "catalog_signatures": {
            "scenarios": [_signature_row(spec) for spec in scenarios],
            "invariants": [_signature_row(spec) for spec in invariants],
            "negatives": [_signature_row(spec) for spec in negatives],
            "episodes": [_signature_row(spec) for spec in episodes],
            "counterfactuals": [_signature_row(spec) for spec in counterfactuals],
            "cross_family": [_signature_row(spec) for spec in cross_family],
        },
        "scenarios": scenario_results,
        "invariants": invariant_results,
        "negatives": tuple(negative_results),
        "episodes": tuple(episode_results),
        "counterfactuals": tuple(counterfactual_results),
        "mutation_activation": [report_row(item) for item in activations],
        "mutation_kills": [report_row(item) for item in kills],
        "metamorphic": [report_row(item) for item in properties],
        "cross_family": tuple(cross_results),
    }
    report_hash = canonical_sha256(report)
    summary = EvaluationSummary(
        fingerprint, len(scenarios), len(invariants), len(negatives), len(episodes), len(counterfactuals), len(cross_family),
        len(kills) / len(activations), survivors, property_failures, report_hash,
    )
    return summary, report
