from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path, PurePosixPath
from typing import Any

from control_tower import AGENT_FILES, PROGRAM_REGISTRY, classify_collision, load_yaml, normalize_route

CLAIMS_FILE = "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"
CLOSED_NO_ACTIVE_IMPLEMENTATION = "CLOSED_NO_ACTIVE_IMPLEMENTATION"


@dataclass(frozen=True)
class ClaimFinding:
    severity: str
    code: str
    message: str
    evidence: dict[str, Any]


def _norm_path(value: str) -> str:
    value = value.replace("\\", "/").strip()
    while value.startswith("./"):
        value = value[2:]
    return str(PurePosixPath(value))


def _under(path: str, root: str) -> bool:
    path_norm = _norm_path(path)
    root_norm = _norm_path(root).rstrip("/")
    return path_norm == root_norm or path_norm.startswith(root_norm + "/")


def _claims_by_lane(claims_doc: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[ClaimFinding]]:
    result: dict[str, dict[str, Any]] = {}
    findings: list[ClaimFinding] = []
    for raw in claims_doc.get("claims", []) or []:
        if not isinstance(raw, dict) or not raw.get("lane_id"):
            findings.append(ClaimFinding("ERROR", "INVALID_CLAIM", "Claim lacks lane_id mapping.", {}))
            continue
        lane_id = str(raw["lane_id"])
        if lane_id in result:
            findings.append(
                ClaimFinding("ERROR", "DUPLICATE_LANE_CLAIM", "A lane has more than one current claim.", {"lane_id": lane_id})
            )
        result[lane_id] = raw
    return result, findings


def _binding_actual(route: Any) -> dict[str, Any]:
    return {
        "task_id": route.task_id,
        "route_epoch": route.route_epoch,
        "issue": route.issue,
        "pr": route.pr,
        "branch": route.branch,
    }


def _binding_drift(binding: dict[str, Any], route: Any) -> dict[str, Any]:
    actual = _binding_actual(route)
    keys = ("task_id", "route_epoch", "issue", "pr", "branch")
    return {
        key: {"claimed": binding.get(key), "actual": actual.get(key)}
        for key in keys
        if binding.get(key) != actual.get(key)
    }


def _validate_closed_claim(lane_id: str, claim: dict[str, Any]) -> list[ClaimFinding]:
    findings: list[ClaimFinding] = []
    if claim.get("execution_agent") is not None:
        findings.append(
            ClaimFinding(
                "ERROR",
                "CLOSED_CLAIM_HAS_EXECUTION_AGENT",
                "A closed lane may not reserve an execution agent.",
                {"lane_id": lane_id, "execution_agent": claim.get("execution_agent")},
            )
        )
    if claim.get("route_binding") not in (None, {}, ""):
        findings.append(
            ClaimFinding(
                "ERROR",
                "CLOSED_CLAIM_HAS_ROUTE_BINDING",
                "A closed lane may not retain an executable route binding.",
                {"lane_id": lane_id},
            )
        )
    active_surface_fields = {
        "write_paths": list(claim.get("write_paths", []) or []),
        "read_paths": list(claim.get("read_paths", []) or []),
        "interfaces": list(claim.get("interfaces", []) or []),
        "read_domains": list(claim.get("read_domains", []) or []),
        "write_domains": list(claim.get("write_domains", []) or []),
        "authority_claims": list(claim.get("authority_claims", []) or []),
    }
    nonempty = {key: value for key, value in active_surface_fields.items() if value}
    if nonempty:
        findings.append(
            ClaimFinding(
                "ERROR",
                "CLOSED_CLAIM_HAS_ACTIVE_SURFACE",
                "A closed lane must release all current read/write/interface/authority work surfaces.",
                {"lane_id": lane_id, "nonempty": nonempty},
            )
        )
    closure_receipt = claim.get("closure_receipt")
    if not isinstance(closure_receipt, dict) or not closure_receipt:
        findings.append(
            ClaimFinding(
                "ERROR",
                "CLOSED_CLAIM_RECEIPT_MISSING",
                "A closed lane must retain a durable closure receipt instead of an active lease.",
                {"lane_id": lane_id},
            )
        )
    return findings


