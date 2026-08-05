"""Six bounded E52 adapters that finalize a complete original-byte ledger."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from .index import ByteTruthIndex, LineRecord
from .ledger import FinalizedLedger, LedgerBuilder, Owner, OwnershipSpan


SUPPORTED_FORMATS = {
    "txt",
    "markdown",
    "json",
    "jsonl",
    "conversation_structured",
    "conversation_plain",
}


@dataclass(frozen=True, slots=True)
class AdapterResult:
    format_name: str
    index: ByteTruthIndex
    ledger: FinalizedLedger


def _finalize(total: int, segments: Iterable[tuple[int, int, Owner, str]]) -> FinalizedLedger:
    builder = LedgerBuilder(total)
    for start, end, owner, label in segments:
        if start != end:
            builder.add(start, end, owner, label)
    return builder.finalize()


def _line_segments(index: ByteTruthIndex, content_owner: Owner, content_label: str) -> list[tuple[int, int, Owner, str]]:
    segments: list[tuple[int, int, Owner, str]] = []
    for record in index.line_records():
        if record.has_trailing_empty_line:
            continue
        if record.content_end > record.content_start:
            segments.append((record.content_start, record.content_end, content_owner, content_label))
        if record.terminator_start is not None and record.terminator_end is not None:
            segments.append((record.terminator_start, record.terminator_end, Owner.STRUCTURE, "line_terminator"))
    return segments


def _json_tokens(source: bytes, offset: int = 0) -> list[tuple[int, int, Owner, str]]:
    """Lex JSON bytes only after stdlib grammar validation has accepted them."""
    tokens: list[tuple[int, int, Owner, str]] = []
    i = 0
    total = len(source)
    while i < total:
        byte = source[i]
        start = i
        if byte in b" \t\r\n":
            while i < total and source[i] in b" \t\r\n":
                i += 1
            tokens.append((offset + start, offset + i, Owner.STRUCTURE, "json_whitespace"))
        elif byte in b"{}[]:,":
            i += 1
            tokens.append((offset + start, offset + i, Owner.STRUCTURE, "json_punctuation"))
        elif byte == 0x22:
            i += 1
            while i < total:
                if source[i] == 0x5C:
                    i += 2
                    continue
                if source[i] == 0x22:
                    i += 1
                    break
                i += 1
            tokens.append((offset + start, offset + i, Owner.ATOM_CANDIDATE, "json_string"))
        else:
            while i < total and source[i] not in b" \t\r\n{}[]:,":
                i += 1
            label = "json_literal" if source[start:i] in (b"true", b"false", b"null") else "json_number"
            tokens.append((offset + start, offset + i, Owner.ATOM_CANDIDATE, label))
    return tokens


def _strict_json_segments(source: bytes, offset: int = 0) -> list[tuple[int, int, Owner, str]]:
    try:
        json.loads(source.decode("utf-8"), object_pairs_hook=list)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [(offset, offset + len(source), Owner.UNKNOWN_ERROR, "json_invalid_or_trailing")]
    return _json_tokens(source, offset)


def _jsonl_segments(index: ByteTruthIndex) -> list[tuple[int, int, Owner, str]]:
    source = index.source_bytes
    segments: list[tuple[int, int, Owner, str]] = []
    for record in index.line_records():
        if record.has_trailing_empty_line:
            continue
        if record.content_end > record.content_start:
            line = source[record.content_start:record.content_end]
            segments.extend(_strict_json_segments(line, record.content_start))
        if record.terminator_start is not None and record.terminator_end is not None:
            segments.append((record.terminator_start, record.terminator_end, Owner.STRUCTURE, "jsonl_terminator"))
    return segments


def _conversation_segments(index: ByteTruthIndex, structured: bool) -> list[tuple[int, int, Owner, str]]:
    source = index.source_bytes
    segments: list[tuple[int, int, Owner, str]] = []
    recognized_roles = {b"user", b"assistant", b"system", b"tool", b"human", b"ai"}
    for record in index.line_records():
        if record.has_trailing_empty_line:
            continue
        start, end = record.content_start, record.content_end
        if start < end and structured:
            cursor = start
            while cursor < end and source[cursor] in b" \t":
                cursor += 1
            if cursor > start:
                segments.append((start, cursor, Owner.STRUCTURE, "conversation_leading_space"))
            colon = source.find(b":", cursor, end)
            role = source[cursor:colon].strip().lower() if colon != -1 else b""
            if colon != -1 and role in recognized_roles:
                role_end = cursor + len(source[cursor:colon].rstrip())
                if role_end > cursor:
                    segments.append((cursor, role_end, Owner.STRUCTURE, "conversation_role"))
                if role_end < colon:
                    segments.append((role_end, colon, Owner.STRUCTURE, "conversation_role_space"))
                segments.append((colon, colon + 1, Owner.STRUCTURE, "conversation_colon"))
                body_start = colon + 1
                while body_start < end and source[body_start] in b" \t":
                    body_start += 1
                if body_start > colon + 1:
                    segments.append((colon + 1, body_start, Owner.STRUCTURE, "conversation_separator_space"))
                if body_start < end and source[body_start:body_start + 1] == b"[":
                    close = source.find(b"]", body_start + 1, end)
                    if close != -1:
                        segments.append((body_start, close + 1, Owner.STRUCTURE, "conversation_metadata"))
                        metadata_end = close + 1
                        body_start = metadata_end
                        while body_start < end and source[body_start] in b" \t":
                            body_start += 1
                        if body_start > metadata_end:
                            segments.append((metadata_end, body_start, Owner.STRUCTURE, "conversation_metadata_space"))
                if body_start < end:
                    segments.append((body_start, end, Owner.ATOM_CANDIDATE, "conversation_body"))
            elif cursor < end:
                segments.append((cursor, end, Owner.ATOM_CANDIDATE, "conversation_body"))
        elif start < end:
            segments.append((start, end, Owner.ATOM_CANDIDATE, "conversation_body"))
        if record.terminator_start is not None and record.terminator_end is not None:
            segments.append((record.terminator_start, record.terminator_end, Owner.STRUCTURE, "conversation_terminator"))
    return segments


def adapt(source: bytes, format_name: str) -> AdapterResult:
    if format_name not in SUPPORTED_FORMATS:
        raise ValueError(f"unsupported format: {format_name}")
    index = ByteTruthIndex(source)
    if not source:
        return AdapterResult(format_name, index, _finalize(0, ()))
    if format_name == "json":
        segments = _strict_json_segments(source)
    elif format_name == "jsonl":
        segments = _jsonl_segments(index)
    elif format_name == "conversation_structured":
        segments = _conversation_segments(index, structured=True)
    elif format_name == "conversation_plain":
        segments = _conversation_segments(index, structured=False)
    else:
        segments = _line_segments(index, Owner.ATOM_CANDIDATE, f"{format_name}_content")
    return AdapterResult(format_name, index, _finalize(index.total_bytes, segments))
