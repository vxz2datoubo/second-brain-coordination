"""Canonical repo-relative write-surface grammar for unified execution authority.

The grammar is intentionally fail-closed. It does not normalize ambiguous or
traversal spellings into a target; it rejects them before authority receipts,
collision identities, or registry-wide overlap admission can be computed.

Evidence spelling and conflict identity are deliberately separate. Accepted Git
spellings are preserved for receipts/audit, while same-repository writer-conflict
identity uses a conservative Windows-first NFC + casefold key so case-equivalent
paths cannot become parallel writers to one mutable object.
"""
from __future__ import annotations

from collections.abc import Sequence
import unicodedata


class CanonicalWritePathError(ValueError):
    """Raised when a write surface is not a unique canonical repository path."""


def canonicalize_write_path_pattern(path: str) -> str:
    """Validate and return the unique canonical spelling for one write surface.

    Accepted forms are either an exact repository-relative path (``src/a.py``)
    or a recursive tree rooted at a non-empty repository-relative path
    (``src/generated/**``). The returned spelling is deliberately identical to
    the accepted input: ambiguous spellings are rejected rather than rewritten.
    """
    if not isinstance(path, str) or not path:
        raise CanonicalWritePathError("write path must be a non-empty string")
    if path != path.strip():
        raise CanonicalWritePathError("write path must not contain edge whitespace")
    if any(ord(char) < 32 or ord(char) == 127 for char in path):
        raise CanonicalWritePathError("write path contains control characters")
    if "\\" in path:
        raise CanonicalWritePathError("backslash separators are not canonical")
    if path.startswith("/"):
        raise CanonicalWritePathError("absolute write paths are forbidden")
    if "//" in path:
        raise CanonicalWritePathError("repeated separators are not canonical")

    recursive = path.endswith("/**")
    root = path[:-3] if recursive else path
    if not root or root.endswith("/"):
        raise CanonicalWritePathError("write path has an empty normalized root")

    segments = root.split("/")
    wildcard_chars = "*?[]"
    for segment in segments:
        if segment in {"", ".", ".."}:
            raise CanonicalWritePathError(
                "dot, traversal, and empty path segments are forbidden"
            )
        if any(char in segment for char in wildcard_chars):
            raise CanonicalWritePathError(
                "only a terminal '/**' recursive pattern is permitted"
            )
        if ":" in segment:
            raise CanonicalWritePathError(
                "drive/alternate-stream style path segments are forbidden"
            )
        if segment.endswith((" ", ".")):
            raise CanonicalWritePathError(
                "platform-ambiguous trailing space/dot segments are forbidden"
            )

    return root + ("/**" if recursive else "")


def write_surface_conflict_key(path: str) -> str:
    """Return a conservative Windows-first identity for writer conflict checks.

    The accepted repository spelling remains unchanged elsewhere. This key is only
    for same-repository collision/overlap identity and intentionally collapses
    Unicode normalization and case variants that can denote one mutable Windows
    filesystem object. False-positive serialization is safer than two writers.
    """
    canonical = canonicalize_write_path_pattern(path)
    recursive = canonical.endswith("/**")
    root = canonical[:-3] if recursive else canonical
    conflict_root = unicodedata.normalize("NFC", root).casefold()
    if not conflict_root:
        raise CanonicalWritePathError("write path has an empty conflict identity")
    return conflict_root + ("/**" if recursive else "")


def canonicalize_authorized_paths(paths: Sequence[str]) -> tuple[str, ...]:
    if isinstance(paths, (str, bytes)) or not isinstance(paths, Sequence):
        raise CanonicalWritePathError("authorized_paths must be a sequence of strings")
    canonical = tuple(canonicalize_write_path_pattern(path) for path in paths)
    if len(canonical) != len(set(canonical)):
        raise CanonicalWritePathError("duplicate canonical write surfaces are forbidden")
    conflict_keys = tuple(write_surface_conflict_key(path) for path in canonical)
    if len(conflict_keys) != len(set(conflict_keys)):
        raise CanonicalWritePathError(
            "Windows-equivalent write surfaces are forbidden within one authority"
        )
    return canonical


def parse_write_pattern(path: str) -> tuple[str, bool]:
    canonical = canonicalize_write_path_pattern(path)
    recursive = canonical.endswith("/**")
    root = canonical[:-3] if recursive else canonical
    return root, recursive


def parse_write_pattern_conflict_key(path: str) -> tuple[str, bool]:
    conflict_key = write_surface_conflict_key(path)
    recursive = conflict_key.endswith("/**")
    root = conflict_key[:-3] if recursive else conflict_key
    return root, recursive
