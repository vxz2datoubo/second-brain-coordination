from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import re
import subprocess
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
from signal_opportunity_ranking import (
    RankingEvidenceError,
    derive_trusted_ranking_evidence,
    ranking_evidence_ref,
)
from trusted_task_release import (
    TRUSTED_RECEIPT_SCHEMA,
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
S0C_SRC = (
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
    "GLOBAL-SIGNAL-PLANE/S0-SYNTHETIC/src"
)
ELIGIBLE_PRIORITY = frozenset({P3, P4})
ELIGIBLE_EXECUTION_STATE = "NOT_STARTED"
INELIGIBLE_PLANNING_STATES = frozenset(
    {"SUPERSEDED", "CONFLICTED", "REJECTED", "CLOSED_NO_ACTION"}
)
INELIGIBLE_EPISTEMIC_STATES = frozenset({"UNKNOWN", "NEEDS_REVALIDATION"})
OWNER_DISPOSITIONS = frozenset(
    {"REUSE_EXISTING_WORK", "ALREADY_SATISFIED", "GAP_PROVEN", "NEEDS_REVALIDATION"}
)
RELEASEABLE_R150 = frozenset(
    {"RELEASE_BOUNDED_TASK", "RELEASE_AS_EXTENSION", "RELEASE_AS_ADAPTER_OR_PLUGIN"}
)
TRUSTED_GITHUB_ASSOCIATIONS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
TRUSTED_CONNECTOR_APP = "chatgpt-codex-connector"
MAX_OWNER_PAGES = 20
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_OWNER_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

# Compatibility baseline retained for the accepted R153 fixture/regressions only.
# The production materialization path no longer expands this constant; R154
# derives the authority-bearing rank vector from trusted evidence instead.
TRUSTED_NEUTRAL_RANKING = {
    "priority_class": P3,
    "user_value_score": 50,
    "materiality_score": 50,
    "dependency_readiness_score": 100,
    "age_cycles": 0,
    "estimated_cost_score": 50,
}


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


def _positive_int(value: Any, code: str) -> int:
    if isinstance(value, bool):
        raise SignalOpportunityMaterializerError(code)
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise SignalOpportunityMaterializerError(code) from exc
    if parsed <= 0:
        raise SignalOpportunityMaterializerError(code)
    return parsed


def _git_head(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SignalOpportunityMaterializerError("COORDINATOR_GIT_HEAD_UNAVAILABLE") from exc


def _load_module_from_src(root: Path, src_rel: str, module_name: str, code: str) -> Any:
    src = (root / src_rel).resolve()
    if not src.is_dir():
        raise SignalOpportunityMaterializerError(f"{code}_SOURCE_MISSING")
    original = list(sys.path)
    try:
        sys.path.insert(0, str(src))
        return importlib.import_module(module_name)
    except (ImportError, OSError) as exc:
        raise SignalOpportunityMaterializerError(f"{code}_LOAD_FAILED") from exc
    finally:
        sys.path[:] = original


def _load_r145_api(root: Path) -> tuple[type[Any], type[BaseException]]:
    module = _load_module_from_src(
        root, R145_SRC, "global_signal_gateway.domain_authority", "R145"
    )
    resolver = getattr(module, "DomainAuthorityResolver", None)
    domain_error = getattr(module, "DomainAuthorityError", None)
    if not isinstance(resolver, type) or not isinstance(domain_error, type):
        raise SignalOpportunityMaterializerError("R145_API_INCOMPLETE")
    return resolver, domain_error


def _load_s0c_ledger_type(root: Path) -> type[Any]:
    module = _load_module_from_src(root, S0C_SRC, "global_signal_plane.ledger", "S0C")
    ledger_type = getattr(module, "DurableSignalLedger", None)
    if not isinstance(ledger_type, type):
        raise SignalOpportunityMaterializerError("S0C_API_INCOMPLETE")
    return ledger_type


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
    _positive_int(out["owner_reconciliation_issue"], "OWNER_RECONCILIATION_ISSUE_INVALID")
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


def _projection_and_history(
    root: Path, ledger: Any
) -> tuple[Mapping[str, Any], list[dict[str, Any]]]:
    """Read S0C truth and prove the stored projection equals canonical replay.

    The replay intentionally calls the retained S0C reducer itself.  R153 does
    not reimplement reducer semantics and does not mutate the durable ledger.
    """
    ledger_type = _load_s0c_ledger_type(root)
    if type(ledger) is not ledger_type:
        raise SignalOpportunityMaterializerError("CANONICAL_S0C_LEDGER_INSTANCE_REQUIRED")

    revision_before = ledger.input_revision()
    projection = ledger.current_projection()
    if projection is None:
        raise SignalOpportunityMaterializerError("S0C_PROJECTION_REQUIRED")
    if not isinstance(projection, Mapping):
        raise SignalOpportunityMaterializerError("S0C_PROJECTION_INVALID")

    history = ledger.history()
    if not isinstance(history, list) or not all(isinstance(item, Mapping) for item in history):
        raise SignalOpportunityMaterializerError("S0C_HISTORY_INVALID")

    reducer = getattr(ledger, "_reduce", None)
    if not callable(reducer):
        raise SignalOpportunityMaterializerError("S0C_CANONICAL_REDUCER_UNAVAILABLE")
    replay = reducer()
    revision_after = ledger.input_revision()
    if revision_before != revision_after:
        raise SignalOpportunityMaterializerError("S0C_INPUT_REVISION_DRIFT")
    if not isinstance(replay, Mapping):
        raise SignalOpportunityMaterializerError("S0C_CANONICAL_REPLAY_INVALID")

    if projection.get("ledger_watermark") != len(history):
        raise SignalOpportunityMaterializerError("S0C_LEDGER_WATERMARK_MISMATCH")
    if projection.get("input_revision") != revision_after:
        raise SignalOpportunityMaterializerError("S0C_INPUT_REVISION_MISMATCH")
    if replay.get("ledger_watermark") != len(history) or replay.get("input_revision") != revision_after:
        raise SignalOpportunityMaterializerError("S0C_CANONICAL_REPLAY_REVISION_MISMATCH")

    reducer_version = projection.get("reducer_version")
    checksum = projection.get("checksum")
    if not isinstance(checksum, str) or len(checksum) != 64 or not isinstance(reducer_version, str):
        raise SignalOpportunityMaterializerError("S0C_PROJECTION_PROOF_INVALID")
    if replay.get("reducer_version") != reducer_version:
        raise SignalOpportunityMaterializerError("S0C_REDUCER_VERSION_MISMATCH")

    projection_core = {
        key: value
        for key, value in projection.items()
        if key not in {"checksum", "projection_version", "generated_at"}
    }
    if _canonical(projection_core) != _canonical(replay):
        raise SignalOpportunityMaterializerError("S0C_PROJECTION_REPLAY_MISMATCH")
    if checksum != _digest(replay):
        raise SignalOpportunityMaterializerError("S0C_PROJECTION_CHECKSUM_MISMATCH")

    return dict(projection), [dict(item) for item in history]


def _signal_origin(
    root: Path, ledger: Any, signal_ref: str
) -> tuple[dict[str, Any], dict[str, Any], str]:
    projection, history = _projection_and_history(root, ledger)
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
    signal_kind = _nonempty(origin.get("signal_kind"), "/s0c/signal_kind")
    origin_offset = origin.get("ledger_offset")
    watermark = projection.get("ledger_watermark")
    if (
        isinstance(origin_offset, bool)
        or not isinstance(origin_offset, int)
        or origin_offset <= 0
        or isinstance(watermark, bool)
        or not isinstance(watermark, int)
        or watermark <= 0
        or origin_offset > watermark
    ):
        raise SignalOpportunityMaterializerError("S0C_SIGNAL_LEDGER_POSITION_INVALID")
    metadata = origin["public_safe_metadata"]
    envelope = dict(metadata["intent_envelope"])
    route = metadata.get("route") if isinstance(metadata, Mapping) else None
    materiality_class = route.get("materiality_class") if isinstance(route, Mapping) else None
    signal_proof_ref = (
        f"s0c://signal/{signal_ref}"
        f"#reducer={projection['reducer_version']};watermark={projection['ledger_watermark']}"
        f";input_revision={projection['input_revision']};sha256={projection['checksum']}"
    )
    return effective, {
        "signal_ref": signal_ref,
        "primary_domain": primary_domain,
        "signal_kind": signal_kind,
        "materiality_class": materiality_class,
        "origin_ledger_offset": origin_offset,
        "ledger_watermark": watermark,
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
            if re.fullmatch(escaped + r"/pulls/[1-9][0-9]*", path):
                return True
            if re.fullmatch(
                escaped + r"/issues/[1-9][0-9]*/comments\?per_page=100&page=[1-9][0-9]*",
                path,
            ):
                return True
            return super()._dynamic_domain_endpoint_allowed(path)

    return _OwnerObserver(), gateway_error


def _trusted_owner_actor(raw: Mapping[str, Any], repository: str) -> bool:
    user = raw.get("user")
    login = user.get("login") if isinstance(user, Mapping) else None
    repository_owner = repository.split("/", 1)[0]
    if login == repository_owner:
        return True
    association = str(raw.get("author_association", "")).upper()
    app = raw.get("performed_via_github_app")
    app_slug = app.get("slug") if isinstance(app, Mapping) else None
    return association in TRUSTED_GITHUB_ASSOCIATIONS and app_slug == TRUSTED_CONNECTOR_APP


def _record_int(body: str, name: str) -> int | None:
    raw = _queue_field(body, name)
    if raw is None or not raw.isdigit():
        return None
    value = int(raw)
    return value if value > 0 else None


def _normalize_owner_record(
    body: str,
    *,
    signal_ref: str,
    owner_domain: str,
    owner_project: str,
    owner_main: str,
    evidence_ref: str,
    container_issue: int,
) -> dict[str, Any] | None:
    schema = _queue_field(body, "schema")
    if schema == AI_FILM_REUSE_HANDOFF_SCHEMA:
        if _queue_field(body, "source_signal_id") != signal_ref:
            return None
        declared_owner = _queue_field(body, "owner_domain")
        if declared_owner not in {owner_domain, owner_project}:
            return {
                "disposition": "NEEDS_REVALIDATION",
                "reason": "OWNER_RECONCILIATION_DOMAIN_MISMATCH",
                "evidence_refs": [evidence_ref],
                "dependency_ready": False,
                "work_refs": [],
            }
        if _queue_field(body, "current_main") != owner_main:
            return {
                "disposition": "NEEDS_REVALIDATION",
                "reason": "OWNER_RECONCILIATION_STALE_MAIN",
                "evidence_refs": [evidence_ref],
                "dependency_ready": False,
                "work_refs": [],
            }
        if _queue_field(body, "reconciliation") != "REUSE_EXTEND_EXISTING_WORK":
            return None
        existing_issue = _record_int(body, "existing_issue")
        existing_pr = _record_int(body, "existing_pr")
        exact_head = _queue_field(body, "existing_exact_head")
        review_queue = _record_int(body, "review_queue")
        review_state = _queue_field(body, "review_state")
        proof_ref = _queue_field(body, "source_proof_git_ref")
        if (
            existing_issue != container_issue
            or existing_pr is None
            or exact_head is None
            or not _SHA40.fullmatch(exact_head)
            or not proof_ref
        ):
            return {
                "disposition": "NEEDS_REVALIDATION",
                "reason": "OWNER_REUSE_HANDOFF_BINDING_INVALID",
                "evidence_refs": [evidence_ref],
                "dependency_ready": False,
                "work_refs": [],
            }
        if (review_queue is None) != (review_state is None):
            return {
                "disposition": "NEEDS_REVALIDATION",
                "reason": "OWNER_REVIEW_LINEAGE_BINDING_INVALID",
                "evidence_refs": [evidence_ref],
                "dependency_ready": False,
                "work_refs": [],
            }
        return {
            "disposition": "REUSE_EXISTING_WORK",
            "reason": "EXACT_SIGNAL_BACKLINK_TO_EXISTING_OWNER_WORK",
            "evidence_refs": [evidence_ref],
            "dependency_ready": False,
            "work_refs": [
                f"github://{owner_project or owner_domain}/issue/{existing_issue}",
                f"github://{owner_project or owner_domain}/pr/{existing_pr}@{exact_head}",
            ],
            "existing_issue": existing_issue,
            "existing_pr": existing_pr,
            "existing_exact_head": exact_head,
            "review_queue": review_queue,
            "review_state": review_state,
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
    if _record_int(body, "reconciliation_issue") != container_issue:
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_RECONCILIATION_CONTAINER_UNBOUND",
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

    normalized: dict[str, Any] = {
        "disposition": disposition,
        "reason": "OWNER_RECONCILIATION_EXACT_SIGNAL_RECORD",
        "evidence_refs": [evidence_ref],
        "dependency_ready": dependency_ready,
        "work_refs": work_refs,
    }
    if disposition == "REUSE_EXISTING_WORK":
        existing_issue = _record_int(body, "existing_issue")
        existing_pr = _record_int(body, "existing_pr")
        exact_head = _queue_field(body, "existing_exact_head")
        review_queue = _record_int(body, "review_queue")
        review_state = _queue_field(body, "review_state")
        if (
            existing_issue != container_issue
            or existing_pr is None
            or exact_head is None
            or not _SHA40.fullmatch(exact_head)
        ):
            return {
                "disposition": "NEEDS_REVALIDATION",
                "reason": "OWNER_REUSE_HANDOFF_BINDING_INVALID",
                "evidence_refs": [evidence_ref],
                "dependency_ready": False,
                "work_refs": [],
            }
        normalized.update(
            existing_issue=existing_issue,
            existing_pr=existing_pr,
            existing_exact_head=exact_head,
            review_queue=review_queue,
            review_state=review_state,
        )
    return normalized


def _fetch_paginated_comments(
    observer: Any,
    gateway_error: type[BaseException],
    repository: str,
    issue_number: int,
) -> list[Mapping[str, Any]]:
    comments: list[Mapping[str, Any]] = []
    for page in range(1, MAX_OWNER_PAGES + 1):
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
            comments.append(item)
        if len(payload) < 100:
            return comments
    raise SignalOpportunityMaterializerError("OWNER_COMMENTS_PAGINATION_INCOMPLETE")


def _verify_review_queue_ticket(
    observer: Any,
    gateway_error: type[BaseException],
    *,
    repository: str,
    queue_issue: int,
    owner_project: str,
    pr_number: int,
    exact_head: str,
    expected_state: str,
) -> tuple[bool, str, list[str]]:
    try:
        _headers, queue_payload, _meta = observer._get_json(
            f"/repos/{repository}/issues/{queue_issue}"
        )
    except gateway_error as exc:
        raise SignalOpportunityMaterializerError("OWNER_PROVIDER_FAILED") from exc
    if (
        not isinstance(queue_payload, Mapping)
        or queue_payload.get("number") != queue_issue
        or queue_payload.get("state") != "open"
    ):
        return False, "OWNER_REVIEW_QUEUE_NOT_CURRENT", []

    events: list[dict[str, Any]] = []
    evidence_refs: list[str] = []
    for raw in _fetch_paginated_comments(observer, gateway_error, repository, queue_issue):
        comment_id = raw.get("id")
        body = raw.get("body")
        if not isinstance(comment_id, int) or not isinstance(body, str):
            raise SignalOpportunityMaterializerError("OWNER_COMMENT_INVALID")
        if not _trusted_owner_actor(raw, repository):
            continue
        schema = _queue_field(body, "schema")
        if schema not in {"REVIEW_REQUEST/v1", "REVIEW_RESULT/v1"}:
            continue
        if _queue_field(body, "project") != owner_project:
            continue
        pr_raw = _queue_field(body, "pr")
        if pr_raw is None or not pr_raw.isdigit() or int(pr_raw) != pr_number:
            continue
        head = (
            _queue_field(body, "exact_head")
            if schema == "REVIEW_REQUEST/v1"
            else _queue_field(body, "reviewed_head")
        )
        if head is None or not _SHA40.fullmatch(head):
            return False, "OWNER_REVIEW_QUEUE_HEAD_INVALID", evidence_refs
        ref = str(
            raw.get("html_url")
            or f"github://{repository}/issues/{queue_issue}#comment={comment_id}"
        )
        evidence_refs.append(ref)
        event: dict[str, Any] = {
            "comment_id": comment_id,
            "schema": schema,
            "head": head,
            "evidence_ref": ref,
        }
        if schema == "REVIEW_REQUEST/v1":
            if _queue_field(body, "status") != "WAITING_REVIEW":
                return False, "OWNER_REVIEW_QUEUE_STATUS_INVALID", evidence_refs
            event["state"] = "WAITING_REVIEW"
        else:
            verdict = _queue_field(body, "verdict")
            if verdict not in {"ACCEPT", "CHANGES_REQUIRED", "BLOCKED"}:
                return False, "OWNER_REVIEW_QUEUE_VERDICT_INVALID", evidence_refs
            event["state"] = verdict
        events.append(event)

    requests = [event for event in events if event["schema"] == "REVIEW_REQUEST/v1"]
    if not requests:
        return False, "OWNER_REVIEW_REQUEST_MISSING", evidence_refs
    current_request = sorted(requests, key=lambda item: int(item["comment_id"]))[-1]
    if current_request["head"] != exact_head:
        return False, "OWNER_REVIEW_LINEAGE_STALE_HEAD", evidence_refs
    same_ticket = [event for event in events if event["head"] == exact_head]
    current_event = sorted(same_ticket, key=lambda item: int(item["comment_id"]))[-1]
    if current_event["state"] != expected_state:
        return False, "OWNER_REVIEW_LINEAGE_STATE_DRIFT", evidence_refs
    return True, "OWNER_REVIEW_LINEAGE_CURRENT", evidence_refs


def _verify_reuse_work(
    observer: Any,
    gateway_error: type[BaseException],
    *,
    repository: str,
    owner_project: str,
    owner_main: str,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    existing_issue = record.get("existing_issue")
    existing_pr = record.get("existing_pr")
    exact_head = record.get("existing_exact_head")
    if (
        not isinstance(existing_issue, int)
        or not isinstance(existing_pr, int)
        or not isinstance(exact_head, str)
        or not _SHA40.fullmatch(exact_head)
    ):
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_REUSE_HANDOFF_BINDING_INVALID",
            "evidence_refs": list(record.get("evidence_refs", [])),
            "dependency_ready": False,
            "work_refs": [],
        }
    try:
        _headers, issue_payload, _meta = observer._get_json(
            f"/repos/{repository}/issues/{existing_issue}"
        )
        _headers, pr_payload, _meta = observer._get_json(
            f"/repos/{repository}/pulls/{existing_pr}"
        )
    except gateway_error as exc:
        raise SignalOpportunityMaterializerError("OWNER_PROVIDER_FAILED") from exc

    issue_ref = f"https://github.com/{repository}/issues/{existing_issue}"
    pr_ref = f"https://github.com/{repository}/pull/{existing_pr}"
    evidence = [*record.get("evidence_refs", []), issue_ref, pr_ref]
    if (
        not isinstance(issue_payload, Mapping)
        or issue_payload.get("number") != existing_issue
        or issue_payload.get("state") != "open"
    ):
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_REFERENCED_ISSUE_NOT_OPEN",
            "evidence_refs": evidence,
            "dependency_ready": False,
            "work_refs": list(record.get("work_refs", [])),
        }
    if not isinstance(pr_payload, Mapping) or pr_payload.get("number") != existing_pr:
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_REFERENCED_PR_INVALID",
            "evidence_refs": evidence,
            "dependency_ready": False,
            "work_refs": list(record.get("work_refs", [])),
        }
    if pr_payload.get("state") != "open" or pr_payload.get("merged_at") is not None:
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_REFERENCED_PR_NOT_OPEN",
            "evidence_refs": evidence,
            "dependency_ready": False,
            "work_refs": list(record.get("work_refs", [])),
        }
    head = pr_payload.get("head")
    base = pr_payload.get("base")
    observed_head = head.get("sha") if isinstance(head, Mapping) else None
    if observed_head != exact_head:
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_REFERENCED_PR_HEAD_DRIFT",
            "evidence_refs": evidence,
            "dependency_ready": False,
            "work_refs": list(record.get("work_refs", [])),
        }
    if (
        not isinstance(base, Mapping)
        or base.get("ref") != "main"
        or base.get("sha") != owner_main
    ):
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_REFERENCED_PR_BASE_DRIFT",
            "evidence_refs": evidence,
            "dependency_ready": False,
            "work_refs": list(record.get("work_refs", [])),
        }

    review_queue = record.get("review_queue")
    review_state = record.get("review_state")
    if review_queue is not None or review_state is not None:
        if not isinstance(review_queue, int) or not isinstance(review_state, str):
            return {
                "disposition": "NEEDS_REVALIDATION",
                "reason": "OWNER_REVIEW_LINEAGE_BINDING_INVALID",
                "evidence_refs": evidence,
                "dependency_ready": False,
                "work_refs": list(record.get("work_refs", [])),
            }
        ok, reason, review_refs = _verify_review_queue_ticket(
            observer,
            gateway_error,
            repository=repository,
            queue_issue=review_queue,
            owner_project=owner_project,
            pr_number=existing_pr,
            exact_head=exact_head,
            expected_state=review_state,
        )
        evidence.extend(review_refs)
        if not ok:
            return {
                "disposition": "NEEDS_REVALIDATION",
                "reason": reason,
                "evidence_refs": sorted(set(evidence)),
                "dependency_ready": False,
                "work_refs": list(record.get("work_refs", [])),
            }

    verified = dict(record)
    verified["reason"] = "EXACT_CURRENT_OWNER_WORK_VERIFIED"
    verified["evidence_refs"] = sorted(set(evidence))
    return verified


