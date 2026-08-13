"""Evidence matrix schema for E50 audit dimensions.

Each dimension (D1..D12) is rated PASS / PARTIAL / FAIL with attached
evidence (positive checks, negative checks, machine receipts, hand
observations). The matrix is bound to the exact vendored canonical head.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


VERDICT_PASS = "PASS"
VERDICT_PARTIAL = "PARTIAL"
VERDICT_FAIL = "FAIL"
VERDICT_BLOCKED = "BLOCKED"  # canonical capability missing on main
VERDICT_NOT_AVAILABLE = "NOT_AVAILABLE"  # cannot exercise at audit time


@dataclass
class Evidence:
    check_id: str
    description: str
    passed: bool
    detail: str = ""


@dataclass
class DimensionVerdict:
    dimension: str            # "D1", ..., "D12"
    title: str
    verdict: str              # VERDICT_*
    rationale: str
    evidence: list[Evidence] = field(default_factory=list)
    critical: bool = False    # critical gates stay NOT_READY if not PASS
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "title": self.title,
            "verdict": self.verdict,
            "rationale": self.rationale,
            "critical": self.critical,
            "notes": self.notes,
            "evidence": [asdict(e) for e in self.evidence],
        }


@dataclass
class EvidenceMatrix:
    canonical_head_sha: str
    vendor_root: str
    dimensions: list[DimensionVerdict] = field(default_factory=list)

    def get(self, dimension: str) -> DimensionVerdict | None:
        for d in self.dimensions:
            if d.dimension == dimension:
                return d
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_head_sha": self.canonical_head_sha,
            "vendor_root": self.vendor_root,
            "dimensions": [d.to_dict() for d in self.dimensions],
        }

    def critical_gates_summary(self) -> dict[str, str]:
        return {d.dimension: d.verdict for d in self.dimensions if d.critical}


@dataclass
class CoverageEntry:
    fixture_id: str
    fixture_class: str       # e.g. "asr", "ocr", "chat", "contradiction_pair"
    expected_atom_types: list[str]
    extracted_atom_types: list[str]
    expected_relations: list[str]
    extracted_relations: list[str]
    miss_count: int
    distort_count: int
    unsupported_count: int
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoverageReport:
    fixture_total: int
    correctly_extracted: int
    missed: int
    distorted: int
    unsupported: int
    entries: list[CoverageEntry] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture_total": self.fixture_total,
            "correctly_extracted": self.correctly_extracted,
            "missed": self.missed,
            "distorted": self.distorted,
            "unsupported": self.unsupported,
            "entries": [e.to_dict() for e in self.entries],
            "notes": self.notes,
        }