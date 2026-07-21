"""Candidate Memory Library v0.2

Complete candidate memory system implementing:
  - Work Package A: Storage engine (atoms, relations, conflicts, unknowns, sources, packets, FTS)
  - Work Package B: Incremental fusion engine (9 merge states)
  - Work Package C: Version snapshots & rollback
  - Work Package D: Hybrid retrieval (8 strategies)
  - Work Package E: QueryPlan & ContextBundle
  - Work Package F: 32-query regression dataset
  - Work Package G: Retrieval evaluation (Recall@K, Precision@K, MRR, conflict/unknown coverage)
  - Work Package H: CLI + health reporting
  - Work Package I: Codex PR #41 compatibility matrix

4-axis independence: knowledge_status / gpt_access / transport_visibility / authority_level
"""

from .store import MemoryStore
from .fusion import FusionEngine, MergeState, MergeAction, MergeDecision, FusionReport
from .snapshot import SnapshotEngine
from .retrieval import HybridRetrieval, RetrievalStrategy, RetrievalResult, RetrievalReport
from .context import QueryPlan, QueryIntent, ContextBundle, ContextAssembler
from .eval import RetrievalEvaluator, EvalReport, REGRESSION_DATASET
from .compat import COMPATIBILITY_MATRIX, get_matrix, check_compatibility

__version__ = "0.2"
__all__ = [
    # Store
    "MemoryStore",
    # Fusion
    "FusionEngine", "MergeState", "MergeAction", "MergeDecision", "FusionReport",
    # Snapshot
    "SnapshotEngine",
    # Retrieval
    "HybridRetrieval", "RetrievalStrategy", "RetrievalResult", "RetrievalReport",
    # Context
    "QueryPlan", "QueryIntent", "ContextBundle", "ContextAssembler",
    # Eval
    "RetrievalEvaluator", "EvalReport", "REGRESSION_DATASET",
    # Compat
    "COMPATIBILITY_MATRIX", "get_matrix", "check_compatibility",
]
