"""E39 S0 — Process-timeout UTF-8 guard via subprocess isolation.

Design (shortest path to green):
- Manual byte-scan with internal iteration ceiling (iterations <= total+10).
- 0xED surrogate, overlong, truncated, >U+10FFFF all rejected explicitly.
- Python strict decode as Gate 2 cross-validation.
- Process-level timeout via subprocess.Popen + wait(timeout) → kill().
  This provides TRUE OS-level termination (Windows TerminateProcess).
- RED tests first: demonstrate thread-based timeout fails against CPU loops.
- GREEN tests: prove subprocess timeout + internal guard ensure termination.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import subprocess
import os
import sys


class UTF8GuardError(ValueError):
    """Raised for any invalid UTF-8 byte sequence."""
    pass


# ═══════════════════════════════════════════════════════════════════════
# Module-level run target for subprocess isolation
# ═══════════════════════════════════════════════════════════════════════

def _subprocess_runner(data: bytes) -> dict:
    """Entry point for subprocess-based timeout. Returns result dict via stdout JSON."""
    idx = UTF8ByteIndex(data)
    return {
        "total_bytes": idx.total_bytes,
        "codepoint_count": idx.codepoint_count,
        "has_bom": idx.has_bom,
        "crlf_count": idx.crlf_count,
        "lf_count": idx.lf_count,
        "chunk_starts_count": len(idx.chunk_starts),
        "line_starts_count": len(idx.line_starts),
    }


# ═══════════════════════════════════════════════════════════════════════
# Core types
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class UTF8ByteIndex:
    """Strict UTF-8 byte index with verified termination.

    Every scan loop has a monotonic iteration counter with hard ceiling
    (total_bytes + 10). This is the PRIMARY timeout guarantee — no external
    process needed for the scan itself.
    """
    source_bytes: bytes

    total_bytes: int = field(init=False)
    codepoint_count: int = field(init=False)
    line_starts: List[int] = field(init=False)
    chunk_starts: List[int] = field(init=False)
    has_bom: bool = field(init=False)
    crlf_count: int = field(init=False)
    lf_count: int = field(init=False)

    def __post_init__(self):
        if not isinstance(self.source_bytes, bytes):
            raise TypeError("source_bytes must be bytes, not str")
        total = len(self.source_bytes)

        # ── Gate 1: Manual byte-scan with iteration ceiling ──
        chunk_starts: List[int] = []
        i = 0
        iterations = 0
        while i < total:
            iterations += 1
            if iterations > total + 10:
                raise UTF8GuardError(
                    f"SCAN_NOT_TERMINATING: {iterations} iterations for {total} bytes"
                )
            b = self.source_bytes[i]
            chunk_starts.append(i)

            if b < 0x80:
                i += 1
            elif b in (0xC0, 0xC1, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF):
                raise UTF8GuardError(f"Invalid lead byte 0x{b:02X} at byte {i}")
            elif 0xC2 <= b <= 0xDF:
                if i + 1 >= total:
                    raise UTF8GuardError(f"Truncated 2-byte sequence at byte {i}")
                b2 = self.source_bytes[i + 1]
                if not (0x80 <= b2 <= 0xBF):
                    raise UTF8GuardError(f"Bad continuation byte at byte {i + 1}")
                cp = ((b & 0x1F) << 6) | (b2 & 0x3F)
                if cp < 0x80:
                    raise UTF8GuardError(f"Overlong 2-byte sequence at byte {i} (cp=U+{cp:04X})")
                i += 2
            elif 0xE0 <= b <= 0xEF:
                if i + 2 >= total:
                    raise UTF8GuardError(f"Truncated 3-byte sequence at byte {i}")
                b2 = self.source_bytes[i + 1]
                b3 = self.source_bytes[i + 2]
                if not (0x80 <= b2 <= 0xBF and 0x80 <= b3 <= 0xBF):
                    raise UTF8GuardError(f"Bad continuation byte in 3-byte at byte {i}")
                cp = ((b & 0x0F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F)
                if cp < 0x800:
                    raise UTF8GuardError(f"Overlong 3-byte sequence at byte {i} (cp=U+{cp:04X})")
                if 0xD800 <= cp <= 0xDFFF:
                    raise UTF8GuardError(f"Surrogate codepoint at byte {i} (cp=U+{cp:04X})")
                i += 3
            elif 0xF0 <= b <= 0xF4:
                if i + 3 >= total:
                    raise UTF8GuardError(f"Truncated 4-byte sequence at byte {i}")
                b2 = self.source_bytes[i + 1]
                b3 = self.source_bytes[i + 2]
                b4 = self.source_bytes[i + 3]
                if not (0x80 <= b2 <= 0xBF and 0x80 <= b3 <= 0xBF and 0x80 <= b4 <= 0xBF):
                    raise UTF8GuardError(f"Bad continuation byte in 4-byte at byte {i}")
                cp = ((b & 0x07) << 18) | ((b2 & 0x3F) << 12) | ((b3 & 0x3F) << 6) | (b4 & 0x3F)
                if cp < 0x10000:
                    raise UTF8GuardError(f"Overlong 4-byte sequence at byte {i} (cp=U+{cp:04X})")
                if cp > 0x10FFFF:
                    raise UTF8GuardError(f"Codepoint >U+10FFFF at byte {i} (cp=U+{cp:06X})")
                i += 4
            elif 0x80 <= b <= 0xBF:
                raise UTF8GuardError(f"Unexpected continuation byte at byte {i}")
            else:
                raise UTF8GuardError(f"Invalid lead byte 0x{b:02X} at byte {i}")

        # ── Gate 2: Python strict decode cross-validation ──
        try:
            self.source_bytes.decode("utf-8", "strict")
        except UnicodeDecodeError as e:
            raise UTF8GuardError(
                f"Gate2 cross-validation failed at byte {e.start}: {e.reason}"
            ) from e

        # ── Line analysis ──
        line_starts: List[int] = [0]
        pos = 0
        while pos < total:
            if pos + 1 < total:
                if self.source_bytes[pos] == 0x0D and self.source_bytes[pos + 1] == 0x0A:
                    pos += 2
                    line_starts.append(pos)
                elif self.source_bytes[pos] == 0x0A:
                    pos += 1
                    line_starts.append(pos)
                else:
                    pos += 1
            else:
                pos += 1

        crlf, lf_only = 0, 0
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

        has_bom = total >= 3 and self.source_bytes[:3] == b"\xEF\xBB\xBF"

        object.__setattr__(self, "total_bytes", total)
        object.__setattr__(self, "codepoint_count", len(chunk_starts))
        object.__setattr__(self, "line_starts", line_starts)
        object.__setattr__(self, "chunk_starts", chunk_starts)
        object.__setattr__(self, "has_bom", has_bom)
        object.__setattr__(self, "crlf_count", crlf)
        object.__setattr__(self, "lf_count", lf_only)

    @property
    def decode(self) -> str:
        return self.source_bytes.decode("utf-8", "strict")

    def byte_to_chunk_index(self, byte_offset: int) -> int:
        if byte_offset < 0 or byte_offset >= self.total_bytes:
            raise IndexError(f"offset {byte_offset} out of range [0, {self.total_bytes})")
        for ci in range(len(self.chunk_starts) - 1, -1, -1):
            if self.chunk_starts[ci] <= byte_offset:
                return ci
        return 0

    def byte_at(self, offset: int) -> int:
        if offset < 0 or offset >= self.total_bytes:
            raise IndexError(f"offset {offset} out of range [0, {self.total_bytes})")
        return self.source_bytes[offset]

    @property
    def legal_boundaries(self) -> List[int]:
        """Byte positions at valid codepoint boundaries, including EOF."""
        return sorted(set([0] + self.chunk_starts + [self.total_bytes]))


# ═══════════════════════════════════════════════════════════════════════
# Process-level timeout via subprocess (TRUE OS-level termination)
# ═══════════════════════════════════════════════════════════════════════

def with_timeout(data: bytes, timeout_sec: float = 2.0) -> dict:
    """Run UTF8ByteIndex(data) in a SUBPROCESS with OS-level timeout."""
    import base64, json, tempfile
    encoded = base64.b64encode(data).decode("ascii")
    # Compute source directory from this file's location
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # => .../src
    src_dir = here
    lines = []
    lines.append("import sys, base64, json")
    lines.append("sys.path.insert(0, " + json.dumps(src_dir) + ")")
    lines.append("from qclaw_strict_byte.utf8_guard import _subprocess_runner, UTF8GuardError")
    lines.append("raw = base64.b64decode(sys.stdin.read())")
    lines.append("try:")
    lines.append("    r = _subprocess_runner(raw)")
    lines.append("    print(json.dumps(r))")
    lines.append("except UTF8GuardError as e:")
    lines.append("    print(json.dumps({'e':'U','m':str(e)}))")
    lines.append("    sys.exit(1)")
    lines.append("except Exception as x:")
    lines.append("    print(json.dumps({'e':'X','m':str(x)}))")
    lines.append("    sys.exit(2)")
    runner = "\n".join(lines)

    fd, rp = tempfile.mkstemp(suffix=".py", prefix="_e39r_")
    os.close(fd)
    with open(rp, "w", encoding="utf-8") as f:
        f.write(runner)
    try:
        proc = subprocess.Popen(
            [sys.executable, rp],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            stdout, stderr = proc.communicate(input=encoded.encode("ascii"), timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.communicate()
            raise TimeoutError(f"UTF-8 scan timed out after {timeout_sec}s")
        if proc.returncode != 0:
            try:
                err = json.loads(stdout.decode("utf-8", "replace"))
                if err.get("e") == "U":
                    raise UTF8GuardError(err["m"])
                raise RuntimeError(f"Subprocess: {err.get('m', str(stderr[:200]))}")
            except (json.JSONDecodeError, KeyError):
                raise RuntimeError(f"Exit {proc.returncode}: {stderr.decode('utf-8','replace')[:200]}")
        return json.loads(stdout.decode("utf-8"))
    finally:
        try: os.unlink(rp)
        except OSError: pass
