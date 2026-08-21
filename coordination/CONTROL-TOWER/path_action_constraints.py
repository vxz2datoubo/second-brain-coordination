from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from control_tower import load_yaml

WORKER_REGISTRY = "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
CLAIMS_FILE = "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"
ALLOWED_ACTIONS = frozenset({"CREATE", "MODIFY", "DELETE"})
ALLOWED_FINAL_STATES = frozenset({"PRESENT", "ABSENT"})
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class ActionFinding:
    severity: str
    code: str
    message: str
    evidence: dict[str, Any]


@dataclass(frozen=True)
class PathActionConstraint:
    path: str
    allowed_actions: tuple[str, ...]
    transition_baseline_sha: str | None = None
    required_final_state: str | None = None


def _norm_path(value: str) -> str:
    value = value.replace("\\", "/").strip()
    while value.startswith("./"):
        value = value[2:]
    return str(PurePosixPath(value))


def _canonical_constraint_map(value: dict[str, PathActionConstraint]) -> dict[str, dict[str, Any]]:
    return {
        path: {
            "allowed_actions": list(constraint.allowed_actions),
            "transition_baseline_sha": constraint.transition_baseline_sha,
            "required_final_state": constraint.required_final_state,
        }
        for path, constraint in sorted(value.items())
    }


def _parse_constraints(raw: Any, source: str) -> tuple[dict[str, PathActionConstraint], list[ActionFinding]]:
    findings: list[ActionFinding] = []
    if raw is None:
        return {}, findings
    if not isinstance(raw, list):
        return {}, [
            ActionFinding(
                "ERROR",
                "PATH_ACTION_CONSTRAINTS_NOT_LIST",
                "Path action constraints must be a list of exact path/action mappings.",
                {"source": source, "actual_type": type(raw).__name__},
            )
        ]

    result: dict[str, PathActionConstraint] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_CONSTRAINT_NOT_MAPPING",
                    "Each path action constraint must be a mapping.",
                    {"source": source, "index": index},
                )
            )
            continue

        path = item.get("path")
        actions = item.get("allowed_actions")
        baseline = item.get("transition_baseline_sha")
        final_state = item.get("required_final_state")

        if not isinstance(path, str) or not path.strip():
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_CONSTRAINT_PATH_INVALID",
                    "A constrained path must be a non-empty exact repository path.",
                    {"source": source, "index": index, "actual": path},
                )
            )
            continue
        path = _norm_path(path)
        if any(token in path for token in ("*", "?", "[", "]")):
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_CONSTRAINT_NOT_EXACT",
                    "Action-constrained paths must be exact paths; wildcard constraints are forbidden.",
                    {"source": source, "index": index, "path": path},
                )
            )
            continue

        if not isinstance(actions, list) or not actions or any(not isinstance(action, str) for action in actions):
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_ALLOWED_ACTIONS_INVALID",
                    "allowed_actions must be a non-empty list of explicit action names.",
                    {"source": source, "index": index, "actual": actions},
                )
            )
            continue
        normalized_actions = tuple(sorted({action.strip().upper() for action in actions if action.strip()}))
        unknown = sorted(set(normalized_actions) - ALLOWED_ACTIONS)
        if unknown:
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_UNKNOWN_ACTION",
                    "Unknown path action names fail closed.",
                    {"source": source, "index": index, "unknown": unknown, "allowed": sorted(ALLOWED_ACTIONS)},
                )
            )
            continue

        if baseline is not None:
            if not isinstance(baseline, str) or not _HEX40.fullmatch(baseline):
                findings.append(
                    ActionFinding(
                        "ERROR",
                        "PATH_ACTION_BASELINE_SHA_INVALID",
                        "transition_baseline_sha must be an exact lowercase 40-hex commit when declared.",
                        {"source": source, "index": index, "actual": baseline},
                    )
                )
                continue
            if not isinstance(final_state, str) or final_state.upper() not in ALLOWED_FINAL_STATES:
                findings.append(
                    ActionFinding(
                        "ERROR",
                        "PATH_ACTION_FINAL_STATE_INVALID",
                        "A transition baseline requires required_final_state PRESENT or ABSENT.",
                        {"source": source, "index": index, "actual": final_state},
                    )
                )
                continue
            final_state = final_state.upper()
        elif final_state is not None:
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_FINAL_STATE_WITHOUT_BASELINE",
                    "required_final_state may not be declared without a transition_baseline_sha.",
                    {"source": source, "index": index},
                )
            )
            continue

        if path in result:
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_DUPLICATE_PATH",
                    "A path may have only one canonical action constraint entry per authority source.",
                    {"source": source, "path": path},
                )
            )
            continue
        result[path] = PathActionConstraint(
            path=path,
            allowed_actions=normalized_actions,
            transition_baseline_sha=baseline,
            required_final_state=final_state,
        )
    return result, findings


