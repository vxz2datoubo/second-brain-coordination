"""Deterministic E23 Evaluation V2 harness over synthetic source-derived SUTs."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import importlib

from catalog_validation import assert_catalogs_distinct
from evaluation_v2_contract import EXPECTED_D2_CORE_SHA256, canonical_sha256, report_row
from independent_oracle import evaluate_episode
from invariant_registry import execute_controlled_violation, validate_invariant_registry
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


def _case(identifier: str, executed_input: dict[str, object], observed_relation: dict[str, object]) -> dict[str, object]:
    return {"id": identifier, "executed_input": executed_input, "observed_relation": observed_relation}


def _run_input(run) -> dict[str, object]:
    """Project only fields actually consumed by the public arbitration call."""
    agent_order = {agent.agent_id: index for index, agent in enumerate(run.episode_state.initial_agents)}
    actions = []
    for action in run.episode_state.action_registry:
        actions.append({
            "agent": agent_order[action.agent_id], "arrival": action.arrival_sequence,
            "label": action.label.value,
            "side": None if action.order is None else action.order.side.value,
            "quantity": None if action.order is None else action.order.quantity,
            "requires_complete_information": action.requires_complete_information,
            "transition": action.conflict_transition.value, "liquidity": action.liquidity_mode.value,
            "has_conflict": action.conflict_key is not None,
            "has_counterparty": action.counterparty_agent_id is not None,
        })
    return {"actions": tuple(actions)}


def _counterfactual_catalog_case(result) -> dict[str, object]:
    """Build a trace only from the already-executed counterfactual result.

    ``CounterfactualSpec`` is an instruction to produce the result, not proof
    of what the SUT actually consumed.  Keeping it out of this projection
    makes a later spec/formula drift visible in the catalog signature.
    """
    baseline_run_id = result.baseline.run_id
    if not baseline_run_id.endswith(":baseline"):
        raise AssertionError("E26_COUNTERFACTUAL_EXECUTION_ID_MISSING_BASELINE_SUFFIX")
    return _case(
        baseline_run_id.removesuffix(":baseline"),
        {
            "baseline": _run_input(result.baseline),
            "alternative": _run_input(result.alternative),
            "changed_assumption_id": result.changed_assumption_id,
        },
        {
            "changed_action_ids": result.changed_action_ids,
            "baseline_state_hash": result.baseline.episode_state.state_hash,
            "alternative_state_hash": result.alternative.episode_state.state_hash,
            "changed_action_count": len(result.changed_action_ids),
        },
    )


def run_evaluation() -> tuple[EvaluationSummary, dict[str, object]]:
    fingerprint = assert_accepted_sut_fingerprint()
    scenarios = scenario_catalog()
    invariants = invariant_catalog()
    negatives = negative_catalog()
    episodes = episode_catalog()
    counterfactuals = counterfactual_catalog()
    cross_family = cross_family_catalog(mutation_property_pairs())
    validate_invariant_registry(tuple(sorted({spec.predicate_id for spec in invariants})))
    outcomes = {spec.scenario_id: execute_scenario(spec) for spec in scenarios}
    scenario_results = tuple({"scenario_id": spec.scenario_id, "passed": evaluate_episode(outcomes[spec.scenario_id].episode_state).valid} for spec in scenarios)
    if not all(row["passed"] for row in scenario_results):
        raise AssertionError("E23_SCENARIO_ORACLE_FAILURE")

    invariant_results = []
    for spec in invariants:
        evidence = execute_controlled_violation(spec.predicate_id, outcomes[spec.fixture_id])
        if evidence.failure_oracle_id != spec.failure_oracle_id:
            raise AssertionError("E25_INVARIANT_ORACLE_MAPPING_MISMATCH:" + spec.invariant_id)
        invariant_results.append({
            "invariant_id": spec.invariant_id,
            "fixture_id": spec.fixture_id,
            "predicate_id": spec.predicate_id,
            "failure_oracle_id": spec.failure_oracle_id,
            "test_id": spec.test_id,
            "passed": evidence.valid_predicate_passed,
            "controlled_violation_rejected": not evidence.violating_predicate_passed,
            "oracle_detects_controlled_violation": evidence.oracle.detected,
            "oracle_reason_codes": evidence.oracle.reason_codes,
            "valid_artifact_sha256": evidence.valid_artifact_sha256,
            "violating_artifact_sha256": evidence.violating_artifact_sha256,
            "oracle_artifact_sha256": evidence.oracle.artifact_sha256,
        })
    invariant_results = tuple(invariant_results)
    if not all(
        row["passed"] and row["controlled_violation_rejected"] and row["oracle_detects_controlled_violation"]
        for row in invariant_results
    ):
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
    episode_executions = {}
    for spec in episodes:
        one, two = execute_episode(spec)
        episode_executions[spec.episode_id] = (one, two)
        report = evaluate_episode(two.episode_state)
        episode_results.append({"episode_id": spec.episode_id, "passed": one.episode_state.step_index == 1 and two.episode_state.step_index == 2 and report.valid})
    if not all(row["passed"] for row in episode_results):
        raise AssertionError("E23_EPISODE_FAILURE")

    counterfactual_results = []
    counterfactual_executions = {}
    for spec in counterfactuals:
        result = execute_counterfactual(spec)
        counterfactual_executions[spec.pair_id] = result
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

    catalogs = {
        "scenarios": [_case(spec.scenario_id, _run_input(outcomes[spec.scenario_id]), {"valid": row["passed"]}) for spec, row in zip(scenarios, scenario_results)],
        "invariants": [_case(
            spec.invariant_id,
            {"fixture": _run_input(outcomes[spec.fixture_id]), "predicate": spec.predicate_id},
            {
                "predicate_passed": row["passed"],
                "controlled_violation_rejected": row["controlled_violation_rejected"],
                "failure_oracle_detects_violation": row["oracle_detects_controlled_violation"],
                "oracle_reason_codes": row["oracle_reason_codes"],
                "valid_artifact_sha256": row["valid_artifact_sha256"],
                "violating_artifact_sha256": row["violating_artifact_sha256"],
            },
        ) for spec, row in zip(invariants, invariant_results)],
        "negatives": [_case(spec.negative_id, {"family": spec.family}, {"raised": row["raised"], "expected": spec.expected_failure_class}) for spec, row in zip(negatives, negative_results)],
        "episodes": [_case(
            spec.episode_id,
            {"first": _run_input(episode_executions[spec.episode_id][0]), "second": _run_input(episode_executions[spec.episode_id][1])},
            {
                "steps": episode_executions[spec.episode_id][1].episode_state.step_index,
                "valid": row["passed"],
                "final_state_hash": episode_executions[spec.episode_id][1].episode_state.state_hash,
            },
        ) for spec, row in zip(episodes, episode_results)],
        "counterfactuals": [
            _counterfactual_catalog_case(counterfactual_executions[spec.pair_id])
            for spec in counterfactuals
        ],
        "cross_family": [_case(spec.interaction_id, {"mutant": spec.mutant_id, "property": spec.property_id, "variant": spec.fixture_variant}, {"passed": row["passed"]}) for spec, row in zip(cross_family, cross_results)],
    }
    assert_catalogs_distinct(catalogs)

    report = {
        "boundary": "PUBLIC_SAFE_SYNTHETIC_ONLY_CANDIDATE_ONLY",
        "sut_fingerprint": fingerprint,
        "catalog_counts": {
            "scenarios": len(scenarios), "invariants": len(invariants), "negatives": len(negatives),
            "episodes": len(episodes), "counterfactuals": len(counterfactuals), "cross_family": len(cross_family),
        },
        "catalog_signatures": {
            **catalogs,
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
