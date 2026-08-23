from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from control_tower import load_yaml
from path_action_constraints import _git_diff_entries
from path_action_policy import validate_full_diff_write_surface

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
ACCEPTED_RUNTIME_HEAD = "a82606b2d3b6605c51bd05e98cd5f87b72850389"
ACCEPTED_RUNTIME_MERGE = "935840769ca9ac032807066b3e0d3d1b780a55b4"
ACCEPTED_RUNTIME_TREE = "615043bbb9159f19e603a741d5ad3ccbd837cef3"

ACTIVE_MODE = "ACTIVE_PATH_ACTION"
CLOSED_MODE = "CLOSED_FAIL_CLOSED"
INVALID_MODE = "INVALID_MIXED_STATE"

# R145 closeout is a one-time, exact control-plane/lifecycle mutation.  CLOSED mode
# must never become a generic write authority.  These are the only base->head
# changes accepted by the lifecycle gate, with exact Git status semantics.
CLOSEOUT_REQUIRED_DIFF: dict[str, str] = {
    ".github/workflows/r145-final-active-gate.yml": "M",
    "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml": "M",
    "coordination/ACTIVE-PROGRAM-LANES.yaml": "M",
    "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml": "M",
    CLOSEOUT_RECEIPT_FILE: "A",
    "coordination/CONTROL-TOWER/RELEASE-GATE.yaml": "M",
    "coordination/CONTROL-TOWER/r145_lifecycle_gate.py": "A",
    "coordination/CONTROL-TOWER/tests/test_r145_lifecycle_gate.py": "A",
    "coordination/PROGRAM-CONTROL-TOWER.md": "M",
    ROUTE_FILE: "M",
}

# The closeout itself necessarily amends r145-final-active-gate.yml to introduce
# lifecycle semantics.  It is the sole protected-root exception and is still
# exact-path/status pinned above.  Every other R145 protected enforcement root
# remains mechanically immutable in CLOSED mode.
CLOSEOUT_FORBIDDEN_PROTECTED_PATHS = (
    ".github/workflows/runtime-governance-root.yml",
    "coordination/CONTROL-TOWER/path_action_constraints.py",
    "coordination/CONTROL-TOWER/path_action_policy.py",
    "coordination/CONTROL-TOWER/R145-BOOTSTRAP-CLEANUP-SCOPE-AMENDMENT.yaml",
)


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
        (accepted_runtime.get("accepted_exact_head") == ACCEPTED_RUNTIME_HEAD, "R145_CLOSEOUT_RECEIPT_HEAD_MISMATCH", accepted_runtime.get("accepted_exact_head")),
        (accepted_runtime.get("runtime_merge_commit") == ACCEPTED_RUNTIME_MERGE, "R145_CLOSEOUT_RECEIPT_MERGE_MISMATCH", accepted_runtime.get("runtime_merge_commit")),
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


