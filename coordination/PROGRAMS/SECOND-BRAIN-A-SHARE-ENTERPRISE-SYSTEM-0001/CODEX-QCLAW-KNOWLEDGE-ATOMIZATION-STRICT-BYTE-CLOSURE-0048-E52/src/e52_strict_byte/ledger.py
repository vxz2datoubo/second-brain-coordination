"""Finalized exact-one-owner ledgers for E52 S1."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class Owner(str, Enum):
    ATOM_CANDIDATE = "ATOM_CANDIDATE"
    STRUCTURE = "STRUCTURE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass(frozen=True, slots=True)
class OwnershipSpan:
    byte_start: int
    byte_end: int
    owner: Owner
    label: str

    def __post_init__(self) -> None:
        if self.byte_start < 0 or self.byte_end <= self.byte_start:
            raise ValueError("ownership spans must be non-empty and non-negative")


class FinalizedLedger:
    """Immutable, sorted byte ownership partition."""

    __slots__ = ("_total_bytes", "_spans", "_manifest", "_frozen")

    def __init__(self, total_bytes: int, spans: tuple[OwnershipSpan, ...]):
        object.__setattr__(self, "_frozen", False)
        object.__setattr__(self, "_total_bytes", int(total_bytes))
        object.__setattr__(self, "_spans", tuple(spans))
        counts: dict[str, int] = {owner.value: 0 for owner in Owner}
        for span in spans:
            counts[span.owner.value] += span.byte_end - span.byte_start
        object.__setattr__(self, "_manifest", MappingProxyType(
            {
                "total_bytes": total_bytes,
                "span_count": len(spans),
                "owner_bytes": MappingProxyType(counts),
                "finalized": True,
            }
        ))
        object.__setattr__(self, "_frozen", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError(f"FinalizedLedger is immutable: {name}")
        object.__setattr__(self, name, value)

    @property
    def total_bytes(self) -> int:
        return self._total_bytes

    def spans(self) -> tuple[OwnershipSpan, ...]:
        return self._spans

    def manifest(self) -> Mapping[str, object]:
        return self._manifest


class LedgerBuilder:
    """Mutable only until `finalize`; validates range, overlap and full coverage."""

    __slots__ = ("_total_bytes", "_spans", "_finalized")

    def __init__(self, total_bytes: int):
        if total_bytes < 0:
            raise ValueError("total_bytes must be non-negative")
        self._total_bytes = total_bytes
        self._spans: list[OwnershipSpan] = []
        self._finalized = False

    def add(self, byte_start: int, byte_end: int, owner: Owner, label: str) -> None:
        if self._finalized:
            raise RuntimeError("cannot add after ledger finalization")
        span = OwnershipSpan(byte_start, byte_end, Owner(owner), label)
        if span.byte_end > self._total_bytes:
            raise ValueError("ownership span exceeds source length")
        for existing in self._spans:
            if span.byte_start < existing.byte_end and existing.byte_start < span.byte_end:
                raise ValueError("ownership overlap")
        self._spans.append(span)

    def finalize(self) -> FinalizedLedger:
        if self._finalized:
            raise RuntimeError("ledger is already finalized")
        ordered = tuple(sorted(self._spans, key=lambda span: (span.byte_start, span.byte_end, span.label)))
        cursor = 0
        for span in ordered:
            if span.byte_start != cursor:
                raise ValueError(f"ledger gap before byte {span.byte_start}")
            cursor = span.byte_end
        if cursor != self._total_bytes:
            raise ValueError(f"ledger gap after byte {cursor}")
        self._finalized = True
        return FinalizedLedger(self._total_bytes, ordered)
