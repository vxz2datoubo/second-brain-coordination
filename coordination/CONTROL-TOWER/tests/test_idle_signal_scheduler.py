from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from idle_signal_scheduler import (
    AUTHORIZATION_SCHEMA,
    DECISION_SCHEMA,
    OPPORTUNITY_SCHEMA,
    P0,
    P1,
    P2,
    P3,
    P4,
    PRIORITY_OBSERVATION_SCHEMA,
    IdleSignalSchedulerError,
    MATERIALIZATION_REQUEST_SCHEMA,
    MATERIALIZER_DECISION_SCHEMA,
    _digest,
    _trusted_review_queue_blockers,
    evaluate_idle_signal_startup,
    materialize_trusted_opportunity_batch,
    validate_opportunity,
)
from trusted_task_release import TRUSTED_RECEIPT_SCHEMA, TrustedReleaseError


REPO_ROOT = Path(__file__).resolve().parents[3]


def head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def proposal(signal_ref: str = "signal:r151-fixture") -> dict:
    return {
        "schema_version": "TaskReleaseProposal/v1",
        "release_candidate_id": "R151-FIXTURE",
        "source_signal_refs": [signal_ref, "issue://461"],
        "signal_primary_domain": "SHARED_COGNITIVE_OS",
        "desired_effect": "Advance one bounded idle Signal opportunity through governed engineering.",
        "proposed_target_domain": "SHARED_COGNITIVE_OS",
        "proposed_write_surface": {
            "write_paths": ["coordination/CONTROL-TOWER/idle_signal_scheduler.py"],
            "read_paths": [
                "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
                "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml",
            ],
            "interfaces": [
                {"name": "TrustedTaskReleaseImpactReceipt", "mode": "read", "frozen": True}
            ],
            "read_domains": ["SHARED_COGNITIVE_OS"],
            "write_domains": ["SHARED_COGNITIVE_OS"],
            "authority_claims": [],
        },
        "materiality": "MATERIAL",
        "risk": ["bounded reversible engineering"],
        "out_of_scope": ["production deployment", "secrets", "trading"],
        "capability_inventory": [
            {
                "component_id": "R149R150TaskReleaseChain",
                "decision": "EXTEND",
                "satisfies_requirement": False,
                "evidence_refs": ["pr://452", "pr://455"],
            }
        ],
        "relations": [
            {
                "relation": "EXTENDS",
                "source": "IdleSignalOpportunityScheduler",
                "target": "R150TrustedTaskRelease",
                "evidence_refs": ["issue://461"],
            }
        ],
        "reverse_consumers": [
            {
                "consumer_id": "startup_task_selection",
                "impact": "CONSUMER_REVALIDATION_ONLY",
                "evidence_refs": ["issue://461"],
            }
        ],
        "consumer_inventory_complete": True,
        "composition": {
            "optional": True,
            "can_compose": True,
            "core_invariant": False,
            "missing_capability_behavior": "ABSTAIN",
            "removal_preserves_unrelated_core": True,
            "justification": "Idle scheduling composes around retained R149/R150 release gates.",
        },
        "synchronized_change_set": [],
        "regression_revalidation_set": ["startup_task_selection"],
        "unaffected_set": [
            {
                "component_id": "SignalTowerDurableTruth",
                "evidence_refs": ["boundary://signal-does-not-self-authorize"],
            }
        ],
        "unresolved_unknowns": [],
    }


