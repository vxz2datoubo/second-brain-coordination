"""E43 Q7 — Mutation Module Tests (build + apply/restore without full execution)"""
import unittest, os, sys, tempfile, shutil, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)

from qclaw_e43.mutations import build_mutations, Mutation, compute_file_hash, MUTATION_FAMILIES


class TestMutationBuild(unittest.TestCase):
    def test_minimum_15_mutations(self):
        muts, hh = build_mutations()
        self.assertGreaterEqual(len(muts), 15)

    def test_all_unique_names(self):
        muts, _ = build_mutations()
        names = [m.name for m in muts]
        self.assertEqual(len(names), len(set(names)))

    def test_all_have_descriptions(self):
        muts, _ = build_mutations()
        for m in muts:
            self.assertTrue(len(m.description) > 10, f"{m.name} description too short")

    def test_all_target_real_files(self):
        muts, _ = build_mutations()
        for m in muts:
            target = os.path.join(SRC, "qclaw_e43", m.file_path)
            self.assertTrue(os.path.exists(target), f"{m.name} target missing: {target}")

    def test_all_original_texts_found_in_source(self):
        muts, _ = build_mutations()
        for m in muts:
            target = os.path.join(SRC, "qclaw_e43", m.file_path)
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(m.original_text, content,
                          f"{m.name}: original_text not found in {m.file_path}")

    def test_families_cover_e43_requirements(self):
        """Cover: forgery, factory_bypass, utf8_replacement, dropped_structure,
        duplicate_master, silent_overwrite, caller_cognition, skill_direct_formal,
        corpus_drift, evaluator_bypass"""
        muts, _ = build_mutations()
        covered = {m.family for m in muts}
        required = {"forgery", "factory_bypass", "utf8_replacement", "dropped_structure",
                    "duplicate_master", "silent_overwrite", "caller_cognition_certain",
                    "skill_direct_formal", "corpus_drift", "evaluator_bypass"}
        missing = required - covered
        self.assertFalse(missing, f"Missing mutation families: {missing}")

    def test_harness_hash_stable(self):
        muts1, h1 = build_mutations()
        muts2, h2 = build_mutations()
        self.assertEqual(h1, h2)

    def test_original_mutant_different(self):
        muts, _ = build_mutations()
        for m in muts:
            self.assertNotEqual(m.original_text, m.mutant_text,
                                f"{m.name}: original == mutant!")

    def test_mutation_apply_restore_roundtrip(self):
        """Test apply→verify→restore→verify on a temp copy of a source file."""
        muts, _ = build_mutations()
        # Use the first mutation that targets an existing file
        m = muts[0]
        target = os.path.join(SRC, "qclaw_e43", m.file_path)
        original = open(target, "r", encoding="utf-8").read()
        orig_hash = compute_file_hash(target)

        # Apply
        modified = original.replace(m.original_text, m.mutant_text, 1)
        self.assertIn(m.mutant_text, modified)
        self.assertNotIn(m.original_text, modified)  # only one occurrence

        # Restore
        restored = modified.replace(m.mutant_text, m.original_text, 1)
        self.assertEqual(restored, original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
