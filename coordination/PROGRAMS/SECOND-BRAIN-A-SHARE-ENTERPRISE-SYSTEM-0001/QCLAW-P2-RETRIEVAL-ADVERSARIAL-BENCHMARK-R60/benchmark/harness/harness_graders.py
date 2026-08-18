from __future__ import annotations
from harness_common import *
from harness_persist import *

def _probe_kind(setup: dict[str, Any]) -> str:
    if "atoms" in setup and isinstance(setup["atoms"], list): return "admission"
    if "conversation_statement" in setup: return "conversation_build"
    if "atom_statement" in setup or "atom_secret_in_metadata" in setup: return "secret_reject"
    if any(key in setup for key in ("alias_enrich_on_closed", "knowledge_identity_collision", "source_dup_revive_closed", "supersession_valid_time_not_later", "orphan_relation")): return "store_invariant"
    if "canonical_json_order" in setup or "content_hash_key_order" in setup: return "canonical_determinism"
    if "idempotent_packet" in setup: return "idempotency"
    if "public_safety_scan" in setup: return "public_safety"
    if "conversation_atom_with_private_pointer" in setup: return "provenance_redaction"
    if setup.get("query_text", "").startswith("search sk-"): return "secret_query"
    return "plan_validation"

def _grade_plan_validation(case: dict[str, Any]) -> dict[str, Any]:
    expected=case["expected_admission_or_abstention"]["verdict"]
    try: _plan(case).validate()
    except ValueError as exc: return _result(case["case_id"],"REJECT","PASS" if expected=="REJECT" else "FAIL",str(exc))
    return _result(case["case_id"],"ADMIT","PASS" if expected=="ADMIT" else "FAIL","plan accepted")

def _grade_conversation_build(case: dict[str, Any]) -> dict[str, Any]:
    from integrated_offline_memory.conversation_memory import build_conversation_candidate
    expected=case["expected_admission_or_abstention"]["verdict"]
    try: build_conversation_candidate(episode=_episode("alice","p1","build-probe"),statement=case["setup"]["conversation_statement"],claim_role="USER_ASSERTION",valid_from="2026-08-14T00:00:00Z")
    except ValueError as exc: return _result(case["case_id"],"REJECT","PASS" if expected=="REJECT" else "FAIL",str(exc))
    return _result(case["case_id"],"ADMIT","PASS" if expected=="ADMIT" else "FAIL","candidate accepted")

def _grade_secret_reject(case: dict[str, Any]) -> dict[str, Any]:
    from integrated_offline_memory.memory_store import MemoryStore,_validate_atom
    setup=case["setup"]; expected=case["expected_admission_or_abstention"]["verdict"]
    if "atom_statement" in setup:
        store=MemoryStore(db_path=":memory:"); store.connect()
        try:
            try: store.insert_atom(_plain_atom(setup["atom_statement"],"p1","candidate"))
            except ValueError as exc: return _result(case["case_id"],"REJECT","PASS" if expected=="REJECT" else "FAIL",str(exc))
            return _result(case["case_id"],"ADMIT","FAIL","secret-shaped text accepted")
        finally: store.close()
    atom=_plain_atom("R60 metadata secret probe","p1","candidate"); atom["memory_metadata"]={"credential_value":"sk-123456789012345678901234"}
    try: _validate_atom(atom)
    except ValueError as exc: return _result(case["case_id"],"REJECT","PASS",str(exc))
    return _result(case["case_id"],"ADMIT","FAIL","secret in memory_metadata accepted")

