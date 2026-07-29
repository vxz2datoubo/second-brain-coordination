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
    InformationSet,
    InventoryState,
    MatchMode,
    MarketState,
    OrderSide,
    OutcomeStatus,
    SecurityStatus,
    SyntheticMatchOutcome,
    SyntheticLot,
    SyntheticOrder,
    SyntheticRuleSnapshot,
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
    # Resolved by arbitration and then frozen in the episode action registry.
    scheduled_step_index: Optional[int] = None

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
    # This is bound to the immutable step schedule and event ID, not trusted alone.
    step_index: int = 0


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
    root_run_id: str = ""
    episode_id: str = ""
    step_boundaries: Tuple["EpisodeStepBoundary", ...] = ()


@dataclass(frozen=True)
class EpisodeStepBoundary:
    """Immutable schedule: one arbitration call appends exactly one boundary."""

    step_index: int
    action_ids: Tuple[str, ...]


@dataclass(frozen=True)
class EpisodeLedgerVerification:
    valid: bool
    reason_codes: Tuple[str, ...]
    reconstructed_state_hash: str


@dataclass(frozen=True)
class _PeerSettlementPlan:
    """One all-or-nothing synthetic peer settlement over one shared pre-state."""

    transfer_id: str
    actions: Tuple[CandidateAction, CandidateAction]
    commit: bool
    outcomes: Tuple[SyntheticMatchOutcome, SyntheticMatchOutcome] = ()
    reason_codes: Tuple[str, ...] = ()

    def outcome_for(self, action_id: str) -> SyntheticMatchOutcome:
        for action, outcome in zip(self.actions, self.outcomes):
            if action.action_id == action_id:
                return outcome
        raise KeyError("UNKNOWN_PEER_SETTLEMENT_ACTION")


def verify_episode_ledger(episode: object) -> EpisodeLedgerVerification:
    """Rebuild every transition from frozen inputs; stored events are comparisons only."""
    structure_reason = _episode_structure_reason(episode)
    if structure_reason:
        return EpisodeLedgerVerification(False, (structure_reason,), "")
    assert isinstance(episode, EpisodeState)
    reasons: list[str] = []

    if len({agent.agent_id for agent in episode.initial_agents}) != len(episode.initial_agents):
        reasons.append("DUPLICATE_INITIAL_AGENT_ID")
    if episode.episode_id != _episode_id(episode.root_run_id, episode.initial_agents, episode.shared_market_state.market):
        reasons.append("EPISODE_ID_RECONSTRUCTION_MISMATCH")
    registry = {action.action_id: action for action in episode.action_registry}
    if len(registry) != len(episode.action_registry):
        reasons.append("DUPLICATE_ACTION_REGISTRY_ID")

    boundary_action_ids: list[str] = []
    for expected_step, boundary in enumerate(episode.step_boundaries, start=1):
        if boundary.step_index != expected_step:
            reasons.append("NON_SEQUENTIAL_STEP_BOUNDARY")
        if len(boundary.action_ids) != len(set(boundary.action_ids)):
            reasons.append("DUPLICATE_BOUNDARY_ACTION_ID")
        if any(action_id not in registry for action_id in boundary.action_ids):
            reasons.append("UNKNOWN_BOUNDARY_ACTION_ID")
            continue
        boundary_actions = tuple(registry[action_id] for action_id in boundary.action_ids)
        if any(action.scheduled_step_index != boundary.step_index for action in boundary_actions):
            reasons.append("ACTION_STEP_BOUNDARY_MISMATCH")
        expected_order = tuple(action.action_id for action in sorted(boundary_actions, key=lambda action: action.arrival_sequence))
        if boundary.action_ids != expected_order:
            reasons.append("NONDETERMINISTIC_BOUNDARY_ACTION_ORDER")
        boundary_action_ids.extend(boundary.action_ids)
    if tuple(sorted(boundary_action_ids)) != tuple(sorted(registry)):
        reasons.append("ACTION_REGISTRY_BOUNDARY_COVERAGE_MISMATCH")
    if len(boundary_action_ids) != len(set(boundary_action_ids)):
        reasons.append("ACTION_REUSED_ACROSS_STEP_BOUNDARIES")
    if episode.step_index != len(episode.step_boundaries):
        reasons.append("EPISODE_STEP_BOUNDARY_MISMATCH")
    if reasons:
        return EpisodeLedgerVerification(False, tuple(sorted(set(reasons))), "")
    peer_group_reasons = _peer_group_invariant_reasons(episode)

    reconstructed: Optional[EpisodeState] = None
    try:
        for boundary in episode.step_boundaries:
            actions = tuple(registry[action_id] for action_id in boundary.action_ids)
            rebuilt = _arbitrate_internal(
                episode.root_run_id,
                episode.shared_market_state.market,
                episode.initial_agents,
                actions,
                prior_episode_state=reconstructed,
                _verify_prior=False,
            )
            reconstructed = rebuilt.episode_state
    except (ValueError, KeyError):
        return EpisodeLedgerVerification(False, ("EPISODE_RECONSTRUCTION_FAILED",), "")
    if reconstructed is None:
        return EpisodeLedgerVerification(False, ("MISSING_STEP_BOUNDARY",), "")

    event_fields = (
        "event_id", "ordinal", "agent_id", "action_id", "label", "accepted", "outcome_status",
        "filled_quantity", "rejected_reason_codes", "cause_refs", "causal_parent_event_ids",
        "owner_pre_state_hash", "owner_post_state_hash", "system_pre_state_hash", "system_post_state_hash",
        "invocation_id", "liquidity_mode", "conflict_transition", "counterparty_agent_id",
        "peer_transfer_id", "step_index",
    )
    if len(episode.event_dag) != len(reconstructed.event_dag):
        reasons.append("EVENT_DAG_LENGTH_MISMATCH")
    for stored, expected in zip(episode.event_dag, reconstructed.event_dag):
        for field_name in event_fields:
            if getattr(stored, field_name) != getattr(expected, field_name):
                reasons.append("EVENT_" + field_name.upper() + "_MISMATCH")
    state_fields = (
        "step_index", "current_agents", "shared_market_state", "executed_action_ids",
        "executed_order_ids", "executed_invocation_ids", "action_registry",
        "external_liquidity_flows", "root_run_id", "episode_id", "step_boundaries",
    )
    for field_name in state_fields:
        if getattr(episode, field_name) != getattr(reconstructed, field_name):
            reasons.append("EPISODE_" + field_name.upper() + "_MISMATCH")
            if field_name in ("current_agents", "shared_market_state"):
                reasons.append("FORGED_STORED_EPISODE_STATE")
            if field_name == "external_liquidity_flows":
                reasons.append("EXTERNAL_FLOW_LEDGER_MISMATCH")
    for stored, expected in zip(episode.event_dag, reconstructed.event_dag):
        if stored.filled_quantity != expected.filled_quantity or stored.outcome_status != expected.outcome_status:
            reasons.append("FORGED_EVENT_OUTCOME")
    reasons.extend(peer_group_reasons)
    if episode.state_hash != reconstructed.state_hash:
        reasons.append("EPISODE_STATE_HASH_MISMATCH")
    return EpisodeLedgerVerification(not reasons, tuple(sorted(set(reasons))), reconstructed.state_hash)


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and abs(value) <= MAX_FEATURE_MAGNITUDE


def _bounded_text(value: object, *, allow_empty: bool = False) -> bool:
    return isinstance(value, str) and len(value) <= MAX_IDENTIFIER_LENGTH and (allow_empty or bool(value))


def _typed_tuple(value: object, expected_type: type, limit: int) -> bool:
    return isinstance(value, tuple) and bool(value) and len(value) <= limit and all(isinstance(item, expected_type) for item in value)


def _valid_refs(value: object, *, allow_empty: bool = False, limit: int = MAX_REFERENCE_COUNT) -> bool:
    return isinstance(value, tuple) and len(value) <= limit and (allow_empty or bool(value)) and all(_bounded_text(item) for item in value)


def _safe_int(value: object, *, minimum: int = -MAX_FEATURE_MAGNITUDE) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and minimum <= value <= MAX_FEATURE_MAGNITUDE


