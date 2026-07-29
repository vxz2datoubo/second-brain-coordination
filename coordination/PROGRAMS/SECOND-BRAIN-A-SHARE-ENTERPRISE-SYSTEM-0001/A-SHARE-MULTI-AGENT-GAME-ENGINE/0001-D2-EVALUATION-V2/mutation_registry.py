"""Executable, source-derived D2 mutations and family-specific kill evidence."""
from __future__ import annotations

from dataclasses import dataclass, replace
from types import ModuleType
from typing import Callable

import d2_game_core as BASE_SUT

from evaluation_v2_contract import MutationActivation, MutationKill, canonical_sha256
from independent_oracle import evaluate_episode, independent_digest, state_hash_binding_oracle
from shadow_sut import SourceReplacement, load_shadow_sut
from synthetic_cases import _base_agents, make_action, peer_pair
from synthetic_engine.fixtures import market
from synthetic_engine.types import OrderSide


@dataclass(frozen=True)
class MutationDefinition:
    mutant_id: str
    family: str
    fixture_id: str
    oracle_id: str
    paired_property_id: str
    replacements: tuple[SourceReplacement, ...]


@dataclass(frozen=True)
class MutationExecution:
    activation: MutationActivation
    kill: MutationKill


def _source_definitions() -> tuple[MutationDefinition, ...]:
    return (
        MutationDefinition(
            "MUT-001-ARRIVAL-IDENTIFIER-ORDER", "arrival_order_identifier_order", "FIX-ARRIVAL", "ORACLE_ARRIVAL_SEQUENCE_ORDER", "MP-001-ARRIVAL-SEQUENCE-SWAP",
            (SourceReplacement(
                "arrival_order", "ordered_actions = tuple(sorted(action_tuple, key=lambda item: item.arrival_sequence))",
                "ordered_actions = tuple(sorted(action_tuple, key=lambda item: (item.agent_id, item.action_id)))",
            ),),
        ),
        MutationDefinition(
            "MUT-002-LATE-REPLAY-RESERVATION", "duplicate_replay_reservation_after_terminal", "FIX-REPLAY", "ORACLE_DUPLICATE_OR_INVALID_ACTION_ID", "MP-003-CONTINUATION-IDENTITY-SUBSTITUTION",
            (
                SourceReplacement("replay_prior_collision", 'raise ValueError("PRIOR_ACTION_REGISTRY_COLLISION")', "pass"),
                SourceReplacement("replay_executed_identity", 'raise ValueError("REPLAYED_ACTION_OR_ORDER_REJECTED")', "pass"),
                SourceReplacement(
                    "replay_duplicate_registry", "if len({action.action_id for action in merged}) != len(merged):\n        raise ValueError(\"DUPLICATE_ACTION_REGISTRY_ID\")",
                    "if False:\n        raise ValueError(\"DUPLICATE_ACTION_REGISTRY_ID\")",
                ),
            ),
        ),
        MutationDefinition(
            "MUT-003-PARTIAL-PEER-COMMIT", "peer_transfer_partial_commit", "FIX-PEER", "ORACLE_PARTIAL_PEER_COMMIT", "MP-005-PEER-QUANTITY-SCALE",
            (SourceReplacement(
                "peer_emit_second_leg", "for peer_action in plan.actions:\n                peer_outcome = plan.outcome_for(peer_action.action_id)\n                owner_pre_hash",
                "for peer_action in plan.actions[:1]:\n                peer_outcome = plan.outcome_for(peer_action.action_id)\n                owner_pre_hash",
            ),),
        ),
        MutationDefinition(
            "MUT-004-EXTERNAL-FLOW-OMITTED", "external_flow_omitted", "FIX-EXTERNAL", "ORACLE_EXTERNAL_FLOW_MISSING_OR_DUPLICATE", "MP-006-EXTERNAL-SIDE-TRANSFORM",
            (SourceReplacement("external_flow_append", "external_flows.append(_flow_for_event(event, action))", "pass"),),
        ),
        MutationDefinition(
            "MUT-005-STORED-HASH-TRUST", "stored_ledger_hash_trusted", "FIX-HASH", "ORACLE_STORED_HASH_BINDING", "MP-007-STATE-HASH-TAMPER",
            (SourceReplacement(
                "stored_hash_verifier", "if episode.state_hash != reconstructed.state_hash:\n        reasons.append(\"EPISODE_STATE_HASH_MISMATCH\")",
                "if False:\n        reasons.append(\"EPISODE_STATE_HASH_MISMATCH\")",
            ),),
        ),
        MutationDefinition(
            "MUT-006-FORWARD-CAUSAL", "causal_parent_forward_or_cycle", "FIX-CAUSAL", "ORACLE_FORWARD_OR_CYCLIC_CAUSAL_PARENT", "MP-004-CAUSAL-PARENT-INJECTION",
            (SourceReplacement(
                "causal_forward_block", "if any(parent not in known_parent_ids for parent in action.causal_parent_event_ids):\n            emit(_blocked_event(episode_id, current_step, ordinal, action, (\"UNKNOWN_OR_FORWARD_CAUSAL_PARENT\",), owner_hash, system_before), action)\n            continue",
                "if False:\n            emit(_blocked_event(episode_id, current_step, ordinal, action, (\"UNKNOWN_OR_FORWARD_CAUSAL_PARENT\",), owner_hash, system_before), action)\n            continue",
            ),),
        ),
        MutationDefinition(
            "MUT-007-CONFLICT-OWNERSHIP-BYPASS", "conflict_claim_release_expire_bypass", "FIX-CONFLICT", "ORACLE_CONFLICT_CLAIM_BYPASS", "MP-002-ALPHA-RENAME-CONFLICT-EXCLUSION",
            (SourceReplacement(
                "conflict_claim_guard", "if action.conflict_key and action.conflict_key in claimed_conflicts:\n            emit(_blocked_event(episode_id, current_step, ordinal, action, (\"CONFLICT_RESOURCE_ALREADY_CLAIMED\",), owner_hash, system_before), action)\n            continue",
                "if False:\n            emit(_blocked_event(episode_id, current_step, ordinal, action, (\"CONFLICT_RESOURCE_ALREADY_CLAIMED\",), owner_hash, system_before), action)\n            continue",
            ),),
        ),
        MutationDefinition(
            "MUT-008-NOMINAL-BOUNDARY", "exact_primitive_enum_carrier_weakened", "FIX-BOUNDARY", "ORACLE_EXACT_CARRIER_BOUNDARY", "MP-008-EXACT-CARRIER-TRANSFORM",
            (
                SourceReplacement("enum_nominal", "return value is None or type(value) is enum_type", "return value is None or isinstance(value, enum_type)"),
                SourceReplacement("carrier_nominal", "return type(value) in (tuple, list)", "return isinstance(value, (tuple, list))"),
                SourceReplacement("action_nominal", "if type(action) is not CandidateAction:", "if not isinstance(action, CandidateAction):", expected_count=2),
                SourceReplacement("registry_action_nominal", "if any(type(action) is not CandidateAction for action in merged):", "if any(not isinstance(action, CandidateAction) for action in merged):"),
            ),
        ),
    )


