from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence

from idle_signal_scheduler import (
    OPPORTUNITY_SCHEMA,
    P3,
    P4,
    _exclusion_hits,
    _load_r137_provider,
    _queue_field,
    _requested_side_effect_surface,
    validate_opportunity,
)
from trusted_task_release import (
    RELEASEABLE_DISPOSITIONS if False else TRUSTED_RECEIPT_SCHEMA,  # type: ignore
    TrustedReleaseError,
    evaluate_trusted_release_proposal,
)


DRAFT_SCHEMA = "SignalOpportunityDraft/v1"
DECISION_SCHEMA = "SignalOpportunityMaterializationDecision/v1"
GENERIC_OWNER_RECONCILIATION_SCHEMA = "SIGNAL_OWNER_RECONCILIATION/v1"
AI_FILM_REUSE_HANDOFF_SCHEMA = "DURABLE_SIGNAL_OWNER_DOMAIN_REUSE_HANDOFF/v1"
COORDINATOR_REPOSITORY = "vxz2datoubo/second-brain-coordination"
R145_SRC = (
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
    "GLOBAL-SIGNAL-PLANE/S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY/src"
)
ELIGIBLE_PRIORITY = frozenset({P3, P4})
ELIGIBLE_EXECUTION_STATE = "NOT_STARTED"
INELIGIBLE_PLANNING_STATES = frozenset({"SUPERSEDED", "CONFLICTED", "CANCELLED", "DONE"})
INELIGIBLE_EPISTEMIC_STATES = frozenset({"UNKNOWN", "NEEDS_REVALIDATION"})
OWNER_DISPOSITIONS = frozenset(
    {"REUSE_EXISTING_WORK", "ALREADY_SATISFIED", "GAP_PROVEN", "NEEDS_REVALIDATION"}
)
RELEASEABLE_R150 = frozenset(
    {"RELEASE_BOUNDED_TASK", "RELEASE_AS_EXTENSION", "RELEASE_AS_ADAPTER_OR_PLUGIN"}
)
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_OWNER_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class SignalOpportunityMaterializerError(ValueError):
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


