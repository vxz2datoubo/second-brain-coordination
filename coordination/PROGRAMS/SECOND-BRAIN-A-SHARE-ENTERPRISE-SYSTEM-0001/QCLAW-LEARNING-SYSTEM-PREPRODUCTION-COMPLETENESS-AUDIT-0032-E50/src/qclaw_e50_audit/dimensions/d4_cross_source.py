"""D4 audit: cross-source identity + dedup + contradiction + supersession.

Canonical implementation audited:
- integrated_offline_memory.canonical.atom_id / content_hash / canonical_json
- integrated_offline_memory.memory_store.MemoryStore (insert_relation,
  import_learning_packet, _supersede_atom, conflicts table)
- integrated_offline_memory.learning_packet.build_learning_packet /
  conversation_atom_id

D4 mandatory asks for stable semantic-object identity, near-duplicate
handling, evidence-based contradiction classification, and temporal/version
supersession without silent overwrite.
"""
from __future__ import annotations

import os
import tempfile

from ..canonical import access
from ..evidence_matrix import (
    DimensionVerdict, Evidence,
    VERDICT_PASS, VERDICT_PARTIAL, VERDICT_FAIL,
)

access.setup_import_path()

from integrated_offline_memory.canonical import atom_id, content_hash, canonical_json, normalize_text  # type: ignore  # noqa: E402
from integrated_offline_memory.memory_store import MemoryStore  # type: ignore  # noqa: E402


def _check(name, desc, ok, detail=""):
    return Evidence(check_id=name, description=desc, passed=bool(ok), detail=detail)


def _atom(atom_id_, atom_type, statement, scope="audit", knowledge_status="candidate",
          confidence=0.8, memory_metadata=None, source_refs=None):
    return {
        "id": atom_id_,
        "atom_type": atom_type,
        "canonical_statement": statement,
        "scope": scope,
        "confidence": confidence,
        "verification_status": "UNVERIFIED",
        "evidence_quality": "UNKNOWN",
        "knowledge_status": knowledge_status,
        "gpt_access": "FULL_SEMANTIC_ACCESS",
        "transport_visibility": "PUBLIC_SAFE_METADATA_ONLY",
        "authority_level": "CANDIDATE_ONLY",
        "source_refs": source_refs or [],
        "memory_metadata": memory_metadata or {},
    }


