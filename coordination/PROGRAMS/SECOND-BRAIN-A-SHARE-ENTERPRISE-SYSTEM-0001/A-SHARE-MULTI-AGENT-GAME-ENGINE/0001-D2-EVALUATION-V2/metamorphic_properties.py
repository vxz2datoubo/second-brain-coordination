"""Real transformed-input properties paired with executable shadow mutants."""
from __future__ import annotations

from dataclasses import replace
from types import ModuleType

import d2_game_core as BASE_SUT

from evaluation_v2_contract import PropertyReport, canonical_sha256
from independent_oracle import evaluate_episode, independent_digest, state_hash_binding_oracle
from mutation_registry import mutation_registry
from shadow_sut import load_shadow_sut
from synthetic_cases import _base_agents, make_action, peer_pair
from synthetic_engine.fixtures import market
from synthetic_engine.types import OrderSide


PROPERTY_IDS = (
    "MP-001-ARRIVAL-SEQUENCE-SWAP",
    "MP-002-ALPHA-RENAME-CONFLICT-EXCLUSION",
    "MP-003-CONTINUATION-IDENTITY-SUBSTITUTION",
    "MP-004-CAUSAL-PARENT-INJECTION",
    "MP-005-PEER-QUANTITY-SCALE",
    "MP-006-EXTERNAL-SIDE-TRANSFORM",
    "MP-007-STATE-HASH-TAMPER",
    "MP-008-EXACT-CARRIER-TRANSFORM",
)


def validate_transformation_registration(property_id: str, baseline_input: object, transformed_input: object) -> None:
    """A named metamorphic property must register an actual input transform."""
    if not property_id or canonical_sha256(baseline_input) == canonical_sha256(transformed_input):
        raise ValueError("E23_IDENTITY_OR_NOOP_METAMORPHIC_TRANSFORMATION_FORBIDDEN")


def _definition_for(mutant_id: str):
    return next(item for item in mutation_registry() if item.mutant_id == mutant_id)


def _shadow(mutant_id: str) -> ModuleType:
    definition = _definition_for(mutant_id)
    return load_shadow_sut(definition.mutant_id, definition.replacements).module


def _report(
    property_id: str,
    mutant_id: str,
    baseline_passed: bool,
    mutant_detected: bool,
    observation: str,
    baseline_value: object,
    transformed_value: object,
) -> PropertyReport:
    return PropertyReport(
        property_id, mutant_id, property_id + ":INPUT_TRANSFORMATION",
        baseline_passed, mutant_detected, observation,
        canonical_sha256(baseline_value), canonical_sha256(transformed_value),
    )


def _run_or_error(call):
    try:
        return call()
    except ValueError as error:
        return error


def arrival_sequence_swap(variant: int = 1) -> PropertyReport:
    """Swapping arrival sequence must reverse terminal event priority."""
    def run(sut: ModuleType, swapped: bool):
        retail, quant = _base_agents("mp-arrival-%d" % variant, sut=sut)
        retail_action = make_action("mp-arrival-%d-retail" % variant, retail.agent_id, 1, sut=sut, quantity=variant)
        quant_action = make_action("mp-arrival-%d-quant" % variant, quant.agent_id, 2, sut=sut, quantity=variant)
        if swapped:
            retail_action, quant_action = replace(retail_action, arrival_sequence=2), replace(quant_action, arrival_sequence=1)
        return sut.arbitrate("mp-arrival-%d" % variant, market(), (retail, quant), (retail_action, quant_action))
    baseline = run(BASE_SUT, False)
    transformed = run(BASE_SUT, True)
    baseline_ids = tuple(event.action_id for event in baseline.events)
    transformed_ids = tuple(event.action_id for event in transformed.events)
    baseline_passed = evaluate_episode(baseline.episode_state).valid and evaluate_episode(transformed.episode_state).valid and transformed_ids == tuple(reversed(baseline_ids))
    mutant = _shadow("MUT-001-ARRIVAL-IDENTIFIER-ORDER")
    mutant_baseline = run(mutant, False)
    mutant_transformed = run(mutant, True)
    mutant_baseline_ids = tuple(event.action_id for event in mutant_baseline.events)
    mutant_transformed_ids = tuple(event.action_id for event in mutant_transformed.events)
    mutant_detected = mutant_transformed_ids != tuple(reversed(mutant_baseline_ids))
    return _report(PROPERTY_IDS[0], "MUT-001-ARRIVAL-IDENTIFIER-ORDER", baseline_passed, mutant_detected,
                   "arrival_swap_changes_expected_priority;mutant_relation=METAMORPHIC_ARRIVAL_RELATION_VIOLATION",
                   baseline_ids, transformed_ids)


