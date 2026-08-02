"""
QCLAW E34 — Span-Based Redaction
No secret-derived hashes, fingerprints, or reversible values.
Safe example patterns for testing only.
"""
import re
from typing import List, Set

# ── Secret patterns (order matters: longer patterns first) ────────────────

SECRET_PATTERNS = [
    # API keys
    (r'sk-(?:proj|ant)-[A-Za-z0-9_-]{20,}', 'sk-REDACTED_API_KEY'),
    (r'sk-[A-Za-z0-9_-]{20,}', 'sk-REDACTED_API_KEY'),
    # GitHub tokens
    (r'gh[pousr]_[A-Za-z0-9]{20,}', 'ghp_REDACTED_GITHUB_TOKEN'),
    # OpenAI keys
    (r'sess-[A-Za-z0-9]{20,}', 'sess-REDACTED_SESSION_KEY'),
    # AWS keys
    (r'AKIA[0-9A-Z]{16}', 'AKIA_REDACTED_AWS_KEY'),
    (r'(?i)aws_secret_access_key\s*[:=]\s*["\']?[\w/+]{20,}', 'aws_secret_access_key=REDACTED'),
    # Database passwords
    (r'(?i)(?:password|passwd|pwd)\s*[:=]\s*["\']?[\S]{3,}["\']?', 'password=REDACTED_PASSWORD'),
    (r'(?i)connection_string\s*[:=]\s*["\'][^"\']+["\']', 'connection_string=REDACTED_URI'),
    # JWT tokens
    (r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}', 'REDACTED_JWT'),
    # Bearer tokens
    (r'(?i)bearer\s+[A-Za-z0-9_\-\.]{10,}', 'Bearer REDACTED_TOKEN'),
    # Private keys
    (r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----[^-]*-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----', '-----BEGIN PRIVATE KEY-----REDACTED-----END PRIVATE KEY-----'),
    # Bitcoin/Ethereum private keys
    (r'(?i)(?:private_key|privkey)\s*[:=]\s*["\']?[0-9a-fA-F]{32,}["\']?', 'private_key=REDACTED'),
    # Credit card numbers
    (r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', 'REDACTED_CARD_NUMBER'),
    # Chinese ID numbers
    (r'\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b', 'REDACTED_ID_NUMBER'),
]

# Safe example values (NOT redacted — these are test fixtures, not real secrets)
SAFE_EXAMPLES = {
    'sk-test-example-key-12345678', 'sk-ant-example-key-for-testing-only',
    'ghp_example_token_placeholder', 'AKIA_EXAMPLE_PLACEHOLDER',
    'password=example_password', 'Bearer example_token_123',
}

def redact(text: str, safe_patterns: Set[str] = None) -> str:
    """
    Redact secrets. Preserves safe examples.
    Returns redacted text with exact span replacement.
    """
    safe = safe_patterns or SAFE_EXAMPLES
    result = text
    
    for pattern, replacement in SECRET_PATTERNS:
        matches = list(re.finditer(pattern, result, re.IGNORECASE))
        # Process in reverse to maintain byte positions
        for match in reversed(matches):
            matched_text = match.group(0)
            if matched_text in safe:
                continue  # Skip safe example patterns
            result = result[:match.start()] + replacement + result[match.end():]
    
    return result

def has_secrets(text: str, safe_patterns: Set[str] = None) -> bool:
    """Check if text contains any secret patterns (excluding safe examples)."""
    safe = safe_patterns or SAFE_EXAMPLES
    for pattern, _ in SECRET_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if match.group(0) not in safe:
                return True
    return False

def list_detected(text: str) -> List[str]:
    """Return list of detected secret types for reporting."""
    detected = []
    safe = SAFE_EXAMPLES
    for pattern, replacement in SECRET_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if match.group(0) not in safe:
                detected.append(replacement)
    return detected
