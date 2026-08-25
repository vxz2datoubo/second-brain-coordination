from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from trusted_task_release import (
    PROPOSAL_SCHEMA,
    TrustedReleaseError,
    _load_r145_api,
    _materialize_active_work_items,
    evaluate_trusted_release_proposal,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def base_proposal() -> dict:
    return {
        "schema_version": PROPOSAL_SCHEMA,
        "release_candidate_id": "R150-CASE-001",
        "source_signal_refs": ["issue://454"],
        "signal_primary_domain": "SHARED_COGNITIVE_OS",
        "desired_effect": "Bind R149 release analysis to trusted current Control Tower evidence.",
        "proposed_target_domain": "SHARED_COGNITIVE_OS",
        "proposed_write_surface": {
            "write_paths": ["coordination/CONTROL-TOWER/trusted_task_release.py"],
            "read_paths": [
                "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
                "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml",
            ],
            "interfaces": [
                {
                    "name": "TaskReleaseImpactReceipt",
                    "mode": "read",
                    "frozen": True,
                }
            ],
            "read_domains": ["SHARED_COGNITIVE_OS"],
            "write_domains": ["SHARED_COGNITIVE_OS"],
            "authority_claims": [],
        },
        "materiality": "MATERIAL",
        "risk": ["caller-provided current state"],
        "out_of_scope": ["automatic task release"],
        "capability_inventory": [
            {
                "component_id": "R149TaskReleaseImpactGate",
                "decision": "EXTEND",
                "satisfies_requirement": False,
                "evidence_refs": ["issue://451", "pr://452"],
            }
        ],
        "relations": [],
        "reverse_consumers": [
            {
                "consumer_id": "task_release_impact",
                "impact": "CONSUMER_REVALIDATION_ONLY",
                "evidence_refs": ["code://task_release_impact.py"],
            }
        ],
        "consumer_inventory_complete": True,
        "composition": {
            "optional": False,
            "can_compose": False,
            "core_invariant": True,
            "missing_capability_behavior": "NOT_APPLICABLE",
            "removal_preserves_unrelated_core": "UNKNOWN",
            "justification": "Trusted release evidence extends the existing Control Tower gate.",
        },
        "synchronized_change_set": ["TrustedTaskReleaseObservationBinding"],
        "regression_revalidation_set": ["task_release_impact"],
        "unaffected_set": [
            {
                "component_id": "SignalTowerRuntime",
                "evidence_refs": ["boundary://signal-is-not-task"],
            }
        ],
        "unresolved_unknowns": [],
    }


def local_snapshot(revision: str | None = None) -> dict:
    head = revision or git_head()
    return {
        "canonical_main": head,
        "scan_coverage": {
            "domain_canonical": {
                "status": "SCANNED",
                "evidence_refs": [f"git://second-brain@{head}"],
            }
        },
    }


def evaluate(proposal: dict | None = None, *, expected: str | None = None, snapshot: dict | None = None):
    head = expected or git_head()
    return evaluate_trusted_release_proposal(
        REPO_ROOT,
        proposal or base_proposal(),
        expected_coordinator_main=head,
        authority_snapshot=snapshot or local_snapshot(head),
    )


def active_claim(*, authority: bool = False) -> dict:
    return {
        "lane_id": "LANE-SYNTHETIC",
        "claim_state": "ACTIVE_IMPLEMENTATION",
        "route_binding": {"task_id": "ACTIVE-CANONICAL-WORK"},
        "owns_coherent_change_surface": False,
        "write_paths": ["coordination/CONTROL-TOWER/trusted_task_release.py"],
        "read_paths": [],
        "interfaces": [],
        "read_domains": [],
        "write_domains": ["SHARED_COGNITIVE_OS"],
        "authority_claims": ["CONTROL_TOWER_RELEASE_AUTHORITY"] if authority else [],
    }


class TrustedTaskReleaseTests(unittest.TestCase):
    def test_01_same_domain_current_repository_materializes_positive_extension(self) -> None:
        head = git_head()
        receipt = evaluate(expected=head)
        self.assertEqual(receipt["schema_version"], "TrustedTaskReleaseImpactReceipt/v1")
        self.assertEqual(receipt["trusted_context"]["canonical_main"], head)
        self.assertEqual(receipt["impact_receipt"]["final_disposition"], "RELEASE_AS_EXTENSION")
        self.assertEqual(receipt["impact_receipt"]["collision_analysis"], [])
        self.assertTrue(receipt["trusted_context"]["exact_refs"])

    def test_02_caller_cannot_inject_any_trusted_current_state(self) -> None:
        for field, value in (
            ("observations", []),
            ("existing_work_items", []),
            ("authority_binding", {"compatible": True}),
            ("domain_binding", {"domain_id": "SHARED_COGNITIVE_OS"}),
            ("collision_analysis", []),
            ("final_disposition", "RELEASE_BOUNDED_TASK"),
            ("trusted_context", {}),
        ):
            with self.subTest(field=field):
                proposal = base_proposal()
                proposal[field] = value
                with self.assertRaises(TrustedReleaseError) as caught:
                    evaluate(proposal)
                self.assertEqual(
                    caught.exception.code, "CALLER_TRUSTED_STATE_INJECTION_FORBIDDEN"
                )

    def test_03_stale_r145_snapshot_cannot_be_reused_on_new_coordinator_main(self) -> None:
        head = git_head()
        stale = local_snapshot("0" * 40)
        with self.assertRaises(TrustedReleaseError) as caught:
            evaluate(expected=head, snapshot=stale)
        self.assertEqual(caught.exception.code, "DOMAIN_CANONICAL_DRIFT")

    def test_04_cross_domain_mismatch_fails_closed(self) -> None:
        proposal = base_proposal()
        proposal["proposed_target_domain"] = "AI_FILM_SYSTEM"
        receipt = evaluate(proposal)
        self.assertEqual(receipt["impact_receipt"]["final_disposition"], "ARCHITECTURE_CONFLICT")
        self.assertFalse(
            receipt["trusted_context"]["domain_guard"]["eligible_for_normal_release_gates"]
        )

    def test_05_expected_main_drift_blocks_before_release_analysis(self) -> None:
        with self.assertRaises(TrustedReleaseError) as caught:
            evaluate_trusted_release_proposal(
                REPO_ROOT,
                base_proposal(),
                expected_coordinator_main="0" * 40,
                authority_snapshot=local_snapshot(),
            )
        self.assertEqual(caught.exception.code, "CANONICAL_MAIN_DRIFT")

    def test_06_control_tower_scan_error_blocks_release(self) -> None:
        with patch("trusted_task_release.scan_repository", return_value={"errors": [{"code": "X"}]}):
            with self.assertRaises(TrustedReleaseError) as caught:
                evaluate()
        self.assertEqual(caught.exception.code, "CONTROL_TOWER_SCAN_FAILED")

    def test_07_claim_validation_error_blocks_release(self) -> None:
        with patch(
            "trusted_task_release.validate_claims",
            return_value={"errors": [{"code": "BROKEN"}], "claim_structural_check": "FAIL"},
        ):
            with self.assertRaises(TrustedReleaseError) as caught:
                evaluate()
        self.assertEqual(caught.exception.code, "WORK_CLAIM_VALIDATION_FAILED")

    def test_08_canonical_active_path_collision_wins_over_caller_omission(self) -> None:
        synthetic_claims = {"claims": [active_claim()]}
        with (
            patch("trusted_task_release.scan_repository", return_value={"errors": []}),
            patch(
                "trusted_task_release.validate_claims",
                return_value={"errors": [], "claim_structural_check": "PASS"},
            ),
            patch("trusted_task_release.load_yaml", return_value=synthetic_claims),
        ):
            receipt = evaluate()
        collision = receipt["impact_receipt"]["collision_analysis"][0]
        self.assertEqual(collision["task_id"], "ACTIVE-CANONICAL-WORK")
        self.assertEqual(collision["level"], "O3")
        self.assertEqual(receipt["impact_receipt"]["final_disposition"], "DEFER_DEPENDENCY")

    def test_09_canonical_active_authority_collision_is_o4(self) -> None:
        proposal = base_proposal()
        proposal["proposed_write_surface"]["authority_claims"] = [
            "CONTROL_TOWER_RELEASE_AUTHORITY"
        ]
        synthetic_claims = {"claims": [active_claim(authority=True)]}
        with (
            patch("trusted_task_release.scan_repository", return_value={"errors": []}),
            patch(
                "trusted_task_release.validate_claims",
                return_value={"errors": [], "claim_structural_check": "PASS"},
            ),
            patch("trusted_task_release.load_yaml", return_value=synthetic_claims),
        ):
            receipt = evaluate(proposal)
        self.assertEqual(receipt["impact_receipt"]["collision_analysis"][0]["level"], "O4")
        self.assertEqual(receipt["impact_receipt"]["final_disposition"], "ARCHITECTURE_CONFLICT")

    def test_10_incomplete_canonical_active_surface_fails_closed(self) -> None:
        claim = active_claim()
        del claim["interfaces"]
        with self.assertRaises(TrustedReleaseError) as caught:
            _materialize_active_work_items({"claims": [claim]})
        self.assertEqual(caught.exception.code, "CANONICAL_ACTIVE_CLAIM_SURFACE_INCOMPLETE")

    def test_11_repository_state_change_during_evaluation_fails_closed(self) -> None:
        head = git_head()
        with patch("trusted_task_release._head", side_effect=[head, "1" * 40]):
            with self.assertRaises(TrustedReleaseError) as caught:
                evaluate(expected=head)
        self.assertEqual(caught.exception.code, "TRUSTED_REPOSITORY_STATE_DRIFT")

    def test_12_receipt_remains_evidence_only(self) -> None:
        receipt = evaluate()
        boundary = receipt["authority_boundary"]
        self.assertTrue(boundary["evidence_only"])
        for field in (
            "creates_task",
            "creates_route",
            "creates_work_claim",
            "creates_worker_slot",
            "grants_execution_authority",
            "grants_domain_write",
            "grants_signal_write",
            "grants_w3_write",
            "grants_merge_authority",
        ):
            self.assertFalse(boundary[field])

    def test_13_same_state_is_deterministic_and_proposal_change_is_bound(self) -> None:
        first = evaluate()
        second = evaluate(copy.deepcopy(base_proposal()))
        self.assertEqual(first, second)
        changed = base_proposal()
        changed["desired_effect"] += " Changed intent."
        third = evaluate(changed)
        self.assertNotEqual(first["receipt_digest"], third["receipt_digest"])

    def test_14_repository_bound_r145_loader_restores_sys_path(self) -> None:
        before = list(sys.path)
        resolver, guard = _load_r145_api(REPO_ROOT)
        self.assertTrue(callable(resolver))
        self.assertTrue(callable(guard))
        self.assertEqual(sys.path, before)


if __name__ == "__main__":
    unittest.main()
