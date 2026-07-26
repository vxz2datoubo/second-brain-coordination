"""Deterministic D2 synthetic multi-agent game core.

This module composes the accepted D1 reducer.  Its participants, beliefs,
intentions, scores, actions, and narratives are synthetic hypotheses only; none
of them identify a real participant or make a trading claim.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Optional, Sequence, Tuple


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
        if not self.hypotheses:
            return False, ("EMPTY_HIDDEN_TYPE_POSTERIOR",)
        weights = [item.normalized_weight for item in self.hypotheses]
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in weights):
            return False, ("INVALID_POSTERIOR_WEIGHT_TYPE",)
        if any(value < 0 or value > 1 for value in weights):
            return False, ("POSTERIOR_WEIGHT_OUT_OF_RANGE",)
        if abs(sum(weights) - 1.0) > 1e-9:
            return False, ("POSTERIOR_NOT_NORMALIZED",)
        return True, ("UNCALIBRATED_NORMALIZED_WEIGHTS_ONLY",)


@dataclass(frozen=True)
class AgentInformationSet:
    available_at_ns: Optional[int]
    observable_refs: Tuple[str, ...]
    unknowns: Tuple[str, ...]
    source_capability: str = SYNTHETIC_CAPABILITY


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
    final_inventory: InventoryState
    ledger_hash: str


@dataclass(frozen=True)
class CounterfactualResult:
    changed_assumption_id: str
    baseline: GameRun
    alternative: GameRun
    changed_action_ids: Tuple[str, ...]


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _event_id(run_id: str, ordinal: int, action: CandidateAction, status: str, reasons: Sequence[str]) -> str:
    return hashlib.sha256(_canonical({
        "run_id": run_id,
        "ordinal": ordinal,
        "agent_id": action.agent_id,
        "action_id": action.action_id,
        "status": status,
        "reasons": tuple(reasons),
    })).hexdigest()


def _inventory_quantity(inventory: InventoryState) -> int:
    return sum(lot.quantity for lot in inventory.lots)


def _action_sort_key(action: CandidateAction) -> tuple[str, str]:
    return action.agent_id, action.action_id


def _validate_agent(agent: AgentState, market: MarketState) -> Tuple[bool, Tuple[str, ...]]:
    if not isinstance(agent.agent_id, str) or not agent.agent_id:
        return False, ("INVALID_AGENT_ID",)
    valid_posterior, posterior_reasons = agent.posterior.validate()
    if not valid_posterior:
        return False, posterior_reasons
    info = agent.information
    if info.source_capability != SYNTHETIC_CAPABILITY:
        return False, ("UNSUPPORTED_AGENT_CAPABILITY",)
    if not isinstance(info.available_at_ns, int) or isinstance(info.available_at_ns, bool) or info.available_at_ns < 0:
        return False, ("UNKNOWN_OR_INVALID_AGENT_INFORMATION_TIME",)
    if market.information is None or market.information.available_at_ns is None:
        return False, ("UNKNOWN_MARKET_INFORMATION_TIME",)
    if info.available_at_ns > market.information.available_at_ns:
        return False, ("AGENT_FUTURE_INFORMATION",)
    return True, posterior_reasons


def _blocked_event(run_id: str, ordinal: int, action: CandidateAction, reasons: Sequence[str]) -> LedgerEvent:
    return LedgerEvent(
        event_id=_event_id(run_id, ordinal, action, "BLOCKED", reasons),
        ordinal=ordinal,
        agent_id=action.agent_id,
        action_id=action.action_id,
        label=ActionLabel.BLOCKED,
        accepted=False,
        outcome_status="INVALID_OR_BLOCKED",
        filled_quantity=0,
        rejected_reason_codes=tuple(reasons),
        cause_refs=tuple(sorted(action.evidence_refs)),
    )


def _abstain_event(run_id: str, ordinal: int, action: CandidateAction, reason: str) -> LedgerEvent:
    return LedgerEvent(
        event_id=_event_id(run_id, ordinal, action, "ABSTAIN", (reason,)),
        ordinal=ordinal,
        agent_id=action.agent_id,
        action_id=action.action_id,
        label=ActionLabel.ABSTAIN,
        accepted=False,
        outcome_status="ABSTAINED",
        filled_quantity=0,
        rejected_reason_codes=(reason,),
        cause_refs=tuple(sorted(action.evidence_refs)),
    )


def arbitrate(
    run_id: str,
    market: MarketState,
    agents: Sequence[AgentState],
    actions: Sequence[CandidateAction],
) -> GameRun:
    """Deterministically applies synthetic candidate actions through the D1 reducer."""
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("INVALID_RUN_ID")
    if len(agents) > MAX_AGENT_COUNT:
        raise ValueError("AGENT_LIMIT_EXCEEDED")
    agent_by_id = {agent.agent_id: agent for agent in agents}
    if len(agent_by_id) != len(agents):
        raise ValueError("DUPLICATE_AGENT_ID")
    if len({action.action_id for action in actions}) != len(actions):
        raise ValueError("DUPLICATE_ACTION_ID")
    if any(not isinstance(action, CandidateAction) for action in actions):
        raise ValueError("INVALID_ACTION_OBJECT")
    if not agents:
        raise ValueError("EMPTY_AGENT_SET")

    working_inventory = agents[0].inventory
    events: list[LedgerEvent] = []
    claimed_conflicts: set[str] = set()
    for ordinal, action in enumerate(sorted(actions, key=_action_sort_key), start=1):
        agent = agent_by_id.get(action.agent_id)
        if agent is None:
            events.append(_blocked_event(run_id, ordinal, action, ("UNKNOWN_AGENT",)))
            continue
        agent_ok, agent_reasons = _validate_agent(agent, market)
        if not agent_ok:
            events.append(_blocked_event(run_id, ordinal, action, agent_reasons))
            continue
        if not action.evidence_refs:
            events.append(_blocked_event(run_id, ordinal, action, ("MISSING_ACTION_EVIDENCE",)))
            continue
        if action.label is ActionLabel.ABSTAIN:
            events.append(_abstain_event(run_id, ordinal, action, "DECLARED_ABSTENTION"))
            continue
        if action.order is None:
            events.append(_blocked_event(run_id, ordinal, action, ("MISSING_SYNTHETIC_ORDER",)))
            continue
        if action.conflict_key and action.conflict_key in claimed_conflicts:
            events.append(_blocked_event(run_id, ordinal, action, ("CONFLICT_KEY_ALREADY_CLAIMED",)))
            continue
        outcome: SyntheticMatchOutcome = reduce_order(market, working_inventory, action.order)
        accepted = outcome.status is not OutcomeStatus.INVALID_OR_BLOCKED
        if accepted and action.conflict_key:
            claimed_conflicts.add(action.conflict_key)
        working_inventory = outcome.inventory
        event = LedgerEvent(
            event_id=_event_id(run_id, ordinal, action, outcome.status.value, outcome.reason_codes),
            ordinal=ordinal,
            agent_id=action.agent_id,
            action_id=action.action_id,
            label=action.label if accepted else ActionLabel.BLOCKED,
            accepted=accepted,
            outcome_status=outcome.status.value,
            filled_quantity=outcome.filled_quantity,
            rejected_reason_codes=tuple(outcome.reason_codes),
            cause_refs=tuple(sorted(action.evidence_refs)),
        )
        events.append(event)
    ledger_payload = [event.__dict__ | {"label": event.label.value} for event in events]
    return GameRun(run_id, tuple(events), working_inventory, hashlib.sha256(_canonical(ledger_payload)).hexdigest())


def run_one_step_counterfactual(
    run_id: str,
    market: MarketState,
    agents: Sequence[AgentState],
    actions: Sequence[CandidateAction],
    changed_assumption_id: str,
) -> CounterfactualResult:
    """Change exactly one declared assumption by converting affected actions to abstention."""
    baseline = arbitrate(run_id + ":baseline", market, agents, actions)
    changed = tuple(action.action_id for action in actions if changed_assumption_id in action.assumption_ids)
    if len(changed) != 1:
        raise ValueError("COUNTERFACTUAL_REQUIRES_EXACTLY_ONE_ACTION")
    alternative_actions = tuple(
        replace(action, label=ActionLabel.ABSTAIN, order=None)
        if action.action_id == changed[0] else action
        for action in actions
    )
    alternative = arbitrate(run_id + ":counterfactual", market, agents, alternative_actions)
    return CounterfactualResult(changed_assumption_id, baseline, alternative, changed)


def inventory_ledger_conserved(initial: InventoryState, result: GameRun, actions: Sequence[CandidateAction]) -> bool:
    """Synthetic accounting identity: initial + filled buys - filled sells equals final."""
    by_id = {action.action_id: action for action in actions}
    delta = 0
    for event in result.events:
        action = by_id.get(event.action_id)
        if action is None or action.order is None:
            continue
        delta += event.filled_quantity if action.order.side.value == "BUY" else -event.filled_quantity
    return _inventory_quantity(initial) + delta == _inventory_quantity(result.final_inventory)


def evaluate_narrative(record: NarrativeForecastRecord, now_ns: int) -> NarrativeStatus:
    if record.status is not NarrativeStatus.UNKNOWN:
        return record.status
    if record.expires_at_ns is None:
        return NarrativeStatus.UNKNOWN
    return NarrativeStatus.EXPIRED if now_ns > record.expires_at_ns else NarrativeStatus.UNKNOWN


def feature_container(value: float, names: Sequence[str], *, mismatch: bool = False):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or abs(value) > MAX_FEATURE_MAGNITUDE:
        raise ValueError("INVALID_UNCALIBRATED_FEATURE_VALUE")
    if not names or any(not isinstance(name, str) or not name for name in names):
        raise ValueError("INVALID_FEATURE_NAMES")
    factory = ParticipantMismatchRisk if mismatch else ParticipantAlignmentScore
    return factory(tuple(sorted(set(names))), float(value))