def _nonempty(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SignalOpportunityMaterializerError("INVALID_STRING", path)
    return value


def _bounded_int(value: Any, path: str, *, high: int = 100) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > high:
        raise SignalOpportunityMaterializerError("INVALID_INTEGER", path)
    return value


def _load_r145_api(root: Path) -> tuple[type[Any], type[BaseException]]:
    src = (root / R145_SRC).resolve()
    if not src.is_dir():
        raise SignalOpportunityMaterializerError("R145_SOURCE_MISSING")
    original = list(sys.path)
    try:
        sys.path.insert(0, str(src))
        module = importlib.import_module("global_signal_gateway.domain_authority")
    except (ImportError, OSError) as exc:
        raise SignalOpportunityMaterializerError("R145_LOAD_FAILED") from exc
    finally:
        sys.path[:] = original
    resolver = getattr(module, "DomainAuthorityResolver", None)
    domain_error = getattr(module, "DomainAuthorityError", None)
    if not isinstance(resolver, type) or not isinstance(domain_error, type):
        raise SignalOpportunityMaterializerError("R145_API_INCOMPLETE")
    return resolver, domain_error


def validate_draft(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SignalOpportunityMaterializerError("DRAFT_NOT_OBJECT")
    required = {
        "schema_version",
        "signal_ref",
        "owner_reconciliation_issue",
        "priority_class",
        "user_value_score",
        "materiality_score",
        "dependency_readiness_score",
        "age_cycles",
        "estimated_cost_score",
        "task_release_proposal",
    }
    if set(value) != required:
        raise SignalOpportunityMaterializerError("DRAFT_FIELDS_INVALID")
    if value.get("schema_version") != DRAFT_SCHEMA:
        raise SignalOpportunityMaterializerError("DRAFT_SCHEMA_INVALID")
    out = _copy(value)
    _nonempty(out["signal_ref"], "/signal_ref")
    issue = out["owner_reconciliation_issue"]
    if isinstance(issue, bool) or not isinstance(issue, int) or issue <= 0:
        raise SignalOpportunityMaterializerError(
            "OWNER_RECONCILIATION_ISSUE_INVALID", "/owner_reconciliation_issue"
        )
    if out["priority_class"] not in ELIGIBLE_PRIORITY:
        raise SignalOpportunityMaterializerError("IDLE_PRIORITY_REQUIRED", "/priority_class")
    for field in (
        "user_value_score",
        "materiality_score",
        "dependency_readiness_score",
        "estimated_cost_score",
    ):
        _bounded_int(out[field], f"/{field}")
    _bounded_int(out["age_cycles"], "/age_cycles", high=1_000_000)
    if not isinstance(out["task_release_proposal"], Mapping):
        raise SignalOpportunityMaterializerError("TASK_RELEASE_PROPOSAL_REQUIRED")
    return out


def _projection_and_history(ledger: Any) -> tuple[Mapping[str, Any], list[dict[str, Any]]]:
    required = (
        "history",
        "current_projection",
        "rebuild_projection",
        "current_projection_version",
        "input_revision",
    )
    if ledger is None or not all(hasattr(ledger, name) for name in required):
        raise SignalOpportunityMaterializerError("S0C_LEDGER_REQUIRED")
    projection = ledger.current_projection()
    if projection is None:
        projection = ledger.rebuild_projection(
            expected_version=ledger.current_projection_version()
        )
    if not isinstance(projection, Mapping):
        raise SignalOpportunityMaterializerError("S0C_PROJECTION_INVALID")
    history = ledger.history()
    if not isinstance(history, list) or not all(isinstance(item, Mapping) for item in history):
        raise SignalOpportunityMaterializerError("S0C_HISTORY_INVALID")
    if projection.get("ledger_watermark") != len(history):
        raise SignalOpportunityMaterializerError("S0C_LEDGER_WATERMARK_MISMATCH")
    if projection.get("input_revision") != ledger.input_revision():
        raise SignalOpportunityMaterializerError("S0C_INPUT_REVISION_MISMATCH")
    if not isinstance(projection.get("checksum"), str) or not isinstance(
        projection.get("reducer_version"), str
    ):
        raise SignalOpportunityMaterializerError("S0C_PROJECTION_PROOF_INVALID")
    return projection, [dict(item) for item in history]


def _signal_origin(
    ledger: Any, signal_ref: str
) -> tuple[dict[str, Any], dict[str, Any], str]:
    projection, history = _projection_and_history(ledger)
    signals = projection.get("signals")
    if not isinstance(signals, list):
        raise SignalOpportunityMaterializerError("S0C_SIGNALS_INVALID")
    matches = [
        dict(item)
        for item in signals
        if isinstance(item, Mapping) and item.get("signal_id") == signal_ref
    ]
    if len(matches) != 1:
        raise SignalOpportunityMaterializerError("S0C_SIGNAL_NOT_UNIQUE_OR_MISSING")
    effective = matches[0]
    planning_state = str(effective.get("planning_state", ""))
    execution_state = str(effective.get("execution_state", ""))
    epistemic_state = str(effective.get("epistemic_state", ""))
    if planning_state in INELIGIBLE_PLANNING_STATES:
        raise SignalOpportunityMaterializerError("S0C_SIGNAL_PLANNING_STATE_INELIGIBLE")
    if execution_state != ELIGIBLE_EXECUTION_STATE:
        raise SignalOpportunityMaterializerError("S0C_SIGNAL_EXECUTION_STATE_INELIGIBLE")
    if epistemic_state in INELIGIBLE_EPISTEMIC_STATES:
        raise SignalOpportunityMaterializerError("S0C_SIGNAL_EPISTEMIC_STATE_INELIGIBLE")

    origins: list[dict[str, Any]] = []
    for item in history:
        if item.get("signal_id") != signal_ref:
            continue
        metadata = item.get("public_safe_metadata")
        envelope = metadata.get("intent_envelope") if isinstance(metadata, Mapping) else None
        if not isinstance(envelope, Mapping):
            continue
        if all(
            isinstance(envelope.get(field), str) and envelope.get(field)
            for field in ("desired_effect", "problem_to_solve", "success_condition")
        ):
            origins.append(item)
    if not origins:
        raise SignalOpportunityMaterializerError("S0C_SEMANTIC_ORIGIN_MISSING")
    origin = sorted(origins, key=lambda item: int(item.get("ledger_offset", 0)))[0]
    primary_domain = _nonempty(origin.get("primary_domain"), "/s0c/primary_domain")
    metadata = origin["public_safe_metadata"]
    envelope = dict(metadata["intent_envelope"])
    signal_proof_ref = (
        f"s0c://signal/{signal_ref}"
        f"#reducer={projection['reducer_version']};watermark={projection['ledger_watermark']}"
        f";input_revision={projection['input_revision']};sha256={projection['checksum']}"
    )
    return effective, {
        "signal_ref": signal_ref,
        "primary_domain": primary_domain,
        "epistemic_state": epistemic_state,
        "desired_effect": envelope["desired_effect"],
        "problem_to_solve": envelope["problem_to_solve"],
        "success_condition": envelope["success_condition"],
        "origin_event_id": origin.get("event_id"),
        "origin_event_digest": _digest(
            {key: value for key, value in origin.items() if key != "ledger_offset"}
        ),
    }, signal_proof_ref


def _resolve_owner_authority(
    root: Path,
    *,
    domain_id: str,
    descriptors: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
    exact_read_proofs: Sequence[Any],
    live_observation_proof: Any,
    expected_coordinator_main: str,
) -> dict[str, Any]:
    resolver_cls, domain_error = _load_r145_api(root)
    try:
        resolved = resolver_cls(descriptors).resolve(
            domain_id,
            observations,
            exact_read_proofs=exact_read_proofs,
            live_observation_proof=live_observation_proof,
            expected_canonical_main=expected_coordinator_main,
            coordinator_repository=COORDINATOR_REPOSITORY,
        )
    except domain_error as exc:
        code = getattr(exc, "code", "DOMAIN_AUTHORITY_UNVERIFIED")
        return {"valid": False, "reason": code, "authority_refs": []}
    return dict(resolved)


def _make_owner_observer(root: Path, repository: str) -> tuple[Any, type[BaseException]]:
    if not _OWNER_REPOSITORY.fullmatch(repository):
        raise SignalOpportunityMaterializerError("OWNER_REPOSITORY_INVALID")
    provider_base, gateway_error = _load_r137_provider(root)
    escaped = re.escape(f"/repos/{repository}")

    class _OwnerObserver(provider_base):
        def __init__(self) -> None:
            super().__init__()
            self._governed_domain_repositories.add(repository)

        def _dynamic_domain_endpoint_allowed(self, path: str) -> bool:
            if re.fullmatch(escaped + r"/issues/[1-9][0-9]*", path):
                return True
            if re.fullmatch(
                escaped + r"/issues/[1-9][0-9]*/comments\?per_page=100&page=[1-9][0-9]*",
                path,
            ):
                return True
            return super()._dynamic_domain_endpoint_allowed(path)

    return _OwnerObserver(), gateway_error


def _normalize_owner_record(
    body: str,
    *,
    signal_ref: str,
    owner_domain: str,
    owner_main: str,
    evidence_ref: str,
) -> dict[str, Any] | None:
    schema = _queue_field(body, "schema")
    if schema == AI_FILM_REUSE_HANDOFF_SCHEMA:
        if _queue_field(body, "source_signal_id") != signal_ref:
            return None
        current_main = _queue_field(body, "current_main")
        if current_main != owner_main:
            return {
                "disposition": "NEEDS_REVALIDATION",
                "reason": "OWNER_RECONCILIATION_STALE_MAIN",
                "evidence_refs": [evidence_ref],
                "dependency_ready": False,
                "work_refs": [],
            }
        reconciliation = _queue_field(body, "reconciliation")
        if reconciliation != "REUSE_EXTEND_EXISTING_WORK":
            return None
        work_refs = []
        for name, prefix in (("existing_issue", "issue"), ("existing_pr", "pr")):
            raw = _queue_field(body, name)
            if raw and raw.isdigit():
                work_refs.append(f"github://{prefix}/{raw}")
        return {
            "disposition": "REUSE_EXISTING_WORK",
            "reason": "EXACT_SIGNAL_BACKLINK_TO_EXISTING_OWNER_WORK",
            "evidence_refs": [evidence_ref],
            "dependency_ready": False,
            "work_refs": work_refs,
        }

    if schema != GENERIC_OWNER_RECONCILIATION_SCHEMA:
        return None
    if _queue_field(body, "signal_id") != signal_ref:
        return None
    if _queue_field(body, "owner_domain") != owner_domain:
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_RECONCILIATION_DOMAIN_MISMATCH",
            "evidence_refs": [evidence_ref],
            "dependency_ready": False,
            "work_refs": [],
        }
    if _queue_field(body, "owner_main") != owner_main:
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_RECONCILIATION_STALE_MAIN",
            "evidence_refs": [evidence_ref],
            "dependency_ready": False,
            "work_refs": [],
        }
    disposition = _queue_field(body, "disposition")
    if disposition not in OWNER_DISPOSITIONS:
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_RECONCILIATION_DISPOSITION_INVALID",
            "evidence_refs": [evidence_ref],
            "dependency_ready": False,
            "work_refs": [],
        }
    dependency_ready = _queue_field(body, "dependency_ready") == "true"
    work_refs_raw = _queue_field(body, "work_refs") or ""
    work_refs = [item.strip() for item in work_refs_raw.split(",") if item.strip()]
    if disposition == "GAP_PROVEN" and not dependency_ready:
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_GAP_DEPENDENCY_NOT_READY",
            "evidence_refs": [evidence_ref],
            "dependency_ready": False,
            "work_refs": work_refs,
        }
    if disposition == "GAP_PROVEN" and work_refs:
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_GAP_CONFLICTS_WITH_EXISTING_WORK_REFS",
            "evidence_refs": [evidence_ref],
            "dependency_ready": False,
            "work_refs": work_refs,
        }
    return {
        "disposition": disposition,
        "reason": "OWNER_RECONCILIATION_EXACT_SIGNAL_RECORD",
        "evidence_refs": [evidence_ref],
        "dependency_ready": dependency_ready,
        "work_refs": work_refs,
    }


