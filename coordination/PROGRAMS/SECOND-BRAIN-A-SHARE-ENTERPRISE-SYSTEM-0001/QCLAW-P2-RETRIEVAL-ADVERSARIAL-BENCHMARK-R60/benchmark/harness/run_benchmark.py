"""R60 benchmark entrypoint; remediation generation 2."""
from __future__ import annotations
from harness_common import *
from harness_persist import *
from harness_graders import *
from harness_regressions import *

def main() -> None:
    cases=load_cases(); runnable=[case for case in cases if case["runnable"]]; spec_pending=[case for case in cases if not case["runnable"]]; results=[]
    for case in runnable:
        try: results.append(run_case(case))
        except Exception as exc: results.append(_result(case["case_id"],"ERROR","ERROR",f"{type(exc).__name__}: {exc}"))
    regressions=run_regressions(); passed=sum(item["verdict"]=="PASS" for item in results); failed=sum(item["verdict"]=="FAIL" for item in results); errored=sum(item["verdict"]=="ERROR" for item in results); reg_passed=sum(item["verdict"]=="PASS" for item in regressions); reg_failed=sum(item["verdict"]=="FAIL" for item in regressions); reg_errored=sum(item["verdict"]=="ERROR" for item in regressions)
    out={
        "schema_version":"r60-harness-results-v2","executor_role":"GPT_ENGINEERING_WORKER","model_id":"GPT-5.6 Sol","historical_60_of_60_status":"REJECTED_INVALID_FALSE_GREEN",
        "runtime_basis":("repository checkout: harness imports the checked-out canonical Phase-3 runtime" if (REPO_ROOT/".git").exists() else "isolated current-runtime projection: canonical/learning_packet/conversation_memory/memory_store are byte-verified against GitHub; retrieval is a logic-preserving local projection cross-checked against canonical GitHub source; authoritative exact-runtime regression evidence is GitHub Phase-3 CI"),
        "execution_harness":("repository checkout" if (REPO_ROOT/".git").exists() else "isolated container; no repository checkout; connector-sourced current-runtime projection"),
        "local_python":platform.python_version(),"canonical_main_revalidated":"d7591b123c72f012f20149337a3ae914db56d29d","current_main_merge_commit":"ad80d5432585335ff38c24ee87f2415d8a656f70","canonical_corpus_blob":"5b84ec894f7f94d6a408dfd0d0744fbfaeca01ba","runnable_cases":len(runnable),"spec_pending_cases":len(spec_pending),"passed":passed,"failed":failed,"errored":errored,"results":results,"regression_summary":{"total":len(regressions),"passed":reg_passed,"failed":reg_failed,"errored":reg_errored},"regressions":regressions,"spec_pending_ids":[case["case_id"] for case in spec_pending],"spec_pending_status":"NEEDS_REVALIDATION_AGAINST_CURRENT_FROZEN_SLICE_CONTRACTS"}
    out_path=R60_DIR/"evidence"/"harness_results.json"; out_path.parent.mkdir(parents=True,exist_ok=True); out_path.write_text(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
    print(f"runnable={len(runnable)} spec_pending={len(spec_pending)} pass={passed} fail={failed} error={errored}; regressions={len(regressions)} reg_pass={reg_passed} reg_fail={reg_failed} reg_error={reg_errored}")
    r19=next((item for item in results if item["case_id"]=="r60-019"),None)
    if r19: print("r60-019",r19["verdict"],r19["observed"],r19["note"])
    for item in (*results,*regressions):
        if item["verdict"] in {"FAIL","ERROR"}: print(" ",item["case_id"],item["verdict"],item.get("note",""))

if __name__=="__main__": main()
