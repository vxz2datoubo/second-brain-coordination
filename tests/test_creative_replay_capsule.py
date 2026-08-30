from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from apps.cli import creativectl
from creative_runtime.continuity import graph_for_ledger
from creative_runtime.contracts import PlayerAction
from creative_runtime.ledger import CreativeLedger
from creative_runtime.replay_capsule import (
    ReplayCapsuleViolation,
    build_verified_replay_capsule,
    verify_verified_replay_capsule,
)


class CreativeReplayCapsuleTests(unittest.TestCase):
    def _played_workspace(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        directory = tempfile.TemporaryDirectory()
        workspace = Path(directory.name)
        creativectl.run(["--workspace", str(workspace), "init", "--scenario", "night_signal"])
        creativectl.run(["--workspace", str(workspace), "choose", "listen"])
        creativectl.run(["--workspace", str(workspace), "choose", "approach"])
        creativectl.run(["--workspace", str(workspace), "choose", "listen"])
        return directory, workspace

    def test_capsule_rebuilds_a_played_route_with_all_runtime_projections(self) -> None:
        directory, workspace = self._played_workspace()
        with directory:
            capsule = creativectl.run(["--workspace", str(workspace), "replay-capsule"])
            verified = verify_verified_replay_capsule(capsule)
        self.assertEqual(capsule["schema"], "CreativeSyntheticReplayCapsule/v1")
        self.assertEqual(capsule["status"], "synthetic_replay_capsule_verified")
        self.assertEqual(capsule["scenario"], "night_signal")
        self.assertEqual(capsule["timeline_hash"], capsule["experience"]["timeline_hash"])
        self.assertEqual(capsule["timeline_hash"], capsule["sequence"]["timeline_hash"])
        self.assertEqual(capsule["timeline_hash"], capsule["director"]["verified_input"]["timeline_hash"])
        self.assertEqual(capsule["source"]["event_count"], len(capsule["source"]["events"]))
        self.assertEqual(verified.capsule_id, capsule["capsule_id"])
        self.assertFalse(capsule["boundary"]["contains_customer_material"])
        self.assertFalse(capsule["boundary"]["contains_caller_free_text"])
        self.assertFalse(capsule["boundary"]["external_provider_called"])

    def test_verifier_rejects_any_tampered_projection_or_cross_scenario_claim(self) -> None:
        directory, workspace = self._played_workspace()
        with directory:
            capsule = creativectl.run(["--workspace", str(workspace), "replay-capsule"])
        changed_director = copy.deepcopy(capsule)
        changed_director["director"]["shots"][0]["camera"] = "invented camera"
        with self.assertRaises(ReplayCapsuleViolation):
            verify_verified_replay_capsule(changed_director)
        changed_scenario = copy.deepcopy(capsule)
        changed_scenario["scenario"] = "harbor_protocol"
        with self.assertRaises(ReplayCapsuleViolation):
            verify_verified_replay_capsule(changed_scenario)
        changed_event = copy.deepcopy(capsule)
        changed_event["source"]["events"][1]["payload"]["resulting_patch"]["risk_delta"] = 999
        with self.assertRaises(ReplayCapsuleViolation):
            verify_verified_replay_capsule(changed_event)

    def test_capsule_rejects_graph_legal_but_caller_authored_choice_text(self) -> None:
        ledger = CreativeLedger()
        ledger.append(
            "story_initialized",
            {"state": {"scene_id": "station_platform", "beat_id": "platform_arrival", "relationships": {"mira": 0}, "known_facts": [], "risk_level": 0, "flags": {}}},
            "2030-01-01T00:00:00Z",
        )
        graph = graph_for_ledger(ledger)
        transition = graph.transition_for(ledger.replay(), "listen")
        ledger.append(
            "player_action",
            {
                "action": PlayerAction("listen", "choice", "a caller supplied safe phrase").to_dict(),
                "resulting_patch": dict(transition.resulting_patch),
                "transition_id": transition.transition_id,
                "graph_revision": graph.revision,
            },
            "2030-01-01T00:01:00Z",
        )
        with self.assertRaisesRegex(ReplayCapsuleViolation, "caller-authored"):
            build_verified_replay_capsule(ledger)

    def test_cli_say_route_cannot_be_exported_as_a_github_safe_capsule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
            chosen = creativectl.run(["--workspace", str(workspace), "say", "listen"])
            self.assertEqual(chosen["status"], "chosen")
            with self.assertRaisesRegex(ReplayCapsuleViolation, "caller-authored"):
                creativectl.run(["--workspace", str(workspace), "replay-capsule"])


if __name__ == "__main__":
    unittest.main()
