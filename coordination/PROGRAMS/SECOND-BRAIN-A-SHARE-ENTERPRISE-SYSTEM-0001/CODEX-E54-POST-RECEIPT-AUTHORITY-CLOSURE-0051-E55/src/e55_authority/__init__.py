"""E55 public-safe source-bound authority candidates.

This package is task-local and research-only.  It does not activate any data,
model, provider, account, or trading capability.
"""

from .authority import (
    AdmissionPolicy,
    AtomFactory,
    AuthorityError,
    EvidenceLedger,
    EvidenceRecordFactory,
    PacketFactory,
    PacketSubrecordFactory,
    RelationFactory,
    SourceAdmissionFactory,
    build_ledger,
)

__all__ = [
    "AdmissionPolicy",
    "AtomFactory",
    "AuthorityError",
    "EvidenceLedger",
    "EvidenceRecordFactory",
    "PacketFactory",
    "PacketSubrecordFactory",
    "RelationFactory",
    "SourceAdmissionFactory",
    "build_ledger",
]
