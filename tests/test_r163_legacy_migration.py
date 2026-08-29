from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from creative_runtime.contracts import PlayerAction, StoryState, canonical_json
from creative_runtime.ledger import CreativeLedger, LedgerViolation
from creative_runtime.saves import (
    CANONICAL_LEGACY_BASELINE,
    MIGRATION_HISTORY_MARKER,
    MIGRATION_PATCH_PROVENANCE_SCHEMA,
    MIGRATION_PLAYER_PROVENANCE_SCHEMA,
    SaveSlotViolation,
    SaveStore,
    migrate_session,
)
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


def write_v2_record(path: Path, graph: SceneGraph, ledger: CreativeLedger, **extra: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "CreativeSession/v2",
        "manifest_hash": graph.manifest_hash,
        "events": ledger.to_records(),
        "migration_history": [],
        **extra,
    }
    path.write_text(canonical_json(record) + "\n", encoding="utf-8")


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

    def test_lossy_multi_action_mapping_fails_closed_instead_of_rewriting_v2_semantics(self) -> None:
        """Legacy echo/approach lacks v2 echo_knock's clue=heard consequence.

        R163 must preserve current v2 behavior and reject this old path rather than
        weakening the v2 graph just to force a migration success.
        """
        legacy = fixture_record("legacy_session_v1_multi_action.json")
        legacy_ledger = CreativeLedger.from_records(legacy["events"])
        with self.assertRaisesRegex(SaveSlotViolation, "cannot be preserved losslessly"):
            migrate_session(legacy, self.graph.manifest_hash, self.graph)
        self.assertEqual(
            semantic_state(legacy_ledger.replay()),
            {
                "relationships": {"mira": 1},
                "known_facts": ["a witness is inside"],
                "risk_level": 1,
                "flags": {"meeting": "offered"},
            },
        )

    def test_current_v2_echo_knock_semantics_are_not_weakened_for_migration(self) -> None:
        state = self.graph.initial_state()
        state, _ = self.graph.apply(state, "listen")
        state, action = self.graph.apply(state, "knock")
        self.assertEqual(action.transition_id, "echo_knock")
        self.assertEqual(state.flags, {"clue": "heard"})

    def test_resolution_terminal_has_explicit_lossless_mapping_and_preserves_semantics(self) -> None:
        legacy = fixture_record("legacy_session_v1_resolution.json")
        legacy_final = CreativeLedger.from_records(legacy["events"]).replay()
        migrated, migrations = migrate_session(legacy, self.graph.manifest_hash, self.graph)
        ledger = CreativeLedger.from_records(migrated["events"])

        self.assertEqual(migrations, (MIGRATION_HISTORY_MARKER,))
        self.assertEqual(migrated["schema"], "CreativeSession/v2")
        self.assertEqual(migrated["manifest_hash"], self.graph.manifest_hash)
        self.assertEqual([event.payload["action"]["action_id"] for event in ledger.events[1:3]], ["knock", "promise"])
        self.assertEqual(ledger.events[-1].event_type, "state_patch")
        final = ledger.replay()
        self.assertEqual((final.scene_id, final.beat_id), ("dawn_courtyard", "return"))
        self.assertEqual(semantic_state(final), semantic_state(legacy_final))

        receipt = migrated["migration_receipt"]
        self.assertEqual(receipt["source_baseline"], CANONICAL_LEGACY_BASELINE)
        self.assertEqual(receipt["source_record_sha256"], "fc9344bbab521ad5ac5ff3177c1bbcbf15582643ede118b871af974dab0feeee")
        self.assertEqual(
            [(item["legacy_beat_id"], item["legacy_action_id"], item["new_action_id"]) for item in receipt["event_mappings"]],
            [("arrival", "approach", "knock"), ("threshold", "listen", "promise")],
        )
        self.assertEqual(receipt["terminal_mapping"]["method"], "explicit_terminal_state_patch_after_promise")

        for mapped_event in ledger.events[1:3]:
            source = mapped_event.payload["migration_source"]
            self.assertEqual(source["schema"], MIGRATION_PLAYER_PROVENANCE_SCHEMA)
            self.assertEqual(source["authority_class"], "VALIDATED_LEGACY_MIGRATION_ONLY")
            self.assertEqual(source["source_record_sha256"], receipt["source_record_sha256"])
            self.assertEqual(source["source_record"], legacy)
        patch_provenance = ledger.events[-1].payload["migration_provenance"]
        self.assertEqual(patch_provenance["schema"], MIGRATION_PATCH_PROVENANCE_SCHEMA)
        self.assertEqual(patch_provenance["authority_class"], "VALIDATED_LEGACY_MIGRATION_ONLY")
        self.assertEqual(patch_provenance["source_record_sha256"], receipt["source_record_sha256"])
        self.assertEqual(patch_provenance["source_record"], legacy)

    def test_legacy_startup_migrates_lossless_fixture_before_default_creation_preserves_source_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = fixture_bytes("legacy_session_v1_resolution.json")
            (workspace / "session.json").write_bytes(source)
            output = io.StringIO()
            result = creativectl.terminal_loop(workspace, io.StringIO("quit\n"), output)
            self.assertEqual(result["status"], "quit")
            self.assertEqual((workspace / "session.json").read_bytes(), source)
            default = workspace / "saves" / "default.json"
            self.assertTrue(default.is_file())
            first_default = default.read_bytes()
            migrated = json.loads(first_default)
            self.assertEqual(migrated["migration_history"], [MIGRATION_HISTORY_MARKER])
            self.assertEqual(
                semantic_state(CreativeLedger.from_records(migrated["events"]).replay()),
                semantic_state(CreativeLedger.from_records(fixture_record("legacy_session_v1_resolution.json")["events"]).replay()),
            )

            second = creativectl.terminal_loop(workspace, io.StringIO("quit\n"), io.StringIO())
            self.assertEqual(second["status"], "quit")
            self.assertEqual(default.read_bytes(), first_default)
            self.assertEqual((workspace / "session.json").read_bytes(), source)

    def test_semantically_unrepresentable_real_legacy_is_user_visible_and_never_shadowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = fixture_bytes("legacy_session_v1_multi_action.json")
            (workspace / "session.json").write_bytes(source)
            output = io.StringIO()
            result = creativectl.terminal_loop(workspace, io.StringIO("quit\n"), output)
            self.assertEqual(result["status"], "legacy_incompatible")
            self.assertTrue(result["legacy_session_preserved"])
            self.assertFalse(result["default_session_created"])
            self.assertIn("original preserved", output.getvalue())
            self.assertEqual((workspace / "session.json").read_bytes(), source)
            self.assertFalse((workspace / "saves" / "default.json").exists())

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

    def test_hash_valid_caller_state_patch_direct_jump_cannot_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = SaveStore(root)
            ledger = CreativeLedger()
            ledger.append("story_initialized", {"state": self.graph.initial_state().to_dict()}, "2030-01-01T00:00:00Z")
            ledger.append(
                "state_patch",
                {"patch": {"scene_id": "dawn_courtyard", "beat_id": "return"}},
                "2030-01-01T00:01:00Z",
            )
            ledger.verify_chain()
            write_v2_record(root / "evil.json", self.graph, ledger)
            with self.assertRaises(SaveSlotViolation):
                store.load("evil", self.graph.manifest_hash, self.graph)

    def test_hash_valid_forged_typed_state_patch_provenance_cannot_load(self) -> None:
        valid, _ = migrate_session(fixture_record("legacy_session_v1_resolution.json"), self.graph.manifest_hash, self.graph)
        valid_ledger = CreativeLedger.from_records(valid["events"])
        forged = CreativeLedger()
        for event in valid_ledger.events:
            payload = json.loads(canonical_json(event.payload))
            if event.event_type == "state_patch":
                payload["migration_provenance"]["source_record_sha256"] = "0" * 64
            forged.append(event.event_type, payload, event.occurred_at, event.parent_artifact_ids)
        forged.verify_chain()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_v2_record(
                root / "forged.json",
                self.graph,
                forged,
                migration_history=valid["migration_history"],
                migration_receipt=valid["migration_receipt"],
            )
            with self.assertRaises(SaveSlotViolation):
                SaveStore(root).load("forged", self.graph.manifest_hash, self.graph)

    def test_caller_state_patch_in_sibling_slot_cannot_restore_over_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.initialize(workspace)
            ledger = CreativeLedger()
            ledger.append("story_initialized", {"state": self.graph.initial_state().to_dict()}, "2030-01-01T00:00:00Z")
            ledger.append(
                "state_patch",
                {"patch": {"scene_id": "dawn_courtyard", "beat_id": "return"}},
                "2030-01-01T00:01:00Z",
            )
            write_v2_record(workspace / "saves" / "evil.json", self.graph, ledger)
            default_before = (workspace / "saves" / "default.json").read_bytes()
            with self.assertRaises(LedgerViolation):
                creativectl._restore_slot(workspace, "evil")
            self.assertEqual((workspace / "saves" / "default.json").read_bytes(), default_before)

    def test_resume_migration_provenance_survives_choose_and_sibling_save(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = fixture_bytes("legacy_session_v1_resume.json")
            (workspace / "session.json").write_bytes(source)
            initial = creativectl.initialize(workspace)
            self.assertEqual(initial["status"], "migrated_legacy")
            default_path = workspace / "saves" / "default.json"
            before = json.loads(default_path.read_text(encoding="utf-8"))
            self.assertEqual(before["migration_history"], [MIGRATION_HISTORY_MARKER])
            self.assertIn("migration_receipt", before)

            chosen = creativectl.choose(workspace, "promise")
            self.assertEqual(chosen["status"], "chosen")
            after = json.loads(default_path.read_text(encoding="utf-8"))
            self.assertEqual(after["migration_history"], [MIGRATION_HISTORY_MARKER])
            self.assertEqual(after["migration_receipt"], before["migration_receipt"])
            self.assertEqual((workspace / "session.json").read_bytes(), source)
            SaveStore(workspace / "saves").load("default", self.graph.manifest_hash, self.graph)

            saved = creativectl.run(["--workspace", str(workspace), "slot", "save", "branch"])
            self.assertEqual(saved["status"], "saved")
            sibling = json.loads((workspace / "saves" / "branch.json").read_text(encoding="utf-8"))
            self.assertEqual(sibling["migration_history"], [MIGRATION_HISTORY_MARKER])
            self.assertEqual(sibling["migration_receipt"], before["migration_receipt"])
            restored = creativectl.run(["--workspace", str(workspace), "slot", "load", "branch"])
            self.assertEqual(restored["status"], "loaded")
            default_after_restore = json.loads(default_path.read_text(encoding="utf-8"))
            self.assertEqual(default_after_restore["migration_history"], [MIGRATION_HISTORY_MARKER])
            self.assertEqual(default_after_restore["migration_receipt"], before["migration_receipt"])


if __name__ == "__main__":
    unittest.main()
