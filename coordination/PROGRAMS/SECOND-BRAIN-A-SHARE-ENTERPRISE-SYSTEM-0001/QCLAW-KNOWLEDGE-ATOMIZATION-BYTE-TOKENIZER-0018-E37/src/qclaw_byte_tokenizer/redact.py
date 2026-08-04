"""E37 S2 — Original-byte redaction engine.

Collects candidate redaction spans from raw bytes, resolves overlaps
deterministically (category priority + longest-match + start + tie-break),
and outputs irreversible mappings. Secret-derived hashes NEVER stored.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, FrozenSet
import re as _re
from .boundary_table import OriginalByteIndex


# ── redaction candidates ─────────────────────────────────────────────
# Priority order (lower = higher priority)
CATEGORY_PRIORITY = {
    "API_KEY": 1,
    "PASSWORD": 1,
    "GITHUB_TOKEN": 1,
    "PRIVATE_KEY": 1,
    "SESSION_TOKEN": 1,
    "COOKIE_SECRET": 2,
    "CONNECTION_STRING": 2,
    "CREDIT_CARD": 2,
    "AUTH_HEADER": 2,
    "SECRET_VALUE": 3,
}

# Byte-level patterns (applied to raw bytes)
_PATTERNS: List[Tuple[str, str, bytes]] = []  # (category, name, compiled regex bytes)


def _init_patterns():
    if _PATTERNS:
        return
    patterns: List[Tuple[str, bytes, str]] = [
        # sk- / sk-or- API keys (common LLM API key prefixes)
        ("API_KEY", rb"sk-[a-zA-Z0-9_-]{20,}(?=[\s\"')\x00]|$)", "sk_prefix"),
        ("API_KEY", rb"sk-or-[a-zA-Z0-9_-]{20,}(?=[\s\"')\x00]|$)", "sk_or_prefix"),
        # GitHub tokens (ghp_ / gho_ / ghu_ / ghs_ / ghr_)
        ("GITHUB_TOKEN", rb"gh[pousr]_[a-zA-Z0-9]{20,}(?=[\s\"')\x00]|$)", "github_token"),
        # Common API key patterns (key= / api_key= / token= in text)
        ("API_KEY", rb"(?:api[_-]?key|apikey|api_secret)\s*[:=]\s*['\"]?[a-zA-Z0-9._-]{16,}", "api_key_eq"),
        ("PASSWORD", rb"(?:password|passwd|pwd)\s*[:=]\s*['\"]?\S{4,}", "password_eq"),
        # Authorization headers
        ("AUTH_HEADER", rb"[Aa]uthorization\s*[:=]\s*['\"]?\S{8,}", "auth_header"),
        # JWT tokens (eyJ prefix)
        ("SECRET_VALUE", rb"eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{4,}\.[a-zA-Z0-9_-]{4,}", "jwt"),
        # Base64-ish long strings that look like secrets (avoid false positives on short tokens)
        ("SECRET_VALUE", rb"[a-zA-Z0-9+/=_-]{40,}(?=[\s\"')\x00]|$)", "base64_long"),
        # Private key header
        ("PRIVATE_KEY", rb"-----BEGIN\s+(?:RSA |EC |DSA )?PRIVATE KEY-----", "priv_key_header"),
        # Bearer tokens
        ("AUTH_HEADER", rb"[Bb]earer\s+[a-zA-Z0-9._-]{20,}", "bearer"),
    ]
    for cat, pat_bytes, name in patterns:
        compiled = _re.compile(pat_bytes)
        _PATTERNS.append((cat, name, compiled))


# ── output types ─────────────────────────────────────────────────────
@dataclass(frozen=True)
class RedactionMapping:
    original_span: Tuple[int, int]
    redacted_span: Tuple[int, int]
    category: str
    length_change: int  # redacted_len - original_len

    @property
    def original_len(self) -> int:
        return self.original_span[1] - self.original_span[0]

    @property
    def redacted_len(self) -> int:
        return self.redacted_span[1] - self.redacted_span[0]


@dataclass(frozen=True)
class RedactedView:
    redacted_bytes: bytes
    mappings: Tuple[RedactionMapping, ...]
    original_len: int
    redacted_count: int
    categories_affected: Tuple[str, ...]

    @property
    def redacted_len(self) -> int:
        return len(self.redacted_bytes)


# ── main API ─────────────────────────────────────────────────────────
def find_redactions(index: OriginalByteIndex) -> List[RedactionMapping]:
    """Find all redaction candidates in source bytes. No overlap resolution."""
    _init_patterns()
    b = index.source_bytes
    candidates: List[Dict[str, Any]] = []

    for cat, name, pattern in _PATTERNS:
        for m in pattern.finditer(b):
            candidates.append({
                "start": m.start(),
                "end": m.end(),
                "category": cat,
                "matched_text": b[m.start():m.end()],
            })

    # Sort by category priority, then longest, then start
    candidates.sort(key=lambda c: (
        CATEGORY_PRIORITY.get(c["category"], 99),
        -(c["end"] - c["start"]),
        c["start"],
    ))

    # Deduplicate (exactly same span)
    seen = set()
    unique = []
    for c in candidates:
        key = (c["start"], c["end"], c["category"])
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique


def resolve_redactions(candidates: List[Dict[str, Any]]) -> List[RedactionMapping]:
    """Resolve overlapping candidates via priority + longest-match + start + tie-break."""
    if not candidates:
        return []

    # Merge into non-overlapping spans
    covered = set()
    resolved: List[RedactionMapping] = []

    for c in candidates:
        s, e = c["start"], c["end"]
        # Check if any byte in [s, e) is already covered
        if any(idx in covered for idx in range(s, e)):
            continue
        for idx in range(s, e):
            covered.add(idx)
        resolved.append(RedactionMapping(
            original_span=(s, e),
            redacted_span=(s, s + 8),  # placeholder: [REDACTED] length determined during apply
            category=c["category"],
            length_change=-8,  # will be fixed in apply_redactions
        ))

    return resolved


def apply_redactions(index: OriginalByteIndex,
                     mappings: List[RedactionMapping]) -> RedactedView:
    """Apply redaction mappings to produce the redacted byte view."""
    if not mappings:
        return RedactedView(
            redacted_bytes=index.source_bytes,
            mappings=(),
            original_len=index.total_bytes,
            redacted_count=0,
            categories_affected=(),
        )

    b = index.source_bytes
    n = index.total_bytes

    # Build segments
    cuts = []
    for m in mappings:
        s, e = m.original_span
        cuts.append((s, 0))  # start redaction
        cuts.append((e, 1))  # end redaction
    cuts.sort()

    # Build redacted output
    parts: List[bytes] = []
    cursor = 0
    cut_idx = 0
    redacted_idx = 0
    final_mappings: List[RedactionMapping] = []
    categories_set = set()

    while cursor < n:
        # Find next cut
        if cut_idx >= len(cuts):
            parts.append(b[cursor:])
            break

        cut_pos, cut_type = cuts[cut_idx]
        if cut_pos < cursor:
            cut_idx += 1
            continue

        if cut_pos > cursor:
            parts.append(b[cursor:cut_pos])

        if cut_type == 0:  # start redaction
            mapping = mappings[redacted_idx]
            rs, re = mapping.original_span
            redacted_text = f"[R{redacted_idx + 1}]".encode("ascii")
            parts.append(redacted_text)
            orig_len = re - rs
            new_len = len(redacted_text)
            final_mappings.append(RedactionMapping(
                original_span=(rs, re),
                redacted_span=(0, 0),  # position in output computed later
                category=mapping.category,
                length_change=new_len - orig_len,
            ))
            categories_set.add(mapping.category)
            redacted_idx += 1
            cursor = re

        cut_idx += 1

    output = b"".join(parts)

    # Compute redacted_span positions in output
    # Re-scan to find [R1], [R2], ...
    final_with_pos: List[RedactionMapping] = []
    for i, fm in enumerate(final_mappings):
        marker = f"[R{i + 1}]".encode("ascii")
        pos = output.find(marker)
        if pos >= 0:
            final_with_pos.append(RedactionMapping(
                original_span=fm.original_span,
                redacted_span=(pos, pos + len(marker)),
                category=fm.category,
                length_change=fm.length_change,
            ))
        else:
            final_with_pos.append(fm)

    return RedactedView(
        redacted_bytes=output,
        mappings=tuple(final_with_pos),
        original_len=n,
        redacted_count=len(final_mappings),
        categories_affected=tuple(sorted(categories_set)),
    )
