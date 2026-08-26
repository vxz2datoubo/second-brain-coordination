from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from idle_signal_apply import (
    ACTIVATION_MANIFEST_SCHEMA,
    APPLY_INTENT_SCHEMA,
    APPLY_RECEIPT_SCHEMA,
    APPLIED_STATE_SCHEMA,
    AUTHORIZED_LOGICAL_PLAN,
    BOOTSTRAP_EVIDENCE_SCHEMA,
    BOOTSTRAP_MANIFEST_SCHEMA,
    RESOURCE_CLASS,
    REVIEWER_ROLE,
    IdleSignalApplyError,
    _digest,
    prepare_apply_transaction,
    verify_applied_state,
)
from idle_signal_scheduler import AUTHORIZATION_SCHEMA, OPPORTUNITY_SCHEMA
from idle_signal_scheduler import validate_opportunity


REPO_ROOT = Path(__file__).resolve().parents[3]
MAIN = "a" * 40


def proposal(signal_ref: str = "signal:r152-fixture") -> dict:
    return {
        "schema_version": "TaskReleaseProposal/v1",
        "release_candidate_id": "R152-FIXTURE",
        "source_signal_refs": [signal_ref, "issue://463"],
        "signal_primary_domain": "SHARED_COGNITIVE_OS",
        "desired_effect": "Apply one governed R151 authorization without authority expansion.",
        "proposed_target_domain": "SHARED_COGNITIVE_OS",
        "proposed_write_surface": {
            "write_paths": ["coordination/CONTROL-TOWER/example_bounded_target.py"],
            "read_paths": [
                "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
                "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml",
            ],
            "interfaces": [
                {
                    "name": "IdleSignalAutoReleaseAuthorization",
                    "mode": "read",
                    "frozen": True,
                }
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
                "component_id": "R151IdleSignalScheduler",
                "decision": "EXTEND",
                "satisfies_requirement": False,
                "evidence_refs": ["pr://462"],
            }
        ],
        "relations": [
            {
                "relation": "EXTENDS",
                "source": "R152ApplyTransaction",
                "target": "R151IdleSignalScheduler",
                "evidence_refs": ["issue://463"],
            }
        ],
        "reverse_consumers": [
            {
                "consumer_id": "startup_task_apply",
                "impact": "CONSUMER_REVALIDATION_ONLY",
                "evidence_refs": ["issue://463"],
            }
        ],
        "consumer_inventory_complete": True,
        "composition": {
            "optional": True,
            "can_compose": True,
            "core_invariant": False,
            "missing_capability_behavior": "ABSTAIN",
            "removal_preserves_unrelated_core": True,
            "justification": "Apply composes after retained R151/R150/R149 gates.",
        },
        "synchronized_change_set": [],
        "regression_revalidation_set": ["startup_task_apply"],
        "unaffected_set": [
            {
                "component_id": "SignalTowerDurableTruth",
                "evidence_refs": ["boundary://signal-does-not-self-authorize"],
            }
        ],
        "unresolved_unknowns": [],
    }


def opportunity(
    opportunity_id: str = "R152-OPP-001",
    signal_ref: str = "signal:r152-fixture",
    *,
    release_proposal: dict | None = None,
) -> dict:
    p = copy.deepcopy(release_proposal or proposal(signal_ref))
    return {
        "schema_version": OPPORTUNITY_SCHEMA,
        "opportunity_id": opportunity_id,
        "signal_ref": signal_ref,
        "signal_primary_domain": "SHARED_COGNITIVE_OS",
        "source_evidence_refs": [signal_ref, "issue://463"],
        "desired_effect": p["desired_effect"],
        "problem_to_solve": "R151 authorization must not become a caller-controlled mutation primitive.",
        "success_condition": "Apply is fresh, exact-bound, staged, and independently reviewable.",
        "current_disposition": "NEW_DURABLE_SIGNAL",
        "epistemic_state": "USER_EXPLICIT",
        "desired_effect_gap_proven": True,
        "dependency_ready": True,
        "priority_class": "P3_BOUNDED_IMPROVEMENT",
        "user_value_score": 90,
        "materiality_score": 85,
        "dependency_readiness_score": 90,
        "age_cycles": 1,
        "estimated_cost_score": 25,
        "task_release_proposal": p,
    }


