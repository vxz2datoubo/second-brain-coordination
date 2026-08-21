from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from control_tower import load_yaml
from path_action_constraints import (
    CLAIMS_FILE,
    WORKER_REGISTRY,
    ActionFinding,
    PathActionConstraint,
    _canonical_constraint_map,
    _find_one,
    _git_diff_entries,
    _parse_constraints,
    _pattern_covers_exact,
    _string_paths,
    validate_contract,
)


@dataclass(frozen=True)
class RequiredContract:
    constraints: dict[str, PathActionConstraint]
    anchor_file: str
    general_s0f_write_allowed: bool
    runtime_workflow_write_allowed: bool
    protected_enforcement_paths: tuple[str, ...]


def _load_required_contract(repo_root: Path, anchor_file: str) -> tuple[RequiredContract | None, list[ActionFinding]]:
    root = repo_root.resolve()
    path = root / anchor_file
    if not path.exists():
        return None, [
            ActionFinding(
                "ERROR",
                "PATH_ACTION_REQUIRED_CONTRACT_ANCHOR_MISSING",
                "The governed required-contract anchor must exist outside the runtime worker write surface.",
                {"anchor_file": anchor_file},
            )
        ]

    doc = load_yaml(path)
    amendment = doc.get("amendment") if isinstance(doc.get("amendment"), dict) else None
    if amendment is None:
        return None, [
            ActionFinding(
                "ERROR",
                "PATH_ACTION_REQUIRED_CONTRACT_ANCHOR_INVALID",
                "The required-contract anchor must contain an amendment mapping.",
                {"anchor_file": anchor_file},
            )
        ]

    raw = [
        {
            "path": amendment.get("exact_path"),
            "allowed_actions": amendment.get("allowed_actions"),
            "transition_baseline_sha": amendment.get("transition_baseline_sha"),
            "required_final_state": amendment.get("required_final_state"),
        }
    ]
    constraints, findings = _parse_constraints(raw, "required_contract_anchor")
    if findings:
        return None, findings
    if len(constraints) != 1:
        return None, [
            ActionFinding(
                "ERROR",
                "PATH_ACTION_REQUIRED_CONTRACT_CARDINALITY_INVALID",
                "The bounded cleanup anchor must define exactly one required path-action contract.",
                {"anchor_file": anchor_file, "constraint_count": len(constraints)},
            )
        ]

    general_s0f = amendment.get("general_s0f_write_allowed")
    if general_s0f is not False:
        return None, [
            ActionFinding(
                "ERROR",
                "PATH_ACTION_REQUIRED_CONTRACT_GENERAL_S0F_NOT_FORBIDDEN",
                "The immutable cleanup anchor must explicitly keep general S0F write authority forbidden.",
                {"anchor_file": anchor_file, "actual": general_s0f},
            )
        ]

    runtime_workflow_write = amendment.get("runtime_workflow_write_allowed")
    if runtime_workflow_write is not False:
        return None, [
            ActionFinding(
                "ERROR",
                "PATH_ACTION_RUNTIME_WORKFLOW_WRITE_NOT_FORBIDDEN",
                "The required contract must explicitly forbid runtime PR workflow writes.",
                {"anchor_file": anchor_file, "actual": runtime_workflow_write},
            )
        ]

    protected_raw = amendment.get("protected_enforcement_paths")
    if not isinstance(protected_raw, list) or not protected_raw or any(not isinstance(item, str) or not item for item in protected_raw):
        return None, [
            ActionFinding(
                "ERROR",
                "PATH_ACTION_PROTECTED_ENFORCEMENT_PATHS_INVALID",
                "The required contract must define a non-empty list of exact governance-owned enforcement paths.",
                {"anchor_file": anchor_file, "actual": protected_raw},
            )
        ]

    protected = tuple(sorted(set(protected_raw)))
    return RequiredContract(
        constraints=constraints,
        anchor_file=anchor_file,
        general_s0f_write_allowed=False,
        runtime_workflow_write_allowed=False,
        protected_enforcement_paths=protected,
    ), []


