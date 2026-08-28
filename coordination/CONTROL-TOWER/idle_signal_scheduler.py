from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
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
MATERIALIZATION_REQUEST_SCHEMA = "SignalOpportunityMaterializationRequest/v1"
TRUSTED_OPPORTUNITY_BATCH_SCHEMA = "TrustedSignalOpportunityBatch/v1"
PRIORITY_OBSERVATION_SCHEMA = "StartupPriorityHints/v1"
TRUSTED_PRIORITY_SCHEMA = "TrustedStartupPriorityObservation/v1"
DECISION_SCHEMA = "IdleSignalStartupDecision/v1"
AUTHORIZATION_SCHEMA = "IdleSignalAutoReleaseAuthorization/v2"
MATERIALIZER_DECISION_SCHEMA = "SignalOpportunityMaterializationDecision/v1"

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

COORDINATOR_REPOSITORY = "vxz2datoubo/second-brain-coordination"
REVIEW_QUEUE_ISSUE = 453
MAX_REVIEW_QUEUE_PAGES = 20
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_QUEUE_COMMENT_ENDPOINT = re.compile(
    r"^/repos/vxz2datoubo/second-brain-coordination/issues/453/comments"
    r"\?per_page=100&page=[1-9][0-9]*$"
)

STANDING_POLICY_REF = "issue://461#user-direction-2026-08-26"
IAGL_PRIORITY_REF = (
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
    "IAGL-STAGE-A/src/_iagl_primitives.py#Priority"
)
R149_REF = "coordination/CONTROL-TOWER/task_release_impact.py"
R150_REF = "coordination/CONTROL-TOWER/trusted_task_release.py"
CURRENT_MATERIALIZER_REF = "coordination/CONTROL-TOWER/signal_opportunity_materializer_current.py"
R137_PROVIDER_SRC = (
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
    "GLOBAL-SIGNAL-PLANE/S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY/src"
)
R137_PROVIDER_REF = (
    f"{R137_PROVIDER_SRC}/global_signal_gateway/live_observation_provider.py"
)


class IdleSignalSchedulerError(ValueError):
    """Stable fail-closed R151 error."""

    def __init__(self, code: str, path: str = "/") -> None:
        super().__init__(code)
        self.code = code
        self.path = path


def _load_r137_provider(root: Path) -> tuple[Any, Any]:
    """Load the retained R137 provider without ambient PYTHONPATH dependence."""
    src = (root / R137_PROVIDER_SRC).resolve()
    if not src.is_dir():
        raise IdleSignalSchedulerError("R137_PROVIDER_SOURCE_MISSING")
    original_path = list(sys.path)
    try:
        sys.path.insert(0, str(src))
        module = importlib.import_module(
            "global_signal_gateway.live_observation_provider"
        )
    except (ImportError, OSError) as exc:
        raise IdleSignalSchedulerError("R137_PROVIDER_LOAD_FAILED") from exc
    finally:
        sys.path[:] = original_path
    provider = getattr(module, "LiveObservationProvider", None)
    gateway_error = getattr(module, "GatewayError", None)
    if not isinstance(provider, type) or not isinstance(gateway_error, type):
        raise IdleSignalSchedulerError("R137_PROVIDER_API_INCOMPLETE")
    return provider, gateway_error


def _make_review_queue_observer(root: Path) -> tuple[Any, type[BaseException]]:
    """Adapt only fixed Review Queue #453 onto the retained R137 transport."""
    provider_base, gateway_error = _load_r137_provider(root)

    class _ReviewQueueLiveObserver(provider_base):
        def _dynamic_domain_endpoint_allowed(self, path: str) -> bool:
            if _QUEUE_COMMENT_ENDPOINT.fullmatch(path):
                return True
            return super()._dynamic_domain_endpoint_allowed(path)

    return _ReviewQueueLiveObserver(), gateway_error


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


