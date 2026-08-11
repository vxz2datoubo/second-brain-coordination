"""Six bounded E52 adapters that finalize a complete original-byte ledger."""
from __future__ import annotations

import json
import re
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


def _txt_segments(index: ByteTruthIndex) -> list[tuple[int, int, Owner, str]]:
    segments: list[tuple[int, int, Owner, str]] = []
    for record in index.line_records():
        if record.has_trailing_empty_line:
            continue
        if not record.is_blank and record.content_end > record.content_start:
            segments.append((record.content_start, record.content_end, Owner.ATOM_CANDIDATE, "txt_content"))
        if record.terminator_start is not None and record.terminator_end is not None:
            label = "txt_blank_separator" if record.is_blank else "txt_terminator"
            segments.append((record.terminator_start, record.terminator_end, Owner.STRUCTURE, label))
    return segments


def _markdown_segments(index: ByteTruthIndex) -> list[tuple[int, int, Owner, str]]:
    source = index.source_bytes
    segments: list[tuple[int, int, Owner, str]] = []
    in_fence = False
    list_pattern = re.compile(rb"(?:[-+*][ \t]+|[0-9]+[.)][ \t]+)")
    table_separator = re.compile(rb"[ \t|:\-]+$")
    for record in index.line_records():
        if record.has_trailing_empty_line:
            continue
        start, end = record.content_start, record.content_end
        raw = source[start:end]
        if not record.is_blank:
            indent = len(raw) - len(raw.lstrip(b" \t"))
            body = raw[indent:]
            body_start = start + indent
            fence = body.startswith((b"```", b"~~~"))
            if fence:
                segments.append((start, end, Owner.STRUCTURE, "markdown_code_fence"))
                in_fence = not in_fence
            elif in_fence:
                segments.append((start, end, Owner.STRUCTURE, "markdown_code_body"))
            elif body.startswith(b"#"):
                marker_end = body_start
                while marker_end < end and source[marker_end:marker_end + 1] == b"#":
                    marker_end += 1
                if marker_end < end and source[marker_end:marker_end + 1] in (b" ", b"\t"):
                    while marker_end < end and source[marker_end:marker_end + 1] in (b" ", b"\t"):
                        marker_end += 1
                segments.append((start, marker_end, Owner.STRUCTURE, "markdown_heading_marker"))
                if marker_end < end:
                    segments.append((marker_end, end, Owner.ATOM_CANDIDATE, "markdown_heading_text"))
            elif body.startswith(b">"):
                marker_end = body_start + 1
                while marker_end < end and source[marker_end:marker_end + 1] in (b" ", b"\t"):
                    marker_end += 1
                segments.append((start, marker_end, Owner.STRUCTURE, "markdown_blockquote_marker"))
                if marker_end < end:
                    segments.append((marker_end, end, Owner.ATOM_CANDIDATE, "markdown_blockquote_body"))
            elif (match := list_pattern.match(body)) is not None:
                marker_end = body_start + match.end()
                segments.append((start, marker_end, Owner.STRUCTURE, "markdown_list_marker"))
                if marker_end < end:
                    segments.append((marker_end, end, Owner.ATOM_CANDIDATE, "markdown_list_body"))
            elif b"|" in body:
                if table_separator.fullmatch(body) is not None:
                    segments.append((start, end, Owner.STRUCTURE, "markdown_table_separator"))
                else:
                    cursor = start
                    while cursor < end:
                        pipe = source.find(b"|", cursor, end)
                        if pipe == -1:
                            if cursor < end:
                                segments.append((cursor, end, Owner.ATOM_CANDIDATE, "markdown_table_cell"))
                            break
                        if cursor < pipe:
                            segments.append((cursor, pipe, Owner.ATOM_CANDIDATE, "markdown_table_cell"))
                        segments.append((pipe, pipe + 1, Owner.STRUCTURE, "markdown_table_pipe"))
                        cursor = pipe + 1
            else:
                segments.append((start, end, Owner.ATOM_CANDIDATE, "markdown_text"))
        if record.terminator_start is not None and record.terminator_end is not None:
            label = "markdown_blank_separator" if record.is_blank else "markdown_terminator"
            segments.append((record.terminator_start, record.terminator_end, Owner.STRUCTURE, label))
    return segments


