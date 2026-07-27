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


class ConflictTransition(str, Enum):
    CLAIM = "claim"
    RELEASE = "release"
    EXPIRE = "expire"
    NONE = "none"


class LiquidityMode(str, Enum):
    EXTERNAL_SYNTHETIC_LIQUIDITY = "external_synthetic_liquidity"
    PEER_TO_PEER_TRANSFER = "peer_to_peer_transfer"


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
    invocation_id: Optional[str] = None
    conflict_transition: ConflictTransition = ConflictTransition.CLAIM
    liquidity_mode: LiquidityMode = LiquidityMode.EXTERNAL_SYNTHETIC_LIQUIDITY
    counterparty_agent_id: Optional[str] = None
    peer_transfer_id: Optional[str] = None

    @property
    def effective_invocation_id(self) -> str:
        return self.invocation_id or self.action_id


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
    invocation_id: str = ""
    liquidity_mode: LiquidityMode = LiquidityMode.EXTERNAL_SYNTHETIC_LIQUIDITY
    conflict_transition: ConflictTransition = ConflictTransition.NONE
    counterparty_agent_id: Optional[str] = None
    peer_transfer_id: Optional[str] = None


@dataclass(frozen=True)
class ExternalLiquidityFlowEvent:
    """Declared open-system offset; never confused with peer inventory transfer."""

    flow_id: str
    ledger_event_id: str
    agent_id: str
    agent_inventory_delta: int
    external_inventory_delta: int


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
    episode_state: Optional["EpisodeState"] = None

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


@dataclass(frozen=True)
class EpisodeState:
    """Immutable episode carrier; all cross-step identity and DAG state lives here."""

    step_index: int
    current_agents: Tuple[AgentState, ...]
    shared_market_state: SharedMarketState
    executed_action_ids: Tuple[str, ...]
    executed_order_ids: Tuple[str, ...]
    executed_invocation_ids: Tuple[str, ...]
    event_dag: Tuple[LedgerEvent, ...]
    initial_agents: Tuple[AgentState, ...]
    action_registry: Tuple[CandidateAction, ...]
    external_liquidity_flows: Tuple[ExternalLiquidityFlowEvent, ...]
    state_hash: str


@dataclass(frozen=True)
class EpisodeLedgerVerification:
    valid: bool
    reason_codes: Tuple[str, ...]
    reconstructed_state_hash: str


