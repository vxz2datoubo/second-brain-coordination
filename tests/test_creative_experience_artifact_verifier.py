from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

from creative_runtime.contracts import canonical_json
from creative_runtime.experience_package import PACKAGE_MANIFEST_NAME, build_package_manifest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creative_experience_artifact_verifier", ROOT / "tools" / "verify_experience_artifact.py")
assert SPEC and SPEC.loader
artifact_verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(artifact_verifier)


class CreativeExperienceArtifactVerifierTests(unittest.TestCase):
    def _write_exact_package(self, directory: Path, head: str, scenario: str = "night_signal") -> Path:
        package = directory / "experience-package"
        package.mkdir()
        members = {
            "experience.json": (canonical_json(artifact_verifier.expected_artifact(head, scenario)) + "\n").encode("utf-8"),
            "verified_experience_player.html": (ROOT / "apps" / "web" / "verified_experience_player.html").read_bytes(),
            "README.md": (ROOT / "apps" / "web" / "README.md").read_bytes(),
        }
        for name, content in members.items():
            (package / name).write_bytes(content)
        (package / PACKAGE_MANIFEST_NAME).write_text(canonical_json(build_package_manifest(head, members)) + "\n", encoding="utf-8")
        return package

    def test_verifier_rebuilds_and_checks_the_exact_demo_artifact(self) -> None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experience.json"
            player = Path(directory) / "verified_experience_player.html"
            guide = Path(directory) / "README.md"
            path.write_text(canonical_json(artifact_verifier.expected_artifact(head)) + "\n", encoding="utf-8")
            player.write_bytes((ROOT / "apps" / "web" / "verified_experience_player.html").read_bytes())
            guide.write_bytes((ROOT / "apps" / "web" / "README.md").read_bytes())
            receipt = artifact_verifier.verify_artifact(path, head, require_clean_worktree=False, player_path=player, guide_path=guide)
        self.assertEqual(receipt["status"], "experience_artifact_exactly_verified")
        self.assertEqual(receipt["head_sha"], head)
        self.assertEqual(receipt["catalog_node_count"], 24)
        self.assertEqual(receipt["catalog_edge_count"], 23)
        self.assertEqual(receipt["catalog_transition_count"], 14)
        self.assertEqual(receipt["sequence_step_count"], 6)
        self.assertEqual(receipt["sequence_total_duration_seconds"], 78)
        self.assertEqual(receipt["worktree_status"], "not_checked_for_verifier_self_test")
        self.assertTrue(receipt["package_members_verified"])
        self.assertEqual(len(receipt["player_sha256"]), 64)
        self.assertEqual(len(receipt["guide_sha256"]), 64)
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

    def test_verifier_rejects_a_tampered_static_player(self) -> None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experience.json"
            player = Path(directory) / "verified_experience_player.html"
            path.write_text(canonical_json(artifact_verifier.expected_artifact(head)) + "\n", encoding="utf-8")
            player.write_text("forged player", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Static player does not exactly match"):
                artifact_verifier.verify_artifact(path, head, require_clean_worktree=False, player_path=player)

    def test_package_verifier_rebuilds_and_checks_the_fixed_four_file_package(self) -> None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
        with tempfile.TemporaryDirectory() as directory:
            package = self._write_exact_package(Path(directory), head)
            receipt = artifact_verifier.verify_package(package, head, require_clean_worktree=False)
        self.assertEqual(receipt["status"], "experience_package_exactly_verified")
        self.assertEqual(receipt["package_member_count"], 3)
        self.assertEqual(receipt["catalog_node_count"], 24)
        self.assertEqual(receipt["sequence_step_count"], 6)

    def test_package_verifier_rejects_a_member_changed_after_its_manifest(self) -> None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
        with tempfile.TemporaryDirectory() as directory:
            package = self._write_exact_package(Path(directory), head)
            (package / "README.md").write_text("forged guide", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "manifest does not exactly match"):
                artifact_verifier.verify_package(package, head, require_clean_worktree=False)

    def test_verifier_rebuilds_the_harbor_protocol_package_from_its_declared_scenario(self) -> None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
        with tempfile.TemporaryDirectory() as directory:
            package = self._write_exact_package(Path(directory), head, "harbor_protocol")
            receipt = artifact_verifier.verify_package(package, head, require_clean_worktree=False)
        self.assertEqual(receipt["status"], "experience_package_exactly_verified")
        self.assertEqual(receipt["scenario"], "harbor_protocol")
        self.assertEqual(receipt["catalog_transition_count"], 12)
        self.assertEqual(receipt["sequence_step_count"], 6)


if __name__ == "__main__":
    unittest.main()
