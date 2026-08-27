from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import inspect
import unittest

from idle_signal_scheduler import P3, P4, validate_opportunity
from signal_opportunity_materializer_current import materialize_signal_opportunity
from signal_priority_classification import (
    EVIDENCE_SCHEMA,
    POLICY_VERSION,
    PriorityClassificationError,
    derive_trusted_priority_evidence,
    priority_evidence_ref,
)
from tests.test_signal_user_value import FakeObserver, declaration, proposal


SIGNAL = "signal:r155-fixture"
DOMAIN = "SECOND_BRAIN_SYSTEM"


def refs() -> list[str]:
    return [
        f"s0c://signal/{SIGNAL}#reducer=v1;sha256=" + "a" * 64,
        "r154://ranking/" + "b" * 64 + "#policy=R154/v1",
        "r155://user-value/" + "c" * 64 + "#policy=R155/v1",
        "r155://ranking-upgrade/" + "d" * 64 + "#policy=R155/v1",
    ]


def classify(state: str) -> dict:
    return derive_trusted_priority_evidence(
        signal_ref=SIGNAL,
        epistemic_state=state,
        base_opportunity_digest="e" * 64,
        source_evidence_refs=refs(),
    )


def opportunity(*, state: str = "USER_EXPLICIT", priority: str = P3) -> dict:
    value = {
        "schema_version": "DigestedSignalOpportunity/v1",
        "opportunity_id": "r153-opportunity:r156-fixture",
        "signal_ref": SIGNAL,
        "signal_primary_domain": DOMAIN,
        "source_evidence_refs": [
            f"s0c://signal/{SIGNAL}#sha256=" + "a" * 64,
            "r154://ranking/" + "b" * 64 + "#policy=R154/v1",
        ],
        "desired_effect": "Classify research priority only from canonical epistemic state.",
        "problem_to_solve": "R154 defaults every idle opportunity to P3.",
        "success_condition": "Candidate hypotheses are P4 without caller priority authority.",
        "current_disposition": "NEW_DURABLE_SIGNAL",
        "epistemic_state": state,
        "desired_effect_gap_proven": True,
        "dependency_ready": True,
        "priority_class": priority,
        "user_value_score": 50,
        "materiality_score": 50,
        "dependency_readiness_score": 100,
        "age_cycles": 0,
        "estimated_cost_score": 50,
        "task_release_proposal": proposal(),
    }
    return validate_opportunity(value)


def base_decision(*, state: str = "USER_EXPLICIT", priority: str = P3) -> dict:
    opp = opportunity(state=state, priority=priority)
    return {
        "schema_version": "SignalOpportunityMaterializationDecision/v1",
        "signal_ref": SIGNAL,
        "disposition": "MATERIALIZED_FOR_R151",
        "reason": "S0C_OWNER_RECONCILIATION_R145_R154_R150_BOUND",
        "evidence_refs": list(opp["source_evidence_refs"]),
        "owner_binding_digest": "f" * 64,
        "opportunity": opp,
        "authority_boundary": {"creates_task": False},
        "decision_digest": "9" * 64,
    }


def run_current(*, state: str = "USER_EXPLICIT", priority: str = P3) -> dict:
    observer = FakeObserver([declaration("HIGH")])
    with patch(
        "signal_opportunity_materializer_current._materialize_r153",
        return_value=base_decision(state=state, priority=priority),
    ), patch(
        "signal_user_value._make_observer",
        return_value=(observer, RuntimeError),
    ):
        return materialize_signal_opportunity(
            Path(__file__).resolve().parents[3],
            object(),
            {"signal_ref": SIGNAL},
            expected_coordinator_main="1" * 40,
            domain_authority_descriptors=[],
            domain_authority_observations=[],
        )


