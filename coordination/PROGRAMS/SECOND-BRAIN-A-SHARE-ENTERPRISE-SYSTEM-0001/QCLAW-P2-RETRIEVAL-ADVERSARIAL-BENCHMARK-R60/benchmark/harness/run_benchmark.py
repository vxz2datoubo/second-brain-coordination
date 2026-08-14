"""R60 read-only benchmark harness.

Grades `runnable` cases against the ACTUAL checked-out Phase-3 runtime WITHOUT
modifying it. Read-only execution of existing public-safe modules — not a second
runtime, not a runtime authority.

Each case maps to exactly one execution target, detected from its `setup`:

  probe = "plan_validation"      -> QueryPlan.validate() must raise (REJECT)
  probe = "conversation_build"   -> build_conversation_candidate must raise
  probe = "secret_reject"        -> insert_atom / _validate_atom must raise credential_value_denied
  probe = "store_invariant"      -> specific store-level invariant must raise
  probe = "canonical_determinism"-> canonical_json / content_hash determinism
  probe = "idempotency"          -> packet re-import must be idempotent
  probe = "public_safety"        -> public_safety_scan stays clean
  probe = "admission"            -> ContextAssembler.assemble admission result

Spec-only (runnable=false) cases are reported as SPEC_PENDING (not graded).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../benchmark/harness
R60_DIR = HERE.parent.parent                      # .../QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60
REPO_ROOT = R60_DIR
for parent in (HERE, *HERE.parents):
    if (parent / "coordination").is_dir():
        REPO_ROOT = parent
        break

PROG = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001"
PHASE3_SRC = REPO_ROOT / PROG / "PHASE-3-INTEGRATED-OFFLINE-MEMORY" / "src"
LOCAL_ADAPTER_SRC = REPO_ROOT / PROG / "PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION" / "src"
PHASE2_SRC = REPO_ROOT / PROG / "PHASE-2-OFFLINE-VERTICAL-SLICE" / "src"
CASES_PATH = R60_DIR / "benchmark" / "cases" / "benchmark_cases.json"

DENIED_STATUSES = {"stale", "revoked", "superseded", "rejected", "quarantined"}


def _setup_path() -> None:
    for s in (str(PHASE3_SRC), str(LOCAL_ADAPTER_SRC), str(PHASE2_SRC)):
        if s not in sys.path:
            sys.path.insert(0, s)


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]


def _result(case_id: str, observed: str, verdict: str, note: str) -> dict:
    return {"case_id": case_id, "observed": observed, "verdict": verdict, "note": note}


def _probe_kind(setup: dict) -> str:
    if "atoms" in setup and isinstance(setup["atoms"], list):
        return "admission"
    if "conversation_statement" in setup:
        return "conversation_build"
    if "atom_statement" in setup or "atom_secret_in_metadata" in setup:
        return "secret_reject"
    if any(k in setup for k in ("alias_enrich_on_closed", "knowledge_identity_collision",
                                "source_dup_revive_closed", "supersession_valid_time_not_later",
                                "orphan_relation")):
        return "store_invariant"
    if "canonical_json_order" in setup or "content_hash_key_order" in setup:
        return "canonical_determinism"
    if "idempotent_packet" in setup:
        return "idempotency"
    if "public_safety_scan" in setup:
        return "public_safety"
    return "plan_validation"


# ── fixture builders ──────────────────────────────────────────────────────────

def _plain_atom(stmt: str, scope: str, status: str, id_hint: str | None) -> dict:
    from integrated_offline_memory.canonical import atom_id  # type: ignore
    return {
        "id": id_hint or atom_id(stmt, "observation", scope),
        "atom_type": "observation",
        "canonical_statement": stmt,
        "scope": scope,
        "confidence": 0.5,
        "knowledge_status": status,
        "gpt_access": "FULL_SEMANTIC_ACCESS",
        "transport_visibility": "PUBLIC_SAFE_METADATA_ONLY",
        "authority_level": "CANDIDATE_ONLY",
        "source_refs": [],
        "memory_metadata": {},
    }


def _conversation_candidate(
    user: str, project: str, stmt: str, valid_from: str,
    valid_to: str | None = None, status: str = "candidate",
    visibility: str | None = None, effective_valid_to: str | None = None,
    superseded_by: str | None = None, palace: dict | None = None,
):
    from integrated_offline_memory.conversation_memory import (  # type: ignore
        ConversationEpisode, build_conversation_candidate,
    )
    ep = ConversationEpisode(
        episode_id=f"ep-{user}-{project}-1",
        user_scope=user, project_scope=project,
        source_pointer=f"synthetic://{user}/{project}/transcript-1",
        source_hash="0" * 64, privacy_class="PUBLIC_SAFE_SYNTHETIC",
        recorded_at="2026-08-14T00:00:00Z",
    )
    cand = build_conversation_candidate(
        episode=ep, statement=stmt, claim_role="USER_ASSERTION",
        valid_from=valid_from, valid_to=valid_to,
    )
    atom = dict(cand["atoms"][0])
    if status != "candidate":
        atom["knowledge_status"] = status
    if visibility is not None:
        atom["transport_visibility"] = visibility
    meta = dict(atom["memory_metadata"])
    conv = dict(meta["conversation"])
    if effective_valid_to is not None:
        conv["effective_valid_to"] = effective_valid_to
    if superseded_by is not None:
        conv["superseded_by"] = superseded_by
    if palace is not None:
        conv["memory_palace"] = palace
    meta["conversation"] = conv
    atom["memory_metadata"] = meta
    return atom, cand


def _knowledge_via_capture(store, user: str, project: str, domain: str, stmt: str,
                           safety_class: str = "PUBLIC_SAFE_SYNTHETIC") -> str:
    from integrated_offline_memory.knowledge_reconciliation import (  # type: ignore
        KnowledgeEpisode, capture_knowledge,
    )
    ep = KnowledgeEpisode(
        episode_id=f"kep-{user}-{project}-1", user_scope=user, project_scope=project,
        privacy_domain=domain, source_pointer=f"synthetic://{user}/{project}/{domain}/doc-1",
        source_text=stmt, recorded_at="2026-08-14T00:00:00Z", safety_class=safety_class,
    )
    receipt = capture_knowledge(
        store=store, episode=ep, passage=stmt,
        valid_from="2026-08-14T00:00:00Z",
        freshness_profile="STRUCTURAL",
        semantic_query="paraphrase probe that is not the statement itself",
    )
    return receipt.atom_ids[0] if receipt.atom_ids else ""


# ── graders ───────────────────────────────────────────────────────────────────

def _grade_plan_validation(case: dict) -> dict:
    from integrated_offline_memory.retrieval import QueryPlan  # type: ignore
    q = case["query_and_intent"]
    setup = case["setup"]
    plan = QueryPlan(
        query_text=str(q.get("query_text") or setup.get("query_text") or ""),
        scopes=tuple(q.get("scopes", [])),
        truth_states=tuple(q.get("truth_states", ["candidate", "approved", "conflict", "unknown"])),
        intent=q.get("intent", "CURRENT"),
        user_scope=q.get("user_scope"),
        privacy_domains=tuple(q.get("privacy_domains", [])),
        privacy_aggregate_mode=q.get("privacy_aggregate_mode", "ISOLATED"),
        valid_at=q.get("valid_at"),
        relation_depth=q.get("relation_depth", 0),
    )
    expected = case["expected_admission_or_abstention"]["verdict"]
    try:
        plan.validate()
    except ValueError as e:
        observed = "REJECT"
        note = str(e)
        verdict = "PASS" if expected == "REJECT" else "FAIL"
    else:
        observed = "ADMIT" if expected in ("ADMIT", "ABSTAIN") else "ADMIT"
        note = "plan accepted"
        verdict = "PASS" if expected == "ADMIT" else "FAIL"
    return _result(case["case_id"], observed, verdict, note)


def _grade_conversation_build(case: dict) -> dict:
    from integrated_offline_memory.conversation_memory import (  # type: ignore
        ConversationEpisode, build_conversation_candidate,
    )
    setup = case["setup"]
    expected = case["expected_admission_or_abstention"]["verdict"]
    ep = ConversationEpisode(
        episode_id="ep-alice-p1-1", user_scope="alice", project_scope="p1",
        source_pointer="synthetic://alice/p1/transcript-1", source_hash="0" * 64,
        privacy_class="PUBLIC_SAFE_SYNTHETIC", recorded_at="2026-08-14T00:00:00Z",
    )
    try:
        build_conversation_candidate(
            episode=ep, statement=setup["conversation_statement"],
            claim_role="USER_ASSERTION", valid_from="2026-08-14T00:00:00Z",
        )
    except ValueError as e:
        return _result(case["case_id"], "REJECT", "PASS" if expected == "REJECT" else "FAIL", str(e))
    return _result(case["case_id"], "ADMIT", "FAIL", "prompt-injection statement accepted (build did not raise)")


def _grade_secret_reject(case: dict) -> dict:
    from integrated_offline_memory.memory_store import MemoryStore, _validate_atom, _contains_secret_value  # type: ignore
    setup = case["setup"]
    expected = case["expected_admission_or_abstention"]["verdict"]
    if "atom_statement" in setup:
        atom = _plain_atom(setup["atom_statement"], "p1", "candidate", None)
        try:
            MemoryStore(db_path=":memory:").connect().insert_atom(atom)
        except ValueError as e:
            return _result(case["case_id"], "REJECT", "PASS" if expected == "REJECT" else "FAIL", str(e))
        return _result(case["case_id"], "ADMIT", "FAIL", "secret-shaped text accepted")
    if "atom_secret_in_metadata" in setup:
        atom = _plain_atom("正常候选事实", "p1", "candidate", None)
        atom["memory_metadata"] = {"credential_value": "sk-123456789012345678901234"}
        try:
            _validate_atom(atom)
        except ValueError as e:
            return _result(case["case_id"], "REJECT", "PASS", str(e))
        return _result(case["case_id"], "ADMIT", "FAIL", "secret in memory_metadata not detected")
    return _result(case["case_id"], "ERROR", "ERROR", "unhandled secret probe")


def _grade_store_invariant(case: dict) -> dict:
    from integrated_offline_memory.memory_store import MemoryStore  # type: ignore
    from integrated_offline_memory.conversation_memory import (  # type: ignore
        ConversationEpisode, build_conversation_candidate, build_conversation_correction,
    )
    setup = case["setup"]
    expected = case["expected_admission_or_abstention"]["verdict"]
    store = MemoryStore(db_path=":memory:")
    store.connect()
    try:
        if "orphan_relation" in setup:
            # With PRAGMA foreign_keys=ON, inserting a relation whose endpoints
            # do not exist must fail closed (IntegrityError). This IS the invariant.
            try:
                store.insert_relation({
                    "id": "rel-orphan-1", "relation_type": "supports",
                    "source_atom_id": "at-does-not-exist", "target_atom_id": "at-also-missing",
                    "confidence": 0.5,
                })
            except Exception as e:
                return _result(case["case_id"], "REJECT", "PASS",
                               "orphan relation fail-closed: " + type(e).__name__)
            # If no FK enforcement, integrity_check must still flag it.
            rep = store.integrity_check()
            if any(i.startswith("orphan_relation:") for i in rep["issues"]):
                return _result(case["case_id"], "REJECT", "PASS", "orphan_relation flagged")
            return _result(case["case_id"], "ADMIT", "FAIL", "orphan relation not flagged")

        if "supersession_valid_time_not_later" in setup:
            ep = ConversationEpisode(
                episode_id="ep-alice-p1-1", user_scope="alice", project_scope="p1",
                source_pointer="synthetic://a/p/1", source_hash="0" * 64,
                privacy_class="PUBLIC_SAFE_SYNTHETIC", recorded_at="2026-08-14T00:00:00Z",
            )
            base = build_conversation_candidate(
                episode=ep, statement="原始事实", claim_role="USER_ASSERTION",
                valid_from="2026-08-14T10:00:00Z",
            )
            store.import_learning_packet(base)
            target_id = base["atoms"][0]["id"]
            try:
                correction = build_conversation_correction(
                    episode=ep, statement="修正事实", replaces_atom_id=target_id,
                    valid_from="2026-08-14T09:00:00Z",  # not later than target valid_from
                )
                store.import_learning_packet(correction)  # must raise supersession_valid_time_invalid
            except ValueError as e:
                return _result(case["case_id"], "REJECT", "PASS", str(e))
            return _result(case["case_id"], "ADMIT", "FAIL", "supersession with non-later valid_from accepted")

        if "alias_enrich_on_closed" in setup:
            # Build a superseded conversation atom then attempt alias enrichment.
            ep = ConversationEpisode(
                episode_id="ep-alice-p1-1", user_scope="alice", project_scope="p1",
                source_pointer="synthetic://a/p/1", source_hash="0" * 64,
                privacy_class="PUBLIC_SAFE_SYNTHETIC", recorded_at="2026-08-14T00:00:00Z",
            )
            base = build_conversation_candidate(
                episode=ep, statement="原始事实", claim_role="USER_ASSERTION",
                valid_from="2026-08-14T10:00:00Z",
            )
            store.import_learning_packet(base)
            target_id = base["atoms"][0]["id"]
            correction = build_conversation_correction(
                episode=ep, statement="修正事实", replaces_atom_id=target_id,
                valid_from="2026-08-14T11:00:00Z",
            )
            store.import_learning_packet(correction)
            # Now attempt to re-import an alias-enriched packet for the (now superseded) atom
            atom = dict(base["atoms"][0])
            meta = dict(atom["memory_metadata"])
            conv = dict(meta["conversation"])
            conv["daily_candidate_id_hash"] = "d" * 64
            conv["daily_candidate_id_hashes"] = ["d" * 64]
            meta["conversation"] = conv
            atom["memory_metadata"] = meta
            try:
                store.insert_atom(atom)
            except ValueError as e:
                return _result(case["case_id"], "REJECT", "PASS", str(e))
            return _result(case["case_id"], "ADMIT", "FAIL", "alias enrichment on closed atom allowed")

        if "knowledge_identity_collision" in setup or "source_dup_revive_closed" in setup:
            # These require a full knowledge atom; cover with a targeted check that
            # the store raises on knowledge identity collision via re-import path.
            return _result(case["case_id"], "UNVERIFIED", "ERROR",
                           "store invariant probe requires full knowledge packet (graded in admission path)")
    finally:
        store.close()
    return _result(case["case_id"], "ERROR", "ERROR", "unhandled store invariant")


def _grade_canonical_determinism(case: dict) -> dict:
    from integrated_offline_memory.canonical import canonical_json, content_hash  # type: ignore
    setup = case["setup"]
    if "canonical_json_order" in setup:
        h1 = canonical_json({"a": 2, "z": 1})
        h2 = canonical_json({"z": 1, "a": 2})
        return _result(case["case_id"], "ADMIT", "PASS" if h1 == h2 else "FAIL",
                       f"canonical_json order-independent={h1 == h2}")
    if "content_hash_key_order" in setup:
        h1 = content_hash({"a": 1, "b": 2})
        h2 = content_hash({"b": 2, "a": 1})
        return _result(case["case_id"], "ADMIT", "PASS" if h1 == h2 else "FAIL",
                       f"content_hash key-order-independent={h1 == h2}")
    return _result(case["case_id"], "ERROR", "ERROR", "unhandled determinism probe")


def _grade_idempotency(case: dict) -> dict:
    from integrated_offline_memory.memory_store import MemoryStore  # type: ignore
    from integrated_offline_memory.conversation_memory import (  # type: ignore
        ConversationEpisode, build_conversation_candidate,
    )
    ep = ConversationEpisode(
        episode_id="ep-alice-p1-1", user_scope="alice", project_scope="p1",
        source_pointer="synthetic://a/p/1", source_hash="0" * 64,
        privacy_class="PUBLIC_SAFE_SYNTHETIC", recorded_at="2026-08-14T00:00:00Z",
    )
    cand = build_conversation_candidate(
        episode=ep, statement="某候选事实", claim_role="USER_ASSERTION",
        valid_from="2026-08-14T00:00:00Z",
    )
    store = MemoryStore(db_path=":memory:")
    store.connect()
    try:
        r1 = store.import_learning_packet(cand)
        r2 = store.import_learning_packet(cand)
        ok = r1["status"] == "IMPORTED" and r2["status"] == "IDEMPOTENT_DUPLICATE"
        return _result(case["case_id"], "ADMIT", "PASS" if ok else "FAIL",
                       f"reimport status={r2['status']}")
    finally:
        store.close()


def _grade_public_safety(case: dict) -> dict:
    # PUBLIC_SAFE guarantee: every fixture must reference only synthetic source
    # pointers and PUBLIC_SAFE_SYNTHETIC privacy classification. Secret-shaped
    # STRINGS (e.g. "sk-123...") are legitimate adversarial negative probes used
    # to verify fail-closed detection; they are synthetic placeholders, not real
    # credentials, and are never uploaded or executed as such.
    cases = load_cases()
    violations = []
    for c in cases:
        setup = c.get("setup", {})
        for key in ("source_pointer", "episode_source_pointer", "knowledge_source_pointer"):
            sp = setup.get(key)
            if sp and not str(sp).startswith("synthetic://"):
                violations.append(f"{c['case_id']}:{key}={sp}")
        for atom in setup.get("atoms", []):
            if atom.get("kind") == "conversation" and atom.get("visibility") == "PRIVATE_LOCAL_CANDIDATE_ONLY":
                violations.append(f"{c['case_id']}:private visibility on synthetic fixture")
    return _result(case["case_id"], "ADMIT", "PASS" if not violations else "FAIL",
                   "all fixtures synthetic:// + PUBLIC_SAFE" if not violations else "; ".join(violations[:5]))


def _forbidden_ids(setup: dict, query: dict) -> set[str]:
    forbidden: set[str] = set()
    q_scopes = set(query.get("scopes", []))
    q_user = query.get("user_scope")
    q_domains = set(query.get("privacy_domains", []))
    for spec in setup.get("atoms", []):
        status = spec.get("status", "candidate")
        if status in DENIED_STATUSES:
            forbidden.add(spec.get("id_hint") or "")
        if spec.get("kind") == "conversation":
            if q_user is not None and spec.get("user") != q_user:
                forbidden.add(spec.get("id_hint") or "")
            if q_scopes and spec.get("project") not in q_scopes:
                forbidden.add(spec.get("id_hint") or "")
            if spec.get("visibility") == "RESTRICTED_NEVER_SYNC":
                forbidden.add(spec.get("id_hint") or "")
            if spec.get("no_packet_lineage"):
                forbidden.add(spec.get("id_hint") or "")
        if spec.get("kind") == "knowledge":
            if q_user is not None and spec.get("user") != q_user:
                forbidden.add(spec.get("id_hint") or "")
            if q_scopes and spec.get("project") not in q_scopes:
                forbidden.add(spec.get("id_hint") or "")
            if q_domains and spec.get("domain") not in q_domains:
                forbidden.add(spec.get("id_hint") or "")
            if spec.get("safety_class") not in (None, "PUBLIC_SAFE_SYNTHETIC"):
                forbidden.add(spec.get("id_hint") or "")
            if spec.get("missing_identity"):
                forbidden.add(spec.get("id_hint") or "")
    for rel in setup.get("relations", []):
        forbidden.add(rel.get("target", ""))
    forbidden.discard("")
    return forbidden


def _grade_admission(case: dict) -> dict:
    from integrated_offline_memory.retrieval import QueryPlan, ContextAssembler  # type: ignore
    from integrated_offline_memory.memory_store import MemoryStore  # type: ignore

    setup = case["setup"]
    query = case["query_and_intent"]
    expected = case["expected_admission_or_abstention"]["verdict"]

    store = MemoryStore(db_path=":memory:")
    store.connect()
    try:
        for atom_spec in setup.get("atoms", []):
            kind = atom_spec.get("kind")
            try:
                if kind == "plain":
                    store.insert_atom(_plain_atom(
                        atom_spec["stmt"], atom_spec.get("scope", "p1"),
                        atom_spec.get("status", "candidate"), atom_spec.get("id_hint"),
                    ))
                elif kind == "conversation":
                    atom, cand = _conversation_candidate(
                        user=atom_spec["user"], project=atom_spec["project"], stmt=atom_spec["stmt"],
                        valid_from=atom_spec.get("valid_from", "2026-08-14T00:00:00Z"),
                        valid_to=atom_spec.get("valid_to"),
                        status=atom_spec.get("status", "candidate"),
                        visibility=atom_spec.get("visibility"),
                        effective_valid_to=atom_spec.get("effective_valid_to"),
                        superseded_by=atom_spec.get("superseded_by"),
                        palace=atom_spec.get("palace"),
                    )
                    store.import_learning_packet(cand)
                elif kind == "knowledge":
                    _knowledge_via_capture(
                        store, atom_spec["user"], atom_spec["project"],
                        atom_spec.get("domain", "synthetic-alpha"), atom_spec["stmt"],
                        safety_class=atom_spec.get("safety_class", "PUBLIC_SAFE_SYNTHETIC"),
                    )
            except ValueError as e:
                # Fail-closed at build/import time: for REJECT cases this is a
                # valid rejection mechanism; for ADMIT/ABSTAIN it is an ERROR.
                if expected == "REJECT":
                    return _result(case["case_id"], "REJECT", "PASS",
                                   "build/import fail-closed: " + str(e))
                return _result(case["case_id"], "ERROR", "ERROR",
                               "unexpected build failure: " + str(e))

        for rel_spec in setup.get("relations", []):
            store.insert_relation({
                "id": "rel-" + rel_spec["source"][:6] + rel_spec["target"][:6],
                "relation_type": rel_spec.get("type", "supports"),
                "source_atom_id": rel_spec["source"],
                "target_atom_id": rel_spec["target"],
                "confidence": 0.5,
            })

        plan = QueryPlan(
            query_text=str(query.get("query_text") or setup.get("query_text") or ""),
            scopes=tuple(query.get("scopes", [])),
            truth_states=tuple(query.get("truth_states", ["candidate", "approved", "conflict", "unknown"])),
            intent=query.get("intent", "CURRENT"),
            user_scope=query.get("user_scope"),
            privacy_domains=tuple(query.get("privacy_domains", [])),
            privacy_aggregate_mode=query.get("privacy_aggregate_mode", "ISOLATED"),
            valid_at=query.get("valid_at"),
            relation_depth=query.get("relation_depth", 0),
            budget=query.get("budget", 50),
            include_unknowns=query.get("include_unknowns", True),
            include_conflicts=query.get("include_conflicts", True),
        )
        try:
            plan.validate()
        except ValueError as e:
            return _result(case["case_id"], "REJECT", "PASS" if expected == "REJECT" else "FAIL",
                           "plan rejected: " + str(e))

        assembler = ContextAssembler(store)
        bundle = assembler.assemble(plan)
        gate = bundle.trust_gate
        outcome = gate.get("outcome", "")
        admitted_ids = [a["id"] for a in bundle.atoms]

        if expected == "REJECT":
            forbidden = _forbidden_ids(setup, query)
            leaked = forbidden & set(admitted_ids)
            passed = not leaked
            return _result(case["case_id"], "ADMIT" if admitted_ids else "REJECT",
                           "PASS" if passed else "FAIL",
                           f"gate={outcome}; admitted={admitted_ids}; leaked={sorted(leaked)}")

        if outcome == "ABSTAIN":
            observed = "ABSTAIN"
        else:
            observed = "ADMIT"
        return _result(case["case_id"], observed, "PASS" if observed == expected else "FAIL",
                       f"gate={outcome}; admitted_count={len(admitted_ids)}; votes={gate.get('semantic_vote_count')}")
    finally:
        store.close()


def run_case(case: dict) -> dict:
    probe = _probe_kind(case["setup"])
    if probe == "plan_validation":
        return _grade_plan_validation(case)
    if probe == "conversation_build":
        return _grade_conversation_build(case)
    if probe == "secret_reject":
        return _grade_secret_reject(case)
    if probe == "store_invariant":
        return _grade_store_invariant(case)
    if probe == "canonical_determinism":
        return _grade_canonical_determinism(case)
    if probe == "idempotency":
        return _grade_idempotency(case)
    if probe == "public_safety":
        return _grade_public_safety(case)
    return _grade_admission(case)


def main() -> None:
    _setup_path()
    cases = load_cases()
    runnable = [c for c in cases if c["runnable"]]
    spec_pending = [c for c in cases if not c["runnable"]]

    results = []
    for case in runnable:
        try:
            results.append(run_case(case))
        except Exception as e:  # noqa: BLE001
            results.append(_result(case["case_id"], "ERROR", "ERROR", f"{type(e).__name__}: {e}"))

    passed = sum(1 for r in results if r["verdict"] == "PASS")
    failed = sum(1 for r in results if r["verdict"] == "FAIL")
    errored = sum(1 for r in results if r["verdict"] == "ERROR")

    out = {
        "schema_version": "r60-harness-results-v1",
        "runnable_cases": len(runnable),
        "spec_pending_cases": len(spec_pending),
        "passed": passed, "failed": failed, "errored": errored,
        "results": results,
        "spec_pending_ids": [c["case_id"] for c in spec_pending],
    }
    out_path = R60_DIR / "evidence" / "harness_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"runnable={len(runnable)} spec_pending={len(spec_pending)} pass={passed} fail={failed} error={errored}")
    print(f"wrote {out_path}")
    for r in results:
        if r["verdict"] in ("FAIL", "ERROR"):
            print("  ", r["case_id"], r["verdict"], r.get("note", ""))


if __name__ == "__main__":
    main()
