from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from global_signal_shadow.adapter import (
    DurableShadowAdmission,
    ReadOnlyExactCommitAdapter,
    ShadowError,
    build_second_brain_snapshot,
    one_shot_receipt,
    self_shadow,
)
from global_signal_shadow.fixtures import commit_control_task, commit_source_status, make_control_fixture, make_source_fixture


class ExactBindingAndDurabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.commit, self.binding = make_source_fixture(self.source)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_b01_root_head_tree_blob_and_worktree_payload_are_all_required(self) -> None:
        adapter = ReadOnlyExactCommitAdapter(self.source, binding=self.binding)
        observation = adapter.read("pending_canonical_writes.yaml")
        self.assertEqual(observation.commit, self.commit)
        self.assertEqual(observation.blob_sha, self.binding.blob_for(observation.path))
        path = self.source / observation.path
        path.write_text(path.read_text(encoding="utf-8") + "# changed after exact commit\n", encoding="utf-8")
        with self.assertRaises(ShadowError) as mismatch:
            adapter.read(observation.path)
        self.assertEqual(mismatch.exception.code, "SOURCE_WORKTREE_PAYLOAD_MISMATCH")

    def test_b02_uses_s0c_sqlite_idempotency_transition_and_fresh_replay(self) -> None:
        first = ReadOnlyExactCommitAdapter(self.source, binding=self.binding).read("pending_canonical_writes.yaml")
        db_path = self.root / "ledger.sqlite"
        admission = DurableShadowAdmission(db_path)
        try:
            initial = admission.admit(first, source_sequence=1)
            self.assertEqual(initial["event"]["status"], "ADMITTED")
            self.assertEqual(admission.admit(first, source_sequence=1)["event"]["status"], "IDEMPOTENT_DUPLICATE")
            _, second_binding = commit_source_status(self.source, "completed")
            second = ReadOnlyExactCommitAdapter(self.source, binding=second_binding).read("pending_canonical_writes.yaml")
            transitioned = admission.admit(second, source_sequence=2)
            projection = admission.ledger.current_projection()
            self.assertIsNotNone(projection)
            self.assertEqual(initial["signal_id"], transitioned["signal_id"])
            self.assertEqual(projection["signals"][0]["execution_state"], "DONE")
            self.assertEqual(len(projection["signals"][0]["provenance_event_refs"]), 2)
            replay = admission.durable_replay_receipt()
            self.assertTrue(replay["match"])
            self.assertEqual(replay["history_count"], 2)
        finally:
            admission.close()

    def test_b03_omission_is_a_noop_not_an_implicit_revoke(self) -> None:
        observation = ReadOnlyExactCommitAdapter(self.source, binding=self.binding).read("pending_canonical_writes.yaml")
        admission = DurableShadowAdmission(self.root / "omission.sqlite")
        try:
            admission.admit_snapshot([observation])
            before = admission.ledger.history()
            self.assertEqual(admission.admit_snapshot([]), [])
            after = admission.ledger.history()
            self.assertEqual(before, after)
            self.assertTrue(all(not event["revokes_refs"] for event in after))
        finally:
            admission.close()

    def test_b04_registry_state_does_not_override_nested_item_state(self) -> None:
        target = self.source / "pending_canonical_writes.yaml"
        target.write_text(
            "registry_id: fixture-pending\nstatus: active\nitems:\n  - id: ITEM-001\n    status: completed\n",
            encoding="utf-8",
        )
        _, binding = commit_source_status(self.source, "completed")
        observation = ReadOnlyExactCommitAdapter(self.source, binding=binding).read("pending_canonical_writes.yaml")
        self.assertEqual(observation.derived_state, "COMPLETED")
        self.assertEqual(observation.derived_items[0].stable_ref, "pending_canonical_writes.yaml#items/ITEM-001")
        self.assertEqual(observation.derived_items[0].state, "COMPLETED")
        self.assertNotEqual(observation.derived_state, "ACTIVE")

    def test_b05_receipt_is_public_safe_and_contains_per_observation_binding(self) -> None:
        adapter = ReadOnlyExactCommitAdapter(self.source, binding=self.binding)
        control = self.root / "control"
        control_commit = make_control_fixture(control)
        receipt = one_shot_receipt(adapter, db_path=self.root / "receipt.sqlite", second_brain_root=control, second_brain_commit=control_commit)
        self.assertEqual(len(receipt["observations"]), len(self.binding.allowed_paths))
        for observation in receipt["observations"]:
            self.assertEqual(set(("repository", "commit", "path", "blob_sha", "content_sha256", "schema_ref", "derived_state", "opaque_ref")) - set(observation), set())
        encoded = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("synthetic fixture domain body", encoded)
        self.assertTrue(receipt["durable_s0c_admission"]["replay"]["match"])
        self.assertTrue(receipt["second_brain_self_shadow"]["drift_result"]["valid"])

    def test_b03_self_shadow_is_built_from_git_bound_control_snapshots(self) -> None:
        control = self.root / "control-drift"
        first = make_control_fixture(control, task_id="TASK-A")
        snapshot = build_second_brain_snapshot(control, commit=first)
        second = commit_control_task(control, "TASK-B")
        drift = self_shadow(snapshot, build_second_brain_snapshot(control, commit=second))
        self.assertFalse(drift["valid"])
        self.assertEqual(drift["codes"], ["CROSS_WINDOW_STATE_DRIFT"])