def validate_true_sut_mutation(definition: MutationDefinition) -> None:
    """Reject output-only registrations before any mutation is executed."""
    if not definition.replacements:
        raise ValueError("E23_MUTATION_REQUIRES_SOURCE_DERIVED_SEAM")
    if not all(item.before and item.after and item.before != item.after for item in definition.replacements):
        raise ValueError("E23_MUTATION_REQUIRES_EXECUTABLE_SOURCE_DELTA")
    if any("EpisodeState" in item.seam_id or item.seam_id.startswith("posthoc_") or "output_after_sut" in item.seam_id for item in definition.replacements):
        raise ValueError("E23_POSTHOC_OUTPUT_MUTATION_FORBIDDEN")


def mutation_registry() -> tuple[MutationDefinition, ...]:
    definitions = _source_definitions()
    for definition in definitions:
        validate_true_sut_mutation(definition)
    return definitions


def _outcome_token(value: object) -> str:
    if isinstance(value, Exception):
        return "ERROR:" + type(value).__name__ + ":" + str(value)
    episode = getattr(value, "episode_state", None)
    if episode is None:
        return canonical_sha256({"value": repr(value)})
    return independent_digest(episode)


def _run_or_error(call: Callable[[], object]) -> object:
    try:
        return call()
    except ValueError as error:
        return error


def _arrival_fixture(sut: ModuleType, variant: int):
    retail, quant = _base_agents("mut-arrival-%d" % variant, sut=sut)
    return sut.arbitrate(
        "mut-arrival-%d" % variant, market(), (retail, quant),
        (
            make_action("mut-arrival-%d-retail" % variant, retail.agent_id, 1, sut=sut, quantity=variant),
            make_action("mut-arrival-%d-quant" % variant, quant.agent_id, 2, sut=sut, quantity=variant),
        ),
    )


