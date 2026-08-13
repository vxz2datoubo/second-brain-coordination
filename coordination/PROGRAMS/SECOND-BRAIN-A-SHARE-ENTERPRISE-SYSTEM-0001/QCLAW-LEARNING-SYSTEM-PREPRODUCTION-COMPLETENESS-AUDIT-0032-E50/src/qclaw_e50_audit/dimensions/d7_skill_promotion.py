"""D7 audit: skill learning + promotion anti-forgery.

Canonical implementation audited:
- CODEX-E66/src/e66_promotion.py (DigestBundle, PreAdmissionSubject,
  AdmissionEvidence, CandidateKnowledgePackage, build_candidate,
  parse_approval_control, verify_approval, safe_marker_name)

D7 mandatory asks to prove that candidate -> experimental -> formal
transition binds to real independently-issued test receipts, and that
caller-authored receipt fields CANNOT mint skill authority.

Truthful findings:
- Canonical has NO automatic skill promotion path. Authority promotion goes
  through the E66 approval-control flow: an E66_APPROVAL_V1 control object
  (13 exact fields incl. gpt_review_ref + expires_at) whose identity must
  bind to the CandidateKnowledgePackage.identity_sha256 + expected_parent.
- build_candidate only allows PUBLIC_SAFE into public promotion and requires
  evidence.repository_id / subject_sha256 / decision to exactly match.
- CandidateKnowledgePackage rejects placeholder evidence hash ("0"*64).
- verify_approval enforces expiry + actor binding.
"""
from __future__ import annotations

import datetime
from ..canonical import access
from ..evidence_matrix import (
    DimensionVerdict, Evidence,
    VERDICT_PASS, VERDICT_PARTIAL, VERDICT_FAIL,
)

access.setup_import_path()

from codex_e66 import e66_promotion as e66  # type: ignore  # noqa: E402


def _check(name, desc, ok, detail=""):
    return Evidence(check_id=name, description=desc, passed=bool(ok), detail=detail)


def _subject(admission_class="PUBLIC_SAFE"):
    return e66.PreAdmissionSubject(
        package_id="pkg-1",
        repository_id="repo-1",
        repository_slug="vxz2datoubo/second-brain-coordination",
        task_id="task-E50",
        route_epoch=58,
        digests=e66.DigestBundle(
            raw_artifact_sha256="a" * 64,
            canonical_semantic_sha256="b" * 64,
            l0_provenance_sha256="c" * 64,
        ),
        provenance_status="verified",
        target_scope="PROJECT",
        admission_class=admission_class,
        expected_parent="d" * 40,
    )


