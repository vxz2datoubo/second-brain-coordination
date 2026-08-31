from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creative_experience_artifact_verifier_for_builder", ROOT / "tools" / "verify_experience_artifact.py")
assert SPEC and SPEC.loader
artifact_verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(artifact_verifier)


class CreativeExperiencePackageBuilderTests(unittest.TestCase):
    def test_harbor_package_keeps_played_route_and_exhaustive_catalogue_on_the_same_scenario(self) -> None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "harbor-package"
            result = subprocess.run(
                [sys.executable, "tools/build_experience_package.py", "--expected-head", head, "--scenario", "harbor_protocol", "--output-dir", str(package)],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            artifact = json.loads((package / "experience.json").read_text(encoding="utf-8"))
            receipt = artifact_verifier.verify_package(package, head, require_clean_worktree=False)
        self.assertEqual(artifact["scenario"], "harbor_protocol")
        self.assertEqual(artifact["experience"]["graph_revision"], "HarborProtocolGraph/v1")
        self.assertEqual(artifact["catalog"]["scenario"], "harbor_protocol")
        self.assertEqual(artifact["catalog"]["graph_revision"], "HarborProtocolGraph/v1")
        self.assertEqual(receipt["scenario"], "harbor_protocol")
        self.assertEqual(receipt["catalog_transition_count"], 12)

    def test_builder_refuses_to_overwrite_a_preexisting_package_directory(self) -> None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "already-exists"
            package.mkdir()
            marker = package / "keep.txt"
            marker.write_text("do not overwrite", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "tools/build_experience_package.py", "--expected-head", head, "--output-dir", str(package)],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("already exists", result.stdout)
            self.assertEqual(marker.read_text(encoding="utf-8"), "do not overwrite")


if __name__ == "__main__":
    unittest.main()