def _safe_optional_int(value: object, *, minimum: int = -MAX_FEATURE_MAGNITUDE) -> bool:
    return value is None or _safe_int(value, minimum=minimum)


def _safe_optional_text(value: object) -> bool:
    return value is None or _bounded_text(value)


def _safe_enum_text_or_none(value: object, enum_type: type[Enum]) -> bool:
    return value is None or isinstance(value, enum_type) or _bounded_text(value)


def _safe_text_tuple(value: object, *, limit: int = MAX_REFERENCE_COUNT) -> bool:
    return isinstance(value, tuple) and len(value) <= limit and all(_bounded_text(item) for item in value)


def _market_structure_reason(market: object) -> Optional[str]:
    """Validate only safe field shapes before D1 or hashing can consume them."""
    if not isinstance(market, MarketState):
        return "INVALID_MARKET_STATE"
    if not _safe_enum_text_or_none(market.phase, Enum):
        return "INVALID_MARKET_PHASE_STRUCTURE"
    if not _safe_optional_text(market.trade_date):
        return "INVALID_MARKET_DATE_STRUCTURE"
    if not _safe_enum_text_or_none(market.security_status, SecurityStatus):
        return "INVALID_MARKET_SECURITY_STATUS_STRUCTURE"
    if market.information is not None:
        if not isinstance(market.information, InformationSet):
            return "INVALID_MARKET_INFORMATION_STRUCTURE"
        info = market.information
        if not _safe_optional_text(info.source_capability) or not _safe_optional_int(info.available_at_ns, minimum=0):
            return "INVALID_MARKET_INFORMATION_FIELD"
        if not _safe_optional_int(info.source_sequence, minimum=0):
            return "INVALID_MARKET_INFORMATION_FIELD"
    if market.rule_snapshot is not None:
        if not isinstance(market.rule_snapshot, SyntheticRuleSnapshot):
            return "INVALID_RULE_SNAPSHOT_STRUCTURE"
        rule = market.rule_snapshot
        if not all(_safe_optional_text(value) for value in (
            rule.snapshot_id, rule.exchange, rule.board, rule.trade_date,
            rule.price_unit, rule.quantity_unit, rule.suspension_behavior, rule.version,
        )):
            return "INVALID_RULE_SNAPSHOT_FIELD"
        if not _safe_optional_int(rule.price_limit_low) or not _safe_optional_int(rule.price_limit_high):
            return "INVALID_RULE_SNAPSHOT_FIELD"
        if not isinstance(rule.t_plus_one_enabled, bool):
            return "INVALID_RULE_SNAPSHOT_FIELD"
        if not isinstance(rule.permitted_phases, tuple) or len(rule.permitted_phases) > MAX_REFERENCE_COUNT:
            return "INVALID_RULE_SNAPSHOT_FIELD"
        if not all(_safe_enum_text_or_none(phase, Enum) for phase in rule.permitted_phases):
            return "INVALID_RULE_SNAPSHOT_FIELD"
    return None


def _inventory_structure_reason(inventory: object) -> Optional[str]:
    if not isinstance(inventory, InventoryState):
        return "INVALID_INVENTORY_STRUCTURE"
    if not isinstance(inventory.lots, tuple) or len(inventory.lots) > MAX_EVENT_COUNT:
        return "INVALID_INVENTORY_LOT_COLLECTION"
    if not _safe_optional_int(inventory.pending_buy_quantity, minimum=0) or not _safe_optional_int(inventory.pending_sell_quantity, minimum=0):
        return "INVALID_INVENTORY_PENDING_QUANTITY"
    if not _safe_optional_text(inventory.settled_trade_date):
        return "INVALID_INVENTORY_SETTLEMENT_DATE"
    for lot in inventory.lots:
        if not isinstance(lot, SyntheticLot):
            return "INVALID_INVENTORY_LOT"
        if not _safe_optional_text(lot.lot_id) or not _safe_optional_text(lot.acquired_trade_date):
            return "INVALID_INVENTORY_LOT_FIELD"
        if not _safe_optional_int(lot.quantity, minimum=0) or not _safe_optional_int(lot.locked_quantity, minimum=0):
            return "INVALID_INVENTORY_LOT_FIELD"
    return None


def _order_structure_reason(order: object) -> Optional[str]:
    if not isinstance(order, SyntheticOrder):
        return "INVALID_SYNTHETIC_ORDER_STRUCTURE"
    if not _safe_optional_text(order.order_id):
        return "INVALID_ORDER_ID_STRUCTURE"
    if not _safe_enum_text_or_none(order.side, OrderSide):
        return "INVALID_ORDER_SIDE_STRUCTURE"
    if not _safe_optional_int(order.quantity, minimum=0) or not _safe_optional_int(order.limit_price):
        return "INVALID_ORDER_NUMERIC_STRUCTURE"
    if not _safe_optional_int(order.available_at_ns, minimum=0):
        return "INVALID_ORDER_TIME_STRUCTURE"
    if not _safe_enum_text_or_none(order.match_mode, MatchMode):
        return "INVALID_ORDER_MATCH_MODE_STRUCTURE"
    if not _safe_optional_int(order.partial_fill_quantity, minimum=0):
        return "INVALID_ORDER_PARTIAL_FILL_STRUCTURE"
    return None


def _agent_structure_reason(agent: object) -> Optional[str]:
    if not isinstance(agent, AgentState):
        return "INVALID_AGENT_OBJECT"
    if not _safe_optional_text(agent.agent_id):
        return "INVALID_AGENT_ID_STRUCTURE"
    if not isinstance(agent.posterior, HiddenTypePosterior):
        return "INVALID_AGENT_POSTERIOR_STRUCTURE"
    if not isinstance(agent.posterior.hypotheses, tuple) or len(agent.posterior.hypotheses) > MAX_REFERENCE_COUNT:
        return "INVALID_AGENT_POSTERIOR_STRUCTURE"
    for hypothesis in agent.posterior.hypotheses:
        if not isinstance(hypothesis, ParticipantArchetypeHypothesis):
            return "INVALID_AGENT_POSTERIOR_STRUCTURE"
        if not _safe_enum_text_or_none(hypothesis.subtype, ParticipantSubtype):
            return "INVALID_AGENT_POSTERIOR_FIELD"
        if not _finite_number(hypothesis.normalized_weight):
            return "INVALID_AGENT_POSTERIOR_FIELD"
        if not _safe_text_tuple(hypothesis.evidence_refs) or not _safe_text_tuple(hypothesis.counterevidence_refs):
            return "INVALID_AGENT_POSTERIOR_FIELD"
        if not _safe_optional_text(hypothesis.alternative_explanation):
            return "INVALID_AGENT_POSTERIOR_FIELD"
    if not _safe_optional_text(agent.posterior.status):
        return "INVALID_AGENT_POSTERIOR_FIELD"
    if not isinstance(agent.information, AgentInformationSet):
        return "INVALID_AGENT_INFORMATION_STRUCTURE"
    info = agent.information
    if not _safe_optional_int(info.available_at_ns, minimum=0):
        return "INVALID_AGENT_INFORMATION_FIELD"
    if not all(_safe_text_tuple(value) for value in (info.observable_refs, info.unknowns, info.private_observable_refs)):
        return "INVALID_AGENT_INFORMATION_FIELD"
    if not _safe_optional_text(info.source_capability):
        return "INVALID_AGENT_INFORMATION_FIELD"
    return _inventory_structure_reason(agent.inventory)


