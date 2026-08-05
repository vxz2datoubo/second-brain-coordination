"""E36 S1 — CoverageValidator: exact-once coverage enforcement, real rejection.
Rule: every source byte must be owned by EXACTLY ONE span, at legal boundaries.
Raises CoverageError if violation found. Finalize() freezes mapping."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional, Callable
from .boundary_table import OriginalByteIndex


class CoverageError(ValueError):
    """Subclass with structured violation data."""
    def __init__(self, kind: str, detail: str, spans: List["Span"] = None):
        super().__init__(f"[{kind}] {detail}")
        self.kind = kind
        self.detail = detail
        self.spans = spans or []


@dataclass(frozen=True)
class Span:
    """A byte range claim on the source."""
    byte_start: int
    byte_end: int      # exclusive
    role: str = ""
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        if self.byte_start < 0 or self.byte_end < 0:
            raise CoverageError("out_of_range",
                f"Negative byte span [{self.byte_start}, {self.byte_end})")
        if self.byte_start > self.byte_end:
            raise CoverageError("inverted",
                f"Start > end: [{self.byte_start}, {self.byte_end})", [self])

    def byte_len(self) -> int:
        return self.byte_end - self.byte_start

    def overlaps(self, other: "Span") -> bool:
        return self.byte_start < other.byte_end and other.byte_start < self.byte_end


class CoverageValidator:
    """Tracks span coverage across byte range. Exact-once enforcement."""

    def __init__(self, index: OriginalByteIndex):
        self._index = index
        self._total = index.total_bytes
        self._spans: List[Span] = []
        self._byte_to_span: Dict[int, Span] = {}  # lazy, built on check
        self._frozen = False

    @property
    def spans(self) -> List[Span]:
        return list(self._spans)

    @property
    def frozen(self) -> bool:
        return self._frozen

    def add_span(self, span: Span):
        if self._frozen:
            raise CoverageError("frozen", "Cannot add spans after finalize")
        self._spans.append(span)

    def add(self, byte_start: int, byte_end: int, role: str = "", **meta):
        self.add_span(Span(byte_start, byte_end, role, meta))

    def check(self) -> Dict[str, object]:
        """Return: {ok, total_bytes, covered_bytes, uncovered_bytes, violations, gap_spans, overlap_zones, out_of_range, inverted, illegal_boundary, boundary_set}.
        Does NOT freeze — caller can fix and re-check."""
        violations: List[Dict] = []
        covered: Set[int] = set()

        # 1. Out-of-range + inverted
        for s in self._spans:
            if s.byte_start < 0 or s.byte_end > self._total:
                violations.append({
                    "kind": "out_of_range",
                    "span": (s.byte_start, s.byte_end, s.role),
                    "limit": self._total
                })
            if s.byte_start > s.byte_end:
                violations.append({
                    "kind": "inverted",
                    "span": (s.byte_start, s.byte_end, s.role)
                })

        # 2. Overlap detection
        sorted_spans = sorted(self._spans, key=lambda s: (s.byte_start, s.byte_end))
        overlap_zones: List[List[Span]] = []
        for i in range(len(sorted_spans)):
            a = sorted_spans[i]
            for j in range(i + 1, len(sorted_spans)):
                b = sorted_spans[j]
                if a.overlaps(b):
                    overlap_zones.append([a, b])

        # 3. Build coverage map (byte -> count)
        byte_counts: List[int] = [0] * self._total
        for s in self._spans:
            if s.byte_start < 0 or s.byte_end > self._total:
                continue
            for bi in range(s.byte_start, s.byte_end):
                byte_counts[bi] += 1

        # 4. Gaps and overlaps from map
        gaps: List[Tuple[int, int]] = []
        over_bytes: List[Tuple[int, int]] = []
        i = 0
        while i < self._total:
            if byte_counts[i] == 0:
                gs = i
                while i < self._total and byte_counts[i] == 0:
                    i += 1
                gaps.append((gs, i))
                continue
            elif byte_counts[i] > 1:
                os = i
                while i < self._total and byte_counts[i] > 1:
                    i += 1
                over_bytes.append((os, i))
                continue
            i += 1

        covered_count = sum(1 for c in byte_counts if c == 1)

        # 5. Illegal boundary check
        legal_bounds = self._index.boundary_bytes
        illegal: List[Tuple[int, int, str]] = []
        for s in self._spans:
            if s.byte_start not in legal_bounds:
                illegal.append((s.byte_start, s.byte_end, f"start@{s.byte_start} not on codepoint boundary", s.role))
            if s.byte_end != self._total and s.byte_end not in legal_bounds:
                illegal.append((s.byte_start, s.byte_end, f"end@{s.byte_end} not on codepoint boundary", s.role))

        result = {
            "ok": (len(violations) + len(overlap_zones) + len(gaps)
                   + len(over_bytes) + len(illegal)) == 0,
            "total_bytes": self._total,
            "covered_bytes": covered_count,
            "uncovered_bytes": self._total - covered_count,
            "violations": violations,
            "gap_spans": gaps,
            "overlap_zones": [(a.byte_start, a.byte_end, a.role, b.byte_start, b.byte_end, b.role) for a, b in overlap_zones],
            "out_of_range": [v for v in violations if v["kind"] == "out_of_range"],
            "inverted": [v for v in violations if v["kind"] == "inverted"],
            "illegal_boundary": illegal,
            "gap_count": len(gaps),
            "over_bytes_count": len(over_bytes),
            "span_count": len(self._spans),
        }
        return result

    def finalize(self):
        """Run check and freeze if and only if OK."""
        result = self.check()
        if not result["ok"]:
            raise CoverageError("finalize_failed",
                f"Cannot finalize: {result['gap_count']} gaps, "
                f"{len(result['overlap_zones'])} overlaps, "
                f"{len(result['violations'])} violations, "
                f"{len(result['illegal_boundary'])} illegal boundaries")
        self._frozen = True
        return result
