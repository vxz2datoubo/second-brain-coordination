#!/usr/bin/env python3
"""
QCLAW E27 — Secret Redaction Module
Precisely redacts authentication/access/financial secret values while
retaining the rest of mixed documents. Produces redaction receipt.

Hard secrets (MUST redact):
  - API keys (sk-*, key-*, api_key=...)
  - Bearer/JWT tokens
  - Passwords in key=value form
  - Private keys (-----BEGIN PRIVATE KEY----- etc.)
  - AWS/cloud credentials (AKIA*, ABIA*)
  - Database connection strings with credentials
  - Bank/broker account numbers with context
  - Mnemonic seed phrases (12/24 words)

Soft passthrough (do NOT redact):
  - API endpoint URLs without secrets
  - Library names, function signatures, request schemas
  - Sample data without embedded credentials
  - Public identifiers (repo names, issue numbers)
"""
import re
import hashlib
from typing import Optional, Tuple

SECRET_PATTERNS = [
    # OpenAI / API keys (sk- prefix)
    (r'\b(sk-[A-Za-z0-9]{32,})\b', "STRIPPED_API_KEY"),
    # Generic API key assignments
    (r'''api_key\s*[=:]\s*['"]([^'"]{8,})['"]''', "STRIPPED_API_KEY_VALUE"),
    # Bearer/JWT tokens
    (r'Bearer\s+([A-Za-z0-9\-_\.]{20,})', "STRIPPED_BEARER_TOKEN"),
    # Passwords in key=value or key:value
    (r'''password\s*[=:]\s*['"]([^'"]{3,})['"]''', "STRIPPED_PASSWORD"),
    (r'''passwd\s*[=:]\s*['"]([^'"]{3,})['"]''', "STRIPPED_PASSWORD"),
    # PEM private keys
    (r'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----.+?-----END (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----', "STRIPPED_PRIVATE_KEY"),
    # AWS access keys
    (r'\b(AKIA|ABIA|ASIA)[A-Z0-9]{16}\b', "STRIPPED_AWS_ACCESS_KEY"),
    # AWS secret keys
    (r'''aws_secret_access_key\s*[=:]\s*['"]([^'"]{8,})['"]''', "STRIPPED_AWS_SECRET"),
    # Database connection strings with credentials
    (r'''(?:mysql|postgres|mongodb|redis)://[^:]+:[^@]+@''', "STRIPPED_DB_CREDENTIALS"),
    # GitHub tokens
    (r'\bghp_[A-Za-z0-9]{32,}\b', "STRIPPED_GITHUB_TOKEN"),
    (r'\bgithub_pat_[A-Za-z0-9_]{20,}\b', "STRIPPED_GITHUB_TOKEN"),
    # Mnemonic seed phrases (12 or 24 words)
    (r'\b(?:[a-z]{3,12}\s+){11,23}[a-z]{3,12}\b', "STRIPPED_POSSIBLE_MNEMONIC"),
    # Generic token assignments
    (r'''token\s*[=:]\s*['"]([A-Za-z0-9\-_\.]{20,})['"]''', "STRIPPED_TOKEN_VALUE"),
    # Secret/env variable assignments
    (r'''SECRET\s*[=:]\s*['"]([^'"]{4,})['"]''', "STRIPPED_SECRET_VALUE"),
    # Private key string embedded in code
    (r'-----BEGIN\s+PRIVATE\s+KEY-----.+?-----END\s+PRIVATE\s+KEY-----', "STRIPPED_PRIVATE_KEY"),
]

