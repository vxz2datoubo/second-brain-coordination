from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from control_tower import load_yaml

WORKER_REGISTRY = "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
CLAIMS_FILE = "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"
ROUTE_FILE = "coordination/ROUTES/GPT-GLOBAL-SIGNAL-TOWER-S0F-CROSS-DOMAIN-ROUTING-ISOLATION-R145.yaml"
RELEASE_GATE_FILE = "coordination/CONTROL-TOWER/RELEASE-GATE.yaml"
PROGRAM_LANES_FILE = "coordination/ACTIVE-PROGRAM-LANES.yaml"
CLOSEOUT_RECEIPT_FILE = (
    "coordination/CONTROL-TOWER/"
    "R145-S0F-CROSS-DOMAIN-ROUTING-ISOLATION-CLOSURE-RECONCILIATION.yaml"
)

SLOT_ID = "GPT-WORKER-R145-PROGRAMMING-1"
LANE_ID = "LANE-A-HARNESS-INTEGRATION"
TASK_ID = "GPT-GLOBAL-SIGNAL-TOWER-S0F-CROSS-DOMAIN-ROUTING-ISOLATION-R145"
ROUTE_EPOCH = 145
RUNTIME_PR = 418

ACTIVE_MODE = "ACTIVE_PATH_ACTION"
CLOSED_MODE = "CLOSED_FAIL_CLOSED"
INVALID_MODE = "INVALID_MIXED_STATE"


def _find_one(items: Any, key: str, value: Any) -> dict[str, Any] | None:
    if not isinstance(items, list):
        return None
    matches = [item for item in items if isinstance(item, dict) and item.get(key) == value]
    return matches[0] if len(matches) == 1 else None


def _bool_is(value: Any, expected: bool) -> bool:
    return isinstance(value, bool) and value is expected


def _empty_list(mapping: dict[str, Any], key: str) -> bool:
    return isinstance(mapping.get(key), list) and mapping.get(key) == []


