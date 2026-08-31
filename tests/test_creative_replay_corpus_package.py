from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package_builder = _load_tool("creative_replay_corpus_package_builder", "build_replay_corpus_package.py")
package_verifier = _load_tool("creative_replay_corpus_package_verifier", "verify_replay_corpus_package.py")


class CreativeReplayCorpusPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True
        ).stdout.strip()
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.package = Path(cls.temporary_directory.name) / "replay-corpus-package"
        cls.built = package_builder.build_package(cls.package, cls.head)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary_directory.cleanup()

    def test_builder_and_verifier_reconstruct_every_synthetic_route(self) -> None:
        receipt = package_verifier.verify_package(self.package, self.head, require_clean_worktree=False)
        corpus = json.loads((self.package / "replay_corpus.json").read_text(encoding="utf-8"))
        self.assertEqual(self.built["status"], "replay_corpus_package_built")
        self.assertEqual(receipt["status"], "replay_corpus_package_exactly_verified")
        self.assertEqual(receipt["corpus_id"], corpus["corpus_id"])
        self.assertEqual(receipt["entry_count"], 38)
        self.assertGreater(receipt["branch_point_count"], 4)
        self.assertEqual(receipt["scenario_route_counts"], corpus["scenario_route_counts"])
        self.assertFalse(receipt["boundary"]["caller_free_text_present"])

    def test_builder_never_overwrites_existing_directory(self) -> None:
        marker = self.package / "keep.txt"
        marker.write_text("do not overwrite", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            package_builder.build_package(self.package, self.head)
        self.assertEqual(marker.read_text(encoding="utf-8"), "do not overwrite")
        marker.unlink()

    def test_verifier_rejects_tampered_route_and_extra_member(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "replay-corpus-package"
            shutil.copytree(self.package, package)
            corpus_path = package / "replay_corpus.json"
            corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
            corpus["entries"][0]["action_ids"] = ["forged"]
            corpus_path.write_text(json.dumps(corpus), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "manifest"):
                package_verifier.verify_package(package, self.head, require_clean_worktree=False)
            (package / "unexpected.txt").write_text("unexpected", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "exactly its fixed"):
                package_verifier.verify_package(package, self.head, require_clean_worktree=False)

    def test_verifier_rejects_tampered_review_board_after_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "replay-corpus-package"
            shutil.copytree(self.package, package)
            review_path = package / "replay_review_board.json"
            board = json.loads(review_path.read_text(encoding="utf-8"))
            board["branch_points"][0]["choices"][0]["transition_id"] = "forged"
            review_path.write_text(json.dumps(board), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "manifest"):
                package_verifier.verify_package(package, self.head, require_clean_worktree=False)

    def test_verifier_rejects_wrong_exact_head_before_reading_package(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Exact-head mismatch"):
            package_verifier.verify_package(self.package, "0" * 40, require_clean_worktree=False)


if __name__ == "__main__":
    unittest.main()
