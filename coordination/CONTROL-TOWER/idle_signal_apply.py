from __future__ import annotations

from base64 import b64decode
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

import yaml

from control_tower import load_yaml
from idle_signal_scheduler import (
    AUTHORIZATION_SCHEMA,
    MAX_REVIEW_QUEUE_PAGES,
    OPPORTUNITY_SCHEMA,
    REVIEW_QUEUE_ISSUE,
    _exclusion_hits,
    _load_r137_provider,
    _queue_field,
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
TRUSTED_BOOTSTRAP_SCHEMA = "TrustedIdleSignalBootstrapObservation/v1"
BOOTSTRAP_MANIFEST_SCHEMA = "IdleSignalBootstrapManifest/v1"
ACTIVATION_MANIFEST_SCHEMA = "IdleSignalActivationManifest/v1"
APPLIED_STATE_SCHEMA = "IdleSignalAppliedState/v1"
TRUSTED_APPLIED_STATE_SCHEMA = "TrustedIdleSignalAppliedStateObservation/v1"
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
REVIEWER_SEPARATION = "EXECUTOR_IS_NOT_ACCEPTANCE_AUTHORITY"
INDEPENDENCE_ATTESTATION = "NO_PRODUCTION_CODE_OR_REMEDIATION_ON_REVIEWED_HEAD"
RESOURCE_CLASS = "LIGHT_TO_MEDIUM_IMPLEMENTATION"
COORDINATOR_REPOSITORY = "vxz2datoubo/second-brain-coordination"
ROUTES_ROOT = "coordination/ROUTES"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_ISSUE_ENDPOINT = re.compile(
    r"^/repos/vxz2datoubo/second-brain-coordination/issues/[1-9][0-9]*$"
)
_QUEUE_COMMENT_ENDPOINT = re.compile(
    r"^/repos/vxz2datoubo/second-brain-coordination/issues/453/comments"
    r"\?per_page=100&page=[1-9][0-9]*$"
)


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


def _sha40(value: Any, code: str, path: str) -> str:
    if not isinstance(value, str) or not _SHA40.fullmatch(value):
        raise IdleSignalApplyError(code, path)
    return value


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise IdleSignalApplyError(code)
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
        if sorted(_canonical(item) for item in left.get(key, [])) != sorted(
            _canonical(item) for item in right.get(key, [])
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
    if authorization_id != f"r151-auto-release:{_digest(id_basis)[:24]}":
        raise IdleSignalApplyError("R151_AUTHORIZATION_ID_FORGED")
    if tuple(value.get("side_effect_plan", [])) != AUTHORIZED_LOGICAL_PLAN:
        raise IdleSignalApplyError("R151_SIDE_EFFECT_PLAN_INVALID")
    authority = value.get("authority")
    if not isinstance(authority, Mapping):
        raise IdleSignalApplyError("R151_AUTHORITY_BOUNDARY_MISSING")
    for key in (
        "can_create_issue",
        "can_create_route",
        "can_create_work_claim",
        "can_allocate_worker_slot",
        "can_begin_bounded_engineering",
    ):
        if authority.get(key) is not True:
            raise IdleSignalApplyError("R151_REQUIRED_APPLY_CAPABILITY_MISSING")
    for key in (
        "creates_signal_truth",
        "signal_self_authorizes",
        "caller_can_attest_priority_completeness",
        "can_merge_without_independent_accept",
        "can_deploy_production",
        "can_expand_permissions_or_secrets",
        "can_touch_trading_orders_or_funds",
        "can_perform_destructive_history_rewrite",
    ):
        if authority.get(key) is not False:
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
    if out["reviewer_separation"] != REVIEWER_SEPARATION:
        raise IdleSignalApplyError("REVIEWER_SEPARATION_INVALID")
    if tuple(out["operation_plan"]) != AUTHORIZED_LOGICAL_PLAN:
        raise IdleSignalApplyError("APPLY_OPERATION_PLAN_INVALID")
    return out


def validate_bootstrap_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate selectors only. Bootstrap truth is re-read from GitHub."""
    if not isinstance(value, Mapping):
        raise IdleSignalApplyError("BOOTSTRAP_EVIDENCE_NOT_OBJECT")
    required = {
        "schema_version",
        "issue",
        "implementation_pr",
        "branch",
        "bootstrap_head",
    }
    if set(value) != required:
        raise IdleSignalApplyError("BOOTSTRAP_EVIDENCE_FIELDS_INVALID")
    if value.get("schema_version") != BOOTSTRAP_EVIDENCE_SCHEMA:
        raise IdleSignalApplyError("BOOTSTRAP_EVIDENCE_SCHEMA_INVALID")
    out = _copy(value)
    _positive_int(out["issue"], "/issue")
    _positive_int(out["implementation_pr"], "/implementation_pr")
    _nonempty(out["branch"], "/branch")
    _sha40(out["bootstrap_head"], "BOOTSTRAP_HEAD_INVALID", "/bootstrap_head")
    return out


def validate_applied_state(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate post-apply selectors only. Canonical truth is re-read live."""
    if not isinstance(value, Mapping):
        raise IdleSignalApplyError("APPLIED_STATE_NOT_OBJECT")
    required = {
        "schema_version",
        "activation_gate_pr",
        "activation_gate_reviewed_head",
        "activation_gate_merge_commit",
        "issue",
        "implementation_pr",
        "branch",
    }
    if set(value) != required:
        raise IdleSignalApplyError("APPLIED_STATE_FIELDS_INVALID")
    if value.get("schema_version") != APPLIED_STATE_SCHEMA:
        raise IdleSignalApplyError("APPLIED_STATE_SCHEMA_INVALID")
    out = _copy(value)
    for field in ("activation_gate_pr", "issue", "implementation_pr"):
        _positive_int(out[field], f"/{field}")
    _nonempty(out["branch"], "/branch")
    for field in ("activation_gate_reviewed_head", "activation_gate_merge_commit"):
        _sha40(out[field], "APPLIED_STATE_SHA_INVALID", f"/{field}")
    return out


def _authorization_identity(
    authorization: Mapping[str, Any], route_epoch: int
) -> dict[str, Any]:
    token = str(authorization["authorization_digest"])[:12].upper()
    return {
        "task_id": f"GPT-IDLE-SIGNAL-AUTO-{token}",
        "route_id": f"GPT-IDLE-SIGNAL-AUTO-ROUTE-{token}",
        "worker_slot_id": f"GPT-WORKER-IDLE-{token}",
        "branch": f"gpt/idle-signal-auto-{token.casefold()}",
        "route_epoch": route_epoch,
        "completion_signal": f"IDLE_SIGNAL_AUTO_{token}_READY_FOR_INDEPENDENT_REVIEW",
    }


def _canonical_route_epochs(root: Path) -> set[int]:
    route_root = root / ROUTES_ROOT
    if not route_root.is_dir():
        raise IdleSignalApplyError("CANONICAL_ROUTE_ROOT_MISSING")
    epochs: set[int] = set()
    for path in sorted(route_root.glob("*.yaml")):
        try:
            doc = load_yaml(path)
        except (OSError, ValueError, TypeError) as exc:
            raise IdleSignalApplyError("CANONICAL_ROUTE_DOCUMENT_INVALID") from exc
        if not isinstance(doc, Mapping):
            raise IdleSignalApplyError("CANONICAL_ROUTE_DOCUMENT_INVALID")
        nested_raw = doc.get("binding")
        if nested_raw is None:
            nested: Mapping[str, Any] = {}
        elif isinstance(nested_raw, Mapping):
            nested = nested_raw
        else:
            raise IdleSignalApplyError("CANONICAL_ROUTE_BINDING_INVALID")
        top = doc.get("route_epoch")
        bound = nested.get("route_epoch")
        if top is not None and bound is not None and top != bound:
            raise IdleSignalApplyError("CANONICAL_ROUTE_EPOCH_AMBIGUOUS")
        value = top if top is not None else bound
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise IdleSignalApplyError("CANONICAL_ROUTE_EPOCH_INVALID")
        epochs.add(value)
    return epochs


def _next_route_epoch(root: Path) -> int:
    epochs = _canonical_route_epochs(root)
    return max(epochs, default=0) + 1


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


def _make_apply_observer(root: Path) -> tuple[Any, type[BaseException]]:
    """Reuse R137 public GitHub observer; extend only fixed coordinator reads."""
    provider_base, gateway_error = _load_r137_provider(root)

    class _ApplyObserver(provider_base):
        def _dynamic_domain_endpoint_allowed(self, path: str) -> bool:
            if _ISSUE_ENDPOINT.fullmatch(path) or _QUEUE_COMMENT_ENDPOINT.fullmatch(path):
                return True
            return super()._dynamic_domain_endpoint_allowed(path)

    return _ApplyObserver(), gateway_error


def _api_json(
    observer: Any,
    gateway_error: type[BaseException],
    path: str,
    code: str,
) -> tuple[Any, Mapping[str, Any]]:
    try:
        _headers, payload, metadata = observer._get_json(path)
    except gateway_error as exc:
        raise IdleSignalApplyError(code) from exc
    return payload, metadata if isinstance(metadata, Mapping) else {}


def _required_bootstrap_markers(
    authorization: Mapping[str, Any],
    opportunity: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, str]:
    return {
        "r151_authorization_id": str(authorization["authorization_id"]),
        "r151_authorization_digest": str(authorization["authorization_digest"]),
        "signal_ref": str(opportunity["signal_ref"]),
        "task_id": str(identity["task_id"]),
    }


def _body_has_markers(body: Any, markers: Mapping[str, str]) -> bool:
    return isinstance(body, str) and all(
        f"{key}: {value}" in body for key, value in markers.items()
    )


def _trusted_bootstrap_observation(
    root: Path,
    selectors: Mapping[str, Any],
    authorization: Mapping[str, Any],
    opportunity: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    observer, gateway_error = _make_apply_observer(root)
    issue_number = int(selectors["issue"])
    pr_number = int(selectors["implementation_pr"])
    branch = str(selectors["branch"])
    bootstrap_head = str(selectors["bootstrap_head"])
    markers = _required_bootstrap_markers(authorization, opportunity, identity)

    issue, issue_meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/issues/{issue_number}",
        "TRUSTED_BOOTSTRAP_ISSUE_READ_FAILED",
    )
    issue = _mapping(issue, "TRUSTED_BOOTSTRAP_ISSUE_INVALID")
    if issue.get("number") != issue_number or issue.get("state") != "open":
        raise IdleSignalApplyError("TRUSTED_BOOTSTRAP_ISSUE_IDENTITY_INVALID")
    if "pull_request" in issue:
        raise IdleSignalApplyError("TRUSTED_BOOTSTRAP_ISSUE_IS_PULL_REQUEST")
    if not _body_has_markers(issue.get("body"), markers):
        raise IdleSignalApplyError("TRUSTED_BOOTSTRAP_ISSUE_MARKERS_MISSING")

    pr, pr_meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/pulls/{pr_number}",
        "TRUSTED_BOOTSTRAP_PR_READ_FAILED",
    )
    pr = _mapping(pr, "TRUSTED_BOOTSTRAP_PR_INVALID")
    base = _mapping(pr.get("base"), "TRUSTED_BOOTSTRAP_PR_BASE_INVALID")
    head = _mapping(pr.get("head"), "TRUSTED_BOOTSTRAP_PR_HEAD_INVALID")
    base_repo = _mapping(base.get("repo"), "TRUSTED_BOOTSTRAP_PR_BASE_REPO_INVALID")
    head_repo = _mapping(head.get("repo"), "TRUSTED_BOOTSTRAP_PR_HEAD_REPO_INVALID")
    if (
        pr.get("number") != pr_number
        or pr.get("state") != "open"
        or pr.get("draft") is not True
        or pr.get("merged") is not False
        or base.get("ref") != "main"
        or base_repo.get("full_name") != COORDINATOR_REPOSITORY
        or head.get("ref") != branch
        or head.get("sha") != bootstrap_head
        or head_repo.get("full_name") != COORDINATOR_REPOSITORY
    ):
        raise IdleSignalApplyError("TRUSTED_BOOTSTRAP_PR_IDENTITY_INVALID")
    if not _body_has_markers(pr.get("body"), markers) or f"#{issue_number}" not in str(
        pr.get("body")
    ):
        raise IdleSignalApplyError("TRUSTED_BOOTSTRAP_PR_MARKERS_MISSING")

    commit, commit_meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{bootstrap_head}",
        "TRUSTED_BOOTSTRAP_COMMIT_READ_FAILED",
    )
    commit = _mapping(commit, "TRUSTED_BOOTSTRAP_COMMIT_INVALID")
    tree = _mapping(commit.get("tree"), "TRUSTED_BOOTSTRAP_TREE_INVALID")
    parents = commit.get("parents")
    if not isinstance(parents, list) or len(parents) != 1 or not isinstance(parents[0], Mapping):
        raise IdleSignalApplyError("TRUSTED_BOOTSTRAP_PARENT_CARDINALITY_INVALID")
    parent_sha = parents[0].get("sha")
    if parent_sha != authorization.get("canonical_main"):
        raise IdleSignalApplyError("TRUSTED_BOOTSTRAP_PARENT_MAIN_MISMATCH")
    parent, parent_meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{parent_sha}",
        "TRUSTED_BOOTSTRAP_PARENT_READ_FAILED",
    )
    parent = _mapping(parent, "TRUSTED_BOOTSTRAP_PARENT_INVALID")
    parent_tree = _mapping(parent.get("tree"), "TRUSTED_BOOTSTRAP_PARENT_TREE_INVALID")
    if _sha40(tree.get("sha"), "TRUSTED_BOOTSTRAP_TREE_SHA_INVALID", "/tree") != _sha40(
        parent_tree.get("sha"),
        "TRUSTED_BOOTSTRAP_PARENT_TREE_SHA_INVALID",
        "/parent_tree",
    ):
        raise IdleSignalApplyError("TRUSTED_BOOTSTRAP_COMMIT_NOT_EMPTY")

    observation = {
        "schema_version": TRUSTED_BOOTSTRAP_SCHEMA,
        "repository": COORDINATOR_REPOSITORY,
        "issue": issue_number,
        "implementation_pr": pr_number,
        "branch": branch,
        "bootstrap_head": bootstrap_head,
        "bootstrap_parent_main": parent_sha,
        "empty_commit_verified": True,
        "draft_pr_verified": True,
        "issue_markers_verified": True,
        "pr_markers_verified": True,
        "provider_metadata": [
            _copy(issue_meta),
            _copy(pr_meta),
            _copy(commit_meta),
            _copy(parent_meta),
        ],
    }
    observation["observation_digest"] = _digest(observation)
    return observation