def _load_common_write_surface(
    repo_root: Path,
    *,
    worker_slot_id: str,
    lane_id: str,
    route_file: str,
) -> tuple[list[str], list[ActionFinding]]:
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
    route = load_yaml(route_path) if route_path.exists() else {}
    route_scope = route.get("write_scope") if isinstance(route.get("write_scope"), dict) else {}

    worker_paths, parsed = _string_paths(worker.get("write_paths") if worker else None, "worker_registry")
    findings.extend(parsed)
    claim_paths, parsed = _string_paths(claim.get("write_paths") if claim else None, "work_claim")
    findings.extend(parsed)
    route_paths, parsed = _string_paths(route_scope.get("implementation"), "route")
    findings.extend(parsed)

    surfaces = {
        "worker_registry": sorted(worker_paths),
        "work_claim": sorted(claim_paths),
        "route": sorted(route_paths),
    }
    if len({json.dumps(value, ensure_ascii=False) for value in surfaces.values()}) != 1:
        findings.append(
            ActionFinding(
                "ERROR",
                "PATH_ACTION_POLICY_WRITE_SURFACE_DRIFT",
                "Full-diff authorization requires one identical Worker/Claim/Route write surface.",
                surfaces,
            )
        )
        return [], findings
    return sorted(worker_paths), findings


def validate_required_anchor(
    repo_root: Path,
    *,
    worker_slot_id: str,
    lane_id: str,
    route_file: str,
    required_contract_file: str,
) -> dict[str, Any]:
    root = repo_root.resolve()
    findings: list[ActionFinding] = []

    contract = validate_contract(root, worker_slot_id=worker_slot_id, lane_id=lane_id, route_file=route_file)
    if contract["status"] != "PASS":
        findings.append(
            ActionFinding(
                "ERROR",
                "PATH_ACTION_BASE_CONTRACT_INVALID",
                "The underlying Worker/Claim/Route action contract must pass before immutable policy anchoring.",
                {"base_findings": contract.get("findings", [])},
            )
        )

    required, anchor_findings = _load_required_contract(root, required_contract_file)
    findings.extend(anchor_findings)

    actual = contract.get("constraints") or {}
    expected = _canonical_constraint_map(required.constraints) if required else {}
    if not expected:
        findings.append(
            ActionFinding(
                "ERROR",
                "PATH_ACTION_REQUIRED_CONTRACT_EMPTY",
                "The required path-action contract may not disappear or collapse to an empty map.",
                {"required_contract_file": required_contract_file},
            )
        )
    elif actual != expected:
        findings.append(
            ActionFinding(
                "ERROR",
                "PATH_ACTION_REQUIRED_CONTRACT_MISMATCH",
                "Worker/Claim/Route must equal the independently anchored required contract, not merely each other.",
                {"required": expected, "actual": actual, "required_contract_file": required_contract_file},
            )
        )

    write_paths, surface_findings = _load_common_write_surface(
        root, worker_slot_id=worker_slot_id, lane_id=lane_id, route_file=route_file
    )
    findings.extend(surface_findings)

    protected_paths: list[str] = []
    if required:
        for exact_path in required.constraints:
            if exact_path not in write_paths:
                findings.append(
                    ActionFinding(
                        "ERROR",
                        "PATH_ACTION_REQUIRED_PATH_NOT_IN_COMMON_WRITE_SURFACE",
                        "The anchored exact cleanup path must remain an explicit exact path in the common write surface.",
                        {"path": exact_path, "write_paths": write_paths},
                    )
                )

        protected_paths = list(required.protected_enforcement_paths)
        for protected in protected_paths:
            covering = sorted(pattern for pattern in write_paths if _pattern_covers_exact(pattern, protected))
            if covering:
                findings.append(
                    ActionFinding(
                        "ERROR",
                        "PATH_ACTION_PROTECTED_ENFORCEMENT_ROOT_WRITABLE",
                        "Runtime write authority must not cover governance-owned enforcement roots.",
                        {"protected_path": protected, "covering_write_paths": covering},
                    )
                )

    errors = [asdict(item) for item in findings if item.severity == "ERROR"]
    return {
        "status": "PASS" if not errors else "FAIL",
        "required_contract_file": required_contract_file,
        "required": expected,
        "actual": actual,
        "write_paths": write_paths,
        "protected_enforcement_paths": protected_paths,
        "findings": [asdict(item) for item in findings],
    }


