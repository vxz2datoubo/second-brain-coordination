from __future__ import annotations
from harness_common import *
from harness_persist import *
from harness_graders import *


def _regression_b01_surface_oracle() -> dict[str, Any]:
    forbidden={"at-hidden-real-id"}; fake_surface={"atoms":[{"id":"at-visible"}],"relations":[{"source_atom_id":"at-visible","target_atom_id":"at-hidden-real-id"}],"conflicts":[],"unknowns":[],"provenance":[],"trust_gate":{"outcome":"ADMIT_CANDIDATE_ONLY"}}
    paths=_walk_exact_ids(fake_surface,forbidden); ok=any("relations" in path for path in paths)
    return _result("reg-b01-full-surface-oracle","DETECTED" if ok else "MISSED","PASS" if ok else "FAIL",f"paths={paths}")


def _regression_b02_persisted_state() -> dict[str, Any]:
    from integrated_offline_memory.memory_store import MemoryStore
    store=MemoryStore(db_path=":memory:"); store.connect()
    try:
        stale=_persist_conversation(store,{"kind":"conversation","user":"alice","project":"p1","stmt":"R60 B02 stale persistence probe","status":"stale"},9001)
        superseded=_persist_conversation(store,{"kind":"conversation","user":"alice","project":"p1","stmt":"R60 B02 supersession persistence probe","status":"superseded","valid_from":"2026-08-14T10:00:00Z","effective_valid_to":"2026-08-14T12:00:00Z"},9002)
        freshness=_persist_conversation(store,{"kind":"conversation","user":"alice","project":"p1","stmt":"R60 B02 freshness persistence probe","valid_from":"2026-08-14T08:00:00Z","palace_freshness":"TRANSIENT","palace_horizon":1,"palace_last_verified":"2026-08-14T08:00:00Z"},9003)
        visibility_failed_closed=False
        try: _persist_conversation(store,{"kind":"conversation","user":"alice","project":"p1","stmt":"R60 B02 visibility mutation probe","visibility":"RESTRICTED_NEVER_SYNC"},9004)
        except ValueError: visibility_failed_closed=True
        sconv=superseded.atom.get("memory_metadata",{}).get("conversation",{}); fconv=freshness.atom.get("memory_metadata",{}).get("conversation",{}); palace=fconv.get("memory_palace",{}) if isinstance(fconv,dict) else {}
        ok=(stale.atom.get("knowledge_status")=="stale" and superseded.atom.get("knowledge_status")=="superseded" and sconv.get("effective_valid_to")=="2026-08-14T12:00:00Z" and bool(sconv.get("superseded_by")) and palace.get("freshness_profile")=="TRANSIENT" and palace.get("freshness_horizon_hours")==1 and palace.get("last_verified_at")=="2026-08-14T08:00:00Z" and palace.get("revalidation_required") is True and visibility_failed_closed)
        return _result("reg-b02-persisted-mutated-state","PERSISTED_OR_FAIL_CLOSED" if ok else "MISMATCH","PASS" if ok else "FAIL",f"stale={stale.atom.get('knowledge_status')}; superseded={superseded.atom.get('knowledge_status')}; effective_valid_to={sconv.get('effective_valid_to')}; freshness={palace}; visibility_fail_closed={visibility_failed_closed}")
    finally: store.close()


def _regression_b03_real_identity() -> dict[str, Any]:
    from integrated_offline_memory.memory_store import MemoryStore
    store=MemoryStore(db_path=":memory:"); store.connect()
    try:
        spec={"kind":"plain","stmt":"R60 B03 revoked no id hint","scope":"p1","status":"revoked"}; records,_=_persist_fixtures(store,{"atoms":[spec]}); forbidden=_forbidden_ids(records,{"scopes":["p1"]},{"atoms":[spec]},{}); actual=records[0].atom_id; ok=actual in forbidden and bool(actual)
        return _result("reg-b03-persisted-identity-oracle","RESOLVED" if ok else "EMPTY","PASS" if ok else "FAIL",f"actual_id={actual}; forbidden={sorted(forbidden)}")
    finally: store.close()


def _regression_b06_missing_provenance_empty_oracle() -> dict[str, Any]:
    from integrated_offline_memory.memory_store import MemoryStore

    store=MemoryStore(db_path=":memory:"); store.connect()
    missing_error=""
    try:
        try:
            _persist_conversation(
                store,
                {
                    "kind":"conversation",
                    "user":"alice",
                    "project":"p1",
                    "stmt":"R60 B06 missing provenance probe",
                    "valid_from":"2026-08-14T08:00:00Z",
                    "no_source_refs":True,
                },
                9200,
            )
        except ValueError as exc:
            missing_error=str(exc)
    finally:
        store.close()
    missing_failed_closed="conversation_provenance_missing" in missing_error

    empty_case={
        "case_id":"reg-b06-empty-forbidden-oracle",
        "expected_admission_or_abstention":{"verdict":"REJECT"},
        "query_and_intent":{
            "query_text":"R60 B06 empty oracle probe",
            "intent":"CURRENT",
            "scopes":["p1"],
            "user_scope":"alice",
            "valid_at":"2026-08-14T10:00:00Z",
        },
        "setup":{
            "atoms":[{
                "kind":"conversation",
                "user":"alice",
                "project":"p1",
                "stmt":"R60 B06 empty oracle probe",
                "valid_from":"2026-08-14T08:00:00Z",
            }]
        },
    }
    empty_result=_grade_admission(empty_case)
    empty_failed_closed=(
        empty_result.get("verdict")=="ERROR"
        and empty_result.get("observed")=="INVALID_FIXTURE_OR_ORACLE"
    )
    ok=missing_failed_closed and empty_failed_closed
    return _result(
        "reg-b06-missing-provenance-empty-oracle",
        "FAIL_CLOSED" if ok else "MISMATCH",
        "PASS" if ok else "FAIL",
        f"missing_source_refs_error={missing_error}; empty_oracle={empty_result.get('observed')}/{empty_result.get('verdict')}",
    )


