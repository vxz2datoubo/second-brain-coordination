"""E37 S2 — Original-byte adapter: Markdown, TXT, JSON, JSONL, conversation.

All span extraction operates on byte offsets from boundary_table.OriginalByteIndex.
No str.find/regex‑char‑index/len(str) used to compute byte spans.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any
import json as _json_mod
from .boundary_table import OriginalByteIndex


# ── adapter span ─────────────────────────────────────────────────────
@dataclass(frozen=True)
class AdapterSpan:
    byte_start: int
    byte_end: int  # exclusive
    role: str  # header|content|list_item|code_block|blockquote|table|…
    cp_start: int
    cp_end: int


# ── plain text ───────────────────────────────────────────────────────
def adapt_txt(index: OriginalByteIndex) -> List[AdapterSpan]:
    spans: List[AdapterSpan] = []
    start = 0
    for chunk in index.chunks:
        if chunk.kind == "EOL":
            roles = "content"  # lines as content
            if start < chunk.byte_start:
                spans.append(AdapterSpan(start, chunk.byte_start, "content", index.byte_to_codepoint(start), index.byte_to_codepoint(chunk.byte_start)))
            start = chunk.byte_end
    if start < index.total_bytes:
        spans.append(AdapterSpan(start, index.total_bytes, "content", index.byte_to_codepoint(start), index.total_codepoints))
    return spans


# ── markdown ─────────────────────────────────────────────────────────
def _is_md_header_line(index: OriginalByteIndex, chunk_start_byte: int) -> bool:
    """Check if the line starting at chunk_start_byte begins with '#' marks."""
    b = index.source_bytes
    i = chunk_start_byte
    if i >= len(b) or b[i] != 0x23:  # '#'
        return False
    while i < len(b) and b[i] == 0x23:
        i += 1
    return i < len(b) and b[i] == 0x20  # '# ' required


def _is_md_code_fence(index: OriginalByteIndex, chunk_start_byte: int) -> bool:
    """Line starts with ``` or ~~~"""
    b = index.source_bytes
    i = chunk_start_byte
    if i + 2 >= len(b):
        return False
    if b[i:i + 3] in (b'```', b'~~~'):
        return True
    return False


def _is_md_blank(index: OriginalByteIndex, line_start: int, line_end: int) -> bool:
    b = index.source_bytes
    sl = b[line_start:line_end]
    return len(sl.strip()) == 0


def _is_md_list_item(index: OriginalByteIndex, chunk_start_byte: int) -> bool:
    b = index.source_bytes
    i = chunk_start_byte
    # bullet or numbered list
    if i >= len(b):
        return False
    if b[i] in (0x2D, 0x2A, 0x2B):  # - * +
        return i + 1 < len(b) and b[i + 1] == 0x20
    # numbered: '1.' etc
    if 0x30 <= b[i] <= 0x39:
        j = i
        while j < len(b) and 0x30 <= b[j] <= 0x39:
            j += 1
        if j < len(b) and b[j] == 0x2E:  # '.'
            return j + 1 < len(b) and (b[j + 1] == 0x20 or b[j + 1] == 0x09)
    return False


def _is_md_blockquote(index: OriginalByteIndex, chunk_start_byte: int) -> bool:
    b = index.source_bytes
    i = chunk_start_byte
    return i < len(b) and b[i] == 0x3E  # '>'


def _is_md_table_row(index: OriginalByteIndex, chunk_start_byte: int) -> bool:
    b = index.source_bytes
    i = chunk_start_byte
    return i < len(b) and b[i] == 0x7C  # '|'


def adapt_markdown(index: OriginalByteIndex) -> List[AdapterSpan]:
    spans: List[AdapterSpan] = []
    b = index.source_bytes
    line_starts = list(index.line_starts) + [index.total_bytes]

    in_code_block = False
    line_start_byte = 0
    for j in range(len(line_starts) - 1):
        ls = line_starts[j]
        le = line_starts[j + 1]

        if _is_md_blank(index, ls, le) and not in_code_block:
            continue

        if _is_md_code_fence(index, ls):
            in_code_block = not in_code_block
            spans.append(AdapterSpan(ls, le, "code_block", index.byte_to_codepoint(ls), index.byte_to_codepoint(le)))
            line_start_byte = le
            continue

        if in_code_block:
            # Continue code block
            spans.append(AdapterSpan(ls, le, "code_block", index.byte_to_codepoint(ls), index.byte_to_codepoint(le)))
            line_start_byte = le
            continue

        if _is_md_header_line(index, ls):
            spans.append(AdapterSpan(ls, le, "header", index.byte_to_codepoint(ls), index.byte_to_codepoint(le)))
        elif _is_md_list_item(index, ls):
            spans.append(AdapterSpan(ls, le, "list_item", index.byte_to_codepoint(ls), index.byte_to_codepoint(le)))
        elif _is_md_blockquote(index, ls):
            spans.append(AdapterSpan(ls, le, "blockquote", index.byte_to_codepoint(ls), index.byte_to_codepoint(le)))
        elif _is_md_table_row(index, ls):
            spans.append(AdapterSpan(ls, le, "table", index.byte_to_codepoint(ls), index.byte_to_codepoint(le)))
        else:
            spans.append(AdapterSpan(ls, le, "content", index.byte_to_codepoint(ls), index.byte_to_codepoint(le)))

        line_start_byte = le

    return spans


