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

__all__ = [
    "FieldSemanticDecision",
    "CloseAvailabilityPolicy",
    "ContextAssembler",
    "ContextBundle",
    "ParseIssue",
    "ParseReport",
    "ParsedDayDataset",
    "SourceActivationPolicy",
    "ReplayReceipt",
    "MemoryStore",
    "QueryPlan",
    "SnapshotManager",
    "TdxDayParser",
    "TdxDayRawRecord",
    "TdxDaySourceAdapter",
    "run_p2_replay",
    "build_learning_packet",
    "to_p2_bars",
    "verify_learning_packet",
]