def alpha_rename_conflict_exclusion(variant: int = 1) -> PropertyReport:
    """Consistent identifier renaming preserves conflict exclusion, not identity labels."""
    def run(sut: ModuleType, first_name: str, second_name: str):
        retail, quant = _base_agents("mp-alpha-%d" % variant, sut=sut)
        retail = replace(retail, agent_id=first_name)
        quant = replace(quant, agent_id=second_name)
        resource = "mp-alpha-resource-%d" % variant
        actions = (
            make_action("mp-alpha-%d-first" % variant, retail.agent_id, 1, sut=sut, quantity=variant, conflict_key=resource),
            make_action("mp-alpha-%d-second" % variant, quant.agent_id, 2, sut=sut, quantity=variant, conflict_key=resource),
        )
        return sut.arbitrate("mp-alpha-%d" % variant, market(), (retail, quant), actions), {first_name: "first", second_name: "second"}
    baseline, baseline_roles = run(BASE_SUT, "role-first", "role-second")
    transformed, transformed_roles = run(BASE_SUT, "zeta-renamed", "alpha-renamed")
    def normalized(run, roles):
        return tuple((roles[event.agent_id], event.accepted, event.outcome_status, event.filled_quantity) for event in run.events)
    baseline_trace = normalized(baseline, baseline_roles)
    transformed_trace = normalized(transformed, transformed_roles)
    baseline_passed = evaluate_episode(baseline.episode_state).valid and evaluate_episode(transformed.episode_state).valid and baseline_trace == transformed_trace and not baseline_trace[1][1]
    mutant = _shadow("MUT-007-CONFLICT-OWNERSHIP-BYPASS")
    mutant_run, _roles = run(mutant, "zeta-renamed", "alpha-renamed")
    mutant_report = evaluate_episode(mutant_run.episode_state)
    mutant_detected = "ORACLE_CONFLICT_CLAIM_BYPASS" in mutant_report.reason_codes
    return _report(PROPERTY_IDS[1], "MUT-007-CONFLICT-OWNERSHIP-BYPASS", baseline_passed, mutant_detected,
                   "alpha_rename_preserves_exclusion;mutant_reason=" + ",".join(mutant_report.reason_codes), baseline_trace, transformed_trace)


def continuation_identity_substitution(variant: int = 1) -> PropertyReport:
    """Replacing a fresh continuation action with a prior identity must fail closed."""
    def continuation(sut: ModuleType, duplicate: bool):
        prefix = "mp-continuation-%d" % variant
        retail, quant = _base_agents(prefix, sut=sut)
        prior_action = make_action(prefix + "-prior", retail.agent_id, 1, sut=sut, quantity=variant)
        prior = sut.arbitrate(prefix + ":one", market(), (retail, quant), (prior_action,))
        next_name = prefix + "-prior" if duplicate else prefix + "-fresh"
        next_action = make_action(next_name, quant.agent_id if not duplicate else retail.agent_id, 1, sut=sut, quantity=variant)
        return sut.arbitrate(prefix + ":two", market(), prior.episode_state.current_agents, (next_action,), prior_episode_state=prior.episode_state)
    baseline_control = _run_or_error(lambda: continuation(BASE_SUT, False))
    baseline_transformed = _run_or_error(lambda: continuation(BASE_SUT, True))
    baseline_passed = not isinstance(baseline_control, Exception) and isinstance(baseline_transformed, ValueError)
    mutant_transformed = _run_or_error(lambda: continuation(_shadow("MUT-002-LATE-REPLAY-RESERVATION"), True))
    mutant_report = evaluate_episode(mutant_transformed.episode_state) if not isinstance(mutant_transformed, Exception) else None
    mutant_detected = mutant_report is not None and "ORACLE_DUPLICATE_OR_INVALID_ACTION_ID" in mutant_report.reason_codes
    return _report(PROPERTY_IDS[2], "MUT-002-LATE-REPLAY-RESERVATION", baseline_passed, mutant_detected,
                   "fresh_to_duplicate_continuation;mutant_reason=" + ",".join(mutant_report.reason_codes if mutant_report else ()),
                   "fresh_accept", "duplicate_reject")


