from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creative_experience_artifact", ROOT / "tools" / "build_experience_demo.py")
assert SPEC and SPEC.loader
artifact_builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(artifact_builder)


class CreativeExperienceArtifactTests(unittest.TestCase):
    def test_artifact_is_exact_head_bound_and_synthetic(self) -> None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
        artifact = artifact_builder.build_demo_artifact(head)
        self.assertEqual(artifact["status"], "experience_artifact_verified")
        self.assertEqual(artifact["head_sha"], head)
        self.assertEqual(artifact["experience"]["status"], "experience_manifest_verified")
        self.assertEqual(len(artifact["experience"]["frames"]), 6)
        self.assertEqual(artifact["sequence"]["status"], "sequence_plan_verified")
        self.assertEqual(len(artifact["sequence"]["steps"]), 6)
        self.assertEqual(artifact["sequence"]["total_duration_seconds"], 78)
        self.assertEqual(artifact["catalog"]["status"], "scenario_catalog_verified")
        self.assertEqual(len(artifact["catalog"]["covered_transition_ids"]), 14)
        self.assertTrue(artifact["boundary"]["synthetic_only"])
        self.assertFalse(artifact["boundary"]["customer_data_present"])
        self.assertFalse(artifact["boundary"]["external_provider_called"])

    def test_artifact_rejects_wrong_head(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Exact-head mismatch"):
            artifact_builder.build_demo_artifact("0" * 40)


if __name__ == "__main__":
    unittest.main()
