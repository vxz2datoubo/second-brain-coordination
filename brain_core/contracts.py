"""Data contracts for the super second brain v0.1.

The contracts are intentionally stdlib-only so the MVP works on a clean local
Python install. Future versions can wrap these dataclasses with Pydantic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import uuid
from typing import Any, TypeVar


T = TypeVar("T")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_hash(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def new_id(prefix: str, seed: str | None = None) -> str:
    suffix = stable_hash(seed, 14) if seed else uuid.uuid4().hex[:14]
    return f"{prefix}_{suffix}"


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def to_dict(record: Any) -> dict[str, Any]:
    if is_dataclass(record):
        return asdict(record)
    if isinstance(record, dict):
        return dict(record)
    raise TypeError(f"Cannot serialize {type(record)!r}")


def to_json(record: Any) -> str:
    return json.dumps(to_dict(record), ensure_ascii=False, sort_keys=True)


def from_dict(cls: type[T], data: dict[str, Any]) -> T:
    names = {f.name for f in fields(cls)}
    kwargs = {k: v for k, v in data.items() if k in names}
    return cls(**kwargs)


@dataclass
class SourceRecord:
    id: str = field(default_factory=lambda: new_id("src"))
    source_type: str = "manual"
    title: str = ""
    uri: str = ""
    captured_at: str = field(default_factory=now_iso)
    published_at: str = ""
    reliability: float = 0.6
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.source_type:
            raise ValueError("SourceRecord.source_type is required")
        self.reliability = clamp(self.reliability)


@dataclass
class EvidenceItem:
    id: str = field(default_factory=lambda: new_id("ev"))
    source_id: str = ""
    quote: str = ""
    evidence_type: str = "fact"
    extracted_at: str = field(default_factory=now_iso)
    method: str = "rule_extractor"
    confidence: float = 0.6
    freshness: float = 1.0
    bias_notes: str = ""
    supports: list[str] = field(default_factory=list)
    refutes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.source_id:
            raise ValueError("EvidenceItem.source_id is required")
        if not self.quote:
            raise ValueError("EvidenceItem.quote is required")
        self.confidence = clamp(self.confidence)
        self.freshness = clamp(self.freshness)


@dataclass
class KnowledgeAtom:
    id: str = field(default_factory=lambda: new_id("atom"))
    title: str = ""
    content: str = ""
    summary: str = ""
    atom_type: str = "fact"
    para: str = "Resources"
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    confidence: float = 0.6
    importance: float = 0.5
    activation: float = 0.5
    decay_rate: float = 0.05
    next_review_at: str = ""
    related_ids: list[str] = field(default_factory=list)
    conflict_ids: list[str] = field(default_factory=list)
    support_evidence_ids: list[str] = field(default_factory=list)
    counter_evidence_ids: list[str] = field(default_factory=list)
    boundaries: list[str] = field(default_factory=list)
    falsification_records: list[dict[str, Any]] = field(default_factory=list)
    status: str = "active"
    implementation_status: str = "Implemented"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.content:
            raise ValueError("KnowledgeAtom.content is required")
        if not self.source_ids:
            raise ValueError("KnowledgeAtom.source_ids must not be empty")
        if not self.evidence_ids:
            raise ValueError("KnowledgeAtom.evidence_ids must not be empty")
        self.confidence = clamp(self.confidence)
        self.importance = clamp(self.importance)
        self.activation = clamp(self.activation)
        self.decay_rate = clamp(self.decay_rate)


@dataclass
class RelationEdge:
    id: str = field(default_factory=lambda: new_id("rel"))
    source_atom_id: str = ""
    target_atom_id: str = ""
    relation_type: str = "related_to"
    confidence: float = 0.4
    evidence_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.source_atom_id or not self.target_atom_id:
            raise ValueError("RelationEdge endpoints are required")
        self.confidence = clamp(self.confidence)


@dataclass
class EpisodicMemory:
    id: str = field(default_factory=lambda: new_id("epi"))
    event_type: str = "ingest"
    title: str = ""
    occurred_at: str = field(default_factory=now_iso)
    participant_ids: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    atom_ids: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    outcome: str = ""
    review_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskApproval:
    id: str = field(default_factory=lambda: new_id("approval"))
    action_type: str = ""
    risk_level: str = "low"
    requires_approval: bool = False
    approved: bool = False
    approved_by: str = ""
    approved_at: str = ""
    reason: str = ""
    policy_version: str = "v0.1"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionRecord:
    id: str = field(default_factory=lambda: new_id("dec"))
    decision_type: str = "general"
    question: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    options: list[str] = field(default_factory=list)
    chosen: str = "wait"
    action: str = "wait"
    evidence_ids: list[str] = field(default_factory=list)
    counter_evidence_ids: list[str] = field(default_factory=list)
    confidence: float = 0.5
    rationale: str = ""
    warnings: list[str] = field(default_factory=list)
    risk_level: str = "medium"
    approval_id: str = ""
    created_at: str = field(default_factory=now_iso)
    outcome: str = ""
    reviewed_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.confidence = clamp(self.confidence)
        if self.confidence >= 0.75 and not self.evidence_ids:
            raise ValueError("High-confidence decisions require evidence_ids")


@dataclass
class ForecastRecord:
    id: str = field(default_factory=lambda: new_id("fc"))
    question: str = ""
    horizon: str = ""
    probability: float = 0.5
    scenarios: list[dict[str, Any]] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    counter_evidence_ids: list[str] = field(default_factory=list)
    confidence: float = 0.5
    triggers: list[str] = field(default_factory=list)
    invalidation_conditions: list[str] = field(default_factory=list)
    risk_exposure: str = ""
    created_at: str = field(default_factory=now_iso)
    review_at: str = ""
    outcome: str = ""
    actual_score: float | None = None
    brier_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.probability = clamp(self.probability)
        self.confidence = clamp(self.confidence)
        if self.confidence >= 0.75 and not self.evidence_ids:
            raise ValueError("High-confidence forecasts require evidence_ids")


@dataclass
class ReviewRecord:
    id: str = field(default_factory=lambda: new_id("review"))
    target_type: str = ""
    target_id: str = ""
    actual_outcome: str = ""
    actual_score: float | None = None
    reviewed_at: str = field(default_factory=now_iso)
    notes: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    lessons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackRecord:
    id: str = field(default_factory=lambda: new_id("feedback"))
    target_type: str = "atom"
    target_ids: list[str] = field(default_factory=list)
    feedback_type: str = "user_feedback"
    feedback_text: str = ""
    tags_to_add: list[str] = field(default_factory=list)
    tags_to_remove: list[str] = field(default_factory=list)
    confidence_delta: float = 0.0
    related_atom_ids: list[str] = field(default_factory=list)
    support_ids: list[str] = field(default_factory=list)
    refute_ids: list[str] = field(default_factory=list)
    improvement_items: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.target_ids:
            raise ValueError("FeedbackRecord.target_ids must not be empty")


@dataclass
class ReasoningTrace:
    id: str = field(default_factory=lambda: new_id("reason"))
    question: str = ""
    trace_type: str = "analysis"
    steps: list[dict[str, Any]] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    counter_evidence_ids: list[str] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.5
    uncertainty: str = ""
    next_action: str = "wait"
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.question:
            raise ValueError("ReasoningTrace.question is required")
        self.confidence = clamp(self.confidence)


@dataclass
class LearningEntry:
    id: str = field(default_factory=lambda: new_id("learn"))
    entry_type: str = "feedback"
    target_type: str = ""
    target_ids: list[str] = field(default_factory=list)
    source_record_id: str = ""
    summary: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    counter_evidence_ids: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    improvement_items: list[str] = field(default_factory=list)
    confidence_delta: float = 0.0
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.target_ids:
            raise ValueError("LearningEntry.target_ids must not be empty")


@dataclass
class WritebackSnapshot:
    id: str = field(default_factory=lambda: new_id("wsnap"))
    name: str = ""
    captured_at: str = field(default_factory=now_iso)
    top_writeback_atoms: list[dict[str, Any]] = field(default_factory=list)
    top_recommended_tags: list[dict[str, Any]] = field(default_factory=list)
    top_chain_texts: list[dict[str, Any]] = field(default_factory=list)
    flagged_for_review: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SelfEvolutionLog:
    id: str = field(default_factory=lambda: new_id("evo"))
    trigger: str = ""
    observation: str = ""
    change_type: str = "learning"
    affected_ids: list[str] = field(default_factory=list)
    proposed_update: str = ""
    applied: bool = False
    metrics: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTrace:
    id: str = field(default_factory=lambda: new_id("trace"))
    agent_name: str = "coordinator"
    task: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.5
    counterpoints: list[str] = field(default_factory=list)
    needs_human_confirmation: bool = False
    implementation_status: str = "Mock"
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.confidence = clamp(self.confidence)


@dataclass
class QualityState:
    quality_score: float = 0.5
    evidence_level: str = "medium"
    source_reliability: float = 0.6
    freshness: float = 1.0
    validation_status: str = "pending"
    out_of_sample_result: str = "not_run"
    failure_count: int = 0
    conflict_count: int = 0
    human_reviewed: bool = False
    status: str = "Experimental"

    def normalize_quality(self) -> None:
        self.quality_score = clamp(self.quality_score)
        self.source_reliability = clamp(self.source_reliability)
        self.freshness = clamp(self.freshness)
        self.failure_count = max(0, int(self.failure_count))
        self.conflict_count = max(0, int(self.conflict_count))


@dataclass
class MarketDataRecord(QualityState):
    id: str = field(default_factory=lambda: new_id("mdata"))
    source_id: str = ""
    symbol: str = ""
    market: str = "CN-A"
    timeframe: str = "1d"
    start_at: str = ""
    end_at: str = ""
    bar_count: int = 0
    record_path: str = ""
    normalization_version: str = "v0.1"
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.source_id:
            raise ValueError("MarketDataRecord.source_id is required")
        if not self.symbol:
            raise ValueError("MarketDataRecord.symbol is required")
        self.bar_count = max(0, int(self.bar_count))
        self.normalize_quality()


@dataclass
class PriceBar(QualityState):
    id: str = field(default_factory=lambda: new_id("pbar"))
    market_data_id: str = ""
    symbol: str = ""
    ts: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    amount: float = 0.0
    timeframe: str = "1d"
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.market_data_id:
            raise ValueError("PriceBar.market_data_id is required")
        if not self.symbol:
            raise ValueError("PriceBar.symbol is required")
        if not self.ts:
            raise ValueError("PriceBar.ts is required")
        self.open = float(self.open)
        self.high = float(self.high)
        self.low = float(self.low)
        self.close = float(self.close)
        self.volume = float(self.volume)
        self.amount = float(self.amount)
        self.normalize_quality()


@dataclass
class OrderBookSnapshot(QualityState):
    id: str = field(default_factory=lambda: new_id("obook"))
    symbol: str = ""
    ts: str = ""
    bids: list[dict[str, Any]] = field(default_factory=list)
    asks: list[dict[str, Any]] = field(default_factory=list)
    source_id: str = ""
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Interface"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.normalize_quality()


@dataclass
class TradePrint(QualityState):
    id: str = field(default_factory=lambda: new_id("tprint"))
    symbol: str = ""
    ts: str = ""
    price: float = 0.0
    size: float = 0.0
    side: str = "unknown"
    source_id: str = ""
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Interface"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.price = float(self.price)
        self.size = float(self.size)
        self.normalize_quality()


@dataclass
class FeatureSet(QualityState):
    id: str = field(default_factory=lambda: new_id("feat"))
    market_data_id: str = ""
    bar_id: str = ""
    symbol: str = ""
    ts: str = ""
    features: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.market_data_id:
            raise ValueError("FeatureSet.market_data_id is required")
        if not self.bar_id:
            raise ValueError("FeatureSet.bar_id is required")
        self.normalize_quality()


@dataclass
class IndicatorDefinition(QualityState):
    id: str = field(default_factory=lambda: new_id("ind"))
    name: str = ""
    category: str = "trend"
    formula: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    interpretation: str = ""
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Implemented"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            raise ValueError("IndicatorDefinition.name is required")
        self.normalize_quality()


@dataclass
class TheoryDefinition(QualityState):
    id: str = field(default_factory=lambda: new_id("theory"))
    name: str = ""
    thesis: str = ""
    hypothesis: str = ""
    entry_logic: str = ""
    exit_logic: str = ""
    invalidation_conditions: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Implemented"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            raise ValueError("TheoryDefinition.name is required")
        self.normalize_quality()


@dataclass
class StrategyDefinition(QualityState):
    id: str = field(default_factory=lambda: new_id("strat"))
    name: str = ""
    strategy_family: str = "trend"
    theory_id: str = ""
    indicator_ids: list[str] = field(default_factory=list)
    entry_rule: str = ""
    exit_rule: str = ""
    risk_rule: str = ""
    timeframe: str = "1d"
    research_mode: bool = True
    live_trading_enabled: bool = False
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Experimental"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            raise ValueError("StrategyDefinition.name is required")
        self.normalize_quality()


@dataclass
class BacktestConfig(QualityState):
    id: str = field(default_factory=lambda: new_id("btcfg"))
    strategy_id: str = ""
    market_data_id: str = ""
    initial_cash: float = 100000.0
    commission_pct: float = 0.00025
    slippage_pct: float = 0.001
    params: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Implemented"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.strategy_id:
            raise ValueError("BacktestConfig.strategy_id is required")
        if not self.market_data_id:
            raise ValueError("BacktestConfig.market_data_id is required")
        self.initial_cash = float(self.initial_cash)
        self.commission_pct = float(self.commission_pct)
        self.slippage_pct = float(self.slippage_pct)
        self.normalize_quality()


@dataclass
class BacktestResult(QualityState):
    id: str = field(default_factory=lambda: new_id("btres"))
    strategy_id: str = ""
    market_data_id: str = ""
    config_id: str = ""
    symbol: str = ""
    sample_start: str = ""
    sample_end: str = ""
    trades_count: int = 0
    win_rate: float = 0.0
    total_return: float = 0.0
    annualized_return: float = 0.0
    max_drawdown: float = 0.0
    final_equity: float = 0.0
    risk_adjusted_score: float = 0.0
    cost_pct: float = 0.0
    summary: str = ""
    recommendation: str = ""
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Implemented"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.strategy_id:
            raise ValueError("BacktestResult.strategy_id is required")
        self.win_rate = clamp(self.win_rate)
        self.normalize_quality()


@dataclass
class ValidationReport(QualityState):
    id: str = field(default_factory=lambda: new_id("vreport"))
    target_type: str = "strategy"
    target_id: str = ""
    effective: bool = False
    verdict: str = "needs_review"
    governance_action: str = "needs_review"
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    net_edge_pct: float = 0.0
    sample_size: int = 0
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Implemented"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.target_id:
            raise ValueError("ValidationReport.target_id is required")
        self.sample_size = max(0, int(self.sample_size))
        self.normalize_quality()


@dataclass
class SignalRecord(QualityState):
    id: str = field(default_factory=lambda: new_id("sig"))
    strategy_id: str = ""
    symbol: str = ""
    ts: str = ""
    signal: str = "wait"
    score: float = 0.0
    confidence: float = 0.5
    reason: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.confidence = clamp(self.confidence)
        self.normalize_quality()


@dataclass
class TradeDecision(QualityState):
    id: str = field(default_factory=lambda: new_id("tdec"))
    signal_id: str = ""
    strategy_id: str = ""
    symbol: str = ""
    action: str = "wait"
    rationale: str = ""
    risk_check_result_id: str = ""
    decision_record_id: str = ""
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.normalize_quality()


@dataclass
class TradeJournal(QualityState):
    id: str = field(default_factory=lambda: new_id("tjournal"))
    symbol: str = ""
    strategy_id: str = ""
    market_data_id: str = ""
    backtest_result_id: str = ""
    validation_report_id: str = ""
    decision_record_id: str = ""
    forecast_record_id: str = ""
    entries: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Implemented"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("TradeJournal.symbol is required")
        self.normalize_quality()


@dataclass
class RiskCheckResult(QualityState):
    id: str = field(default_factory=lambda: new_id("rcheck"))
    context_type: str = "trade"
    action: str = "wait"
    allowed: bool = False
    research_mode: bool = True
    live_trading_enabled: bool = False
    warnings: list[str] = field(default_factory=list)
    net_edge_pct: float = 0.0
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Implemented"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.normalize_quality()


@dataclass
class StrategyReview(QualityState):
    id: str = field(default_factory=lambda: new_id("sreview"))
    strategy_id: str = ""
    backtest_result_id: str = ""
    verdict: str = "needs_review"
    lessons: list[str] = field(default_factory=list)
    action_recommendation: str = "needs_review"
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Implemented"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.normalize_quality()


@dataclass
class SkillRegistryEntry(QualityState):
    id: str = field(default_factory=lambda: new_id("skill"))
    skill_name: str = ""
    domain: str = "trading"
    version: str = "v0.1"
    capability_type: str = "workflow"
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Implemented"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.skill_name:
            raise ValueError("SkillRegistryEntry.skill_name is required")
        self.normalize_quality()


@dataclass
class ModuleStatusRecord(QualityState):
    id: str = field(default_factory=lambda: new_id("mod"))
    module_name: str = ""
    domain: str = "trading"
    quality_action: str = "keep"
    summary: str = ""
    dependencies: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Implemented"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.module_name:
            raise ValueError("ModuleStatusRecord.module_name is required")
        self.normalize_quality()


@dataclass
class BulletinStateRecord(QualityState):
    id: str = field(default_factory=lambda: new_id("bstate"))
    bulletin_path: str = ""
    state_status: str = "进行中"
    completed: list[str] = field(default_factory=list)
    in_progress: list[str] = field(default_factory=list)
    next_step: str = ""
    recent_event: str = ""
    summary: str = ""
    created_at: str = field(default_factory=now_iso)
    implementation_status: str = "Implemented"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.normalize_quality()


# ── Phase 3: Task & Reminder Records ──

# Status flow per blueprint §11.1:
# Captured → Clarifying → Planned → Scheduled → InProgress ─┬→ Done → Reviewed → Archived
#                           ├→ Blocked ───→ InProgress       │
#                           ├→ Deferred ───→ Planned         │
#                           └→ Cancelled ────────────────────┘

TASK_STATUS_FLOW: dict[str, list[str]] = {
    "Captured":   ["Clarifying", "Cancelled"],
    "Clarifying": ["Planned", "Cancelled", "Deferred"],
    "Planned":    ["Scheduled", "Deferred", "Cancelled"],
    "Scheduled":  ["InProgress", "Blocked", "Cancelled", "Deferred"],
    "InProgress": ["Done", "Blocked", "Cancelled"],
    "Blocked":    ["InProgress", "Cancelled", "Deferred"],
    "Deferred":   ["Planned", "Cancelled"],
    "Done":       ["Reviewed", "Archived"],
    "Cancelled":  ["Archived"],
    "Reviewed":   ["Archived"],
    "Archived":   [],
}


@dataclass
class TaskRecord:
    """Blueprint §11.2: 日常任务记录"""
    id: str = field(default_factory=lambda: new_id("task"))
    user_id: str = "default"
    title: str = ""
    description: str = ""
    source_message_id: str = ""
    created_at: str = field(default_factory=now_iso)
    due_at: str = ""              # ISO timestamp
    scheduled_start: str = ""
    scheduled_end: str = ""
    priority: str = "medium"       # low | medium | high | urgent
    energy_level: str = "medium"   # low | medium | high
    estimated_minutes: int = 0
    status: str = "Captured"
    dependencies: list[str] = field(default_factory=list)
    related_goals: list[str] = field(default_factory=list)
    related_memories: list[str] = field(default_factory=list)
    reminders: list[str] = field(default_factory=list)  # reminder timestamps
    conflict_records: list[str] = field(default_factory=list)
    last_reviewed_at: str = ""
    completed_at: str = ""
    note: str = ""                 # latest update note
    metadata: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════
# Phase 5: Goals & Future Simulation
# ═══════════════════════════════════════════

GOAL_STATUS_FLOW: dict[str, list[str]] = {
    "dreaming":   ["defining", "abandoned"],
    "defining":   ["planned", "deferred", "abandoned"],
    "planned":    ["in_progress", "deferred", "abandoned"],
    "in_progress": ["achieved", "blocked", "abandoned"],
    "blocked":    ["in_progress", "deferred", "abandoned"],
    "deferred":   ["planned", "abandoned"],
    "achieved":   ["archived", "reviewing"],
    "reviewing":  ["archived", "planned"],  # review may spawn follow-up goals
    "archived":   [],
    "abandoned":  ["dreaming"],   # can rekindle
}


@dataclass
class GoalRecord:
    """Blueprint §5.2: 长期目标和未来推演

    Goal → Milestones → Tasks → Review 闭环。
    支持嵌套层次：life > yearly > quarterly > monthly > weekly > daily
    """
    id: str = field(default_factory=lambda: new_id("goal"))
    user_id: str = "default"
    title: str = ""
    description: str = ""
    goal_type: str = "monthly"      # daily | weekly | monthly | quarterly | yearly | life
    time_horizon: str = "medium"     # short(day-week) | medium(month-quarter) | long(year+) | lifelong
    parent_goal_id: str = ""         # hierarchy parent
    sub_goal_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    target_date: str = ""            # ISO date when should be achieved
    started_at: str = ""
    progress: float = 0.0            # 0.0 ~ 1.0
    status: str = "dreaming"         # GOAL_STATUS_FLOW
    milestones: list[dict[str, Any]] = field(default_factory=list)  # [{date, text, achieved: bool}]
    related_tasks: list[str] = field(default_factory=list)          # TaskRecord IDs
    success_criteria: list[str] = field(default_factory=list)       # measurable outcomes
    blockers: list[str] = field(default_factory=list)
    review_interval_days: int = 7    # how often to auto-review
    last_reviewed_at: str = ""
    next_review_at: str = ""
    reflections: list[dict[str, Any]] = field(default_factory=list)  # [{date, text, progress_rating: 1-5}]
    priority: str = "medium"         # low | medium | high | critical
    energy_required: str = "medium"  # low | medium | high
    risk_factors: list[str] = field(default_factory=list)
    motivation: str = ""             # why this goal matters
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FuturePath:
    """单条未来推演路径"""
    id: str = field(default_factory=lambda: new_id("path"))
    path_type: str = "most_likely"   # optimistic | pessimistic | most_likely | wildcard | baseline
    probability: float = 0.5          # 0-1
    description: str = ""
    timeline: list[dict[str, Any]] = field(default_factory=list)  # [{date, event, confidence}]
    key_milestones: list[str] = field(default_factory=list)
    risk_events: list[str] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)
    early_signals: list[str] = field(default_factory=list)        # signals to watch
    best_outcome: str = ""
    worst_outcome: str = ""
    expected_outcome: str = ""
    confidence: float = 0.6
    created_at: str = field(default_factory=now_iso)


@dataclass
class WeekPlan:
    """周计划快照"""
    id: str = field(default_factory=lambda: new_id("wplan"))
    week_start: str = ""  # ISO date (Monday)
    goal_ids: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)
    focus_areas: list[str] = field(default_factory=list)  # top 3 priorities
    energy_budget: str = "medium"
    note: str = ""
    created_at: str = field(default_factory=now_iso)
    reviewed_at: str = ""