# ── json ─────────────────────────────────────────────────────────────
def adapt_json(index: OriginalByteIndex) -> List[AdapterSpan]:
    """Tokenize JSON by scanning bytes, NOT json.loads().

    We produce spans for: { } [ ] : , strings, numbers (int/float/exp),
    booleans (true/false), null, and whitespace.
    All spans preserve order and exact byte boundaries.
    """
    spans: List[AdapterSpan] = []
    b = index.source_bytes
    n = index.total_bytes
    i = 0

    while i < n:
        byte = b[i]
        # Whitespace
        if byte in (0x20, 0x09, 0x0A, 0x0D):
            i += 1
            continue
        # Structural
        if byte in (0x7B, 0x7D, 0x5B, 0x5D, 0x3A, 0x2C):
            kind = {0x7B: "object_start", 0x7D: "object_end", 0x5B: "array_start",
                    0x5D: "array_end", 0x3A: "colon", 0x2C: "comma"}[byte]
            spans.append(AdapterSpan(i, i + 1, kind, index.byte_to_codepoint(i), index.byte_to_codepoint(i + 1)))
            i += 1
            continue
        # String
        if byte == 0x22:  # '"'
            j = i + 1
            while j < n:
                if b[j] == 0x5C:  # '\\'
                    j += 2
                elif b[j] == 0x22:
                    j += 1
                    break
                else:
                    j += 1
            spans.append(AdapterSpan(i, j, "json_string", index.byte_to_codepoint(i), index.byte_to_codepoint(j)))
            i = j
            continue
        # Number or keyword
        if (0x30 <= byte <= 0x39) or byte in (0x2D, 0x2B):  # digit, -, +
            j = i
            # sign already handled
            while j < n and b[j] in (0x2D, 0x2B, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x2E, 0x65, 0x45):
                j += 1
            spans.append(AdapterSpan(i, j, "json_number", index.byte_to_codepoint(i), index.byte_to_codepoint(j)))
            i = j
            continue
        # true
        if b[i:i + 4] == b'true':
            spans.append(AdapterSpan(i, i + 4, "json_bool", index.byte_to_codepoint(i), index.byte_to_codepoint(i + 4)))
            i += 4
            continue
        # false
        if b[i:i + 5] == b'false':
            spans.append(AdapterSpan(i, i + 5, "json_bool", index.byte_to_codepoint(i), index.byte_to_codepoint(i + 5)))
            i += 5
            continue
        # null
        if b[i:i + 4] == b'null':
            spans.append(AdapterSpan(i, i + 4, "json_null", index.byte_to_codepoint(i), index.byte_to_codepoint(i + 4)))
            i += 4
            continue
        # Unknown byte
        i += 1

    return spans


# ── JSONL ─────────────────────────────────────────────────────────────
def adapt_jsonl(index: OriginalByteIndex) -> List[AdapterSpan]:
    """Split JSONL into line boundaries. Complete lines only."""
    spans: List[AdapterSpan] = []
    b = index.source_bytes
    n = index.total_bytes
    last = 0
    for i in range(n):
        if b[i] == 0x0A:  # LF
            line_bytes = b[last:i]
            if line_bytes.strip():
                spans.append(AdapterSpan(last, i, "jsonl_line", index.byte_to_codepoint(last), index.byte_to_codepoint(i)))
            last = i + 1

    # No trailing newline → treat as malformed (leave as gap)
    if last < n and b[last:].strip():
        pass  # Gap — caller must handle via LEDGER

    return spans


# ── conversation ──────────────────────────────────────────────────────
def adapt_conversation_structured(index: OriginalByteIndex) -> List[AdapterSpan]:
    """Best-effort conversation parsing from byte index.

    Looks for JSON-style conversation with role/content fields.
    """
    json_spans = adapt_json(index)
    spans: List[AdapterSpan] = []
    b = index.source_bytes

    for s in json_spans:
        if s.role == "json_string":
            seg = b[s.byte_start:s.byte_end]
            ut = seg.decode("utf-8")
            if ut.strip('"') in ("system", "user", "assistant", "tool"):
                spans.append(AdapterSpan(s.byte_start, s.byte_end, "conversation_role",
                                         s.cp_start, s.cp_end))
                continue
        spans.append(AdapterSpan(s.byte_start, s.byte_end, s.role, s.cp_start, s.cp_end))

    return spans


def adapt_conversation_plain(index: OriginalByteIndex) -> List[AdapterSpan]:
    """Plain-text conversation: User:/Assistant: prefixes."""
    spans: List[AdapterSpan] = []
    b = index.source_bytes
    line_starts = list(index.line_starts) + [index.total_bytes]

    for j in range(len(line_starts) - 1):
        ls = line_starts[j]
        le = line_starts[j + 1]
        line = b[ls:le]

        role = "conversation_body"
        if line.startswith(b"User:"):
            role = "conversation_user"
        elif line.startswith(b"Assistant:"):
            role = "conversation_assistant"
        elif line.startswith(b"System:"):
            role = "conversation_system"

        spans.append(AdapterSpan(ls, le, role, index.byte_to_codepoint(ls), index.byte_to_codepoint(le)))

    return spans


# ── dispatch ─────────────────────────────────────────────────────────
_ADAPTERS = {
    "txt": adapt_txt,
    "markdown": adapt_markdown,
    "json": adapt_json,
    "jsonl": adapt_jsonl,
    "conversation_structured": adapt_conversation_structured,
    "conversation_plain": adapt_conversation_plain,
}


def adapt(format: str, index: OriginalByteIndex) -> List[AdapterSpan]:
    fn = _ADAPTERS.get(format)
    if fn is None:
        raise ValueError(f"Unknown adapter format: {format}")
    return fn(index)
