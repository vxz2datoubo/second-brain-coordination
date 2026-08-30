"""Generation adapters that are deterministic offline by default and by policy."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .contracts import GenerationRequest, GenerationResult, canonical_json
from .director import QualityReport, VerifiedDirectorCompilation


class GenerationViolation(ValueError):
    """Raised before a request can cross an external-provider authority boundary."""


GENERATION_RECEIPT_SCHEMA = "CreativeOfflineGenerationReceipt/v1"
GENERATION_RECEIPT_DIRECTORY = "generation-receipts"


@dataclass(frozen=True)
class OfflineGenerationReceipt:
    """A replayable record of a simulated generation, never a media payload."""

    receipt_id: str
    request: GenerationRequest
    result: GenerationResult
    source_timeline_hash: str
    source_graph_revision: str
    source_final_event_id: str
    source_final_transition_id: str | None
    shot_id: str
    quality_metrics: Mapping[str, int]
    created_at: str
    receipt_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": GENERATION_RECEIPT_SCHEMA,
            "receipt_id": self.receipt_id,
            "request": self.request.to_dict(),
            "result": self.result.to_dict(),
            "source": {
                "timeline_hash": self.source_timeline_hash,
                "graph_revision": self.source_graph_revision,
                "final_event_id": self.source_final_event_id,
                "final_transition_id": self.source_final_transition_id,
            },
            "shot_id": self.shot_id,
            "quality_metrics": dict(self.quality_metrics),
            "created_at": self.created_at,
            "receipt_hash": self.receipt_hash,
        }


@dataclass(frozen=True)
class OfflineGenerationRecord:
    """Return value that distinguishes a new atomic record from idempotent reuse."""

    status: str
    receipt: OfflineGenerationReceipt
    receipt_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "receipt_path": self.receipt_path,
            "receipt": self.receipt.to_dict(),
        }


def _require_quality(request: GenerationRequest, report: QualityReport) -> None:
    if not report.can_generate:
        raise GenerationViolation("Generation blocked: director quality gate did not pass")
    if request.content_rating != "non_explicit":
        raise GenerationViolation("Generation blocked: only non_explicit content is permitted")


class OfflineGenerationAdapter:
    """Produce a stable reference, never a media file or network request."""

    provider = "offline"

    def generate(self, request: GenerationRequest, report: QualityReport) -> GenerationResult:
        _require_quality(request, report)
        if request.provider != self.provider:
            raise GenerationViolation("Offline adapter accepts provider=offline only")
        request_hash = hashlib.sha256(canonical_json(request.to_dict()).encode("utf-8")).hexdigest()
        return GenerationResult(
            request_id=request.request_id,
            provider=self.provider,
            status="simulated",
            output_ref="offline://creative-runtime/" + request_hash[:24],
            request_hash=request_hash,
            simulated=True,
        )


class ExternalGenerationGuard:
    """Represents Dreamina/command integrations without implementing a call path."""

    def preview(self, request: GenerationRequest, report: QualityReport) -> GenerationResult:
        """Return an auditable denial. This method never reads environment variables."""

        _require_quality(request, report)
        request_hash = hashlib.sha256(canonical_json(request.to_dict()).encode("utf-8")).hexdigest()
        if not request.confirm_generate:
            status = "blocked_confirmation_required"
        else:
            status = "blocked_route_authority"
        return GenerationResult(
            request_id=request.request_id,
            provider=request.provider,
            status=status,
            output_ref=None,
            request_hash=request_hash,
            simulated=True,
        )


def adapter_for(provider: str) -> OfflineGenerationAdapter | ExternalGenerationGuard:
    if provider == "offline":
        return OfflineGenerationAdapter()
    if provider in {"dreamina", "command"}:
        return ExternalGenerationGuard()
    raise GenerationViolation("Unknown generation provider: " + provider)


def offline_generation_receipt_path(workspace: Path, receipt_id: str) -> Path:
    """Return the task-local, git-ignored location for one safe receipt."""

    if not receipt_id.startswith("gen_") or len(receipt_id) != 24:
        raise GenerationViolation("Invalid offline generation receipt identifier")
    return workspace / GENERATION_RECEIPT_DIRECTORY / (receipt_id + ".json")


def _digest_record(record: Mapping[str, Any]) -> str:
    material = {str(key): value for key, value in record.items() if key != "receipt_hash"}
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


def _request_for_verified_compilation(
    compiled: VerifiedDirectorCompilation,
    shot_id: str | None,
) -> GenerationRequest:
    """Construct a deterministic request only from graph-validated direction."""

    brief = compiled.compilation.brief
    verified = compiled.verified_input
    if brief.source_timeline_hash != verified.timeline_hash:
        raise GenerationViolation("Director brief is not bound to the verified timeline")
    if not compiled.compilation.quality_report.can_generate:
        raise GenerationViolation("Generation blocked: director quality gate did not pass")
    selected = next((shot for shot in compiled.compilation.shots if shot.shot_id == shot_id), None) if shot_id else compiled.compilation.shots[0] if compiled.compilation.shots else None
    if selected is None:
        raise GenerationViolation("Requested shot is not present in the verified director compilation")
    material = {
        "schema": "OfflineGenerationRequestIdentity/v1",
        "timeline_hash": verified.timeline_hash,
        "final_event_id": verified.final_event_id,
        "graph_revision": verified.graph_revision,
        "shot": selected.to_dict(),
        "quality_metrics": compiled.compilation.quality_report.metrics.to_dict(),
    }
    request_hash = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
    return GenerationRequest(
        request_id="req_" + request_hash[:20],
        provider="offline",
        shot_plan=selected,
        content_rating=brief.content_rating,
        confirm_generate=False,
    )


def _offline_receipt_material(compiled: VerifiedDirectorCompilation, shot_id: str | None) -> dict[str, Any]:
    """Build the stable content for an offline receipt before its file identity."""

    request = _request_for_verified_compilation(compiled, shot_id)
    result = OfflineGenerationAdapter().generate(request, compiled.compilation.quality_report)
    verified = compiled.verified_input
    return {
        "schema": GENERATION_RECEIPT_SCHEMA,
        "receipt_id": "",  # Filled from a stable material hash below.
        "request": request.to_dict(),
        "result": result.to_dict(),
        "source": {
            "timeline_hash": verified.timeline_hash,
            "graph_revision": verified.graph_revision,
            "final_event_id": verified.final_event_id,
            "final_transition_id": verified.final_transition_id,
        },
        "shot_id": request.shot_plan.shot_id,
        "quality_metrics": compiled.compilation.quality_report.metrics.to_dict(),
        "created_at": "",  # Replaced by the recorded final event timestamp by the caller.
    }


def _receipt_from_material(material: Mapping[str, Any], *, created_at: str) -> OfflineGenerationReceipt:
    """Finalize a receipt record from canonical deterministic material."""

    final_material = dict(material)
    final_material["created_at"] = str(created_at)
    identity_material = {str(key): value for key, value in final_material.items() if key != "receipt_id"}
    receipt_id = "gen_" + hashlib.sha256(canonical_json(identity_material).encode("utf-8")).hexdigest()[:20]
    final_material["receipt_id"] = receipt_id
    receipt_hash = _digest_record(final_material)
    source = final_material["source"]
    request_record = final_material["request"]
    result_record = final_material["result"]
    return OfflineGenerationReceipt(
        receipt_id=receipt_id,
        request=GenerationRequest(
            request_id=str(request_record["request_id"]),
            provider=str(request_record["provider"]),
            shot_plan=_shot_from_record(request_record["shot_plan"]),
            content_rating=str(request_record["content_rating"]),
            confirm_generate=bool(request_record.get("confirm_generate", False)),
        ),
        result=GenerationResult(
            request_id=str(result_record["request_id"]),
            provider=str(result_record["provider"]),
            status=str(result_record["status"]),
            output_ref=result_record.get("output_ref"),
            request_hash=str(result_record["request_hash"]),
            simulated=bool(result_record["simulated"]),
        ),
        source_timeline_hash=str(source["timeline_hash"]),
        source_graph_revision=str(source["graph_revision"]),
        source_final_event_id=str(source["final_event_id"]),
        source_final_transition_id=source.get("final_transition_id"),
        shot_id=str(final_material["shot_id"]),
        quality_metrics={str(key): int(value) for key, value in final_material["quality_metrics"].items()},
        created_at=str(final_material["created_at"]),
        receipt_hash=receipt_hash,
    )


def _shot_from_record(record: Mapping[str, Any]):
    """Keep receipt parsing local so contracts stay provider-free."""

    from .contracts import ShotPlan

    return ShotPlan(
        shot_id=str(record["shot_id"]),
        beat_id=str(record["beat_id"]),
        shot_role=str(record["shot_role"]),
        camera=str(record["camera"]),
        performance_task=str(record["performance_task"]),
        duration_seconds=int(record["duration_seconds"]),
        reference_artifact_ids=tuple(str(item) for item in record.get("reference_artifact_ids", ())),
        axis=str(record.get("axis", "")),
        lighting=str(record.get("lighting", "")),
        sound=str(record.get("sound", "")),
        dominant_change=str(record.get("dominant_change", "")),
    )


def _atomic_write_receipt(path: Path, content: str) -> bool:
    """Write a new receipt once; an existing one is verified by the caller."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise GenerationViolation("An incomplete offline generation receipt temporary file exists")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise GenerationViolation("Refusing to overwrite an existing offline generation receipt")
        os.replace(temporary, path)
        return True
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def _load_receipt(path: Path) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GenerationViolation("Offline generation receipt is not valid JSON") from error
    if not isinstance(record, Mapping) or record.get("schema") != GENERATION_RECEIPT_SCHEMA:
        raise GenerationViolation("Unsupported offline generation receipt schema")
    if _digest_record(record) != record.get("receipt_hash"):
        raise GenerationViolation("Offline generation receipt hash does not match its content")
    return dict(record)


