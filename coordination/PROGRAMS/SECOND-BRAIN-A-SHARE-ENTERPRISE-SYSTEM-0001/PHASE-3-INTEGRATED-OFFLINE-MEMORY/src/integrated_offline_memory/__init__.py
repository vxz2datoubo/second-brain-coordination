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
from .knowledge_contracts import (
    KnowledgeAccessDecision,
    KnowledgeGatewayPolicy,
    KnowledgeQuery,
    KnowledgeSourceManifest,
    LocalKnowledgeReference,
    evaluate_knowledge_access,
)
from .local_knowledge import (
    ExistingServiceKnowledgeAdapter,
    LocalDirectoryKnowledgeAdapter,
    LocalFileKnowledgeAdapter,
    LocalKnowledgeAdapter,
    LocalKnowledgeDocument,
    LocalKnowledgeLoadResult,
    build_local_knowledge_packet,
    hash_local_directory,
    hash_local_file,
)
from .answer_evidence import AnswerEvidenceBundle, AnswerEvidenceCompiler
from .feedback import (
    FeedbackCommitReceipt,
    FeedbackLearningPacket,
    FeedbackProcessor,
    FeedbackRecord,
    RevocationReceipt,
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
    "KnowledgeAccessDecision",
    "KnowledgeGatewayPolicy",
    "KnowledgeQuery",
    "KnowledgeSourceManifest",
    "LocalKnowledgeReference",
    "LocalKnowledgeAdapter",
    "LocalKnowledgeDocument",
    "LocalKnowledgeLoadResult",
    "LocalFileKnowledgeAdapter",
    "LocalDirectoryKnowledgeAdapter",
    "ExistingServiceKnowledgeAdapter",
    "AnswerEvidenceBundle",
    "AnswerEvidenceCompiler",
    "FeedbackRecord",
    "FeedbackLearningPacket",
    "FeedbackCommitReceipt",
    "FeedbackProcessor",
    "RevocationReceipt",
    "QueryPlan",
    "SnapshotManager",
    "TdxDayParser",
    "TdxDayRawRecord",
    "TdxDaySourceAdapter",
    "run_p2_replay",
    "replay_receipt_to_learning_packet",
    "run_integrated_flow",
    "build_learning_packet",
    "build_local_knowledge_packet",
    "evaluate_knowledge_access",
    "hash_local_directory",
    "hash_local_file",
    "to_p2_bars",
    "verify_learning_packet",
]
