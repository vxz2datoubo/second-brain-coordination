from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

STATUS_SCHEMA = "REVIEW_CYCLE_STATUS/v1"
PROVENANCE_SCHEMA = "REVIEW_LIVENESS_PROVENANCE/v1"
LIVE_OBSERVATION_SCHEMA = "REVIEW_LIVENESS_LIVE_OBSERVATION/v1"

PROJECT_DIRECTORY = {
    "SECOND_BRAIN": ("vxz2datoubo/second-brain-coordination", 453),
    "AI_WORLD_SIMULATION_ENGINE": ("vxz2datoubo/ai-world-simulation-engine", 50),
    "EUSTIA_AI_FILM": ("vxz2datoubo/eustia-ai-film", 15),
}

REQUIRED_LIVENESS_SURFACES = frozenset(
    {
        "REVIEW_QUEUE",
        "PR_STATE",
        "CI_PROVENANCE",
        "CANONICALIZATION",
        "CONTROL_TOWER_RELEASE",
        "ENGINEERING_IMPLEMENTATION",
        "REMEDIATION_REQUEUE",
        "STALE_REQUEST_SCAN",
        "FINAL_FRESHNESS_READBACK",
    }
)

STALL_CLASSES = {
    "ACCEPTED_NOT_CANONICALIZED": ("BLOCKED", "CANONICALIZER"),
    "CANONICALIZED_NOT_RELEASED": ("BLOCKED", "CONTROL_TOWER"),
    "RELEASED_NOT_IMPLEMENTED": ("ACTIVE", "ENGINEERING"),
    "IMPLEMENTED_NOT_QUEUED": ("BLOCKED", "ENGINEERING"),
    "REMEDIATION_NOT_REQUEUED": ("BLOCKED", "ENGINEERING"),
    "STALE_REVIEW_REQUEST": ("BLOCKED", "ENGINEERING"),
    "CI_OR_PROVENANCE_BLOCKED": ("BLOCKED", "ENGINEERING"),
    "NORMAL_IDLE": ("IDLE", "NONE"),
    "UNKNOWN_BLOCKED": ("UNKNOWN", "UNKNOWN"),
}

_REQUEST_SCHEMA = "REVIEW_REQUEST/v1"
_RESULT_SCHEMA = "REVIEW_RESULT/v1"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_FIELD = re.compile(r"(?m)^[ \t]*{name}[ \t]*:[ \t]*[`'\"]?([^`'\"\n\r]+)")
_COMPLETION_MARKERS = (
    "READY_FOR_INDEPENDENT_REVIEW",
    "READY_FOR_RE-REVIEW",
    "READY_FOR_INDEPENDENT_RE_REVIEW",
    "completion_signal:",
    "Completion signal:",
)
_RELEASE_MARKERS = (
    "CONTROL_TOWER_RELEASED",
    "BOUNDED_ENGINEERING_AUTHORIZED",
    "GPT_REMEDIATION_RELEASE/v1",
)
_IMPLEMENTED_MARKERS = (
    "ENGINEERING_COMPLETE",
    "IMPLEMENTATION_COMPLETE",
    "READY_FOR_INDEPENDENT_REVIEW",
)
_CI_BAD_CONCLUSIONS = frozenset(
    {"failure", "cancelled", "timed_out", "action_required", "startup_failure"}
)
_CI_OK_CONCLUSIONS = frozenset({"success", "neutral"})
_CI_INFLIGHT = frozenset({"queued", "in_progress", "pending", "waiting", "requested"})


class ReviewPipelineLivenessError(ValueError):
    pass


@dataclass(frozen=True)
class SurfaceReadAttestation:
    """Evidence-only compatibility object; never freshness authority."""

    surface: str
    source_ref: str
    observed_revision: str
    observed_main_sha: str
    complete: bool


@dataclass(frozen=True)
class LivenessProvenanceEnvelope:
    """Evidence-only compatibility envelope.

    Historical callers may serialize it, but its contents cannot mint trusted
    freshness. NORMAL_IDLE is produced only by observe_review_cycle() after
    internally constructed live GitHub reads and a final freshness readback.
    """

    schema: str
    repository: str
    queue_issue: int
    canonical_main_sha: str
    queue_snapshot_ref: str
    surface_reads: tuple[SurfaceReadAttestation, ...]


