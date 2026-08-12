"""Governed offline market-data and candidate-memory integration."""

from .contracts import (
    FieldSemanticDecision,
    ParseIssue,
    ParseReport,
    SourceActivationPolicy,
    TdxDayRawRecord,
)
from .tdx_day import ParsedDayDataset, TdxDayParser, TdxDaySourceAdapter
from .replay_bridge import CloseAvailabilityPolicy, ReplayReceipt, run_p2_replay, to_p2_bars
from .learning_packet import build_learning_packet, verify_learning_packet
from .memory_store import MemoryStore
from .retrieval import ContextAssembler, ContextBundle, QueryPlan
from .snapshot import SnapshotManager
from .integrated_flow import (
    context_bundle_semantic_hash,
    IntegratedFlowReceipt,
    replay_receipt_to_learning_packet,
    run_integrated_flow,
)
from .private_candidate_ingestion import (
    DAILY_MEMORY_CANDIDATE_V2,
    PRIVATE_SOURCE_BINDING_WAITING,
    PRIVATE_SOURCE_BINDING_REJECTED,
    PRIVATE_SOURCE_BINDING_CONFIGURED,
    PrivateCandidateIngestionResult,
    W3_PRIVATE_CANDIDATE_ENVELOPE_V1,
    build_private_w3_candidate_envelope,
    daily_v2_package_to_w3_private_envelopes,
    ingest_daily_memory_candidate_v2,
    load_daily_memory_candidate_v2,
    private_source_binding_status,
    validate_private_data_paths,
)

__all__ = [
    "FieldSemanticDecision",
    "CloseAvailabilityPolicy",
    "ContextAssembler",
    "ContextBundle",
    "context_bundle_semantic_hash",
    "ParseIssue",
    "ParseReport",
    "ParsedDayDataset",
    "SourceActivationPolicy",
    "ReplayReceipt",
    "MemoryStore",
    "IntegratedFlowReceipt",
    "QueryPlan",
    "SnapshotManager",
    "TdxDayParser",
    "TdxDayRawRecord",
    "TdxDaySourceAdapter",
    "run_p2_replay",
    "replay_receipt_to_learning_packet",
    "run_integrated_flow",
    "build_learning_packet",
    "to_p2_bars",
    "verify_learning_packet",
    "DAILY_MEMORY_CANDIDATE_V2",
    "W3_PRIVATE_CANDIDATE_ENVELOPE_V1",
    "PRIVATE_SOURCE_BINDING_WAITING",
    "PRIVATE_SOURCE_BINDING_REJECTED",
    "PRIVATE_SOURCE_BINDING_CONFIGURED",
    "PrivateCandidateIngestionResult",
    "build_private_w3_candidate_envelope",
    "daily_v2_package_to_w3_private_envelopes",
    "ingest_daily_memory_candidate_v2",
    "load_daily_memory_candidate_v2",
    "private_source_binding_status",
    "validate_private_data_paths",
]