def _action_structure_reason(action: object) -> Optional[str]:
    if not isinstance(action, CandidateAction):
        return "INVALID_ACTION_OBJECT"
    if not _safe_optional_text(action.action_id) or not _safe_optional_text(action.agent_id):
        return "INVALID_ACTION_ID_STRUCTURE"
    if not _safe_enum_text_or_none(action.label, ActionLabel):
        return "INVALID_ACTION_LABEL_STRUCTURE"
    if action.order is not None:
        order_reason = _order_structure_reason(action.order)
        if order_reason:
            return order_reason
    if not _safe_text_tuple(action.assumption_ids) or not _safe_text_tuple(action.evidence_refs):
        return "INVALID_ACTION_REFERENCE_STRUCTURE"
    if not _safe_optional_text(action.conflict_key) or not isinstance(action.requires_complete_information, bool):
        return "INVALID_ACTION_CONFLICT_STRUCTURE"
    if not _safe_text_tuple(action.causal_parent_event_ids, limit=MAX_CAUSAL_PARENT_COUNT):
        return "INVALID_ACTION_CAUSAL_STRUCTURE"
    if not _safe_int(action.arrival_sequence, minimum=0):
        return "INVALID_ARRIVAL_SEQUENCE"
    if not _safe_optional_text(action.invocation_id):
        return "INVALID_INVOCATION_ID_STRUCTURE"
    if not _safe_enum_text_or_none(action.conflict_transition, ConflictTransition):
        return "INVALID_CONFLICT_TRANSITION_STRUCTURE"
    if not _safe_enum_text_or_none(action.liquidity_mode, LiquidityMode):
        return "INVALID_LIQUIDITY_MODE_STRUCTURE"
    if not _safe_optional_text(action.counterparty_agent_id) or not _safe_optional_text(action.peer_transfer_id):
        return "INVALID_PEER_IDENTIFIER_STRUCTURE"
    if not _safe_optional_int(action.scheduled_step_index, minimum=1):
        return "INVALID_SCHEDULED_STEP_STRUCTURE"
    return None


def _ledger_event_structure_reason(event: object) -> Optional[str]:
    if not isinstance(event, LedgerEvent):
        return "INVALID_LEDGER_EVENT_OBJECT"
    if not all(_safe_optional_text(value) for value in (
        event.event_id, event.agent_id, event.action_id, event.owner_pre_state_hash,
        event.owner_post_state_hash, event.system_pre_state_hash, event.system_post_state_hash,
        event.invocation_id, event.counterparty_agent_id, event.peer_transfer_id,
    )):
        return "INVALID_LEDGER_EVENT_IDENTIFIER_STRUCTURE"
    if not _safe_int(event.ordinal, minimum=1) or not _safe_int(event.filled_quantity):
        return "INVALID_LEDGER_EVENT_NUMERIC_STRUCTURE"
    if not isinstance(event.accepted, bool):
        return "INVALID_LEDGER_EVENT_ACCEPTED_STRUCTURE"
    if not _safe_enum_text_or_none(event.label, ActionLabel) or not _safe_optional_text(event.outcome_status):
        return "INVALID_LEDGER_EVENT_SEMANTIC_STRUCTURE"
    if not all(_safe_text_tuple(value) for value in (
        event.rejected_reason_codes, event.cause_refs, event.causal_parent_event_ids,
    )):
        return "INVALID_LEDGER_EVENT_REFERENCE_STRUCTURE"
    if not _safe_enum_text_or_none(event.liquidity_mode, LiquidityMode):
        return "INVALID_LEDGER_EVENT_LIQUIDITY_STRUCTURE"
    if not _safe_enum_text_or_none(event.conflict_transition, ConflictTransition):
        return "INVALID_LEDGER_EVENT_CONFLICT_STRUCTURE"
    if not _safe_int(event.step_index, minimum=1):
        return "INVALID_LEDGER_EVENT_STEP_STRUCTURE"
    return None


def _flow_structure_reason(flow: object) -> Optional[str]:
    if not isinstance(flow, ExternalLiquidityFlowEvent):
        return "INVALID_EXTERNAL_FLOW_OBJECT"
    if not all(_safe_optional_text(value) for value in (flow.flow_id, flow.ledger_event_id, flow.agent_id)):
        return "INVALID_EXTERNAL_FLOW_IDENTIFIER_STRUCTURE"
    if not _safe_int(flow.agent_inventory_delta) or not _safe_int(flow.external_inventory_delta):
        return "INVALID_EXTERNAL_FLOW_DELTA_STRUCTURE"
    return None


def _shared_market_structure_reason(shared: object) -> Optional[str]:
    if not isinstance(shared, SharedMarketState):
        return "INVALID_SHARED_MARKET_STATE"
    market_reason = _market_structure_reason(shared.market)
    if market_reason:
        return market_reason
    if not _safe_text_tuple(shared.claimed_conflict_keys, limit=MAX_EVENT_COUNT):
        return "INVALID_SHARED_CLAIM_KEY_STRUCTURE"
    if not isinstance(shared.conflict_claim_event_ids, tuple) or len(shared.conflict_claim_event_ids) > MAX_EVENT_COUNT:
        return "INVALID_SHARED_CLAIM_MAP_STRUCTURE"
    for pair in shared.conflict_claim_event_ids:
        if not isinstance(pair, tuple) or len(pair) != 2 or not all(_bounded_text(item) for item in pair):
            return "INVALID_SHARED_CLAIM_MAP_STRUCTURE"
    if not _safe_optional_text(shared.state_hash) or not _safe_optional_text(shared.contract):
        return "INVALID_SHARED_MARKET_HASH_STRUCTURE"
    return None


def _boundary_structure_reason(boundary: object) -> Optional[str]:
    if not isinstance(boundary, EpisodeStepBoundary):
        return "INVALID_STEP_BOUNDARY_OBJECT"
    if not _safe_int(boundary.step_index, minimum=1):
        return "INVALID_STEP_BOUNDARY_INDEX"
    if not _safe_text_tuple(boundary.action_ids, limit=MAX_ACTION_COUNT):
        return "INVALID_STEP_BOUNDARY_ACTION_IDS"
    return None


def _episode_structure_reason(episode: object) -> Optional[str]:
    """Total, non-mutating preflight for the verifier's public trust boundary."""
    if not isinstance(episode, EpisodeState):
        return "INVALID_EPISODE_STATE"
    if not _bounded_text(episode.root_run_id) or not _bounded_text(episode.episode_id):
        return "MISSING_IMMUTABLE_EPISODE_IDENTITY"
    if not _safe_int(episode.step_index, minimum=0):
        return "INVALID_EPISODE_STEP_INDEX"
    shared_reason = _shared_market_structure_reason(episode.shared_market_state)
    if shared_reason:
        return shared_reason
    collections = (
        ("INVALID_INITIAL_AGENT_REGISTRY", episode.initial_agents, AgentState, False),
        ("INVALID_CURRENT_AGENT_REGISTRY", episode.current_agents, AgentState, False),
        ("INVALID_ACTION_REGISTRY", episode.action_registry, CandidateAction, False),
        ("INVALID_EVENT_DAG", episode.event_dag, LedgerEvent, False),
        # A fully matched peer transfer legitimately has no external flow.
        ("INVALID_EXTERNAL_FLOW_REGISTRY", episode.external_liquidity_flows, ExternalLiquidityFlowEvent, True),
        ("INVALID_STEP_BOUNDARY_REGISTRY", episode.step_boundaries, EpisodeStepBoundary, False),
    )
    for reason, value, expected_type, allow_empty in collections:
        if (
            not isinstance(value, tuple)
            or len(value) > MAX_EVENT_COUNT
            or (not allow_empty and not value)
            or not all(isinstance(item, expected_type) for item in value)
        ):
            return reason
    for identifiers in (episode.executed_action_ids, episode.executed_order_ids, episode.executed_invocation_ids):
        if not _safe_text_tuple(identifiers, limit=MAX_EVENT_COUNT):
            return "INVALID_EPISODE_EXECUTED_ID_REGISTRY"
    if not _bounded_text(episode.state_hash):
        return "INVALID_EPISODE_STATE_HASH_STRUCTURE"
    for agent in tuple(episode.initial_agents) + tuple(episode.current_agents):
        agent_reason = _agent_structure_reason(agent)
        if agent_reason:
            return agent_reason
    for action in episode.action_registry:
        action_reason = _action_structure_reason(action)
        if action_reason:
            return action_reason
    for event in episode.event_dag:
        event_reason = _ledger_event_structure_reason(event)
        if event_reason:
            return event_reason
    for flow in episode.external_liquidity_flows:
        flow_reason = _flow_structure_reason(flow)
        if flow_reason:
            return flow_reason
    for boundary in episode.step_boundaries:
        boundary_reason = _boundary_structure_reason(boundary)
        if boundary_reason:
            return boundary_reason
    return None


