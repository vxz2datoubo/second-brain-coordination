from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import unittest

from creative_runtime.experience_library import (
    ExperienceLibraryViolation,
    artifact_sha256,
    build_synthetic_experience_artifact,
    build_verified_experience_library,
    verify_verified_experience_library,
)


ROOT = Path(__file__).resolve().parents[1]


class CreativeExperienceLibraryTests(unittest.TestCase):
    def _head(self) -> str:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()

    def test_library_contains_every_registered_synthetic_scenario_at_one_exact_head(self) -> None:
        head = self._head()
        library = build_verified_experience_library(head)
        payload = library.to_dict()
        self.assertEqual(payload["schema"], "CreativeRuntimeExperienceLibrary/v1")
        self.assertEqual(payload["status"], "experience_library_verified")
        self.assertEqual(payload["head_sha"], head)
        self.assertEqual(payload["entry_count"], 2)
        self.assertEqual([entry["scenario"] for entry in payload["entries"]], ["harbor_protocol", "night_signal"])
        self.assertEqual(payload["scenario_ids"], ["harbor_protocol", "night_signal"])
        self.assertTrue(payload["boundary"]["synthetic_only"])
        self.assertFalse(payload["boundary"]["client_story_authority"])
        for entry in payload["entries"]:
            artifact = entry["artifact"]
            self.assertEqual(artifact["head_sha"], head)
            self.assertEqual(entry["scenario"], artifact["scenario"])
            self.assertEqual(entry["artifact_sha256"], artifact_sha256(artifact))
            self.assertEqual(entry["catalog_id"], artifact["catalog"]["catalog_id"])
            self.assertEqual(entry["graph_revision"], artifact["catalog"]["graph_revision"])

    def test_library_verifier_rejects_any_tampered_entry_or_changed_scenario_set(self) -> None:
        head = self._head()
        payload = build_verified_experience_library(head).to_dict()
        verified = verify_verified_experience_library(head, payload)
        self.assertEqual(verified.to_dict(), payload)

        forged = deepcopy(payload)
        forged["entries"][0]["artifact"]["catalog"]["edges"][0]["action_label"] = "forged local label"
        with self.assertRaisesRegex(ExperienceLibraryViolation, "does not exactly match"):
            verify_verified_experience_library(head, forged)

        shortened = deepcopy(payload)
        shortened["entries"] = shortened["entries"][:1]
        shortened["entry_count"] = 1
        with self.assertRaisesRegex(ExperienceLibraryViolation, "complete registered"):
            verify_verified_experience_library(head, shortened)

    def test_single_artifact_and_library_entry_share_the_runtime_owned_rebuild_contract(self) -> None:
        head = self._head()
        artifact = build_synthetic_experience_artifact(head, "night_signal")
        library = build_verified_experience_library(head)
        entry = next(item for item in library.entries if item["scenario"] == "night_signal")
        self.assertEqual(entry["artifact"], artifact)


if __name__ == "__main__":
    unittest.main()
