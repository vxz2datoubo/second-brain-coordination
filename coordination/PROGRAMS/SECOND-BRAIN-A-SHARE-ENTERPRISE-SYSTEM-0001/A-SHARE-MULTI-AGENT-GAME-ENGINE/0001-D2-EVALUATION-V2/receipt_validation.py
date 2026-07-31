"""Fail-closed validation for Evaluation V2 completion evidence carriers."""
from __future__ import annotations


WPDCR_REQUIRED_SECTIONS = frozenset({
    "route_context",
    "command_claim_and_execution_trace",
    "primary_work_and_process_trace",
    "difficulty_and_complexity",
    "new_and_unexpected_discoveries",
    "expandable_ideas_and_high_value_opportunities",
    "unresolved_hard_problems_and_unknowns",
    "problems_failures_and_negative_results",
    "coordination_requests",
    "cross_agent_handoff_and_system_impact",
    "decisions_alternatives_and_lessons",
    "next_action_and_gate",
    "report_integrity",
})

ARCHIVE_RECEIPT_REQUIRED_FIELDS = frozenset({
    "archive_run_id", "commit", "archive_sha256", "archive_size_bytes",
    "extracted_file_count", "root_id", "root_path_sha256", "artifacts", "commands",
})

ARCHIVE_ARTIFACT_REQUIRED_FIELDS = frozenset({"relative_path", "sha256", "size_bytes"})

ARCHIVE_COMMAND_REQUIRED_FIELDS = frozenset({
    "name", "command", "working_directory_relative", "script_relative_path",
    "exit_code", "stdout_sha256", "stderr_sha256",
})

REQUIRED_COMPLETION_FIELDS = frozenset({
    "task_id", "route_epoch", "completion_signal", "pull_request", "issue",
    "branch", "reviewed_base", "remote_main_before", "remote_main_after",
    "tested_commit", "tested_parent", "receipt_commit", "changed_files",
    "commands", "unknowns", "negative_findings", "archive_evidence", "wpdcr",
})


def validate_wpdcr_sections(wpdcr: dict[str, object]) -> None:
    if not isinstance(wpdcr, dict):
        raise ValueError("E28_WPDCR_NOT_A_MAPPING")
    missing = sorted(WPDCR_REQUIRED_SECTIONS - set(wpdcr))
    if missing:
        raise ValueError("E28_WPDCR_REQUIRED_SECTION_MISSING:" + ",".join(missing))
    if any(wpdcr[section] in (None, "", [], {}) for section in WPDCR_REQUIRED_SECTIONS):
        raise ValueError("E28_WPDCR_REQUIRED_SECTION_EMPTY")


