"""E35 S1 — LosslessAdapters: 100% byte coverage for 5 input formats.
Every byte in the source is accounted for as either content, structure, or GAP.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from qclaw_byte_atomizer.byte_index import ByteIndex, ByteSpan
import json
import re


@dataclass
class AdaptedSpan:
    """A span from the adapter with its semantic role."""
    byte_span: ByteSpan
    role: str  # "content", "structure", "GAP", "code_block", "list_item", "table", "header"
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "start": self.byte_span.start, "end": self.byte_span.end,
            "text": self.byte_span.text, "role": self.role,
            "metadata": self.metadata
        }


class LosslessAdapter:
    """Base adapter with 100% byte coverage guarantee."""

    def __init__(self, source: str):
        self.source = source
        self.idx = ByteIndex(source)
        self.spans: List[AdaptedSpan] = []

    def add_content(self, start: int, end: int, role: str, meta: dict = None):
        if end > start:
            self.spans.append(AdaptedSpan(
                byte_span=self.idx.span(start, end),
                role=role,
                metadata=meta or {}
            ))

    def add_gap(self, start: int, end: int):
        if end > start:
            self.add_content(start, end, "GAP")

    def fill_gaps(self):
        """Ensure 100% coverage by tagging all uncovered bytes as GAP."""
        sorted_spans = sorted(self.spans, key=lambda s: s.byte_span.start)
        raw_spans = [s.byte_span for s in sorted_spans]
        gaps = self.idx.find_gaps(raw_spans)
        for gap_start, gap_end in gaps:
            self.add_gap(gap_start, gap_end)
        self.spans.sort(key=lambda s: s.byte_span.start)

    def coverage(self) -> float:
        raw_spans = [s.byte_span for s in self.spans]
        return self.idx.coverage(raw_spans)

    def get_spans(self) -> List[AdaptedSpan]:
        return self.spans


class MarkdownAdapter(LosslessAdapter):
    """Lossless Markdown adapter. 100% byte coverage."""

    def adapt(self) -> LosslessAdapter:
        pos = 0
        text = self.source
        n = len(text)

        # Skip leading newlines
        while pos < n and text[pos] == "\n":
            pos += 1

        while pos < n:
            # Code blocks (fenced)
            if text[pos:pos+3] == "```":
                try:
                    lang_end = text.index("\n", pos + 3)
                except ValueError:
                    lang_end = n
                lang_line_end = lang_end
                close = text.find("\n```", lang_line_end)
                if close == -1:
                    close_end = n
                else:
                    close_end = close + 4
                # Include trailing newline if present
                if close_end < n and text[close_end] == "\n":
                    close_end += 1
                self.add_content(pos, close_end, "code_block",
                                 {"language": text[pos+3:lang_line_end].strip()})
                pos = close_end
                continue

            # Headers (# ...)
            if text[pos] == "#" and (pos == 0 or text[pos-1] == "\n"):
                end = text.find("\n", pos)
                if end == -1:
                    end = n
                else:
                    end += 1
                self.add_content(pos, end, "header")
                pos = end
                continue

            # List items (-, *, +)
            if (pos == 0 or text[pos-1] == "\n") and text[pos] in "-*+" and pos+1 < n and text[pos+1] == " ":
                end = text.find("\n", pos)
                if end == -1:
                    end = n
                else:
                    end += 1
                self.add_content(pos, end, "list_item")
                pos = end
                continue

            # Numbered list
            ln_match = re.match(r"^\d+\.\s", text[pos:])
            if (pos == 0 or text[pos-1] == "\n") and ln_match:
                end = text.find("\n", pos)
                if end == -1:
                    end = n
                else:
                    end += 1
                self.add_content(pos, end, "list_item")
                pos = end
                continue

            # Table (pipe detection) - must be at start of line or after newline
            if (pos == 0 or text[pos-1] == "\n") and pos < n and text[pos] == "|":
                end = text.find("\n", pos)
                if end == -1:
                    end = n
                else:
                    end += 1
                self.add_content(pos, end, "table")
                pos = end
                continue

            # Skip lone newlines between blocks
            if text[pos] == "\n":
                end = pos + 1
                # Skip multiple contiguous newlines
                while end < n and text[end] == "\n":
                    end += 1
                self.add_gap(pos, end)
                pos = end
                continue

            # Paragraph / content block
            end = text.find("\n\n", pos)
            if end == -1:
                end = n
            else:
                end += 2
            text_block = text[pos:end].strip()
            if text_block:
                self.add_content(pos, end, "content")
            pos = end

        # Fill gaps to guarantee 100% coverage
        self.fill_gaps()
        return self


class TextAdapter(LosslessAdapter):
    """Lossless plain text adapter."""

    def adapt(self) -> LosslessAdapter:
        text = self.source
        pos = 0
        while pos < len(text):
            end = text.find("\n\n", pos)
            if end == -1:
                end = len(text)
            else:
                end += 2
            content = text[pos:end].strip()
            if content:
                self.add_content(pos, end, "content")
            pos = end
        self.fill_gaps()
        return self


class JsonAdapter(LosslessAdapter):
    """Lossless JSON adapter. Captures field key-value regions + gaps."""

    def adapt(self) -> LosslessAdapter:
        text = self.source
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            self.add_content(0, len(text), "GAP")
            return self

        self._walk(obj, "", text)
        self.fill_gaps()
        return self

    def _walk(self, obj, path, source_text):
        if isinstance(obj, dict):
            for key, value in obj.items():
                field_path = f"{path}.{key}" if path else key
                # Find key position in source
                escaped_key = json.dumps(key)
                key_pos = source_text.find(escaped_key)
                if key_pos >= 0:
                    # Find the value region after the key
                    colon_pos = source_text.find(":", key_pos + len(escaped_key))
                    if colon_pos >= 0:
                        # Approximate value end
                        val_start = colon_pos + 1
                        val_str = json.dumps(value, ensure_ascii=False)
                        val_end = source_text.find(val_str, val_start)
                        if val_end >= 0:
                            end = val_end + len(val_str)
                            self.add_content(key_pos, end, "content",
                                             {"field_path": field_path, "key": key})
                if isinstance(value, (dict, list)):
                    self._walk(value, field_path, source_text)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._walk(item, f"{path}[{i}]", source_text)


class JsonlAdapter(LosslessAdapter):
    """Lossless JSONL adapter. Line-by-line complete coverage."""

    def adapt(self) -> LosslessAdapter:
        lines = self.source.split("\n")
        pos = 0
        for line in lines:
            line_with_nl = line + "\n"
            stripped = line.strip()
            if stripped:
                try:
                    json.loads(stripped)
                    self.add_content(pos, pos + len(line_with_nl), "content")
                except json.JSONDecodeError:
                    self.add_content(pos, pos + len(line_with_nl), "GAP")
            pos += len(line_with_nl)
        self.fill_gaps()
        return self


class ConversationAdapter(LosslessAdapter):
    """Lossless conversation adapter. Turn-by-turn with meta gaps."""

    def adapt(self) -> LosslessAdapter:
        text = self.source
        pos = 0
        # Match turn markers like "User:", "Assistant:", "System:"
        turn_pattern = re.compile(r"^(User|Assistant|System):", re.MULTILINE)

        for m in turn_pattern.finditer(text):
            turn_start = m.start()
            self.add_content(turn_start, turn_start + len(m.group()), "structure",
                             {"turn_role": m.group(1)})
            # Find next turn or end
            next_turn = turn_pattern.search(text, m.end())
            content_end = next_turn.start() if next_turn else len(text)
            body = text[m.end():content_end].strip()
            if body:
                self.add_content(m.end(), content_end, "content",
                                 {"turn_role": m.group(1)})

        self.fill_gaps()
        return self
