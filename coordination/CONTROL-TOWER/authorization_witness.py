from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from control_tower import AGENT_FILES, PROGRAM_REGISTRY, load_yaml, normalize_route, route_witness
from lane_claims import CLAIMS_FILE, validate_claims
from worker_slots import (
    AGENT_TYPE as GPT_WORKER_AGENT_TYPE,
    load_worker_slots,
    validate_worker_slots,
    worker_registry_witness,
    worker_slot_route_witness,
)

RELEASE_GATE = "coordination/CONTROL-TOWER/RELEASE-GATE.yaml"


def _hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _find_lane(items: list[Any], lane_id: str) -> dict[str, Any]:
    matches = [item for item in items if isinstance(item, dict) and str(item.get("lane_id")) == lane_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one lane {lane_id}, found {len(matches)}")
    return matches[0]


def _assert_worker_authority_valid(root: Path) -> dict[str, Any]:
    report = validate_worker_slots(root)
    if report.get("worker_slot_structural_check") != "PASS":
        codes = [item.get("code") for item in report.get("errors", []) if isinstance(item, dict)]
        raise ValueError(f"INVALID_GPT_WORKER_AUTHORITY:{','.join(str(code) for code in codes)}")
    return report


def authorization_witness(repo_root: Path, lane_id: str) -> dict[str, Any]:
    root = repo_root.resolve()
    registry = load_yaml(root / PROGRAM_REGISTRY)
    claims_doc = load_yaml(root / CLAIMS_FILE)
    gate = load_yaml(root / RELEASE_GATE)
    lane = _find_lane(list(registry.get("program_lanes", []) or []), lane_id)
    claim = _find_lane(list(claims_doc.get("claims", []) or []), lane_id)
    agent = claim.get("execution_agent")

    # R3: invalid/missing/malformed canonical worker authority cannot mint a green authorization witness.
    worker_report = _assert_worker_authority_valid(root)

    all_routes = {
        name: route_witness(normalize_route(name, load_yaml(root / relpath)))
        for name, relpath in AGENT_FILES.items()
    }
    worker_slots = load_worker_slots(root)
    worker_slots_by_id = {slot.worker_slot_id: slot for slot in worker_slots if slot.worker_slot_id}
    worker_slots_witness = [worker_slot_route_witness(slot) for slot in worker_slots]
    worker_registry = worker_registry_witness(root)

    route = None
    if agent == GPT_WORKER_AGENT_TYPE:
        worker_slot_id = claim.get("worker_slot_id") or (
            claim.get("route_binding") or {}
        ).get("worker_slot_id")
        slot = worker_slots_by_id.get(str(worker_slot_id)) if worker_slot_id else None
        if slot is not None:
            route = worker_slot_route_witness(slot)
    else:
        route = all_routes.get(str(agent)) if agent is not None else None
        if agent is not None and str(agent) not in all_routes:
            raise ValueError(f"unknown execution agent {agent}")

    relevant_overlaps = [
        item
        for item in registry.get("cross_lane_overlap_matrix", []) or []
        if isinstance(item, dict) and lane_id in [str(value) for value in item.get("pair", []) or []]
    ]
    all_claims = list(claims_doc.get("claims", []) or [])
    all_lanes = list(registry.get("program_lanes", []) or [])
    release_gate_material = {
        "foundation_state": gate.get("foundation_state"),
        "lane_release_state": gate.get("lane_release_state"),
        "automatic_lane_release": gate.get("automatic_lane_release"),
        "passing_ci_does_not_release_lanes": gate.get("passing_ci_does_not_release_lanes"),
    }
    material = {
        "lane": lane,
        "claim": claim,
        "all_claims": all_claims,
        "all_lanes": all_lanes,
        "all_routes": all_routes,
        # R3: this now includes strict raw registry worker_slots and bounded maintenance/adoption authority material.
        "worker_registry": worker_registry,
        "worker_slots": worker_slots_witness,
        "worker_authority_structural_check": worker_report.get("worker_slot_structural_check"),
        "maintenance_adoption_structural_check": worker_report.get("maintenance_adoption_structural_check"),
        "release_policy": registry.get("current_user_release_policy", {}),
        "capacity_policy": registry.get("portfolio_capacity_policy", {}),
        "relevant_overlaps": relevant_overlaps,
        "all_overlaps": list(registry.get("cross_lane_overlap_matrix", []) or []),
        "release_gate": release_gate_material,
    }
    claim_report = validate_claims(root)
    key_fields = {
        "lane_id": lane_id,
        "claim_state": claim.get("claim_state"),
        "execution_agent": agent,
        "task_id": route.get("task_id") if route else None,
        "route_epoch": route.get("route_epoch") if route else None,
        "claim_structural_check": claim_report.get("claim_structural_check"),
        "proposal_only_candidate": claim_report.get("proposal_only_candidate"),
        "foundation_state": gate.get("foundation_state"),
        "lane_release_state": gate.get("lane_release_state"),
    }
    return {
        "schema_version": "1.3",
        **key_fields,
        "route_fingerprint": route.get("fingerprint") if route else None,
        "all_routes_fingerprint": _hash(all_routes),
        "worker_registry_fingerprint": _hash(worker_registry),
        "worker_slots_fingerprint": _hash(worker_slots_witness),
        "worker_authority_structural_check": worker_report.get("worker_slot_structural_check"),
        "maintenance_adoption_structural_check": worker_report.get("maintenance_adoption_structural_check"),
        "claim_fingerprint": _hash(claim),
        "all_claims_fingerprint": _hash(all_claims),
        "policy_fingerprint": _hash(
            {
                "worker_registry": material["worker_registry"],
                "worker_authority_structural_check": material["worker_authority_structural_check"],
                "maintenance_adoption_structural_check": material["maintenance_adoption_structural_check"],
                "release_policy": material["release_policy"],
                "capacity_policy": material["capacity_policy"],
                "all_overlaps": material["all_overlaps"],
                "release_gate": material["release_gate"],
            }
        ),
        "authorization_fingerprint": _hash(material),
    }


def verify_authorization_witness(repo_root: Path, witness: dict[str, Any]) -> dict[str, Any]:
    lane_id = witness.get("lane_id")
    if not isinstance(lane_id, str) or not lane_id:
        return {"fresh": False, "reason": "INVALID_WITNESS_LANE_ID", "current": None}
    try:
        current = authorization_witness(repo_root, lane_id)
    except (OSError, ValueError, TypeError) as exc:
        return {
            "fresh": False,
            "reason": "AUTHORIZATION_MATERIAL_INVALID",
            "lane_id": lane_id,
            "expected_fingerprint": witness.get("authorization_fingerprint"),
            "current_fingerprint": None,
            "current": None,
            "error": str(exc),
        }
    fresh = witness.get("authorization_fingerprint") == current.get("authorization_fingerprint")
    return {
        "fresh": fresh,
        "reason": "MATCH" if fresh else "AUTHORIZATION_MATERIAL_CHANGED",
        "lane_id": lane_id,
        "expected_fingerprint": witness.get("authorization_fingerprint"),
        "current_fingerprint": current.get("authorization_fingerprint"),
        "current": current,
    }
