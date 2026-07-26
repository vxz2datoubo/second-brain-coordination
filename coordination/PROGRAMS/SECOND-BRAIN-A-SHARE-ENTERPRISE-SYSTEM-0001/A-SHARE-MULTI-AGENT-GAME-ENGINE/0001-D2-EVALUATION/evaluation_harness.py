"""Deterministic, synthetic-only evaluation loop for the D2 game core."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


_ENGINE_ROOT = Path(__file__).resolve().parents[1]
_D2_ROOT = _ENGINE_ROOT / "0001-D2"
if str(_D2_ROOT) not in sys.path:
    sys.path.insert(0, str(_D2_ROOT))

from d2_game_core import (  # noqa: E402
    ActionLabel, AgentInformationSet, AgentState, CandidateAction, HiddenTypePosterior,
    ParticipantArchetypeHypothesis, ParticipantSubtype, arbitrate,
    inventory_ledger_conserved, run_bounded_counterfactual_episode,
    run_one_step_counterfactual,
)
from synthetic_engine.fixtures import INVENTORY, market, order  # noqa: E402
from synthetic_engine.types import InventoryState, MatchMode, OrderSide, SecurityStatus, SessionPhase, SyntheticLot  # noqa: E402


SYNTHETIC_EVALUATION_CAPABILITY = "SYNTHETIC_RESEARCH_ONLY"


@dataclass(frozen=True)
class EvaluationScenario:
    scenario_id: str
    category: str
    phase: SessionPhase
    action_label: ActionLabel
    match_mode: MatchMode
    side: OrderSide
    agent_information_ns: int | None
    market_information_ns: int
    evidence_present: bool
    conflict: bool
    hidden_ambiguity: bool
    requires_complete_information: bool
    unknowns: tuple[str, ...]
    security_status: SecurityStatus = SecurityStatus.ACTIVE


@dataclass(frozen=True)
class EvaluationResult:
    scenario_id: str
    ledger_hash: str
    event_count: int
    accepted_count: int
    blocked_or_abstained_count: int


def _posterior(ambiguous: bool) -> HiddenTypePosterior:
    if ambiguous:
        return HiddenTypePosterior((
            ParticipantArchetypeHypothesis(ParticipantSubtype.RETAIL_LIQUIDITY_TAKER, 0.5, ("synthetic:e1",), ("synthetic:c1",), "synthetic alt 1"),
            ParticipantArchetypeHypothesis(ParticipantSubtype.SYSTEMATIC_REBALANCER, 0.5, ("synthetic:e2",), ("synthetic:c2",), "synthetic alt 2"),
        ))
    return HiddenTypePosterior((ParticipantArchetypeHypothesis(
        ParticipantSubtype.RETAIL_LIQUIDITY_TAKER, 1.0, ("synthetic:e",), ("synthetic:c",), "synthetic alternative",
    ),))


def build_scenarios() -> tuple[EvaluationScenario, ...]:
    phases = (
        SessionPhase.PREOPEN, SessionPhase.CALL_AUCTION, SessionPhase.AUCTION_FREEZE,
        SessionPhase.CONTINUOUS_AM, SessionPhase.MIDDAY_BREAK, SessionPhase.CONTINUOUS_PM,
        SessionPhase.CLOSING_AUCTION, SessionPhase.CLOSED, SessionPhase.SUSPENDED,
    )
    labels = (ActionLabel.FEASIBLE, ActionLabel.BEST_RESPONSE_CANDIDATE, ActionLabel.MOST_CONSISTENT, ActionLabel.ROBUST)
    modes = (MatchMode.FULL, MatchMode.PARTIAL, MatchMode.NO_FILL_CANCEL, MatchMode.NO_FILL_CARRY)
    result = []
    for index in range(48):
        phase = phases[index % len(phases)]
        category = ("session", "inventory", "information", "narrative", "policy_shock", "conflict")[index % 6]
        label = labels[index % len(labels)]
        if index in (15, 31):
            label = ActionLabel.ABSTAIN
        result.append(EvaluationScenario(
            scenario_id=f"E{index + 1:02d}",
            category=category,
            phase=phase,
            action_label=label,
            match_mode=modes[index % len(modes)],
            side=OrderSide.SELL if index % 5 == 0 else OrderSide.BUY,
            agent_information_ns=None if index == 40 else (101 if index in (14, 35) else 100),
            market_information_ns=100,
            evidence_present=index not in (16, 37),
            conflict=index in (5, 23, 41),
            hidden_ambiguity=index % 7 == 0,
            requires_complete_information=index in (18, 39),
            unknowns=("synthetic:missing",) if index in (18, 39) else (),
            security_status=SecurityStatus.SUSPENDED if phase is SessionPhase.SUSPENDED else SecurityStatus.ACTIVE,
        ))
    return tuple(result)


def _inventory_for(scenario: EvaluationScenario) -> InventoryState:
    if scenario.side is OrderSide.SELL:
        return INVENTORY
    return INVENTORY


def run_scenario(scenario: EvaluationScenario) -> EvaluationResult:
    if scenario.agent_information_ns is None:
        information = AgentInformationSet(None, ("synthetic:public",), scenario.unknowns)
    else:
        information = AgentInformationSet(scenario.agent_information_ns, ("synthetic:public",), scenario.unknowns, ("synthetic:private",))
    inventory = _inventory_for(scenario)
    agent = AgentState("agent-eval", _posterior(scenario.hidden_ambiguity), information, inventory)
    state = market(scenario.phase, scenario.security_status)
    first_order = order(
        f"{scenario.scenario_id}:a",
        side=scenario.side,
        mode=scenario.match_mode,
        partial=1 if scenario.match_mode is MatchMode.PARTIAL else None,
        available=scenario.market_information_ns,
    )
    evidence = ("synthetic:evidence",) if scenario.evidence_present else ()
    first = CandidateAction(
        f"{scenario.scenario_id}:a", "agent-eval", scenario.action_label, first_order,
        (f"assumption:{scenario.scenario_id}",), evidence,
        conflict_key=f"conflict:{scenario.scenario_id}" if scenario.conflict else None,
        requires_complete_information=scenario.requires_complete_information,
    )
    actions = (first,)
    if scenario.conflict:
        actions += (CandidateAction(
            f"{scenario.scenario_id}:b", "agent-eval", ActionLabel.FEASIBLE,
            order(f"{scenario.scenario_id}:b", available=scenario.market_information_ns),
            (f"assumption:{scenario.scenario_id}:second",), ("synthetic:evidence",),
            conflict_key=f"conflict:{scenario.scenario_id}",
        ),)
    result = arbitrate("evaluation:" + scenario.scenario_id, state, (agent,), actions)
    accepted = sum(1 for event in result.events if event.accepted)
    return EvaluationResult(scenario.scenario_id, result.ledger_hash, len(result.events), accepted, len(result.events) - accepted)


def run_all_scenarios() -> tuple[EvaluationResult, ...]:
    return tuple(run_scenario(scenario) for scenario in build_scenarios())


def build_counterfactual_pairs() -> tuple[tuple[str, str], ...]:
    pairs = []
    for index in range(24):
        agent = AgentState("agent-cf", _posterior(False), AgentInformationSet(100, ("synthetic:public",), ()), INVENTORY)
        action = CandidateAction(
            f"cf-{index}", "agent-cf", ActionLabel.FEASIBLE, order(f"cf-{index}"),
            (f"assumption:cf:{index}",), ("synthetic:evidence",),
        )
        result = run_one_step_counterfactual(f"pair-{index}", market(), (agent,), (action,), f"assumption:cf:{index}")
        pairs.append((result.baseline.ledger_hash, result.alternative.ledger_hash))
    return tuple(pairs)


def run_multistep_episodes() -> tuple[str, ...]:
    hashes = []
    for index in range(12):
        agent = AgentState("agent-ms", _posterior(index % 2 == 0), AgentInformationSet(100, ("synthetic:public",), ()), INVENTORY)
        actions = (
            CandidateAction(f"ms-{index}:a", "agent-ms", ActionLabel.FEASIBLE, order(f"ms-{index}:a"), (f"a:{index}",), ("synthetic:e",)),
            CandidateAction(f"ms-{index}:b", "agent-ms", ActionLabel.FEASIBLE, order(f"ms-{index}:b"), (f"b:{index}",), ("synthetic:e",)),
        )
        episode = run_bounded_counterfactual_episode(f"episode-{index}", market(), (agent,), actions, (f"a:{index}", f"b:{index}"), max_steps=2)
        hashes.append(episode.runs[-1].ledger_hash)
    return tuple(hashes)


def reject_adapter_contamination(envelope: Mapping[str, object]) -> bool:
    """A tiny fail-closed synthetic boundary used only for failure injection."""
    return (
        envelope.get("status") == "CANDIDATE"
        and envelope.get("authority_write") is False
        and envelope.get("source_capability") == SYNTHETIC_EVALUATION_CAPABILITY
        and envelope.get("claim_kind") in {"synthetic_fixture", "compatibility_probe"}
    )


def invariant_catalog() -> dict[str, bool]:
    scenarios = build_scenarios()
    results = run_all_scenarios()
    checks = {
        f"scenario_{result.scenario_id}_stable_ledger": bool(result.ledger_hash) and result.event_count >= 1
        for result in results
    }
    agent = AgentState("agent-invariant", _posterior(False), AgentInformationSet(100, ("synthetic:public",), ()), INVENTORY)
    candidate = CandidateAction("invariant", "agent-invariant", ActionLabel.FEASIBLE, order("invariant"), ("a",), ("e",))
    run = arbitrate("invariant", market(), (agent,), (candidate,))
    checks.update({
        "scenario_count_48": len(scenarios) == 48,
        "result_count_48": len(results) == 48,
        "ordered_scenario_ids": tuple(item.scenario_id for item in scenarios) == tuple(f"E{i:02d}" for i in range(1, 49)),
        "ledger_repeatability": run.ledger_hash == arbitrate("invariant", market(), (agent,), (candidate,)).ledger_hash,
        "inventory_accounting": inventory_ledger_conserved(INVENTORY, run, (candidate,)),
        "counterfactual_pair_count_24": len(build_counterfactual_pairs()) == 24,
        "counterfactual_pairs_differ": all(left != right for left, right in build_counterfactual_pairs()),
        "multi_step_count_12": len(run_multistep_episodes()) == 12,
        "multi_step_hashes_present": all(run_multistep_episodes()),
        "adapter_candidate_allowed": reject_adapter_contamination({"status": "CANDIDATE", "authority_write": False, "source_capability": SYNTHETIC_EVALUATION_CAPABILITY, "claim_kind": "synthetic_fixture"}),
        "adapter_authority_rejected": not reject_adapter_contamination({"status": "CANDIDATE", "authority_write": True, "source_capability": SYNTHETIC_EVALUATION_CAPABILITY, "claim_kind": "synthetic_fixture"}),
        "all_results_bounded": all(result.event_count <= 2 for result in results),
    })
    if len(checks) != 60:
        raise AssertionError(f"expected 60 invariants, got {len(checks)}")
    return checks


def negative_cases() -> tuple[tuple[str, Callable[[], object]], ...]:
    state = market()
    good_agent = AgentState("negative-agent", _posterior(False), AgentInformationSet(100, ("synthetic:public",), ()), INVENTORY)
    bad_action = CandidateAction("bad", "negative-agent", ActionLabel.FEASIBLE, order("bad"), ("a",), ())
    return (
        ("unknown_agent", lambda: arbitrate("n01", state, (good_agent,), (CandidateAction("n01", "missing", ActionLabel.FEASIBLE, order("n01"), ("a",), ("e",)),))),
        ("missing_order", lambda: arbitrate("n02", state, (good_agent,), (CandidateAction("n02", "negative-agent", ActionLabel.FEASIBLE, None, ("a",), ("e",)),))),
        ("missing_evidence", lambda: arbitrate("n03", state, (good_agent,), (bad_action,))),
        ("future_information", lambda: arbitrate("n04", state, (AgentState("negative-agent", _posterior(False), AgentInformationSet(101, ("p",), ()), INVENTORY),), (CandidateAction("n04", "negative-agent", ActionLabel.FEASIBLE, order("n04"), ("a",), ("e",)),))),
        ("invalid_information_time", lambda: arbitrate("n05", state, (AgentState("negative-agent", _posterior(False), AgentInformationSet(None, ("p",), ()), INVENTORY),), (CandidateAction("n05", "negative-agent", ActionLabel.FEASIBLE, order("n05"), ("a",), ("e",)),))),
        ("empty_posterior", lambda: arbitrate("n06", state, (AgentState("negative-agent", HiddenTypePosterior(()), AgentInformationSet(100, ("p",), ()), INVENTORY),), (CandidateAction("n06", "negative-agent", ActionLabel.FEASIBLE, order("n06"), ("a",), ("e",)),))),
        ("unnormalized_posterior", lambda: arbitrate("n07", state, (AgentState("negative-agent", HiddenTypePosterior((ParticipantArchetypeHypothesis(ParticipantSubtype.RETAIL_LIQUIDITY_TAKER, .9, ("e",), ("c",), "alt"),)), AgentInformationSet(100, ("p",), ()), INVENTORY),), (CandidateAction("n07", "negative-agent", ActionLabel.FEASIBLE, order("n07"), ("a",), ("e",)),))),
        ("duplicate_action", lambda: arbitrate("n08", state, (good_agent,), (CandidateAction("dup", "negative-agent", ActionLabel.FEASIBLE, order("dup"), ("a",), ("e",)), CandidateAction("dup", "negative-agent", ActionLabel.FEASIBLE, order("dup2"), ("b",), ("e",))))),
        ("duplicate_agent", lambda: arbitrate("n09", state, (good_agent, good_agent), (CandidateAction("n09", "negative-agent", ActionLabel.FEASIBLE, order("n09"), ("a",), ("e",)),))),
        ("forward_causal_parent", lambda: arbitrate("n10", state, (good_agent,), (CandidateAction("n10", "negative-agent", ActionLabel.FEASIBLE, order("n10"), ("a",), ("e",), causal_parent_event_ids=("future",)),))),
        ("causal_cycle_proxy", lambda: arbitrate("n11", state, (good_agent,), (CandidateAction("n11", "negative-agent", ActionLabel.FEASIBLE, order("n11"), ("a",), ("e",), causal_parent_event_ids=("n11",)),))),
        ("adapter_authority", lambda: reject_adapter_contamination({"status": "CANDIDATE", "authority_write": True, "source_capability": SYNTHETIC_EVALUATION_CAPABILITY, "claim_kind": "synthetic_fixture"})),
        ("adapter_unknown_capability", lambda: reject_adapter_contamination({"status": "CANDIDATE", "authority_write": False, "source_capability": "UNKNOWN", "claim_kind": "synthetic_fixture"})),
        ("adapter_fact_promotion", lambda: reject_adapter_contamination({"status": "CANDIDATE", "authority_write": False, "source_capability": SYNTHETIC_EVALUATION_CAPABILITY, "claim_kind": "fact"})),
        ("empty_agents", lambda: arbitrate("n15", state, (), (CandidateAction("n15", "negative-agent", ActionLabel.FEASIBLE, order("n15"), ("a",), ("e",)),))),
        ("invalid_max_steps", lambda: run_bounded_counterfactual_episode("n16", state, (good_agent,), (CandidateAction("n16", "negative-agent", ActionLabel.FEASIBLE, order("n16"), ("a",), ("e",)),), ("a",), max_steps=13)),
        ("duplicate_assumptions", lambda: run_bounded_counterfactual_episode("n17", state, (good_agent,), (CandidateAction("n17", "negative-agent", ActionLabel.FEASIBLE, order("n17"), ("a",), ("e",)),), ("a", "a"), max_steps=2)),
        ("multi_target_counterfactual", lambda: run_one_step_counterfactual("n18", state, (good_agent,), (CandidateAction("n18a", "negative-agent", ActionLabel.FEASIBLE, order("n18a"), ("a",), ("e",)), CandidateAction("n18b", "negative-agent", ActionLabel.FEASIBLE, order("n18b"), ("a",), ("e",))), "a")),
        ("suspended_state", lambda: arbitrate("n19", market(status=SecurityStatus.SUSPENDED), (good_agent,), (CandidateAction("n19", "negative-agent", ActionLabel.FEASIBLE, order("n19"), ("a",), ("e",)),))),
        ("price_limit", lambda: arbitrate("n20", state, (good_agent,), (CandidateAction("n20", "negative-agent", ActionLabel.FEASIBLE, order("n20", price=11), ("a",), ("e",)),))),
        ("fresh_t1_sell", lambda: arbitrate("n21", state, (AgentState("negative-agent", _posterior(False), AgentInformationSet(100, ("p",), ()), InventoryState((SyntheticLot("fresh", "2026-07-26", 1),), settled_trade_date="2026-07-26")),), (CandidateAction("n21", "negative-agent", ActionLabel.FEASIBLE, order("n21", side=OrderSide.SELL, qty=1), ("a",), ("e",)),))),
        ("unknown_match_mode", lambda: arbitrate("n22", state, (good_agent,), (CandidateAction("n22", "negative-agent", ActionLabel.FEASIBLE, order("n22", mode=MatchMode.UNKNOWN), ("a",), ("e",)),))),
        ("closed_phase", lambda: arbitrate("n23", market(SessionPhase.CLOSED), (good_agent,), (CandidateAction("n23", "negative-agent", ActionLabel.FEASIBLE, order("n23"), ("a",), ("e",)),))),
        ("malformed_private_collection", lambda: arbitrate("n24", state, (AgentState("negative-agent", _posterior(False), AgentInformationSet(100, ("p",), (), "not-a-tuple"), INVENTORY),), (CandidateAction("n24", "negative-agent", ActionLabel.FEASIBLE, order("n24"), ("a",), ("e",)),))),
    )


def normalized_evaluation_hash() -> str:
    payload = {
        "results": [item.__dict__ for item in run_all_scenarios()],
        "invariants": invariant_catalog(),
        "counterfactual_pairs": build_counterfactual_pairs(),
        "multi_step": run_multistep_episodes(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