def _grade_store_invariant(case: dict[str, Any]) -> dict[str, Any]:
    from integrated_offline_memory.memory_store import MemoryStore
    from integrated_offline_memory.conversation_memory import build_conversation_candidate,build_conversation_correction
    setup=case["setup"]; store=MemoryStore(db_path=":memory:"); store.connect()
    try:
        if "orphan_relation" in setup:
            try: store.insert_relation({"id":"rel-orphan-r60","relation_type":"supports","source_atom_id":"at-does-not-exist","target_atom_id":"at-also-missing","confidence":0.5})
            except Exception as exc: return _result(case["case_id"],"REJECT","PASS","orphan relation fail-closed: "+type(exc).__name__)
            report=store.integrity_check(); detected=any(item.startswith("orphan_relation:") for item in report["issues"])
            return _result(case["case_id"],"REJECT" if detected else "ADMIT","PASS" if detected else "FAIL","orphan integrity check")
        episode=_episode("alice","p1","store-invariant")
        base=build_conversation_candidate(episode=episode,statement="R60 original fact",claim_role="USER_ASSERTION",valid_from="2026-08-14T10:00:00Z"); store.import_learning_packet(base); target_id=base["atoms"][0]["id"]
        if "supersession_valid_time_not_later" in setup:
            try: store.import_learning_packet(build_conversation_correction(episode=episode,statement="R60 invalid correction",replaces_atom_id=target_id,valid_from="2026-08-14T09:00:00Z"))
            except ValueError as exc: return _result(case["case_id"],"REJECT","PASS",str(exc))
            return _result(case["case_id"],"ADMIT","FAIL","non-later supersession accepted")
        if "alias_enrich_on_closed" in setup:
            store.import_learning_packet(build_conversation_correction(episode=episode,statement="R60 valid correction",replaces_atom_id=target_id,valid_from="2026-08-14T11:00:00Z"))
            enriched=build_conversation_candidate(episode=episode,statement="R60 original fact",claim_role="USER_ASSERTION",valid_from="2026-08-14T10:00:00Z",external_candidate_id="r60-alias-on-closed")
            try: store.import_learning_packet(enriched)
            except ValueError as exc: return _result(case["case_id"],"REJECT","PASS",str(exc))
            return _result(case["case_id"],"ADMIT","FAIL","alias enrichment on closed atom allowed")
        return _result(case["case_id"],"ERROR","ERROR","unhandled store invariant")
    finally: store.close()

def _grade_canonical_determinism(case: dict[str, Any]) -> dict[str, Any]:
    from integrated_offline_memory.canonical import canonical_json,content_hash
    setup=case["setup"]
    ok=canonical_json({"a":2,"z":1})==canonical_json({"z":1,"a":2}) if "canonical_json_order" in setup else content_hash({"a":1,"b":2})==content_hash({"b":2,"a":1})
    return _result(case["case_id"],"ADMIT","PASS" if ok else "FAIL",f"deterministic={ok}")

def _grade_idempotency(case: dict[str, Any]) -> dict[str, Any]:
    from integrated_offline_memory.memory_store import MemoryStore
    from integrated_offline_memory.conversation_memory import build_conversation_candidate
    packet=build_conversation_candidate(episode=_episode("alice","p1","idempotency"),statement="R60 idempotency fact",claim_role="USER_ASSERTION",valid_from="2026-08-14T00:00:00Z")
    store=MemoryStore(db_path=":memory:"); store.connect()
    try:
        first=store.import_learning_packet(packet); second=store.import_learning_packet(packet); ok=first["status"]=="IMPORTED" and second["status"]=="IDEMPOTENT_DUPLICATE"
        return _result(case["case_id"],"ADMIT","PASS" if ok else "FAIL",f"second={second['status']}")
    finally: store.close()

