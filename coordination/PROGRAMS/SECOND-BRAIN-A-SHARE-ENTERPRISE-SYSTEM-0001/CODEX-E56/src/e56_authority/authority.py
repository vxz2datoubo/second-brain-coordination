"""Immutable source admission, total format ownership and verified records.

This module deliberately treats Python reflection as outside the ordinary-caller
threat model. Public authority objects expose no mutable registry, seal or
policy attribute; every downstream object is re-derived from a closure-held
record of exact admitted bytes before it can be used.
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
    """Raised when an E56 authority invariant is not satisfied."""


def canonical_bytes(value: object) -> bytes:
    """Encode the finite public-safe JSON domain deterministically."""

    def normalize(item: object) -> object:
        if isinstance(item, Mapping):
            return {str(key): normalize(value) for key, value in sorted(item.items(), key=lambda pair: str(pair[0]))}
        if isinstance(item, tuple | list):
            return [normalize(value) for value in item]
        if item is None or isinstance(item, str | int | float | bool):
            return item
        raise AuthorityError("value falls outside the canonical JSON domain")

    try:
        return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AuthorityError("value cannot be canonically encoded") from exc


def stable_digest(value: object) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


_FORMATS = frozenset({"text", "markdown", "json", "jsonl"})
_SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}")
_BLOCKED = re.compile(r"(?:-----BEGIN(?:[ -][A-Z0-9]+){0,5}(?:-----)?|gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class AdmissionPolicy:
    version: str = "e56-admission-policy-v1"
    max_bytes: int = 1_000_000
    formats: tuple[str, ...] = ("json", "jsonl", "markdown", "text")

    @property
    def identity(self) -> str:
        return stable_digest({"version": self.version, "max_bytes": self.max_bytes, "formats": self.formats})

    def validate(self, data: bytes, source_id: str, format_name: str) -> None:
        if not isinstance(data, bytes) or not data:
            raise AuthorityError("source must be nonempty exact bytes")
        if len(data) > self.max_bytes:
            raise AuthorityError("source exceeds the admission byte limit")
        if not isinstance(source_id, str) or not _SOURCE_ID.fullmatch(source_id):
            raise AuthorityError("source_id is not an admitted public identifier")
        if format_name not in self.formats or format_name not in _FORMATS:
            raise AuthorityError("source format is not admitted by this policy")
        try:
            text = data.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise AuthorityError("source is not strict UTF-8") from exc
        if _BLOCKED.search(text):
            raise AuthorityError("blocked credential or private-key marker in source")
        if format_name == "json":
            _parse_json(text)
        elif format_name == "jsonl":
            for number, line in enumerate(text.splitlines(), start=1):
                if line.strip():
                    try:
                        _parse_json(line)
                    except AuthorityError as exc:
                        raise AuthorityError(f"invalid JSONL record at line {number}") from exc


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    """A public value; authority comes only from the closure-held registry."""

    data: bytes
    source_id: str
    format_name: str
    source_sha256: str
    policy_identity: str

    def identity(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "source_id": self.source_id,
                "format": self.format_name,
                "source_sha256": self.source_sha256,
                "byte_length": len(self.data),
                "policy_identity": self.policy_identity,
            }
        )


@dataclass(frozen=True, slots=True)
class _IssuedSourceRecord:
    source: SourceEvidence
    exact_data: bytes
    source_id: str
    format_name: str
    source_sha256: str
    policy_identity: str


@dataclass(frozen=True, slots=True)
class _AdmissionState:
    authority: object
    policy: AdmissionPolicy
    issued: dict[int, _IssuedSourceRecord]


# These closure-like module internals are intentionally not exposed through any
# public authority object. Their entries hold original object references so an
# id cannot be reused after a source value dies.
_ADMISSION_STATES: dict[int, _AdmissionState] = {}


class SourceAdmission:
    """Issues sources without public policy, registry or seal state."""

    __slots__ = ()

    def __init__(self, policy: AdmissionPolicy | None = None) -> None:
        selected = policy or AdmissionPolicy()
        if not isinstance(selected, AdmissionPolicy):
            raise AuthorityError("admission policy type is invalid")
        _ADMISSION_STATES[id(self)] = _AdmissionState(self, selected, {})

    def _state(self) -> _AdmissionState:
        state = _ADMISSION_STATES.get(id(self))
        if state is None or state.authority is not self:
            raise AuthorityError("admission authority state is absent")
        return state

    @property
    def policy_identity(self) -> str:
        return self._state().policy.identity

    def admit(self, data: bytes, *, source_id: str, format_name: str) -> SourceEvidence:
        state = self._state()
        copied = bytes(data)
        state.policy.validate(copied, source_id, format_name)
        evidence = SourceEvidence(copied, source_id, format_name, sha256(copied).hexdigest(), state.policy.identity)
        state.issued[id(evidence)] = _IssuedSourceRecord(
            evidence, copied, source_id, format_name, sha256(copied).hexdigest(), state.policy.identity
        )
        return evidence

    def verify(self, value: object) -> bool:
        if not isinstance(value, SourceEvidence):
            return False
        try:
            state = self._state()
            record = state.issued.get(id(value))
            if record is None or record.source is not value:
                return False
            if (
                value.data != record.exact_data
                or value.source_id != record.source_id
                or value.format_name != record.format_name
                or value.source_sha256 != record.source_sha256
                or value.policy_identity != record.policy_identity
                or record.policy_identity != state.policy.identity
            ):
                return False
            state.policy.validate(record.exact_data, record.source_id, record.format_name)
            return sha256(record.exact_data).hexdigest() == record.source_sha256
        except (AuthorityError, AttributeError):
            return False

    def require(self, value: object) -> SourceEvidence:
        if not self.verify(value):
            raise AuthorityError("source was not issued and revalidated by this admission authority")
        return value


class SpanOwner(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    SEMANTIC = "SEMANTIC"
    REDACTED = "REDACTED"


@dataclass(frozen=True, slots=True, order=True)
class ByteRange:
    start: int
    end: int

    def __post_init__(self) -> None:
        if not isinstance(self.start, int) or not isinstance(self.end, int) or self.start >= self.end or self.start < 0:
            raise AuthorityError("byte range is invalid")


@dataclass(frozen=True, slots=True, order=True)
class OwnershipSpan:
    start: int
    end: int
    owner: SpanOwner


@dataclass(frozen=True, slots=True)
class DecodedCharacter:
    text: str
    raw: ByteRange
    escaped: bool


@dataclass(frozen=True, slots=True)
class SemanticSpan:
    span_id: str
    source_sha256: str
    raw_ranges: tuple[ByteRange, ...]
    decoded_text: str
    origin: str
    decoded_evidence_sha256: str


@dataclass(frozen=True, slots=True)
class _JsonString:
    quote_start: int
    quote_end: int
    decoded: str
    characters: tuple[DecodedCharacter, ...]
    is_key: bool


def _parse_json(text: str) -> object:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        output: dict[str, object] = {}
        for key, value in items:
            if key in output:
                raise AuthorityError("duplicate JSON key is rejected")
            output[key] = value
        return output

    try:
        return json.loads(text, object_pairs_hook=pairs)
    except AuthorityError:
        raise
    except json.JSONDecodeError as exc:
        raise AuthorityError("JSON source is structurally invalid") from exc


def _utf8_end(data: bytes, index: int) -> int:
    lead = data[index]
    if lead < 0x80:
        return index + 1
    if 0xC2 <= lead <= 0xDF:
        return index + 2
    if 0xE0 <= lead <= 0xEF:
        return index + 3
    if 0xF0 <= lead <= 0xF4:
        return index + 4
    raise AuthorityError("invalid UTF-8 lead byte in JSON string")


def _scan_json_string(data: bytes, quote_start: int) -> tuple[_JsonString, int]:
    index = quote_start + 1
    characters: list[DecodedCharacter] = []
    while index < len(data):
        current = data[index]
        if current == 0x22:
            quote_end = index + 1
            try:
                decoded = json.loads(data[quote_start:quote_end].decode("utf-8", "strict"))
            except json.JSONDecodeError as exc:
                raise AuthorityError("invalid JSON string") from exc
            if not isinstance(decoded, str) or "".join(item.text for item in characters) != decoded:
                raise AuthorityError("JSON raw-to-decoded mapping is inconsistent")
            lookahead = quote_end
            while lookahead < len(data) and data[lookahead] in b" \t\r\n":
                lookahead += 1
            return _JsonString(quote_start, quote_end, decoded, tuple(characters), lookahead < len(data) and data[lookahead] == 0x3A), quote_end
        if current == 0x5C:
            end = index + 2
            if end > len(data):
                raise AuthorityError("truncated JSON escape")
            if data[index + 1] == ord("u"):
                end = index + 6
                if end > len(data) or not re.fullmatch(rb"[0-9A-Fa-f]{4}", data[index + 2:end]):
                    raise AuthorityError("invalid JSON unicode escape")
            try:
                piece = json.loads(b'"' + data[index:end] + b'"')
            except json.JSONDecodeError as exc:
                raise AuthorityError("invalid JSON escape") from exc
            characters.extend(DecodedCharacter(char, ByteRange(index, end), True) for char in piece)
            index = end
            continue
        end = _utf8_end(data, index)
        try:
            piece = data[index:end].decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise AuthorityError("invalid UTF-8 inside JSON string") from exc
        characters.append(DecodedCharacter(piece, ByteRange(index, end), False))
        index = end
    raise AuthorityError("JSON string has no closing quote")


def _json_strings(data: bytes, base: int = 0) -> tuple[_JsonString, ...]:
    tokens: list[_JsonString] = []
    index = 0
    while index < len(data):
        if data[index] == 0x22:
            token, index = _scan_json_string(data, index)
            tokens.append(
                _JsonString(
                    base + token.quote_start,
                    base + token.quote_end,
                    token.decoded,
                    tuple(DecodedCharacter(char.text, ByteRange(base + char.raw.start, base + char.raw.end), char.escaped) for char in token.characters),
                    token.is_key,
                )
            )
        else:
            index += 1
    return tuple(tokens)


def _lines(data: bytes) -> tuple[tuple[int, int], ...]:
    output: list[tuple[int, int]] = []
    start = 0
    for index, byte in enumerate(data):
        if byte == 0x0A:
            end = index - 1 if index > start and data[index - 1] == 0x0D else index
            output.append((start, end))
            start = index + 1
    if start < len(data):
        output.append((start, len(data)))
    return tuple(output)


def _partition(length: int, markers: Sequence[OwnershipSpan]) -> tuple[OwnershipSpan, ...]:
    result: list[OwnershipSpan] = []
    cursor = 0
    for marker in sorted(markers, key=lambda item: (item.start, item.end, item.owner.value)):
        if not 0 <= cursor <= marker.start < marker.end <= length:
            raise AuthorityError("ownership spans overlap or leave source bounds")
        if cursor < marker.start:
            result.append(OwnershipSpan(cursor, marker.start, SpanOwner.STRUCTURAL))
        result.append(marker)
        cursor = marker.end
    if cursor < length:
        result.append(OwnershipSpan(cursor, length, SpanOwner.STRUCTURAL))
    if not result:
        raise AuthorityError("ownership partition is empty")
    if result[0].start != 0 or result[-1].end != length:
        raise AuthorityError("ownership partition is incomplete")
    if any(left.end != right.start for left, right in zip(result, result[1:])):
        raise AuthorityError("ownership partition is not contiguous")
    return tuple(result)


def _semantic(source: SourceEvidence, ranges: Sequence[ByteRange], decoded: str, origin: str) -> SemanticSpan:
    if not ranges or not decoded:
        raise AuthorityError("semantic evidence must have decoded text and exact raw ranges")
    mapping = {
        "source": source.source_sha256,
        "ranges": [{"start": item.start, "end": item.end} for item in ranges],
        "decoded": decoded,
        "origin": origin,
    }
    digest = stable_digest(mapping)
    return SemanticSpan("span:" + digest, source.source_sha256, tuple(ranges), decoded, origin, digest)


def _text_ownership(source: SourceEvidence) -> tuple[tuple[OwnershipSpan, ...], tuple[SemanticSpan, ...]]:
    markers: list[OwnershipSpan] = []
    semantic: list[SemanticSpan] = []
    for start, end in _lines(source.data):
        raw = source.data[start:end]
        if not raw.strip():
            continue
        if raw == b"[REDACTED]":
            markers.append(OwnershipSpan(start, end, SpanOwner.REDACTED))
            continue
        markers.append(OwnershipSpan(start, end, SpanOwner.SEMANTIC))
        semantic.append(_semantic(source, (ByteRange(start, end),), raw.decode("utf-8", "strict"), "text_line_v1"))
    return _partition(len(source.data), markers), tuple(sorted(semantic, key=lambda item: item.span_id))


_MD_PREFIX = re.compile(rb"(?: {0,3}(?:#{1,6}[ \t]+|>[ \t]?|[-+*][ \t]+|\d+[.)][ \t]+))")
_MD_PUNCTUATION = frozenset(b"|`[]()_*#")


def _markdown_ownership(source: SourceEvidence) -> tuple[tuple[OwnershipSpan, ...], tuple[SemanticSpan, ...]]:
    markers: list[OwnershipSpan] = []
    semantic: list[SemanticSpan] = []
    fenced = False
    for start, end in _lines(source.data):
        raw = source.data[start:end]
        if raw.lstrip().startswith((b"```", b"~~~")):
            fenced = not fenced
            continue
        if fenced or not raw.strip() or re.fullmatch(rb"[ \t|:-]+", raw):
            continue
        match = _MD_PREFIX.match(raw)
        content_start = start + (match.end() if match else 0)
        cursor = content_start
        for offset in range(content_start, end):
            if source.data[offset] in _MD_PUNCTUATION:
                if cursor < offset and source.data[cursor:offset].strip():
                    markers.append(OwnershipSpan(cursor, offset, SpanOwner.SEMANTIC))
                    semantic.append(_semantic(source, (ByteRange(cursor, offset),), source.data[cursor:offset].decode("utf-8", "strict"), "markdown_content_v1"))
                cursor = offset + 1
        if cursor < end and source.data[cursor:end].strip():
            markers.append(OwnershipSpan(cursor, end, SpanOwner.SEMANTIC))
            semantic.append(_semantic(source, (ByteRange(cursor, end),), source.data[cursor:end].decode("utf-8", "strict"), "markdown_content_v1"))
    return _partition(len(source.data), markers), tuple(sorted(semantic, key=lambda item: item.span_id))


def _json_ownership(source: SourceEvidence, jsonl: bool) -> tuple[tuple[OwnershipSpan, ...], tuple[SemanticSpan, ...]]:
    markers: list[OwnershipSpan] = []
    semantic: list[SemanticSpan] = []
    line_sets = _lines(source.data) if jsonl else ((0, len(source.data)),)
    for start, end in line_sets:
        payload = source.data[start:end]
        if not payload.strip():
            continue
        _parse_json(payload.decode("utf-8", "strict"))
        for token in _json_strings(payload, start):
            if token.is_key or not token.decoded:
                continue
            literal_ranges = tuple(item.raw for item in token.characters if not item.escaped)
            for byte_range in literal_ranges:
                markers.append(OwnershipSpan(byte_range.start, byte_range.end, SpanOwner.SEMANTIC))
            semantic.append(_semantic(source, tuple(item.raw for item in token.characters), token.decoded, "json_decoded_value_v1"))
    return _partition(len(source.data), markers), tuple(sorted(semantic, key=lambda item: item.span_id))


@dataclass(frozen=True, slots=True)
class EvidenceLedger:
    source: SourceEvidence
    ownership: tuple[OwnershipSpan, ...]
    semantic_spans: tuple[SemanticSpan, ...]
    manifest_sha256: str
    _admission: SourceAdmission

    def verify(self) -> bool:
        if not self._admission.verify(self.source):
            return False
        try:
            rebuilt_ownership, rebuilt_semantic = _build_ownership(self.source)
            manifest = _ledger_manifest(self.source, rebuilt_ownership, rebuilt_semantic)
            return rebuilt_ownership == self.ownership and rebuilt_semantic == self.semantic_spans and stable_digest(manifest) == self.manifest_sha256
        except AuthorityError:
            return False

    def semantic(self, span_id: str) -> SemanticSpan:
        if not self.verify():
            raise AuthorityError("ledger failed revalidation")
        for span in self.semantic_spans:
            if span.span_id == span_id:
                return span
        raise AuthorityError("semantic span is not admitted")


def _build_ownership(source: SourceEvidence) -> tuple[tuple[OwnershipSpan, ...], tuple[SemanticSpan, ...]]:
    if source.format_name == "text":
        return _text_ownership(source)
    if source.format_name == "markdown":
        return _markdown_ownership(source)
    return _json_ownership(source, source.format_name == "jsonl")


def _ledger_manifest(source: SourceEvidence, ownership: Sequence[OwnershipSpan], semantic: Sequence[SemanticSpan]) -> Mapping[str, object]:
    return {
        "source": dict(source.identity()),
        "ownership": [{"start": item.start, "end": item.end, "owner": item.owner.value} for item in ownership],
        "semantic": [
            {"id": item.span_id, "ranges": [{"start": raw.start, "end": raw.end} for raw in item.raw_ranges], "decoded": item.decoded_text, "origin": item.origin, "decoded_evidence": item.decoded_evidence_sha256}
            for item in semantic
        ],
    }


def build_ledger(admission: SourceAdmission, source: SourceEvidence) -> EvidenceLedger:
    admission.require(source)
    ownership, semantic = _build_ownership(source)
    return EvidenceLedger(source, ownership, semantic, stable_digest(_ledger_manifest(source, ownership, semantic)), admission)


@dataclass(frozen=True, slots=True)
class CanonicalAtom:
    atom_id: str
    span_id: str
    atom_type: str
    source_sha256: str
    decoded_text: str
    evidence_sha256: str


class AtomFactory:
    __slots__ = ("_ledger", "_issued")

    def __init__(self, ledger: EvidenceLedger) -> None:
        if not ledger.verify():
            raise AuthorityError("atom factory needs a verified ledger")
        self._ledger = ledger
        self._issued: dict[str, CanonicalAtom] = {}

    def issue(self, span_id: str, *, atom_type: str = "claim") -> CanonicalAtom:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", atom_type):
            raise AuthorityError("atom type is invalid")
        span = self._ledger.semantic(span_id)
        atom = CanonicalAtom(
            "atom:" + stable_digest({"span": span.span_id, "type": atom_type}), span.span_id, atom_type,
            span.source_sha256, span.decoded_text, span.decoded_evidence_sha256,
        )
        self._issued[atom.atom_id] = atom
        return atom

    def verify(self, atom: object) -> bool:
        if not isinstance(atom, CanonicalAtom) or self._issued.get(atom.atom_id) is not atom:
            return False
        try:
            span = self._ledger.semantic(atom.span_id)
            expected = CanonicalAtom("atom:" + stable_digest({"span": span.span_id, "type": atom.atom_type}), span.span_id, atom.atom_type, span.source_sha256, span.decoded_text, span.decoded_evidence_sha256)
            return atom == expected
        except AuthorityError:
            return False


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    record_id: str
    span_id: str
    source_sha256: str
    statement: str
    evidence_sha256: str


class EvidenceFactory:
    __slots__ = ("_ledger", "_issued")

    def __init__(self, ledger: EvidenceLedger) -> None:
        if not ledger.verify():
            raise AuthorityError("evidence factory needs a verified ledger")
        self._ledger = ledger
        self._issued: dict[str, EvidenceRecord] = {}

    def issue(self, span_id: str, *, statement: str | None = None) -> EvidenceRecord:
        span = self._ledger.semantic(span_id)
        derived = span.decoded_text
        if statement is not None and statement != derived:
            raise AuthorityError("evidence statement must equal its admitted decoded span")
        record = EvidenceRecord("evidence:" + stable_digest({"span": span.span_id, "statement": derived}), span.span_id, span.source_sha256, derived, span.decoded_evidence_sha256)
        self._issued[record.record_id] = record
        return record

    def verify(self, record: object) -> bool:
        if not isinstance(record, EvidenceRecord) or self._issued.get(record.record_id) is not record:
            return False
        try:
            span = self._ledger.semantic(record.span_id)
            return record == EvidenceRecord("evidence:" + stable_digest({"span": span.span_id, "statement": span.decoded_text}), span.span_id, span.source_sha256, span.decoded_text, span.decoded_evidence_sha256)
        except AuthorityError:
            return False


class RecordKind(str, Enum):
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"
    REDACTION = "REDACTION"
    VALIDATION = "VALIDATION"


@dataclass(frozen=True, slots=True)
class PacketRecord:
    record_id: str
    kind: RecordKind
    evidence_id: str
    payload: tuple[tuple[str, str], ...]


class PacketFactory:
    __slots__ = ("_evidence", "_issued")

    def __init__(self, evidence: EvidenceFactory) -> None:
        self._evidence = evidence
        self._issued: dict[str, PacketRecord] = {}

    def _issue(self, kind: RecordKind, evidence: EvidenceRecord, payload: Mapping[str, str]) -> PacketRecord:
        if not self._evidence.verify(evidence):
            raise AuthorityError("packet record requires issued source-bound evidence")
        canonical = tuple(sorted((str(key), str(value)) for key, value in payload.items()))
        allowed = {
            RecordKind.UNKNOWN: {"reason"},
            RecordKind.CONFLICT: {"conflicting_evidence_id"},
            RecordKind.REDACTION: {"reason_code"},
            RecordKind.VALIDATION: {"rule_id", "outcome"},
        }[kind]
        if {key for key, _value in canonical} != allowed:
            raise AuthorityError("packet payload does not match the kind-specific schema")
        record = PacketRecord("packet:" + stable_digest({"kind": kind.value, "evidence": evidence.record_id, "payload": canonical}), kind, evidence.record_id, canonical)
        self._issued[record.record_id] = record
        return record

    def unknown(self, evidence: EvidenceRecord, *, reason: str) -> PacketRecord:
        if not reason.strip():
            raise AuthorityError("UNKNOWN requires a nonempty reason")
        return self._issue(RecordKind.UNKNOWN, evidence, {"reason": reason})

    def conflict(self, evidence: EvidenceRecord, *, conflicting_evidence_id: str) -> PacketRecord:
        if not conflicting_evidence_id.startswith("evidence:") or conflicting_evidence_id == evidence.record_id:
            raise AuthorityError("CONFLICT requires a distinct evidence record identifier")
        return self._issue(RecordKind.CONFLICT, evidence, {"conflicting_evidence_id": conflicting_evidence_id})

    def redaction(self, evidence: EvidenceRecord, *, reason_code: str) -> PacketRecord:
        if not re.fullmatch(r"[A-Z0-9_]{3,64}", reason_code):
            raise AuthorityError("REDACTION requires a reason code")
        return self._issue(RecordKind.REDACTION, evidence, {"reason_code": reason_code})

    def validation(self, evidence: EvidenceRecord, *, rule_id: str, outcome: str) -> PacketRecord:
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{3,96}", rule_id) or outcome not in {"PASS", "FAIL"}:
            raise AuthorityError("VALIDATION requires a rule and PASS or FAIL outcome")
        return self._issue(RecordKind.VALIDATION, evidence, {"outcome": outcome, "rule_id": rule_id})

    def verify(self, record: object) -> bool:
        if not isinstance(record, PacketRecord) or self._issued.get(record.record_id) is not record:
            return False
        evidence = next((item for item in self._evidence._issued.values() if item.record_id == record.evidence_id), None)
        if evidence is None or not self._evidence.verify(evidence):
            return False
        payload = dict(record.payload)
        allowed = {
            RecordKind.UNKNOWN: {"reason"},
            RecordKind.CONFLICT: {"conflicting_evidence_id"},
            RecordKind.REDACTION: {"reason_code"},
            RecordKind.VALIDATION: {"rule_id", "outcome"},
        }[record.kind]
        if set(payload) != allowed:
            return False
        return record.record_id == "packet:" + stable_digest({"kind": record.kind.value, "evidence": evidence.record_id, "payload": tuple(sorted(record.payload))})


@dataclass(frozen=True, slots=True)
class RelationEvidence:
    relation_id: str
    from_atom_id: str
    to_atom_id: str
    relation_type: str
    evidence_id: str
    source_sha256: str
    decoded_evidence_sha256: str


class RelationFactory:
    __slots__ = ("_atoms", "_evidence", "_issued")

    def __init__(self, atoms: AtomFactory, evidence: EvidenceFactory) -> None:
        self._atoms, self._evidence, self._issued = atoms, evidence, {}

    def issue(self, from_atom: CanonicalAtom, to_atom: CanonicalAtom, *, relation_type: str, evidence: EvidenceRecord) -> RelationEvidence:
        if not self._atoms.verify(from_atom) or not self._atoms.verify(to_atom) or not self._evidence.verify(evidence):
            raise AuthorityError("relation requires verified endpoints and evidence")
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", relation_type):
            raise AuthorityError("relation type is invalid")
        if evidence.source_sha256 != from_atom.source_sha256 or evidence.source_sha256 != to_atom.source_sha256:
            raise AuthorityError("relation source differs from endpoint source")
        relation = RelationEvidence(
            "relation:" + stable_digest({"from": from_atom.atom_id, "to": to_atom.atom_id, "type": relation_type, "evidence": evidence.record_id}),
            from_atom.atom_id, to_atom.atom_id, relation_type, evidence.record_id, evidence.source_sha256, evidence.evidence_sha256,
        )
        self._issued[relation.relation_id] = relation
        return relation

    def verify(self, relation: object) -> bool:
        if not isinstance(relation, RelationEvidence) or self._issued.get(relation.relation_id) is not relation:
            return False
        evidence = next((item for item in self._evidence._issued.values() if item.record_id == relation.evidence_id), None)
        if evidence is None or not self._evidence.verify(evidence):
            return False
        atoms = [item for item in self._atoms._issued.values() if item.atom_id in {relation.from_atom_id, relation.to_atom_id}]
        if len(atoms) != 2 or any(not self._atoms.verify(item) for item in atoms):
            return False
        return relation.relation_id == "relation:" + stable_digest({"from": relation.from_atom_id, "to": relation.to_atom_id, "type": relation.relation_type, "evidence": evidence.record_id}) and relation.source_sha256 == evidence.source_sha256 and relation.decoded_evidence_sha256 == evidence.evidence_sha256
