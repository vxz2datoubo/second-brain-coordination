"""Credential/secret redaction boundary.

Rule (TASK-BRIEF.yaml): "Keep authentication-secret values local; never persist
them to GitHub, logs, receipts, fixtures, or return packages."

This module is the single choke point for any text that could leave the bridge.
"""
from __future__ import annotations

import re

from .contracts import BridgeBoundaryError

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("github_pat", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("ghp", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("gho", re.compile(r"gho_[A-Za-z0-9]{20,}")),
    ("ghs", re.compile(r"ghs_[A-Za-z0-9]{20,}")),
    ("openai", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("slack", re.compile(r"xox[bp]-[A-Za-z0-9-]{10,}")),
    ("pem", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("kv_secret", re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S+")),
)

REDACTED = "[REDACTED]"


def redact(text: str) -> str:
    """Return text with any credential-looking substring replaced."""
    out = text
    for _name, pattern in _SECRET_PATTERNS:
        out = pattern.sub(REDACTED, out)
    return out


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for _name, pattern in _SECRET_PATTERNS)


def assert_no_secrets(text: str, *, where: str = "value") -> None:
    """Fail closed if a credential-looking value would be persisted."""
    if contains_secret(text):
        raise BridgeBoundaryError(
            f"credential-looking value rejected at {where}"
        )
