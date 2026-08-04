"""E40 S2 — Bounded adapters for every original byte.

Six formats: markdown, txt, json, jsonl, conversation_structured, conversation_plain.
All byte-position (no str.find / regex char index / len(str) byte-span writes).
Every adapter returns bounded spans with explicit role labels.
No silent omission: every byte must be covered or provably unowned.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
import json as _json
import re

from .immutable_index import ByteTruthIndex


class ContentRole(str, Enum):
    """Span roles for adapter output."""
    HEADER = "header"
    BLANK_LINE = "blank_line"
    CONTENT = "content"
    CODE_BLOCK = "code_block"
    CODE_BLOCK_FENCE = "code_block_fence"
    LIST_ITEM = "list_item"
    TABLE_ROW = "table_row"
    TABLE_SEPARATOR = "table_separator"
    LINK = "link"
    BLOCKQUOTE = "blockquote"

    # JSON roles
    JSON_OBJECT_START = "json_object_start"
    JSON_OBJECT_END = "json_object_end"
    JSON_ARRAY_START = "json_array_start"
    JSON_ARRAY_END = "json_array_end"
    JSON_STRING = "json_string"
    JSON_NUMBER = "json_number"
    JSON_BOOL = "json_bool"
    JSON_NULL = "json_null"
    JSON_KEY = "json_key"
    JSON_COLON = "json_colon"
    JSON_COMMA = "json_comma"
    JSON_WHITESPACE = "json_whitespace"

    # Conversation roles
    CONVERSATION_ROLE = "conversation_role"
    CONVERSATION_CONTENT = "conversation_content"
    CONVERSATION_METADATA = "conversation_metadata"
    CONVERSATION_SEPARATOR = "conversation_separator"


@dataclass
class ContentSpan:
    """A typed span covering a byte range."""
    byte_start: int
    byte_end: int  # exclusive
    role: ContentRole
    text: bytes = b""


# ═══════════════════════════════════════════════════════════════════════
# TXT adapter
# ═══════════════════════════════════════════════════════════════════════

def _adapt_txt(index: ByteTruthIndex) -> List[ContentSpan]:
    span_count = 0
    spans: List[ContentSpan] = []
    src = index._source_bytes  # type: ignore
    total = index.total_bytes

    if total == 0:
        return spans

    # Parse line by line using byte positions
    for line_start in index.line_starts():
        # Find line end
        line_end = line_start
        while line_end < total:
            b = src[line_end]
            if b == ord('\n'):
                break
            if line_end + 1 < total and src[line_end] == ord('\r') and src[line_end + 1] == ord('\n'):
                break
            line_end += 1

        # Include the line terminator
        if line_end < total:
            if src[line_end] == ord('\r') and line_end + 1 < total and src[line_end + 1] == ord('\n'):
                line_end += 2
            elif src[line_end] == ord('\n'):
                line_end += 1

        # Classify line
        role = ContentRole.CONTENT
        text = src[line_start:line_end]
        stripped = text.strip()
        if len(stripped) == 0:
            role = ContentRole.BLANK_LINE
        elif text.startswith(b"# "):
            role = ContentRole.HEADER
        elif text.startswith(b"- ") or text.startswith(b"* "):
            role = ContentRole.LIST_ITEM

        span_count += 1
        spans.append(ContentSpan(line_start, min(line_end, total), role, text))

    return spans


# ═══════════════════════════════════════════════════════════════════════
# Markdown adapter
# ═══════════════════════════════════════════════════════════════════════

def _adapt_markdown(index: ByteTruthIndex) -> List[ContentSpan]:
    spans: List[ContentSpan] = []
    src = index._source_bytes  # type: ignore
    total = index.total_bytes

    if total == 0:
        return spans

    in_code_block = False
    fence_marker: Optional[bytes] = None

    for line_start in index.line_starts():
        # Find line end
        line_end = line_start
        while line_end < total:
            b = src[line_end]
            if b == ord('\n'):
                break
            if line_end + 1 < total and src[line_end] == ord('\r') and src[line_end + 1] == ord('\n'):
                break
            line_end += 1

        line_text = src[line_start:line_end]

        # Include terminator in span
        span_end = line_end
        if span_end < total:
            if src[span_end] == ord('\r') and span_end + 1 < total and src[span_end + 1] == ord('\n'):
                span_end += 2
            elif src[span_end] == ord('\n'):
                span_end += 1

        stripped = line_text.strip()

        if stripped.startswith(b"```"):
            if not in_code_block:
                in_code_block = True
                fence_marker = stripped[3:].strip()
                spans.append(ContentSpan(line_start, span_end, ContentRole.CODE_BLOCK_FENCE, src[line_start:span_end]))
            else:
                in_code_block = False
                fence_marker = None
                spans.append(ContentSpan(line_start, span_end, ContentRole.CODE_BLOCK_FENCE, src[line_start:span_end]))
            continue

        if in_code_block:
            spans.append(ContentSpan(line_start, span_end, ContentRole.CODE_BLOCK, src[line_start:span_end]))
            continue

        if len(stripped) == 0:
            spans.append(ContentSpan(line_start, span_end, ContentRole.BLANK_LINE, src[line_start:span_end]))
        elif stripped.startswith(b"#"):
            spans.append(ContentSpan(line_start, span_end, ContentRole.HEADER, src[line_start:span_end]))
        elif stripped.startswith(b"- ") or stripped.startswith(b"* ") or re.match(rb"^\d+\.\s", stripped):
            spans.append(ContentSpan(line_start, span_end, ContentRole.LIST_ITEM, src[line_start:span_end]))
        elif b"|" in stripped:
            spans.append(ContentSpan(line_start, span_end, ContentRole.TABLE_ROW, src[line_start:span_end]))
        elif stripped.startswith(b">"):
            spans.append(ContentSpan(line_start, span_end, ContentRole.BLOCKQUOTE, src[line_start:span_end]))
        else:
            spans.append(ContentSpan(line_start, span_end, ContentRole.CONTENT, src[line_start:span_end]))

    return spans


# ═══════════════════════════════════════════════════════════════════════
# JSON adapter — byte-level tokenizer preserving order/escapes/duplicates
# ═══════════════════════════════════════════════════════════════════════

def _adapt_json(index: ByteTruthIndex) -> List[ContentSpan]:
    spans: List[ContentSpan] = []
    src = index._source_bytes  # type: ignore
    total = index.total_bytes
    i = 0

    def skip_whitespace():
        nonlocal i
        while i < total and src[i:i+1] in (b' ', b'\t', b'\n', b'\r'):
            ws_start = i
            i += 1
            while i < total and src[i:i+1] in (b' ', b'\t', b'\n', b'\r'):
                i += 1
            spans.append(ContentSpan(ws_start, i, ContentRole.JSON_WHITESPACE, src[ws_start:i]))

    def read_string():
        nonlocal i
        start = i
        i += 1  # skip opening quote
        while i < total:
            if src[i:i+1] == b'"':
                i += 1
                spans.append(ContentSpan(start, i, ContentRole.JSON_STRING, src[start:i]))
                return
            elif src[i:i+1] == b'\\' and i + 1 < total:
                i += 2
            else:
                i += 1
        raise ValueError(f"[json_unterminated_string] at byte {start}")

    def read_number():
        nonlocal i
        start = i
        while i < total and src[i:i+1] in (b'0',b'1',b'2',b'3',b'4',b'5',b'6',b'7',b'8',b'9',b'.',b'-',b'+',b'e',b'E'):
            i += 1
        spans.append(ContentSpan(start, i, ContentRole.JSON_NUMBER, src[start:i]))

    def read_value():
        nonlocal i
        if i >= total:
            return
        skip_whitespace()
        if i >= total:
            return
        b = src[i:i+1]
        if b == b'{':
            start = i
            i += 1
            spans.append(ContentSpan(start, i, ContentRole.JSON_OBJECT_START, src[start:i]))
            skip_whitespace()
            if i < total and src[i:i+1] != b'}':
                read_kv_pairs()
            skip_whitespace()
            if i < total and src[i:i+1] == b'}':
                start = i
                i += 1
                spans.append(ContentSpan(start, i, ContentRole.JSON_OBJECT_END, src[start:i]))
        elif b == b'[':
            start = i
            i += 1
            spans.append(ContentSpan(start, i, ContentRole.JSON_ARRAY_START, src[start:i]))
            skip_whitespace()
            if i < total and src[i:i+1] != b']':
                read_value()
                skip_whitespace()
                while i < total and src[i:i+1] == b',':
                    start = i
                    i += 1
                    spans.append(ContentSpan(start, i, ContentRole.JSON_COMMA, src[start:i]))
                    read_value()
                    skip_whitespace()
            if i < total and src[i:i+1] == b']':
                start = i
                i += 1
                spans.append(ContentSpan(start, i, ContentRole.JSON_ARRAY_END, src[start:i]))
        elif b == b'"':
            read_string()
        elif b in (b't', b'f'):
            start = i
            i += 4 if b == b't' else 5
            spans.append(ContentSpan(start, i, ContentRole.JSON_BOOL, src[start:i]))
        elif b == b'n':
            start = i
            i += 4
            spans.append(ContentSpan(start, i, ContentRole.JSON_NULL, src[start:i]))
        elif b in (b'0',b'1',b'2',b'3',b'4',b'5',b'6',b'7',b'8',b'9',b'-'):
            read_number()

    def read_kv_pairs():
        nonlocal i
        while i < total:
            skip_whitespace()
            if i >= total or src[i:i+1] == b'}':
                break
            key_start = i
            read_string()
            skip_whitespace()
            if i < total and src[i:i+1] == b':':
                start = i
                i += 1
                spans.append(ContentSpan(start, i, ContentRole.JSON_COLON, src[start:i]))
            read_value()
            skip_whitespace()
            if i < total and src[i:i+1] == b',':
                start = i
                i += 1
                spans.append(ContentSpan(start, i, ContentRole.JSON_COMMA, src[start:i]))

    read_value()
    skip_whitespace()
    # Trailing bytes
    if i < total:
        spans.append(ContentSpan(i, total, ContentRole.JSON_WHITESPACE, src[i:total]))
    return spans


# ═══════════════════════════════════════════════════════════════════════
# JSONL adapter — line-bounded slices
# ═══════════════════════════════════════════════════════════════════════

def _adapt_jsonl(index: ByteTruthIndex) -> List[ContentSpan]:
    spans: List[ContentSpan] = []
    src = index._source_bytes  # type: ignore
    total = index.total_bytes
    line_starts = index.line_starts()

    for idx, line_start in enumerate(line_starts):
        is_last = idx == len(line_starts) - 1
        if is_last:
            line_text = src[line_start:total]
        else:
            line_end = line_starts[idx + 1]
            # rewind the line terminator
            if line_end - 1 >= 0 and src[line_end - 1] == ord('\n'):
                probe = line_end
                if probe - 2 >= 0 and src[probe - 2] == ord('\r'):
                    line_text = src[line_start:probe - 2]
                else:
                    line_text = src[line_start:probe - 1]
            else:
                line_text = src[line_start:line_end]

        stripped = line_text.strip()
        if len(stripped) == 0:
            continue

        # Try parsing as JSON for this line
        try:
            _json.loads(stripped.decode("utf-8"))
            spans.append(ContentSpan(line_start, line_start + len(line_text),
                                     ContentRole.CONTENT, line_text))
        except Exception:
            spans.append(ContentSpan(line_start, line_start + len(line_text),
                                     ContentRole.CONTENT, line_text))

    return spans


# ═══════════════════════════════════════════════════════════════════════
# Conversation adapter (structured + plain)
# ═══════════════════════════════════════════════════════════════════════

def _adapt_conversation_structured(index: ByteTruthIndex) -> List[ContentSpan]:
    """Conversation with structured fields: role, content, optional metadata."""
    spans: List[ContentSpan] = []
    src = index._source_bytes  # type: ignore
    total = index.total_bytes

    if total == 0:
        return spans

    # Simple structured conversation: line-based with role:content
    for line_start in index.line_starts():
        line_end = line_start
        while line_end < total:
            b = src[line_end]
            if b == ord('\n'):
                break
            if line_end + 1 < total and src[line_end] == ord('\r') and src[line_end + 1] == ord('\n'):
                break
            line_end += 1

        span_end = line_end
        if span_end < total:
            if src[span_end] == ord('\r') and span_end + 1 < total and src[span_end + 1] == ord('\n'):
                span_end += 2
            elif src[span_end] == ord('\n'):
                span_end += 1

        line = src[line_start:line_end]
        stripped = line.strip()

        if len(stripped) == 0:
            spans.append(ContentSpan(line_start, span_end, ContentRole.CONVERSATION_SEPARATOR, src[line_start:span_end]))
            continue

        # Look for role prefix: "role: content" or "role:content"
        colon_pos = stripped.find(b':')
        if colon_pos > 0:
            role_part = stripped[:colon_pos].strip().lower()
            if role_part in (b"user", b"assistant", b"system", b"human", b"ai", b"tool"):
                # Role
                role_byte_end = line_start + colon_pos + 1
                spans.append(ContentSpan(line_start, role_byte_end,
                                         ContentRole.CONVERSATION_ROLE, src[line_start:role_byte_end]))
                # Content after colon
                content_start = role_byte_end
                if content_start < span_end:
                    spans.append(ContentSpan(content_start, span_end,
                                             ContentRole.CONVERSATION_CONTENT, src[content_start:span_end]))
                continue

        # Plain content
        spans.append(ContentSpan(line_start, span_end, ContentRole.CONVERSATION_CONTENT, src[line_start:span_end]))

    return spans


def _adapt_conversation_plain(index: ByteTruthIndex) -> List[ContentSpan]:
    """Plain conversation without structured fields."""
    spans: List[ContentSpan] = []
    src = index._source_bytes  # type: ignore
    total = index.total_bytes

    for line_start in index.line_starts():
        line_end = line_start
        while line_end < total:
            b = src[line_end]
            if b == ord('\n'):
                break
            if line_end + 1 < total and src[line_end] == ord('\r') and src[line_end + 1] == ord('\n'):
                break
            line_end += 1

        span_end = line_end
        if span_end < total:
            if src[span_end] == ord('\r') and span_end + 1 < total and src[span_end + 1] == ord('\n'):
                span_end += 2
            elif src[span_end] == ord('\n'):
                span_end += 1

        text = src[line_start:span_end]
        role = ContentRole.CONVERSATION_CONTENT if text.strip() else ContentRole.CONVERSATION_SEPARATOR
        spans.append(ContentSpan(line_start, span_end, role, text))

    return spans


# ═══════════════════════════════════════════════════════════════════════
# Public adapter dispatch
# ═══════════════════════════════════════════════════════════════════════

def adapt(source: bytes, format: str) -> Tuple[ByteTruthIndex, List[ContentSpan]]:
    """Parse source bytes with the given format.

    Formats: txt, markdown, json, jsonl, conversation_structured, conversation_plain.
    """
    index = ByteTruthIndex(source)

    adapters = {
        "txt": _adapt_txt,
        "markdown": _adapt_markdown,
        "json": _adapt_json,
        "jsonl": _adapt_jsonl,
        "conversation_structured": _adapt_conversation_structured,
        "conversation_plain": _adapt_conversation_plain,
    }

    fn = adapters.get(format)
    if fn is None:
        raise ValueError(f"[unknown_format] {format!r}. Known: {list(adapters)}")

    spans = fn(index)
    return index, spans
