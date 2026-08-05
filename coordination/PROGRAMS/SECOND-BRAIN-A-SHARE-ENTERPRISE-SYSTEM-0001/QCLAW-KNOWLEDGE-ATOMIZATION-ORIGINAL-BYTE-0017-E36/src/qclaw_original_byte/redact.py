"""E36 S3 — Original-byte redaction with deterministic overlap resolution.
Plans redaction spans on raw bytes, resolves overlaps, preserves structure,
emits safe_redacted content. Never persists secret text/hash/fingerprint."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Set, Dict, Optional
import re, hashlib

from .boundary_table import OriginalByteIndex
from .coverage import Span


# === Secret patterns (compiled on raw bytes) ===
SECRET_BYTE_PATTERNS = [
    # API keys: sk-... (OpenAI-like)
    (re.compile(rb'sk-[A-Za-z0-9_\-]{20,}'), "API_KEY"),
    # GitHub tokens: ghp_...
    (re.compile(rb'ghp_[A-Za-z0-9_]{20,}'), "GITHUB_TOKEN"),
    # Generic bearer tokens
    (re.compile(rb'Bearer\s+[A-Za-z0-9_\-\.]{20,}'), "BEARER_TOKEN"),
    # Passwords: password= / "password": "..." 
    (re.compile(rb'(?:password|passwd|pwd)\s*[=:]\s*[\x27\x22]([^\x27\x22]*)[\x27\x22]', re.IGNORECASE), "PASSWORD"),
    # Private keys: -----BEGIN ... PRIVATE KEY-----
    (re.compile(rb'-----BEGIN\s+(?:RSA\s+|EC\s+|DSA\s+|ED25519\s+)?PRIVATE KEY-----[\s\S]*?-----END\s+(?:RSA\s+|EC\s+|DSA\s+|ED25519\s+)?PRIVATE KEY-----'), "PRIVATE_KEY"),
    # Connection strings
    (re.compile(rb'(?:mongodb|postgresql|mysql|redis)://[^\s\x22\x27<>]+'), "CONNECTION_STRING"),
    # AWS keys: AKIA...
    (re.compile(rb'AKIA[0-9A-Z]{16}'), "AWS_ACCESS_KEY"),
    # AWS secret keys (heuristic: 40 char base64 after SecretAccessKey)
    (re.compile(rb'SecretAccessKey[\s=:]+[\x27\x22]?([A-Za-z0-9/+=]{40})'), "AWS_SECRET_KEY"),
    # JWT tokens: eyJ...
    (re.compile(rb'eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+'), "JWT_TOKEN"),
    # Session cookies
    (re.compile(rb'(?:session|auth)_?token\s*[=:]\s*[\x27\x22]?([A-Za-z0-9_\-]{16,})[\x27\x22]?', re.IGNORECASE), "SESSION_TOKEN"),
    # Generic value after "secret" label
    (re.compile(rb'(?:secret|api[_\s]?(?:key|secret))\s*[=:]\s*[\x27\x22]([A-Za-z0-9_\-\.]{8,})[\x27\x22]', re.IGNORECASE), "SECRET_VALUE"),
    # Phone numbers (E.164 or common format)
    (re.compile(rb'\+[1-9]\d{6,14}'), "PHONE_NUMBER"),
    # Email addresses
    (re.compile(rb'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}'), "EMAIL"),
    # IP addresses
    (re.compile(rb'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), "IP_ADDRESS"),
]

# Safe patterns (examples/docs that should NOT be redacted)
SAFE_BYTE_PATTERNS = [
    re.compile(rb'sk-example', re.IGNORECASE),
    re.compile(rb'sk-demo', re.IGNORECASE),
    re.compile(rb'sk-placeholder', re.IGNORECASE),
    re.compile(rb'sk-your-key-here', re.IGNORECASE),
    re.compile(rb'ghp_example', re.IGNORECASE),
    re.compile(rb'ghp_demo', re.IGNORECASE),
    re.compile(rb'ghp_placeholder', re.IGNORECASE),
    re.compile(rb'AWS_EXAMPLE', re.IGNORECASE),
    re.compile(rb'password.*example', re.IGNORECASE),
    re.compile(rb'password.*placeholder', re.IGNORECASE),
    re.compile(rb'test@example\.com', re.IGNORECASE),
    re.compile(rb'example@example\.com', re.IGNORECASE),
    re.compile(rb'127\.0\.0\.1'),
    re.compile(rb'192\.168\.'),
    re.compile(rb'10\.\d{1,3}\.'),
]


def _is_safe(byte_span: bytes) -> bool:
    """Check if a matched span matches any safe pattern (skip redaction)."""
    for pat in SAFE_BYTE_PATTERNS:
        if pat.search(byte_span):
            return True
    return False


@dataclass(frozen=True)
class RedactionSpan:
    """A redaction plan entry: what byte range to redact, why, and lineage."""
    byte_start: int
    byte_end: int
    category: str
    original_length: int
    redacted_id: str  # deterministic non-secret-derived ID

    @classmethod
    def from_match(cls, start: int, end: int, category: str, source_len: int) -> "RedactionSpan":
        # Deterministic ID from (start, end, category) — NOT from secret content
        seed = f"{start}:{end}:{category}:{source_len}".encode()
        rid = hashlib.sha256(seed).hexdigest()[:16]
        return cls(start, end, category, end - start, rid)

    def redact_bytes(self, source: bytes) -> bytes:
        """Apply this redaction to byte source."""
        replacement = f"[REDACTED_{self.category}_{self.redacted_id}]".encode()
        return source[:self.byte_start] + replacement + source[self.byte_end:]


class SpanRedactor:
    """Plan redaction spans on original bytes. Resolve overlaps. Preserve lineage.
    NEVER stores secret text — only (start, end, category) metadata."""

    def __init__(self, index: OriginalByteIndex):
        self._raw = index.source_bytes
        self._len = len(self._raw)
        self._spans: List[RedactionSpan] = []

    @property
    def spans(self) -> List[RedactionSpan]:
        return list(self._spans)

    def detect_all(self) -> List[RedactionSpan]:
        """Scan raw bytes for all secret patterns. Return all matches."""
        raw: List[Tuple[int, int, str]] = []
        seen_ranges: Set[Tuple[int, int]] = set()

        for pattern, category in SECRET_BYTE_PATTERNS:
            for m in pattern.finditer(self._raw):
                start, end = m.start(), m.end()
                if (start, end) in seen_ranges:
                    continue
                matched_bytes = self._raw[start:end]
                if _is_safe(matched_bytes):
                    continue
                raw.append((start, end, category))
                seen_ranges.add((start, end))

        # Sort by start, then by length descending (longest first → priority)
        raw.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        return [RedactionSpan.from_match(s, e, c, self._len) for s, e, c in raw]

    def plan(self) -> List[RedactionSpan]:
        """Plan redactions with overlap resolution. First detection wins (longest)."""
        candidates = self.detect_all()
        resolved: List[RedactionSpan] = []
        covered: List[Tuple[int, int]] = []

        for rs in candidates:
            # Check overlap with already-resolved spans
            overlaps = False
            for cs, ce in covered:
                if rs.byte_start < ce and cs < rs.byte_end:
                    overlaps = True
                    break
            if not overlaps:
                resolved.append(rs)
                covered.append((rs.byte_start, rs.byte_end))

        self._spans = resolved
        return resolved

    def redact(self, spans: List[RedactionSpan] = None) -> bytes:
        """Apply redactions to source bytes. Returns redacted copy."""
        if spans is None:
            spans = self._spans
        result = self._raw
        # Apply from right to left so offsets stay valid
        for rs in sorted(spans, key=lambda x: x.byte_start, reverse=True):
            result = rs.redact_bytes(result)
        return result

    def redaction_counts(self) -> Dict[str, int]:
        """Return count by category."""
        counts: Dict[str, int] = {}
        for rs in self._spans:
            counts[rs.category] = counts.get(rs.category, 0) + 1
        return counts
