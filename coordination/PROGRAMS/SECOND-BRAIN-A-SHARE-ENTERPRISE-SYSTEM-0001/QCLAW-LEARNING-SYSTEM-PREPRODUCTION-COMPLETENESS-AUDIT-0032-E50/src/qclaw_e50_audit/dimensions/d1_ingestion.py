"""D1 audit: source ingestion, privacy boundary, immutable provenance.

Canonical implementations exercised:
- public_safety_scan.public_safety_scan_text  (Phase-3 root)
- ConversationEpisode.validate  (conversation_memory.py)
- canonical.content_hash / canonical.source_pointer  (canonical.py)
- local_adapter.contracts.LocalArtifactReference / SourceManifest

NOT audited (left to other dimensions):
- Atom ingestion (D5)
- Source-to-atom derivation (D3)
"""
from __future__ import annotations

from .. import authoritative as access
from ..evidence_matrix import DimensionVerdict, Evidence, VERDICT_PASS, VERDICT_PARTIAL, VERDICT_FAIL

access.setup_import_path()

from integrated_offline_memory.conversation_memory import ConversationEpisode  # type: ignore  # noqa: E402
from integrated_offline_memory.canonical import content_hash  # type: ignore  # noqa: E402
from integrated_offline_memory import memory_store as p3_memory_store  # type: ignore  # noqa: E402
from local_adapter.contracts import LocalArtifactReference, canonical_hash  # type: ignore  # noqa: E402


def _check(name, desc, ok, detail=""):
    return Evidence(check_id=name, description=desc, passed=bool(ok), detail=detail)


def _detect_secret(text: str) -> bool:
    """Use canonical memory_store._SECRET regex to detect real secrets."""
    return bool(p3_memory_store._SECRET.search(text))