def _replay_fixture(sut: ModuleType, variant: int):
    prefix = "mut-replay-%d" % variant
    retail, quant = _base_agents(prefix, sut=sut)
    original = make_action(prefix + "-reused", retail.agent_id, 1, sut=sut, quantity=variant)
    first = sut.arbitrate(prefix + ":one", market(), (retail, quant), (original,))
    duplicate = make_action(prefix + "-reused", retail.agent_id, 1, sut=sut, quantity=variant)
    return sut.arbitrate(prefix + ":two", market(), first.episode_state.current_agents, (duplicate,), prior_episode_state=first.episode_state)


def _peer_fixture(sut: ModuleType, variant: int):
    prefix = "mut-peer-%d" % variant
    retail, quant, buy, sell = peer_pair(prefix, variant, sut=sut)
    return sut.arbitrate(prefix, market(), (retail, quant), (buy, sell))


def _external_fixture(sut: ModuleType, variant: int):
    retail, quant = _base_agents("mut-external-%d" % variant, sut=sut)
    return sut.arbitrate(
        "mut-external-%d" % variant, market(), (retail, quant),
        (make_action("mut-external-%d-buy" % variant, retail.agent_id, 1, sut=sut, quantity=variant),),
    )


def _causal_fixture(sut: ModuleType, variant: int):
    retail, quant = _base_agents("mut-causal-%d" % variant, sut=sut)
    action = make_action(
        "mut-causal-%d-forward" % variant, retail.agent_id, 1, sut=sut, quantity=variant,
        parents=("not-yet-emitted-parent-%d" % variant,),
    )
    return sut.arbitrate("mut-causal-%d" % variant, market(), (retail, quant), (action,))


def _conflict_fixture(sut: ModuleType, variant: int):
    prefix = "mut-conflict-%d" % variant
    retail, quant = _base_agents(prefix, sut=sut)
    return sut.arbitrate(
        prefix, market(), (retail, quant),
        (
            make_action(prefix + "-first", retail.agent_id, 1, sut=sut, quantity=variant, conflict_key=prefix + "-resource"),
            make_action(prefix + "-second", quant.agent_id, 2, sut=sut, quantity=variant, conflict_key=prefix + "-resource"),
        ),
    )


def _carrier_fixture(sut: ModuleType, variant: int):
    class CarrierTuple(tuple):
        pass
    retail, quant = _base_agents("mut-boundary-%d" % variant, sut=sut)
    action = make_action("mut-boundary-%d-action" % variant, retail.agent_id, 1, sut=sut, quantity=variant)
    return sut.arbitrate("mut-boundary-%d" % variant, market(), (retail, quant), CarrierTuple((action,)))