def _grade_provenance_redaction(case: dict[str, Any]) -> dict[str, Any]:
    from integrated_offline_memory.conversation_memory import ConversationEpisode,build_conversation_candidate
    from integrated_offline_memory.memory_store import MemoryStore
    from integrated_offline_memory.retrieval import ContextAssembler,QueryPlan
    raw_pointer="synthetic://r60/private-pointer-that-must-not-surface"
    episode=ConversationEpisode(episode_id="r60-provenance-27",user_scope="alice",project_scope="p1",source_pointer=raw_pointer,source_hash="0"*64,privacy_class="PUBLIC_SAFE_SYNTHETIC",recorded_at="2026-08-14T00:00:00Z")
    packet=build_conversation_candidate(episode=episode,statement="R60 provenance redaction probe",claim_role="USER_ASSERTION",valid_from="2026-08-14T00:00:00Z")
    store=MemoryStore(db_path=":memory:"); store.connect()
    try:
        store.import_learning_packet(packet); plan=QueryPlan(query_text="R60 provenance redaction probe",scopes=("p1",),user_scope="alice",valid_at="2026-08-14T10:00:00Z"); bundle=ContextAssembler(store).assemble(plan)
        ok=raw_pointer not in json.dumps(bundle.provenance,ensure_ascii=False,sort_keys=True)
        return _result(case["case_id"],"ADMIT" if ok else "LEAK","PASS" if ok else "FAIL","raw pointer absent from provenance" if ok else "raw pointer leaked")
    finally: store.close()

def _grade_secret_query(case: dict[str, Any]) -> dict[str, Any]:
    from integrated_offline_memory.memory_store import MemoryStore
    from integrated_offline_memory.retrieval import ContextAssembler,QueryPlan
    secret_probe=str(case["setup"]["query_text"]); store=MemoryStore(db_path=":memory:"); store.connect()
    try:
        assembler=ContextAssembler(store); bundle=assembler.assemble(QueryPlan(query_text=secret_probe,scopes=("p1",))); serialized=json.dumps(bundle.to_dict(),ensure_ascii=False,sort_keys=True)
        ok=secret_probe not in serialized and "sk-123456789012345678901234" not in serialized
        return _result(case["case_id"],"ADMIT" if ok else "LEAK","PASS" if ok else "FAIL",f"gate={bundle.trust_gate.get('outcome')}; query_echo={not ok}")
    finally: store.close()

def _grade_public_safety(case: dict[str, Any]) -> dict[str, Any]:
    violations=[]
    for candidate in load_cases():
        setup=candidate.get("setup",{})
        for key in ("source_pointer","episode_source_pointer","knowledge_source_pointer"):
            pointer=setup.get(key)
            if pointer and not str(pointer).startswith("synthetic://"): violations.append(f"{candidate['case_id']}:{key}")
        for atom in setup.get("atoms",[]):
            if atom.get("kind")=="conversation" and atom.get("visibility")=="PRIVATE_LOCAL_CANDIDATE_ONLY": violations.append(f"{candidate['case_id']}:private_visibility")
    return _result(case["case_id"],"ADMIT","PASS" if not violations else "FAIL","public-safe corpus" if not violations else str(violations[:5]))

