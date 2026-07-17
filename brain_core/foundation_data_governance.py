"""Foundation data governance for the mother system.

This module implements the first architecture slice requested by
FOUNDATION-DATA-GOVERNANCE-0001 v2:

- unified object-model bindings
- data-layer boundaries
- market-data adapter contracts
- capability negotiation
- data-quality governance

The implementation is intentionally isolated from live trading. It reuses the
existing mother-system records for writeback, while keeping new adapter and
governance schemas local to this module until later phases promote them into
broader runtime use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import csv
import json
from pathlib import Path
from typing import Any

from .contracts import (
    BulletinStateRecord,
    EvidenceItem,
    KnowledgeAtom,
    MarketDataRecord,
    ModuleStatusRecord,
    PriceBar,
    SelfEvolutionLog,
    SkillRegistryEntry,
    SourceRecord,
    clamp,
    new_id,
    now_iso,
    to_dict,
)


TASK_ID = "FOUNDATION-DATA-GOVERNANCE-0001"
SCHEMA_VERSION = "foundation-data-governance-v2"


@dataclass
class GovernanceEnvelope:
    object_id: str = ""
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=now_iso)
    effective_at: str = ""
    available_at: str = ""
    source_id: str = ""
    lineage: dict[str, Any] = field(default_factory=dict)
    quality_flags: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DataLineageRecord(GovernanceEnvelope):
    provider_name: str = ""
    provider_payload_type: str = ""
    raw_ref: str = ""
    normalized_ref: str = ""
    provider_field_map: dict[str, str] = field(default_factory=dict)
    transformation_steps: list[str] = field(default_factory=list)
    implementation_status: str = "Implemented"
    runtime_status: str = "Experimental"


@dataclass
class DataQualityRecord(GovernanceEnvelope):
    grade: str = "B"
    blocking: bool = False
    flags: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    implementation_status: str = "Implemented"
    runtime_status: str = "Experimental"


@dataclass
class TradeEvent(GovernanceEnvelope):
    symbol: str = ""
    exchange_timestamp: str = ""
    vendor_timestamp: str = ""
    receive_timestamp: str = ""
    price: float = 0.0
    size: float = 0.0
    direction: str = "unknown"
    direction_origin: str = "inferred"
    implementation_status: str = "Implemented"
    runtime_status: str = "Interface"


@dataclass
class OrderEvent(GovernanceEnvelope):
    symbol: str = ""
    exchange_timestamp: str = ""
    vendor_timestamp: str = ""
    receive_timestamp: str = ""
    side: str = ""
    price: float = 0.0
    size: float = 0.0
    order_id: str = ""
    event_type: str = "new"
    implementation_status: str = "Implemented"
    runtime_status: str = "Interface"


@dataclass
class BookSnapshot(GovernanceEnvelope):
    symbol: str = ""
    exchange_timestamp: str = ""
    vendor_timestamp: str = ""
    receive_timestamp: str = ""
    depth_levels: int = 0
    bids: list[dict[str, Any]] = field(default_factory=list)
    asks: list[dict[str, Any]] = field(default_factory=list)
    implementation_status: str = "Implemented"
    runtime_status: str = "Interface"


@dataclass
class AuctionSnapshot(GovernanceEnvelope):
    symbol: str = ""
    exchange_timestamp: str = ""
    vendor_timestamp: str = ""
    receive_timestamp: str = ""
    session_phase: str = "09:25_final_only"
    indicative_price: float = 0.0
    indicative_volume: float = 0.0
    implementation_status: str = "Implemented"
    runtime_status: str = "Mock"


@dataclass
class SecurityStatusEvent(GovernanceEnvelope):
    symbol: str = ""
    exchange: str = "SZSE"
    board: str = ""
    security_type: str = "stock"
    risk_warning_type: str = ""
    listing_stage: str = ""
    special_status: str = ""
    suspension_status: str = ""
    upper_limit_price: float = 0.0
    lower_limit_price: float = 0.0
    implementation_status: str = "Implemented"
    runtime_status: str = "Interface"


@dataclass
class CorporateActionEvent(GovernanceEnvelope):
    symbol: str = ""
    action_type: str = ""
    effective_date: str = ""
    description: str = ""
    adjustment_factor: float = 1.0
    implementation_status: str = "Implemented"
    runtime_status: str = "Interface"


@dataclass
class FeatureDefinition(GovernanceEnvelope):
    name: str = ""
    category: str = ""
    formula_summary: str = ""
    inputs: list[str] = field(default_factory=list)
    feature_version: str = "v0.1"
    implementation_status: str = "Implemented"
    runtime_status: str = "Experimental"


@dataclass
class DatasetSnapshot(GovernanceEnvelope):
    dataset_name: str = ""
    layer: str = "normalized"
    dataset_path: str = ""
    row_count: int = 0
    snapshot_hash: str = ""
    implementation_status: str = "Implemented"
    runtime_status: str = "Experimental"


@dataclass
class ResearchHypothesis(GovernanceEnvelope):
    hypothesis_name: str = ""
    statement: str = ""
    domain: str = "trading"
    invalidation_conditions: list[str] = field(default_factory=list)
    implementation_status: str = "Implemented"
    runtime_status: str = "Experimental"


@dataclass
class ExperimentRecord(GovernanceEnvelope):
    experiment_name: str = ""
    hypothesis_id: str = ""
    dataset_snapshot_id: str = ""
    result_summary: str = ""
    implementation_status: str = "Implemented"
    runtime_status: str = "Experimental"


@dataclass
class ModelRecord(GovernanceEnvelope):
    model_name: str = ""
    model_type: str = "heuristic"
    version: str = "v0.1"
    training_dataset_id: str = ""
    implementation_status: str = "Implemented"
    runtime_status: str = "Interface"


@dataclass
class StrategyLifecycleRecord(GovernanceEnvelope):
    strategy_id: str = ""
    lifecycle_state: str = "candidate"
    quality_action: str = "keep"
    approved_by: str = ""
    rollback_point: str = ""
    implementation_status: str = "Implemented"
    runtime_status: str = "Experimental"


@dataclass
class OrderIntent(GovernanceEnvelope):
    symbol: str = ""
    side: str = "wait"
    quantity: float = 0.0
    rationale: str = ""
    implementation_status: str = "Implemented"
    runtime_status: str = "Interface"


@dataclass
class ExecutionRecord(GovernanceEnvelope):
    symbol: str = ""
    side: str = ""
    quantity: float = 0.0
    avg_price: float = 0.0
    execution_status: str = "not_sent"
    implementation_status: str = "Implemented"
    runtime_status: str = "Not Implemented Yet"


@dataclass
class PositionLot(GovernanceEnvelope):
    symbol: str = ""
    quantity: float = 0.0
    sellable_quantity: float = 0.0
    average_cost: float = 0.0
    available_cash_for_trading: float = 0.0
    withdrawable_cash: float = 0.0
    implementation_status: str = "Implemented"
    runtime_status: str = "Interface"


@dataclass
class RiskEvent(GovernanceEnvelope):
    symbol: str = ""
    risk_type: str = ""
    severity: str = "medium"
    blocking: bool = False
    description: str = ""
    implementation_status: str = "Implemented"
    runtime_status: str = "Experimental"


@dataclass
class CapabilityDescriptor:
    adapter_name: str = ""
    source_key: str = ""
    source_family: str = ""
    market: str = "CN-A"
    symbol_scope: str = ""
    timeframe_scope: str = ""
    implementation_status: str = "Implemented"
    capabilities: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class AdapterHealthStatus:
    adapter_name: str = ""
    source_key: str = ""
    health_status: str = "healthy"
    blocking: bool = False
    last_checked_at: str = field(default_factory=now_iso)
    notes: list[str] = field(default_factory=list)
    implementation_status: str = "Implemented"


@dataclass
class SourceReliabilityProfile:
    source_key: str = ""
    authority_order: int = 999
    reliability_score: float = 0.5
    quality_grade: str = "B"
    point_in_time_status: str = "partial"
    license_scope: str = "local_research"
    fallback: str = ""
    implementation_status: str = "Implemented"


@dataclass
class DataLayerPolicy:
    layer_key: str = ""
    description: str = ""
    storage_target: str = ""
    writer: str = ""
    reader: str = ""
    immutable: bool = False
    retention: str = ""
    recomputable: bool = False
    tracked_in_git: bool = False
    sensitive: bool = False
    stores: list[str] = field(default_factory=list)
    does_not_store: list[str] = field(default_factory=list)


def _capability(
    *,
    status: str,
    field_coverage: list[str],
    time_coverage: str,
    history_start: str,
    latency_profile: str,
    quality_grade: str,
    license_scope: str,
    fallback: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "field_coverage": list(field_coverage),
        "time_coverage": time_coverage,
        "history_start": history_start,
        "latency_profile": latency_profile,
        "quality_grade": quality_grade,
        "license_scope": license_scope,
        "fallback": fallback,
    }


def build_data_layer_policies(root: str | Path) -> dict[str, DataLayerPolicy]:
    root = Path(root)
    sqlite_target = str(root / "data" / "super_brain_v01.sqlite").replace("\\", "/")
    return {
        "raw": DataLayerPolicy(
            layer_key="raw",
            description="Vendor-native payloads and snapshots kept append-only for replay and audit.",
            storage_target=str(root / "data" / "raw").replace("\\", "/"),
            writer="WorkBuddy runtime adapters / local ingest bridges",
            reader="normalizers, replay adapters, forensic audit",
            immutable=True,
            retention="long_term_append_only",
            recomputable=False,
            tracked_in_git=False,
            sensitive=True,
            stores=[
                "vendor response payloads",
                "snapshot samples",
                "connector raw dumps",
            ],
            does_not_store=[
                "normalized strategy-ready fields",
                "hand-edited conclusions",
            ],
        ),
        "normalized": DataLayerPolicy(
            layer_key="normalized",
            description="Supplier-agnostic market objects with lineage back to raw inputs.",
            storage_target=f"{sqlite_target}#sources,market_data_records,price_bars",
            writer="foundation adapters and trading-domain normalizers",
            reader="feature builders, replay, validation, governance",
            immutable=False,
            retention="long_term_versioned",
            recomputable=True,
            tracked_in_git=False,
            sensitive=True,
            stores=[
                "SourceRecord",
                "MarketDataRecord",
                "PriceBar",
                "lineage references",
            ],
            does_not_store=[
                "vendor-only field names at strategy surface",
                "presentation-only markdown summaries",
            ],
        ),
        "features": DataLayerPolicy(
            layer_key="features",
            description="Derived features with feature_time, available_time, and versioned inputs.",
            storage_target=f"{sqlite_target}#feature_sets",
            writer="feature pipelines",
            reader="strategy selection, validation, research replay",
            immutable=False,
            retention="recomputable_with_snapshot_reference",
            recomputable=True,
            tracked_in_git=False,
            sensitive=False,
            stores=[
                "FeatureSet",
                "feature_version",
                "input snapshot references",
            ],
            does_not_store=[
                "human-readable only reports",
                "raw vendor payload blobs",
            ],
        ),
        "signals": DataLayerPolicy(
            layer_key="signals",
            description="Probabilistic outputs, decisions, forecasts, and validation surfaces.",
            storage_target=(
                f"{sqlite_target}#signal_records,trade_decisions,decisions,forecasts,"
                "validation_reports,backtest_results,strategy_reviews"
            ),
            writer="strategy runners, governance, replay validation",
            reader="research queue, bulletin sync, review loop",
            immutable=False,
            retention="versioned_reviewable",
            recomputable=True,
            tracked_in_git=False,
            sensitive=False,
            stores=[
                "probabilities",
                "confidence",
                "evidence links",
                "validation verdicts",
            ],
            does_not_store=[
                "single-source truth of raw facts",
                "secret credentials",
            ],
        ),
        "reports": DataLayerPolicy(
            layer_key="reports",
            description="Human-readable summaries, docs, and bulletin-facing artifacts.",
            storage_target=(
                f"{str(root / 'bulletin').replace('\\', '/')} + "
                f"{str(root / 'docs').replace('\\', '/')} + "
                f"{str(root / 'reports').replace('\\', '/')}"
            ),
            writer="bulletin sync, governance docs, review summaries",
            reader="human reviewers, Codex, ChatGPT, WorkBuddy",
            immutable=False,
            retention="keep_latest_plus_history",
            recomputable=True,
            tracked_in_git=True,
            sensitive=False,
            stores=[
                "announcement board",
                "governance docs",
                "report markdown",
            ],
            does_not_store=[
                "only copy of normalized facts",
                "vendor raw payloads",
            ],
        ),
        "runtime_logs": DataLayerPolicy(
            layer_key="runtime_logs",
            description="Operational logs, audit events, retries, latency, and recovery traces.",
            storage_target=(
                f"{str(root / 'data' / 'audit' / 'events.jsonl').replace('\\', '/')} + "
                f"{str(root / 'logs').replace('\\', '/')}"
            ),
            writer="BrainStore audit log, runtime bridges, health checks",
            reader="operators, forensic review, failure analysis",
            immutable=True,
            retention="append_only_with_rotation",
            recomputable=False,
            tracked_in_git=False,
            sensitive=True,
            stores=[
                "audit events",
                "error traces",
                "latency and recovery markers",
            ],
            does_not_store=[
                "canonical market facts",
                "strategy-ready normalized tables",
            ],
        ),
    }


def build_object_model_bindings() -> dict[str, list[dict[str, Any]]]:
    return {
        "evidence_and_source": [
            {"concept": "SourceRecord", "binding": "brain_core.contracts.SourceRecord", "implementation_status": "Implemented", "runtime_status": "Implemented"},
            {"concept": "EvidenceItem", "binding": "brain_core.contracts.EvidenceItem", "implementation_status": "Implemented", "runtime_status": "Implemented"},
            {"concept": "DataLineageRecord", "binding": "brain_core.foundation_data_governance.DataLineageRecord", "implementation_status": "Implemented", "runtime_status": "Experimental"},
            {"concept": "DataQualityRecord", "binding": "brain_core.foundation_data_governance.DataQualityRecord", "implementation_status": "Implemented", "runtime_status": "Experimental"},
        ],
        "market_data": [
            {"concept": "MarketDataRecord", "binding": "brain_core.contracts.MarketDataRecord", "implementation_status": "Implemented", "runtime_status": "Experimental"},
            {"concept": "TradeEvent", "binding": "brain_core.foundation_data_governance.TradeEvent", "implementation_status": "Implemented", "runtime_status": "Interface"},
            {"concept": "OrderEvent", "binding": "brain_core.foundation_data_governance.OrderEvent", "implementation_status": "Implemented", "runtime_status": "Interface"},
            {"concept": "BookSnapshot", "binding": "brain_core.foundation_data_governance.BookSnapshot", "implementation_status": "Implemented", "runtime_status": "Interface"},
            {"concept": "AuctionSnapshot", "binding": "brain_core.foundation_data_governance.AuctionSnapshot", "implementation_status": "Implemented", "runtime_status": "Mock"},
            {"concept": "PriceBar", "binding": "brain_core.contracts.PriceBar", "implementation_status": "Implemented", "runtime_status": "Implemented"},
            {"concept": "SecurityStatusEvent", "binding": "brain_core.foundation_data_governance.SecurityStatusEvent", "implementation_status": "Implemented", "runtime_status": "Interface"},
            {"concept": "CorporateActionEvent", "binding": "brain_core.foundation_data_governance.CorporateActionEvent", "implementation_status": "Implemented", "runtime_status": "Interface"},
        ],
        "research_and_features": [
            {"concept": "FeatureSet", "binding": "brain_core.contracts.FeatureSet", "implementation_status": "Implemented", "runtime_status": "Implemented"},
            {"concept": "FeatureDefinition", "binding": "brain_core.foundation_data_governance.FeatureDefinition", "implementation_status": "Implemented", "runtime_status": "Experimental"},
            {"concept": "DatasetSnapshot", "binding": "brain_core.foundation_data_governance.DatasetSnapshot", "implementation_status": "Implemented", "runtime_status": "Experimental"},
            {"concept": "ResearchHypothesis", "binding": "brain_core.foundation_data_governance.ResearchHypothesis", "implementation_status": "Implemented", "runtime_status": "Experimental"},
            {"concept": "ExperimentRecord", "binding": "brain_core.foundation_data_governance.ExperimentRecord", "implementation_status": "Implemented", "runtime_status": "Experimental"},
        ],
        "validation_and_decision": [
            {"concept": "BacktestResult", "binding": "brain_core.contracts.BacktestResult", "implementation_status": "Implemented", "runtime_status": "Implemented"},
            {"concept": "ValidationReport", "binding": "brain_core.contracts.ValidationReport", "implementation_status": "Implemented", "runtime_status": "Implemented"},
            {"concept": "DecisionRecord", "binding": "brain_core.contracts.DecisionRecord", "implementation_status": "Implemented", "runtime_status": "Implemented"},
            {"concept": "ForecastRecord", "binding": "brain_core.contracts.ForecastRecord", "implementation_status": "Implemented", "runtime_status": "Implemented"},
            {"concept": "ModelRecord", "binding": "brain_core.foundation_data_governance.ModelRecord", "implementation_status": "Implemented", "runtime_status": "Interface"},
            {"concept": "StrategyLifecycleRecord", "binding": "brain_core.foundation_data_governance.StrategyLifecycleRecord", "implementation_status": "Implemented", "runtime_status": "Experimental"},
        ],
        "trade_and_review": [
            {"concept": "OrderIntent", "binding": "brain_core.foundation_data_governance.OrderIntent", "implementation_status": "Implemented", "runtime_status": "Interface"},
            {"concept": "ExecutionRecord", "binding": "brain_core.foundation_data_governance.ExecutionRecord", "implementation_status": "Implemented", "runtime_status": "Not Implemented Yet"},
            {"concept": "PositionLot", "binding": "brain_core.foundation_data_governance.PositionLot", "implementation_status": "Implemented", "runtime_status": "Interface"},
            {"concept": "TradeJournal", "binding": "brain_core.contracts.TradeJournal", "implementation_status": "Implemented", "runtime_status": "Implemented"},
            {"concept": "RiskEvent", "binding": "brain_core.foundation_data_governance.RiskEvent", "implementation_status": "Implemented", "runtime_status": "Experimental"},
            {"concept": "SelfEvolutionLog", "binding": "brain_core.contracts.SelfEvolutionLog", "implementation_status": "Implemented", "runtime_status": "Implemented"},
        ],
    }


def _default_capabilities(*, history_start: str = "", fallback: str = "no_signal") -> dict[str, dict[str, Any]]:
    return {
        "realtime_snapshot": _capability(status="unavailable", field_coverage=[], time_coverage="none", history_start="", latency_profile="offline", quality_grade="C", license_scope="local_research", fallback=fallback),
        "depth_levels": _capability(status="unavailable", field_coverage=[], time_coverage="none", history_start="", latency_profile="offline", quality_grade="C", license_scope="local_research", fallback=fallback),
        "trade_by_trade": _capability(status="unavailable", field_coverage=[], time_coverage="none", history_start="", latency_profile="offline", quality_grade="C", license_scope="local_research", fallback=fallback),
        "market_by_order": _capability(status="unavailable", field_coverage=[], time_coverage="none", history_start="", latency_profile="offline", quality_grade="C", license_scope="local_research", fallback=fallback),
        "order_id": _capability(status="unavailable", field_coverage=[], time_coverage="none", history_start="", latency_profile="offline", quality_grade="C", license_scope="local_research", fallback=fallback),
        "cancel_event": _capability(status="unavailable", field_coverage=[], time_coverage="none", history_start="", latency_profile="offline", quality_grade="C", license_scope="local_research", fallback=fallback),
        "modify_event": _capability(status="unavailable", field_coverage=[], time_coverage="none", history_start="", latency_profile="offline", quality_grade="C", license_scope="local_research", fallback=fallback),
        "sequence_no": _capability(status="unavailable", field_coverage=[], time_coverage="none", history_start="", latency_profile="offline", quality_grade="C", license_scope="local_research", fallback=fallback),
        "channel_no": _capability(status="unavailable", field_coverage=[], time_coverage="none", history_start="", latency_profile="offline", quality_grade="C", license_scope="local_research", fallback=fallback),
        "auction_snapshot": _capability(status="unavailable", field_coverage=[], time_coverage="none", history_start="", latency_profile="offline", quality_grade="C", license_scope="local_research", fallback=fallback),
        "auction_order_event": _capability(status="unavailable", field_coverage=[], time_coverage="none", history_start="", latency_profile="offline", quality_grade="C", license_scope="local_research", fallback=fallback),
        "historical_replay": _capability(status="unavailable", field_coverage=[], time_coverage="none", history_start=history_start, latency_profile="offline", quality_grade="C", license_scope="local_research", fallback=fallback),
        "point_in_time": _capability(status="partial", field_coverage=["effective_at", "available_at"], time_coverage="derived", history_start=history_start, latency_profile="offline", quality_grade="B", license_scope="local_research", fallback=fallback),
        "local_persistence": _capability(status="partial", field_coverage=["path"], time_coverage="local", history_start=history_start, latency_profile="offline", quality_grade="B", license_scope="local_research", fallback=fallback),
        "source_latency_metadata": _capability(status="partial", field_coverage=["receive_timestamp"], time_coverage="partial", history_start=history_start, latency_profile="offline", quality_grade="B", license_scope="local_research", fallback=fallback),
        "correction_stream": _capability(status="unverified", field_coverage=[], time_coverage="unknown", history_start="", latency_profile="unknown", quality_grade="C", license_scope="unknown", fallback=fallback),
        "recovery_support": _capability(status="unverified", field_coverage=[], time_coverage="unknown", history_start="", latency_profile="unknown", quality_grade="C", license_scope="unknown", fallback=fallback),
    }


class MarketDataAdapter:
    adapter_name = "market_data_adapter"
    source_key = "generic_source"
    source_family = "generic"
    implementation_status = "Interface"

    def __init__(self, *, root: str | Path, symbol: str, timeframe: str):
        self.root = Path(root)
        self.symbol = symbol
        self.timeframe = timeframe

    def capability_descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            adapter_name=self.adapter_name,
            source_key=self.source_key,
            source_family=self.source_family,
            symbol_scope=self.symbol,
            timeframe_scope=self.timeframe,
            implementation_status=self.implementation_status,
            capabilities=_default_capabilities(),
        )

    def health_status(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(
            adapter_name=self.adapter_name,
            source_key=self.source_key,
            health_status="declared_only",
            blocking=False,
            notes=["Adapter schema exists, but runtime behavior is not fully wired."],
        )

    def reliability_profile(self) -> SourceReliabilityProfile:
        return SourceReliabilityProfile(
            source_key=self.source_key,
            authority_order=999,
            reliability_score=0.45,
            quality_grade="C",
            point_in_time_status="unverified",
            license_scope="unknown",
            fallback="no_signal",
        )


class TdxMcpSnapshotAdapter(MarketDataAdapter):
    adapter_name = "TdxMcpSnapshotAdapter"
    source_key = "tdx_mcp_snapshot"
    source_family = "tdx"
    implementation_status = "Implemented"

    def capability_descriptor(self) -> CapabilityDescriptor:
        caps = _default_capabilities(fallback="degrade_to_snapshot_only")
        caps["realtime_snapshot"] = _capability(
            status="available",
            field_coverage=["price", "change_pct", "volume", "amount", "inside", "outside", "quote_ts"],
            time_coverage="intraday_snapshot",
            history_start="runtime_only",
            latency_profile="bridge_defined",
            quality_grade="B",
            license_scope="local_research",
            fallback="degrade_to_snapshot_only",
        )
        caps["depth_levels"] = _capability(
            status="partial",
            field_coverage=["bids", "asks"],
            time_coverage="snapshot_only",
            history_start="runtime_only",
            latency_profile="bridge_defined",
            quality_grade="B",
            license_scope="local_research",
            fallback="treat_depth_as_snapshot_only",
        )
        caps["l2_aggregate"] = _capability(
            status="partial",
            field_coverage=[
                "L2TicNum",
                "L2OrderNum",
                "TotalBVol",
                "TotalSVol",
                "BCancel",
                "SCancel",
                "Zjl",
                "Zjl_HB",
                "OpenAmo",
                "OpenZTBuy",
                "Wtb",
                "FzAmo",
                "VOpenZAF",
            ],
            time_coverage="intraday_aggregate_snapshot",
            history_start="runtime_only",
            latency_profile="bridge_or_tdxquant_defined",
            quality_grade="B",
            license_scope="local_research",
            fallback="degrade_to_snapshot_only",
        )
        caps["true_ddx_ddy"] = _capability(
            status="unverified",
            field_coverage=[],
            time_coverage="none",
            history_start="",
            latency_profile="unknown",
            quality_grade="C",
            license_scope="unknown",
            fallback="treat_vendor_fund_flow_as_vendor_defined_only",
        )
        caps["raw_trade_tick"] = _capability(
            status="unverified",
            field_coverage=[],
            time_coverage="none",
            history_start="",
            latency_profile="unknown",
            quality_grade="C",
            license_scope="unknown",
            fallback="block_tick_strategies",
        )
        caps["raw_order_event"] = _capability(
            status="unverified",
            field_coverage=[],
            time_coverage="none",
            history_start="",
            latency_profile="unknown",
            quality_grade="C",
            license_scope="unknown",
            fallback="block_order_event_strategies",
        )
        caps["local_persistence"] = _capability(
            status="partial",
            field_coverage=["source_record", "sample_payload"],
            time_coverage="runtime_snapshot",
            history_start="runtime_only",
            latency_profile="bridge_defined",
            quality_grade="B",
            license_scope="local_research",
            fallback="persist_sample_only",
        )
        return CapabilityDescriptor(
            adapter_name=self.adapter_name,
            source_key=self.source_key,
            source_family=self.source_family,
            symbol_scope=self.symbol,
            timeframe_scope=self.timeframe,
            implementation_status=self.implementation_status,
            capabilities=caps,
        )

    def health_status(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(
            adapter_name=self.adapter_name,
            source_key=self.source_key,
            health_status="schema_ready_runtime_external",
            blocking=False,
            notes=[
                "Uses external TDX MCP / TdxQuant field mapping when WorkBuddy provides real samples.",
                "Current verified path is five-level snapshot plus L2 aggregate fields; true DDX/DDY remains unverified.",
                "Must not treat payload_injected_sample as live-readiness proof.",
            ],
        )

    def reliability_profile(self) -> SourceReliabilityProfile:
        return SourceReliabilityProfile(
            source_key=self.source_key,
            authority_order=1,
            reliability_score=0.9,
            quality_grade="A",
            point_in_time_status="partial",
            license_scope="local_research",
            fallback="degrade_to_snapshot_only",
        )


class HistoricalTradeReplayAdapter(MarketDataAdapter):
    adapter_name = "HistoricalTradeReplayAdapter"
    source_key = "historical_trade_replay"
    source_family = "local_file"
    implementation_status = "Implemented"

    def capability_descriptor(self) -> CapabilityDescriptor:
        caps = _default_capabilities(history_start="file_dependent", fallback="block_to_no_signal")
        caps["historical_replay"] = _capability(
            status="available",
            field_coverage=["timestamp", "open", "high", "low", "close", "volume", "amount"],
            time_coverage="file_window",
            history_start="file_dependent",
            latency_profile="offline_local",
            quality_grade="B",
            license_scope="local_research",
            fallback="block_to_no_signal",
        )
        caps["point_in_time"] = _capability(
            status="partial",
            field_coverage=["effective_at", "available_at", "exchange_timestamp"],
            time_coverage="end_of_bar_visible",
            history_start="file_dependent",
            latency_profile="offline_local",
            quality_grade="B",
            license_scope="local_research",
            fallback="end_of_bar_only",
        )
        caps["local_persistence"] = _capability(
            status="available",
            field_coverage=["path", "lineage"],
            time_coverage="full_file",
            history_start="file_dependent",
            latency_profile="offline_local",
            quality_grade="A",
            license_scope="local_research",
            fallback="block_to_no_signal",
        )
        return CapabilityDescriptor(
            adapter_name=self.adapter_name,
            source_key=self.source_key,
            source_family=self.source_family,
            symbol_scope=self.symbol,
            timeframe_scope=self.timeframe,
            implementation_status=self.implementation_status,
            capabilities=caps,
        )

    def health_status(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(
            adapter_name=self.adapter_name,
            source_key=self.source_key,
            health_status="healthy_if_file_exists",
            blocking=False,
            notes=[
                "Normalizes local csv/json replay sources into mother-system objects.",
                "Point-in-time semantics are bar-close only unless stronger timestamps arrive.",
            ],
        )

    def reliability_profile(self) -> SourceReliabilityProfile:
        return SourceReliabilityProfile(
            source_key=self.source_key,
            authority_order=4,
            reliability_score=0.78,
            quality_grade="B",
            point_in_time_status="partial",
            license_scope="local_research",
            fallback="block_to_no_signal",
        )

    def normalize(self, data_path: str | Path) -> dict[str, Any]:
        path = Path(data_path)
        if not path.exists():
            raise FileNotFoundError(path)
        rows, provider_field_map = self._load_rows(path)
        if not rows:
            raise ValueError(f"No bars found in {path}")
        original_ts = [str(row["ts"]) for row in rows]
        sorted_rows = sorted(rows, key=lambda row: str(row["ts"]))
        quality_flags: list[dict[str, Any]] = []
        if original_ts != [str(row["ts"]) for row in sorted_rows]:
            quality_flags.append({"flag": "out_of_order", "blocking": False})
        seen: set[str] = set()
        duplicates = False
        for row in sorted_rows:
            ts = str(row["ts"])
            if ts in seen:
                duplicates = True
            seen.add(ts)
        if duplicates:
            quality_flags.append({"flag": "duplicate", "blocking": True})
        if any(float(row.get("amount", 0.0) or 0.0) == 0.0 for row in sorted_rows):
            quality_flags.append({"flag": "field_semantics_unverified", "blocking": False, "field": "amount"})
        if not all(str(row["ts"]).strip() for row in sorted_rows):
            quality_flags.append({"flag": "timestamp_regression", "blocking": True})

        source_id = new_id("src", f"{self.source_key}:{path}:{self.symbol}:{self.timeframe}")
        market_data_id = new_id("mdata", f"{source_id}:dataset")
        source_record = SourceRecord(
            id=source_id,
            source_type="historical_trade_replay",
            title=path.name,
            uri=str(path).replace("\\", "/"),
            reliability=0.78,
            metadata={
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "provider_name": "local_file",
                "provider_payload_type": path.suffix.lower().lstrip("."),
                "symbol_scope": self.symbol,
                "timeframe_scope": self.timeframe,
                "provider_field_map": provider_field_map,
                "quality_flags": list(quality_flags),
                "implementation_status": "Implemented",
            },
        )
        market_data_record = MarketDataRecord(
            id=market_data_id,
            source_id=source_id,
            symbol=self.symbol,
            market="CN-A",
            timeframe=self.timeframe,
            start_at=str(sorted_rows[0]["ts"]),
            end_at=str(sorted_rows[-1]["ts"]),
            bar_count=len(sorted_rows),
            record_path=str(path).replace("\\", "/"),
            normalization_version=SCHEMA_VERSION,
            quality_score=0.82 if not any(flag.get("blocking") for flag in quality_flags) else 0.55,
            evidence_level="normalized_dataset",
            source_reliability=source_record.reliability,
            freshness=0.7,
            validation_status="normalized",
            out_of_sample_result="not_run",
            status="Experimental",
            metadata={
                "schema_version": SCHEMA_VERSION,
                "effective_at": str(sorted_rows[0]["ts"]),
                "available_at": str(sorted_rows[-1]["ts"]),
                "lineage": {
                    "raw_path": str(path).replace("\\", "/"),
                    "provider_name": "local_file",
                    "provider_field_map": provider_field_map,
                },
                "quality_flags": list(quality_flags),
                "provider_fields": sorted(provider_field_map.keys()),
                "three_timestamps_mode": "bar_close_only",
                "implementation_status": "Implemented",
            },
        )
        price_bars: list[PriceBar] = []
        for index, row in enumerate(sorted_rows):
            ts = str(row["ts"])
            bar = PriceBar(
                id=new_id("pbar", f"{market_data_id}:{ts}:{index}"),
                market_data_id=market_data_id,
                symbol=self.symbol,
                ts=ts,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                amount=float(row.get("amount", 0.0) or 0.0),
                timeframe=self.timeframe,
                quality_score=market_data_record.quality_score,
                evidence_level="normalized_bar",
                source_reliability=source_record.reliability,
                freshness=0.7,
                validation_status="normalized",
                out_of_sample_result="not_run",
                status="Experimental",
                metadata={
                    "schema_version": SCHEMA_VERSION,
                    "exchange_timestamp": ts,
                    "vendor_timestamp": ts,
                    "receive_timestamp": "",
                    "effective_at": ts,
                    "available_at": ts,
                    "lineage": {
                        "raw_path": str(path).replace("\\", "/"),
                        "row_index": index,
                        "provider_fields": provider_field_map,
                    },
                    "quality_flags": list(quality_flags),
                    "point_in_time_mode": "bar_close_only",
                },
            )
            price_bars.append(bar)

        lineage = DataLineageRecord(
            object_id=new_id("lineage", f"{market_data_id}:{path}"),
            effective_at=market_data_record.start_at,
            available_at=market_data_record.end_at,
            source_id=source_id,
            lineage={
                "market_data_id": market_data_id,
                "bar_count": len(price_bars),
            },
            quality_flags=list(quality_flags),
            provider_name="local_file",
            provider_payload_type=path.suffix.lower().lstrip("."),
            raw_ref=str(path).replace("\\", "/"),
            normalized_ref=f"sqlite://market_data_records/{market_data_id}",
            provider_field_map=provider_field_map,
            transformation_steps=[
                "load_local_file",
                "normalize_bar_columns",
                "derive_bar_close_available_at",
            ],
            runtime_status="Experimental",
        )
        quality = DataQualityRecord(
            object_id=new_id("quality", f"{market_data_id}:{path}"),
            effective_at=market_data_record.start_at,
            available_at=market_data_record.end_at,
            source_id=source_id,
            lineage={"market_data_id": market_data_id},
            quality_flags=list(quality_flags),
            grade="A" if not quality_flags else ("B" if not any(flag.get("blocking") for flag in quality_flags) else "C"),
            blocking=any(bool(flag.get("blocking")) for flag in quality_flags),
            flags=list(quality_flags),
            summary=self._quality_summary(quality_flags, len(price_bars)),
            runtime_status="Experimental",
        )
        return {
            "source_record": to_dict(source_record),
            "market_data_record": to_dict(market_data_record),
            "price_bars": [to_dict(bar) for bar in price_bars],
            "lineage_record": to_dict(lineage),
            "quality_record": to_dict(quality),
            "capability_descriptor": to_dict(self.capability_descriptor()),
            "adapter_health_status": to_dict(self.health_status()),
            "source_reliability_profile": to_dict(self.reliability_profile()),
            "implementation_status": "Implemented",
        }

    def _load_rows(self, path: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                raw_rows = [dict(row) for row in reader]
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                raw_rows = [dict(item) for item in data]
            elif isinstance(data, dict):
                candidate = data.get("bars") or data.get("data") or data.get("items") or []
                raw_rows = [dict(item) for item in candidate]
            else:
                raw_rows = []
        rows: list[dict[str, Any]] = []
        provider_field_map: dict[str, str] = {}
        for item in raw_rows:
            normalized = self._normalize_row(item)
            rows.append(normalized)
            provider_field_map.update({k: normalized_key for k, normalized_key in normalized["provider_fields"].items()})
        stripped_rows = []
        for row in rows:
            clean = dict(row)
            clean.pop("provider_fields", None)
            stripped_rows.append(clean)
        return stripped_rows, provider_field_map

    def _normalize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        lookup = {str(key).strip().lower(): value for key, value in row.items()}
        ts_key = next((key for key in ("date", "datetime", "time", "ts", "timestamp") if key in lookup), "")
        if not ts_key:
            raise ValueError("Historical replay row is missing a timestamp-like field")
        def pick(*names: str, default: float = 0.0) -> float:
            for name in names:
                if name in lookup and str(lookup[name]).strip():
                    return float(lookup[name])
            return float(default)
        provider_fields = {
            key: {
                ts_key: "ts",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
                "amount": "amount",
                "turnover": "amount",
            }.get(key, key)
            for key in lookup
        }
        return {
            "ts": str(lookup[ts_key]).strip(),
            "open": pick("open", "o"),
            "high": pick("high", "h"),
            "low": pick("low", "l"),
            "close": pick("close", "c"),
            "volume": pick("volume", "vol"),
            "amount": pick("amount", "turnover", default=0.0),
            "provider_fields": provider_fields,
        }

    def _quality_summary(self, flags: list[dict[str, Any]], bar_count: int) -> str:
        if not flags:
            return f"Historical replay normalization is clean for {bar_count} bars."
        labels = ",".join(str(flag.get("flag", "")) for flag in flags)
        return f"Historical replay normalization produced {bar_count} bars with flags={labels}."


class MockMboAdapter(MarketDataAdapter):
    adapter_name = "MockMboAdapter"
    source_key = "mock_mbo"
    source_family = "mock"
    implementation_status = "Implemented"

    def capability_descriptor(self) -> CapabilityDescriptor:
        caps = _default_capabilities(fallback="no_signal")
        caps["market_by_order"] = _capability(
            status="partial",
            field_coverage=["bids", "asks", "synthetic_order_count"],
            time_coverage="mock_snapshot",
            history_start="mock_only",
            latency_profile="offline_mock",
            quality_grade="C",
            license_scope="local_research",
            fallback="do_not_compute_true_cancel_rate",
        )
        caps["depth_levels"] = _capability(
            status="partial",
            field_coverage=["bids", "asks"],
            time_coverage="mock_snapshot",
            history_start="mock_only",
            latency_profile="offline_mock",
            quality_grade="C",
            license_scope="local_research",
            fallback="snapshot_only",
        )
        caps["local_persistence"] = _capability(
            status="available",
            field_coverage=["sample_payload"],
            time_coverage="mock_snapshot",
            history_start="mock_only",
            latency_profile="offline_mock",
            quality_grade="B",
            license_scope="local_research",
            fallback="no_signal",
        )
        return CapabilityDescriptor(
            adapter_name=self.adapter_name,
            source_key=self.source_key,
            source_family=self.source_family,
            symbol_scope=self.symbol,
            timeframe_scope=self.timeframe,
            implementation_status=self.implementation_status,
            capabilities=caps,
        )

    def health_status(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(
            adapter_name=self.adapter_name,
            source_key=self.source_key,
            health_status="mock_only",
            blocking=False,
            notes=[
                "MBO schema exists for contract testing only.",
                "Do not calculate real cancel-rate, modify-rate, or order-id persistence from this adapter.",
            ],
        )


class MockAuctionAdapter(MarketDataAdapter):
    adapter_name = "MockAuctionAdapter"
    source_key = "mock_auction"
    source_family = "mock"
    implementation_status = "Implemented"

    def capability_descriptor(self) -> CapabilityDescriptor:
        caps = _default_capabilities(fallback="analyze_0925_final_only")
        caps["auction_snapshot"] = _capability(
            status="available",
            field_coverage=["indicative_price", "indicative_volume", "session_phase"],
            time_coverage="09:25_final_only",
            history_start="mock_only",
            latency_profile="offline_mock",
            quality_grade="C",
            license_scope="local_research",
            fallback="analyze_0925_final_only",
        )
        caps["auction_order_event"] = _capability(
            status="unavailable",
            field_coverage=[],
            time_coverage="none",
            history_start="",
            latency_profile="offline_mock",
            quality_grade="C",
            license_scope="local_research",
            fallback="analyze_0925_final_only",
        )
        return CapabilityDescriptor(
            adapter_name=self.adapter_name,
            source_key=self.source_key,
            source_family=self.source_family,
            symbol_scope=self.symbol,
            timeframe_scope=self.timeframe,
            implementation_status=self.implementation_status,
            capabilities=caps,
        )

    def health_status(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(
            adapter_name=self.adapter_name,
            source_key=self.source_key,
            health_status="mock_only",
            blocking=False,
            notes=[
                "Auction contract is available for final-result semantics only.",
                "No auction order sequence is exposed in this phase.",
            ],
        )


class FoundationDataGovernanceV01:
    def __init__(self, store, board, evolution, root: str | Path, trading):
        self.store = store
        self.board = board
        self.evolution = evolution
        self.root = Path(root)
        self.trading = trading

    def report(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        symbol = str(payload.get("symbol", "300418") or "300418").upper()
        timeframe = str(payload.get("timeframe", "1d") or "1d")
        data_path = str(payload.get("data_path", "") or "").strip()
        writeback = bool(payload.get("writeback", True))
        object_model = build_object_model_bindings()
        data_layers = {key: to_dict(value) for key, value in build_data_layer_policies(self.root).items()}
        adapter_catalog = self._adapter_catalog(symbol=symbol, timeframe=timeframe, data_path=data_path)
        branch_or_worktree = self._branch_or_worktree_state()
        reused_existing_components = [
            "brain_core/contracts.py",
            "brain_core/storage.py",
            "brain_core/service.py",
            "brain_core/trading_domain.py",
            "bulletin/super-second-brain-v01-board.md",
            "data/super_brain_v01.sqlite",
            "data/raw",
        ]
        new_components = [
            "brain_core/foundation_data_governance.py",
            "docs/governance/FOUNDATION-DATA-GOVERNANCE-0001.md",
            "docs/governance/MEMORY-AUTHORITY-BOUNDARY.md",
        ]
        architecture_decisions = [
            "Reuse current brain_core + bulletin + data instead of creating a parallel mother system.",
            "Keep new market-data governance schemas isolated in a dedicated module until later phases promote them.",
            "Preserve raw -> normalized lineage and vendor field maps in metadata instead of leaking vendor fields into strategy APIs.",
            "Treat permanent memory as navigation only; runtime authority remains code + schema + approved config + tests.",
            "Use capability negotiation to downgrade unsupported analyses to no_signal or snapshot-only behavior instead of overclaiming.",
        ]
        unresolved_conflicts: list[str] = []
        if not (self.root / ".git").exists():
            unresolved_conflicts.append(
                "Repository is not a git worktree, so branch/worktree isolation could not be created literally; implementation stayed isolated at file scope."
            )
        if adapter_catalog["templates"]["tdx_quant"]["implementation_status"] != "Interface":
            unresolved_conflicts.append("TdxQuant template drifted from Interface-only expectation.")
        report_summary = (
            "Foundation data-governance baseline registered for the mother system: object model bindings, "
            "layer boundaries, capability negotiation, quality governance, and A-share adapter isolation are now explicit."
        )

        writeback_result = self._writeback(
            symbol=symbol,
            timeframe=timeframe,
            data_path=data_path,
            object_model=object_model,
            data_layers=data_layers,
            adapter_catalog=adapter_catalog,
            report_summary=report_summary,
            branch_or_worktree=branch_or_worktree,
            architecture_decisions=architecture_decisions,
            unresolved_conflicts=unresolved_conflicts,
            writeback=writeback,
        )

        return {
            "task_id": TASK_ID,
            "branch_or_worktree": branch_or_worktree,
            "git_state": {
                "is_git_repo": (self.root / ".git").exists(),
                "status": "not_a_git_repo" if not (self.root / ".git").exists() else "git_repo_present",
            },
            "changed_files": [
                "brain_core/foundation_data_governance.py",
                "brain_core/service.py",
                "apps/cli/brainctl.py",
                "docs/governance/FOUNDATION-DATA-GOVERNANCE-0001.md",
                "docs/governance/MEMORY-AUTHORITY-BOUNDARY.md",
                "tests/test_foundation_data_governance.py",
            ],
            "reused_existing_components": reused_existing_components,
            "new_components": new_components,
            "architecture_decisions": architecture_decisions,
            "commands_run": [],
            "tests_run": [],
            "test_results": {},
            "unresolved_conflicts": unresolved_conflicts,
            "required_workbuddy_packages": [
                "TDX MCP real function list + raw sample payloads",
                "TdxQuant real field catalog, permissions, and sample snapshots",
                "Historical tick / order file schema and representative samples",
                "WeStock / Tushare point-in-time field semantics and corrections behavior",
                "Current data directory layout and connector latency / gap / reconnect reports",
            ],
            "migration_plan": [
                "Keep existing records in brain_core storage untouched and add governance coverage as additive metadata and new docs.",
                "Promote these adapter and quality schemas into broader runtime only after WorkBuddy provides real field packs.",
                "Move candidate lifecycle thresholds into the later Replay + Validation task instead of hard-coding them here.",
            ],
            "rollback_plan": [
                "Remove the new foundation module and docs without touching existing trading replay records.",
                "Delete the foundation-specific SkillRegistryEntry / ModuleStatusRecord / BulletinStateRecord / SelfEvolutionLog rows if a revert is approved.",
                "Preserve data/super_brain_v01.sqlite and data/audit/events.jsonl as the source of truth during rollback.",
            ],
            "next_two_tasks": [
                "A股规则引擎、微观结构与时段语义",
                "Replay + Validation 闭环与策略生命周期",
            ],
            "confirmation_no_live_trading_changes": True,
            "object_model_bindings": object_model,
            "data_layers": data_layers,
            "adapter_catalog": adapter_catalog,
            "memory_authority_boundary": {
                "doc_path": str(self.root / "docs" / "governance" / "MEMORY-AUTHORITY-BOUNDARY.md").replace("\\", "/"),
                "precedence": [
                    "user_current_instruction",
                    "AGENTS_and_subdirectory_rules",
                    "approved_schema_and_config",
                    "code_and_tests",
                    "permanent_memory_as_navigation_only",
                ],
            },
            "writeback": writeback_result,
            "report_summary": report_summary,
            "confirmation_research_only": True,
            "implementation_status": "Implemented",
        }

    def _adapter_catalog(self, *, symbol: str, timeframe: str, data_path: str) -> dict[str, Any]:
        historical = HistoricalTradeReplayAdapter(root=self.root, symbol=symbol, timeframe=timeframe)
        tdx_snapshot = TdxMcpSnapshotAdapter(root=self.root, symbol=symbol, timeframe=timeframe)
        mock_mbo = MockMboAdapter(root=self.root, symbol=symbol, timeframe=timeframe)
        mock_auction = MockAuctionAdapter(root=self.root, symbol=symbol, timeframe=timeframe)
        catalog = {
            "implemented": {
                "historical_trade_replay": {
                    "capability_descriptor": to_dict(historical.capability_descriptor()),
                    "health_status": to_dict(historical.health_status()),
                    "reliability_profile": to_dict(historical.reliability_profile()),
                    "normalization_preview": historical.normalize(data_path) if data_path else {},
                    "implementation_status": "Implemented",
                },
                "tdx_mcp_snapshot": {
                    "capability_descriptor": to_dict(tdx_snapshot.capability_descriptor()),
                    "health_status": to_dict(tdx_snapshot.health_status()),
                    "reliability_profile": to_dict(tdx_snapshot.reliability_profile()),
                    "implementation_status": "Implemented",
                },
                "mock_mbo": {
                    "capability_descriptor": to_dict(mock_mbo.capability_descriptor()),
                    "health_status": to_dict(mock_mbo.health_status()),
                    "reliability_profile": to_dict(mock_mbo.reliability_profile()),
                    "negotiation_example": negotiate_capability_requests(
                        descriptor=mock_mbo.capability_descriptor(),
                        requested_capabilities=["market_by_order", "sequence_no", "cancel_event"],
                        quality_record=DataQualityRecord(
                            object_id="example",
                            flags=[{"flag": "field_semantics_unverified", "blocking": False}],
                            quality_flags=[{"flag": "field_semantics_unverified", "blocking": False}],
                            summary="mock example",
                        ),
                    ),
                    "implementation_status": "Implemented",
                },
                "mock_auction": {
                    "capability_descriptor": to_dict(mock_auction.capability_descriptor()),
                    "health_status": to_dict(mock_auction.health_status()),
                    "implementation_status": "Implemented",
                },
            },
            "templates": {
                "tdx_quant": {
                    "implementation_status": "Interface",
                    "status": "unverified",
                    "notes": [
                        "Do not invent TdxQuant fields before WorkBuddy supplies the real schema pack.",
                    ],
                },
                "westock": {
                    "implementation_status": "Interface",
                    "status": "partial",
                    "notes": [
                        "Historical enrichment only until point-in-time semantics and real field coverage are verified.",
                    ],
                },
                "tushare": {
                    "implementation_status": "Interface",
                    "status": "partial",
                    "notes": [
                        "Lower-priority enrichment lane for fundamentals and news until point-in-time semantics are verified.",
                    ],
                },
            },
        }
        return catalog

    def _branch_or_worktree_state(self) -> str:
        if (self.root / ".git").exists():
            return "codex/FOUNDATION-DATA-GOVERNANCE-0001"
        return "unavailable:not-a-git-repo"

    def _writeback(
        self,
        *,
        symbol: str,
        timeframe: str,
        data_path: str,
        object_model: dict[str, Any],
        data_layers: dict[str, Any],
        adapter_catalog: dict[str, Any],
        report_summary: str,
        branch_or_worktree: str,
        architecture_decisions: list[str],
        unresolved_conflicts: list[str],
        writeback: bool,
    ) -> dict[str, Any]:
        if not writeback:
            return {
                "changed": False,
                "source_record": {},
                "evidence_item": {},
                "knowledge_atom": {},
                "skill_registry_entry": {},
                "module_status_record": {},
                "bulletin_state_record": {},
                "self_evolution_log": {},
            }

        source_id = new_id("src", f"{TASK_ID}:foundation-report")
        evidence_id = new_id("ev", f"{TASK_ID}:foundation-report")
        atom_id = new_id("atom", f"{TASK_ID}:foundation-report")
        skill_id = new_id("skill", "mother_system:foundation_data_governance_v2")
        module_id = new_id("mod", "mother_system:foundation_data_governance_v2")

        existing_source = self.store.get("sources", source_id)
        existing_evidence = self.store.get("evidence", evidence_id)
        existing_atom = self.store.get("atoms", atom_id)
        existing_skill = self.store.get("skill_registry_entries", skill_id)
        existing_module = self.store.get("module_status_records", module_id)

        source_record = SourceRecord(
            id=source_id,
            source_type="foundation_data_governance_report",
            title=f"{TASK_ID} architecture baseline",
            uri=f"brain://governance/{TASK_ID}",
            reliability=0.92,
            metadata={
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "symbol_scope": symbol,
                "timeframe_scope": timeframe,
                "data_path": data_path,
                "branch_or_worktree": branch_or_worktree,
                "object_model_categories": list(object_model.keys()),
                "data_layer_keys": list(data_layers.keys()),
                "adapter_keys": list(adapter_catalog.get("implemented", {}).keys()),
                "unresolved_conflicts": list(unresolved_conflicts),
                "implementation_status": "Implemented",
            },
        )
        if existing_source and existing_source.get("captured_at"):
            source_record.captured_at = str(existing_source.get("captured_at"))

        evidence_item = EvidenceItem(
            id=evidence_id,
            source_id=source_id,
            quote=report_summary,
            evidence_type="architecture_governance",
            confidence=0.92,
            metadata={
                "task_id": TASK_ID,
                "branch_or_worktree": branch_or_worktree,
                "adapter_keys": list(adapter_catalog.get("implemented", {}).keys()),
                "data_layer_keys": list(data_layers.keys()),
                "implementation_status": "Implemented",
            },
        )
        if existing_evidence and existing_evidence.get("extracted_at"):
            evidence_item.extracted_at = str(existing_evidence.get("extracted_at"))

        atom = KnowledgeAtom(
            id=atom_id,
            title=f"{TASK_ID} baseline",
            content=report_summary,
            summary=report_summary,
            atom_type="architecture_governance",
            source_ids=[source_id],
            evidence_ids=[evidence_id],
            confidence=0.9,
            importance=0.88,
            status="active",
            implementation_status="Implemented",
            metadata={
                "task_id": TASK_ID,
                "branch_or_worktree": branch_or_worktree,
                "data_layers": list(data_layers.keys()),
                "adapter_keys": list(adapter_catalog.get("implemented", {}).keys()),
                "implementation_status": "Implemented",
            },
        )
        if existing_atom and existing_atom.get("created_at"):
            atom.created_at = str(existing_atom.get("created_at"))
        if existing_atom and existing_atom.get("updated_at"):
            atom.updated_at = str(existing_atom.get("updated_at"))

        skill_entry = SkillRegistryEntry(
            id=skill_id,
            skill_name="mother_system.foundation_data_governance_v2",
            domain="mother_system",
            version="v0.2",
            capability_type="architecture_governance",
            quality_score=0.83,
            evidence_level="architecture_audit",
            source_reliability=0.92,
            freshness=0.97,
            validation_status="audited",
            out_of_sample_result="not_run",
            human_reviewed=False,
            status="Experimental",
            implementation_status="Implemented",
            metadata={
                "task_id": TASK_ID,
                "branch_or_worktree": branch_or_worktree,
                "data_layers": data_layers,
                "adapter_catalog": adapter_catalog,
                "memory_authority_boundary_doc": str(self.root / "docs" / "governance" / "MEMORY-AUTHORITY-BOUNDARY.md").replace("\\", "/"),
                "implementation_status": "Implemented",
            },
        )
        if existing_skill and existing_skill.get("created_at"):
            skill_entry.created_at = str(existing_skill.get("created_at"))

        module_record = ModuleStatusRecord(
            id=module_id,
            module_name="foundation_data_governance_v2",
            domain="mother_system",
            quality_action="keep",
            summary=report_summary,
            dependencies=[
                "brain_core/contracts.py",
                "brain_core/storage.py",
                "brain_core/trading_domain.py",
                "docs/governance/FOUNDATION-DATA-GOVERNANCE-0001.md",
                "docs/governance/MEMORY-AUTHORITY-BOUNDARY.md",
            ],
            quality_score=0.84,
            evidence_level="architecture_audit",
            source_reliability=0.92,
            freshness=0.97,
            validation_status="audited",
            out_of_sample_result="not_run",
            human_reviewed=False,
            status="Experimental",
            implementation_status="Implemented",
            metadata={
                "task_id": TASK_ID,
                "branch_or_worktree": branch_or_worktree,
                "architecture_decisions": list(architecture_decisions),
                "unresolved_conflicts": list(unresolved_conflicts),
                "data_layers": data_layers,
                "adapter_catalog": adapter_catalog,
                "implementation_status": "Implemented",
            },
        )
        if existing_module and existing_module.get("created_at"):
            module_record.created_at = str(existing_module.get("created_at"))

        changed = False
        if existing_source != to_dict(source_record):
            self.store.save("sources", source_record)
            changed = True
        if existing_evidence != to_dict(evidence_item):
            self.store.save("evidence", evidence_item)
            changed = True
        if existing_atom != to_dict(atom):
            self.store.save("atoms", atom)
            changed = True
        if existing_skill != to_dict(skill_entry):
            self.store.save("skill_registry_entries", skill_entry)
            changed = True
        if existing_module != to_dict(module_record):
            self.store.save("module_status_records", module_record)
            changed = True

        evolution_log: SelfEvolutionLog | None = None
        board_state: dict[str, Any] = {}
        bulletin_state_record = None
        if changed:
            evolution_log = self.evolution.record(
                trigger="foundation_data_governance_v2_registered",
                observation=report_summary,
                change_type="architecture_governance",
                affected_ids=[source_id, evidence_id, atom_id, skill_id, module_id],
                proposed_update=(
                    "Use the new foundation governance layer as the base for A-share rules-engine and replay-validation work, "
                    "instead of extending trading logic without explicit capability and quality contracts."
                ),
                applied=True,
                metrics={
                    "task_id": TASK_ID,
                    "data_layer_count": len(data_layers),
                    "implemented_adapter_count": len(adapter_catalog.get("implemented", {})),
                    "template_adapter_count": len(adapter_catalog.get("templates", {})),
                    "git_repo_present": (self.root / ".git").exists(),
                },
            )
            state = self.board.get_state()
            completed = list(state.get("completed", []))
            completed_line = "Foundation data-governance v2 baseline 已接入母系统（对象模型 / 分层 / 适配器 / 能力协商 / 质量治理）"
            if completed_line not in completed:
                completed.append(completed_line)
            board_state = self.board.update(
                completed=completed,
                summary=report_summary,
                event_type="foundation_data_governance_v2_registered",
            )

        existing_bulletin_rows = self.store.list_records("bulletin_state_records", limit=1000)
        needs_bulletin_state_record = not any(
            str((item.get("metadata", {}) or {}).get("event_type", "") or "") == "foundation_data_governance_v2_registered"
            and str((item.get("metadata", {}) or {}).get("module_name", "") or "") == "foundation_data_governance_v2"
            for item in existing_bulletin_rows
        )
        if needs_bulletin_state_record:
            board_snapshot = board_state or self.board.get_state()
            bulletin_state_record = BulletinStateRecord(
                bulletin_path=str(self.board.path),
                state_status=str(board_snapshot.get("status", "") or ""),
                completed=list(board_snapshot.get("completed", [])),
                in_progress=list(board_snapshot.get("in_progress", [])),
                next_step=str(board_snapshot.get("next_step", "") or ""),
                recent_event="foundation_data_governance_v2_registered",
                quality_score=0.84,
                evidence_level="architecture_audit",
                source_reliability=0.92,
                freshness=0.97,
                validation_status="audited",
                out_of_sample_result="not_run",
                status="Experimental",
                implementation_status="Implemented",
                metadata={
                    "event_type": "foundation_data_governance_v2_registered",
                    "module_name": "foundation_data_governance_v2",
                    "task_id": TASK_ID,
                    "data_layers": data_layers,
                    "adapter_catalog": adapter_catalog,
                    "branch_or_worktree": branch_or_worktree,
                    "implementation_status": "Implemented",
                },
            )
            self.store.save("bulletin_state_records", bulletin_state_record)
            changed = True

        return {
            "changed": changed,
            "source_record": to_dict(source_record),
            "evidence_item": to_dict(evidence_item),
            "knowledge_atom": to_dict(atom),
            "skill_registry_entry": to_dict(skill_entry),
            "module_status_record": to_dict(module_record),
            "bulletin_state_record": to_dict(bulletin_state_record) if bulletin_state_record else {},
            "self_evolution_log": to_dict(evolution_log) if evolution_log else {},
        }


def negotiate_capability_requests(
    *,
    descriptor: CapabilityDescriptor,
    requested_capabilities: list[str],
    quality_record: DataQualityRecord | None = None,
) -> dict[str, Any]:
    allowed: list[str] = []
    downgraded: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    notes: list[str] = []
    for capability in requested_capabilities:
        detail = descriptor.capabilities.get(capability, {})
        status = str(detail.get("status", "unavailable") or "unavailable")
        if status == "available":
            allowed.append(capability)
            continue
        if status == "partial":
            downgraded.append(
                {
                    "capability": capability,
                    "fallback": str(detail.get("fallback", "") or ""),
                    "reason": f"{capability} is only partially available",
                }
            )
            if capability == "market_by_order":
                notes.append("No true market-by-order stream; do not compute real cancel-rate or order persistence.")
            elif capability == "auction_order_event":
                notes.append("No auction sequence; restrict analysis to 09:25 final auction result.")
            elif capability == "trade_by_trade":
                notes.append("Trade direction may be inferred only; do not present it as original exchange direction.")
            continue
        blocked.append(
            {
                "capability": capability,
                "fallback": str(detail.get("fallback", "no_signal") or "no_signal"),
                "reason": f"{capability} is {status}",
            }
        )
        if capability == "sequence_no":
            notes.append("Sequence numbers are unavailable or unverified; sequence-sensitive studies must block.")
    if quality_record and quality_record.blocking:
        blocked.append(
            {
                "capability": "quality_gate",
                "fallback": "no_signal",
                "reason": "quality record is blocking",
            }
        )
        notes.append("Quality flags marked as blocking, so the output must degrade to no_signal.")
    recommended_output = "normal"
    if blocked:
        recommended_output = "no_signal"
    elif downgraded:
        recommended_output = "downgraded"
    return {
        "adapter_name": descriptor.adapter_name,
        "source_key": descriptor.source_key,
        "requested_capabilities": list(requested_capabilities),
        "allowed_capabilities": allowed,
        "downgraded_capabilities": downgraded,
        "blocked_capabilities": blocked,
        "recommended_output": recommended_output,
        "notes": notes,
        "implementation_status": "Implemented",
    }
