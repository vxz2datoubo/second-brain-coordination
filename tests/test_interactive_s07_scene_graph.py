from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import tempfile
import unittest

from creative_runtime.ledger import CreativeLedger
from creative_runtime.saves import SaveSlotViolation, SaveStore
from creative_runtime.scene_graph import SceneGraph, SceneGraphViolation, synthetic_three_scene_manifest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_s07", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


def initialized_ledger(graph: SceneGraph) -> CreativeLedger:
    ledger = CreativeLedger()
    ledger.append(
        "story_initialized",
        {"state": graph.initial_state().to_dict()},
        "2026-08-29T00:00:00Z",
    )
    return ledger


class SceneGraphTests(unittest.TestCase):
    def test_three_scene_manifest_has_deterministic_reconvergent_paths(self) -> None:
        graph = SceneGraph(synthetic_three_scene_manifest())
        self.assertEqual(graph.initial_state().scene_id, "archive_gate")
        self.assertEqual(graph.initial_state().beat_id, "arrival")

        echo, _ = graph.apply(graph.initial_state(), "listen")
        via_echo, _ = graph.apply(echo, "knock")
        direct, _ = graph.apply(graph.initial_state(), "knock")
        self.assertEqual((via_echo.scene_id, via_echo.beat_id), ("interior_archive", "threshold"))
        self.assertEqual((direct.scene_id, direct.beat_id), ("interior_archive", "threshold"))

        accord, _ = graph.apply(direct, "promise")
        finale, _ = graph.apply(accord, "depart")
        self.assertEqual((finale.scene_id, finale.beat_id), ("dawn_courtyard", "return"))
        self.assertEqual(graph.manifest_hash, SceneGraph(synthetic_three_scene_manifest()).manifest_hash)

    def test_invalid_or_dangling_manifest_fails_closed(self) -> None:
        invalid = synthetic_three_scene_manifest()
        invalid["scenes"][0]["beats"][0]["actions"][0]["transition"]["target"] = {
            "scene_id": "missing_scene",
            "beat_id": "missing_beat",
        }
        with self.assertRaises(SceneGraphViolation):
            SceneGraph(invalid)

        invalid = synthetic_three_scene_manifest()
        duplicate = dict(invalid["scenes"][0]["beats"][0]["actions"][0])
        invalid["scenes"][0]["beats"][0]["actions"].append(duplicate)
        with self.assertRaises(SceneGraphViolation):
            SceneGraph(invalid)


class SaveSlotTests(unittest.TestCase):
    def test_cli_exposes_slots_transcript_and_branch_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init"])
            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            saved = creativectl.run(["--workspace", str(workspace), "slot", "save", "heard"])
            self.assertEqual(saved["status"], "saved")
            creativectl.run(["--workspace", str(workspace), "choose", "knock"])
            creativectl.run(["--workspace", str(workspace), "slot", "save", "inside"])
            transcript = creativectl.run(["--workspace", str(workspace), "transcript"])
            self.assertEqual(transcript["status"], "transcript")
            self.assertEqual(transcript["turns"][-1]["scene_id"], "interior_archive")
            comparison = creativectl.run(["--workspace", str(workspace), "compare", "heard", "inside"])
            self.assertEqual(comparison["status"], "compared")
            self.assertFalse(comparison["same_event_digest"])
            self.assertEqual(creativectl.run(["--workspace", str(workspace), "slot", "list"])["slots"], ["default", "heard", "inside"])
            self.assertEqual(creativectl.run(["--workspace", str(workspace), "slot", "delete", "heard"])["status"], "deleted")

    def test_slot_round_trip_migration_and_tamper_rejection(self) -> None:
        graph = SceneGraph(synthetic_three_scene_manifest())
        ledger = initialized_ledger(graph)
        next_state, _ = graph.apply(graph.initial_state(), "listen")
        ledger.append(
            "player_action",
            {
                "action_id": "listen",
                "resulting_patch": {
                    "scene_id": next_state.scene_id,
                    "beat_id": next_state.beat_id,
                    "relationship_delta": {"Mira": 1},
                    "reveal_facts": ["a coded signal is behind the door"],
                },
            },
            "2026-08-29T00:01:00Z",
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = SaveStore(root)
            saved_path = store.save("chapter_one", ledger, graph.manifest_hash)
            self.assertTrue(saved_path.exists())
            self.assertEqual(store.list_slots(), ["chapter_one"])
            loaded = store.load("chapter_one", graph.manifest_hash)
            self.assertEqual(loaded.ledger.to_records(), ledger.to_records())
            replayed = loaded.ledger.replay()
            self.assertEqual((replayed.scene_id, replayed.beat_id), (next_state.scene_id, next_state.beat_id))
            self.assertIn("a coded signal is behind the door", replayed.known_facts)

            v1_record = {"schema": "CreativeSession/v1", "events": ledger.to_records()}
            (root / "legacy.json").write_text(json.dumps(v1_record), encoding="utf-8")
            migrated = store.load("legacy", graph.manifest_hash)
            self.assertEqual(migrated.schema, "CreativeSession/v2")
            self.assertEqual(migrated.migrations, ("CreativeSession/v1->v2",))
            self.assertEqual(migrated.ledger.to_records(), ledger.to_records())

            (root / "broken.json").write_text("not valid json", encoding="utf-8")
            with self.assertRaises(SaveSlotViolation):
                store.load("broken", graph.manifest_hash)
            with self.assertRaises(SaveSlotViolation):
                store.load("chapter_one", "incorrect-manifest-hash")
            self.assertEqual(store.load("chapter_one", graph.manifest_hash).ledger.to_records(), ledger.to_records())

    def test_slot_names_cannot_escape_the_save_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SaveStore(Path(directory))
            for invalid in ("../escape", "con", "C:drive", "slot.name", ""):
                with self.subTest(invalid=invalid):
                    with self.assertRaises(SaveSlotViolation):
                        store.load(invalid, "hash")


if __name__ == "__main__":
    unittest.main()
