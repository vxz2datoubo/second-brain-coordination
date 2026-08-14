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
    DAILY_MEMORY_CANDIDATE_TRANSPORT_V1,
    NO_ELIGIBLE_USER_MEMORY_CANDIDATES,
    PRIVATE_SOURCE_BINDING_WAITING,
    PRIVATE_SOURCE_BINDING_REJECTED,
    PRIVATE_SOURCE_BINDING_CONFIGURED,
    PrivateCandidateIngestionResult,
    W3_PRIVATE_CANDIDATE_ENVELOPE_V1,
    build_private_w3_candidate_envelope,
    daily_v2_package_to_w3_private_envelopes,
    daily_memory_candidate_transport_to_w3_private_envelopes,
    ingest_daily_memory_candidate_v2,
    load_daily_memory_candidate_v2,
    private_source_binding_status,
    normalize_daily_memory_candidate_v2_report,
    serialize_daily_memory_candidate_v2_report,
    validate_private_data_paths,
)
from .recurring_candidate_soak import (
    CommittedStateAuditFailure,
    CommittedStateTeardownFailure,
    RecurringCandidateSoakError,
    run_from_environment,
    run_recurring_candidate_ingestion,
)
from .memory_palace import CaptureReceipt, capture_text, cognitive_coverage, normalize_temporal_expression, retrieve_memory_palace
from .knowledge_reconciliation import (
    KnowledgeEpisode, KnowledgeCandidate, ReconciliationReceipt, capture_knowledge,
    decompose_knowledge_passage, identity_domain_hash, proposition_id,
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
    "DAILY_MEMORY_CANDIDATE_TRANSPORT_V1",
    "NO_ELIGIBLE_USER_MEMORY_CANDIDATES",
    "W3_PRIVATE_CANDIDATE_ENVELOPE_V1",
    "PRIVATE_SOURCE_BINDING_WAITING",
    "PRIVATE_SOURCE_BINDING_REJECTED",
    "PRIVATE_SOURCE_BINDING_CONFIGURED",
    "PrivateCandidateIngestionResult",
    "build_private_w3_candidate_envelope",
    "daily_v2_package_to_w3_private_envelopes",
    "daily_memory_candidate_transport_to_w3_private_envelopes",
    "ingest_daily_memory_candidate_v2",
    "load_daily_memory_candidate_v2",
    "private_source_binding_status",
    "normalize_daily_memory_candidate_v2_report",
    "serialize_daily_memory_candidate_v2_report",
    "validate_private_data_paths",
    "run_from_environment",
    "run_recurring_candidate_ingestion",
    "RecurringCandidateSoakError",
    "CommittedStateAuditFailure",
    "CommittedStateTeardownFailure",
    "CaptureReceipt",
    "capture_text",
    "cognitive_coverage",
    "normalize_temporal_expression",
    "retrieve_memory_palace",
    "KnowledgeEpisode",
    "KnowledgeCandidate",
    "ReconciliationReceipt",
    "capture_knowledge",
    "decompose_knowledge_passage",
    "identity_domain_hash",
    "proposition_id",
]
