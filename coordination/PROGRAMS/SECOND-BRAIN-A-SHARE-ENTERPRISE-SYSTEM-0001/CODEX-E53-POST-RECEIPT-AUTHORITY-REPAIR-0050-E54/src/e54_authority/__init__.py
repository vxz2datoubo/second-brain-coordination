"""E54 public-safe source-bound authority package."""

from .authority import (
    AtomFactory,
    AuthorityError,
    CanonicalAtom,
    CanonicalField,
    CanonicalPacket,
    CanonicalPacketFactory,
    FinalizedLedger,
    FieldRule,
    OwnershipSpan,
    RelationFactory,
    SourceEvidence,
    SpanOwner,
    TypedRelation,
    VerifiedAtomRegistry,
    build_ledger,
    canonical_bytes,
    deep_freeze,
    recompute_manifest,
    thaw,
)
from .hygiene import HygieneReport, HistoryPath, scan_commit_range
from .topology import ReceiptTopologyReport, validate_receipt_fields, verify_final_receipt
from .provider import validate_environment_evidence, validate_matrix
from .mutations import MUTATION_SPECS, MutationResult, MutationSpec, run_mutation_matrix
from .provider_evidence import build_canonical_evidence, build_environment_evidence

__all__ = [
    "AtomFactory", "AuthorityError", "CanonicalAtom", "CanonicalField", "CanonicalPacket", "CanonicalPacketFactory",
    "FinalizedLedger", "FieldRule", "OwnershipSpan", "RelationFactory", "SourceEvidence", "SpanOwner",
    "TypedRelation", "VerifiedAtomRegistry", "build_ledger", "canonical_bytes", "deep_freeze",
    "recompute_manifest", "thaw",
    "HygieneReport", "HistoryPath", "scan_commit_range", "ReceiptTopologyReport",
    "validate_receipt_fields", "verify_final_receipt",
    "validate_environment_evidence", "validate_matrix",
    "MUTATION_SPECS", "MutationResult", "MutationSpec", "run_mutation_matrix",
    "build_canonical_evidence", "build_environment_evidence",
]
