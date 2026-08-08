"""E47 Universal Candidate Knowledge Schema.

CANDIDATE ONLY — no formal authority claims.
All memory zones / skill states structurally locked to CANDIDATE.
"""
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any


# === Evidence Kind (strict 5-fold separation) ===

class EvidenceKind(str, Enum):
    SOURCE_EXTRACT = "SOURCE_EXTRACT"        # Verbatim text from source
    USER_CLAIM = "USER_CLAIM"                # User-stated claim/observation
    EXTERNAL_CLAIM = "EXTERNAL_CLAIM"        # Third-party/external claim
    INFERENCE = "INFERENCE"                  # Agent-derived inference
    VALUE_JUDGMENT = "VALUE_JUDGMENT"        # Subjective evaluation


# === Atom Type ===

class AtomType(str, Enum):
    CONCEPT = "CONCEPT"
    DEFINITION = "DEFINITION"
    MECHANISM = "MECHANISM"
    CAUSAL_CHAIN = "CAUSAL_CHAIN"
    CONDITION = "CONDITION"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    INDICATOR = "INDICATOR"
    DATA_SOURCE = "DATA_SOURCE"
    SCOPE = "SCOPE"
    FAILURE_CONDITION = "FAILURE_CONDITION"
    VERIFICATION_METHOD = "VERIFICATION_METHOD"
    EXECUTABLE_ACTION = "EXECUTABLE_ACTION"
    HYPOTHESIS = "HYPOTHESIS"


# === Confidence ===

class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNTRUSTED = "UNTRUSTED"


# === Relation Type ===

class RelationType(str, Enum):
    SUPPORTS = "SUPPORTS"
    DEPENDS_ON = "DEPENDS_ON"
    REFINES = "REFINES"
    CONTRADICTS = "CONTRADICTS"
    RAISES_UNKNOWN = "RAISES_UNKNOWN"
    VERIFIED_BY = "VERIFIED_BY"


# === Contradiction Class ===

class ContradictionClass(str, Enum):
    TIME_CHANGE = "TIME_CHANGE"
    SCENARIO_DIFFERENCE = "SCENARIO_DIFFERENCE"
    DEFINITION_MISMATCH = "DEFINITION_MISMATCH"
    PROBABLE_ERROR = "PROBABLE_ERROR"


# === Source Span (exact byte/line range, not labels) ===

@dataclass(frozen=True)
class SourceSpan:
    """Precise source reference. Each atom must have one or more spans."""
    byte_start: int
    byte_end: int       # exclusive
    line_start: int     # 1-indexed
    line_end: int       # inclusive
    span_label: str = ""  # brief annotation, NOT a substitution for exact range

    def to_dict(self) -> dict:
        d = {
            "byte_start": self.byte_start,
            "byte_end": self.byte_end,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }
        if self.span_label:
            d["span_label"] = self.span_label
        return d


# === Source Snapshot (hash + metadata) ===

@dataclass(frozen=True)
class SourceSnapshot:
    """Immutable source identity for provenance tracking."""
    source_id: str
    source_url: str
    source_title: str
    source_hash: str          # SHA-256 of full source text
    source_size_bytes: int
    source_content: str       # Full text (for span verification)
    ingested_at: str          # ISO-8601 timestamp — excluded from identity hash!

    def identity_hash(self) -> str:
        """Content identity WITHOUT timestamp."""
        raw = f"{self.source_url}|{self.source_title}|{self.source_hash}|{self.source_size_bytes}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "source_hash": self.source_hash,
            "source_size_bytes": self.source_size_bytes,
            "ingested_at": self.ingested_at,
        }

    def verify_span(self, span: SourceSpan) -> str:
        """Verify span bytes match source content. Returns slice or raises.
        
        Note: byte_start/byte_end are positions in source_bytes (UTF-8 encoded).
        We decode the slice back to str for comparison.
        """
        if span.byte_start < 0 or span.byte_end > self.source_size_bytes:
            raise ValueError(f"Span out of range: {span.byte_start}:{span.byte_end}")
        src_bytes = self.source_content.encode("utf-8")
        return src_bytes[span.byte_start:span.byte_end].decode("utf-8")


# === Atom ===

@dataclass(frozen=True)
class Atom:
    atom_id: str
    atom_type: AtomType
    content: str
    source_spans: Tuple[SourceSpan, ...]  # At least one exact span
    evidence_kind: EvidenceKind
    confidence: Confidence
    scope: str = ""
    invalidation_conditions: str = ""

    def to_dict(self) -> dict:
        return {
            "atom_id": self.atom_id,
            "atom_type": self.atom_type.value,
            "content": self.content,
            "source_spans": [s.to_dict() for s in self.source_spans],
            "evidence_kind": self.evidence_kind.value,
            "confidence": self.confidence.value,
            "scope": self.scope,
            "invalidation_conditions": self.invalidation_conditions,
        }


# === Relation ===

@dataclass(frozen=True)
class Relation:
    source_atom_id: str
    target_atom_id: str
    relation_type: RelationType
    span_index: int = -1  # index into source_spans of source atom, or -1 for inferred

    def to_dict(self) -> dict:
        return {
            "source_atom_id": self.source_atom_id,
            "target_atom_id": self.target_atom_id,
            "relation_type": self.relation_type.value,
            "span_index": self.span_index,
        }


# === Contradiction ===

@dataclass(frozen=True)
class Contradiction:
    contradiction_id: str
    atom_ids: Tuple[str, ...]
    contradiction_class: ContradictionClass
    detail: str

    def to_dict(self) -> dict:
        return {
            "contradiction_id": self.contradiction_id,
            "atom_ids": list(self.atom_ids),
            "contradiction_class": self.contradiction_class.value,
            "detail": self.detail,
        }


