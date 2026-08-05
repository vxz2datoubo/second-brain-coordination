"""E39 S1 — Exact-once byte-range owner ledger.

OwnerSpan: frozen namedtuple-like, ATOM_CANDIDATE | STRUCTURE | UNKNOWN_ERROR.
ByteLedger: immutable after finalize, exact-once coverage, EOF-exclusive boundaries.
Rejects: overlap, out-of-range, inverted, zero-length, illegal boundaries, duplicate.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Set, Dict, Tuple

from .utf8_guard import UTF8ByteIndex


# ═══════════════════════════════════════════════════════════════════════
# Owner enum
# ═══════════════════════════════════════════════════════════════════════

OWNER_ATOM_CANDIDATE = "ATOM_CANDIDATE"
OWNER_STRUCTURE = "STRUCTURE"
OWNER_UNKNOWN_ERROR = "UNKNOWN_ERROR"
VALID_OWNERS = frozenset({OWNER_ATOM_CANDIDATE, OWNER_STRUCTURE, OWNER_UNKNOWN_ERROR})


class LedgerError(ValueError):
    """Raised for any ledger invariant violation."""
    pass


# ═══════════════════════════════════════════════════════════════════════
# OwnerSpan
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OwnerSpan:
    """Immutable byte-range ownership claim.

    byte_end is EXCLUSIVE (EOF-relative).
    """
    byte_start: int
    byte_end: int          # exclusive
    owner: str
    label: str = ""

    def __post_init__(self):
        if self.byte_start < 0:
            raise LedgerError(f"[out_of_range] byte_start={self.byte_start} < 0")
        if self.byte_end < 0:
            raise LedgerError(f"[out_of_range] byte_end={self.byte_end} < 0")
        if self.byte_start > self.byte_end:
            raise LedgerError(
                f"[inverted] start={self.byte_start} > end={self.byte_end}"
            )
        if self.byte_start == self.byte_end:
            raise LedgerError(f"[zero_length] start==end={self.byte_start}")
        if self.owner not in VALID_OWNERS:
            raise LedgerError(
                f"[invalid_owner] '{self.owner}' not in {sorted(VALID_OWNERS)}"
            )

    @property
    def byte_length(self) -> int:
        return self.byte_end - self.byte_start

    def overlaps(self, other: "OwnerSpan") -> bool:
        """True if [start,end) ranges intersect (non-empty overlap)."""
        return self.byte_start < other.byte_end and other.byte_start < self.byte_end

    def __repr__(self) -> str:
        return (
            f"OwnerSpan({self.byte_start},{self.byte_end} "
            f"owner={self.owner} label={self.label!r} len={self.byte_length})"
        )


# ═══════════════════════════════════════════════════════════════════════
# ByteLedger
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ByteLedger:
    """Exact-once byte-range coverage ledger.

    - All spans must be within [0, total_bytes) with legal boundaries.
    - end=total_bytes is legal (marks last byte).
    - No overlap, no gaps after finalize.
    - Immutable after finalize().
    """
    index: UTF8ByteIndex

    def __post_init__(self):
        self._total = self.index.total_bytes
        self._spans: List[OwnerSpan] = []
        self._frozen = False
        self._boundaries: Set[int] = set(self.index.legal_boundaries)

    @property
    def total_bytes(self) -> int:
        return self._total

    @property
    def frozen(self) -> bool:
        return self._frozen

    def _check_not_frozen(self, action: str = "add"):
        if self._frozen:
            raise LedgerError(f"[frozen] Cannot {action}: ledger is finalized")

    def _check_boundary(self, pos: int):
        """Ensure pos is a legal codepoint boundary or EOF."""
        if pos == self._total:
            return  # EOF is always legal
        if pos not in self._boundaries:
            raise LedgerError(
                f"[illegal_boundary] byte {pos} is not a codepoint boundary "
                f"(legal boundaries near: {self._find_nearby(pos)})"
            )

    def _find_nearby(self, pos: int) -> List[int]:
        """Return nearby legal boundaries for error messages."""
        sorted_b = sorted(self._boundaries)
        result = []
        for b in sorted_b:
            if b < pos:
                result = [b]
            elif b > pos:
                result.append(b)
                return result[-3:]
        return result[-3:]

    def add(self, byte_start: int, byte_end: int,
            owner: str, label: str = "") -> OwnerSpan:
        """Add an ownership span. Validates all invariants before accepting.

        Raises LedgerError on: frozen, out-of-range, illegal boundary,
        inverted, zero-length, invalid owner, overlap.
        """
        self._check_not_frozen("add")

        # out-of-range
        if byte_start >= self._total:
            raise LedgerError(f"[out_of_range] start={byte_start} >= total={self._total}")
        if byte_end > self._total:
            raise LedgerError(f"[out_of_range] end={byte_end} > total={self._total}")

        # boundary check
        self._check_boundary(byte_start)
        self._check_boundary(byte_end)

        # build provisional span (triggers inverted/zero_length/invalid_owner)
        span = OwnerSpan(byte_start, byte_end, owner, label)

        # overlap check
        for existing in self._spans:
            if span.overlaps(existing):
                raise LedgerError(
                    f"[overlap] new {span} overlaps existing {existing}"
                )

        self._spans.append(span)
        return span

    def check(self) -> dict:
        """Return coverage diagnostics without mutating state."""
        total = self._total
        if total == 0:
            return {
                "total_bytes": 0, "covered": 0,
                "spans": 0, "gaps": [] if not self._spans else [],
                "gap_count": 0, "overlap_count": 0,
                "owners": {},
                "complete": True,
            }
        if not self._spans:
            return {
                "total_bytes": total, "covered": 0,
                "spans": 0, "gaps": [(0, total)],
                "gap_count": 1, "overlap_count": 0,
                "owners": {},
                "complete": False,
            }

        sorted_spans = sorted(self._spans, key=lambda s: s.byte_start)
        covered = 0
        gaps: List[Tuple[int, int]] = []
        cursor = 0
        overlap_count = 0
        owners: Dict[str, int] = {}

        for i, span in enumerate(sorted_spans):
            if span.byte_start < cursor:
                overlap_count += 1
            if span.byte_start > cursor:
                gaps.append((cursor, span.byte_start))
            covered += span.byte_length
            cursor = max(cursor, span.byte_end)
            owners[span.owner] = owners.get(span.owner, 0) + 1

        if cursor < total:
            gaps.append((cursor, total))

        # Verify overlap via pairwise check
        ov = 0
        for i in range(len(sorted_spans)):
            for j in range(i + 1, len(sorted_spans)):
                if sorted_spans[i].overlaps(sorted_spans[j]):
                    ov += 1

        return {
            "total_bytes": total,
            "covered": covered,
            "spans": len(self._spans),
            "gaps": gaps,
            "gap_count": len(gaps),
            "overlap_count": ov,
            "owners": owners,
            "complete": len(gaps) == 0 and ov == 0,
        }

    def finalize(self) -> "ByteLedger":
        """Freeze and verify exact-once 100% coverage.

        Raises LedgerError with gaps if coverage is incomplete.
        Returns self for chaining.
        """
        if self._frozen:
            return self
        diag = self.check()
        if diag["gaps"]:
            raise LedgerError(
                f"[finalize_failed] {diag['gap_count']} gaps: "
                f"{diag['gaps'][:5]}{'...' if len(diag['gaps']) > 5 else ''}"
            )
        self._frozen = True
        return self

    @property
    def spans(self) -> List[OwnerSpan]:
        return list(self._spans)
