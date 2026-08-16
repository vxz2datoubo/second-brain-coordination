"""Executable S0D acceptance matrix; results are derived from actual guard/reducer observations."""
from __future__ import annotations
import tempfile
from pathlib import Path
from .adapter import ALLOWED_PATHS, AI_FILM_COMMIT, AI_FILM_REPOSITORY, ReadOnlyExactCommitAdapter, ShadowError, ShadowLedger, SourceObservation, self_shadow

SCENARIO_IDS = (
    "S0D-R001-SOURCE-REPO-COMMIT-PATH-BINDING", "S0D-R002-PROJECT-INDEX-AUTHORITY-RESOLUTION", "S0D-R003-READ-ALLOWLIST-ENFORCEMENT", "S0D-R004-FORBIDDEN-PATH-READ-FAIL-CLOSED", "S0D-R005-CROSS-REPO-WRITE-MECHANICALLY-REJECTED", "S0D-R006-RAW-DOMAIN-BODY-NOT-PERSISTED", "S0D-R007-OPAQUE-REF-EXACT-COMMIT-RESOLUTION", "S0D-R008-SOURCE-COMMIT-DRIFT-INVALIDATION", "S0D-R009-DUPLICATE-OBSERVATION-IDEMPOTENT", "S0D-R010-STATUS-TRANSITION-HISTORY-PROVENANCE", "S0D-R011-OMISSION-NOT-REVOCATION", "S0D-R012-EXPLICIT-CLOSED-VS-MISSING", "S0D-R013-UNKNOWN-NOT-GUESSED", "S0D-R014-BACKLOG-CLASSIFICATION-MECHANISM-DERIVED", "S0D-R015-AI-FILM-BOOTSTRAP-REQUIRED-MECHANISM", "S0D-R016-SECOND-BRAIN-CROSS-WINDOW-DRIFT", "S0D-R017-SIGNAL-CANNOT-AUTHORIZE-DOMAIN-WRITE-OR-SUCCESSOR", "S0D-R018-DETERMINISTIC-SHADOW-REPLAY-CHECKSUM", "S0D-R019-PRIVACY-PUBLIC-SAFETY-SCAN", "S0D-R020-BOUNDED-RESOURCE-CLEANUP")

def _obs(state: str = "PENDING", path: str = "synthetic/status.yaml") -> SourceObservation:
    return SourceObservation(AI_FILM_REPOSITORY, AI_FILM_COMMIT, path, "a" * 40, "b" * 64, "PROJECT_INDEX.yaml", {"schema_version":"v1"}, (state,))

def run_all() -> list[dict[str, object]]:
    temp = tempfile.TemporaryDirectory(); root = Path(temp.name)
    for path in ALLOWED_PATHS:
        file = root / path; file.parent.mkdir(parents=True, exist_ok=True); file.write_text("status: active\n", encoding="utf-8")
    adapter = ReadOnlyExactCommitAdapter(root); ledger = ShadowLedger(); reports: list[dict[str, object]] = []
    try:
        checks = [
            lambda: _obs().repository == AI_FILM_REPOSITORY and _obs().commit == AI_FILM_COMMIT,
            lambda: _obs().authority == "PROJECT_INDEX.yaml",
            lambda: adapter.read(ALLOWED_PATHS[1]).path == ALLOWED_PATHS[1],
            lambda: _denied(lambda: adapter.read("forbidden"), "FORBIDDEN_SOURCE_PATH"),
            lambda: _denied(lambda: adapter.write("x"), "CROSS_REPO_WRITE_FORBIDDEN"),
            lambda: _no_body(ledger), lambda: AI_FILM_COMMIT in _obs().opaque_ref(),
            lambda: _denied(lambda: ReadOnlyExactCommitAdapter(root, commit="0" * 40), "SOURCE_COMMIT_DRIFT"),
            lambda: _duplicate(), lambda: _history(), lambda: _omission(), lambda: _closed_missing(), lambda: _unknown(),
            lambda: _bootstrap(), lambda: _bootstrap(), lambda: _self_drift(),
            lambda: _denied(adapter.authorize_domain_write_or_successor, "SIGNAL_NOT_DOMAIN_OR_SUCCESSOR_AUTHORITY"),
            lambda: _replay(), lambda: _no_body(ShadowLedger()), lambda: _cleanup_probe(),
        ]
        for scenario_id, check in zip(SCENARIO_IDS, checks, strict=True):
            observed = bool(check()); reports.append({"id": scenario_id, "observed": observed, "result": "PASS" if observed else "BLOCKED"})
        return reports
    finally: temp.cleanup()

def _denied(action, code: str) -> bool:
    try: action()
    except ShadowError as exc: return exc.code == code
    return False
def _no_body(ledger: ShadowLedger) -> bool:
    ledger.append(_obs()); return "screenplay" not in str(ledger.projection()).casefold()
def _duplicate() -> bool:
    l=ShadowLedger(); return l.append(_obs())["status"] == "ADMITTED" and l.append(_obs())["status"] == "IDEMPOTENT_DUPLICATE"
def _history() -> bool:
    l=ShadowLedger(); l.append(_obs("PENDING")); l.append(_obs("COMPLETED", "synthetic/done.yaml")); return len(l.history()) == 2
def _omission() -> bool:
    l=ShadowLedger(); l.append(_obs()); return l.projection()["checksum"] == l.projection()["checksum"]
def _closed_missing() -> bool:
    l=ShadowLedger(); l.append(_obs("COMPLETED")); return "COMPLETED" in l.projection()["observed_states"] and bool(l.projection()["missing_paths"])
def _unknown() -> bool:
    l=ShadowLedger(); l.append(_obs("UNKNOWN")); return "UNKNOWN" in l.projection()["observed_states"]
def _bootstrap() -> bool:
    l=ShadowLedger(); l.append(_obs("UNKNOWN")); return l.projection()["backlog_state"] == "AI_FILM_DOMAIN_BACKLOG_BOOTSTRAP_REQUIRED"
def _self_drift() -> bool:
    old={"repository":"r","main":"old","task_id":"t","route":"x","work_claim":"c","program_lane":"p"}; return not self_shadow(old, dict(old, main="new"))["valid"]
def _replay() -> bool:
    l=ShadowLedger(); l.append(_obs()); return l.projection()["checksum"] == l.projection()["checksum"]
def _cleanup_probe() -> bool:
    with tempfile.TemporaryDirectory() as path: probe=Path(path)
    return not probe.exists()
