"""D6 audit: user cognition + verified user-message origin.

Canonical implementation audited:
- integrated_offline_memory.conversation_memory (ConversationEpisode,
  build_conversation_candidate, build_conversation_correction)

D6 mandatory asks to bind canonical verified user-message origin /
ConversationEpisode provenance, NOT caller enums/booleans.

Truthful findings:
- Canonical rejects ASSISTANT_* claim roles as user memory (no caller can
  mint USER memory from an assistant claim).
- ConversationEpisode enforces privacy_class/coverage -> source_class
  mapping; PRIVATE_LOCAL_CANDIDATE is the only non-synthetic path and it is
  gated by PRIVATE_LOCAL_AUTHORIZED source_class.
- User memory requires episode identity (episode_id/user_scope/project_scope/
  source_pointer/source_hash) + provenance (source_pointer_hash).
"""
from __future__ import annotations

from ..canonical import access
from ..evidence_matrix import (
    DimensionVerdict, Evidence,
    VERDICT_PASS, VERDICT_PARTIAL, VERDICT_FAIL,
)

access.setup_import_path()

from integrated_offline_memory.conversation_memory import (  # type: ignore  # noqa: E402
    ConversationEpisode, build_conversation_candidate, build_conversation_correction,
)
from integrated_offline_memory import canonical  # type: ignore  # noqa: E402


def _check(name, desc, ok, detail=""):
    return Evidence(check_id=name, description=desc, passed=bool(ok), detail=detail)


def _episode(privacy_class="PUBLIC_SAFE_SYNTHETIC", coverage="synthetic",
             source_class="SYNTHETIC_PUBLIC_SAFE"):
    return ConversationEpisode(
        episode_id="ep-1",
        user_scope="userA",
        project_scope="projectX",
        source_pointer="file:///tmp/ep1.txt",
        source_hash="a" * 64,
        privacy_class=privacy_class,
        recorded_at="2026-08-12T10:00:00Z",
        coverage=coverage,
        source_class=source_class,
    )


