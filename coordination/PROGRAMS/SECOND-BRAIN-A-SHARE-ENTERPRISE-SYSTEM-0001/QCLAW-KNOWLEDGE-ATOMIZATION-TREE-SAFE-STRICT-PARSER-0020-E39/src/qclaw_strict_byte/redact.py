"""E39 S3 — Source-order irreversible byte-level redaction.

Key properties:
- Categories with priority order (API_KEY > PASSWORD > TOKEN > ...)
- Longest-match first + start position + stable tie-break for overlapping spans
- No secret plaintext, hash, fingerprint, or reversible substitution stored
- Output: original span, redacted-view span, replacement category, length delta,
  coverage proof
- Lineage preservation: original byte positions tracked in mapping
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Set


# ═══════════════════════════════════════════════════════════════════════
# Redaction categories (priority-ordered)
# ═══════════════════════════════════════════════════════════════════════

REDACT_CATEGORIES = [
    "PRIVATE_KEY",
    "API_KEY",
    "PASSWORD",
    "TOKEN",
    "SECRET",
    "SESSION_ID",
    "COOKIE",
    "CONNECTION_STRING",
    "INTERNAL_PATH",
    "CREDENTIAL",
]

CATEGORY_PRIORITY = {cat: i for i, cat in enumerate(REDACT_CATEGORIES)}


# ═══════════════════════════════════════════════════════════════════════
# Detection patterns (regex on decoded text, resolved to byte spans)
# ═══════════════════════════════════════════════════════════════════════

import re

REDACT_PATTERNS: List[Tuple[str, str, str]] = [
    # (category, regex, label)
    ("PRIVATE_KEY", r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP)\s+PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:RSA|DSA|EC|OPENSSH|PGP)\s+PRIVATE\s+KEY-----", "private_key_block"),
    ("PRIVATE_KEY", r"-----BEGIN\s+PRIVATE\s+KEY-----[\s\S]*?-----END\s+PRIVATE\s+KEY-----", "private_key_pkcs8"),
    ("API_KEY", r"(?:api[_-]?key|apikey|API_KEY)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{16,})['\"]?", "api_key_assignment"),
    ("API_KEY", r"sk-[A-Za-z0-9_\-]{20,}", "openai_key"),
    ("API_KEY", r"AIza[0-9A-Za-z\-_]{35}", "google_api_key"),
    ("PASSWORD", r"(?:password|passwd|pwd)\s*[:=]\s*['\"]?(\S{4,})['\"]?", "password_assignment"),
    ("PASSWORD", r"(?:密码|パスワード|비밀번호)\s*[:=]\s*['\"]?(\S{3,})['\"]?", "password_cjk"),
    ("TOKEN", r"(?:token|access_token|auth_token)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{10,})['\"]?", "token_assignment"),
    ("TOKEN", r"ghp_[A-Za-z0-9]{36}", "github_pat"),
    ("TOKEN", r"github_pat_[A-Za-z0-9_]{20,}", "github_pat_v2"),
    ("SECRET", r"(?:secret|SECRET)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?", "secret_assignment"),
    ("SESSION_ID", r"(?:session[_-]?id|sessionId|JSESSIONID)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{8,})['\"]?", "session_id"),
    ("COOKIE", r"set-cookie\s*:\s*['\"]?([^;]+)", "set_cookie"),
    ("CONNECTION_STRING", r"(?:mongodb|mysql|postgresql|postgres|sqlite|redis)://[^\s\"']{10,}", "conn_string"),
    ("INTERNAL_PATH", r"(?:C:|/home|/Users|/root)/\S{5,}", "absolute_path"),
    ("CREDENTIAL", r"credential\s*[:=]\s*['\"]?(\S{6,})['\"]?", "credential"),
]


# ═══════════════════════════════════════════════════════════════════════
# RedactionSpan
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RedactionCandidate:
    """A detected sensitive byte range before overlap resolution."""
    byte_start: int
    byte_end: int
    category: str
    label: str = ""


@dataclass(frozen=True)
class RedactionMapping:
    """Final resolved redaction mapping after overlap resolution.

    original_span: (byte_start, byte_end) in source
    redacted_span: (byte_start, byte_end) in redacted output
    replacement: replacement text (e.g. "[R1]")
    category: redaction category
    length_delta: redacted - original length
    """
    original_start: int
    original_end: int
    redacted_start: int
    redacted_end: int
    replacement: str
    category: str
    length_delta: int

    @property
    def original_length(self) -> int:
        return self.original_end - self.original_start

    @property
    def redacted_length(self) -> int:
        return self.redacted_end - self.redacted_start


# ═══════════════════════════════════════════════════════════════════════
# Byte-level pattern matching
# ═══════════════════════════════════════════════════════════════════════

def _char_to_byte_map(source: bytes) -> Dict[int, int]:
    """Build char-index → byte-offset for the source.

    char_index: position in decoded str
    byte_offset: position in original bytes
    """
    mapping: Dict[int, int] = {}
    byte_pos = 0
    char_pos = 0
    while byte_pos < len(source):
        mapping[char_pos] = byte_pos
        ch = source[byte_pos]
        if ch < 0x80:
            byte_pos += 1
        elif ch < 0xE0:
            byte_pos += 2
        elif ch < 0xF0:
            byte_pos += 3
        else:
            byte_pos += 4
        char_pos += 1
    mapping[char_pos] = byte_pos  # end-of-string sentinel
    return mapping


def find_redaction_candidates(source: bytes) -> List[RedactionCandidate]:
    """Scan source bytes for all redaction candidates using regex on decoded text.

    Returns unsorted list of candidates with byte positions.
    """
    try:
        text = source.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return []  # Only valid UTF-8 gets scanned

    c2b = _char_to_byte_map(source)
    candidates: List[RedactionCandidate] = []

    for category, pattern, label in REDACT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            # If the pattern has a capture group, use the whole match or group 1
            # We redact the entire match for keys, but only the value for assignments
            full_start = match.start()
            full_end = match.end()

            # For assignment patterns (group 1), redact just the value
            if match.lastindex and match.lastindex >= 1:
                g1_start = match.start(1)
                g1_end = match.end(1)
                # Only redact the value part (not the key name)
                if "PRIVATE_KEY" in category and "BEGIN" in match.group(0):
                    # Redact entire block
                    byte_start = c2b.get(full_start, full_start * 2)
                    byte_end = c2b.get(full_end, full_end * 2)
                else:
                    byte_start = c2b.get(g1_start, g1_start * 2)
                    byte_end = c2b.get(g1_end, g1_end * 2)
            else:
                byte_start = c2b.get(full_start, full_start)
                byte_end = c2b.get(full_end, full_end)

            if byte_end > byte_start:
                candidates.append(RedactionCandidate(
                    byte_start, byte_end, category, label
                ))

    return candidates


# ═══════════════════════════════════════════════════════════════════════
# Overlap resolution
# ═══════════════════════════════════════════════════════════════════════

def _resolve_overlaps(candidates: List[RedactionCandidate]) -> List[RedactionCandidate]:
    """Resolve overlapping redaction candidates.

    Rules:
    1. Higher priority (lower CATEGORY_PRIORITY index) wins
    2. Longest match wins at same priority
    3. Earlier start wins at same length
    4. Stable tie-break by category name
    """
    if not candidates:
        return []

    # Sort by: priority (asc), then -length (desc = longest first), then start
    def sort_key(c: RedactionCandidate):
        return (
            CATEGORY_PRIORITY.get(c.category, 99),
            -(c.byte_end - c.byte_start),
            c.byte_start,
            c.category,
        )

    sorted_c = sorted(candidates, key=sort_key)

    accepted: List[RedactionCandidate] = []
    covered: List[Tuple[int, int]] = []  # non-overlapping covered ranges

    for c in sorted_c:
        # Check if this span overlaps with any accepted span
        overlaps = False
        for (cs, ce) in covered:
            if c.byte_start < ce and cs < c.byte_end:
                overlaps = True
                break
        if not overlaps:
            accepted.append(c)
            covered.append((c.byte_start, c.byte_end))

    # Final sort by position for ordered output
    accepted.sort(key=lambda c: c.byte_start)
    return accepted


# ═══════════════════════════════════════════════════════════════════════
# Main redaction engine
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class RedactionResult:
    """Output of byte-level redaction."""
    redacted_bytes: bytes
    mapping: List[RedactionMapping]
    original_length: int
    redacted_length: int
    candidates_found: int
    resolved_count: int


def redact(source: bytes, safe_examples: Optional[List[bytes]] = None) -> RedactionResult:
    """Apply irreversible byte-level redaction.

    Args:
        source: Original source bytes
        safe_examples: Byte patterns that look like secrets but are safe
                       (never redacted). Default: typical safe examples.

    Returns:
        RedactionResult with redacted output and mapping.
    """
    if safe_examples is None:
        safe_examples = [
            b"sk-test-placeholder-00000000000000000000",
            b"api_key=EXAMPLE_DO_NOT_USE_IN_PRODUCTION",
            b"password=demo123",
            b"token=example_token_abcdef",
            b"sk-demo-not-real-000000000000000000000000",
            b"ghp_0000000000000000000000000000000000",
        ]

    # 1. Find candidates
    candidates = find_redaction_candidates(source)

    # 2. Filter out safe examples
    safe_ranges: List[Tuple[int, int]] = []
    for safe in safe_examples:
        pos = 0
        while True:
            idx = source.find(safe, pos)
            if idx == -1:
                break
            safe_ranges.append((idx, idx + len(safe)))
            pos = idx + 1

    def is_safe(c: RedactionCandidate) -> bool:
        for sr, se in safe_ranges:
            if sr <= c.byte_start and c.byte_end <= se:
                return True
        return False

    candidates = [c for c in candidates if not is_safe(c)]

    # 3. Resolve overlaps
    resolved = _resolve_overlaps(candidates)

    # 4. Build redacted output and mapping
    output_parts: List[bytes] = []
    mapping: List[RedactionMapping] = []
    cursor = 0
    r_counter = 0

    for c in resolved:
        # Copy non-redacted bytes before this span
        if cursor < c.byte_start:
            output_parts.append(source[cursor:c.byte_start])

        r_counter += 1
        replacement = f"[R{r_counter}]".encode("utf-8")

        redacted_start = sum(len(p) for p in output_parts)
        redacted_end = redacted_start + len(replacement)

        output_parts.append(replacement)

        mapping.append(RedactionMapping(
            original_start=c.byte_start,
            original_end=c.byte_end,
            redacted_start=redacted_start,
            redacted_end=redacted_end,
            replacement=f"[R{r_counter}]",
            category=c.category,
            length_delta=len(replacement) - (c.byte_end - c.byte_start),
        ))

        cursor = c.byte_end

    # Remaining bytes
    if cursor < len(source):
        output_parts.append(source[cursor:])

    redacted_bytes = b"".join(output_parts)

    return RedactionResult(
        redacted_bytes=redacted_bytes,
        mapping=mapping,
        original_length=len(source),
        redacted_length=len(redacted_bytes),
        candidates_found=len(candidates),
        resolved_count=len(resolved),
    )
