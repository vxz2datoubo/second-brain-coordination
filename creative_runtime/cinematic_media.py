"""Source-bound, deterministic media-job planning for the offline runtime.

This module deliberately does *not* read images, produce media, open a
network connection, inspect environment variables, or call a provider.  It
models the part that must be correct before such a provider is ever allowed:
short segment identity, per-campaign idempotency, quality gates, and a stable
simulated result reference.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import re
from typing import Any

from .contracts import (
    AppearanceContinuityRecord,
    CinematicSegment,
    MediaJob,
    MediaQualityReport,
    MediaResult,
    canonical_json,
)
from .director_context import DirectorContextCompilation


class CinematicMediaViolation(ValueError):
    """Raised when a media job has no safe, verified offline authority."""


_HASH = re.compile(r"^[a-f0-9]{64}$")
_SEGMENT = re.compile(r"^segment_[a-f0-9]{20}$")
_CAMPAIGN = re.compile(r"^camp_[a-f0-9]{20}$")
_REF = re.compile(r"^(?:offline|private)://[a-z0-9][a-z0-9/_-]{7,180}$")
OFFLINE_ADAPTER = "offline_deterministic/v1"


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _require_hash(value: str, label: str) -> None:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise CinematicMediaViolation(label + " must be an exact SHA-256 hash")


def _require_ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REF.fullmatch(value):
        raise CinematicMediaViolation(label + " must be an opaque offline:// or private:// reference")


def build_cinematic_segment(
    compiled: DirectorContextCompilation,
    continuity: AppearanceContinuityRecord,
) -> CinematicSegment:
    """Bind a 4--15 second segment to verified direction and campaign state."""

    brief = compiled.brief_v2
    quality = compiled.legacy_compilation.compilation.quality_report
    if not quality.can_generate:
        raise CinematicMediaViolation("director quality gate did not pass")
    if continuity.campaign_id != brief.campaign_id:
        raise CinematicMediaViolation("appearance continuity belongs to another campaign")
    if continuity.continuity_ledger_hash != brief.continuity_ledger_hash:
        raise CinematicMediaViolation("appearance continuity does not bind the verified story ledger")
    if continuity.validation_status != "references_verified_no_media_read":
        raise CinematicMediaViolation("appearance continuity is not approved reference-only metadata")
    duration = sum(shot.duration_seconds for shot in compiled.legacy_compilation.compilation.shots)
    if not 4 <= duration <= 15:
        raise CinematicMediaViolation("cinematic segment duration must remain in the 4--15 second offline contract")
    shot_bundle_hash = _digest(
        {
            "brief": brief.to_dict(),
            "shots": [shot.to_dict() for shot in compiled.legacy_compilation.compilation.shots],
        }
    )
    segment_id = "segment_" + _digest(
        {
            "campaign_id": brief.campaign_id,
            "shot_bundle_hash": shot_bundle_hash,
            "continuity": continuity.to_dict(),
        }
    )[:20]
    return CinematicSegment(
        segment_id=segment_id,
        campaign_id=brief.campaign_id,
        shot_bundle_hash=shot_bundle_hash,
        duration_seconds=duration,
        audio_plan=" + ".join(shot.sound for shot in compiled.legacy_compilation.compilation.shots),
        style_profile_id=brief.style_profile_id,
        continuity_record_ref="offline://continuity/" + _digest(continuity.to_dict())[:24],
        generation_authorization_status="offline_simulation_only",
    )


def create_offline_media_job(segment: CinematicSegment) -> tuple[MediaJob, MediaQualityReport]:
    """Queue one deterministic simulated job and its pre-generation gates."""

    if not _SEGMENT.fullmatch(segment.segment_id) or not _CAMPAIGN.fullmatch(segment.campaign_id):
        raise CinematicMediaViolation("segment identity is malformed")
    _require_hash(segment.shot_bundle_hash, "shot_bundle_hash")
    _require_ref(segment.continuity_record_ref, "continuity_record_ref")
    if segment.generation_authorization_status != "offline_simulation_only":
        raise CinematicMediaViolation("only offline simulation segments may be queued in GitHub runtime")
    if not 4 <= segment.duration_seconds <= 15:
        raise CinematicMediaViolation("segment duration is outside 4--15 seconds")
    request_hash = _digest({"segment": segment.to_dict(), "adapter": OFFLINE_ADAPTER})
    job_id = "mediajob_" + request_hash[:20]
    job = MediaJob(
        job_id=job_id,
        request_hash=request_hash,
        segment_ref="offline://cinematic-segments/" + segment.segment_id,
        provider_adapter=OFFLINE_ADAPTER,
        confirmation_status="not_required_offline",
        budget_gate_ref="offline://budget-gates/no-spend",
        idempotency_key="media:" + segment.campaign_id + ":" + request_hash[:24],
        status="queued_offline",
    )
    report = MediaQualityReport(
        job_id=job.job_id,
        identity_check="pass_reference_bound",
        continuity_check="pass_ledger_bound",
        content_check="pass_non_explicit_contract",
        audio_check="pass_audio_plan_present",
        policy_check="pass_offline_no_provider",
        verdict="pass",
        evidence_refs=(segment.continuity_record_ref, "offline://quality/" + request_hash[:24]),
    )
    return job, report


def execute_offline_media_job(job: MediaJob, report: MediaQualityReport, *, occurred_at: str) -> MediaResult:
    """Return a stable simulated result; never retries or contacts a provider."""

    if job.provider_adapter != OFFLINE_ADAPTER or job.status != "queued_offline":
        raise CinematicMediaViolation("only a newly queued offline job can execute")
    if job.confirmation_status != "not_required_offline" or job.budget_gate_ref != "offline://budget-gates/no-spend":
        raise CinematicMediaViolation("offline job has an invalid authorization boundary")
    if report.job_id != job.job_id or report.verdict != "pass":
        raise CinematicMediaViolation("media quality report does not permit this job")
    if not occurred_at or "\n" in occurred_at:
        raise CinematicMediaViolation("occurred_at must be a supplied single-line event timestamp")
    result_hash = _digest({"job": job.to_dict(), "report": report.to_dict(), "occurred_at": occurred_at})
    return MediaResult(
        job_id=job.job_id,
        provider_ref="offline://adapters/deterministic-v1",
        result_ref="offline://cinematic-results/" + result_hash[:24],
        result_hash=result_hash,
        created_at=occurred_at,
        status="simulated",
        failure_reason=None,
    )


class OfflineMediaQueue:
    """A process-local queue whose idempotency key is campaign scoped.

    Persistence remains intentionally delegated to the existing task-local
    generation receipt mechanism; this layer prevents stateful queue logic from
    becoming an accidental cross-user media cache.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, MediaJob] = {}
        self._results: dict[str, MediaResult] = {}

    def enqueue(self, segment: CinematicSegment) -> tuple[MediaJob, MediaQualityReport, bool]:
        job, report = create_offline_media_job(segment)
        existing = self._jobs.get(job.idempotency_key)
        if existing is not None:
            if existing.request_hash != job.request_hash:
                raise CinematicMediaViolation("idempotency collision has different request material")
            return existing, replace(report, job_id=existing.job_id), False
        self._jobs[job.idempotency_key] = job
        return job, report, True

    def execute(self, job: MediaJob, report: MediaQualityReport, *, occurred_at: str) -> MediaResult:
        stored = self._jobs.get(job.idempotency_key)
        if stored != job:
            raise CinematicMediaViolation("job was not created by this queue")
        existing = self._results.get(job.idempotency_key)
        if existing is not None:
            return existing
        result = execute_offline_media_job(job, report, occurred_at=occurred_at)
        self._results[job.idempotency_key] = result
        return result
