"""E35 S2 — SpanRedactor: plan spans on original bytes, resolve overlaps, preserve lineage."""
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from qclaw_byte_atomizer.byte_index import ByteIndex, ByteSpan
import re


@dataclass
class RedactionSpan:
    """A redaction plan entry on original bytes."""
    start: int
    end: int
    category: str  # "PASSWORD", "API_KEY", "SECRET", "TOKEN", "PRIVATE_KEY", etc.
    matched_text: str
    replacement: str

    def to_dict(self):
        return {"start": self.start, "end": self.end, "category": self.category,
                "matched_text": "<redacted>", "replacement": self.replacement}


SECRET_PATTERNS = [
    # API keys (sk-, api_key=, etc.)
    (re.compile(r'sk-[a-zA-Z0-9_-]{16,}', re.ASCII), "API_KEY"),
    (re.compile(r'api[_]?key\s*[:=]\s*["\']?[a-zA-Z0-9_-]{12,}', re.IGNORECASE), "API_KEY"),
    (re.compile(r'ghp_[a-zA-Z0-9]{20,}', re.ASCII), "GH_TOKEN"),
    (re.compile(r'github[_]?pat[_]?[a-zA-Z0-9_-]{12,}', re.IGNORECASE), "GH_TOKEN"),
    (re.compile(r'Bearer\s+[a-zA-Z0-9._-]{20,}', re.ASCII), "BEARER_TOKEN"),
    (re.compile(r'password\s*[:=]\s*["\']?\S{4,}', re.IGNORECASE), "PASSWORD"),
    (re.compile(r'secret\s*[:=]\s*["\']?\S{4,}', re.IGNORECASE), "SECRET"),
    (re.compile(r'private[_]?key', re.IGNORECASE), "PRIVATE_KEY"),
    (re.compile(r'-----BEGIN\s+(RSA|EC|DSA|PRIVATE|OPENSSH)\s+PRIVATE\s+KEY-----.*?-----END\s+\1\s+PRIVATE\s+KEY-----', re.DOTALL), "PRIVATE_KEY"),
    (re.compile(r'AWS_ACCESS_KEY_ID\s*[:=]\s*["\']?\S{8,}', re.IGNORECASE), "AWS_KEY"),
    (re.compile(r'AWS_SECRET_ACCESS_KEY\s*[:=]\s*["\']?\S{8,}', re.IGNORECASE), "AWS_KEY"),
    (re.compile(r'connection[_]?string\s*[:=]\s*["\']?.+?["\']?', re.IGNORECASE), "CONNECTION_STRING"),
    (re.compile(r'\b[A-Za-z0-9+/]{40,}={0,2}\b', re.ASCII), "BASE64_SUSPECT"),
    (re.compile(r'oauth[_]?token\s*[:=]\s*["\']?\S{8,}', re.IGNORECASE), "OAUTH_TOKEN"),
]

# Example/safe patterns are NOT redacted
SAFE_PATTERNS = [
    re.compile(r'sk-test-example', re.IGNORECASE),
    re.compile(r'ghp_example', re.IGNORECASE),
    re.compile(r'example[_]?key', re.IGNORECASE),
    re.compile(r'placeholder', re.IGNORECASE),
    re.compile(r'demo[_]?token', re.IGNORECASE),
    re.compile(r'REDACTED_', re.IGNORECASE),
]


class SpanRedactor:
    """Plan redaction spans on original bytes, resolve overlaps, preserve lineage."""

    def __init__(self, source: str):
        self.source = source
        self.source_bytes = source.encode("utf-8")
        self.idx = ByteIndex(source)

    def plan_redactions(self) -> List[RedactionSpan]:
        """Detect all secret spans in original bytes."""
        redactions: List[RedactionSpan] = []
        seen_ranges: List[Tuple[int, int]] = []

        for pattern, category in SECRET_PATTERNS:
            for m in pattern.finditer(self.source):
                start, end = m.start(), m.end()
                matched = m.group()

                # Skip safe patterns
                is_safe = False
                for sp in SAFE_PATTERNS:
                    if sp.search(matched):
                        is_safe = True
                        break
                if is_safe:
                    continue

                # Check overlap with existing redactions
                is_duplicate = False
                for rs, re_seen in seen_ranges:
                    if not (end <= rs or start >= re_seen):
                        is_duplicate = True
                        break
                if is_duplicate:
                    continue

                redactions.append(RedactionSpan(
                    start=start, end=end, category=category,
                    matched_text=matched,
                    replacement=f"REDACTED_{category}"
                ))
                seen_ranges.append((start, end))

        # Sort and resolve overlaps by longest-first
        redactions.sort(key=lambda r: (r.end - r.start), reverse=True)  # longest first
        seen_ranges = []
        resolved: List[RedactionSpan] = []
        for r in redactions:
            has_overlap = False
            for rs, re_seen in seen_ranges:
                if not (r.end <= rs or r.start >= re_seen):
                    has_overlap = True
                    break
            if not has_overlap:
                resolved.append(r)
                seen_ranges.append((r.start, r.end))

        resolved.sort(key=lambda r: r.start)
        return resolved

    def apply(self, redactions: List[RedactionSpan]) -> Tuple[str, List[RedactionSpan]]:
        """Apply redactions to produce redacted output + preserved lineage."""
        if not redactions:
            return self.source, []

        # Build redacted text
        result = []
        pos = 0
        applied = []
        for r in sorted(redactions, key=lambda x: x.start):
            if r.start < pos:
                continue
            result.append(self.source[pos:r.start])
            result.append(r.replacement)
            applied.append(r)
            pos = r.end
        result.append(self.source[pos:])

        return "".join(result), applied

    def redact(self) -> Tuple[str, List[RedactionSpan]]:
        """Full redact: detect + apply."""
        plans = self.plan_redactions()
        return self.apply(plans)
