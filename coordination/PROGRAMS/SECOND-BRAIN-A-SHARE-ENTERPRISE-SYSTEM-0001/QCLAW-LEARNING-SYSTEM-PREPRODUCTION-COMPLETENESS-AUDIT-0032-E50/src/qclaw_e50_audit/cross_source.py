"""cross_source — D4 stable semantic object identity, dedup, contradiction, supersession.

D4 pass criteria:
  - stable identity: same content → same canonical_id across reruns + reorderings
  - dedup: identical / near-identical atoms detected (configurable threshold)
  - contradiction: explicit CONTRADICTS edge between versioned variants
  - supersession: newer source supersedes older with provenance retained
  - no silent overwrite (earlier content never destroyed)

Identity canonicalization:
  - canonical_id = sha256(canonical_form) where canonical_form = NFC-normalized text + structural hash of byte span
  - this is stable across Python 3.11 / 3.13 (NFC is deterministic; no platform dependence)
"""
from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass, field
from enum import Enum


class CrossSourceRelation(str, Enum):
    CONTRADICTS = "CONTRADICTS"
    SUPERSEDES = "SUPERSEDES"
    DUPLICATE_OF = "DUPLICATE_OF"
    NEAR_DUPLICATE_OF = "NEAR_DUPLICATE_OF"


CONTRADICTS = CrossSourceRelation.CONTRADICTS
SUPERSEDES = CrossSourceRelation.SUPERSEDES
DUPLICATE_OF = CrossSourceRelation.DUPLICATE_OF
NEAR_DUPLICATE_OF = CrossSourceRelation.NEAR_DUPLICATE_OF


def canonical_form(content: str, source_uri: str, byte_start: int, byte_end: int) -> str:
    """NFC-normalize + structural fingerprint.

    The fingerprint is the concatenation of source_uri + normalized content + byte span.
    NFC normalization is the same on Python 3.11 and 3.13 (Unicode standard, deterministic).
    """
    nfc = unicodedata.normalize("NFC", content)
    return f"{source_uri}|{byte_start}|{byte_end}|{nfc}"


def canonical_id(content: str, source_uri: str, byte_start: int, byte_end: int) -> str:
    return hashlib.sha256(
        canonical_form(content, source_uri, byte_start, byte_end).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class SemanticObjectIdentity:
    """An identity record for one semantic object across versions/sources."""
    canonical_id: str
    content_nfc: str
    source_uri: str
    byte_start: int
    byte_end: int
    version: int = 1

    @classmethod
    def from_atom(cls, *, source_uri: str, content: str,
                  byte_start: int, byte_end: int, version: int = 1) -> "SemanticObjectIdentity":
        nfc = unicodedata.normalize("NFC", content)
        cid = canonical_id(content, source_uri, byte_start, byte_end)
        return cls(
            canonical_id=cid,
            content_nfc=nfc,
            source_uri=source_uri,
            byte_start=byte_start,
            byte_end=byte_end,
            version=version,
        )


@dataclass
class CrossSourceMaster:
    """Master index for stable identity + dedup + contradiction + supersession.

    Records identities by canonical_id. Earlier content is NEVER overwritten;
    supersession creates a NEW identity entry with version+1 and an explicit
    SUPERSEDES edge to the prior canonical_id.
    """
    identities: dict = field(default_factory=dict)  # canonical_id -> SemanticObjectIdentity
    supersession_edges: list = field(default_factory=list)  # (newer_id, older_id)
    contradiction_edges: list = field(default_factory=list)  # (id_a, id_b)
    duplicate_edges: list = field(default_factory=list)  # (id_a, id_b, kind)

    def register(self, ident: SemanticObjectIdentity) -> str:
        """Idempotent register: returns canonical_id."""
        if ident.canonical_id not in self.identities:
            self.identities[ident.canonical_id] = ident
        return ident.canonical_id

    def supersede(self, newer: SemanticObjectIdentity, older_id: str) -> str:
        """Mark newer as superseding older. Both identities retained; older NOT deleted."""
        self.register(newer)
        edge = (newer.canonical_id, older_id)
        if edge not in self.supersession_edges:
            self.supersession_edges.append(edge)
        return newer.canonical_id

    def contradict(self, id_a: str, id_b: str) -> None:
        edge = tuple(sorted([id_a, id_b]))
        if edge not in self.contradiction_edges:
            self.contradiction_edges.append(edge)

    def dedup(self, id_a: str, id_b: str, near: bool = False) -> None:
        kind = NEAR_DUPLICATE_OF if near else DUPLICATE_OF
        edge = (tuple(sorted([id_a, id_b])), kind)
        if edge not in self.duplicate_edges:
            self.duplicate_edges.append(edge)

    def query_superseded(self, canonical_id: str) -> list:
        """Return list of canonical_ids that supersede the given one."""
        return [n for (n, o) in self.supersession_edges if o == canonical_id]

    def is_superseded(self, canonical_id: str) -> bool:
        return bool(self.query_superseded(canonical_id))

    def stats(self) -> dict:
        return {
            "identities": len(self.identities),
            "supersession_edges": len(self.supersession_edges),
            "contradiction_edges": len(self.contradiction_edges),
            "duplicate_edges": len(self.duplicate_edges),
        }