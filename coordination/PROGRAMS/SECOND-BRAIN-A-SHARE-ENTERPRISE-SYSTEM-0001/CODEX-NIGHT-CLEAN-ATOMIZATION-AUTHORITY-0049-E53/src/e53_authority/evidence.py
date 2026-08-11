"""Immutable source evidence.  This is the only gateway for exact source bytes."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping

from .utf8_index import ByteTruthIndex


def _canonical_identity(source_id: str, format_name: str, digest: str, length: int) -> Mapping[str, object]:
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("source_id must be a nonempty public identifier")
    if format_name not in {"text", "markdown", "json", "jsonl"}:
        raise ValueError("unsupported source format")
    return MappingProxyType(
        {
            "source_id": source_id,
            "format": format_name,
            "sha256": digest,
            "byte_length": length,
        }
    )


@dataclass(frozen=True, init=False, slots=True)
class SourceEvidence:
    """A copied public-safe source with identity derived from its bytes."""

    _data: bytes
    _index: ByteTruthIndex
    _sha256: str
    _identity: Mapping[str, object]

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("SourceEvidence must be created with SourceEvidence.from_bytes")

    @classmethod
    def from_bytes(cls, data: bytes, *, source_id: str, format_name: str) -> "SourceEvidence":
        copied = bytes(data)
        index = ByteTruthIndex(copied)
        digest = sha256(copied).hexdigest()
        instance = object.__new__(cls)
        object.__setattr__(instance, "_data", copied)
        object.__setattr__(instance, "_index", index)
        object.__setattr__(instance, "_sha256", digest)
        object.__setattr__(instance, "_identity", _canonical_identity(source_id, format_name, digest, len(copied)))
        return instance

    @property
    def sha256(self) -> str:
        return self._sha256

    @property
    def byte_length(self) -> int:
        return len(self._data)

    @property
    def identity(self) -> Mapping[str, object]:
        return self._identity

    @property
    def index(self) -> ByteTruthIndex:
        return self._index

    def bytes_slice(self, start: int, end: int) -> bytes:
        return self._index.slice(start, end)

    def text_slice(self, start: int, end: int) -> str:
        return self._index.text_slice(start, end)

    def verify(self) -> bool:
        return sha256(self._data).hexdigest() == self._sha256 and self._identity["byte_length"] == len(self._data)
