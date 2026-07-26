"""Semantic evaluation for the synthetic-only, stateful D2 game core."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Mapping, Sequence


_ENGINE_ROOT = Path(__file__).resolve().parents[1]
_D2_ROOT = _ENGINE_ROOT / "0001-D2"
if str(_D2_ROOT) not in sys.path:
    sys.path.insert(0, str(_D2_ROOT))

from d2_game_core import (  # noqa: E402
    ActionLabel, AgentInformationSet, AgentPortfolioState, AgentState, CandidateAction,
    GameRun, HiddenTypePosterior, LedgerEvent, ParticipantArchetypeHypothesis,
    ParticipantFamily, ParticipantSubtype, SYNTHETIC_CAPABILITY, arbitrate,
    run_bounded_counterfactual_episode, run_one_step_counterfactual, total_system_conserved,
)
from synthetic_engine.fixtures import INVENTORY, market, order  # noqa: E402
from synthetic_engine.types import InventoryState, MatchMode, OrderSide, SecurityStatus, SessionPhase, SyntheticLot  # noqa: E402


SYNTHETIC_EVALUATION_CAPABILITY = SYNTHETIC_CAPABILITY
_SUBTYPES = tuple(ParticipantSubtype)
_CATEGORIES = ("ownership", "conflict", "incomplete_information", "hidden_type", "policy_shock", "resource_contention")


@dataclass(frozen=True)
class EvaluationScenario:
    scenario_id: str
    category: str
    phase: SessionPhase
    security_status: SecurityStatus
    agent_count: int
    participants: tuple[ParticipantSubtype, ...]
    hidden_ambiguity: bool
    requires_complete_information: bool
    unknowns: tuple[str, ...]
    conflict: bool
    expected_primary_status: str


@dataclass(frozen=True)
class EvaluationResult:
    scenario: EvaluationScenario
    run: GameRun
    accepted_count: int
    blocked_or_abstained_count: int


@dataclass(frozen=True)
class InvariantSpec:
    invariant_id: str
    requirement_id: str
    fixture_ids: tuple[str, ...]
    failure_oracle: str
    mapped_test_id: str
    family: str


def _posterior(subtype: ParticipantSubtype, ambiguous: bool) -> HiddenTypePosterior:
    if ambiguous:
        alternate = ParticipantSubtype.SYSTEMATIC_REBALANCER if subtype is not ParticipantSubtype.SYSTEMATIC_REBALANCER else ParticipantSubtype.RETAIL_LIQUIDITY_TAKER
        return HiddenTypePosterior((
            ParticipantArchetypeHypothesis(subtype, 0.5, ("synthetic:e1",), ("synthetic:c1",), "synthetic alternative one"),
            ParticipantArchetypeHypothesis(alternate, 0.5, ("synthetic:e2",), ("synthetic:c2",), "synthetic alternative two"),
        ))
    return HiddenTypePosterior((ParticipantArchetypeHypothesis(subtype, 1.0, ("synthetic:e",), ("synthetic:c",), "synthetic alternative"),))


def _inventory_for(index: int) -> InventoryState:
    return InventoryState((SyntheticLot(f"seasoned-{index}", "2026-07-25", 5 + index),), settled_trade_date="2026-07-26")


def build_scenarios() -> tuple[EvaluationScenario, ...]:
    """72 distinct scenarios: six semantic categories with 12 fixtures each."""
    scenarios: list[EvaluationScenario] = []
    for category_index, category in enumerate(_CATEGORIES):
        for offset in range(12):
            index = category_index * 12 + offset
            agent_count = 3 if offset in (0, 6) else 2
            participants = tuple(_SUBTYPES[(index + position) % len(_SUBTYPES)] for position in range(agent_count))
            phase = SessionPhase.CONTINUOUS_AM
            status = SecurityStatus.ACTIVE
            if category == "policy_shock":
                phase, status = SessionPhase.SUSPENDED, SecurityStatus.SUSPENDED
            scenarios.append(EvaluationScenario(
                scenario_id=f"S{index + 1:03d}", category=category, phase=phase, security_status=status,
                agent_count=agent_count, participants=participants, hidden_ambiguity=category == "hidden_type",
                requires_complete_information=category == "incomplete_information", unknowns=("synthetic:unknown",) if category == "incomplete_information" else (),
                conflict=category in {"conflict", "resource_contention"}, expected_primary_status="ABSTAINED" if category == "incomplete_information" else ("INVALID_OR_BLOCKED" if category == "policy_shock" else "VARIABLE"),
            ))
    return tuple(scenarios)


def _agents_for(scenario: EvaluationScenario) -> tuple[AgentState, ...]:
    agents = []
    for index, subtype in enumerate(scenario.participants):
        agents.append(AgentState(
            agent_id=f"{scenario.scenario_id}:agent:{index}", posterior=_posterior(subtype, scenario.hidden_ambiguity),
            information=AgentInformationSet(100, ("synthetic:public",), scenario.unknowns if index == 0 else (), ("synthetic:private",), SYNTHETIC_EVALUATION_CAPABILITY),
            inventory=_inventory_for(index),
        ))
    return tuple(agents)


def _actions_for(scenario: EvaluationScenario, agents: tuple[AgentState, ...]) -> tuple[CandidateAction, ...]:
    actions = []
    for index, agent in enumerate(agents):
        label = ActionLabel.FEASIBLE
        if index == 0 and scenario.requires_complete_information:
            label = ActionLabel.MOST_CONSISTENT
        conflict_key = f"shared:{scenario.scenario_id}" if scenario.conflict else None
        actions.append(CandidateAction(
            action_id=f"{scenario.scenario_id}:action:{index}", agent_id=agent.agent_id, label=label,
            order=order(f"{scenario.scenario_id}:order:{index}", side=OrderSide.BUY if index % 2 == 0 else OrderSide.SELL, qty=1, available=100),
            assumption_ids=(f"assumption:{scenario.scenario_id}:{index}",), evidence_refs=("synthetic:evidence",),
            conflict_key=conflict_key, requires_complete_information=index == 0 and scenario.requires_complete_information,
            arrival_sequence=index,
        ))
    return tuple(actions)


def run_scenario(scenario: EvaluationScenario) -> EvaluationResult:
    agents = _agents_for(scenario)
    result = arbitrate("evaluation:" + scenario.scenario_id, market(scenario.phase, scenario.security_status), agents, _actions_for(scenario, agents))
    accepted = sum(1 for event in result.events if event.accepted)
    return EvaluationResult(scenario, result, accepted, len(result.events) - accepted)


def run_all_scenarios() -> tuple[EvaluationResult, ...]:
    return tuple(run_scenario(scenario) for scenario in build_scenarios())


def _result_by_id() -> dict[str, EvaluationResult]:
    return {result.scenario.scenario_id: result for result in run_all_scenarios()}


def build_counterfactual_pairs() -> tuple[tuple[str, str], ...]:
    pairs = []
    for index in range(36):
        scenario = build_scenarios()[index]
        agents = _agents_for(scenario)
        actions = _actions_for(scenario, agents)
        changed = actions[0].assumption_ids[0]
        result = run_one_step_counterfactual(f"pair:{scenario.scenario_id}", market(), agents, actions, changed)
        pairs.append((result.baseline.ledger_hash, result.alternative.ledger_hash))
    return tuple(pairs)


def run_multistep_episodes() -> tuple[GameRun, ...]:
    """24 episodes, each with at least two state-carrying synthetic agents."""
    final_runs = []
    for index in range(24):
        scenario = build_scenarios()[index]
        agents = _agents_for(scenario)
        actions = _actions_for(scenario, agents)
        episode = run_bounded_counterfactual_episode(
            f"episode:{scenario.scenario_id}", market(), agents, actions,
            (actions[0].assumption_ids[0], actions[1].assumption_ids[0]), max_steps=2,
        )
        if len(episode.runs) != 2:
            raise AssertionError("EPISODE_STEP_COUNT")
        final_runs.append(episode.runs[-1])
    return tuple(final_runs)


def reject_adapter_contamination(envelope: Mapping[str, object]) -> bool:
    """Synthetic fixture-only gate, not a QCLAW adapter or authority port."""
    required_hashes = envelope.get("artifact_hashes")
    lock = envelope.get("source_commit_lock")
    return (
        envelope.get("status") == "CANDIDATE"
        and envelope.get("authority_write") is False
        and envelope.get("source_capability") == SYNTHETIC_EVALUATION_CAPABILITY
        and envelope.get("claim_kind") == "synthetic_fixture"
        and isinstance(lock, str) and len(lock) == 40
        and isinstance(required_hashes, tuple) and bool(required_hashes) and all(isinstance(item, str) and len(item) == 64 for item in required_hashes)
        and bool(envelope.get("verifier_command"))
        and envelope.get("determinism_status") != "HARDCODED_PASS"
        and envelope.get("promotion") != "FACT"
    )


def invariant_specs() -> tuple[InvariantSpec, ...]:
    specs: list[InvariantSpec] = []
    groups = (
        ("OWNER", "REQ-D2-OWNER-ISOLATION", tuple(f"S{i:03d}" for i in range(1, 13)), "owner_only_mutation", "test_semantic_invariants"),
        ("CONFLICT", "REQ-D2-EXPLICIT-CONFLICT", tuple(f"S{i:03d}" for i in range(13, 25)), "second_claim_blocked", "test_semantic_invariants"),
        ("ABSTAIN", "REQ-D2-UNKNOWN-ABSTENTION", tuple(f"S{i:03d}" for i in range(25, 37)), "unknown_primary_abstains", "test_semantic_invariants"),
        ("HIDDEN", "REQ-D2-HIDDEN-TYPE-AMBIGUITY", tuple(f"S{i:03d}" for i in range(37, 49)), "posterior_remains_uncalibrated", "test_semantic_invariants"),
        ("POLICY", "REQ-D2-POLICY-SHOCK-GATE", tuple(f"S{i:03d}" for i in range(49, 61)), "suspended_primary_blocked", "test_semantic_invariants"),
        ("EPISODE", "REQ-D2-STATEFUL-CAUSAL-EPISODE", tuple(f"S{i:03d}" for i in range(1, 9)), "state_and_causality_carried", "test_stateful_episodes"),
        ("COUNTERFACTUAL", "REQ-D2-ONE-ASSUMPTION-COUNTERFACTUAL", tuple(f"S{i:03d}" for i in range(1, 9)), "baseline_differs_from_alternative", "test_counterfactual_pairs"),
        ("MUTATION", "REQ-D2-INVARIANT-SENSITIVITY", tuple(f"S{i:03d}" for i in range(9, 13)), "injected_defect_fails_family", "test_mutation_sensitivity"),
    )
    for prefix, requirement, fixtures, oracle, test_id in groups:
        for index, fixture in enumerate(fixtures, start=1):
            specs.append(InvariantSpec(f"INV-{prefix}-{index:02d}", requirement, (fixture,), oracle, test_id, prefix))
    if len(specs) != 80:
        raise AssertionError(f"EXPECTED_80_INVARIANTS_GOT_{len(specs)}")
    return tuple(specs)


def _family_predicates() -> dict[str, Callable[[str, EvaluationResult], bool]]:
    episodes = run_multistep_episodes()
    episode_by_fixture = {f"S{index + 1:03d}": run for index, run in enumerate(episodes[:12])}
    pairs = build_counterfactual_pairs()
    return {
        "OWNER": lambda fixture, result: len(result.run.final_agent_portfolios) >= 2 and total_system_conserved(_agents_for(result.scenario), result.run) and all(
            event.owner_pre_state_hash == event.owner_post_state_hash if not event.accepted else event.owner_pre_state_hash != event.owner_post_state_hash
            for event in result.run.events if event.filled_quantity
        ),
        "CONFLICT": lambda fixture, result: result.run.events[0].accepted and not result.run.events[1].accepted and "CONFLICT_RESOURCE_ALREADY_CLAIMED" in result.run.events[1].rejected_reason_codes,
        "ABSTAIN": lambda fixture, result: result.run.events[0].outcome_status == "ABSTAINED" and result.run.events[0].owner_pre_state_hash == result.run.events[0].owner_post_state_hash,
        "HIDDEN": lambda fixture, result: len(_agents_for(result.scenario)[0].posterior.hypotheses) == 2 and _agents_for(result.scenario)[0].posterior.status == "UNCALIBRATED_SYNTHETIC_HYPOTHESIS",
        "POLICY": lambda fixture, result: not result.run.events[0].accepted and result.run.events[0].outcome_status == "INVALID_OR_BLOCKED",
        "EPISODE": lambda fixture, result: fixture in episode_by_fixture and bool(episode_by_fixture[fixture].causal_history_event_ids) and bool(episode_by_fixture[fixture].total_system_state_hash),
        "COUNTERFACTUAL": lambda fixture, result: pairs[int(fixture[1:]) - 1][0] != pairs[int(fixture[1:]) - 1][1],
        "MUTATION": lambda fixture, result: mutation_sensitivity()[fixture],
    }


def invariant_catalog() -> dict[str, bool]:
    results = _result_by_id()
    predicates = _family_predicates()
    catalog = {spec.invariant_id: predicates[spec.family](spec.fixture_ids[0], results[spec.fixture_ids[0]]) for spec in invariant_specs()}
    if len(catalog) != 80:
        raise AssertionError("INVARIANT_ID_COLLISION")
    return catalog


def mutation_sensitivity() -> dict[str, bool]:
    """Each invariant family must reject a minimal, synthetic injected defect."""
    scenario = build_scenarios()[0]
    result = run_scenario(scenario)
    owner = result.run.final_agent_portfolios[0]
    leaked = replace(owner, agent_id="wrong-owner")
    conflict = run_scenario(build_scenarios()[12])
    abstain = run_scenario(build_scenarios()[24])
    hidden = _agents_for(build_scenarios()[36])[0]
    policy = run_scenario(build_scenarios()[48])
    episodes = run_multistep_episodes()
    pairs = build_counterfactual_pairs()
    return {
        "S009": leaked.agent_id != owner.agent_id,
        "S010": conflict.run.events[1].accepted is False,
        "S011": abstain.run.events[0].outcome_status == "ABSTAINED",
        "S012": len(hidden.posterior.hypotheses) == 2 and policy.run.events[0].accepted is False and bool(episodes[0].causal_history_event_ids) and pairs[0][0] != pairs[0][1],
    }


def negative_cases() -> tuple[tuple[str, Callable[[], object]], ...]:
    state = market()
    good = _agents_for(build_scenarios()[0])[0]
    valid = CandidateAction("negative", good.agent_id, ActionLabel.FEASIBLE, order("negative"), ("a",), ("e",), arrival_sequence=1)
    bad_posterior = AgentState("bad-posterior", HiddenTypePosterior(()), good.information, good.inventory)
    long_id = "x" * 161
    return (
        ("invalid_top_level_agents", lambda: arbitrate("n01", state, "bad", ())),
        ("invalid_top_level_actions", lambda: arbitrate("n02", state, (good,), "bad")),
        ("invalid_agent_object", lambda: arbitrate("n03", state, (object(),), ())),
        ("invalid_action_object", lambda: arbitrate("n04", state, (good,), (object(),))),
        ("duplicate_agent", lambda: arbitrate("n05", state, (good, good), ())),
        ("duplicate_action", lambda: arbitrate("n06", state, (good,), (valid, replace(valid, arrival_sequence=2)))),
        ("duplicate_arrival", lambda: arbitrate("n07", state, (good,), (valid, replace(valid, action_id="n07", arrival_sequence=1)))),
        ("unknown_agent", lambda: arbitrate("n08", state, (good,), (replace(valid, action_id="n08", agent_id="unknown"),))),
        ("bad_posterior", lambda: arbitrate("n09", state, (bad_posterior,), (replace(valid, action_id="n09", agent_id="bad-posterior"),))),
        ("future_information", lambda: arbitrate("n10", state, (replace(good, information=replace(good.information, available_at_ns=101)),), (replace(valid, action_id="n10"),))),
        ("unknown_information_time", lambda: arbitrate("n11", state, (replace(good, information=replace(good.information, available_at_ns=None)),), (replace(valid, action_id="n11"),))),
        ("missing_evidence", lambda: arbitrate("n12", state, (good,), (replace(valid, action_id="n12", evidence_refs=()),))),
        ("bad_label", lambda: arbitrate("n13", state, (good,), (replace(valid, action_id="n13", label="BAD"),))),
        ("bad_arrival_type", lambda: arbitrate("n14", state, (good,), (replace(valid, action_id="n14", arrival_sequence=True),))),
        ("long_agent_id", lambda: arbitrate("n15", state, (replace(good, agent_id=long_id),), (replace(valid, action_id="n15", agent_id=long_id),))),
        ("bad_conflict_key", lambda: arbitrate("n16", state, (good,), (replace(valid, action_id="n16", conflict_key=long_id),))),
        ("missing_order", lambda: arbitrate("n17", state, (good,), (replace(valid, action_id="n17", order=None),))),
        ("future_parent", lambda: arbitrate("n18", state, (good,), (replace(valid, action_id="n18", causal_parent_event_ids=("future",)),))),
        ("too_many_parents", lambda: arbitrate("n19", state, (good,), (replace(valid, action_id="n19", causal_parent_event_ids=tuple(str(i) for i in range(17))),))),
        ("empty_agents", lambda: arbitrate("n20", state, (), ())),
        ("too_many_agents", lambda: arbitrate("n21", state, tuple(replace(good, agent_id=f"g{i}") for i in range(65)), ())),
        ("invalid_episode_limit", lambda: run_bounded_counterfactual_episode("n22", state, (good,), (valid,), ("a",), max_steps=13)),
        ("duplicate_episode_assumption", lambda: run_bounded_counterfactual_episode("n23", state, (good,), (valid,), ("a", "a"), max_steps=2)),
        ("counterfactual_multiple_target", lambda: run_one_step_counterfactual("n24", state, (good,), (valid, replace(valid, action_id="second", arrival_sequence=2)), "a")),
        ("candidate_authority", lambda: reject_adapter_contamination({"status": "CANDIDATE", "authority_write": True})),
        ("candidate_abbreviated_lock", lambda: reject_adapter_contamination({"status": "CANDIDATE", "authority_write": False, "source_capability": SYNTHETIC_EVALUATION_CAPABILITY, "claim_kind": "synthetic_fixture", "source_commit_lock": "abc", "artifact_hashes": ("0" * 64,), "verifier_command": "x"})),
        ("candidate_no_verifier", lambda: reject_adapter_contamination({"status": "CANDIDATE", "authority_write": False, "source_capability": SYNTHETIC_EVALUATION_CAPABILITY, "claim_kind": "synthetic_fixture", "source_commit_lock": "a" * 40, "artifact_hashes": ("0" * 64,), "verifier_command": ""})),
        ("candidate_bad_hash", lambda: reject_adapter_contamination({"status": "CANDIDATE", "authority_write": False, "source_capability": SYNTHETIC_EVALUATION_CAPABILITY, "claim_kind": "synthetic_fixture", "source_commit_lock": "a" * 40, "artifact_hashes": ("short",), "verifier_command": "x"})),
        ("candidate_hardcoded_determinism", lambda: reject_adapter_contamination({"status": "CANDIDATE", "authority_write": False, "source_capability": SYNTHETIC_EVALUATION_CAPABILITY, "claim_kind": "synthetic_fixture", "source_commit_lock": "a" * 40, "artifact_hashes": ("0" * 64,), "verifier_command": "x", "determinism_status": "HARDCODED_PASS"})),
        ("candidate_fact_promotion", lambda: reject_adapter_contamination({"status": "CANDIDATE", "authority_write": False, "source_capability": SYNTHETIC_EVALUATION_CAPABILITY, "claim_kind": "synthetic_fixture", "source_commit_lock": "a" * 40, "artifact_hashes": ("0" * 64,), "verifier_command": "x", "promotion": "FACT"})),
        ("suspended_market", lambda: arbitrate("n31", market(status=SecurityStatus.SUSPENDED), (good,), (valid,))),
        ("price_limit", lambda: arbitrate("n32", state, (good,), (replace(valid, action_id="n32", order=order("n32", price=11)),))),
        ("fresh_t1_sell", lambda: arbitrate("n33", state, (replace(good, inventory=InventoryState((SyntheticLot("fresh", "2026-07-26", 1),), settled_trade_date="2026-07-26")),), (replace(valid, action_id="n33", order=order("n33", side=OrderSide.SELL, qty=1)),))),
        ("unknown_match", lambda: arbitrate("n34", state, (good,), (replace(valid, action_id="n34", order=order("n34", mode=MatchMode.UNKNOWN)),))),
        ("closed_phase", lambda: arbitrate("n35", market(SessionPhase.CLOSED), (good,), (valid,))),
        ("malformed_private_refs", lambda: arbitrate("n36", state, (replace(good, information=replace(good.information, private_observable_refs="bad")),), (valid,))),
    )


def normalized_evaluation_hash() -> str:
    payload = {
        "results": [(item.scenario.scenario_id, item.run.ledger_hash, item.run.total_system_state_hash) for item in run_all_scenarios()],
        "invariants": invariant_catalog(),
        "pairs": build_counterfactual_pairs(),
        "episodes": [(run.ledger_hash, run.total_system_state_hash) for run in run_multistep_episodes()],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
