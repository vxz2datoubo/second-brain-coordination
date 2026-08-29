from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from creative_runtime.contracts import PlayerAction, StoryState, canonical_json
from creative_runtime.ledger import CreativeLedger
from creative_runtime.saves import CANONICAL_LEGACY_BASELINE, SaveSlotViolation, SaveStore, migrate_session
from creative_runtime.scene_graph import SceneGraph, synthetic_three_scene_manifest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "r163"
SPEC = importlib.util.spec_from_file_location("creativectl_r163_a", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def fixture_record(name: str) -> dict:
    return json.loads(fixture_bytes(name).decode("utf-8"))


def semantic_state(state: StoryState) -> dict:
    value = state.to_dict()
    return {
        "relationships": value["relationships"],
        "known_facts": value["known_facts"],
        "risk_level": value["risk_level"],
        "flags": value["flags"],
    }


class R163CanonicalLegacyFixtureTests(unittest.TestCase):
    def test_multi_action_fixture_is_a_real_baseline_v1_chain(self) -> None:
        raw = fixture_bytes("legacy_session_v1_multi_action.json")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "dc7289a727ffe02897ea0c1bd6d9b8de84905b5e8b249635c653924092e378a1")
        record = json.loads(raw)
        self.assertEqual(record["schema"], "CreativeSession/v1")
        ledger = CreativeLedger.from_records(record["events"])
        initial = StoryState.from_dict(ledger.events[0].payload["state"])
        self.assertEqual((initial.scene_id, initial.beat_id), ("synthetic_archive", "arrival"))
        self.assertEqual(
            [event.payload["action"]["action_id"] for event in ledger.events[1:]],
            ["listen", "approach", "leave"],
        )
        final = ledger.replay()
        self.assertEqual((final.scene_id, final.beat_id), ("synthetic_archive", "courtyard"))
        self.assertEqual(semantic_state(final), {
            "relationships": {"mira": 1},
            "known_facts": ["a witness is inside"],
            "risk_level": 1,
            "flags": {"meeting": "offered"},
        })

    def test_resolution_fixture_is_a_real_baseline_v1_terminal_chain(self) -> None:
        raw = fixture_bytes("legacy_session_v1_resolution.json")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "485329c61b9641b949010a1af35b929abe8236ba813a3c362af62ecd0b5df17f")
        record = json.loads(raw)
        ledger = CreativeLedger.from_records(record["events"])
        self.assertEqual([event.payload["action"]["action_id"] for event in ledger.events[1:]], ["approach", "listen"])
        final = ledger.replay()
        self.assertEqual((final.scene_id, final.beat_id), ("synthetic_archive", "resolution"))
        self.assertEqual(semantic_state(final), {
            "relationships": {"mira": 2},
            "known_facts": [],
            "risk_level": -1,
            "flags": {"arrival": "announced"},
        })