def verify_episode_ledger(episode: object) -> EpisodeLedgerVerification:
    """Reconstruct the episode from immutable inputs; never trust stored portfolios."""
    if not isinstance(episode, EpisodeState):
        return EpisodeLedgerVerification(False, ("INVALID_EPISODE_STATE",), "")
    reasons: list[str] = []
    events = episode.event_dag
    ids = tuple(event.event_id for event in events)
    if len(ids) != len(set(ids)):
        reasons.append("DUPLICATE_EVENT_ID")
    if len(episode.executed_action_ids) != len(set(episode.executed_action_ids)):
        reasons.append("DUPLICATE_EXECUTED_ACTION_ID")
    if len(episode.executed_order_ids) != len(set(episode.executed_order_ids)):
        reasons.append("DUPLICATE_EXECUTED_ORDER_ID")
    if len(episode.executed_invocation_ids) != len(set(episode.executed_invocation_ids)):
        reasons.append("DUPLICATE_EXECUTED_INVOCATION_ID")
    registry = {action.action_id: action for action in episode.action_registry}
    if len(registry) != len(episode.action_registry):
        reasons.append("DUPLICATE_ACTION_REGISTRY_ID")
    if any(not isinstance(agent, AgentState) for agent in episode.initial_agents):
        reasons.append("INVALID_INITIAL_AGENT_REGISTRY")
        return EpisodeLedgerVerification(False, tuple(sorted(set(reasons))), "")
    if len({agent.agent_id for agent in episode.initial_agents}) != len(episode.initial_agents):
        reasons.append("DUPLICATE_INITIAL_AGENT_ID")
    portfolios = _build_portfolios(episode.initial_agents)
    claimed: dict[str, str] = {}
    known: set[str] = set()
    known_order: list[str] = []
    executed_actions: set[str] = set()
    executed_orders: set[str] = set()
    executed_invocations: set[str] = set()
    verified_flows: list[ExternalLiquidityFlowEvent] = []
    peer_deltas: dict[str, int] = {}
    peer_pair_reasons = _validate_peer_transfer_pairs(episode.action_registry)
    if peer_pair_reasons:
        reasons.append("INVALID_PEER_TRANSFER_REGISTRY")
    for ordinal, event in enumerate(events, start=1):
        action = registry.get(event.action_id)
        if action is None or action.agent_id != event.agent_id:
            reasons.append("EVENT_ACTION_REGISTRY_MISMATCH")
            continue
        if event.ordinal != ordinal:
            reasons.append("NON_SEQUENTIAL_EVENT_ORDINAL")
        if any(parent not in known for parent in event.causal_parent_event_ids):
            reasons.append("INVALID_OR_FORWARD_CAUSAL_PARENT")
        owner = portfolios.get(action.agent_id)
        if owner is None:
            reasons.append("VERIFIER_UNKNOWN_OWNER")
            continue
        owner_pre = owner.post_state_hash
        system_pre = _system_hash(portfolios, episode.shared_market_state.market, claimed, tuple(known_order))
        if event.owner_pre_state_hash != owner_pre or event.system_pre_state_hash != system_pre:
            reasons.append("FORGED_PRE_STATE")
        if action.action_id in executed_actions or action.effective_invocation_id in executed_invocations:
            reasons.append("REPLAYED_EVENT_IDENTITY")
        if action.order is not None and action.order.order_id in executed_orders:
            reasons.append("REPLAYED_EVENT_ORDER_ID")

        next_owner = owner
        expected_filled = 0
        expected_status = event.outcome_status
        if action.conflict_transition in (ConflictTransition.RELEASE, ConflictTransition.EXPIRE):
            claim_event_id = claimed.get(action.conflict_key or "")
            claim_event = next((known_event for known_event in events[: ordinal - 1] if known_event.event_id == claim_event_id), None)
            if claim_event_id is None or claim_event is None or claim_event.agent_id != action.agent_id:
                reasons.append("INVALID_RESOURCE_LIFECYCLE_OWNER")
            else:
                del claimed[action.conflict_key or ""]
                expected_status = "CONFLICT_RESOURCE_" + action.conflict_transition.value.upper()
        elif event.accepted:
            if action.order is None:
                reasons.append("ACCEPTED_EVENT_WITHOUT_ORDER")
            else:
                outcome = reduce_order(episode.shared_market_state.market, owner.final_inventory, action.order)
                expected_filled = outcome.filled_quantity
                expected_status = outcome.status.value
                if outcome.status is OutcomeStatus.INVALID_OR_BLOCKED:
                    reasons.append("FORGED_ACCEPTED_OUTCOME")
                next_inventory = outcome.inventory
                next_owner = AgentPortfolioState(
                    action.agent_id,
                    owner.initial_inventory,
                    next_inventory,
                    owner.pre_state_hash,
                    _portfolio_hash(action.agent_id, next_inventory),
                    owner.net_filled_quantity + (outcome.filled_quantity if action.order.side.value == "BUY" else -outcome.filled_quantity),
                )
                portfolios[action.agent_id] = next_owner
                if action.conflict_key and action.conflict_transition is ConflictTransition.CLAIM:
                    claimed[action.conflict_key] = event.event_id
                if action.liquidity_mode is LiquidityMode.EXTERNAL_SYNTHETIC_LIQUIDITY:
                    verified_flows.append(_flow_for_event(event, action))
                else:
                    signed = outcome.filled_quantity if action.order.side.value == "BUY" else -outcome.filled_quantity
                    peer_deltas[action.peer_transfer_id or ""] = peer_deltas.get(action.peer_transfer_id or "", 0) + signed
        elif event.filled_quantity != 0:
            reasons.append("BLOCKED_EVENT_MUTATES_INVENTORY")

        system_post = _system_hash(portfolios, episode.shared_market_state.market, claimed, tuple(known_order) + (event.event_id,))
        if event.owner_post_state_hash != next_owner.post_state_hash or event.system_post_state_hash != system_post:
            reasons.append("FORGED_POST_STATE")
        if event.filled_quantity != expected_filled or event.outcome_status != expected_status:
            reasons.append("FORGED_EVENT_OUTCOME")
        identity_consumed = event.accepted or event.outcome_status == "ABSTAINED" or "DECLARED_BLOCKED_ACTION" in event.rejected_reason_codes
        if identity_consumed:
            executed_actions.add(action.action_id)
            executed_invocations.add(action.effective_invocation_id)
            if event.accepted and action.order is not None and action.conflict_transition not in (ConflictTransition.RELEASE, ConflictTransition.EXPIRE):
                executed_orders.add(action.order.order_id)
        known.add(event.event_id)
        known_order.append(event.event_id)
    if any(delta != 0 for delta in peer_deltas.values()):
        reasons.append("UNBALANCED_PEER_TRANSFER")
    if tuple(sorted(verified_flows, key=lambda flow: flow.flow_id)) != tuple(sorted(episode.external_liquidity_flows, key=lambda flow: flow.flow_id)):
        reasons.append("EXTERNAL_FLOW_LEDGER_MISMATCH")
    final_agents = _agents_from_portfolios(episode.initial_agents, tuple(portfolios[agent_id] for agent_id in sorted(portfolios)))
    expected_shared = SharedMarketState(
        episode.shared_market_state.market,
        tuple(sorted(claimed)),
        tuple(sorted(claimed.items())),
        _sha({"market": episode.shared_market_state.market, "claims": sorted(claimed.items())}),
    )
    if episode.current_agents != final_agents or episode.shared_market_state != expected_shared:
        reasons.append("FORGED_STORED_EPISODE_STATE")
    reconstructed = _episode_state_hash(
        step_index=episode.step_index,
        initial_agents=episode.initial_agents,
        current_agents=final_agents,
        shared_market_state=expected_shared,
        executed_action_ids=tuple(sorted(executed_actions)),
        executed_order_ids=tuple(sorted(executed_orders)),
        executed_invocation_ids=tuple(sorted(executed_invocations)),
        event_dag=events,
        action_registry=episode.action_registry,
        external_liquidity_flows=verified_flows,
    )
    if (
        episode.executed_action_ids != tuple(sorted(executed_actions))
        or episode.executed_order_ids != tuple(sorted(executed_orders))
        or episode.executed_invocation_ids != tuple(sorted(executed_invocations))
        or reconstructed != episode.state_hash
    ):
        reasons.append("EPISODE_STATE_HASH_MISMATCH")
    return EpisodeLedgerVerification(not reasons, tuple(sorted(set(reasons))), reconstructed)


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
    """Hash only mutable system state; causal history is verified in the event DAG."""
    return _sha({
        "portfolios": {agent_id: portfolios[agent_id].final_inventory for agent_id in sorted(portfolios)},
        "market": market,
        "claimed_conflicts": sorted(claimed.items()),
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
    if action.invocation_id is not None and not _bounded_text(action.invocation_id):
        return False, ("INVALID_INVOCATION_ID",)
    if not isinstance(action.conflict_transition, ConflictTransition) or not isinstance(action.liquidity_mode, LiquidityMode):
        return False, ("INVALID_ACTION_SEMANTICS",)
    if action.counterparty_agent_id is not None and not _bounded_text(action.counterparty_agent_id):
        return False, ("INVALID_COUNTERPARTY_AGENT_ID",)
    if action.peer_transfer_id is not None and not _bounded_text(action.peer_transfer_id):
        return False, ("INVALID_PEER_TRANSFER_ID",)
    if action.liquidity_mode is LiquidityMode.PEER_TO_PEER_TRANSFER:
        if action.counterparty_agent_id is None:
            return False, ("PEER_TRANSFER_REQUIRES_COUNTERPARTY",)
        if action.peer_transfer_id is None:
            return False, ("PEER_TRANSFER_REQUIRES_TRANSFER_ID",)
    return True, ()


def _merge_action_registry(
    prior: Sequence[CandidateAction], current: Sequence[CandidateAction],
) -> Tuple[CandidateAction, ...]:
    merged = tuple(prior) + tuple(current)
    if any(not isinstance(action, CandidateAction) for action in merged):
        raise ValueError("INVALID_ACTION_REGISTRY")
    if len({action.action_id for action in merged}) != len(merged):
        raise ValueError("DUPLICATE_ACTION_REGISTRY_ID")
    return tuple(sorted(merged, key=lambda action: action.action_id))


def _episode_state_hash(
    *,
    step_index: int,
    initial_agents: Sequence[AgentState],
    current_agents: Sequence[AgentState],
    shared_market_state: SharedMarketState,
    executed_action_ids: Sequence[str],
    executed_order_ids: Sequence[str],
    executed_invocation_ids: Sequence[str],
    event_dag: Sequence[LedgerEvent],
    action_registry: Sequence[CandidateAction],
    external_liquidity_flows: Sequence[ExternalLiquidityFlowEvent],
) -> str:
    return _sha({
        "step_index": step_index,
        "initial_agents": tuple(initial_agents),
        "current_agents": tuple(current_agents),
        "shared_market_state": shared_market_state,
        "executed_action_ids": tuple(executed_action_ids),
        "executed_order_ids": tuple(executed_order_ids),
        "executed_invocation_ids": tuple(executed_invocation_ids),
        "event_dag": tuple(event_dag),
        "action_registry": tuple(action_registry),
        "external_liquidity_flows": tuple(external_liquidity_flows),
    })


def _validate_peer_transfer_pairs(actions: Sequence[CandidateAction]) -> dict[str, Tuple[str, ...]]:
    """Return per-action failure reasons; valid transfers are exactly adjacent, reciprocal pairs."""
    peers = [action for action in actions if action.liquidity_mode is LiquidityMode.PEER_TO_PEER_TRANSFER]
    grouped: dict[str, list[CandidateAction]] = {}
    for action in peers:
        if action.peer_transfer_id is not None:
            grouped.setdefault(action.peer_transfer_id, []).append(action)
    reasons: dict[str, Tuple[str, ...]] = {}
    for transfer_id, pair in grouped.items():
        if len(pair) != 2:
            for action in pair:
                reasons[action.action_id] = ("PEER_TRANSFER_REQUIRES_EXACTLY_TWO_ACTIONS",)
            continue
        first, second = sorted(pair, key=lambda action: action.arrival_sequence)
        valid = (
            first.counterparty_agent_id == second.agent_id
            and second.counterparty_agent_id == first.agent_id
            and first.agent_id != second.agent_id
            and first.order is not None
            and second.order is not None
            and first.order.side != second.order.side
            and first.order.quantity == second.order.quantity
            and second.arrival_sequence == first.arrival_sequence + 1
        )
        if not valid:
            reasons[first.action_id] = ("INVALID_PEER_TRANSFER_PAIR",)
            reasons[second.action_id] = ("INVALID_PEER_TRANSFER_PAIR",)
    return reasons


def _flow_for_event(event: LedgerEvent, action: CandidateAction) -> ExternalLiquidityFlowEvent:
    signed = event.filled_quantity if action.order and action.order.side.value == "BUY" else -event.filled_quantity
    return ExternalLiquidityFlowEvent(
        _sha({"ledger_event_id": event.event_id, "agent_id": event.agent_id, "agent_delta": signed}),
        event.event_id,
        event.agent_id,
        signed,
        -signed,
    )


def _blocked_event(run_id: str, ordinal: int, action: CandidateAction, reasons: Sequence[str], owner_hash: str, system_hash: str) -> LedgerEvent:
    event_id = _event_id(run_id, ordinal, action, "BLOCKED", reasons, owner_hash, owner_hash)
    return LedgerEvent(event_id, ordinal, action.agent_id, action.action_id, ActionLabel.BLOCKED, False,
                       "INVALID_OR_BLOCKED", 0, tuple(reasons), tuple(sorted(action.evidence_refs)),
                       tuple(sorted(action.causal_parent_event_ids)), owner_hash, owner_hash, system_hash, system_hash,
                       action.effective_invocation_id, action.liquidity_mode, action.conflict_transition,
                       action.counterparty_agent_id, action.peer_transfer_id)


def _abstain_event(run_id: str, ordinal: int, action: CandidateAction, reason: str, owner_hash: str, system_hash: str) -> LedgerEvent:
    event_id = _event_id(run_id, ordinal, action, "ABSTAIN", (reason,), owner_hash, owner_hash)
    return LedgerEvent(event_id, ordinal, action.agent_id, action.action_id, ActionLabel.ABSTAIN, False,
                       "ABSTAINED", 0, (reason,), tuple(sorted(action.evidence_refs)),
                       tuple(sorted(action.causal_parent_event_ids)), owner_hash, owner_hash, system_hash, system_hash,
                       action.effective_invocation_id, action.liquidity_mode, action.conflict_transition,
                       action.counterparty_agent_id, action.peer_transfer_id)


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
    prior_episode_state: Optional[EpisodeState] = None,
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
    if prior_episode_state is not None:
        if not isinstance(prior_episode_state, EpisodeState) or prior_episode_state.shared_market_state.market != market:
            raise ValueError("INVALID_PRIOR_EPISODE_STATE")
        if not verify_episode_ledger(prior_episode_state).valid:
            raise ValueError("UNVERIFIABLE_PRIOR_EPISODE_STATE")
        prior_events = prior_episode_state.event_dag
        prior_shared_market_state = prior_episode_state.shared_market_state
        prior_executed_action_ids = prior_episode_state.executed_action_ids
        prior_executed_order_ids = prior_episode_state.executed_order_ids
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
    if prior_episode_state is not None:
        if {agent.agent_id for agent in agent_tuple} != {agent.agent_id for agent in prior_episode_state.current_agents}:
            raise ValueError("PRIOR_EPISODE_AGENT_SET_MISMATCH")
        # The prior episode is the immutable source of inventories.  Callers may
        # supply stale descriptive agent objects, but cannot roll holdings back.
        agent_tuple = prior_episode_state.current_agents
    invocation_ids = tuple(action.effective_invocation_id for action in action_tuple)
    order_ids = tuple(action.order.order_id for action in action_tuple if action.order is not None)
    if len(set(invocation_ids)) != len(invocation_ids):
        raise ValueError("DUPLICATE_INVOCATION_ID")
    if len(set(order_ids)) != len(order_ids):
        raise ValueError("DUPLICATE_ORDER_ID")
    agent_by_id = {agent.agent_id: agent for agent in agent_tuple}
    invalid_agents = {agent.agent_id: _validate_agent(agent, market)[1] for agent in agent_tuple if not _validate_agent(agent, market)[0]}
    invalid_actions = {action.action_id: _validate_action(action)[1] for action in action_tuple if not _validate_action(action)[0]}
    invalid_actions.update(_validate_peer_transfer_pairs(action_tuple))
    portfolios = _build_portfolios(agent_tuple)
    events: list[LedgerEvent] = []
    prior_ids = tuple(event.event_id for event in prior_events)
    known_parent_ids = set(prior_ids)
    claimed_conflicts: dict[str, str] = dict(prior_shared_market_state.conflict_claim_event_ids) if prior_shared_market_state else {}
    executed_action_ids = set(prior_executed_action_ids)
    executed_order_ids = set(prior_executed_order_ids)
    executed_invocation_ids = set(prior_episode_state.executed_invocation_ids) if prior_episode_state else set()
    if (
        any(action.action_id in executed_action_ids for action in action_tuple)
        or any(invocation_id in executed_invocation_ids for invocation_id in invocation_ids)
        or any(order_id in executed_order_ids for order_id in order_ids)
    ):
        raise ValueError("REPLAYED_ACTION_OR_ORDER_REJECTED")
    peer_pairs: dict[str, CandidateAction] = {}
    for action in action_tuple:
        if action.liquidity_mode is LiquidityMode.PEER_TO_PEER_TRANSFER and action.peer_transfer_id is not None:
            candidates = [
                other for other in action_tuple
                if other.peer_transfer_id == action.peer_transfer_id and other.action_id != action.action_id
            ]
            if len(candidates) == 1:
                peer_pairs[action.action_id] = candidates[0]
    peer_outcomes: dict[str, SyntheticMatchOutcome] = {}
    peer_failure_reasons: dict[str, Tuple[str, ...]] = {}
    external_flows: list[ExternalLiquidityFlowEvent] = []

    for ordinal, action in enumerate(sorted(action_tuple, key=lambda item: item.arrival_sequence), start=len(prior_events) + 1):
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
            executed_action_ids.add(action.action_id)
            executed_invocation_ids.add(action.effective_invocation_id)
            continue
        if action.label is ActionLabel.BLOCKED:
            events.append(_blocked_event(run_id, ordinal, action, ("DECLARED_BLOCKED_ACTION",), owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            executed_action_ids.add(action.action_id)
            executed_invocation_ids.add(action.effective_invocation_id)
            continue
        if action.requires_complete_information and agent.information.unknowns:
            events.append(_abstain_event(run_id, ordinal, action, "INCOMPLETE_INFORMATION", owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            executed_action_ids.add(action.action_id)
            executed_invocation_ids.add(action.effective_invocation_id)
            continue
        if action.conflict_key and action.conflict_transition in (ConflictTransition.RELEASE, ConflictTransition.EXPIRE):
            if action.conflict_key not in claimed_conflicts:
                events.append(_blocked_event(run_id, ordinal, action, ("CONFLICT_RESOURCE_NOT_CLAIMED",), owner_hash, system_before))
                known_parent_ids.add(events[-1].event_id)
                continue
            claim_event_id = claimed_conflicts[action.conflict_key]
            claim_event = next((event for event in tuple(prior_events) + tuple(events) if event.event_id == claim_event_id), None)
            if claim_event is None or claim_event.agent_id != action.agent_id:
                events.append(_blocked_event(run_id, ordinal, action, ("CONFLICT_RESOURCE_NOT_OWNED",), owner_hash, system_before))
                known_parent_ids.add(events[-1].event_id)
                continue
            del claimed_conflicts[action.conflict_key]
            event_id = _event_id(run_id, ordinal, action, "CONFLICT_RESOURCE_" + action.conflict_transition.value.upper(), (), owner_hash, owner_hash)
            system_after = _system_hash(portfolios, market, claimed_conflicts, prior_ids + tuple(event.event_id for event in events) + (event_id,))
            events.append(LedgerEvent(
                event_id, ordinal, action.agent_id, action.action_id, action.label, True,
                "CONFLICT_RESOURCE_" + action.conflict_transition.value.upper(), 0, (),
                tuple(sorted(action.evidence_refs)), tuple(sorted(action.causal_parent_event_ids)),
                owner_hash, owner_hash, system_before, system_after, action.effective_invocation_id,
                action.liquidity_mode, action.conflict_transition, action.counterparty_agent_id, action.peer_transfer_id,
            ))
            known_parent_ids.add(events[-1].event_id)
            executed_action_ids.add(action.action_id); executed_invocation_ids.add(action.effective_invocation_id)
            continue
        if action.order is None:
            events.append(_blocked_event(run_id, ordinal, action, ("MISSING_SYNTHETIC_ORDER",), owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        if action.conflict_key and action.conflict_key in claimed_conflicts:
            events.append(_blocked_event(run_id, ordinal, action, ("CONFLICT_RESOURCE_ALREADY_CLAIMED",), owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        if action.action_id in peer_failure_reasons:
            events.append(_blocked_event(run_id, ordinal, action, peer_failure_reasons[action.action_id], owner_hash, system_before))
            known_parent_ids.add(events[-1].event_id)
            continue
        if action.liquidity_mode is LiquidityMode.PEER_TO_PEER_TRANSFER and action.action_id not in peer_outcomes:
            counterpart = peer_pairs.get(action.action_id)
            counterpart_owner = portfolios.get(counterpart.agent_id) if counterpart else None
            if (
                counterpart is None
                or counterpart_owner is None
                or counterpart.action_id in invalid_actions
                or counterpart.agent_id in invalid_agents
                or counterpart.label in (ActionLabel.ABSTAIN, ActionLabel.BLOCKED)
                or counterpart.requires_complete_information and agent_by_id[counterpart.agent_id].information.unknowns
            ):
                peer_failure_reasons[action.action_id] = ("UNMATCHED_OR_INFEASIBLE_PEER_TRANSFER",)
                if counterpart is not None:
                    peer_failure_reasons[counterpart.action_id] = ("UNMATCHED_OR_INFEASIBLE_PEER_TRANSFER",)
                events.append(_blocked_event(run_id, ordinal, action, peer_failure_reasons[action.action_id], owner_hash, system_before))
                known_parent_ids.add(events[-1].event_id)
                continue
            own_outcome = reduce_order(market, owner.final_inventory, action.order)
            counterpart_outcome = reduce_order(market, counterpart_owner.final_inventory, counterpart.order)
            if (
                own_outcome.status is OutcomeStatus.INVALID_OR_BLOCKED
                or counterpart_outcome.status is OutcomeStatus.INVALID_OR_BLOCKED
                or own_outcome.filled_quantity != counterpart_outcome.filled_quantity
            ):
                peer_failure_reasons[action.action_id] = ("PEER_TRANSFER_OUTCOME_MISMATCH",)
                peer_failure_reasons[counterpart.action_id] = ("PEER_TRANSFER_OUTCOME_MISMATCH",)
                events.append(_blocked_event(run_id, ordinal, action, peer_failure_reasons[action.action_id], owner_hash, system_before))
                known_parent_ids.add(events[-1].event_id)
                continue
            peer_outcomes[action.action_id] = own_outcome
            peer_outcomes[counterpart.action_id] = counterpart_outcome
        outcome: SyntheticMatchOutcome = peer_outcomes.pop(action.action_id, None) or reduce_order(market, owner.final_inventory, action.order)
        accepted = outcome.status is not OutcomeStatus.INVALID_OR_BLOCKED
        next_inventory = outcome.inventory
        next_owner_hash = _portfolio_hash(action.agent_id, next_inventory)
        next_portfolio = AgentPortfolioState(action.agent_id, owner.initial_inventory, next_inventory, owner.pre_state_hash,
                                             next_owner_hash, owner.net_filled_quantity + (outcome.filled_quantity if action.order.side.value == "BUY" else -outcome.filled_quantity))
        portfolios[action.agent_id] = next_portfolio
        provisional_id = _event_id(run_id, ordinal, action, outcome.status.value, outcome.reason_codes, owner_hash, next_owner_hash)
        if accepted and action.conflict_key and action.conflict_transition is ConflictTransition.CLAIM:
            claimed_conflicts[action.conflict_key] = provisional_id
        system_after = _system_hash(portfolios, market, claimed_conflicts, prior_ids + tuple(event.event_id for event in events) + (provisional_id,))
        event = LedgerEvent(provisional_id, ordinal, action.agent_id, action.action_id,
                            action.label if accepted else ActionLabel.BLOCKED, accepted, outcome.status.value,
                            outcome.filled_quantity, tuple(outcome.reason_codes), tuple(sorted(action.evidence_refs)),
                             tuple(sorted(action.causal_parent_event_ids)), owner_hash, next_owner_hash, system_before, system_after,
                              action.effective_invocation_id, action.liquidity_mode, action.conflict_transition,
                              action.counterparty_agent_id, action.peer_transfer_id)
        events.append(event)
        if accepted and action.liquidity_mode is LiquidityMode.EXTERNAL_SYNTHETIC_LIQUIDITY:
            external_flows.append(_flow_for_event(event, action))
        known_parent_ids.add(event.event_id)
        executed_action_ids.add(action.action_id)
        executed_invocation_ids.add(action.effective_invocation_id)
        executed_order_ids.add(action.order.order_id)
    ordered_portfolios = tuple(portfolios[agent_id] for agent_id in sorted(portfolios))
    shared_hash = _sha({"market": market, "claims": sorted(claimed_conflicts.items())})
    shared = SharedMarketState(market, tuple(sorted(claimed_conflicts)), tuple(sorted(claimed_conflicts.items())), shared_hash)
    ledger_hash = _sha([event for event in events])
    total_hash = _system_hash(portfolios, market, claimed_conflicts, prior_ids + tuple(event.event_id for event in events))
    episode_agents = _agents_from_portfolios(agent_tuple, ordered_portfolios)
    initial_agents = prior_episode_state.initial_agents if prior_episode_state else agent_tuple
    action_registry = _merge_action_registry(prior_episode_state.action_registry if prior_episode_state else (), action_tuple)
    all_flows = tuple(prior_episode_state.external_liquidity_flows if prior_episode_state else ()) + tuple(external_flows)
    all_events = tuple(prior_events) + tuple(events)
    step_index = (prior_episode_state.step_index + 1) if prior_episode_state else 1
    episode = EpisodeState(
        step_index, episode_agents, shared,
        tuple(sorted(executed_action_ids)), tuple(sorted(executed_order_ids)), tuple(sorted(executed_invocation_ids)),
        all_events, initial_agents, action_registry, all_flows,
        _episode_state_hash(
            step_index=step_index, initial_agents=initial_agents, current_agents=episode_agents,
            shared_market_state=shared, executed_action_ids=tuple(sorted(executed_action_ids)),
            executed_order_ids=tuple(sorted(executed_order_ids)), executed_invocation_ids=tuple(sorted(executed_invocation_ids)),
            event_dag=all_events, action_registry=action_registry, external_liquidity_flows=all_flows,
        ),
    )
    return GameRun(run_id, tuple(events), ordered_portfolios, shared, ledger_hash, total_hash, prior_ids,
                   tuple(sorted(executed_action_ids)), tuple(sorted(executed_order_ids)), action_tuple, episode)


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
        step_actions = tuple(
            replace(action, label=ActionLabel.ABSTAIN, order=None,
                    causal_parent_event_ids=action.causal_parent_event_ids or inherited_parent)
            for action in current_actions if action.action_id == target_id
        )
        prior_run = runs[-1] if runs else None
        run = arbitrate(
            run_id + f":step:{index}", market, current_agents, step_actions,
            prior_episode_state=prior_run.episode_state if prior_run else None,
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
    """True only for closed peer-ledger runs; external synthetic flows are accounted, not conserved."""
    if not isinstance(initial_agents, (tuple, list)):
        return False
    if not isinstance(result.episode_state, EpisodeState) or not verify_episode_ledger(result.episode_state).valid:
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
            if action.liquidity_mode is LiquidityMode.EXTERNAL_SYNTHETIC_LIQUIDITY:
                return False
        elif event.filled_quantity != 0:
            return False
    return all(
        initial_by_id.get(portfolio.agent_id) == portfolio.initial_inventory
        and _inventory_quantity(portfolio.final_inventory) - _inventory_quantity(portfolio.initial_inventory) == recomputed.get(portfolio.agent_id)
        for portfolio in result.final_agent_portfolios
    )


def total_system_accounted(initial_agents: Sequence[AgentState], result: GameRun) -> bool:
    """Verify all local inventory changes have an explicit external or matched peer explanation."""
    if not isinstance(result.episode_state, EpisodeState):
        return False
    if not verify_episode_ledger(result.episode_state).valid:
        return False
    initial_total = sum(_inventory_quantity(agent.inventory) for agent in initial_agents if isinstance(agent, AgentState))
    final_total = sum(_inventory_quantity(state.final_inventory) for state in result.final_agent_portfolios)
    external_delta = sum(flow.agent_inventory_delta for flow in result.episode_state.external_liquidity_flows)
    return final_total == initial_total + external_delta


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
