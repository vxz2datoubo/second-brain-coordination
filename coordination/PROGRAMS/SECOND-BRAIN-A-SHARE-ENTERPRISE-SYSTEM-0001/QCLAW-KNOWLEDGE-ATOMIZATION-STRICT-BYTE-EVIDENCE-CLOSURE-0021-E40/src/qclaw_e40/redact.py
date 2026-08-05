"""E40 S3 — Irreversible redaction engine.

- Original byte scanning for secret candidates
- Deterministic overlap resolution: category priority + longest-match + start offset
- Source-order irreversible mapping
- No secret-derived material: no hash/fingerprint/reversible substitution of secrets
- Safe examples skippable (never used as bypass)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum
import re


class RedactCategory(str, Enum):
    PRIVATE_KEY = "PRIVATE_KEY"
    API_KEY = "API_KEY"
    PASSWORD = "PASSWORD"
    TOKEN = "TOKEN"
    SECRET = "SECRET"
    SESSION_ID = "SESSION_ID"
    COOKIE = "COOKIE"
    CONNECTION_STRING = "CONNECTION_STRING"
    INTERNAL_PATH = "INTERNAL_PATH"
    CREDENTIAL = "CREDENTIAL"


# Priority: lower number = higher priority override
CATEGORY_PRIORITY: Dict[RedactCategory, int] = {
    RedactCategory.PRIVATE_KEY: 1,
    RedactCategory.API_KEY: 2,
    RedactCategory.PASSWORD: 3,
    RedactCategory.TOKEN: 4,
    RedactCategory.SECRET: 5,
    RedactCategory.SESSION_ID: 6,
    RedactCategory.COOKIE: 7,
    RedactCategory.CONNECTION_STRING: 8,
    RedactCategory.CREDENTIAL: 9,
    RedactCategory.INTERNAL_PATH: 10,
}

# Ordered pattern table for redaction candidates
REDACT_PATTERNS: List[Tuple[RedactCategory, bytes]] = [
    (RedactCategory.PRIVATE_KEY, re.compile(
        rb'-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP|PRIVATE) KEY-----.+?-----END (?:RSA|EC|DSA|OPENSSH|PGP|PRIVATE) KEY-----',
        re.DOTALL)),
    (RedactCategory.API_KEY, re.compile(rb'sk-[A-Za-z0-9_\-]{20,}')),
    (RedactCategory.API_KEY, re.compile(rb'(?:api[_-]?key|apikey|API_KEY)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{16,})["\']?', re.IGNORECASE)),
    (RedactCategory.PASSWORD, re.compile(rb'(?:password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]{4,})["\']?', re.IGNORECASE)),
    (RedactCategory.TOKEN, re.compile(rb'(?:token|access_token|auth_token|bearer)\s*[:=]\s*["\']?([A-Za-z0-9_\-\.]{16,})["\']?', re.IGNORECASE)),
    (RedactCategory.TOKEN, re.compile(rb'ghp_[A-Za-z0-9]{36,}')),
    (RedactCategory.SECRET, re.compile(rb'(?:secret|client_secret)\s*[:=]\s*["\']?([A-Za-z0-9_\-+/]{16,})["\']?', re.IGNORECASE)),
    (RedactCategory.SESSION_ID, re.compile(rb'(?:session[_-]?id|sessionid|JSESSIONID)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{8,})["\']?', re.IGNORECASE)),
    (RedactCategory.COOKIE, re.compile(rb'(?:cookie|set-cookie)\s*[:=]\s*(.+)', re.IGNORECASE)),
    (RedactCategory.CONNECTION_STRING, re.compile(rb'(?:DSN|connection[_-]?string|connect[_-]?str)\s*[:=]\s*["\']?(.+?)["\']?', re.IGNORECASE)),
    (RedactCategory.CREDENTIAL, re.compile(rb'(?:credential|credentials|auth)\s*[:=]\s*["\']?([A-Za-z0-9_\-.]{8,})["\']?', re.IGNORECASE)),
    (RedactCategory.INTERNAL_PATH, re.compile(rb'/(?:home|Users|var|etc|opt)/[A-Za-z0-9_\-/.]{4,}')),
]


@dataclass
class RedactionCandidate:
    """A byte range identified for redaction."""
    byte_start: int
    byte_end: int  # exclusive
    category: RedactCategory
    matched_text: bytes
    pattern_index: int  # which REDACT_PATTERNS rule matched


@dataclass
class RedactionMapping:
    """Irreversible redaction of one span."""
    original_span: Tuple[int, int]  # (start, end) in source bytes
    redacted_span: Tuple[int, int]  # (start, end) in output bytes
    category: RedactCategory
    replacement_label: str  # like "[R1]", "[R2]"
    length_change: int  # redacted_length - original_length


@dataclass
class RedactionResult:
    """Complete redaction result."""
    original_length: int
    redacted_bytes: bytes
    redacted_length: int
    mapping: List[RedactionMapping]
    candidates_found: int
    resolved_count: int


def find_redaction_candidates(source: bytes, safe_examples: Optional[List[bytes]] = None) -> List[RedactionCandidate]:
    """Find all redaction candidates in source bytes.

    safe_examples: segments to skip (not redacted) — must match exactly.
    """
    candidates: List[RedactionCandidate] = []
    safe_set: Set[Tuple[int, int]] = set()

    if safe_examples:
        # Exact match only — no fuzzy matching
        pos = 0
        for seg in safe_examples:
            idx = source.find(seg, pos)
            if idx >= 0:
                safe_set.add((idx, idx + len(seg)))
                pos = idx + len(seg)

    for pidx, (category, pattern) in enumerate(REDACT_PATTERNS):
        for match in pattern.finditer(source):
            start, end = match.start(), match.end()
            # Skip if covered by safe example
            if any(ss <= start and end <= se for ss, se in safe_set):
                continue
            candidates.append(RedactionCandidate(
                byte_start=start,
                byte_end=end,
                category=category,
                matched_text=source[start:end],
                pattern_index=pidx,
            ))

    return candidates


def resolve_overlaps(candidates: List[RedactionCandidate]) -> List[RedactionCandidate]:
    """Resolve overlapping candidates by category priority, longest-match, start offset."""
    if not candidates:
        return []

    # Sort: higher priority (lower number), then longest, then earliest start
    candidates.sort(key=lambda c: (
        CATEGORY_PRIORITY[c.category],
        -(c.byte_end - c.byte_start),  # longest first
        c.byte_start,
    ))

    resolved: List[RedactionCandidate] = []
    blocked_intervals: List[Tuple[int, int]] = []

    for cand in candidates:
        if any(s < cand.byte_end and cand.byte_start < e for s, e in blocked_intervals):
            continue
        resolved.append(cand)
        blocked_intervals.append((cand.byte_start, cand.byte_end))

    return resolved


def redact(source: bytes, safe_examples: Optional[List[bytes]] = None) -> RedactionResult:
    """Redact secrets from source bytes. Returns irreversible result."""
    candidates = find_redaction_candidates(source, safe_examples)
    resolved = resolve_overlaps(candidates)

    if not resolved:
        return RedactionResult(
            original_length=len(source),
            redacted_bytes=source,
            redacted_length=len(source),
            mapping=[],
            candidates_found=len(candidates),
            resolved_count=0,
        )

    # Sort resolved by byte_start for sequential processing
    resolved.sort(key=lambda c: c.byte_start)

    # Build output byte buffer with redacted replacements
    parts: List[bytes] = []
    mapping: List[RedactionMapping] = []
    cursor = 0
    output_cursor = 0

    for idx, cand in enumerate(resolved):
        # Copy unredacted bytes before this candidate
        if cursor < cand.byte_start:
            parts.append(source[cursor:cand.byte_start])
            output_cursor += cand.byte_start - cursor

        # Redaction replacement
        label = f"[R{idx + 1}]".encode("ascii")
        parts.append(label)

        mapping.append(RedactionMapping(
            original_span=(cand.byte_start, cand.byte_end),
            redacted_span=(output_cursor, output_cursor + len(label)),
            category=cand.category,
            replacement_label=f"[R{idx + 1}]",
            length_change=len(label) - (cand.byte_end - cand.byte_start),
        ))

        output_cursor += len(label)
        cursor = cand.byte_end

    # Copy remaining bytes
    if cursor < len(source):
        parts.append(source[cursor:])

    output = b"".join(parts)
    return RedactionResult(
        original_length=len(source),
        redacted_bytes=output,
        redacted_length=len(output),
        mapping=mapping,
        candidates_found=len(candidates),
        resolved_count=len(resolved),
    )