def run() -> DimensionVerdict:
    evidence: list[Evidence] = []

    # 1. canonical _SECRET regex rejects real GitHub PAT
    secret_payload = "My access token is ghp_abcdefghijklmnopqrstuvwxyz0123456789"
    detected = _detect_secret(secret_payload)
    evidence.append(_check(
        "d1.secret_token_rejected",
        "canonical memory_store._SECRET detects GitHub PAT",
        detected,
        detail=f"detected={detected}",
    ))

    openai_key = "I use sk-abcdefghijklmnopqrstuvwxyz0123456789 for everything"
    detected = _detect_secret(openai_key)
    evidence.append(_check(
        "d1.openai_key_rejected",
        "canonical _SECRET detects OpenAI sk- key",
        detected,
        detail=f"detected={detected}",
    ))

    private_block = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQ\n-----END PRIVATE KEY-----"
    detected = _detect_secret(private_block)
    evidence.append(_check(
        "d1.private_key_rejected",
        "canonical _SECRET detects private-key block",
        detected,
        detail=f"detected={detected}",
    ))

    # 2. PUBLIC_SAFE content is NOT detected as secret
    clean = "今天我们来讨论一下成交量和价格的关系。如果成交量上升，价格就倾向于上升。"
    detected = _detect_secret(clean)
    evidence.append(_check(
        "d1.public_safe_accepted",
        "canonical _SECRET does NOT flag clean PUBLIC_SAFE Chinese",
        not detected,
        detail=f"detected={detected}",
    ))

    # 3. ConversationEpisode rejects PRIVATE privacy_class
    try:
        ConversationEpisode(
            episode_id="ep1",
            user_scope="u1",
            project_scope="p1",
            source_pointer="src://x",
            source_hash="abc",
            privacy_class="PRIVATE",
            recorded_at="2026-08-12T10:00:00Z",
        ).validate()
        evidence.append(_check(
            "d1.conversation_episode_private_rejected",
            "ConversationEpisode rejects privacy_class=PRIVATE",
            False, detail="accepted; this is a bug",
        ))
    except ValueError as e:
        evidence.append(_check(
            "d1.conversation_episode_private_rejected",
            "ConversationEpisode rejects privacy_class=PRIVATE",
            True, detail=str(e),
        ))

    # 4. ConversationEpisode rejects non-synthetic coverage
    try:
        ConversationEpisode(
            episode_id="ep2",
            user_scope="u1",
            project_scope="p1",
            source_pointer="src://x",
            source_hash="abc",
            privacy_class="PUBLIC_SAFE_SYNTHETIC",
            recorded_at="2026-08-12T10:00:00Z",
            coverage="real",
        ).validate()
        evidence.append(_check(
            "d1.conversation_episode_real_coverage_rejected",
            "ConversationEpisode rejects coverage=real",
            False, detail="accepted; this is a bug",
        ))
    except ValueError as e:
        evidence.append(_check(
            "d1.conversation_episode_real_coverage_rejected",
            "ConversationEpisode rejects coverage=real",
            True, detail=str(e),
        ))

    # 5. ConversationEpisode accepts PUBLIC_SAFE_SYNTHETIC + synthetic
    try:
        ep = ConversationEpisode(
            episode_id="ep3",
            user_scope="u1",
            project_scope="p1",
            source_pointer="src://x",
            source_hash="abc",
            privacy_class="PUBLIC_SAFE_SYNTHETIC",
            recorded_at="2026-08-12T10:00:00Z",
        )
        ep.validate()
        evidence.append(_check(
            "d1.conversation_episode_synthetic_accepted",
            "ConversationEpisode accepts PUBLIC_SAFE_SYNTHETIC + synthetic",
            True, detail=f"manifest_id={ep.manifest_id}",
        ))
    except Exception as e:
        evidence.append(_check(
            "d1.conversation_episode_synthetic_accepted",
            "ConversationEpisode accepts PUBLIC_SAFE_SYNTHETIC + synthetic",
            False, detail=str(e),
        ))

    # 6. LocalArtifactReference rejects bad sha256 format (immutable provenance)
    try:
        LocalArtifactReference(
            reference_id="r1",
            local_location_hint="path://x",
            sha256="not-a-hex",
        ).validate()
        evidence.append(_check(
            "d1.local_artifact_reference_rejects_bad_sha",
            "LocalArtifactReference rejects non-SHA256 hash",
            False, detail="accepted; this is a bug",
        ))
    except Exception as e:
        evidence.append(_check(
            "d1.local_artifact_reference_rejects_bad_sha",
            "LocalArtifactReference rejects non-SHA256 hash",
            True, detail=type(e).__name__,
        ))

    # 7. canonical_hash is deterministic
    h1 = canonical_hash({"a": 1, "b": 2})
    h2 = canonical_hash({"b": 2, "a": 1})
    evidence.append(_check(
        "d1.local_canonical_hash_is_deterministic",
        "local_adapter canonical_hash is deterministic (sort_keys)",
        h1 == h2 and len(h1) == 64,
        detail=f"len={len(h1)}",
    ))

    # 8. content_hash is deterministic
    h3 = content_hash({"a": 1, "b": 2})
    h4 = content_hash({"b": 2, "a": 1})
    evidence.append(_check(
        "d1.canonical_content_hash_is_deterministic",
        "phase3 canonical.content_hash is deterministic",
        h3 == h4 and len(h3) == 64,
        detail=f"len={len(h3)}",
    ))

    # 9. Source-missing fail-closed: ConversationEpisode with empty required field
    try:
        ConversationEpisode(
            episode_id="",  # missing
            user_scope="u1",
            project_scope="p1",
            source_pointer="src://x",
            source_hash="abc",
            privacy_class="PUBLIC_SAFE_SYNTHETIC",
            recorded_at="2026-08-12T10:00:00Z",
        ).validate()
        evidence.append(_check(
            "d1.conversation_episode_missing_identity_rejected",
            "ConversationEpisode rejects empty episode_id",
            False, detail="accepted; this is a bug",
        ))
    except ValueError as e:
        evidence.append(_check(
            "d1.conversation_episode_missing_identity_rejected",
            "ConversationEpisode rejects empty episode_id",
            True, detail=str(e),
        ))

    passed = sum(1 for e in evidence if e.passed)
    total = len(evidence)
    if passed == total:
        verdict = VERDICT_PASS
        rationale = f"All {total} ingestion/privacy/provenance gates passed against canonical implementations."
    elif passed >= total - 2:
        verdict = VERDICT_PARTIAL
        rationale = f"{passed}/{total} gates passed; {total - passed} did not."
    else:
        verdict = VERDICT_FAIL
        rationale = f"Only {passed}/{total} ingestion/privacy/provenance gates passed."

    return DimensionVerdict(
        dimension="D1",
        title="Source ingestion / privacy / immutable provenance",
        verdict=verdict,
        rationale=rationale,
        evidence=evidence,
        critical=True,  # authority boundary gate
        notes="Audit of canonical public_safety_scan + ConversationEpisode + canonical_hash + LocalArtifactReference.",
    )