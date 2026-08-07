"""E57 public-safe, synthetic authority boundary.

The package intentionally makes a narrow claim: a regular in-process consumer
cannot mint accepted records by importing this module or constructing values.
Issuance state and attestation keys live in a dedicated child process. This is
not a claim that hostile code with arbitrary memory/process control is secure.
"""

from .core import (
    AtomRecord,
    AuthorityError,
    AuthorityRecord,
    AuthoritySession,
    EvidenceRecord,
    PacketRecord,
    RelationRecord,
    SourceRecord,
)

__all__ = [
    "AtomRecord",
    "AuthorityError",
    "AuthorityRecord",
    "AuthoritySession",
    "EvidenceRecord",
    "PacketRecord",
    "RelationRecord",
    "SourceRecord",
]