def opportunity(
    opportunity_id: str = "OPP-001",
    *,
    signal_ref: str = "signal:r151-fixture",
    priority: str = P3,
    user_value: int = 80,
    materiality: int = 70,
    readiness: int = 90,
    age: int = 0,
    cost: int = 20,
    disposition: str = "NEW_DURABLE_SIGNAL",
    epistemic: str = "USER_EXPLICIT",
    dependency_ready: bool = True,
    desired_effect_gap: bool = True,
    release_proposal: dict | None = None,
) -> dict:
    p = copy.deepcopy(release_proposal or proposal(signal_ref))
    p["source_signal_refs"] = [signal_ref, "issue://461"]
    p["signal_primary_domain"] = "SHARED_COGNITIVE_OS"
    p["desired_effect"] = (
        "Advance one bounded idle Signal opportunity through governed engineering."
    )
    return {
        "schema_version": OPPORTUNITY_SCHEMA,
        "opportunity_id": opportunity_id,
        "signal_ref": signal_ref,
        "signal_primary_domain": "SHARED_COGNITIVE_OS",
        "source_evidence_refs": [signal_ref, "issue://461"],
        "desired_effect": p["desired_effect"],
        "problem_to_solve": "Useful Signal opportunities otherwise remain dormant indefinitely.",
        "success_condition": "One safe bounded task is selected only when higher-priority work is absent.",
        "current_disposition": disposition,
        "epistemic_state": epistemic,
        "desired_effect_gap_proven": desired_effect_gap,
        "dependency_ready": dependency_ready,
        "priority_class": priority,
        "user_value_score": user_value,
        "materiality_score": materiality,
        "dependency_readiness_score": readiness,
        "age_cycles": age,
        "estimated_cost_score": cost,
        "task_release_proposal": p,
    }


def priority_observation(*items: dict) -> dict:
    return {
        "schema_version": PRIORITY_OBSERVATION_SCHEMA,
        "observation_id": "startup-hints-r151-test",
        "evidence_refs": ["invocation://current-user-context"],
        "items": list(items),
    }


def priority_item(priority: str) -> dict:
    return {
        "priority": priority,
        "work_ref": f"work://{priority}",
        "reason": "synthetic additive priority fixture",
        "evidence_refs": [f"fixture://{priority}"],
    }


def r150_receipt(current_head: str, disposition: str = "RELEASE_AS_EXTENSION") -> dict:
    return {
        "schema_version": TRUSTED_RECEIPT_SCHEMA,
        "release_candidate_id": "R151-FIXTURE",
        "trusted_context": {
            "canonical_main": current_head,
            "domain_guard": {"eligible_for_normal_release_gates": True},
        },
        "impact_receipt": {"final_disposition": disposition},
        "authority_boundary": {
            "evidence_only": True,
            "creates_task": False,
            "creates_route": False,
            "creates_work_claim": False,
            "creates_worker_slot": False,
            "grants_execution_authority": False,
            "grants_domain_write": False,
            "grants_signal_write": False,
            "grants_w3_write": False,
            "grants_merge_authority": False,
        },
        "receipt_digest": "a" * 64,
    }


def _fixture_materializer_decision(raw: dict) -> dict:
    try:
        normalized = validate_opportunity(copy.deepcopy(raw))
    except IdleSignalSchedulerError:
        value = {
            "schema_version": MATERIALIZER_DECISION_SCHEMA,
            "signal_ref": str(raw.get("signal_ref") or "signal:invalid"),
            "disposition": "INELIGIBLE_SIGNAL_STATE",
            "reason": "FIXTURE_INELIGIBLE",
            "evidence_refs": ["fixture://materializer"],
            "owner_binding_digest": None,
            "opportunity": None,
            "authority_boundary": {"creates_signal_truth": False},
        }
    else:
        value = {
            "schema_version": MATERIALIZER_DECISION_SCHEMA,
            "signal_ref": normalized["signal_ref"],
            "disposition": "MATERIALIZED_FOR_R151",
            "reason": "FIXTURE_CURRENT_MATERIALIZER",
            "evidence_refs": ["fixture://materializer"],
            "owner_binding_digest": "f" * 64,
            "opportunity": normalized,
            "authority_boundary": {"creates_signal_truth": False},
        }
    value["decision_digest"] = _digest(value)
    return value