def validate_full_diff_write_surface(
    repo_root: Path,
    *,
    base_sha: str,
    head_sha: str,
    write_paths: list[str],
    protected_paths: list[str] | None = None,
) -> dict[str, Any]:
    entries = _git_diff_entries(repo_root.resolve(), base_sha, head_sha)
    findings: list[ActionFinding] = []
    checked: list[dict[str, Any]] = []
    protected = set(protected_paths or [])

    for status, paths in entries:
        for path in paths:
            matching = sorted(pattern for pattern in write_paths if _pattern_covers_exact(pattern, path))
            is_protected = path in protected
            checked.append(
                {
                    "git_status": status,
                    "path": path,
                    "matching_write_paths": matching,
                    "protected_enforcement_path": is_protected,
                }
            )
            if is_protected:
                findings.append(
                    ActionFinding(
                        "ERROR",
                        "PATH_ACTION_PROTECTED_ENFORCEMENT_ROOT_CHANGED",
                        "The governed runtime PR may not modify a governance-owned enforcement root.",
                        {"git_status": status, "path": path},
                    )
                )
            if not matching:
                findings.append(
                    ActionFinding(
                        "ERROR",
                        "PATH_ACTION_DIFF_OUTSIDE_WRITE_SURFACE",
                        "Every changed path in the governed runtime PR must be authorized by the common Worker/Claim/Route write surface.",
                        {"git_status": status, "path": path, "write_paths": write_paths},
                    )
                )

    errors = [asdict(item) for item in findings if item.severity == "ERROR"]
    return {
        "status": "PASS" if not errors else "FAIL",
        "base_sha": base_sha,
        "head_sha": head_sha,
        "checked": checked,
        "findings": [asdict(item) for item in findings],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pin a required path-action contract and optionally enforce full PR write-surface coverage.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--worker-slot", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--route-file", required=True)
    parser.add_argument("--required-contract-file", required=True)
    parser.add_argument("--base-sha")
    parser.add_argument("--head-sha")
    parser.add_argument("--enforce-full-write-surface", action="store_true")
    args = parser.parse_args()

    if bool(args.base_sha) != bool(args.head_sha):
        parser.error("--base-sha and --head-sha must be supplied together")
    if args.enforce_full_write_surface and not args.head_sha:
        parser.error("--enforce-full-write-surface requires --base-sha and --head-sha")

    root = Path(args.repo_root)
    anchor = validate_required_anchor(
        root,
        worker_slot_id=args.worker_slot,
        lane_id=args.lane,
        route_file=args.route_file,
        required_contract_file=args.required_contract_file,
    )
    output: dict[str, Any] = {"required_contract": anchor}
    exit_code = 0 if anchor["status"] == "PASS" else 2

    if args.enforce_full_write_surface and args.base_sha and args.head_sha:
        surface = validate_full_diff_write_surface(
            root,
            base_sha=args.base_sha,
            head_sha=args.head_sha,
            write_paths=list(anchor.get("write_paths") or []),
            protected_paths=list(anchor.get("protected_enforcement_paths") or []),
        )
        output["full_diff_write_surface"] = surface
        if surface["status"] != "PASS":
            exit_code = 2

    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
