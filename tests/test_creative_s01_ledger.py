from __future__ import annotations

import json
import unittest

from creative_runtime.contracts import PlayerAction, StoryState, canonical_json
from creative_runtime.ledger import CreativeLedger, LedgerViolation, create_artifact


class CreativeS01LedgerTests(unittest.TestCase):
    def build_ledger(self) -> CreativeLedger:
        ledger = CreativeLedger()
        ledger.append(
            "story_initialized",
            {"state": StoryState(scene_id="atrium", beat_id="arrival", relationships={"mira": 0}).to_dict()},
            "2030-01-01T00:00:00Z",
        )
        ledger.append(
            "player_action",
            {
                "action": PlayerAction("listen", "choice", "Listen at the door").to_dict(),
                "resulting_patch": {
                    "beat_id": "echo",
                    "relationship_delta": {"mira": 1},
                    "reveal_facts": ["a hidden witness exists"],
                    "risk_delta": 1,
                },
            },
            "2030-01-01T00:01:00Z",
        )
        return ledger

    def test_same_explicit_inputs_create_same_event_chain_and_replay(self) -> None:
        first = self.build_ledger()
        second = self.build_ledger()
        self.assertEqual(first.to_records(), second.to_records())
        self.assertEqual(first.replay(), second.replay())
        replayed = CreativeLedger.from_records(json.loads(canonical_json(first.to_records()))).replay()
        self.assertEqual(replayed.beat_id, "echo")
        self.assertEqual(replayed.relationships["mira"], 1)
        self.assertEqual(replayed.known_facts, ("a hidden witness exists",))

    def test_tampered_record_cannot_replay(self) -> None:
        records = self.build_ledger().to_records()
        records[1]["payload"]["resulting_patch"]["risk_delta"] = 99
        with self.assertRaises(LedgerViolation):
            CreativeLedger.from_records(records)

    def test_artifact_has_stable_source_hash_and_parent_reference(self) -> None:
        artifact = create_artifact(
            "story_beat",
            {"beat_id": "arrival", "text": "Synthetic private scene"},
            "2030-01-01T00:00:00Z",
            parent_artifact_ids=("art_parent",),
        )
        same = create_artifact(
            "story_beat",
            {"text": "Synthetic private scene", "beat_id": "arrival"},
            "2030-01-01T00:00:00Z",
            parent_artifact_ids=("art_parent",),
        )
        self.assertEqual(artifact.artifact_id, same.artifact_id)
        self.assertEqual(artifact.source_hash, same.source_hash)
        self.assertEqual(artifact.parent_artifact_ids, ("art_parent",))

    def test_non_finite_json_values_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            canonical_json({"invalid": float("nan")})


if __name__ == "__main__":
    unittest.main()