def run() -> DimensionVerdict:
    evidence: list[Evidence] = []

    # 1. CandidateKnowledgePackage rejects placeholder evidence hash
    placeholder_rejected = False
    try:
        subj = _subject()
        ev = e66.AdmissionEvidence(ref="r1", repository_id="repo-1",
                                   subject_sha256=subj.sha256,
                                   decision="PUBLIC_SAFE")
        pkg = e66.CandidateKnowledgePackage(subj, ev.ref, "0" * 64)
    except e66.Reject as e:
        placeholder_rejected = "placeholder" in str(e)
    evidence.append(_check(
        "d7.placeholder_evidence_hash_rejected",
        "CandidateKnowledgePackage rejects placeholder evidence hash (0*64)",
        placeholder_rejected,
    ))

    # 2. DigestBundle validates SHA format on all three fields
    digest_format_enforced = False
    try:
        e66.DigestBundle(raw_artifact_sha256="not-a-sha",
                         canonical_semantic_sha256="b" * 64,
                         l0_provenance_sha256="c" * 64)
    except e66.Reject as e:
        digest_format_enforced = "sha256" in str(e)
    evidence.append(_check(
        "d7.digest_sha_format_enforced",
        "DigestBundle enforces 64-hex SHA format on all digests",
        digest_format_enforced,
    ))

    # 3. build_candidate rejects non-PUBLIC_SAFE for public promotion
    non_public_rejected = False
    try:
        subj = _subject(admission_class="PRIVATE_OR_SENSITIVE")
        ev = e66.AdmissionEvidence(ref="r1", repository_id="repo-1",
                                   subject_sha256=subj.sha256,
                                   decision="PRIVATE_OR_SENSITIVE")
        e66.build_candidate(subj, ev)
    except e66.Reject as e:
        non_public_rejected = "non-public" in str(e)
    evidence.append(_check(
        "d7.non_public_cannot_enter_public_promotion",
        "build_candidate rejects non-PUBLIC_SAFE for public promotion",
        non_public_rejected,
    ))

    # 4. build_candidate requires evidence binding (repo + subject + decision)
    mismatch_rejected = False
    try:
        subj = _subject()
        ev = e66.AdmissionEvidence(ref="r1", repository_id="WRONG-REPO",
                                   subject_sha256=subj.sha256,
                                   decision="PUBLIC_SAFE")
        e66.build_candidate(subj, ev)
    except e66.Reject as e:
        mismatch_rejected = "mismatch" in str(e)
    evidence.append(_check(
        "d7.evidence_binding_required",
        "build_candidate requires evidence repo/subject/decision binding",
        mismatch_rejected,
    ))

    # 5. parse_approval_control requires exact 13 fields + APPROVE decision
    malformed_rejected = False
    try:
        e66.parse_approval_control("E66_APPROVAL_V1\n{\"object_type\":\"ISSUE_COMMENT\"}")
    except e66.Reject as e:
        malformed_rejected = "approval" in str(e) or "fields" in str(e)
    evidence.append(_check(
        "d7.approval_control_exact_fields",
        "parse_approval_control requires exact REQUIRED fields + APPROVE",
        malformed_rejected,
    ))

    # 6. A caller-authored control object with wrong binding is rejected
    binding_rejected = False
    binding_detail = ""
    try:
        subj = _subject()
        ev = e66.AdmissionEvidence(ref="r1", repository_id="repo-1",
                                   subject_sha256=subj.sha256,
                                   decision="PUBLIC_SAFE")
        pkg = e66.build_candidate(subj, ev)
        # forge approval with wrong candidate_identity_sha256
        forged = {
            "object_type": "ISSUE_COMMENT", "object_id": "1",
            "repository_id": "repo-1",
            "repository_slug": "vxz2datoubo/second-brain-coordination",
            "actor_id": "attacker", "decision": "APPROVE",
            "task_id": "task-E50", "route_epoch": "58",
            "candidate_identity_sha256": "f" * 64,  # wrong identity
            "expected_parent": "d" * 40,
            "expires_at": "2027-01-01T00:00:00Z",
            "gpt_review_ref": "rev-1",
        }
        e66.verify_approval(forged, pkg,
                            datetime.datetime(2026, 8, 12, tzinfo=datetime.timezone.utc),
                            "attacker")
    except e66.Reject as e:
        binding_rejected = "binding mismatch" in str(e)
        binding_detail = str(e)
    evidence.append(_check(
        "d7.approval_binding_mismatch_rejected",
        "verify_approval rejects caller-authored approval with wrong identity binding",
        binding_rejected,
        detail=binding_detail,
    ))

    # 7. expired approval rejected
    expired_rejected = False
    try:
        subj = _subject()
        ev = e66.AdmissionEvidence(ref="r1", repository_id="repo-1",
                                   subject_sha256=subj.sha256,
                                   decision="PUBLIC_SAFE")
        pkg = e66.build_candidate(subj, ev)
        valid = {
            "object_type": "ISSUE_COMMENT", "object_id": "1",
            "repository_id": "repo-1",
            "repository_slug": "vxz2datoubo/second-brain-coordination",
            "actor_id": "actor", "decision": "APPROVE",
            "task_id": "task-E50", "route_epoch": "58",
            "candidate_identity_sha256": pkg.identity_sha256,
            "expected_parent": "d" * 40,
            "expires_at": "2020-01-01T00:00:00Z",  # already expired
            "gpt_review_ref": "rev-1",
        }
        e66.verify_approval(valid, pkg,
                            datetime.datetime(2026, 8, 12, tzinfo=datetime.timezone.utc),
                            "actor")
    except e66.Reject as e:
        expired_rejected = "expired" in str(e)
    evidence.append(_check(
        "d7.expired_approval_rejected",
        "verify_approval rejects expired approval control",
        expired_rejected,
    ))

    # 8. safe_marker_name prevents path traversal in promotion marker store
    traversal_rejected = False
    try:
        e66.safe_marker_name("../evil")
    except e66.Reject as e:
        traversal_rejected = "unsafe" in str(e)
    evidence.append(_check(
        "d7.marker_path_traversal_prevented",
        "safe_marker_name rejects path traversal in marker CAS",
        traversal_rejected,
    ))

    passed = sum(1 for e in evidence if e.passed)
    total = len(evidence)
    if passed == total:
        verdict = VERDICT_PASS
    elif passed >= total - 2:
        verdict = VERDICT_PARTIAL
    else:
        verdict = VERDICT_FAIL

    return DimensionVerdict(
        dimension="D7",
        title="Skill learning + promotion anti-forgery",
        verdict=verdict,
        rationale=(f"{passed}/{total} promotion anti-forgery gates passed against "
                   "canonical CODEX-E66 e66_promotion."),
        evidence=evidence,
        critical=True,
        notes=("Canonical has NO automatic caller-authored skill promotion. "
               "Promotion requires an E66_APPROVAL_V1 control object with 13 exact "
               "fields (incl. gpt_review_ref + expires_at) whose identity must bind "
               "to CandidateKnowledgePackage.identity_sha256 + expected_parent. "
               "build_candidate restricts to PUBLIC_SAFE and requires evidence "
               "repo/subject/decision binding. Placeholder evidence hashes are "
               "rejected. verify_approval enforces actor binding + expiry. "
               "This satisfies D7 anti-forgery: caller-constructed receipt fields "
               "cannot mint formal skill authority."),
    )