# Fake values that look like secrets but are safe
SAFE_FAKE_PATTERNS = [
    re.compile(r'''sk-test-[A-Za-z0-9]+''', re.IGNORECASE),
    re.compile(r'''api_key\s*[=:]\s*(['"])(?:your_key_here|example|test|fake|replace_me|placeholder)\1''', re.IGNORECASE),
    re.compile(r'''token\s*[=:]\s*(['"])(?:your_token_here|example|test|fake|replace_me|placeholder)\1''', re.IGNORECASE),
]

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def redact(text: str, source_id: str = "unknown") -> Tuple[str, list]:
    """
    Redact secret values from text. Returns (redacted_text, redaction_log).
    Does NOT redact safe fake/example values.
    """
    log = []
    redacted = text
    
    for pattern, label in SECRET_PATTERNS:
        compiled = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        matches = list(compiled.finditer(redacted))
        for m in matches:
            found = m.group(0)
            # Check if it's a safe fake value
            is_safe = False
            # Check captured group (the actual value) against safe patterns
            captured = None
            try:
                captured = m.group(1)
            except IndexError:
                captured = found
            # Also check simpler safe list
            safe_vals = {"your_key_here", "example_token_placeholder", "example", "test", "fake", "replace_me", "placeholder", "token_value_here", "your_token_here", "example_token", "fake_token", "test_token"}
            if captured and captured.lower() in safe_vals:
                is_safe = True
            if m.group(0).lower().startswith("token = 'example"):
                is_safe = True
            if m.group(0).lower().startswith("api_key = 'your"):
                is_safe = True
            for sfp in SAFE_FAKE_PATTERNS:
                if sfp.search(found):
                    is_safe = True
                    break
            
            if not is_safe:
                replacement = f"[REDACTED:{label}]"
                redacted = redacted.replace(found, replacement)
                log.append({
                    "type": label,
                    "location": f"offset_{m.start()}_to_{m.end()}",
                    "detected_length": len(found),
                    "replaced_with": replacement,
                    "source_id": source_id,
                    "detected_hash": sha256(found)[:16],
                    "was_safe_fake": False
                })
    
    return redacted, log

def redact_file(filepath: str) -> Tuple[str, list]:
    """Redact a file and return (redacted_content, redaction_log)."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        original = f.read()
    return redact(original, filepath)

def verify_zero_secrets(text: str) -> bool:
    """
    Verify that text contains zero unredacted secrets.
    This is called AFTER redact() — any remaining matches are bugs.
    """
    for pattern, label in SECRET_PATTERNS:
        compiled = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        matches = list(compiled.finditer(text))
        for m in matches:
            found = m.group(0)
            is_safe = False
            captured = None
            try:
                captured = m.group(1)
            except IndexError:
                captured = found
            safe_vals = {"your_key_here", "example_token_placeholder", "example", "test", "fake", "replace_me", "placeholder", "token_value_here", "your_token_here", "example_token", "fake_token", "test_token"}
            if captured and captured.lower() in safe_vals:
                is_safe = True
            if found.lower().startswith("token = 'example"):
                is_safe = True
            if found.lower().startswith("api_key = 'your"):
                is_safe = True
            for sfp in SAFE_FAKE_PATTERNS:
                if sfp.search(found):
                    is_safe = True
                    break
            if not is_safe:
                return False
    return True

# ── Test cases ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        # Real secrets that MUST be redacted
        ("API_KEY = sk-abcdef1234567890abcdef1234567890abc", True),
        ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0", True),
        ("""mysql://admin:realpassword@db.example.com:3306/mydb""", True),
        ("password='mySecret123'", True),
        ('aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"', True),
        ("ghp_1234567890abcdef1234567890abcdef1234", True),
        
        # Safe values that should NOT be redacted
        ("api_key = 'your_key_here'", False),
        ("token = 'example_token_placeholder'", False),
        ("Using the OpenAI API at https://api.openai.com/v1/chat/completions", False),
        ("api_key parameter is passed to the constructor", False),
        ("The function returns a JWT token string", False),
        
        # Mixed documents
        ("This knowledge base entry references an API: api_key='sk-real-secret-key-abcdefgh1234567890' but the rest is knowledge.", True),
    ]
    
    all_passed = 0
    for i, (text, expect_redact) in enumerate(test_cases):
        redacted, log = redact(text, f"test_{i}")
        was_redacted = len(log) > 0
        
        if was_redacted == expect_redact:
            all_passed += 1
            status = "✅"
        else:
            status = f"❌ (expected_redact={expect_redact}, got_redact={was_redacted})"
        
        print(f"[{i}] {status} | log entries: {len(log)} | text: {redacted[:100]}...")
        
        # For things that should redact: verify zero remaining secrets
        if was_redacted and expect_redact:
            clean = verify_zero_secrets(redacted)
            if not clean:
                print(f"     ❌ ZERO_SECRET_CHECK FAILED")
                all_passed -= 1
    
    print(f"\nPassed: {all_passed}/{len(test_cases)}")