def record_offline_generation(
    workspace: Path,
    compiled: VerifiedDirectorCompilation,
    *,
    final_event_occurred_at: str,
    shot_id: str | None = None,
) -> OfflineGenerationRecord:
    """Atomically persist a deterministic offline-only generation receipt.

    There is no external provider branch here.  The receipt records a stable
    offline URI plus source timeline, graph, event, shot, and quality metrics;
    it never creates media, reads credentials, or replaces a previous result.
    """

    material = _offline_receipt_material(compiled, shot_id)
    # The final ledger event time is part of provenance, not wall-clock time.
    receipt = _receipt_from_material(material, created_at=final_event_occurred_at)
    path = offline_generation_receipt_path(workspace, receipt.receipt_id)
    content = canonical_json(receipt.to_dict()) + "\n"
    stored = _atomic_write_receipt(path, content)
    if not stored:
        existing = _load_receipt(path)
        if canonical_json(existing) != canonical_json(receipt.to_dict()):
            raise GenerationViolation("Existing offline generation receipt differs from the verified request")
    return OfflineGenerationRecord(
        status="offline_generation_recorded" if stored else "offline_generation_already_recorded",
        receipt=receipt,
        receipt_path=str(path),
    )


def verify_offline_generation_record(
    workspace: Path,
    compiled: VerifiedDirectorCompilation,
    *,
    final_event_occurred_at: str,
    receipt_id: str,
) -> OfflineGenerationReceipt:
    """Reconstruct and compare one receipt without writing or repairing files."""

    path = offline_generation_receipt_path(workspace, receipt_id)
    if not path.is_file():
        raise GenerationViolation("Offline generation receipt does not exist")
    existing = _load_receipt(path)
    try:
        expected_material = _offline_receipt_material(compiled, _shot_id_from_record(existing))
    except GenerationViolation as error:
        raise GenerationViolation("Offline generation receipt does not match the current verified story source") from error
    expected = _receipt_from_material(expected_material, created_at=final_event_occurred_at)
    if expected.receipt_id != receipt_id or canonical_json(existing) != canonical_json(expected.to_dict()):
        raise GenerationViolation("Offline generation receipt does not match the current verified story source")
    return expected


def _shot_id_from_record(record: Mapping[str, Any]) -> str:
    shot_id = record.get("shot_id")
    if not isinstance(shot_id, str):
        raise GenerationViolation("Offline generation receipt has no valid shot identifier")
    return shot_id