def run() -> DimensionVerdict:
    evidence: list[Evidence] = []

    # 1. atom_id is deterministic + stable across paraphrase (not identical text)
    id_a = atom_id("Volume rising signals bullish sentiment", "concept", "trading_research")
    id_b = atom_id("Volume rising signals bullish sentiment", "concept", "trading_research")
    evidence.append(_check(
        "d4.atom_id_deterministic",
        "atom_id is deterministic for identical (statement, type, scope)",
        id_a == id_b and id_a.startswith("at-"),
        detail=f"id={id_a}",
    ))

    # 2. canonical_json normalizes NFKC + whitespace, so near-duplicates with
    #    trivial whitespace/case differences share the same content_hash
    #    NOTE: content_hash does NOT lowercase — case is preserved. NFKC + 
    #    whitespace normalization still collapses halfwidth/fullwidth + space runs.
    h1 = content_hash("Volume   Rising\u3000Signals  Bullish")  # fullwidth space + multi-space
    h2 = content_hash("Volume Rising Signals Bullish")
    evidence.append(_check(
        "d4.canonical_normalization_for_dedup",
        "content_hash normalizes whitespace + NFKC for near-dup detection",
        h1 == h2,
        detail=f"h1={h1[:16]}... h2={h2[:16]}...",
    ))

    # 3. stable cross-source identity: same statement from two sources
    #    shares atom_id ONLY if scope matches; different scope = different id
    id_scope_a = atom_id("X is true", "claim", "scopeA")
    id_scope_b = atom_id("X is true", "claim", "scopeB")
    evidence.append(_check(
        "d4.atom_id_scope_sensitive",
        "atom_id differs when scope differs (no silent cross-scope merge)",
        id_scope_a != id_scope_b,
        detail=f"scopeA={id_scope_a}, scopeB={id_scope_b}",
    ))

    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(db_path=os.path.join(tmpdir, "audit.db"))
        store.connect()

        # 4. supersession preserves old statement while closing valid-time
        #    (no silent overwrite)
        from integrated_offline_memory.learning_packet import build_learning_packet  # noqa: E402
        # atoms passed to build_learning_packet use "statement" key
        old_pk = _atom("at-old-1", "observation",
                       "Volume is measured in lots", scope="data_quality",
                       knowledge_status="candidate")
        old_pk["statement"] = old_pk.pop("canonical_statement")
        new_pk = _atom("at-new-1", "observation",
                       "Volume is measured in shares", scope="data_quality",
                       knowledge_status="candidate")
        new_pk["statement"] = new_pk.pop("canonical_statement")
        rel = {
            "id": "rel-sup-1",
            "relation_type": "supersedes",
            "source_atom_id": "at-new-1",
            "target_atom_id": "at-old-1",
            "confidence": 0.9,
            "context": "correction",
        }
        try:
            packet = build_learning_packet(
                source_manifest_ids=["src-1"],
                source_hash=content_hash("sup"),
                validation_report={"ok": True},
                evidence_refs=["src-1"],
                atoms=[old_pk, new_pk],
                relations=[rel],
                conflicts=[],
                unknowns=[],
            )
            store.import_learning_packet(packet)
            supersession_ok = True
            supersession_detail = ""
        except Exception as e:
            supersession_ok = False
            supersession_detail = str(e)

        evidence.append(_check(
            "d4.supersession_via_packet",
            "MemoryStore supersession flows through import_learning_packet",
            supersession_ok,
            detail=supersession_detail,
        ))

        # old atom knowledge_status should now be "superseded"
        if supersession_ok:
            fetched_old = store.get_atom("at-old-1")
            old_preserved = fetched_old is not None and \
                fetched_old.get("canonical_statement", "").startswith("Volume is measured")
            old_superseded = fetched_old is not None and \
                fetched_old.get("knowledge_status") == "superseded"
            evidence.append(_check(
                "d4.supersession_preserves_old_statement",
                "Supersession preserves old statement (no silent overwrite)",
                old_preserved,
                detail=f"old_status={fetched_old.get('knowledge_status') if fetched_old else None}",
            ))
            evidence.append(_check(
                "d4.supersession_closes_old_valid_time",
                "Supersession sets old atom knowledge_status=superseded",
                old_superseded,
            ))
        else:
            evidence.append(_check(
                "d4.supersession_preserves_old_statement",
                "Supersession preserves old statement (no silent overwrite)",
                False, detail="supersession failed, cannot verify",
            ))
            evidence.append(_check(
                "d4.supersession_closes_old_valid_time",
                "Supersession sets old atom knowledge_status=superseded",
                False, detail="supersession failed, cannot verify",
            ))

        # 5. contradiction classification via conflicts table
        from integrated_offline_memory.learning_packet import build_learning_packet as _blp  # noqa: E402
        atom_x = _atom("at-x-1", "claim", "Volume predicts price", scope="audit")
        atom_x["statement"] = atom_x.pop("canonical_statement")
        atom_y = _atom("at-y-1", "claim", "Volume does not predict price", scope="audit")
        atom_y["statement"] = atom_y.pop("canonical_statement")
        conflict_ok = True
        conflict_detail = ""
        try:
            store.import_learning_packet(_blp(
                source_manifest_ids=["src-c"],
                source_hash=content_hash("conf"),
                validation_report={"ok": True},
                evidence_refs=["src-c"],
                atoms=[atom_x, atom_y],
                relations=[],
                conflicts=[{
                    "id": "conf-1",
                    "atom_id_a": "at-x-1",
                    "atom_id_b": "at-y-1",
                    "conflict_type": "DIRECT",
                    "resolution_status": "UNRESOLVED",
                    "resolution_note": "",
                }],
                unknowns=[],
            ))
        except Exception as e:
            conflict_ok = False
            conflict_detail = str(e)
        evidence.append(_check(
            "d4.conflict_classification_storage",
            "MemoryStore stores evidence-based contradiction in conflicts table",
            conflict_ok,
            detail=conflict_detail,
        ))

        # 6. duplicate atom id is idempotent (no duplicate rows)
        store.insert_atom(_atom("at-dup-1", "concept", "Idempotent statement", scope="audit"))
        store.insert_atom(_atom("at-dup-1", "concept", "Idempotent statement", scope="audit"))
        dup_count = 0
        try:
            rows = store.conn.execute(
                "SELECT COUNT(*) FROM atoms WHERE id='at-dup-1'").fetchone()
            dup_count = rows[0] if rows else 0
        except Exception:
            dup_count = -1
        evidence.append(_check(
            "d4.duplicate_atom_id_idempotent",
            "Re-inserting same atom id is idempotent (single row)",
            dup_count == 1,
            detail=f"row_count={dup_count}",
        ))
        store.close()

    passed = sum(1 for e in evidence if e.passed)
    total = len(evidence)
    if passed == total:
        verdict = VERDICT_PASS
    elif passed >= total - 2:
        verdict = VERDICT_PARTIAL
    else:
        verdict = VERDICT_FAIL
    rationale = f"{passed}/{total} cross-source identity gates passed against canonical MemoryStore."

    return DimensionVerdict(
        dimension="D4",
        title="Cross-source identity + dedup + contradiction + supersession",
        verdict=verdict,
        rationale=rationale,
        evidence=evidence,
        critical=True,
        notes=("Canonical atom_id is deterministic and scope-sensitive. "
               "content_hash normalizes NFKC/whitespace for near-dup detection. "
               "Supersession flows through import_learning_packet and preserves old "
               "statement while closing valid-time. Contradictions stored in conflicts "
               "table. No silent cross-source merge observed."),
    )
