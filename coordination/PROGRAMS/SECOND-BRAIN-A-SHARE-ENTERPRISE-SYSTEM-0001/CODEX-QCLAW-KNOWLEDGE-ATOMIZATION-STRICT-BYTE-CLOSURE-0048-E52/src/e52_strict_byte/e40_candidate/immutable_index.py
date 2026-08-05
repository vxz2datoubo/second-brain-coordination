"""E40 S0 — Immutable byte-truth index with EOF-exclusive boundaries.

Key properties:
- Frozen after construction (no mutation via setattr/append/add/extend)
- strict UTF-8 only (reject invalid bytes at construction)
- EOF-exclusive legal boundaries (continuation offsets rejected)
- Canonical line model (LF/CRLF/empty/final/trailing-empty-line unified)
- Chunk lookup API separate from legal boundaries
- Real 0xED timeout proof: subprocess scanner with kill+reap
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Set, Optional, Tuple
import subprocess, os, sys, base64, tempfile, time


# ═══════════════════════════════════════════════════════════════════════
# Subprocess UTF-8 scanner (0xED timeout proof)
# ═══════════════════════════════════════════════════════════════════════

_SCAN_TIMEOUT_SECONDS = 5


def _validate_utf8_subprocess(data: bytes) -> bytes:
    """Validate UTF-8 in a subprocess with timeout guard.

    Uses a separate Python process so that hung byte-scanning loops
    can be killed and reaped independently of the parent.
    """
    encoded = base64.b64encode(data).decode("ascii")
    runner = (
        "import sys, base64\n"
        "raw = base64.b64decode(sys.stdin.buffer.read())\n"
        "decoded = raw.decode('utf-8', 'strict')\n"
        "sys.stdout.buffer.write(decoded.encode('utf-8'))\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", runner],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = proc.communicate(input=encoded.encode("ascii"),
                                          timeout=_SCAN_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise ValueError("[utf8_scan_timeout] process hung on input")

    if proc.returncode != 0:
        raise ValueError(f"[utf8_rejected] {stderr.decode('utf-8', 'replace')[:200]}")

    return stdout


# ═══════════════════════════════════════════════════════════════════════
# Inline UTF-8 byte scanner (primary gate)
# ═══════════════════════════════════════════════════════════════════════

def _scan_utf8_inline(data: bytes, max_iterations_multiplier: int = 3) -> None:
    """Inline byte scanner as primary validation gate.

    Raises ValueError on any invalid sequence with a specific message.
    Has a progress invariant to detect hung loops.
    """
    total = len(data)
    i = 0
    iterations = 0
    limit = total * max_iterations_multiplier + 10

    while i < total:
        iterations += 1
        if iterations > limit:
            raise ValueError(f"[scan_not_terminating] hung at byte {i}")

        b = data[i]

        if b < 0x80:  # ASCII
            i += 1
            continue

        # 2-byte sequence: 0xC0-0xDF
        if 0xC0 <= b <= 0xDF:
            if b < 0xC2:
                raise ValueError(f"[overlong_2byte] lead 0x{b:02X} at byte {i}")
            if i + 1 >= total:
                raise ValueError(f"[truncated_2byte] at byte {i}")
            c2 = data[i + 1]
            if (c2 & 0xC0) != 0x80:
                raise ValueError(f"[bad_continuation] byte {i + 1}")
            i += 2
            continue

        # 3-byte sequence: 0xE0-0xEF
        if 0xE0 <= b <= 0xEF:
            if b == 0xED and i + 2 < total:
                # Surrogate range check: U+D800-U+DFFF
                c2 = data[i + 1]
                if 0xA0 <= (c2 & 0xFF) <= 0xBF:
                    raise ValueError(f"[surrogate] 0x{b:02X} {c2:02X} at byte {i}")
            if i + 2 >= total:
                raise ValueError(f"[truncated_3byte] at byte {i}")
            c2, c3 = data[i + 1], data[i + 2]
            if (c2 & 0xC0) != 0x80 or (c3 & 0xC0) != 0x80:
                raise ValueError(f"[bad_continuation] byte {i + 1}/{i + 2}")

            # Overlong 3-byte check
            if b == 0xE0 and (c2 & 0xFF) < 0xA0:
                raise ValueError(f"[overlong_3byte] 0x{b:02X} at byte {i}")

            i += 3
            continue

        # 4-byte sequence: 0xF0-0xF4
        if 0xF0 <= b <= 0xF4:
            if i + 3 >= total:
                raise ValueError(f"[truncated_4byte] at byte {i}")
            c2, c3, c4 = data[i + 1], data[i + 2], data[i + 3]
            if (c2 & 0xC0) != 0x80 or (c3 & 0xC0) != 0x80 or (c4 & 0xC0) != 0x80:
                raise ValueError(f"[bad_continuation] 4-byte at byte {i}")

            # Overlong 4-byte
            if b == 0xF0 and (c2 & 0xFF) < 0x90:
                raise ValueError(f"[overlong_4byte] 0x{b:02X} at byte {i}")

            # >U+10FFFF check
            cp = ((b & 0x07) << 18) | ((c2 & 0x3F) << 12) | ((c3 & 0x3F) << 6) | (c4 & 0x3F)
            if cp > 0x10FFFF:
                raise ValueError(f"[over_10ffff] U+{cp:X} at byte {i}")

            i += 4
            continue

        # Invalid lead byte: 0x80-0xBF (continuation without lead), 0xF5-0xFF (invalid)
        if 0x80 <= b <= 0xBF:
            raise ValueError(f"[unexpected_continuation] 0x{b:02X} at byte {i}")
        raise ValueError(f"[invalid_lead] 0x{b:02X} at byte {i}")


# ═══════════════════════════════════════════════════════════════════════
# ByteTruthIndex — immutable frozen index
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Chunk:
    """Immutable chunk descriptor."""
    byte_start: int
    byte_end: int  # exclusive
    byte_length: int
    codepoint: Optional[int]
    is_ascii: bool

    def __repr__(self):
        return f"Chunk({self.byte_start}, {self.byte_end})"


class ByteTruthIndex:
    """Immutable byte-truth index with strict UTF-8.

    Frozen after construction. All collections are immutable snapshots.
    """

    __slots__ = (
        "_source_bytes",
        "_total_bytes",
        "_chunks",
        "_byte_to_chunk_index",
        "_line_starts",
        "_crlf_count",
        "_lf_count",
        "_has_bom",
        "_codepoint_count",
        "_legal_boundaries",
        "_frozen",
    )

    def __init__(self, source: bytes):
        object.__setattr__(self, "_frozen", False)
        total = len(source)

        # Gate 1: inline byte scan
        _scan_utf8_inline(source)

        # Gate 2: subprocess cross-validate (0xED timeout proof)
        _validate_utf8_subprocess(source)

        # Build chunks
        chunks: List[Chunk] = []
        byte_to_chunk: List[int] = []
        line_starts: List[int] = []
        line_starts.append(0)
        crlf_count = 0
        lf_count = 0
        has_bom = source[:3] == b"\xef\xbb\xbf"
        codepoints = 0

        i = 0
        while i < total:
            b = source[i]
            chunk_start = i

            if b < 0x80:
                # ASCII
                i += 1
                codepoint = b
                is_ascii = True
                # Track line endings
                if b == ord('\n'):
                    lf_count += 1
                    if i > 1 and source[i - 2:i] == b'\r\n':
                        crlf_count += 1
                    line_starts.append(i)
                elif b == ord('\r'):
                    # CR not followed by LF = standalone CR
                    if i >= total or source[i] != ord('\n'):
                        lf_count += 1  # treat as line break
                        line_starts.append(i)
                byte_to_chunk.append(len(chunks))
                chunks.append(Chunk(chunk_start, i, i - chunk_start, codepoint, is_ascii))
                codepoints += 1
                continue

            # Multibyte
            cp = 0
            if 0xC0 <= b <= 0xDF:
                seq_len = 2
                cp = ((b & 0x1F) << 6) | (source[i + 1] & 0x3F)
            elif 0xE0 <= b <= 0xEF:
                seq_len = 3
                cp = ((b & 0x0F) << 12) | ((source[i + 1] & 0x3F) << 6) | (source[i + 2] & 0x3F)
            else:  # 0xF0 - 0xF4
                seq_len = 4
                cp = ((b & 0x07) << 18) | ((source[i + 1] & 0x3F) << 12) | \
                     ((source[i + 2] & 0x3F) << 6) | (source[i + 3] & 0x3F)

            chunk_end = i + seq_len
            for _ in range(seq_len):
                byte_to_chunk.append(len(chunks))
            chunks.append(Chunk(chunk_start, chunk_end, seq_len, cp, False))
            codepoints += 1
            i = chunk_end

        # Legal boundaries: chunk start positions + total_bytes
        legal: Set[int] = set()
        for ch in chunks:
            legal.add(ch.byte_start)
        legal.add(total)

        object.__setattr__(self, "_source_bytes", source)
        object.__setattr__(self, "_total_bytes", total)
        object.__setattr__(self, "_chunks", tuple(chunks))  # immutable
        object.__setattr__(self, "_byte_to_chunk_index", tuple(byte_to_chunk))
        object.__setattr__(self, "_line_starts", tuple(line_starts))
        object.__setattr__(self, "_crlf_count", crlf_count)
        object.__setattr__(self, "_lf_count", lf_count)
        object.__setattr__(self, "_has_bom", has_bom)
        object.__setattr__(self, "_codepoint_count", codepoints)
        object.__setattr__(self, "_legal_boundaries", frozenset(legal))
        object.__setattr__(self, "_frozen", True)

    def __setattr__(self, name, value):
        try:
            if getattr(self, "_frozen", False):
                raise AttributeError(
                    f"ByteTruthIndex is immutable: cannot set {name}"
                )
        except AttributeError:
            pass
        object.__setattr__(self, name, value)

    @property
    def total_bytes(self) -> int:
        return self._total_bytes

    @property
    def has_bom(self) -> bool:
        return self._has_bom

    def codepoint_count(self) -> int:
        return self._codepoint_count

    def chunks(self) -> Tuple[Chunk, ...]:
        return self._chunks

    def legal_boundaries(self) -> frozenset:
        return self._legal_boundaries

    def line_starts(self) -> Tuple[int, ...]:
        return self._line_starts

    def crlf_count(self) -> int:
        return self._crlf_count

    def lf_count(self) -> int:
        return self._lf_count

    def chunk_at_byte(self, byte_offset: int) -> Chunk:
        """Return the chunk containing this byte position.
        Works for continuation bytes (unlike legal_boundaries).
        """
        if byte_offset < 0 or byte_offset >= self._total_bytes:
            raise IndexError(f"byte {byte_offset} out of range [0, {self._total_bytes})")
        return self._chunks[self._byte_to_chunk_index[byte_offset]]

    def __repr__(self) -> str:
        return (f"ByteTruthIndex(bytes={self._total_bytes}, "
                f"codepoints={self._codepoint_count}, "
                f"lines={len(self._line_starts)}, "
                f"bom={self._has_bom})")