def _expected_control_documents(
    root: Path,
    lane_id: str,
    replacement_claim: Mapping[str, Any],
    worker_slot: Mapping[str, Any],
) -> dict[str, Any]:
    claims_doc = load_yaml(root / CLAIMS_FILE)
    workers_doc = load_yaml(root / GPT_WORKERS_REGISTRY)
    if not isinstance(claims_doc, Mapping) or not isinstance(workers_doc, Mapping):
        raise IdleSignalApplyError("CONTROL_DOCUMENT_BASELINE_INVALID")
    claims = claims_doc.get("claims")
    slots = workers_doc.get("worker_slots")
    if not isinstance(claims, list) or not isinstance(slots, list):
        raise IdleSignalApplyError("CONTROL_DOCUMENT_BASELINE_INVALID")
    matches = [index for index, item in enumerate(claims) if isinstance(item, Mapping) and item.get("lane_id") == lane_id]
    if len(matches) != 1:
        raise IdleSignalApplyError("CONTROL_DOCUMENT_LANE_CARDINALITY_INVALID")
    if slots:
        raise IdleSignalApplyError("CONTROL_DOCUMENT_WORKER_BASELINE_NOT_EMPTY")
    expected_claims = _copy(claims_doc)
    expected_claims["claims"][matches[0]] = _copy(replacement_claim)
    expected_workers = _copy(workers_doc)
    expected_workers["worker_slots"] = [_copy(worker_slot)]
    return {
        "claims": {
            "path": CLAIMS_FILE,
            "baseline_digest": _digest(claims_doc),
            "expected_document": expected_claims,
            "expected_digest": _digest(expected_claims),
        },
        "workers": {
            "path": GPT_WORKERS_REGISTRY,
            "baseline_digest": _digest(workers_doc),
            "expected_document": expected_workers,
            "expected_digest": _digest(expected_workers),
        },
    }


