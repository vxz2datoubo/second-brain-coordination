"""E42 Q7 — Mutation Harness Tests + Source Module Verification"""
import unittest, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_e42.mutations import (
    build_mutations, Mutation, MutationHarness, compute_sha256,
)


class TestMutations(unittest.TestCase):
    def setUp(self):
        self.mutations = build_mutations()

    def test_minimum_15_mutations(self):
        self.assertGreaterEqual(len(self.mutations), 15,
            f"E42 requires >=15 mutations, got {len(self.mutations)}")

    def test_all_mutations_have_unique_names(self):
        names = [m.name for m in self.mutations]
        self.assertEqual(len(names), len(set(names)))

    def test_all_mutations_have_descriptions(self):
        for m in self.mutations:
            self.assertTrue(m.description, f"Mutation {m.name} missing description")
            self.assertTrue(len(m.description) > 10)

    def test_all_mutations_target_real_files(self):
        src_dir = os.path.join(SRC, "qclaw_e42")
        for m in self.mutations:
            target = os.path.normpath(os.path.join(src_dir, os.path.basename(m.file_path)))
            self.assertTrue(os.path.exists(target),
                f"Mutation {m.name} targets missing file: {target}")

    def test_all_mutations_have_line_numbers(self):
        for m in self.mutations:
            self.assertTrue(len(m.original_lines) > 0,
                f"Mutation {m.name} has no original_lines")
            self.assertEqual(len(m.original_lines), len(m.mutant_lines),
                f"Mutation {m.name}: original/mutant line counts differ")

    def test_mutation_types_cover_e41_blockers(self):
        """Must cover: forgery, strip loss, duplicate master, silent overwrite,
        heuristic conflict, corpus drift, evaluator bypass, missing artifacts, premature receipt"""
        names = {m.name for m in self.mutations}
        required = ["M01_FORGE", "M02_ATOM_FACTORY", "M03_ALLOW_DUPLICATE",
                    "M05_SILENT_OVERWRITE", "M06_HEURISTIC", "M08_GLOBAL",
                    "M10_SKILL_SKIP", "M14_LINK_REGISTRY"]
        for r in required:
            matches = [n for n in names if n.startswith(r)]
            self.assertTrue(matches, f"Missing mutation covering {r}")

    def test_mutation_line_format(self):
        for m in self.mutations:
            for i, ol in enumerate(m.original_lines):
                self.assertIsInstance(ol, int)
                self.assertTrue(ol >= 1, f"Line numbers must be 1-indexed: {m.name} line {ol}")
                self.assertTrue(ol <= 500, f"Line number suspiciously high: {m.name} line {ol}")
            for ml in m.mutant_lines:
                self.assertIsInstance(ml, str)


class TestSourceModulesExist(unittest.TestCase):
    """Verify all production modules are importable."""
    def test_authority_imports(self):
        from qclaw_e42.authority import AtomFactory, EvidenceBundle, Atom, AtomType
        self.assertTrue(True)

    def test_source_trace_imports(self):
        from qclaw_e42.source_trace import SourceDocument, SourceSpan, LinkRegistry
        self.assertTrue(True)

    def test_master_record_imports(self):
        from qclaw_e42.master_record import MasterRecordRegistry, ConflictClass
        self.assertTrue(True)

    def test_cognition_imports(self):
        from qclaw_e42.cognition import CognitionEngine, MemoryZone
        self.assertTrue(True)

    def test_skill_lifecycle_imports(self):
        from qclaw_e42.skill_lifecycle import SkillBuilder, SkillState
        self.assertTrue(True)

    def test_corpus_imports(self):
        from qclaw_e42.corpus import build_corpus, CorpusCaseType
        self.assertTrue(True)

    def test_mutations_imports(self):
        from qclaw_e42.mutations import build_mutations
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
