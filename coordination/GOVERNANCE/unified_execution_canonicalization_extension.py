"""Canonicalization effect-isolation contracts.

Pure, side-effect-free validation for canonicalizer identity/capability admission,
pre-merge effect fencing, post-effect reconciliation, and prospective PR #615
adjudication. This module never calls GitHub, never performs a merge, and never
mints merge permission. A protected carrier must authenticate the evidence that
enters these validators.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any, Iterable, Mapping

try:
    ExecutionContractError
except NameError:  # standalone focused tests
    class ExecutionContractError(ValueError):
        pass

_CANONICALIZATION_ISSUER = object()

CANONICALIZATION_STATES = (
    "REVIEW_ACCEPTED",
    "SELECT_ELIGIBLE_CANONICALIZER",
    "ROLE_AND_CAPABILITY_ADMISSION",
    "FRESH_CANONICALIZATION_GATES",
    "MERGE_REQUESTED",
    "REMOTE_EFFECT_RECONCILED",
    "CANONICALIZATION_RECORDED",
)
CANONICALIZATION_EFFECT_CORE_HAS_GITHUB_SIDE_EFFECTS = False
CANONICALIZATION_EFFECT_CORE_CAN_MINT_MERGE_AUTHORITY = False

CANONICALIZATION_FAILURE_STATES = {
    "INDEPENDENCE_CONFLICT",
    "CANONICALIZER_WRITE_UNAVAILABLE",
    "RUNTIME_MODE_DISALLOWS_MERGE",
    "CANONICALIZATION_AUTHORITY_MISSING",
    "NO_ELIGIBLE_CANONICALIZER",
    "HEAD_DRIFT",
    "BASE_OR_POLICY_DRIFT",
    "CI_OR_REVIEW_IDENTITY_MISMATCH",
    "MERGE_EFFECT_UNKNOWN",
    "LEASE_OR_FENCING_INVALID",
    "MERGE_ACTOR_MISMATCH",
    "MERGED_WITH_UNEXPECTED_BASE_OR_TREE",
    "OWNER_GATE_REQUIRED",
}

_ACCEPTED_REVIEW_VERDICTS = {"ACCEPT", "ACCEPT_WITH_BOUNDED_NONBLOCKING_FINDINGS"}
_TRUSTED_INDEPENDENCE_EVIDENCE = {
    "PROTECTED_WORKLOAD_IDENTITY",
    "GOVERNED_SESSION_ATTESTATION",
    "SEPARATE_GITHUB_APP_IDENTITY",
}
_TRUSTED_CAPABILITY_EVIDENCE = {
    "PROTECTED_CAPABILITY_PROBE",
    "GITHUB_INSTALLATION_SCOPE_ATTESTATION",
    "GOVERNED_MERGE_ADAPTER_ATTESTATION",
}
_DISALLOWED_MERGE_RUNTIME_MODES = {"READ_ONLY", "PLAN_ONLY", "REVIEW_ONLY"}


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, set):
        return frozenset(_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_freeze(v) for v in value)
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_jsonable(v) for v in value]
    return value


def _json_digest(value: Any) -> str:
    raw = json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _require(mapping: Mapping[str, Any], fields: Iterable[str], label: str) -> None:
    missing = [field for field in fields if field not in mapping]
    if missing:
        raise ExecutionContractError(f"{label}: missing required fields: {', '.join(missing)}")


def _nonempty(value: Any, label: str) -> str:
    text = str(value).strip()
    if not text:
        raise ExecutionContractError(f"{label}: value must be non-empty")
    return text


def _sha40(value: Any, label: str) -> str:
    text = _nonempty(value, label).lower()
    if len(text) != 40 or any(ch not in "0123456789abcdef" for ch in text):
        raise ExecutionContractError(f"{label}: expected 40-char git sha")
    return text


def build_contributor_conflict_set(*identity_groups: Iterable[str]) -> frozenset[str]:
    """Aggregate author/executor/contributor/orchestrator/effect identities.

    Empty identities fail closed because silently omitting an identity can manufacture
    independence. Reopening a session or renaming a role is not a conflict reset.
    """
    values: set[str] = set()
    for group in identity_groups:
        for raw in group:
            values.add(_nonempty(raw, "contributor_identity"))
    if not values:
        raise ExecutionContractError("contributor_set: at least one contributor identity is required")
    return frozenset(values)


@dataclass(frozen=True)
class VerifiedCanonicalizerEvidence:
    _payload: Mapping[str, Any]
    _issuer: object

    def as_mapping(self) -> Mapping[str, Any]:
        if self._issuer is not _CANONICALIZATION_ISSUER:
            raise ExecutionContractError("canonicalizer_evidence: untrusted issuer")
        return self._payload


@dataclass(frozen=True)
class CanonicalizerAdmission:
    _payload: Mapping[str, Any]
    _issuer: object

    def as_mapping(self) -> Mapping[str, Any]:
        if self._issuer is not _CANONICALIZATION_ISSUER:
            raise ExecutionContractError("canonicalizer_admission: untrusted issuer")
        return self._payload


def _issue_verified_canonicalizer_evidence(
    payload: Mapping[str, Any],
) -> VerifiedCanonicalizerEvidence:
    """Protected-adapter/test hook, not an authority source by itself.

    Production callers must populate it only after fresh protected identity/capability
    evidence is authenticated. The object is an immutable projection, not permission.
    """
    return VerifiedCanonicalizerEvidence(_freeze(dict(payload)), _CANONICALIZATION_ISSUER)


def _evidence_mapping(evidence: VerifiedCanonicalizerEvidence) -> Mapping[str, Any]:
    if not isinstance(evidence, VerifiedCanonicalizerEvidence):
        raise ExecutionContractError(
            "canonicalizer_evidence: caller-supplied mapping/boolean/digest is not trusted evidence"
        )
    return evidence.as_mapping()


def _admission_mapping(admission: CanonicalizerAdmission) -> Mapping[str, Any]:
    if not isinstance(admission, CanonicalizerAdmission):
        raise ExecutionContractError(
            "canonicalizer_admission: caller-supplied mapping is not a verified admission"
        )
    return admission.as_mapping()


def admit_canonicalizer(
    evidence: VerifiedCanonicalizerEvidence,
    contributor_conflict_set: Iterable[str],
) -> CanonicalizerAdmission:
    payload = dict(_evidence_mapping(evidence))
    _require(
        payload,
        (
            "repository", "pull_request", "exact_head_sha",
            "canonicalizer_identity", "session_or_workload_identity", "carrier",
            "runtime_mode", "independence_evidence_source", "capability_evidence_source",
            "merge_write_capable", "github_principal", "allowed_github_actors",
            "permission_policy_digest", "fencing_identity", "observed_at",
        ),
        "canonicalizer_evidence",
    )
    _sha40(payload["exact_head_sha"], "canonicalizer_evidence.exact_head_sha")
    _nonempty(payload["repository"], "canonicalizer_evidence.repository")
    if int(payload["pull_request"]) <= 0:
        raise ExecutionContractError("canonicalizer_evidence.pull_request: must be positive")

    if payload["independence_evidence_source"] not in _TRUSTED_INDEPENDENCE_EVIDENCE:
        raise ExecutionContractError(
            "canonicalizer_evidence: independence evidence source is not trusted"
        )
    if payload["capability_evidence_source"] not in _TRUSTED_CAPABILITY_EVIDENCE:
        raise ExecutionContractError(
            "canonicalizer_evidence: capability evidence source is not trusted"
        )
    if payload["runtime_mode"] in _DISALLOWED_MERGE_RUNTIME_MODES:
        raise ExecutionContractError("RUNTIME_MODE_DISALLOWS_MERGE")
    if payload["merge_write_capable"] is not True:
        raise ExecutionContractError("CANONICALIZER_WRITE_UNAVAILABLE")

    conflicts = {str(item).strip() for item in contributor_conflict_set}
    if not conflicts or "" in conflicts:
        raise ExecutionContractError("contributor_set: invalid or empty conflict identity")
    candidate_identities = {
        str(payload["canonicalizer_identity"]),
        str(payload["session_or_workload_identity"]),
        str(payload["github_principal"]),
    }
    if candidate_identities & conflicts:
        raise ExecutionContractError("INDEPENDENCE_CONFLICT")

    allowed_actors = tuple(str(v).strip() for v in payload["allowed_github_actors"])
    if not allowed_actors or any(not v for v in allowed_actors):
        raise ExecutionContractError(
            "canonicalizer_evidence: allowed_github_actors must be non-empty"
        )
    if str(payload["github_principal"]) not in set(allowed_actors):
        raise ExecutionContractError(
            "canonicalizer_evidence: github_principal must be represented in allowed_github_actors"
        )

    payload["contributor_conflict_set_digest"] = _json_digest(sorted(conflicts))
    payload["admission_status"] = "ROLE_AND_CAPABILITY_ADMISSION"
    payload["admission_digest"] = _json_digest(
        {k: v for k, v in payload.items() if k != "admission_digest"}
    )
    return CanonicalizerAdmission(_freeze(payload), _CANONICALIZATION_ISSUER)


def canonicalization_state_transition(current_state: str, event: str) -> str:
    transitions = {
        ("REVIEW_ACCEPTED", "SELECT"): "SELECT_ELIGIBLE_CANONICALIZER",
        ("SELECT_ELIGIBLE_CANONICALIZER", "ADMIT"): "ROLE_AND_CAPABILITY_ADMISSION",
        ("ROLE_AND_CAPABILITY_ADMISSION", "GATES_PASS"): "FRESH_CANONICALIZATION_GATES",
        ("FRESH_CANONICALIZATION_GATES", "REQUEST_MERGE"): "MERGE_REQUESTED",
        ("MERGE_REQUESTED", "EFFECT_READBACK"): "REMOTE_EFFECT_RECONCILED",
        ("REMOTE_EFFECT_RECONCILED", "RECORD"): "CANONICALIZATION_RECORDED",
    }
    next_state = transitions.get((current_state, event))
    if next_state is None:
        raise ExecutionContractError(
            f"canonicalization_state: illegal transition {current_state!r} + {event!r}"
        )
    return next_state


def canonicalizer_failure_recovery(failure_state: str) -> str:
    if failure_state not in CANONICALIZATION_FAILURE_STATES:
        raise ExecutionContractError(f"canonicalization_failure: unknown state {failure_state}")
    recovery = {
        "CANONICALIZER_WRITE_UNAVAILABLE":
            "FENCE_OR_READBACK_OLD_ATTEMPT_THEN_SELECT_ANOTHER_ALREADY_AUTHORIZED_INDEPENDENT_CARRIER",
        "RUNTIME_MODE_DISALLOWS_MERGE":
            "SELECT_ANOTHER_ALREADY_AUTHORIZED_INDEPENDENT_CARRIER_AND_FRESH_ADMIT",
        "NO_ELIGIBLE_CANONICALIZER": "PERSIST_WAIT_NO_AUTHOR_OR_ORCHESTRATOR_FALLBACK",
        "MERGE_EFFECT_UNKNOWN": "READBACK_REMOTE_EFFECT_BEFORE_ANY_RETRY",
        "HEAD_DRIFT": "INVALIDATE_OLD_REVIEW_AND_ADMISSION_REBUILD_EXACT_HEAD_EVIDENCE",
        "BASE_OR_POLICY_DRIFT": "REBUILD_FRESH_CANONICALIZATION_GATES",
        "MERGE_ACTOR_MISMATCH": "PRESERVE_PHYSICAL_EFFECT_AND_REGISTER_GOVERNANCE_INCIDENT",
        "MERGED_WITH_UNEXPECTED_BASE_OR_TREE": "INDEPENDENT_ADJUDICATION_NO_CLEAN_RECEIPT",
        "LEASE_OR_FENCING_INVALID": "REJECT_LATE_OR_STALE_ATTEMPT",
        "INDEPENDENCE_CONFLICT": "SELECT_CANONICALIZER_OUTSIDE_CONTRIBUTOR_SET",
        "CANONICALIZATION_AUTHORITY_MISSING": "PERSIST_WAIT_FOR_GOVERNED_AUTHORITY",
        "CI_OR_REVIEW_IDENTITY_MISMATCH": "REJECT_AND_REBUILD_EXACT_BOUND_EVIDENCE",
        "OWNER_GATE_REQUIRED": "WAIT_FOR_EXPLICIT_OWNER_PERMISSION_OR_POLICY_DECISION",
    }
    return recovery[failure_state]


def validate_pre_merge_effect_gate(
    request: Mapping[str, Any],
    admission: CanonicalizerAdmission,
    review_evidence: Mapping[str, Any],
    ci_evidence: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    admitted = _admission_mapping(admission)
    _require(
        request,
        (
            "repository", "pull_request", "exact_head_sha", "fresh_main_sha",
            "observed_base_sha", "candidate_tree_sha", "operation_id", "attempt_id",
            "fencing_identity", "head_lock_semantics", "review_required", "ci_required",
        ),
        "canonicalization_request",
    )
    exact_head = _sha40(request["exact_head_sha"], "canonicalization_request.exact_head_sha")
    fresh_main = _sha40(request["fresh_main_sha"], "canonicalization_request.fresh_main_sha")
    observed_base = _sha40(
        request["observed_base_sha"], "canonicalization_request.observed_base_sha"
    )
    candidate_tree = _sha40(
        request["candidate_tree_sha"], "canonicalization_request.candidate_tree_sha"
    )
    if fresh_main != observed_base:
        raise ExecutionContractError("BASE_OR_POLICY_DRIFT")
    if request["head_lock_semantics"] != "HEAD_ONLY_NOT_BASE_CAS":
        raise ExecutionContractError(
            "canonicalization_request: merge head lock must not be represented as base+head atomic CAS"
        )
    for field in ("repository", "pull_request", "fencing_identity"):
        if str(request[field]) != str(admitted[field]):
            raise ExecutionContractError(f"canonicalization_request: admission mismatch: {field}")
    if exact_head != str(admitted["exact_head_sha"]):
        raise ExecutionContractError("HEAD_DRIFT")

    if request["review_required"] is not True:
        raise ExecutionContractError("canonicalization_request: independent review must be required")
    _require(review_evidence, ("reviewed_head", "verdict", "review_evidence_ref"), "review_evidence")
    if _sha40(review_evidence["reviewed_head"], "review_evidence.reviewed_head") != exact_head:
        raise ExecutionContractError("CI_OR_REVIEW_IDENTITY_MISMATCH")
    if review_evidence["verdict"] not in _ACCEPTED_REVIEW_VERDICTS:
        raise ExecutionContractError("CI_OR_REVIEW_IDENTITY_MISMATCH")

    if request["ci_required"] is True:
        if ci_evidence is None:
            raise ExecutionContractError("CI_OR_REVIEW_IDENTITY_MISMATCH")
        _require(ci_evidence, ("actual_checkout_sha", "result", "audit_status"), "ci_evidence")
        if _sha40(ci_evidence["actual_checkout_sha"], "ci_evidence.actual_checkout_sha") != exact_head:
            raise ExecutionContractError("CI_OR_REVIEW_IDENTITY_MISMATCH")
        if ci_evidence["result"] not in {"PASS", "SUCCESS"} or ci_evidence["audit_status"] != "AUTHORITATIVE":
            raise ExecutionContractError("CI_OR_REVIEW_IDENTITY_MISMATCH")
    elif ci_evidence is not None and "actual_checkout_sha" in ci_evidence:
        if _sha40(ci_evidence["actual_checkout_sha"], "ci_evidence.actual_checkout_sha") != exact_head:
            raise ExecutionContractError("CI_OR_REVIEW_IDENTITY_MISMATCH")

    material = {
        "repository": request["repository"],
        "pull_request": int(request["pull_request"]),
        "exact_head_sha": exact_head,
        "fresh_main_sha": fresh_main,
        "observed_base_sha": observed_base,
        "candidate_tree_sha": candidate_tree,
        "operation_id": _nonempty(request["operation_id"], "operation_id"),
        "attempt_id": _nonempty(request["attempt_id"], "attempt_id"),
        "fencing_identity": _nonempty(request["fencing_identity"], "fencing_identity"),
        "canonicalizer_admission_digest": admitted["admission_digest"],
        "review_evidence_ref": review_evidence["review_evidence_ref"],
        "ci_evidence_digest": _json_digest(ci_evidence) if ci_evidence is not None else None,
        "state": "FRESH_CANONICALIZATION_GATES",
    }
    material["effect_request_digest"] = _json_digest(material)
    return MappingProxyType(material)


def reconcile_merge_effect(
    admitted_request: Mapping[str, Any],
    admission: CanonicalizerAdmission,
    receipt: Mapping[str, Any],
) -> Mapping[str, Any]:
    admitted = _admission_mapping(admission)
    _require(
        admitted_request,
        (
            "repository", "pull_request", "exact_head_sha", "observed_base_sha",
            "candidate_tree_sha", "operation_id", "attempt_id", "fencing_identity",
            "effect_request_digest",
        ),
        "admitted_request",
    )
    _require(
        receipt,
        (
            "effect_status", "operation_id", "attempt_id", "fencing_identity",
            "merge_request_actor_identity", "github_actor", "observed_pr_head",
            "merge_commit_sha", "parent_shas", "result_tree_sha",
        ),
        "merge_effect_receipt",
    )
    if receipt["effect_status"] == "UNKNOWN":
        return MappingProxyType({"state": "MERGE_EFFECT_UNKNOWN", "retry_allowed": False})
    if receipt["effect_status"] != "MERGED":
        raise ExecutionContractError("merge_effect_receipt: unsupported terminal effect status")

    for field in ("operation_id", "attempt_id", "fencing_identity"):
        if str(receipt[field]) != str(admitted_request[field]):
            raise ExecutionContractError("LEASE_OR_FENCING_INVALID")
    if _sha40(receipt["observed_pr_head"], "merge_effect_receipt.observed_pr_head") != admitted_request["exact_head_sha"]:
        raise ExecutionContractError("HEAD_DRIFT")

    actor_identity = str(receipt["merge_request_actor_identity"])
    allowed_request_actors = {
        str(admitted["canonicalizer_identity"]),
        str(admitted["session_or_workload_identity"]),
    }
    if actor_identity not in allowed_request_actors:
        raise ExecutionContractError("MERGE_ACTOR_MISMATCH")
    if str(receipt["github_actor"]) not in {str(v) for v in admitted["allowed_github_actors"]}:
        raise ExecutionContractError("MERGE_ACTOR_MISMATCH")

    parents = tuple(str(v) for v in receipt["parent_shas"])
    expected_parents = (
        str(admitted_request["observed_base_sha"]),
        str(admitted_request["exact_head_sha"]),
    )
    if parents != expected_parents:
        raise ExecutionContractError("MERGED_WITH_UNEXPECTED_BASE_OR_TREE")
    if str(receipt["result_tree_sha"]) != str(admitted_request["candidate_tree_sha"]):
        raise ExecutionContractError("MERGED_WITH_UNEXPECTED_BASE_OR_TREE")
    merge_commit = _sha40(receipt["merge_commit_sha"], "merge_effect_receipt.merge_commit_sha")

    material = {
        "state": "CANONICALIZATION_RECORDED",
        "repository": admitted_request["repository"],
        "pull_request": admitted_request["pull_request"],
        "exact_head_sha": admitted_request["exact_head_sha"],
        "merge_commit_sha": merge_commit,
        "result_tree_sha": receipt["result_tree_sha"],
        "merge_request_actor_identity": actor_identity,
        "github_actor": receipt["github_actor"],
        "effect_request_digest": admitted_request["effect_request_digest"],
    }
    material["canonicalization_receipt_digest"] = _json_digest(material)
    return MappingProxyType(material)


def validate_pr615_prospective_adjudication(record: Mapping[str, Any]) -> None:
    _require(
        record,
        (
            "schema", "incident_ref", "original_pr", "accepted_exact_head",
            "pre_merge_main", "original_merge_commit", "accepted_candidate_tree",
            "merged_tree", "historical_merge_procedure",
            "original_merge_authorization_retroactively_granted", "content_disposition",
            "effective_from", "r187_reactivation_authorized", "rollback_default",
            "original_canonicalization_receipt_clean_authority",
        ),
        "pr615_adjudication",
    )
    expected = {
        "schema": "PR615_POST_MERGE_ADJUDICATION/v1",
        "incident_ref": 618,
        "original_pr": 615,
        "accepted_exact_head": "61ff56f1f1ad9c84e40bb68b3860a10bd1d6befb",
        "pre_merge_main": "e6c5c1e019e652650e9e55c9b4fad2431ffcd8ac",
        "original_merge_commit": "5967215d1efb2831bcb60e13f483fed88ecbb226",
        "accepted_candidate_tree": "26256afce26dbedcccd4cca7b8214347f3ee21fc",
        "merged_tree": "26256afce26dbedcccd4cca7b8214347f3ee21fc",
        "historical_merge_procedure": "GOVERNANCE_DEFECT_SELF_MERGE",
        "original_merge_authorization_retroactively_granted": False,
        "content_disposition": "RETAIN_BY_NEW_GOVERNED_DECISION",
        "effective_from": "ON_LAWFUL_CANONICAL_PUBLICATION_OF_THIS_ADJUDICATION",
        "r187_reactivation_authorized": False,
        "rollback_default": False,
        "original_canonicalization_receipt_clean_authority": False,
    }
    for field, value in expected.items():
        if record[field] != value:
            if field == "original_merge_authorization_retroactively_granted":
                raise ExecutionContractError("pr615_adjudication: retroactively granting merge authority is forbidden")
            raise ExecutionContractError(f"pr615_adjudication: invalid {field}")
    if record["accepted_candidate_tree"] != record["merged_tree"]:
        raise ExecutionContractError(
            "pr615_adjudication: accepted and merged tree identity mismatch"
        )
