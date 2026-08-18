from __future__ import annotations

import inspect
from pathlib import Path
import unittest

import yaml

from global_signal_gateway.retrospective_evidence import (
    build_candidate_evidence,
    compare_post_hoc_oracle,
    expand_source_fragment_refs,
)

ROOT = Path(__file__).resolve().parents[1] / "R142"
PACKAGE = ROOT / "REAL-RETROSPECTIVE-PACKAGE.yaml"
PLAN = ROOT / "REAL-RETROSPECTIVE-EVIDENCE-PLAN.yaml"
SOURCE = "file-library://file_00000000d81881fb9108c634c60942bc"


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class F03EvidenceIndependenceTests(unittest.TestCase):
    def test_wrong_oracle_cannot_select_evidence_slot(self):
        signature = inspect.signature(build_candidate_evidence)
        self.assertNotIn("expected", signature.parameters)
        self.assertNotIn("oracle", signature.parameters)
        facts = {
            "FACT": {
                "fact_class": "CURRENT_CAPABILITY_SATISFIED",
                "verified": True,
                "evidence_refs": ["git://exact-main/capability"],
            }
        }
        evidence, derivation = build_candidate_evidence(
            {"fact_ids": ["FACT"]},
            facts,
            provider_ref="provider://r137/evidence/x",
            capability_ref="git://exact-main/gateway",
        )
        self.assertEqual(evidence["satisfied_refs"], ["git://exact-main/capability"])
        self.assertEqual(evidence["current_signal_refs"], [])
        self.assertEqual(derivation["fact_classes"], ["CURRENT_CAPABILITY_SATISFIED"])
        oracle = compare_post_hoc_oracle(
            {"CANDIDATE": "ALREADY_SATISFIED"},
            {
                "label": "INTENTIONALLY_WRONG",
                "legacy_candidate_count": "1",
                "legacy_disposition_counts": {"ALREADY_CANONICAL": 1},
            },
        )
        self.assertFalse(oracle["authoritative"])
        self.assertFalse(oracle["mismatch_is_failure"])
        self.assertFalse(oracle["disposition_counts_match_legacy"])

    def test_unverified_current_fact_fails_closed(self):
        facts = {
            "FACT": {
                "fact_class": "CURRENT_CANONICAL_MATCH",
                "verified": False,
                "evidence_refs": ["git://exact-main/missing-predicate"],
            }
        }
        evidence, derivation = build_candidate_evidence(
            {"fact_ids": ["FACT"]},
            facts,
            provider_ref="provider://r137/evidence/x",
            capability_ref="git://exact-main/gateway",
        )
        self.assertFalse(evidence["desired_effect_unmet"])
        self.assertEqual(evidence["current_signal_refs"], [])
        self.assertEqual(evidence["satisfied_refs"], [])
        self.assertTrue(evidence["needs_revalidation_refs"])
        self.assertEqual(derivation["derivation"], "FAIL_CLOSED_UNVERIFIED_CURRENT_FACT")

    def test_plan_has_no_per_candidate_disposition_inputs(self):
        plan = load(PLAN)
        policy = plan["evidence_derivation_policy"]
        self.assertFalse(policy["expected_oracle_authoritative"])
        self.assertFalse(policy["expected_oracle_used_for_fact_selection"])
        self.assertFalse(policy["expected_oracle_used_for_evidence_slot_selection"])
        self.assertFalse(policy["oracle_mismatch_is_failure"])
        for binding in plan["candidate_fact_bindings"].values():
            self.assertEqual(set(binding), {"fact_ids"})
        self.assertEqual(plan["post_hoc_oracle"]["legacy_candidate_count"], "48")
        self.assertFalse(plan["post_hoc_oracle"]["authoritative"])

    def test_f04_reextraction_preserves_actual_51_atom_set(self):
        package = load(PACKAGE)
        self.assertEqual(package["package_metadata"]["reconstructed_candidate_count"], 51)
        self.assertEqual(len(package["candidates"]), 51)
        ids = {item["candidate_id"] for item in package["candidates"]}
        self.assertIn("ST-H2-SIGNAL-PLANE-POINTER-STATE-ONLY", ids)
        self.assertIn("ST-L5-AI-FILM-REVISION-SERIES-FINAL-DELTA", ids)
        self.assertIn("ST-L6-AI-FILM-REAL-OUTPUT-LEARNING", ids)
        self.assertNotEqual(len(ids), 48)

    def test_k_source_sections_match_genuine_handoff(self):
        package = load(PACKAGE)
        by_id = {item["candidate_id"]: item for item in package["candidates"]}
        expected = {
            "ST-K1-RECONCILIATION-RECEIPT-FRESHNESS-INVALIDATION": "fragment:K3",
            "ST-K2-IDEMPOTENT-INGESTION-COLLISION-FAIL-CLOSED": "fragment:K4",
            "ST-K3-SEMANTIC-FALSE-MERGE-PROTECTION": "fragment:K5",
            "ST-K4-FLOOD-BACKPRESSURE-COMPACTION": "fragment:K6",
            "ST-K5-AGING-STARVATION-VISIBILITY": "fragment:K7",
            "ST-K6-EXPLAINABLE-PRIORITY-VECTOR": "fragment:K8",
            "ST-K7-NO-MEGA-AGENT-AUTHORITY-COLLAPSE": "fragment:K9",
            "ST-K8-NEGATIVE-CROSS-DOMAIN-TRANSFER-VALIDATION": "fragment:K10",
            "ST-K9-REVERSIBILITY-COMPENSATION-SEMANTICS": "fragment:K12",
            "ST-K10-REUSE-TRACE-AUDIT-TRUTH": "fragment:K13",
            "ST-K11-PRE-POST-WORK-RECONCILIATION": "fragment:K14",
            "ST-K12-CRASH-RECOVERY-REDUCER-REPLAY": "fragment:K15",
        }
        for candidate_id, source_ref in expected.items():
            self.assertEqual(by_id[candidate_id]["source_message_ref"], source_ref)
        self.assertEqual(by_id["ST-K4-FLOOD-BACKPRESSURE-COMPACTION"]["source_message_ref"], "fragment:K6")
        self.assertEqual(by_id["ST-K12-CRASH-RECOVERY-REDUCER-REPLAY"]["source_message_ref"], "fragment:K15")

    def test_dedup_and_artifact_level_provenance_are_truthful(self):
        raw = load(PACKAGE)
        expanded = expand_source_fragment_refs(raw)
        by_id = {item["candidate_id"]: item for item in expanded["candidates"]}
        self.assertIn(SOURCE + "#K1", by_id["ST-F1-CROSS-WINDOW-STATE-DRIFT"]["evidence_refs"])
        self.assertIn(SOURCE + "#F3", by_id["ST-F2-EXACT-HEAD-STALE-REVIEW-DETECTION"]["evidence_refs"])
        self.assertIn(SOURCE + "#K11", by_id["ST-B3-PUBLIC-SAFE-CONTENT-CONTROL-SEPARATION"]["evidence_refs"])
        self.assertEqual(by_id["ST-H2-W3-CONTINUITY-RETRIEVAL-BY-REF"]["source_message_ref"], SOURCE + "#H3")
        self.assertEqual(by_id["ST-FINAL2-REVERSIBLE-CHANGESET-BINDING"]["source_message_ref"], SOURCE)

    def test_no_invented_historical_fragment_ids(self):
        package = load(PACKAGE)
        allowed = {
            *(f"fragment:A{i}" for i in range(1, 5)),
            *(f"fragment:B{i}" for i in range(1, 5)),
            *(f"fragment:C{i}" for i in range(1, 5)),
            *(f"fragment:D{i}" for i in range(1, 5)),
            *(f"fragment:E{i}" for i in range(1, 4)),
            "fragment:F1", "fragment:F3", "fragment:G1",
            "fragment:H1", "fragment:H2", "fragment:H3",
            "fragment:I1", "fragment:I2",
            *(f"fragment:K{i}" for i in range(1, 16)),
            *(f"fragment:L{i}" for i in range(1, 7)),
            "fragment:M", "artifact",
        }
        for candidate in package["candidates"]:
            refs = [candidate["source_message_ref"], candidate["original_intent_ref"], *candidate["evidence_refs"]]
            self.assertTrue(set(refs) <= allowed, (candidate["candidate_id"], refs))


if __name__ == "__main__":
    unittest.main()