def _observe_owner_reconciliation(
    root: Path,
    *,
    repository: str,
    issue_number: int,
    signal_ref: str,
    owner_domain: str,
    owner_project: str,
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
    issue_url = str(
        issue_payload.get("html_url") or f"https://github.com/{repository}/issues/{issue_number}"
    )
    trusted_records: list[tuple[int, dict[str, Any]]] = []
    untrusted_matching_record = False

    issue_body = issue_payload.get("body")
    if isinstance(issue_body, str):
        record = _normalize_owner_record(
            issue_body,
            signal_ref=signal_ref,
            owner_domain=owner_domain,
            owner_project=owner_project,
            owner_main=owner_main,
            evidence_ref=issue_url,
            container_issue=issue_number,
        )
        if record is not None:
            if _trusted_owner_actor(issue_payload, repository):
                trusted_records.append((0, record))
            else:
                untrusted_matching_record = True

    for item in _fetch_paginated_comments(observer, gateway_error, repository, issue_number):
        comment_id = item.get("id")
        body = item.get("body")
        if not isinstance(comment_id, int) or not isinstance(body, str):
            raise SignalOpportunityMaterializerError("OWNER_COMMENT_INVALID")
        evidence_ref = str(
            item.get("html_url")
            or f"github://{repository}/issues/{issue_number}#comment={comment_id}"
        )
        record = _normalize_owner_record(
            body,
            signal_ref=signal_ref,
            owner_domain=owner_domain,
            owner_project=owner_project,
            owner_main=owner_main,
            evidence_ref=evidence_ref,
            container_issue=issue_number,
        )
        if record is None:
            continue
        if _trusted_owner_actor(item, repository):
            trusted_records.append((comment_id, record))
        else:
            untrusted_matching_record = True

    if not trusted_records:
        return {
            "disposition": "NEEDS_REVALIDATION",
            "reason": (
                "OWNER_RECONCILIATION_UNTRUSTED_PROVENANCE"
                if untrusted_matching_record
                else "OWNER_EXACT_SIGNAL_RECONCILIATION_RECORD_REQUIRED"
            ),
            "evidence_refs": [issue_url],
            "dependency_ready": False,
            "work_refs": [],
        }

    result = dict(sorted(trusted_records, key=lambda pair: pair[0])[-1][1])
    if result["disposition"] == "REUSE_EXISTING_WORK":
        result = _verify_reuse_work(
            observer,
            gateway_error,
            repository=repository,
            owner_project=owner_project,
            owner_main=owner_main,
            record=result,
        )
    elif result["disposition"] == "ALREADY_SATISFIED":
        if issue_state != "closed":
            result = {
                "disposition": "NEEDS_REVALIDATION",
                "reason": "OWNER_SATISFIED_RECORD_REQUIRES_CLOSED_ISSUE",
                "evidence_refs": result["evidence_refs"],
                "dependency_ready": False,
                "work_refs": result["work_refs"],
            }
    elif result["disposition"] == "GAP_PROVEN" and issue_state != "open":
        result = {
            "disposition": "NEEDS_REVALIDATION",
            "reason": "OWNER_GAP_RECORD_REQUIRES_OPEN_RECONCILIATION_ISSUE",
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
    if _git_head(root) != expected_coordinator_main:
        raise SignalOpportunityMaterializerError("CANONICAL_MAIN_DRIFT")
    draft = validate_draft(draft_value)
    signal_ref = draft["signal_ref"]
    try:
        _effective, origin, signal_proof_ref = _signal_origin(root, ledger, signal_ref)
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
    owner_project = str(owner_binding.get("project_id") or origin["primary_domain"])
    owner = _observe_owner_reconciliation(
        root,
        repository=owner_repo,
        issue_number=draft["owner_reconciliation_issue"],
        signal_ref=signal_ref,
        owner_domain=origin["primary_domain"],
        owner_project=owner_project,
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

    try:
        ranking = derive_trusted_ranking_evidence(
            signal_ref=signal_ref,
            signal_proof_ref=signal_proof_ref,
            signal_kind=origin["signal_kind"],
            materiality_class=origin.get("materiality_class"),
            origin_ledger_offset=origin["origin_ledger_offset"],
            ledger_watermark=origin["ledger_watermark"],
            dependency_ready=owner.get("dependency_ready") is True,
            task_release_proposal=proposal,
            source_evidence_refs=evidence,
        )
        ranking_ref = ranking_evidence_ref(ranking)
    except RankingEvidenceError as exc:
        return _decision(
            signal_ref=signal_ref,
            disposition=(
                "INELIGIBLE_SIGNAL_STATE"
                if exc.code == "HIGH_RISK_SIGNAL_NOT_IDLE_RANKABLE"
                else "NEEDS_REVALIDATION"
            ),
            reason=f"R154_RANKING_FAILED:{exc.code}",
            evidence_refs=evidence,
            owner_binding=owner_binding,
        )
    evidence = sorted(set([*evidence, ranking_ref]))
    rank_vector = dict(ranking["rank_vector"])

    candidate = {
        "schema_version": OPPORTUNITY_SCHEMA,
        "opportunity_id": f"r153-opportunity:{_digest([signal_ref, owner_main, proposal])[:24]}",
        "signal_ref": signal_ref,
        "signal_primary_domain": origin["primary_domain"],
        "source_evidence_refs": evidence,
        "desired_effect": origin["desired_effect"],
        "problem_to_solve": origin["problem_to_solve"],
        "success_condition": origin["success_condition"],
        "current_disposition": "NEW_DURABLE_SIGNAL",
        "epistemic_state": origin["epistemic_state"],
        "desired_effect_gap_proven": True,
        "dependency_ready": owner.get("dependency_ready") is True,
        **rank_vector,
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
    impact_receipt = r150.get("impact_receipt")
    final_disposition = (
        impact_receipt.get("final_disposition")
        if isinstance(impact_receipt, Mapping)
        else None
    )
    if final_disposition not in RELEASEABLE_R150:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason=f"R150_NOT_RELEASEABLE:{final_disposition or 'UNKNOWN'}",
            evidence_refs=[
                *evidence,
                f"r150://receipt/{r150.get('receipt_digest', 'UNKNOWN')}",
            ],
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
        reason="S0C_OWNER_RECONCILIATION_R145_R154_R150_BOUND",
        evidence_refs=normalized["source_evidence_refs"],
        owner_binding=owner_binding,
        opportunity=normalized,
    )