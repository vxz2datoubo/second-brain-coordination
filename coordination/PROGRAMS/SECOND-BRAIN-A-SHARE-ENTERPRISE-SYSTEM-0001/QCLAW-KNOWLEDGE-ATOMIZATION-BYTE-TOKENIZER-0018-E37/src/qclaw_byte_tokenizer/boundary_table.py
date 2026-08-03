"""E37 S0 — Immutable strict-UTF-8 byte/codepoint/line boundary table.

Production entry accepts bytes; rejects invalid strict UTF-8 before any parsing.
All boundary data is immutable after construction (frozen=True).
Exposes: chunks (tuple), total_bytes, total_codepoints, total_lines,
byte_to_chunk_index(), byte_to_line(), byte_to_codepoint(), codepoint_to_byte().

Chunk kind: BOM | ASCII | CJK | EMOJI | COMBINING | EOL | SPACE | EMOJI_ZWJ
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, List, Optional
import struct


# ── strict UTF-8 validation ──────────────────────────────────────────
def _validate_strict_utf8(data: bytes) -> None:
    """Raise ValueError if data is not valid strict UTF-8.

    Strict: rejects overlong sequences, surrogates, >U+10FFFF, and non-shortest forms.
    """
    i, n = 0, len(data)
    while i < n:
        b0 = data[i]
        if b0 <= 0x7F:
            i += 1
            continue
        if 0xC2 <= b0 <= 0xDF:
            if i + 1 >= n:
                raise ValueError(f"Truncated 2-byte sequence at byte {i}")
            b1 = data[i + 1]
            if not (0x80 <= b1 <= 0xBF):
                raise ValueError(f"Invalid continuation byte 0x{b1:02X} at byte {i+1}")
            cp = ((b0 & 0x1F) << 6) | (b1 & 0x3F)
            if cp < 0x80:
                raise ValueError(f"Overlong 2-byte for U+{cp:04X} at byte {i}")
            i += 2
            continue
        if b0 == 0xE0:
            if i + 2 >= n:
                raise ValueError(f"Truncated 3-byte sequence at byte {i}")
            b1, b2 = data[i + 1], data[i + 2]
            if not (0x80 <= b2 <= 0xBF):
                raise ValueError(f"Invalid 3-byte continuation at byte {i}")
            if b1 < 0x80 or b1 > 0xBF:
                raise ValueError(f"Invalid E0 continuation at byte {i}")
            if b1 < 0xA0:
                raise ValueError(f"Overlong E0 for U+{(0x0000):04X} at byte {i}")
            cp = ((b0 & 0x0F) << 12) | ((b1 & 0x3F) << 6) | (b2 & 0x3F)
            if cp < 0x800:
                raise ValueError(f"Overlong E0 for U+{cp:04X} at byte {i}")
            i += 3
            continue
        if 0xE1 <= b0 <= 0xEC or b0 in (0xEE, 0xEF):
            if i + 2 >= n:
                raise ValueError(f"Truncated 3-byte sequence at byte {i}")
            b1, b2 = data[i + 1], data[i + 2]
            if not (0x80 <= b1 <= 0xBF and 0x80 <= b2 <= 0xBF):
                raise ValueError(f"Invalid 3-byte continuation at byte {i}")
            cp = ((b0 & 0x0F) << 12) | ((b1 & 0x3F) << 6) | (b2 & 0x3F)
            if b0 == 0xED:
                if cp >= 0xD800 and cp <= 0xDFFF:
                    raise ValueError(f"Surrogate U+{cp:04X} at byte {i}")
            i += 3
            continue
        if b0 == 0xF0:
            if i + 3 >= n:
                raise ValueError(f"Truncated 4-byte sequence at byte {i}")
            b1, b2, b3 = data[i + 1], data[i + 2], data[i + 3]
            if not (0x80 <= b2 <= 0xBF and 0x80 <= b3 <= 0xBF):
                raise ValueError(f"Invalid 4-byte continuation at byte {i}")
            if b1 < 0x80 or b1 > 0xBF:
                raise ValueError(f"Invalid F0 continuation at byte {i}")
            if b1 < 0x90:
                raise ValueError(f"Overlong F0 at byte {i}")
            cp = ((b0 & 0x07) << 18) | ((b1 & 0x3F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F)
            if cp > 0x10FFFF:
                raise ValueError(f"Codepoint >U+10FFFF at byte {i}")
            i += 4
            continue
        if 0xF1 <= b0 <= 0xF3:
            if i + 3 >= n:
                raise ValueError(f"Truncated 4-byte sequence at byte {i}")
            b1, b2, b3 = data[i + 1], data[i + 2], data[i + 3]
            if not (0x80 <= b1 <= 0xBF and 0x80 <= b2 <= 0xBF and 0x80 <= b3 <= 0xBF):
                raise ValueError(f"Invalid 4-byte continuation at byte {i}")
            cp = ((b0 & 0x07) << 18) | ((b1 & 0x3F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F)
            if cp > 0x10FFFF:
                raise ValueError(f"Codepoint >U+10FFFF at byte {i}")
            i += 4
            continue
        if b0 == 0xF4:
            if i + 3 >= n:
                raise ValueError(f"Truncated 4-byte sequence at byte {i}")
            b1, b2, b3 = data[i + 1], data[i + 2], data[i + 3]
            if not (0x80 <= b1 <= 0xBF and 0x80 <= b2 <= 0xBF and 0x80 <= b3 <= 0xBF):
                raise ValueError(f"Invalid F4 continuation at byte {i}")
            cp = ((b0 & 0x07) << 18) | ((b1 & 0x3F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F)
            if cp > 0x10FFFF:
                raise ValueError(f"Codepoint >U+10FFFF at byte {i}")
            i += 4
            continue
        if 0x80 <= b0 <= 0xBF:
            raise ValueError(f"Unexpected continuation byte 0x{b0:02X} at byte {i}")
        if b0 in (0xC0, 0xC1):
            raise ValueError(f"Overlong lead byte 0x{b0:02X} at byte {i}")
        if b0 in (0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF):
            raise ValueError(f"Invalid byte 0x{b0:02X} at byte {i}")


# ── chunk types ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class Chunk:
    byte_start: int
    byte_end: int  # exclusive
    codepoint: int
    byte_len: int
    cp_index: int  # 0-based codepoint index
    codepoint_value: int  # Unicode scalar value
    kind: str  # BOM|ASCII|SPACE|CJK|EMOJI|COMBINING|EOL|EMOJI_ZWJ
    is_bom: bool = False
    is_crlf: bool = False

    @property
    def boundary_byte(self) -> int:
        """The byte offset immediately AFTER this chunk (== byte_end)."""
        return self.byte_end


# ── OriginalByteIndex ────────────────────────────────────────────────
class OriginalByteIndex:
    """Immutable table mapping byte↔codepoint↔line for valid strict UTF-8."""

    __slots__ = ("_source_bytes", "_chunks", "_total_bytes", "_total_codepoints",
                 "_total_lines", "_byte_to_chunk", "_line_starts",
                 "_leading_bom", "_frozen")

    def __init__(self, source_bytes: bytes):
        _validate_strict_utf8(source_bytes)
        # Bypass __setattr__ freeze check during init
        object.__setattr__(self, '_frozen', False)
        object.__setattr__(self, '_source_bytes', source_bytes)
        object.__setattr__(self, '_total_bytes', len(source_bytes))

        chunks: List[Chunk] = []
        byte_to_chunk: List[int] = []  # byte offset → chunk index
        line_starts: List[int] = [0]
        leading_bom = False

        i = 0
        cp_idx = 0
        while i < self._total_bytes:
            b0 = source_bytes[i]
            if b0 <= 0x7F:
                if b0 == 0x0A:  # LF
                    kind = "EOL"
                    is_crlf = False
                elif b0 == 0x20:
                    kind = "SPACE"
                    is_crlf = False
                else:
                    kind = "BOM" if b0 == 0xEF and cp_idx == 0 else "ASCII"
                    is_crlf = False
                chunk = Chunk(i, i + 1, cp_idx, 1, cp_idx, b0, kind, is_bom=(b0 == 0xEF and cp_idx == 0), is_crlf=False)
                # Detect BOM
                if b0 == 0xEF and i + 2 < self._total_bytes:
                    if source_bytes[i:i+3] == b'\xEF\xBB\xBF':
                        pass  # BOM handled below as 3-byte
                if b0 == 0x0D:  # CR
                    if i + 1 < self._total_bytes and source_bytes[i + 1] == 0x0A:
                        # CRLF — merge into one EOL chunk
                        chunk = Chunk(i, i + 2, cp_idx, 2, cp_idx, 0x0D0A, "EOL", is_crlf=True)
                        for _ in range(2):
                            byte_to_chunk.append(len(chunks))
                        chunks.append(chunk)
                        line_starts.append(i + 2)
                        cp_idx += 1
                        i += 2
                        continue
                # Regular LF or other ASCII
                for _ in range(1):
                    byte_to_chunk.append(len(chunks))
                chunks.append(chunk)
                if chunk.kind == "EOL" and not chunk.is_crlf:
                    line_starts.append(i + 1)
                i += 1
                cp_idx += 1
                if chunk.is_bom:
                    leading_bom = True
                continue

            if 0xC2 <= b0 <= 0xDF:
                end = i + 2
                cp_val = ((b0 & 0x1F) << 6) | (source_bytes[i + 1] & 0x3F)
                kind = "ASCII" if cp_val < 0x100 else "CJK" if (0x4E00 <= cp_val <= 0x9FFF or 0x3400 <= cp_val <= 0x4DBF) else "COMBINING" if _is_combining(cp_val) else "CJK"
            elif 0xE0 <= b0 <= 0xEF:
                end = i + 3
                cp_val = ((b0 & 0x0F) << 12) | ((source_bytes[i + 1] & 0x3F) << 6) | (source_bytes[i + 2] & 0x3F)
                kind = _classify(cp_val, source_bytes, i, end)
            elif 0xF0 <= b0 <= 0xF4:
                end = i + 4
                cp_val = ((b0 & 0x07) << 18) | ((source_bytes[i + 1] & 0x3F) << 12) | ((source_bytes[i + 2] & 0x3F) << 6) | (source_bytes[i + 3] & 0x3F)
                kind = _classify(cp_val, source_bytes, i, end)
            else:
                raise ValueError(f"Unreachable: byte 0x{b0:02X} at {i}")

            # BOM detection (EF BB BF at position 0)
            is_bom_flag = (i == 0 and source_bytes[i:end] == b'\xEF\xBB\xBF')
            if is_bom_flag:
                kind = "BOM"
                leading_bom = True

            chunk = Chunk(i, end, cp_idx, end - i, cp_idx, cp_val, kind, is_bom=is_bom_flag)
            for _ in range(end - i):
                byte_to_chunk.append(len(chunks))
            chunks.append(chunk)
            i = end
            cp_idx += 1

        # Remove duplicate line_starts
        line_starts = sorted(set(line_starts))

        self._chunks = tuple(chunks)
        self._byte_to_chunk = tuple(byte_to_chunk)
        self._total_codepoints = cp_idx
        self._total_lines = max(len(line_starts), 1)
        self._line_starts = tuple(line_starts)
        self._leading_bom = leading_bom

        # Lock immutability after construction
        object.__setattr__(self, '_frozen', True)

    @property
    def source_bytes(self) -> bytes:
        return self._source_bytes

    @property
    def chunks(self) -> Tuple[Chunk, ...]:
        return self._chunks

    @property
    def total_bytes(self) -> int:
        return self._total_bytes

    @property
    def total_codepoints(self) -> int:
        return self._total_codepoints

    @property
    def total_lines(self) -> int:
        return self._total_lines

    @property
    def line_starts(self) -> Tuple[int, ...]:
        return self._line_starts

    @property
    def leading_bom(self) -> bool:
        return self._leading_bom

    @property
    def legal_boundaries(self) -> Tuple[int, ...]:
        """All legal byte offsets where spans may start/end (chunk boundaries)."""
        boundaries = set()
        boundaries.add(0)
        for c in self._chunks:
            boundaries.add(c.byte_end)
        boundaries.add(self._total_bytes)
        return tuple(sorted(boundaries))

    def byte_to_chunk_index(self, byte_offset: int) -> int:
        """Chunk index for byte_offset (clamped: 0..total_bytes)."""
        if byte_offset <= 0:
            return 0
        if byte_offset >= self._total_bytes:
            return len(self._chunks) - 1 if self._chunks else 0
        return self._byte_to_chunk[byte_offset]

    def byte_to_line(self, byte_offset: int) -> int:
        """1-based line number for byte_offset."""
        for idx, ls in enumerate(self._line_starts):
            if byte_offset < ls:
                return idx
        return len(self._line_starts)

    def byte_to_codepoint(self, byte_offset: int) -> int:
        """Codepoint index for byte_offset (0-based)."""
        return self._chunks[self.byte_to_chunk_index(byte_offset)].cp_index

    def codepoint_to_byte(self, cp_index: int) -> int:
        """Byte offset of the first byte of codepoint cp_index (0-based)."""
        if cp_index < 0 or cp_index >= self._total_codepoints:
            raise IndexError(f"Codepoint index {cp_index} out of range [0, {self._total_codepoints})")
        # Binary search
        lo, hi = 0, len(self._chunks)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._chunks[mid].cp_index < cp_index:
                lo = mid + 1
            else:
                hi = mid
        return self._chunks[lo].byte_start

    def chunk_at_byte(self, byte_offset: int) -> Chunk:
        return self._chunks[self.byte_to_chunk_index(byte_offset)]

    def chunk_at_cp(self, cp_index: int) -> Chunk:
        byte = self.codepoint_to_byte(cp_index)
        return self.chunk_at_byte(byte)

    def __repr__(self) -> str:
        return (f"OriginalByteIndex(bytes={self._total_bytes}, cps={self._total_codepoints}, "
                f"lines={self._total_lines}, chunks={len(self._chunks)}, bom={self._leading_bom})")

    # Prevent mutation
    def __setattr__(self, name, value):
        if getattr(self, '_frozen', False):
            raise TypeError(f"OriginalByteIndex is immutable")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        raise TypeError(f"OriginalByteIndex is immutable")


# ── helpers ──────────────────────────────────────────────────────────
def _is_combining(cp: int) -> bool:
    """Check if cp is a Unicode combining mark."""
    return (0x0300 <= cp <= 0x036F or   # Combining Diacritical Marks
            0x1AB0 <= cp <= 0x1AFF or   # Combining Diacritical Marks Extended
            0x1DC0 <= cp <= 0x1DFF or   # Combining Diacritical Marks Supplement
            0x20D0 <= cp <= 0x20FF or   # Combining Diacritical Marks for Symbols
            0xFE20 <= cp <= 0xFE2F)     # Combining Half Marks


def _is_emoji(cp: int) -> bool:
    """Simple emoji range check."""
    return (0x1F300 <= cp <= 0x1F9FF or  # Misc Symbols, Emoticons, Supplemental
            0x2600 <= cp <= 0x27BF or     # Misc Symbols
            0x1F600 <= cp <= 0x1F64F or   # Emoticons
            0x1F680 <= cp <= 0x1F6FF or   # Transport
            0x1F900 <= cp <= 0x1F9FF or   # Supplemental Symbols
            0x2702 <= cp <= 0x27B0 or     # Dingbats
            cp == 0x200D)                 # ZWJ


def _is_zwj(following: bytes) -> bool:
    """Check if ZWJ (U+200D) follows immediately in bytes."""
    return following[:3] == b'\xE2\x80\x8D'


def _is_cjk(cp: int) -> bool:
    """CJK Unified Ideographs and extensions."""
    return (0x4E00 <= cp <= 0x9FFF or   # CJK Unified
            0x3400 <= cp <= 0x4DBF or   # CJK Extension A
            0x20000 <= cp <= 0x2A6DF)   # CJK Extension B


def _classify(cp: int, data: bytes, start: int, end: int) -> str:
    """Classify a codepoint into a chunk kind."""
    if cp == 0xFEFF:
        return "BOM"
    if _is_combining(cp):
        return "COMBINING"
    if cp == 0x200D:
        return "EMOJI_ZWJ"  # ZWJ itself
    if _is_emoji(cp):
        # Check if ZWJ follows (emoji ZWJ sequence)
        if end < len(data) and _is_zwj(data[end:]):
            return "EMOJI_ZWJ"
        return "EMOJI"
    if _is_cjk(cp):
        return "CJK"
    return "ASCII"