def _bootstrap_manifest(
    authorization: Mapping[str, Any],
    opportunity: Mapping[str, Any],
    identity: Mapping[str, Any],
    *,
    current_main: str,
) -> dict[str, Any]:
    markers = _required_bootstrap_markers(authorization, opportunity, identity)
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
            "required_body_markers": markers,
        },
        "runtime_pr_bootstrap": {
            "operation": "begin_bounded_engineering",
            "phase": "NON_EXECUTABLE_BOOTSTRAP_ONLY",
            "branch": identity["branch"],
            "branch_parent": current_main,
            "requires_issue_output": True,
            "empty_commit_required": True,
            "file_mutations": [],
            "draft_pr_required": True,
            "required_pr_body_markers": markers,
            "required_pr_issue_reference": "OUTPUT_OF_CREATE_ISSUE",
        },
        "trusted_bootstrap_readback_required": True,
        "deferred_until_trusted_bootstrap_readback": [
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
    root: Path,
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
        "repository": COORDINATOR_REPOSITORY,
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
            "trusted_bootstrap_observation_digest": bootstrap["observation_digest"],
            "bootstrap_head": bootstrap["bootstrap_head"],
        },
        "reviewer_role": intent["reviewer_role"],
        "reviewer_separation": intent["reviewer_separation"],
        "activation_state": "ACTIVE",
        "closure_state": None,
    }
    route_path = f"{ROUTES_ROOT}/{identity['route_id']}.yaml"
    if (root / route_path).exists():
        raise IdleSignalApplyError("DETERMINISTIC_ROUTE_ID_ALREADY_EXISTS")
    control_documents = _expected_control_documents(root, intent["lane_id"], claim, worker_slot)
    value = {
        "schema_version": ACTIVATION_MANIFEST_SCHEMA,
        "status": "ACTIVATION_GATE_CANDIDATE",
        "canonical_main": current_main,
        "authorization_digest": authorization["authorization_digest"],
        "opportunity_digest": opportunity["opportunity_digest"],
        "trusted_bootstrap_observation": _copy(bootstrap),
        "identity": _copy(identity),
        "logical_authorized_plan": list(AUTHORIZED_LOGICAL_PLAN),
        "atomic_control_plane_commit_required": True,
        "partial_apply_forbidden": True,
        "activation_gate": {
            "must_be_separate_pr": True,
            "exact_changed_paths": [route_path, CLAIMS_FILE, GPT_WORKERS_REGISTRY],
            "independent_exact_head_review_required": True,
            "review_queue_issue": REVIEW_QUEUE_ISSUE,
            "merge_requires_expected_head": True,
            "merge_method_required": "merge",
            "execution_effective_only_after_gate_is_canonical": True,
            "post_merge_trusted_readback_required_before_first_implementation_commit": True,
        },
        "route_artifact": {"path": route_path, "payload": route},
        "work_claim_replacement": claim,
        "worker_slot_append": worker_slot,
        "control_plane_documents": control_documents,
        "begin_bounded_engineering": {
            "allowed_only_after_activation_gate_canonical_and_readback_verified": True,
            "implementation_pr": pr,
            "branch": branch,
            "expected_pre_implementation_head": bootstrap["bootstrap_head"],
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
    if presented.get("opportunity_id") != opportunity["opportunity_id"]:
        raise IdleSignalApplyError("AUTHORIZATION_OPPORTUNITY_ID_MISMATCH")
    if presented.get("opportunity_digest") != opportunity["opportunity_digest"]:
        raise IdleSignalApplyError("AUTHORIZATION_OPPORTUNITY_DIGEST_MISMATCH")
    if presented.get("signal_ref") != opportunity["signal_ref"]:
        raise IdleSignalApplyError("AUTHORIZATION_SIGNAL_MISMATCH")

    intent = validate_apply_intent(apply_intent)
    proposal_surface = _normalized_surface(
        opportunity["task_release_proposal"].get("proposed_write_surface"),
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
    next_epoch = _next_route_epoch(root)
    if intent["route_epoch"] != next_epoch:
        raise IdleSignalApplyError("ROUTE_EPOCH_NOT_NEXT_CANONICAL")
    claim = _load_lane_state(root, intent["lane_id"])
    _validate_lane_reopen_rule(claim, intent["release_reason_class"])
    identity = _authorization_identity(presented, next_epoch)
    if bootstrap_evidence is None:
        return _bootstrap_manifest(
            presented, opportunity, identity, current_main=expected_current_main
        )

    selectors = validate_bootstrap_evidence(bootstrap_evidence)
    if selectors["branch"] != identity["branch"]:
        raise IdleSignalApplyError("BOOTSTRAP_BRANCH_MISMATCH")
    bootstrap = _trusted_bootstrap_observation(
        root, selectors, presented, opportunity, identity
    )
    return _activation_manifest(
        root,
        presented,
        opportunity,
        intent,
        identity,
        bootstrap,
        current_main=expected_current_main,
    )


def _blob_yaml_mapping(
    observer: Any,
    gateway_error: type[BaseException],
    blob_sha: str,
    code: str,
) -> dict[str, Any]:
    payload, _meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/git/blobs/{blob_sha}",
        code,
    )
    payload = _mapping(payload, code)
    if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
        raise IdleSignalApplyError(code)
    try:
        raw = b64decode(payload["content"], validate=False).decode("utf-8")
        value = yaml.safe_load(raw)
    except (ValueError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise IdleSignalApplyError(code) from exc
    if not isinstance(value, Mapping):
        raise IdleSignalApplyError(code)
    return dict(value)


def _tree_index(tree_payload: Mapping[str, Any]) -> dict[str, tuple[str, str, str]]:
    if tree_payload.get("truncated") is True:
        raise IdleSignalApplyError("TRUSTED_APPLY_TREE_TRUNCATED")
    entries = tree_payload.get("tree")
    if not isinstance(entries, list):
        raise IdleSignalApplyError("TRUSTED_APPLY_TREE_INVALID")
    out: dict[str, tuple[str, str, str]] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        path, sha, kind, mode = (
            entry.get("path"),
            entry.get("sha"),
            entry.get("type"),
            entry.get("mode"),
        )
        if all(isinstance(item, str) for item in (path, sha, kind, mode)):
            out[path] = (sha, kind, mode)
    return out


def _changed_paths(
    base_tree: Mapping[str, tuple[str, str, str]],
    head_tree: Mapping[str, tuple[str, str, str]],
) -> set[str]:
    return {
        path
        for path in set(base_tree) | set(head_tree)
        if base_tree.get(path) != head_tree.get(path)
    }


def _one_matching(items: Any, *, key: str, expected: Any, code: str) -> dict[str, Any]:
    if not isinstance(items, list):
        raise IdleSignalApplyError(code)
    matches = [
        item for item in items if isinstance(item, Mapping) and item.get(key) == expected
    ]
    if len(matches) != 1:
        raise IdleSignalApplyError(code)
    return dict(matches[0])


def _trusted_exact_head_acceptance(
    root: Path, pr_number: int, reviewed_head: str
) -> dict[str, Any]:
    observer, gateway_error = _make_apply_observer(root)
    events: list[dict[str, Any]] = []
    latest_request: dict[str, Any] | None = None
    queue_refs: list[str] = []
    pagination_complete = False
    for page in range(1, MAX_REVIEW_QUEUE_PAGES + 1):
        payload, _meta = _api_json(
            observer,
            gateway_error,
            f"/repos/{COORDINATOR_REPOSITORY}/issues/{REVIEW_QUEUE_ISSUE}/comments?per_page=100&page={page}",
            "TRUSTED_REVIEW_QUEUE_READ_FAILED",
        )
        if not isinstance(payload, list):
            raise IdleSignalApplyError("TRUSTED_REVIEW_QUEUE_PAYLOAD_INVALID")
        for raw in payload:
            if not isinstance(raw, Mapping) or not isinstance(raw.get("body"), str) or not isinstance(raw.get("id"), int):
                raise IdleSignalApplyError("TRUSTED_REVIEW_QUEUE_COMMENT_INVALID")
            body = str(raw["body"])
            if _queue_field(body, "project") != "SECOND_BRAIN":
                continue
            try:
                event_pr = int(_queue_field(body, "pr") or "")
            except ValueError as exc:
                raise IdleSignalApplyError("TRUSTED_REVIEW_QUEUE_PR_INVALID") from exc
            if event_pr != pr_number:
                continue
            schema = _queue_field(body, "schema")
            ref = str(raw.get("html_url") or f"github://{COORDINATOR_REPOSITORY}/issues/{REVIEW_QUEUE_ISSUE}#comment={raw['id']}")
            if schema == "REVIEW_REQUEST/v1":
                head = _queue_field(body, "exact_head")
                if head is None or not _SHA40.fullmatch(head):
                    raise IdleSignalApplyError("TRUSTED_REVIEW_QUEUE_HEAD_INVALID")
                event = {
                    "comment_id": raw["id"],
                    "schema": schema,
                    "head": head,
                    "status": _queue_field(body, "status"),
                    "evidence_ref": ref,
                }
                if event["status"] != "WAITING_REVIEW":
                    raise IdleSignalApplyError("TRUSTED_REVIEW_QUEUE_STATUS_INVALID")
                if latest_request is None or event["comment_id"] > latest_request["comment_id"]:
                    latest_request = event
                if head == reviewed_head:
                    events.append(event)
                    queue_refs.append(ref)
            elif schema == "REVIEW_RESULT/v1":
                head = _queue_field(body, "reviewed_head")
                if head is None or not _SHA40.fullmatch(head):
                    raise IdleSignalApplyError("TRUSTED_REVIEW_QUEUE_HEAD_INVALID")
                if head != reviewed_head:
                    continue
                event = {
                    "comment_id": raw["id"],
                    "schema": schema,
                    "head": head,
                    "verdict": _queue_field(body, "verdict"),
                    "review_evidence_ref": _queue_field(body, "review_evidence_ref"),
                    "review_channel": _queue_field(body, "review_channel"),
                    "reviewer_agent_id": _queue_field(body, "reviewer_agent_id"),
                    "independence_attestation": _queue_field(body, "independence_attestation"),
                    "evidence_ref": ref,
                }
                events.append(event)
                queue_refs.append(ref)
        if len(payload) < 100:
            pagination_complete = True
            break
    if not pagination_complete:
        raise IdleSignalApplyError("TRUSTED_REVIEW_QUEUE_PAGINATION_INCOMPLETE")
    if latest_request is None or latest_request["head"] != reviewed_head:
        raise IdleSignalApplyError("TRUSTED_REVIEW_LATEST_REQUEST_HEAD_MISMATCH")
    if not events:
        raise IdleSignalApplyError("TRUSTED_REVIEW_TICKET_MISSING")
    latest = max(events, key=lambda item: int(item["comment_id"]))
    if latest.get("schema") != "REVIEW_RESULT/v1" or latest.get("verdict") != "ACCEPT":
        raise IdleSignalApplyError("TRUSTED_REVIEW_EXACT_HEAD_NOT_ACCEPTED")
    if latest.get("review_channel") not in {
        "GITHUB_APPROVE",
        "EXACT_HEAD_COMMENT_ATTESTATION",
    }:
        raise IdleSignalApplyError("TRUSTED_REVIEW_CHANNEL_INVALID")
    if latest.get("reviewer_agent_id") != REVIEWER_ROLE:
        raise IdleSignalApplyError("TRUSTED_REVIEWER_ROLE_INVALID")
    if latest.get("independence_attestation") != INDEPENDENCE_ATTESTATION:
        raise IdleSignalApplyError("TRUSTED_REVIEW_INDEPENDENCE_ATTESTATION_INVALID")
    review_ref = latest.get("review_evidence_ref")
    if not isinstance(review_ref, str) or not review_ref.strip():
        raise IdleSignalApplyError("TRUSTED_REVIEW_EVIDENCE_REF_MISSING")
    ids = re.findall(r"[0-9]+", review_ref)
    if not ids:
        raise IdleSignalApplyError("TRUSTED_REVIEW_EVIDENCE_ID_UNRESOLVED")
    expected_review_id = int(ids[-1])
    expected_state = (
        "APPROVED"
        if latest["review_channel"] == "GITHUB_APPROVE"
        else "COMMENTED"
    )

    matching_review: Mapping[str, Any] | None = None
    review_pagination_complete = False
    for page in range(1, MAX_REVIEW_QUEUE_PAGES + 1):
        payload, _meta = _api_json(
            observer,
            gateway_error,
            f"/repos/{COORDINATOR_REPOSITORY}/pulls/{pr_number}/reviews?per_page=100&page={page}",
            "TRUSTED_PR_REVIEWS_READ_FAILED",
        )
        if not isinstance(payload, list):
            raise IdleSignalApplyError("TRUSTED_PR_REVIEWS_PAYLOAD_INVALID")
        for raw in payload:
            if not isinstance(raw, Mapping):
                raise IdleSignalApplyError("TRUSTED_PR_REVIEW_INVALID")
            if (
                raw.get("id") == expected_review_id
                and raw.get("commit_id") == reviewed_head
                and str(raw.get("state", "")).upper() == expected_state
            ):
                matching_review = raw
        if len(payload) < 100:
            review_pagination_complete = True
            break
    if not review_pagination_complete:
        raise IdleSignalApplyError("TRUSTED_PR_REVIEWS_PAGINATION_INCOMPLETE")
    if matching_review is None:
        raise IdleSignalApplyError("TRUSTED_PR_REVIEW_EVIDENCE_MISMATCH")

    result = {
        "queue_issue": REVIEW_QUEUE_ISSUE,
        "pr": pr_number,
        "reviewed_head": reviewed_head,
        "verdict": "ACCEPT",
        "review_channel": latest["review_channel"],
        "reviewer_agent_id": REVIEWER_ROLE,
        "independence_attestation": INDEPENDENCE_ATTESTATION,
        "queue_result_comment_id": latest["comment_id"],
        "queue_result_ref": latest["evidence_ref"],
        "review_evidence_ref": review_ref,
        "review_submission_id": expected_review_id,
        "review_submission_state": expected_state,
        "queue_refs": sorted(set(queue_refs)),
    }
    result["acceptance_digest"] = _digest(result)
    return result


def _trusted_post_apply_observation(
    root: Path,
    manifest: Mapping[str, Any],
    selectors: Mapping[str, Any],
) -> dict[str, Any]:
    observer, gateway_error = _make_apply_observer(root)
    merge_commit = str(selectors["activation_gate_merge_commit"])
    reviewed_head = str(selectors["activation_gate_reviewed_head"])
    activation_pr = int(selectors["activation_gate_pr"])
    acceptance = _trusted_exact_head_acceptance(root, activation_pr, reviewed_head)

    main_ref, main_meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/git/ref/heads/main",
        "TRUSTED_APPLY_MAIN_READ_FAILED",
    )
    main_ref = _mapping(main_ref, "TRUSTED_APPLY_MAIN_INVALID")
    main_object = _mapping(main_ref.get("object"), "TRUSTED_APPLY_MAIN_OBJECT_INVALID")
    if main_object.get("sha") != merge_commit:
        raise IdleSignalApplyError("TRUSTED_APPLY_CURRENT_MAIN_MISMATCH")

    gate_pr, gate_pr_meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/pulls/{activation_pr}",
        "TRUSTED_APPLY_GATE_PR_READ_FAILED",
    )
    gate_pr = _mapping(gate_pr, "TRUSTED_APPLY_GATE_PR_INVALID")
    gate_base = _mapping(gate_pr.get("base"), "TRUSTED_APPLY_GATE_BASE_INVALID")
    gate_head = _mapping(gate_pr.get("head"), "TRUSTED_APPLY_GATE_HEAD_INVALID")
    gate_head_repo = _mapping(gate_head.get("repo"), "TRUSTED_APPLY_GATE_HEAD_REPO_INVALID")
    if (
        gate_pr.get("number") != activation_pr
        or gate_pr.get("state") != "closed"
        or gate_pr.get("merged") is not True
        or gate_pr.get("draft") is not False
        or gate_pr.get("merge_commit_sha") != merge_commit
        or gate_base.get("ref") != "main"
        or gate_head.get("sha") != reviewed_head
        or gate_head_repo.get("full_name") != COORDINATOR_REPOSITORY
    ):
        raise IdleSignalApplyError("TRUSTED_APPLY_GATE_PR_IDENTITY_INVALID")

    merge, merge_meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{merge_commit}",
        "TRUSTED_APPLY_MERGE_COMMIT_READ_FAILED",
    )
    merge = _mapping(merge, "TRUSTED_APPLY_MERGE_COMMIT_INVALID")
    parents = merge.get("parents")
    if (
        not isinstance(parents, list)
        or len(parents) != 2
        or not all(isinstance(item, Mapping) for item in parents)
        or parents[0].get("sha") != manifest.get("canonical_main")
        or parents[1].get("sha") != reviewed_head
    ):
        raise IdleSignalApplyError("TRUSTED_APPLY_MERGE_PARENT_BINDING_INVALID")
    merge_tree = _mapping(merge.get("tree"), "TRUSTED_APPLY_MERGE_TREE_INVALID")
    merge_tree_sha = _sha40(
        merge_tree.get("sha"), "TRUSTED_APPLY_MERGE_TREE_SHA_INVALID", "/merge/tree"
    )

    base_commit, base_commit_meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{manifest['canonical_main']}",
        "TRUSTED_APPLY_BASE_COMMIT_READ_FAILED",
    )
    reviewed_commit, reviewed_commit_meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{reviewed_head}",
        "TRUSTED_APPLY_REVIEWED_COMMIT_READ_FAILED",
    )
    base_commit = _mapping(base_commit, "TRUSTED_APPLY_BASE_COMMIT_INVALID")
    reviewed_commit = _mapping(reviewed_commit, "TRUSTED_APPLY_REVIEWED_COMMIT_INVALID")
    base_tree_sha = _sha40(
        _mapping(base_commit.get("tree"), "TRUSTED_APPLY_BASE_TREE_INVALID").get("sha"),
        "TRUSTED_APPLY_BASE_TREE_SHA_INVALID",
        "/base/tree",
    )
    reviewed_tree_sha = _sha40(
        _mapping(reviewed_commit.get("tree"), "TRUSTED_APPLY_REVIEWED_TREE_INVALID").get("sha"),
        "TRUSTED_APPLY_REVIEWED_TREE_SHA_INVALID",
        "/reviewed/tree",
    )
    if reviewed_tree_sha != merge_tree_sha:
        raise IdleSignalApplyError("TRUSTED_APPLY_MERGE_TREE_NOT_REVIEWED_TREE")

    base_tree_payload, base_tree_meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/git/trees/{base_tree_sha}?recursive=1",
        "TRUSTED_APPLY_BASE_TREE_READ_FAILED",
    )
    reviewed_tree_payload, reviewed_tree_meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/git/trees/{reviewed_tree_sha}?recursive=1",
        "TRUSTED_APPLY_REVIEWED_TREE_READ_FAILED",
    )
    base_index = _tree_index(_mapping(base_tree_payload, "TRUSTED_APPLY_BASE_TREE_INVALID"))
    reviewed_index = _tree_index(_mapping(reviewed_tree_payload, "TRUSTED_APPLY_REVIEWED_TREE_INVALID"))
    expected_paths = set(
        _mapping(manifest.get("activation_gate"), "TRUSTED_APPLY_GATE_MANIFEST_MISSING").get(
            "exact_changed_paths", []
        )
    )
    if _changed_paths(base_index, reviewed_index) != expected_paths:
        raise IdleSignalApplyError("TRUSTED_APPLY_GATE_CHANGED_PATH_SET_MISMATCH")

    implementation_pr = int(selectors["implementation_pr"])
    implementation, implementation_meta = _api_json(
        observer,
        gateway_error,
        f"/repos/{COORDINATOR_REPOSITORY}/pulls/{implementation_pr}",
        "TRUSTED_APPLY_IMPLEMENTATION_PR_READ_FAILED",
    )
    implementation = _mapping(implementation, "TRUSTED_APPLY_IMPLEMENTATION_PR_INVALID")
    implementation_head = _mapping(
        implementation.get("head"), "TRUSTED_APPLY_IMPLEMENTATION_HEAD_INVALID"
    )
    bootstrap = _mapping(
        manifest.get("trusted_bootstrap_observation"),
        "TRUSTED_APPLY_BOOTSTRAP_OBSERVATION_MISSING",
    )
    if (
        implementation.get("number") != implementation_pr
        or implementation.get("state") != "open"
        or implementation.get("draft") is not True
        or implementation.get("merged") is not False
        or implementation_head.get("ref") != selectors["branch"]
        or implementation_head.get("sha") != bootstrap.get("bootstrap_head")
    ):
        raise IdleSignalApplyError("TRUSTED_APPLY_IMPLEMENTATION_PR_DRIFT")

    route_artifact = _mapping(
        manifest.get("route_artifact"), "TRUSTED_APPLY_ROUTE_MANIFEST_MISSING"
    )
    route_path = route_artifact.get("path")
    if not isinstance(route_path, str) or route_path not in reviewed_index:
        raise IdleSignalApplyError("TRUSTED_APPLY_ROUTE_MISSING_FROM_MAIN")
    for path in (CLAIMS_FILE, GPT_WORKERS_REGISTRY):
        if path not in reviewed_index:
            raise IdleSignalApplyError("TRUSTED_APPLY_CONTROL_OBJECT_MISSING_FROM_MAIN")

    route_doc = _blob_yaml_mapping(
        observer,
        gateway_error,
        reviewed_index[route_path][0],
        "TRUSTED_APPLY_ROUTE_BLOB_INVALID",
    )
    claims_doc = _blob_yaml_mapping(
        observer,
        gateway_error,
        reviewed_index[CLAIMS_FILE][0],
        "TRUSTED_APPLY_CLAIMS_BLOB_INVALID",
    )
    workers_doc = _blob_yaml_mapping(
        observer,
        gateway_error,
        reviewed_index[GPT_WORKERS_REGISTRY][0],
        "TRUSTED_APPLY_WORKERS_BLOB_INVALID",
    )
    if route_doc != route_artifact.get("payload"):
        raise IdleSignalApplyError("TRUSTED_APPLY_ROUTE_PAYLOAD_MISMATCH")
    control_docs = _mapping(
        manifest.get("control_plane_documents"),
        "TRUSTED_APPLY_CONTROL_DOCUMENT_MANIFEST_MISSING",
    )
    claims_spec = _mapping(control_docs.get("claims"), "TRUSTED_APPLY_CLAIMS_SPEC_MISSING")
    workers_spec = _mapping(control_docs.get("workers"), "TRUSTED_APPLY_WORKERS_SPEC_MISSING")
    if claims_doc != claims_spec.get("expected_document") or _digest(claims_doc) != claims_spec.get("expected_digest"):
        raise IdleSignalApplyError("TRUSTED_APPLY_CLAIMS_FULL_DOCUMENT_MISMATCH")
    if workers_doc != workers_spec.get("expected_document") or _digest(workers_doc) != workers_spec.get("expected_digest"):
        raise IdleSignalApplyError("TRUSTED_APPLY_WORKERS_FULL_DOCUMENT_MISMATCH")

    observation = {
        "schema_version": TRUSTED_APPLIED_STATE_SCHEMA,
        "base_main_before_activation": manifest["canonical_main"],
        "activation_gate_pr": activation_pr,
        "activation_gate_reviewed_head": reviewed_head,
        "activation_gate_merge_commit": merge_commit,
        "current_main_after_activation": merge_commit,
        "merge_parents": [parents[0].get("sha"), parents[1].get("sha")],
        "independent_review_acceptance": acceptance,
        "activation_changed_paths": sorted(expected_paths),
        "implementation_issue": selectors["issue"],
        "implementation_pr": implementation_pr,
        "branch": selectors["branch"],
        "implementation_head_still_bootstrap": True,
        "route_readback_verified": True,
        "full_claims_document_readback_verified": True,
        "full_worker_registry_readback_verified": True,
        "provider_metadata": [
            _copy(main_meta),
            _copy(gate_pr_meta),
            _copy(merge_meta),
            _copy(base_commit_meta),
            _copy(reviewed_commit_meta),
            _copy(base_tree_meta),
            _copy(reviewed_tree_meta),
            _copy(implementation_meta),
        ],
    }
    observation["observation_digest"] = _digest(observation)
    return observation


