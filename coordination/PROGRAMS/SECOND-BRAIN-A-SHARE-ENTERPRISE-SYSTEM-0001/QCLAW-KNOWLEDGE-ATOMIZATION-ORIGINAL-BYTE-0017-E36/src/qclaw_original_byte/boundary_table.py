"""E36 S0 — OriginalByteIndex: strict UTF-8 boundary table on immutable source bytes.
Accepts arbitrary bytes. Rejects invalid strict UTF-8 BEFORE building the table.
Chunk granularity at UTF-8 codepoint boundaries. Handles BOM, combining chars."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set
import unicodedata


def is_valid_strict_utf8(data: bytes) -> bool:
    """Reject overlongs, surrogates, and byte sequences > U+10FFFF."""
    i = 0
    n = len(data)
    while i < n:
        b0 = data[i]
        # ASCII
        if b0 <= 0x7F:
            i += 1
            continue
        # 2-byte: 110xxxxx 10xxxxxx
        if 0xC2 <= b0 <= 0xDF:
            if i + 1 >= n:
                return False
            b1 = data[i + 1]
            if (b1 & 0xC0) != 0x80:
                return False
            cp = ((b0 & 0x1F) << 6) | (b1 & 0x3F)
            if cp < 0x80:  # overlong
                return False
            i += 2
            continue
        # 3-byte: 1110xxxx 10xxxxxx 10xxxxxx
        if 0xE0 <= b0 <= 0xEF:
            if i + 2 >= n:
                return False
            b1, b2 = data[i + 1], data[i + 2]
            if (b1 & 0xC0) != 0x80 or (b2 & 0xC0) != 0x80:
                return False
            cp = ((b0 & 0x0F) << 12) | ((b1 & 0x3F) << 6) | (b2 & 0x3F)
            if b0 == 0xE0 and cp < 0x800:  # overlong
                return False
            if 0xD800 <= cp <= 0xDFFF:  # surrogates
                return False
            i += 3
            continue
        # 4-byte: 11110xxx 10xxxxxx 10xxxxxx 10xxxxxx
        if 0xF0 <= b0 <= 0xF4:
            if i + 3 >= n:
                return False
            b1, b2, b3 = data[i + 1], data[i + 2], data[i + 3]
            if (b1 & 0xC0) != 0x80 or (b2 & 0xC0) != 0x80 or (b3 & 0xC0) != 0x80:
                return False
            cp = ((b0 & 0x07) << 18) | ((b1 & 0x3F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F)
            if b0 == 0xF0 and cp < 0x10000:  # overlong
                return False
            if cp > 0x10FFFF:  # beyond Unicode
                return False
            i += 4
            continue
        # Invalid leading byte
        return False
    return True


@dataclass(frozen=True)
class Chunk:
    """One boundary-table entry: byte range + codepoint range + line."""
    idx: int           # chunk index (0-based)
    byte_start: int    # inclusive
    byte_end: int      # exclusive
    cp_start: int      # codepoint start
    cp_end: int        # codepoint end (exclusive)
    line: int          # 0-based line
    is_eol: bool = False
    is_bom: bool = False

    def byte_len(self) -> int:
        return self.byte_end - self.byte_start

    def cp_len(self) -> int:
        return self.cp_end - self.cp_start


@dataclass
class OriginalByteIndex:
    """Immutable boundary table on original UTF-8 bytes.
    Built ONLY after strict UTF-8 validation succeeds."""

    source_bytes: bytes
    chunks: List[Chunk] = field(default_factory=list)
    line_breaks: List[int] = field(default_factory=list)  # byte positions of '\n'
    total_bytes: int = 0
    total_codepoints: int = 0
    total_lines: int = 0
    has_bom: bool = False
    is_crlf: bool = False

    @classmethod
    def from_bytes(cls, data: bytes) -> "OriginalByteIndex":
        if not is_valid_strict_utf8(data):
            raise ValueError("Input bytes are not valid strict UTF-8")

        idx = cls(source_bytes=data)
        idx._build()
        return idx

    @classmethod
    def from_string(cls, text: str) -> "OriginalByteIndex":
        return cls.from_bytes(text.encode("utf-8"))

    def _build(self):
        data = self.source_bytes
        n = len(data)
        self.chunks = []
        self.line_breaks = []
        pos_byte = 0
        pos_cp = 0
        line = 0

        # Check BOM
        if n >= 3 and data[:3] == b'\xEF\xBB\xBF':
            self.has_bom = True
            self.chunks.append(Chunk(idx=0, byte_start=0, byte_end=3,
                                     cp_start=0, cp_end=1, line=0, is_bom=True))
            pos_byte = 3
            pos_cp = 1

        # Check CRLF early
        if b'\r\n' in data:
            self.is_crlf = True

        chunk_idx = 1 if self.has_bom else 0

        while pos_byte < n:
            b0 = data[pos_byte]
            cp_len = 1  # bytes for this codepoint

            if b0 <= 0x7F:
                cp_len = 1
            elif 0xC2 <= b0 <= 0xDF:
                cp_len = 2
            elif 0xE0 <= b0 <= 0xEF:
                cp_len = 3
            elif 0xF0 <= b0 <= 0xF4:
                cp_len = 4

            byte_end = pos_byte + cp_len
            is_eol = (data[pos_byte] == 0x0A)  # \n

            # Handle CRLF: skip \r before \n
            if is_eol and pos_byte > 0 and data[pos_byte - 1] == 0x0D:
                # Merge CR+LF into one chunk
                if self.chunks and self.chunks[-1].byte_end == pos_byte:
                    last = self.chunks[-1]
                    # Replace last chunk with merged CRLF
                    self.chunks[-1] = Chunk(
                        idx=last.idx,
                        byte_start=last.byte_start,
                        byte_end=byte_end,
                        cp_start=last.cp_start,
                        cp_end=last.cp_end + 1,  # CR counted already
                        line=last.line,
                        is_eol=True
                    )
                else:
                    self.chunks.append(Chunk(
                        idx=chunk_idx, byte_start=pos_byte - 1, byte_end=byte_end,
                        cp_start=pos_cp - 1, cp_end=pos_cp + 1, line=line, is_eol=True
                    ))
                pos_byte = byte_end
                pos_cp += 1
                self.line_breaks.append(pos_byte)
                line += 1
                chunk_idx += 1
                continue

            self.chunks.append(Chunk(
                idx=chunk_idx,
                byte_start=pos_byte,
                byte_end=byte_end,
                cp_start=pos_cp,
                cp_end=pos_cp + 1,
                line=line,
                is_eol=is_eol
            ))
            if is_eol:
                self.line_breaks.append(byte_end)
                line += 1

            pos_byte = byte_end
            pos_cp += 1
            chunk_idx += 1

        self.total_bytes = n
        self.total_codepoints = pos_cp
        self.total_lines = line + (0 if n > 0 and data[-1:] != b'\n' else 0)
        if n > 0 and data[-1:] != b'\n':
            self.total_lines += 1

    def chunk_at_byte(self, byte_offset: int) -> Optional[Chunk]:
        for c in self.chunks:
            if c.byte_start <= byte_offset < c.byte_end:
                return c
        return None

    def chunk_at_cp(self, cp_offset: int) -> Optional[Chunk]:
        for c in self.chunks:
            if c.cp_start <= cp_offset < c.cp_end:
                return c
        return None

    @property
    def boundary_bytes(self) -> Set[int]:
        """Return all legal byte boundaries (valid chunk edges)."""
        b = {0, self.total_bytes}
        for c in self.chunks:
            b.add(c.byte_start)
            b.add(c.byte_end)
        return b