def _arbitration_structure_error(
    run_id: object,
    market: object,
    agents: object,
    actions: object,
    *,
    prior_events: object,
    prior_shared_market_state: object,
    prior_executed_action_ids: object,
    prior_executed_order_ids: object,
    prior_episode_state: object,
) -> Optional[str]:
    """Shared pre-event contract: never key, sort, or hash unproven nested values."""
    if not _bounded_text(run_id):
        return "INVALID_RUN_ID"
    market_reason = _market_structure_reason(market)
    if market_reason:
        return market_reason
    if not isinstance(agents, (tuple, list)) or not isinstance(actions, (tuple, list)):
        return "INVALID_TOP_LEVEL_COLLECTION"
    if not 1 <= len(agents) <= MAX_AGENT_COUNT:
        return "INVALID_AGENT_COUNT"
    if len(actions) > MAX_ACTION_COUNT:
        return "ACTION_LIMIT_EXCEEDED"
    if not isinstance(prior_events, (tuple, list)) or len(prior_events) > MAX_EVENT_COUNT:
        return "INVALID_PRIOR_EVENT_COLLECTION"
    if not isinstance(prior_executed_action_ids, (tuple, list)) or not isinstance(prior_executed_order_ids, (tuple, list)):
        return "INVALID_PRIOR_EXECUTION_COLLECTION"
    if not _safe_text_tuple(tuple(prior_executed_action_ids), limit=MAX_EVENT_COUNT) or not _safe_text_tuple(tuple(prior_executed_order_ids), limit=MAX_EVENT_COUNT):
        return "INVALID_PRIOR_EXECUTION_ID"
    for event in prior_events:
        event_reason = _ledger_event_structure_reason(event)
        if event_reason:
            return "INVALID_PRIOR_EVENT_COLLECTION"
    if prior_shared_market_state is not None:
        shared_reason = _shared_market_structure_reason(prior_shared_market_state)
        if shared_reason:
            return "INVALID_OR_CHANGED_PRIOR_SHARED_MARKET_STATE"
    if prior_episode_state is not None:
        episode_reason = _episode_structure_reason(prior_episode_state)
        if episode_reason:
            return "INVALID_PRIOR_EPISODE_STATE"
    for agent in agents:
        agent_reason = _agent_structure_reason(agent)
        if agent_reason:
            return agent_reason
    for action in actions:
        action_reason = _action_structure_reason(action)
        if action_reason:
            return action_reason
    return None


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


def _episode_id(root_run_id: str, initial_agents: Sequence[AgentState], market: MarketState) -> str:
    return _sha({"root_run_id": root_run_id, "initial_agents": tuple(initial_agents), "market": market})


def _event_id(
    episode_id: str,
    step_index: int,
    ordinal: int,
    action: CandidateAction,
    *,
    label: ActionLabel,
    accepted: bool,
    status: str,
    filled_quantity: int,
    reasons: Sequence[str],
    cause_refs: Sequence[str],
    causal_parent_event_ids: Sequence[str],
    owner_pre_hash: str,
    owner_post_hash: str,
) -> str:
    """Content-address every immutable action and reconstructed terminal semantic."""
    return _sha({
        "episode_id": episode_id,
        "step_index": step_index,
        "ordinal": ordinal,
        "action": action,
        "label": label,
        "accepted": accepted,
        "status": status,
        "filled_quantity": filled_quantity,
        "reasons": tuple(reasons),
        "cause_refs": tuple(cause_refs),
        "causal_parent_event_ids": tuple(causal_parent_event_ids),
        "owner_pre_hash": owner_pre_hash,
        "owner_post_hash": owner_post_hash,
    })


def _event_from_semantics(
    episode_id: str,
    step_index: int,
    ordinal: int,
    action: CandidateAction,
    *,
    label: ActionLabel,
    accepted: bool,
    outcome_status: str,
    filled_quantity: int,
    rejected_reason_codes: Sequence[str],
    owner_pre_state_hash: str,
    owner_post_state_hash: str,
    system_pre_state_hash: str,
    system_post_state_hash: str,
) -> LedgerEvent:
    cause_refs = tuple(sorted(action.evidence_refs))
    parents = tuple(sorted(action.causal_parent_event_ids))
    reasons = tuple(rejected_reason_codes)
    event_id = _event_id(
        episode_id, step_index, ordinal, action,
        label=label, accepted=accepted, status=outcome_status,
        filled_quantity=filled_quantity, reasons=reasons,
        cause_refs=cause_refs, causal_parent_event_ids=parents,
        owner_pre_hash=owner_pre_state_hash, owner_post_hash=owner_post_state_hash,
    )
    return LedgerEvent(
        event_id, ordinal, action.agent_id, action.action_id, label, accepted,
        outcome_status, filled_quantity, reasons, cause_refs, parents,
        owner_pre_state_hash, owner_post_state_hash, system_pre_state_hash,
        system_post_state_hash, action.effective_invocation_id, action.liquidity_mode,
        action.conflict_transition, action.counterparty_agent_id, action.peer_transfer_id,
        step_index,
    )


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
    if action.scheduled_step_index is not None and (
        not isinstance(action.scheduled_step_index, int)
        or isinstance(action.scheduled_step_index, bool)
        or action.scheduled_step_index < 1
    ):
        return False, ("INVALID_SCHEDULED_STEP_INDEX",)
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
    if any(action.scheduled_step_index is None for action in merged):
        raise ValueError("UNRESOLVED_ACTION_STEP_BOUNDARY")
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
    root_run_id: str = "",
    episode_id: str = "",
    step_boundaries: Sequence[EpisodeStepBoundary] = (),
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
        "root_run_id": root_run_id,
        "episode_id": episode_id,
        "step_boundaries": tuple(step_boundaries),
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
            and isinstance(first.order, SyntheticOrder)
            and isinstance(second.order, SyntheticOrder)
            and first.order.side != second.order.side
            and first.order.quantity == second.order.quantity
            and second.arrival_sequence == first.arrival_sequence + 1
        )
        if not valid:
            reasons[first.action_id] = ("INVALID_PEER_TRANSFER_PAIR",)
            reasons[second.action_id] = ("INVALID_PEER_TRANSFER_PAIR",)
    return reasons


def _peer_declaration_failure_map(actions: Sequence[CandidateAction]) -> dict[str, Tuple[str, ...]]:
    """Classify malformed peer declarations before any settlement can occur.

    A declaration failure is distinct from a structurally valid peer pair that
    later aborts its shared settlement plan.  The distinction lets the
    verifier accept an honestly emitted, zero-mutation declaration abort while
    retaining the normal strict checks for forged or truncated valid pairs.
    """
    failure_sets: dict[str, set[str]] = {}

    def add_failure(action_id: str, reason: str) -> None:
        failure_sets.setdefault(action_id, set()).add(reason)

    for action in actions:
        if action.liquidity_mode is not LiquidityMode.PEER_TO_PEER_TRANSFER:
            continue
        if action.peer_transfer_id is None:
            add_failure(action.action_id, "PEER_TRANSFER_REQUIRES_TRANSFER_ID")
        elif not _bounded_text(action.peer_transfer_id):
            add_failure(action.action_id, "INVALID_PEER_TRANSFER_ID")
        if action.counterparty_agent_id is None:
            add_failure(action.action_id, "PEER_TRANSFER_REQUIRES_COUNTERPARTY")
        elif not _bounded_text(action.counterparty_agent_id):
            add_failure(action.action_id, "INVALID_COUNTERPARTY_AGENT_ID")
        if not isinstance(action.order, SyntheticOrder):
            add_failure(action.action_id, "INVALID_SYNTHETIC_ORDER")

    # A malformed group remains visible to every member while each action also
    # retains its own precise declaration fault.  This keeps a deterministic
    # DECLARATION_ABORT explainable without turning a pair-shape error into a
    # false reciprocal settlement.
    for action_id, reasons in _validate_peer_transfer_pairs(actions).items():
        for reason in reasons:
            add_failure(action_id, reason)

    return {
        action_id: tuple(sorted(reasons))
        for action_id, reasons in failure_sets.items()
    }


