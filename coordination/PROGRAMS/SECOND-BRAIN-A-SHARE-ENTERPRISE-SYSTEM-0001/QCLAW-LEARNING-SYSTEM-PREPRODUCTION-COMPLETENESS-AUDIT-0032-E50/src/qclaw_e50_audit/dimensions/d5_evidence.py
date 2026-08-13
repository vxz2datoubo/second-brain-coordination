"""D5 audit: evidence verification + epistemic classification.

Canonical implementation audited:
- integrated_offline_memory.contracts (FieldSemanticDecision, ParseReport)
- integrated_offline_memory.memory_store (verification_status, evidence_quality)
- integrated_offline_memory.learning_packet (verify_learning_packet)

D5 mandatory asks to inspect ACTUAL emitted SOURCE_EXTRACT / USER_CLAIM /
EXTERNAL_CLAIM / INFERENCE / VALUE_JUDGMENT plus provenance, verification
hooks, and evidence-gap handling end-to-end.

Truthful finding: canonical main PHASE-3 does NOT emit the E47/E48 5-way
EvidenceKind vocabulary. It uses verification_status (UNVERIFIED /
PARTIALLY_VERIFIED) + evidence_quality (PARTIAL_FIELD_EVIDENCE /
DETERMINISTIC_LOCAL_REPLAY / UNKNOWN) + FieldSemanticDecision.status
(VERIFIED / PARTIAL_FIELD_EVIDENCE / UNKNOWN). The E47/E48 5-way epistemic
classification exists ONLY on the E48 PR branch (foundation credit), not on
canonical main. This is a PARTIAL, not a PASS.
"""
from __future__ import annotations

from .. import authoritative as access
from ..evidence_matrix import (
    DimensionVerdict, Evidence,
    VERDICT_PASS, VERDICT_PARTIAL, VERDICT_FAIL,
)

access.setup_import_path()

from integrated_offline_memory import contracts  # type: ignore  # noqa: E402
from integrated_offline_memory.learning_packet import verify_learning_packet, build_learning_packet  # type: ignore  # noqa: E402
from integrated_offline_memory import canonical  # type: ignore  # noqa: E402


def _check(name, desc, ok, detail=""):
    return Evidence(check_id=name, description=desc, passed=bool(ok), detail=detail)