def _json_string_segments(source: bytes, start: int, offset: int, is_key: bool) -> tuple[int, list[tuple[int, int, Owner, str]]]:
    role = "json_key" if is_key else "json_value"
    content_owner = Owner.STRUCTURE if is_key else Owner.ATOM_CANDIDATE
    segments = [(offset + start, offset + start + 1, Owner.STRUCTURE, f"{role}_quote")]
    cursor = start + 1
    content_start = cursor
    while cursor < len(source):
        if source[cursor] == 0x5C:
            if content_start < cursor:
                segments.append((offset + content_start, offset + cursor, content_owner, f"{role}_body" if is_key else "json_value_string_content"))
            if cursor + 1 >= len(source):
                raise ValueError("unterminated JSON escape")
            segments.append((offset + cursor, offset + cursor + 2, Owner.STRUCTURE, f"{role}_escape"))
            cursor += 2
            content_start = cursor
            continue
        if source[cursor] == 0x22:
            if content_start < cursor:
                segments.append((offset + content_start, offset + cursor, content_owner, f"{role}_body" if is_key else "json_value_string_content"))
            segments.append((offset + cursor, offset + cursor + 1, Owner.STRUCTURE, f"{role}_quote"))
            return cursor + 1, segments
        cursor += 1
    raise ValueError("unterminated JSON string")


def _json_tokens(source: bytes, offset: int = 0) -> list[tuple[int, int, Owner, str]]:
    """Lex JSON roles after grammar validation without promoting object keys."""
    tokens: list[tuple[int, int, Owner, str]] = []
    i = 0
    total = len(source)
    stack: list[list[str]] = []

    def consume_value() -> None:
        if not stack:
            return
        kind, state = stack[-1]
        if kind == "object" and state == "value":
            stack[-1][1] = "comma_or_end"
        elif kind == "array" and state == "value_or_end":
            stack[-1][1] = "comma_or_end"
        else:
            raise ValueError("JSON value appears in an invalid grammar state")

    while i < total:
        byte = source[i]
        start = i
        if byte in b" \t\r\n":
            while i < total and source[i] in b" \t\r\n":
                i += 1
            tokens.append((offset + start, offset + i, Owner.STRUCTURE, "json_whitespace"))
        elif byte == 0x7B:  # {
            consume_value()
            i += 1
            tokens.append((offset + start, offset + i, Owner.STRUCTURE, "json_object_open"))
            stack.append(["object", "key_or_end"])
        elif byte == 0x5B:  # [
            consume_value()
            i += 1
            tokens.append((offset + start, offset + i, Owner.STRUCTURE, "json_array_open"))
            stack.append(["array", "value_or_end"])
        elif byte in (0x7D, 0x5D):  # } ]
            if not stack:
                raise ValueError("JSON closes an absent container")
            kind, state = stack[-1]
            expected = "object" if byte == 0x7D else "array"
            if kind != expected or state not in ({"key_or_end", "comma_or_end"} if kind == "object" else {"value_or_end", "comma_or_end"}):
                raise ValueError("JSON closes a container in an invalid state")
            stack.pop()
            i += 1
            tokens.append((offset + start, offset + i, Owner.STRUCTURE, "json_object_close" if byte == 0x7D else "json_array_close"))
        elif byte == 0x3A:  # :
            if not stack or stack[-1] != ["object", "colon"]:
                raise ValueError("JSON colon appears outside object-key context")
            stack[-1][1] = "value"
            i += 1
            tokens.append((offset + start, offset + i, Owner.STRUCTURE, "json_key_value_separator"))
        elif byte == 0x2C:  # ,
            if not stack or stack[-1][1] != "comma_or_end":
                raise ValueError("JSON comma appears outside value context")
            stack[-1][1] = "key_or_end" if stack[-1][0] == "object" else "value_or_end"
            i += 1
            tokens.append((offset + start, offset + i, Owner.STRUCTURE, "json_item_separator"))
        elif byte == 0x22:
            is_key = bool(stack and stack[-1] == ["object", "key_or_end"])
            i, string_segments = _json_string_segments(source, start, offset, is_key)
            tokens.extend(string_segments)
            if is_key:
                stack[-1][1] = "colon"
            else:
                consume_value()
        else:
            while i < total and source[i] not in b" \t\r\n{}[]:,":
                i += 1
            label = "json_literal" if source[start:i] in (b"true", b"false", b"null") else "json_number"
            consume_value()
            tokens.append((offset + start, offset + i, Owner.ATOM_CANDIDATE, f"json_value_{label}"))
    if stack:
        raise ValueError("JSON lexical state did not close")
    return tokens


def _strict_json_segments(source: bytes, offset: int = 0) -> list[tuple[int, int, Owner, str]]:
    try:
        json.loads(source.decode("utf-8"), object_pairs_hook=list)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [(offset, offset + len(source), Owner.UNKNOWN_ERROR, "json_invalid_or_trailing")]
    try:
        return _json_tokens(source, offset)
    except ValueError:
        return [(offset, offset + len(source), Owner.UNKNOWN_ERROR, "json_role_parse_failure")]


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
    elif format_name == "txt":
        segments = _txt_segments(index)
    else:
        segments = _markdown_segments(index)
    return AdapterResult(format_name, index, _finalize(index.total_bytes, segments))
