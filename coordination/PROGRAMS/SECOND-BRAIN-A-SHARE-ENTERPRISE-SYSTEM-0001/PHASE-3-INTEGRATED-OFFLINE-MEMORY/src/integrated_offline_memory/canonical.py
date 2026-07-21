"""NFKC canonicalization and content-addressed identity absorbed from PR #45."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "")).strip()


def canonical_value(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, dict):
        return {str(key): canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [canonical_value(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(canonical_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def atom_id(statement: str, atom_type: str, scope: str = "") -> str:
    return "at-" + content_hash({"statement": statement, "type": atom_type, "scope": scope})[:20]


def relation_id(source_atom_id: str, target_atom_id: str, relation_type: str) -> str:
    return "rel-" + content_hash({"source": source_atom_id, "target": target_atom_id, "type": relation_type})[:20]


def packet_id(source_hash: str, atom_ids: list[str], validation_hash: str) -> str:
    return "lp-" + content_hash({"source_hash": source_hash, "atom_ids": sorted(atom_ids), "validation_hash": validation_hash})[:20]
