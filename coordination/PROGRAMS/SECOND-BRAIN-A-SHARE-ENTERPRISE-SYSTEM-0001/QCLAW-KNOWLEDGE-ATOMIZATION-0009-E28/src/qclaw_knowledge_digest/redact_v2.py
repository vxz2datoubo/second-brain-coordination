#!/usr/bin/env python3
"""
QCLAW E28 — Span-Based Redaction v2
Fixes E27 defects:
  - Span planner (no global replacement)
  - Overlap resolution (longer match priority)
  - No secret-derived fingerprints/hashes stored
"""
import re
from dataclasses import dataclass
from typing import Tuple, List

SECRET_PATTERNS = [
    (r'\b(sk-[A-Za-z0-9]{32,})\b', "STRIPPED_API_KEY"),
    (r'''api_key\s*[=:]\s*['"]([^'"]{8,})['"]''', "STRIPPED_API_KEY_VALUE"),
    (r'Bearer\s+([A-Za-z0-9\-_\.]{20,})', "STRIPPED_BEARER_TOKEN"),
    (r'''password\s*[=:]\s*['"]([^'"]{3,})['"]''', "STRIPPED_PASSWORD"),
    (r'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----.+?-----END (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----', "STRIPPED_PRIVATE_KEY"),
    (r'\b(AKIA|ABIA|ASIA)[A-Z0-9]{16}\b', "STRIPPED_AWS_KEY"),
    (r'''(?:mysql|postgres|mongodb|redis)://[^:]+:[^@]+@''', "STRIPPED_DB_CREDENTIALS"),
    (r'\bghp_[A-Za-z0-9]{32,}\b', "STRIPPED_GITHUB_TOKEN"),
    (r'\bgithub_pat_[A-Za-z0-9_]{20,}\b', "STRIPPED_GITHUB_TOKEN"),
    (r'''token\s*[=:]\s*['"]([A-Za-z0-9\-_\.]{20,})['"]''', "STRIPPED_TOKEN_VALUE"),
]

SAFE_VALUES = {"your_key_here", "example_token_placeholder", "example", "test", "fake",
               "replace_me", "placeholder", "token_value_here", "your_token_here",
               "example_token", "fake_token", "test_token"}

def is_safe_match(found: str, captured_value: str = None) -> bool:
    """Check if a match is a safe/example value."""
    if captured_value and captured_value.lower() in SAFE_VALUES:
        return True
    if found.lower().startswith(("token = 'example", "api_key = 'your")):
        return True
    return False

@dataclass
class RedactionSpan:
    start: int
    end: int       # exclusive
    label: str

# Need dataclass import
def plan_redaction_spans(text: str, source_id: str = "") -> Tuple[List[RedactionSpan], List[dict]]:
    """
    Plan redaction spans with overlap resolution.
    Longer spans take priority. No global replacement.
    Returns (spans, log). Log contains NO secret-derived fingerprints.
    """
    spans = []
    log = []
    
    for pattern, label in SECRET_PATTERNS:
        compiled = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        for m in compiled.finditer(text):
            found = m.group(0)
            # Check captured group for safe values
            captured = None
            try:
                captured = m.group(1)
            except IndexError:
                pass
            
            if is_safe_match(found, captured):
                log.append({
                    "type": label,
                    "span": [m.start(), m.end()],
                    "action": "SKIPPED_SAFE",
                    "source_id": source_id
                })
                continue
            
            spans.append(RedactionSpan(start=m.start(), end=m.end(), label=label))
            log.append({
                "type": label,
                "span": [m.start(), m.end()],
                "length": m.end() - m.start(),
                "action": "REDACTED",
                "source_id": source_id
            })
    
    # Resolve overlaps: sort by start, keep longer span on overlap
    spans.sort(key=lambda s: (s.start, -(s.end - s.start)))
    resolved = []
    for s in spans:
        # Check if this span is covered by an already-resolved longer span
        covered = False
        for r in resolved:
            if r.start <= s.start and r.end >= s.end:
                covered = True
                break
        if not covered:
            resolved.append(s)
    
    # Sort by start position
    resolved.sort(key=lambda s: s.start)
    return resolved, log

def apply_redactions(text: str, spans: List[RedactionSpan]) -> str:
    """Apply redaction spans. Builds output byte-by-byte."""
    result = []
    last_end = 0
    for s in spans:
        result.append(text[last_end:s.start])
        result.append(f"[REDACTED:{s.label}]")
        last_end = s.end
    result.append(text[last_end:])
    return "".join(result)

def redact(text: str, source_id: str = "") -> Tuple[str, List[dict]]:
    """Main redaction: plan spans → resolve overlaps → apply → log (no hashes)."""
    spans, log = plan_redaction_spans(text, source_id)
    redacted = apply_redactions(text, spans)
    return redacted, log

def verify_zero_secrets(text: str, expect_redacted: bool = True) -> Tuple[bool, List[str]]:
    """Verify zero unredacted secrets. Returns (clean, violations)."""
    violations = []
    for pattern, label in SECRET_PATTERNS:
        compiled = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        for m in compiled.finditer(text):
            found = m.group(0)
            captured = None
            try:
                captured = m.group(1)
            except IndexError:
                pass
            if not is_safe_match(found, captured):
                if expect_redacted and "[REDACTED:" not in found:
                    violations.append(f"{label} at {m.start()}:{m.end()}")
    return len(violations) == 0, violations

# ── Tests ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        ("API_KEY = sk-abcdef1234567890abcdef1234567890abc", "redact"),
        ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0", "redact"),
        ("mysql://admin:realpass@db.example.com:3306/mydb", "redact"),
        ("api_key = 'your_key_here'", "safe"),
        ("token = 'example_token_placeholder'", "safe"),
        ("sk-abcdef1234567890abcdef1234567890abcdef and ghp_1234567890abcdef1234567890abcdef1234 side by side", "redact"),
    ]
    passed = 0
    for text, expect in tests:
        redacted, log = redact(text)
        actual = "redact" if any(l["action"] == "REDACTED" for l in log) else "safe"
        ok = actual == expect
        if ok: passed += 1
        print(f"{'✅' if ok else '❌'} [{actual}] log={len(log)}: {redacted[:80]}...")
    print(f"\n{passed}/{len(tests)} passed")
