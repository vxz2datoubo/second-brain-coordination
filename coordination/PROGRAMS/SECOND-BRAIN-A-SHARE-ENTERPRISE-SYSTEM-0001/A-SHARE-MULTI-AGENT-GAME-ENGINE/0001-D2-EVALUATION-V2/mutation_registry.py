"""Executable E22 mutation registry; no boolean-only mutant predicates."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from d2_game_core import CandidateAction, arbitrate
from synthetic_engine.fixtures import market

from evaluation_v2_contract import MutationActivation, MutationKill, canonical_sha256
from independent_oracle import evaluate_episode, independent_digest
from synthetic_cases import ScenarioSpec, _base_agents, execute_scenario, make_action


@dataclass(frozen=True)
class MutationProbe:
    baseline: object
    mutated: object
    baseline_digest: str
    mutated_digest: str
    changed: bool
    observation: str


@dataclass(frozen=True)
class MutationDefinition:
    mutant_id: str
    family: str
    fixture_id: str
    killer_test_ids: tuple[str, ...]
    activate: Callable[[], MutationProbe]
    kill: Callable[[MutationProbe], tuple[bool, str, str]]


def _conflict_result(prefix: str):
    return execute_scenario(ScenarioSpec(prefix, "conflict", 1, "REQ-E22-MUT", "TEST-MUTATION"))


def _external_result(prefix: str):
    return execute_scenario(ScenarioSpec(prefix, "external_buy", 1, "REQ-E22-MUT", "TEST-MUTATION"))


def _peer_result(prefix: str):
    return execute_scenario(ScenarioSpec(prefix, "peer", 1, "REQ-E22-MUT", "TEST-MUTATION"))


def _causal_result(prefix: str):
    return execute_scenario(ScenarioSpec(prefix, "causal", 1, "REQ-E22-MUT", "TEST-MUTATION"))


def _probe_episode(baseline: object, mutated: object, observation: str) -> MutationProbe:
    baseline_digest = independent_digest(baseline.episode_state)
    mutated_digest = independent_digest(mutated if hasattr(mutated, "event_dag") else mutated.episode_state)
    return MutationProbe(baseline, mutated, baseline_digest, mutated_digest, baseline_digest != mutated_digest, observation)


def _arrival_order_probe() -> MutationProbe:
    retail, quant = _base_agents("mut-arrival")
    declared = (
        make_action("mut-arrival-zeta", retail.agent_id, 1, conflict_key="mut-arrival-resource"),
        make_action("mut-arrival-alpha", quant.agent_id, 2, conflict_key="mut-arrival-resource"),
    )
    baseline = arbitrate("mut-arrival", market(), (retail, quant), declared)
    # A real fault substitutes identifier order for the declared immutable
    # arrival order. Re-numbering makes that altered priority observable to the
    # public SUT instead of merely permuting an input collection it sorts again.
    mutant = tuple(
        replace(action, arrival_sequence=index)
        for index, action in enumerate(sorted(declared, key=lambda item: (item.agent_id, item.action_id)), start=1)
    )
    mutated = arbitrate("mut-arrival", market(), (retail, quant), mutant)
    base_winner = next(event.agent_id for event in baseline.events if event.accepted)
    mutant_winner = next(event.agent_id for event in mutated.events if event.accepted)
    return MutationProbe(baseline, mutated, independent_digest(baseline.episode_state), independent_digest(mutated.episode_state),
                         base_winner != mutant_winner, "declared=" + base_winner + "; identifier_order=" + mutant_winner)


def _arrival_kill(probe: MutationProbe) -> tuple[bool, str, str]:
    return probe.changed, "MUT-ARRIVAL-ORDER", probe.observation


def _duplicate_reservation_probe() -> MutationProbe:
    baseline = execute_scenario(ScenarioSpec("MUT-DUP", "blocked", 1, "REQ-E22-MUT", "TEST-MUTATION"))
    episode = baseline.episode_state
    mutated = replace(episode, action_registry=())
    return _probe_episode(baseline, mutated, "terminal action registry removed after blocked terminal event")


def _oracle_invalid_kill(probe: MutationProbe) -> tuple[bool, str, str]:
    report = evaluate_episode(probe.mutated, expected_digest=probe.baseline_digest)
    return (not report.valid), "ORACLE-INDEPENDENT-ACCOUNTING", ",".join(report.reason_codes)


def _peer_partial_probe() -> MutationProbe:
    baseline = _peer_result("MUT-PEER")
    episode = baseline.episode_state
    first = episode.event_dag[0]
    mutated_events = (replace(first, filled_quantity=0),) + episode.event_dag[1:]
    mutated = replace(episode, event_dag=mutated_events)
    return _probe_episode(baseline, mutated, "one peer leg filled quantity changed to zero")


def _external_omitted_probe() -> MutationProbe:
    baseline = _external_result("MUT-EXTERNAL")
    episode = baseline.episode_state
    mutated = replace(episode, external_liquidity_flows=())
    return _probe_episode(baseline, mutated, "external offset removed")


def _stored_hash_probe() -> MutationProbe:
    baseline = _external_result("MUT-HASH")
    episode = baseline.episode_state
    first = episode.event_dag[0]
    mutated = replace(episode, event_dag=(replace(first, accepted=False, filled_quantity=0),) + episode.event_dag[1:],
                      state_hash="stored-hash-not-trusted")
    return _probe_episode(baseline, mutated, "event semantics changed while stored state hash is forged")


def _causal_cycle_probe() -> MutationProbe:
    baseline = _causal_result("MUT-CAUSAL")
    episode = baseline.episode_state
    last = episode.event_dag[-1]
    mutated_events = episode.event_dag[:-1] + (replace(last, causal_parent_event_ids=(last.event_id,)),)
    mutated = replace(episode, event_dag=mutated_events)
    return _probe_episode(baseline, mutated, "forward/self causal parent accepted in stored record")


def _conflict_bypass_probe() -> MutationProbe:
    baseline = _conflict_result("MUT-CONFLICT")
    episode = baseline.episode_state
    second = episode.event_dag[1]
    mutated_events = episode.event_dag[:1] + (replace(second, accepted=True, filled_quantity=1, outcome_status="FILLED"),) + episode.event_dag[2:]
    mutated = replace(episode, event_dag=mutated_events)
    return _probe_episode(baseline, mutated, "second conflict claimant changed from blocked to accepted")


def _exact_boundary_probe() -> MutationProbe:
    retail, quant = _base_agents("mut-exact")
    source = make_action("mut-exact-action", retail.agent_id, 1)
    class NominalAction(CandidateAction):
        pass
    variants = {
        "nominal_carrier": NominalAction(**source.__dict__),
        "string_enum": replace(source, label="feasible"),
        "bool_primitive": replace(source, arrival_sequence=True),
        "multi_fault": replace(source, label="feasible", arrival_sequence=True),
    }
    observed = {}
    for name, action in variants.items():
        try:
            arbitrate("mut-exact-" + name, market(), (retail, quant), (action,))
        except ValueError as error:
            observed[name] = str(error)
        else:
            observed[name] = "INVALID_BOUNDARY_ACCEPTED"
    baseline = {"valid_action_type": type(source).__name__}
    mutated = {"boundary_results": observed}
    observation = ";".join(name + "=" + observed[name] for name in sorted(observed))
    return MutationProbe(baseline, mutated, canonical_sha256(baseline), canonical_sha256(mutated),
                         all(value != "INVALID_BOUNDARY_ACCEPTED" for value in observed.values()), observation)


def _exact_boundary_kill(probe: MutationProbe) -> tuple[bool, str, str]:
    return probe.changed and "INVALID_BOUNDARY_ACCEPTED" not in probe.observation, "ORACLE-EXACT-BOUNDARY", probe.observation


def mutation_registry() -> tuple[MutationDefinition, ...]:
    return (
        MutationDefinition("MUT-001-ARRIVAL-IDENTIFIER-ORDER", "arrival_order_identifier_order", "SCN-CONFLICT", ("TEST-MUTATION-REGISTRY",), _arrival_order_probe, _arrival_kill),
        MutationDefinition("MUT-002-LATE-REPLAY-RESERVATION", "duplicate_replay_reservation_after_terminal", "SCN-BLOCKED", ("TEST-MUTATION-REGISTRY",), _duplicate_reservation_probe, _oracle_invalid_kill),
        MutationDefinition("MUT-003-PARTIAL-PEER-COMMIT", "peer_transfer_partial_commit", "SCN-PEER", ("TEST-MUTATION-REGISTRY",), _peer_partial_probe, _oracle_invalid_kill),
        MutationDefinition("MUT-004-EXTERNAL-FLOW-OMITTED", "external_flow_omitted_or_sign_inverted", "SCN-EXTERNAL", ("TEST-MUTATION-REGISTRY",), _external_omitted_probe, _oracle_invalid_kill),
        MutationDefinition("MUT-005-STORED-HASH-TRUST", "stored_ledger_hash_trusted", "SCN-EXTERNAL", ("TEST-MUTATION-REGISTRY",), _stored_hash_probe, _oracle_invalid_kill),
        MutationDefinition("MUT-006-FORWARD-CAUSAL", "causal_parent_forward_or_cycle", "SCN-CAUSAL", ("TEST-MUTATION-REGISTRY",), _causal_cycle_probe, _oracle_invalid_kill),
        MutationDefinition("MUT-007-CONFLICT-OWNERSHIP-BYPASS", "conflict_claim_release_expire_bypass", "SCN-CONFLICT", ("TEST-MUTATION-REGISTRY",), _conflict_bypass_probe, _oracle_invalid_kill),
        MutationDefinition("MUT-008-NOMINAL-BOUNDARY", "exact_primitive_enum_carrier_weakened", "SCN-BOUNDARY", ("TEST-MUTATION-REGISTRY",), _exact_boundary_probe, _exact_boundary_kill),
    )


def execute_mutation_registry() -> tuple[tuple[MutationActivation, ...], tuple[MutationKill, ...]]:
    activations: list[MutationActivation] = []
    kills: list[MutationKill] = []
    for definition in mutation_registry():
        probe = definition.activate()
        killed, oracle_id, observation = definition.kill(probe)
        status = "KILLED" if killed else "SURVIVED"
        activations.append(MutationActivation(
            definition.mutant_id, definition.family, definition.fixture_id, probe.baseline_digest,
            probe.mutated_digest, probe.changed, definition.killer_test_ids, status,
        ))
        kills.append(MutationKill(definition.mutant_id, definition.killer_test_ids[0], oracle_id, killed, observation))
    return tuple(activations), tuple(kills)
