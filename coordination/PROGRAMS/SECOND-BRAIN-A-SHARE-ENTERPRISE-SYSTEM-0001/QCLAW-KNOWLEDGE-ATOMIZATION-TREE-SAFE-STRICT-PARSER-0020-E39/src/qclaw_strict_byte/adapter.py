"""E39 S2 — Byte-position adapters for 6 formats.

Formats: markdown, txt, json, jsonl, conversation_structured, conversation_plain.
All adapters operate on raw bytes and produce SpanRole tuples with byte
spans — no str.find(), no regex char-index, no len(str) for byte spans.

JSON adapter is a full byte-level tokenizer that preserves duplicates,
escapes, whitespace, punctuation, and ordering. No json.loads() used
for positioning.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import json

from .utf8_guard import UTF8ByteIndex
from .ledger import OWNER_ATOM_CANDIDATE, OWNER_STRUCTURE, OWNER_UNKNOWN_ERROR


# ═══════════════════════════════════════════════════════════════════════
# SpanRole
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SpanRole:
    byte_start: int
    byte_end: int          # exclusive
    role: str
    owner: str = OWNER_ATOM_CANDIDATE
    label: str = ""

    @property
    def byte_length(self) -> int:
        return self.byte_end - self.byte_start

    @property
    def text(self) -> str:
        """Note: callers must supply source_bytes."""
        raise NotImplementedError("text property requires source_bytes — use .extract()")


def extract_text(source: bytes, span: SpanRole) -> str:
    return source[span.byte_start:span.byte_end].decode("utf-8", "replace")


# ═══════════════════════════════════════════════════════════════════════
# Roles
# ═══════════════════════════════════════════════════════════════════════

ROLE_HEADER = "header"
ROLE_CONTENT = "content"
ROLE_BLANK_LINE = "blank_line"
ROLE_LIST_ITEM = "list_item"
ROLE_CODE_BLOCK = "code_block"
ROLE_TABLE = "table"
ROLE_JSON_KEY = "json_key"
ROLE_JSON_VALUE = "json_value"
ROLE_JSON_STRING = "json_string"
ROLE_JSON_NUMBER = "json_number"
ROLE_JSON_BOOL = "json_bool"
ROLE_JSON_NULL = "json_null"
ROLE_JSON_ARRAY_START = "json_array_start"
ROLE_JSON_ARRAY_END = "json_array_end"
ROLE_JSON_OBJECT_START = "json_object_start"
ROLE_JSON_OBJECT_END = "json_object_end"
ROLE_JSON_COMMA = "json_comma"
ROLE_JSON_COLON = "json_colon"
ROLE_JSON_STRUCTURE = "json_structure"
ROLE_CONVERSATION_ROLE = "conversation_role"
ROLE_CONVERSATION_CONTENT = "conversation_content"
ROLE_CONVERSATION_TIMESTAMP = "conversation_timestamp"
ROLE_CONVERSATION_METADATA = "conversation_metadata"
ROLE_STRUCTURE = "structure"
ROLE_UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════════════
# TXT adapter
# ═══════════════════════════════════════════════════════════════════════

def adapt_txt(index: UTF8ByteIndex) -> List[SpanRole]:
    """Treat entire text as content, line terminators inclusive."""
    b = index.source_bytes
    total = index.total_bytes
    if total == 0:
        return []
    spans: List[SpanRole] = []
    pos = 0
    line_start = 0
    while pos < total:
        if pos + 1 < total and b[pos] == 0x0D and b[pos + 1] == 0x0A:
            # Include CRLF in span
            is_blank = (pos == line_start)
            spans.append(SpanRole(line_start, pos + 2,
                                  ROLE_BLANK_LINE if is_blank else ROLE_CONTENT,
                                  OWNER_STRUCTURE if is_blank else OWNER_ATOM_CANDIDATE))
            pos += 2
            line_start = pos
        elif b[pos] == 0x0A:
            is_blank = (pos == line_start)
            spans.append(SpanRole(line_start, pos + 1,
                                  ROLE_BLANK_LINE if is_blank else ROLE_CONTENT,
                                  OWNER_STRUCTURE if is_blank else OWNER_ATOM_CANDIDATE))
            pos += 1
            line_start = pos
        else:
            pos += 1
    if line_start < total:
        spans.append(SpanRole(line_start, total, ROLE_CONTENT))
    return spans


# ═══════════════════════════════════════════════════════════════════════
# Markdown adapter
# ═══════════════════════════════════════════════════════════════════════

def adapt_markdown(index: UTF8ByteIndex) -> List[SpanRole]:
    """Parse markdown at byte level: headers, code blocks, tables, lists, content."""
    b = index.source_bytes
    total = index.total_bytes
    chunks = index.chunk_starts
    lines = _split_lines_byte(index)

    spans: List[SpanRole] = []
    in_code_block = False
    code_fence = b""
    i_line = 0

    while i_line < len(lines):
        line_start, line_end = lines[i_line]
        line_bytes = b[line_start:line_end]
        stripped = line_bytes.lstrip(b" ")

        # Skip trailing whitespace for classification
        if not stripped:
            spans.append(SpanRole(line_start, line_end, ROLE_BLANK_LINE, OWNER_STRUCTURE))
            i_line += 1
            continue

        # Code block fence detection
        if stripped.startswith(b"```"):
            code_fence = stripped.split(b" ")[0] if b" " in stripped else stripped
            if not in_code_block:
                # Opening fence
                spans.append(SpanRole(line_start, line_end, ROLE_STRUCTURE,
                                      OWNER_STRUCTURE, "code_fence_open"))
                in_code_block = True
                # Collect code block content
                code_start = i_line + 1
                i_line += 1
                while i_line < len(lines):
                    cl_start, cl_end = lines[i_line]
                    cl_bytes = b[cl_start:cl_end]
                    cl_stripped = cl_bytes.lstrip(b" ")
                    if cl_stripped.startswith(b"```"):
                        # Closing fence — emit accumulated code
                        if code_start < i_line:
                            cs = lines[code_start][0]
                            ce = lines[i_line - 1][1]
                            spans.append(SpanRole(cs, ce, ROLE_CODE_BLOCK, OWNER_ATOM_CANDIDATE))
                        spans.append(SpanRole(cl_start, cl_end, ROLE_STRUCTURE,
                                              OWNER_STRUCTURE, "code_fence_close"))
                        in_code_block = False
                        i_line += 1
                        break
                    i_line += 1
                if in_code_block:
                    # Unclosed — emit rest as code block
                    cs = lines[code_start][0] if code_start < len(lines) else lines[-1][1]
                    ce = lines[-1][1] if code_start < len(lines) else total
                    spans.append(SpanRole(cs, ce, ROLE_CODE_BLOCK, OWNER_ATOM_CANDIDATE,
                                          "unclosed"))
                continue
            else:
                # Closing fence
                spans.append(SpanRole(line_start, line_end, ROLE_STRUCTURE,
                                      OWNER_STRUCTURE, "code_fence_close"))
                in_code_block = False
                i_line += 1
                continue

        if in_code_block:
            i_line += 1
            continue

        # Header detection
        hash_count = 0
        j = 0
        while j < len(stripped) and stripped[j] == 0x23:  # #
            hash_count += 1
            j += 1
        if hash_count >= 1 and hash_count <= 6 and (j >= len(stripped) or stripped[j] == 0x20):
            spans.append(SpanRole(line_start, line_end, ROLE_HEADER,
                                  OWNER_ATOM_CANDIDATE, f"h{hash_count}"))
            i_line += 1
            continue

        # Table detection (starts with |)
        if stripped.startswith(b"|"):
            table_lines: List[Tuple[int, int]] = []
            while i_line < len(lines):
                tl_start, tl_end = lines[i_line]
                tl = b[tl_start:tl_end].lstrip(b" ")
                if tl.startswith(b"|"):
                    table_lines.append((tl_start, tl_end))
                    i_line += 1
                else:
                    break
            if table_lines:
                ts = table_lines[0][0]
                te = table_lines[-1][1]
                spans.append(SpanRole(ts, te, ROLE_TABLE, OWNER_ATOM_CANDIDATE,
                                      f"{len(table_lines)}rows"))
            continue

        # List item detection
        is_list = False
        if (stripped.startswith(b"- ") or stripped.startswith(b"* ") or
            stripped.startswith(b"+ ")):
            is_list = True
        elif len(stripped) >= 3 and stripped[0] in range(0x30, 0x3A):
            # Numbered list: "1. "
            dot_pos = -1
            for k, ch in enumerate(stripped):
                if ch == 0x2E:  # .
                    dot_pos = k
                    break
            if dot_pos > 0 and dot_pos < len(stripped) - 1 and stripped[dot_pos + 1] == 0x20:
                is_list = True

        if is_list:
            spans.append(SpanRole(line_start, line_end, ROLE_LIST_ITEM))
            i_line += 1
            continue

        # Default: content
        spans.append(SpanRole(line_start, line_end, ROLE_CONTENT))
        i_line += 1

    return spans


def _split_lines_byte(index: UTF8ByteIndex) -> List[Tuple[int, int]]:
    """Split source into line ranges (byte_start, byte_end) including terminators."""
    b = index.source_bytes
    total = index.total_bytes
    lines: List[Tuple[int, int]] = []
    pos = 0
    line_start = 0
    while pos < total:
        if pos + 1 < total and b[pos] == 0x0D and b[pos + 1] == 0x0A:
            lines.append((line_start, pos + 2))  # include CRLF
            pos += 2
            line_start = pos
        elif b[pos] == 0x0A:
            lines.append((line_start, pos + 1))  # include LF
            pos += 1
            line_start = pos
        else:
            pos += 1
    if line_start < total:
        lines.append((line_start, total))
    return lines


# ═══════════════════════════════════════════════════════════════════════
# JSON byte-level tokenizer
# ═══════════════════════════════════════════════════════════════════════

def adapt_json(index: UTF8ByteIndex) -> List[SpanRole]:
    """Tokenize JSON at byte level.

    Preserves: duplicate keys, all whitespace, escape sequences, punctuation,
    array/object boundaries, number formats, booleans, nulls, ordering.

    Does NOT use json.loads() for positioning.
    """
    spans, _ = _json_tokenize(index.source_bytes)
    # Validate structure only
    try:
        json.loads(index.source_bytes.decode("utf-8", "strict"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass  # Tokenization proceeds even for invalid JSON
    return spans


def _json_tokenize(data: bytes, pos: int = 0, depth: int = 0) -> Tuple[List[SpanRole], int]:
    """Recursive byte-level JSON tokenizer. Returns (spans, new_pos)."""
    spans: List[SpanRole] = []
    total = len(data)

    # Skip whitespace
    while pos < total and data[pos] in (0x20, 0x09, 0x0A, 0x0D):
        pos += 1

    if pos >= total:
        return spans, pos

    ch = data[pos]

    if ch == 0x7B:  # {
        spans.append(SpanRole(pos, pos + 1, ROLE_JSON_OBJECT_START, OWNER_STRUCTURE))
        pos += 1
        first = True
        while pos < total:
            while pos < total and data[pos] in (0x20, 0x09, 0x0A, 0x0D):
                pos += 1
            if pos >= total:
                break
            if data[pos] == 0x7D:  # }
                break
            if not first:
                if data[pos] == 0x2C:  # ,
                    spans.append(SpanRole(pos, pos + 1, ROLE_JSON_COMMA, OWNER_STRUCTURE))
                    pos += 1
                else:
                    break
            first = False

            # Key
            while pos < total and data[pos] in (0x20, 0x09, 0x0A, 0x0D):
                pos += 1
            key_spans, pos = _json_parse_string(data, pos)
            if key_spans:
                # Mark the first string span as key
                for ks in key_spans:
                    if ks.role == ROLE_JSON_STRING:
                        spans.append(SpanRole(ks.byte_start, ks.byte_end,
                                              ROLE_JSON_KEY, OWNER_STRUCTURE))
                    else:
                        spans.append(ks)
            else:
                # Malformed — consume the token
                while pos < total and data[pos] not in (0x3A, 0x2C, 0x7D, 0x7B, 0x5B):
                    pos += 1

            # Colon
            while pos < total and data[pos] in (0x20, 0x09, 0x0A, 0x0D):
                pos += 1
            if pos < total and data[pos] == 0x3A:  # :
                spans.append(SpanRole(pos, pos + 1, ROLE_JSON_COLON, OWNER_STRUCTURE))
                pos += 1

            # Value
            while pos < total and data[pos] in (0x20, 0x09, 0x0A, 0x0D):
                pos += 1
            if pos < total:
                val_spans, pos = _json_parse_value(data, pos, depth + 1)
                spans.extend(val_spans)

        if pos < total and data[pos] == 0x7D:  # }
            spans.append(SpanRole(pos, pos + 1, ROLE_JSON_OBJECT_END, OWNER_STRUCTURE))
            pos += 1
        return spans, pos

    elif ch == 0x5B:  # [
        spans.append(SpanRole(pos, pos + 1, ROLE_JSON_ARRAY_START, OWNER_STRUCTURE))
        pos += 1
        first = True
        while pos < total:
            while pos < total and data[pos] in (0x20, 0x09, 0x0A, 0x0D):
                pos += 1
            if pos >= total or data[pos] == 0x5D:  # ]
                break
            if not first:
                if data[pos] == 0x2C:  # ,
                    spans.append(SpanRole(pos, pos + 1, ROLE_JSON_COMMA, OWNER_STRUCTURE))
                    pos += 1
                else:
                    break
            first = False
            val_spans, pos = _json_parse_value(data, pos, depth + 1)
            spans.extend(val_spans)
        if pos < total and data[pos] == 0x5D:  # ]
            spans.append(SpanRole(pos, pos + 1, ROLE_JSON_ARRAY_END, OWNER_STRUCTURE))
            pos += 1
        return spans, pos

    else:
        # Root-level primitive
        val_spans, pos = _json_parse_value(data, pos, depth)
        spans.extend(val_spans)
        return spans, pos


def _json_parse_value(data: bytes, pos: int, depth: int = 0) -> Tuple[List[SpanRole], int]:
    """Parse a single JSON value at byte position."""
    total = len(data)
    spans: List[SpanRole] = []

    while pos < total and data[pos] in (0x20, 0x09, 0x0A, 0x0D):
        pos += 1
    if pos >= total:
        return spans, pos

    ch = data[pos]

    if ch == 0x22:  # "string
        return _json_parse_string(data, pos)

    elif ch == 0x7B:  # {object
        return _json_tokenize(data, pos, depth)

    elif ch == 0x5B:  # [array
        return _json_tokenize(data, pos, depth)

    elif ch in (0x2D,) or (0x30 <= ch <= 0x39):  # - or digit → number
        start = pos
        if data[pos] == 0x2D:  # -
            pos += 1
        while pos < total and 0x30 <= data[pos] <= 0x39:
            pos += 1
        if pos < total and data[pos] == 0x2E:  # .
            pos += 1
            while pos < total and 0x30 <= data[pos] <= 0x39:
                pos += 1
        if pos < total and data[pos] in (0x65, 0x45):  # e/E
            pos += 1
            if pos < total and data[pos] in (0x2B, 0x2D):
                pos += 1
            while pos < total and 0x30 <= data[pos] <= 0x39:
                pos += 1
        spans.append(SpanRole(start, pos, ROLE_JSON_NUMBER, OWNER_ATOM_CANDIDATE))
        return spans, pos

    elif ch == 0x74:  # t → true
        if data[pos:pos+4] == b"true":
            spans.append(SpanRole(pos, pos + 4, ROLE_JSON_BOOL, OWNER_ATOM_CANDIDATE, "true"))
            return spans, pos + 4
    elif ch == 0x66:  # f → false
        if data[pos:pos+5] == b"false":
            spans.append(SpanRole(pos, pos + 5, ROLE_JSON_BOOL, OWNER_ATOM_CANDIDATE, "false"))
            return spans, pos + 5
    elif ch == 0x6E:  # n → null
        if data[pos:pos+4] == b"null":
            spans.append(SpanRole(pos, pos + 4, ROLE_JSON_NULL, OWNER_STRUCTURE, "null"))
            return spans, pos + 4

    # Unknown — consume one byte and treat as unknown
    spans.append(SpanRole(pos, pos + 1, ROLE_UNKNOWN, OWNER_UNKNOWN_ERROR))
    return spans, pos + 1


def _json_parse_string(data: bytes, pos: int) -> Tuple[List[SpanRole], int]:
    """Parse a JSON string (quoted) at byte level, preserving escapes."""
    total = len(data)
    if pos >= total or data[pos] != 0x22:  # "
        return [], pos

    spans: List[SpanRole] = []
    # Opening quote
    spans.append(SpanRole(pos, pos + 1, ROLE_JSON_STRUCTURE, OWNER_STRUCTURE, "quote_open"))
    pos += 1

    content_start = pos
    while pos < total:
        ch = data[pos]
        if ch == 0x5C:  # \
            pos += 2  # skip escape + next char
        elif ch == 0x22:  # "
            break
        else:
            pos += 1

    # String content
    if pos > content_start:
        spans.append(SpanRole(content_start, pos, ROLE_JSON_STRING, OWNER_ATOM_CANDIDATE))

    # Closing quote
    if pos < total and data[pos] == 0x22:
        spans.append(SpanRole(pos, pos + 1, ROLE_JSON_STRUCTURE, OWNER_STRUCTURE, "quote_close"))
        pos += 1

    return spans, pos


# ═══════════════════════════════════════════════════════════════════════
# JSONL adapter
# ═══════════════════════════════════════════════════════════════════════

def adapt_jsonl(index: UTF8ByteIndex) -> List[SpanRole]:
    """Parse JSONL: each line is one JSON object. Preserves line terminators."""
    b = index.source_bytes
    total = index.total_bytes
    lines = _split_lines_byte(index)
    spans: List[SpanRole] = []

    for line_start, line_end in lines:
        line_data = b[line_start:line_end]
        # Trim trailing CR (already handled by line splitting)
        stripped = line_data.rstrip(b"\r\n")
        if not stripped:
            spans.append(SpanRole(line_start, line_end, ROLE_BLANK_LINE, OWNER_STRUCTURE))
            continue
        try:
            json.loads(stripped.decode("utf-8"))
            token_spans, _ = _json_tokenize(b, line_start)
            spans.extend(token_spans)
        except (json.JSONDecodeError, UnicodeDecodeError):
            spans.append(SpanRole(line_start, line_end, ROLE_UNKNOWN, OWNER_UNKNOWN_ERROR,
                                  "malformed_jsonl"))

    return spans


# ═══════════════════════════════════════════════════════════════════════
# Conversation adapters
# ═══════════════════════════════════════════════════════════════════════

def adapt_conversation_structured(index: UTF8ByteIndex) -> List[SpanRole]:
    """Parse conversation with role/content/optional timestamp/metadata structure.

    Expected format: lines with role:content or similar structured messages.
    """
    b = index.source_bytes
    total = index.total_bytes
    lines = _split_lines_byte(index)
    spans: List[SpanRole] = []

    for line_start, line_end in lines:
        line_data = b[line_start:line_end]
        if not line_data.strip():
            spans.append(SpanRole(line_start, line_end, ROLE_BLANK_LINE, OWNER_STRUCTURE))
            continue

        # Look for "role: " or "role:" pattern
        colon_pos = -1
        for i in range(min(len(line_data), 30)):
            if line_data[i] == 0x3A:  # :
                colon_pos = i
                break

        if colon_pos > 0:
            role_bytes = line_data[:colon_pos].strip()
            content_start = line_start + colon_pos + 1
            # Skip space after colon
            if content_start < line_end and b[content_start] == 0x20:
                content_start += 1

            role_str = role_bytes.decode("utf-8", "replace").lower().strip()
            spans.append(SpanRole(line_start, line_start + colon_pos,
                                  ROLE_CONVERSATION_ROLE, OWNER_STRUCTURE, role_str))
            if content_start < line_end:
                spans.append(SpanRole(content_start, line_end,
                                      ROLE_CONVERSATION_CONTENT, OWNER_ATOM_CANDIDATE))
        else:
            spans.append(SpanRole(line_start, line_end, ROLE_CONVERSATION_CONTENT))

    return spans


def adapt_conversation_plain(index: UTF8ByteIndex) -> List[SpanRole]:
    """Parse plain conversation messages separated by blank lines or turn markers."""
    b = index.source_bytes
    total = index.total_bytes
    lines = _split_lines_byte(index)
    spans: List[SpanRole] = []

    current_start = -1
    for line_start, line_end in lines:
        line_data = b[line_start:line_end]
        if not line_data.strip():
            if current_start >= 0:
                spans.append(SpanRole(current_start, line_start,
                                      ROLE_CONVERSATION_CONTENT))
                current_start = -1
            continue
        if current_start < 0:
            current_start = line_start

    if current_start >= 0:
        spans.append(SpanRole(current_start, total, ROLE_CONVERSATION_CONTENT))

    return spans


# ═══════════════════════════════════════════════════════════════════════
# Main dispatch
# ═══════════════════════════════════════════════════════════════════════

ADAPTERS = {
    "markdown": adapt_markdown,
    "txt": adapt_txt,
    "json": adapt_json,
    "jsonl": adapt_jsonl,
    "conversation_structured": adapt_conversation_structured,
    "conversation_plain": adapt_conversation_plain,
}


def adapt(index: UTF8ByteIndex, fmt: str) -> List[SpanRole]:
    """Dispatch to the correct adapter by format name."""
    if fmt not in ADAPTERS:
        raise ValueError(f"Unknown format: {fmt}. Supported: {sorted(ADAPTERS.keys())}")
    return ADAPTERS[fmt](index)
