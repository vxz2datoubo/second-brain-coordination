from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from creative_runtime.contracts import GenerationRequest, StoryState
from creative_runtime.director import compile_director
from creative_runtime.generation import adapter_for
from creative_runtime.knowledge import KnowledgeReviewBridge
from creative_runtime.provenance import ProvenanceViolation, SourceProvenance, require_reusable_source


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_s06", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeS06EndToEndTests(unittest.TestCase):
    def test_interaction_to_director_to_offline_generation_to_review_to_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init"])
            chosen = creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            state = StoryState.from_dict(chosen["state"])
            compilation = compile_director(state)
            self.assertTrue(compilation.quality_report.can_generate)
            result = adapter_for("offline").generate(
                GenerationRequest("req_e2e_001", "offline", compilation.shots[0], "non_explicit"),
                compilation.quality_report,
            )
            bridge = KnowledgeReviewBridge()
            candidate = bridge.correct(
                "Listening before acting can reveal a safe next step.",
                source_event_ids=(creativectl._load_session(workspace).events[-1].event_id,),
                source_artifact_ids=("art_scene_synthetic_archive",),
            )
            reviewed = bridge.review(candidate.candidate_id, "HUMAN_REVIEWER", True, "Trace checked")
            replayed = creativectl.run(["--workspace", str(workspace), "replay"])
            self.assertEqual(result.status, "simulated")
            self.assertEqual(reviewed.status, "approved_reusable_candidate")
            self.assertEqual(replayed["state"], chosen["state"])

    def test_local_or_unregistered_source_reuse_is_rejected(self) -> None:
        with self.assertRaises(ProvenanceViolation):
            require_reusable_source(SourceProvenance("local-film", "LOCAL_UNVERIFIED", False))
        with self.assertRaises(ProvenanceViolation):
            require_reusable_source(SourceProvenance("external-ref", "REFERENCE_ONLY", False))
        require_reusable_source(SourceProvenance("approved-synthetic", "SYNTHETIC", True, "GPT-IMPORT-001"))


if __name__ == "__main__":
    unittest.main()
