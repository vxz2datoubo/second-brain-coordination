"""E42 Q6 — Corpus Tests"""
import unittest, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_e42.corpus import (
    build_corpus, CorpusCase, CorpusCaseType, ExpectedAtomType, DOMAIN,
)


class TestCorpus(unittest.TestCase):
    def setUp(self):
        self.corpus = build_corpus()

    def test_minimum_case_count(self):
        """Must have at least 10 cases."""
        self.assertGreaterEqual(len(self.corpus), 10)

    def test_all_case_types_present(self):
        types = {c.case_type for c in self.corpus}
        self.assertIn(CorpusCaseType.POSITIVE, types)
        self.assertIn(CorpusCaseType.NEGATIVE, types)
        self.assertIn(CorpusCaseType.ADVERSARIAL, types)
        self.assertIn(CorpusCaseType.CONTRADICTORY, types)
        self.assertIn(CorpusCaseType.AMBIGUOUS, types)

    def test_all_case_ids_unique(self):
        ids = [c.case_id for c in self.corpus]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_case_ids_contain_seed(self):
        # Every case ID has a seed suffix
        for c in self.corpus:
            self.assertTrue("_" in c.case_id, f"Case {c.case_id} missing seed")

    def test_domain_separation_constant(self):
        self.assertIn(b"QCLAW:E42:CORPUS:V1", DOMAIN)

    def test_case_types_match_enums(self):
        for c in self.corpus:
            self.assertIn(c.case_type, CorpusCaseType)

    def test_anti_pattern_cases_should_fail(self):
        anti = [c for c in self.corpus if c.anti_pattern]
        self.assertTrue(len(anti) >= 3, f"Need at least 3 anti-pattern cases, got {len(anti)}")
        failing = [c for c in anti if c.should_fail]
        self.assertTrue(len(failing) >= 2, f"At least 2 anti-pattern cases require should_fail, got {len(failing)}")

    def test_empty_case(self):
        empty = [c for c in self.corpus if c.raw_input == b""]
        self.assertEqual(len(empty), 1)
        self.assertEqual(empty[0].expected_min_atoms, 0)

    def test_secret_like_case_exists(self):
        secret = [c for c in self.corpus if c.anti_pattern == "secret_string_leakage"]
        self.assertEqual(len(secret), 1)
        self.assertIn(b"sk-", secret[0].raw_input)

    def test_contradictory_case_has_classification(self):
        contra = [c for c in self.corpus if c.case_type == CorpusCaseType.CONTRADICTORY]
        for c in contra:
            self.assertIsNotNone(c.expected_contradiction_class)

    def test_positive_cases_have_expected_atoms(self):
        positive = [c for c in self.corpus if c.case_type == CorpusCaseType.POSITIVE]
        self.assertTrue(len(positive) >= 3)
        for c in positive:
            self.assertGreaterEqual(c.expected_min_atoms, 0)

    def test_no_case_has_raw_input_with_real_secrets(self):
        """Corpus must be PUBLIC_SAFE — no real API keys."""
        for c in self.corpus:
            self.assertNotIn(b"sk-live-", c.raw_input)
            self.assertNotIn(b"xoxb-", c.raw_input)


if __name__ == "__main__":
    unittest.main(verbosity=2)
