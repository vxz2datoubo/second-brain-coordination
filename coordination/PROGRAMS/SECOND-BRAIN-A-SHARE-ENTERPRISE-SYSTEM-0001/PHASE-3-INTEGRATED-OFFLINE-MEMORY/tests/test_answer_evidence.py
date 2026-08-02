from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PHASE_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ROOT = PHASE_ROOT.parent
for source_root in (
    PHASE_ROOT / "src",
    PROGRAM_ROOT / "PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION" / "src",
    PROGRAM_ROOT / "PHASE-2-OFFLINE-VERTICAL-SLICE" / "src",
):
    sys.path.insert(0, str(source_root))

from integrated_offline_memory.answer_evidence import AnswerEvidenceCompiler
from integrated_offline_memory.canonical import atom_id
from integrated_offline_memory.learning_packet import build_learning_packet
from integrated_offline_memory.memory_store import MemoryStore
from integrated_offline_memory.retrieval import ContextAssembler, QueryPlan
from integrated_offline_memory.schema_validation import validate_schema_subset
from integrated_offline_memory.security import CredentialValueDenied


def atom(statement: str, *, scope: str = "evidence", **extra):
    value = {"atom_type": "fact", "statement": statement, "scope": scope, "confidence": 0.8}
    value.update(extra)
    return value


def packet(atoms, *, relations=None, conflicts=None, unknowns=None, source_hash="e" * 64):
    return build_learning_packet(
        source_manifest_ids=["manifest-evidence"],
        source_hash=source_hash,
        validation_report={"status": "SYNTHETIC_TEST", "research_only": True},
        evidence_refs=["manifest:manifest-evidence", "evidence:synthetic"],
        atoms=atoms,
        relations=relations or [],
        conflicts=conflicts or [],
        unknowns=unknowns or [],
    )


