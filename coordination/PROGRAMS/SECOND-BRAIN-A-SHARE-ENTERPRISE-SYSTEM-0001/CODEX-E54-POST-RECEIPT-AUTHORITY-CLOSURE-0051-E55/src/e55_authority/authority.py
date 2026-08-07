"""Controlled, source-bound atomization for the E55 authority closure.

The public API deliberately separates raw source admission from later graph
objects.  All downstream factories require an identity-issued, revalidated
``SourceEvidence`` object.  Python reflection is not a security boundary, but
ordinary construction, copied state, and altered fields fail closed because a
factory registry and every admission invariant are checked again.
"""

from __future__ import annotations

from base64 import b64decode
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import unquote_to_bytes


class AuthorityError(ValueError):
    """Raised when a public-safe authority invariant is not satisfied."""


def _canonical(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, tuple | list):
        return [_canonical(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise AuthorityError("value is outside the finite canonical JSON domain")


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(_canonical(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AuthorityError("value cannot be canonically encoded") from exc


def stable_digest(value: object) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))})
    if isinstance(value, tuple | list):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise AuthorityError("projection contains a noncanonical value")


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_thaw(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise AuthorityError("projection contains a noncanonical value")


_ALLOWED_FORMATS = frozenset({"text", "markdown", "json", "jsonl"})
_PRIVATE_BOUNDARY = re.compile(r"-----BEGIN(?:[ -][A-Z0-9]+){0,5}(?:-----)?", re.IGNORECASE)
_TOKEN_SHAPE = re.compile(
    r"(?:gh[pousr]_+|github_pat_+|sk-+|xox[abprs]-+|AKIA[0-9A-Z]*|AIza[0-9A-Za-z_-]*)",
    re.IGNORECASE,
)
_BASE64_TOKEN = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{4,}={0,2}(?![A-Za-z0-9+/=])")


def _blocked_marker(text: str) -> str | None:
    if _PRIVATE_BOUNDARY.search(text):
        return "private_key_boundary"
    if _TOKEN_SHAPE.search(text):
        return "credential_token_shape"
    return None


def _decoded_variants(text: str) -> Iterable[tuple[str, str]]:
    """Yield safe candidate decodings without treating a decode as trusted."""
    yield "direct", text
    try:
        percent = unquote_to_bytes(text)
        decoded = percent.decode("utf-8", "strict")
        if decoded != text:
            yield "percent", decoded
    except UnicodeDecodeError:
        pass
    for match in _BASE64_TOKEN.finditer(text):
        token = match.group(0)
        if len(token) % 4:
            continue
        try:
            raw = b64decode(token, validate=True)
            decoded = raw.decode("utf-8", "strict")
        except (ValueError, UnicodeDecodeError):
            continue
        yield "base64", decoded


def _reject_marker_variants(text: str, *, stage: str) -> None:
    for encoding, candidate in _decoded_variants(text):
        marker = _blocked_marker(candidate)
        if marker is not None:
            raise AuthorityError(f"source admission rejected {marker} in {stage}:{encoding}")


def _no_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise AuthorityError("JSON duplicate key is rejected before atomization")
        result[key] = value
    return result


def _parse_json(text: str) -> object:
    try:
        return json.loads(text, object_pairs_hook=_no_duplicate_pairs)
    except AuthorityError:
        raise
    except json.JSONDecodeError as exc:
        raise AuthorityError("JSON source is structurally invalid") from exc


def _walk_strings(value: object) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif isinstance(value, str):
        yield value


@dataclass(frozen=True, slots=True)
class AdmissionPolicy:
    """Versioned source admission policy; all policy checks are replayable."""

    version: str = "e55-admission-policy-v1"
    allowed_formats: frozenset[str] = _ALLOWED_FORMATS
    max_bytes: int = 1_000_000

    def validate(self, data: bytes, *, source_id: str, format_name: str) -> None:
        if not isinstance(data, bytes) or not data:
            raise AuthorityError("source must be nonempty bytes")
        if len(data) > self.max_bytes:
            raise AuthorityError("source exceeds the policy byte limit")
        if not isinstance(source_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}", source_id):
            raise AuthorityError("source_id is not an admitted public identifier")
        if format_name not in self.allowed_formats:
            raise AuthorityError("declared source format is not admitted")
        try:
            text = data.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise AuthorityError("source is not strict UTF-8") from exc
        _reject_marker_variants(text, stage="raw")
        if format_name == "json":
            for item in _walk_strings(_parse_json(text)):
                _reject_marker_variants(item, stage="decoded_json")
        elif format_name == "jsonl":
            for index, line in enumerate(text.splitlines(), start=1):
                if not line.strip():
                    continue
                for item in _walk_strings(_parse_json(line)):
                    _reject_marker_variants(item, stage=f"decoded_jsonl_line_{index}")


class SourceEvidence:
    """An evidence value that is only useful through its issuing factory."""

    __slots__ = ("_data", "source_id", "format_name", "source_sha256", "policy_version", "_seal")

    def __init__(self, data: bytes, source_id: str, format_name: str, source_sha256: str, policy_version: str, seal: object) -> None:
        self._data = data
        self.source_id = source_id
        self.format_name = format_name
        self.source_sha256 = source_sha256
        self.policy_version = policy_version
        self._seal = seal

    @property
    def byte_length(self) -> int:
        return len(self._data)

    def bytes_slice(self, start: int, end: int) -> bytes:
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start <= end <= len(self._data):
            raise AuthorityError("slice falls outside exact source bytes")
        return self._data[start:end]

    def text_slice(self, start: int, end: int) -> str:
        try:
            return self.bytes_slice(start, end).decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise AuthorityError("slice cuts a UTF-8 code point") from exc

    def identity(self) -> Mapping[str, object]:
        return _freeze(
            {
                "source_id": self.source_id,
                "format": self.format_name,
                "source_sha256": sha256(self._data).hexdigest(),
                "byte_length": len(self._data),
                "policy_version": self.policy_version,
            }
        )


class SourceAdmissionFactory:
    """Issues and revalidates source evidence by identity, not digest alone."""

    def __init__(self, policy: AdmissionPolicy | None = None) -> None:
        self.policy = policy or AdmissionPolicy()
        self._seal = object()
        self._issued: dict[int, SourceEvidence] = {}

    def admit(self, data: bytes, *, source_id: str, format_name: str) -> SourceEvidence:
        copied = bytes(data)
        self.policy.validate(copied, source_id=source_id, format_name=format_name)
        evidence = SourceEvidence(copied, source_id, format_name, sha256(copied).hexdigest(), self.policy.version, self._seal)
        self._issued[id(evidence)] = evidence
        return evidence

    def verify(self, evidence: object) -> bool:
        if not isinstance(evidence, SourceEvidence) or self._issued.get(id(evidence)) is not evidence:
            return False
        try:
            if evidence._seal is not self._seal or evidence.policy_version != self.policy.version:
                return False
            self.policy.validate(evidence._data, source_id=evidence.source_id, format_name=evidence.format_name)
            return sha256(evidence._data).hexdigest() == evidence.source_sha256
        except (AuthorityError, AttributeError):
            return False

    def require(self, evidence: object) -> SourceEvidence:
        if not self.verify(evidence):
            raise AuthorityError("source evidence was not issued and revalidated by this admission factory")
        return evidence


class SpanOwner(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    ATOM_CANDIDATE = "ATOM_CANDIDATE"
    REDACTED = "REDACTED"


@dataclass(frozen=True, slots=True, order=True)
class OwnershipSpan:
    start: int
    end: int
    owner: SpanOwner


@dataclass(frozen=True, slots=True)
class DecodedCharacter:
    value: str
    raw_start: int
    raw_end: int
    is_literal_source: bool


@dataclass(frozen=True, slots=True)
class SemanticSpan:
    span_id: str
    source_sha256: str
    start: int
    end: int
    decoded_text: str
    origin: str


@dataclass(frozen=True, slots=True)
class JsonStringToken:
    quote_start: int
    quote_end: int
    decoded_text: str
    decoded_characters: tuple[DecodedCharacter, ...]
    is_key: bool

    @property
    def has_escape_syntax(self) -> bool:
        return any(not character.is_literal_source for character in self.decoded_characters)


def _utf8_char_end(data: bytes, start: int) -> int:
    lead = data[start]
    if lead < 0x80:
        return start + 1
    if 0xC2 <= lead <= 0xDF:
        return start + 2
    if 0xE0 <= lead <= 0xEF:
        return start + 3
    if 0xF0 <= lead <= 0xF4:
        return start + 4
    raise AuthorityError("JSON literal content has invalid UTF-8")


def _scan_json_string(data: bytes, quote_start: int, *, base: int) -> tuple[JsonStringToken, int]:
    index = quote_start + 1
    decoded_chars: list[DecodedCharacter] = []
    while index < len(data):
        current = data[index]
        if current == 0x22:
            quote_end = index + 1
            raw = data[quote_start:quote_end]
            try:
                decoded = json.loads(raw.decode("utf-8", "strict"))
            except json.JSONDecodeError as exc:
                raise AuthorityError("JSON string token is invalid") from exc
            if not isinstance(decoded, str):
                raise AuthorityError("JSON tokenizer expected a string")
            rendered = "".join(item.value for item in decoded_chars)
            if rendered != decoded:
                raise AuthorityError("raw/decoded JSON string mapping is inconsistent")
            lookahead = quote_end
            while lookahead < len(data) and data[lookahead] in b" \t\r\n":
                lookahead += 1
            return JsonStringToken(base + quote_start, base + quote_end, decoded, tuple(decoded_chars), lookahead < len(data) and data[lookahead] == 0x3A), quote_end
        if current == 0x5C:
            if index + 1 >= len(data):
                raise AuthorityError("JSON escape is truncated")
            escape_end = index + 2
            if data[index + 1] == ord("u"):
                escape_end = index + 6
                if escape_end > len(data) or not re.fullmatch(rb"[0-9A-Fa-f]{4}", data[index + 2:escape_end]):
                    raise AuthorityError("JSON unicode escape is malformed")
            raw_escape = data[index:escape_end]
            try:
                decoded_escape = json.loads(b'"' + raw_escape + b'"')
            except json.JSONDecodeError as exc:
                raise AuthorityError("JSON escape is malformed") from exc
            decoded_chars.extend(
                DecodedCharacter(character, base + index, base + escape_end, False) for character in decoded_escape
            )
            index = escape_end
            continue
        end = _utf8_char_end(data, index)
        try:
            literal = data[index:end].decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise AuthorityError("JSON literal content is invalid UTF-8") from exc
        decoded_chars.append(DecodedCharacter(literal, base + index, base + end, True))
        index = end
    raise AuthorityError("JSON string terminator is missing")


def _json_tokens(data: bytes, *, base: int = 0) -> tuple[JsonStringToken, ...]:
    tokens: list[JsonStringToken] = []
    index = 0
    while index < len(data):
        if data[index] == 0x22:
            token, index = _scan_json_string(data, index, base=base)
            tokens.append(token)
        else:
            index += 1
    return tuple(tokens)


def _line_ranges(data: bytes) -> tuple[tuple[int, int], ...]:
    ranges: list[tuple[int, int]] = []
    start = 0
    for index, value in enumerate(data):
        if value == 0x0A:
            end = index - 1 if index > start and data[index - 1] == 0x0D else index
            ranges.append((start, end))
            start = index + 1
    if start < len(data):
        ranges.append((start, len(data)))
    return tuple(ranges)


def _is_semantic_json_value(token: JsonStringToken) -> bool:
    """Only unescaped JSON value literals can become raw-source evidence."""
    return not token.is_key and not token.has_escape_syntax and token.quote_end - token.quote_start > 2


def _partition(length: int, markers: Sequence[tuple[int, int, SpanOwner]]) -> tuple[OwnershipSpan, ...]:
    result: list[OwnershipSpan] = []
    cursor = 0
    for start, end, owner in sorted(markers, key=lambda item: (item[0], item[1], item[2].value)):
        if not 0 <= cursor <= start < end <= length:
            raise AuthorityError("ownership markers overlap or fall outside source")
        if cursor < start:
            result.append(OwnershipSpan(cursor, start, SpanOwner.STRUCTURAL))
        result.append(OwnershipSpan(start, end, owner))
        cursor = end
    if cursor < length:
        result.append(OwnershipSpan(cursor, length, SpanOwner.STRUCTURAL))
    if not result:
        raise AuthorityError("empty source has no ownership partition")
    return tuple(result)


def _spans_for_source(source: SourceEvidence) -> tuple[tuple[OwnershipSpan, ...], tuple[SemanticSpan, ...]]:
    data = source.bytes_slice(0, source.byte_length)
    markers: list[tuple[int, int, SpanOwner]] = []
    semantic: list[SemanticSpan] = []
    if source.format_name == "json":
        _parse_json(data.decode("utf-8", "strict"))
        tokens = _json_tokens(data)
        for token in tokens:
            # An escaped decoded character is represented by a mapping record,
            # but its raw escape bytes are syntax.  We conservatively do not
            # create an atom candidate for a mixed raw/escaped token.
            if not _is_semantic_json_value(token):
                continue
            start, end = token.quote_start + 1, token.quote_end - 1
            markers.append((start, end, SpanOwner.ATOM_CANDIDATE))
            span_id = "span:" + stable_digest({"source": source.source_sha256, "start": start, "end": end, "decoded": token.decoded_text, "origin": "json_literal_v1"})
            semantic.append(SemanticSpan(span_id, source.source_sha256, start, end, token.decoded_text, "json_literal_v1"))
    elif source.format_name == "jsonl":
        for line_start, line_end in _line_ranges(data):
            line = data[line_start:line_end]
            if not line.strip():
                continue
            _parse_json(line.decode("utf-8", "strict"))
            for token in _json_tokens(line, base=line_start):
                if not _is_semantic_json_value(token):
                    continue
                start, end = token.quote_start + 1, token.quote_end - 1
                markers.append((start, end, SpanOwner.ATOM_CANDIDATE))
                span_id = "span:" + stable_digest({"source": source.source_sha256, "start": start, "end": end, "decoded": token.decoded_text, "origin": "jsonl_literal_v1"})
                semantic.append(SemanticSpan(span_id, source.source_sha256, start, end, token.decoded_text, "jsonl_literal_v1"))
    else:
        for start, end in _line_ranges(data):
            raw = data[start:end]
            if not raw.strip():
                continue
            if raw == b"[REDACTED]":
                markers.append((start, end, SpanOwner.REDACTED))
                continue
            markers.append((start, end, SpanOwner.ATOM_CANDIDATE))
            text = raw.decode("utf-8", "strict")
            span_id = "span:" + stable_digest({"source": source.source_sha256, "start": start, "end": end, "decoded": text, "origin": "line_literal_v1"})
            semantic.append(SemanticSpan(span_id, source.source_sha256, start, end, text, "line_literal_v1"))
    return _partition(source.byte_length, markers), tuple(sorted(semantic, key=lambda item: item.span_id))


@dataclass(frozen=True, slots=True)
class EvidenceLedger:
    source: SourceEvidence
    spans: tuple[OwnershipSpan, ...]
    semantic_spans: tuple[SemanticSpan, ...]
    manifest_sha256: str
    _factory: SourceAdmissionFactory

    def _manifest(self) -> dict[str, object]:
        return {
            "source": _thaw(self.source.identity()),
            "spans": [{"start": span.start, "end": span.end, "owner": span.owner.value} for span in self.spans],
            "semantic_spans": [
                {"span_id": item.span_id, "start": item.start, "end": item.end, "decoded_text": item.decoded_text, "origin": item.origin}
                for item in self.semantic_spans
            ],
        }

    def verify(self) -> bool:
        if not self._factory.verify(self.source):
            return False
        try:
            spans, semantic = _spans_for_source(self.source)
            expected = {
                "source": _thaw(self.source.identity()),
                "spans": [{"start": span.start, "end": span.end, "owner": span.owner.value} for span in spans],
                "semantic_spans": [
                    {"span_id": item.span_id, "start": item.start, "end": item.end, "decoded_text": item.decoded_text, "origin": item.origin}
                    for item in semantic
                ],
            }
            return spans == self.spans and semantic == self.semantic_spans and sha256(canonical_bytes(expected)).hexdigest() == self.manifest_sha256
        except AuthorityError:
            return False

    def semantic(self, span_id: str) -> SemanticSpan:
        if not self.verify():
            raise AuthorityError("ledger is no longer valid")
        for span in self.semantic_spans:
            if span.span_id == span_id:
                return span
        raise AuthorityError("semantic span is not admitted by this ledger")


def build_ledger(factory: SourceAdmissionFactory, source: SourceEvidence) -> EvidenceLedger:
    factory.require(source)
    spans, semantic = _spans_for_source(source)
    manifest = {
        "source": _thaw(source.identity()),
        "spans": [{"start": span.start, "end": span.end, "owner": span.owner.value} for span in spans],
        "semantic_spans": [
            {"span_id": item.span_id, "start": item.start, "end": item.end, "decoded_text": item.decoded_text, "origin": item.origin}
            for item in semantic
        ],
    }
    return EvidenceLedger(source, spans, semantic, sha256(canonical_bytes(manifest)).hexdigest(), factory)


@dataclass(frozen=True, slots=True)
class CanonicalAtom:
    atom_id: str
    span_id: str
    atom_type: str
    source_sha256: str
    text: str
    evidence_sha256: str


class AtomFactory:
    def __init__(self, ledger: EvidenceLedger) -> None:
        if not ledger.verify():
            raise AuthorityError("atom factory requires a verified ledger")
        self._ledger = ledger
        self._issued: dict[str, CanonicalAtom] = {}

    def issue(self, span_id: str, *, atom_type: str = "claim") -> CanonicalAtom:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", atom_type):
            raise AuthorityError("atom type is not admitted")
        span = self._ledger.semantic(span_id)
        raw = self._ledger.source.bytes_slice(span.start, span.end)
        atom = CanonicalAtom(
            "atom:" + stable_digest({"span_id": span.span_id, "atom_type": atom_type}),
            span.span_id,
            atom_type,
            span.source_sha256,
            span.decoded_text,
            sha256(raw).hexdigest(),
        )
        self._issued[atom.atom_id] = atom
        return atom

    def verify(self, atom: object) -> bool:
        if not isinstance(atom, CanonicalAtom) or self._issued.get(atom.atom_id) is not atom or not self._ledger.verify():
            return False
        try:
            span = self._ledger.semantic(atom.span_id)
            raw = self._ledger.source.bytes_slice(span.start, span.end)
            expected = CanonicalAtom(
                "atom:" + stable_digest({"span_id": span.span_id, "atom_type": atom.atom_type}),
                span.span_id, atom.atom_type, span.source_sha256, span.decoded_text, sha256(raw).hexdigest(),
            )
            return atom == expected
        except AuthorityError:
            return False

    def get(self, atom_id: str) -> CanonicalAtom:
        atom = self._issued.get(atom_id)
        if atom is None or not self.verify(atom):
            raise AuthorityError("atom is absent or not factory-issued")
        return atom


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    record_id: str
    purpose: str
    span_id: str
    source_sha256: str
    evidence_sha256: str
    statement: str


class EvidenceRecordFactory:
    """Issues semantic evidence records; structural bytes have no span id."""

    def __init__(self, ledger: EvidenceLedger) -> None:
        if not ledger.verify():
            raise AuthorityError("evidence records require a verified ledger")
        self._ledger = ledger
        self._issued: dict[str, EvidenceRecord] = {}

    def issue(self, span_id: str, *, purpose: str, statement: str) -> EvidenceRecord:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", purpose):
            raise AuthorityError("evidence purpose is not admitted")
        if not isinstance(statement, str) or not statement or len(statement) > 500:
            raise AuthorityError("evidence statement is not admitted")
        span = self._ledger.semantic(span_id)
        raw = self._ledger.source.bytes_slice(span.start, span.end)
        record = EvidenceRecord(
            "evidence:" + stable_digest({"purpose": purpose, "span_id": span_id, "statement": statement}),
            purpose, span_id, span.source_sha256, sha256(raw).hexdigest(), statement,
        )
        self._issued[record.record_id] = record
        return record

    def verify(self, record: object) -> bool:
        if not isinstance(record, EvidenceRecord) or self._issued.get(record.record_id) is not record or not self._ledger.verify():
            return False
        try:
            span = self._ledger.semantic(record.span_id)
            raw = self._ledger.source.bytes_slice(span.start, span.end)
            expected = EvidenceRecord(
                "evidence:" + stable_digest({"purpose": record.purpose, "span_id": record.span_id, "statement": record.statement}),
                record.purpose, record.span_id, span.source_sha256, sha256(raw).hexdigest(), record.statement,
            )
            return record == expected
        except AuthorityError:
            return False


@dataclass(frozen=True, slots=True)
class TypedRelation:
    relation_id: str
    relation_type: str
    source_atom_id: str
    target_atom_id: str
    evidence_record_id: str
    evidence_sha256: str


class RelationFactory:
    def __init__(self, atoms: AtomFactory, evidence: EvidenceRecordFactory) -> None:
        self._atoms = atoms
        self._evidence = evidence
        self._issued: dict[str, TypedRelation] = {}

    def issue(self, source_atom_id: str, target_atom_id: str, *, relation_type: str, evidence: EvidenceRecord) -> TypedRelation:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", relation_type):
            raise AuthorityError("relation type is not admitted")
        source = self._atoms.get(source_atom_id)
        target = self._atoms.get(target_atom_id)
        if not self._evidence.verify(evidence):
            raise AuthorityError("relation requires a verified semantic evidence record")
        relation = TypedRelation(
            "relation:" + stable_digest({"type": relation_type, "source": source.atom_id, "target": target.atom_id, "evidence": evidence.record_id}),
            relation_type, source.atom_id, target.atom_id, evidence.record_id, evidence.evidence_sha256,
        )
        self._issued[relation.relation_id] = relation
        return relation

    def verify(self, relation: object) -> bool:
        if not isinstance(relation, TypedRelation) or self._issued.get(relation.relation_id) is not relation:
            return False
        try:
            source = self._atoms.get(relation.source_atom_id)
            target = self._atoms.get(relation.target_atom_id)
            record = self._evidence._issued.get(relation.evidence_record_id)
            if record is None or not self._evidence.verify(record):
                return False
            expected = TypedRelation(
                "relation:" + stable_digest({"type": relation.relation_type, "source": source.atom_id, "target": target.atom_id, "evidence": record.record_id}),
                relation.relation_type, source.atom_id, target.atom_id, record.record_id, record.evidence_sha256,
            )
            return relation == expected
        except AuthorityError:
            return False


class PacketRecordKind(str, Enum):
    UNKNOWN = "unknown"
    CONFLICT = "conflict"
    REDACTION = "redaction"
    VALIDATION = "validation"


@dataclass(frozen=True, slots=True)
class PacketSubrecord:
    record_id: str
    kind: PacketRecordKind
    evidence_record_id: str
    value: str
    status: str


class PacketSubrecordFactory:
    """Creates typed, evidence-bound packet statements instead of caller maps."""

    def __init__(self, evidence: EvidenceRecordFactory) -> None:
        self._evidence = evidence
        self._issued: dict[str, PacketSubrecord] = {}

    def issue(self, kind: PacketRecordKind, evidence: EvidenceRecord, *, value: str, status: str = "OPEN") -> PacketSubrecord:
        if not isinstance(kind, PacketRecordKind) or not self._evidence.verify(evidence):
            raise AuthorityError("packet subrecord requires a kind and verified evidence")
        if not isinstance(value, str) or not value or len(value) > 500 or _blocked_marker(value):
            raise AuthorityError("packet subrecord value is not public-safe")
        allowed_status = {"OPEN", "CONFIRMED", "REDACTED", "PASS", "FAIL", "UNKNOWN"}
        if status not in allowed_status:
            raise AuthorityError("packet subrecord status is not admitted")
        record = PacketSubrecord(
            "packet-record:" + stable_digest({"kind": kind.value, "evidence": evidence.record_id, "value": value, "status": status}),
            kind, evidence.record_id, value, status,
        )
        self._issued[record.record_id] = record
        return record

    def verify(self, record: object) -> bool:
        if not isinstance(record, PacketSubrecord) or self._issued.get(record.record_id) is not record:
            return False
        evidence = self._evidence._issued.get(record.evidence_record_id)
        if evidence is None or not self._evidence.verify(evidence):
            return False
        try:
            expected = PacketSubrecord(
                "packet-record:" + stable_digest({"kind": record.kind.value, "evidence": evidence.record_id, "value": record.value, "status": record.status}),
                record.kind, evidence.record_id, record.value, record.status,
            )
            return record == expected
        except (AuthorityError, AttributeError):
            return False


@dataclass(frozen=True, slots=True)
class CanonicalPacket:
    packet_id: str
    canonical_json: bytes
    atom_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]
    subrecord_ids: tuple[str, ...]


class PacketFactory:
    def __init__(self, ledger: EvidenceLedger, atoms: AtomFactory, relations: RelationFactory, records: PacketSubrecordFactory) -> None:
        if not ledger.verify():
            raise AuthorityError("packet factory requires a verified ledger")
        self._ledger = ledger
        self._atoms = atoms
        self._relations = relations
        self._records = records
        self._issued: dict[str, tuple[CanonicalPacket, tuple[CanonicalAtom, ...], tuple[TypedRelation, ...], tuple[PacketSubrecord, ...]]] = {}

    def _body(self, atoms: Sequence[CanonicalAtom], relations: Sequence[TypedRelation], records: Sequence[PacketSubrecord]) -> dict[str, object]:
        if not self._ledger.verify() or any(not self._atoms.verify(atom) for atom in atoms):
            raise AuthorityError("packet graph contains an invalid atom or ledger")
        if any(not self._relations.verify(relation) for relation in relations):
            raise AuthorityError("packet graph contains an invalid relation")
        if any(not self._records.verify(record) for record in records):
            raise AuthorityError("packet graph contains an invalid typed subrecord")
        return {
            "schema_version": "e55-packet-v1",
            "source": _thaw(self._ledger.source.identity()),
            "ledger_manifest_sha256": self._ledger.manifest_sha256,
            "atoms": [
                {"atom_id": atom.atom_id, "span_id": atom.span_id, "atom_type": atom.atom_type, "text": atom.text, "evidence_sha256": atom.evidence_sha256}
                for atom in atoms
            ],
            "relations": [
                {"relation_id": relation.relation_id, "relation_type": relation.relation_type, "source_atom_id": relation.source_atom_id, "target_atom_id": relation.target_atom_id, "evidence_record_id": relation.evidence_record_id, "evidence_sha256": relation.evidence_sha256}
                for relation in relations
            ],
            "subrecords": [
                {"record_id": record.record_id, "kind": record.kind.value, "evidence_record_id": record.evidence_record_id, "value": record.value, "status": record.status}
                for record in records
            ],
        }

    def issue(self, *, atoms: Sequence[CanonicalAtom], relations: Sequence[TypedRelation], records: Sequence[PacketSubrecord]) -> CanonicalPacket:
        atom_set = {atom.atom_id for atom in atoms}
        relation_set = {relation.relation_id for relation in relations}
        record_set = {record.record_id for record in records}
        if len(atom_set) != len(atoms) or len(relation_set) != len(relations) or len(record_set) != len(records):
            raise AuthorityError("packet rejects duplicate graph identities")
        ordered_atoms = tuple(sorted(atoms, key=lambda item: item.atom_id))
        ordered_relations = tuple(sorted(relations, key=lambda item: item.relation_id))
        ordered_records = tuple(sorted(records, key=lambda item: item.record_id))
        body = self._body(ordered_atoms, ordered_relations, ordered_records)
        encoded = canonical_bytes(body)
        packet = CanonicalPacket(
            "packet:" + sha256(encoded).hexdigest(), encoded,
            tuple(item.atom_id for item in ordered_atoms), tuple(item.relation_id for item in ordered_relations), tuple(item.record_id for item in ordered_records),
        )
        self._issued[packet.packet_id] = (packet, ordered_atoms, ordered_relations, ordered_records)
        return packet

    def verify(self, packet: object) -> bool:
        if not isinstance(packet, CanonicalPacket):
            return False
        issued = self._issued.get(packet.packet_id)
        if issued is None or issued[0] is not packet:
            return False
        try:
            body = self._body(issued[1], issued[2], issued[3])
            encoded = canonical_bytes(body)
            return (
                packet.canonical_json == encoded
                and packet.packet_id == "packet:" + sha256(encoded).hexdigest()
                and packet.atom_ids == tuple(item.atom_id for item in issued[1])
                and packet.relation_ids == tuple(item.relation_id for item in issued[2])
                and packet.subrecord_ids == tuple(item.record_id for item in issued[3])
            )
        except AuthorityError:
            return False
