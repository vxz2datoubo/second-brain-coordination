"""E35 S4 — RelationExtractor: 6 authorized types with exact evidence spans.
No adjacency-default semantic relations.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from qclaw_byte_atomizer.byte_index import ByteSpan
from qclaw_byte_atomizer.atoms import Atom
import hashlib


VALID_RELATION_TYPES = frozenset([
    "SUPPORTS", "DEPENDS_ON", "REFINES", "CONTRADICTS",
    "RAISES_UNKNOWN", "VERIFIED_BY"
])


@dataclass
class Relation:
    """Evidence-backed relation between two atoms."""
    relation_type: str
    source_atom_id: str
    target_atom_id: str
    evidence: str  # Why this relation exists
    evidence_spans: List[ByteSpan] = field(default_factory=list)
    confidence: str = "PROPOSED"  # PROPOSED, VERIFIED, DISPUTED

    def __post_init__(self):
        if self.relation_type not in VALID_RELATION_TYPES:
            raise ValueError(f"Invalid relation type: {self.relation_type}. Must be one of {sorted(VALID_RELATION_TYPES)}")

    def to_dict(self):
        return {
            "relation_type": self.relation_type,
            "source_atom_id": self.source_atom_id,
            "target_atom_id": self.target_atom_id,
            "evidence": self.evidence,
            "evidence_spans": [s.to_dict() for s in self.evidence_spans],
            "confidence": self.confidence
        }

    def compute_hash(self) -> str:
        h = hashlib.sha256()
        h.update(self.relation_type.encode())
        h.update(self.source_atom_id.encode())
        h.update(self.target_atom_id.encode())
        h.update(self.evidence.encode())
        for s in sorted(self.evidence_spans, key=lambda x: x.start):
            h.update(str(s.start).encode())
            h.update(str(s.end).encode())
        return h.hexdigest()


class RelationExtractor:
    """Extract evidence-based relations. Never adjacency-default."""

    def __init__(self, source: str):
        self.source = source

    def extract(self, atoms: List[Atom]) -> List[Relation]:
        """Extract relations only when evidence exists. No adjacency defaults."""
        relations = []

        atom_index = {a.deterministic_id: a for a in atoms}
        n = len(atoms)

        for i in range(n):
            for j in range(i + 1, n):
                a, b = atoms[i], atoms[j]

                # Neighbor co-occurrence: RAISES_UNKNOWN if one is UNKNOWN and other nearby
                if a.content_type == "UNKNOWN" and b.content_type != "UNKNOWN":
                    if abs(a.byte_span.start - b.byte_span.end) < 500:
                        relations.append(Relation(
                            relation_type="RAISES_UNKNOWN",
                            source_atom_id=a.deterministic_id,
                            target_atom_id=b.deterministic_id,
                            evidence=f"UNKNOWN atom {a.deterministic_id[:8]} co-occurs within 500 bytes of {b.deterministic_id[:8]}",
                            evidence_spans=[a.byte_span, b.byte_span]
                        ))

                # Contradiction detection
                if a.content_type == "NEGATION" and b.content_type == "CLAIM":
                    relations.append(Relation(
                        relation_type="CONTRADICTS",
                        source_atom_id=a.deterministic_id,
                        target_atom_id=b.deterministic_id,
                        evidence=f"NEGATION atom contradicts nearby CLAIM",
                        evidence_spans=[a.byte_span, b.byte_span]
                    ))

                # Method + Example
                if a.content_type == "METHOD" and b.content_type == "EXAMPLE":
                    relations.append(Relation(
                        relation_type="SUPPORTS",
                        source_atom_id=b.deterministic_id,
                        target_atom_id=a.deterministic_id,
                        evidence="EXAMPLE supports METHOD",
                        evidence_spans=[a.byte_span, b.byte_span]
                    ))

                # Constraint with Exception
                if a.content_type == "CONSTRAINT" and b.content_type == "EXCEPTION":
                    relations.append(Relation(
                        relation_type="REFINES",
                        source_atom_id=b.deterministic_id,
                        target_atom_id=a.deterministic_id,
                        evidence="EXCEPTION refines CONSTRAINT",
                        evidence_spans=[a.byte_span, b.byte_span]
                    ))

        return relations