# === Unknown ===

@dataclass(frozen=True)
class Unknown:
    unknown_id: str
    question: str
    related_atom_ids: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "unknown_id": self.unknown_id,
            "question": self.question,
            "related_atom_ids": list(self.related_atom_ids),
        }


# === Candidate Memory ===

@dataclass(frozen=True)
class CandidateMemory:
    record_id: str
    statement: str
    confidence: Confidence
    source_atom_ids: Tuple[str, ...]
    evidence_basis: str

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "statement": self.statement,
            "memory_zone": "CANDIDATE",  # STRUCTURALLY LOCKED
            "confidence": self.confidence.value,
            "source_atom_ids": list(self.source_atom_ids),
            "evidence_basis": self.evidence_basis,
        }


# === Candidate Skill ===

@dataclass(frozen=True)
class CandidateSkill:
    skill_id: str
    name: str
    description: str
    failure_conditions: str

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "state": "CANDIDATE",   # STRUCTURALLY LOCKED
            "failure_conditions": self.failure_conditions,
            "requires_e60_authority": True,  # STRUCTURALLY LOCKED
        }


# === Universal Candidate Knowledge Package ===

@dataclass(frozen=True)
class CandidateKnowledgePackage:
    """One package per digested source material.

    Universal schema. Output as independent JSON/YAML artifact.
    Code is engine; knowledge is data.
    """
    package_id: str          # e.g. "E47-DIGEST-001"
    source: SourceSnapshot   # Full source with hash
    package_version: int = 1
    atoms: Tuple[Atom, ...] = ()
    relations: Tuple[Relation, ...] = ()
    contradictions: Tuple[Contradiction, ...] = ()
    unknowns: Tuple[Unknown, ...] = ()
    memory_records: Tuple[CandidateMemory, ...] = ()
    skills: Tuple[CandidateSkill, ...] = ()
    summary: str = ""

    def content_hash(self) -> str:
        """Deterministic hash of all knowledge content.

        EXCLUDES: timestamp, package_version.
        INCLUDES: source identity + atoms + relations + contradictions
                  + unknowns + memory + skills + summary.
        """
        raw = self.package_id
        raw += self.source.identity_hash()
        for a in sorted(self.atoms, key=lambda x: x.atom_id):
            raw += a.atom_id + a.atom_type.value + a.content + a.evidence_kind.value
            for s in a.source_spans:
                raw += f"{s.byte_start}:{s.byte_end}"
        for r in sorted(self.relations, key=lambda x: (x.source_atom_id, x.target_atom_id)):
            raw += r.source_atom_id + r.target_atom_id + r.relation_type.value
        for c in sorted(self.contradictions, key=lambda x: x.contradiction_id):
            raw += c.contradiction_id + c.contradiction_class.value
        for u in sorted(self.unknowns, key=lambda x: x.unknown_id):
            raw += u.unknown_id + u.question
        for m in sorted(self.memory_records, key=lambda x: x.record_id):
            raw += m.record_id + m.statement
        for s in sorted(self.skills, key=lambda x: x.skill_id):
            raw += s.skill_id + s.name + s.description
        raw += self.summary
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        """Full serializable dictionary. Suitable for JSON/YAML artifact."""
        return {
            "schema": "QCLAW-CANDIDATE-KNOWLEDGE-PACKAGE-V1",
            "package_id": self.package_id,
            "package_version": self.package_version,
            "content_hash": self.content_hash(),
            "source": self.source.to_dict(),
            "summary": self.summary,
            "atoms": [a.to_dict() for a in self.atoms],
            "relations": [r.to_dict() for r in self.relations],
            "contradictions": [c.to_dict() for c in self.contradictions],
            "unknowns": [u.to_dict() for u in self.unknowns],
            "memory_records": [m.to_dict() for m in self.memory_records],
            "skills": [s.to_dict() for s in self.skills],
        }

    def atom_ids(self) -> set:
        return {a.atom_id for a in self.atoms}

    def validate(self) -> List[str]:
        """Self-validate and return list of errors. Empty = valid."""
        errors = []
        ids = self.atom_ids()
        for r in self.relations:
            if r.source_atom_id not in ids:
                errors.append(f"Relation {r.source_atom_id}->{r.target_atom_id}: source not in atoms")
            if r.target_atom_id not in ids:
                errors.append(f"Relation {r.source_atom_id}->{r.target_atom_id}: target not in atoms")
        for c in self.contradictions:
            for aid in c.atom_ids:
                if aid not in ids:
                    errors.append(f"Contradiction {c.contradiction_id}: atom {aid} not found")
        for u in self.unknowns:
            for aid in u.related_atom_ids:
                if aid not in ids:
                    errors.append(f"Unknown {u.unknown_id}: atom {aid} not found")
        for m in self.memory_records:
            for aid in m.source_atom_ids:
                if aid not in ids:
                    errors.append(f"Memory {m.record_id}: atom {aid} not found")
        for a in self.atoms:
            if not a.source_spans:
                errors.append(f"Atom {a.atom_id}: no source spans")
            for s in a.source_spans:
                if s.byte_end <= s.byte_start:
                    errors.append(f"Atom {a.atom_id}: invalid span {s.byte_start}:{s.byte_end}")
                if s.byte_end > self.source.source_size_bytes:
                    errors.append(f"Atom {a.atom_id}: span end {s.byte_end} > source size {self.source.source_size_bytes}")
        return errors