def evaluate_closeout_diff_entries(entries: list[tuple[str, tuple[str, ...]]]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    actual: dict[str, str] = {}
    for status, paths in entries:
        if len(paths) != 1:
            findings.append(
                {
                    "code": "R145_CLOSEOUT_RENAME_OR_MULTI_PATH_DIFF_FORBIDDEN",
                    "git_status": status,
                    "paths": list(paths),
                }
            )
        for path in paths:
            if path in actual:
                findings.append({"code": "R145_CLOSEOUT_DUPLICATE_DIFF_PATH", "path": path})
            actual[path] = status[:1].upper()

    expected = dict(CLOSEOUT_REQUIRED_DIFF)
    for path, expected_status in expected.items():
        actual_status = actual.get(path)
        if actual_status != expected_status:
            findings.append(
                {
                    "code": "R145_CLOSEOUT_REQUIRED_DIFF_STATUS_MISMATCH",
                    "path": path,
                    "expected": expected_status,
                    "actual": actual_status,
                }
            )
    for path, actual_status in actual.items():
        if path not in expected:
            findings.append(
                {
                    "code": "R145_CLOSEOUT_DIFF_OUTSIDE_AUTHORIZED_SURFACE",
                    "path": path,
                    "actual": actual_status,
                }
            )

    return {
        "status": "PASS" if not findings else "FAIL",
        "expected": expected,
        "actual": actual,
        "findings": findings,
    }


def _git_output(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True, stderr=subprocess.STDOUT).strip()


def evaluate_closeout_git(repo_root: Path, base_sha: str, head_sha: str) -> dict[str, Any]:
    root = repo_root.resolve()
    findings: list[dict[str, Any]] = []

    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ACCEPTED_RUNTIME_MERGE, base_sha],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        findings.append(
            {
                "code": "R145_CLOSEOUT_BASE_NOT_DESCENDANT_OF_ACCEPTED_RUNTIME_MERGE",
                "base_sha": base_sha,
                "accepted_runtime_merge": ACCEPTED_RUNTIME_MERGE,
                "detail": str(exc),
            }
        )

    try:
        runtime_parent_2 = _git_output(root, "rev-parse", f"{ACCEPTED_RUNTIME_MERGE}^2")
        runtime_tree = _git_output(root, "rev-parse", f"{ACCEPTED_RUNTIME_MERGE}^{{tree}}")
        if runtime_parent_2 != ACCEPTED_RUNTIME_HEAD:
            findings.append(
                {
                    "code": "R145_CLOSEOUT_ACCEPTED_RUNTIME_PARENT_DRIFT",
                    "expected": ACCEPTED_RUNTIME_HEAD,
                    "actual": runtime_parent_2,
                }
            )
        if runtime_tree != ACCEPTED_RUNTIME_TREE:
            findings.append(
                {
                    "code": "R145_CLOSEOUT_ACCEPTED_RUNTIME_TREE_DRIFT",
                    "expected": ACCEPTED_RUNTIME_TREE,
                    "actual": runtime_tree,
                }
            )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        findings.append({"code": "R145_CLOSEOUT_ACCEPTED_RUNTIME_OBJECT_UNAVAILABLE", "detail": str(exc)})

    try:
        entries = _git_diff_entries(root, base_sha, head_sha)
        exact = evaluate_closeout_diff_entries(entries)
        findings.extend(exact["findings"])
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        entries = []
        exact = {"status": "FAIL", "expected": dict(CLOSEOUT_REQUIRED_DIFF), "actual": {}, "findings": []}
        findings.append({"code": "R145_CLOSEOUT_REAL_DIFF_UNAVAILABLE", "detail": str(exc)})

    # Reuse the canonical full-diff write-surface validator so CLOSED mode is
    # mechanically checked against the real base/head diff instead of merely
    # trusting lifecycle state documents.
    try:
        surface = validate_full_diff_write_surface(
            root,
            base_sha=base_sha,
            head_sha=head_sha,
            write_paths=sorted(CLOSEOUT_REQUIRED_DIFF),
            protected_paths=list(CLOSEOUT_FORBIDDEN_PROTECTED_PATHS),
        )
        if surface.get("status") != "PASS":
            for item in surface.get("findings", []):
                findings.append(
                    {
                        "code": item.get("code", "R145_CLOSEOUT_FULL_DIFF_POLICY_FAILED"),
                        "policy_finding": item,
                    }
                )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        surface = {"status": "FAIL", "checked": [], "findings": []}
        findings.append({"code": "R145_CLOSEOUT_FULL_DIFF_POLICY_UNAVAILABLE", "detail": str(exc)})

    return {
        "status": "PASS" if not findings else "FAIL",
        "base_sha": base_sha,
        "head_sha": head_sha,
        "accepted_runtime_head": ACCEPTED_RUNTIME_HEAD,
        "accepted_runtime_merge": ACCEPTED_RUNTIME_MERGE,
        "accepted_runtime_tree": ACCEPTED_RUNTIME_TREE,
        "exact_closeout_diff": exact,
        "full_diff_write_surface": surface,
        "findings": findings,
    }


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
    parser.add_argument("--base-sha")
    parser.add_argument("--head-sha")
    args = parser.parse_args()
    if bool(args.base_sha) != bool(args.head_sha):
        parser.error("--base-sha and --head-sha must be supplied together")

    root = Path(args.repo_root)
    result = evaluate_repository(root)
    if args.mode_only:
        print(result["mode"])
        return 0 if result["status"] == "PASS" else 2

    if result["status"] == "PASS" and result["mode"] == CLOSED_MODE:
        if not args.base_sha or not args.head_sha:
            result = {
                "status": "FAIL",
                "mode": INVALID_MODE,
                "findings": [{"code": "R145_CLOSEOUT_DIFF_BINDING_REQUIRED"}],
            }
        else:
            diff_result = evaluate_closeout_git(root, args.base_sha, args.head_sha)
            result = {
                **result,
                "closeout_git": diff_result,
                "status": "PASS" if diff_result["status"] == "PASS" else "FAIL",
                "mode": CLOSED_MODE if diff_result["status"] == "PASS" else INVALID_MODE,
                "findings": diff_result["findings"],
            }

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
