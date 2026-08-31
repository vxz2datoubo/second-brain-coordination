from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from creative_runtime.continuity import compile_director_sequence
from creative_runtime.contracts import PlayerAction, StoryState, canonical_json
from creative_runtime.ledger import CreativeLedger
from creative_runtime.review import build_review_packet
from creative_runtime.saves import LEGACY_SCHEMA, SaveStore, SaveViolation, SavedSession
from creative_runtime.timeline import TimelineViolation, build_prefix_timeline


def _legacy_ledger(actions: list[str]) -> CreativeLedger:
    """Produce genuine baseline-v1 vocabulary and patch semantics."""

    ledger = CreativeLedger()
    ledger.append(
        "story_initialized",
        {"state": StoryState("synthetic_archive", "arrival", {"mira": 0}).to_dict()},
        "2030-01-01T00:00:00Z",
    )
    state = ledger.replay()
    for index, action_id in enumerate(actions, start=1):
        if state.beat_id == "arrival" and action_id == "listen":
            patch = {"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1}
        elif state.beat_id == "arrival" and action_id == "approach":
            patch = {"beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}}
        elif state.beat_id == "echo" and action_id == "approach":
            patch = {"beat_id": "threshold", "relationship_delta": {"mira": 1}}
        elif state.beat_id == "threshold" and action_id == "listen":
            patch = {"beat_id": "resolution", "relationship_delta": {"mira": 1}, "risk_delta": -1}
        elif state.beat_id == "arrival" and action_id == "leave":
            patch = {"beat_id": "courtyard", "risk_delta": -1, "flags": {"arrival": "deferred"}}
        elif state.beat_id == "echo" and action_id == "leave":
            patch = {"beat_id": "courtyard", "flags": {"clue": "recorded"}}
        elif state.beat_id == "threshold" and action_id == "leave":
            patch = {"beat_id": "courtyard", "flags": {"meeting": "offered"}}
        else:
            raise AssertionError("test route is not canonical legacy vocabulary")
        ledger.append(
            "player_action",
            {"action": PlayerAction(action_id, "choice", action_id).to_dict(), "resulting_patch": patch},
            f"2030-01-01T00:{index:02d}:00Z",
        )
        state = ledger.replay()
    return ledger


def _write_legacy(workspace: Path, actions: list[str]) -> bytes:
    legacy = _legacy_ledger(actions)
    source = canonical_json({"schema": LEGACY_SCHEMA, "events": legacy.to_records()}).encode("utf-8") + b"\n"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "session.json").write_bytes(source)
    return source


class R165CleanSuccessorTests(unittest.TestCase):
    def test_hash_valid_caller_state_patch_is_rejected_before_all_consumers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SaveStore(Path(directory))
            session, _ = store.initialize()
            session.ledger.append(
                "state_patch", {"patch": {"scene_id": "dawn_courtyard", "beat_id": "return"}}, "2030-01-01T00:01:00Z"
            )
            path = store.path_for()
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["events"] = session.ledger.to_records()  # hashes remain fully valid
            path.write_text(canonical_json(raw) + "\n", encoding="utf-8")
            with self.assertRaises(SaveViolation):
                store.load()
            with self.assertRaises(SaveViolation):
                compile_director_sequence(store.load())
            with self.assertRaises(SaveViolation):
                build_review_packet(store.load())

    def test_normal_prefix_timeline_is_truthful_and_director_review_share_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SaveStore(Path(directory))
            session, _ = store.initialize()
            from apps.cli import creativectl
            # Importing the module through its package path keeps this test focused
            # on state authority rather than command-line argument parsing.
            workspace = Path(directory)
            creativectl.choose(workspace, "listen")
            creativectl.choose(workspace, "knock")
            creativectl.choose(workspace, "promise")
            session = store.load()
            timeline = build_prefix_timeline(session)
            self.assertEqual([entry.state["beat_id"] for entry in timeline], ["arrival", "echo", "threshold", "accord"])
            self.assertEqual([entry.state["risk_level"] for entry in timeline], [0, 1, 1, 0])
            self.assertEqual(timeline[2].state["flags"], {"clue": "heard"})
            self.assertTrue(compile_director_sequence(session).compilation.quality_report.can_generate)
            self.assertEqual(build_review_packet(session)["state"], timeline[-1].state)

    def test_real_v1_source_migrates_losslessly_and_source_bytes_never_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original = _write_legacy(workspace, ["listen", "approach", "leave"])
            session, status = SaveStore(workspace).initialize()
            self.assertEqual(status, "migrated")
            self.assertEqual((session.state().scene_id, session.state().beat_id), ("dawn_courtyard", "return"))
            self.assertEqual(workspace.joinpath("session.json").read_bytes(), original)
            payload = json.loads(SaveStore(workspace).path_for().read_text(encoding="utf-8"))
            self.assertIn("migration_receipt", payload)
            self.assertTrue(payload["migration_history"])
            self.assertEqual(SaveStore(workspace).initialize()[1], "already_initialized")
            self.assertEqual(workspace.joinpath("session.json").read_bytes(), original)

    def test_terminal_bridge_is_source_bound_and_cannot_be_reused_after_native_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original = _write_legacy(workspace, ["approach", "listen"])
            store = SaveStore(workspace)
            migrated, status = store.initialize()
            self.assertEqual(status, "migrated")
            self.assertEqual(migrated.state().beat_id, "accord")
            self.assertEqual(workspace.joinpath("session.json").read_bytes(), original)
            raw = json.loads(store.path_for().read_text(encoding="utf-8"))
            # A copied receipt cannot legitimise a bridge after an arbitrary v2
            # prefix: exact deterministic prefix comparison rejects it.
            native_store = SaveStore(workspace / "native")
            native, _ = native_store.initialize()
            forged = json.loads(native_store.path_for().read_text(encoding="utf-8"))
            forged["migration_receipt"] = raw["migration_receipt"]
            forged["migration_history"] = raw["migration_history"]
            forged["events"].append(raw["events"][-1])
            native_store.path_for().write_text(canonical_json(forged) + "\n", encoding="utf-8")
            with self.assertRaises(SaveViolation):
                native_store.load()

    def test_receipt_history_survive_choose_say_repeated_save_and_slots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            _write_legacy(workspace, ["listen"])
            store = SaveStore(workspace)
            migrated, _ = store.initialize()
            from apps.cli import creativectl
            creativectl.choose(workspace, "knock")
            after_choose = store.load()
            self.assertIsNotNone(after_choose.migration_receipt)
            self.assertTrue(after_choose.migration_history)
            store.save(after_choose)
            store.save(after_choose, "sibling")
            restored = store.load("sibling")
            store.save(restored, "default")
            self.assertEqual(store.load().migration_receipt, migrated.migration_receipt)
            # A separate migrated echo save exercises free-text continued play.
            say_workspace = workspace / "say"
            _write_legacy(say_workspace, ["listen"])
            say_store = SaveStore(say_workspace)
            say_store.initialize()
            self.assertEqual(creativectl.say(say_workspace, "I knock at the door")["status"], "chosen")
            self.assertIsNotNone(say_store.load().migration_receipt)

    def test_native_v2_never_acquires_migration_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SaveStore(Path(directory))
            native, _ = store.initialize()
            self.assertIsNone(native.migration_receipt)
            raw = json.loads(store.path_for().read_text(encoding="utf-8"))
            self.assertNotIn("migration_receipt", raw)
            self.assertEqual(raw["migration_history"], [])

    def test_tampered_legacy_and_unsafe_slot_fail_closed_without_default_shadow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = _write_legacy(workspace, ["listen"])
            record = json.loads(source.decode("utf-8"))
            record["events"][1]["payload"]["resulting_patch"]["risk_delta"] = 99
            workspace.joinpath("session.json").write_text(canonical_json(record) + "\n", encoding="utf-8")
            with self.assertRaises(SaveViolation):
                SaveStore(workspace).initialize()
            self.assertFalse(SaveStore(workspace).path_for().exists())
            self.assertFalse((workspace / "saves" / "default.json").exists())
            with self.assertRaises(SaveViolation):
                SaveStore(workspace).path_for("../escape")


if __name__ == "__main__":
    unittest.main()