def _observe_owner_reconciliation(
    root: Path,
    *,
    repository: str,
    issue_number: int,
    signal_ref: str,
    owner_domain: str,
    owner_main: str,
    observer: Any = None,
) -> dict[str, Any]:
    if observer is None:
        observer, gateway_error = _make_owner_observer(root, repository)
    else:
        gateway_error = Exception
    try:
        _headers, main_payload, _meta = observer._get_json(
            f"/repos/{repository}/git/ref/heads/main"
        )
        _headers, issue_payload, _meta = observer._get_json(
            f"/repos/{repository}/issues/{issue_number}"
        )
    except gateway_error as exc:
        raise SignalOpportunityMaterializerError("OWNER_PROVIDER_FAILED") from exc
    if not isinstance(main_payload, Mapping):
        raise SignalOpportunityMaterializerError("OWNER_MAIN_PAYLOAD_INVALID")
    obj = main_payload.get("object")
    observed_main = obj.get("sha") if isinstance(obj, Mapping) else None
    if observed_main != owner_main:
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_MAIN_DRIFT",
            "evidence_refs": [],
            "dependency_ready": False,
            "work_refs": [],
        }
    if not isinstance(issue_payload, Mapping) or issue_payload.get("number") != issue_number:
        raise SignalOpportunityMaterializerError("OWNER_RECONCILIATION_ISSUE_INVALID")
    issue_state = issue_payload.get("state")
    records: list[tuple[int, dict[str, Any]]] = []
    issue_body = issue_payload.get("body")
    issue_url = issue_payload.get("html_url")
    if isinstance(issue_body, str):
        record = _normalize_owner_record(
            issue_body,
            signal_ref=signal_ref,
            owner_domain=owner_domain,
            owner_main=owner_main,
            evidence_ref=str(issue_url or f"github://{repository}/issues/{issue_number}"),
        )
        if record is not None:
            records.append((0, record))
    pagination_complete = False
    for page in range(1, 21):
        path = (
            f"/repos/{repository}/issues/{issue_number}/comments"
            f"?per_page=100&page={page}"
        )
        try:
            _headers, payload, _meta = observer._get_json(path)
        except gateway_error as exc:
            raise SignalOpportunityMaterializerError("OWNER_PROVIDER_FAILED") from exc
        if not isinstance(payload, list):
            raise SignalOpportunityMaterializerError("OWNER_COMMENTS_PAYLOAD_INVALID")
        for item in payload:
            if not isinstance(item, Mapping):
                raise SignalOpportunityMaterializerError("OWNER_COMMENT_INVALID")
            comment_id = item.get("id")
            body = item.get("body")
            if not isinstance(comment_id, int) or not isinstance(body, str):
                raise SignalOpportunityMaterializerError("OWNER_COMMENT_INVALID")
            record = _normalize_owner_record(
                body,
                signal_ref=signal_ref,
                owner_domain=owner_domain,
                owner_main=owner_main,
                evidence_ref=str(
                    item.get("html_url")
                    or f"github://{repository}/issues/{issue_number}#comment={comment_id}"
                ),
            )
            if record is not None:
                records.append((comment_id, record))
        if len(payload) < 100:
            pagination_complete = True
            break
    if not pagination_complete:
        raise SignalOpportunityMaterializerError("OWNER_COMMENTS_PAGINATION_INCOMPLETE")
    if not records:
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_EXACT_SIGNAL_RECONCILIATION_RECORD_REQUIRED",
            "evidence_refs": [str(issue_url or f"github://{repository}/issues/{issue_number}")],
            "dependency_ready": False,
            "work_refs": [],
        }
    result = dict(sorted(records, key=lambda pair: pair[0])[-1][1])
    if result["disposition"] == "REUSE_EXISTING_WORK" and issue_state != "open":
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_REUSE_RECORD_STALE_AFTER_ISSUE_CLOSED",
            "evidence_refs": result["evidence_refs"],
            "dependency_ready": False,
            "work_refs": result["work_refs"],
        }
    if result["disposition"] == "ALREADY_SATISFIED" and issue_state != "closed":
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_SATISFIED_RECORD_REQUIRES_CLOSED_ISSUE",
            "evidence_refs": result["evidence_refs"],
            "dependency_ready": False,
            "work_refs": result["work_refs"],
        }
    result["owner_issue_state"] = issue_state
    result["owner_main"] = owner_main
    return result


