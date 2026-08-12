"""ingestion — E50 multi-source adapter.

D1: every adapter emits immutable provenance (source URI / class / hash / byte range).
    No silent defaults. Private sources refused (see source_policy).

D2: ASR / chat / OCR inputs go through E48 L1 reconstructor (fail-closed semantics).
    For D1 we do not invoke the reconstructor here; D2 evaluation calls ingest_source
    + l1_reconstruct.reconstruct() externally.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional

from .source_policy import SourceClass, SourcePolicy, PrivateSourceRefused, DEFAULT_POLICY


class SourceRefused(PrivateSourceRefused):
    """Specific name for ingestion-layer refusal."""


@dataclass(frozen=True)
class SourceArtifact:
    """Immutable wrapper around a raw source.

    byte_range: (start, end) byte offsets into the artifact's raw text.
                Default (0, len(raw_text)).
    metadata: free-form provenance (e.g., {"author": "public-domain", "year": 1966}).
    """
    source_uri: str
    source_class: SourceClass
    raw_text: str
    is_private: bool = False
    byte_range: tuple = (0, 0)  # set in __post_init__
    l0_hash: str = ""           # set in __post_init__
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        # l0_hash: SHA-256 of raw text bytes (immutable L0 identity)
        if not self.l0_hash:
            object.__setattr__(self, "l0_hash",
                hashlib.sha256(self.raw_text.encode("utf-8")).hexdigest())
        # byte_range default
        if self.byte_range == (0, 0):
            object.__setattr__(self, "byte_range",
                (0, len(self.raw_text.encode("utf-8"))))

    def l0_size_bytes(self) -> int:
        return len(self.raw_text.encode("utf-8"))

    def slice_l0(self, start: int, end: int) -> str:
        """Return L0 byte slice (must equal atom.content for SOURCE_EXTRACT invariant)."""
        return self.raw_text.encode("utf-8")[start:end].decode("utf-8")


def _check_policy(policy: SourcePolicy, source_class: SourceClass,
                  is_private: bool, source_uri: str) -> None:
    try:
        policy.check(source_class=source_class, is_private=is_private, source_uri=source_uri)
    except PrivateSourceRefused as e:
        raise SourceRefused(str(e)) from e


def ingest_source(
    *,
    source_uri: str,
    source_class: SourceClass,
    raw_text: str,
    is_private: bool = False,
    metadata: Optional[dict] = None,
    policy: SourcePolicy = DEFAULT_POLICY,
) -> SourceArtifact:
    """Generic ingestion. Refuses private sources."""
    _check_policy(policy, source_class, is_private, source_uri)
    return SourceArtifact(
        source_uri=source_uri,
        source_class=source_class,
        raw_text=raw_text,
        is_private=is_private,
        metadata=dict(metadata or {}),
    )


def ingest_article(uri: str, text: str, **meta) -> SourceArtifact:
    return ingest_source(
        source_uri=uri,
        source_class=SourceClass.CLEAN_ARTICLE,
        raw_text=text,
        metadata=meta,
    )


def ingest_asr(uri: str, text: str, **meta) -> SourceArtifact:
    return ingest_source(
        source_uri=uri,
        source_class=SourceClass.NOISY_ASR,
        raw_text=text,
        metadata=meta,
    )


def ingest_chat(uri: str, text: str, **meta) -> SourceArtifact:
    return ingest_source(
        source_uri=uri,
        source_class=SourceClass.CHAT_DIALOGUE,
        raw_text=text,
        metadata=meta,
    )


def ingest_ocr(uri: str, text: str, **meta) -> SourceArtifact:
    return ingest_source(
        source_uri=uri,
        source_class=SourceClass.OCR_TYPO_HEAVY,
        raw_text=text,
        metadata=meta,
    )


def ingest_contradiction_pair(uri_a: str, text_a: str,
                              uri_b: str, text_b: str, **meta) -> tuple:
    """Returns (artifact_a, artifact_b)."""
    a = ingest_source(
        source_uri=uri_a,
        source_class=SourceClass.CONTRADICTION_PAIR,
        raw_text=text_a,
        metadata={**meta, "pair_role": "A"},
    )
    b = ingest_source(
        source_uri=uri_b,
        source_class=SourceClass.CONTRADICTION_PAIR,
        raw_text=text_b,
        metadata={**meta, "pair_role": "B"},
    )
    return a, b


def ingest_method(uri: str, text: str, **meta) -> SourceArtifact:
    return ingest_source(
        source_uri=uri,
        source_class=SourceClass.METHOD_SKILL,
        raw_text=text,
        metadata=meta,
    )