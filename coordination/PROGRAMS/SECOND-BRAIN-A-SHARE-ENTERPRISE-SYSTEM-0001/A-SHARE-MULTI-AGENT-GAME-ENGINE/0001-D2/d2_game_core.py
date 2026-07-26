"""Deterministic, synthetic-only D2 stateful multi-agent game core.

This module deliberately models hypotheses rather than real market identities.
Each agent owns an independent inventory.  The only shared mutable surface is
the explicit synthetic conflict-resource registry; it is never inferred from
prices, order flow, or a real person.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple


_D1_ROOT = Path(__file__).resolve().parents[1] / "0001-D1"
if str(_D1_ROOT) not in sys.path:
    sys.path.insert(0, str(_D1_ROOT))

from synthetic_engine.engine import reduce_order
from synthetic_engine.types import (  # noqa: E402
    InventoryState,
    MarketState,
    OutcomeStatus,
    SyntheticMatchOutcome,
    SyntheticOrder,
)


SYNTHETIC_CAPABILITY = "SYNTHETIC_RESEARCH_ONLY"
MAX_AGENT_COUNT = 64
MAX_ACTION_COUNT = 256
MAX_EVENT_COUNT = 256
MAX_REFERENCE_COUNT = 32
MAX_CAUSAL_PARENT_COUNT = 16
MAX_IDENTIFIER_LENGTH = 160
MAX_FEATURE_MAGNITUDE = 1_000_000


class ParticipantFamily(str, Enum):
    RETAIL = "retail"
    INSTITUTIONAL_QUANT = "institutional_quant"
    ACTIVE_CAPITAL = "active_capital"
    POLICY_INDUSTRIAL_FOREIGN_AGGREGATE = "policy_industrial_foreign_aggregate"


class ParticipantSubtype(str, Enum):
    RETAIL_LIQUIDITY_TAKER = "retail_liquidity_taker"
    RETAIL_ANCHORED_HOLDER = "retail_anchored_holder"
    SYSTEMATIC_REBALANCER = "systematic_rebalancer"
    LONG_HORIZON_FUND = "long_horizon_fund"
    EVENT_DRIVEN_ACTIVE = "event_driven_active"
    SHORT_HORIZON_MOMENTUM = "short_horizon_momentum"
    POLICY_AGGREGATE = "policy_aggregate"
    INDUSTRIAL_AGGREGATE = "industrial_aggregate"
    FOREIGN_AGGREGATE = "foreign_aggregate"


SUBTYPE_FAMILY = {
    ParticipantSubtype.RETAIL_LIQUIDITY_TAKER: ParticipantFamily.RETAIL,
    ParticipantSubtype.RETAIL_ANCHORED_HOLDER: ParticipantFamily.RETAIL,
    ParticipantSubtype.SYSTEMATIC_REBALANCER: ParticipantFamily.INSTITUTIONAL_QUANT,
    ParticipantSubtype.LONG_HORIZON_FUND: ParticipantFamily.INSTITUTIONAL_QUANT,
    ParticipantSubtype.EVENT_DRIVEN_ACTIVE: ParticipantFamily.ACTIVE_CAPITAL,
    ParticipantSubtype.SHORT_HORIZON_MOMENTUM: ParticipantFamily.ACTIVE_CAPITAL,
    ParticipantSubtype.POLICY_AGGREGATE: ParticipantFamily.POLICY_INDUSTRIAL_FOREIGN_AGGREGATE,
    ParticipantSubtype.INDUSTRIAL_AGGREGATE: ParticipantFamily.POLICY_INDUSTRIAL_FOREIGN_AGGREGATE,
    ParticipantSubtype.FOREIGN_AGGREGATE: ParticipantFamily.POLICY_INDUSTRIAL_FOREIGN_AGGREGATE,
}


class ActionLabel(str, Enum):
    FEASIBLE = "feasible"
    BLOCKED = "blocked"
    ABSTAIN = "abstain"
    BEST_RESPONSE_CANDIDATE = "best_response_candidate"
    MOST_CONSISTENT = "most_consistent"
    ROBUST = "robust"


class NarrativeStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    CANDIDATE = "CANDIDATE"
    EXPIRED = "EXPIRED"
    REFUTED = "REFUTED"


@dataclass(frozen=True)
class ParticipantArchetypeHypothesis:
    subtype: ParticipantSubtype
    normalized_weight: float
    evidence_refs: Tuple[str, ...]
    counterevidence_refs: Tuple[str, ...]
    alternative_explanation: str

    @property
    def family(self) -> ParticipantFamily:
        return SUBTYPE_FAMILY[self.subtype]


@dataclass(frozen=True)
class HiddenTypePosterior:
    hypotheses: Tuple[ParticipantArchetypeHypothesis, ...]
    status: str = "UNCALIBRATED_SYNTHETIC_HYPOTHESIS"

    def validate(self) -> Tuple[bool, Tuple[str, ...]]:
        if not _typed_tuple(self.hypotheses, ParticipantArchetypeHypothesis, MAX_REFERENCE_COUNT):
            return False, ("INVALID_HIDDEN_TYPE_HYPOTHESES",)
        weights = [item.normalized_weight for item in self.hypotheses]
        if any(not _finite_number(value) for value in weights):
            return False, ("INVALID_POSTERIOR_WEIGHT_TYPE",)
        if any(value < 0 or value > 1 for value in weights):
            return False, ("POSTERIOR_WEIGHT_OUT_OF_RANGE",)
        if abs(sum(weights) - 1.0) > 1e-9:
            return False, ("POSTERIOR_NOT_NORMALIZED",)
        for item in self.hypotheses:
            if not isinstance(item.subtype, ParticipantSubtype):
                return False, ("UNKNOWN_PARTICIPANT_SUBTYPE",)
            if not _valid_refs(item.evidence_refs) or not _valid_refs(item.counterevidence_refs):
                return False, ("INVALID_POSTERIOR_REFERENCE",)
            if not _bounded_text(item.alternative_explanation, allow_empty=False):
                return False, ("INVALID_ALTERNATIVE_EXPLANATION",)
        return True, ("UNCALIBRATED_NORMALIZED_WEIGHTS_ONLY",)


@dataclass(frozen=True)
class AgentInformationSet:
    available_at_ns: Optional[int]
    observable_refs: Tuple[str, ...]
    unknowns: Tuple[str, ...]
    private_observable_refs: Tuple[str, ...] = ()
    source_capability: str = SYNTHETIC_CAPABILITY

    @property
    def public_observable_refs(self) -> Tuple[str, ...]:
        return self.observable_refs


@dataclass(frozen=True)
class AgentState:
    agent_id: str
    posterior: HiddenTypePosterior
    information: AgentInformationSet
    inventory: InventoryState


@dataclass(frozen=True)
class CandidateAction:
    action_id: str
    agent_id: str
    label: ActionLabel
    order: Optional[SyntheticOrder]
    assumption_ids: Tuple[str, ...]
    evidence_refs: Tuple[str, ...]
    conflict_key: Optional[str] = None
    requires_complete_information: bool = False
    causal_parent_event_ids: Tuple[str, ...] = ()
    arrival_sequence: int = 0


@dataclass(frozen=True)
class AgentPortfolioState:
    """Per-agent state; no other agent can mutate this inventory implicitly."""

    agent_id: str
    initial_inventory: InventoryState
    final_inventory: InventoryState
    pre_state_hash: str
    post_state_hash: str
    net_filled_quantity: int


@dataclass(frozen=True)
class SharedMarketState:
    market: MarketState
    claimed_conflict_keys: Tuple[str, ...]
    conflict_claim_event_ids: Tuple[Tuple[str, str], ...]
    state_hash: str
    contract: str = "EXPLICIT_SYNTHETIC_CONFLICT_RESOURCE_ONLY"


@dataclass(frozen=True)
class LedgerEvent:
    event_id: str
    ordinal: int
    agent_id: str
    action_id: str
    label: ActionLabel
    accepted: bool
    outcome_status: str
    filled_quantity: int
    rejected_reason_codes: Tuple[str, ...]
    cause_refs: Tuple[str, ...]
    causal_parent_event_ids: Tuple[str, ...]
    owner_pre_state_hash: str
    owner_post_state_hash: str
    system_pre_state_hash: str
    system_post_state_hash: str


@dataclass(frozen=True)
class ParticipantAlignmentScore:
    feature_names: Tuple[str, ...]
    uncalibrated_value: float
    status: str = "UNCALIBRATED_SYNTHETIC_FEATURE"
    prohibited_use: str = "NOT_A_REAL_PARTICIPANT_IDENTITY_OR_PROBABILITY"


@dataclass(frozen=True)
class ParticipantMismatchRisk:
    feature_names: Tuple[str, ...]
    uncalibrated_value: float
    status: str = "UNCALIBRATED_SYNTHETIC_FEATURE"
    prohibited_use: str = "NOT_A_REAL_PARTICIPANT_IDENTITY_OR_PROBABILITY"


@dataclass(frozen=True)
class NarrativeForecastRecord:
    claim_id: str
    claim: str
    evidence_refs: Tuple[str, ...]
    counterevidence_refs: Tuple[str, ...]
    expires_at_ns: Optional[int]
    status: NarrativeStatus = NarrativeStatus.UNKNOWN


@dataclass(frozen=True)
class GameRun:
    run_id: str
    events: Tuple[LedgerEvent, ...]
    final_agent_portfolios: Tuple[AgentPortfolioState, ...]
    shared_market_state: SharedMarketState
    ledger_hash: str
    total_system_state_hash: str
    causal_history_event_ids: Tuple[str, ...] = ()
    executed_action_ids: Tuple[str, ...] = ()
    executed_order_ids: Tuple[str, ...] = ()
    action_records: Tuple[CandidateAction, ...] = ()

    @property
    def final_inventory(self) -> Optional[InventoryState]:
        """Legacy projection, intentionally unavailable once there are multiple agents."""
        return self.final_agent_portfolios[0].final_inventory if len(self.final_agent_portfolios) == 1 else None


@dataclass(frozen=True)
class CounterfactualResult:
    changed_assumption_id: str
    baseline: GameRun
    alternative: GameRun
    changed_action_ids: Tuple[str, ...]


@dataclass(frozen=True)
class BoundedCounterfactualEpisode:
    changed_assumption_ids: Tuple[str, ...]
    runs: Tuple[GameRun, ...]
    max_steps: int
    final_state_hash: str


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and abs(value) <= MAX_FEATURE_MAGNITUDE


def _bounded_text(value: object, *, allow_empty: bool = False) -> bool:
    return isinstance(value, str) and len(value) <= MAX_IDENTIFIER_LENGTH and (allow_empty or bool(value))


def _typed_tuple(value: object, expected_type: type, limit: int) -> bool:
    return isinstance(value, tuple) and bool(value) and len(value) <= limit and all(isinstance(item, expected_type) for item in value)


def _valid_refs(value: object, *, allow_empty: bool = False, limit: int = MAX_REFERENCE_COUNT) -> bool:
    return isinstance(value, tuple) and len(value) <= limit and (allow_empty or bool(value)) and all(_bounded_text(item) for item in value)


def _primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _primitive(asdict(value))
    if isinstance(value, dict):
        return {str(key): _primitive(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_primitive(item) for item in value]
    return value


def _canonical(value: object) -> bytes:
    return json.dumps(_primitive(value), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _inventory_quantity(inventory: InventoryState) -> int:
    return sum(lot.quantity for lot in inventory.lots if isinstance(lot.quantity, int) and not isinstance(lot.quantity, bool))


def _portfolio_hash(agent_id: str, inventory: InventoryState) -> str:
    return _sha({"agent_id": agent_id, "inventory": inventory})


def _system_hash(portfolios: dict[str, AgentPortfolioState], market: MarketState, claimed: dict[str, str], prior_event_ids: Sequence[str]) -> str:
    return _sha({
        "portfolios": {agent_id: portfolios[agent_id].final_inventory for agent_id in sorted(portfolios)},
        "market": market,
        "claimed_conflicts": sorted(claimed.items()),
        "causal_history": tuple(prior_event_ids),
    })


def _event_id(run_id: str, ordinal: int, action: CandidateAction, status: str, reasons: Sequence[str], pre_hash: str, post_hash: str) -> str:
    return _sha({"run_id": run_id, "ordinal": ordinal, "action": action.action_id, "agent": action.agent_id,
                 "status": status, "reasons": tuple(reasons), "pre": pre_hash, "post": post_hash})


def _validate_agent(agent: object, market: MarketState) -> Tuple[bool, Tuple[str, ...]]:
    if not isinstance(agent, AgentState):
        return False, ("INVALID_AGENT_OBJECT",)
    if not _bounded_text(agent.agent_id):
        return False, ("INVALID_AGENT_ID",)
    if not isinstance(agent.posterior, HiddenTypePosterior) or not isinstance(agent.information, AgentInformationSet):
        return False, ("INVALID_AGENT_COMPONENT",)
    if not isinstance(agent.inventory, InventoryState):
        return False, ("INVALID_AGENT_INVENTORY",)
    valid_posterior, posterior_reasons = agent.posterior.validate()
    if not valid_posterior:
        return False, posterior_reasons
    info = agent.information
    if info.source_capability != SYNTHETIC_CAPABILITY:
        return False, ("UNSUPPORTED_AGENT_CAPABILITY",)
    if not _valid_refs(info.observable_refs, allow_empty=True) or not _valid_refs(info.private_observable_refs, allow_empty=True):
        return False, ("INVALID_AGENT_INFORMATION_REFERENCE",)
    if not _valid_refs(info.unknowns, allow_empty=True):
        return False, ("INVALID_AGENT_UNKNOWN_COLLECTION",)
    if not isinstance(info.available_at_ns, int) or isinstance(info.available_at_ns, bool) or info.available_at_ns < 0:
        return False, ("UNKNOWN_OR_INVALID_AGENT_INFORMATION_TIME",)
    if not isinstance(market, MarketState) or market.information is None or market.information.available_at_ns is None:
        return False, ("UNKNOWN_MARKET_INFORMATION_TIME",)
    if info.available_at_ns > market.information.available_at_ns:
        return False, ("AGENT_FUTURE_INFORMATION",)
    return True, posterior_reasons


def _validate_action(action: object) -> Tuple[bool, Tuple[str, ...]]:
    if not isinstance(action, CandidateAction):
        return False, ("INVALID_ACTION_OBJECT",)
    if not _bounded_text(action.action_id) or not _bounded_text(action.agent_id):
        return False, ("INVALID_ACTION_OR_AGENT_ID",)
    if not isinstance(action.label, ActionLabel):
        return False, ("INVALID_ACTION_LABEL",)
    if not isinstance(action.arrival_sequence, int) or isinstance(action.arrival_sequence, bool) or action.arrival_sequence < 0:
        return False, ("INVALID_ARRIVAL_SEQUENCE",)
    if not _valid_refs(action.assumption_ids) or not _valid_refs(action.evidence_refs):
        return False, ("INVALID_ACTION_REFERENCE",)
    if not _valid_refs(action.causal_parent_event_ids, allow_empty=True, limit=MAX_CAUSAL_PARENT_COUNT):
        return False, ("INVALID_CAUSAL_PARENT_REFERENCE",)
    if action.conflict_key is not None and not _bounded_text(action.conflict_key):
        return False, ("INVALID_CONFLICT_KEY",)
    if not isinstance(action.requires_complete_information, bool):
        return False, ("INVALID_COMPLETE_INFORMATION_FLAG",)
    if action.order is not None and not isinstance(action.order, SyntheticOrder):
        return False, ("INVALID_SYNTHETIC_ORDER",)
    return True, ()


def _blocked_event(run_id: str, ordinal: int, action: CandidateAction, reasons: Sequence[str], owner_hash: str, system_hash: str) -> LedgerEvent:
    event_id = _event_id(run_id, ordinal, action, "BLOCKED", reasons, owner_hash, owner_hash)
    return LedgerEvent(event_id, ordinal, action.agent_id, action.action_id, ActionLabel.BLOCKED, False,
                       "INVALID_OR_BLOCKED", 0, tuple(reasons), tuple(sorted(action.evidence_refs)),
                       tuple(sorted(action.causal_parent_event_ids)), owner_hash, owner_hash, system_hash, system_hash)


def _abstain_event(run_id: str, ordinal: int, action: CandidateAction, reason: str, owner_hash: str, system_hash: str) -> LedgerEvent:
    event_id = _event_id(run_id, ordinal, action, "ABSTAIN", (reason,), owner_hash, owner_hash)
    return LedgerEvent(event_id, ordinal, action.agent_id, action.action_id, ActionLabel.ABSTAIN, False,
                       "ABSTAINED", 0, (reason,), tuple(sorted(action.evidence_refs)),
                       tuple(sorted(action.causal_parent_event_ids)), owner_hash, owner_hash, system_hash, system_hash)


def _build_portfolios(agents: Tuple[AgentState, ...]) -> dict[str, AgentPortfolioState]:
    return {agent.agent_id: AgentPortfolioState(agent.agent_id, agent.inventory, agent.inventory,
                                                 _portfolio_hash(agent.agent_id, agent.inventory),
                                                 _portfolio_hash(agent.agent_id, agent.inventory), 0)
            for agent in agents}


def arbitrate(
    run_id: str,
    market: MarketState,
    agents: Sequence[AgentState],
    actions: Sequence[CandidateAction],
    *,
    prior_events: Sequence[LedgerEvent] = (),
    prior_shared_market_state: Optional[SharedMarketState] = None,
    prior_executed_action_ids: Sequence[str] = (),
    prior_executed_order_ids: Sequence[str] = (),
) -> GameRun:
    """Apply actions to owning agents only, under explicit synthetic arbitration."""
    if not _bounded_text(run_id):
        raise ValueError("INVALID_RUN_ID")
    if not isinstance(market, MarketState):
        raise ValueError("INVALID_MARKET_STATE")
    if not isinstance(agents, (tuple, list)) or not isinstance(actions, (tuple, list)):
        raise ValueError("INVALID_TOP_LEVEL_COLLECTION")
    if not 1 <= len(agents) <= MAX_AGENT_COUNT:
        raise ValueError("INVALID_AGENT_COUNT")
    if len(actions) > MAX_ACTION_COUNT:
        raise ValueError("ACTION_LIMIT_EXCEEDED")
    if len(prior_events) > MAX_EVENT_COUNT or any(not isinstance(event, LedgerEvent) for event in prior_events):
        raise ValueError("INVALID_PRIOR_EVENT_COLLECTION")
    if len({event.event_id for event in prior_events}) != len(prior_events):
        raise ValueError("DUPLICATE_PRIOR_EVENT_ID")
    if not isinstance(prior_executed_action_ids, (tuple, list)) or not isinstance(prior_executed_order_ids, (tuple, list)):
        raise ValueError("INVALID_PRIOR_EXECUTION_COLLECTION")
    if len(set(prior_executed_action_ids)) != len(prior_executed_action_ids) or len(set(prior_executed_order_ids)) != len(prior_executed_order_ids):
        raise ValueError("DUPLICATE_PRIOR_EXECUTION_ID")
    if any(not _bounded_text(item) for item in tuple(prior_executed_action_ids) + tuple(prior_executed_order_ids)):
        raise ValueError("INVALID_PRIOR_EXECUTION_ID")
    if prior_shared_market_state is not None:
        if not isinstance(prior_shared_market_state, SharedMarketState) or prior_shared_market_state.market != market:
            raise ValueError("INVALID_OR_CHANGED_PRIOR_SHARED_MARKET_STATE")
    if any(not isinstance(agent, AgentState) for agent in agents):
        raise ValueError("INVALID_AGENT_OBJECT")
    if any(not isinstance(action, CandidateAction) for action in actions):
        raise ValueError("INVALID_ACTION_OBJECT")
    agent_tuple, action_tuple = tuple(agents), tuple(actions)
    if len({agent.agent_id for agent in agent_tuple}) != len(agent_tuple):
        raise ValueError("DUPLICATE_AGENT_ID")
    if len({action.action_id for action in action_tuple}) != len(action_tuple):
        raise ValueError("DUPLICATE_ACTION_ID")
    if len({action.arrival_sequence for action in action_tuple}) != len(action_tuple):
        raise ValueError("AMBIGUOUS_ACTION_ARRIVAL_SEQUENCE")
    agent_by_id = {agent.agent_id: agent for agent in agent_tuple}
    invalid_agents = {agent.agent_id: _validate_agent(agent, market)[1] for agent in agent_tuple if not _validate_agent(agent, market)[0]}
    invalid_actions = {action.action_id: _validate_action(action)[1] for action in action_tuple if not _validate_action(action)[0]}
    portfolios = _build_portfolios(agent_tuple)
    events: list[LedgerEvent] = []
    prior_ids = tuple(event.event_id for event in prior_events)
    known_parent_ids = set(prior_ids)
    claimed_conflicts: dict[str, str] = dict(prior_shared_market_state.conflict_claim_event_ids) if prior_shared_market_state else {}
    executed_action_ids = set(prior_executed_action_ids)
    executed_order_ids = set(prior_executed_order_ids)

    for ordinal, action in enumerate(sorted(action_tuple, key=lambda item: item.arrival_sequence), start=1):
        owner = portfolios.get(action.agent_id)
        owner_hash = owner.post_state_hash if owner is not None else "UNKNOWN_OWNER_STATE"
        system_before = _system_hash(portfolios, market, claimed_conflicts, prior_ids + tuple(event.event_id for event in events))
        if action.action_id in invalid_actions:
            events.append(_blocked_event(run_id, ordinal, action, invalid_actions[action.action_id], owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        agent = agent_by_id.get(action.agent_id)
        if agent is None:
            events.append(_blocked_event(run_id, ordinal, action, ("UNKNOWN_AGENT",), owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        if agent.agent_id in invalid_agents:
            events.append(_blocked_event(run_id, ordinal, action, invalid_agents[agent.agent_id], owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        if any(parent not in known_parent_ids for parent in action.causal_parent_event_ids):
            events.append(_blocked_event(run_id, ordinal, action, ("UNKNOWN_OR_FORWARD_CAUSAL_PARENT",), owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        if action.label is ActionLabel.ABSTAIN:
            events.append(_abstain_event(run_id, ordinal, action, "DECLARED_ABSTENTION", owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        if action.label is ActionLabel.BLOCKED:
            events.append(_blocked_event(run_id, ordinal, action, ("DECLARED_BLOCKED_ACTION",), owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        if action.requires_complete_information and agent.information.unknowns:
            events.append(_abstain_event(run_id, ordinal, action, "INCOMPLETE_INFORMATION", owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        if action.order is None:
            events.append(_blocked_event(run_id, ordinal, action, ("MISSING_SYNTHETIC_ORDER",), owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        if action.action_id in executed_action_ids or action.order.order_id in executed_order_ids:
            events.append(_blocked_event(run_id, ordinal, action, ("REPLAYED_ACTION_OR_ORDER_REJECTED",), owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        if action.conflict_key and action.conflict_key in claimed_conflicts:
            events.append(_blocked_event(run_id, ordinal, action, ("CONFLICT_RESOURCE_ALREADY_CLAIMED",), owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        outcome: SyntheticMatchOutcome = reduce_order(market, owner.final_inventory, action.order)
        accepted = outcome.status is not OutcomeStatus.INVALID_OR_BLOCKED
        next_inventory = outcome.inventory
        next_owner_hash = _portfolio_hash(action.agent_id, next_inventory)
        next_portfolio = AgentPortfolioState(action.agent_id, owner.initial_inventory, next_inventory, owner.pre_state_hash,
                                             next_owner_hash, owner.net_filled_quantity + (outcome.filled_quantity if action.order.side.value == "BUY" else -outcome.filled_quantity))
        portfolios[action.agent_id] = next_portfolio
        provisional_id = _event_id(run_id, ordinal, action, outcome.status.value, outcome.reason_codes, owner_hash, next_owner_hash)
        if accepted and action.conflict_key:
            claimed_conflicts[action.conflict_key] = provisional_id
        system_after = _system_hash(portfolios, market, claimed_conflicts, prior_ids + tuple(event.event_id for event in events) + (provisional_id,))
        event = LedgerEvent(provisional_id, ordinal, action.agent_id, action.action_id,
                            action.label if accepted else ActionLabel.BLOCKED, accepted, outcome.status.value,
                            outcome.filled_quantity, tuple(outcome.reason_codes), tuple(sorted(action.evidence_refs)),
                            tuple(sorted(action.causal_parent_event_ids)), owner_hash, next_owner_hash, system_before, system_after)
        events.append(event)
        known_parent_ids.add(event.event_id)
        executed_action_ids.add(action.action_id)
        executed_order_ids.add(action.order.order_id)
    ordered_portfolios = tuple(portfolios[agent_id] for agent_id in sorted(portfolios))
    shared_hash = _sha({"market": market, "claims": sorted(claimed_conflicts.items())})
    shared = SharedMarketState(market, tuple(sorted(claimed_conflicts)), tuple(sorted(claimed_conflicts.items())), shared_hash)
    ledger_hash = _sha([event for event in events])
    total_hash = _system_hash(portfolios, market, claimed_conflicts, prior_ids + tuple(event.event_id for event in events))
    return GameRun(run_id, tuple(events), ordered_portfolios, shared, ledger_hash, total_hash, prior_ids,
                   tuple(sorted(executed_action_ids)), tuple(sorted(executed_order_ids)), action_tuple)


def run_one_step_counterfactual(run_id: str, market: MarketState, agents: Sequence[AgentState], actions: Sequence[CandidateAction], changed_assumption_id: str) -> CounterfactualResult:
    baseline = arbitrate(run_id + ":baseline", market, agents, actions)
    changed = tuple(action.action_id for action in actions if isinstance(action, CandidateAction) and changed_assumption_id in action.assumption_ids)
    if len(changed) != 1:
        raise ValueError("COUNTERFACTUAL_REQUIRES_EXACTLY_ONE_ACTION")
    alternative_actions = tuple(replace(action, label=ActionLabel.ABSTAIN, order=None) if action.action_id == changed[0] else action for action in actions)
    alternative = arbitrate(run_id + ":counterfactual", market, agents, alternative_actions)
    return CounterfactualResult(changed_assumption_id, baseline, alternative, changed)


def _agents_from_portfolios(agents: Sequence[AgentState], portfolios: Sequence[AgentPortfolioState]) -> Tuple[AgentState, ...]:
    inventory_by_id = {portfolio.agent_id: portfolio.final_inventory for portfolio in portfolios}
    return tuple(replace(agent, inventory=inventory_by_id[agent.agent_id]) for agent in agents)


def run_bounded_counterfactual_episode(run_id: str, market: MarketState, agents: Sequence[AgentState], actions: Sequence[CandidateAction], changed_assumption_ids: Sequence[str], *, max_steps: int = 12) -> BoundedCounterfactualEpisode:
    """State-carrying episode: later steps inherit prior portfolios and causal ledger."""
    if not isinstance(max_steps, int) or isinstance(max_steps, bool) or not 1 <= max_steps <= 12:
        raise ValueError("INVALID_COUNTERFACTUAL_MAX_STEPS")
    if not isinstance(changed_assumption_ids, (tuple, list)):
        raise ValueError("INVALID_COUNTERFACTUAL_ASSUMPTION_SEQUENCE")
    identifiers = tuple(changed_assumption_ids)
    if not identifiers or len(identifiers) > max_steps or len(set(identifiers)) != len(identifiers) or not all(_bounded_text(item) for item in identifiers):
        raise ValueError("INVALID_COUNTERFACTUAL_ASSUMPTION_SEQUENCE")
    current_agents = tuple(agents)
    current_actions = tuple(actions)
    accumulated_events: tuple[LedgerEvent, ...] = ()
    runs: list[GameRun] = []
    for index, assumption_id in enumerate(identifiers, start=1):
        matching = [action for action in current_actions if isinstance(action, CandidateAction) and assumption_id in action.assumption_ids]
        if len(matching) != 1:
            raise ValueError("COUNTERFACTUAL_REQUIRES_EXACTLY_ONE_ACTION")
        target_id = matching[0].action_id
        inherited_parent = (accumulated_events[-1].event_id,) if accumulated_events else ()
        current_actions = tuple(
            replace(action, label=ActionLabel.ABSTAIN, order=None,
                    causal_parent_event_ids=action.causal_parent_event_ids or inherited_parent)
            if action.action_id == target_id else action
            for action in current_actions
        )
        prior_run = runs[-1] if runs else None
        run = arbitrate(
            run_id + f":step:{index}", market, current_agents, current_actions,
            prior_events=accumulated_events,
            prior_shared_market_state=prior_run.shared_market_state if prior_run else None,
            prior_executed_action_ids=prior_run.executed_action_ids if prior_run else (),
            prior_executed_order_ids=prior_run.executed_order_ids if prior_run else (),
        )
        runs.append(run)
        accumulated_events = accumulated_events + run.events
        current_agents = _agents_from_portfolios(current_agents, run.final_agent_portfolios)
    return BoundedCounterfactualEpisode(identifiers, tuple(runs), max_steps, runs[-1].total_system_state_hash)


def inventory_ledger_conserved(initial: InventoryState, result: GameRun, actions: Sequence[CandidateAction]) -> bool:
    """Legacy single-agent conservation helper retained for scaffold consumers."""
    if result.final_inventory is None:
        return False
    by_id = {action.action_id: action for action in actions if isinstance(action, CandidateAction)}
    delta = sum(event.filled_quantity if by_id.get(event.action_id) and by_id[event.action_id].order and by_id[event.action_id].order.side.value == "BUY" else -event.filled_quantity for event in result.events)
    return _inventory_quantity(initial) + delta == _inventory_quantity(result.final_inventory)


def total_system_conserved(initial_agents: Sequence[AgentState], result: GameRun) -> bool:
    """Recompute deltas from immutable action/event records; ignore stored net fields."""
    if not isinstance(initial_agents, (tuple, list)):
        return False
    initial_by_id = {agent.agent_id: agent.inventory for agent in initial_agents if isinstance(agent, AgentState)}
    if len(initial_by_id) != len(result.final_agent_portfolios):
        return False
    actions = {action.action_id: action for action in result.action_records}
    if len(actions) != len(result.action_records):
        return False
    recomputed: dict[str, int] = {agent_id: 0 for agent_id in initial_by_id}
    for event in result.events:
        action = actions.get(event.action_id)
        if action is None or action.agent_id != event.agent_id:
            return False
        if event.accepted:
            if action.order is None or event.filled_quantity < 0:
                return False
            signed = event.filled_quantity if action.order.side.value == "BUY" else -event.filled_quantity
            recomputed[event.agent_id] = recomputed.get(event.agent_id, 0) + signed
        elif event.filled_quantity != 0:
            return False
    return all(
        initial_by_id.get(portfolio.agent_id) == portfolio.initial_inventory
        and _inventory_quantity(portfolio.final_inventory) - _inventory_quantity(portfolio.initial_inventory) == recomputed.get(portfolio.agent_id)
        for portfolio in result.final_agent_portfolios
    )


def evaluate_narrative(record: NarrativeForecastRecord, now_ns: int) -> NarrativeStatus:
    if record.status is not NarrativeStatus.UNKNOWN:
        return record.status
    if record.expires_at_ns is None:
        return NarrativeStatus.UNKNOWN
    return NarrativeStatus.EXPIRED if now_ns > record.expires_at_ns else NarrativeStatus.UNKNOWN


def feature_container(value: float, names: Sequence[str], *, mismatch: bool = False):
    if not _finite_number(value):
        raise ValueError("INVALID_UNCALIBRATED_FEATURE_VALUE")
    if not isinstance(names, (tuple, list)) or not names or any(not _bounded_text(name) for name in names):
        raise ValueError("INVALID_FEATURE_NAMES")
    factory = ParticipantMismatchRisk if mismatch else ParticipantAlignmentScore
    return factory(tuple(sorted(set(names))), float(value))
