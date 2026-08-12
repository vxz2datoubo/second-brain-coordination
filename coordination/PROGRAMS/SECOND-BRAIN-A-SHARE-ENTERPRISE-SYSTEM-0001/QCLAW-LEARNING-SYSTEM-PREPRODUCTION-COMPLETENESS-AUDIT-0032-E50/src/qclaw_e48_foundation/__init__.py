"""E48 foundation (vendored).

FROZEN SNAPSHOT from E48 head e018fc1a85fc (QCLAW-RAW-SOURCE-SEMANTIC-RECONSTRUCTION-KNOWLEDGE-GRAPH-PROJECTION-0030-E48).

Accepted by GPT (review_id 4915512021) for E50 foundation credit:
  - L0 immutable raw evidence
  - L1 auditable semantic reconstruction
  - bounded E47-style L2 atomization
  - L3 graph projection
  - ambiguity / UNKNOWN fail-closed
  - truthful conditional relation direction (DEPENDS_ON source=MECHANISM, target=CONDITION)

NOT accepted (explicit): private/real user samples.
Do not edit here for E50; instead, build E50 audit modules in qclaw_e50_audit/ and import from this package.
"""

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