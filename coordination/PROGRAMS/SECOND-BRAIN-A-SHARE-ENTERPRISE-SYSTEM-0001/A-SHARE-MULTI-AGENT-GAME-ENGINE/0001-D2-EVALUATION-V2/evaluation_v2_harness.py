"""Deterministic executable E22 Evaluation V2 harness."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import importlib
import sys

from evaluation_v2_contract import EXPECTED_D2_CORE_SHA256, canonical_sha256, report_row
from independent_oracle import evaluate_episode
from metamorphic_properties import PROPERTY_IDS, property_function_map, run_metamorphic_properties
from mutation_registry import execute_mutation_registry, mutation_registry
from synthetic_cases import (
    counterfactual_catalog, cross_family_catalog, episode_catalog, execute_counterfactual, execute_episode,
    execute_negative, execute_scenario, invariant_catalog, negative_catalog, scenario_catalog,
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
        raise RuntimeError("E22_SUT_FINGERPRINT_MISMATCH:" + actual)
    return actual


def _invariant_passes(predicate_id: str, run) -> bool:
    episode = run.episode_state
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
        return evaluate_episode(episode).valid
    raise ValueError("UNKNOWN_INVARIANT_PREDICATE:" + predicate_id)


def run_evaluation() -> tuple[EvaluationSummary, dict[str, object]]:
    fingerprint = assert_accepted_sut_fingerprint()
    scenarios = scenario_catalog()
    outcomes = {spec.scenario_id: execute_scenario(spec) for spec in scenarios}
    invariants = invariant_catalog()
    invariant_results = tuple({
        "invariant_id": spec.invariant_id, "requirement_id": spec.requirement_id,
        "fixture_id": spec.fixture_id, "failure_oracle_id": spec.failure_oracle_id,
        "test_id": spec.test_id, "passed": _invariant_passes(spec.predicate_id, outcomes[spec.fixture_id]),
    } for spec in invariants)
    if not all(row["passed"] for row in invariant_results):
        raise AssertionError("E22_INVARIANT_FAILURE")

    negatives = negative_catalog()
    negative_results = []
    for spec in negatives:
        try:
            execute_negative(spec)
        except ValueError as error:
            negative_results.append({"negative_id": spec.negative_id, "test_id": spec.test_id, "raised": type(error).__name__, "passed": True})
        else:
            negative_results.append({"negative_id": spec.negative_id, "test_id": spec.test_id, "raised": "NONE", "passed": False})
    if not all(row["passed"] for row in negative_results):
        raise AssertionError("E22_NEGATIVE_CASE_ACCEPTED")

    episodes = episode_catalog()
    episode_results = []
    for spec in episodes:
        one, two = execute_episode(spec)
        report = evaluate_episode(two.episode_state)
        passed = one.episode_state.step_index == 1 and two.episode_state.step_index == 2 and report.valid
        episode_results.append({"episode_id": spec.episode_id, "test_id": spec.test_id, "passed": passed})
    if not all(row["passed"] for row in episode_results):
        raise AssertionError("E22_EPISODE_FAILURE")

    counterfactuals = counterfactual_catalog()
    counterfactual_results = []
    for spec in counterfactuals:
        result = execute_counterfactual(spec)
        passed = len(result.changed_action_ids) == 1 and result.changed_action_ids[0] in {event.action_id for event in result.baseline.events}
        counterfactual_results.append({"pair_id": spec.pair_id, "test_id": spec.test_id, "passed": passed})
    if not all(row["passed"] for row in counterfactual_results):
        raise AssertionError("E22_COUNTERFACTUAL_FAILURE")

    activations, kills = execute_mutation_registry()
    if not all(item.behavior_changed for item in activations):
        raise AssertionError("E22_DECORATIVE_MUTANT")
    survivors = tuple(item.mutant_id for item in activations if item.status != "KILLED")
    if survivors or not all(item.killed for item in kills):
        raise AssertionError("E22_SURVIVING_MUTANT")

    properties = run_metamorphic_properties()
    property_failures = tuple(item.property_id for item in properties if not item.passed)
    if property_failures:
        raise AssertionError("E22_METAMORPHIC_FAILURE:" + ",".join(property_failures))

    cross_family = cross_family_catalog(tuple(item.mutant_id for item in activations), PROPERTY_IDS)
    definitions_by_id = {item.mutant_id: item for item in mutation_registry()}
    property_functions = property_function_map()
    cross_results = []
    for spec in cross_family:
        # Each row re-activates the selected fault and its independently named
        # property instead of borrowing a count from a previously run matrix.
        definition = definitions_by_id[spec.mutant_id]
        probe = definition.activate()
        killed, _oracle_id, _observation = definition.kill(probe)
        property_result = property_functions[spec.property_id]()
        cross_results.append({
            "interaction_id": spec.interaction_id, "mutant_id": spec.mutant_id, "property_id": spec.property_id,
            "test_id": spec.test_id, "passed": probe.changed and killed and property_result.passed,
        })
    cross_results = tuple(cross_results)
    if not all(row["passed"] for row in cross_results):
        raise AssertionError("E22_CROSS_FAMILY_FAILURE")

    executable_test_ids = {
        "TEST-CATALOG-SCENARIOS", "TEST-CATALOG-INVARIANTS", "TEST-CATALOG-NEGATIVES",
        "TEST-CATALOG-EPISODES", "TEST-CATALOG-COUNTERFACTUALS", "TEST-CATALOG-CROSS-FAMILY",
        "TEST-MUTATION-REGISTRY",
    }
    catalog_test_ids = {spec.test_id for spec in scenarios} | {spec.test_id for spec in invariants} | {spec.test_id for spec in negatives} | {spec.test_id for spec in episodes} | {spec.test_id for spec in counterfactuals} | {spec.test_id for spec in cross_family}
    if catalog_test_ids - executable_test_ids:
        raise AssertionError("E22_ORPHAN_CATALOG_TEST_ID")

    report = {
        "boundary": "PUBLIC_SAFE_SYNTHETIC_ONLY",
        "sut_fingerprint": fingerprint,
        "catalog_counts": {
            "scenarios": len(scenarios), "invariants": len(invariants), "negatives": len(negatives),
            "episodes": len(episodes), "counterfactuals": len(counterfactuals), "cross_family": len(cross_family),
        },
        "invariants": invariant_results,
        "negatives": negative_results,
        "episodes": episode_results,
        "counterfactuals": counterfactual_results,
        "mutation_activation": [report_row(item) for item in activations],
        "mutation_kills": [report_row(item) for item in kills],
        "metamorphic": [report_row(item) for item in properties],
        "cross_family": cross_results,
    }
    report_hash = canonical_sha256(report)
    summary = EvaluationSummary(
        fingerprint, len(scenarios), len(invariants), len(negatives), len(episodes), len(counterfactuals), len(cross_family),
        len(kills) / len(activations), survivors, property_failures, report_hash,
    )
    return summary, report
