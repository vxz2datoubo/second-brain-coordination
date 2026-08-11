"""E40 S1 — Exact one-owner byte ledger.

ATOM_CANDIDATE / STRUCTURE / UNKNOWN_ERROR.
Exact once per byte: no overlap, no gap post-finalize, no zero-length spill.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Set, Optional, Dict, FrozenSet


class Owner(str, Enum):
    ATOM_CANDIDATE = "ATOM_CANDIDATE"
    STRUCTURE = "STRUCTURE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass(frozen=True)
class OwnershipSpan:
    """Immutable ownership span."""
    byte_start: int
    byte_end: int  # exclusive
    owner: Owner
    label: str = ""

    def __post_init__(self):
        if self.byte_start < 0:
            raise ValueError(f"[out_of_range] negative start {self.byte_start}")
        if self.byte_end < 0:
            raise ValueError(f"[out_of_range] negative end {self.byte_end}")
        if self.byte_start > self.byte_end:
            raise ValueError(f"[inverted] start {self.byte_start} > end {self.byte_end}")
        if self.byte_start == self.byte_end:
            raise ValueError(f"[zero_length] span at {self.byte_start}")
        # Validate owner
        try:
            Owner(self.owner)
        except ValueError:
            raise ValueError(f"[invalid_owner] {self.owner!r}")

    def overlaps(self, other: "OwnershipSpan") -> bool:
        return self.byte_start < other.byte_end and other.byte_start < self.byte_end


class ByteLedger:
    """Exact one-owner per byte ledger.

    Properties:
    - ATOM_CANDIDATE, STRUCTURE, UNKNOWN_ERROR only
    - add() rejects overlap, out-of-range, illegal boundary, zero-length
    - finalize() detects gaps permanently
    - After finalize, no further add
    """

    def __init__(self, total_bytes: int):
        if total_bytes < 0:
            raise ValueError(f"[negative_total] {total_bytes}")
        self._total = total_bytes
        self._spans: List[OwnershipSpan] = []
        self._frozen = False
        self._finalized = False

    @property
    def total_bytes(self) -> int:
        return self._total

    @property
    def is_finalized(self) -> bool:
        return self._finalized

    def spans(self) -> Tuple[OwnershipSpan, ...]:
        return tuple(self._spans)

    def add(self, byte_start: int, byte_end: int, owner: Owner,
            label: str = "") -> OwnershipSpan:
        """Add an ownership span. Rejects duplicates/overlaps/range violations."""
        if self._finalized:
            raise RuntimeError("[finalized] cannot add after finalize")
        if self._frozen:
            raise RuntimeError("[frozen] ledger is frozen; cannot add")

        # Out of range
        if byte_start >= self._total:
            raise ValueError(f"[out_of_range] start {byte_start} >= total {self._total}")
        if byte_end > self._total:
            raise ValueError(f"[out_of_range] end {byte_end} > total {self._total}")

        span = OwnershipSpan(byte_start, byte_end, Owner(owner), label)

        # Check overlap with existing
        for existing in self._spans:
            if span.overlaps(existing):
                raise ValueError(
                    f"[overlap] new ({byte_start},{byte_end}) "
                    f"overlaps existing ({existing.byte_start},{existing.byte_end})"
                )

        self._spans.append(span)
        return span

    def freeze(self):
        """Freeze the ledger (no more adds), but finalize not yet called."""
        self._frozen = True

    def finalize(self):
        """Check coverage and freeze permanently. Raises on gaps."""
        if self._finalized:
            return
        self._frozen = True
        gaps = self._find_gaps()
        if gaps:
            gap_desc = ", ".join(f"({s},{e})" for s, e in gaps[:5])
            raise ValueError(f"[finalize_failed] {len(gaps)} gaps: [{gap_desc}]")
        self._finalized = True

    def _find_gaps(self) -> List[Tuple[int, int]]:
        gaps: List[Tuple[int, int]] = []
        spans = sorted(self._spans, key=lambda s: s.byte_start)
        cursor = 0
        for s in spans:
            if s.byte_start > cursor:
                gaps.append((cursor, s.byte_start))
            cursor = max(cursor, s.byte_end)
        if cursor < self._total:
            gaps.append((cursor, self._total))
        return gaps

    def coverage(self) -> Dict:
        """Return diagnostics dict."""
        spans = sorted(self._spans, key=lambda s: s.byte_start)
        covered = sum(s.byte_end - s.byte_start for s in spans)
        owners: Dict[str, int] = {}
        for s in spans:
            owners[s.owner.value] = owners.get(s.owner.value, 0) + (s.byte_end - s.byte_start)
        gaps = self._find_gaps() if not self._finalized else []
        return {
            "total_bytes": self._total,
            "covered_bytes": covered,
            "spans_count": len(spans),
            "gaps": [(g, h) for g, h in gaps],
            "gap_count": len(gaps),
            "owners": owners,
            "finalized": self._finalized,
        }