def hints() -> dict:
    return {
        "schema_version": "StartupPriorityHints/v1",
        "observation_id": "r152-fixture-hints",
        "evidence_refs": ["fixture://current-user-context"],
        "items": [],
    }


def authorization(raw_opportunity: dict, main: str = MAIN) -> dict:
    normalized = validate_opportunity(raw_opportunity)
    value = {
        "schema_version": AUTHORIZATION_SCHEMA,
        "signal_ref": normalized["signal_ref"],
        "opportunity_id": normalized["opportunity_id"],
        "opportunity_digest": normalized["opportunity_digest"],
        "canonical_main": main,
        "priority_observation_digest": "b" * 64,
        "r150_receipt_digest": "c" * 64,
        "r150_final_disposition": "RELEASE_AS_EXTENSION",
        "standing_user_policy_ref": "issue://461#user-direction-2026-08-26",
        "priority_semantics_ref": "fixture://priority",
        "priority_provider_ref": "fixture://provider",
        "release_gate_refs": [
            "coordination/CONTROL-TOWER/task_release_impact.py",
            "coordination/CONTROL-TOWER/trusted_task_release.py",
        ],
        "side_effect_plan": list(AUTHORIZED_LOGICAL_PLAN),
        "authority": {
            "creates_signal_truth": False,
            "signal_self_authorizes": False,
            "caller_can_attest_priority_completeness": False,
            "can_create_issue": True,
            "can_create_route": True,
            "can_create_work_claim": True,
            "can_allocate_worker_slot": True,
            "can_begin_bounded_engineering": True,
            "can_merge_without_independent_accept": False,
            "can_deploy_production": False,
            "can_expand_permissions_or_secrets": False,
            "can_touch_trading_orders_or_funds": False,
            "can_perform_destructive_history_rewrite": False,
        },
        "independent_exact_head_review_required": True,
        "apply_requires_fresh_recheck": True,
    }
    value["authorization_id"] = f"r151-auto-release:{_digest(value)[:24]}"
    value["authorization_digest"] = _digest(value)
    return value


def intent(raw_opportunity: dict, lane_id: str = "LANE-A-HARNESS-INTEGRATION") -> dict:
    return {
        "schema_version": APPLY_INTENT_SCHEMA,
        "lane_id": lane_id,
        "route_epoch": 152,
        "release_reason_class": "NEW_GOVERNED_TASK",
        "requested_surface": copy.deepcopy(
            raw_opportunity["task_release_proposal"]["proposed_write_surface"]
        ),
        "resource_class": RESOURCE_CLASS,
        "reviewer_role": REVIEWER_ROLE,
        "reviewer_separation": "EXECUTOR_IS_NOT_ACCEPTANCE_AUTHORITY",
        "operation_plan": list(AUTHORIZED_LOGICAL_PLAN),
    }


def bootstrap_evidence(bootstrap_manifest: dict) -> dict:
    return {
        "schema_version": BOOTSTRAP_EVIDENCE_SCHEMA,
        "issue": 500,
        "implementation_pr": 501,
        "branch": bootstrap_manifest["identity"]["branch"],
        "bootstrap_head": "d" * 40,
        "draft": True,
        "empty_bootstrap_commit": True,
        "file_mutations": [],
    }


def observed_state(manifest: dict) -> dict:
    bootstrap = manifest["bootstrap_evidence"]
    return {
        "schema_version": APPLIED_STATE_SCHEMA,
        "canonical_main": manifest["canonical_main"],
        "activation_gate_pr": 502,
        "activation_gate_reviewed_head": "e" * 40,
        "activation_gate_verdict": "ACCEPT",
        "activation_gate_merge_commit": "f" * 40,
        "issue": bootstrap["issue"],
        "implementation_pr": bootstrap["implementation_pr"],
        "branch": bootstrap["branch"],
        "route_artifact": copy.deepcopy(manifest["route_artifact"]),
        "work_claim": copy.deepcopy(manifest["work_claim_replacement"]),
        "worker_slot": copy.deepcopy(manifest["worker_slot_append"]),
    }