def _string_paths(raw: Any, source: str) -> tuple[list[str], list[ActionFinding]]:
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        return [], [
            ActionFinding(
                "ERROR",
                "PATH_ACTION_WRITE_PATHS_INVALID",
                "Write paths must remain a list of strings before action constraints can be enforced.",
                {"source": source, "actual_type": type(raw).__name__},
            )
        ]
    return [_norm_path(item) for item in raw], []


def _pattern_covers_exact(pattern: str, exact_path: str) -> bool:
    pattern = _norm_path(pattern)
    exact_path = _norm_path(exact_path)
    if pattern == exact_path:
        return True
    if pattern.endswith("/**"):
        root = pattern[:-3].rstrip("/")
        return exact_path == root or exact_path.startswith(root + "/")
    if any(token in pattern for token in ("*", "?", "[", "]")):
        from fnmatch import fnmatchcase

        return fnmatchcase(exact_path, pattern)
    return False


def _find_one(items: Any, *, key: str, value: str, source: str) -> tuple[dict[str, Any] | None, list[ActionFinding]]:
    if not isinstance(items, list):
        return None, [
            ActionFinding("ERROR", "PATH_ACTION_AUTHORITY_LIST_INVALID", "Authority entries must be a list.", {"source": source})
        ]
    matches = [item for item in items if isinstance(item, dict) and str(item.get(key)) == value]
    if len(matches) != 1:
        return None, [
            ActionFinding(
                "ERROR",
                "PATH_ACTION_AUTHORITY_IDENTITY_NOT_UNIQUE",
                "Action authority must resolve to exactly one matching entry.",
                {"source": source, "key": key, "value": value, "match_count": len(matches)},
            )
        ]
    return matches[0], []


