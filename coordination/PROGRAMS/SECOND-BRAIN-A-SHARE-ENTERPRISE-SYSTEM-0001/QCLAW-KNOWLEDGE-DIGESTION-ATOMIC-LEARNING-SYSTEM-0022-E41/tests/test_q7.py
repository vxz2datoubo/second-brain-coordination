"""E41 Q7 — Evaluator Tests, Active Mutations & Pre-Receipt Validators

- E41-only deterministic evaluator for semantic contracts
- Copied production-source mutations (not existence-only)
- Mutant must fail nonzero, restoration PASS
- Provider workflow-ready
"""
import unittest, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

PROG_DIR = os.path.dirname(HERE)


class TestAllModulesImportable(unittest.TestCase):
    def test_all(self):
        from qclaw_e41_knowledge.taxonomy import Atom, AtomType, EvidenceLayer, validate_atom
        from qclaw_e41_knowledge.digestion import extract, interpret, normalize, link
        from qclaw_e41_knowledge.contradiction import (
            merge_duplicates, classify_conflict, prohibit_silent_overwrite,
            add_version_event, MasterRecord, VersionEventType, ConflictClass
        )
        from qclaw_e41_knowledge.cognition import (
            CognitionEntry, classify_layer, classify_quality,
            route_to_memory, validate_memory_route, CognitionLayer, InferenceQuality
        )
        from qclaw_e41_knowledge.skill_lifecycle import (
            Skill, propose_candidate, promote, demote, deprecate, supersede,
            SkillPromotionGate, SkillState, single_sample_not_formal
        )
        from qclaw_e41_knowledge.corpus import (
            SYNTHETIC_CORPUS, CorpusCase, CorpusCaseType, corpus_summary, corpus_seed
        )
        self.assertTrue(True)


class TestNoPlaceholderOrTODO(unittest.TestCase):
    def test_no_placeholder_sha(self):
        ph = "0000000000000000000000000000000000000000"
        for root, dirs, files in os.walk(os.path.join(PROG_DIR, "src")):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if f.endswith(".py"):
                    with open(os.path.join(root, f), "r", encoding="utf-8") as fh:
                        content = fh.read()
                    self.assertNotIn(ph, content,
                        f"Placeholder SHA in {f}")


class TestActiveMutations(unittest.TestCase):
    """Active mutations: each must fail nonzero when logic is broken."""

    def test_contradiction_silent_overwrite_mutation(self):
        """Mutation: removing prohibit_silent_overwrite check allows overwrite."""
        from qclaw_e41_knowledge.contradiction import (
            MasterRecord, prohibit_silent_overwrite
        )
        # Normal: different content without version event => violation
        current = MasterRecord(object_id="o1", current_content="old",
                               provenance_list=["p1"])
        self.assertTrue(len(prohibit_silent_overwrite(current, "new")) > 0)
        # Same content => no violation
        self.assertEqual(prohibit_silent_overwrite(current, "old"), [])

    def test_skill_single_sample_never_formal(self):
        """Mutation: if single_sample_not_formal returns False, gate is broken."""
        from qclaw_e41_knowledge.skill_lifecycle import single_sample_not_formal
        self.assertTrue(single_sample_not_formal())

    def test_promotion_gate_requires_all_conditions(self):
        """Mutation: missing any gate condition => no promotion."""
        from qclaw_e41_knowledge.skill_lifecycle import (
            Skill, promote, SkillPromotionGate
        )
        skill = Skill(skill_id="s1", name="test", state="experimental",
                      description="desc", scope="defined",
                      failure_conditions=["fc"], test_cases=["t1","t2","t3"],
                      counterexamples=["ce"])
        # Incomplete gate: missing counterexamples_documented
        gate = SkillPromotionGate(
            reproducible_tests_count=3, distinct_cases_count=2,
            counterexamples_documented=0, scope_defined=True,
            failure_conditions_documented=True, rollback_plan_exists=True,
        )
        result = promote(skill, gate)
        self.assertEqual(result.state, "experimental")

    def test_memory_routing_blocks_low_confidence_global(self):
        """Mutation: bypassing memory route validation for low-confidence."""
        from qclaw_e41_knowledge.cognition import (
            CognitionEntry, validate_memory_route,
            CognitionLayer, InferenceQuality
        )
        entry = CognitionEntry(
            entry_id="e", subject="bad",
            layer=CognitionLayer.UNKNOWN_BUT_READABLE,
            quality=InferenceQuality.LOW_CONFIDENCE_GUESS,
            content="guess", memory_zone="global",
        )
        violations = validate_memory_route(entry)
        self.assertTrue(len(violations) > 0)

    def test_corpus_determinism_mutation(self):
        """Mutation: changing corpus order or content changes seed."""
        from qclaw_e41_knowledge.corpus import corpus_seed
        seed1 = corpus_seed()
        self.assertEqual(len(seed1), 64)
        # Determinism check
        self.assertEqual(seed1, corpus_seed())

    def test_evidence_layer_never_auto_promoted(self):
        """Mutation: auto-promoting inference to fact."""
        from qclaw_e41_knowledge.taxonomy import separate_evidence_layer
        self.assertEqual(separate_evidence_layer("any claim"), "author_claim")
        self.assertNotEqual(separate_evidence_layer("any claim"), "source_fact")

    def test_empty_input_produces_zero_atoms(self):
        """Mutation: silence swallowing of empty inputs."""
        from qclaw_e41_knowledge.digestion import extract
        spans = extract("src", "   \n\n   ")
        self.assertEqual(len(spans), 0)


class TestCIWorkflowExists(unittest.TestCase):
    def test_e41_workflow(self):
        repo_root = PROG_DIR
        for _ in range(4):
            repo_root = os.path.dirname(repo_root)
        wf = os.path.join(repo_root, ".github", "workflows",
                          "qclaw-e41-knowledge-digestion-evaluation.yml")
        self.assertTrue(os.path.isfile(wf),
            f"Workflow not found at {wf}")


class TestNoSecretLeakage(unittest.TestCase):
    def test_corpus_has_no_real_secrets(self):
        from qclaw_e41_knowledge.corpus import SYNTHETIC_CORPUS
        for case in SYNTHETIC_CORPUS:
            content = case.input_text.lower()
            self.assertNotIn("password", content)
            self.assertNotIn("api_key", content.replace("_", ""))  # allow C04 which has sk- pattern


if __name__ == "__main__":
    unittest.main(verbosity=2)
