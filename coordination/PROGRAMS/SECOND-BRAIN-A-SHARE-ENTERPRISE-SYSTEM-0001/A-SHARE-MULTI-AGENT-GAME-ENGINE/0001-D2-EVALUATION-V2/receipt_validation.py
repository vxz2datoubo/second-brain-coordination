"""Fail-closed validation for E26 completion evidence carriers."""
from __future__ import annotations


REQUIRED_COMPLETION_FIELDS = frozenset({
    "task_id", "route_epoch", "completion_signal", "pull_request", "issue",
    "branch", "reviewed_base", "remote_main_before", "remote_main_after",
    "tested_commit", "tested_parent", "receipt_commit", "changed_files",
    "commands", "unknowns", "negative_findings", "archive_evidence",
})


def validate_completion_evidence(carrier: dict[str, object]) -> None:
    missing = sorted(REQUIRED_COMPLETION_FIELDS - set(carrier))
    if missing:
        raise ValueError("E26_COMPLETION_EVIDENCE_MISSING:" + ",".join(missing))
    placeholders = {
        key for key, value in carrier.items()
        if value in (None, "", "TBD", "THIS_COMMIT", "THIS_COMMIT_AFTER_PUSH")
    }
    if placeholders:
        raise ValueError("E26_COMPLETION_EVIDENCE_PLACEHOLDER:" + ",".join(sorted(placeholders)))
    if not isinstance(carrier["changed_files"], list) or not isinstance(carrier["commands"], list):
        raise ValueError("E26_COMPLETION_EVIDENCE_INVALID_COLLECTION")
    archive_evidence = carrier["archive_evidence"]
    if not isinstance(archive_evidence, dict) or archive_evidence.get("exact_commit") != carrier["tested_commit"]:
        raise ValueError("E26_COMPLETION_EVIDENCE_ARCHIVE_COMMIT_MISMATCH")
