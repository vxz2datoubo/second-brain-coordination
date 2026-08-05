"""Irreversible production redaction with no safe-example bypass."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class RedactionCategory(str, Enum):
    PRIVATE_KEY = "PRIVATE_KEY"
    API_KEY = "API_KEY"
    TOKEN = "TOKEN"
    PASSWORD = "PASSWORD"
    CONNECTION_STRING = "CONNECTION_STRING"


_PRIORITY = {
    RedactionCategory.PRIVATE_KEY: 0,
    RedactionCategory.API_KEY: 1,
    RedactionCategory.TOKEN: 2,
    RedactionCategory.PASSWORD: 3,
    RedactionCategory.CONNECTION_STRING: 4,
}
_PATTERNS: tuple[tuple[RedactionCategory, re.Pattern[bytes]], ...] = (
    (
        RedactionCategory.PRIVATE_KEY,
        re.compile(
            rb"-----BEGIN (?:(?:RSA|EC|DSA|OPENSSH|PGP|ENCRYPTED) )?PRIVATE KEY-----[\s\S]+?-----END (?:(?:RSA|EC|DSA|OPENSSH|PGP|ENCRYPTED) )?PRIVATE KEY-----"
        ),
    ),
    (RedactionCategory.API_KEY, re.compile(rb"(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9_\-.]{12,}['\"]?", re.I)),
    (RedactionCategory.TOKEN, re.compile(rb"(?:token|bearer|access_token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-.]{12,}['\"]?", re.I)),
    (RedactionCategory.PASSWORD, re.compile(rb"(?:password|passwd|pwd)\s*[:=]\s*['\"]?[^'\"\s]{6,}['\"]?", re.I)),
    (RedactionCategory.CONNECTION_STRING, re.compile(rb"(?:postgres|mysql|mongodb)://[^\s'\"]+", re.I)),
)


@dataclass(frozen=True, slots=True)
class RedactionMapping:
    original_span: tuple[int, int]
    replacement_span: tuple[int, int]
    category: RedactionCategory
    irreversible_sequence: int


@dataclass(frozen=True, slots=True)
class RedactionResult:
    redacted_bytes: bytes
    mappings: tuple[RedactionMapping, ...]
    categories: tuple[RedactionCategory, ...]


@dataclass(frozen=True, slots=True)
class _Candidate:
    start: int
    end: int
    category: RedactionCategory


def _candidates(source: bytes) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    for category, pattern in _PATTERNS:
        for match in pattern.finditer(source):
            candidates.append(_Candidate(match.start(), match.end(), category))
    return candidates


def _resolve(candidates: list[_Candidate]) -> list[_Candidate]:
    selected: list[_Candidate] = []
    occupied: list[tuple[int, int]] = []
    for candidate in sorted(
        candidates,
        key=lambda value: (_PRIORITY[value.category], -(value.end - value.start), value.start),
    ):
        if any(start < candidate.end and candidate.start < end for start, end in occupied):
            continue
        selected.append(candidate)
        occupied.append((candidate.start, candidate.end))
    return sorted(selected, key=lambda value: value.start)


def redact(source: bytes) -> RedactionResult:
    """Return a safe replacement stream and irreversible, non-secret metadata."""
    resolved = _resolve(_candidates(source))
    if not resolved:
        return RedactionResult(redacted_bytes=bytes(source), mappings=(), categories=())
    parts: list[bytes] = []
    mappings: list[RedactionMapping] = []
    cursor = 0
    output_cursor = 0
    for sequence, candidate in enumerate(resolved, start=1):
        prefix = source[cursor:candidate.start]
        parts.append(prefix)
        output_cursor += len(prefix)
        replacement = f"[REDACTED_{candidate.category.value}_{sequence}]".encode("ascii")
        parts.append(replacement)
        mappings.append(
            RedactionMapping(
                original_span=(candidate.start, candidate.end),
                replacement_span=(output_cursor, output_cursor + len(replacement)),
                category=candidate.category,
                irreversible_sequence=sequence,
            )
        )
        output_cursor += len(replacement)
        cursor = candidate.end
    parts.append(source[cursor:])
    return RedactionResult(
        redacted_bytes=b"".join(parts),
        mappings=tuple(mappings),
        categories=tuple(mapping.category for mapping in mappings),
    )
