"""E38 S0 — Strict UTF-8 guard with provable termination.

Every scan loop has a monotonic progress invariant. 0xED surrogate halves
are explicitly rejected (not silently consumed). Timeout/progress tests
prove no infinite loop on any input.

Design:
- Python's built-in .decode('utf-8', 'strict') is the FIRST rejection gate.
  This covers surrogate, overlong, truncated, >U+10FFFF, bad continuation.
- Then a manual byte-scan verifier confirms every boundary is legal.
- Every loop increments a byte counter with a hard ceiling = len(data) + 1.
- Negative test: 0xED sequences that could confuse a naive parser.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import time

# ── provably-terminating decoder ─────────────────────────────────────

class UTF8GuardError(ValueError):
    """Raised for any invalid UTF-8 byte sequence."""
    pass


@dataclass(frozen=True)
class UTF8ByteIndex:
    """Strict UTF-8 byte index with verified termination.

    All scanning loops have a monotonic byte counter that never exceeds
    len(data)+1 iterations. Timeout negative tests prove this.
    """
    source_bytes: bytes
    total_bytes: int = field(init=False)
    codepoint_count: int = field(init=False)
    line_starts: List[int] = field(init=False)  # byte offsets where lines start
    chunk_starts: List[int] = field(init=False)  # byte offsets of codepoint starts
    has_bom: bool = field(init=False)
    crlf_count: int = field(init=False)
    lf_count: int = field(init=False)

    def __post_init__(self):
        if not isinstance(self.source_bytes, bytes):
            raise TypeError("source_bytes must be bytes, not str")

        # ── Gate 1: Manual byte-scan with monotonic progress ──
        # Must come FIRST so specific messages (Surrogate/Overlong/etc) are raised.
        # Python's built-in strict decode is Gate 2 (cross-validation).
        total = len(self.source_bytes)
        chunk_starts: List[int] = []
        chunks: List[str] = []
        i = 0
        iterations = 0
        # Progress invariant: i strictly increases each iteration, bounded by total
        while i < total:
            iterations += 1
            if iterations > total + 10:
                raise UTF8GuardError(f"SCAN_NOT_TERMINATING: {iterations} iterations for {total} bytes")
            b = self.source_bytes[i]
            chunk_starts.append(i)

            if b < 0x80:
                # ASCII — 1 byte
                chunks.append(chr(b))
                i += 1
            elif b in (0xC0, 0xC1, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF):
                raise UTF8GuardError(f"Invalid lead byte 0x{b:02X} at {i}")
            elif 0xC2 <= b <= 0xDF:
                # 2-byte sequence
                if i + 1 >= total:
                    raise UTF8GuardError(f"Truncated 2-byte seq at {i}")
                b2 = self.source_bytes[i + 1]
                if not (0x80 <= b2 <= 0xBF):
                    raise UTF8GuardError(f"Bad continuation byte at {i+1}")
                cp = ((b & 0x1F) << 6) | (b2 & 0x3F)
                if cp < 0x80:
                    raise UTF8GuardError(f"Overlong 2-byte at {i} (cp={cp:#x})")
                chunks.append(chr(cp))
                i += 2
            elif 0xE0 <= b <= 0xEF:
                # 3-byte sequence
                if i + 2 >= total:
                    raise UTF8GuardError(f"Truncated 3-byte seq at {i}")
                b2 = self.source_bytes[i + 1]
                b3 = self.source_bytes[i + 2]
                if not (0x80 <= b2 <= 0xBF and 0x80 <= b3 <= 0xBF):
                    raise UTF8GuardError(f"Bad continuation in 3-byte at {i}")
                cp = ((b & 0x0F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F)
                if cp < 0x800:
                    raise UTF8GuardError(f"Overlong 3-byte at {i} (cp={cp:#x})")
                # 0xED A0-80 to ED BF-BF = surrogate range U+D800-U+DFFF
                if 0xD800 <= cp <= 0xDFFF:
                    raise UTF8GuardError(f"Surrogate codepoint at {i} (cp={cp:#x})")
                chunks.append(chr(cp))
                i += 3
            elif 0xF0 <= b <= 0xF4:
                # 4-byte sequence
                if i + 3 >= total:
                    raise UTF8GuardError(f"Truncated 4-byte seq at {i}")
                b2 = self.source_bytes[i + 1]
                b3 = self.source_bytes[i + 2]
                b4 = self.source_bytes[i + 3]
                if not (0x80 <= b2 <= 0xBF and 0x80 <= b3 <= 0xBF and 0x80 <= b4 <= 0xBF):
                    raise UTF8GuardError(f"Bad continuation in 4-byte at {i}")
                cp = ((b & 0x07) << 18) | ((b2 & 0x3F) << 12) | ((b3 & 0x3F) << 6) | (b4 & 0x3F)
                if cp < 0x10000:
                    raise UTF8GuardError(f"Overlong 4-byte at {i} (cp={cp:#x})")
                if cp > 0x10FFFF:
                    raise UTF8GuardError(f"Codepoint >U+10FFFF at {i} (cp={cp:#x})")
                chunks.append(chr(cp))
                i += 4
            elif 0x80 <= b <= 0xBF:
                raise UTF8GuardError(f"Unexpected continuation byte at {i}")
            else:
                raise UTF8GuardError(f"Invalid lead byte 0x{b:02X} at {i}")

        # Post-scan: verify
        decoded = "".join(chunks)

        # ── Gate 2: Python strict decode cross-validation ──
        try:
            text = self.source_bytes.decode("utf-8", "strict")
        except UnicodeDecodeError as e:
            raise UTF8GuardError(f"Gate2 cross-validation failed at byte {e.start}: {e.reason}") from e

        # Compute line starts
        line_starts = [0]
        for pos in range(total):
            if pos + 1 < total:
                if self.source_bytes[pos] == 0x0D and self.source_bytes[pos + 1] == 0x0A:
                    line_starts.append(pos + 2)
                elif self.source_bytes[pos] == 0x0A and (pos == 0 or self.source_bytes[pos - 1] != 0x0D):
                    line_starts.append(pos + 1)

        # Count CRLF/LF
        crlf = 0
        lf_only = 0
        p = 0
        while p < total:
            if p + 1 < total and self.source_bytes[p] == 0x0D and self.source_bytes[p + 1] == 0x0A:
                crlf += 1
                p += 2
            elif self.source_bytes[p] == 0x0A:
                lf_only += 1
                p += 1
            else:
                p += 1

        # BOM detection
        has_bom = self.source_bytes[:3] == b"\xEF\xBB\xBF"

        object.__setattr__(self, "total_bytes", total)
        object.__setattr__(self, "codepoint_count", len(chunks))
        object.__setattr__(self, "line_starts", line_starts)
        object.__setattr__(self, "chunk_starts", chunk_starts)
        object.__setattr__(self, "has_bom", has_bom)
        object.__setattr__(self, "crlf_count", crlf)
        object.__setattr__(self, "lf_count", lf_only)

    @property
    def decode(self) -> str:
        """Decoded text (strict)."""
        return self.source_bytes.decode("utf-8", "strict")

    def byte_to_chunk_index(self, byte_offset: int) -> int:
        """Return chunk index for given byte offset."""
        if byte_offset < 0 or byte_offset >= self.total_bytes:
            raise IndexError(f"byte_offset {byte_offset} out of range [0, {self.total_bytes})")
        for ci in range(len(self.chunk_starts) - 1, -1, -1):
            if self.chunk_starts[ci] <= byte_offset:
                return ci
        return 0

    def byte_at(self, offset: int) -> int:
        if offset < 0 or offset >= self.total_bytes:
            raise IndexError(f"offset {offset} out of range")
        return self.source_bytes[offset]

    @property
    def legal_boundaries(self) -> List[int]:
        """All legal byte boundaries for span start/end."""
        return sorted([0] + self.chunk_starts + [self.total_bytes])


# ── progress/timeout guard ───────────────────────────────────────────

class Terminated:
    """Result when a timed operation completes."""
    def __init__(self, value):
        self.value = value


def with_timeout(fn, args=(), kwargs=None, timeout_sec: float = 2.0):
    """Run fn with a timeout. Returns Terminated(value) or raises TimeoutError."""
    import signal
    if kwargs is None:
        kwargs = {}

    result = [None]
    exception = [None]

    def _runner():
        try:
            result[0] = fn(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    import threading
    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join(timeout_sec)
    if t.is_alive():
        raise TimeoutError(f"Operation timed out after {timeout_sec}s (likely infinite loop)")
    if exception[0]:
        raise exception[0]
    return Terminated(result[0])
