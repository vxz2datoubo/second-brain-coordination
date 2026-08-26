from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from control_tower import load_yaml
from lane_claims import (
    ACTIVE_IMPLEMENTATION,
    RESERVED_IMPLEMENTATION_NON_EXECUTABLE,
    CLAIMS_FILE,
)
from trusted_task_release import (
    GPT_WORKERS_REGISTRY,
    TRUSTED_RECEIPT_SCHEMA,
    TrustedReleaseError,
    evaluate_trusted_release_proposal,
)


OPPORTUNITY_SCHEMA = "DigestedSignalOpportunity/v1"
PRIORITY_OBSERVATION_SCHEMA = "StartupPriorityObservation/v1"
DECISION_SCHEMA = "IdleSignalStartupDecision/v1"
AUTHORIZATION_SCHEMA = "IdleSignalAutoReleaseAuthorization/v1"

P0 = "P0_USER_OR_HIGH_RISK"
P1 = "P1_EXACT_HEAD_REVIEW"
P2 = "P2_BLOCKER_OR_DRIFT"
P3 = "P3_BOUNDED_IMPROVEMENT"
P4 = "P4_RESEARCH"
PRIORITY_ORDER = {P0: 0, P1: 1, P2: 2, P3: 3, P4: 4}
BLOCKING_PRIORITIES = frozenset({P0, P1, P2})
IDLE_PRIORITIES = frozenset({P3, P4})

RELEASEABLE_R150_DISPOSITIONS = frozenset(
    {"RELEASE_BOUNDED_TASK", "RELEASE_AS_EXTENSION", "RELEASE_AS_ADAPTER_OR_PLUGIN"}
)
INELIGIBLE_DISPOSITIONS = frozenset(
    {
        "ALREADY_CANONICAL",
        "ALREADY_SATISFIED",
        "SUPERSEDED",
        "REJECTED",
        "CLOSED_NO_ACTION",
        "DONE",
        "CANCELLED",
    }
)
INELIGIBLE_EPISTEMIC_STATES = frozenset({"UNKNOWN", "NEEDS_REVALIDATION"})

STANDING_AUTO_RELEASE_EXCLUSIONS = frozenset(
    {
        "trading",
        "trade",
        "order",
        "fund",
        "funds",
        "secret",
        "credential",
        "permission",
        "visibility",
        "production",
        "deploy",
        "deployment",
        "destructive",
        "force_push",
        "force-push",
        "reset",
        "private_key",
        "token",
    }
)

ACTIVE_PROGRAM_LANES = "coordination/ACTIVE-PROGRAM-LANES.yaml"
STANDING_POLICY_REF = "issue://461#user-direction-2026-08-26"
IAGL_PRIORITY_REF = (
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
    "IAGL-STAGE-A/src/_iagl_primitives.py#Priority"
)
R149_REF = "coordination/CONTROL-TOWER/task_release_impact.py"
R150_REF = "coordination/CONTROL-TOWER/trusted_task_release.py"


class IdleSignalSchedulerError(ValueError):
    """Stable fail-closed R151 error."""

    def __init__(self, code: str, path: str = "/") -> None:
        super().__init__(code)
        self.code = code
        self.path = path


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _copy(value: Any) -> Any:
    return json.loads(_canonical(value))


def _nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IdleSignalSchedulerError("INVALID_STRING", path)
    return value


