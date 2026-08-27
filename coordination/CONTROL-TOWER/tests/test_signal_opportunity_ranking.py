from __future__ import annotations

import copy
import unittest

from signal_opportunity_ranking import (
    MAX_AGE_CYCLES,
    POLICY_VERSION,
    RANKING_SCHEMA,
    RankingEvidenceError,
    derive_trusted_ranking_evidence,
    ranking_evidence_ref,
)
from tests.test_signal_opportunity_materializer import SIGNAL, proposal


PROOF = (
    f"s0c://signal/{SIGNAL}#reducer=S0C/v1;watermark=1;"
    f"input_revision=1;sha256={'a' * 64}"
)


def rank(**overrides):
    values = {
        "signal_ref": SIGNAL,
        "signal_proof_ref": PROOF,
        "signal_kind": "REQUIREMENT",
        "materiality_class": "MATERIAL",
        "origin_ledger_offset": 1,
        "ledger_watermark": 1,
        "dependency_ready": True,
        "task_release_proposal": proposal(),
        "source_evidence_refs": ["owner-reconcile://fixture"],
    }
    values.update(overrides)
    return derive_trusted_ranking_evidence(**values)


class TrustedSignalOpportunityRankingTests(unittest.TestCase):
    def test_01_standard_r153_fixture_preserves_accepted_neutral_vector(self) -> None:
        value = rank()
        self.assertEqual(value["schema_version"], RANKING_SCHEMA)
        self.assertEqual(value["policy_version"], POLICY_VERSION)
        self.assertEqual(
            value["rank_vector"],
            {
                "priority_class": "P3_BOUNDED_IMPROVEMENT",
                "user_value_score": 50,
                "materiality_score": 50,
                "dependency_readiness_score": 100,
                "age_cycles": 0,
                "estimated_cost_score": 50,
            },
        )

    def test_02_caller_style_score_fields_do_not_exist_on_r154_input(self) -> None:
        with self.assertRaises(TypeError):
            rank(user_value_score=100)
        with self.assertRaises(TypeError):
            rank(estimated_cost_score=0)

    def test_03_free_text_urgency_words_do_not_change_rank(self) -> None:
        plain = proposal()
        loud = copy.deepcopy(plain)
        loud["desired_effect"] = "URGENT CRITICAL HIGH VALUE " + loud["desired_effect"]
        loud["risk"] = ["urgent critical high value"]
        first = rank(task_release_proposal=plain)
        second = rank(task_release_proposal=loud)
        self.assertEqual(first["rank_vector"], second["rank_vector"])
        self.assertEqual(first["ranking_digest"], second["ranking_digest"])

    def test_04_materiality_is_canonical_mapping_or_fail_closed(self) -> None:
        self.assertEqual(rank(materiality_class="LOW")["rank_vector"]["materiality_score"], 25)
        self.assertEqual(rank(materiality_class=None)["rank_vector"]["materiality_score"], 50)
        with self.assertRaises(RankingEvidenceError) as high:
            rank(materiality_class="HIGH_RISK")
        self.assertEqual(high.exception.code, "HIGH_RISK_SIGNAL_NOT_IDLE_RANKABLE")
        with self.assertRaises(RankingEvidenceError) as invalid:
            rank(materiality_class="VERY_IMPORTANT")
        self.assertEqual(invalid.exception.code, "CANONICAL_MATERIALITY_UNRECOGNIZED")

    def test_05_age_comes_only_from_canonical_positions_and_is_capped(self) -> None:
        value = rank(origin_ledger_offset=2, ledger_watermark=100)
        self.assertEqual(value["rank_vector"]["age_cycles"], MAX_AGE_CYCLES)
        provenance = value["feature_provenance"]["age_cycles"]
        self.assertEqual(provenance["origin_ledger_offset"], 2)
        self.assertEqual(provenance["ledger_watermark"], 100)
        with self.assertRaises(RankingEvidenceError):
            rank(origin_ledger_offset=3, ledger_watermark=2)

    def test_06_change_surface_cost_proxy_is_monotonic_and_capped(self) -> None:
        small = proposal()
        small["proposed_write_surface"] = {
            "write_paths": [],
            "read_paths": [],
            "interfaces": [],
            "read_domains": [],
            "write_domains": [],
            "authority_claims": [],
        }
        medium = copy.deepcopy(small)
        medium["proposed_write_surface"]["write_paths"] = ["a.py"]
        large = copy.deepcopy(medium)
        large["proposed_write_surface"]["authority_claims"] = [f"authority-{i}" for i in range(10)]
        a = rank(task_release_proposal=small)["rank_vector"]["estimated_cost_score"]
        b = rank(task_release_proposal=medium)["rank_vector"]["estimated_cost_score"]
        c = rank(task_release_proposal=large)["rank_vector"]["estimated_cost_score"]
        self.assertLess(a, b)
        self.assertLess(b, c)
        self.assertEqual(c, 100)

    def test_07_unknown_user_value_remains_neutral_not_fabricated(self) -> None:
        value = rank()
        self.assertEqual(value["rank_vector"]["user_value_score"], 50)
        self.assertIn("NO_CANONICAL_USER_VALUE_AUTHORITY", value["feature_provenance"]["user_value_score"]["reason"])

    def test_08_same_trusted_inputs_are_deterministic(self) -> None:
        self.assertEqual(rank(), rank())

    def test_09_ranking_receipt_grants_no_authority(self) -> None:
        value = rank()
        self.assertTrue(value["authority_boundary"])
        self.assertFalse(any(value["authority_boundary"].values()))

    def test_10_proof_must_bind_exact_signal(self) -> None:
        with self.assertRaises(RankingEvidenceError) as raised:
            rank(signal_proof_ref="s0c://signal/other#sha256=x")
        self.assertEqual(raised.exception.code, "S0C_SIGNAL_PROOF_BINDING_INVALID")

    def test_11_reference_is_digest_and_policy_bound(self) -> None:
        value = rank()
        ref = ranking_evidence_ref(value)
        self.assertIn(value["ranking_digest"], ref)
        self.assertIn(POLICY_VERSION, ref)


if __name__ == "__main__":
    unittest.main()