class AnswerEvidenceTestCase(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore().connect()
        self.addCleanup(self.store.close)
        self.compiler = AnswerEvidenceCompiler(self.store)

    def test_350_direct_match_reason_is_explicit(self):
        self.store.import_learning_packet(packet([atom("direct evidence phrase")]))
        result = self.compiler.compile(QueryPlan(query_text="direct evidence"))
        self.assertEqual(result.selected_evidence[0]["selection_reason"], "DIRECT_QUERY_MATCH")

    def test_351_bundle_is_deterministic_in_same_snapshot(self):
        self.store.import_learning_packet(packet([atom("deterministic evidence")]))
        plan = QueryPlan(query_text="deterministic")
        self.assertEqual(self.compiler.compile(plan).semantic_hash, self.compiler.compile(plan).semantic_hash)

    def test_352_bundle_hash_excludes_wall_clock_metadata(self):
        value = packet([atom("cross store deterministic")])
        first = self.store.import_learning_packet(value)
        first_hash = self.compiler.compile(QueryPlan(query_text="cross store")).semantic_hash
        other = MemoryStore().connect()
        self.addCleanup(other.close)
        second = other.import_learning_packet(value)
        second_hash = AnswerEvidenceCompiler(other).compile(QueryPlan(query_text="cross store")).semantic_hash
        self.assertEqual(first["revision_id"], second["revision_id"])
        self.assertEqual(first_hash, second_hash)

    def test_353_empty_result_abstains(self):
        result = self.compiler.compile(QueryPlan(query_text="absent"))
        self.assertTrue(result.abstained)
        self.assertIn("NO_RETRIEVABLE_EVIDENCE", result.abstention_reasons)

    def test_354_missing_lineage_abstains(self):
        value = packet([atom("lineage absent")])["atoms"][0]
        value["source_refs"] = []
        self.store.insert_atom(value)
        result = self.compiler.compile(QueryPlan(query_text="lineage absent"))
        self.assertIn("SOURCE_LINEAGE_MISSING", result.abstention_reasons)

    def test_355_only_unverified_unknown_evidence_abstains(self):
        self.store.import_learning_packet(packet([atom(
            "unknown evidence", verification_status="UNVERIFIED", evidence_quality="UNKNOWN",
        )]))
        result = self.compiler.compile(QueryPlan(query_text="unknown evidence"))
        self.assertIn("ONLY_UNVERIFIED_UNKNOWN_EVIDENCE", result.abstention_reasons)

    def test_356_verified_candidate_does_not_abstain(self):
        self.store.import_learning_packet(packet([atom("supported candidate")]))
        self.assertFalse(self.compiler.compile(QueryPlan(query_text="supported candidate")).abstained)

    def test_357_conflict_counterpart_is_included(self):
        left = atom_id("alpha thesis", "fact", "evidence")
        right = atom_id("omega negation", "fact", "evidence")
        self.store.import_learning_packet(packet(
            [atom("alpha thesis", id=left), atom("omega negation", id=right)],
            conflicts=[{"atom_id_a": left, "atom_id_b": right}],
        ))
        result = self.compiler.compile(QueryPlan(query_text="alpha thesis", include_conflicts=True))
        self.assertEqual({item["atom_id"] for item in result.selected_evidence}, {left, right})
        reasons = {item["atom_id"]: item["selection_reason"] for item in result.selected_evidence}
        self.assertEqual(reasons[right], "CONFLICT_COUNTERPART")

    def test_358_conflict_sets_uncertainty(self):
        left = atom_id("left conflict", "fact", "evidence")
        right = atom_id("right conflict", "fact", "evidence")
        self.store.import_learning_packet(packet(
            [atom("left conflict", id=left), atom("right conflict", id=right)],
            conflicts=[{"atom_id_a": left, "atom_id_b": right}],
        ))
        result = self.compiler.compile(QueryPlan(query_text="left conflict"))
        self.assertIn("UNRESOLVED_CONFLICT_PRESENT", result.uncertainty_reasons)

    def test_359_open_unknown_sets_uncertainty(self):
        value = packet([atom("known premise")])
        atom_key = value["atoms"][0]["id"]
        value = packet(
            [atom("known premise", id=atom_key)],
            unknowns=[{"question": "unresolved unit", "related_atom_ids": [atom_key]}],
        )
        self.store.import_learning_packet(value)
        result = self.compiler.compile(QueryPlan(query_text="known premise"))
        self.assertIn("OPEN_UNKNOWN_PRESENT", result.uncertainty_reasons)

    def test_360_budget_omission_has_reason(self):
        self.store.import_learning_packet(packet([atom("budget common one"), atom("budget common two")]))
        result = self.compiler.compile(QueryPlan(query_text="budget common", budget=1))
        self.assertEqual(result.omitted_evidence[0]["reason"], "CONTEXT_BUDGET_EXCEEDED")
        self.assertIn("CONTEXT_BUDGET_OMISSION", result.uncertainty_reasons)

    def test_361_exceptions_and_failure_conditions_are_preserved(self):
        self.store.import_learning_packet(packet([atom(
            "conditional evidence", exceptions=["except_x"], failure_conditions=["fails_y"],
        )]))
        result = self.compiler.compile(QueryPlan(query_text="conditional evidence"))
        selected = result.selected_evidence[0]["atom"]
        self.assertEqual((selected["exceptions"], selected["failure_conditions"]), (["except_x"], ["fails_y"]))
        self.assertIn("CONDITIONAL_EVIDENCE_PRESENT", result.uncertainty_reasons)

    def test_362_current_mode_excludes_superseded(self):
        old = atom_id("old state", "fact", "evidence")
        new = atom_id("new state", "fact", "evidence")
        self.store.import_learning_packet(packet(
            [atom("old state", id=old), atom("new state", id=new)],
            relations=[{"source_atom_id": new, "target_atom_id": old, "relation_type": "supersedes"}],
        ))
        result = self.compiler.compile(QueryPlan(query_text="old state"))
        self.assertNotIn(old, {item["atom_id"] for item in result.selected_evidence})

    def test_363_history_mode_can_include_superseded(self):
        old = atom_id("historical state", "fact", "evidence")
        new = atom_id("current state", "fact", "evidence")
        self.store.import_learning_packet(packet(
            [atom("historical state", id=old), atom("current state", id=new)],
            relations=[{"source_atom_id": new, "target_atom_id": old, "relation_type": "supersedes"}],
        ))
        plan = QueryPlan(
            query_text="historical state",
            truth_states=("candidate", "approved", "conflict", "unknown", "superseded"),
            history_mode="HISTORY",
        )
        result = self.compiler.compile(plan)
        self.assertIn(old, {item["atom_id"] for item in result.selected_evidence})
        self.assertEqual(result.history_mode, "HISTORY")

    def test_364_context_from_another_plan_is_rejected(self):
        context = ContextAssembler(self.store).assemble(QueryPlan(query_text="first"))
        with self.assertRaisesRegex(ValueError, "query_plan_mismatch"):
            self.compiler.compile(QueryPlan(query_text="second"), context)

    def test_365_credential_shaped_query_is_denied_without_echo(self):
        query = "ghp_" + "A" * 32
        with self.assertRaises(CredentialValueDenied):
            self.compiler.compile(QueryPlan(query_text=query))

    def test_366_bundle_cannot_write_authority_or_trade(self):
        result = self.compiler.compile(QueryPlan(query_text="none"))
        self.assertEqual((result.authority_write, result.no_trade_gate), (False, True))

    def test_367_source_lineage_is_explicit(self):
        self.store.import_learning_packet(packet([atom("lineage evidence")]))
        result = self.compiler.compile(QueryPlan(query_text="lineage evidence"))
        self.assertIn("manifest:manifest-evidence", result.source_lineage)

    def test_368_relation_expansion_has_related_reason(self):
        alpha = atom_id("alpha relation", "fact", "evidence")
        beta = atom_id("beta neighbor", "fact", "evidence")
        self.store.import_learning_packet(packet(
            [atom("alpha relation", id=alpha), atom("beta neighbor", id=beta)],
            relations=[{"source_atom_id": alpha, "target_atom_id": beta, "relation_type": "supports"}],
        ))
        result = self.compiler.compile(QueryPlan(query_text="alpha relation", relation_depth=1))
        reasons = {item["atom_id"]: item["selection_reason"] for item in result.selected_evidence}
        self.assertEqual(reasons[beta], "RELATED_CONTEXT")

    def test_369_empty_query_uses_structured_filter_reason(self):
        self.store.import_learning_packet(packet([atom("scope only", scope="selected-scope")]))
        result = self.compiler.compile(QueryPlan(query_text="", scopes=("selected-scope",)))
        self.assertEqual(result.selected_evidence[0]["selection_reason"], "STRUCTURED_FILTER_MATCH")

    def test_370_schema_validates(self):
        self.store.import_learning_packet(packet([atom("schema evidence")]))
        result = self.compiler.compile(QueryPlan(query_text="schema evidence"))
        schema = json.loads((PHASE_ROOT / "schemas" / "AnswerEvidenceBundle.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, result.to_dict())

    def test_371_selected_evidence_carries_full_candidate_atom(self):
        self.store.import_learning_packet(packet([atom("full candidate atom", premises=["premise-a"])]))
        result = self.compiler.compile(QueryPlan(query_text="full candidate atom"))
        self.assertEqual(result.selected_evidence[0]["atom"]["premises"], ["premise-a"])

    def test_372_conflict_expansion_can_be_disabled(self):
        left = atom_id("cobalt premise", "fact", "evidence")
        right = atom_id("magenta rebuttal", "fact", "evidence")
        self.store.import_learning_packet(packet(
            [atom("cobalt premise", id=left), atom("magenta rebuttal", id=right)],
            conflicts=[{"atom_id_a": left, "atom_id_b": right}],
        ))
        result = self.compiler.compile(QueryPlan(query_text="cobalt premise", include_conflicts=False))
        self.assertEqual([item["atom_id"] for item in result.selected_evidence], [left])
        self.assertEqual(result.conflicts, ())

    def test_373_unknown_reporting_can_be_disabled(self):
        value = packet([atom("known without unknown")])
        atom_key = value["atoms"][0]["id"]
        self.store.import_learning_packet(packet(
            [atom("known without unknown", id=atom_key)],
            unknowns=[{"question": "hidden by explicit plan", "related_atom_ids": [atom_key]}],
        ))
        result = self.compiler.compile(QueryPlan(query_text="known without unknown", include_unknowns=False))
        self.assertEqual(result.unknowns, ())


if __name__ == "__main__":
    unittest.main()
