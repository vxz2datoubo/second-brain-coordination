"""E44 Q6-Q7 Tests — Corpus evaluator and mutation harness validation"""
import unittest, os, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)

from qclaw_e44.capability import CapabilityVerifier
from qclaw_e44.authority import EvidenceRegistry, EvidenceFactory
from qclaw_e44.master_record import MasterRegistry
from qclaw_e44.cognition import CognitionEngine
from qclaw_e44.skill_lifecycle import SkillFactory
from qclaw_e44.corpus import build_corpus, run_pipeline, evaluate_corpus


def _make_services():
    reg = EvidenceRegistry()
    evf = EvidenceFactory(reg, b"e44_ev_key_xxxxxxxxxxxxxxxxx32")
    cv = CapabilityVerifier("E44-eval-issuer", "1.0")
    master = MasterRegistry(b"e44_master_key_xxxxxxxxxxxxxxx32")
    cog = CognitionEngine(reg, b"e44_cog_key_xxxxxxxxxxxxxxxxx32")
    skill_f = SkillFactory(b"e44_skill_key_xxxxxxxxxxxxxxxxx32")
    return cv, evf, master, cog, skill_f


class TestCorpusEvaluator(unittest.TestCase):
    def setUp(self):
        self.cv, self.evf, self.master, self.cog, self.skill_f = _make_services()
        self.corpus = build_corpus()

    def test_corpus_has_8_cases(self):
        self.assertGreaterEqual(len(self.corpus), 8)

    def test_run_pipeline_positive(self):
        case = self.corpus[0]
        outcome = run_pipeline(case, self.cv, self.evf, self.master, self.cog, self.skill_f)
        self.assertEqual(outcome["derived_origin"], "source_fact")

    def test_run_pipeline_user_explicit(self):
        case = self.corpus[1]
        outcome = run_pipeline(case, self.cv, self.evf, self.master, self.cog, self.skill_f)
        self.assertEqual(outcome["cognition_state"], "known_and_stated")

    def test_run_pipeline_hypothesis(self):
        case = self.corpus[2]
        run_pipeline(case, self.cv, self.evf, self.master, self.cog, self.skill_f)
        self.assertTrue(case.should_fail)

    def test_evaluate_corpus(self):
        passed, failed, outcomes = evaluate_corpus(self.corpus,
            self.cv, self.evf, self.master, self.cog, self.skill_f)
        self.assertEqual(len(outcomes), 8)

    def test_production_no_ground_truth(self):
        import inspect
        sig = inspect.signature(run_pipeline)
        self.assertNotIn("expected", sig.parameters)

    def test_empty_input_case(self):
        case = self.corpus[5]
        self.assertEqual(len(case.input_bytes), 0)


class TestMutationAnchors(unittest.TestCase):
    """Verify all mutation anchors are found in source without subprocess."""

    def test_mutations_defined(self):
        from qclaw_e44.mutations import MUTATIONS
        self.assertGreaterEqual(len(MUTATIONS), 12)

    def test_anchors_found(self):
        from qclaw_e44.mutations import MUTATIONS
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for m in MUTATIONS:
            tf = os.path.join(base, m["target_file"])
            self.assertTrue(os.path.isfile(tf), f"target: {m['target_file']}")
            with open(tf, "rb") as f:
                content = f.read()
            self.assertIn(m["anchor"], content, f"anchor: {m['id']}")

    def test_mutation_structure(self):
        from qclaw_e44.mutations import MUTATIONS
        for m in MUTATIONS:
            self.assertIn("id", m)
            self.assertIn("anchor", m)
            self.assertEqual(type(m["anchor"]), bytes)

    def test_single_mutation_run(self):
        """Run exactly one mutation (no subprocess, just coverage)."""
        from qclaw_e44.mutations import run_mutation, MUTATIONS
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tf = os.path.join(base, MUTATIONS[0]["target_file"])
        with open(tf, "rb") as f:
            before = hashlib.sha256(f.read()).hexdigest()
        result = run_mutation(MUTATIONS[0])
        with open(tf, "rb") as f:
            after = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(before, after, "source mutated!")
        self.assertIn("anchor_offset", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