@dataclass(frozen=True)
class LivenessEvidence:
    project: str
    repository: str
    queue_issue: int
    pending_exact_head_tickets: int
    reviewed_this_cycle: int = 0
    accepted_not_canonicalized_ref: str | None = None
    canonicalized_not_released_ref: str | None = None
    released_not_implemented_ref: str | None = None
    implemented_not_queued_ref: str | None = None
    remediation_not_requeued_ref: str | None = None
    stale_review_request_ref: str | None = None
    ci_or_provenance_blocked_ref: str | None = None
    provenance: LivenessProvenanceEnvelope | None = None
    prior_stall_fingerprint: str | None = None
    prior_stall_repeat_count: int = 0


@dataclass(frozen=True)
class _Snapshot:
    main_sha: str
    queue_digest: str
    open_pr_digest: str
    open_issue_digest: str


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _require_nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewPipelineLivenessError(f"{name}_REQUIRED")
    return value.strip()


def _validate_count(value: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ReviewPipelineLivenessError(f"{name}_INVALID")
    return value


def _validate_issue_number(value: int, name: str) -> int:
    value = _validate_count(value, name)
    if value == 0:
        raise ReviewPipelineLivenessError(f"{name}_INVALID")
    return value


def _is_full_sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA40.fullmatch(value) is not None


def _field(body: Any, name: str) -> str | None:
    if not isinstance(body, str):
        return None
    match = re.search(_FIELD.pattern.format(name=re.escape(name)), body)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def _int_field(body: Any, name: str) -> int | None:
    value = _field(body, name)
    if value is None:
        return None
    if value.startswith("#"):
        value = value[1:]
    return int(value) if value.isdigit() else None


def _head_from_pr(raw: Mapping[str, Any]) -> str | None:
    head = raw.get("head")
    if isinstance(head, Mapping):
        sha = head.get("sha")
        if _is_full_sha(sha):
            return str(sha)
    return None


def _merged(raw: Mapping[str, Any]) -> bool:
    return raw.get("merged") is True or raw.get("merged_at") is not None


def _select_blocker(
    evidence: LivenessEvidence, *, trusted_idle: bool = False
) -> tuple[str, str | None]:
    if evidence.pending_exact_head_tickets > 0:
        return "PENDING_REVIEW", None
    ordered = (
        ("STALE_REVIEW_REQUEST", evidence.stale_review_request_ref),
        ("CI_OR_PROVENANCE_BLOCKED", evidence.ci_or_provenance_blocked_ref),
        ("ACCEPTED_NOT_CANONICALIZED", evidence.accepted_not_canonicalized_ref),
        ("CANONICALIZED_NOT_RELEASED", evidence.canonicalized_not_released_ref),
        ("REMEDIATION_NOT_REQUEUED", evidence.remediation_not_requeued_ref),
        ("IMPLEMENTED_NOT_QUEUED", evidence.implemented_not_queued_ref),
        ("RELEASED_NOT_IMPLEMENTED", evidence.released_not_implemented_ref),
    )
    for blocker_class, ref in ordered:
        if ref:
            return blocker_class, ref
    if trusted_idle:
        return "NORMAL_IDLE", None
    return "UNKNOWN_BLOCKED", None


def _classify(
    evidence: LivenessEvidence, *, trusted_idle: bool = False
) -> dict[str, Any]:
    project = _require_nonempty(evidence.project, "PROJECT")
    repository = _require_nonempty(evidence.repository, "REPOSITORY")
    queue_issue = _validate_issue_number(evidence.queue_issue, "QUEUE_ISSUE")
    pending = _validate_count(evidence.pending_exact_head_tickets, "PENDING_TICKETS")
    reviewed = _validate_count(evidence.reviewed_this_cycle, "REVIEWED_THIS_CYCLE")
    prior_repeat = _validate_count(
        evidence.prior_stall_repeat_count, "PRIOR_REPEAT_COUNT"
    )
    directory = PROJECT_DIRECTORY.get(project)
    if directory is not None and directory != (repository, queue_issue):
        raise ReviewPipelineLivenessError("PROJECT_QUEUE_BINDING_MISMATCH")

    blocker_class, blocking_ref = _select_blocker(
        evidence, trusted_idle=trusted_idle
    )
    if blocker_class == "PENDING_REVIEW":
        pipeline_status = "ACTIVE"
        next_role = "INDEPENDENT_REVIEWER"
        next_action = "REVIEW_PENDING_EXACT_HEAD_TICKETS"
        fingerprint = "NONE"
    else:
        pipeline_status, next_role = STALL_CLASSES[blocker_class]
        action_by_class = {
            "ACCEPTED_NOT_CANONICALIZED": "CANONICALIZE_ACCEPTED_EXACT_HEAD",
            "CANONICALIZED_NOT_RELEASED": "FRESH_RECONCILE_AND_DECIDE_NEXT_RELEASE",
            "RELEASED_NOT_IMPLEMENTED": "START_BOUNDED_ENGINEERING_SLICE",
            "IMPLEMENTED_NOT_QUEUED": "POST_CANONICAL_REVIEW_REQUEST_FOR_EXACT_HEAD",
            "REMEDIATION_NOT_REQUEUED": "POST_NEW_REVIEW_REQUEST_FOR_REMEDIATED_HEAD",
            "STALE_REVIEW_REQUEST": "REQUEUE_CURRENT_EXACT_HEAD_OR_FIX_STALE_REQUEST",
            "CI_OR_PROVENANCE_BLOCKED": "RESTORE_REQUIRED_EXACT_HEAD_CI_OR_PROVENANCE",
            "NORMAL_IDLE": "NONE",
            "UNKNOWN_BLOCKED": "OBTAIN_MISSING_FRESH_GITHUB_EVIDENCE",
        }
        next_action = action_by_class[blocker_class]
        if blocker_class in {"NORMAL_IDLE", "UNKNOWN_BLOCKED"}:
            fingerprint = (
                "NONE"
                if blocker_class == "NORMAL_IDLE"
                else f"{project}|UNKNOWN_BLOCKED|{queue_issue}"
            )
        else:
            fingerprint = f"{project}|{blocker_class}|{blocking_ref}"

    repeated = (
        fingerprint != "NONE" and fingerprint == evidence.prior_stall_fingerprint
    )
    repeat_count = (
        prior_repeat + 1 if repeated else (1 if fingerprint != "NONE" else 0)
    )
    return {
        "schema": STATUS_SCHEMA,
        "project": project,
        "queue_issue": queue_issue,
        "pending_exact_head_tickets": pending,
        "reviewed_this_cycle": reviewed,
        "pipeline_status": pipeline_status,
        "blocker_class": blocker_class if blocker_class != "PENDING_REVIEW" else "NONE",
        "blocking_ref": blocking_ref or "NONE",
        "next_authority_role": next_role,
        "next_required_action": next_action,
        "stall_fingerprint": fingerprint,
        "stall_repeat_count": repeat_count,
        "new_evidence": not repeated,
        "reviewer_mutations": "NONE",
    }


def classify_review_cycle(evidence: LivenessEvidence) -> dict[str, Any]:
    """Classify caller evidence without granting caller freshness authority."""
    return _classify(evidence, trusted_idle=False)


def _validate_status_shape(value: Mapping[str, Any]) -> None:
    required = {
        "schema",
        "project",
        "queue_issue",
        "pending_exact_head_tickets",
        "reviewed_this_cycle",
        "pipeline_status",
        "blocker_class",
        "blocking_ref",
        "next_authority_role",
        "next_required_action",
        "stall_fingerprint",
        "stall_repeat_count",
        "new_evidence",
        "reviewer_mutations",
    }
    if set(value) != required:
        raise ReviewPipelineLivenessError("STATUS_FIELDS_INVALID")
    if value.get("schema") != STATUS_SCHEMA:
        raise ReviewPipelineLivenessError("STATUS_SCHEMA_INVALID")
    if value.get("reviewer_mutations") != "NONE":
        raise ReviewPipelineLivenessError("REVIEWER_MUTATION_FORBIDDEN")
    if value.get("pipeline_status") not in {
        "HEALTHY",
        "BLOCKED",
        "ACTIVE",
        "IDLE",
        "UNKNOWN",
    }:
        raise ReviewPipelineLivenessError("PIPELINE_STATUS_INVALID")
    _require_nonempty(value.get("project"), "PROJECT")
    _validate_issue_number(value.get("queue_issue"), "QUEUE_ISSUE")
    _validate_count(value.get("pending_exact_head_tickets"), "PENDING_TICKETS")
    _validate_count(value.get("reviewed_this_cycle"), "REVIEWED_THIS_CYCLE")
    _validate_count(value.get("stall_repeat_count"), "STALL_REPEAT_COUNT")
    if not isinstance(value.get("new_evidence"), bool):
        raise ReviewPipelineLivenessError("NEW_EVIDENCE_INVALID")


def validate_review_cycle_status(
    value: Mapping[str, Any], evidence: LivenessEvidence | None = None
) -> None:
    _validate_status_shape(value)
    if evidence is None:
        raise ReviewPipelineLivenessError("LIVENESS_EVIDENCE_REQUIRED")
    expected = classify_review_cycle(evidence)
    mismatched = [key for key in expected if value.get(key) != expected[key]]
    if mismatched:
        raise ReviewPipelineLivenessError(
            "STATUS_SEMANTICS_MISMATCH:" + ",".join(sorted(mismatched))
        )


def _load_retained_provider(root: Path) -> tuple[Any, type[BaseException]]:
    try:
        from idle_signal_scheduler import _load_r137_provider
    except (ImportError, OSError) as exc:
        raise ReviewPipelineLivenessError("R137_PROVIDER_IMPORT_FAILED") from exc
    try:
        provider_base, gateway_error = _load_r137_provider(root)
    except Exception as exc:
        raise ReviewPipelineLivenessError("R137_PROVIDER_LOAD_FAILED") from exc
    if not isinstance(provider_base, type) or not isinstance(gateway_error, type):
        raise ReviewPipelineLivenessError("R137_PROVIDER_API_INVALID")
    return provider_base, gateway_error


def _make_live_observer(
    root: Path, repository: str, queue_issue: int
) -> tuple[Any, type[BaseException]]:
    provider_base, gateway_error = _load_retained_provider(root)
    repo_re = re.escape(repository)
    queue = str(queue_issue)

    class _ReviewLivenessObserver(provider_base):
        def _dynamic_domain_endpoint_allowed(self, path: str) -> bool:
            patterns = (
                rf"^/repos/{repo_re}/git/ref/heads/main$",
                rf"^/repos/{repo_re}/issues/{queue}$",
                rf"^/repos/{repo_re}/issues/{queue}/comments\?per_page=100&page=[1-9][0-9]*$",
                rf"^/repos/{repo_re}/pulls\?state=open&per_page=100&page=[1-9][0-9]*$",
                rf"^/repos/{repo_re}/pulls/[1-9][0-9]*$",
                rf"^/repos/{repo_re}/issues\?state=open&per_page=100&page=[1-9][0-9]*$",
                rf"^/repos/{repo_re}/actions/runs\?head_sha=[0-9a-f]{{40}}&event=pull_request&per_page=100&page=[1-9][0-9]*$",
            )
            if any(re.fullmatch(pattern, path) for pattern in patterns):
                return True
            return super()._dynamic_domain_endpoint_allowed(path)

    return _ReviewLivenessObserver(), gateway_error


def _read_pages(
    observer: Any,
    gateway_error: type[BaseException],
    path_template: str,
    *,
    max_pages: int = 20,
) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for page in range(1, max_pages + 1):
        try:
            _headers, payload, _meta = observer._get_json(path_template.format(page=page))
        except gateway_error as exc:
            raise ReviewPipelineLivenessError("LIVE_GITHUB_READ_FAILED") from exc
        if not isinstance(payload, list):
            raise ReviewPipelineLivenessError("LIVE_GITHUB_PAGE_INVALID")
        for raw in payload:
            if not isinstance(raw, Mapping):
                raise ReviewPipelineLivenessError("LIVE_GITHUB_ITEM_INVALID")
            rows.append(raw)
        if len(payload) < 100:
            return rows
    raise ReviewPipelineLivenessError("LIVE_GITHUB_PAGINATION_INCOMPLETE")


def _read_pr(
    observer: Any,
    gateway_error: type[BaseException],
    repository: str,
    pr_number: int,
) -> Mapping[str, Any]:
    try:
        _headers, payload, _meta = observer._get_json(
            f"/repos/{repository}/pulls/{pr_number}"
        )
    except gateway_error as exc:
        raise ReviewPipelineLivenessError("LIVE_PR_READ_FAILED") from exc
    if not isinstance(payload, Mapping) or payload.get("number") != pr_number:
        raise ReviewPipelineLivenessError("LIVE_PR_PAYLOAD_INVALID")
    return payload


def _read_action_runs(
    observer: Any,
    gateway_error: type[BaseException],
    repository: str,
    head: str,
    *,
    max_pages: int = 20,
) -> list[Mapping[str, Any]]:
    if not _is_full_sha(head):
        raise ReviewPipelineLivenessError("CI_HEAD_INVALID")
    rows: list[Mapping[str, Any]] = []
    for page in range(1, max_pages + 1):
        path = (
            f"/repos/{repository}/actions/runs?head_sha={head}"
            f"&event=pull_request&per_page=100&page={page}"
        )
        try:
            _headers, payload, _meta = observer._get_json(path)
        except gateway_error as exc:
            raise ReviewPipelineLivenessError("LIVE_CI_READ_FAILED") from exc
        if not isinstance(payload, Mapping):
            raise ReviewPipelineLivenessError("LIVE_CI_PAYLOAD_INVALID")
        batch = payload.get("workflow_runs")
        if not isinstance(batch, list):
            raise ReviewPipelineLivenessError("LIVE_CI_RUNS_INVALID")
        for raw in batch:
            if not isinstance(raw, Mapping):
                raise ReviewPipelineLivenessError("LIVE_CI_RUN_INVALID")
            if raw.get("head_sha") != head:
                raise ReviewPipelineLivenessError("LIVE_CI_HEAD_MISMATCH")
            rows.append(raw)
        if len(batch) < 100:
            return rows
    raise ReviewPipelineLivenessError("LIVE_CI_PAGINATION_INCOMPLETE")


def _ci_blocker_ref(
    observer: Any,
    gateway_error: type[BaseException],
    repository: str,
    pr_number: int,
    head: str,
) -> str | None:
    runs = _read_action_runs(observer, gateway_error, repository, head)
    meaningful = []
    for run in runs:
        status = str(run.get("status") or "").lower()
        conclusion = run.get("conclusion")
        conclusion_norm = str(conclusion).lower() if conclusion is not None else None
        if conclusion_norm == "skipped":
            continue
        meaningful.append(run)
        if status in _CI_INFLIGHT:
            return f"PR#{pr_number}@{head}:CI_{status.upper()}"
        if status == "completed" and conclusion_norm in _CI_BAD_CONCLUSIONS:
            return f"PR#{pr_number}@{head}:CI_{conclusion_norm.upper()}"
        if status not in _CI_INFLIGHT | {"completed"}:
            return f"PR#{pr_number}@{head}:CI_STATUS_UNKNOWN"
    if not meaningful:
        return f"PR#{pr_number}@{head}:NO_OBSERVABLE_EXACT_HEAD_CI"
    if not any(
        str(run.get("status") or "").lower() == "completed"
        and str(run.get("conclusion") or "").lower() in _CI_OK_CONCLUSIONS
        for run in meaningful
    ):
        return f"PR#{pr_number}@{head}:NO_SUCCESSFUL_EXACT_HEAD_CI"
    return None


def _queue_records(
    comments: list[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    requests: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for raw in comments:
        body = raw.get("body")
        comment_id = raw.get("id")
        if not isinstance(body, str) or not isinstance(comment_id, int):
            continue
        schema = _field(body, "schema")
        if schema not in {_REQUEST_SCHEMA, _RESULT_SCHEMA}:
            continue
        pr = _int_field(body, "pr")
        head = _field(body, "exact_head") or _field(body, "reviewed_head")
        if pr is None or not _is_full_sha(head):
            continue
        record = {
            "id": comment_id,
            "pr": pr,
            "head": str(head),
            "body": body,
            "issue": _int_field(body, "issue") or _int_field(body, "source_issue"),
        }
        if schema == _REQUEST_SCHEMA:
            requests.append(record)
        else:
            record["verdict"] = (_field(body, "verdict") or "").upper()
            results.append(record)
    requests.sort(key=lambda row: row["id"])
    results.sort(key=lambda row: row["id"])
    return requests, results


def _derive_live_evidence(
    *,
    project: str,
    repository: str,
    queue_issue: int,
    queue_comments: list[Mapping[str, Any]],
    open_prs: list[Mapping[str, Any]],
    open_issues: list[Mapping[str, Any]],
    observer: Any,
    gateway_error: type[BaseException],
    prior_stall_fingerprint: str | None,
    prior_stall_repeat_count: int,
) -> LivenessEvidence:
    requests, results = _queue_records(queue_comments)
    results_by_tuple: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for result in results:
        results_by_tuple.setdefault((result["pr"], result["head"]), []).append(result)

    live_pr_cache: dict[int, Mapping[str, Any]] = {}

    def pr(number: int) -> Mapping[str, Any]:
        if number not in live_pr_cache:
            live_pr_cache[number] = _read_pr(
                observer, gateway_error, repository, number
            )
        return live_pr_cache[number]

    pending: list[dict[str, Any]] = []
    stale: list[str] = []
    for request in requests:
        settled = [
            result
            for result in results_by_tuple.get((request["pr"], request["head"]), [])
            if result["id"] > request["id"]
        ]
        if settled:
            continue
        raw_pr = pr(request["pr"])
        current_head = _head_from_pr(raw_pr)
        if current_head != request["head"]:
            stale.append(
                f"PR#{request['pr']}@{request['head']}->@{current_head or 'UNKNOWN'}"
            )
        else:
            pending.append(request)

    accepted_not_canonicalized: list[str] = []
    remediation_not_requeued: list[str] = []
    for result in results:
        later_same_tuple = [
            item
            for item in results_by_tuple.get((result["pr"], result["head"]), [])
            if item["id"] > result["id"]
        ]
        if later_same_tuple:
            continue
        raw_pr = pr(result["pr"])
        current_head = _head_from_pr(raw_pr)
        verdict = result.get("verdict")
        if verdict == "ACCEPT":
            if (
                raw_pr.get("state") == "open"
                and not _merged(raw_pr)
                and current_head == result["head"]
            ):
                accepted_not_canonicalized.append(
                    f"PR#{result['pr']}@{result['head']}"
                )
        elif verdict == "CHANGES_REQUIRED":
            newer_request_for_current = any(
                req["pr"] == result["pr"]
                and current_head is not None
                and req["head"] == current_head
                and req["id"] > result["id"]
                for req in requests
            )
            if not newer_request_for_current and raw_pr.get("state") == "open":
                remediation_not_requeued.append(
                    f"PR#{result['pr']}@{current_head or result['head']}"
                )

    requested_heads = {(row["pr"], row["head"]) for row in requests}
    implemented_not_queued: list[str] = []
    for raw_pr in open_prs:
        number = raw_pr.get("number")
        head = _head_from_pr(raw_pr)
        body = raw_pr.get("body") or ""
        if (
            isinstance(number, int)
            and head is not None
            and (number, head) not in requested_heads
            and any(marker in body for marker in _COMPLETION_MARKERS)
        ):
            implemented_not_queued.append(f"PR#{number}@{head}")

    released_not_implemented: list[str] = []
    for raw_issue in open_issues:
        if "pull_request" in raw_issue:
            continue
        number = raw_issue.get("number")
        body = raw_issue.get("body") or ""
        if (
            isinstance(number, int)
            and any(marker in body for marker in _RELEASE_MARKERS)
            and not any(marker in body for marker in _IMPLEMENTED_MARKERS)
            and "NO_IMPLEMENTATION_AUTHORIZED" not in body
        ):
            released_not_implemented.append(f"ISSUE#{number}")

    ci_candidates: dict[tuple[int, str], None] = {}
    for row in pending:
        ci_candidates[(row["pr"], row["head"])] = None
    for ref in implemented_not_queued + remediation_not_requeued:
        match = re.fullmatch(r"PR#([1-9][0-9]*)@([0-9a-f]{40})", ref)
        if match:
            ci_candidates[(int(match.group(1)), match.group(2))] = None
    ci_blockers = [
        blocker
        for number, head in sorted(ci_candidates)
        if (
            blocker := _ci_blocker_ref(
                observer, gateway_error, repository, number, head
            )
        )
    ]

    return LivenessEvidence(
        project=project,
        repository=repository,
        queue_issue=queue_issue,
        pending_exact_head_tickets=len(pending),
        reviewed_this_cycle=0,
        accepted_not_canonicalized_ref=(
            sorted(accepted_not_canonicalized)[0]
            if accepted_not_canonicalized
            else None
        ),
        released_not_implemented_ref=(
            sorted(released_not_implemented)[0]
            if released_not_implemented
            else None
        ),
        implemented_not_queued_ref=(
            sorted(implemented_not_queued)[0] if implemented_not_queued else None
        ),
        remediation_not_requeued_ref=(
            sorted(remediation_not_requeued)[0]
            if remediation_not_requeued
            else None
        ),
        stale_review_request_ref=sorted(stale)[0] if stale else None,
        ci_or_provenance_blocked_ref=sorted(ci_blockers)[0] if ci_blockers else None,
        provenance=None,
        prior_stall_fingerprint=prior_stall_fingerprint,
        prior_stall_repeat_count=prior_stall_repeat_count,
    )


def _read_main(
    observer: Any, gateway_error: type[BaseException], repository: str
) -> str:
    try:
        _headers, payload, _meta = observer._get_json(
            f"/repos/{repository}/git/ref/heads/main"
        )
    except gateway_error as exc:
        raise ReviewPipelineLivenessError("LIVE_GITHUB_READ_FAILED") from exc
    if not isinstance(payload, Mapping):
        raise ReviewPipelineLivenessError("LIVE_MAIN_PAYLOAD_INVALID")
    obj = payload.get("object")
    sha = obj.get("sha") if isinstance(obj, Mapping) else None
    if not _is_full_sha(sha):
        raise ReviewPipelineLivenessError("LIVE_MAIN_SHA_INVALID")
    return str(sha)


def _read_snapshot(
    observer: Any,
    gateway_error: type[BaseException],
    repository: str,
    queue_issue: int,
) -> tuple[_Snapshot, list[Mapping[str, Any]], list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    main_sha = _read_main(observer, gateway_error, repository)
    try:
        _headers, queue_payload, _meta = observer._get_json(
            f"/repos/{repository}/issues/{queue_issue}"
        )
    except gateway_error as exc:
        raise ReviewPipelineLivenessError("LIVE_GITHUB_READ_FAILED") from exc
    if (
        not isinstance(queue_payload, Mapping)
        or queue_payload.get("number") != queue_issue
    ):
        raise ReviewPipelineLivenessError("LIVE_QUEUE_PAYLOAD_INVALID")
    queue_comments = _read_pages(
        observer,
        gateway_error,
        f"/repos/{repository}/issues/{queue_issue}/comments?per_page=100&page={{page}}",
    )
    open_prs = _read_pages(
        observer,
        gateway_error,
        f"/repos/{repository}/pulls?state=open&per_page=100&page={{page}}",
    )
    open_issues = _read_pages(
        observer,
        gateway_error,
        f"/repos/{repository}/issues?state=open&per_page=100&page={{page}}",
    )
    snapshot = _Snapshot(
        main_sha=main_sha,
        queue_digest=_digest(queue_comments),
        open_pr_digest=_digest(open_prs),
        open_issue_digest=_digest(open_issues),
    )
    return snapshot, queue_comments, open_prs, open_issues


def observe_review_cycle(
    repo_root: str | Path,
    project: str,
    *,
    prior_stall_fingerprint: str | None = None,
    prior_stall_repeat_count: int = 0,
) -> dict[str, Any]:
    """Fresh-read fixed GitHub liveness surfaces for one registered project.

    NORMAL_IDLE is only possible when the internal retained R137 observer reads
    canonical queue/PR/Issue/relevant CI surfaces and an immediate final
    readback proves that the report did not race with a concurrent change.
    """

    if project not in PROJECT_DIRECTORY:
        raise ReviewPipelineLivenessError("PROJECT_NOT_REGISTERED")
    repository, queue_issue = PROJECT_DIRECTORY[project]
    root = Path(repo_root).resolve()
    observer, gateway_error = _make_live_observer(root, repository, queue_issue)

    before, queue_comments, open_prs, open_issues = _read_snapshot(
        observer, gateway_error, repository, queue_issue
    )
    evidence = _derive_live_evidence(
        project=project,
        repository=repository,
        queue_issue=queue_issue,
        queue_comments=queue_comments,
        open_prs=open_prs,
        open_issues=open_issues,
        observer=observer,
        gateway_error=gateway_error,
        prior_stall_fingerprint=prior_stall_fingerprint,
        prior_stall_repeat_count=prior_stall_repeat_count,
    )

    after, _q2, _p2, _i2 = _read_snapshot(
        observer, gateway_error, repository, queue_issue
    )
    if after != before:
        raise ReviewPipelineLivenessError("LIVE_OBSERVATION_CHANGED_DURING_SCAN")

    return _classify(evidence, trusted_idle=True)
