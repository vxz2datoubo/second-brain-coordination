"""E39 S4 — Conservative atom extraction with deterministic IDs.

Rules:
- Default owner is CLAIM, never FACT
- No vocabulary-level FACT upgrade (assertTrue never triggers FACT)
- Atom IDs are sha256 of deterministic components
- 7 semantic fields: condition, exception, negation, temporal_scope,
  assumption, evidence_status, applicability
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import hashlib
import json

from .utf8_guard import UTF8ByteIndex
from .ledger import ByteLedger, OwnerSpan, OWNER_ATOM_CANDIDATE, OWNER_STRUCTURE, OWNER_UNKNOWN_ERROR


# ═══════════════════════════════════════════════════════════════════════
# Atom types
# ═══════════════════════════════════════════════════════════════════════

ATOM_CLAIM = "CLAIM"
ATOM_FACT = "FACT"
ATOM_DEFINITION = "DEFINITION"
ATOM_QUESTION = "QUESTION"
ATOM_UNKNOWN = "UNKNOWN"

VALID_ATOM_TYPES = frozenset({ATOM_CLAIM, ATOM_FACT, ATOM_DEFINITION, ATOM_QUESTION, ATOM_UNKNOWN})

# FACT is NEVER assigned by automated extraction (only human/gate-level override)
# assertTrue / vocabulary analysis shall never trigger FACT.
ATOM_TYPE_ALWAYS_CLAIM = ATOM_CLAIM


# ═══════════════════════════════════════════════════════════════════════
# Atom
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Atom:
    """A knowledge atom extracted from source bytes."""
    atom_id: str
    atom_type: str  # CLAIM (default), FACT (manual only), DEFINITION, QUESTION, UNKNOWN
    content: str    # extracted text
    byte_start: int
    byte_end: int
    subject_family: str = ""
    subject_subtype: str = ""
    # 7 semantic fields
    condition: Optional[str] = None
    exception: Optional[str] = None
    negation: bool = False
    temporal_scope: Optional[str] = None
    assumption: Optional[str] = None
    evidence_status: str = "NONE"  # NONE, PARTIAL, DIRECT, VERIFIED
    applicability: str = "GENERAL"  # GENERAL, SPECIFIC, CONDITIONAL
    source_hash: str = ""
    source_commit: str = ""
    # Never FACT from automatic extraction
    policy_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "atom_id": self.atom_id,
            "atom_type": self.atom_type,
            "content": self.content,
            "byte_start": self.byte_start,
            "byte_end": self.byte_end,
            "subject_family": self.subject_family,
            "subject_subtype": self.subject_subtype,
            "condition": self.condition,
            "exception": self.exception,
            "negation": self.negation,
            "temporal_scope": self.temporal_scope,
            "assumption": self.assumption,
            "evidence_status": self.evidence_status,
            "applicability": self.applicability,
            "source_hash": self.source_hash,
            "source_commit": self.source_commit,
        }

    def to_bytes_repr(self) -> bytes:
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False).encode("utf-8")


# ═══════════════════════════════════════════════════════════════════════
# Deterministic ID generation
# ═══════════════════════════════════════════════════════════════════════

def _make_atom_id(
    content: str,
    byte_start: int,
    byte_end: int,
    atom_type: str,
    source_hash: str,
    policy_version: str = "1.0.0",
) -> str:
    """Generate deterministic SHA-256 atom ID.

    Components: normalized content + byte range + type + source hash + policy version.
    Does NOT include source_commit (may change).
    """
    canonical = json.dumps({
        "content": content,
        "byte_start": byte_start,
        "byte_end": byte_end,
        "type": atom_type,
        "source_hash": source_hash,
        "policy_version": policy_version,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════════════
# Atom extractor
# ═══════════════════════════════════════════════════════════════════════

def extract_atoms(
    index: UTF8ByteIndex,
    ledger: ByteLedger,
    source_hash: str = "",
    source_commit: str = "",
) -> List[Atom]:
    """Extract atoms from all ATOM_CANDIDATE spans in the ledger.

    Each span becomes a CLAIM atom by default. FACT is never assigned.

    Returns list of atoms with deterministic IDs.
    """
    source = index.source_bytes
    atoms: List[Atom] = []

    for span in ledger.spans:
        if span.owner != OWNER_ATOM_CANDIDATE:
            continue

        try:
            content = source[span.byte_start:span.byte_end].decode("utf-8", "strict")
        except UnicodeDecodeError:
            # Structured spans might not be valid UTF-8 text — skip
            continue

        if not content.strip():
            continue

        # Always CLAIM — never FACT from extraction
        atom_type = ATOM_CLAIM

        # Detect question marks → QUESTION type
        if content.strip().endswith("?"):
            atom_type = ATOM_QUESTION

        atom_id = _make_atom_id(
            content=content,
            byte_start=span.byte_start,
            byte_end=span.byte_end,
            atom_type=atom_type,
            source_hash=source_hash,
        )

        atoms.append(Atom(
            atom_id=atom_id,
            atom_type=atom_type,
            content=content,
            byte_start=span.byte_start,
            byte_end=span.byte_end,
            subject_family=span.label or "",
            source_hash=source_hash,
            source_commit=source_commit,
        ))

    return atoms
