"""Deterministic 64-hex SHA-256 digests for E61 cross-agent compatibility.

Three digests, each with a precise canonicalization contract. Volatile /
non-semantic fields are explicitly excluded from ``canonical_semantic_sha256``
so it stays stable across reruns, while ``raw_artifact_sha256`` covers the
exact serialized bytes and ``l0_provenance_sha256`` binds the immutable L0
identity + exact source/span/provenance manifest.

Contract summary
----------------
``raw_artifact_sha256``
    SHA-256 over the exact serialized bytes of the L2 candidate artifact /
    bundle (JSON, sorted-keys UTF-8, no trailing newline).
``canonical_semantic_sha256``
    SHA-256 over canonical semantic dict. Excludes ``ingested_at`` and any
    ``content_hash`` / ``*_sha256`` self-referential fields.
``l0_provenance_sha256``
    SHA-256 over the L0 immutable identity bundle: source_id, source_url,
    source_title, source_hash, source_size_bytes, plus an ordered list of
    (atom_id, byte_start, byte_end, evidence_kind) tuples covering every L0
    span used by L2.

All functions are pure, deterministic, and stdlib-only.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping


def canonical_json(obj: Any) -> str:
    """Return deterministic canonical JSON: sorted keys, UTF-8, no whitespace.

    JSON lists preserve order (they are *part of the semantic content*).
    JSON objects use sorted keys so that {"a":1,"b":2} and {"b":2,"a":1} hash
    identically. This is required for cross-run, cross-Python determinism.
    """
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_hex(data: bytes | bytearray | memoryview | str) -> str:
    """Full 64-hex SHA-256.

    Accepts bytes (raw artifact path) or str (canonical JSON path).
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(bytes(data)).hexdigest()


def raw_artifact_sha256(serialized_bytes: bytes | bytearray | memoryview) -> str:
    """Full 64-hex SHA-256 of the exact serialized candidate artifact bytes.
    No transformation. Includes all fields (including volatile).
    """
    return sha256_hex(bytes(serialized_bytes))


# Fields that are *never* part of semantic identity. Keep this list tight and
# explicit — anything else that drifts must produce a digest drift.
_VOLATILE_FIELDS = frozenset({
    "ingested_at",
    "package_version",
    "content_hash",          # legacy 16-hex E47 compatibility field
    "raw_artifact_sha256",
    "canonical_semantic_sha256",
    "l0_provenance_sha256",
})


def _strip_volatile(obj: Any) -> Any:
    """Recursively remove volatile fields from a parsed JSON-like object.
    Lists preserve order; dicts lose ``_VOLATILE_FIELDS`` keys.
    """
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items() if k not in _VOLATILE_FIELDS}
    if isinstance(obj, list):
        return [_strip_volatile(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_strip_volatile(v) for v in obj)
    return obj


def canonical_semantic_sha256(semantic_obj: Mapping[str, Any] | Any) -> str:
    """Full 64-hex SHA-256 over deterministic canonical semantic representation.

    The semantic object is the parsed L2 candidate package dict, with
    volatile fields stripped before canonicalization. The result is stable
    across reruns and across supported Python 3.11/3.13 as long as the
    semantic content is stable.
    """
    cleaned = _strip_volatile(semantic_obj)
    return sha256_hex(canonical_json(cleaned))


def _l0_manifest(source: Mapping[str, Any], atoms: Iterable[Mapping[str, Any]]) -> list:
    """Build an ordered L0 manifest: source identity + every L0 span used by L2.

    The manifest is a list of plain values (not dicts-of-dicts), so it sorts
    trivially. Order is preserved by list iteration.
    """
    identity_fields = ("source_id", "source_url", "source_title",
                       "source_hash", "source_size_bytes")
    identity = {k: source[k] for k in identity_fields if k in source}
    identity_list = [identity]
    span_records: list = []
    for atom in atoms:
        atom_id = atom.get("atom_id")
        evidence_kind = atom.get("evidence_kind")
        for span in atom.get("source_spans", []) or []:
            span_records.append((
                atom_id,
                int(span.get("byte_start", 0)),
                int(span.get("byte_end", 0)),
                evidence_kind,
            ))
    return identity_list + span_records


def l0_provenance_sha256(source: Mapping[str, Any],
                         atoms: Iterable[Mapping[str, Any]]) -> str:
    """Full 64-hex SHA-256 binding immutable L0 identity + provenance manifest.

    The manifest is an *ordered* list, so byte ranges follow their declaration
    order. Any source mutation or span mutation alters this digest; volatile
    fields (e.g. timestamps) do not. ``source`` MUST be the ``SourceSnapshot``
    dict (or an equivalent mapping) and ``atoms`` MUST be the parsed L2 atoms
    list. Normalized substitutes (L1 text) are *never* hashed here.
    """
    manifest = _l0_manifest(source, atoms)
    return sha256_hex(canonical_json(manifest))


@dataclass(frozen=True)
class DigestBundle:
    """Container for the three E61-compatible full digests + the legacy 16-hex field.

    The legacy ``legacy_content_hash`` is a *compatibility-only* field. It is
    never a production identity. See issue #216 comment #5249272794 rule #1.
    """
    raw_artifact_sha256: str
    canonical_semantic_sha256: str
    l0_provenance_sha256: str
    legacy_content_hash: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "raw_artifact_sha256": self.raw_artifact_sha256,
            "canonical_semantic_sha256": self.canonical_semantic_sha256,
            "l0_provenance_sha256": self.l0_provenance_sha256,
            "legacy_content_hash_compat_only": self.legacy_content_hash,
        }


__all__ = [
    "canonical_json",
    "sha256_hex",
    "raw_artifact_sha256",
    "canonical_semantic_sha256",
    "l0_provenance_sha256",
    "DigestBundle",
]