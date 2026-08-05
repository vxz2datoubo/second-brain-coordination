"""E37 S3 — Atoms: byte-level semantic units with deterministic ID.

Each atom owns byte spans from adapter output. Classification is
driven by structural evidence (adapter role) NOT vocabulary heuristics.
Default = CLAIM; FACT only when explicit verifiable-rule evidence present.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict
import hashlib
from .boundary_table import OriginalByteIndex
from .adapter import AdapterSpan


# ── atom classification (structurally driven) ────────────────────────
ATOM_CLASSES = ("CLAIM", "FACT", "DEFINITION", "EVIDENCE", "UNKNOWN")

# Adapter role → atom class mapping (structural evidence only)
ROLE_TO_CLASS = {
    "header": "CLAIM",
    "content": "CLAIM",
    "list_item": "CLAIM",
    "code_block": "DEFINITION",
    "blockquote": "EVIDENCE",
    "table": "CLAIM",
    "json_string": "CLAIM",
    "json_number": "EVIDENCE",
    "json_bool": "EVIDENCE",
    "json_null": "CLAIM",
    "jsonl_line": "CLAIM",
    "conversation_role": "CLAIM",
    "conversation_user": "CLAIM",
    "conversation_assistant": "CLAIM",
    "conversation_system": "CLAIM",
    "conversation_body": "CLAIM",
    "object_start": "STRUCTURE",
    "object_end": "STRUCTURE",
    "array_start": "STRUCTURE",
    "array_end": "STRUCTURE",
    "colon": "STRUCTURE",
    "comma": "STRUCTURE",
}


# ── Atom ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Atom:
    atom_id: str           # sha256(full_deterministic_id)
    byte_start: int
    byte_end: int
    class_: str            # CLAIM|FACT|DEFINITION|EVIDENCE|UNKNOWN
    role: str              # Adapter role that produced it
    text_preview: str      # first 60 chars
    source_hash: str       # sha256 of source bytes
    source_byte_len: int

    @property
    def byte_len(self) -> int:
        return self.byte_end - self.byte_start


# ── atom extractor ───────────────────────────────────────────────────
def _build_id(
    byte_content: bytes,
    class_: str,
    role: str,
    source_hash: str,
    byte_start: int,
    byte_end: int,
) -> str:
    """Deterministic atom ID: SHA-256 of full provenance tuple."""
    raw = (
        f"class={class_}|role={role}|source={source_hash}"
        f"|byte=[{byte_start},{byte_end})|len={byte_end - byte_start}"
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def extract_atoms(
    index: OriginalByteIndex,
    spans: List[AdapterSpan],
) -> List[Atom]:
    """Extract atoms from adapter spans on original bytes.

    Each span becomes an atom with class derived from adapter role.
    STRUCTURE-class tokens are excluded from atom output (they are
    ledger-only). Default class is CLAIM unless verifiable structural
    evidence exists for FACT/EVIDENCE/DEFINITION.
    """
    b = index.source_bytes
    source_hash = hashlib.sha256(b).hexdigest()
    atoms: List[Atom] = []

    for span in spans:
        cls = ROLE_TO_CLASS.get(span.role, "CLAIM")
        if cls == "STRUCTURE":
            continue  # structural tokens are in ledger, not atoms

        seg = b[span.byte_start:span.byte_end]
        aid = _build_id(seg, cls, span.role, source_hash, span.byte_start, span.byte_end)
        text_preview = seg.decode("utf-8", errors="replace")[:60]

        atoms.append(Atom(
            atom_id=aid,
            byte_start=span.byte_start,
            byte_end=span.byte_end,
            class_=cls,
            role=span.role,
            text_preview=text_preview,
            source_hash=source_hash,
            source_byte_len=index.total_bytes,
        ))

    return atoms


# ── atom coverage helpers ───────────────────────────────────────────
def atom_coverage(index: OriginalByteIndex, atoms: List[Atom]) -> Tuple[int, int, float]:
    """Return (covered_bytes, total_bytes, coverage_ratio)."""
    total = index.total_bytes
    if total == 0:
        return (0, 0, 1.0)
    covered = 0
    for a in atoms:
        covered += a.byte_len
    return (covered, total, covered / total if total > 0 else 1.0)


def find_atom_gaps(index: OriginalByteIndex, atoms: List[Atom]) -> List[Tuple[int, int]]:
    """Find byte ranges not covered by any atom."""
    if not atoms:
        return [(0, index.total_bytes)] if index.total_bytes > 0 else []
    sorted_atoms = sorted(atoms, key=lambda a: a.byte_start)
    gaps = []
    cursor = 0
    for a in sorted_atoms:
        if cursor < a.byte_start:
            gaps.append((cursor, a.byte_start))
        cursor = max(cursor, a.byte_end)
    if cursor < index.total_bytes:
        gaps.append((cursor, index.total_bytes))
    return gaps
