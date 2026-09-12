"""Deterministic JSON rendering for the cognitive loop.

Kept local so the loop stays dependency-free and does not import the creative
runtime. Mirrors the stable contract used elsewhere in the repository.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from typing import Any, Mapping


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    """Render a JSON value in the single stable format used for hashes."""

    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
