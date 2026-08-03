"""E37 S1 — Exact-once byte ownership ledger.

Every source byte has exactly one owner: ATOM_CANDIDATE | STRUCTURE | UNKNOWN_ERROR.
Zero-length, overlap, omission, duplicate, out-of-range, inverted, illegal-boundary → fail closed.
Immutable after finalize().
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Optional, Set
from .boundary_table import OriginalByteIndex


class LedgerError(ValueError):
    """Structured exception for ledger violations."""


@dataclass(frozen=True)
class OwnerSpan:
    """A single ownership assignment for a byte range."""
    byte_start: int
    byte_end: int  # exclusive
    owner: str  # ATOM_CANDIDATE | STRUCTURE | UNKNOWN_ERROR
    label: str = ""  # human-readable tag

    def __post_init__(self):
        if self.byte_start < 0:
            raise LedgerError(f"[out_of_range] Negative start: {self.byte_start}")
        if self.byte_end < 0:
            raise LedgerError(f"[out_of_range] Negative end: {self.byte_end}")
        if self.byte_start > self.byte_end:
            raise LedgerError(f"[inverted] Start > end: [{self.byte_start}, {self.byte_end})")
        if self.byte_start == self.byte_end:
            raise LedgerError(f"[zero_length] Span [{self.byte_start}, {self.byte_end}) is empty")
        if self.owner not in ("ATOM_CANDIDATE", "STRUCTURE", "UNKNOWN_ERROR"):
            raise LedgerError(f"[invalid_owner] '{self.owner}' not in [ATOM_CANDIDATE, STRUCTURE, UNKNOWN_ERROR]")

    @property
    def length(self) -> int:
        return self.byte_end - self.byte_start


class ByteLedger:
    """Tracks exact-once ownership of every byte in the source."""

    def __init__(self, index: OriginalByteIndex):
        self._index = index
        self._total = index.total_bytes
        self._spans: List[OwnerSpan] = []
        self._frozen = False

    @property
    def total_bytes(self) -> int:
        return self._total

    @property
    def spans(self) -> Tuple[OwnerSpan, ...]:
        return tuple(self._spans)

    @property
    def frozen(self) -> bool:
        return self._frozen

    def add(self, byte_start: int, byte_end: int, owner: str, label: str = "") -> OwnerSpan:
        """Add an ownership span. Raises LedgerError on any violation."""
        if self._frozen:
            raise LedgerError("[frozen] Cannot add spans after finalize")

        span = OwnerSpan(byte_start, byte_end, owner, label)

        # Check out-of-range BEFORE boundary legality
        if byte_start > self._total:
            raise LedgerError(f"[out_of_range] Start {byte_start} > total {self._total}")
        if byte_end > self._total:
            raise LedgerError(f"[out_of_range] End {byte_end} > total {self._total}")
        # Check boundary legality
        legal = self._index.legal_boundaries
        if byte_start not in legal:
            raise LedgerError(f"[illegal_boundary] Start {byte_start} not on codepoint boundary")
        if byte_end not in legal and byte_end != self._total:
            raise LedgerError(f"[illegal_boundary] End {byte_end} not on codepoint boundary")

        # Check overlap with existing spans
        for existing in self._spans:
            if span.byte_start < existing.byte_end and existing.byte_start < span.byte_end:
                raise LedgerError(
                    f"[overlap] New [{span.byte_start},{span.byte_end}) "
                    f"overlaps existing [{existing.byte_start},{existing.byte_end}) '{existing.owner}'"
                )

        self._spans.append(span)
        return span

    def check(self) -> Dict:
        """Return diagnostics: gaps, overlaps, coverage, total, spans."""
        if len(self._spans) == 0:
            return {"ok": self._total == 0, "total": self._total, "covered": 0,
                    "gaps": [(0, self._total)], "gap_count": 1 if self._total > 0 else 0,
                    "overlap_count": 0, "spans": 0, "owners": {}}

        sorted_spans = sorted(self._spans, key=lambda s: s.byte_start)
        gaps = []
        pos = 0

        for s in sorted_spans:
            if pos < s.byte_start:
                gaps.append((pos, s.byte_start))
            pos = max(pos, s.byte_end)

        if pos < self._total:
            gaps.append((pos, self._total))

        covered = sum(s.length for s in self._spans)

        # Count by owner
        owners = {}
        for s in self._spans:
            owners[s.owner] = owners.get(s.owner, 0) + s.length

        return {
            "ok": len(gaps) == 0 and covered == self._total,
            "total": self._total,
            "covered": covered,
            "gaps": gaps,
            "gap_count": len(gaps),
            "overlap_count": 0,  # overlaps prevented at add time
            "spans": len(self._spans),
            "owners": owners,
        }

    def finalize(self) -> Dict:
        """Finalize and return check(). Raises LedgerError if gaps exist."""
        self._frozen = True
        result = self.check()
        if not result["ok"]:
            raise LedgerError(
                f"[finalize_failed] Cannot finalize: {result['gap_count']} gaps, "
                f"covered {result['covered']}/{self._total}"
            )
        return result

    def owner_at(self, byte_offset: int) -> Optional[str]:
        """Return the owner for a specific byte, or None if uncovered."""
        for s in self._spans:
            if s.byte_start <= byte_offset < s.byte_end:
                return s.owner
        return None

    def all_owners(self) -> Dict[str, List[OwnerSpan]]:
        """Group spans by owner type."""
        result: Dict[str, List[OwnerSpan]] = {}
        for s in self._spans:
            result.setdefault(s.owner, []).append(s)
        return result
