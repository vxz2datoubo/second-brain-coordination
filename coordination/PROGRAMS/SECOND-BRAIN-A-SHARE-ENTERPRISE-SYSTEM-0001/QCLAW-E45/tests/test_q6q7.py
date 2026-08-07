"""E45 Q6/Q7 — Corpus evaluator + mutation anchor tests

Mutation subprocess execution is left to CI workflow.
Tests here verify: anchors found, structure correct, restore works on dry-run replacement.
"""
import unittest, os, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from qclaw_e45.capability import make_test_capability, EvidenceOrigin, VerificationState
from qclaw_e45.authority import EvidenceRegistry, EvidenceFactory
from qclaw_e45.master_record import MasterRegistry
from qclaw_e45.cognition import CognitionEngine
from qclaw_e45.skill_lifecycle import SkillFactory
from qclaw_e45.corpus import build_corpus, CorpusInput, CorpusExpected, run_pipeline


def _test_cap_fn(raw_bytes, source_id):
    text = raw_bytes.decode("utf-8", "replace")
    if "user_msg_" in source_id:
        origin = EvidenceOrigin.USER_EXPLICIT_MESSAGE
    elif "hypothesis" in text.lower() or "Maybe" in text:
        origin = EvidenceOrigin.HYPOTHESIS
    elif "best" in text.lower() or "opinion" in text.lower():
        origin = EvidenceOrigin.VALUE_JUDGMENT
    elif "Expert" in text or "author" in text.lower():
        origin = EvidenceOrigin.AUTHOR_CLAIM
    elif raw_bytes == b"" or "api_key" in text.lower():
        origin = EvidenceOrigin.UNKNOWN
    else:
        origin = EvidenceOrigin.SOURCE_DOCUMENT
    return make_test_capability(source_id, (0, len(text)), text, origin, raw_bytes,
                               verified=(origin != EvidenceOrigin.UNKNOWN))


class TestCorpusEvaluator(unittest.TestCase):
    def setUp(self):
        self.corpus = build_corpus()

    def test_corpus_has_8_cases(self):
        self.assertEqual(len(self.corpus), 8)

    def test_input_expected_separate_types(self):
        for case in self.corpus:
            self.assertIsInstance(case.input, CorpusInput)
            self.assertIsInstance(case.expected, CorpusExpected)

    def test_run_pipeline_source_fact(self):
        reg = EvidenceRegistry(); evf = EvidenceFactory(reg)
        mr = MasterRegistry(); ce = CognitionEngine(reg); sf = SkillFactory()
        outcome = run_pipeline(self.corpus[0].input, _test_cap_fn, evf, mr, ce, sf)
        self.assertEqual(outcome["origin"], "source_document")

    def test_run_pipeline_user_explicit(self):
        reg = EvidenceRegistry(); evf = EvidenceFactory(reg)
        mr = MasterRegistry(); ce = CognitionEngine(reg); sf = SkillFactory()
        outcome = run_pipeline(self.corpus[1].input, _test_cap_fn, evf, mr, ce, sf)
        self.assertEqual(outcome["origin"], "user_explicit_message")

    def test_run_pipeline_hypothesis(self):
        reg = EvidenceRegistry(); evf = EvidenceFactory(reg)
        mr = MasterRegistry(); ce = CognitionEngine(reg); sf = SkillFactory()
        outcome = run_pipeline(self.corpus[2].input, _test_cap_fn, evf, mr, ce, sf)
        self.assertEqual(outcome["origin"], "hypothesis")

    def test_empty_input(self):
        case = self.corpus[4]
        self.assertEqual(len(case.input.input_bytes), 0)

    def test_secret_case(self):
        case = self.corpus[5]
        self.assertIn(b"api_key", case.input.input_bytes)

    def test_pipeline_never_receives_expected(self):
        import inspect
        sig = inspect.signature(run_pipeline)
        params = list(sig.parameters)
        self.assertNotIn("expected", params)
        self.assertNotIn("ground_truth", params)
        self.assertNotIn("should_fail", params)


class TestMutationAnchors(unittest.TestCase):
    def test_mutations_defined(self):
        from qclaw_e45.mutations import MUTATIONS
        self.assertEqual(len(MUTATIONS), 15)

    def test_all_anchors_found(self):
        from qclaw_e45.mutations import MUTATIONS
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for m in MUTATIONS:
            tf = os.path.join(base, m["target_file"])
            self.assertTrue(os.path.isfile(tf), f"target not found: {tf}")
            with open(tf, "rb") as f:
                content = f.read()
            self.assertIn(m["anchor"], content, f"{m['id']} anchor not found")

    def test_all_anchors_unique(self):
        from qclaw_e45.mutations import MUTATIONS
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for m in MUTATIONS:
            tf = os.path.join(base, m["target_file"])
            with open(tf, "rb") as f:
                content = f.read()
            count = content.count(m["anchor"])
            self.assertEqual(count, 1, f"{m['id']} anchor appears {count}x")

    def test_restore_works(self):
        """Dry-run: apply and immediately restore without subprocess."""
        from qclaw_e45.mutations import MUTATIONS
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        m0 = MUTATIONS[0]
        tf = os.path.join(base, m0["target_file"])
        with open(tf, "rb") as f:
            original = f.read()
        original_sha = hashlib.sha256(original).hexdigest()
        # Apply
        mutant = original.replace(m0["anchor"], m0["replacement"], 1)
        self.assertNotEqual(mutant, original, "mutation did not change source")
        # Write then restore
        with open(tf, "wb") as f:
            f.write(mutant)
        with open(tf, "wb") as f:
            f.write(original)
        # Verify restored
        with open(tf, "rb") as f:
            restored = f.read()
        self.assertEqual(hashlib.sha256(restored).hexdigest(), original_sha,
                        "restore failed — source modified!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