def causal_parent_injection(variant: int = 1) -> PropertyReport:
    """Injecting an unavailable parent changes a valid action to zero-fill blocked."""
    def run(sut: ModuleType, injected: bool):
        retail, quant = _base_agents("mp-causal-%d" % variant, sut=sut)
        parents = ("not-yet-parent-%d" % variant,) if injected else ()
        action = make_action("mp-causal-%d-action" % variant, retail.agent_id, 1, sut=sut, quantity=variant, parents=parents)
        return sut.arbitrate("mp-causal-%d" % variant, market(), (retail, quant), (action,))
    baseline = run(BASE_SUT, False)
    transformed = run(BASE_SUT, True)
    baseline_passed = evaluate_episode(baseline.episode_state).valid and evaluate_episode(transformed.episode_state).valid and baseline.events[0].accepted and not transformed.events[0].accepted and transformed.events[0].filled_quantity == 0
    mutant_transformed = run(_shadow("MUT-006-FORWARD-CAUSAL"), True)
    mutant_report = evaluate_episode(mutant_transformed.episode_state)
    mutant_detected = "ORACLE_FORWARD_OR_CYCLIC_CAUSAL_PARENT" in mutant_report.reason_codes
    return _report(PROPERTY_IDS[3], "MUT-006-FORWARD-CAUSAL", baseline_passed, mutant_detected,
                   "inject_unknown_parent;mutant_reason=" + ",".join(mutant_report.reason_codes),
                   (baseline.events[0].accepted,), (transformed.events[0].accepted, transformed.events[0].filled_quantity))


def peer_quantity_scale(variant: int = 1) -> PropertyReport:
    """Scaling both legs preserves closed-system peer conservation."""
    def run(sut: ModuleType, quantity: int):
        retail, quant, buy, sell = peer_pair("mp-peer-%d-%d" % (variant, quantity), quantity, sut=sut)
        return sut.arbitrate("mp-peer-%d-%d" % (variant, quantity), market(), (retail, quant), (buy, sell))
    baseline = run(BASE_SUT, variant)
    transformed = run(BASE_SUT, variant + 1)
    baseline_passed = evaluate_episode(baseline.episode_state).valid and evaluate_episode(transformed.episode_state).valid
    mutant_transformed = run(_shadow("MUT-003-PARTIAL-PEER-COMMIT"), variant + 1)
    mutant_report = evaluate_episode(mutant_transformed.episode_state)
    mutant_detected = "ORACLE_PARTIAL_PEER_COMMIT" in mutant_report.reason_codes
    return _report(PROPERTY_IDS[4], "MUT-003-PARTIAL-PEER-COMMIT", baseline_passed, mutant_detected,
                   "peer_quantity_scale_preserves_zero_sum;mutant_reason=" + ",".join(mutant_report.reason_codes),
                   independent_digest(baseline.episode_state), independent_digest(transformed.episode_state))


def external_side_transform(variant: int = 1) -> PropertyReport:
    """Changing an external order side flips the declared open-system offset."""
    def run(sut: ModuleType, side: OrderSide):
        retail, quant = _base_agents("mp-external-%d-%s" % (variant, side.value.lower()), sut=sut)
        owner = retail if side is OrderSide.BUY else quant
        action = make_action("mp-external-%d-%s" % (variant, side.value.lower()), owner.agent_id, 1, sut=sut, side=side, quantity=variant)
        return sut.arbitrate("mp-external-%d-%s" % (variant, side.value.lower()), market(), (retail, quant), (action,))
    baseline = run(BASE_SUT, OrderSide.BUY)
    transformed = run(BASE_SUT, OrderSide.SELL)
    baseline_passed = evaluate_episode(baseline.episode_state).valid and evaluate_episode(transformed.episode_state).valid and baseline.episode_state.external_liquidity_flows[0].agent_inventory_delta == -transformed.episode_state.external_liquidity_flows[0].agent_inventory_delta
    mutant_transformed = run(_shadow("MUT-004-EXTERNAL-FLOW-OMITTED"), OrderSide.SELL)
    mutant_report = evaluate_episode(mutant_transformed.episode_state)
    mutant_detected = "ORACLE_EXTERNAL_FLOW_MISSING_OR_DUPLICATE" in mutant_report.reason_codes
    return _report(PROPERTY_IDS[5], "MUT-004-EXTERNAL-FLOW-OMITTED", baseline_passed, mutant_detected,
                   "external_side_flips_offset;mutant_reason=" + ",".join(mutant_report.reason_codes),
                   independent_digest(baseline.episode_state), independent_digest(transformed.episode_state))


