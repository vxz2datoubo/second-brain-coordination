from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from creative_runtime.experience import (
    ExperienceViolation,
    build_verified_experience,
    build_verified_scenario_catalog,
    verify_verified_experience,
    verify_verified_scenario_catalog,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_experience", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeExperienceTests(unittest.TestCase):
    def test_experience_replays_every_prefix_without_backfilling_future_facts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            prefix = ["--workspace", str(workspace), "--slot", "night_route"]
            creativectl.run([*prefix, "init", "--scenario", "night_signal"])
            creativectl.run([*prefix, "choose", "listen"])
            creativectl.run([*prefix, "choose", "approach"])
            ledger = creativectl._load_session(workspace, "night_route")
            manifest = creativectl.run([*prefix, "experience"])

            self.assertEqual(manifest["status"], "experience_manifest_verified")
            self.assertEqual(manifest["slot_id"], "night_route")
            self.assertEqual(len(manifest["frames"]), 3)
            self.assertEqual(manifest["frames"][0]["state"]["beat_id"], "platform_arrival")
            self.assertEqual(manifest["frames"][0]["accessibility"]["known_facts_only"], [])
            self.assertEqual(manifest["frames"][1]["state"]["beat_id"], "platform_signal")
            self.assertEqual(manifest["frames"][1]["accessibility"]["known_facts_only"], ["a protected relay is active"])
            self.assertEqual(manifest["frames"][2]["state"]["scene_id"], "signal_room")
            self.assertEqual(manifest["provenance"]["customer_data_present"], False)
            self.assertEqual(manifest["provenance"]["external_provider_called"], False)
            self.assertEqual(verify_verified_experience(ledger, manifest, slot="night_route").experience_id, manifest["experience_id"])

    def test_experience_rejects_any_tampered_display_frame(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
            ledger = creativectl._load_session(workspace)
            manifest = build_verified_experience(ledger).to_dict()
            manifest["frames"][0]["story_text"] = "invented future disclosure"
            with self.assertRaisesRegex(ExperienceViolation, "does not exactly match"):
                verify_verified_experience(ledger, manifest)

    def test_catalogue_is_exhaustive_and_clients_can_only_follow_verified_edges(self) -> None:
        catalogue = creativectl.run(["catalog", "--scenario", "night_signal"])
        nodes = {node["timeline_hash"]: node["frame"] for node in catalogue["nodes"]}
        edges = {(edge["from_timeline_hash"], edge["action_id"]): edge for edge in catalogue["edges"]}
        current = catalogue["initial_timeline_hash"]

        self.assertEqual(catalogue["status"], "scenario_catalog_verified")
        self.assertEqual(catalogue["scenario"], "night_signal")
        self.assertEqual(len(catalogue["covered_transition_ids"]), 14)
        self.assertEqual({item["action_id"] for item in nodes[current]["legal_choices"]}, {"listen", "approach", "leave"})
        for action_id, expected_scene in (("listen", "station_platform"), ("approach", "signal_room"), ("listen", "archive_vault")):
            current = edges[(current, action_id)]["to_timeline_hash"]
            self.assertEqual(nodes[current]["state"]["scene_id"], expected_scene)
        self.assertNotIn((current, "invent_action"), edges)
        self.assertEqual(
            verify_verified_scenario_catalog("night_signal", catalogue).catalog_id,
            catalogue["catalog_id"],
        )
        catalogue["edges"][0]["to_timeline_hash"] = "forged"
        with self.assertRaisesRegex(ExperienceViolation, "does not exactly match"):
            verify_verified_scenario_catalog("night_signal", catalogue)


if __name__ == "__main__":
    unittest.main()
