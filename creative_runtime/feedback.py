"""Immutable, source-bound user feedback for offline creative outputs.

Feedback is deliberately kept separate from story facts and director rules.
It records a bounded numeric observation against a verified offline-generation
receipt, then callers may turn it into a *pending* knowledge candidate.  No
feedback record can promote itself into canonical knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .contracts import canonical_json
from .generation import OfflineGenerationReceipt
from .session import DEFAULT_SLOT, validate_slot


FEEDBACK_SCHEMA = "CreativeFeedback/v1"
FEEDBACK_DIRECTORY = "feedback"


class FeedbackViolation(ValueError):
    """Raised when feedback is malformed, conflicting, or lacks verified source."""


@dataclass(frozen=True)
class FeedbackRecord:
    feedback_id: str
    receipt_id: str
    source_timeline_hash: str
    source_receipt_hash: str
    rating: int
    note: str
    submitted_at: str
    feedback_hash: str
    slot_id: str = DEFAULT_SLOT

    def to_dict(self) -> dict[str, Any]:
        result = {
            "schema": FEEDBACK_SCHEMA,
            "feedback_id": self.feedback_id,
            "receipt_id": self.receipt_id,
            "source_timeline_hash": self.source_timeline_hash,
            "source_receipt_hash": self.source_receipt_hash,
            "rating": self.rating,
            "note": self.note,
            "submitted_at": self.submitted_at,
            "feedback_hash": self.feedback_hash,
        }
        if self.slot_id != DEFAULT_SLOT:
            result["slot_id"] = self.slot_id
        return result


def _feedback_hash(record: Mapping[str, Any]) -> str:
    material = {str(key): value for key, value in record.items() if key != "feedback_hash"}
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


def feedback_path(workspace: Path, feedback_id: str, slot: str = DEFAULT_SLOT) -> Path:
    if not feedback_id.startswith("fb_") or len(feedback_id) != 23:
        raise FeedbackViolation("Invalid feedback identifier")
    normalized_slot = validate_slot(slot)
    directory = workspace / FEEDBACK_DIRECTORY
    if normalized_slot != DEFAULT_SLOT:
        directory = directory / "slots" / normalized_slot
    return directory / (feedback_id + ".json")


def _validate_input(rating: int, note: str) -> tuple[int, str]:
    if isinstance(rating, bool) or not isinstance(rating, int) or not 0 <= rating <= 5:
        raise FeedbackViolation("Feedback rating must be an integer from 0 through 5")
    normalized_note = " ".join(note.split())
    if not normalized_note:
        raise FeedbackViolation("Feedback note cannot be empty")
    if len(normalized_note) > 1000:
        raise FeedbackViolation("Feedback note exceeds the 1000-character offline limit")
    return rating, normalized_note


def build_feedback_record(
    receipt: OfflineGenerationReceipt,
    *,
    rating: int,
    note: str,
    submitted_at: str,
    slot: str = DEFAULT_SLOT,
) -> FeedbackRecord:
    """Create a stable feedback identity from explicit, reviewable inputs."""

    normalized_rating, normalized_note = _validate_input(rating, note)
    if receipt.result.provider != "offline" or not receipt.result.simulated:
        raise FeedbackViolation("Feedback source must be a verified simulated offline generation receipt")
    normalized_slot = validate_slot(slot)
    if receipt.source_slot_id != normalized_slot:
        raise FeedbackViolation("Feedback slot does not match the verified generation receipt slot")
    material = {
        "schema": FEEDBACK_SCHEMA,
        "feedback_id": "",
        "receipt_id": receipt.receipt_id,
        "source_timeline_hash": receipt.source_timeline_hash,
        "source_receipt_hash": receipt.receipt_hash,
        "rating": normalized_rating,
        "note": normalized_note,
        "submitted_at": str(submitted_at),
    }
    if normalized_slot != DEFAULT_SLOT:
        material["slot_id"] = normalized_slot
    identity_material = {key: value for key, value in material.items() if key != "feedback_id"}
    feedback_id = "fb_" + hashlib.sha256(canonical_json(identity_material).encode("utf-8")).hexdigest()[:20]
    material["feedback_id"] = feedback_id
    return FeedbackRecord(
        feedback_id=feedback_id,
        receipt_id=receipt.receipt_id,
        source_timeline_hash=receipt.source_timeline_hash,
        source_receipt_hash=receipt.receipt_hash,
        rating=normalized_rating,
        note=normalized_note,
        submitted_at=str(submitted_at),
        feedback_hash=_feedback_hash(material),
        slot_id=normalized_slot,
    )


def _load_feedback(path: Path) -> FeedbackRecord:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FeedbackViolation("Feedback record is not valid JSON") from error
    if not isinstance(record, Mapping) or record.get("schema") != FEEDBACK_SCHEMA:
        raise FeedbackViolation("Unsupported feedback schema")
    if _feedback_hash(record) != record.get("feedback_hash"):
        raise FeedbackViolation("Feedback hash does not match its content")
    rating, note = _validate_input(record.get("rating"), str(record.get("note", "")))
    result = FeedbackRecord(
        feedback_id=str(record.get("feedback_id", "")),
        receipt_id=str(record.get("receipt_id", "")),
        source_timeline_hash=str(record.get("source_timeline_hash", "")),
        source_receipt_hash=str(record.get("source_receipt_hash", "")),
        rating=rating,
        note=note,
        submitted_at=str(record.get("submitted_at", "")),
        feedback_hash=str(record.get("feedback_hash", "")),
        slot_id=validate_slot(record.get("slot_id", DEFAULT_SLOT)),
    )
    workspace = path.parent.parent if result.slot_id == DEFAULT_SLOT else path.parent.parent.parent.parent
    if feedback_path(workspace, result.feedback_id, result.slot_id) != path:
        raise FeedbackViolation("Feedback path and identifier do not agree")
    if len(result.source_timeline_hash) != 64 or len(result.source_receipt_hash) != 64:
        raise FeedbackViolation("Feedback source hashes are malformed")
    return result


def record_feedback(workspace: Path, record: FeedbackRecord, slot: str = DEFAULT_SLOT) -> tuple[str, FeedbackRecord, Path]:
    """Write one immutable feedback record, or prove an identical prior one."""

    normalized_slot = validate_slot(slot)
    if record.slot_id != normalized_slot:
        raise FeedbackViolation("Feedback record slot does not match the requested slot")
    path = feedback_path(workspace, record.feedback_id, normalized_slot)
    content = canonical_json(record.to_dict()) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = _load_feedback(path)
        if canonical_json(existing.to_dict()) != canonical_json(record.to_dict()):
            raise FeedbackViolation("Existing feedback record differs from the submitted feedback")
        return "feedback_already_recorded", existing, path
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise FeedbackViolation("An incomplete feedback temporary file exists")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise FeedbackViolation("Refusing to overwrite an existing feedback record")
        os.replace(temporary, path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    return "feedback_recorded", record, path


def load_feedback(workspace: Path, feedback_id: str, slot: str = DEFAULT_SLOT) -> FeedbackRecord:
    normalized_slot = validate_slot(slot)
    path = feedback_path(workspace, feedback_id, normalized_slot)
    if not path.is_file():
        raise FeedbackViolation("Feedback record does not exist")
    result = _load_feedback(path)
    if result.slot_id != normalized_slot:
        raise FeedbackViolation("Feedback record slot does not match the requested slot")
    return result
