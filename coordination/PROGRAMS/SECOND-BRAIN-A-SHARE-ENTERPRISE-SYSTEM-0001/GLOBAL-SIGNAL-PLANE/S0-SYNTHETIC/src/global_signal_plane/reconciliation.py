"""Synthetic reconciliation receipt builder/verifier; it never grants execution authority."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _fingerprint(binding: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(binding).encode("utf-8")).hexdigest()


BOUND_FIELDS = ("ledger_watermark", "projection_version", "main_sha", "pr_head", "pr_state", "active_routes", "work_claim", "program_lane", "domain_snapshots", "user_approval_state")


def build_receipt(snapshot: Mapping[str, Any], *, receipt_id: str = "synthetic-receipt") -> dict[str, Any]:
    """Build a public-safe binding witness from synthetic snapshot refs only."""
    binding = {field: snapshot.get(field) for field in BOUND_FIELDS}
    return {
        "schema_version": "GlobalReconciliationReceipt/v1",
        "receipt_id": receipt_id,
        "result": "PASS",
        "execution_authorized": False,
        "binding": binding,
        "receipt_fingerprint": _fingerprint(binding),
        "raw_private_content_present": False,
    }


def verify_receipt(receipt: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    """Compare-and-check material state. A PASS is freshness evidence, never a work authorization."""
    binding = receipt.get("binding", {})
    codes: list[str] = []
    if receipt.get("receipt_fingerprint") != _fingerprint(binding):
        return {"valid": False, "result": "BLOCKED", "codes": ["INVALID_RECEIPT"], "execution_authorized": False}
    if current.get("user_approval_state") in {"CANCEL", "REVOKE"}:
        return {"valid": False, "result": "BLOCKED", "codes": ["USER_REVOKE_INVALIDATES_PASS"], "execution_authorized": False}
    if binding.get("pr_head") != current.get("pr_head"):
        codes.append("STALE_REVIEW_HEAD")
    if binding.get("pr_state") != current.get("pr_state"):
        codes.append("STALE_PR_STATE")
    for field, code in (("main_sha", "STALE_MAIN_SNAPSHOT"), ("active_routes", "ROUTE_WORKCLAIM_DRIFT"), ("work_claim", "ROUTE_WORKCLAIM_DRIFT"), ("program_lane", "ROUTE_PROGRAM_LANE_DRIFT"), ("ledger_watermark", "STALE_LEDGER_WATERMARK"), ("projection_version", "STALE_PROJECTION"), ("domain_snapshots", "DOMAIN_SNAPSHOT_STALE")):
        if binding.get(field) != current.get(field):
            codes.append(code)
    if current.get("route_state") == "DONE" and current.get("program_lane") == "ACTIVE":
        codes.extend(["CROSS_WINDOW_STATE_DRIFT", "ROUTE_WORKCLAIM_DRIFT", "ROUTE_PROGRAM_LANE_DRIFT"])
    if current.get("same_agent_double_booked"):
        codes.append("SAME_AGENT_DOUBLE_BOOKED")
    if codes:
        unique = sorted(set(codes))
        result = "NEEDS_REFRESH" if set(unique).issubset({"STALE_PR_STATE", "STALE_MAIN_SNAPSHOT", "STALE_LEDGER_WATERMARK", "STALE_PROJECTION", "DOMAIN_SNAPSHOT_STALE"}) else "BLOCKED"
        return {"valid": False, "result": result, "codes": unique, "execution_authorized": False}
    return {"valid": True, "result": "PASS", "codes": [], "execution_authorized": False}
