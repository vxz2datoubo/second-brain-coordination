"""Typed raw/decoded ownership and execution-derived semantic records."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Iterable, Mapping

from .core import AuthorityError, AuthorityRecord, AuthoritySession, RecordKind, SourceRecord, canonical_bytes, stable_digest


class ValueKind(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    STRING = "STRING"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    NULL = "NULL"
    TEXT = "TEXT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ByteRange:
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise AuthorityError("byte range is invalid")


@dataclass(frozen=True, slots=True)
class DecodedCharacter:
    text: str
    raw: ByteRange
    escaped: bool


@dataclass(frozen=True, slots=True)
class TypedValue:
    kind: ValueKind
    raw: ByteRange
    decoded: str | None
    characters: tuple[DecodedCharacter, ...] = ()


@dataclass(frozen=True, slots=True)
class OwnershipResult:
    source_sha256: str
    format_name: str
    byte_length: int
    values: tuple[TypedValue, ...]
    coverage: tuple[ByteRange, ...]

    @property
    def digest(self) -> str:
        return stable_digest(
            {
                "source_sha256": self.source_sha256,
                "format": self.format_name,
                "byte_length": self.byte_length,
                "values": [
                    {
                        "kind": item.kind.value,
                        "raw": [item.raw.start, item.raw.end],
                        "decoded": item.decoded,
                        "characters": [
                            {"text": char.text, "raw": [char.raw.start, char.raw.end], "escaped": char.escaped}
                            for char in item.characters
                        ],
                    }
                    for item in self.values
                ],
            }
        )

    def assert_complete_partition(self) -> None:
        cursor = 0
        for item in self.coverage:
            if item.start != cursor:
                raise AuthorityError("raw ownership has a gap or overlap")
            cursor = item.end
        if cursor != self.byte_length:
            raise AuthorityError("raw ownership does not cover all bytes")


_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_ESCAPES = {"\\\"": "\"", "\\\\": "\\", "\\/": "/", "\\b": "\b", "\\f": "\f", "\\n": "\n", "\\r": "\r", "\\t": "\t"}


def _offsets(text: str) -> tuple[int, ...]:
    positions = [0]
    for character in text:
        positions.append(positions[-1] + len(character.encode("utf-8")))
    return tuple(positions)


def _json_validate(text: str) -> None:
    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise AuthorityError("duplicate JSON key is unsupported")
            result[key] = value
        return result

    try:
        json.loads(text, object_pairs_hook=reject_duplicate)
    except AuthorityError:
        raise
    except json.JSONDecodeError as exc:
        raise AuthorityError("invalid JSON") from exc


def _string_value(text: str, offsets: tuple[int, ...], start: int) -> tuple[TypedValue, int]:
    index = start + 1
    characters: list[DecodedCharacter] = []
    decoded: list[str] = []
    while index < len(text):
        character = text[index]
        if character == '"':
            end = index + 1
            return TypedValue(ValueKind.STRING, ByteRange(offsets[start], offsets[end]), "".join(decoded), tuple(characters)), end
        if character == "\\":
            if index + 1 >= len(text):
                raise AuthorityError("truncated JSON escape")
            if text[index + 1] == "u":
                if index + 6 > len(text) or not re.fullmatch(r"[0-9a-fA-F]{4}", text[index + 2 : index + 6]):
                    raise AuthorityError("invalid JSON unicode escape")
                codepoint = int(text[index + 2 : index + 6], 16)
                end = index + 6
                if 0xD800 <= codepoint <= 0xDBFF and text[index + 6 : index + 8] == "\\u" and index + 12 <= len(text):
                    low = int(text[index + 8 : index + 12], 16)
                    if 0xDC00 <= low <= 0xDFFF:
                        codepoint = 0x10000 + ((codepoint - 0xD800) << 10) + low - 0xDC00
                        end = index + 12
                value = chr(codepoint)
            else:
                raw_escape = text[index : index + 2]
                if raw_escape not in _ESCAPES:
                    raise AuthorityError("invalid JSON escape")
                value = _ESCAPES[raw_escape]
                end = index + 2
            raw = ByteRange(offsets[index], offsets[end])
            characters.append(DecodedCharacter(value, raw, True))
            decoded.append(value)
            index = end
            continue
        if ord(character) < 0x20:
            raise AuthorityError("unescaped control character in JSON string")
        raw = ByteRange(offsets[index], offsets[index + 1])
        characters.append(DecodedCharacter(character, raw, False))
        decoded.append(character)
        index += 1
    raise AuthorityError("unterminated JSON string")


def parse_json_ownership(data: bytes, *, format_name: str = "json") -> OwnershipResult:
    """Tokenize valid JSON without silently dropping non-string typed values."""

    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise AuthorityError("JSON input is not strict UTF-8") from exc
    _json_validate(text)
    offsets = _offsets(text)
    values: list[TypedValue] = []
    coverage: list[ByteRange] = []
    index = 0
    while index < len(text):
        character = text[index]
        start = index
        if character == '"':
            value, index = _string_value(text, offsets, index)
            values.append(value)
        elif character in "{}[]:," or character.isspace():
            index += 1
            values.append(TypedValue(ValueKind.STRUCTURAL, ByteRange(offsets[start], offsets[index]), None))
        elif text.startswith("true", index) or text.startswith("false", index):
            literal = "true" if text.startswith("true", index) else "false"
            index += len(literal)
            values.append(TypedValue(ValueKind.BOOLEAN, ByteRange(offsets[start], offsets[index]), literal))
        elif text.startswith("null", index):
            index += 4
            values.append(TypedValue(ValueKind.NULL, ByteRange(offsets[start], offsets[index]), None))
        else:
            match = _NUMBER.match(text, index)
            if not match:
                raise AuthorityError("JSON lexical ownership cannot classify token")
            index = match.end()
            values.append(TypedValue(ValueKind.NUMBER, ByteRange(offsets[start], offsets[index]), match.group(0)))
        coverage.append(ByteRange(offsets[start], offsets[index]))
    result = OwnershipResult(sha256(data).hexdigest(), format_name, len(data), tuple(values), tuple(coverage))
    result.assert_complete_partition()
    return result


def parse_jsonl_ownership(data: bytes) -> tuple[OwnershipResult, ...]:
    records: list[OwnershipResult] = []
    offset = 0
    for raw_line in data.splitlines(keepends=True):
        logical = raw_line.rstrip(b"\r\n")
        if logical:
            parsed = parse_json_ownership(logical, format_name="jsonl")
            records.append(parsed)
        offset += len(raw_line)
    if not records:
        raise AuthorityError("JSONL must contain at least one nonempty record")
    return tuple(records)


def parse_markdown_ownership(data: bytes) -> OwnershipResult:
    """Classify supported text and make complex Markdown explicitly UNKNOWN."""

    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise AuthorityError("Markdown input is not strict UTF-8") from exc
    offsets = _offsets(text)
    values: list[TypedValue] = []
    coverage: list[ByteRange] = []
    line_start = 0
    for line in text.splitlines(keepends=True) or [text]:
        line_end = line_start + len(line)
        stripped = line.rstrip("\r\n")
        unknown = any(marker in stripped for marker in ("```", "`", "[", "](", "|", "<", ">"))
        kind = ValueKind.UNKNOWN if unknown else ValueKind.TEXT
        if line_start != line_end:
            values.append(TypedValue(kind, ByteRange(offsets[line_start], offsets[line_end]), stripped or None))
            coverage.append(ByteRange(offsets[line_start], offsets[line_end]))
        line_start = line_end
    if not coverage and data:
        raise AuthorityError("Markdown ownership unexpectedly omitted content")
    result = OwnershipResult(sha256(data).hexdigest(), "markdown", len(data), tuple(values), tuple(coverage))
    if data:
        result.assert_complete_partition()
    return result


@dataclass(frozen=True, slots=True)
class EvaluatorReceipt:
    evaluator_id: str
    rule_id: str
    rule_version: str
    input_digest: str
    run_id: str
    outcome: str

    def verify_shape(self) -> None:
        if not all(isinstance(value, str) and value for value in (self.evaluator_id, self.rule_id, self.rule_version, self.input_digest, self.run_id)):
            raise AuthorityError("evaluator receipt has missing identity fields")
        if self.outcome not in {"PASS", "FAIL"}:
            raise AuthorityError("evaluator receipt outcome is not executable")

    @property
    def digest(self) -> str:
        self.verify_shape()
        return stable_digest(
            {
                "evaluator_id": self.evaluator_id,
                "rule_id": self.rule_id,
                "rule_version": self.rule_version,
                "input_digest": self.input_digest,
                "run_id": self.run_id,
                "outcome": self.outcome,
            }
        )


def issue_evidence(
    session: AuthoritySession,
    source: SourceRecord,
    ownership: OwnershipResult,
    value: TypedValue,
    *,
    endpoint_ids: Iterable[str] = (),
) -> AuthorityRecord:
    session.require(source, RecordKind.SOURCE)
    if source.payload()["source_sha256"] != ownership.source_sha256 or value not in ownership.values:
        raise AuthorityError("evidence must derive from a verified source ownership value")
    endpoints = tuple(sorted(set(endpoint_ids)))
    return session.issue(
        RecordKind.EVIDENCE,
        {
            "source_record_id": source.record_id,
            "source_sha256": ownership.source_sha256,
            "ownership_digest": ownership.digest,
            "value_kind": value.kind.value,
            "raw_range": [value.raw.start, value.raw.end],
            "statement_digest": stable_digest({"source": source.record_id, "kind": value.kind.value, "range": [value.raw.start, value.raw.end], "decoded": value.decoded}),
            "endpoint_ids": list(endpoints),
        },
    )


def issue_atom(session: AuthoritySession, evidence: AuthorityRecord) -> AuthorityRecord:
    session.require(evidence, RecordKind.EVIDENCE)
    return session.issue(RecordKind.ATOM, {"evidence_record_id": evidence.record_id, "evidence_payload_digest": evidence.payload_digest})


def issue_conflict(session: AuthoritySession, left: AuthorityRecord, right: AuthorityRecord) -> AuthorityRecord:
    session.require(left, RecordKind.EVIDENCE)
    session.require(right, RecordKind.EVIDENCE)
    if left.record_id == right.record_id:
        raise AuthorityError("conflict needs two distinct evidence records")
    left_payload, right_payload = left.payload(), right.payload()
    if left_payload["source_record_id"] == right_payload["source_record_id"]:
        raise AuthorityError("conflict needs independently sourced evidence")
    return session.issue(
        RecordKind.PACKET,
        {
            "packet_type": "CONFLICT",
            "left_evidence_id": left.record_id,
            "right_evidence_id": right.record_id,
            "left_source_record_id": left_payload["source_record_id"],
            "right_source_record_id": right_payload["source_record_id"],
            "state": "UNRESOLVED",
        },
    )


def issue_validation(session: AuthoritySession, evidence: AuthorityRecord, receipt: EvaluatorReceipt) -> AuthorityRecord:
    session.require(evidence, RecordKind.EVIDENCE)
    receipt.verify_shape()
    if receipt.input_digest != evidence.payload_digest:
        raise AuthorityError("validation receipt does not bind the evaluated evidence payload")
    return session.issue(
        RecordKind.PACKET,
        {
            "packet_type": "VALIDATION",
            "evidence_record_id": evidence.record_id,
            "evaluator_id": receipt.evaluator_id,
            "rule_id": receipt.rule_id,
            "rule_version": receipt.rule_version,
            "input_digest": receipt.input_digest,
            "run_id": receipt.run_id,
            "outcome": receipt.outcome,
            "receipt_digest": receipt.digest,
        },
    )


def issue_redaction(session: AuthoritySession, source: SourceRecord, raw: ByteRange, *, reason_policy_id: str) -> AuthorityRecord:
    session.require(source, RecordKind.SOURCE)
    if not reason_policy_id or raw.end > int(source.payload()["byte_length"]):
        raise AuthorityError("redaction requires an exact in-source range and policy")
    return session.issue(
        RecordKind.PACKET,
        {
            "packet_type": "REDACTION",
            "source_record_id": source.record_id,
            "source_sha256": source.payload()["source_sha256"],
            "raw_range": [raw.start, raw.end],
            "reason_policy_id": reason_policy_id,
        },
    )


def issue_relation(session: AuthoritySession, left: AuthorityRecord, right: AuthorityRecord, evidence: AuthorityRecord, *, relation_type: str) -> AuthorityRecord:
    session.require(left, RecordKind.ATOM)
    session.require(right, RecordKind.ATOM)
    session.require(evidence, RecordKind.EVIDENCE)
    if not relation_type or left.record_id == right.record_id:
        raise AuthorityError("relation needs distinct verified endpoints and a type")
    endpoint_ids = tuple(evidence.payload()["endpoint_ids"])
    if tuple(sorted((left.record_id, right.record_id))) != endpoint_ids:
        raise AuthorityError("relation evidence does not bind both endpoint identities")
    return session.issue(
        RecordKind.RELATION,
        {
            "relation_type": relation_type,
            "left_atom_id": left.record_id,
            "right_atom_id": right.record_id,
            "evidence_record_id": evidence.record_id,
            "evidence_ownership_digest": evidence.payload()["ownership_digest"],
        },
    )