def validate_claims(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    registry = load_yaml(repo_root / PROGRAM_REGISTRY)
    claims_doc = load_yaml(repo_root / CLAIMS_FILE)
    claims, findings = _claims_by_lane(claims_doc)

    registry_lanes = {
        str(item["lane_id"]): item
        for item in registry.get("program_lanes", []) or []
        if isinstance(item, dict) and item.get("lane_id")
    }
    if set(claims) != set(registry_lanes):
        findings.append(
            ClaimFinding(
                "ERROR",
                "CLAIM_REGISTRY_COVERAGE_MISMATCH",
                "Every registered Program Lane must have exactly one current work claim.",
                {
                    "missing_claims": sorted(set(registry_lanes) - set(claims)),
                    "unknown_claims": sorted(set(claims) - set(registry_lanes)),
                },
            )
        )

    routes = {
        agent: normalize_route(agent, load_yaml(repo_root / relpath))
        for agent, relpath in AGENT_FILES.items()
    }
    proposal_roots = claims_doc.get("proposal_roots", {}) or {}

    for lane_id, claim in claims.items():
        state = str(claim.get("claim_state", ""))
        if state == "ACTIVE_IMPLEMENTATION":
            agent = claim.get("execution_agent")
            if agent not in routes:
                findings.append(
                    ClaimFinding("ERROR", "ACTIVE_CLAIM_AGENT_INVALID", "Active implementation has no valid execution agent.", {"lane_id": lane_id, "agent": agent})
                )
                continue
            binding = claim.get("route_binding")
            if not isinstance(binding, dict):
                findings.append(
                    ClaimFinding("ERROR", "ACTIVE_CLAIM_ROUTE_BINDING_MISSING", "Active implementation lacks route binding.", {"lane_id": lane_id})
                )
                continue
            drift = _binding_drift(binding, routes[str(agent)])
            if drift:
                findings.append(
                    ClaimFinding(
                        "ERROR",
                        "ACTIVE_CLAIM_ROUTE_STALE",
                        "Lane work claim is stale relative to the current per-agent ACTIVE route.",
                        {"lane_id": lane_id, "agent": agent, "drift": drift},
                    )
                )
            if not claim.get("write_paths"):
                findings.append(
                    ClaimFinding("ERROR", "ACTIVE_CLAIM_WRITE_SURFACE_MISSING", "Active implementation must declare write paths.", {"lane_id": lane_id})
                )
            if not routes[str(agent)].execution_allowed:
                findings.append(
                    ClaimFinding("ERROR", "ACTIVE_CLAIM_ROUTE_NOT_EXECUTABLE", "Active implementation is bound to a non-executable route.", {"lane_id": lane_id, "agent": agent})
                )
        elif state == "HELD_PROPOSAL_ONLY":
            if claim.get("execution_agent") is not None or claim.get("route_binding") not in (None, {}, ""):
                findings.append(
                    ClaimFinding("ERROR", "PROPOSAL_ONLY_HAS_EXECUTION_BINDING", "Proposal-only claim may not reserve an execution agent or route.", {"lane_id": lane_id})
                )
            safe = claim.get("safe_start_after_foundation", {}) or {}
            if safe.get("runtime_write_allowed") is not False or safe.get("implementation_route_allowed") is not False:
                findings.append(
                    ClaimFinding("ERROR", "PROPOSAL_ONLY_RUNTIME_NOT_LOCKED", "Proposal-only claim must explicitly lock runtime and implementation execution.", {"lane_id": lane_id})
                )
            if claim.get("authority_claims") or claim.get("write_domains"):
                findings.append(
                    ClaimFinding("ERROR", "PROPOSAL_ONLY_AUTHORITY_CLAIM", "Proposal-only work cannot claim domain write authority.", {"lane_id": lane_id})
                )
            root = proposal_roots.get(lane_id)
            if not root:
                findings.append(
                    ClaimFinding("ERROR", "PROPOSAL_ROOT_MISSING", "Proposal-only lane lacks an isolated proposal root.", {"lane_id": lane_id})
                )
            else:
                outside = [path for path in claim.get("write_paths", []) or [] if not _under(str(path), str(root))]
                if outside:
                    findings.append(
                        ClaimFinding("ERROR", "PROPOSAL_WRITE_OUTSIDE_ROOT", "Proposal-only lane writes outside its isolated proposal root.", {"lane_id": lane_id, "paths": outside, "root": root})
                    )
        elif state == CLOSED_NO_ACTIVE_IMPLEMENTATION:
            findings.extend(_validate_closed_claim(lane_id, claim))
        else:
            findings.append(
                ClaimFinding("ERROR", "UNKNOWN_CLAIM_STATE", "Lane work claim uses an unsupported state.", {"lane_id": lane_id, "state": state})
            )

    pairwise: list[dict[str, Any]] = []
    for left_id, right_id in combinations(sorted(claims), 2):
        result = classify_collision(claims[left_id], claims[right_id])
        pairwise.append({"pair": [left_id, right_id], **result})
        left_active = claims[left_id].get("claim_state") == "ACTIVE_IMPLEMENTATION"
        right_active = claims[right_id].get("claim_state") == "ACTIVE_IMPLEMENTATION"
        if left_active and right_active and result["level"] in {"O3", "O4"}:
            findings.append(
                ClaimFinding(
                    "ERROR",
                    "CONCURRENT_IMPLEMENTATION_COLLISION",
                    "Two active implementations collide on a mutable surface or authority.",
                    {"pair": [left_id, right_id], "collision": result},
                )
            )

    proposal_pairwise = [
        item
        for item in pairwise
        if claims[item["pair"][0]].get("claim_state") == "HELD_PROPOSAL_ONLY"
        or claims[item["pair"][1]].get("claim_state") == "HELD_PROPOSAL_ONLY"
    ]
    proposal_blockers = [item for item in proposal_pairwise if item["level"] in {"O3", "O4"}]

    errors = [asdict(item) for item in findings if item.severity == "ERROR"]
    warnings = [asdict(item) for item in findings if item.severity == "WARN"]
    return {
        "schema_version": "1.1",
        "claims_id": claims_doc.get("claims_id"),
        "errors": errors,
        "warnings": warnings,
        "pairwise": pairwise,
        "proposal_only_collision_blockers": proposal_blockers,
        "claim_structural_check": "PASS" if not errors else "FAIL",
        "proposal_only_candidate": "ELIGIBLE_FOR_GPT_RELEASE_DECISION" if not errors and not proposal_blockers else "NOT_READY",
    }