class TrustedPriorityClassificationTests(unittest.TestCase):
    def test_01_action_capable_epistemic_states_preserve_p3(self) -> None:
        for state in ("USER_EXPLICIT", "CONFIRMED_FACT", "HIGH_CONFIDENCE_INFERENCE"):
            with self.subTest(state=state):
                value = classify(state)
                self.assertEqual(value["schema_version"], EVIDENCE_SCHEMA)
                self.assertEqual(value["policy_version"], POLICY_VERSION)
                self.assertEqual(value["priority_class"], P3)

    def test_02_candidate_hypothesis_deterministically_demotes_to_p4(self) -> None:
        value = classify("CANDIDATE_HYPOTHESIS")
        self.assertEqual(value["priority_class"], P4)
        self.assertEqual(value["reason"], "CANONICAL_CANDIDATE_HYPOTHESIS_REQUIRES_RESEARCH")

    def test_03_unknown_and_needs_revalidation_cannot_become_p4(self) -> None:
        for state in ("UNKNOWN", "NEEDS_REVALIDATION"):
            with self.subTest(state=state):
                with self.assertRaises(PriorityClassificationError) as raised:
                    classify(state)
                self.assertEqual(
                    raised.exception.code,
                    "INELIGIBLE_EPISTEMIC_STATE_MUST_REMAIN_BLOCKED",
                )

    def test_04_unrecognized_epistemic_state_fails_closed(self) -> None:
        with self.assertRaises(PriorityClassificationError) as raised:
            classify("MODEL_SAYS_RESEARCH")
        self.assertEqual(raised.exception.code, "UNRECOGNIZED_EPISTEMIC_STATE")

    def test_05_exact_s0c_and_r155_evidence_are_required(self) -> None:
        base = {
            "signal_ref": SIGNAL,
            "epistemic_state": "CANDIDATE_HYPOTHESIS",
            "base_opportunity_digest": "e" * 64,
        }
        with self.assertRaises(PriorityClassificationError) as no_s0c:
            derive_trusted_priority_evidence(
                **base,
                source_evidence_refs=["r155://ranking-upgrade/" + "d" * 64],
            )
        self.assertEqual(no_s0c.exception.code, "S0C_SIGNAL_PROOF_REQUIRED")
        with self.assertRaises(PriorityClassificationError) as no_r155:
            derive_trusted_priority_evidence(
                **base,
                source_evidence_refs=[f"s0c://signal/{SIGNAL}#proof"],
            )
        self.assertEqual(
            no_r155.exception.code,
            "R155_RANKING_UPGRADE_EVIDENCE_REQUIRED",
        )

    def test_06_no_caller_priority_or_free_text_classifier_input_exists(self) -> None:
        parameters = set(inspect.signature(derive_trusted_priority_evidence).parameters)
        self.assertEqual(
            parameters,
            {"signal_ref", "epistemic_state", "base_opportunity_digest", "source_evidence_refs"},
        )
        with self.assertRaises(TypeError):
            derive_trusted_priority_evidence(
                signal_ref=SIGNAL,
                epistemic_state="USER_EXPLICIT",
                base_opportunity_digest="e" * 64,
                source_evidence_refs=refs(),
                priority_class=P4,  # type: ignore[call-arg]
            )
        with self.assertRaises(TypeError):
            derive_trusted_priority_evidence(
                signal_ref=SIGNAL,
                epistemic_state="USER_EXPLICIT",
                base_opportunity_digest="e" * 64,
                source_evidence_refs=refs(),
                signal_kind="RESEARCH",  # type: ignore[call-arg]
            )

    def test_07_evidence_is_deterministic_digest_bound_and_authority_free(self) -> None:
        first = classify("CANDIDATE_HYPOTHESIS")
        second = classify("CANDIDATE_HYPOTHESIS")
        self.assertEqual(first, second)
        ref = priority_evidence_ref(first)
        self.assertIn(first["evidence_digest"], ref)
        self.assertIn("base=" + "e" * 64, ref)
        self.assertFalse(any(first["authority_boundary"].values()))

    def test_08_current_materializer_preserves_p3_for_user_explicit(self) -> None:
        result = run_current(state="USER_EXPLICIT")
        self.assertEqual(result["disposition"], "MATERIALIZED_FOR_R151")
        self.assertEqual(result["opportunity"]["priority_class"], P3)
        self.assertEqual(result["opportunity"]["user_value_score"], 75)
        refs_text = " ".join(result["opportunity"]["source_evidence_refs"])
        self.assertIn("r155://ranking-upgrade/", refs_text)
        self.assertIn("r156://priority/", refs_text)

    def test_09_current_materializer_demotes_candidate_hypothesis_to_p4(self) -> None:
        result = run_current(state="CANDIDATE_HYPOTHESIS")
        self.assertEqual(result["disposition"], "MATERIALIZED_FOR_R151")
        self.assertEqual(result["opportunity"]["priority_class"], P4)
        self.assertEqual(result["opportunity"]["user_value_score"], 75)
        self.assertEqual(result["reason"], "R153_R154_R155_R156_TRUSTED_PRIORITY_BOUND")

    def test_10_preexisting_p4_cannot_bypass_r154_p3_baseline(self) -> None:
        result = run_current(state="CANDIDATE_HYPOTHESIS", priority=P4)
        self.assertEqual(result["disposition"], "NEEDS_REVALIDATION")
        self.assertEqual(result["reason"], "R156_BASE_PRIORITY_NOT_R154_P3")

    def test_11_r151_priority_ordering_contract_remains_unchanged(self) -> None:
        from idle_signal_scheduler import PRIORITY_ORDER

        self.assertLess(PRIORITY_ORDER[P3], PRIORITY_ORDER[P4])
        self.assertEqual(P3, "P3_BOUNDED_IMPROVEMENT")
        self.assertEqual(P4, "P4_RESEARCH")


if __name__ == "__main__":
    unittest.main()
