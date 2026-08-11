"""E40 S4 — Atoms, Relations, Packet with verified semantics."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import hashlib
import json as _json

from .ledger import OwnershipSpan, Owner


class AtomField(str, Enum):
    """Seven semantic fields per atom."""
    CONDITION = "condition"
    EXCEPTION = "exception"
    NEGATION = "negation"
    TEMPORAL_SCOPE = "temporal_scope"
    ASSUMPTION = "assumption"
    EVIDENCE_STATUS = "evidence_status"
    APPLICABILITY = "applicability"


@dataclass
class Atom:
    """A knowledge atom with deterministic ID."""
    atom_id: str
    byte_start: int
    byte_end: int
    text: bytes
    classification: str = "CLAIM"  # Default CLAIM — never auto-upgrade to FACT
    fields: Dict[str, str] = field(default_factory=lambda: {
        f.value: "UNSPECIFIED" for f in AtomField
    })
    source_blob_sha: str = ""


def atom_id(owner_span: OwnershipSpan, text: bytes, classification: str) -> str:
    """Deterministic atom identifier."""
    h = hashlib.sha256()
    h.update(str(owner_span.byte_start).encode())
    h.update(str(owner_span.byte_end).encode())
    h.update(text)
    h.update(classification.encode())
    return h.hexdigest()


def extract_atoms(spans: List[OwnershipSpan], source: bytes) -> List[Atom]:
    """Extract atoms from ownership spans that are ATOM_CANDIDATE."""
    atoms: List[Atom] = []
    for span in spans:
        if span.owner != Owner.ATOM_CANDIDATE:
            continue
        text = source[span.byte_start:span.byte_end]
        aid = atom_id(span, text, "CLAIM")
        atoms.append(Atom(
            atom_id=aid,
            byte_start=span.byte_start,
            byte_end=span.byte_end,
            text=text,
            classification="CLAIM",
            fields={f.value: "UNSPECIFIED" for f in AtomField},
        ))
    return atoms