def _valid_peer_pair_map(actions: Sequence[CandidateAction]) -> dict[str, Tuple[CandidateAction, CandidateAction]]:
    """Return only structurally valid, same-step candidate pairs.

    Malformed declarations deliberately remain ordinary fail-closed actions.  A
    valid pair, by contrast, is required to pass through the atomic plan below.
    """
    shape_failures = _peer_declaration_failure_map(actions)
    grouped: dict[str, list[CandidateAction]] = {}
    for action in actions:
        if action.liquidity_mode is LiquidityMode.PEER_TO_PEER_TRANSFER and action.peer_transfer_id is not None:
            grouped.setdefault(action.peer_transfer_id, []).append(action)
    pairs: dict[str, Tuple[CandidateAction, CandidateAction]] = {}
    for transfer_id, group in grouped.items():
        if len(group) != 2 or any(action.action_id in shape_failures for action in group):
            continue
        first, second = tuple(sorted(group, key=lambda action: action.arrival_sequence))
        pairs[first.action_id] = (first, second)
        pairs[second.action_id] = (first, second)
    return pairs


def _peer_abort_reasons(*reason_groups: Sequence[str] | str) -> Tuple[str, ...]:
    reasons = {"PEER_GROUP_ABORTED"}
    for group in reason_groups:
        if isinstance(group, str):
            reasons.add(group)
        else:
            reasons.update(group)
    return tuple(sorted(reasons))


def _plan_peer_settlement(
    pair: Tuple[CandidateAction, CandidateAction],
    *,
    market: MarketState,
    agents_by_id: dict[str, AgentState],
    portfolios: dict[str, AgentPortfolioState],
    known_parent_ids: set[str],
    invalid_agents: dict[str, Tuple[str, ...]],
    invalid_actions: dict[str, Tuple[str, ...]],
) -> _PeerSettlementPlan:
    """Preflight both legs against one immutable shared state before mutation."""
    first, second = pair
    transfer_id = first.peer_transfer_id or second.peer_transfer_id or "UNKNOWN_PEER_TRANSFER"
    reasons: list[str] = []
    for action in pair:
        reasons.extend(invalid_actions.get(action.action_id, ()))
        if action.agent_id not in agents_by_id or action.agent_id not in portfolios:
            reasons.append("PEER_GROUP_UNKNOWN_AGENT")
        reasons.extend(invalid_agents.get(action.agent_id, ()))
        if action.label in (ActionLabel.ABSTAIN, ActionLabel.BLOCKED):
            reasons.append("PEER_GROUP_NONEXECUTABLE_ACTION")
        if action.order is None:
            reasons.append("PEER_GROUP_MISSING_SYNTHETIC_ORDER")
        if any(parent not in known_parent_ids for parent in action.causal_parent_event_ids):
            reasons.append("PEER_GROUP_UNKNOWN_OR_FORWARD_CAUSAL_PARENT")
        agent = agents_by_id.get(action.agent_id)
        if action.requires_complete_information and agent is not None and agent.information.unknowns:
            reasons.append("PEER_GROUP_INCOMPLETE_INFORMATION")
        # D2 has no atomic shared-resource transfer semantics yet.  Prohibit
        # every resource-affecting peer declaration before either leg mutates.
        if action.conflict_key is not None or action.conflict_transition in (ConflictTransition.RELEASE, ConflictTransition.EXPIRE):
            reasons.append("UNSUPPORTED_PEER_CONFLICT_RESOURCE")
    if reasons:
        return _PeerSettlementPlan(transfer_id, pair, False, (), _peer_abort_reasons(tuple(reasons)))

    first_owner, second_owner = portfolios[first.agent_id], portfolios[second.agent_id]
    first_outcome = reduce_order(market, first_owner.final_inventory, first.order)
    second_outcome = reduce_order(market, second_owner.final_inventory, second.order)
    outcomes = (first_outcome, second_outcome)
    if any(outcome.status in (OutcomeStatus.INVALID_OR_BLOCKED, OutcomeStatus.UNKNOWN_OUTCOME) for outcome in outcomes):
        details = tuple(sorted({reason for outcome in outcomes for reason in outcome.reason_codes}))
        return _PeerSettlementPlan(transfer_id, pair, False, (), _peer_abort_reasons("PEER_GROUP_ORDER_OUTCOME_INVALID", details))
    if first_outcome.filled_quantity != second_outcome.filled_quantity:
        return _PeerSettlementPlan(transfer_id, pair, False, (), _peer_abort_reasons("PEER_GROUP_OUTCOME_MISMATCH"))
    signed_first = first_outcome.filled_quantity if first.order.side.value == "BUY" else -first_outcome.filled_quantity
    signed_second = second_outcome.filled_quantity if second.order.side.value == "BUY" else -second_outcome.filled_quantity
    if signed_first + signed_second != 0:
        return _PeerSettlementPlan(transfer_id, pair, False, (), _peer_abort_reasons("PEER_GROUP_NONCOMPLEMENTARY_DELTA"))
    return _PeerSettlementPlan(transfer_id, pair, True, outcomes, ())


