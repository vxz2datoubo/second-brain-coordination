"""R60 benchmark entrypoint; deterministic machine receipt generation."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from harness_common import *
from harness_persist import *
from harness_graders import *
from harness_regressions import *


TASK_ID = "QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60"
ROUTE_EPOCH = 60
HISTORICAL_60_OF_60_STATUS = "REJECTED_INVALID_FALSE_GREEN"
SPEC_PENDING_STATUS = "NEEDS_REVALIDATION_AGAINST_CURRENT_FROZEN_SLICE_CONTRACTS"


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    prefix = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(prefix + data).hexdigest()


def _receipt_path() -> Path:
    override = os.environ.get("R60_RECEIPT_PATH")
    if override:
        return Path(override)
    return R60_DIR / "evidence" / "harness_results.json"


def build_machine_result() -> dict[str, Any]:
    cases = load_cases()
    runnable = [case for case in cases if case["runnable"]]
    spec_pending = [case for case in cases if not case["runnable"]]

    results: list[dict[str, Any]] = []
    for case in runnable:
        try:
            results.append(run_case(case))
        except Exception as exc:
            results.append(
                _result(
                    case["case_id"],
                    "ERROR",
                    "ERROR",
                    f"{type(exc).__name__}: {exc}",
                )
            )

    regressions = run_regressions()
    passed = sum(item["verdict"] == "PASS" for item in results)
    failed = sum(item["verdict"] == "FAIL" for item in results)
    errored = sum(item["verdict"] == "ERROR" for item in results)
    reg_passed = sum(item["verdict"] == "PASS" for item in regressions)
    reg_failed = sum(item["verdict"] == "FAIL" for item in regressions)
    reg_errored = sum(item["verdict"] == "ERROR" for item in regressions)

    return {
        "schema_version": "r60-harness-results-v3",
        "receipt_kind": "DETERMINISTIC_BENCHMARK_RESULT_ONLY",
        "task_id": TASK_ID,
        "route_epoch": ROUTE_EPOCH,
        "historical_60_of_60_status": HISTORICAL_60_OF_60_STATUS,
        "corpus_git_blob_sha": _git_blob_sha(CASES_PATH),
        "runnable_cases": len(runnable),
        "spec_pending_cases": len(spec_pending),
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "results": results,
        "regression_summary": {
            "total": len(regressions),
            "passed": reg_passed,
            "failed": reg_failed,
            "errored": reg_errored,
        },
        "regressions": regressions,
        "spec_pending_ids": [case["case_id"] for case in spec_pending],
        "spec_pending_status": SPEC_PENDING_STATUS,
    }


def main() -> None:
    result = build_machine_result()
    out_path = _receipt_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    out_path.write_text(payload, encoding="utf-8")

    print(
        "runnable={runnable} spec_pending={pending} pass={passed} fail={failed} "
        "error={errored}; regressions={reg_total} reg_pass={reg_pass} "
        "reg_fail={reg_fail} reg_error={reg_error}".format(
            runnable=result["runnable_cases"],
            pending=result["spec_pending_cases"],
            passed=result["passed"],
            failed=result["failed"],
            errored=result["errored"],
            reg_total=result["regression_summary"]["total"],
            reg_pass=result["regression_summary"]["passed"],
            reg_fail=result["regression_summary"]["failed"],
            reg_error=result["regression_summary"]["errored"],
        )
    )
    r19 = next((item for item in result["results"] if item["case_id"] == "r60-019"), None)
    if r19:
        print("r60-019", r19["verdict"], r19["observed"], r19["note"])
    for item in (*result["results"], *result["regressions"]):
        if item["verdict"] in {"FAIL", "ERROR"}:
            print(" ", item["case_id"], item["verdict"], item.get("note", ""))


if __name__ == "__main__":
    main()