class IdleSignalApplyTests(unittest.TestCase):
    def prepare(
        self,
        raw_opportunity: dict | None = None,
        *,
        auth: dict | None = None,
        apply_intent: dict | None = None,
        bootstrap: dict | None = None,
        fresh_error: IdleSignalApplyError | None = None,
    ) -> dict:
        raw_opportunity = copy.deepcopy(raw_opportunity or opportunity())
        auth = copy.deepcopy(auth or authorization(raw_opportunity))
        apply_intent = copy.deepcopy(apply_intent or intent(raw_opportunity))
        fresh_patch = (
            patch("idle_signal_apply._fresh_authorization", side_effect=fresh_error)
            if fresh_error
            else patch("idle_signal_apply._fresh_authorization", return_value=auth)
        )
        with patch("idle_signal_apply._git_head", return_value=MAIN), fresh_patch:
            return prepare_apply_transaction(
                REPO_ROOT,
                raw_opportunity,
                hints(),
                auth,
                apply_intent,
                expected_current_main=MAIN,
                bootstrap_evidence=bootstrap,
            )

    def activation(self) -> dict:
        raw = opportunity()
        auth = authorization(raw)
        bootstrap_manifest = self.prepare(raw, auth=auth)
        return self.prepare(
            raw,
            auth=auth,
            bootstrap=bootstrap_evidence(bootstrap_manifest),
        )

    def test_01_main_drift_invalidates_authorization(self) -> None:
        raw = opportunity()
        auth = authorization(raw)
        with patch("idle_signal_apply._git_head", return_value="9" * 40):
            with self.assertRaisesRegex(IdleSignalApplyError, "CURRENT_MAIN_DRIFT"):
                prepare_apply_transaction(
                    REPO_ROOT,
                    raw,
                    hints(),
                    auth,
                    intent(raw),
                    expected_current_main=MAIN,
                )

    def test_02_new_p1_or_p2_after_scheduling_blocks_fresh_apply(self) -> None:
        with self.assertRaisesRegex(
            IdleSignalApplyError, "R151_FRESH_REPLAY_NOT_AUTHORIZED"
        ):
            self.prepare(
                fresh_error=IdleSignalApplyError(
                    "R151_FRESH_REPLAY_NOT_AUTHORIZED:HIGHER_PRIORITY_OR_ACTIVE_WORK_PRESENT"
                )
            )

    def test_03_forged_authorization_digest_fails(self) -> None:
        raw = opportunity()
        auth = authorization(raw)
        auth["authorization_digest"] = "0" * 64
        with self.assertRaisesRegex(IdleSignalApplyError, "DIGEST_FORGED"):
            self.prepare(raw, auth=auth)

    def test_04_authorization_from_other_opportunity_fails(self) -> None:
        raw = opportunity()
        other = opportunity("OTHER-OPP")
        with self.assertRaisesRegex(IdleSignalApplyError, "OPPORTUNITY_ID_MISMATCH"):
            self.prepare(raw, auth=authorization(other))

    def test_05_write_path_expansion_fails(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw)
        apply_intent["requested_surface"]["write_paths"].append("coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml")
        with self.assertRaisesRegex(IdleSignalApplyError, "SURFACE_EXPANSION_OR_DRIFT"):
            self.prepare(raw, apply_intent=apply_intent)

    def test_06_write_domain_expansion_fails(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw)
        apply_intent["requested_surface"]["write_domains"].append("W3_MEMORY")
        with self.assertRaisesRegex(IdleSignalApplyError, "SURFACE_EXPANSION_OR_DRIFT"):
            self.prepare(raw, apply_intent=apply_intent)

    def test_07_authority_claim_expansion_fails(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw)
        apply_intent["requested_surface"]["authority_claims"].append("SECOND_TASK_AUTHORITY")
        with self.assertRaisesRegex(IdleSignalApplyError, "SURFACE_EXPANSION_OR_DRIFT"):
            self.prepare(raw, apply_intent=apply_intent)

    def test_08_interface_mutation_fails(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw)
        apply_intent["requested_surface"]["interfaces"][0]["mode"] = "write"
        with self.assertRaisesRegex(IdleSignalApplyError, "SURFACE_EXPANSION_OR_DRIFT"):
            self.prepare(raw, apply_intent=apply_intent)

    def test_09_task_identity_drift_across_applied_state_fails(self) -> None:
        manifest = self.activation()
        observed = observed_state(manifest)
        observed["worker_slot"]["task_id"] = "ATTACKER-TASK"
        with self.assertRaisesRegex(IdleSignalApplyError, "WORKER_SLOT_MISMATCH"):
            verify_applied_state(manifest, observed)

    def test_10_route_epoch_drift_fails(self) -> None:
        manifest = self.activation()
        observed = observed_state(manifest)
        observed["work_claim"]["route_binding"]["route_epoch"] += 1
        with self.assertRaisesRegex(IdleSignalApplyError, "CLAIM_MISMATCH"):
            verify_applied_state(manifest, observed)

    def test_11_branch_drift_fails(self) -> None:
        manifest = self.activation()
        observed = observed_state(manifest)
        observed["branch"] = "gpt/attacker-branch"
        with self.assertRaisesRegex(IdleSignalApplyError, "APPLIED_IDENTITY_MISMATCH"):
            verify_applied_state(manifest, observed)

    def test_12_issue_drift_fails(self) -> None:
        manifest = self.activation()
        observed = observed_state(manifest)
        observed["issue"] += 1
        with self.assertRaisesRegex(IdleSignalApplyError, "APPLIED_IDENTITY_MISMATCH"):
            verify_applied_state(manifest, observed)

    def test_13_lane_c_ordinary_improvement_cannot_bypass_reopen_rule(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw, "LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP")
        apply_intent["release_reason_class"] = "NEW_GOVERNED_TASK"
        with self.assertRaisesRegex(IdleSignalApplyError, "LANE_REOPEN_REASON_NOT_AUTHORIZED"):
            self.prepare(raw, apply_intent=apply_intent)

    def test_14_existing_active_claim_or_slot_blocks_duplicate_apply(self) -> None:
        raw = opportunity()
        auth = authorization(raw)
        with (
            patch("idle_signal_apply._git_head", return_value=MAIN),
            patch("idle_signal_apply._fresh_authorization", return_value=auth),
            patch(
                "idle_signal_apply._assert_no_existing_live_control_state",
                side_effect=IdleSignalApplyError("EXISTING_ACTIVE_OR_RESERVED_CLAIM"),
            ),
        ):
            with self.assertRaisesRegex(IdleSignalApplyError, "EXISTING_ACTIVE"):
                prepare_apply_transaction(
                    REPO_ROOT,
                    raw,
                    hints(),
                    auth,
                    intent(raw),
                    expected_current_main=MAIN,
                )

    def test_15_partial_operation_plan_fails(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw)
        apply_intent["operation_plan"] = apply_intent["operation_plan"][:-1]
        with self.assertRaisesRegex(IdleSignalApplyError, "OPERATION_PLAN_INVALID"):
            self.prepare(raw, apply_intent=apply_intent)

    def test_16_reordered_operation_plan_fails(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw)
        apply_intent["operation_plan"][1:3] = reversed(apply_intent["operation_plan"][1:3])
        with self.assertRaisesRegex(IdleSignalApplyError, "OPERATION_PLAN_INVALID"):
            self.prepare(raw, apply_intent=apply_intent)

    def test_17_excluded_high_risk_side_effect_fails(self) -> None:
        p = proposal()
        p["risk"] = ["production deploy"]
        raw = opportunity(release_proposal=p)
        with self.assertRaisesRegex(IdleSignalApplyError, "EXCLUDED_SIDE_EFFECT_REQUESTED"):
            self.prepare(raw)

    def test_18_valid_bootstrap_manifest_is_deterministic_and_non_executable(self) -> None:
        first = self.prepare()
        second = self.prepare()
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], BOOTSTRAP_MANIFEST_SCHEMA)
        self.assertEqual(first["status"], "BOOTSTRAP_REQUIRED")
        self.assertEqual(first["runtime_pr_bootstrap"]["file_mutations"], [])
        self.assertFalse(first["authority_boundary"]["execution_authority_granted"])

    def test_19_valid_activation_manifest_is_exact_bound_and_candidate_only(self) -> None:
        manifest = self.activation()
        self.assertEqual(manifest["schema_version"], ACTIVATION_MANIFEST_SCHEMA)
        self.assertTrue(manifest["atomic_control_plane_commit_required"])
        self.assertTrue(manifest["partial_apply_forbidden"])
        self.assertFalse(manifest["authority_boundary"]["manifest_performs_side_effects"])
        self.assertFalse(manifest["authority_boundary"]["execution_authority_granted_by_manifest"])
        self.assertFalse(manifest["authority_boundary"]["merge_authority_granted"])
        self.assertFalse(manifest["authority_boundary"]["w3_write_authorized"])
        self.assertFalse(manifest["authority_boundary"]["signal_runtime_write_authorized"])
        claim = manifest["work_claim_replacement"]
        slot = manifest["worker_slot_append"]
        self.assertEqual(claim["route_binding"]["task_id"], slot["task_id"])
        self.assertEqual(claim["route_binding"]["route_epoch"], slot["route_epoch"])
        self.assertEqual(claim["route_binding"]["issue"], slot["issue"])
        self.assertEqual(claim["route_binding"]["pr"], slot["pr"])
        self.assertEqual(claim["route_binding"]["branch"], slot["branch"])

    def test_20_bootstrap_requires_empty_commit_without_file_mutation(self) -> None:
        bootstrap_manifest = self.prepare()
        evidence = bootstrap_evidence(bootstrap_manifest)
        evidence["file_mutations"] = ["README.md"]
        with self.assertRaisesRegex(IdleSignalApplyError, "BOOTSTRAP_FILE_MUTATION_FORBIDDEN"):
            self.prepare(bootstrap=evidence)

    def test_21_bootstrap_branch_is_not_caller_replaceable(self) -> None:
        bootstrap_manifest = self.prepare()
        evidence = bootstrap_evidence(bootstrap_manifest)
        evidence["branch"] = "gpt/attacker"
        with self.assertRaisesRegex(IdleSignalApplyError, "BOOTSTRAP_BRANCH_MISMATCH"):
            self.prepare(bootstrap=evidence)

    def test_22_post_apply_partial_state_fails_closed(self) -> None:
        manifest = self.activation()
        observed = observed_state(manifest)
        observed.pop("worker_slot")
        with self.assertRaisesRegex(IdleSignalApplyError, "APPLIED_STATE_FIELDS_INVALID"):
            verify_applied_state(manifest, observed)

    def test_23_post_apply_requires_independent_accept(self) -> None:
        manifest = self.activation()
        observed = observed_state(manifest)
        observed["activation_gate_verdict"] = "CHANGES_REQUIRED"
        with self.assertRaisesRegex(IdleSignalApplyError, "ACTIVATION_GATE_NOT_ACCEPTED"):
            verify_applied_state(manifest, observed)

    def test_24_valid_post_apply_receipt_is_evidence_only(self) -> None:
        manifest = self.activation()
        receipt = verify_applied_state(manifest, observed_state(manifest))
        self.assertEqual(receipt["schema_version"], APPLY_RECEIPT_SCHEMA)
        self.assertTrue(receipt["authority_boundary"]["evidence_only"])
        self.assertFalse(receipt["authority_boundary"]["grants_execution_authority"])
        self.assertFalse(receipt["authority_boundary"]["grants_merge_authority"])
        self.assertFalse(receipt["authority_boundary"]["grants_production_deploy"])
        self.assertFalse(receipt["authority_boundary"]["grants_secrets_or_permission_expansion"])
        self.assertFalse(receipt["authority_boundary"]["grants_trading_order_or_fund_access"])
        self.assertFalse(receipt["authority_boundary"]["grants_destructive_history_rewrite"])


if __name__ == "__main__":
    unittest.main()
