from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

from creative_runtime.contracts import canonical_json


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creative_experience_artifact_verifier", ROOT / "tools" / "verify_experience_artifact.py")
assert SPEC and SPEC.loader
artifact_verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(artifact_verifier)


class CreativeExperienceArtifactVerifierTests(unittest.TestCase):
    def test_verifier_rebuilds_and_checks_the_exact_demo_artifact(self) -> None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experience.json"
            path.write_text(canonical_json(artifact_verifier.expected_artifact(head)) + "\n", encoding="utf-8")
            receipt = artifact_verifier.verify_artifact(path, head, require_clean_worktree=False)
        self.assertEqual(receipt["status"], "experience_artifact_exactly_verified")
        self.assertEqual(receipt["head_sha"], head)
        self.assertEqual(receipt["catalog_node_count"], 24)
        self.assertEqual(receipt["catalog_edge_count"], 23)
        self.assertEqual(receipt["catalog_transition_count"], 14)
        self.assertEqual(receipt["worktree_status"], "not_checked_for_verifier_self_test")
        self.assertTrue(receipt["boundary"]["synthetic_only"])

    def test_verifier_rejects_one_tampered_catalogue_edge(self) -> None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experience.json"
            artifact = artifact_verifier.expected_artifact(head)
            artifact["catalog"]["edges"][0]["to_timeline_hash"] = "forged"
            path.write_text(canonical_json(artifact) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "does not exactly match"):
                artifact_verifier.verify_artifact(path, head, require_clean_worktree=False)


if __name__ == "__main__":
    unittest.main()