def _execute_definition(definition: MutationDefinition, variant: int) -> MutationExecution:
    shadow = load_shadow_sut(definition.mutant_id, definition.replacements)
    mutant = shadow.module
    if definition.family == "arrival_order_identifier_order":
        baseline = _arrival_fixture(BASE_SUT, variant)
        mutated = _arrival_fixture(mutant, variant)
        baseline_report, mutant_report = evaluate_episode(baseline.episode_state), evaluate_episode(mutated.episode_state)
    elif definition.family == "duplicate_replay_reservation_after_terminal":
        baseline = _run_or_error(lambda: _replay_fixture(BASE_SUT, variant))
        mutated = _run_or_error(lambda: _replay_fixture(mutant, variant))
        baseline_report = None
        mutant_report = evaluate_episode(mutated.episode_state) if not isinstance(mutated, Exception) else None
    elif definition.family == "peer_transfer_partial_commit":
        baseline = _peer_fixture(BASE_SUT, variant)
        mutated = _peer_fixture(mutant, variant)
        baseline_report, mutant_report = evaluate_episode(baseline.episode_state), evaluate_episode(mutated.episode_state)
    elif definition.family == "external_flow_omitted":
        baseline = _external_fixture(BASE_SUT, variant)
        mutated = _external_fixture(mutant, variant)
        baseline_report, mutant_report = evaluate_episode(baseline.episode_state), evaluate_episode(mutated.episode_state)
    elif definition.family == "stored_ledger_hash_trusted":
        baseline_run = _external_fixture(BASE_SUT, variant)
        mutant_run = _external_fixture(mutant, variant)
        baseline = replace(baseline_run.episode_state, state_hash="tampered-state-hash-%d" % variant)
        mutated = replace(mutant_run.episode_state, state_hash="tampered-state-hash-%d" % variant)
        baseline_report = BASE_SUT.verify_episode_ledger(baseline)
        mutant_report = mutant.verify_episode_ledger(mutated)
        expected_hash = mutant_run.episode_state.state_hash
    elif definition.family == "causal_parent_forward_or_cycle":
        baseline = _causal_fixture(BASE_SUT, variant)
        mutated = _causal_fixture(mutant, variant)
        baseline_report, mutant_report = evaluate_episode(baseline.episode_state), evaluate_episode(mutated.episode_state)
    elif definition.family == "conflict_claim_release_expire_bypass":
        baseline = _conflict_fixture(BASE_SUT, variant)
        mutated = _conflict_fixture(mutant, variant)
        baseline_report, mutant_report = evaluate_episode(baseline.episode_state), evaluate_episode(mutated.episode_state)
    elif definition.family == "exact_primitive_enum_carrier_weakened":
        baseline = _run_or_error(lambda: _carrier_fixture(BASE_SUT, variant))
        mutated = _run_or_error(lambda: _carrier_fixture(mutant, variant))
        baseline_report = None
        mutant_report = None
    else:
        raise ValueError("UNKNOWN_MUTATION_FAMILY:" + definition.family)

    baseline_token = _outcome_token(baseline)
    mutant_token = _outcome_token(mutated)
    if definition.family == "stored_ledger_hash_trusted":
        baseline_token = canonical_sha256({"tampered_state_hash": baseline.state_hash, "verifier_valid": baseline_report.valid})
        mutant_token = canonical_sha256({"tampered_state_hash": mutated.state_hash, "verifier_valid": mutant_report.valid})
    behavior_changed = baseline_token != mutant_token
    reason_codes: tuple[str, ...]
    if definition.family == "stored_ledger_hash_trusted":
        hash_report = state_hash_binding_oracle(mutated, expected_hash)
        killed = (not baseline_report.valid) and mutant_report.valid and not hash_report.valid
        reason_codes = hash_report.reason_codes
    elif definition.family == "exact_primitive_enum_carrier_weakened":
        killed = isinstance(baseline, ValueError) and not isinstance(mutated, Exception)
        reason_codes = (definition.oracle_id,) if killed else ()
    elif definition.family == "duplicate_replay_reservation_after_terminal":
        killed = isinstance(baseline, ValueError) and mutant_report is not None and definition.oracle_id in mutant_report.reason_codes
        reason_codes = mutant_report.reason_codes if mutant_report is not None else ()
    else:
        killed = bool(baseline_report and baseline_report.valid and mutant_report and definition.oracle_id in mutant_report.reason_codes)
        reason_codes = mutant_report.reason_codes if mutant_report is not None else ()
    activation = MutationActivation(
        definition.mutant_id, definition.family, definition.fixture_id,
        shadow.source_sha256, shadow.mutant_source_sha256, baseline_token, mutant_token,
        behavior_changed, "SOURCE_DERIVED_SHADOW_MODULE", "KILLED" if killed else "SURVIVED",
    )
    kill = MutationKill(
        definition.mutant_id, "TEST-E23-MUTATION-" + definition.mutant_id,
        definition.oracle_id, killed, tuple(sorted(set(reason_codes))), False,
        "same_fixture_baseline=" + baseline_token + ";mutant=" + mutant_token,
    )
    return MutationExecution(activation, kill)


def execute_mutation(definition: MutationDefinition, variant: int = 1) -> MutationExecution:
    validate_true_sut_mutation(definition)
    execution = _execute_definition(definition, variant)
    if not execution.activation.behavior_changed:
        raise AssertionError("E23_DECORATIVE_MUTANT:" + definition.mutant_id)
    if execution.kill.digest_only:
        raise AssertionError("E23_DIGEST_ONLY_MUTATION_KILL:" + definition.mutant_id)
    return execution


def execute_mutation_registry() -> tuple[tuple[MutationActivation, ...], tuple[MutationKill, ...]]:
    executions = tuple(execute_mutation(definition) for definition in mutation_registry())
    return tuple(item.activation for item in executions), tuple(item.kill for item in executions)


def mutation_property_pairs() -> tuple[tuple[str, str], ...]:
    return tuple((definition.mutant_id, definition.paired_property_id) for definition in mutation_registry())
