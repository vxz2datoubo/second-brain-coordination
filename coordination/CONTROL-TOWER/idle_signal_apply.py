from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

from control_tower import load_yaml
from idle_signal_scheduler import (
    AUTHORIZATION_SCHEMA,
    OPPORTUNITY_SCHEMA,
    _exclusion_hits,
    _requested_side_effect_surface,
    evaluate_idle_signal_startup,
    validate_opportunity,
)
from lane_claims import (
    ACTIVE_IMPLEMENTATION,
    CLAIMS_FILE,
    CLOSED_NO_ACTIVE_IMPLEMENTATION,
    RESERVED_IMPLEMENTATION_NON_EXECUTABLE,
)
from trusted_task_release import GPT_WORKERS_REGISTRY


APPLY_INTENT_SCHEMA = "IdleSignalApplyIntent/v1"
BOOTSTRAP_EVIDENCE_SCHEMA = "IdleSignalBootstrapEvidence/v1"
BOOTSTRAP_MANIFEST_SCHEMA = "IdleSignalBootstrapManifest/v1"
ACTIVATION_MANIFEST_SCHEMA = "IdleSignalActivationManifest/v1"
APPLIED_STATE_SCHEMA = "IdleSignalAppliedState/v1"
APPLY_RECEIPT_SCHEMA = "IdleSignalApplyReceipt/v1"

AUTHORIZED_LOGICAL_PLAN = (
    "create_issue",
    "create_route",
    "create_work_claim",
    "allocate_worker_slot",
    "begin_bounded_engineering",
)
AGENT_TYPE = "GPT_ENGINEERING_WORKER"
MODEL_ID = "GPT-5.6 Sol"
REVIEWER_ROLE = "GPT_INDEPENDENT_REVIEWER"
RESOURCE_CLASS = "LIGHT_TO_MEDIUM_IMPLEMENTATION"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


class IdleSignalApplyError(ValueError):
    """Stable fail-closed R152 error."""

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


