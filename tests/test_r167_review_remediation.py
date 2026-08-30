from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from creative_runtime.continuity import compile_director_sequence
from creative_runtime.contracts import PlayerAction, StoryState, canonical_json
from creative_runtime.ledger import CreativeLedger
from creative_runtime.review import build_review_packet
from creative_runtime.review_ticket import ReviewTicketViolation, validate_review_request
from creative_runtime.saves import SaveStore, SaveViolation, SavedSession, V1_SCHEMA, V2_SCHEMA
from creative_runtime.timeline import TimelineViolation, timeline


def legacy_ledger(actions: list[str]) -> CreativeLedger:
    patches = {
        ("arrival", "listen"): {"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1},
        ("arrival", "approach"): {"beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}},
        ("arrival", "leave"): {"beat_id": "courtyard", "risk_delta": -1, "flags": {"arrival": "deferred"}},
        ("echo", "approach"): {"beat_id": "threshold", "relationship_delta": {"mira": 1}},
        ("echo", "leave"): {"beat_id": "courtyard", "flags": {"clue": "recorded"}},
        ("threshold", "listen"): {"beat_id": "resolution", "relationship_delta": {"mira": 1}, "risk_delta": -1},
        ("threshold", "leave"): {"beat_id": "courtyard", "flags": {"meeting": "offered"}},
    }
    ledger = CreativeLedger()
    state = StoryState("synthetic_archive", "arrival", relationships={"mira": 0})
    ledger.append("story_initialized", {"state": state.to_dict()}, "2030-01-01T00:00:00Z")
    for index, action_id in enumerate(actions, start=1):
        patch = patches[(state.beat_id, action_id)]
        ledger.append("player_action", {"action": PlayerAction(action_id, "choice", action_id).to_dict(), "resulting_patch": patch}, f"2030-01-01T00:{index:02d}:00Z")
        from creative_runtime.ledger import apply_state_patch
        state = apply_state_patch(state, patch)
    return ledger


def write_legacy(workspace: Path, actions: list[str]) -> tuple[Path, bytes]:
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / "session.json"
    raw = (canonical_json({"schema": V1_SCHEMA, "events": legacy_ledger(actions).to_records()}) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return path, raw


class R167MigrationTests(unittest.TestCase):
    def test_lossy_listen_approach_leave_rejected_without_source_or_shadow_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source, original = write_legacy(workspace, ["listen", "approach", "leave"])
            with self.assertRaisesRegex(SaveViolation, "LOSSY_UNREPRESENTABLE"):
                SaveStore(workspace).load()
            self.assertEqual(source.read_bytes(), original)
            self.assertFalse((workspace / "saves" / "default.json").exists())

    def test_lossless_approach_listen_terminal_bridge_is_source_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            _, original = write_legacy(workspace, ["approach", "listen"])
            store = SaveStore(workspace)
            session = store.load()
            self.assertIsNotNone(session.migration_receipt)
            self.assertEqual(session.state().relationships["mira"], 2)
            self.assertEqual(session.state().risk_level, -1)
            self.assertEqual(session.ledger.events[-1].event_type, "migration_bridge")
            self.assertEqual((workspace / "session.json").read_bytes(), original)
            copied = session.to_dict()
            copied["events"] = copied["events"][:-1]
            with self.assertRaises(SaveViolation):
                SavedSession.from_dict(copied)

    def test_migration_receipt_durability_and_native_v2_nonlabeling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_legacy(workspace, ["approach"])
            store = SaveStore(workspace)
            migrated = store.load()
            migrated = store.append_choice(migrated, "promise", "promise", "2030-01-01T00:03:00Z")
            store.save(migrated)
            store.save(migrated, "sibling")
            restored = store.load("sibling")
            self.assertEqual(restored.migration_receipt, migrated.migration_receipt)
            self.assertEqual(restored.migration_history, migrated.migration_history)
            native = store.create_initial()
            store.save(native, "native")
            reloaded_native = store.load("native")
            self.assertIsNone(reloaded_native.migration_receipt)
            self.assertEqual(reloaded_native.migration_history, ())

    def test_hash_valid_state_patch_is_rejected_before_all_consumers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            store = SaveStore(workspace)
            session = store.create_initial()
            session.ledger.append("state_patch", {"patch": {"risk_delta": 99}}, "2030-01-01T00:01:00Z")
            raw = canonical_json({"schema": V2_SCHEMA, "events": session.ledger.to_records(), "migration_receipt": None, "migration_history": []}) + "\n"
            target = store.path_for()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(raw, encoding="utf-8")
            with self.assertRaises(SaveViolation):
                store.load()
            forged = SavedSession(session.ledger)
            for consumer in (timeline, compile_director_sequence, build_review_packet):
                with self.assertRaises((SaveViolation, TimelineViolation)):
                    consumer(forged)

    def test_wrong_transition_patch_and_unsafe_slot_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SaveStore(Path(directory))
            session = store.create_initial()
            session.ledger.append("player_action", {"action": PlayerAction("listen", "choice", "listen").to_dict(), "transition_id": "forged", "resulting_patch": {"beat_id": "echo"}}, "2030-01-01T00:01:00Z")
            with self.assertRaises(SaveViolation):
                session.validate()
            with self.assertRaises(SaveViolation):
                store.path_for("../escape")


class R167ReviewTicketTests(unittest.TestCase):
    def test_canonical_ticket_requires_exact_fields_and_real_handoff(self) -> None:
        good = {
            "effective_spec_snapshot_id": "SECOND-BRAIN-R167-ISSUE503-SNAPSHOT-001",
            "effective_spec_snapshot_ref": "issuecomment-5465651279",
            "canonical_base": "e201d4b54d54bec63d448b27aae33adeb1cc70df",
            "exact_head": "a" * 40,
            "engineering_handoff_ref": "issuecomment-12345",
        }
        validate_review_request(good)
        for broken in (
            {key: value for key, value in good.items() if key != "exact_head"},
            {**good, "prewrite_snapshot_id": "alias"},
            {**good, "engineering_handoff_ref": "issuecomment-PENDING_LOOKUP"},
        ):
            with self.assertRaises(ReviewTicketViolation):
                validate_review_request(broken)


if __name__ == "__main__":
    unittest.main()