class R163MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = SceneGraph(synthetic_three_scene_manifest())

    def test_multi_action_migration_rebuilds_chain_and_preserves_declared_semantics(self) -> None:
        legacy = fixture_record("legacy_session_v1_multi_action.json")
        legacy_ledger = CreativeLedger.from_records(legacy["events"])
        migrated, migrations = migrate_session(legacy, self.graph.manifest_hash, self.graph)
        migrated_ledger = CreativeLedger.from_records(migrated["events"])

        self.assertEqual(migrations, ("CreativeSession/v1->v2:r163-canonical-semantic-mapping",))
        self.assertEqual(migrated["schema"], "CreativeSession/v2")
        self.assertEqual(migrated["manifest_hash"], self.graph.manifest_hash)
        self.assertEqual([event.payload["action"]["action_id"] for event in migrated_ledger.events[1:]], ["listen", "knock", "retreat"])
        self.assertNotEqual(migrated_ledger.events[1].event_id, legacy_ledger.events[1].event_id)
        final = migrated_ledger.replay()
        self.assertEqual((final.scene_id, final.beat_id), ("dawn_courtyard", "return"))
        self.assertEqual(semantic_state(final), semantic_state(legacy_ledger.replay()))

        receipt = migrated["migration_receipt"]
        self.assertEqual(receipt["source_baseline"], CANONICAL_LEGACY_BASELINE)
        self.assertEqual(receipt["source_record_sha256"], "823af2e1eeaecae2c37a75679865ca9f525c0a1a4217414bac7eadec51ffa10c")
        self.assertEqual(
            [(item["legacy_beat_id"], item["legacy_action_id"], item["new_action_id"]) for item in receipt["event_mappings"]],
            [("arrival", "listen", "listen"), ("echo", "approach", "knock"), ("threshold", "leave", "retreat")],
        )
        self.assertIsNone(receipt["terminal_mapping"])

    def test_resolution_terminal_has_explicit_mapping_and_preserves_semantics(self) -> None:
        legacy = fixture_record("legacy_session_v1_resolution.json")
        legacy_final = CreativeLedger.from_records(legacy["events"]).replay()
        migrated, _ = migrate_session(legacy, self.graph.manifest_hash, self.graph)
        ledger = CreativeLedger.from_records(migrated["events"])
        self.assertEqual([event.payload["action"]["action_id"] for event in ledger.events[1:3]], ["knock", "promise"])
        self.assertEqual(ledger.events[-1].event_type, "state_patch")
        final = ledger.replay()
        self.assertEqual((final.scene_id, final.beat_id), ("dawn_courtyard", "return"))
        self.assertEqual(semantic_state(final), semantic_state(legacy_final))
        self.assertEqual(migrated["migration_receipt"]["terminal_mapping"]["method"], "explicit_terminal_state_patch_after_promise")
        self.assertEqual(migrated["migration_receipt"]["source_record_sha256"], "fc9344bbab521ad5ac5ff3177c1bbcbf15582643ede118b871af974dab0feeee")

    def test_legacy_startup_migrates_before_default_creation_preserves_source_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = fixture_bytes("legacy_session_v1_multi_action.json")
            (workspace / "session.json").write_bytes(source)
            output = io.StringIO()
            result = creativectl.terminal_loop(workspace, io.StringIO("quit\n"), output)
            self.assertEqual(result["status"], "quit")
            self.assertEqual((workspace / "session.json").read_bytes(), source)
            default = workspace / "saves" / "default.json"
            self.assertTrue(default.is_file())
            first_default = default.read_bytes()
            migrated = json.loads(first_default)
            self.assertEqual(migrated["migration_history"], ["CreativeSession/v1->v2:r163-canonical-semantic-mapping"])

            second = creativectl.terminal_loop(workspace, io.StringIO("quit\n"), io.StringIO())
            self.assertEqual(second["status"], "quit")
            self.assertEqual(default.read_bytes(), first_default)
            self.assertEqual((workspace / "session.json").read_bytes(), source)

    def test_corrupt_legacy_is_user_visible_fail_closed_and_never_shadowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = b"{not-json\n"
            (workspace / "session.json").write_bytes(source)
            output = io.StringIO()
            result = creativectl.terminal_loop(workspace, io.StringIO("quit\n"), output)
            self.assertEqual(result["status"], "legacy_incompatible")
            self.assertTrue(result["legacy_session_preserved"])
            self.assertFalse(result["default_session_created"])
            self.assertIn("original preserved", output.getvalue())
            self.assertEqual((workspace / "session.json").read_bytes(), source)
            self.assertFalse((workspace / "saves" / "default.json").exists())

    def test_valid_but_noncanonical_legacy_action_fails_closed_without_source_change(self) -> None:
        legacy = CreativeLedger()
        legacy.append(
            "story_initialized",
            {"state": StoryState(scene_id="synthetic_archive", beat_id="arrival", relationships={"mira": 0}).to_dict()},
            "2030-01-01T00:00:00Z",
        )
        legacy.append(
            "player_action",
            {
                "action": PlayerAction("invent", "choice", "Invent a route").to_dict(),
                "resulting_patch": {"beat_id": "echo"},
            },
            "2030-01-01T00:01:00Z",
        )
        source = (canonical_json({"schema": "CreativeSession/v1", "events": legacy.to_records()}) + "\n").encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "session.json").write_bytes(source)
            result = creativectl.terminal_loop(workspace, io.StringIO("quit\n"), io.StringIO())
            self.assertEqual(result["status"], "legacy_incompatible")
            self.assertEqual((workspace / "session.json").read_bytes(), source)
            self.assertFalse((workspace / "saves" / "default.json").exists())

    def test_canonical_action_with_tampered_patch_is_not_laundered(self) -> None:
        legacy = fixture_record("legacy_session_v1_multi_action.json")
        legacy["events"][1]["payload"]["resulting_patch"]["risk_delta"] = 99
        with self.assertRaises(SaveSlotViolation):
            migrate_session(legacy, self.graph.manifest_hash, self.graph)

    def test_slot_paths_remain_confined(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SaveStore(Path(directory))
            for invalid in ("../escape", "con", "C:drive", "slot.name", "", "../../session"):
                with self.subTest(invalid=invalid):
                    with self.assertRaises(SaveSlotViolation):
                        store.load(invalid, self.graph.manifest_hash, self.graph)


if __name__ == "__main__":
    unittest.main()