def _git_head(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise IdleSignalApplyError("GIT_HEAD_UNAVAILABLE") from exc


def _nonempty(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IdleSignalApplyError("INVALID_STRING", path)
    return value


def _positive_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise IdleSignalApplyError("INVALID_POSITIVE_INTEGER", path)
    return value


def _normalized_surface(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise IdleSignalApplyError("SURFACE_NOT_OBJECT", path)
    required = {
        "write_paths",
        "read_paths",
        "interfaces",
        "read_domains",
        "write_domains",
        "authority_claims",
    }
    if set(value) != required:
        raise IdleSignalApplyError("SURFACE_FIELDS_INVALID", path)
    out: dict[str, Any] = {}
    for key in required:
        items = value.get(key)
        if not isinstance(items, list):
            raise IdleSignalApplyError("SURFACE_FIELD_NOT_LIST", f"{path}/{key}")
        if key != "interfaces" and any(not isinstance(item, str) for item in items):
            raise IdleSignalApplyError("SURFACE_STRING_ITEM_INVALID", f"{path}/{key}")
        out[key] = _copy(items)
    return out


def _surface_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    for key in (
        "write_paths",
        "read_paths",
        "interfaces",
        "read_domains",
        "write_domains",
        "authority_claims",
    ):
        left_items = left.get(key, [])
        right_items = right.get(key, [])
        if sorted(_canonical(item) for item in left_items) != sorted(
            _canonical(item) for item in right_items
        ):
            return False
    return True


def _validate_authorization(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise IdleSignalApplyError("R151_AUTHORIZATION_NOT_OBJECT")
    if value.get("schema_version") != AUTHORIZATION_SCHEMA:
        raise IdleSignalApplyError("R151_AUTHORIZATION_SCHEMA_INVALID")
    authorization_digest = value.get("authorization_digest")
    if not isinstance(authorization_digest, str) or len(authorization_digest) != 64:
        raise IdleSignalApplyError("R151_AUTHORIZATION_DIGEST_INVALID")
    without_digest = dict(_copy(value))
    without_digest.pop("authorization_digest", None)
    if _digest(without_digest) != authorization_digest:
        raise IdleSignalApplyError("R151_AUTHORIZATION_DIGEST_FORGED")
    authorization_id = value.get("authorization_id")
    if not isinstance(authorization_id, str) or not authorization_id:
        raise IdleSignalApplyError("R151_AUTHORIZATION_ID_INVALID")
    id_basis = dict(without_digest)
    id_basis.pop("authorization_id", None)
    expected_id = f"r151-auto-release:{_digest(id_basis)[:24]}"
    if authorization_id != expected_id:
        raise IdleSignalApplyError("R151_AUTHORIZATION_ID_FORGED")
    if tuple(value.get("side_effect_plan", [])) != AUTHORIZED_LOGICAL_PLAN:
        raise IdleSignalApplyError("R151_SIDE_EFFECT_PLAN_INVALID")
    authority = value.get("authority")
    if not isinstance(authority, Mapping):
        raise IdleSignalApplyError("R151_AUTHORITY_BOUNDARY_MISSING")
    required_true = (
        "can_create_issue",
        "can_create_route",
        "can_create_work_claim",
        "can_allocate_worker_slot",
        "can_begin_bounded_engineering",
    )
    if any(authority.get(key) is not True for key in required_true):
        raise IdleSignalApplyError("R151_REQUIRED_APPLY_CAPABILITY_MISSING")
    required_false = (
        "creates_signal_truth",
        "signal_self_authorizes",
        "caller_can_attest_priority_completeness",
        "can_merge_without_independent_accept",
        "can_deploy_production",
        "can_expand_permissions_or_secrets",
        "can_touch_trading_orders_or_funds",
        "can_perform_destructive_history_rewrite",
    )
    if any(authority.get(key) is not False for key in required_false):
        raise IdleSignalApplyError("R151_UNSAFE_AUTHORITY_PRESENT")
    if value.get("apply_requires_fresh_recheck") is not True:
        raise IdleSignalApplyError("R151_FRESH_RECHECK_REQUIRED")
    if value.get("independent_exact_head_review_required") is not True:
        raise IdleSignalApplyError("R151_INDEPENDENT_REVIEW_REQUIRED")
    return _copy(value)


def validate_apply_intent(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise IdleSignalApplyError("APPLY_INTENT_NOT_OBJECT")
    required = {
        "schema_version",
        "lane_id",
        "route_epoch",
        "release_reason_class",
        "requested_surface",
        "resource_class",
        "reviewer_role",
        "reviewer_separation",
        "operation_plan",
    }
    if set(value) != required:
        raise IdleSignalApplyError("APPLY_INTENT_FIELDS_INVALID")
    if value.get("schema_version") != APPLY_INTENT_SCHEMA:
        raise IdleSignalApplyError("APPLY_INTENT_SCHEMA_INVALID")
    out = _copy(value)
    _nonempty(out["lane_id"], "/lane_id")
    _positive_int(out["route_epoch"], "/route_epoch")
    _nonempty(out["release_reason_class"], "/release_reason_class")
    out["requested_surface"] = _normalized_surface(
        out["requested_surface"], "/requested_surface"
    )
    if out["resource_class"] != RESOURCE_CLASS:
        raise IdleSignalApplyError("RESOURCE_CLASS_NOT_BOUNDED")
    if out["reviewer_role"] != REVIEWER_ROLE:
        raise IdleSignalApplyError("REVIEWER_ROLE_INVALID")
    if out["reviewer_separation"] != "EXECUTOR_IS_NOT_ACCEPTANCE_AUTHORITY":
        raise IdleSignalApplyError("REVIEWER_SEPARATION_INVALID")
    if tuple(out["operation_plan"]) != AUTHORIZED_LOGICAL_PLAN:
        raise IdleSignalApplyError("APPLY_OPERATION_PLAN_INVALID")
    return out


def validate_bootstrap_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise IdleSignalApplyError("BOOTSTRAP_EVIDENCE_NOT_OBJECT")
    required = {
        "schema_version",
        "issue",
        "implementation_pr",
        "branch",
        "bootstrap_head",
        "draft",
        "empty_bootstrap_commit",
        "file_mutations",
    }
    if set(value) != required:
        raise IdleSignalApplyError("BOOTSTRAP_EVIDENCE_FIELDS_INVALID")
    if value.get("schema_version") != BOOTSTRAP_EVIDENCE_SCHEMA:
        raise IdleSignalApplyError("BOOTSTRAP_EVIDENCE_SCHEMA_INVALID")
    out = _copy(value)
    _positive_int(out["issue"], "/issue")
    _positive_int(out["implementation_pr"], "/implementation_pr")
    _nonempty(out["branch"], "/branch")
    if not isinstance(out["bootstrap_head"], str) or not _SHA40.fullmatch(
        out["bootstrap_head"]
    ):
        raise IdleSignalApplyError("BOOTSTRAP_HEAD_INVALID")
    if out["draft"] is not True:
        raise IdleSignalApplyError("BOOTSTRAP_PR_MUST_BE_DRAFT")
    if out["empty_bootstrap_commit"] is not True:
        raise IdleSignalApplyError("BOOTSTRAP_COMMIT_MUST_BE_EMPTY")
    if out["file_mutations"] != []:
        raise IdleSignalApplyError("BOOTSTRAP_FILE_MUTATION_FORBIDDEN")
    return out


def _authorization_identity(
    authorization: Mapping[str, Any], route_epoch: int
) -> dict[str, Any]:
    seed = str(authorization["authorization_digest"])
    token = seed[:12].upper()
    branch_token = seed[:12]
    return {
        "task_id": f"GPT-IDLE-SIGNAL-AUTO-{token}",
        "route_id": f"GPT-IDLE-SIGNAL-AUTO-ROUTE-{token}",
        "worker_slot_id": f"GPT-WORKER-IDLE-{token}",
        "branch": f"gpt/idle-signal-auto-{branch_token}",
        "route_epoch": route_epoch,
        "completion_signal": f"IDLE_SIGNAL_AUTO_{token}_READY_FOR_INDEPENDENT_REVIEW",
    }


def _load_lane_state(root: Path, lane_id: str) -> dict[str, Any]:
    doc = load_yaml(root / CLAIMS_FILE)
    claims = doc.get("claims") if isinstance(doc, Mapping) else None
    if not isinstance(claims, list):
        raise IdleSignalApplyError("CANONICAL_CLAIMS_INVALID")
    matches = [
        claim
        for claim in claims
        if isinstance(claim, Mapping) and claim.get("lane_id") == lane_id
    ]
    if len(matches) != 1:
        raise IdleSignalApplyError("LANE_CLAIM_CARDINALITY_INVALID")
    claim = dict(matches[0])
    if claim.get("claim_state") != CLOSED_NO_ACTIVE_IMPLEMENTATION:
        raise IdleSignalApplyError("LANE_NOT_CLOSED_FOR_FRESH_RELEASE")
    for field in (
        "write_paths",
        "read_paths",
        "interfaces",
        "read_domains",
        "write_domains",
        "authority_claims",
    ):
        if claim.get(field) not in ([], None):
            raise IdleSignalApplyError("CLOSED_LANE_RETAINS_ACTIVE_SURFACE", f"/{field}")
    if claim.get("route_binding") not in (None, {}, ""):
        raise IdleSignalApplyError("CLOSED_LANE_RETAINS_ROUTE")
    return claim


def _validate_lane_reopen_rule(
    claim: Mapping[str, Any], release_reason_class: str
) -> None:
    receipt = claim.get("closure_receipt")
    rule = receipt.get("reopen_rule") if isinstance(receipt, Mapping) else None
    if not isinstance(rule, str) or not rule.strip():
        raise IdleSignalApplyError("LANE_REOPEN_RULE_MISSING")
    upper = rule.upper()
    restricted = {"BUG", "SECURITY_GAP", "CONTRACT_DEFECT", "PROVEN_REGRESSION"}
    if "BUG" in upper and "SECURITY_GAP" in upper:
        if release_reason_class not in restricted:
            raise IdleSignalApplyError("LANE_REOPEN_REASON_NOT_AUTHORIZED")
    elif "NEW_GOVERNED_TASK" not in upper and "NEW_GOVERNED_SUCCESSOR" not in upper:
        raise IdleSignalApplyError("LANE_REOPEN_RULE_UNSUPPORTED")


def _assert_no_existing_live_control_state(root: Path) -> None:
    claims_doc = load_yaml(root / CLAIMS_FILE)
    claims = claims_doc.get("claims") if isinstance(claims_doc, Mapping) else None
    if not isinstance(claims, list):
        raise IdleSignalApplyError("CANONICAL_CLAIMS_INVALID")
    for claim in claims:
        if isinstance(claim, Mapping) and claim.get("claim_state") in {
            ACTIVE_IMPLEMENTATION,
            RESERVED_IMPLEMENTATION_NON_EXECUTABLE,
        }:
            raise IdleSignalApplyError("EXISTING_ACTIVE_OR_RESERVED_CLAIM")
    workers_doc = load_yaml(root / GPT_WORKERS_REGISTRY)
    slots = workers_doc.get("worker_slots") if isinstance(workers_doc, Mapping) else None
    if not isinstance(slots, list):
        raise IdleSignalApplyError("GPT_WORKER_REGISTRY_INVALID")
    if slots:
        raise IdleSignalApplyError("EXISTING_GPT_WORKER_SLOT")


def _fresh_authorization(
    root: Path,
    opportunity: Mapping[str, Any],
    priority_hints: Mapping[str, Any],
    *,
    expected_current_main: str,
) -> dict[str, Any]:
    result = evaluate_idle_signal_startup(
        root,
        [opportunity],
        expected_coordinator_main=expected_current_main,
        priority_observation_value=priority_hints,
    )
    if not isinstance(result, Mapping):
        raise IdleSignalApplyError("R151_FRESH_REPLAY_INVALID")
    if result.get("status") != "AUTO_RELEASE_AUTHORIZED":
        raise IdleSignalApplyError(
            f"R151_FRESH_REPLAY_NOT_AUTHORIZED:{result.get('reason') or 'UNKNOWN'}"
        )
    authorization = result.get("authorization")
    if not isinstance(authorization, Mapping):
        raise IdleSignalApplyError("R151_FRESH_AUTHORIZATION_MISSING")
    return _validate_authorization(authorization)


def _bootstrap_manifest(
    authorization: Mapping[str, Any],
    opportunity: Mapping[str, Any],
    identity: Mapping[str, Any],
    *,
    current_main: str,
) -> dict[str, Any]:
    value = {
        "schema_version": BOOTSTRAP_MANIFEST_SCHEMA,
        "status": "BOOTSTRAP_REQUIRED",
        "canonical_main": current_main,
        "authorization_digest": authorization["authorization_digest"],
        "opportunity_digest": opportunity["opportunity_digest"],
        "logical_authorized_plan": list(AUTHORIZED_LOGICAL_PLAN),
        "identity": _copy(identity),
        "issue": {
            "operation": "create_issue",
            "title": f"Auto-released bounded engineering: {opportunity['desired_effect']}",
            "body_markers": {
                "r151_authorization_id": authorization["authorization_id"],
                "r151_authorization_digest": authorization["authorization_digest"],
                "signal_ref": opportunity["signal_ref"],
                "task_id": identity["task_id"],
            },
        },
        "runtime_pr_bootstrap": {
            "operation": "begin_bounded_engineering",
            "phase": "NON_EXECUTABLE_BOOTSTRAP_ONLY",
            "branch": identity["branch"],
            "requires_issue_output": True,
            "empty_commit_required": True,
            "file_mutations": [],
            "draft_pr_required": True,
            "reason": (
                "R144 requires Issue/PR/branch identity before any ACTIVE or RESERVED "
                "GPT worker slot can become canonical."
            ),
        },
        "deferred_until_bootstrap_evidence": [
            "create_route",
            "create_work_claim",
            "allocate_worker_slot",
            "begin_executable_bounded_engineering",
        ],
        "authority_boundary": {
            "execution_authority_granted": False,
            "canonical_route_write_authorized": False,
            "canonical_claim_write_authorized": False,
            "canonical_worker_slot_write_authorized": False,
            "file_mutation_authorized": False,
            "merge_authority_granted": False,
            "production_deploy_authorized": False,
            "secrets_or_permission_expansion_authorized": False,
            "trading_order_or_fund_authorized": False,
            "destructive_history_authorized": False,
            "independent_review_required_for_activation_gate": True,
        },
    }
    value["manifest_digest"] = _digest(value)
    return value


def _activation_manifest(
    authorization: Mapping[str, Any],
    opportunity: Mapping[str, Any],
    intent: Mapping[str, Any],
    identity: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
    *,
    current_main: str,
) -> dict[str, Any]:
    surface = _copy(intent["requested_surface"])
    issue = bootstrap["issue"]
    pr = bootstrap["implementation_pr"]
    branch = bootstrap["branch"]
    binding = {
        "worker_slot_id": identity["worker_slot_id"],
        "task_id": identity["task_id"],
        "route_epoch": identity["route_epoch"],
        "issue": issue,
        "pr": pr,
        "branch": branch,
    }
    route = {
        "schema_version": "1.3",
        "route_id": identity["route_id"],
        "repository": "vxz2datoubo/second-brain-coordination",
        "status": "ACTIVE_IMPLEMENTATION",
        "execution_allowed": True,
        "runtime_code_change_allowed": True,
        "automatic_resume": False,
        "merge_authorized": False,
        "self_review_forbidden": True,
        "binding": {
            "task_id": identity["task_id"],
            "route_epoch": identity["route_epoch"],
            "issue": issue,
            "lane_id": intent["lane_id"],
            "implementation_branch": branch,
            "implementation_pr": pr,
            "worker_slot_id": identity["worker_slot_id"],
        },
        "executor": {
            "role": AGENT_TYPE,
            "model_id": MODEL_ID,
            "worker_slot_id": identity["worker_slot_id"],
            "reviewer_role": REVIEWER_ROLE,
            "impersonation_forbidden": True,
        },
        "write_scope": {
            "implementation": list(surface["write_paths"]),
            "cross_repo": [],
        },
        "hard_locks": [
            "NO_W3_WRITE",
            "NO_SIGNAL_TOWER_RUNTIME_WRITE",
            "NO_TRADE",
            "NO_SECRET_PERMISSION_EXPANSION",
            "NO_PRODUCTION_DEPLOY",
            "NO_DESTRUCTIVE_HISTORY_REWRITE",
            "NO_SELF_REVIEW",
            "NO_SELF_MERGE",
        ],
    }
    claim = {
        "lane_id": intent["lane_id"],
        "claim_state": ACTIVE_IMPLEMENTATION,
        "execution_agent": AGENT_TYPE,
        "worker_slot_id": identity["worker_slot_id"],
        "resource_class": intent["resource_class"],
        "route_binding": _copy(binding),
        **surface,
    }
    worker_slot = {
        "worker_slot_id": identity["worker_slot_id"],
        "agent_type": AGENT_TYPE,
        "executor_role": AGENT_TYPE,
        "model_id": MODEL_ID,
        "task_id": identity["task_id"],
        "route_epoch": identity["route_epoch"],
        "issue": issue,
        "pr": pr,
        "branch": branch,
        "status": "ACTIVE_IMPLEMENTATION",
        "execution_allowed": True,
        "completion_signal": identity["completion_signal"],
        **surface,
        "resource_class": intent["resource_class"],
        "provenance": {
            "r151_authorization_id": authorization["authorization_id"],
            "r151_authorization_digest": authorization["authorization_digest"],
            "r152_base_main": current_main,
            "bootstrap_head": bootstrap["bootstrap_head"],
        },
        "reviewer_role": intent["reviewer_role"],
        "reviewer_separation": intent["reviewer_separation"],
        "activation_state": "ACTIVE",
        "closure_state": None,
    }
    value = {
        "schema_version": ACTIVATION_MANIFEST_SCHEMA,
        "status": "ACTIVATION_GATE_CANDIDATE",
        "canonical_main": current_main,
        "authorization_digest": authorization["authorization_digest"],
        "opportunity_digest": opportunity["opportunity_digest"],
        "bootstrap_evidence": _copy(bootstrap),
        "identity": _copy(identity),
        "logical_authorized_plan": list(AUTHORIZED_LOGICAL_PLAN),
        "atomic_control_plane_commit_required": True,
        "partial_apply_forbidden": True,
        "activation_gate": {
            "must_be_separate_pr": True,
            "independent_exact_head_review_required": True,
            "merge_requires_expected_head": True,
            "execution_effective_only_after_gate_is_canonical": True,
        },
        "route_artifact": {
            "path": f"coordination/ROUTES/{identity['route_id']}.yaml",
            "payload": route,
        },
        "work_claim_replacement": claim,
        "worker_slot_append": worker_slot,
        "begin_bounded_engineering": {
            "allowed_only_after_activation_gate_canonical": True,
            "implementation_pr": pr,
            "branch": branch,
            "write_paths": list(surface["write_paths"]),
        },
        "authority_boundary": {
            "manifest_performs_side_effects": False,
            "execution_authority_granted_by_manifest": False,
            "activation_candidate_only": True,
            "merge_authority_granted": False,
            "production_deploy_authorized": False,
            "secrets_or_permission_expansion_authorized": False,
            "trading_order_or_fund_authorized": False,
            "destructive_history_authorized": False,
            "w3_write_authorized": False,
            "signal_runtime_write_authorized": False,
        },
    }
    value["manifest_digest"] = _digest(value)
    return value


def prepare_apply_transaction(
    repo_root: str | Path,
    opportunity_value: Mapping[str, Any],
    priority_hints: Mapping[str, Any],
    presented_authorization: Mapping[str, Any],
    apply_intent: Mapping[str, Any],
    *,
    expected_current_main: str,
    bootstrap_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Prepare R151 apply without performing GitHub/control-plane side effects."""
    root = Path(repo_root).resolve()
    if _git_head(root) != expected_current_main:
        raise IdleSignalApplyError("CURRENT_MAIN_DRIFT")
    presented = _validate_authorization(presented_authorization)
    if presented.get("canonical_main") != expected_current_main:
        raise IdleSignalApplyError("R151_AUTHORIZATION_MAIN_STALE")

    opportunity = validate_opportunity(opportunity_value)
    if opportunity.get("schema_version") != OPPORTUNITY_SCHEMA:
        raise IdleSignalApplyError("OPPORTUNITY_SCHEMA_INVALID")
    if presented.get("opportunity_id") != opportunity["opportunity_id"]:
        raise IdleSignalApplyError("AUTHORIZATION_OPPORTUNITY_ID_MISMATCH")
    if presented.get("opportunity_digest") != opportunity["opportunity_digest"]:
        raise IdleSignalApplyError("AUTHORIZATION_OPPORTUNITY_DIGEST_MISMATCH")
    if presented.get("signal_ref") != opportunity["signal_ref"]:
        raise IdleSignalApplyError("AUTHORIZATION_SIGNAL_MISMATCH")

    intent = validate_apply_intent(apply_intent)
    proposal = opportunity["task_release_proposal"]
    proposal_surface = _normalized_surface(
        proposal.get("proposed_write_surface"),
        "/task_release_proposal/proposed_write_surface",
    )
    if not _surface_equal(intent["requested_surface"], proposal_surface):
        raise IdleSignalApplyError("CALLER_APPLY_SURFACE_EXPANSION_OR_DRIFT")
    if _exclusion_hits(_requested_side_effect_surface(opportunity)):
        raise IdleSignalApplyError("EXCLUDED_SIDE_EFFECT_REQUESTED")

    fresh = _fresh_authorization(
        root,
        opportunity_value,
        priority_hints,
        expected_current_main=expected_current_main,
    )
    if fresh["authorization_digest"] != presented["authorization_digest"]:
        raise IdleSignalApplyError("R151_FRESH_AUTHORIZATION_MISMATCH")
    if fresh["priority_observation_digest"] != presented["priority_observation_digest"]:
        raise IdleSignalApplyError("R151_PRIORITY_OBSERVATION_DRIFT")
    if fresh["r150_receipt_digest"] != presented["r150_receipt_digest"]:
        raise IdleSignalApplyError("R150_RECEIPT_DRIFT")

    _assert_no_existing_live_control_state(root)
    claim = _load_lane_state(root, intent["lane_id"])
    _validate_lane_reopen_rule(claim, intent["release_reason_class"])

    identity = _authorization_identity(presented, intent["route_epoch"])
    if bootstrap_evidence is None:
        return _bootstrap_manifest(
            presented,
            opportunity,
            identity,
            current_main=expected_current_main,
        )

    bootstrap = validate_bootstrap_evidence(bootstrap_evidence)
    if bootstrap["branch"] != identity["branch"]:
        raise IdleSignalApplyError("BOOTSTRAP_BRANCH_MISMATCH")
    return _activation_manifest(
        presented,
        opportunity,
        intent,
        identity,
        bootstrap,
        current_main=expected_current_main,
    )


def verify_applied_state(
    manifest: Mapping[str, Any], observed: Mapping[str, Any]
) -> dict[str, Any]:
    """Verify exact post-apply bindings. Receipt is evidence-only."""
    if (
        not isinstance(manifest, Mapping)
        or manifest.get("schema_version") != ACTIVATION_MANIFEST_SCHEMA
    ):
        raise IdleSignalApplyError("ACTIVATION_MANIFEST_REQUIRED")
    expected_digest = manifest.get("manifest_digest")
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise IdleSignalApplyError("ACTIVATION_MANIFEST_DIGEST_INVALID")
    manifest_basis = dict(_copy(manifest))
    manifest_basis.pop("manifest_digest", None)
    if _digest(manifest_basis) != expected_digest:
        raise IdleSignalApplyError("ACTIVATION_MANIFEST_DIGEST_FORGED")

    if (
        not isinstance(observed, Mapping)
        or observed.get("schema_version") != APPLIED_STATE_SCHEMA
    ):
        raise IdleSignalApplyError("APPLIED_STATE_SCHEMA_INVALID")
    required = {
        "schema_version",
        "canonical_main",
        "activation_gate_pr",
        "activation_gate_reviewed_head",
        "activation_gate_verdict",
        "activation_gate_merge_commit",
        "issue",
        "implementation_pr",
        "branch",
        "route_artifact",
        "work_claim",
        "worker_slot",
    }
    if set(observed) != required:
        raise IdleSignalApplyError("APPLIED_STATE_FIELDS_INVALID")
    if observed["activation_gate_verdict"] != "ACCEPT":
        raise IdleSignalApplyError("ACTIVATION_GATE_NOT_ACCEPTED")
    for field in ("activation_gate_reviewed_head", "activation_gate_merge_commit"):
        if not isinstance(observed[field], str) or not _SHA40.fullmatch(observed[field]):
            raise IdleSignalApplyError("ACTIVATION_GATE_SHA_INVALID", f"/{field}")
    _positive_int(observed["activation_gate_pr"], "/activation_gate_pr")

    bootstrap = manifest["bootstrap_evidence"]
    exact_scalars = {
        "canonical_main": manifest["canonical_main"],
        "issue": bootstrap["issue"],
        "implementation_pr": bootstrap["implementation_pr"],
        "branch": bootstrap["branch"],
    }
    for field, expected in exact_scalars.items():
        if observed.get(field) != expected:
            raise IdleSignalApplyError("APPLIED_IDENTITY_MISMATCH", f"/{field}")

    if observed["route_artifact"] != manifest["route_artifact"]:
        raise IdleSignalApplyError("APPLIED_ROUTE_MISMATCH")
    if observed["work_claim"] != manifest["work_claim_replacement"]:
        raise IdleSignalApplyError("APPLIED_CLAIM_MISMATCH")
    if observed["worker_slot"] != manifest["worker_slot_append"]:
        raise IdleSignalApplyError("APPLIED_WORKER_SLOT_MISMATCH")

    receipt = {
        "schema_version": APPLY_RECEIPT_SCHEMA,
        "manifest_digest": expected_digest,
        "canonical_main_before_activation": manifest["canonical_main"],
        "activation_gate_pr": observed["activation_gate_pr"],
        "activation_gate_reviewed_head": observed["activation_gate_reviewed_head"],
        "activation_gate_merge_commit": observed["activation_gate_merge_commit"],
        "implementation_issue": observed["issue"],
        "implementation_pr": observed["implementation_pr"],
        "branch": observed["branch"],
        "identity": _copy(manifest["identity"]),
        "verification": {
            "exact_issue_pr_branch_binding": True,
            "exact_route_binding": True,
            "exact_claim_binding": True,
            "exact_worker_slot_binding": True,
            "activation_gate_accept_required": True,
        },
        "authority_boundary": {
            "evidence_only": True,
            "grants_execution_authority": False,
            "grants_merge_authority": False,
            "grants_production_deploy": False,
            "grants_secrets_or_permission_expansion": False,
            "grants_trading_order_or_fund_access": False,
            "grants_destructive_history_rewrite": False,
            "grants_w3_write": False,
            "grants_signal_runtime_write": False,
        },
    }
    receipt["receipt_digest"] = _digest(receipt)
    return receipt
