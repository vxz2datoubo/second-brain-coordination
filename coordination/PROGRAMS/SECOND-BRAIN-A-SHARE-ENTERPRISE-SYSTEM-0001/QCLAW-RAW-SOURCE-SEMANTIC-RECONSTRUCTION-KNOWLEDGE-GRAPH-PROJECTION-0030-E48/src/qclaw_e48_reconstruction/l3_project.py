"""L3 projection — derive a deterministic graph from L1 + L2.

The projection consumes the E47-style L2 ``CandidateKnowledgePackage`` dict
and the L1 ``NormalizedSemanticView``. It does not invent edges and does not
fabricate nodes for missing atoms. Counts are derived from the input lists.

Visualization expects this projection JSON: every node carries ``node_id``,
``node_type``, ``label``; every edge carries ``source_node_id``,
``target_node_id``, ``edge_type``, ``confidence``.
"""
from __future__ import annotations

from typing import Iterable, List, Mapping, Sequence

from .l1_schema import NormalizedSemanticView
from .l3_schema import (
    EdgeType,
    GraphEdge,
    GraphNode,
    KnowledgeGraphProjection,
    NodeType,
)


def project_graph(
    l2_package: Mapping[str, object],
    l1_view: NormalizedSemanticView,
    projection_id: str = "E48-L3-001",
    projection_schema_version: str = "1.0",
) -> KnowledgeGraphProjection:
    """Build the L3 graph from the E47 L2 package dict + the L1 view.

    No fabricated edges. Provenance edges go from each atom to its L1 segment
    (when an exact byte range matches) and onward to the L0 source.
    """
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []

    # 1. source / document node from the L2 source metadata.
    src = l2_package.get("source", {}) or {}
    source_id = src.get("source_id") or "source:unknown"
    nodes.append(GraphNode(
        node_id=source_id,
        node_type=NodeType.SOURCE,
        label=src.get("source_title") or source_id,
        attributes=(("source_hash", str(src.get("source_hash", ""))),),
    ))

    # 2. one normalized_segment node per L1 segment.
    for seg in l1_view.segments:
        nid = f"seg:{seg.segment_id}"
        nodes.append(GraphNode(
            node_id=nid,
            node_type=NodeType.NORMALIZED_SEGMENT,
            label=seg.segment_id,
            attributes=(
                ("byte_start", str(seg.byte_start)),
                ("byte_end", str(seg.byte_end)),
                ("confidence", f"{seg.confidence:.4f}"),
            ),
        ))
        # Provenance: segment → source.
        edges.append(GraphEdge(
            edge_id=f"e:{seg.segment_id}->{source_id}",
            source_node_id=nid,
            target_node_id=source_id,
            edge_type=EdgeType.SEGMENT_TO_RAW_SPAN,
            confidence=1.0,
            attributes=(("via", "L0 raw byte slice"),),
        ))
        # Provenance: raw_span → source (alias of the same edge type, kept for symmetry).
        edges.append(GraphEdge(
            edge_id=f"e:raw:{seg.segment_id}->{source_id}",
            source_node_id=nid,
            target_node_id=source_id,
            edge_type=EdgeType.RAW_SPAN_TO_SOURCE,
            confidence=1.0,
        ))

    # 3. one knowledge_atom node + relations from the L2 atoms.
    atoms = l2_package.get("atoms", []) or []
    relations = l2_package.get("relations", []) or []
    contradictions = l2_package.get("contradictions", []) or []
    unknowns = l2_package.get("unknowns", []) or []
    memories = l2_package.get("memory_records", []) or []
    skills = l2_package.get("skills", []) or []

    atom_index = {a.get("atom_id"): a for a in atoms if a.get("atom_id")}

    for atom in atoms:
        nid = f"atom:{atom['atom_id']}"
        nodes.append(GraphNode(
            node_id=nid,
            node_type=NodeType.KNOWLEDGE_ATOM,
            label=atom.get("content", "")[:48],
            attributes=(
                ("atom_type", str(atom.get("atom_type", ""))),
                ("evidence_kind", str(atom.get("evidence_kind", ""))),
                ("confidence", str(atom.get("confidence", ""))),
            ),
        ))
        # Provenance: atom → segment (when an L0 span falls inside a segment).
        for span in atom.get("source_spans", []) or []:
            b_start = int(span.get("byte_start", 0))
            b_end = int(span.get("byte_end", 0))
            target_seg = next(
                (s for s in l1_view.segments
                 if s.byte_start <= b_start and s.byte_end >= b_end),
                None,
            )
            if target_seg is not None:
                edges.append(GraphEdge(
                    edge_id=f"e:{atom['atom_id']}->{target_seg.segment_id}",
                    source_node_id=nid,
                    target_node_id=f"seg:{target_seg.segment_id}",
                    edge_type=EdgeType.ATOM_TO_SEGMENT,
                    confidence=1.0,
                ))

    # 4. relations from L2 (semantic edges).
    for rel in relations:
        s_id = rel.get("source_atom_id")
        t_id = rel.get("target_atom_id")
        if s_id not in atom_index or t_id not in atom_index:
            continue  # do not invent an endpoint; the caller is wrong
        et_raw = str(rel.get("relation_type", "")).strip()
        try:
            et = EdgeType(et_raw)
        except ValueError:
            continue
        edges.append(GraphEdge(
            edge_id=f"e:rel:{s_id}->{t_id}:{et.value}",
            source_node_id=f"atom:{s_id}",
            target_node_id=f"atom:{t_id}",
            edge_type=et,
            confidence=1.0,
            attributes=(("span_index", str(rel.get("span_index", -1))),),
        ))

    # 5. contradiction sets (keep counts derived; may be empty — still valid).
    for c in contradictions:
        nid = f"contradiction:{c.get('contradiction_id')}"
        nodes.append(GraphNode(
            node_id=nid,
            node_type=NodeType.KNOWLEDGE_ATOM,
            label=str(c.get("contradiction_id", ""))[:48],
            attributes=(
                ("class", str(c.get("contradiction_class", ""))),
                ("detail", str(c.get("detail", ""))[:64]),
            ),
        ))
        for aid in c.get("atom_ids", []) or []:
            if aid in atom_index:
                edges.append(GraphEdge(
                    edge_id=f"e:contra:{aid}->{nid}",
                    source_node_id=f"atom:{aid}",
                    target_node_id=nid,
                    edge_type=EdgeType.CONTRADICTS,
                    confidence=1.0,
                ))

    # 6. unknowns become UNKNOWN nodes; relations to atoms via RAISES_UNKNOWN.
    for u in unknowns:
        nid = f"unknown:{u.get('unknown_id')}"
        nodes.append(GraphNode(
            node_id=nid,
            node_type=NodeType.UNKNOWN,
            label=str(u.get("question", ""))[:48],
        ))
        for aid in u.get("related_atom_ids", []) or []:
            if aid in atom_index:
                edges.append(GraphEdge(
                    edge_id=f"e:raises:{aid}->{nid}",
                    source_node_id=f"atom:{aid}",
                    target_node_id=nid,
                    edge_type=EdgeType.RAISES_UNKNOWN,
                    confidence=1.0,
                ))

    # 7. candidate memory / skill nodes (only when L2 actually has them).
    for m in memories:
        nid = f"memory:{m.get('record_id')}"
        nodes.append(GraphNode(
            node_id=nid,
            node_type=NodeType.CANDIDATE_MEMORY,
            label=str(m.get("statement", ""))[:48],
            attributes=(("confidence", str(m.get("confidence", ""))),),
        ))
        for aid in m.get("source_atom_ids", []) or []:
            if aid in atom_index:
                edges.append(GraphEdge(
                    edge_id=f"e:mem:{aid}->{nid}",
                    source_node_id=f"atom:{aid}",
                    target_node_id=nid,
                    edge_type=EdgeType.SUPPORTS,
                    confidence=float(m.get("confidence") == "HIGH"),
                ))
    for s in skills:
        nid = f"skill:{s.get('skill_id')}"
        nodes.append(GraphNode(
            node_id=nid,
            node_type=NodeType.CANDIDATE_SKILL,
            label=str(s.get("name", ""))[:48],
            attributes=(("state", str(s.get("state", "CANDIDATE"))),),
        ))

    return KnowledgeGraphProjection(
        projection_id=projection_id,
        projection_schema_version=projection_schema_version,
        nodes=tuple(nodes),
        edges=tuple(edges),
    ).with_sha()


__all__ = ["project_graph"]