def _peer_group_invariant_reasons(episode: EpisodeState) -> Tuple[str, ...]:
    """Independently check closed-system peer semantics, not reducer agreement."""
    peer_actions = [
        action for action in episode.action_registry
        if action.liquidity_mode is LiquidityMode.PEER_TO_PEER_TRANSFER
    ]
    if not peer_actions:
        return ()
    declaration_failures = _peer_declaration_failure_map(peer_actions)
    groups: dict[str, list[CandidateAction]] = {}
    for action in peer_actions:
        group_id = action.peer_transfer_id
        if group_id is None:
            group_id = "__MISSING_PEER_TRANSFER_ID__:" + action.action_id
        groups.setdefault(group_id, []).append(action)
    reasons: set[str] = set()
    for _, group in groups.items():
        ordered_actions = tuple(sorted(group, key=lambda action: action.arrival_sequence))
        action_ids = {action.action_id for action in ordered_actions}
        transfer_id = ordered_actions[0].peer_transfer_id
        group_events = [
            event for event in episode.event_dag
            if event.action_id in action_ids or (
                transfer_id is not None and event.peer_transfer_id == transfer_id
            )
        ]
        declaration_abort_ids = {
            action.action_id for action in ordered_actions if action.action_id in declaration_failures
        }
        if declaration_abort_ids:
            event_by_action: dict[str, list[LedgerEvent]] = {action.action_id: [] for action in ordered_actions}
            for event in group_events:
                if event.action_id in event_by_action:
                    event_by_action[event.action_id].append(event)
                else:
                    reasons.add("PEER_DECLARATION_ABORT_EVENT_MEMBERSHIP_MISMATCH")
            if len(group_events) != len(ordered_actions) or any(len(items) != 1 for items in event_by_action.values()):
                reasons.add("PEER_DECLARATION_ABORT_EVENT_MEMBERSHIP_MISMATCH")
                continue
            ordered_events = tuple(event_by_action[action.action_id][0] for action in ordered_actions)
            if tuple(event.action_id for event in sorted(ordered_events, key=lambda event: event.ordinal)) != tuple(action.action_id for action in ordered_actions):
                reasons.add("PEER_DECLARATION_ABORT_NONDETERMINISTIC_EVENT_ORDER")
            for action, event in zip(ordered_actions, ordered_events):
                expected_reasons = set(declaration_failures.get(action.action_id, ()))
                if (
                    event.peer_transfer_id != action.peer_transfer_id
                    or event.counterparty_agent_id != action.counterparty_agent_id
                    or event.step_index != action.scheduled_step_index
                ):
                    reasons.add("PEER_DECLARATION_ABORT_EVENT_ACTION_BINDING_MISMATCH")
                if (
                    event.accepted
                    or event.filled_quantity != 0
                    or event.label is not ActionLabel.BLOCKED
                    or event.owner_pre_state_hash != event.owner_post_state_hash
                    or event.system_pre_state_hash != event.system_post_state_hash
                ):
                    reasons.add("PEER_DECLARATION_ABORT_MUTATED_STATE")
                    # A changed, previously reciprocal peer action must not be
                    # laundered into a declaration abort.  Preserve the
                    # reciprocal-action failure as an independent signal for
                    # forged histories, while honest zero-mutation declaration
                    # aborts remain verifier-valid.
                    reasons.add("PEER_GROUP_INVALID_RECIPROCAL_ACTIONS")
                if not expected_reasons.issubset(set(event.rejected_reason_codes)):
                    reasons.add("PEER_DECLARATION_ABORT_REASON_MISMATCH")
            declaration_event_ids = {event.event_id for event in ordered_events}
            if any(flow.ledger_event_id in declaration_event_ids for flow in episode.external_liquidity_flows):
                reasons.add("PEER_DECLARATION_ABORT_EXTERNAL_FLOW_PRESENT")
            continue
        if len(ordered_actions) != 2:
            reasons.add("PEER_GROUP_INCOMPLETE_RECIPROCAL_MEMBERSHIP")
            continue
        if len({action.scheduled_step_index for action in ordered_actions}) != 1:
            reasons.add("PEER_GROUP_CROSS_STEP_MEMBERSHIP")
        if _peer_declaration_failure_map(ordered_actions):
            reasons.add("PEER_GROUP_INVALID_RECIPROCAL_ACTIONS")
        has_unsupported_resource_effect = any(
            action.conflict_key is not None
            or action.conflict_transition in (ConflictTransition.RELEASE, ConflictTransition.EXPIRE)
            for action in ordered_actions
        )
        event_by_action: dict[str, list[LedgerEvent]] = {action.action_id: [] for action in ordered_actions}
        for event in group_events:
            if event.action_id in event_by_action:
                event_by_action[event.action_id].append(event)
            else:
                reasons.add("PEER_GROUP_EVENT_MEMBERSHIP_MISMATCH")
        if len(group_events) != 2 or any(len(items) != 1 for items in event_by_action.values()):
            reasons.add("PEER_GROUP_EVENT_MEMBERSHIP_MISMATCH")
            continue
        ordered_events = tuple(event_by_action[action.action_id][0] for action in ordered_actions)
        if tuple(event.action_id for event in sorted(ordered_events, key=lambda event: event.ordinal)) != tuple(action.action_id for action in ordered_actions):
            reasons.add("PEER_GROUP_NONDETERMINISTIC_EVENT_ORDER")
        if any(
            event.peer_transfer_id != transfer_id
            or event.counterparty_agent_id != action.counterparty_agent_id
            or event.step_index != action.scheduled_step_index
            for action, event in zip(ordered_actions, ordered_events)
        ):
            reasons.add("PEER_GROUP_EVENT_ACTION_BINDING_MISMATCH")
        peer_event_ids = {event.event_id for event in ordered_events}
        if any(flow.ledger_event_id in peer_event_ids for flow in episode.external_liquidity_flows):
            reasons.add("PEER_GROUP_EXTERNAL_FLOW_PRESENT")
        accepted = tuple(event for event in ordered_events if event.accepted)
        if len(accepted) == 1:
            reasons.add("PEER_GROUP_PARTIAL_COMMIT")
            continue
        if len(accepted) == 0:
            if any(
                event.filled_quantity != 0
                or event.owner_pre_state_hash != event.owner_post_state_hash
                or event.label is not ActionLabel.BLOCKED
                for event in ordered_events
            ):
                reasons.add("PEER_GROUP_ABORT_MUTATED_STATE")
            continue
        if any(event.filled_quantity < 0 or event.label is ActionLabel.BLOCKED for event in ordered_events):
            reasons.add("PEER_GROUP_INVALID_COMMIT_EVENT")
            continue
        if has_unsupported_resource_effect:
            reasons.add("PEER_GROUP_UNSUPPORTED_RESOURCE_EFFECT")
        signed = tuple(
            event.filled_quantity if action.order and action.order.side.value == "BUY" else -event.filled_quantity
            for action, event in zip(ordered_actions, ordered_events)
        )
        if signed[0] + signed[1] != 0 or ordered_events[0].filled_quantity != ordered_events[1].filled_quantity:
            reasons.add("PEER_GROUP_NONCOMPLEMENTARY_DELTA")

    if len(peer_actions) == len(episode.action_registry):
        initial_total = sum(_inventory_quantity(agent.inventory) for agent in episode.initial_agents)
        current_total = sum(_inventory_quantity(agent.inventory) for agent in episode.current_agents)
        if episode.external_liquidity_flows:
            reasons.add("PEER_ONLY_EXTERNAL_FLOW_PRESENT")
        if initial_total != current_total:
            reasons.add("PEER_ONLY_TOTAL_SYSTEM_NOT_CONSERVED")
    return tuple(sorted(reasons))


def _flow_for_event(event: LedgerEvent, action: CandidateAction) -> ExternalLiquidityFlowEvent:
    signed = event.filled_quantity if action.order and action.order.side.value == "BUY" else -event.filled_quantity
    return ExternalLiquidityFlowEvent(
        _sha({"ledger_event_id": event.event_id, "agent_id": event.agent_id, "agent_delta": signed}),
        event.event_id,
        event.agent_id,
        signed,
        -signed,
    )


def _blocked_event(
    episode_id: str, step_index: int, ordinal: int, action: CandidateAction,
    reasons: Sequence[str], owner_hash: str, system_hash: str,
) -> LedgerEvent:
    return _event_from_semantics(
        episode_id, step_index, ordinal, action,
        label=ActionLabel.BLOCKED, accepted=False, outcome_status="INVALID_OR_BLOCKED",
        filled_quantity=0, rejected_reason_codes=tuple(reasons),
        owner_pre_state_hash=owner_hash, owner_post_state_hash=owner_hash,
        system_pre_state_hash=system_hash, system_post_state_hash=system_hash,
    )


def _abstain_event(
    episode_id: str, step_index: int, ordinal: int, action: CandidateAction,
    reason: str, owner_hash: str, system_hash: str,
) -> LedgerEvent:
    return _event_from_semantics(
        episode_id, step_index, ordinal, action,
        label=ActionLabel.ABSTAIN, accepted=False, outcome_status="ABSTAINED",
        filled_quantity=0, rejected_reason_codes=(reason,),
        owner_pre_state_hash=owner_hash, owner_post_state_hash=owner_hash,
        system_pre_state_hash=system_hash, system_post_state_hash=system_hash,
    )


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
    return _arbitrate_internal(
        run_id, market, agents, actions,
        prior_events=prior_events,
        prior_shared_market_state=prior_shared_market_state,
        prior_executed_action_ids=prior_executed_action_ids,
        prior_executed_order_ids=prior_executed_order_ids,
        prior_episode_state=prior_episode_state,
        _verify_prior=True,
    )


