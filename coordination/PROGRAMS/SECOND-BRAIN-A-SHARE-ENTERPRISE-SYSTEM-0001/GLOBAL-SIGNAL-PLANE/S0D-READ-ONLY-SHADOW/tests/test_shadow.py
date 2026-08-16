from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from global_signal_shadow.adapter import ALLOWED_PATHS, AI_FILM_COMMIT, AI_FILM_REPOSITORY, PROJECT_INDEX_BLOB, ReadOnlyExactCommitAdapter, ShadowError, ShadowLedger, SourceObservation, self_shadow

ROOT = Path(__file__).resolve().parents[1]
def write_source(root: Path, paths: tuple[str, ...] = ALLOWED_PATHS) -> None:
    for path in paths:
        target = root / path; target.parent.mkdir(parents=True, exist_ok=True)
        text = "schema_version: v1\nstatus: active\n"
        if path == "PROJECT_INDEX.yaml": text += "project_id: EUSTIA_AI_FILM\nsource_authority: this_file\n"
        target.write_text(text, encoding="utf-8")
    index = root / "PROJECT_INDEX.yaml"
    # Fixture adapter uses the known object id only after overriding its expected payload in individual tests.

class ShadowTest(unittest.TestCase):
    def source(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        directory = tempfile.TemporaryDirectory(); root = Path(directory.name); write_source(root); return directory, root
    def observation(self, path: str = "10_运行时/pending_canonical_writes.yaml", state: str = "PENDING") -> SourceObservation:
        return SourceObservation(AI_FILM_REPOSITORY, AI_FILM_COMMIT, path, "a" * 40, "b" * 64, "PROJECT_INDEX.yaml", {"schema_version":"v1"}, (state,))
    def test_allowlist_write_rejection_and_drift_fail_closed(self) -> None:
        directory, root = self.source(); self.addCleanup(directory.cleanup)
        adapter = ReadOnlyExactCommitAdapter(root)
        with self.assertRaises(ShadowError) as forbidden: adapter.read("03_剧本.md")
        self.assertEqual(forbidden.exception.code, "FORBIDDEN_SOURCE_PATH")
        with self.assertRaises(ShadowError) as write: adapter.write("x", "y")
        self.assertEqual(write.exception.code, "CROSS_REPO_WRITE_FORBIDDEN")
        with self.assertRaises(ShadowError) as drift: ReadOnlyExactCommitAdapter(root, commit="0" * 40)
        self.assertEqual(drift.exception.code, "SOURCE_COMMIT_DRIFT")
    def test_history_idempotency_omission_unknown_and_bootstrap_are_mechanism_derived(self) -> None:
        ledger = ShadowLedger(); first = self.observation(state="UNKNOWN")
        self.assertEqual(ledger.append(first)["status"], "ADMITTED"); self.assertEqual(ledger.append(first)["status"], "IDEMPOTENT_DUPLICATE")
        projection = ledger.projection(); self.assertEqual(projection["backlog_state"], "AI_FILM_DOMAIN_BACKLOG_BOOTSTRAP_REQUIRED")
        self.assertIn(first.path, projection["unresolved_paths"]); self.assertEqual(len(ledger.history()), 1)
    def test_status_history_replay_and_self_drift_are_observed(self) -> None:
        ledger = ShadowLedger(); ledger.append(self.observation(state="PENDING")); before = ledger.projection(); after = ledger.projection()
        self.assertEqual(before["checksum"], after["checksum"]); self.assertIn("PENDING", before["observed_states"])
        stale = {"repository":"vxz2datoubo/second-brain-coordination","main":"old","task_id":"t","route":"r","work_claim":"c","program_lane":"p"}
        current = dict(stale, main="new")
        self.assertEqual(self_shadow(stale, current)["codes"], ["CROSS_WINDOW_STATE_DRIFT"])
    def test_public_projection_has_no_raw_body_or_private_marker(self) -> None:
        ledger = ShadowLedger(); ledger.append(self.observation()); encoded = json.dumps(ledger.projection())
        self.assertNotIn("screenplay", encoded.casefold()); self.assertNotIn("private", encoded.casefold())
