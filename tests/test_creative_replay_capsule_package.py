from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from apps.cli import creativectl
from creative_runtime.replay_capsule import ReplayCapsuleViolation


ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package_builder = _load_tool("creative_replay_capsule_package_builder", "build_replay_capsule_package.py")
package_verifier = _load_tool("creative_replay_capsule_package_verifier", "verify_replay_capsule_package.py")


class CreativeReplayCapsulePackageTests(unittest.TestCase):
    def _head(self) -> str:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()

    def _canonical_workspace(self, directory: Path) -> Path:
        workspace = directory / "workspace"
        creativectl.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
        creativectl.run(["--workspace", str(workspace), "choose", "listen"])
        creativectl.run(["--workspace", str(workspace), "choose", "approach"])
        creativectl.run(["--workspace", str(workspace), "choose", "listen"])
        return workspace

    def test_builder_and_verifier_reconstruct_a_fixed_synthetic_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "replay-package"
            built = package_builder.build_package(package, self._canonical_workspace(root), expected_head=self._head())
            receipt = package_verifier.verify_package(package, self._head(), require_clean_worktree=False)
            capsule = json.loads((package / "replay_capsule.json").read_text(encoding="utf-8"))
        self.assertEqual(built["status"], "replay_capsule_package_built")
        self.assertEqual(receipt["status"], "replay_capsule_package_exactly_verified")
        self.assertEqual(receipt["capsule_id"], capsule["capsule_id"])
        self.assertEqual(receipt["timeline_hash"], capsule["timeline_hash"])
        self.assertEqual(receipt["event_count"], 4)
        self.assertFalse(receipt["boundary"]["contains_caller_free_text"])

    def test_builder_never_overwrites_an_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "replay-package"
            package.mkdir()
            marker = package / "keep.txt"
            marker.write_text("do not overwrite", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                package_builder.build_package(package, self._canonical_workspace(root), expected_head=self._head())
            self.assertEqual(marker.read_text(encoding="utf-8"), "do not overwrite")

    def test_caller_text_route_is_rejected_before_any_package_directory_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            package = root / "unsafe-package"
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "night_signal"])
            creativectl.run(["--workspace", str(workspace), "say", "listen"])
            with self.assertRaisesRegex(ReplayCapsuleViolation, "caller-authored"):
                package_builder.build_package(package, workspace, expected_head=self._head())
            self.assertFalse(package.exists())

    def test_verifier_rejects_tampered_member_and_extra_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "replay-package"
            package_builder.build_package(package, self._canonical_workspace(root), expected_head=self._head())
            player = package / "verified_replay_capsule_player.html"
            player.write_text(player.read_text(encoding="utf-8") + "<!-- changed -->", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "manifest"):
                package_verifier.verify_package(package, self._head(), require_clean_worktree=False)
            player.write_bytes((ROOT / "apps" / "web" / "verified_replay_capsule_player.html").read_bytes())
            (package / "unexpected.txt").write_text("unexpected", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "exactly its fixed"):
                package_verifier.verify_package(package, self._head(), require_clean_worktree=False)


if __name__ == "__main__":
    unittest.main()