def _regression_b07_wrong_rejection_reason() -> dict[str, Any]:
    # Deliberately use r60-038's visibility-denial contract while constructing a
    # fixture that is rejected for missing provenance. The outer regression only
    # passes when the inner benchmark case REFUSES to pass the wrong guard.
    wrong_case={
        "case_id":"r60-038",
        "expected_admission_or_abstention":{"verdict":"REJECT"},
        "query_and_intent":{
            "query_text":"R60 B07 wrong rejection reason probe",
            "intent":"CURRENT",
            "scopes":["p1"],
            "user_scope":"alice",
            "valid_at":"2026-08-14T10:00:00Z",
        },
        "setup":{
            "atoms":[{
                "kind":"conversation",
                "user":"alice",
                "project":"p1",
                "stmt":"R60 B07 wrong rejection reason probe",
                "valid_from":"2026-08-14T08:00:00Z",
                "no_source_refs":True,
            }]
        },
    }
    wrong=_grade_admission(wrong_case)
    note=wrong.get("note","")
    ok=(
        wrong.get("observed")=="UNEXPECTED_REJECTION_REASON"
        and wrong.get("verdict")=="FAIL"
        and wrong.get("rejection_code")=="invalid_learning_packet:conversation_provenance_missing"
        and "conversation_transport_visibility_denied" in note
    )
    return _result(
        "reg-b07-wrong-rejection-reason",
        "FAIL_CLOSED" if ok else "MISMATCH",
        "PASS" if ok else "FAIL",
        f"inner={wrong.get('observed')}/{wrong.get('verdict')}; rejection_code={wrong.get('rejection_code')}; note={note}",
    )


def _regression_r118_public_report_equivalence() -> dict[str, Any]:
    from integrated_offline_memory.memory_store import MemoryStore
    from integrated_offline_memory.retrieval import ContextAssembler,QueryPlan
    plan=QueryPlan(query_text="R60 hidden foreign report probe",scopes=("p1",),user_scope="alice",valid_at="2026-08-14T10:00:00Z")
    def report(with_hidden: bool) -> dict[str, Any]:
        store=MemoryStore(db_path=":memory:"); store.connect()
        try:
            if with_hidden: _persist_conversation(store,{"kind":"conversation","user":"bob","project":"p1","stmt":"R60 hidden foreign report probe"},9100)
            assembler=ContextAssembler(store); assembler.assemble(plan); return assembler.last_admission_report
        finally: store.close()
    absent=report(False); hidden=report(True); ok=hidden==absent
    return _result("reg-r118-public-report-oracle-equivalence","EQUIVALENT" if ok else "DIFFERENT","PASS" if ok else "FAIL",f"absent={absent}; hidden={hidden}")


def _regression_r119_endpoint_safe_projection() -> dict[str, Any]:
    from integrated_offline_memory.memory_store import MemoryStore
    from integrated_offline_memory.retrieval import ContextAssembler,QueryPlan
    from integrated_offline_memory.canonical import relation_id
    store=MemoryStore(db_path=":memory:"); store.connect()
    try:
        visible=_plain_atom("R60 visible endpoint probe","p1","candidate"); hidden=_plain_atom("R60 revoked endpoint probe","p1","revoked"); store.insert_atom(visible); store.insert_atom(hidden); store.insert_relation({"id":relation_id(visible["id"],hidden["id"],"supports"),"relation_type":"supports","source_atom_id":visible["id"],"target_atom_id":hidden["id"],"confidence":0.5})
        plan=QueryPlan(query_text="R60 visible endpoint probe",scopes=("p1",),relation_depth=1,valid_at="2026-08-14T10:00:00Z"); assembler=ContextAssembler(store); bundle=assembler.assemble(plan); base_leaks=_leak_paths(bundle,assembler,{hidden["id"]}); projection=assembler.assemble_gpt_context_bundle_v1(plan).to_dict(); projection_paths=_walk_exact_ids(projection,{hidden["id"]},"$gpt_projection"); ok=not base_leaks and not projection_paths
        return _result("reg-r119-endpoint-safe-projection","SUPPRESSED" if ok else "LEAK","PASS" if ok else "FAIL",f"bundle_leaks={base_leaks}; projection_paths={projection_paths}")
    finally: store.close()


def run_regressions() -> list[dict[str, Any]]:
    probes=(
        _regression_b01_surface_oracle,
        _regression_b02_persisted_state,
        _regression_b03_real_identity,
        _regression_b06_missing_provenance_empty_oracle,
        _regression_b07_wrong_rejection_reason,
        _regression_r118_public_report_equivalence,
        _regression_r119_endpoint_safe_projection,
    )
    results=[]
    for probe in probes:
        try: results.append(probe())
        except Exception as exc: results.append(_result(probe.__name__,"ERROR","ERROR",f"{type(exc).__name__}: {exc}"))
    return results


__all__=[name for name in globals() if not name.startswith("__")]