def evaluate_documents(
    worker_doc: dict[str, Any],
    claims_doc: dict[str, Any],
    route_doc: dict[str, Any],
    release_doc: dict[str, Any],
    lanes_doc: dict[str, Any],
    receipt_doc: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    slots = worker_doc.get("worker_slots")
    if not isinstance(slots, list):
        findings.append({"code": "R145_LIFECYCLE_WORKER_SLOTS_INVALID", "actual": type(slots).__name__})
        slots = []
    r145_slots = [item for item in slots if isinstance(item, dict) and item.get("worker_slot_id") == SLOT_ID]
    if len(r145_slots) > 1:
        findings.append({"code": "R145_LIFECYCLE_SLOT_NOT_UNIQUE", "count": len(r145_slots)})

    claim = _find_one(claims_doc.get("claims"), "lane_id", LANE_ID)
    if claim is None:
        findings.append({"code": "R145_LIFECYCLE_LANE_A_CLAIM_NOT_UNIQUE"})
        claim = {}

    route_binding = route_doc.get("binding") if isinstance(route_doc.get("binding"), dict) else {}
    route_executor = route_doc.get("executor") if isinstance(route_doc.get("executor"), dict) else {}
    write_scope = route_doc.get("write_scope") if isinstance(route_doc.get("write_scope"), dict) else {}

    lane_release = (
        release_doc.get("lane_specific_release_state", {}).get(LANE_ID, {})
        if isinstance(release_doc.get("lane_specific_release_state"), dict)
        else {}
    )
    lane = _find_one(lanes_doc.get("program_lanes"), "lane_id", LANE_ID)
    if lane is None:
        findings.append({"code": "R145_LIFECYCLE_PROGRAM_LANE_NOT_UNIQUE"})
        lane = {}

    accepted_runtime = receipt_doc.get("accepted_runtime") if isinstance(receipt_doc.get("accepted_runtime"), dict) else {}
    closeout_effects = receipt_doc.get("closeout_effects") if isinstance(receipt_doc.get("closeout_effects"), dict) else {}

    active_slot = r145_slots[0] if len(r145_slots) == 1 else None
    active_identity = bool(
        active_slot
        and active_slot.get("task_id") == TASK_ID
        and active_slot.get("route_epoch") == ROUTE_EPOCH
        and active_slot.get("issue") == 415
        and active_slot.get("pr") == RUNTIME_PR
        and active_slot.get("worker_slot_id") == SLOT_ID
        and active_slot.get("status") == "ACTIVE_IMPLEMENTATION"
        and _bool_is(active_slot.get("execution_allowed"), True)
        and claim.get("claim_state") == "ACTIVE_IMPLEMENTATION"
        and claim.get("execution_agent") == "GPT_ENGINEERING_WORKER"
        and claim.get("worker_slot_id") == SLOT_ID
        and route_doc.get("status") == "ACTIVE_IMPLEMENTATION"
        and _bool_is(route_doc.get("execution_allowed"), True)
        and _bool_is(route_doc.get("runtime_code_change_allowed"), True)
        and route_binding.get("task_id") == TASK_ID
        and route_binding.get("route_epoch") == ROUTE_EPOCH
        and route_binding.get("implementation_pr") == RUNTIME_PR
        and route_executor.get("worker_slot_id") == SLOT_ID
    )
    if active_identity and not findings:
        return {"status": "PASS", "mode": ACTIVE_MODE, "findings": []}

    closed_checks: list[tuple[bool, str, Any]] = [
        (len(r145_slots) == 0, "R145_CLOSEOUT_SLOT_STILL_PRESENT", len(r145_slots)),
        (claim.get("claim_state") == "CLOSED_NO_ACTIVE_IMPLEMENTATION", "R145_CLOSEOUT_CLAIM_NOT_CLOSED", claim.get("claim_state")),
        (claim.get("execution_agent") is None, "R145_CLOSEOUT_EXECUTION_AGENT_RETAINED", claim.get("execution_agent")),
        (claim.get("worker_slot_id") is None, "R145_CLOSEOUT_CLAIM_SLOT_RETAINED", claim.get("worker_slot_id")),
        (claim.get("route_binding") is None, "R145_CLOSEOUT_ROUTE_BINDING_RETAINED", claim.get("route_binding")),
        (claim.get("resource_class") == "NO_ACTIVE_IMPLEMENTATION", "R145_CLOSEOUT_RESOURCE_CLASS_ACTIVE", claim.get("resource_class")),
        (_empty_list(claim, "write_paths"), "R145_CLOSEOUT_CLAIM_WRITE_PATHS_RETAINED", claim.get("write_paths")),
        (_empty_list(claim, "read_paths"), "R145_CLOSEOUT_CLAIM_READ_PATHS_RETAINED", claim.get("read_paths")),
        (_empty_list(claim, "interfaces"), "R145_CLOSEOUT_CLAIM_INTERFACES_RETAINED", claim.get("interfaces")),
        (_empty_list(claim, "read_domains"), "R145_CLOSEOUT_CLAIM_READ_DOMAINS_RETAINED", claim.get("read_domains")),
        (_empty_list(claim, "write_domains"), "R145_CLOSEOUT_CLAIM_WRITE_DOMAINS_RETAINED", claim.get("write_domains")),
        (_empty_list(claim, "authority_claims"), "R145_CLOSEOUT_CLAIM_AUTHORITY_RETAINED", claim.get("authority_claims")),
        (route_doc.get("status") == "CLOSED_HISTORY_ONLY", "R145_CLOSEOUT_ROUTE_NOT_CLOSED", route_doc.get("status")),
        (_bool_is(route_doc.get("execution_allowed"), False), "R145_CLOSEOUT_ROUTE_EXECUTION_RETAINED", route_doc.get("execution_allowed")),
        (_bool_is(route_doc.get("runtime_code_change_allowed"), False), "R145_CLOSEOUT_RUNTIME_WRITE_RETAINED", route_doc.get("runtime_code_change_allowed")),
        (_bool_is(route_doc.get("automatic_resume"), False), "R145_CLOSEOUT_AUTOMATIC_RESUME_RETAINED", route_doc.get("automatic_resume")),
        (_bool_is(route_doc.get("merge_authorized"), False), "R145_CLOSEOUT_MERGE_AUTHORITY_RETAINED", route_doc.get("merge_authorized")),
        (_empty_list(write_scope, "implementation"), "R145_CLOSEOUT_ROUTE_WRITE_PATHS_RETAINED", write_scope.get("implementation")),
        (_empty_list(write_scope, "exact_action_constraints"), "R145_CLOSEOUT_ROUTE_ACTION_CONSTRAINTS_RETAINED", write_scope.get("exact_action_constraints")),
        (_empty_list(write_scope, "cross_repo"), "R145_CLOSEOUT_CROSS_REPO_WRITE_RETAINED", write_scope.get("cross_repo")),
        (lane_release.get("state") == "R145_S0F_ACCEPTED_MERGED / NO_ACTIVE_IMPLEMENTATION", "R145_CLOSEOUT_RELEASE_GATE_STATE_INVALID", lane_release.get("state")),
        (lane_release.get("worker_slot_id") is None, "R145_CLOSEOUT_RELEASE_GATE_SLOT_RETAINED", lane_release.get("worker_slot_id")),
        (_bool_is(lane_release.get("runtime_write_allowed"), False), "R145_CLOSEOUT_RELEASE_GATE_RUNTIME_WRITE_RETAINED", lane_release.get("runtime_write_allowed")),
        (_bool_is(lane_release.get("implementation_route_allowed"), False), "R145_CLOSEOUT_RELEASE_GATE_ROUTE_RETAINED", lane_release.get("implementation_route_allowed")),
        (lane.get("observed_state") == "R145_S0F_ACCEPTED_MERGED / NO_ACTIVE_IMPLEMENTATION", "R145_CLOSEOUT_PROGRAM_LANE_STATE_INVALID", lane.get("observed_state")),
        (lane.get("active_execution_route") is None, "R145_CLOSEOUT_PROGRAM_LANE_ROUTE_RETAINED", lane.get("active_execution_route")),
        (lane.get("implementation_owner") is None, "R145_CLOSEOUT_PROGRAM_LANE_OWNER_RETAINED", lane.get("implementation_owner")),
        (receipt_doc.get("status") in {"READY_FOR_INDEPENDENT_EXACT_HEAD_REVIEW", "CLOSEOUT_CANDIDATE / REQUIRES_INDEPENDENT_EXACT_HEAD_REVIEW"}, "R145_CLOSEOUT_RECEIPT_STATE_INVALID", receipt_doc.get("status")),
        (accepted_runtime.get("task_id") == TASK_ID, "R145_CLOSEOUT_RECEIPT_TASK_MISMATCH", accepted_runtime.get("task_id")),
        (accepted_runtime.get("runtime_pr") == RUNTIME_PR, "R145_CLOSEOUT_RECEIPT_PR_MISMATCH", accepted_runtime.get("runtime_pr")),
        (accepted_runtime.get("review_disposition") == "ACCEPT", "R145_CLOSEOUT_RECEIPT_REVIEW_NOT_ACCEPT", accepted_runtime.get("review_disposition")),
        (accepted_runtime.get("blocker_count") == 0, "R145_CLOSEOUT_RECEIPT_BLOCKERS_RETAINED", accepted_runtime.get("blocker_count")),
        (closeout_effects.get("gpt_engineering_worker", {}).get("expected_active_slots") == 0, "R145_CLOSEOUT_RECEIPT_EXPECTS_ACTIVE_SLOT", closeout_effects.get("gpt_engineering_worker")),
        (closeout_effects.get("lane_a_work_claim", {}).get("expected_state") == "CLOSED_NO_ACTIVE_IMPLEMENTATION", "R145_CLOSEOUT_RECEIPT_CLAIM_EXPECTATION_INVALID", closeout_effects.get("lane_a_work_claim")),
        (closeout_effects.get("r145_route", {}).get("expected_state") == "CLOSED_HISTORY_ONLY", "R145_CLOSEOUT_RECEIPT_ROUTE_EXPECTATION_INVALID", closeout_effects.get("r145_route")),
    ]
    for ok, code, actual in closed_checks:
        if not ok:
            findings.append({"code": code, "actual": actual})

    if findings:
        return {"status": "FAIL", "mode": INVALID_MODE, "findings": findings}
    return {"status": "PASS", "mode": CLOSED_MODE, "findings": []}


def evaluate_repository(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    return evaluate_documents(
        load_yaml(root / WORKER_REGISTRY),
        load_yaml(root / CLAIMS_FILE),
        load_yaml(root / ROUTE_FILE),
        load_yaml(root / RELEASE_GATE_FILE),
        load_yaml(root / PROGRAM_LANES_FILE),
        load_yaml(root / CLOSEOUT_RECEIPT_FILE),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed R145 ACTIVE-vs-CLOSED lifecycle gate.")
    parser.add_argument("--repo-root", default="../..")
    parser.add_argument("--mode-only", action="store_true")
    args = parser.parse_args()
    result = evaluate_repository(Path(args.repo_root))
    if args.mode_only:
        print(result["mode"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