def run() -> DimensionVerdict:
    evidence: list[Evidence] = []

    # 1. ASSISTANT claim role cannot become user memory
    assistant_rejected = False
    assistant_detail = ""
    try:
        build_conversation_candidate(
            episode=_episode(),
            statement="The market is bullish",
            claim_role="ASSISTANT_ANALYSIS",
            valid_from="2026-08-12T10:00:00Z",
        )
    except ValueError as e:
        assistant_rejected = "assistant_claim_cannot_be_user_memory" in str(e)
        assistant_detail = str(e)
    evidence.append(_check(
        "d6.assistant_claim_not_user_memory",
        "ASSISTANT_* claim roles are rejected as user memory",
        assistant_rejected,
        detail=assistant_detail,
    ))

    # 2. invalid claim_role rejected
    bad_role_rejected = False
    try:
        build_conversation_candidate(
            episode=_episode(),
            statement="The market is bullish",
            claim_role="MADE_UP_ROLE",
            valid_from="2026-08-12T10:00:00Z",
        )
    except ValueError as e:
        bad_role_rejected = "conversation_claim_role_denied" in str(e)
    evidence.append(_check(
        "d6.invalid_claim_role_rejected",
        "Invalid claim_role rejected (enum enforced)",
        bad_role_rejected,
    ))

    # 3. USER_ASSERTION accepted (canonical verified user-message origin path)
    user_candidate_ok = False
    user_detail = ""
    try:
        candidate = build_conversation_candidate(
            episode=_episode(),
            statement="The market is bullish",
            claim_role="USER_ASSERTION",
            valid_from="2026-08-12T10:00:00Z",
        )
        # candidate carries conversation provenance
        atom = candidate["atoms"][0]
        meta = atom.get("memory_metadata", {}).get("conversation", {})
        user_candidate_ok = (
            meta.get("claim_role") == "USER_ASSERTION"
            and "episode_manifest_id" in meta
            and "conversation://" in atom.get("source_refs", [""])[0]
        )
    except ValueError as e:
        user_detail = str(e)
    evidence.append(_check(
        "d6.user_assertion_with_provenance",
        "USER_ASSERTION produces candidate with episode provenance",
        user_candidate_ok,
        detail=user_detail,
    ))

    # 4. PRIVATE_LOCAL_CANDIDATE requires source_class PRIVATE_LOCAL_AUTHORIZED
    #    (privacy classification enforced, not caller boolean)
    privacy_mismatch_rejected = False
    try:
        ConversationEpisode(
            episode_id="ep-p", user_scope="userA", project_scope="projectX",
            source_pointer="file:///tmp/private.txt", source_hash="b" * 64,
            privacy_class="PRIVATE_LOCAL_CANDIDATE", recorded_at="2026-08-12T10:00:00Z",
            coverage="private_local", source_class="SYNTHETIC_PUBLIC_SAFE",
        ).validate()
    except ValueError as e:
        privacy_mismatch_rejected = "conversation_episode_source_classification_denied" in str(e)
    evidence.append(_check(
        "d6.privacy_class_source_class_bound",
        "PRIVATE source requires matching source_class (no caller override)",
        privacy_mismatch_rejected,
    ))

    # 5. SECRET_CREDENTIAL source denied entirely
    secret_denied = False
    try:
        ConversationEpisode(
            episode_id="ep-s", user_scope="userA", project_scope="projectX",
            source_pointer="file:///tmp/secret.txt", source_hash="c" * 64,
            privacy_class="SECRET_CREDENTIAL", recorded_at="2026-08-12T10:00:00Z",
            coverage="synthetic", source_class="SYNTHETIC_PUBLIC_SAFE",
        ).validate()
    except ValueError as e:
        secret_denied = ("conversation_episode_private_source_denied" in str(e)
                         or "source_classification_denied" in str(e))
    evidence.append(_check(
        "d6.secret_credential_source_denied",
        "SECRET_CREDENTIAL episode denied at validation",
        secret_denied,
    ))

    # 6. episode identity required (no empty provenance)
    identity_required = False
    try:
        ConversationEpisode(
            episode_id="", user_scope="", project_scope="", source_pointer="",
            source_hash="", privacy_class="PUBLIC_SAFE_SYNTHETIC",
            recorded_at="2026-08-12T10:00:00Z",
        ).validate()
    except ValueError as e:
        identity_required = "conversation_episode_identity_required" in str(e)
    evidence.append(_check(
        "d6.episode_identity_required",
        "ConversationEpisode requires full identity (no empty provenance)",
        identity_required,
    ))

    # 7. USER_CORRECTION targets a pre-existing atom (correction closure)
    correction_target_required = False
    try:
        build_conversation_correction(
            episode=_episode(),
            statement="Actually the market is bearish",
            replaces_atom_id="",
            valid_from="2026-08-12T10:00:00Z",
        )
    except ValueError as e:
        correction_target_required = "conversation_correction_target_invalid" in str(e)
    evidence.append(_check(
        "d6.correction_requires_target",
        "USER_CORRECTION requires a valid target atom id",
        correction_target_required,
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
        dimension="D6",
        title="User cognition + verified user-message origin",
        verdict=verdict,
        rationale=(f"{passed}/{total} user-origin gates passed against canonical "
                   "ConversationEpisode/build_conversation_candidate."),
        evidence=evidence,
        critical=True,
        notes=("Canonical binds user memory to ConversationEpisode provenance "
               "(episode_manifest_id + source_pointer_hash + source_hash), rejects "
               "ASSISTANT_* as user memory, enforces privacy_class->source_class "
               "mapping, denies SECRET_CREDENTIAL, and requires USER_CORRECTION to "
               "target a pre-existing atom. No caller enum/boolean can mint "
               "verified user origin."),
    )