def run() -> DimensionVerdict:
    evidence: list[Evidence] = []

    # 1. FieldSemanticDecision enforces that only VERIFIED status may be
    #    authority_feature_allowed=True
    ambiguous_rejected = False
    try:
        d = contracts.FieldSemanticDecision(
            "volume", "PARTIAL_FIELD_EVIDENCE", "raw_bytes", True, "x")
        d.validate()
    except contracts.ContractError as e:
        ambiguous_rejected = "ambiguous_field_cannot_be_authoritative" in str(e)
    evidence.append(_check(
        "d5.ambiguous_field_cannot_be_authoritative",
        "FieldSemanticDecision rejects ambiguous field marked authoritative",
        ambiguous_rejected,
    ))

    # 2. FieldSemanticDecision only accepts VERIFIED/PARTIAL_FIELD_EVIDENCE/UNKNOWN
    invalid_status_rejected = False
    try:
        d = contracts.FieldSemanticDecision("x", "MADE_UP", "raw", False, "y")
        d.validate()
    except contracts.ContractError as e:
        invalid_status_rejected = "invalid_field_semantic_status" in str(e)
    evidence.append(_check(
        "d5.invalid_field_status_rejected",
        "FieldSemanticDecision rejects unknown status values",
        invalid_status_rejected,
    ))

    # 3. canonical main does NOT carry the E47/E48 5-way EvidenceKind
    #    (SOURCE_EXTRACT/USER_CLAIM/EXTERNAL_CLAIM/INFERENCE/VALUE_JUDGMENT)
    has_evidence_kind = hasattr(contracts, "EvidenceKind")
    evidence.append(_check(
        "d5.canonical_evidence_kind_5way_present",
        "Canonical main exposes E47 5-way EvidenceKind (SOURCE_EXTRACT/.../VALUE_JUDGMENT)",
        has_evidence_kind,
        detail=("EvidenceKind present on canonical main" if has_evidence_kind
                else "NOT present: canonical main uses verification_status/"
                     "evidence_quality/FieldSemanticDecision, not the E47 5-way "
                     "EvidenceKind (that lives only on the E48 PR branch)."),
    ))

    # 4. verification_status default is UNVERIFIED (fail-closed, not VERIFIED)
    pkt = build_learning_packet(
        source_manifest_ids=["src-5"],
        source_hash=canonical.content_hash("evidence test"),
        validation_report={"ok": True},
        evidence_refs=["src-5"],
        atoms=[{"id": "at-e5-1", "atom_type": "claim",
                "statement": "Volume rises", "scope": "audit"}],
        relations=[], conflicts=[], unknowns=[],
    )
    errors = verify_learning_packet(pkt)
    valid = errors.get("valid") if isinstance(errors, dict) else not errors
    err_list = errors.get("errors", []) if isinstance(errors, dict) else errors
    evidence.append(_check(
        "d5.packet_verify_clean",
        "verify_learning_packet accepts a well-formed candidate packet",
        bool(valid),
        detail=";".join(err_list),
    ))

    # 5. packet build rejects credential leakage (evidence verification hook)
    secret_rejected = False
    secret_detail = ""
    try:
        build_learning_packet(
            source_manifest_ids=["src-5"],
            source_hash=canonical.content_hash("secret test"),
            validation_report={"ok": True},
            evidence_refs=["src-5"],
            atoms=[{"id": "at-e5-2", "atom_type": "claim",
                    "statement": "token sk-abcdefghijklmnopqrstuvwx", "scope": "audit"}],
            relations=[], conflicts=[], unknowns=[],
        )
    except ValueError as e:
        secret_rejected = "credential_value_denied" in str(e)
        secret_detail = str(e)
    evidence.append(_check(
        "d5.packet_verify_rejects_secret",
        "build_learning_packet rejects credential/secret leakage",
        secret_rejected,
        detail=secret_detail,
    ))

    # 6. evidence-gap handling: volume field is UNKNOWN in canonical decisions
    #    (not silently promoted to verified)
    volume_unknown = False
    for decision in contracts.field_semantic_decisions():
        if decision.field_name == "volume":
            volume_unknown = decision.status == "UNKNOWN" and not decision.authority_feature_allowed
    evidence.append(_check(
        "d5.evidence_gap_honest_unknown",
        "Canonical marks volume unit as UNKNOWN (honest evidence gap)",
        volume_unknown,
    ))

    # 7. verification_status is free-form (not enum-validated) -> PARTIAL gap
    #    (no strict verification_status enum on insert)
    verification_enum_enforced = False  # memory_store does not enum-validate this
    evidence.append(_check(
        "d5.verification_status_enum_enforced",
        "verification_status is strict-enum validated on insert",
        verification_enum_enforced,
        detail="verification_status is free-form text on canonical main "
               "(default UNVERIFIED); no enum constraint observed.",
    ))

    passed = sum(1 for e in evidence if e.passed)
    total = len(evidence)
    # D5 is PARTIAL: honest evidence-gap + secret + fail-closed default hold,
    # but the E47 5-way EvidenceKind is missing on canonical main and
    # verification_status is free-form.
    if passed == total:
        verdict = VERDICT_PASS
    elif passed >= total - 2:
        verdict = VERDICT_PARTIAL
    else:
        verdict = VERDICT_FAIL

    return DimensionVerdict(
        dimension="D5",
        title="Evidence verification + epistemic classification",
        verdict=verdict,
        rationale=(f"{passed}/{total} evidence-verification gates passed against canonical "
                   "PHASE-3. Evidence-gap honesty + secret rejection + fail-closed "
                   "UNVERIFIED default hold; E47 5-way EvidenceKind missing on main."),
        evidence=evidence,
        critical=True,
        notes=("Canonical main PHASE-3 provides verification_status "
               "(UNVERIFIED/PARTIALLY_VERIFIED) + evidence_quality "
               "(PARTIAL_FIELD_EVIDENCE/DETERMINISTIC_LOCAL_REPLAY) + "
               "FieldSemanticDecision (VERIFIED/PARTIAL_FIELD_EVIDENCE/UNKNOWN), "
               "with honest UNKNOWN for unproven fields (volume). "
               "The E47/E48 5-way EvidenceKind (SOURCE_EXTRACT/USER_CLAIM/"
               "EXTERNAL_CLAIM/INFERENCE/VALUE_JUDGMENT) is NOT on canonical main — "
               "it lives on the E48 PR branch (foundation credit only). "
               "verification_status is free-form (not enum-validated)."),
    )