def _requested_side_effect_surface(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Project requested side effects only; negative safeguards are not requests."""
    proposal = candidate.get("task_release_proposal")
    if not isinstance(proposal, Mapping):
        raise IdleSignalSchedulerError("TASK_RELEASE_PROPOSAL_REQUIRED")
    surface = proposal.get("proposed_write_surface")
    if not isinstance(surface, Mapping):
        raise IdleSignalSchedulerError("PROPOSED_WRITE_SURFACE_REQUIRED")
    interfaces = surface.get("interfaces", [])
    write_interfaces: list[Any] = []
    if isinstance(interfaces, list):
        for item in interfaces:
            if isinstance(item, Mapping):
                if str(item.get("mode", "")).casefold() == "write":
                    write_interfaces.append(item)
            elif isinstance(item, str):
                write_interfaces.append(item)
    return {
        "risk": proposal.get("risk", []),
        "write_paths": surface.get("write_paths", []),
        "write_domains": surface.get("write_domains", []),
        "authority_claims": surface.get("authority_claims", []),
        "write_interfaces": write_interfaces,
    }


def validate_priority_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate caller priority hints.

    Hints are additive only. They can add a P0/P1/P2 blocker, but they cannot
    claim scan completeness and cannot suppress trusted canonical blockers.
    """
    if not isinstance(value, Mapping):
        raise IdleSignalSchedulerError("PRIORITY_HINTS_NOT_OBJECT")
    required = {"schema_version", "observation_id", "evidence_refs", "items"}
    if set(value) != required:
        raise IdleSignalSchedulerError("PRIORITY_HINTS_FIELDS_INVALID")
    if value.get("schema_version") != PRIORITY_OBSERVATION_SCHEMA:
        raise IdleSignalSchedulerError("PRIORITY_HINTS_SCHEMA_INVALID")
    _nonempty_string(value.get("observation_id"), "/observation_id")
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
        raise IdleSignalSchedulerError(
            "OPPORTUNITY_ALREADY_CLOSED_OR_SATISFIED", f"{path}/current_disposition"
        )
    if out["epistemic_state"] in INELIGIBLE_EPISTEMIC_STATES:
        raise IdleSignalSchedulerError(
            "OPPORTUNITY_EPISTEMIC_STATE_BLOCKS_RELEASE", f"{path}/epistemic_state"
        )
    if out["desired_effect_gap_proven"] is not True:
        raise IdleSignalSchedulerError(
            "DESIRED_EFFECT_GAP_NOT_PROVEN", f"{path}/desired_effect_gap_proven"
        )
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
        raise IdleSignalSchedulerError(
            "TASK_RELEASE_PROPOSAL_REQUIRED", f"{path}/task_release_proposal"
        )
    proposal = dict(out["task_release_proposal"])
    if proposal.get("schema_version") != "TaskReleaseProposal/v1":
        raise IdleSignalSchedulerError(
            "TASK_RELEASE_PROPOSAL_SCHEMA_INVALID",
            f"{path}/task_release_proposal/schema_version",
        )
    if out["signal_ref"] not in proposal.get("source_signal_refs", []):
        raise IdleSignalSchedulerError(
            "SIGNAL_PROPOSAL_BINDING_MISSING",
            f"{path}/task_release_proposal/source_signal_refs",
        )
    if proposal.get("signal_primary_domain") != out["signal_primary_domain"]:
        raise IdleSignalSchedulerError(
            "SIGNAL_DOMAIN_PROPOSAL_MISMATCH",
            f"{path}/task_release_proposal/signal_primary_domain",
        )
    if proposal.get("desired_effect") != out["desired_effect"]:
        raise IdleSignalSchedulerError(
            "DESIRED_EFFECT_PROPOSAL_MISMATCH",
            f"{path}/task_release_proposal/desired_effect",
        )
    out["opportunity_digest"] = _digest(out)
    return out


def _load_current_materializer() -> Any:
    try:
        module = importlib.import_module("signal_opportunity_materializer_current")
    except (ImportError, OSError) as exc:
        raise IdleSignalSchedulerError("CURRENT_MATERIALIZER_LOAD_FAILED") from exc
    materialize = getattr(module, "materialize_signal_opportunity", None)
    if not callable(materialize):
        raise IdleSignalSchedulerError("CURRENT_MATERIALIZER_API_INCOMPLETE")
    return materialize


def _validate_materialization_request(value: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    path = f"/materialization_requests/{index}"
    if not isinstance(value, Mapping):
        raise IdleSignalSchedulerError("MATERIALIZATION_REQUEST_NOT_OBJECT", path)
    required = {
        "schema_version",
        "ledger",
        "draft_value",
        "domain_authority_descriptors",
        "domain_authority_observations",
        "authority_exact_read_proofs",
        "authority_live_observation_proof",
    }
    if set(value) != required:
        raise IdleSignalSchedulerError("MATERIALIZATION_REQUEST_FIELDS_INVALID", path)
    if value.get("schema_version") != MATERIALIZATION_REQUEST_SCHEMA:
        raise IdleSignalSchedulerError("MATERIALIZATION_REQUEST_SCHEMA_INVALID", path)
    if not isinstance(value.get("draft_value"), Mapping):
        raise IdleSignalSchedulerError("MATERIALIZATION_DRAFT_NOT_OBJECT", f"{path}/draft_value")
    descriptors = value.get("domain_authority_descriptors")
    observations = value.get("domain_authority_observations")
    proofs = value.get("authority_exact_read_proofs")
    if not isinstance(descriptors, Sequence) or isinstance(descriptors, (str, bytes)):
        raise IdleSignalSchedulerError("MATERIALIZATION_DESCRIPTORS_INVALID", path)
    if not isinstance(observations, Sequence) or isinstance(observations, (str, bytes)):
        raise IdleSignalSchedulerError("MATERIALIZATION_OBSERVATIONS_INVALID", path)
    if not isinstance(proofs, Sequence) or isinstance(proofs, (str, bytes)):
        raise IdleSignalSchedulerError("MATERIALIZATION_EXACT_READ_PROOFS_INVALID", path)
    return dict(value)


def _validate_materializer_decision(value: Mapping[str, Any], *, index: int) -> dict[str, Any] | None:
    path = f"/materialization_decisions/{index}"
    if not isinstance(value, Mapping):
        raise IdleSignalSchedulerError("MATERIALIZATION_DECISION_NOT_OBJECT", path)
    if value.get("schema_version") != MATERIALIZER_DECISION_SCHEMA:
        raise IdleSignalSchedulerError("MATERIALIZATION_DECISION_SCHEMA_INVALID", path)
    supplied_digest = value.get("decision_digest")
    if not isinstance(supplied_digest, str) or len(supplied_digest) != 64:
        raise IdleSignalSchedulerError("MATERIALIZATION_DECISION_DIGEST_INVALID", path)
    basis = dict(_copy(value))
    basis.pop("decision_digest", None)
    if _digest(basis) != supplied_digest:
        raise IdleSignalSchedulerError("MATERIALIZATION_DECISION_DIGEST_MISMATCH", path)
    signal_ref = value.get("signal_ref")
    _nonempty_string(signal_ref, f"{path}/signal_ref")
    if value.get("disposition") != "MATERIALIZED_FOR_R151":
        return None
    opportunity_raw = value.get("opportunity")
    if not isinstance(opportunity_raw, Mapping):
        raise IdleSignalSchedulerError("MATERIALIZED_OPPORTUNITY_MISSING", path)
    supplied_opportunity_digest = opportunity_raw.get("opportunity_digest")
    if not isinstance(supplied_opportunity_digest, str) or len(supplied_opportunity_digest) != 64:
        raise IdleSignalSchedulerError("MATERIALIZED_OPPORTUNITY_DIGEST_INVALID", path)
    opportunity_input = dict(opportunity_raw)
    opportunity_input.pop("opportunity_digest", None)
    opportunity = validate_opportunity(opportunity_input, index=index)
    if opportunity["opportunity_digest"] != supplied_opportunity_digest:
        raise IdleSignalSchedulerError("MATERIALIZED_OPPORTUNITY_DIGEST_MISMATCH", path)
    if opportunity["signal_ref"] != signal_ref:
        raise IdleSignalSchedulerError("MATERIALIZATION_SIGNAL_BINDING_MISMATCH", path)
    return {
        "signal_ref": signal_ref,
        "opportunity_id": opportunity["opportunity_id"],
        "opportunity_digest": opportunity["opportunity_digest"],
        "materialization_decision_digest": supplied_digest,
        "opportunity": opportunity,
    }


def _make_trusted_batch_api() -> tuple[Any, Any, type[Any]]:
    seal = object()

    class _TrustedOpportunityBatch:
        __slots__ = ("_payload_json",)

        def __init__(self, payload: Mapping[str, Any], token: object) -> None:
            if token is not seal:
                raise IdleSignalSchedulerError("TRUSTED_BATCH_CONSTRUCTION_FORBIDDEN")
            object.__setattr__(self, "_payload_json", _canonical(payload))

        def __setattr__(self, name: str, value: Any) -> None:
            raise AttributeError("trusted opportunity batch is immutable")

        def _open(self, token: object) -> dict[str, Any]:
            if token is not seal:
                raise IdleSignalSchedulerError("TRUSTED_BATCH_SEAL_INVALID")
            return json.loads(self._payload_json)

    def mint(payload: Mapping[str, Any]) -> Any:
        return _TrustedOpportunityBatch(payload, seal)

    def open_batch(value: Any) -> dict[str, Any]:
        if type(value) is not _TrustedOpportunityBatch:
            raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_REQUIRED")
        payload = value._open(seal)
        if payload.get("schema_version") != TRUSTED_OPPORTUNITY_BATCH_SCHEMA:
            raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_SCHEMA_INVALID")
        batch_digest = payload.get("batch_digest")
        if not isinstance(batch_digest, str) or len(batch_digest) != 64:
            raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_DIGEST_INVALID")
        basis = dict(payload)
        basis.pop("batch_digest", None)
        if _digest(basis) != batch_digest:
            raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_DIGEST_MISMATCH")
        return payload

    return mint, open_batch, _TrustedOpportunityBatch


_mint_trusted_batch, _open_trusted_batch, _TRUSTED_BATCH_TYPE = _make_trusted_batch_api()


def materialize_trusted_opportunity_batch(
    repo_root: str | Path,
    materialization_requests: Sequence[Mapping[str, Any]],
    *,
    expected_coordinator_main: str,
) -> Any:
    """Mint an invocation-local batch only from the canonical current materializer."""
    if not isinstance(materialization_requests, Sequence) or isinstance(
        materialization_requests, (str, bytes)
    ):
        raise IdleSignalSchedulerError("MATERIALIZATION_REQUESTS_INVALID")
    root = Path(repo_root).resolve()
    materialize = _load_current_materializer()
    items: list[dict[str, Any]] = []
    for index, raw in enumerate(materialization_requests):
        request = _validate_materialization_request(raw, index=index)
        try:
            decision = materialize(
                root,
                request["ledger"],
                request["draft_value"],
                expected_coordinator_main=expected_coordinator_main,
                domain_authority_descriptors=request["domain_authority_descriptors"],
                domain_authority_observations=request["domain_authority_observations"],
                authority_exact_read_proofs=request["authority_exact_read_proofs"],
                authority_live_observation_proof=request["authority_live_observation_proof"],
            )
        except Exception as exc:
            code = getattr(exc, "code", type(exc).__name__)
            raise IdleSignalSchedulerError(
                f"CURRENT_MATERIALIZER_FAILED:{code}", f"/materialization_requests/{index}"
            ) from exc
        item = _validate_materializer_decision(decision, index=index)
        if item is not None:
            items.append(item)
    payload: dict[str, Any] = {
        "schema_version": TRUSTED_OPPORTUNITY_BATCH_SCHEMA,
        "canonical_main": expected_coordinator_main,
        "materializer_ref": CURRENT_MATERIALIZER_REF,
        "items": items,
        "authority_boundary": {
            "creates_signal_truth": False,
            "creates_task": False,
            "selects_opportunity": False,
            "releases_task": False,
            "grants_execution_authority": False,
            "grants_domain_write": False,
            "grants_w3_write": False,
            "grants_merge_authority": False,
        },
    }
    payload["batch_digest"] = _digest(payload)
    return _mint_trusted_batch(payload)


def trusted_batch_opportunities(value: Any, *, expected_coordinator_main: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = _open_trusted_batch(value)
    if payload.get("canonical_main") != expected_coordinator_main:
        raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_MAIN_MISMATCH")
    if payload.get("materializer_ref") != CURRENT_MATERIALIZER_REF:
        raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_MATERIALIZER_MISMATCH")
    expected_boundary = {
        "creates_signal_truth": False,
        "creates_task": False,
        "selects_opportunity": False,
        "releases_task": False,
        "grants_execution_authority": False,
        "grants_domain_write": False,
        "grants_w3_write": False,
        "grants_merge_authority": False,
    }
    if payload.get("authority_boundary") != expected_boundary:
        raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_AUTHORITY_BOUNDARY_INVALID")
    items = payload.get("items")
    if not isinstance(items, list):
        raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_ITEMS_INVALID")
    opportunities: list[dict[str, Any]] = []
    seen_opportunity_digests: set[str] = set()
    expected_item_fields = {
        "signal_ref",
        "opportunity_id",
        "opportunity_digest",
        "materialization_decision_digest",
        "opportunity",
    }
    for index, item in enumerate(items):
        if not isinstance(item, Mapping) or set(item) != expected_item_fields:
            raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_ITEM_INVALID")
        opportunity_raw = item.get("opportunity")
        if not isinstance(opportunity_raw, Mapping):
            raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_OPPORTUNITY_MISSING")
        supplied = opportunity_raw.get("opportunity_digest")
        opportunity_input = dict(opportunity_raw)
        opportunity_input.pop("opportunity_digest", None)
        opportunity = validate_opportunity(opportunity_input, index=index)
        if supplied != opportunity["opportunity_digest"] or supplied != item.get("opportunity_digest"):
            raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_OPPORTUNITY_DRIFT")
        if opportunity["signal_ref"] != item.get("signal_ref"):
            raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_SIGNAL_DRIFT")
        if item.get("opportunity_id") != opportunity["opportunity_id"]:
            raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_ID_DRIFT")
        decision_digest = item.get("materialization_decision_digest")
        if not isinstance(decision_digest, str) or len(decision_digest) != 64:
            raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_DECISION_DIGEST_INVALID")
        if opportunity["opportunity_digest"] in seen_opportunity_digests:
            raise IdleSignalSchedulerError("TRUSTED_OPPORTUNITY_BATCH_DUPLICATE_OPPORTUNITY")
        seen_opportunity_digests.add(opportunity["opportunity_digest"])
        opportunities.append(opportunity)
    return opportunities, payload


def _canonical_idle_blockers(root: Path) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    claims_doc = load_yaml(root / CLAIMS_FILE)
    claims = claims_doc.get("claims") if isinstance(claims_doc, Mapping) else None
    if not isinstance(claims, list):
        raise IdleSignalSchedulerError("CANONICAL_CLAIMS_DOCUMENT_INVALID")
    for index, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            raise IdleSignalSchedulerError("CANONICAL_CLAIM_INVALID", f"/claims/{index}")
        if claim.get("claim_state") in {
            ACTIVE_IMPLEMENTATION,
            RESERVED_IMPLEMENTATION_NON_EXECUTABLE,
        }:
            binding = claim.get("route_binding")
            task_id = binding.get("task_id") if isinstance(binding, Mapping) else None
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
            raise IdleSignalSchedulerError(
                "GPT_WORKER_SLOT_INVALID", f"/worker_slots/{index}"
            )
        blockers.append(
            {
                "priority": P2,
                "work_ref": (
                    f"worker-slot://{slot.get('worker_slot_id') or slot.get('slot_id') or index}"
                ),
                "reason": "GPT_ENGINEERING_WORKER_SLOT_ALREADY_ACTIVE",
                "evidence_refs": [GPT_WORKERS_REGISTRY],
            }
        )
    return blockers


def _queue_field(body: str, name: str) -> str | None:
    match = re.search(
        rf"(?m)^[ \t]*{re.escape(name)}:[ \t]*([^\r\n#]+?)[ \t]*$",
        body,
    )
    if match is None:
        return None
    return match.group(1).strip().strip("'\"")


def _trusted_review_queue_blockers(
    root: Path,
) -> tuple[list[dict[str, Any]], list[str], str]:
    """Read fixed Review Queue #453 through the retained R137 GitHub provider."""
    observer, gateway_error = _make_review_queue_observer(root)
    normalized_events: list[dict[str, Any]] = []
    evidence_refs: list[str] = []
    pagination_complete = False
    for page in range(1, MAX_REVIEW_QUEUE_PAGES + 1):
        path = (
            f"/repos/{COORDINATOR_REPOSITORY}/issues/{REVIEW_QUEUE_ISSUE}/comments"
            f"?per_page=100&page={page}"
        )
        try:
            _headers, payload, _metadata = observer._get_json(path)
        except gateway_error as exc:
            code = getattr(exc, "code", "UNKNOWN")
            raise IdleSignalSchedulerError(
                f"TRUSTED_REVIEW_QUEUE_PROVIDER_FAILED:{code}"
            ) from exc
        if not isinstance(payload, list):
            raise IdleSignalSchedulerError("TRUSTED_REVIEW_QUEUE_PAYLOAD_INVALID")
        for raw in payload:
            if not isinstance(raw, Mapping):
                raise IdleSignalSchedulerError("TRUSTED_REVIEW_QUEUE_COMMENT_INVALID")
            comment_id = raw.get("id")
            body = raw.get("body")
            html_url = raw.get("html_url")
            if not isinstance(comment_id, int) or not isinstance(body, str):
                raise IdleSignalSchedulerError("TRUSTED_REVIEW_QUEUE_COMMENT_INVALID")
            schema = _queue_field(body, "schema")
            if schema not in {"REVIEW_REQUEST/v1", "REVIEW_RESULT/v1"}:
                continue
            project = _queue_field(body, "project")
            if project != "SECOND_BRAIN":
                continue
            pr_raw = _queue_field(body, "pr")
            try:
                pr = int(pr_raw or "")
            except ValueError as exc:
                raise IdleSignalSchedulerError("TRUSTED_REVIEW_QUEUE_PR_INVALID") from exc
            if pr <= 0:
                raise IdleSignalSchedulerError("TRUSTED_REVIEW_QUEUE_PR_INVALID")
            ref = (
                str(html_url)
                if isinstance(html_url, str) and html_url
                else f"github://{COORDINATOR_REPOSITORY}/issues/{REVIEW_QUEUE_ISSUE}#comment={comment_id}"
            )
            evidence_refs.append(ref)
            if schema == "REVIEW_REQUEST/v1":
                exact_head = _queue_field(body, "exact_head")
                status = _queue_field(body, "status")
                if exact_head is None or not _SHA40.fullmatch(exact_head):
                    raise IdleSignalSchedulerError("TRUSTED_REVIEW_QUEUE_HEAD_INVALID")
                if status != "WAITING_REVIEW":
                    raise IdleSignalSchedulerError("TRUSTED_REVIEW_QUEUE_STATUS_INVALID")
                normalized_events.append(
                    {
                        "comment_id": comment_id,
                        "schema": schema,
                        "pr": pr,
                        "head": exact_head,
                        "status": status,
                        "evidence_ref": ref,
                    }
                )
            else:
                reviewed_head = _queue_field(body, "reviewed_head")
                verdict = _queue_field(body, "verdict")
                if reviewed_head is None or not _SHA40.fullmatch(reviewed_head):
                    raise IdleSignalSchedulerError("TRUSTED_REVIEW_QUEUE_HEAD_INVALID")
                if verdict not in {"ACCEPT", "CHANGES_REQUIRED", "BLOCKED"}:
                    raise IdleSignalSchedulerError("TRUSTED_REVIEW_QUEUE_VERDICT_INVALID")
                normalized_events.append(
                    {
                        "comment_id": comment_id,
                        "schema": schema,
                        "pr": pr,
                        "head": reviewed_head,
                        "verdict": verdict,
                        "evidence_ref": ref,
                    }
                )
        if len(payload) < 100:
            pagination_complete = True
            break
    if not pagination_complete:
        raise IdleSignalSchedulerError("TRUSTED_REVIEW_QUEUE_PAGINATION_INCOMPLETE")

    latest_by_ticket: dict[tuple[int, str], dict[str, Any]] = {}
    current_request_by_pr: dict[int, dict[str, Any]] = {}
    for event in sorted(normalized_events, key=lambda item: int(item["comment_id"])):
        pr = int(event["pr"])
        head = str(event["head"])
        latest_by_ticket[(pr, head)] = event
        if event["schema"] == "REVIEW_REQUEST/v1":
            current_request_by_pr[pr] = event

    latest_ticket_states: list[dict[str, Any]] = []
    for (pr, head), event in sorted(latest_by_ticket.items()):
        latest_ticket_states.append(
            {
                "pr": pr,
                "head": head,
                "event": event,
            }
        )

    blockers: list[dict[str, Any]] = []
    current_lineage_states: list[dict[str, Any]] = []
    for pr, request in sorted(current_request_by_pr.items()):
        head = str(request["head"])
        event = latest_by_ticket[(pr, head)]
        current_lineage_states.append(
            {
                "pr": pr,
                "head": head,
                "request_comment_id": request["comment_id"],
                "current_event": event,
            }
        )
        if event["schema"] == "REVIEW_REQUEST/v1":
            blockers.append(
                {
                    "priority": P1,
                    "work_ref": f"pr://{pr}@{head}",
                    "reason": "TRUSTED_REVIEW_QUEUE_WAITING_REVIEW",
                    "evidence_refs": [event["evidence_ref"]],
                }
            )
            continue
        verdict = event["verdict"]
        if verdict in {"CHANGES_REQUIRED", "BLOCKED"}:
            blockers.append(
                {
                    "priority": P2,
                    "work_ref": f"pr://{pr}@{head}",
                    "reason": f"TRUSTED_REVIEW_QUEUE_{verdict}",
                    "evidence_refs": [event["evidence_ref"]],
                }
            )

    observation = {
        "provider_ref": R137_PROVIDER_REF,
        "issue": REVIEW_QUEUE_ISSUE,
        "event_count": len(normalized_events),
        "latest_ticket_states": latest_ticket_states,
        "current_lineage_states": current_lineage_states,
        "pagination_complete": True,
    }
    return blockers, sorted(set(evidence_refs)), _digest(observation)


def _trusted_priority_observation(
    root: Path, caller_hints: Mapping[str, Any]
) -> dict[str, Any]:
    review_blockers, review_refs, review_digest = _trusted_review_queue_blockers(root)
    canonical_blockers = _canonical_idle_blockers(root)
    caller_blockers = [
        item for item in caller_hints["items"] if item["priority"] in BLOCKING_PRIORITIES
    ]
    items = [*review_blockers, *canonical_blockers, *caller_blockers]
    evidence_refs = sorted(
        set(
            [
                R137_PROVIDER_REF,
                CLAIMS_FILE,
                GPT_WORKERS_REGISTRY,
                *review_refs,
                *caller_hints["evidence_refs"],
            ]
        )
    )
    value = {
        "schema_version": TRUSTED_PRIORITY_SCHEMA,
        "scan_complete": True,
        "trusted_sources": {
            "review_queue_issue": REVIEW_QUEUE_ISSUE,
            "review_queue_digest": review_digest,
            "canonical_claims": CLAIMS_FILE,
            "canonical_worker_slots": GPT_WORKERS_REGISTRY,
            "caller_hints_additive_only": True,
        },
        "evidence_refs": evidence_refs,
        "items": _copy(items),
        "caller_hints_digest": caller_hints["observation_digest"],
    }
    value["observation_digest"] = _digest(value)
    return value


def _rank_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
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


def _decision(
    status: str,
    *,
    reason: str,
    selected: Mapping[str, Any] | None = None,
    blockers: Sequence[Mapping[str, Any]] = (),
    priority_observation: Mapping[str, Any] | None = None,
    r150_receipt: Mapping[str, Any] | None = None,
    authorization: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": DECISION_SCHEMA,
        "status": status,
        "reason": reason,
        "selected_opportunity_id": selected.get("opportunity_id") if selected else None,
        "selected_signal_ref": selected.get("signal_ref") if selected else None,
        "blockers": _copy(list(blockers)),
        "priority_observation_digest": (
            priority_observation.get("observation_digest")
            if priority_observation
            else None
        ),
        "r150_receipt_digest": r150_receipt.get("receipt_digest") if r150_receipt else None,
        "authorization": _copy(authorization) if authorization else None,
    }
    value["decision_digest"] = _digest(value)
    return value


def _authorization(
    selected: Mapping[str, Any],
    *,
    current_main: str,
    priority_observation: Mapping[str, Any],
    r150_receipt: Mapping[str, Any],
    trusted_batch: Mapping[str, Any],
    materialization_decision_digest: str,
) -> dict[str, Any]:
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
    if (
        not isinstance(authority_boundary, Mapping)
        or authority_boundary.get("evidence_only") is not True
    ):
        raise IdleSignalSchedulerError("R150_EVIDENCE_ONLY_BOUNDARY_REQUIRED")
    if priority_observation.get("schema_version") != TRUSTED_PRIORITY_SCHEMA:
        raise IdleSignalSchedulerError("TRUSTED_PRIORITY_OBSERVATION_REQUIRED")
    if priority_observation.get("scan_complete") is not True:
        raise IdleSignalSchedulerError("TRUSTED_PRIORITY_SCAN_INCOMPLETE")
    if any(
        item.get("priority") in BLOCKING_PRIORITIES
        for item in priority_observation.get("items", [])
        if isinstance(item, Mapping)
    ):
        raise IdleSignalSchedulerError("TRUSTED_PRIORITY_BLOCKER_PRESENT")
    batch_digest = trusted_batch.get("batch_digest")
    if not isinstance(batch_digest, str) or len(batch_digest) != 64:
        raise IdleSignalSchedulerError("TRUSTED_BATCH_DIGEST_REQUIRED")
    if not isinstance(materialization_decision_digest, str) or len(materialization_decision_digest) != 64:
        raise IdleSignalSchedulerError("MATERIALIZATION_DECISION_DIGEST_REQUIRED")

    payload = {
        "schema_version": AUTHORIZATION_SCHEMA,
        "signal_ref": selected["signal_ref"],
        "opportunity_id": selected["opportunity_id"],
        "opportunity_digest": selected["opportunity_digest"],
        "trusted_opportunity_batch_digest": batch_digest,
        "materialization_decision_digest": materialization_decision_digest,
        "canonical_main": current_main,
        "priority_observation_digest": priority_observation["observation_digest"],
        "r150_receipt_digest": receipt_digest,
        "r150_final_disposition": disposition,
        "standing_user_policy_ref": STANDING_POLICY_REF,
        "priority_semantics_ref": IAGL_PRIORITY_REF,
        "priority_provider_ref": R137_PROVIDER_REF,
        "opportunity_materializer_ref": CURRENT_MATERIALIZER_REF,
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
            "caller_can_attest_priority_completeness": False,
            "caller_can_supply_opportunity_truth": False,
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
        "apply_requires_fresh_rematerialization": True,
    }
    payload["authorization_id"] = f"r151-auto-release:{_digest(payload)[:24]}"
    payload["authorization_digest"] = _digest(payload)
    return payload


def evaluate_idle_signal_startup(
    repo_root: str | Path,
    trusted_opportunity_batch: Any,
    *,
    expected_coordinator_main: str,
    priority_observation_value: Mapping[str, Any],
) -> dict[str, Any]:
    """Select at most one current-materializer-proven idle opportunity."""
    root = Path(repo_root).resolve()
    caller_hints = validate_priority_observation(priority_observation_value)
    opportunities, batch_payload = trusted_batch_opportunities(
        trusted_opportunity_batch,
        expected_coordinator_main=expected_coordinator_main,
    )

    try:
        priority_observation = _trusted_priority_observation(root, caller_hints)
    except IdleSignalSchedulerError as exc:
        return _decision(
            "NO_IDLE_RELEASE",
            reason=f"TRUSTED_PRIORITY_FAIL_CLOSED:{exc.code}",
        )

    blockers = [
        item
        for item in priority_observation["items"]
        if item["priority"] in BLOCKING_PRIORITIES
    ]
    if blockers:
        return _decision(
            "NO_IDLE_RELEASE",
            reason="HIGHER_PRIORITY_OR_ACTIVE_WORK_PRESENT",
            blockers=blockers,
            priority_observation=priority_observation,
        )

    valid: list[dict[str, Any]] = []
    user_gate: list[dict[str, Any]] = []
    for candidate in opportunities:
        hits = _exclusion_hits(_requested_side_effect_surface(candidate))
        if hits:
            user_gate.append(
                {
                    "opportunity_id": candidate["opportunity_id"],
                    "exclusion_hits": list(hits),
                }
            )
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
            reason="NO_ELIGIBLE_TRUSTED_SIGNAL_OPPORTUNITY",
            priority_observation=priority_observation,
        )

    selected = min(valid, key=_rank_key)
    selected_items = [
        item
        for item in batch_payload["items"]
        if item["opportunity_digest"] == selected["opportunity_digest"]
    ]
    if len(selected_items) != 1:
        raise IdleSignalSchedulerError("SELECTED_OPPORTUNITY_PROVENANCE_CARDINALITY_INVALID")
    selected_item = selected_items[0]
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
        trusted_batch=batch_payload,
        materialization_decision_digest=selected_item["materialization_decision_digest"],
    )
    return _decision(
        "AUTO_RELEASE_AUTHORIZED",
        reason=(
            "IDLE_SIGNAL_OPPORTUNITY_PASSED_CURRENT_MATERIALIZER_TRUSTED_PRIORITY_"
            "R149_R150_AND_STANDING_POLICY"
        ),
        selected=selected,
        priority_observation=priority_observation,
        r150_receipt=r150_receipt,
        authorization=authorization,
    )