def validate_contract(
    repo_root: Path,
    *,
    worker_slot_id: str,
    lane_id: str,
    route_file: str,
) -> dict[str, Any]:
    root = repo_root.resolve()
    findings: list[ActionFinding] = []

    worker_doc = load_yaml(root / WORKER_REGISTRY)
    worker, worker_findings = _find_one(
        worker_doc.get("worker_slots"), key="worker_slot_id", value=worker_slot_id, source="worker_registry"
    )
    findings.extend(worker_findings)

    claims_doc = load_yaml(root / CLAIMS_FILE)
    claim, claim_findings = _find_one(claims_doc.get("claims"), key="lane_id", value=lane_id, source="work_claim")
    findings.extend(claim_findings)

    route_path = root / route_file
    if not route_path.exists():
        findings.append(
            ActionFinding(
                "ERROR",
                "PATH_ACTION_ROUTE_MISSING",
                "The exact route authority file is required for action-constraint reconciliation.",
                {"route_file": route_file},
            )
        )
        route: dict[str, Any] = {}
    else:
        route = load_yaml(route_path)

    worker_constraints, parsed = _parse_constraints(
        worker.get("path_action_constraints") if worker else None, "worker_registry"
    )
    findings.extend(parsed)
    claim_constraints, parsed = _parse_constraints(
        claim.get("path_action_constraints") if claim else None, "work_claim"
    )
    findings.extend(parsed)
    route_write_scope = route.get("write_scope") if isinstance(route.get("write_scope"), dict) else {}
    route_constraints, parsed = _parse_constraints(route_write_scope.get("exact_action_constraints"), "route")
    findings.extend(parsed)

    worker_write_paths, parsed = _string_paths(worker.get("write_paths") if worker else None, "worker_registry")
    findings.extend(parsed)
    claim_write_paths, parsed = _string_paths(claim.get("write_paths") if claim else None, "work_claim")
    findings.extend(parsed)
    route_write_paths, parsed = _string_paths(route_write_scope.get("implementation"), "route")
    findings.extend(parsed)

    if worker is not None and claim is not None:
        claim_binding = claim.get("route_binding") if isinstance(claim.get("route_binding"), dict) else {}
        route_binding = route.get("binding") if isinstance(route.get("binding"), dict) else {}
        route_executor = route.get("executor") if isinstance(route.get("executor"), dict) else {}
        identity_checks = {
            "worker_slot_id": (worker.get("worker_slot_id"), claim.get("worker_slot_id"), route_executor.get("worker_slot_id")),
            "task_id": (worker.get("task_id"), claim_binding.get("task_id"), route_binding.get("task_id")),
            "route_epoch": (worker.get("route_epoch"), claim_binding.get("route_epoch"), route_binding.get("route_epoch")),
            "issue": (worker.get("issue"), claim_binding.get("issue"), route_binding.get("issue")),
            "pr": (worker.get("pr"), claim_binding.get("pr"), route_binding.get("implementation_pr")),
            "branch": (worker.get("branch"), claim_binding.get("branch"), route_binding.get("implementation_branch")),
        }
        for field, values in identity_checks.items():
            if len(set(json.dumps(value, sort_keys=True, default=str) for value in values)) != 1:
                findings.append(
                    ActionFinding(
                        "ERROR",
                        "PATH_ACTION_AUTHORITY_IDENTITY_DRIFT",
                        "Worker, Work Claim and Route must identify the same execution authority before action constraints are usable.",
                        {"field": field, "worker_claim_route": values},
                    )
                )

    write_sets = {
        "worker_registry": sorted(worker_write_paths),
        "work_claim": sorted(claim_write_paths),
        "route": sorted(route_write_paths),
    }
    if len({json.dumps(value, ensure_ascii=False) for value in write_sets.values()}) != 1:
        findings.append(
            ActionFinding(
                "ERROR",
                "PATH_ACTION_WRITE_SURFACE_DRIFT",
                "Worker, Work Claim and Route write surfaces must match exactly when action constraints are present.",
                write_sets,
            )
        )

    constraint_sets = {
        "worker_registry": _canonical_constraint_map(worker_constraints),
        "work_claim": _canonical_constraint_map(claim_constraints),
        "route": _canonical_constraint_map(route_constraints),
    }
    if len({json.dumps(value, ensure_ascii=False, sort_keys=True) for value in constraint_sets.values()}) != 1:
        findings.append(
            ActionFinding(
                "ERROR",
                "PATH_ACTION_CONSTRAINT_DRIFT",
                "Worker, Work Claim and Route path-action semantics must match exactly.",
                constraint_sets,
            )
        )

    canonical_constraints = worker_constraints if worker_constraints else claim_constraints if claim_constraints else route_constraints
    for exact_path, constraint in canonical_constraints.items():
        for source, paths in write_sets.items():
            if exact_path not in paths:
                findings.append(
                    ActionFinding(
                        "ERROR",
                        "PATH_ACTION_CONSTRAINED_PATH_NOT_WRITABLE",
                        "Every constrained path must also be present as the same exact write path in all authority sources.",
                        {"source": source, "path": exact_path},
                    )
                )
            broader = [path for path in paths if path != exact_path and _pattern_covers_exact(path, exact_path)]
            if broader:
                findings.append(
                    ActionFinding(
                        "ERROR",
                        "PATH_ACTION_BROADER_WRITE_BYPASS",
                        "A broader write surface may not cover an action-constrained exact path.",
                        {"source": source, "path": exact_path, "broader_paths": broader},
                    )
                )
        if not constraint.allowed_actions:
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_EMPTY_AUTHORITY",
                    "An action-constrained path must allow at least one explicit action.",
                    {"path": exact_path},
                )
            )

    errors = [asdict(item) for item in findings if item.severity == "ERROR"]
    return {
        "status": "PASS" if not errors else "FAIL",
        "worker_slot_id": worker_slot_id,
        "lane_id": lane_id,
        "route_file": route_file,
        "constraints": _canonical_constraint_map(canonical_constraints),
        "findings": [asdict(item) for item in findings],
    }