def verify_applied_state(
    repo_root: str | Path,
    manifest: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    """Fresh-read post-activation canonical state. Receipt remains evidence-only."""
    root = Path(repo_root).resolve()
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != ACTIVATION_MANIFEST_SCHEMA:
        raise IdleSignalApplyError("ACTIVATION_MANIFEST_REQUIRED")
    expected_digest = manifest.get("manifest_digest")
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise IdleSignalApplyError("ACTIVATION_MANIFEST_DIGEST_INVALID")
    basis = dict(_copy(manifest))
    basis.pop("manifest_digest", None)
    if _digest(basis) != expected_digest:
        raise IdleSignalApplyError("ACTIVATION_MANIFEST_DIGEST_FORGED")

    selectors = validate_applied_state(observed)
    bootstrap = _mapping(
        manifest.get("trusted_bootstrap_observation"),
        "TRUSTED_APPLY_BOOTSTRAP_OBSERVATION_MISSING",
    )
    for field, expected in {
        "issue": bootstrap.get("issue"),
        "implementation_pr": bootstrap.get("implementation_pr"),
        "branch": bootstrap.get("branch"),
    }.items():
        if selectors.get(field) != expected:
            raise IdleSignalApplyError("APPLIED_IDENTITY_MISMATCH", f"/{field}")

    trusted = _trusted_post_apply_observation(root, manifest, selectors)
    acceptance = _mapping(
        trusted.get("independent_review_acceptance"),
        "TRUSTED_APPLY_REVIEW_ACCEPTANCE_MISSING",
    )
    receipt = {
        "schema_version": APPLY_RECEIPT_SCHEMA,
        "manifest_digest": expected_digest,
        "trusted_observation_digest": trusted["observation_digest"],
        "base_main_before_activation": trusted["base_main_before_activation"],
        "activation_gate_pr": trusted["activation_gate_pr"],
        "activation_gate_reviewed_head": trusted["activation_gate_reviewed_head"],
        "activation_gate_merge_commit": trusted["activation_gate_merge_commit"],
        "current_main_after_activation": trusted["current_main_after_activation"],
        "review_acceptance_digest": acceptance["acceptance_digest"],
        "review_channel": acceptance["review_channel"],
        "review_evidence_ref": acceptance["review_evidence_ref"],
        "implementation_issue": trusted["implementation_issue"],
        "implementation_pr": trusted["implementation_pr"],
        "branch": trusted["branch"],
        "identity": _copy(manifest["identity"]),
        "verification": {
            "current_main_is_activation_merge_commit": True,
            "merge_parent_1_is_base_main": True,
            "merge_parent_2_is_reviewed_head": True,
            "exact_head_independent_accept_verified": True,
            "activation_changed_paths_exact": True,
            "implementation_pr_still_at_empty_bootstrap_head": True,
            "exact_route_readback": True,
            "full_claims_document_readback": True,
            "full_worker_registry_readback": True,
            "trusted_provider_readback": True,
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
