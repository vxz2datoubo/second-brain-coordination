from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from creative_runtime.replay_corpus import build_verified_synthetic_replay_corpus
from creative_runtime.replay_review import (
    ReplayReviewViolation,
    build_verified_replay_review_board,
    verify_verified_replay_review_board,
)


ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


review_builder = _load_tool("creative_replay_review_builder", "build_replay_review_board.py")
review_verifier = _load_tool("creative_replay_review_verifier", "verify_replay_review_board.py")
CLI_SPEC = importlib.util.spec_from_file_location(
    "creativectl_replay_review", ROOT / "apps" / "cli" / "creativectl.py"
)
assert CLI_SPEC and CLI_SPEC.loader
creativectl = importlib.util.module_from_spec(CLI_SPEC)
CLI_SPEC.loader.exec_module(creativectl)


class CreativeReplayReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True
        ).stdout.strip()
        cls.corpus = build_verified_synthetic_replay_corpus(cls.head).to_dict()
        cls.board = build_verified_replay_review_board(cls.head, cls.corpus)

    def test_board_lists_only_real_choice_points_with_exact_terminal_deltas(self) -> None:
        verified = verify_verified_replay_review_board(self.head, self.corpus, self.board)
        self.assertEqual(verified["schema"], "CreativeSyntheticReplayReviewBoard/v1")
        self.assertEqual(verified["corpus_id"], self.corpus["corpus_id"])
        self.assertGreater(verified["branch_point_count"], 4)
        self.assertEqual(verified["branch_point_count"], len(verified["branch_points"]))
        for branch in verified["branch_points"]:
            self.assertGreaterEqual(len(branch["choices"]), 2)
            self.assertTrue(branch["prefix_state_hash"])
            for choice in branch["choices"]:
                self.assertTrue(choice["transition_id"])
                self.assertEqual(choice["terminal_route_count"], len(choice["terminal_outcomes"]))
                self.assertTrue(all(outcome["terminal_delta"]["final_state_hash"] for outcome in choice["terminal_outcomes"]))
                self.assertTrue(all(outcome["director_continuity"]["opening"]["axis"] for outcome in choice["terminal_outcomes"]))
                self.assertEqual(choice["review_tags"], sorted(choice["review_tags"]))

    def test_verifier_rejects_forged_outcome_delta_or_branch_choice(self) -> None:
        forged_delta = copy.deepcopy(self.board)
        forged_delta["branch_points"][0]["choices"][0]["terminal_outcomes"][0]["terminal_delta"]["risk_delta"] = 99
        with self.assertRaises(ReplayReviewViolation):
            verify_verified_replay_review_board(self.head, self.corpus, forged_delta)
        forged_choice = copy.deepcopy(self.board)
        forged_choice["branch_points"][0]["choices"][0]["action_id"] = "forged"
        with self.assertRaises(ReplayReviewViolation):
            verify_verified_replay_review_board(self.head, self.corpus, forged_choice)
        forged_camera = copy.deepcopy(self.board)
        forged_camera["branch_points"][0]["choices"][0]["terminal_outcomes"][0]["director_continuity"]["closing"]["camera"] = "forged"
        with self.assertRaises(ReplayReviewViolation):
            verify_verified_replay_review_board(self.head, self.corpus, forged_camera)

    def test_file_builder_and_verifier_refuse_overwrite_and_head_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review-board.json"
            receipt = review_builder.build_review_board(path, self.head)
            self.assertEqual(receipt["status"], "synthetic_replay_review_board_built")
            self.assertTrue(path.is_file())
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                review_builder.build_review_board(path, self.head)
            supplied = json.loads(path.read_text(encoding="utf-8"))
            supplied["head_sha"] = "0" * 40
            path.write_text(json.dumps(supplied), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                review_verifier.verify_review_board(path, self.head, require_clean_worktree=False)

    def test_cli_exposes_a_read_only_exact_head_filter(self) -> None:
        selection = creativectl.run(["replay-review", "--scenario", "three_scene", "--tag", "scene_change"])
        self.assertEqual(selection["schema"], "CreativeSyntheticReplayReviewSelection/v1")
        self.assertEqual(selection["filters"], {"scenario": "three_scene", "review_tag": "scene_change"})
        self.assertGreater(selection["branch_point_count"], 0)
        self.assertTrue(all(branch["scenario"] == "three_scene" for branch in selection["branch_points"]))
        self.assertTrue(all("scene_change" in branch["review_tags"] for branch in selection["branch_points"]))
        self.assertFalse(selection["boundary"]["external_provider_called"])


if __name__ == "__main__":
    unittest.main()
