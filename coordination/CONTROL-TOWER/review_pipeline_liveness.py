from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


STATUS_SCHEMA = "REVIEW_CYCLE_STATUS/v1"
PROVENANCE_SCHEMA = "REVIEW_LIVENESS_PROVENANCE/v1"

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


class ReviewPipelineLivenessError(ValueError):
    pass


@dataclass(frozen=True)
class SurfaceReadAttestation:
    surface: str
    source_ref: str
    observed_revision: str
    fresh: bool
    complete: bool


@dataclass(frozen=True)
class LivenessProvenanceEnvelope:
    schema: str
    repository: str
    queue_issue: int
    canonical_main_sha: str
    queue_snapshot_ref: str
    surface_reads: tuple[SurfaceReadAttestation, ...]


@dataclass(frozen=True)
class LivenessEvidence:
    project: str
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


def _require_nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewPipelineLivenessError(f"{name}_REQUIRED")
    return value.strip()


def _validate_count(value: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ReviewPipelineLivenessError(f"{name}_INVALID")
    return value


def _is_full_sha(value: str) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def _provenance_is_complete(evidence: LivenessEvidence) -> bool:
    envelope = evidence.provenance
    if envelope is None:
        return False
    if envelope.schema != PROVENANCE_SCHEMA:
        return False
    if not isinstance(envelope.repository, str) or not envelope.repository.strip():
        return False
    if envelope.queue_issue != evidence.queue_issue:
        return False
    if not _is_full_sha(envelope.canonical_main_sha):
        return False
    if not isinstance(envelope.queue_snapshot_ref, str) or not envelope.queue_snapshot_ref.strip():
        return False
    if not isinstance(envelope.surface_reads, tuple):
        return False

    by_surface: dict[str, SurfaceReadAttestation] = {}
    for read in envelope.surface_reads:
        if not isinstance(read, SurfaceReadAttestation):
            return False
        if read.surface not in REQUIRED_LIVENESS_SURFACES:
            return False
        if read.surface in by_surface:
            return False
        if not isinstance(read.source_ref, str) or not read.source_ref.strip():
            return False
        if not isinstance(read.observed_revision, str) or not read.observed_revision.strip():
            return False
        if not isinstance(read.fresh, bool) or not isinstance(read.complete, bool):
            return False
        by_surface[read.surface] = read

    if set(by_surface) != REQUIRED_LIVENESS_SURFACES:
        return False
    return all(read.fresh and read.complete for read in by_surface.values())


def _select_blocker(e: LivenessEvidence) -> tuple[str, str | None]:
    if e.pending_exact_head_tickets > 0:
        return "PENDING_REVIEW", None

    ordered = (
        ("STALE_REVIEW_REQUEST", e.stale_review_request_ref),
        ("CI_OR_PROVENANCE_BLOCKED", e.ci_or_provenance_blocked_ref),
        ("ACCEPTED_NOT_CANONICALIZED", e.accepted_not_canonicalized_ref),
        ("CANONICALIZED_NOT_RELEASED", e.canonicalized_not_released_ref),
        ("REMEDIATION_NOT_REQUEUED", e.remediation_not_requeued_ref),
        ("IMPLEMENTED_NOT_QUEUED", e.implemented_not_queued_ref),
        ("RELEASED_NOT_IMPLEMENTED", e.released_not_implemented_ref),
    )
    for blocker_class, ref in ordered:
        if ref:
            return blocker_class, ref

    if not _provenance_is_complete(e):
        return "UNKNOWN_BLOCKED", None
    return "NORMAL_IDLE", None


def classify_review_cycle(evidence: LivenessEvidence) -> dict[str, Any]:
    project = _require_nonempty(evidence.project, "PROJECT")
    queue_issue = _validate_count(evidence.queue_issue, "QUEUE_ISSUE")
    pending = _validate_count(evidence.pending_exact_head_tickets, "PENDING_TICKETS")
    reviewed = _validate_count(evidence.reviewed_this_cycle, "REVIEWED_THIS_CYCLE")
    prior_repeat = _validate_count(evidence.prior_stall_repeat_count, "PRIOR_REPEAT_COUNT")

    blocker_class, blocking_ref = _select_blocker(evidence)
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

    repeated = fingerprint != "NONE" and fingerprint == evidence.prior_stall_fingerprint
    repeat_count = prior_repeat + 1 if repeated else (1 if fingerprint != "NONE" else 0)

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
    if value.get("pipeline_status") not in {"HEALTHY", "BLOCKED", "ACTIVE", "IDLE", "UNKNOWN"}:
        raise ReviewPipelineLivenessError("PIPELINE_STATUS_INVALID")
    _require_nonempty(value.get("project"), "PROJECT")
    _validate_count(value.get("queue_issue"), "QUEUE_ISSUE")
    _validate_count(value.get("pending_exact_head_tickets"), "PENDING_TICKETS")
    _validate_count(value.get("reviewed_this_cycle"), "REVIEWED_THIS_CYCLE")
    _validate_count(value.get("stall_repeat_count"), "STALL_REPEAT_COUNT")
    if not isinstance(value.get("new_evidence"), bool):
        raise ReviewPipelineLivenessError("NEW_EVIDENCE_INVALID")


def validate_review_cycle_status(
    value: Mapping[str, Any], evidence: LivenessEvidence | None = None
) -> None:
    """Fail closed unless status semantics exactly re-derive from fresh provenance-bound evidence."""
    _validate_status_shape(value)
    if evidence is None:
        raise ReviewPipelineLivenessError("LIVENESS_EVIDENCE_REQUIRED")

    expected = classify_review_cycle(evidence)
    mismatched = [key for key in expected if value.get(key) != expected[key]]
    if mismatched:
        raise ReviewPipelineLivenessError(
            "STATUS_SEMANTICS_MISMATCH:" + ",".join(sorted(mismatched))
        )
