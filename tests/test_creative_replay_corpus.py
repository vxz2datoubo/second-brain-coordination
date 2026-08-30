from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from creative_runtime.replay_corpus import (
    ReplayCorpusViolation,
    SYNTHETIC_REPLAY_CORPUS_SCENARIOS,
    build_verified_synthetic_replay_corpus,
    verify_verified_synthetic_replay_corpus,
)


ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


corpus_builder = _load_tool("creative_replay_corpus_builder", "build_replay_corpus.py")
corpus_verifier = _load_tool("creative_replay_corpus_verifier", "verify_replay_corpus.py")


class CreativeReplayCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True
        ).stdout.strip()
        cls.corpus = build_verified_synthetic_replay_corpus(cls.head).to_dict()

    def _head(self) -> str:
        return self.head

    def test_corpus_covers_every_registered_terminal_route_with_verified_capsules(self) -> None:
        corpus = self.corpus
        verified = verify_verified_synthetic_replay_corpus(self._head(), corpus)
        self.assertEqual(corpus["schema"], "CreativeSyntheticReplayCorpus/v1")
        self.assertEqual(corpus["scenario_ids"], list(SYNTHETIC_REPLAY_CORPUS_SCENARIOS))
        self.assertEqual(corpus["entry_count"], len(verified.entries))
        self.assertGreater(corpus["entry_count"], 20)
        self.assertEqual(sum(corpus["scenario_route_counts"].values()), corpus["entry_count"])
        self.assertEqual({entry["scenario"] for entry in corpus["entries"]}, set(SYNTHETIC_REPLAY_CORPUS_SCENARIOS))
        self.assertEqual(len({entry["route_id"] for entry in corpus["entries"]}), corpus["entry_count"])
        self.assertTrue(all(entry["capsule"]["boundary"]["contains_caller_free_text"] is False for entry in corpus["entries"]))

    def test_verifier_rejects_one_tampered_capsule_or_removed_scenario(self) -> None:
        corpus = self.corpus
        tampered_capsule = copy.deepcopy(corpus)
        tampered_capsule["entries"][0]["capsule"]["director"]["shots"][0]["camera"] = "forged camera"
        with self.assertRaises(ReplayCorpusViolation):
            verify_verified_synthetic_replay_corpus(self._head(), tampered_capsule)
        missing_scenario = copy.deepcopy(corpus)
        missing_scenario["scenario_ids"] = missing_scenario["scenario_ids"][1:]
        with self.assertRaisesRegex(ReplayCorpusViolation, "complete registered scenario set"):
            verify_verified_synthetic_replay_corpus(self._head(), missing_scenario)

    def test_file_builder_and_verifier_refuse_overwrite_and_exact_head_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replay-corpus.json"
            receipt = corpus_builder.build_corpus(path, self._head())
            self.assertEqual(receipt["status"], "synthetic_replay_corpus_built")
            self.assertTrue(path.is_file())
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                corpus_builder.build_corpus(path, self._head())
            supplied = json.loads(path.read_text(encoding="utf-8"))
            supplied["head_sha"] = "0" * 40
            path.write_text(json.dumps(supplied), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                corpus_verifier.verify_corpus(path, self._head(), require_clean_worktree=False)


if __name__ == "__main__":
    unittest.main()