def _arbitrate_internal(
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
    _verify_prior: bool,
) -> GameRun:
    """Only this reducer constructs events; verifier reuses it with trusted inputs disabled."""
    structure_error = _arbitration_structure_error(
        run_id, market, agents, actions,
        prior_events=prior_events,
        prior_shared_market_state=prior_shared_market_state,
        prior_executed_action_ids=prior_executed_action_ids,
        prior_executed_order_ids=prior_executed_order_ids,
        prior_episode_state=prior_episode_state,
    )
    if structure_error:
        raise ValueError(structure_error)
    assert isinstance(market, MarketState)
    assert isinstance(agents, (tuple, list)) and isinstance(actions, (tuple, list))
    assert isinstance(prior_events, (tuple, list))
    assert isinstance(prior_executed_action_ids, (tuple, list))
    assert isinstance(prior_executed_order_ids, (tuple, list))
    if len({event.event_id for event in prior_events}) != len(prior_events):
        raise ValueError("DUPLICATE_PRIOR_EVENT_ID")
    if len(set(prior_executed_action_ids)) != len(prior_executed_action_ids) or len(set(prior_executed_order_ids)) != len(prior_executed_order_ids):
        raise ValueError("DUPLICATE_PRIOR_EXECUTION_ID")
    if prior_episode_state is not None:
        assert isinstance(prior_episode_state, EpisodeState)
        if prior_episode_state.shared_market_state.market != market:
            raise ValueError("INVALID_PRIOR_EPISODE_STATE")
        if _verify_prior and not verify_episode_ledger(prior_episode_state).valid:
            raise ValueError("UNVERIFIABLE_PRIOR_EPISODE_STATE")
        prior_events = prior_episode_state.event_dag
        prior_shared_market_state = prior_episode_state.shared_market_state
        prior_executed_action_ids = prior_episode_state.executed_action_ids
        prior_executed_order_ids = prior_episode_state.executed_order_ids
    if prior_shared_market_state is not None:
        assert isinstance(prior_shared_market_state, SharedMarketState)
        if prior_shared_market_state.market != market:
            raise ValueError("INVALID_OR_CHANGED_PRIOR_SHARED_MARKET_STATE")
    agent_tuple, raw_action_tuple = tuple(agents), tuple(actions)
    if len({agent.agent_id for agent in agent_tuple}) != len(agent_tuple):
        raise ValueError("DUPLICATE_AGENT_ID")
    if len({action.action_id for action in raw_action_tuple}) != len(raw_action_tuple):
        raise ValueError("DUPLICATE_ACTION_ID")
    if len({action.arrival_sequence for action in raw_action_tuple}) != len(raw_action_tuple):
        raise ValueError("AMBIGUOUS_ACTION_ARRIVAL_SEQUENCE")
    if prior_episode_state is not None:
        if {agent.agent_id for agent in agent_tuple} != {agent.agent_id for agent in prior_episode_state.current_agents}:
            raise ValueError("PRIOR_EPISODE_AGENT_SET_MISMATCH")
        # The prior episode is the immutable source of inventories.  Callers may
        # supply stale descriptive agent objects, but cannot roll holdings back.
        agent_tuple = prior_episode_state.current_agents
    current_step = prior_episode_state.step_index + 1 if prior_episode_state else 1
    if any(action.scheduled_step_index not in (None, current_step) for action in raw_action_tuple):
        raise ValueError("ACTION_STEP_BOUNDARY_MISMATCH")
    action_tuple = tuple(replace(action, scheduled_step_index=current_step) for action in raw_action_tuple)
    invocation_ids = tuple(action.effective_invocation_id for action in action_tuple)
    order_ids = tuple(action.order.order_id for action in action_tuple if action.order is not None)
    if len(set(invocation_ids)) != len(invocation_ids):
        raise ValueError("DUPLICATE_INVOCATION_ID")
    if len(set(order_ids)) != len(order_ids):
        raise ValueError("DUPLICATE_ORDER_ID")
    initial_agents = prior_episode_state.initial_agents if prior_episode_state else agent_tuple
    root_run_id = prior_episode_state.root_run_id if prior_episode_state else run_id
    if not _bounded_text(root_run_id):
        raise ValueError("INVALID_PRIOR_EPISODE_IDENTITY")
    episode_id = _episode_id(root_run_id, initial_agents, market)
    if prior_episode_state is not None and prior_episode_state.episode_id != episode_id:
        raise ValueError("PRIOR_EPISODE_IDENTITY_MISMATCH")
    prior_registry = prior_episode_state.action_registry if prior_episode_state else ()
    prior_registry_action_ids = {action.action_id for action in prior_registry}
    prior_registry_invocation_ids = {action.effective_invocation_id for action in prior_registry}
    prior_registry_order_ids = {action.order.order_id for action in prior_registry if action.order is not None}
    prior_registry_peer_transfer_ids = {
        action.peer_transfer_id for action in prior_registry
        if action.peer_transfer_id is not None
    }
    if (
        any(action.action_id in prior_registry_action_ids for action in action_tuple)
        or any(invocation_id in prior_registry_invocation_ids for invocation_id in invocation_ids)
        or any(order_id in prior_registry_order_ids for order_id in order_ids)
        or any(
            action.peer_transfer_id is not None and action.peer_transfer_id in prior_registry_peer_transfer_ids
            for action in action_tuple
        )
    ):
        raise ValueError("PRIOR_ACTION_REGISTRY_COLLISION")
    # This must happen before the first event can be constructed.
    action_registry = _merge_action_registry(prior_registry, action_tuple)
    prior_boundaries = prior_episode_state.step_boundaries if prior_episode_state else ()
    step_boundaries = prior_boundaries + (
        EpisodeStepBoundary(current_step, tuple(action.action_id for action in sorted(action_tuple, key=lambda action: action.arrival_sequence))),
    )
    agent_by_id = {agent.agent_id: agent for agent in agent_tuple}
    invalid_agents = {agent.agent_id: _validate_agent(agent, market)[1] for agent in agent_tuple if not _validate_agent(agent, market)[0]}
    invalid_actions = {action.action_id: _validate_action(action)[1] for action in action_tuple if not _validate_action(action)[0]}
    peer_shape_failures = _peer_declaration_failure_map(action_tuple)
    invalid_actions.update(peer_shape_failures)
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
    peer_pairs = _valid_peer_pair_map(action_tuple)
    processed_peer_action_ids: set[str] = set()
    ordered_actions = tuple(sorted(action_tuple, key=lambda item: item.arrival_sequence))
    ordinal_by_action_id = {
        action.action_id: ordinal
        for ordinal, action in enumerate(ordered_actions, start=len(prior_events) + 1)
    }
    external_flows: list[ExternalLiquidityFlowEvent] = []

    def emit(event: LedgerEvent, action: CandidateAction) -> None:
        """Every terminal event reserves all supplied replay identities, including blocks."""
        events.append(event)
        known_parent_ids.add(event.event_id)
        executed_action_ids.add(action.action_id)
        executed_invocation_ids.add(action.effective_invocation_id)
        if action.order is not None:
            executed_order_ids.add(action.order.order_id)

    for ordinal, action in enumerate(ordered_actions, start=len(prior_events) + 1):
        if action.action_id in processed_peer_action_ids:
            continue
        owner = portfolios.get(action.agent_id)
        owner_hash = owner.post_state_hash if owner is not None else "UNKNOWN_OWNER_STATE"
        system_before = _system_hash(portfolios, market, claimed_conflicts, prior_ids + tuple(event.event_id for event in events))
        if action.action_id in peer_pairs:
            plan = _plan_peer_settlement(
                peer_pairs[action.action_id], market=market, agents_by_id=agent_by_id,
                portfolios=portfolios, known_parent_ids=known_parent_ids,
                invalid_agents=invalid_agents, invalid_actions=invalid_actions,
            )
            processed_peer_action_ids.update(item.action_id for item in plan.actions)
            if not plan.commit:
                for peer_action in plan.actions:
                    peer_owner = portfolios.get(peer_action.agent_id)
                    peer_hash = peer_owner.post_state_hash if peer_owner is not None else "UNKNOWN_OWNER_STATE"
                    emit(_blocked_event(
                        episode_id, current_step, ordinal_by_action_id[peer_action.action_id], peer_action,
                        plan.reason_codes, peer_hash, system_before,
                    ), peer_action)
                continue

            next_portfolios = dict(portfolios)
            owner_hashes: dict[str, Tuple[str, str]] = {}
            for peer_action in plan.actions:
                peer_owner = portfolios[peer_action.agent_id]
                peer_outcome = plan.outcome_for(peer_action.action_id)
                next_inventory = peer_outcome.inventory
                next_hash = _portfolio_hash(peer_action.agent_id, next_inventory)
                signed_fill = peer_outcome.filled_quantity if peer_action.order and peer_action.order.side.value == "BUY" else -peer_outcome.filled_quantity
                next_portfolios[peer_action.agent_id] = AgentPortfolioState(
                    peer_action.agent_id, peer_owner.initial_inventory, next_inventory,
                    peer_owner.pre_state_hash, next_hash, peer_owner.net_filled_quantity + signed_fill,
                )
                owner_hashes[peer_action.action_id] = (peer_owner.post_state_hash, next_hash)
            system_after = _system_hash(
                next_portfolios, market, claimed_conflicts,
                prior_ids + tuple(event.event_id for event in events),
            )
            portfolios = next_portfolios
            for peer_action in plan.actions:
                peer_outcome = plan.outcome_for(peer_action.action_id)
                owner_pre_hash, owner_post_hash = owner_hashes[peer_action.action_id]
                emit(_event_from_semantics(
                    episode_id, current_step, ordinal_by_action_id[peer_action.action_id], peer_action,
                    label=peer_action.label, accepted=True, outcome_status=peer_outcome.status.value,
                    filled_quantity=peer_outcome.filled_quantity,
                    rejected_reason_codes=tuple(peer_outcome.reason_codes),
                    owner_pre_state_hash=owner_pre_hash, owner_post_state_hash=owner_post_hash,
                    system_pre_state_hash=system_before, system_post_state_hash=system_after,
                ), peer_action)
            continue
        if action.action_id in invalid_actions:
            emit(_blocked_event(episode_id, current_step, ordinal, action, invalid_actions[action.action_id], owner_hash, system_before), action)
            continue
        agent = agent_by_id.get(action.agent_id)
        if agent is None:
            emit(_blocked_event(episode_id, current_step, ordinal, action, ("UNKNOWN_AGENT",), owner_hash, system_before), action)
            continue
        if agent.agent_id in invalid_agents:
            emit(_blocked_event(episode_id, current_step, ordinal, action, invalid_agents[agent.agent_id], owner_hash, system_before), action)
            continue
        if any(parent not in known_parent_ids for parent in action.causal_parent_event_ids):
            emit(_blocked_event(episode_id, current_step, ordinal, action, ("UNKNOWN_OR_FORWARD_CAUSAL_PARENT",), owner_hash, system_before), action)
            continue
        if action.label is ActionLabel.ABSTAIN:
            emit(_abstain_event(episode_id, current_step, ordinal, action, "DECLARED_ABSTENTION", owner_hash, system_before), action)
            continue
        if action.label is ActionLabel.BLOCKED:
            emit(_blocked_event(episode_id, current_step, ordinal, action, ("DECLARED_BLOCKED_ACTION",), owner_hash, system_before), action)
            continue
        if action.requires_complete_information and agent.information.unknowns:
            emit(_abstain_event(episode_id, current_step, ordinal, action, "INCOMPLETE_INFORMATION", owner_hash, system_before), action)
            continue
        if action.conflict_key and action.conflict_transition in (ConflictTransition.RELEASE, ConflictTransition.EXPIRE):
            if action.conflict_key not in claimed_conflicts:
                emit(_blocked_event(episode_id, current_step, ordinal, action, ("CONFLICT_RESOURCE_NOT_CLAIMED",), owner_hash, system_before), action)
                continue
            claim_event_id = claimed_conflicts[action.conflict_key]
            claim_event = next((event for event in tuple(prior_events) + tuple(events) if event.event_id == claim_event_id), None)
            if claim_event is None or claim_event.agent_id != action.agent_id:
                emit(_blocked_event(episode_id, current_step, ordinal, action, ("CONFLICT_RESOURCE_NOT_OWNED",), owner_hash, system_before), action)
                continue
            del claimed_conflicts[action.conflict_key]
            status = "CONFLICT_RESOURCE_" + action.conflict_transition.value.upper()
            event_id = _event_id(
                episode_id, current_step, ordinal, action, label=action.label, accepted=True,
                status=status, filled_quantity=0, reasons=(), cause_refs=tuple(sorted(action.evidence_refs)),
                causal_parent_event_ids=tuple(sorted(action.causal_parent_event_ids)),
                owner_pre_hash=owner_hash, owner_post_hash=owner_hash,
            )
            system_after = _system_hash(portfolios, market, claimed_conflicts, prior_ids + tuple(event.event_id for event in events) + (event_id,))
            emit(_event_from_semantics(
                episode_id, current_step, ordinal, action, label=action.label, accepted=True,
                outcome_status=status, filled_quantity=0, rejected_reason_codes=(),
                owner_pre_state_hash=owner_hash, owner_post_state_hash=owner_hash,
                system_pre_state_hash=system_before, system_post_state_hash=system_after,
            ), action)
            continue
        if action.order is None:
            emit(_blocked_event(episode_id, current_step, ordinal, action, ("MISSING_SYNTHETIC_ORDER",), owner_hash, system_before), action)
            continue
        if action.conflict_key and action.conflict_key in claimed_conflicts:
            emit(_blocked_event(episode_id, current_step, ordinal, action, ("CONFLICT_RESOURCE_ALREADY_CLAIMED",), owner_hash, system_before), action)
            continue
        outcome: SyntheticMatchOutcome = reduce_order(market, owner.final_inventory, action.order)
        accepted = outcome.status is not OutcomeStatus.INVALID_OR_BLOCKED
        next_inventory = outcome.inventory
        next_owner_hash = _portfolio_hash(action.agent_id, next_inventory)
        next_portfolio = AgentPortfolioState(action.agent_id, owner.initial_inventory, next_inventory, owner.pre_state_hash,
                                             next_owner_hash, owner.net_filled_quantity + (outcome.filled_quantity if action.order.side.value == "BUY" else -outcome.filled_quantity))
        portfolios[action.agent_id] = next_portfolio
        event_label = action.label if accepted else ActionLabel.BLOCKED
        provisional_id = _event_id(
            episode_id, current_step, ordinal, action, label=event_label, accepted=accepted,
            status=outcome.status.value, filled_quantity=outcome.filled_quantity,
            reasons=tuple(outcome.reason_codes), cause_refs=tuple(sorted(action.evidence_refs)),
            causal_parent_event_ids=tuple(sorted(action.causal_parent_event_ids)),
            owner_pre_hash=owner_hash, owner_post_hash=next_owner_hash,
        )
        if accepted and action.conflict_key and action.conflict_transition is ConflictTransition.CLAIM:
            claimed_conflicts[action.conflict_key] = provisional_id
        system_after = _system_hash(portfolios, market, claimed_conflicts, prior_ids + tuple(event.event_id for event in events) + (provisional_id,))
        event = _event_from_semantics(
            episode_id, current_step, ordinal, action, label=event_label, accepted=accepted,
            outcome_status=outcome.status.value, filled_quantity=outcome.filled_quantity,
            rejected_reason_codes=tuple(outcome.reason_codes), owner_pre_state_hash=owner_hash,
            owner_post_state_hash=next_owner_hash, system_pre_state_hash=system_before,
            system_post_state_hash=system_after,
        )
        emit(event, action)
        if accepted and action.liquidity_mode is LiquidityMode.EXTERNAL_SYNTHETIC_LIQUIDITY:
            external_flows.append(_flow_for_event(event, action))
    ordered_portfolios = tuple(portfolios[agent_id] for agent_id in sorted(portfolios))
    shared_hash = _sha({"market": market, "claims": sorted(claimed_conflicts.items())})
    shared = SharedMarketState(market, tuple(sorted(claimed_conflicts)), tuple(sorted(claimed_conflicts.items())), shared_hash)
    ledger_hash = _sha([event for event in events])
    total_hash = _system_hash(portfolios, market, claimed_conflicts, prior_ids + tuple(event.event_id for event in events))
    episode_agents = _agents_from_portfolios(agent_tuple, ordered_portfolios)
    all_flows = tuple(prior_episode_state.external_liquidity_flows if prior_episode_state else ()) + tuple(external_flows)
    all_events = tuple(prior_events) + tuple(events)
    episode = EpisodeState(
        current_step, episode_agents, shared,
        tuple(sorted(executed_action_ids)), tuple(sorted(executed_order_ids)), tuple(sorted(executed_invocation_ids)),
        all_events, initial_agents, action_registry, all_flows,
        _episode_state_hash(
            step_index=current_step, initial_agents=initial_agents, current_agents=episode_agents,
            shared_market_state=shared, executed_action_ids=tuple(sorted(executed_action_ids)),
            executed_order_ids=tuple(sorted(executed_order_ids)), executed_invocation_ids=tuple(sorted(executed_invocation_ids)),
            event_dag=all_events, action_registry=action_registry, external_liquidity_flows=all_flows,
            root_run_id=root_run_id, episode_id=episode_id, step_boundaries=step_boundaries,
        ),
        root_run_id, episode_id, step_boundaries,
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
    if sum(recomputed.values()) != 0:
        return False
    if sum(_inventory_quantity(item.inventory) for item in initial_agents) != sum(
        _inventory_quantity(portfolio.final_inventory) for portfolio in result.final_agent_portfolios
    ):
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