def _git_diff_entries(repo_root: Path, base_sha: str, head_sha: str) -> list[tuple[str, tuple[str, ...]]]:
    output = subprocess.check_output(
        ["git", "diff", "--name-status", "-M", base_sha, head_sha], cwd=repo_root, text=True
    )
    result: list[tuple[str, tuple[str, ...]]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        result.append((parts[0], tuple(_norm_path(item) for item in parts[1:])))
    return result


def _derived_action(status: str) -> str:
    code = status[:1].upper()
    if code == "A":
        return "CREATE"
    if code == "D":
        return "DELETE"
    if code in {"M", "T"}:
        return "MODIFY"
    return "UNSUPPORTED"


def validate_diff_actions(
    constraints: dict[str, PathActionConstraint], entries: list[tuple[str, tuple[str, ...]]]
) -> list[ActionFinding]:
    findings: list[ActionFinding] = []
    by_path: dict[str, list[tuple[str, tuple[str, ...]]]] = {path: [] for path in constraints}
    for status, paths in entries:
        for constrained_path in constraints:
            if constrained_path in paths:
                by_path[constrained_path].append((status, paths))

    for path, matching in by_path.items():
        allowed = set(constraints[path].allowed_actions)
        for status, paths in matching:
            action = _derived_action(status)
            if action not in allowed:
                findings.append(
                    ActionFinding(
                        "ERROR",
                        "PATH_ACTION_DIFF_VIOLATION",
                        "The actual Git diff action is not authorized for this exact constrained path.",
                        {
                            "path": path,
                            "git_status": status,
                            "diff_paths": list(paths),
                            "derived_action": action,
                            "allowed_actions": sorted(allowed),
                        },
                    )
                )
    return findings


def validate_diff(
    repo_root: Path,
    *,
    base_sha: str,
    head_sha: str,
    constraints: dict[str, PathActionConstraint],
) -> dict[str, Any]:
    entries = _git_diff_entries(repo_root.resolve(), base_sha, head_sha)
    findings = validate_diff_actions(constraints, entries)
    errors = [asdict(item) for item in findings if item.severity == "ERROR"]
    return {
        "status": "PASS" if not errors else "FAIL",
        "base_sha": base_sha,
        "head_sha": head_sha,
        "constrained_paths": sorted(constraints),
        "findings": [asdict(item) for item in findings],
    }


def _git_commit_exists(repo_root: Path, commit: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def _git_object_exists(repo_root: Path, commit: str, path: str) -> bool:
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{path}"],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return probe.returncode == 0


def validate_transition_lineage(
    repo_root: Path,
    *,
    head_sha: str,
    constraints: dict[str, PathActionConstraint],
) -> dict[str, Any]:
    root = repo_root.resolve()
    findings: list[ActionFinding] = []
    checked: dict[str, Any] = {}

    for path, constraint in constraints.items():
        baseline = constraint.transition_baseline_sha
        final_state = constraint.required_final_state
        if baseline is None:
            continue

        baseline_commit_exists = _git_commit_exists(root, baseline)
        if not baseline_commit_exists:
            checked[path] = {
                "baseline_sha": baseline,
                "baseline_commit_exists": False,
                "baseline_is_ancestor": False,
                "baseline_present": False,
                "head_present": _git_object_exists(root, head_sha, path),
                "required_final_state": final_state,
                "transition_entries": [],
            }
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_TRANSITION_BASELINE_UNAVAILABLE",
                    "The governed cleanup baseline commit must exist in the checked repository history.",
                    {"path": path, "baseline_sha": baseline, "head_sha": head_sha},
                )
            )
            continue

        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", baseline, head_sha],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
        baseline_present = _git_object_exists(root, baseline, path)
        head_present = _git_object_exists(root, head_sha, path)
        transition_entries = _git_diff_entries(root, baseline, head_sha)
        relevant_entries = [entry for entry in transition_entries if path in entry[1]]
        findings.extend(validate_diff_actions({path: constraint}, relevant_entries))

        checked[path] = {
            "baseline_sha": baseline,
            "baseline_commit_exists": True,
            "baseline_is_ancestor": ancestor,
            "baseline_present": baseline_present,
            "head_present": head_present,
            "required_final_state": final_state,
            "transition_entries": [[status, list(paths)] for status, paths in relevant_entries],
        }

        if not ancestor:
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_TRANSITION_BASELINE_NOT_ANCESTOR",
                    "The governed cleanup baseline must remain an ancestor of the runtime head; history rewrite or unrelated substitution fails closed.",
                    {"path": path, "baseline_sha": baseline, "head_sha": head_sha},
                )
            )
        if not baseline_present:
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_TRANSITION_BASELINE_PATH_MISSING",
                    "The governed cleanup baseline must actually contain the constrained path.",
                    {"path": path, "baseline_sha": baseline},
                )
            )
        if final_state == "ABSENT" and head_present:
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_REQUIRED_FINAL_STATE_VIOLATION",
                    "The constrained path must be absent from the governed runtime head after cleanup.",
                    {"path": path, "head_sha": head_sha, "required_final_state": final_state},
                )
            )
        if final_state == "PRESENT" and not head_present:
            findings.append(
                ActionFinding(
                    "ERROR",
                    "PATH_ACTION_REQUIRED_FINAL_STATE_VIOLATION",
                    "The constrained path must be present in the governed runtime head.",
                    {"path": path, "head_sha": head_sha, "required_final_state": final_state},
                )
            )
        if baseline_present and final_state == "ABSENT":
            actions = [_derived_action(status) for status, _ in relevant_entries]
            if actions != ["DELETE"]:
                findings.append(
                    ActionFinding(
                        "ERROR",
                        "PATH_ACTION_DELETE_TRANSITION_NOT_EXACT",
                        "A DELETE-only cleanup must resolve from baseline-present to final-absent as exactly one net DELETE transition.",
                        {"path": path, "actions": actions, "entries": checked[path]["transition_entries"]},
                    )
                )

    errors = [asdict(item) for item in findings if item.severity == "ERROR"]
    return {
        "status": "PASS" if not errors else "FAIL",
        "head_sha": head_sha,
        "checked": checked,
        "findings": [asdict(item) for item in findings],
    }


