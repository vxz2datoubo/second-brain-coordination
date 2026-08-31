from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from creative_runtime import continuation
from creative_runtime.contracts import canonical_json
from creative_runtime.ledger import CreativeLedger, LedgerViolation


ROOT = Path(__file__).resolve().parents[1]


def cli_module():
    spec = importlib.util.spec_from_file_location("cli_r171", ROOT / "apps" / "cli" / "creativectl.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_envelope(workspace: Path, slot: str | None = None) -> dict:
    path = (
        workspace / "saves" / "slots" / f"{slot}.json"
        if slot is not None
        else workspace / "saves" / "default.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def write_envelope(workspace: Path, envelope: dict, slot: str | None = None) -> None:
    path = (
        workspace / "saves" / "slots" / f"{slot}.json"
        if slot is not None
        else workspace / "saves" / "default.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(envelope) + "\n", encoding="utf-8")


def rebuild_records(records: list[dict], mutator=None, order: list[int] | None = None) -> list[dict]:
    ledger = CreativeLedger()
    indexes = order if order is not None else list(range(len(records)))
    for new_sequence, original_index in enumerate(indexes):
        record = records[original_index]
        payload = copy.deepcopy(record["payload"])
        event_type = record["event_type"]
        occurred_at = record["occurred_at"]
        parents = tuple(record.get("parent_artifact_ids", ()))
        if mutator is not None:
            event_type, payload, occurred_at = mutator(
                new_sequence,
                original_index,
                event_type,
                payload,
                occurred_at,
            )
        ledger.append(event_type, payload, occurred_at, parents)
    return ledger.to_records()


class R171ContinuationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = cli_module()

    def _legacy(self, workspace: Path, *actions: str) -> bytes:
        self.cli.initialize(workspace)
        for action in actions:
            result = self.cli.choose(workspace, action)
            self.assertEqual(result["status"], "chosen")
        return (workspace / "session.json").read_bytes()

    def _assert_all_consumers_reject(self, workspace: Path) -> None:
        consumers = (
            lambda: continuation.load_session(workspace),
            lambda: continuation.state(workspace),
            lambda: continuation.timeline(workspace),
            lambda: continuation.director_sequence(workspace),
            lambda: continuation.review_packet(workspace),
            lambda: continuation.view(workspace),
        )
        for consumer in consumers:
            with self.subTest(consumer=consumer):
                with self.assertRaises(LedgerViolation):
                    consumer()

    def test_end_to_end_migration_choose_say_slots_and_consumers_share_one_history(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            original = self._legacy(workspace, "listen")
            migrated = continuation.migrate(workspace)
            self.assertEqual(migrated["schema"], "CreativeSession/v2")
            self.assertNotIn("actions", migrated)
            initial_receipt = copy.deepcopy(migrated["migration"])

            choose_result = self.cli.choose(workspace, "knock")
            self.assertTrue(choose_result["v2"])
            self.assertEqual(choose_result["state"]["beat_id"], "threshold")
            continuation.save_slot(workspace, "after-knock")

            say_result = self.cli.say(workspace, "I listen carefully")
            self.assertTrue(say_result["v2"])
            self.assertEqual(say_result["state"]["beat_id"], "accord")
            continuation.save_default(workspace)
            continuation.save_default(workspace)
            continuation.save_slot(workspace, "after-promise")

            self.assertEqual((workspace / "session.json").read_bytes(), original)
            self.assertEqual(read_envelope(workspace)["migration"], initial_receipt)
            self.assertEqual(read_envelope(workspace, "after-knock")["migration"], initial_receipt)
            self.assertEqual(read_envelope(workspace, "after-promise")["migration"], initial_receipt)

            restored = continuation.restore_slot(workspace, "after-knock")
            self.assertEqual(restored.beat_id, "threshold")
            resumed = self.cli.say(workspace, "promise to listen carefully")
            self.assertEqual(resumed["state"]["beat_id"], "accord")
            self.assertEqual((workspace / "session.json").read_bytes(), original)

            session = continuation.load_session(workspace)
            final_state = session.state().to_dict()
            timeline = continuation.timeline(workspace)
            director = continuation.director_sequence(workspace)
            packet = continuation.review_packet(workspace)
            self.assertEqual(timeline["final_state"], final_state)
            self.assertEqual(director["final_state"], final_state)
            self.assertEqual(packet["final_state"], final_state)
            self.assertEqual(packet["event_history_digest"], timeline["event_history_digest"])
            self.assertEqual(packet["event_history_digest"], director["event_history_digest"])
            self.assertTrue(packet["migrated"])
            self.assertFalse(packet["canonical_knowledge_written"])
            self.assertFalse(packet["generation_called"])

            play = self.cli.run(["--workspace", str(workspace), "play"])
            replay = self.cli.run(["--workspace", str(workspace), "replay"])
            review = self.cli.run(["--workspace", str(workspace), "review-packet"])
            self.assertTrue(play["v2"])
            self.assertTrue(replay["v2"])
            self.assertEqual(review["packet"]["final_state"], final_state)

    def test_illegal_v2_action_fails_before_default_save_mutation(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            self._legacy(workspace, "listen")
            continuation.migrate(workspace)
            before = (workspace / "saves" / "default.json").read_bytes()
            with self.assertRaisesRegex(LedgerViolation, "not legal"):
                continuation.choose(workspace, "promise")
            self.assertEqual((workspace / "saves" / "default.json").read_bytes(), before)

    def test_hash_valid_state_patch_is_forbidden_by_every_consumer(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            self._legacy(workspace, "approach")
            continuation.migrate(workspace)
            envelope = read_envelope(workspace)
            ledger = CreativeLedger.from_records(envelope["events"])
            ledger.append(
                "state_patch",
                {"patch": {"beat_id": "accord", "risk_delta": -99}},
                "2030-01-03T00:00:00Z",
            )
            envelope["events"] = ledger.to_records()
            write_envelope(workspace, envelope)
            self._assert_all_consumers_reject(workspace)

    def test_hash_valid_extra_migration_bridge_is_forbidden(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            self._legacy(workspace, "approach")
            continuation.migrate(workspace)
            envelope = read_envelope(workspace)
            ledger = CreativeLedger.from_records(envelope["events"])
            ledger.append(
                "migration_bridge",
                {
                    "kind": "forged_post_prefix_bridge",
                    "source_digest": envelope["migration"]["source_digest"],
                    "state_neutral": True,
                },
                "2030-01-03T00:00:00Z",
            )
            envelope["events"] = ledger.to_records()
            write_envelope(workspace, envelope)
            self._assert_all_consumers_reject(workspace)

    def test_hash_valid_transition_patch_tamper_fails_graph_validation(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            self._legacy(workspace, "listen")
            continuation.migrate(workspace)
            continuation.choose(workspace, "record")
            envelope = read_envelope(workspace)
            records = envelope["events"]
            last = len(records) - 1

            def mutate(new_sequence, original_index, event_type, payload, occurred_at):
                if original_index == last:
                    payload["resulting_patch"] = {
                        "scene_id": "dawn_courtyard",
                        "beat_id": "return",
                        "flags": {"clue": "invented"},
                    }
                return event_type, payload, occurred_at

            envelope["events"] = rebuild_records(records, mutate)
            write_envelope(workspace, envelope)
            self._assert_all_consumers_reject(workspace)

    def test_source_a_source_b_receipt_and_ledger_swap_fails_every_consumer(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            workspace_a = base / "a"
            workspace_b = base / "b"
            source_a = self._legacy(workspace_a, "approach")
            self._legacy(workspace_b, "leave")
            continuation.migrate(workspace_a)
            continuation.migrate(workspace_b)
            envelope_b = read_envelope(workspace_b)
            write_envelope(workspace_a, envelope_b)
            self.assertEqual((workspace_a / "session.json").read_bytes(), source_a)
            self._assert_all_consumers_reject(workspace_a)

    def test_modified_legacy_source_rejects_all_consumers(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            self._legacy(workspace, "approach")
            continuation.migrate(workspace)
            source = workspace / "session.json"
            source.write_bytes(source.read_bytes() + b" ")
            self._assert_all_consumers_reject(workspace)

    def test_lossy_listen_approach_leave_migration_has_no_shadow_save(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            original = self._legacy(workspace, "listen", "approach", "leave")
            with self.assertRaisesRegex(LedgerViolation, "lossy"):
                continuation.migrate(workspace)
            self.assertFalse((workspace / "saves" / "default.json").exists())
            self.assertEqual((workspace / "session.json").read_bytes(), original)

    def test_terminal_migration_bridge_is_deterministic_and_misposition_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            self._legacy(workspace, "approach", "listen")
            migrated = continuation.migrate(workspace)
            bridges = [
                record for record in migrated["events"]
                if record["event_type"] == "migration_bridge"
            ]
            self.assertEqual(len(bridges), 1)
            expected = migrated["migration"]["migration_bridge_positions"]
            self.assertEqual(
                expected,
                [{"sequence": bridges[0]["sequence"], "event_id": bridges[0]["event_id"]}],
            )

            envelope = read_envelope(workspace)
            records = envelope["events"]
            bridge_index = next(
                index for index, record in enumerate(records)
                if record["event_type"] == "migration_bridge"
            )
            self.assertEqual(bridge_index, len(records) - 1)
            order = list(range(len(records)))
            order.remove(bridge_index)
            order.insert(max(1, bridge_index - 1), bridge_index)
            envelope["events"] = rebuild_records(records, order=order)
            write_envelope(workspace, envelope)
            self._assert_all_consumers_reject(workspace)

    def test_native_v2_is_not_labeled_migrated_and_needs_no_legacy_source(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            session = continuation.initialize_native(workspace)
            self.assertFalse(session.migrated)
            self.assertFalse((workspace / "session.json").exists())
            self.assertEqual(read_envelope(workspace)["schema"], "CreativeSession/v2")
            self.assertIsNone(read_envelope(workspace)["migration"])
            self.assertFalse(continuation.review_packet(workspace)["migrated"])

    def test_legacy_parallel_continuation_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            path = workspace / "saves" / "default.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                canonical_json(
                    {
                        "schema": "CreativeSession/" + "v2-" + "continuation",
                        "receipt": {},
                        "actions": [],
                    }
                ) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(LedgerViolation, "schema"):
                continuation.load_session(workspace)


if __name__ == "__main__":
    unittest.main()