def _list_of_strings(value: Any, path: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise IdleSignalSchedulerError("INVALID_STRING_LIST", path)
    for index, item in enumerate(value):
        _nonempty_string(item, f"{path}/{index}")
    return list(value)


def _bounded_int(value: Any, path: str, *, low: int = 0, high: int = 100) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < low or value > high:
        raise IdleSignalSchedulerError("INVALID_BOUNDED_INTEGER", path)
    return value


def _risk_tokens(value: Any) -> set[str]:
    tokens: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            tokens.update(_risk_tokens(str(key)))
            tokens.update(_risk_tokens(item))
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            tokens.update(_risk_tokens(item))
    elif isinstance(value, str):
        normalized = value.casefold()
        for separator in ("/", ":", "=", ",", ";", "|", "-", "_"):
            normalized = normalized.replace(separator, " ")
        tokens.update(part for part in normalized.split() if part)
    return tokens


def _exclusion_hits(value: Any) -> tuple[str, ...]:
    return tuple(sorted(STANDING_AUTO_RELEASE_EXCLUSIONS & _risk_tokens(value)))


def validate_priority_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise IdleSignalSchedulerError("PRIORITY_OBSERVATION_NOT_OBJECT")
    required = {
        "schema_version",
        "observation_id",
        "scan_complete",
        "evidence_refs",
        "items",
    }
    if set(value) != required:
        raise IdleSignalSchedulerError("PRIORITY_OBSERVATION_FIELDS_INVALID")
    if value.get("schema_version") != PRIORITY_OBSERVATION_SCHEMA:
        raise IdleSignalSchedulerError("PRIORITY_OBSERVATION_SCHEMA_INVALID")
    _nonempty_string(value.get("observation_id"), "/observation_id")
    if value.get("scan_complete") is not True:
        raise IdleSignalSchedulerError("STARTUP_PRIORITY_SCAN_INCOMPLETE", "/scan_complete")
    _list_of_strings(value.get("evidence_refs"), "/evidence_refs", nonempty=True)
    if not isinstance(value.get("items"), list):
        raise IdleSignalSchedulerError("PRIORITY_ITEMS_INVALID", "/items")
    normalized = _copy(value)
    for index, item in enumerate(normalized["items"]):
        path = f"/items/{index}"
        if not isinstance(item, Mapping):
            raise IdleSignalSchedulerError("PRIORITY_ITEM_NOT_OBJECT", path)
        if set(item) != {"priority", "work_ref", "reason", "evidence_refs"}:
            raise IdleSignalSchedulerError("PRIORITY_ITEM_FIELDS_INVALID", path)
        priority = _nonempty_string(item.get("priority"), f"{path}/priority")
        if priority not in PRIORITY_ORDER:
            raise IdleSignalSchedulerError("PRIORITY_CLASS_INVALID", f"{path}/priority")
        _nonempty_string(item.get("work_ref"), f"{path}/work_ref")
        _nonempty_string(item.get("reason"), f"{path}/reason")
        _list_of_strings(item.get("evidence_refs"), f"{path}/evidence_refs", nonempty=True)
    normalized["observation_digest"] = _digest(normalized)
    return normalized


def validate_opportunity(value: Mapping[str, Any], *, index: int = 0) -> dict[str, Any]:
    path = f"/opportunities/{index}"
    if not isinstance(value, Mapping):
        raise IdleSignalSchedulerError("OPPORTUNITY_NOT_OBJECT", path)
    required = {
        "schema_version",
        "opportunity_id",
        "signal_ref",
        "signal_primary_domain",
        "source_evidence_refs",
        "desired_effect",
        "problem_to_solve",
        "success_condition",
        "current_disposition",
        "epistemic_state",
        "desired_effect_gap_proven",
        "dependency_ready",
        "priority_class",
        "user_value_score",
        "materiality_score",
        "dependency_readiness_score",
        "age_cycles",
        "estimated_cost_score",
        "task_release_proposal",
    }
    missing = sorted(required - set(value))
    if missing:
        raise IdleSignalSchedulerError("OPPORTUNITY_FIELD_MISSING", f"{path}/{missing[0]}")
    extra = sorted(set(value) - required)
    if extra:
        raise IdleSignalSchedulerError("OPPORTUNITY_FIELD_UNRECOGNIZED", f"{path}/{extra[0]}")
    if value.get("schema_version") != OPPORTUNITY_SCHEMA:
        raise IdleSignalSchedulerError("OPPORTUNITY_SCHEMA_INVALID", f"{path}/schema_version")
    out = _copy(value)
    for name in (
        "opportunity_id",
        "signal_ref",
        "signal_primary_domain",
        "desired_effect",
        "problem_to_solve",
        "success_condition",
        "current_disposition",
        "epistemic_state",
        "priority_class",
    ):
        _nonempty_string(out[name], f"{path}/{name}")
    _list_of_strings(out["source_evidence_refs"], f"{path}/source_evidence_refs", nonempty=True)
    if out["current_disposition"] in INELIGIBLE_DISPOSITIONS:
        raise IdleSignalSchedulerError("OPPORTUNITY_ALREADY_CLOSED_OR_SATISFIED", f"{path}/current_disposition")
    if out["epistemic_state"] in INELIGIBLE_EPISTEMIC_STATES:
        raise IdleSignalSchedulerError("OPPORTUNITY_EPISTEMIC_STATE_BLOCKS_RELEASE", f"{path}/epistemic_state")
    if out["desired_effect_gap_proven"] is not True:
        raise IdleSignalSchedulerError("DESIRED_EFFECT_GAP_NOT_PROVEN", f"{path}/desired_effect_gap_proven")
    if out["dependency_ready"] is not True:
        raise IdleSignalSchedulerError("DEPENDENCY_NOT_READY", f"{path}/dependency_ready")
    if out["priority_class"] not in IDLE_PRIORITIES:
        raise IdleSignalSchedulerError("IDLE_PRIORITY_REQUIRED", f"{path}/priority_class")
    for name in (
        "user_value_score",
        "materiality_score",
        "dependency_readiness_score",
        "estimated_cost_score",
    ):
        _bounded_int(out[name], f"{path}/{name}")
    _bounded_int(out["age_cycles"], f"{path}/age_cycles", low=0, high=1_000_000)
    if not isinstance(out["task_release_proposal"], Mapping):
        raise IdleSignalSchedulerError("TASK_RELEASE_PROPOSAL_REQUIRED", f"{path}/task_release_proposal")
    proposal = dict(out["task_release_proposal"])
    if proposal.get("schema_version") != "TaskReleaseProposal/v1":
        raise IdleSignalSchedulerError("TASK_RELEASE_PROPOSAL_SCHEMA_INVALID", f"{path}/task_release_proposal/schema_version")
    if out["signal_ref"] not in proposal.get("source_signal_refs", []):
        raise IdleSignalSchedulerError("SIGNAL_PROPOSAL_BINDING_MISSING", f"{path}/task_release_proposal/source_signal_refs")
    if proposal.get("signal_primary_domain") != out["signal_primary_domain"]:
        raise IdleSignalSchedulerError("SIGNAL_DOMAIN_PROPOSAL_MISMATCH", f"{path}/task_release_proposal/signal_primary_domain")
    if proposal.get("desired_effect") != out["desired_effect"]:
        raise IdleSignalSchedulerError("DESIRED_EFFECT_PROPOSAL_MISMATCH", f"{path}/task_release_proposal/desired_effect")
    out["opportunity_digest"] = _digest(out)
    return out


def _canonical_idle_blockers(root: Path) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    claims_doc = load_yaml(root / CLAIMS_FILE)
    claims = claims_doc.get("claims") if isinstance(claims_doc, Mapping) else None
    if not isinstance(claims, list):
        raise IdleSignalSchedulerError("CANONICAL_CLAIMS_DOCUMENT_INVALID")
    for index, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            raise IdleSignalSchedulerError("CANONICAL_CLAIM_INVALID", f"/claims/{index}")
        if claim.get("claim_state") in {ACTIVE_IMPLEMENTATION, RESERVED_IMPLEMENTATION_NON_EXECUTABLE}:
            task_id = None
            binding = claim.get("route_binding")
            if isinstance(binding, Mapping):
                task_id = binding.get("task_id")
            blockers.append(
                {
                    "priority": P2,
                    "work_ref": f"task://{task_id or 'UNKNOWN'}",
                    "reason": "CANONICAL_ACTIVE_OR_RESERVED_WORK_CLAIM",
                    "evidence_refs": [CLAIMS_FILE],
                }
            )
    worker_doc = load_yaml(root / GPT_WORKERS_REGISTRY)
    slots = worker_doc.get("worker_slots") if isinstance(worker_doc, Mapping) else None
    if not isinstance(slots, list):
        raise IdleSignalSchedulerError("GPT_WORKER_REGISTRY_INVALID")
    for index, slot in enumerate(slots):
        if not isinstance(slot, Mapping):
            raise IdleSignalSchedulerError("GPT_WORKER_SLOT_INVALID", f"/worker_slots/{index}")
        blockers.append(
            {
                "priority": P2,
                "work_ref": f"worker-slot://{slot.get('worker_slot_id') or slot.get('slot_id') or index}",
                "reason": "GPT_ENGINEERING_WORKER_SLOT_ALREADY_ACTIVE",
                "evidence_refs": [GPT_WORKERS_REGISTRY],
            }
        )
    return blockers


def _rank_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    # IAGL-compatible ordering: priority dominates. Aging/starvation is a bounded
    # tie-breaker inside P3/P4 and can never outrank P0/P1/P2 because those are
    # blocked before this function is used.
    score = (
        int(item["user_value_score"])
        + int(item["materiality_score"])
        + int(item["dependency_readiness_score"])
        + min(int(item["age_cycles"]), 20) * 2
        - int(item["estimated_cost_score"])
    )
    return (
        PRIORITY_ORDER[item["priority_class"]],
        -score,
        -min(int(item["age_cycles"]), 20),
        str(item["opportunity_id"]),
    )


def _decision(status: str, *, reason: str, selected: Mapping[str, Any] | None = None, blockers: Sequence[Mapping[str, Any]] = (), priority_observation: Mapping[str, Any] | None = None, r150_receipt: Mapping[str, Any] | None = None, authorization: Mapping[str, Any] | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": DECISION_SCHEMA,
        "status": status,
        "reason": reason,
        "selected_opportunity_id": selected.get("opportunity_id") if selected else None,
        "selected_signal_ref": selected.get("signal_ref") if selected else None,
        "blockers": _copy(list(blockers)),
        "priority_observation_digest": priority_observation.get("observation_digest") if priority_observation else None,
        "r150_receipt_digest": r150_receipt.get("receipt_digest") if r150_receipt else None,
        "authorization": _copy(authorization) if authorization else None,
    }
    value["decision_digest"] = _digest(value)
    return value


def _authorization(selected: Mapping[str, Any], *, current_main: str, priority_observation: Mapping[str, Any], r150_receipt: Mapping[str, Any]) -> dict[str, Any]:
    if r150_receipt.get("schema_version") != TRUSTED_RECEIPT_SCHEMA:
        raise IdleSignalSchedulerError("R150_TRUSTED_RECEIPT_REQUIRED")
    receipt_digest = r150_receipt.get("receipt_digest")
    if not isinstance(receipt_digest, str) or len(receipt_digest) != 64:
        raise IdleSignalSchedulerError("R150_RECEIPT_DIGEST_INVALID")
    trusted = r150_receipt.get("trusted_context")
    if not isinstance(trusted, Mapping) or trusted.get("canonical_main") != current_main:
        raise IdleSignalSchedulerError("R150_RECEIPT_CANONICAL_MAIN_MISMATCH")
    impact = r150_receipt.get("impact_receipt")
    if not isinstance(impact, Mapping):
        raise IdleSignalSchedulerError("R150_IMPACT_RECEIPT_MISSING")
    disposition = impact.get("final_disposition")
    if disposition not in RELEASEABLE_R150_DISPOSITIONS:
        raise IdleSignalSchedulerError("R150_DISPOSITION_NOT_AUTO_RELEASEABLE")
    authority_boundary = r150_receipt.get("authority_boundary")
    if not isinstance(authority_boundary, Mapping) or authority_boundary.get("evidence_only") is not True:
        raise IdleSignalSchedulerError("R150_EVIDENCE_ONLY_BOUNDARY_REQUIRED")

    payload = {
        "schema_version": AUTHORIZATION_SCHEMA,
        "signal_ref": selected["signal_ref"],
        "opportunity_id": selected["opportunity_id"],
        "opportunity_digest": selected["opportunity_digest"],
        "canonical_main": current_main,
        "priority_observation_digest": priority_observation["observation_digest"],
        "r150_receipt_digest": receipt_digest,
        "r150_final_disposition": disposition,
        "standing_user_policy_ref": STANDING_POLICY_REF,
        "priority_semantics_ref": IAGL_PRIORITY_REF,
        "release_gate_refs": [R149_REF, R150_REF],
        "side_effect_plan": [
            "create_issue",
            "create_route",
            "create_work_claim",
            "allocate_worker_slot",
            "begin_bounded_engineering",
        ],
        "authority": {
            "creates_signal_truth": False,
            "signal_self_authorizes": False,
            "can_create_issue": True,
            "can_create_route": True,
            "can_create_work_claim": True,
            "can_allocate_worker_slot": True,
            "can_begin_bounded_engineering": True,
            "can_merge_without_independent_accept": False,
            "can_deploy_production": False,
            "can_expand_permissions_or_secrets": False,
            "can_touch_trading_orders_or_funds": False,
            "can_perform_destructive_history_rewrite": False,
        },
        "independent_exact_head_review_required": True,
        "apply_requires_fresh_recheck": True,
    }
    payload["authorization_id"] = f"r151-auto-release:{_digest(payload)[:24]}"
    payload["authorization_digest"] = _digest(payload)
    return payload


def evaluate_idle_signal_startup(
    repo_root: str | Path,
    opportunities: Sequence[Mapping[str, Any]],
    *,
    expected_coordinator_main: str,
    priority_observation_value: Mapping[str, Any],
) -> dict[str, Any]:
    """Select at most one idle Signal opportunity and bind it through R150.

    This function is evaluation-only. It returns an explicit side-effect plan but
    performs no GitHub Issue/Route/Claim/worker mutation itself.
    """
    root = Path(repo_root).resolve()
    priority_observation = validate_priority_observation(priority_observation_value)

    canonical_blockers = _canonical_idle_blockers(root)
    external_blockers = [
        item for item in priority_observation["items"] if item["priority"] in BLOCKING_PRIORITIES
    ]
    blockers = [*canonical_blockers, *external_blockers]
    if blockers:
        return _decision(
            "NO_IDLE_RELEASE",
            reason="HIGHER_PRIORITY_OR_ACTIVE_WORK_PRESENT",
            blockers=blockers,
            priority_observation=priority_observation,
        )

    valid: list[dict[str, Any]] = []
    user_gate: list[dict[str, Any]] = []
    for index, raw in enumerate(opportunities):
        try:
            candidate = validate_opportunity(raw, index=index)
        except IdleSignalSchedulerError:
            continue
        hits = _exclusion_hits(candidate["task_release_proposal"])
        if hits:
            user_gate.append({"opportunity_id": candidate["opportunity_id"], "exclusion_hits": list(hits)})
            continue
        valid.append(candidate)

    if not valid:
        if user_gate:
            return _decision(
                "USER_GATE",
                reason="ONLY_HIGH_RISK_OR_EXCLUDED_SIGNAL_OPPORTUNITIES_AVAILABLE",
                blockers=user_gate,
                priority_observation=priority_observation,
            )
        return _decision(
            "NO_IDLE_RELEASE",
            reason="NO_ELIGIBLE_DIGESTED_SIGNAL_OPPORTUNITY",
            priority_observation=priority_observation,
        )

    selected = min(valid, key=_rank_key)
    try:
        r150_receipt = evaluate_trusted_release_proposal(
            root,
            selected["task_release_proposal"],
            expected_coordinator_main=expected_coordinator_main,
        )
    except TrustedReleaseError as exc:
        return _decision(
            "NO_IDLE_RELEASE",
            reason=f"R150_FAIL_CLOSED:{exc.code}",
            selected=selected,
            priority_observation=priority_observation,
        )

    impact = r150_receipt.get("impact_receipt")
    disposition = impact.get("final_disposition") if isinstance(impact, Mapping) else None
    if disposition not in RELEASEABLE_R150_DISPOSITIONS:
        return _decision(
            "NO_IDLE_RELEASE",
            reason=f"R150_NON_RELEASE:{disposition or 'UNKNOWN'}",
            selected=selected,
            priority_observation=priority_observation,
            r150_receipt=r150_receipt,
        )

    authorization = _authorization(
        selected,
        current_main=expected_coordinator_main,
        priority_observation=priority_observation,
        r150_receipt=r150_receipt,
    )
    return _decision(
        "AUTO_RELEASE_AUTHORIZED",
        reason="IDLE_SIGNAL_OPPORTUNITY_PASSED_PRIORITY_R149_R150_AND_STANDING_POLICY",
        selected=selected,
        priority_observation=priority_observation,
        r150_receipt=r150_receipt,
        authorization=authorization,
    )
