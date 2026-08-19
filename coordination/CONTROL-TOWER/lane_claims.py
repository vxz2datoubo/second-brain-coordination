from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path, PurePosixPath
from typing import Any

from control_tower import AGENT_FILES, PROGRAM_REGISTRY, classify_collision, load_yaml, normalize_route
from worker_slots import AGENT_TYPE as GPT_WORKER_AGENT_TYPE, load_worker_slots

CLAIMS_FILE = "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"
ACTIVE_IMPLEMENTATION = "ACTIVE_IMPLEMENTATION"
RESERVED_IMPLEMENTATION_NON_EXECUTABLE = "RESERVED_IMPLEMENTATION_NON_EXECUTABLE"
HELD_PROPOSAL_ONLY = "HELD_PROPOSAL_ONLY"
CLOSED_NO_ACTIVE_IMPLEMENTATION = "CLOSED_NO_ACTIVE_IMPLEMENTATION"
CLOSED_RESOURCE_CLASS = "NO_ACTIVE_IMPLEMENTATION"
RESERVATION_RESOURCE_CLASS = "LIGHT_TO_MEDIUM_IMPLEMENTATION_RESERVATION"
CLOSURE_EVIDENCE_KEYS = {
    "merge_commit",
    "closure_issue",
    "issue",
    "receipt_ref",
    "tested_head",
    "artifact_ref",
}


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
    if claim.get("resource_class") != CLOSED_RESOURCE_CLASS:
        findings.append(
            ClaimFinding(
                "ERROR",
                "CLOSED_CLAIM_RESOURCE_CLASS_INVALID",
                "A closed lane must explicitly release the active resource lease.",
                {"lane_id": lane_id, "resource_class": claim.get("resource_class"), "required": CLOSED_RESOURCE_CLASS},
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
    elif not (set(closure_receipt) & CLOSURE_EVIDENCE_KEYS):
        findings.append(
            ClaimFinding(
                "ERROR",
                "CLOSED_CLAIM_RECEIPT_EVIDENCE_MISSING",
                "A closed lane closure receipt must contain at least one durable evidence reference.",
                {"lane_id": lane_id, "accepted_evidence_keys": sorted(CLOSURE_EVIDENCE_KEYS)},
            )
        )
    return findings


def _validate_bound_implementation_claim(
    lane_id: str,
    claim: dict[str, Any],
    routes: dict[str, Any],
    *,
    reserved: bool,
    worker_slots_by_id: dict[str, Any] | None = None,
) -> list[ClaimFinding]:
    findings: list[ClaimFinding] = []
    prefix = "RESERVED_CLAIM" if reserved else "ACTIVE_CLAIM"
    label = "Reserved implementation" if reserved else "Active implementation"

    agent = claim.get("execution_agent")
    worker_slots_by_id = worker_slots_by_id or {}

    binding = claim.get("route_binding")
    route: Any = None
    worker_slot_id: str | None = None

    if agent == GPT_WORKER_AGENT_TYPE:
        worker_slot_id = claim.get("worker_slot_id") or (
            binding.get("worker_slot_id") if isinstance(binding, dict) else None
        )
        if not worker_slot_id:
            findings.append(
                ClaimFinding(
                    "ERROR",
                    f"{prefix}_WORKER_SLOT_MISSING",
                    f"{label} bound to GPT_ENGINEERING_WORKER must bind an exact worker slot/lease identity.",
                    {"lane_id": lane_id},
                )
            )
            return findings
        slot = worker_slots_by_id.get(str(worker_slot_id))
        if slot is None:
            findings.append(
                ClaimFinding(
                    "ERROR",
                    f"{prefix}_WORKER_SLOT_UNKNOWN",
                    "Work claim references a GPT worker slot/lease that is not present in the canonical registry.",
                    {"lane_id": lane_id, "worker_slot_id": worker_slot_id},
                )
            )
            return findings
        route = slot
        if isinstance(binding, dict) and binding.get("worker_slot_id") not in (None, worker_slot_id):
            findings.append(
                ClaimFinding(
                    "ERROR",
                    f"{prefix}_WORKER_SLOT_BINDING_MISMATCH",
                    "Work claim route_binding worker_slot_id disagrees with the claimed worker slot identity.",
                    {
                        "lane_id": lane_id,
                        "claimed": worker_slot_id,
                        "binding": binding.get("worker_slot_id"),
                    },
                )
            )
    elif agent in routes:
        route = routes[str(agent)]
    else:
        findings.append(
            ClaimFinding(
                "ERROR",
                f"{prefix}_AGENT_INVALID",
                f"{label} has no valid execution agent.",
                {"lane_id": lane_id, "agent": agent},
            )
        )
        return findings

    if not isinstance(binding, dict):
        findings.append(
            ClaimFinding(
                "ERROR",
                f"{prefix}_ROUTE_BINDING_MISSING",
                f"{label} lacks route binding.",
                {"lane_id": lane_id},
            )
        )
        return findings

    drift = _binding_drift(binding, route)
    if drift:
        findings.append(
            ClaimFinding(
                "ERROR",
                f"{prefix}_ROUTE_STALE",
                "Lane work claim is stale relative to the current per-agent ACTIVE route.",
                {"lane_id": lane_id, "agent": agent, "drift": drift},
            )
        )

    if not claim.get("write_paths"):
        findings.append(
            ClaimFinding(
                "ERROR",
                f"{prefix}_WRITE_SURFACE_MISSING",
                f"{label} must declare write paths so collision governance remains mechanical.",
                {"lane_id": lane_id},
            )
        )

    if reserved:
        if route.execution_allowed:
            findings.append(
                ClaimFinding(
                    "ERROR",
                    "RESERVED_CLAIM_ROUTE_EXECUTABLE",
                    "A reservation must be bound to a non-executable route until a later activation gate.",
                    {"lane_id": lane_id, "agent": agent},
                )
            )
        if claim.get("resource_class") != RESERVATION_RESOURCE_CLASS:
            findings.append(
                ClaimFinding(
                    "ERROR",
                    "RESERVED_CLAIM_RESOURCE_CLASS_INVALID",
                    "A non-executable implementation reservation must use the reservation resource class.",
                    {
                        "lane_id": lane_id,
                        "resource_class": claim.get("resource_class"),
                        "required": RESERVATION_RESOURCE_CLASS,
                    },
                )
            )
        scope = claim.get("implementation_scope") or {}
        if not isinstance(scope, dict) or not scope.get("global_reconciliation_receipt"):
            findings.append(
                ClaimFinding(
                    "ERROR",
                    "RESERVED_CLAIM_RECONCILIATION_RECEIPT_MISSING",
                    "A two-phase implementation reservation must reference its GlobalReconciliationReceipt.",
                    {"lane_id": lane_id},
                )
            )
    else:
        if not route.execution_allowed:
            findings.append(
                ClaimFinding(
                    "ERROR",
                    "ACTIVE_CLAIM_ROUTE_NOT_EXECUTABLE",
                    "Active implementation is bound to a non-executable route.",
                    {"lane_id": lane_id, "agent": agent},
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
    worker_slots = load_worker_slots(repo_root)
    worker_slots_by_id = {slot.worker_slot_id: slot for slot in worker_slots if slot.worker_slot_id}
    proposal_roots = claims_doc.get("proposal_roots", {}) or {}

    for lane_id, claim in claims.items():
        state = str(claim.get("claim_state", ""))
        if state == ACTIVE_IMPLEMENTATION:
            findings.extend(
                _validate_bound_implementation_claim(
                    lane_id, claim, routes, reserved=False, worker_slots_by_id=worker_slots_by_id
                )
            )
        elif state == RESERVED_IMPLEMENTATION_NON_EXECUTABLE:
            findings.extend(
                _validate_bound_implementation_claim(
                    lane_id, claim, routes, reserved=True, worker_slots_by_id=worker_slots_by_id
                )
            )
        elif state == HELD_PROPOSAL_ONLY:
            if claim.get("execution_agent") is not None or claim.get("route_binding") not in (None, {}, ""):
                findings.append(
                    ClaimFinding(
                        "ERROR",
                        "PROPOSAL_ONLY_HAS_EXECUTION_BINDING",
                        "Proposal-only claim may not reserve an execution agent or route.",
                        {"lane_id": lane_id},
                    )
                )
            safe = claim.get("safe_start_after_foundation", {}) or {}
            if safe.get("runtime_write_allowed") is not False or safe.get("implementation_route_allowed") is not False:
                findings.append(
                    ClaimFinding(
                        "ERROR",
                        "PROPOSAL_ONLY_RUNTIME_NOT_LOCKED",
                        "Proposal-only claim must explicitly lock runtime and implementation execution.",
                        {"lane_id": lane_id},
                    )
                )
            if claim.get("authority_claims") or claim.get("write_domains"):
                findings.append(
                    ClaimFinding(
                        "ERROR",
                        "PROPOSAL_ONLY_AUTHORITY_CLAIM",
                        "Proposal-only work cannot claim domain write authority.",
                        {"lane_id": lane_id},
                    )
                )
            root = proposal_roots.get(lane_id)
            if not root:
                findings.append(
                    ClaimFinding(
                        "ERROR",
                        "PROPOSAL_ROOT_MISSING",
                        "Proposal-only lane lacks an isolated proposal root.",
                        {"lane_id": lane_id},
                    )
                )
            else:
                outside = [path for path in claim.get("write_paths", []) or [] if not _under(str(path), str(root))]
                if outside:
                    findings.append(
                        ClaimFinding(
                            "ERROR",
                            "PROPOSAL_WRITE_OUTSIDE_ROOT",
                            "Proposal-only lane writes outside its isolated proposal root.",
                            {"lane_id": lane_id, "paths": outside, "root": root},
                        )
                    )
        elif state == CLOSED_NO_ACTIVE_IMPLEMENTATION:
            findings.extend(_validate_closed_claim(lane_id, claim))
        else:
            findings.append(
                ClaimFinding(
                    "ERROR",
                    "UNKNOWN_CLAIM_STATE",
                    "Lane work claim uses an unsupported state.",
                    {"lane_id": lane_id, "state": state},
                )
            )

    implementation_occupancy_states = {ACTIVE_IMPLEMENTATION, RESERVED_IMPLEMENTATION_NON_EXECUTABLE}
    pairwise: list[dict[str, Any]] = []
    for left_id, right_id in combinations(sorted(claims), 2):
        result = classify_collision(claims[left_id], claims[right_id])
        pairwise.append({"pair": [left_id, right_id], **result})
        left_occupies = claims[left_id].get("claim_state") in implementation_occupancy_states
        right_occupies = claims[right_id].get("claim_state") in implementation_occupancy_states
        if left_occupies and right_occupies and result["level"] in {"O3", "O4"}:
            findings.append(
                ClaimFinding(
                    "ERROR",
                    "CONCURRENT_IMPLEMENTATION_COLLISION",
                    "Two active/reserved implementations collide on a mutable surface or authority.",
                    {"pair": [left_id, right_id], "collision": result},
                )
            )

    proposal_pairwise = [
        item
        for item in pairwise
        if claims[item["pair"][0]].get("claim_state") == HELD_PROPOSAL_ONLY
        or claims[item["pair"][1]].get("claim_state") == HELD_PROPOSAL_ONLY
    ]
    proposal_blockers = [item for item in proposal_pairwise if item["level"] in {"O3", "O4"}]

    errors = [asdict(item) for item in findings if item.severity == "ERROR"]
    warnings = [asdict(item) for item in findings if item.severity == "WARN"]
    return {
        "schema_version": "1.3",
        "claims_id": claims_doc.get("claims_id"),
        "errors": errors,
        "warnings": warnings,
        "pairwise": pairwise,
        "proposal_only_collision_blockers": proposal_blockers,
        "claim_structural_check": "PASS" if not errors else "FAIL",
        "proposal_only_candidate": "ELIGIBLE_FOR_GPT_RELEASE_DECISION" if not errors and not proposal_blockers else "NOT_READY",
    }
