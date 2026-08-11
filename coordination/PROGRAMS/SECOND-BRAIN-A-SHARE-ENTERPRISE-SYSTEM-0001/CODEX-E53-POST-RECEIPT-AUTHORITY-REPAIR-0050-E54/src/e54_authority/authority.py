"""Source-bound atom authority primitives for E54.

The module accepts only supplied public-safe bytes.  Its purpose is to make
every atom, ownership decision, relation, and packet independently
recomputable; it is not a source-admission, market, or production service.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence


class AuthorityError(ValueError):
    """Raised when a public-safe authority invariant is violated."""


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(thaw(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AuthorityError("value is outside the finite canonical JSON domain") from exc


def digest(value: object) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def deep_freeze(value: object) -> object:
    """Recursively remove ordinary mutable aliases from public projections."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): deep_freeze(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))})
    if isinstance(value, (list, tuple)):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted((deep_freeze(item) for item in value), key=repr))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise AuthorityError("projection contains a non-canonical value")


def thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    if isinstance(value, list):
        return [thaw(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise AuthorityError("projection contains a non-canonical value")


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    _data: bytes
    source_id: str
    format_name: str
    source_sha256: str

    @classmethod
    def from_bytes(cls, data: bytes, *, source_id: str, format_name: str) -> "SourceEvidence":
        if not isinstance(data, bytes):
            raise AuthorityError("source must be bytes")
        if not isinstance(source_id, str) or not source_id.strip():
            raise AuthorityError("source_id must be a nonempty public identifier")
        if format_name not in {"text", "markdown", "json", "jsonl"}:
            raise AuthorityError("unsupported declared source format")
        try:
            data.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise AuthorityError("source is not strict UTF-8") from exc
        # Public-safe fixtures may test the marker, but no packet may admit a
        # PEM private-key boundary or token-shaped raw source.
        private_marker = b"-----BEGIN " + b"PRIVATE" + b" KEY-----"
        if private_marker in data or b"ghp_" in data or b"sk-" in data:
            raise AuthorityError("source contains a blocked private or credential-shaped marker")
        copied = bytes(data)
        return cls(copied, source_id, format_name, sha256(copied).hexdigest())

    @property
    def byte_length(self) -> int:
        return len(self._data)

    @property
    def identity(self) -> Mapping[str, object]:
        return deep_freeze(self.recompute_identity())  # fresh deep-frozen projection

    def recompute_identity(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "format": self.format_name,
            "sha256": sha256(self._data).hexdigest(),
            "byte_length": len(self._data),
        }

    def verify(self) -> bool:
        expected = self.recompute_identity()
        return expected["sha256"] == self.source_sha256 and expected["sha256"] == sha256(self._data).hexdigest()

    def bytes_slice(self, start: int, end: int) -> bytes:
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start <= end <= len(self._data):
            raise AuthorityError("slice is outside exact source bytes")
        return self._data[start:end]

    def text_slice(self, start: int, end: int) -> str:
        try:
            return self.bytes_slice(start, end).decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise AuthorityError("slice cuts a UTF-8 sequence") from exc

    def utf8_boundary(self, offset: int) -> bool:
        try:
            self.bytes_slice(0, offset).decode("utf-8", "strict")
        except (AuthorityError, UnicodeDecodeError):
            return False
        return True


class SpanOwner(str, Enum):
    ATOM_CANDIDATE = "ATOM_CANDIDATE"
    STRUCTURAL = "STRUCTURAL"
    REDACTED = "REDACTED"
    UNKNOWN = "UNKNOWN"


class FieldRule(str, Enum):
    EXACT_UTF8_SLICE = "EXACT_UTF8_SLICE"
    ASCII_LOWER_STRIP = "ASCII_LOWER_STRIP"
    JSON_STRING = "JSON_STRING"


@dataclass(frozen=True, slots=True, order=True)
class OwnershipSpan:
    start: int
    end: int
    owner: SpanOwner

    def __post_init__(self) -> None:
        if not isinstance(self.owner, SpanOwner) or not isinstance(self.start, int) or not isinstance(self.end, int):
            raise AuthorityError("ownership span fields are invalid")
        if self.start < 0 or self.end <= self.start:
            raise AuthorityError("ownership span must be nonempty and nonnegative")


def _span_records(spans: Sequence[OwnershipSpan]) -> list[dict[str, object]]:
    return [{"start": item.start, "end": item.end, "owner": item.owner.value} for item in spans]


def _validate_partition(evidence: SourceEvidence, spans: Sequence[OwnershipSpan]) -> dict[str, int]:
    cursor = 0
    totals = {owner.value: 0 for owner in SpanOwner}
    for span in spans:
        if span.start != cursor or span.end > evidence.byte_length:
            raise AuthorityError("ownership spans must form a total ordered non-overlapping partition")
        if not evidence.utf8_boundary(span.start) or not evidence.utf8_boundary(span.end):
            raise AuthorityError("ownership span cuts a UTF-8 code point")
        totals[span.owner.value] += span.end - span.start
        cursor = span.end
    if cursor != evidence.byte_length:
        raise AuthorityError("ownership spans do not cover all source bytes")
    return totals


def recompute_manifest(evidence: SourceEvidence, spans: Sequence[OwnershipSpan]) -> Mapping[str, object]:
    ordered = tuple(sorted(spans, key=lambda item: (item.start, item.end, item.owner.value)))
    totals = _validate_partition(evidence, ordered)
    identity = evidence.recompute_identity()
    span_records = _span_records(ordered)
    body = {
        "source_identity": identity,
        "source_sha256": evidence.source_sha256,
        "byte_length": evidence.byte_length,
        "span_count": len(ordered),
        "spans": span_records,
        "owner_totals": totals,
        "partition_total": sum(totals.values()),
        "boundaries_utf8": True,
        "evidence_verified": evidence.verify(),
    }
    body["coverage_sha256"] = digest(body)
    return deep_freeze(body)


@dataclass(frozen=True, slots=True)
class FinalizedLedger:
    evidence: SourceEvidence
    spans: tuple[OwnershipSpan, ...]
    _manifest: Mapping[str, object]

    @classmethod
    def from_spans(cls, evidence: SourceEvidence, spans: Iterable[OwnershipSpan]) -> "FinalizedLedger":
        if not evidence.verify():
            raise AuthorityError("ledger requires verified source evidence")
        ordered = tuple(sorted(tuple(spans), key=lambda item: (item.start, item.end, item.owner.value)))
        return cls(evidence, ordered, recompute_manifest(evidence, ordered))

    @property
    def coverage_manifest(self) -> Mapping[str, object]:
        return deep_freeze(thaw(self._manifest))

    def fresh_manifest(self) -> Mapping[str, object]:
        return recompute_manifest(self.evidence, self.spans)

    def verify(self) -> bool:
        try:
            expected = self.fresh_manifest()
        except AuthorityError:
            return False
        return thaw(self._manifest) == thaw(expected) and self.evidence.verify()

    def is_exact_atom_candidate(self, start: int, end: int) -> bool:
        return any(item.start == start and item.end == end and item.owner is SpanOwner.ATOM_CANDIDATE for item in self.spans)


def _partition_from_markers(evidence: SourceEvidence, markers: Sequence[tuple[int, int, SpanOwner]]) -> tuple[OwnershipSpan, ...]:
    """Turn non-overlapping marked regions into a byte-complete partition."""
    ordered = sorted(markers, key=lambda item: (item[0], item[1], item[2].value))
    result: list[OwnershipSpan] = []
    cursor = 0
    for start, end, owner in ordered:
        if start < cursor or end > evidence.byte_length or start >= end:
            raise AuthorityError("format markers overlap or fall outside source")
        if cursor < start:
            result.append(OwnershipSpan(cursor, start, SpanOwner.STRUCTURAL))
        result.append(OwnershipSpan(start, end, owner))
        cursor = end
    if cursor < evidence.byte_length:
        result.append(OwnershipSpan(cursor, evidence.byte_length, SpanOwner.STRUCTURAL))
    if not result:
        raise AuthorityError("empty source has no atomizable public bytes")
    _validate_partition(evidence, result)
    return tuple(result)


def _json_value_string_markers(data: bytes, *, base: int = 0) -> list[tuple[int, int, SpanOwner]]:
    """Mark only string *contents* that are values; keys and syntax stay structural."""
    markers: list[tuple[int, int, SpanOwner]] = []
    index = 0
    length = len(data)
    while index < length:
        if data[index] != 0x22:
            index += 1
            continue
        quote_start = index
        index += 1
        content_start = index
        escaped = False
        while index < length:
            current = data[index]
            if escaped:
                escaped = False
            elif current == 0x5C:
                escaped = True
            elif current == 0x22:
                break
            index += 1
        if index >= length:
            raise AuthorityError("JSON string terminator missing")
        content_end = index
        index += 1
        lookahead = index
        while lookahead < length and data[lookahead] in b" \t\r\n":
            lookahead += 1
        # A string followed by ':' is a key. Its quotes and escape syntax remain structural.
        if lookahead >= length or data[lookahead] != 0x3A:
            if content_start != content_end:
                markers.append((base + content_start, base + content_end, SpanOwner.ATOM_CANDIDATE))
    return markers


def _line_ranges(data: bytes) -> list[tuple[int, int, int]]:
    ranges: list[tuple[int, int, int]] = []
    start = 0
    for index, value in enumerate(data):
        if value == 0x0A:
            content_end = index - 1 if index > start and data[index - 1] == 0x0D else index
            ranges.append((start, content_end, index + 1))
            start = index + 1
    if start < len(data):
        ranges.append((start, len(data), len(data)))
    return ranges


def _markdown_markers(data: bytes) -> list[tuple[int, int, SpanOwner]]:
    markers: list[tuple[int, int, SpanOwner]] = []
    fenced = False
    for start, content_end, end in _line_ranges(data):
        raw = data[start:content_end]
        stripped = raw.lstrip(b" \t")
        indentation = len(raw) - len(stripped)
        if stripped.startswith((b"```", b"~~~")):
            fenced = not fenced
            continue
        if fenced or not stripped or stripped.startswith(b"#") or stripped.startswith(b"|") or b"|" in stripped:
            continue
        if stripped == b"[REDACTED]":
            markers.append((start, content_end, SpanOwner.REDACTED))
            continue
        prefix = 0
        if stripped.startswith(b">"):
            prefix = 1 + (1 if len(stripped) > 1 and stripped[1:2] == b" " else 0)
        else:
            match = re.match(rb"(?:[-+*]|\d+[.)])\s+", stripped)
            if match:
                prefix = match.end()
        candidate_start = start + indentation + prefix
        if candidate_start < content_end:
            markers.append((candidate_start, content_end, SpanOwner.ATOM_CANDIDATE))
    if fenced:
        raise AuthorityError("markdown fence is unterminated")
    return markers


def build_ledger(evidence: SourceEvidence) -> FinalizedLedger:
    if evidence.byte_length == 0:
        raise AuthorityError("empty source has no atomizable public bytes")
    data = evidence.bytes_slice(0, evidence.byte_length)
    if evidence.format_name == "json":
        try:
            json.loads(data.decode("utf-8", "strict"))
        except json.JSONDecodeError as exc:
            raise AuthorityError("JSON source is structurally invalid") from exc
        markers = _json_value_string_markers(data)
    elif evidence.format_name == "jsonl":
        markers = []
        for start, content_end, _end in _line_ranges(data):
            line = data[start:content_end]
            if not line.strip():
                continue
            try:
                json.loads(line.decode("utf-8", "strict"))
            except json.JSONDecodeError as exc:
                raise AuthorityError("JSONL line is structurally invalid") from exc
            markers.extend(_json_value_string_markers(line, base=start))
    elif evidence.format_name == "markdown":
        markers = _markdown_markers(data)
    else:
        markers = []
        for start, content_end, _end in _line_ranges(data):
            if start < content_end and data[start:content_end].strip():
                markers.append((start, content_end, SpanOwner.ATOM_CANDIDATE))
    return FinalizedLedger.from_spans(evidence, _partition_from_markers(evidence, markers))


@dataclass(frozen=True, slots=True)
class CanonicalAtom:
    atom_id: str
    atom_type: str
    source_sha256: str
    start: int
    end: int
    text: str
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class CanonicalField:
    field_id: str
    atom_id: str
    name: str
    rule: FieldRule
    start: int
    end: int
    value: object
    evidence_sha256: str


class AtomFactory:
    def __init__(self, evidence: SourceEvidence, ledger: FinalizedLedger) -> None:
        if ledger.evidence is not evidence or not ledger.verify():
            raise AuthorityError("atom factory requires one verified source and ledger")
        self._evidence = evidence
        self._ledger = ledger
        self._issued: dict[str, CanonicalAtom] = {}

    def issue(self, start: int, end: int, *, atom_type: str = "claim") -> CanonicalAtom:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", atom_type) or atom_type == "fact":
            raise AuthorityError("atom type is not admitted")
        if not self._ledger.is_exact_atom_candidate(start, end):
            raise AuthorityError("atom must match one complete candidate-owned span")
        raw = self._evidence.bytes_slice(start, end)
        text = self._evidence.text_slice(start, end)
        atom_id = "atom:" + digest({"source_sha256": self._evidence.source_sha256, "start": start, "end": end, "atom_type": atom_type})
        evidence_sha256 = sha256(raw).hexdigest()
        atom = CanonicalAtom(atom_id, atom_type, self._evidence.source_sha256, start, end, text, evidence_sha256)
        self._issued[atom_id] = atom
        return atom

    def verify(self, atom: CanonicalAtom) -> bool:
        if self._issued.get(getattr(atom, "atom_id", "")) is not atom or not self._ledger.verify():
            return False
        try:
            raw = self._evidence.bytes_slice(atom.start, atom.end)
            expected = self.issue_preview(atom.start, atom.end, atom.atom_type)
        except (AuthorityError, AttributeError):
            return False
        return atom == expected and atom.text == raw.decode("utf-8", "strict")

    def issue_preview(self, start: int, end: int, atom_type: str) -> CanonicalAtom:
        if not self._ledger.is_exact_atom_candidate(start, end):
            raise AuthorityError("atom must match one complete candidate-owned span")
        raw = self._evidence.bytes_slice(start, end)
        return CanonicalAtom(
            "atom:" + digest({"source_sha256": self._evidence.source_sha256, "start": start, "end": end, "atom_type": atom_type}),
            atom_type,
            self._evidence.source_sha256,
            start,
            end,
            raw.decode("utf-8", "strict"),
            sha256(raw).hexdigest(),
        )

    def extract_field(self, atom: CanonicalAtom, *, name: str, start: int, end: int, rule: FieldRule) -> CanonicalField:
        if not self.verify(atom):
            raise AuthorityError("field requires a factory-issued atom")
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name):
            raise AuthorityError("field name is not admitted")
        if not isinstance(rule, FieldRule) or not atom.start <= start < end <= atom.end:
            raise AuthorityError("field range or rule is invalid")
        raw = self._evidence.bytes_slice(start, end)
        text = self._evidence.text_slice(start, end)
        if rule is FieldRule.EXACT_UTF8_SLICE:
            value: object = text
        elif rule is FieldRule.ASCII_LOWER_STRIP:
            if any(ord(char) > 127 for char in text):
                raise AuthorityError("ASCII_LOWER_STRIP rejects non-ASCII source")
            value = text.strip().lower()
        else:
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise AuthorityError("JSON_STRING field is invalid JSON") from exc
            if not isinstance(value, str):
                raise AuthorityError("JSON_STRING field must decode to a string")
        field_id = "field:" + digest({"atom_id": atom.atom_id, "name": name, "rule": rule.value, "start": start, "end": end, "value": value, "evidence_sha256": sha256(raw).hexdigest()})
        return CanonicalField(field_id, atom.atom_id, name, rule, start, end, value, sha256(raw).hexdigest())

    def verify_field(self, field: CanonicalField) -> bool:
        try:
            atom = self._issued.get(field.atom_id)
            if atom is None:
                return False
            return field == self.extract_field(atom, name=field.name, start=field.start, end=field.end, rule=field.rule)
        except (AuthorityError, AttributeError):
            return False


class VerifiedAtomRegistry:
    def __init__(self, factory: AtomFactory) -> None:
        self._factory = factory
        self._atoms: dict[str, CanonicalAtom] = {}

    @property
    def evidence(self) -> SourceEvidence:
        return self._factory._evidence

    def register(self, atom: CanonicalAtom) -> CanonicalAtom:
        if not self._factory.verify(atom):
            raise AuthorityError("registry only admits factory-issued atoms")
        existing = self._atoms.get(atom.atom_id)
        if existing is not None and existing is not atom:
            raise AuthorityError("atom identity collision")
        self._atoms[atom.atom_id] = atom
        return atom

    def get(self, atom_id: str) -> CanonicalAtom:
        atom = self._atoms.get(atom_id)
        if atom is None or not self._factory.verify(atom):
            raise AuthorityError("atom is absent from verified registry")
        return atom

    def all(self) -> tuple[CanonicalAtom, ...]:
        return tuple(self.get(key) for key in sorted(self._atoms))


@dataclass(frozen=True, slots=True)
class TypedRelation:
    relation_id: str
    relation_type: str
    source_atom_id: str
    target_atom_id: str
    source_sha256: str
    evidence_sha256: str
    start: int
    end: int


class RelationFactory:
    def __init__(self, registry: VerifiedAtomRegistry) -> None:
        self._registry = registry
        self._issued: dict[str, TypedRelation] = {}

    def issue(self, source_atom_id: str, target_atom_id: str, *, start: int, end: int, relation_type: str = "supports") -> TypedRelation:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", relation_type):
            raise AuthorityError("relation type is not admitted")
        source = self._registry.get(source_atom_id)
        target = self._registry.get(target_atom_id)
        raw = self._registry.evidence.bytes_slice(start, end)
        if not raw:
            raise AuthorityError("relation evidence slice must be nonempty")
        payload = {
            "relation_type": relation_type,
            "source_atom_id": source.atom_id,
            "target_atom_id": target.atom_id,
            "source_sha256": self._registry.evidence.source_sha256,
            "evidence_sha256": sha256(raw).hexdigest(),
            "evidence_hex": raw.hex(),
            "start": start,
            "end": end,
        }
        relation = TypedRelation(
            "rel:" + digest(payload), relation_type, source.atom_id, target.atom_id,
            self._registry.evidence.source_sha256, sha256(raw).hexdigest(), start, end,
        )
        self._issued[relation.relation_id] = relation
        return relation

    def verify(self, relation: TypedRelation) -> bool:
        if self._issued.get(getattr(relation, "relation_id", "")) is not relation:
            return False
        try:
            expected = self.issue_preview(relation)
        except (AuthorityError, AttributeError):
            return False
        return relation == expected

    def issue_preview(self, relation: TypedRelation) -> TypedRelation:
        source = self._registry.get(relation.source_atom_id)
        target = self._registry.get(relation.target_atom_id)
        raw = self._registry.evidence.bytes_slice(relation.start, relation.end)
        payload = {
            "relation_type": relation.relation_type,
            "source_atom_id": source.atom_id,
            "target_atom_id": target.atom_id,
            "source_sha256": self._registry.evidence.source_sha256,
            "evidence_sha256": sha256(raw).hexdigest(),
            "evidence_hex": raw.hex(),
            "start": relation.start,
            "end": relation.end,
        }
        return TypedRelation(
            "rel:" + digest(payload), relation.relation_type, source.atom_id, target.atom_id,
            self._registry.evidence.source_sha256, sha256(raw).hexdigest(), relation.start, relation.end,
        )


@dataclass(frozen=True, slots=True)
class CanonicalPacket:
    packet_id: str
    canonical_json: bytes
    source_identity: Mapping[str, object]
    coverage_manifest: Mapping[str, object]
    atom_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _PacketSnapshot:
    atoms: tuple[CanonicalAtom, ...]
    relations: tuple[TypedRelation, ...]
    fields: tuple[CanonicalField, ...]
    unknowns: tuple[str, ...]
    conflicts: tuple[str, ...]
    redaction_lineage: tuple[str, ...]
    validation: Mapping[str, object]


def _atom_dict(atom: CanonicalAtom) -> dict[str, object]:
    return {"atom_id": atom.atom_id, "atom_type": atom.atom_type, "source_sha256": atom.source_sha256, "start": atom.start, "end": atom.end, "text": atom.text, "evidence_sha256": atom.evidence_sha256}


def _relation_dict(relation: TypedRelation) -> dict[str, object]:
    return {"relation_id": relation.relation_id, "relation_type": relation.relation_type, "source_atom_id": relation.source_atom_id, "target_atom_id": relation.target_atom_id, "source_sha256": relation.source_sha256, "evidence_sha256": relation.evidence_sha256, "start": relation.start, "end": relation.end}


def _field_dict(field: CanonicalField) -> dict[str, object]:
    return {"field_id": field.field_id, "atom_id": field.atom_id, "name": field.name, "rule": field.rule.value, "start": field.start, "end": field.end, "value": field.value, "evidence_sha256": field.evidence_sha256}


class CanonicalPacketFactory:
    def __init__(self, evidence: SourceEvidence, ledger: FinalizedLedger, registry: VerifiedAtomRegistry, relations: RelationFactory) -> None:
        if registry.evidence is not evidence or ledger.evidence is not evidence or not evidence.verify() or not ledger.verify():
            raise AuthorityError("packet factory requires one verified graph")
        self._evidence = evidence
        self._ledger = ledger
        self._registry = registry
        self._relations = relations
        self._issued: dict[str, tuple[CanonicalPacket, _PacketSnapshot]] = {}

    def _build_body(self, snapshot: _PacketSnapshot) -> dict[str, object]:
        for atom in snapshot.atoms:
            if self._registry.get(atom.atom_id) is not atom:
                raise AuthorityError("packet contains a foreign or stale atom")
        for relation in snapshot.relations:
            if not self._relations.verify(relation):
                raise AuthorityError("packet contains a foreign or stale relation")
        for field in snapshot.fields:
            if not self._registry._factory.verify_field(field):
                raise AuthorityError("packet contains foreign or altered field evidence")
        fresh_manifest = self._ledger.fresh_manifest()
        if not self._ledger.verify():
            raise AuthorityError("packet ledger verification failed")
        return {
            "schema_version": "e54.1",
            "source_identity": self._evidence.recompute_identity(),
            "coverage_manifest": thaw(fresh_manifest),
            "atoms": [_atom_dict(atom) for atom in snapshot.atoms],
            "relations": [_relation_dict(relation) for relation in snapshot.relations],
            "fields": [_field_dict(field) for field in snapshot.fields],
            "unknowns": list(snapshot.unknowns),
            "conflicts": list(snapshot.conflicts),
            "redaction_lineage": list(snapshot.redaction_lineage),
            "validation": thaw(snapshot.validation),
        }

    def issue(self, *, atoms: Sequence[CanonicalAtom], relations: Sequence[TypedRelation], fields: Sequence[CanonicalField] = (), unknowns: Sequence[str] = (), conflicts: Sequence[str] = (), redaction_lineage: Sequence[str] = (), validation: Mapping[str, object] | None = None) -> CanonicalPacket:
        if len({atom.atom_id for atom in atoms}) != len(atoms) or len({item.relation_id for item in relations}) != len(relations) or len({item.field_id for item in fields}) != len(fields):
            raise AuthorityError("duplicate graph identities are rejected")
        snapshot = _PacketSnapshot(
            tuple(sorted(atoms, key=lambda atom: atom.atom_id)),
            tuple(sorted(relations, key=lambda item: item.relation_id)),
            tuple(sorted(fields, key=lambda item: item.field_id)),
            tuple(sorted(set(unknowns))), tuple(sorted(set(conflicts))), tuple(sorted(set(redaction_lineage))),
            deep_freeze(dict(validation or {})),
        )
        body = self._build_body(snapshot)
        canonical_json = canonical_bytes(body)
        packet = CanonicalPacket(
            "packet:" + sha256(canonical_json).hexdigest(), canonical_json,
            deep_freeze(self._evidence.recompute_identity()), self._ledger.fresh_manifest(),
            tuple(atom.atom_id for atom in snapshot.atoms), tuple(item.relation_id for item in snapshot.relations),
        )
        self._issued[packet.packet_id] = (packet, snapshot)
        return packet

    def verify(self, packet: CanonicalPacket) -> bool:
        issued = self._issued.get(getattr(packet, "packet_id", ""))
        if issued is None or issued[0] is not packet:
            return False
        try:
            body = self._build_body(issued[1])
            expected_json = canonical_bytes(body)
            expected_id = "packet:" + sha256(expected_json).hexdigest()
            expected_identity = deep_freeze(self._evidence.recompute_identity())
            expected_manifest = self._ledger.fresh_manifest()
        except (AuthorityError, TypeError, ValueError):
            return False
        return (
            packet.canonical_json == expected_json
            and packet.packet_id == expected_id
            and thaw(packet.source_identity) == thaw(expected_identity)
            and thaw(packet.coverage_manifest) == thaw(expected_manifest)
            and packet.atom_ids == tuple(atom.atom_id for atom in issued[1].atoms)
            and packet.relation_ids == tuple(item.relation_id for item in issued[1].relations)
        )