def _constraints_from_contract(result: dict[str, Any]) -> dict[str, PathActionConstraint]:
    raw = []
    for path, spec in (result.get("constraints") or {}).items():
        raw.append({"path": path, **spec})
    constraints, findings = _parse_constraints(raw, "validated_contract")
    if findings:
        raise ValueError("validated contract could not be reconstructed")
    return constraints


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate path-level action constraints across Worker/Claim/Route authority.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--worker-slot", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--route-file", required=True)
    parser.add_argument("--base-sha")
    parser.add_argument("--head-sha")
    parser.add_argument("--enforce-transition-lineage", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo_root)
    contract = validate_contract(root, worker_slot_id=args.worker_slot, lane_id=args.lane, route_file=args.route_file)
    output: dict[str, Any] = {"contract": contract}
    exit_code = 0 if contract["status"] == "PASS" else 2

    if bool(args.base_sha) != bool(args.head_sha):
        parser.error("--base-sha and --head-sha must be supplied together")

    constraints: dict[str, PathActionConstraint] = {}
    if contract["status"] == "PASS":
        constraints = _constraints_from_contract(contract)

    if args.base_sha and args.head_sha and constraints:
        diff = validate_diff(root, base_sha=args.base_sha, head_sha=args.head_sha, constraints=constraints)
        output["diff"] = diff
        if diff["status"] != "PASS":
            exit_code = 2

    if args.enforce_transition_lineage:
        if not args.head_sha:
            parser.error("--enforce-transition-lineage requires --head-sha")
        if contract["status"] == "PASS":
            transition = validate_transition_lineage(root, head_sha=args.head_sha, constraints=constraints)
            output["transition"] = transition
            if transition["status"] != "PASS":
                exit_code = 2

    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