def validate_archive_evidence(archive_evidence: dict[str, object], expected_commit: str) -> None:
    if not isinstance(archive_evidence, dict) or archive_evidence.get("exact_commit") != expected_commit:
        raise ValueError("E26_COMPLETION_EVIDENCE_ARCHIVE_COMMIT_MISMATCH")
    receipts = archive_evidence.get("archive_receipts")
    if not isinstance(receipts, list) or len(receipts) != 3:
        raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_RECEIPT_COUNT")
    root_ids: set[str] = set()
    root_path_hashes: set[str] = set()
    archive_bytes: set[tuple[str, int]] = set()
    artifact_manifests: set[tuple[tuple[str, str, int], ...]] = set()
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_RECEIPT_INVALID")
        missing = ARCHIVE_RECEIPT_REQUIRED_FIELDS - set(receipt)
        if missing:
            raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_RECEIPT_MISSING:" + ",".join(sorted(missing)))
        if receipt["commit"] != expected_commit:
            raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_RECEIPT_COMMIT_MISMATCH")
        root_id = receipt["root_id"]
        root_path_sha256 = receipt["root_path_sha256"]
        if not isinstance(root_id, str) or not root_id or not isinstance(root_path_sha256, str) or not root_path_sha256:
            raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_ROOT_MISSING")
        root_ids.add(root_id)
        root_path_hashes.add(root_path_sha256)
        archive_sha256 = receipt["archive_sha256"]
        archive_size_bytes = receipt["archive_size_bytes"]
        if not isinstance(archive_sha256, str) or not archive_sha256 or not isinstance(archive_size_bytes, int) or archive_size_bytes < 1:
            raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_BYTES_INVALID")
        archive_bytes.add((archive_sha256, archive_size_bytes))
        artifacts = receipt["artifacts"]
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_ARTIFACTS_MISSING")
        manifest = []
        for artifact in artifacts:
            if not isinstance(artifact, dict) or ARCHIVE_ARTIFACT_REQUIRED_FIELDS - set(artifact):
                raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_ARTIFACT_INVALID")
            path = artifact["relative_path"]
            digest = artifact["sha256"]
            size = artifact["size_bytes"]
            if not isinstance(path, str) or not path or path.startswith(("/", "\\")) or ":" in path or ".." in path.replace("\\", "/").split("/"):
                raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_ARTIFACT_PATH_INVALID")
            if not isinstance(digest, str) or not digest or not isinstance(size, int) or size < 0:
                raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_ARTIFACT_VALUE_INVALID")
            manifest.append((path, digest, size))
        if len({item[0] for item in manifest}) != len(manifest):
            raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_ARTIFACT_PATH_DUPLICATE")
        artifact_manifests.add(tuple(manifest))
        commands = receipt["commands"]
        if not isinstance(commands, list) or not commands:
            raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_COMMANDS_MISSING")
        for command in commands:
            if not isinstance(command, dict) or ARCHIVE_COMMAND_REQUIRED_FIELDS - set(command):
                raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_COMMAND_INVALID")
            command_tokens = command["command"]
            script = command["script_relative_path"]
            cwd = command["working_directory_relative"]
            if not isinstance(command_tokens, list) or not command_tokens or not isinstance(script, str) or not script:
                raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_COMMAND_PATH_MISSING")
            if command_tokens[-1] != script or script.startswith(("/", "\\")) or ":" in script or ".." in script.replace("\\", "/").split("/"):
                raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_COMMAND_ESCAPES_ROOT")
            if not isinstance(cwd, str) or not cwd or cwd.startswith(("/", "\\")) or ":" in cwd or ".." in cwd.replace("\\", "/").split("/"):
                raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_COMMAND_WORKING_DIRECTORY_INVALID")
            if command["exit_code"] != 0:
                raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_COMMAND_NOT_GREEN")
    if len(root_ids) != 3 or len(root_path_hashes) != 3:
        raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_ROOT_NOT_DISTINCT")
    if len(archive_bytes) != 1:
        raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_BYTES_DRIFT")
    if len(artifact_manifests) != 1:
        raise ValueError("E28_COMPLETION_EVIDENCE_ARCHIVE_ARTIFACT_MANIFEST_DRIFT")


def validate_completion_evidence(
    carrier: dict[str, object],
    *,
    expected_completion_signal: str | None = None,
) -> None:
    missing = sorted(REQUIRED_COMPLETION_FIELDS - set(carrier))
    if missing:
        raise ValueError("E26_COMPLETION_EVIDENCE_MISSING:" + ",".join(missing))
    placeholders = {
        key for key, value in carrier.items()
        if value in (None, "", "TBD", "THIS_COMMIT", "THIS_COMMIT_AFTER_PUSH")
    }
    if placeholders:
        raise ValueError("E26_COMPLETION_EVIDENCE_PLACEHOLDER:" + ",".join(sorted(placeholders)))
    if expected_completion_signal is not None and carrier["completion_signal"] != expected_completion_signal:
        raise ValueError("E28_COMPLETION_EVIDENCE_COMPLETION_SIGNAL_MISMATCH")
    if not isinstance(carrier["changed_files"], list) or not isinstance(carrier["commands"], list):
        raise ValueError("E26_COMPLETION_EVIDENCE_INVALID_COLLECTION")
    validate_archive_evidence(carrier["archive_evidence"], carrier["tested_commit"])
    validate_wpdcr_sections(carrier["wpdcr"])
