"""E36 S2 — Chunk-granular adapters on OriginalByteIndex.
Uses byte-position scanning (paragraph-level), not per-chunk iteration."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import re, json

from .boundary_table import OriginalByteIndex, Chunk
from .coverage import CoverageValidator, Span


@dataclass(frozen=True)
class ContentSpan:
    byte_start: int
    byte_end: int
    role: str
    metadata: Dict = field(default_factory=dict)

    def text(self, source_bytes: bytes) -> str:
        return source_bytes[self.byte_start:self.byte_end].decode("utf-8", errors="replace")


def _next_chunk_index(index: OriginalByteIndex, byte_offset: int) -> int:
    """Return chunk idx where c.byte_start >= byte_offset, or len(chunks)."""
    chunks = index.chunks
    lo, hi = 0, len(chunks)
    while lo < hi:
        mid = (lo + hi) // 2
        if chunks[mid].byte_start < byte_offset:
            lo = mid + 1
        else:
            hi = mid
    return lo


class MarkdownByteAdapter:
    def __init__(self, index: OriginalByteIndex):
        self._index = index

    def parse(self) -> List[ContentSpan]:
        raw = self._index.source_bytes
        n = len(raw)
        spans: List[ContentSpan] = []
        pos = 0

        while pos < n:
            rest = raw[pos:]
            rest_str = rest.decode("utf-8", errors="replace")

            # Skip leading blank lines
            if rest_str.startswith("\n"):
                end = pos
                while end < n and raw[end:end+1] == b'\n':
                    end += 1
                spans.append(ContentSpan(pos, end, "blank_line"))
                pos = end
                continue

            # Code block
            if rest_str.startswith("```"):
                end_marker = rest_str.find("\n```")
                if end_marker >= 0:
                    close = end_marker + 4
                    block_end = pos + close
                    if block_end < n and raw[block_end:block_end+1] == b'\n':
                        block_end += 1
                    lang_end = rest_str.find("\n")
                    lang = rest_str[3:lang_end].strip() if lang_end > 0 else ""
                    spans.append(ContentSpan(pos, block_end, "code_block", {"language": lang}))
                    pos = block_end
                    continue

            # Header at line start
            if rest_str.startswith("#"):
                m = re.match(r'^(#{1,6})\s', rest_str)
                if m:
                    level = len(m.group(1))
                    nl = rest_str.find("\n")
                    if nl < 0:
                        h_end = n
                    else:
                        h_end = pos + nl + 1
                    spans.append(ContentSpan(pos, h_end, "header", {"level": level}))
                    pos = h_end
                    continue

            # Table at line start
            if rest_str.startswith("|"):
                nl = rest_str.find("\n")
                if nl < 0:
                    t_end = n
                else:
                    t_end = pos + nl + 1
                spans.append(ContentSpan(pos, t_end, "table"))
                pos = t_end
                continue

            # List item
            m_li = re.match(r'^[\-\*\+]\s', rest_str)
            if m_li:
                nl = rest_str.find("\n")
                if nl < 0:
                    li_end = n
                else:
                    li_end = pos + nl + 1
                spans.append(ContentSpan(pos, li_end, "list_item"))
                pos = li_end
                continue

            # Numbered list
            m_nl = re.match(r'^\d+\.\s', rest_str)
            if m_nl:
                nl = rest_str.find("\n")
                if nl < 0:
                    nli_end = n
                else:
                    nli_end = pos + nl + 1
                spans.append(ContentSpan(pos, nli_end, "list_item"))
                pos = nli_end
                continue

            # Content paragraph — until double newline or structural marker
            double_nl = rest_str.find("\n\n")
            if double_nl >= 0:
                pe = pos + double_nl + 2
            else:
                pe = n

            text_block = raw[pos:pe].decode("utf-8", errors="replace").strip()
            if text_block:
                spans.append(ContentSpan(pos, pe, "content"))
            pos = pe

        return spans

    def coverage(self, spans: List[ContentSpan]) -> float:
        covered = sum(s.byte_end - s.byte_start for s in spans)
        return covered / self._index.total_bytes if self._index.total_bytes > 0 else 0.0


class TextByteAdapter:
    def __init__(self, index: OriginalByteIndex):
        self._index = index

    def parse(self) -> List[ContentSpan]:
        raw = self._index.source_bytes
        n = len(raw)
        spans: List[ContentSpan] = []
        pos = 0
        while pos < n:
            end = raw.find(b'\n\n', pos)
            if end < 0:
                end = n
            else:
                end += 2
            text = raw[pos:end].decode("utf-8", errors="replace").strip()
            if text:
                spans.append(ContentSpan(pos, end, "content"))
            pos = end
        return spans

    def coverage(self, spans: List[ContentSpan]) -> float:
        covered = sum(s.byte_end - s.byte_start for s in spans)
        return covered / self._index.total_bytes if self._index.total_bytes > 0 else 0.0


class JsonByteAdapter:
    def __init__(self, index: OriginalByteIndex):
        self._index = index

    def parse(self) -> List[ContentSpan]:
        raw = self._index.source_bytes
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return [ContentSpan(0, len(raw), "invalid_json")]

        spans: List[ContentSpan] = []
        self._walk(data, raw, 0, len(raw), "$", spans)
        return spans

    def _walk(self, obj, raw: bytes, start: int, end: int, path: str, spans: List[ContentSpan]):
        if isinstance(obj, dict):
            spans.append(ContentSpan(start, end, "json_object", {"path": path, "key_count": len(obj)}))
            span_text = raw[start:end].decode("utf-8", errors="replace")
            pos = 0
            for k, v in obj.items():
                key_quoted = f'"{k}"'
                key_start = span_text.find(key_quoted, pos)
                if key_start >= 0:
                    ks = start + key_start
                    ke = ks + len(key_quoted)
                    spans.append(ContentSpan(ks, ke, "json_key", {"key": k, "path": f"{path}.{k}"}))
                    pos = key_start + len(key_quoted) + 1
            spans.append(ContentSpan(start, end, "json_content", {"path": path}))
        elif isinstance(obj, list):
            spans.append(ContentSpan(start, end, "json_array", {"path": path, "length": len(obj)}))
            spans.append(ContentSpan(start, end, "json_content", {"path": path}))
        elif isinstance(obj, str):
            spans.append(ContentSpan(start, end, "json_string", {"path": path, "len": len(obj)}))
        else:
            spans.append(ContentSpan(start, end, "json_value", {"path": path}))

    def coverage(self, spans: List[ContentSpan]) -> float:
        covered = sum(s.byte_end - s.byte_start for s in spans)
        return covered / self._index.total_bytes if self._index.total_bytes > 0 else 0.0


class JsonlByteAdapter:
    def __init__(self, index: OriginalByteIndex):
        self._index = index

    def parse(self) -> List[ContentSpan]:
        raw = self._index.source_bytes
        spans: List[ContentSpan] = []
        pos = 0
        remaining = raw
        while remaining:
            nl = remaining.find(b'\n')
            if nl < 0:
                line = remaining
                next_pos = len(raw)
            else:
                line = remaining[:nl]
                next_pos = pos + nl + 1
            if line.strip():
                try:
                    json.loads(line.decode("utf-8"))
                    spans.append(ContentSpan(pos, next_pos, "jsonl_line", {"valid": True}))
                except json.JSONDecodeError:
                    spans.append(ContentSpan(pos, next_pos, "jsonl_line", {"valid": False}))
            else:
                spans.append(ContentSpan(pos, next_pos, "jsonl_empty"))
            pos = next_pos
            remaining = raw[pos:] if pos < len(raw) else b""
        return spans

    def coverage(self, spans: List[ContentSpan]) -> float:
        covered = sum(s.byte_end - s.byte_start for s in spans)
        return covered / self._index.total_bytes if self._index.total_bytes > 0 else 0.0


class ConversationByteAdapter:
    def __init__(self, index: OriginalByteIndex):
        self._index = index

    def parse(self, roles: List[str] = None) -> List[ContentSpan]:
        allowed = set(roles) if roles else {"user", "assistant", "system", "human", "ai"}
        raw = self._index.source_bytes
        text = raw.decode("utf-8", errors="replace")
        spans: List[ContentSpan] = []

        role_pattern = re.compile(r'^(user|assistant|system|human|ai)\s*[:：]\s*', re.MULTILINE)
        matches = list(role_pattern.finditer(text))
        if not matches:
            spans.append(ContentSpan(0, len(raw), "conversation_body", {"role": "unknown"}))
            return spans

        for idx, m in enumerate(matches):
            role = m.group(1)
            if role.lower() not in allowed:
                continue
            role_start = m.start()
            role_end = m.end()
            spans.append(ContentSpan(role_start, role_end, "conversation_role", {"role": role}))
            body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw)
            if body_end > role_end:
                spans.append(ContentSpan(role_end, body_end, "conversation_body", {"role": role}))

        return spans

    def coverage(self, spans: List[ContentSpan]) -> float:
        covered = sum(s.byte_end - s.byte_start for s in spans)
        return covered / self._index.total_bytes if self._index.total_bytes > 0 else 0.0
