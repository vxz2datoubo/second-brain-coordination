"""E35 S0 — ByteIndex: byte↔codepoint↔line reversible mapping.
Every span slices exactly to source bytes. Deterministic across Python 3.11+/3.13+.
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
import json


@dataclass(frozen=True)
class ByteSpan:
    """Byte-exact span: source_bytes[start:end].decode("utf-8") == text."""
    start: int
    end: int  # exclusive
    text: str

    def to_dict(self):
        return {"start": self.start, "end": self.end, "text": self.text}

    def slice(self, source_bytes: bytes) -> str:
        return source_bytes[self.start:self.end].decode("utf-8")

    def verify(self, source_bytes: bytes) -> bool:
        try:
            return self.slice(source_bytes) == self.text
        except Exception:
            return False

    def __len__(self):
        return self.end - self.start


@dataclass
class ByteIndex:
    """Bidirectional byte ↔ codepoint ↔ line index for a UTF-8 source."""
    source: str
    source_bytes: bytes = field(init=False)
    byte_to_pos: Dict[int, Tuple[int, int]] = field(default_factory=dict)  # byte→(cp_idx,line)
    line_starts: List[int] = field(default_factory=list)  # byte offsets of line starts

    def __post_init__(self):
        self.source_bytes = self.source.encode("utf-8")
        self._build()

    def _build(self):
        """Build bidirectional index."""
        byte_pos = 0
        line_start_byte = 0
        self.line_starts = [0]

        for cp_idx, ch in enumerate(self.source):
            ch_bytes = ch.encode("utf-8")
            for b_off in range(len(ch_bytes)):
                self.byte_to_pos[byte_pos + b_off] = (cp_idx, len(self.line_starts) - 1)
            byte_pos += len(ch_bytes)
            if ch == "\n":
                self.line_starts.append(byte_pos)

    def total_bytes(self) -> int:
        return len(self.source_bytes)

    def total_codepoints(self) -> int:
        return len(self.source)

    def total_lines(self) -> int:
        return len(self.line_starts)

    def codepoint_at_byte(self, byte_offset: int) -> int:
        entry = self.byte_to_pos.get(byte_offset)
        return entry[0] if entry else -1

    def line_at_byte(self, byte_offset: int) -> int:
        entry = self.byte_to_pos.get(byte_offset)
        return entry[1] if entry else -1

    def line_byte_range(self, line_idx: int) -> Tuple[int, int]:
        """Byte range for a line (start inclusive, end exclusive)."""
        if line_idx < 0 or line_idx >= len(self.line_starts):
            return (-1, -1)
        start = self.line_starts[line_idx]
        if line_idx + 1 < len(self.line_starts):
            end = self.line_starts[line_idx + 1]
        else:
            end = self.total_bytes()
        return (start, end)

    def span(self, start_byte: int, end_byte: int) -> ByteSpan:
        """Create verified ByteSpan."""
        text = self.source_bytes[start_byte:end_byte].decode("utf-8")
        return ByteSpan(start=start_byte, end=end_byte, text=text)

    def coverage(self, spans: List[ByteSpan]) -> float:
        """Compute fraction of total bytes covered by spans."""
        if not spans or self.total_bytes() == 0:
            return 0.0
        covered = 0
        sorted_spans = sorted(spans, key=lambda s: s.start)
        last_end = 0
        for s in sorted_spans:
            if s.end <= last_end:
                continue
            start = max(s.start, last_end)
            covered += s.end - start
            last_end = s.end
        return min(covered / self.total_bytes(), 1.0)

    def find_gaps(self, sorted_spans: List[ByteSpan]) -> List[Tuple[int, int]]:
        """Find byte ranges not covered by sorted non-overlapping spans."""
        gaps = []
        pos = 0
        for s in sorted_spans:
            if s.start > pos:
                gaps.append((pos, s.start))
            pos = max(pos, s.end)
        if pos < self.total_bytes():
            gaps.append((pos, self.total_bytes()))
        return gaps

    def serialize_spans(self, spans: List[ByteSpan]) -> list:
        return [s.to_dict() for s in spans]