def state_hash_tamper(variant: int = 1) -> PropertyReport:
    """Changing only stored state hash must be rejected by the SUT verifier."""
    def run(sut: ModuleType):
        retail, quant = _base_agents("mp-hash-%d" % variant, sut=sut)
        action = make_action("mp-hash-%d-action" % variant, retail.agent_id, 1, sut=sut, quantity=variant)
        return sut.arbitrate("mp-hash-%d" % variant, market(), (retail, quant), (action,))
    baseline_run = run(BASE_SUT)
    tampered_baseline = replace(baseline_run.episode_state, state_hash="tampered-hash-%d" % variant)
    baseline_verification = BASE_SUT.verify_episode_ledger(tampered_baseline)
    baseline_passed = evaluate_episode(baseline_run.episode_state).valid and not baseline_verification.valid
    mutant = _shadow("MUT-005-STORED-HASH-TRUST")
    mutant_run = run(mutant)
    tampered_mutant = replace(mutant_run.episode_state, state_hash="tampered-hash-%d" % variant)
    mutant_verification = mutant.verify_episode_ledger(tampered_mutant)
    binding = state_hash_binding_oracle(tampered_mutant, mutant_run.episode_state.state_hash)
    mutant_detected = mutant_verification.valid and not binding.valid
    return _report(PROPERTY_IDS[6], "MUT-005-STORED-HASH-TRUST", baseline_passed, mutant_detected,
                   "tamper_state_hash;mutant_binding=" + ",".join(binding.reason_codes),
                   baseline_run.episode_state.state_hash, tampered_baseline.state_hash)


def exact_carrier_transform(variant: int = 1) -> PropertyReport:
    """Replacing an exact tuple carrier with a subclass must remain fail closed."""
    def run(sut: ModuleType):
        class CarrierTuple(tuple):
            pass
        retail, quant = _base_agents("mp-boundary-%d" % variant, sut=sut)
        action = make_action("mp-boundary-%d-action" % variant, retail.agent_id, 1, sut=sut, quantity=variant)
        return sut.arbitrate("mp-boundary-%d" % variant, market(), (retail, quant), CarrierTuple((action,)))
    baseline = _run_or_error(lambda: run(BASE_SUT))
    mutant = _run_or_error(lambda: run(_shadow("MUT-008-NOMINAL-BOUNDARY")))
    baseline_passed = isinstance(baseline, ValueError)
    mutant_detected = not isinstance(mutant, Exception)
    return _report(PROPERTY_IDS[7], "MUT-008-NOMINAL-BOUNDARY", baseline_passed, mutant_detected,
                   "exact_tuple_to_subclass;baseline=" + type(baseline).__name__ + ";mutant=" + type(mutant).__name__,
                   type(baseline).__name__, type(mutant).__name__)


def property_function_map():
    return {
        PROPERTY_IDS[0]: arrival_sequence_swap,
        PROPERTY_IDS[1]: alpha_rename_conflict_exclusion,
        PROPERTY_IDS[2]: continuation_identity_substitution,
        PROPERTY_IDS[3]: causal_parent_injection,
        PROPERTY_IDS[4]: peer_quantity_scale,
        PROPERTY_IDS[5]: external_side_transform,
        PROPERTY_IDS[6]: state_hash_tamper,
        PROPERTY_IDS[7]: exact_carrier_transform,
    }


def run_metamorphic_properties(variant: int = 1) -> tuple[PropertyReport, ...]:
    return tuple(function(variant) for function in property_function_map().values())
