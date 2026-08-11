"""L3 KnowledgeGraphProjection — derived, deterministic graph layer.

Layer contract (per W3 blueprint + E48 plan §4):
- Node / edge counts derived from the actual L2 package + L1 view. No fixed quotas.
- Every edge endpoint exists.
- Empty contradiction sets are valid.
- Visualization loads from this projection JSON, exposes provenance on click.

The projection carries its own ``projection_sha256`` (separate from any L1/L2
hash). Adding hashes does NOT promote L3 to authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Set, Tuple

from .digests import canonical_json, sha256_hex


class NodeType(str, Enum):
    SOURCE = "source"
    DOCUMENT = "document"
    NORMALIZED_SEGMENT = "normalized_segment"
    KNOWLEDGE_ATOM = "knowledge_atom"
    UNKNOWN = "unknown"
    CANDIDATE_MEMORY = "candidate_memory"
    CANDIDATE_SKILL = "candidate_skill"


class EdgeType(str, Enum):
    # Semantic relations (from E47).
    SUPPORTS = "SUPPORTS"
    DEPENDS_ON = "DEPENDS_ON"
    REFINES = "REFINES"
    CONTRADICTS = "CONTRADICTS"
    RAISES_UNKNOWN = "RAISES_UNKNOWN"
    VERIFIED_BY = "VERIFIED_BY"
    # Provenance relations (added by E48).
    ATOM_TO_SEGMENT = "atom_to_segment"
    SEGMENT_TO_RAW_SPAN = "segment_to_raw_span"
    RAW_SPAN_TO_SOURCE = "raw_span_to_source"
    # Ambiguity edges.
    ATOM_TO_AMBIGUITY = "atom_to_ambiguity"


SEMANTIC_EDGE_TYPES: frozenset = frozenset({
    EdgeType.SUPPORTS.value,
    EdgeType.DEPENDS_ON.value,
    EdgeType.REFINES.value,
    EdgeType.CONTRADICTS.value,
    EdgeType.RAISES_UNKNOWN.value,
    EdgeType.VERIFIED_BY.value,
})

PROVENANCE_EDGE_TYPES: frozenset = frozenset({
    EdgeType.ATOM_TO_SEGMENT.value,
    EdgeType.SEGMENT_TO_RAW_SPAN.value,
    EdgeType.RAW_SPAN_TO_SOURCE.value,
    EdgeType.ATOM_TO_AMBIGUITY.value,
})


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    node_type: NodeType
    label: str = ""
    attributes: Tuple[Tuple[str, str], ...] = ()  # ordered pairs for determinism

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "label": self.label,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: EdgeType
    confidence: float = 1.0
    attributes: Tuple[Tuple[str, str], ...] = ()

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type.value,
            "confidence": self.confidence,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class KnowledgeGraphProjection:
    """Derived L3 graph. Carries its own ``projection_sha256``.

    Counts are derived from ``nodes`` / ``edges`` content, never hard-coded.
    """
    projection_id: str
    projection_schema_version: str
    nodes: Tuple[GraphNode, ...]
    edges: Tuple[GraphEdge, ...]
    projection_sha256: str = ""

    def with_sha(self) -> "KnowledgeGraphProjection":
        canonical = {
            "projection_id": self.projection_id,
            "projection_schema_version": self.projection_schema_version,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }
        sha = sha256_hex(canonical_json(canonical))
        if sha == self.projection_sha256:
            return self
        return KnowledgeGraphProjection(
            projection_id=self.projection_id,
            projection_schema_version=self.projection_schema_version,
            nodes=self.nodes,
            edges=self.edges,
            projection_sha256=sha,
        )

    def to_dict(self) -> dict:
        p = self.with_sha()
        return {
            "schema": "QCLAW-E48-KNOWLEDGE-GRAPH-PROJECTION-V1",
            "projection_id": p.projection_id,
            "projection_schema_version": p.projection_schema_version,
            "projection_sha256": p.projection_sha256,
            "node_count": len(p.nodes),
            "edge_count": len(p.edges),
            "nodes": [n.to_dict() for n in p.nodes],
            "edges": [e.to_dict() for e in p.edges],
        }

    def validate(self) -> List[str]:
        """Every edge endpoint must exist. No fabricated edges."""
        errs: List[str] = []
        ids: Set[str] = {n.node_id for n in self.nodes}
        for e in self.edges:
            if e.source_node_id not in ids:
                errs.append(
                    f"Edge {e.edge_id}: source node {e.source_node_id} not in nodes"
                )
            if e.target_node_id not in ids:
                errs.append(
                    f"Edge {e.edge_id}: target node {e.target_node_id} not in nodes"
                )
            if e.edge_type == EdgeType.CONTRADICTS and not (0.0 <= e.confidence <= 1.0):
                errs.append(f"Edge {e.edge_id}: CONTRADICTS confidence out of [0,1]")
        return errs


__all__ = [
    "NodeType",
    "EdgeType",
    "SEMANTIC_EDGE_TYPES",
    "PROVENANCE_EDGE_TYPES",
    "GraphNode",
    "GraphEdge",
    "KnowledgeGraphProjection",
]