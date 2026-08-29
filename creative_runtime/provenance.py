"""Programmatic source-provenance gate for task-local creative artifacts."""

from __future__ import annotations

from dataclasses import dataclass


class ProvenanceViolation(ValueError):
    """Raised when a local or unregistered source attempts to enter the runtime."""


@dataclass(frozen=True)
class SourceProvenance:
    source_id: str
    classification: str
    approved_for_reuse: bool
    gpt_import_record: str | None = None


def require_reusable_source(source: SourceProvenance) -> None:
    if source.classification in {"LOCAL_UNVERIFIED", "WORKBUDDY_UNCOMMITTED"}:
        raise ProvenanceViolation("Local or WorkBuddy material is not a reusable GitHub source")
    if not source.approved_for_reuse or not source.gpt_import_record:
        raise ProvenanceViolation("Reuse requires a GPT-auditable source import record")