def _decision(
    *,
    signal_ref: str,
    disposition: str,
    reason: str,
    evidence_refs: Sequence[str],
    owner_binding: Mapping[str, Any] | None = None,
    opportunity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": DECISION_SCHEMA,
        "signal_ref": signal_ref,
        "disposition": disposition,
        "reason": reason,
        "evidence_refs": sorted(set(map(str, evidence_refs))),
        "owner_binding_digest": (
            owner_binding.get("binding_digest")
            if isinstance(owner_binding, Mapping) and owner_binding.get("valid") is True
            else None
        ),
        "opportunity": _copy(opportunity) if opportunity is not None else None,
        "authority_boundary": {
            "creates_signal_truth": False,
            "creates_task": False,
            "creates_issue": False,
            "creates_route": False,
            "creates_work_claim": False,
            "creates_worker_slot": False,
            "grants_execution_authority": False,
            "grants_domain_write": False,
            "grants_w3_write": False,
            "grants_merge_authority": False,
        },
    }
    value["decision_digest"] = _digest(value)
    return value


def materialize_signal_opportunity(
    repo_root: str | Path,
    ledger: Any,
    draft_value: Mapping[str, Any],
    *,
    expected_coordinator_main: str,
    domain_authority_descriptors: Sequence[Mapping[str, Any]],
    domain_authority_observations: Sequence[Mapping[str, Any]],
    authority_exact_read_proofs: Sequence[Any] = (),
    authority_live_observation_proof: Any = None,
    owner_observer: Any = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    draft = validate_draft(draft_value)
    signal_ref = draft["signal_ref"]
    try:
        _effective, origin, signal_proof_ref = _signal_origin(ledger, signal_ref)
    except SignalOpportunityMaterializerError as exc:
        return _decision(
            signal_ref=signal_ref,
            disposition="INELIGIBLE_SIGNAL_STATE",
            reason=exc.code,
            evidence_refs=[],
        )

    owner_binding = _resolve_owner_authority(
        root,
        domain_id=origin["primary_domain"],
        descriptors=domain_authority_descriptors,
        observations=domain_authority_observations,
        exact_read_proofs=authority_exact_read_proofs,
        live_observation_proof=authority_live_observation_proof,
        expected_coordinator_main=expected_coordinator_main,
    )
    if not owner_binding.get("valid"):
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason=str(owner_binding.get("reason", "DOMAIN_AUTHORITY_UNVERIFIED")),
            evidence_refs=[signal_proof_ref, *owner_binding.get("authority_refs", [])],
            owner_binding=owner_binding,
        )
    owner_repo = str(owner_binding["repository"])
    owner_main = str(owner_binding["canonical_commit"])
    owner = _observe_owner_reconciliation(
        root,
        repository=owner_repo,
        issue_number=draft["owner_reconciliation_issue"],
        signal_ref=signal_ref,
        owner_domain=origin["primary_domain"],
        owner_main=owner_main,
        observer=owner_observer,
    )
    evidence = [
        signal_proof_ref,
        *owner_binding.get("authority_refs", []),
        *owner.get("evidence_refs", []),
    ]
    if owner["disposition"] == "REUSE_EXISTING_WORK":
        return _decision(
            signal_ref=signal_ref,
            disposition="REUSE_EXISTING_OWNER_WORK",
            reason=str(owner["reason"]),
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )
    if owner["disposition"] == "ALREADY_SATISFIED":
        return _decision(
            signal_ref=signal_ref,
            disposition="ALREADY_SATISFIED",
            reason=str(owner["reason"]),
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )
    if owner["disposition"] != "GAP_PROVEN":
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason=str(owner["reason"]),
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )

    proposal = _copy(draft["task_release_proposal"])
    if proposal.get("schema_version") != "TaskReleaseProposal/v1":
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="TASK_RELEASE_PROPOSAL_SCHEMA_INVALID",
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )
    if signal_ref not in proposal.get("source_signal_refs", []):
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="SIGNAL_PROPOSAL_BINDING_MISSING",
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )
    if proposal.get("signal_primary_domain") != origin["primary_domain"]:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="PLANNER_SIGNAL_DOMAIN_MUTATION_FORBIDDEN",
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )
    if proposal.get("proposed_target_domain") != origin["primary_domain"]:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="CROSS_DOMAIN_AUTO_MATERIALIZATION_FORBIDDEN",
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )
    if proposal.get("desired_effect") != origin["desired_effect"]:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="PLANNER_DESIRED_EFFECT_MUTATION_FORBIDDEN",
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )

    candidate = {
        "schema_version": OPPORTUNITY_SCHEMA,
        "opportunity_id": f"r153-opportunity:{_digest([signal_ref, owner['owner_main'], proposal])[:24]}",
        "signal_ref": signal_ref,
        "signal_primary_domain": origin["primary_domain"],
        "source_evidence_refs": sorted(set(evidence)),
        "desired_effect": origin["desired_effect"],
        "problem_to_solve": origin["problem_to_solve"],
        "success_condition": origin["success_condition"],
        "current_disposition": "NEW_DURABLE_SIGNAL",
        "epistemic_state": origin["epistemic_state"],
        "desired_effect_gap_proven": True,
        "dependency_ready": owner.get("dependency_ready") is True,
        "priority_class": draft["priority_class"],
        "user_value_score": draft["user_value_score"],
        "materiality_score": draft["materiality_score"],
        "dependency_readiness_score": draft["dependency_readiness_score"],
        "age_cycles": draft["age_cycles"],
        "estimated_cost_score": draft["estimated_cost_score"],
        "task_release_proposal": proposal,
    }
    try:
        normalized = validate_opportunity(candidate)
    except Exception as exc:
        code = getattr(exc, "code", "R151_OPPORTUNITY_VALIDATION_FAILED")
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason=str(code),
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )
    if _exclusion_hits(_requested_side_effect_surface(normalized)):
        return _decision(
            signal_ref=signal_ref,
            disposition="INELIGIBLE_SIGNAL_STATE",
            reason="R151_STANDING_AUTO_RELEASE_EXCLUSION",
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )

    try:
        r150 = evaluate_trusted_release_proposal(
            root,
            proposal,
            expected_coordinator_main=expected_coordinator_main,
            authority_exact_read_proofs=authority_exact_read_proofs,
            authority_live_observation_proof=authority_live_observation_proof,
        )
    except TrustedReleaseError as exc:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason=f"R150_PREFLIGHT_FAILED:{exc.code}",
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )
    if r150.get("schema_version") != TRUSTED_RECEIPT_SCHEMA:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="R150_RECEIPT_INVALID",
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )
    final_disposition = r150.get("impact_receipt", {}).get("final_disposition")
    if final_disposition not in RELEASEABLE_R150:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason=f"R150_NOT_RELEASEABLE:{final_disposition or 'UNKNOWN'}",
            evidence_refs=[*evidence, f"r150://receipt/{r150.get('receipt_digest', 'UNKNOWN')}"],
            owner_binding=owner_binding,
        )
    normalized["source_evidence_refs"] = sorted(
        set(normalized["source_evidence_refs"])
        | {f"r150://receipt/{r150['receipt_digest']}"}
    )
    normalized.pop("opportunity_digest", None)
    normalized = validate_opportunity(normalized)
    return _decision(
        signal_ref=signal_ref,
        disposition="MATERIALIZED_FOR_R151",
        reason="S0C_OWNER_RECONCILIATION_R145_R150_BOUND",
        evidence_refs=normalized["source_evidence_refs"],
        owner_binding=owner_binding,
        opportunity=normalized,
    )
