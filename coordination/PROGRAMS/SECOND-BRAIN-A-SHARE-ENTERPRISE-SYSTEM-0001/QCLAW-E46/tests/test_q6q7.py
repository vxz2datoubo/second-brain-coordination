"""E46 Q6-Q7 tests — Corpus, Mutations."""

import unittest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from qclaw_e46.corpus import (
    build_corpus, CorpusInput, CorpusExpected, 
    run_evaluator, EvaluatorResult,
)
from qclaw_e46.mutations import (
    MUTATIONS, PRODUCTION_MODULES,
    compute_hash,
    apply_mutation, restore_source,
    run_mutation, run_all_mutations,
)


class TestCorpus(unittest.TestCase):
    """Q6: Corpus + evaluator."""
    
    def test_build_corpus_returns_separate_lists(self):
        inputs, expecteds = build_corpus()
        self.assertEqual(len(inputs), len(expecteds))
        self.assertGreater(len(inputs), 0)
    
    def test_positive_case_not_rejected(self):
        inputs, expecteds = build_corpus()
        pos_cases = [e for e in expecteds if not e.should_reject]
        self.assertGreater(len(pos_cases), 0)
    
    def test_anti_pattern_cases_should_reject(self):
        inputs, expecteds = build_corpus()
        ap_cases = [e for e in expecteds if e.should_reject]
        self.assertGreater(len(ap_cases), 0)
        for ap in ap_cases:
            self.assertTrue(ap.anti_pattern_name)
    
    def test_input_never_contains_expected(self):
        """CorpusInput is a different type than CorpusExpected."""
        inp = CorpusInput(case_id="t", case_type="POSITIVE", source_text=b"test")
        self.assertNotIsInstance(inp, CorpusExpected)
    
    def test_evaluator_detects_mismatch(self):
        inputs, expecteds = build_corpus()
        # A pipeline that returns wrong data
        def bad_pipeline(inp):
            return {"atom_count": 0, "atom_types": [], "confidence": "UNTRUSTED", "memory_zone": "NO_PERSIST"}
        results = run_evaluator(inputs[:1], expecteds[:1], bad_pipeline)
        # C01 expects HIGH/PROJECT, pipeline returns UNTRUSTED/NO_PERSIST -> FAIL
        self.assertEqual(results[0].verdict, "FAIL")
    
    def test_evaluator_returns_results_for_all(self):
        inputs, expecteds = build_corpus()
        def simple_pipeline(inp):
            return {"atom_count": 1, "atom_types": ["DEFINITION"], "confidence": "HIGH", "memory_zone": "PROJECT"}
        results = run_evaluator(inputs, expecteds, simple_pipeline)
        self.assertEqual(len(results), len(inputs))
    
    def test_null_pipeline_is_fail(self):
        inputs, expecteds = build_corpus()
        def null_pipeline(inp):
            return None
        results = run_evaluator(inputs[:1], expecteds[:1], null_pipeline)
        self.assertEqual(results[0].verdict, "FAIL")


class TestMutations(unittest.TestCase):
    """Q7: Real mutation harness — anchors, apply, restore."""
    
    def test_mutations_defined(self):
        """At least 8 mutations defined."""
        self.assertGreaterEqual(len(MUTATIONS), 8)
    
    def test_production_modules_exist(self):
        """All production modules must exist."""
        for name, path in PRODUCTION_MODULES.items():
            self.assertTrue(os.path.isfile(path), f"Missing: {name} at {path}")
    
    def test_all_anchors_found_in_source(self):
        """Every mutation anchor must exist in current source."""
        missing = []
        for mut in MUTATIONS:
            filepath = PRODUCTION_MODULES[mut.module]
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            if mut.anchor_text not in content:
                missing.append(f"{mut.name}: '{mut.anchor_text[:40]}' not found in {mut.module}")
        self.assertEqual(len(missing), 0, f"Missing anchors:\n" + "\n".join(missing))
    
    def test_apply_mutation_changes_hash(self):
        """Applying a mutation changes the file hash."""
        mut = MUTATIONS[0]  # M01
        filepath = PRODUCTION_MODULES[mut.module]
        with open(filepath, "r", encoding="utf-8") as f:
            original = f.read()
        source_hash = compute_hash(filepath)
        
        src_hash, mut_hash, anchor = apply_mutation(mut)
        self.assertNotEqual(src_hash, mut_hash, "Mutation should change hash")
        self.assertTrue(anchor)
        
        # Restore
        restore_source(filepath, original)
        self.assertEqual(source_hash, compute_hash(filepath))
    
    def test_restore_exact_after_apply(self):
        """Restore after apply returns exact original hash."""
        mut = MUTATIONS[0]
        filepath = PRODUCTION_MODULES[mut.module]
        original_hash = compute_hash(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            original = f.read()
        
        apply_mutation(mut)
        restored_hash = restore_source(filepath, original)
        self.assertEqual(original_hash, restored_hash)
    
    def test_single_mutation_apply_restore_cycle(self):
        """Mutation apply+restore cycle preserves original hash."""
        mut = MUTATIONS[1]  # M02
        filepath = PRODUCTION_MODULES[mut.module]
        with open(filepath, "r", encoding="utf-8") as f:
            original = f.read()
        
        # Verify anchor exists
        self.assertIn(mut.anchor_text, original)
        
        # Apply
        src_hash, mut_hash, anchor = apply_mutation(mut)
        self.assertTrue(anchor)
        self.assertNotEqual(src_hash, mut_hash, "Mutation should change hash")
        
        # Verify source file changed
        with open(filepath, "r", encoding="utf-8") as f:
            modified = f.read()
        self.assertIn(mut.replacement_text, modified)
        
        # Restore
        restored_hash = restore_source(filepath, original)
        self.assertEqual(src_hash, restored_hash, "Restored hash must match original")
        
        # Verify source file restored
        with open(filepath, "r", encoding="utf-8") as f:
            restored = f.read()
        self.assertEqual(original, restored, "Restored content must match original")
    
    def test_restore_works_for_all(self):
        """Restore after all mutations returns to original state."""
        original_hashes = {name: compute_hash(path) for name, path in PRODUCTION_MODULES.items()}
        originals = {}
        for name, path in PRODUCTION_MODULES.items():
            with open(path, "r", encoding="utf-8") as f:
                originals[name] = f.read()
        
        # Apply and immediately restore each
        for mut in MUTATIONS:
            filepath = PRODUCTION_MODULES[mut.module]
            if mut.anchor_text in originals[mut.module]:
                apply_mutation(mut)
                restore_source(filepath, originals[mut.module])
        
        # Verify all restored
        for name, path in PRODUCTION_MODULES.items():
            self.assertEqual(original_hashes[name], compute_hash(path),
                           f"Module {name} not properly restored!")


if __name__ == "__main__":
    unittest.main()
