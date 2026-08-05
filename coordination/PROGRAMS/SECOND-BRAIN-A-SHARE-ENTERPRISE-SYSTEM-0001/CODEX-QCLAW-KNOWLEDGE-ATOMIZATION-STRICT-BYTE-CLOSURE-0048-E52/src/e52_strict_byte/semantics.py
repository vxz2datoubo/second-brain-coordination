"""Schema-governed atoms, executable relations and finalized E52 packets."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Sequence

from .index import ByteTruthIndex
from .ledger import Owner, OwnershipSpan


class AtomClassification(str, Enum):
    CLAIM = "CLAIM"
    FACT = "FACT"


class FieldProvenance(str, Enum):
    EXTRACTED = "EXTRACTED"
    DEFAULT = "DEFAULT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class FieldSpec:
    value_schema: str
    default_value: str
    default_rule: str
    unknown_value: str
    unknown_reason: str


FIELD_SPECS: Mapping[str, FieldSpec] = MappingProxyType({
    "condition": FieldSpec("nonempty_utf8_text", "UNSPECIFIED_CONDITION", "default:no_condition_rule", "UNKNOWN_CONDITION", "condition has no deterministic source rule"),
    "exception": FieldSpec("nonempty_utf8_text", "NO_STATED_EXCEPTION", "default:no_exception_rule", "UNKNOWN_EXCEPTION", "exception has no deterministic source rule"),
    "negation": FieldSpec("enum:AFFIRMED|NEGATED|NOT_STATED", "NOT_STATED", "default:negation_not_stated", "UNKNOWN_NEGATION", "negation has no deterministic source rule"),
    "temporal_scope": FieldSpec("nonempty_utf8_text", "UNSPECIFIED_TEMPORAL_SCOPE", "default:no_temporal_scope_rule", "UNKNOWN_TEMPORAL_SCOPE", "temporal scope has no deterministic source rule"),
    "assumption": FieldSpec("nonempty_utf8_text", "NO_STATED_ASSUMPTION", "default:no_assumption_rule", "UNKNOWN_ASSUMPTION", "assumption has no deterministic source rule"),
    "evidence_status": FieldSpec("enum:VERIFIED|UNVERIFIED|NOT_STATED", "NOT_STATED", "default:evidence_not_stated", "UNKNOWN_EVIDENCE_STATUS", "evidence status has no deterministic source rule"),
    "applicability": FieldSpec("nonempty_utf8_text", "UNSPECIFIED_APPLICABILITY", "default:no_applicability_rule", "UNKNOWN_APPLICABILITY", "applicability has no deterministic source rule"),
})
REQUIRED_FIELDS = tuple(FIELD_SPECS)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("canonical mappings require string keys")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (str, int, float, bool, type(None), bytes)):
        return bytes(value) if isinstance(value, bytes) else value
    raise TypeError(f"unsupported canonical value type: {type(value).__name__}")


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, bytes):
        return value.hex()
    return value


@dataclass(frozen=True, slots=True)
class SemanticFieldValue:
    value: str
    provenance: FieldProvenance
    source_rule: str
    evidence_span: tuple[int, int] | None = None
    unknown_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, FieldProvenance) or not self.value or not self.source_rule:
            raise ValueError("semantic field value, provenance, and source rule are required")
        if self.evidence_span is not None and self.evidence_span[1] <= self.evidence_span[0]:
            raise ValueError("field evidence span must be non-empty")
        if self.provenance is FieldProvenance.UNKNOWN:
            if self.evidence_span is not None or not self.unknown_reason:
                raise ValueError("UNKNOWN field needs a field-specific reason and no evidence span")
        elif self.unknown_reason:
            raise ValueError("known semantic field cannot carry unknown_reason")


def unknown_field_values() -> dict[str, SemanticFieldValue]:
    """Create independent, field-specific UNKNOWN values for automatic claims."""
    return {
        name: SemanticFieldValue(
            value=spec.unknown_value,
            provenance=FieldProvenance.UNKNOWN,
            source_rule="unknown:no_deterministic_extractor",
            unknown_reason=spec.unknown_reason,
        )
        for name, spec in FIELD_SPECS.items()
    }


def _validate_value_schema(field_name: str, value: str) -> None:
    schema = FIELD_SPECS[field_name].value_schema
    if schema.startswith("enum:"):
        if value not in schema.removeprefix("enum:").split("|"):
            raise ValueError(f"{field_name} violates {schema}")
    elif not value:
        raise ValueError(f"{field_name} requires non-empty text")


def _validate_semantic_field(field_name: str, field: SemanticFieldValue, atom_span: tuple[int, int]) -> None:
    spec = FIELD_SPECS[field_name]
    if field.provenance is FieldProvenance.UNKNOWN:
        if field.value != spec.unknown_value or field.source_rule != "unknown:no_deterministic_extractor" or field.unknown_reason != spec.unknown_reason:
            raise ValueError(f"{field_name} UNKNOWN does not use its declared field rule")
        return
    if field.provenance is FieldProvenance.DEFAULT:
        if field.value != spec.default_value or field.source_rule != spec.default_rule or field.evidence_span is not None:
            raise ValueError(f"{field_name} DEFAULT does not use its declared rule")
        return
    if field.evidence_span is None or field.source_rule != "extract:explicit_source_span":
        raise ValueError(f"{field_name} EXTRACTED needs explicit source-span evidence")
    start, end = field.evidence_span
    if start < atom_span[0] or end > atom_span[1]:
        raise ValueError(f"{field_name} evidence must be inside its atom evidence span")
    _validate_value_schema(field_name, field.value)


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
        if not _is_sha256(self.source_digest):
            raise ValueError("atom source digest must be SHA-256")
        if not isinstance(self.classification, AtomClassification):
            raise ValueError("atom classification must be declared")
        # SemanticFieldValue is already a frozen value object. Only the outer
        # mapping needs copying so caller aliases cannot alter atom semantics.
        frozen_fields = MappingProxyType(dict(self.fields))
        if set(frozen_fields) != set(REQUIRED_FIELDS):
            raise ValueError("atom must provide exactly seven semantic fields")
        for name in REQUIRED_FIELDS:
            field = frozen_fields[name]
            if not isinstance(field, SemanticFieldValue):
                raise TypeError("atom fields must be SemanticFieldValue instances")
            _validate_semantic_field(name, field, self.byte_span)
        frozen_refs = tuple(str(value) for value in self.evidence_refs)
        if self.classification is AtomClassification.FACT and (self.auto_extracted or not frozen_refs):
            raise ValueError("FACT requires non-automatic verified evidence")
        object.__setattr__(self, "fields", frozen_fields)
        object.__setattr__(self, "evidence_refs", frozen_refs)


class RelationEvidenceType(str, Enum):
    EXPLICIT_LINK = "EXPLICIT_LINK"


class RelationType(str, Enum):
    EXPLICIT_LINK = "EXPLICIT_LINK"


_RELATION_TYPE_BY_EVIDENCE: Mapping[RelationEvidenceType, RelationType] = MappingProxyType({
    RelationEvidenceType.EXPLICIT_LINK: RelationType.EXPLICIT_LINK,
})


@dataclass(frozen=True, slots=True)
class RelationEvidence:
    evidence_type: RelationEvidenceType
    source_digest: str
    byte_span: tuple[int, int]
    evidence_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_type, RelationEvidenceType):
            raise ValueError("relation evidence type must be a declared enum")
        if self.byte_span[0] < 0 or self.byte_span[1] <= self.byte_span[0]:
            raise ValueError("relation evidence needs a non-empty byte span")
        if not _is_sha256(self.source_digest) or not _is_sha256(self.evidence_digest):
            raise ValueError("relation evidence requires SHA-256 source and evidence digests")


@dataclass(frozen=True, slots=True)
class Relation:
    source_atom_id: str
    target_atom_id: str
    relation_type: RelationType
    evidence: RelationEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.relation_type, RelationType):
            raise ValueError("relation type must be a declared enum")
        if self.relation_type is not _RELATION_TYPE_BY_EVIDENCE[self.evidence.evidence_type]:
            raise ValueError("relation type must match evidence type")


def _source_index_and_digest(source: bytes, declared_digest: str | None = None) -> tuple[bytes, ByteTruthIndex, str]:
    source_bytes = bytes(source)
    index = ByteTruthIndex(source_bytes)
    actual_digest = hashlib.sha256(source_bytes).hexdigest()
    if declared_digest is not None and declared_digest != actual_digest:
        raise ValueError("caller-supplied source digest mismatch")
    return source_bytes, index, actual_digest


def _validate_source_span(index: ByteTruthIndex, start: int, end: int) -> None:
    if start < 0 or end <= start or end > index.total_bytes:
        raise ValueError("evidence span is outside source bounds")
    index.codepoint_index_at_boundary(start)
    index.codepoint_index_at_boundary(end)


def extract_claim(span: OwnershipSpan, source: bytes, source_digest: str | None = None) -> Atom:
    source_bytes, index, actual_digest = _source_index_and_digest(source, source_digest)
    if span.owner is not Owner.ATOM_CANDIDATE:
        raise ValueError("only atom-candidate ownership spans may be extracted")
    _validate_source_span(index, span.byte_start, span.byte_end)
    evidence_bytes = source_bytes[span.byte_start:span.byte_end]
    text = evidence_bytes.decode("utf-8", "strict")
    atom_id = hashlib.sha256(
        f"{actual_digest}:{span.byte_start}:{span.byte_end}:CLAIM:".encode("utf-8") + evidence_bytes
    ).hexdigest()
    return Atom(
        atom_id=atom_id,
        text=text,
        byte_span=(span.byte_start, span.byte_end),
        source_digest=actual_digest,
        classification=AtomClassification.CLAIM,
        fields=unknown_field_values(),
        evidence_refs=(f"byte-span:{span.byte_start}:{span.byte_end}",),
        auto_extracted=True,
    )


def extract_explicit_link_relation(
    source: bytes,
    link_span: tuple[int, int],
    atoms: Mapping[str, Atom],
    source_digest: str | None = None,
) -> Relation:
    """Extract a relation only from exact `[[source_id->target_id]]` evidence bytes."""
    source_bytes, index, actual_digest = _source_index_and_digest(source, source_digest)
    start, end = link_span
    _validate_source_span(index, start, end)
    raw = source_bytes[start:end]
    if not raw.startswith(b"[[") or not raw.endswith(b"]]") or raw.count(b"->") != 1:
        raise ValueError("relation needs explicit link syntax")
    try:
        left_raw, right_raw = raw[2:-2].split(b"->", 1)
        left, right = left_raw.decode("ascii"), right_raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("relation endpoint identifiers must be ASCII") from error
    if left not in atoms or right not in atoms:
        raise ValueError("relation endpoint is not present in atom registry")
    for endpoint in (atoms[left], atoms[right]):
        if endpoint.source_digest != actual_digest:
            raise ValueError("relation endpoints must belong to the same source registry")
    return Relation(
        source_atom_id=left,
        target_atom_id=right,
        relation_type=RelationType.EXPLICIT_LINK,
        evidence=RelationEvidence(
            RelationEvidenceType.EXPLICIT_LINK,
            actual_digest,
            link_span,
            hashlib.sha256(raw).hexdigest(),
        ),
    )


def validate_relation(
    relation: Relation,
    atoms: Mapping[str, Atom],
    source: bytes,
    source_digest: str | None = None,
) -> None:
    source_bytes, index, actual_digest = _source_index_and_digest(source, source_digest)
    if relation.source_atom_id not in atoms or relation.target_atom_id not in atoms:
        raise ValueError("relation references unknown atom")
    if relation.relation_type is not _RELATION_TYPE_BY_EVIDENCE[relation.evidence.evidence_type]:
        raise ValueError("relation type and evidence type mismatch")
    if relation.evidence.source_digest != actual_digest:
        raise ValueError("relation evidence source digest mismatch")
    _validate_source_span(index, *relation.evidence.byte_span)
    raw = source_bytes[relation.evidence.byte_span[0]:relation.evidence.byte_span[1]]
    if hashlib.sha256(raw).hexdigest() != relation.evidence.evidence_digest:
        raise ValueError("relation evidence bytes digest mismatch")
    expected = f"[[{relation.source_atom_id}->{relation.target_atom_id}]]".encode("ascii")
    if raw != expected:
        raise ValueError("relation evidence bytes do not match declared endpoints")
    for endpoint in (atoms[relation.source_atom_id], atoms[relation.target_atom_id]):
        if endpoint.source_digest != actual_digest:
            raise ValueError("relation endpoint source registry mismatch")


def _field_payload(fields: Mapping[str, SemanticFieldValue]) -> dict[str, object]:
    return {
        name: {
            "value": fields[name].value,
            "provenance": fields[name].provenance.value,
            "source_rule": fields[name].source_rule,
            "evidence_span": list(fields[name].evidence_span) if fields[name].evidence_span is not None else None,
            "unknown_reason": fields[name].unknown_reason,
        }
        for name in sorted(fields)
    }


@dataclass(frozen=True, slots=True)
class CanonicalPacket:
    source_identity: Mapping[str, object]
    atoms: Sequence[Atom]
    relations: Sequence[Relation]
    unknowns: Sequence[str]
    conflicts: Sequence[str]
    redaction_lineage: Mapping[str, object]
    coverage_manifest: Mapping[str, object]
    config: Mapping[str, object]
    validator_results: Mapping[str, bool]

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_identity", _freeze(dict(self.source_identity)))
        object.__setattr__(self, "atoms", tuple(self.atoms))
        object.__setattr__(self, "relations", tuple(self.relations))
        object.__setattr__(self, "unknowns", tuple(str(value) for value in self.unknowns))
        object.__setattr__(self, "conflicts", tuple(str(value) for value in self.conflicts))
        object.__setattr__(self, "redaction_lineage", _freeze(dict(self.redaction_lineage)))
        object.__setattr__(self, "coverage_manifest", _freeze(dict(self.coverage_manifest)))
        object.__setattr__(self, "config", _freeze(dict(self.config)))
        object.__setattr__(self, "validator_results", _freeze(dict(self.validator_results)))

    def validate(self) -> None:
        identity = self.source_identity
        digest = identity.get("sha256")
        byte_length = identity.get("byte_length")
        if not _is_sha256(digest) or not isinstance(byte_length, int) or byte_length < 0 or not identity.get("format"):
            raise ValueError("packet requires complete source identity")
        if not self.config or not isinstance(self.config.get("schema_version"), str):
            raise ValueError("packet requires versioned configuration")
        if self.coverage_manifest.get("total_bytes") != byte_length or self.coverage_manifest.get("finalized") is not True:
            raise ValueError("packet coverage manifest is incomplete or inconsistent")
        if not isinstance(self.redaction_lineage.get("applied"), bool) or not self.redaction_lineage.get("policy"):
            raise ValueError("packet redaction lineage is incomplete")
        if not self.validator_results or not all(value is True for value in self.validator_results.values()):
            raise ValueError("packet validator results must be present and all true")
        atom_ids: set[str] = set()
        atom_registry: dict[str, Atom] = {}
        for atom in self.atoms:
            if not isinstance(atom, Atom) or atom.atom_id in atom_ids:
                raise ValueError("packet atoms must be unique declared atoms")
            if atom.source_digest != digest or atom.byte_span[1] > byte_length:
                raise ValueError("packet atom identity does not match source identity")
            atom_ids.add(atom.atom_id)
            atom_registry[atom.atom_id] = atom
        for relation in self.relations:
            if not isinstance(relation, Relation):
                raise ValueError("packet relations must be declared relations")
            if relation.source_atom_id not in atom_registry or relation.target_atom_id not in atom_registry:
                raise ValueError("packet relation endpoints are absent")
            if relation.evidence.source_digest != digest or relation.evidence.byte_span[1] > byte_length:
                raise ValueError("packet relation identity does not match source identity")
            if relation.relation_type is not _RELATION_TYPE_BY_EVIDENCE[relation.evidence.evidence_type]:
                raise ValueError("packet relation type is not bound to evidence")

    def finalize(self) -> "CanonicalPacket":
        self.validate()
        return self

    def payload(self) -> dict[str, object]:
        self.finalize()
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
                    "relation_type": relation.relation_type.value,
                    "evidence": {
                        "evidence_type": relation.evidence.evidence_type.value,
                        "source_digest": relation.evidence.source_digest,
                        "byte_span": list(relation.evidence.byte_span),
                        "evidence_digest": relation.evidence.evidence_digest,
                    },
                }
                for relation in sorted(self.relations, key=lambda value: (value.source_atom_id, value.target_atom_id, value.relation_type.value))
            ],
            "unknowns": list(self.unknowns),
            "conflicts": list(self.conflicts),
            "redaction_lineage": _thaw(self.redaction_lineage),
            "coverage_manifest": _thaw(self.coverage_manifest),
            "source_identity": _thaw(self.source_identity),
            "config": _thaw(self.config),
            "validator_results": _thaw(self.validator_results),
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(self.payload(), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def packet_id(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()
