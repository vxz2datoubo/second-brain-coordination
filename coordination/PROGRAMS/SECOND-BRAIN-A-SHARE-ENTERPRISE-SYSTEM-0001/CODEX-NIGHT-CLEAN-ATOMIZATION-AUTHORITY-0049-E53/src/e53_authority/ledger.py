"""A finalized ownership ledger bound to one SourceEvidence object."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Iterable, Mapping

from .evidence import SourceEvidence


class LedgerError(ValueError):
    pass


class SpanOwner(str, Enum):
    ATOM_CANDIDATE = "ATOM_CANDIDATE"
    STRUCTURAL = "STRUCTURAL"
    REDACTED = "REDACTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True, order=True)
class OwnershipSpan:
    start: int
    end: int
    owner: SpanOwner

    def __post_init__(self) -> None:
        if not isinstance(self.owner, SpanOwner):
            raise LedgerError("span owner must be a SpanOwner")
        if not isinstance(self.start, int) or not isinstance(self.end, int) or self.start < 0 or self.end <= self.start:
            raise LedgerError("span must have a positive, nonnegative range")


def _coverage_digest(evidence: SourceEvidence, spans: tuple[OwnershipSpan, ...]) -> str:
    canonical = {
        "source_sha256": evidence.sha256,
        "byte_length": evidence.byte_length,
        "spans": [{"start": item.start, "end": item.end, "owner": item.owner.value} for item in spans],
    }
    return sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True, init=False, slots=True)
class FinalizedLedger:
    _evidence: SourceEvidence
    _spans: tuple[OwnershipSpan, ...]
    _manifest: Mapping[str, object]

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("FinalizedLedger must be created with LedgerBuilder.finalize")

    @property
    def evidence(self) -> SourceEvidence:
        return self._evidence

    @property
    def spans(self) -> tuple[OwnershipSpan, ...]:
        return self._spans

    @property
    def coverage_manifest(self) -> Mapping[str, object]:
        return self._manifest

    def owner_for(self, start: int, end: int) -> SpanOwner:
        for item in self._spans:
            if item.start <= start and end <= item.end:
                return item.owner
        raise LedgerError("requested range is not ledger-owned")

    def is_exact_atom_candidate(self, start: int, end: int) -> bool:
        return any(item.start == start and item.end == end and item.owner is SpanOwner.ATOM_CANDIDATE for item in self._spans)

    def verify(self) -> bool:
        return self._manifest.get("coverage_sha256") == _coverage_digest(self._evidence, self._spans)


class LedgerBuilder:
    """Builds a total non-overlapping partition before finalization."""

    __slots__ = ("_evidence", "_spans", "_finalized")

    def __init__(self, evidence: SourceEvidence) -> None:
        if not isinstance(evidence, SourceEvidence) or not evidence.verify():
            raise LedgerError("ledger requires verified SourceEvidence")
        self._evidence = evidence
        self._spans: list[OwnershipSpan] = []
        self._finalized = False

    def add(self, start: int, end: int, owner: SpanOwner) -> "LedgerBuilder":
        if self._finalized:
            raise LedgerError("ledger is already finalized")
        span = OwnershipSpan(start, end, owner)
        if end > self._evidence.byte_length or not self._evidence.index.boundaries_are_utf8(start, end):
            raise LedgerError("span is outside exact UTF-8 source boundaries")
        self._spans.append(span)
        return self

    def finalize(self) -> FinalizedLedger:
        if self._finalized:
            raise LedgerError("ledger can only be finalized once")
        ordered = tuple(sorted(self._spans, key=lambda item: (item.start, item.end, item.owner.value)))
        cursor = 0
        totals: dict[str, int] = {owner.value: 0 for owner in SpanOwner}
        for span in ordered:
            if span.start != cursor:
                raise LedgerError("ledger must be a complete non-overlapping partition")
            cursor = span.end
            totals[span.owner.value] += span.end - span.start
        if cursor != self._evidence.byte_length:
            raise LedgerError("ledger does not cover all source bytes")
        digest = _coverage_digest(self._evidence, ordered)
        manifest = MappingProxyType(
            {
                "source_identity": dict(self._evidence.identity),
                "source_sha256": self._evidence.sha256,
                "byte_length": self._evidence.byte_length,
                "span_count": len(ordered),
                "owner_byte_totals": MappingProxyType(totals),
                "coverage_sha256": digest,
            }
        )
        instance = object.__new__(FinalizedLedger)
        object.__setattr__(instance, "_evidence", self._evidence)
        object.__setattr__(instance, "_spans", ordered)
        object.__setattr__(instance, "_manifest", manifest)
        self._finalized = True
        return instance
