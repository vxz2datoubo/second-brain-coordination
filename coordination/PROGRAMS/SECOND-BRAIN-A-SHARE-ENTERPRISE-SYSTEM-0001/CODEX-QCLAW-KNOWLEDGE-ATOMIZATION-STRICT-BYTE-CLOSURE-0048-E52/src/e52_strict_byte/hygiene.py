"""Fail-closed delivery hygiene for E52 source and provider artifacts."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable


_FORBIDDEN_SEGMENTS = frozenset({"__pycache__", ".pytest_cache", "artifacts"})
_FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".tmp", ".generated", ".generated.json")
_FORBIDDEN_NAMES = frozenset({".coverage"})


def generated_path_reason(path: str | Path) -> str | None:
    """Return a stable reason when an E52 delivery path is generated or transient."""
    candidate = Path(path)
    parts = {part.casefold() for part in candidate.parts}
    name = candidate.name.casefold()
    if parts & _FORBIDDEN_SEGMENTS:
        return "forbidden_generated_directory"
    if name in _FORBIDDEN_NAMES:
        return "forbidden_generated_filename"
    if name.endswith(_FORBIDDEN_SUFFIXES):
        return "forbidden_generated_suffix"
    return None


def assert_delivery_paths_clean(paths: Iterable[str | Path]) -> None:
    rejected = [(str(path), generated_path_reason(path)) for path in paths]
    rejected = [(path, reason) for path, reason in rejected if reason is not None]
    if rejected:
        detail = ", ".join(f"{path}:{reason}" for path, reason in sorted(rejected))
        raise ValueError(f"E52 delivery rejects generated paths: {detail}")


def assert_source_tree_clean(root: str | Path) -> None:
    root_path = Path(root)
    assert_delivery_paths_clean(path.relative_to(root_path) for path in root_path.rglob("*"))
