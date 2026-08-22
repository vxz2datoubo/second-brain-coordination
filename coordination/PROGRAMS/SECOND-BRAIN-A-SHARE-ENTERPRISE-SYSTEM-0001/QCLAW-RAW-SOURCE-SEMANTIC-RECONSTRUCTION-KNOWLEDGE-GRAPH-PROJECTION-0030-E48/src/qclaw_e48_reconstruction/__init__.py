"""QCLAW E48 Raw-source semantic reconstruction + knowledge-graph projection.

CANDIDATE_ONLY / PUBLIC_SAFE / NO_TRADE.
Formal persistence is blocked pending E61 + GPT_ACCEPTED_REAL_PRODUCTION_DURABLE_AUTHORITY_BINDING.

Layers:
  L0 RawSourceSnapshot        — immutable, hash-pinned (see E47 schema)
  L1 NormalizedSemanticView   — this module: derived, auditable, hash-pinned
  L2 CandidateKnowledgeAtoms  — reuse E47 module by import (no E47 code copied)
  L3 KnowledgeGraphProjection — this module: derived, deterministic, hash-pinned

E61 compatibility:
  Every layer carries a 64-hex SHA-256 digest derived by deterministic canonical
  serialization. Legacy 16-hex content_hash (E47) is kept for compatibility only and
  is never a production identity. See ``digests.py`` for canonicalization contracts.
"""
from .l1_schema import (
    NormalizedSemanticView,
    NormalizedSegment,
    NormalizationEdit,
    AmbiguityCandidate,
    TerminologyAlias,
    UnknownMarker,
    EditType,
)
from .l3_schema import (
    KnowledgeGraphProjection,
    GraphNode,
    GraphEdge,
    NodeType,
    EdgeType,
    PROVENANCE_EDGE_TYPES,
    SEMANTIC_EDGE_TYPES,
)
from .digests import (
    canonical_json,
    sha256_hex,
    raw_artifact_sha256,
    canonical_semantic_sha256,
    l0_provenance_sha256,
    DigestBundle,
)
from .l2_derive import derive_l2_package

__all__ = [
    "NormalizedSemanticView",
    "NormalizedSegment",
    "NormalizationEdit",
    "AmbiguityCandidate",
    "TerminologyAlias",
    "UnknownMarker",
    "EditType",
    "KnowledgeGraphProjection",
    "GraphNode",
    "GraphEdge",
    "NodeType",
    "EdgeType",
    "PROVENANCE_EDGE_TYPES",
    "SEMANTIC_EDGE_TYPES",
    "canonical_json",
    "sha256_hex",
    "raw_artifact_sha256",
    "canonical_semantic_sha256",
    "l0_provenance_sha256",
    "DigestBundle",
    "derive_l2_package",
]