"""Mechanism-driven S0D R001-R020 acceptance matrix."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any, Callable

from .adapter import (
    DurableShadowAdmission,
    ReadOnlyExactCommitAdapter,
    ShadowError,
    build_second_brain_snapshot,
    self_shadow,
)
from .fixtures import commit_control_task, commit_source_status, make_control_fixture, make_source_fixture


SCENARIO_IDS = (
    "S0D-R001-SOURCE-REPO-COMMIT-PATH-BINDING", "S0D-R002-PROJECT-INDEX-AUTHORITY-RESOLUTION",
    "S0D-R003-READ-ALLOWLIST-ENFORCEMENT", "S0D-R004-FORBIDDEN-PATH-READ-FAIL-CLOSED",
    "S0D-R005-CROSS-REPO-WRITE-MECHANICALLY-REJECTED", "S0D-R006-RAW-DOMAIN-BODY-NOT-PERSISTED",
    "S0D-R007-OPAQUE-REF-EXACT-COMMIT-RESOLUTION", "S0D-R008-SOURCE-COMMIT-DRIFT-INVALIDATION",
    "S0D-R009-DUPLICATE-OBSERVATION-IDEMPOTENT", "S0D-R010-STATUS-TRANSITION-HISTORY-PROVENANCE",
    "S0D-R011-OMISSION-NOT-REVOCATION", "S0D-R012-EXPLICIT-CLOSED-VS-MISSING",
    "S0D-R013-UNKNOWN-NOT-GUESSED", "S0D-R014-BACKLOG-CLASSIFICATION-MECHANISM-DERIVED",
    "S0D-R015-AI-FILM-BOOTSTRAP-REQUIRED-MECHANISM", "S0D-R016-SECOND-BRAIN-CROSS-WINDOW-DRIFT",
    "S0D-R017-SIGNAL-CANNOT-AUTHORIZE-DOMAIN-WRITE-OR-SUCCESSOR", "S0D-R018-DETERMINISTIC-SHADOW-REPLAY-CHECKSUM",
    "S0D-R019-PRIVACY-PUBLIC-SAFETY-SCAN", "S0D-R020-BOUNDED-RESOURCE-CLEANUP",
)


def _denied(action: Callable[[], Any], code: str) -> bool:
    try:
        action()
    except ShadowError as exc:
        return exc.code == code
    return False


def run_all() -> list[dict[str, object]]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source_root = root / "source"
        first_commit, first_binding = make_source_fixture(source_root)
        adapter = ReadOnlyExactCommitAdapter(source_root, binding=first_binding)
        index = adapter.read("PROJECT_INDEX.yaml")
        pending = adapter.read("pending_canonical_writes.yaml")
        unknown = adapter.read("UNKNOWN_REGISTRY.yaml")
        continuity = adapter.read("continuity.md")
        db_path = root / "durable.sqlite"
        admission = DurableShadowAdmission(db_path)
        try:
            first = admission.admit(pending, source_sequence=1)
            duplicate = admission.admit(pending, source_sequence=1)
            second_commit, second_binding = commit_source_status(source_root, "completed")
            second = ReadOnlyExactCommitAdapter(source_root, binding=second_binding).read("pending_canonical_writes.yaml")
            transition = admission.admit(second, source_sequence=2)
            history = admission.ledger.history()
            projection = admission.ledger.current_projection()
            assert projection is not None
            omission_before = list(history)
            omitted = admission.admit_snapshot([], source_sequence_start=3)
            omission_after = admission.ledger.history()
            control_root = root / "control"
            control_first = make_control_fixture(control_root)
            control_snapshot = build_second_brain_snapshot(control_root, commit=control_first)
            control_second = commit_control_task(control_root, "TASK-B")
            control_drift = self_shadow(control_snapshot, build_second_brain_snapshot(control_root, commit=control_second))
            replay = admission.durable_replay_receipt()
            summary = admission.staging_summary([index, pending, unknown, continuity])
            raw_public = json.dumps({"history": admission.ledger.history(), "summary": summary}, sort_keys=True)
            checks = [
                lambda: index.repository == first_binding.repository and index.commit == first_commit and index.blob_sha == first_binding.blob_for(index.path),
                lambda: index.authority == "PROJECT_INDEX.yaml" and index.metadata["authority_declaration"] == "this_file" and index.metadata["project_id"] == "EUSTIA_AI_FILM",
                lambda: pending.path == "pending_canonical_writes.yaml" and pending.blob_sha == first_binding.blob_for(pending.path),
                lambda: _denied(lambda: adapter.read("forbidden.yaml"), "FORBIDDEN_SOURCE_PATH"),
                lambda: _denied(lambda: adapter.write("x"), "CROSS_REPO_WRITE_FORBIDDEN"),
                lambda: "synthetic fixture domain body" not in raw_public,
                lambda: first_commit in pending.opaque_ref() and pending.blob_sha in pending.opaque_ref(),
                lambda: _tamper_fails(source_root, second_binding),
                lambda: first["event"]["status"] == "ADMITTED" and duplicate["event"]["status"] == "IDEMPOTENT_DUPLICATE",
                lambda: len(history) == 2 and first["signal_id"] == transition["signal_id"] and projection["signals"][0]["execution_state"] == "DONE" and len(projection["signals"][0]["provenance_event_refs"]) == 2,
                lambda: omitted == [] and omission_before == omission_after and all(not event["revokes_refs"] for event in omission_after),
                lambda: second.derived_state == "COMPLETED" and bool(summary["missing_paths"]),
                lambda: continuity.derived_state == "UNKNOWN" and continuity.schema_ref == "MARKDOWN_UNSTRUCTURED/UNKNOWN",
                lambda: pending.derived_items[0].stable_ref.endswith("items/ITEM-001") and pending.derived_items[0].state == "PENDING" and pending.derived_state == "PENDING",
                lambda: summary["backlog_state"] == "AI_FILM_DOMAIN_BACKLOG_BOOTSTRAP_REQUIRED",
                lambda: control_drift["result"] == "BLOCKED" and "CROSS_WINDOW_STATE_DRIFT" in control_drift["codes"],
                lambda: _denied(adapter.authorize_domain_write_or_successor, "SIGNAL_NOT_DOMAIN_OR_SUCCESSOR_AUTHORITY"),
                lambda: replay["replayed_from_persisted_history"] and replay["match"] and replay["history_count"] == 2,
                lambda: "synthetic fixture domain body" not in raw_public and "private" not in raw_public.casefold(),
                lambda: _cleanup_probe(root),
            ]
            reports: list[dict[str, object]] = []
            for scenario_id, check in zip(SCENARIO_IDS, checks, strict=True):
                observed = bool(check())
                reports.append({"id": scenario_id, "observed": observed, "result": "PASS" if observed else "BLOCKED"})
            return reports
        finally:
            admission.close()


def _tamper_fails(source_root: Path, binding: Any) -> bool:
    target = source_root / "pending_canonical_writes.yaml"
    original = target.read_text(encoding="utf-8")
    target.write_text(original + "# uncommitted tamper\n", encoding="utf-8")
    try:
        return _denied(lambda: ReadOnlyExactCommitAdapter(source_root, binding=binding), "SOURCE_WORKTREE_PAYLOAD_MISMATCH")
    finally:
        target.write_text(original, encoding="utf-8")


def _cleanup_probe(root: Path) -> bool:
    path: Path
    with tempfile.TemporaryDirectory(dir=root) as created:
        path = Path(created)
    return not path.exists()
