"""Schema-governed atoms, executable relations and canonical E52 packets."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Mapping, Sequence

from .ledger import Owner, OwnershipSpan


class AtomClassification(str, Enum):
    CLAIM = "CLAIM"
    FACT = "FACT"


class FieldProvenance(str, Enum):
    EXTRACTED = "EXTRACTED"
    DEFAULT = "DEFAULT"
    UNKNOWN = "UNKNOWN"


REQUIRED_FIELDS = (
    "condition",
    "exception",
    "negation",
    "temporal_scope",
    "assumption",
    "evidence_status",
    "applicability",
)


@dataclass(frozen=True, slots=True)
class SemanticFieldValue:
    value: str
    provenance: FieldProvenance
    unknown_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("semantic field value is required")
        if self.provenance is FieldProvenance.UNKNOWN and not self.unknown_reason:
            raise ValueError("UNKNOWN semantic field needs a reason")
        if self.provenance is not FieldProvenance.UNKNOWN and self.unknown_reason:
            raise ValueError("known semantic field cannot carry unknown_reason")


@dataclass(frozen=True, slots=True)
class Atom:
    atom_id: str
    text: str
    byte_span: tuple[int, int]
    source_digest: str
    classification: AtomClassification
    fields: Mapping[str, SemanticFieldValue]
    evidence_refs: tuple[str, ...]
    auto_extracted: bool

    def __post_init__(self) -> None:
        if self.byte_span[0] < 0 or self.byte_span[1] <= self.byte_span[0]:
            raise ValueError("atom needs a non-empty evidence span")
        if set(self.fields) != set(REQUIRED_FIELDS):
            raise ValueError("atom must provide exactly seven semantic fields")
        if self.classification is AtomClassification.FACT and (self.auto_extracted or not self.evidence_refs):
            raise ValueError("FACT requires non-automatic verified evidence")


class RelationEvidenceType(str, Enum):
    EXPLICIT_LINK = "EXPLICIT_LINK"


@dataclass(frozen=True, slots=True)
class RelationEvidence:
    evidence_type: RelationEvidenceType
    source_digest: str
    byte_span: tuple[int, int]

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_type, RelationEvidenceType):
            raise ValueError("relation evidence type must be a declared enum")
        if self.byte_span[1] <= self.byte_span[0]:
            raise ValueError("relation evidence needs a non-empty byte span")


@dataclass(frozen=True, slots=True)
class Relation:
    source_atom_id: str
    target_atom_id: str
    relation_type: str
    evidence: RelationEvidence


def _unknown_fields() -> dict[str, SemanticFieldValue]:
    return {
        name: SemanticFieldValue(
            value="UNKNOWN",
            provenance=FieldProvenance.UNKNOWN,
            unknown_reason="not supplied by deterministic extraction",
        )
        for name in REQUIRED_FIELDS
    }


def extract_claim(span: OwnershipSpan, source: bytes, source_digest: str) -> Atom:
    if span.owner is not Owner.ATOM_CANDIDATE:
        raise ValueError("only atom-candidate ownership spans may be extracted")
    text = source[span.byte_start:span.byte_end].decode("utf-8", "strict")
    atom_id = hashlib.sha256(
        f"{source_digest}:{span.byte_start}:{span.byte_end}:CLAIM:".encode("utf-8") + source[span.byte_start:span.byte_end]
    ).hexdigest()
    return Atom(
        atom_id=atom_id,
        text=text,
        byte_span=(span.byte_start, span.byte_end),
        source_digest=source_digest,
        classification=AtomClassification.CLAIM,
        fields=_unknown_fields(),
        evidence_refs=(f"byte-span:{span.byte_start}:{span.byte_end}",),
        auto_extracted=True,
    )


def extract_explicit_link_relation(
    source: bytes,
    source_digest: str,
    link_span: tuple[int, int],
    atoms: Mapping[str, Atom],
) -> Relation:
    """Extract `[[source_id->target_id]]` only when source bytes and endpoints agree."""
    start, end = link_span
    raw = source[start:end]
    if not raw.startswith(b"[[") or not raw.endswith(b"]]") or b"->" not in raw:
        raise ValueError("relation needs explicit link syntax")
    source_id, target_id = raw[2:-2].split(b"->", 1)
    left, right = source_id.decode("ascii"), target_id.decode("ascii")
    if left not in atoms or right not in atoms:
        raise ValueError("relation endpoint is not present in atom registry")
    return Relation(
        source_atom_id=left,
        target_atom_id=right,
        relation_type="EXPLICIT_LINK",
        evidence=RelationEvidence(RelationEvidenceType.EXPLICIT_LINK, source_digest, link_span),
    )


def validate_relation(relation: Relation, atoms: Mapping[str, Atom], source_digest: str) -> None:
    if relation.source_atom_id not in atoms or relation.target_atom_id not in atoms:
        raise ValueError("relation references unknown atom")
    if relation.evidence.source_digest != source_digest:
        raise ValueError("relation evidence source digest mismatch")
    if not relation.relation_type:
        raise ValueError("relation type is required")


def _field_payload(fields: Mapping[str, SemanticFieldValue]) -> dict[str, object]:
    return {
        name: {
            "value": fields[name].value,
            "provenance": fields[name].provenance.value,
            "unknown_reason": fields[name].unknown_reason,
        }
        for name in sorted(fields)
    }


@dataclass(frozen=True, slots=True)
class CanonicalPacket:
    source_identity: Mapping[str, str]
    atoms: tuple[Atom, ...]
    relations: tuple[Relation, ...]
    unknowns: tuple[str, ...]
    conflicts: tuple[str, ...]
    redaction_lineage: Mapping[str, object]
    coverage_manifest: Mapping[str, object]
    config: Mapping[str, object]
    validator_results: Mapping[str, bool]

    def payload(self) -> dict[str, object]:
        return {
            "atoms": [
                {
                    "atom_id": atom.atom_id,
                    "text": atom.text,
                    "byte_span": list(atom.byte_span),
                    "source_digest": atom.source_digest,
                    "classification": atom.classification.value,
                    "fields": _field_payload(atom.fields),
                    "evidence_refs": list(atom.evidence_refs),
                    "auto_extracted": atom.auto_extracted,
                }
                for atom in sorted(self.atoms, key=lambda value: value.atom_id)
            ],
            "relations": [
                {
                    "source_atom_id": relation.source_atom_id,
                    "target_atom_id": relation.target_atom_id,
                    "relation_type": relation.relation_type,
                    "evidence": {
                        "evidence_type": relation.evidence.evidence_type.value,
                        "source_digest": relation.evidence.source_digest,
                        "byte_span": list(relation.evidence.byte_span),
                    },
                }
                for relation in sorted(self.relations, key=lambda value: (value.source_atom_id, value.target_atom_id, value.relation_type))
            ],
            "unknowns": list(self.unknowns),
            "conflicts": list(self.conflicts),
            "redaction_lineage": self.redaction_lineage,
            "coverage_manifest": self.coverage_manifest,
            "source_identity": self.source_identity,
            "config": self.config,
            "validator_results": self.validator_results,
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(self.payload(), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def packet_id(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()
