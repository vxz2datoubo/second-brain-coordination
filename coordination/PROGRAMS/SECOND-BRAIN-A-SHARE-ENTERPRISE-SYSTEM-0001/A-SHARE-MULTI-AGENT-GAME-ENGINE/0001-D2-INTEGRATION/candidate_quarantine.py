"""Fail-closed candidate knowledge quarantine for synthetic D2 compatibility.

This module accepts only synthetic fixtures.  It neither fetches nor imports
candidate knowledge, and it cannot promote a claim, probability, identity, or
signal into runtime state.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple


PORT_SCHEMA_VERSION = "1.0"
SYNTHETIC_CAPABILITY = "SYNTHETIC_RESEARCH_ONLY"
CANONICAL_FAMILIES = (
    "RETAIL",
    "INSTITUTIONAL_QUANT",
    "ACTIVE_CAPITAL",
    "POLICY_INDUSTRIAL_FOREIGN_AGGREGATE",
)
IMMUTABLE_SOURCE_TRANSLATIONS = {
    ("retail", "synthetic-retail"): "RETAIL",
    ("institutional_quant", "synthetic-systematic"): "INSTITUTIONAL_QUANT",
    ("active_capital", "synthetic-event-driven"): "ACTIVE_CAPITAL",
    ("policy_industrial_foreign_aggregate", "synthetic-policy"): "POLICY_INDUSTRIAL_FOREIGN_AGGREGATE",
}
DEPRECATED_CANONICAL_LABELS = {"LargeCapital", "QuantStrategy", "ActiveSpeculative"}
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class CandidateEnvelope:
    source_schema_version: str
    source_commit_lock: str
    artifact_hashes: Tuple[str, ...]
    verifier_command: str
    verifier_evidence_hashes: Tuple[str, ...]
    status: str
    authority_write: bool
    source_capability: str
    source_family_label: str
    source_subtype_label: str
    canonical_family_label: Optional[str]
    target_kind: str
    identity_claimed: bool
    deterministic_status: str
    run_attestations: Tuple["RunAttestation", ...] = ()


@dataclass(frozen=True)
class RunAttestation:
    command: str
    exit_code: int
    stdout_hash: str
    stderr_hash: str
    normalized_package_hash: str


@dataclass(frozen=True)
class ClaimEvidenceEnvelope:
    """Candidate-only payload shape. Text is a synthetic fixture, never imported truth."""

    candidate_claim_id: str
    claim_kind: str
    synthetic_fixture_text: str
    evidence_refs: Tuple[str, ...]
    counterevidence_refs: Tuple[str, ...]
    unknown_refs: Tuple[str, ...]
    expires_at_ns: int
    authority_write: bool = False
    promotion: str = "CANDIDATE_ONLY"


@dataclass(frozen=True)
class OntologyTranslation:
    source_family_label: str
    source_subtype_label: str
    canonical_family: str
    status: str
    rationale: str


@dataclass(frozen=True)
class QuarantineDecision:
    accepted: bool
    reason_codes: Tuple[str, ...]
    translation: OntologyTranslation


def _valid_text(value: object, maximum: int = 240) -> bool:
    return isinstance(value, str) and bool(value) and len(value) <= maximum


def _valid_hashes(values: object, matcher: re.Pattern[str]) -> bool:
    return isinstance(values, tuple) and bool(values) and all(isinstance(value, str) and bool(matcher.fullmatch(value)) for value in values)


def negotiate_schema(source_version: object) -> Tuple[bool, str]:
    if not isinstance(source_version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+", source_version):
        return False, "INVALID_SOURCE_SCHEMA_VERSION"
    if source_version.split(".", 1)[0] != PORT_SCHEMA_VERSION.split(".", 1)[0]:
        return False, "INCOMPATIBLE_SOURCE_SCHEMA_MAJOR"
    return True, "SCHEMA_MAJOR_COMPATIBLE"


def translate_ontology(source_family_label: object, source_subtype_label: object, canonical_family_label: object) -> OntologyTranslation:
    source_family = source_family_label if isinstance(source_family_label, str) else ""
    source_subtype = source_subtype_label if isinstance(source_subtype_label, str) else ""
    if canonical_family_label in DEPRECATED_CANONICAL_LABELS:
        return OntologyTranslation(source_family, source_subtype, "UNMAPPED_UNKNOWN", "REJECTED", "DEPRECATED_LABEL_PRESENTED_AS_CANONICAL")
    derived = IMMUTABLE_SOURCE_TRANSLATIONS.get((source_family, source_subtype))
    if derived is None:
        return OntologyTranslation(source_family, source_subtype, "UNMAPPED_UNKNOWN", "REJECTED", "UNMAPPED_SOURCE_TRANSLATION")
    if canonical_family_label is not None and canonical_family_label != derived:
        return OntologyTranslation(source_family, source_subtype, "UNMAPPED_UNKNOWN", "REJECTED", "ADVISORY_CANONICAL_LABEL_MISMATCH")
    if canonical_family_label is not None and canonical_family_label not in CANONICAL_FAMILIES:
        return OntologyTranslation(source_family, source_subtype, "UNMAPPED_UNKNOWN", "REJECTED", "UNKNOWN_CANONICAL_FAMILY")
    if canonical_family_label == derived:
        return OntologyTranslation(source_family, source_subtype, derived, "MAPPED", "IMMUTABLE_TRANSLATION_CONFIRMED")
    if derived in CANONICAL_FAMILIES:
        return OntologyTranslation(source_family, source_subtype, derived, "MAPPED", "IMMUTABLE_TRANSLATION_DERIVED")
    return OntologyTranslation(source_family, source_subtype, "UNMAPPED_UNKNOWN", "REJECTED", "UNKNOWN_SOURCE_FAMILY_LABEL")


def derive_determinism_status(attestations: object) -> Tuple[bool, str]:
    """Accept exactly three independently recorded, hash-identical successful runs."""
    if not isinstance(attestations, tuple) or len(attestations) != 3:
        return False, "EXACTLY_THREE_RUN_ATTESTATIONS_REQUIRED"
    if any(not isinstance(item, RunAttestation) for item in attestations):
        return False, "INVALID_RUN_ATTESTATION"
    if any(not _valid_text(item.command) or item.exit_code != 0 for item in attestations):
        return False, "RUN_COMMAND_OR_EXIT_INVALID"
    hashes = tuple(item.normalized_package_hash for item in attestations)
    if any(not _HEX64.fullmatch(item.stdout_hash) or not _HEX64.fullmatch(item.stderr_hash) or not _HEX64.fullmatch(item.normalized_package_hash) for item in attestations):
        return False, "RUN_ATTESTATION_HASH_INVALID"
    if len(set(hashes)) != 1:
        return False, "RUN_PACKAGE_HASH_MISMATCH"
    if len({(item.command, item.stdout_hash, item.stderr_hash) for item in attestations}) != 3:
        return False, "DUPLICATE_OR_REUSED_RUN_EVIDENCE"
    return True, "VERIFIED_THREE_RUN_DETERMINISM"


def validate_claim_envelope(envelope: object, now_ns: int) -> Tuple[bool, Tuple[str, ...]]:
    if not isinstance(envelope, ClaimEvidenceEnvelope):
        return False, ("INVALID_CLAIM_ENVELOPE_OBJECT",)
    if not _valid_text(envelope.candidate_claim_id) or envelope.claim_kind != "SYNTHETIC_FIXTURE":
        return False, ("NON_SYNTHETIC_OR_INVALID_CLAIM_KIND",)
    if not _valid_text(envelope.synthetic_fixture_text) or not _valid_hashes(envelope.evidence_refs, _HEX64):
        return False, ("INVALID_SYNTHETIC_CLAIM_OR_EVIDENCE",)
    if not isinstance(envelope.counterevidence_refs, tuple) or not isinstance(envelope.unknown_refs, tuple):
        return False, ("INVALID_COUNTER_OR_UNKNOWN_REFS",)
    if any(not isinstance(item, str) for item in envelope.counterevidence_refs + envelope.unknown_refs):
        return False, ("INVALID_COUNTER_OR_UNKNOWN_REF_VALUE",)
    if not isinstance(envelope.expires_at_ns, int) or isinstance(envelope.expires_at_ns, bool) or envelope.expires_at_ns <= now_ns:
        return False, ("CANDIDATE_CLAIM_EXPIRED_OR_INVALID",)
    if envelope.authority_write or envelope.promotion != "CANDIDATE_ONLY":
        return False, ("CLAIM_TO_FACT_OR_AUTHORITY_PROMOTION_REJECTED",)
    return True, ("CANDIDATE_CLAIM_QUARANTINED",)


def validate_candidate(envelope: object) -> QuarantineDecision:
    fallback = OntologyTranslation("", "", "UNMAPPED_UNKNOWN", "REJECTED", "INVALID_ENVELOPE")
    if not isinstance(envelope, CandidateEnvelope):
        return QuarantineDecision(False, ("INVALID_CANDIDATE_ENVELOPE_OBJECT",), fallback)
    translation = translate_ontology(envelope.source_family_label, envelope.source_subtype_label, envelope.canonical_family_label)
    reasons: list[str] = []
    compatible, schema_reason = negotiate_schema(envelope.source_schema_version)
    if not compatible:
        reasons.append(schema_reason)
    if not _HEX40.fullmatch(envelope.source_commit_lock or ""):
        reasons.append("ABBREVIATED_OR_INVALID_SOURCE_LOCK")
    if not _valid_hashes(envelope.artifact_hashes, _HEX64):
        reasons.append("MISSING_OR_INVALID_ARTIFACT_HASH")
    if not _valid_text(envelope.verifier_command):
        reasons.append("MISSING_VERIFIER_COMMAND")
    if not _valid_hashes(envelope.verifier_evidence_hashes, _HEX64):
        reasons.append("MISSING_VERIFIER_EVIDENCE_HASH")
    deterministic_ok, deterministic_reason = derive_determinism_status(envelope.run_attestations)
    if not deterministic_ok or envelope.deterministic_status != deterministic_reason:
        reasons.append(deterministic_reason)
    if envelope.status != "CANDIDATE" or envelope.authority_write:
        reasons.append("CANDIDATE_STATUS_OR_AUTHORITY_VIOLATION")
    if envelope.source_capability != SYNTHETIC_CAPABILITY:
        reasons.append("NON_SYNTHETIC_SOURCE_CAPABILITY")
    if envelope.target_kind != "CANDIDATE_CLAIM":
        reasons.append("CLAIM_TO_FACT_OR_RUNTIME_PROMOTION_REJECTED")
    if envelope.identity_claimed:
        reasons.append("IDENTITY_PROMOTION_REJECTED")
    if translation.status != "MAPPED":
        reasons.append(translation.rationale)
    if reasons:
        return QuarantineDecision(False, tuple(sorted(set(reasons))), translation)
    return QuarantineDecision(True, ("CANDIDATE_QUARANTINE_ACCEPTED", "NO_AUTHORITY_WRITE", "SYNTHETIC_FIXTURE_ONLY"), translation)
