"""E56 fail-closed canonical-authority closure package."""

from .authority import (
    AdmissionPolicy,
    AtomFactory,
    AuthorityError,
    EvidenceFactory,
    PacketFactory,
    RelationFactory,
    SourceAdmission,
    build_ledger,
)

__all__ = [
    "AdmissionPolicy",
    "AtomFactory",
    "AuthorityError",
    "EvidenceFactory",
    "PacketFactory",
    "RelationFactory",
    "SourceAdmission",
    "build_ledger",
]
