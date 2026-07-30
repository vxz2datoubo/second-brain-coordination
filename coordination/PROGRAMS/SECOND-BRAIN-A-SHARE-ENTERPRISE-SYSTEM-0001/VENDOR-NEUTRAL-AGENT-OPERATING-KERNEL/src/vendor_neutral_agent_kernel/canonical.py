"""Deterministic, dependency-free canonical serialization."""

from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from enum import Enum
from hashlib import sha256
import json
import math
from typing import Any, Mapping


def canonical_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            field.name: canonical_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {
            str(key): canonical_value(value[key])
            for key in sorted(value, key=str)
        }
    if isinstance(value, (tuple, list)):
        return [canonical_value(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NON_FINITE_CANONICAL_FLOAT")
        return value
    if value is None or type(value) in (str, int, bool):
        return value
    raise TypeError("UNSUPPORTED_CANONICAL_VALUE:" + type(value).__name__)


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonical_value(value),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_sha256(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def seal_contract(value: Any) -> Any:
    """Return a dataclass with meta.content_hash bound to its other content."""
    if not is_dataclass(value) or not hasattr(value, "meta"):
        raise TypeError("SEAL_REQUIRES_CONTRACT_DATACLASS")
    meta = value.meta
    if not is_dataclass(meta) or not hasattr(meta, "content_hash"):
        raise TypeError("SEAL_REQUIRES_CONTRACT_META")
    unhashed_meta = replace(meta, content_hash="")
    unhashed_value = replace(value, meta=unhashed_meta)
    digest = canonical_sha256(unhashed_value)
    return replace(value, meta=replace(meta, content_hash=digest))