def trusted_batch(items: list[dict], current: str):
    def fake_materializer(_root, _ledger, draft_value, **_kwargs):
        return _fixture_materializer_decision(draft_value["fixture_opportunity"])
    requests = [
        {
            "schema_version": MATERIALIZATION_REQUEST_SCHEMA,
            "ledger": object(),
            "draft_value": {"fixture_opportunity": copy.deepcopy(item)},
            "domain_authority_descriptors": [],
            "domain_authority_observations": [],
            "authority_exact_read_proofs": [],
            "authority_live_observation_proof": None,
        }
        for item in items
    ]
    with patch("idle_signal_scheduler._load_current_materializer", return_value=fake_materializer):
        return materialize_trusted_opportunity_batch(
            REPO_ROOT, requests, expected_coordinator_main=current
        )


class IdleSignalSchedulerTests(unittest.TestCase):
    def evaluate(
        self,
        items,
        scan=None,
        *,
        canonical_blockers=None,
        trusted_review_blockers=None,
        r150=None,
    ):
        current = head()
        scan = scan or priority_observation()
        if r150 is None:
            r150 = r150_receipt(current)
        trusted_review_blockers = list(trusted_review_blockers or [])
        batch = trusted_batch(list(items), current)
        with (
            patch(
                "idle_signal_scheduler._canonical_idle_blockers",
                return_value=list(canonical_blockers or []),
            ),
            patch(
                "idle_signal_scheduler._trusted_review_queue_blockers",
                return_value=(
                    trusted_review_blockers,
                    ["fixture://trusted-review-queue"],
                    "b" * 64,
                ),
            ),
            patch(
                "idle_signal_scheduler.evaluate_trusted_release_proposal",
                return_value=r150,
            ),
        ):
            return evaluate_idle_signal_startup(
                REPO_ROOT,
                batch,
                expected_coordinator_main=current,
                priority_observation_value=scan,
            )

    def test_01_p0_user_or_high_risk_blocks_idle_signal(self) -> None:
        result = self.evaluate([opportunity()], priority_observation(priority_item(P0)))
        self.assertEqual(result["status"], "NO_IDLE_RELEASE")
        self.assertEqual(result["reason"], "HIGHER_PRIORITY_OR_ACTIVE_WORK_PRESENT")

    def test_02_p1_exact_head_review_blocks_idle_signal(self) -> None:
        result = self.evaluate([opportunity()], priority_observation(priority_item(P1)))
        self.assertEqual(result["status"], "NO_IDLE_RELEASE")

    def test_03_p2_blocker_or_drift_blocks_idle_signal(self) -> None:
        result = self.evaluate([opportunity()], priority_observation(priority_item(P2)))
        self.assertEqual(result["status"], "NO_IDLE_RELEASE")

    def test_04_canonical_active_work_blocks_even_when_caller_hints_empty(self) -> None:
        blocker = {
            "priority": P2,
            "work_ref": "task://ACTIVE",
            "reason": "CANONICAL_ACTIVE_OR_RESERVED_WORK_CLAIM",
            "evidence_refs": ["coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"],
        }
        result = self.evaluate([opportunity()], canonical_blockers=[blocker])
        self.assertEqual(result["status"], "NO_IDLE_RELEASE")
        self.assertTrue(result["blockers"])

    def test_05_already_satisfied_or_superseded_is_ineligible(self) -> None:
        result = self.evaluate(
            [
                opportunity("DONE-1", disposition="ALREADY_SATISFIED"),
                opportunity("DONE-2", disposition="SUPERSEDED"),
            ]
        )
        self.assertEqual(result["status"], "NO_IDLE_RELEASE")
        self.assertEqual(result["reason"], "NO_ELIGIBLE_TRUSTED_SIGNAL_OPPORTUNITY")

    def test_06_unknown_or_needs_revalidation_cannot_release(self) -> None:
        result = self.evaluate(
            [
                opportunity("U-1", epistemic="UNKNOWN"),
                opportunity("U-2", epistemic="NEEDS_REVALIDATION"),
            ]
        )
        self.assertEqual(result["status"], "NO_IDLE_RELEASE")

    def test_07_higher_value_p3_selected_deterministically(self) -> None:
        low = opportunity("LOW", signal_ref="signal:low", user_value=30)
        high = opportunity("HIGH", signal_ref="signal:high", user_value=95)
        result = self.evaluate([low, high])
        self.assertEqual(result["status"], "AUTO_RELEASE_AUTHORIZED")
        self.assertEqual(result["selected_opportunity_id"], "HIGH")
        self.assertEqual(result["selected_signal_ref"], "signal:high")

    def test_08_p3_always_outranks_p4_even_when_p4_is_older(self) -> None:
        p3 = opportunity("P3", signal_ref="signal:p3", priority=P3, user_value=10)
        p4 = opportunity(
            "P4",
            signal_ref="signal:p4",
            priority=P4,
            user_value=100,
            materiality=100,
            readiness=100,
            age=100,
            cost=0,
        )
        result = self.evaluate([p4, p3])
        self.assertEqual(result["selected_opportunity_id"], "P3")

    def test_09_starvation_age_breaks_same_priority_tie(self) -> None:
        young = opportunity("YOUNG", signal_ref="signal:young", user_value=70, age=0)
        old = opportunity("OLD", signal_ref="signal:old", user_value=70, age=5)
        result = self.evaluate([young, old])
        self.assertEqual(result["selected_opportunity_id"], "OLD")

    def test_10_high_risk_excluded_side_effect_forces_user_gate(self) -> None:
        risky = opportunity()
        risky["task_release_proposal"]["risk"] = [
            "production deployment with secret token"
        ]
        result = self.evaluate([risky])
        self.assertEqual(result["status"], "USER_GATE")

    def test_11_stale_current_main_r150_failure_fails_closed(self) -> None:
        with (
            patch("idle_signal_scheduler._canonical_idle_blockers", return_value=[]),
            patch(
                "idle_signal_scheduler._trusted_review_queue_blockers",
                return_value=([], ["fixture://trusted-review-queue"], "b" * 64),
            ),
            patch(
                "idle_signal_scheduler.evaluate_trusted_release_proposal",
                side_effect=TrustedReleaseError("CANONICAL_MAIN_DRIFT"),
            ),
        ):
            result = evaluate_idle_signal_startup(
                REPO_ROOT,
                trusted_batch([opportunity()], head()),
                expected_coordinator_main=head(),
                priority_observation_value=priority_observation(),
            )
        self.assertEqual(result["status"], "NO_IDLE_RELEASE")
        self.assertEqual(result["reason"], "R150_FAIL_CLOSED:CANONICAL_MAIN_DRIFT")

    def test_12_r150_non_release_cannot_mint_authorization(self) -> None:
        result = self.evaluate(
            [opportunity()], r150=r150_receipt(head(), "NO_TASK_ALREADY_SATISFIED")
        )
        self.assertEqual(result["status"], "NO_IDLE_RELEASE")
        self.assertIsNone(result["authorization"])

    def test_13_forged_or_malformed_r150_receipt_cannot_mint_authorization(self) -> None:
        forged = r150_receipt(head())
        forged["schema_version"] = "ForgedReceipt/v1"
        with self.assertRaises(IdleSignalSchedulerError) as caught:
            self.evaluate([opportunity()], r150=forged)
        self.assertEqual(caught.exception.code, "R150_TRUSTED_RECEIPT_REQUIRED")

    def test_14_valid_candidate_mints_exact_bound_authorization_only(self) -> None:
        current = head()
        result = self.evaluate([opportunity()])
        self.assertEqual(result["schema_version"], DECISION_SCHEMA)
        self.assertEqual(result["status"], "AUTO_RELEASE_AUTHORIZED")
        auth = result["authorization"]
        self.assertEqual(auth["schema_version"], AUTHORIZATION_SCHEMA)
        self.assertEqual(auth["canonical_main"], current)
        self.assertEqual(auth["signal_ref"], "signal:r151-fixture")
        self.assertTrue(auth["authority"]["can_create_issue"])
        self.assertTrue(auth["authority"]["can_begin_bounded_engineering"])
        self.assertFalse(auth["authority"]["signal_self_authorizes"])
        self.assertFalse(auth["authority"]["caller_can_attest_priority_completeness"])
        self.assertFalse(auth["authority"]["can_merge_without_independent_accept"])
        self.assertFalse(auth["authority"]["can_deploy_production"])
        self.assertTrue(auth["independent_exact_head_review_required"])
        self.assertTrue(auth["apply_requires_fresh_recheck"])
        self.assertTrue(auth["apply_requires_fresh_rematerialization"])
        self.assertFalse(auth["authority"]["caller_can_supply_opportunity_truth"])
        self.assertEqual(len(auth["trusted_opportunity_batch_digest"]), 64)
        self.assertEqual(len(auth["materialization_decision_digest"]), 64)

    def test_15_signal_proposal_binding_is_mandatory(self) -> None:
        bad = opportunity()
        bad["task_release_proposal"]["source_signal_refs"] = ["signal:other"]
        with self.assertRaises(IdleSignalSchedulerError) as caught:
            validate_opportunity(bad)
        self.assertEqual(caught.exception.code, "SIGNAL_PROPOSAL_BINDING_MISSING")

    def test_16_caller_cannot_self_attest_priority_scan_completeness(self) -> None:
        scan = priority_observation()
        scan["scan_complete"] = True
        with self.assertRaises(IdleSignalSchedulerError) as caught:
            evaluate_idle_signal_startup(
                REPO_ROOT,
                trusted_batch([opportunity()], head()),
                expected_coordinator_main=head(),
                priority_observation_value=scan,
            )
        self.assertEqual(caught.exception.code, "PRIORITY_HINTS_FIELDS_INVALID")

    def test_17_forged_empty_caller_hints_cannot_hide_trusted_p1(self) -> None:
        trusted_p1 = {
            "priority": P1,
            "work_ref": "pr://999@" + "c" * 40,
            "reason": "TRUSTED_REVIEW_QUEUE_WAITING_REVIEW",
            "evidence_refs": ["https://github.com/example/review-queue-comment"],
        }
        result = self.evaluate(
            [opportunity()],
            scan=priority_observation(),
            trusted_review_blockers=[trusted_p1],
        )
        self.assertEqual(result["status"], "NO_IDLE_RELEASE")
        self.assertEqual(result["reason"], "HIGHER_PRIORITY_OR_ACTIVE_WORK_PRESENT")
        self.assertEqual(result["blockers"][0]["priority"], P1)

    def test_18_review_queue_parser_settles_matching_exact_head_ticket(self) -> None:
        head_a = "a" * 40
        head_b = "b" * 40
        payload = [
            {
                "id": 1,
                "html_url": "https://github.com/q/1",
                "body": (
                    "schema: REVIEW_REQUEST/v1\nproject: SECOND_BRAIN\npr: 91\n"
                    f"exact_head: {head_a}\nstatus: WAITING_REVIEW\n"
                ),
            },
            {
                "id": 2,
                "html_url": "https://github.com/q/2",
                "body": (
                    "schema: REVIEW_RESULT/v1\nproject: SECOND_BRAIN\npr: 91\n"
                    f"reviewed_head: {head_a}\nverdict: ACCEPT\n"
                ),
            },
            {
                "id": 3,
                "html_url": "https://github.com/q/3",
                "body": (
                    "schema: REVIEW_REQUEST/v1\nproject: SECOND_BRAIN\npr: 92\n"
                    f"exact_head: {head_b}\nstatus: WAITING_REVIEW\n"
                ),
            },
            {
                "id": 4,
                "html_url": "https://github.com/q/4",
                "body": (
                    "schema: REVIEW_RESULT/v1\nproject: SECOND_BRAIN\npr: 92\n"
                    f"reviewed_head: {head_b}\nverdict: CHANGES_REQUIRED\n"
                ),
            },
        ]

        class FakeGatewayError(Exception):
            code = "FAKE"

        class FakeObserver:
            def _get_json(self, path):
                return ({"content-type": "application/json"}, payload, {"path": path})

        with patch(
            "idle_signal_scheduler._make_review_queue_observer",
            return_value=(FakeObserver(), FakeGatewayError),
        ):
            blockers, refs, digest = _trusted_review_queue_blockers(REPO_ROOT)
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["priority"], P2)
        self.assertEqual(blockers[0]["work_ref"], f"pr://92@{head_b}")
        self.assertEqual(len(refs), 4)
        self.assertEqual(len(digest), 64)

    def test_19_late_old_head_result_cannot_suppress_new_head_request(self) -> None:
        head_a = "a" * 40
        head_b = "b" * 40
        payload = [
            {
                "id": 11,
                "html_url": "https://github.com/q/11",
                "body": (
                    "schema: REVIEW_REQUEST/v1\nproject: SECOND_BRAIN\npr: 93\n"
                    f"exact_head: {head_a}\nstatus: WAITING_REVIEW\n"
                ),
            },
            {
                "id": 12,
                "html_url": "https://github.com/q/12",
                "body": (
                    "schema: REVIEW_REQUEST/v1\nproject: SECOND_BRAIN\npr: 93\n"
                    f"exact_head: {head_b}\nstatus: WAITING_REVIEW\n"
                ),
            },
            {
                "id": 13,
                "html_url": "https://github.com/q/13",
                "body": (
                    "schema: REVIEW_RESULT/v1\nproject: SECOND_BRAIN\npr: 93\n"
                    f"reviewed_head: {head_a}\nverdict: ACCEPT\n"
                ),
            },
        ]

        class FakeGatewayError(Exception):
            code = "FAKE"

        class FakeObserver:
            def _get_json(self, path):
                return ({"content-type": "application/json"}, payload, {"path": path})

        with patch(
            "idle_signal_scheduler._make_review_queue_observer",
            return_value=(FakeObserver(), FakeGatewayError),
        ):
            blockers, refs, digest = _trusted_review_queue_blockers(REPO_ROOT)
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["priority"], P1)
        self.assertEqual(blockers[0]["work_ref"], f"pr://93@{head_b}")
        self.assertEqual(blockers[0]["reason"], "TRUSTED_REVIEW_QUEUE_WAITING_REVIEW")
        self.assertEqual(len(refs), 3)
        self.assertEqual(len(digest), 64)

    def test_20_historical_failure_does_not_deadlock_accepted_newer_lineage(self) -> None:
        head_a = "a" * 40
        head_b = "b" * 40
        payload = [
            {
                "id": 21,
                "html_url": "https://github.com/q/21",
                "body": (
                    "schema: REVIEW_REQUEST/v1\nproject: SECOND_BRAIN\npr: 94\n"
                    f"exact_head: {head_a}\nstatus: WAITING_REVIEW\n"
                ),
            },
            {
                "id": 22,
                "html_url": "https://github.com/q/22",
                "body": (
                    "schema: REVIEW_RESULT/v1\nproject: SECOND_BRAIN\npr: 94\n"
                    f"reviewed_head: {head_a}\nverdict: CHANGES_REQUIRED\n"
                ),
            },
            {
                "id": 23,
                "html_url": "https://github.com/q/23",
                "body": (
                    "schema: REVIEW_REQUEST/v1\nproject: SECOND_BRAIN\npr: 94\n"
                    f"exact_head: {head_b}\nstatus: WAITING_REVIEW\n"
                ),
            },
            {
                "id": 24,
                "html_url": "https://github.com/q/24",
                "body": (
                    "schema: REVIEW_RESULT/v1\nproject: SECOND_BRAIN\npr: 94\n"
                    f"reviewed_head: {head_b}\nverdict: ACCEPT\n"
                ),
            },
        ]

        class FakeGatewayError(Exception):
            code = "FAKE"

        class FakeObserver:
            def _get_json(self, path):
                return ({"content-type": "application/json"}, payload, {"path": path})

        with patch(
            "idle_signal_scheduler._make_review_queue_observer",
            return_value=(FakeObserver(), FakeGatewayError),
        ):
            blockers, refs, digest = _trusted_review_queue_blockers(REPO_ROOT)
        self.assertEqual(blockers, [])
        self.assertEqual(len(refs), 4)
        self.assertEqual(len(digest), 64)

    def test_21_trusted_priority_provider_failure_is_fail_closed(self) -> None:
        with (
            patch("idle_signal_scheduler._canonical_idle_blockers", return_value=[]),
            patch(
                "idle_signal_scheduler._trusted_review_queue_blockers",
                side_effect=IdleSignalSchedulerError(
                    "TRUSTED_REVIEW_QUEUE_PAGINATION_INCOMPLETE"
                ),
            ),
        ):
            result = evaluate_idle_signal_startup(
                REPO_ROOT,
                trusted_batch([opportunity()], head()),
                expected_coordinator_main=head(),
                priority_observation_value=priority_observation(),
            )
        self.assertEqual(result["status"], "NO_IDLE_RELEASE")
        self.assertIn("TRUSTED_PRIORITY_FAIL_CLOSED", result["reason"])


    def test_22_raw_opportunity_sequence_cannot_enter_r151(self) -> None:
        with self.assertRaisesRegex(IdleSignalSchedulerError, "TRUSTED_OPPORTUNITY_BATCH_REQUIRED"):
            evaluate_idle_signal_startup(
                REPO_ROOT,
                [opportunity()],
                expected_coordinator_main=head(),
                priority_observation_value=priority_observation(),
            )

    def test_23_fake_mapping_cannot_forge_trusted_batch(self) -> None:
        fake = {"schema_version": "TrustedSignalOpportunityBatch/v1", "batch_digest": "0" * 64}
        with self.assertRaisesRegex(IdleSignalSchedulerError, "TRUSTED_OPPORTUNITY_BATCH_REQUIRED"):
            evaluate_idle_signal_startup(
                REPO_ROOT, fake, expected_coordinator_main=head(), priority_observation_value=priority_observation()
            )

    def test_24_materialization_decision_digest_tamper_fails_closed(self) -> None:
        raw = opportunity()
        def fake(_root, _ledger, _draft, **_kwargs):
            value = _fixture_materializer_decision(raw)
            value["decision_digest"] = "0" * 64
            return value
        request = {
            "schema_version": MATERIALIZATION_REQUEST_SCHEMA,
            "ledger": object(),
            "draft_value": {"fixture_opportunity": raw},
            "domain_authority_descriptors": [],
            "domain_authority_observations": [],
            "authority_exact_read_proofs": [],
            "authority_live_observation_proof": None,
        }
        with patch("idle_signal_scheduler._load_current_materializer", return_value=fake):
            with self.assertRaisesRegex(IdleSignalSchedulerError, "DECISION_DIGEST_MISMATCH"):
                materialize_trusted_opportunity_batch(REPO_ROOT, [request], expected_coordinator_main=head())

    def test_25_non_materialized_decision_never_enters_batch(self) -> None:
        raw = opportunity(epistemic="UNKNOWN")
        result = self.evaluate([raw])
        self.assertEqual(result["status"], "NO_IDLE_RELEASE")
        self.assertEqual(result["reason"], "NO_ELIGIBLE_TRUSTED_SIGNAL_OPPORTUNITY")


if __name__ == "__main__":
    unittest.main()