def _grade_admission(case: dict[str, Any]) -> dict[str, Any]:
    from integrated_offline_memory.memory_store import MemoryStore
    from integrated_offline_memory.retrieval import ContextAssembler
    expected=case["expected_admission_or_abstention"]["verdict"]; store=MemoryStore(db_path=":memory:"); store.connect()
    try:
        try:
            records,aliases=_persist_fixtures(store,case["setup"]); _persist_relations(store,case["setup"],aliases); _persist_unknowns(store,case["setup"],records,aliases)
        except ValueError as exc:
            if expected=="REJECT": return _result(case["case_id"],"REJECT","PASS","canonical build/import fail-closed: "+str(exc))
            return _result(case["case_id"],"ERROR","ERROR","unexpected fixture persistence failure: "+str(exc))
        plan=_plan(case)
        try: plan.validate()
        except ValueError as exc: return _result(case["case_id"],"REJECT","PASS" if expected=="REJECT" else "FAIL","plan rejected: "+str(exc))
        assembler=ContextAssembler(store); bundle=assembler.assemble(plan); forbidden=_forbidden_ids(records,case["query_and_intent"],case["setup"],aliases); leaks=_leak_paths(bundle,assembler,forbidden); admitted_ids=[atom["id"] for atom in bundle.atoms]
        if expected=="REJECT":
            # Q60-B06: once a negative fixture has successfully persisted and the
            # query plan is valid, an empty forbidden oracle is not evidence of
            # safety. It means the harness failed to construct the negative
            # identity set and must fail closed rather than `not leaks => PASS`.
            if records and not forbidden:
                return _result(
                    case["case_id"],
                    "INVALID_FIXTURE_OR_ORACLE",
                    "ERROR",
                    f"negative fixture persisted but forbidden oracle is empty; admitted={admitted_ids}",
                    leak_paths=leaks,
                    forbidden_ids=[],
                )
            passed=not leaks
            return _result(case["case_id"],"REJECT" if passed else "LEAK","PASS" if passed else "FAIL",f"forbidden={sorted(forbidden)}; admitted={admitted_ids}; leak_surfaces={sorted(leaks)}",leak_paths=leaks,forbidden_ids=sorted(forbidden))
        cid=case["case_id"]
        if cid=="r60-025":
            ok=bool(bundle.unknowns); return _result(cid,"ADMIT" if ok else "MISSING_UNKNOWN","PASS" if ok else "FAIL",f"unknown_count={len(bundle.unknowns)}")
        if cid=="r60-068":
            expected_related=aliases.get("a1"); unknown_related={item for unknown in bundle.unknowns for item in unknown.get("related_atom_ids",[])}; ok=bool(bundle.unknowns) and expected_related in unknown_related
            return _result(cid,"ADMIT" if ok else "MISSING_RELATED_UNKNOWN","PASS" if ok else "FAIL",f"unknown_count={len(bundle.unknowns)}; related={sorted(unknown_related)}")
        if cid=="r60-069":
            ok=not bundle.unknowns; return _result(cid,"ADMIT" if ok else "UNKNOWN_LEAK","PASS" if ok else "FAIL",f"unknown_count={len(bundle.unknowns)}")
        if cid=="r60-029":
            ids2=[atom["id"] for atom in assembler.assemble(plan).atoms]; ok=admitted_ids==ids2; return _result(cid,"ADMIT" if ok else "NONDETERMINISTIC","PASS" if ok else "FAIL",f"first={admitted_ids}; second={ids2}")
        if cid=="r60-030":
            ok=admitted_ids==sorted(admitted_ids); return _result(cid,"ADMIT" if ok else "UNSTABLE_TIE","PASS" if ok else "FAIL",f"ids={admitted_ids}")
        if cid=="r60-031":
            ok=len(admitted_ids)==len(set(admitted_ids))==1; return _result(cid,"ADMIT" if ok else "DUPLICATE","PASS" if ok else "FAIL",f"ids={admitted_ids}")
        if cid=="r60-032":
            ok=len(admitted_ids)<=plan.budget and len(bundle.omitted_due_to_budget)==3; return _result(cid,"ADMIT" if ok else "BUDGET_MISMATCH","PASS" if ok else "FAIL",f"selected={len(admitted_ids)}; omitted={len(bundle.omitted_due_to_budget)}")
        outcome=bundle.trust_gate.get("outcome",""); observed="ABSTAIN" if outcome=="ABSTAIN" else "ADMIT"
        return _result(case["case_id"],observed,"PASS" if observed==expected else "FAIL",f"gate={outcome}; admitted_count={len(admitted_ids)}")
    finally: store.close()

def run_case(case: dict[str, Any]) -> dict[str, Any]:
    probe=_probe_kind(case["setup"])
    if probe=="admission": return _grade_admission(case)
    if probe=="plan_validation": return _grade_plan_validation(case)
    if probe=="conversation_build": return _grade_conversation_build(case)
    if probe=="secret_reject": return _grade_secret_reject(case)
    if probe=="store_invariant": return _grade_store_invariant(case)
    if probe=="canonical_determinism": return _grade_canonical_determinism(case)
    if probe=="idempotency": return _grade_idempotency(case)
    if probe=="public_safety": return _grade_public_safety(case)
    if probe=="provenance_redaction": return _grade_provenance_redaction(case)
    if probe=="secret_query": return _grade_secret_query(case)
    return _result(case["case_id"],"ERROR","ERROR",f"unknown_probe={probe}")

__all__=[name for name in globals() if not name.startswith("__")]
