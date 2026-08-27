from __future__ import annotations

import copy
from pathlib import Path
from unittest.mock import patch
import unittest

from signal_opportunity_materializer import (
    DRAFT_SCHEMA,
    DECISION_SCHEMA,
    SignalOpportunityMaterializerError,
    _load_s0c_ledger_type,
    materialize_signal_opportunity,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MAIN = "a" * 40
OWNER_MAIN = "b" * 40
SIGNAL = "signal:r153-fixture"
OWNER_REPO = "vxz2datoubo/eustia-ai-film"


def signal_event() -> dict:
    return {
        "schema_version": "SignalEvent/v1",
        "event_id": "r153:event-1",
        "signal_id": SIGNAL,
        "event_type": "EXPLICIT_SIGNAL_CAPTURE",
        "signal_kind": "REQUIREMENT",
        "planning_state": "CAPTURED",
        "execution_state": "NOT_STARTED",
        "epistemic_state": "USER_EXPLICIT",
        "primary_domain": "AI_FILM_SYSTEM",
        "related_domains": ["SECOND_BRAIN_SYSTEM"],
        "authority_targets": [],
        "touch_set": ["OWNER_DOMAIN_RUNTIME_EVIDENCE"],
        "related_signal_refs": [],
        "supersedes_refs": [],
        "revokes_refs": [],
        "cross_domain_candidate": False,
        "event_source": "R136_EXPLICIT_INTAKE",
        "source_type": "CHATGPT_PUBLIC_SAFE_GITHUB_TRANSPORT",
        "source_actor": "AUTHORIZED_CHATGPT_WINDOW",
        "source_project": "EUSTIA_AI_FILM",
        "source_ref": "r147-transport://capture/r153-fixture",
        "summary_ref": "intent://r153-fixture",
        "payload_schema_ref": "SignalIntakeEnvelope/v1",
        "privacy_scope_ref": "PUBLIC_SAFE_METADATA_ONLY",
        "idempotency_key": "r136-envelope:r153-fixture",
        "occurred_at": "2026-08-27T00:00:00+00:00",
        "observed_at": "2026-08-27T00:00:00+00:00",
        "public_safe_metadata": {
            "intent_envelope": {
                "source_window_ref": "window://r153-test",
                "source_actor": "AUTHORIZED_CHATGPT_WINDOW",
                "source_project": "EUSTIA_AI_FILM",
                "original_intent_ref": "intent://r153-fixture",
                "public_safe_summary": "Prove real canonical directing execution.",
                "desired_effect": "Prove real canonical directing execution.",
                "problem_to_solve": "Plausible output must not masquerade as mechanism-backed execution.",
                "success_condition": "Canonical runtime evidence is present or verification fails closed.",
                "expected_problems": ["plausible imitation"],
                "risks": ["false verification"],
                "assumptions": [],
                "unknowns": [],
                "dependencies": [],
                "evidence_refs": ["github://owner/project-index"],
                "counterevidence_refs": [],
                "privacy_scope_ref": "PUBLIC_SAFE_METADATA_ONLY",
            },
            "route": {
                "execution_class": "GOVERNED_MISSION",
                "materiality_class": "MATERIAL",
                "persistence_class": "DURABLE_SIGNAL",
            },
        },
    }


def proposal() -> dict:
    return {
        "schema_version": "TaskReleaseProposal/v1",
        "release_candidate_id": "R153-FIXTURE",
        "source_signal_refs": [SIGNAL, "issue://465"],
        "signal_primary_domain": "AI_FILM_SYSTEM",
        "desired_effect": "Prove real canonical directing execution.",
        "proposed_target_domain": "AI_FILM_SYSTEM",
        "proposed_write_surface": {
            "write_paths": ["tools/runtime_evidence_probe.py"],
            "read_paths": ["PROJECT_INDEX.yaml"],
            "interfaces": [
                {"name": "DirectorLearningRuntime", "mode": "read", "frozen": True}
            ],
            "read_domains": ["AI_FILM_SYSTEM"],
            "write_domains": ["AI_FILM_SYSTEM"],
            "authority_claims": [],
        },
        "materiality": "MATERIAL",
        "risk": ["bounded reversible engineering"],
        "out_of_scope": ["production deploy", "secrets", "trading"],
        "capability_inventory": [
            {
                "component_id": "DirectorLearningRuntime",
                "decision": "EXTEND",
                "satisfies_requirement": False,
                "evidence_refs": ["github://owner/runtime"],
            }
        ],
        "relations": [
            {
                "relation": "EXTENDS",
                "source": "R153RuntimeEvidence",
                "target": "DirectorLearningRuntime",
                "evidence_refs": ["issue://465"],
            }
        ],
        "reverse_consumers": [
            {
                "consumer_id": "director-runtime-validation",
                "impact": "CONSUMER_REVALIDATION_ONLY",
                "evidence_refs": ["issue://465"],
            }
        ],
        "consumer_inventory_complete": True,
        "composition": {
            "optional": True,
            "can_compose": True,
            "core_invariant": False,
            "missing_capability_behavior": "ABSTAIN",
            "removal_preserves_unrelated_core": True,
            "justification": "Adds evidence binding without replacing runtime authority.",
        },
        "synchronized_change_set": [],
        "regression_revalidation_set": ["director-runtime-validation"],
        "unaffected_set": [
            {
                "component_id": "LearningAuthority",
                "evidence_refs": ["boundary://unchanged"],
            }
        ],
        "unresolved_unknowns": [],
    }


def draft() -> dict:
    return {
        "schema_version": DRAFT_SCHEMA,
        "signal_ref": SIGNAL,
        "owner_reconciliation_issue": 16,
        "priority_class": "P3_BOUNDED_IMPROVEMENT",
        "user_value_score": 90,
        "materiality_score": 85,
        "dependency_readiness_score": 90,
        "age_cycles": 2,
        "estimated_cost_score": 20,
        "task_release_proposal": proposal(),
    }


def owner_binding(valid: bool = True) -> dict:
    if not valid:
        return {"valid": False, "reason": "DOMAIN_ROUTE_UNRESOLVED", "authority_refs": []}
    return {
        "valid": True,
        "reason": "DOMAIN_CANONICAL_AUTHORITY_BOUND",
        "domain_id": "AI_FILM_SYSTEM",
        "project_id": "EUSTIA_AI_FILM",
        "repository": OWNER_REPO,
        "canonical_commit": OWNER_MAIN,
        "writeback_owner": "AI_FILM_SYSTEM",
        "authority_refs": ["domain-authority://AI_FILM_SYSTEM", "provider://r137/fixture"],
        "trusted_authority_refs": ["semantic-authority://fixture"],
        "provider_attribution_ref": "provider://r137/fixture",
        "binding_digest": "c" * 64,
        "legacy_compatibility": False,
    }


def r150_receipt(final: str = "RELEASE_AS_EXTENSION") -> dict:
    return {
        "schema_version": "TrustedTaskReleaseImpactReceipt/v1",
        "release_candidate_id": "R153-FIXTURE",
        "trusted_context": {"canonical_main": MAIN},
        "impact_receipt": {"final_disposition": final},
        "authority_boundary": {"evidence_only": True},
        "receipt_digest": "d" * 64,
    }


class FakeOwnerObserver:
    def __init__(self, *, body: str = "", issue_state: str = "open", main: str = OWNER_MAIN):
        self.body = body
        self.issue_state = issue_state
        self.main = main

    def _get_json(self, path: str):
        if path.endswith("/git/ref/heads/main"):
            return {}, {"object": {"sha": self.main}}, {}
        if path.endswith("/issues/16"):
            return {}, {
                "number": 16,
                "state": self.issue_state,
                "body": "",
                "html_url": f"https://github.com/{OWNER_REPO}/issues/16",
            }, {}
        if "/issues/16/comments?" in path:
            page = int(path.rsplit("page=", 1)[1])
            if page == 1 and self.body:
                return {}, [{
                    "id": 100,
                    "body": self.body,
                    "html_url": f"https://github.com/{OWNER_REPO}/issues/16#issuecomment-100",
                }], {}
            return {}, [], {}
        raise AssertionError(path)


def reuse_body() -> str:
    return f"""```yaml
schema: DURABLE_SIGNAL_OWNER_DOMAIN_REUSE_HANDOFF/v1
source_signal_id: {SIGNAL}
source_durable_receipt_id: durable-admission:fixture
source_proof_git_ref: signal-tower/ingress
owner_domain: EUSTIA_AI_FILM
existing_issue: 16
existing_pr: 17
existing_exact_head: {'e' * 40}
current_main: {OWNER_MAIN}
review_queue: 15
review_state: WAITING_REVIEW
reconciliation: REUSE_EXTEND_EXISTING_WORK
new_issue_required: false
new_pr_required: false
```"""


def generic_body(disposition: str, *, dependency_ready: bool = False, work_refs: str = "") -> str:
    extra = f"\nwork_refs: {work_refs}" if work_refs else ""
    return f"""```yaml
schema: SIGNAL_OWNER_RECONCILIATION/v1
signal_id: {SIGNAL}
owner_domain: AI_FILM_SYSTEM
owner_main: {OWNER_MAIN}
disposition: {disposition}
dependency_ready: {'true' if dependency_ready else 'false'}{extra}
```"""


class SignalOpportunityMaterializerTests(unittest.TestCase):
    def setUp(self) -> None:
        ledger_type = _load_s0c_ledger_type(REPO_ROOT)
        self.ledger = ledger_type(":memory:")
        result = self.ledger.ingest_raw(signal_event())
        self.assertEqual(result["status"], "ADMITTED")

    def tearDown(self) -> None:
        self.ledger.close()

    def run_materializer(
        self,
        *,
        draft_value: dict | None = None,
        observer: FakeOwnerObserver | None = None,
        binding: dict | None = None,
        receipt: dict | None = None,
    ) -> dict:
        draft_value = copy.deepcopy(draft_value or draft())
        observer = observer or FakeOwnerObserver(body=reuse_body())
        binding = copy.deepcopy(binding if binding is not None else owner_binding())
        receipt = copy.deepcopy(receipt or r150_receipt())
        with (
            patch("signal_opportunity_materializer._git_head", return_value=MAIN),
            patch("signal_opportunity_materializer._resolve_owner_authority", return_value=binding),
            patch("signal_opportunity_materializer.evaluate_trusted_release_proposal", return_value=receipt),
        ):
            return materialize_signal_opportunity(
                REPO_ROOT,
                self.ledger,
                draft_value,
                expected_coordinator_main=MAIN,
                domain_authority_descriptors=[],
                domain_authority_observations=[],
                owner_observer=observer,
            )

    def test_01_fake_ledger_cannot_substitute_for_canonical_s0c(self) -> None:
        fake = object()
        with patch("signal_opportunity_materializer._git_head", return_value=MAIN):
            result = materialize_signal_opportunity(
                REPO_ROOT,
                fake,
                draft(),
                expected_coordinator_main=MAIN,
                domain_authority_descriptors=[],
                domain_authority_observations=[],
            )
        self.assertEqual(result["disposition"], "INELIGIBLE_SIGNAL_STATE")
        self.assertEqual(result["reason"], "CANONICAL_S0C_LEDGER_INSTANCE_REQUIRED")

    def test_02_transport_event_mapping_alone_is_not_s0c(self) -> None:
        with patch("signal_opportunity_materializer._git_head", return_value=MAIN):
            result = materialize_signal_opportunity(
                REPO_ROOT,
                {"event": signal_event()},
                draft(),
                expected_coordinator_main=MAIN,
                domain_authority_descriptors=[],
                domain_authority_observations=[],
            )
        self.assertEqual(result["reason"], "CANONICAL_S0C_LEDGER_INSTANCE_REQUIRED")

    def test_03_stale_projection_watermark_fails_closed(self) -> None:
        original = self.ledger.current_projection
        projection = copy.deepcopy(original())
        projection["ledger_watermark"] += 1
        with (
            patch.object(self.ledger, "current_projection", return_value=projection),
            patch("signal_opportunity_materializer._git_head", return_value=MAIN),
        ):
            result = materialize_signal_opportunity(
                REPO_ROOT,
                self.ledger,
                draft(),
                expected_coordinator_main=MAIN,
                domain_authority_descriptors=[],
                domain_authority_observations=[],
            )
        self.assertEqual(result["reason"], "S0C_LEDGER_WATERMARK_MISMATCH")

    def test_04_non_not_started_signal_cannot_materialize(self) -> None:
        projection = copy.deepcopy(self.ledger.current_projection())
        projection["signals"][0]["execution_state"] = "DONE"
        with (
            patch.object(self.ledger, "current_projection", return_value=projection),
            patch("signal_opportunity_materializer._git_head", return_value=MAIN),
        ):
            result = materialize_signal_opportunity(
                REPO_ROOT,
                self.ledger,
                draft(),
                expected_coordinator_main=MAIN,
                domain_authority_descriptors=[],
                domain_authority_observations=[],
            )
        self.assertEqual(result["reason"], "S0C_SIGNAL_EXECUTION_STATE_INELIGIBLE")

    def test_05_needs_revalidation_epistemic_state_cannot_materialize(self) -> None:
        projection = copy.deepcopy(self.ledger.current_projection())
        projection["signals"][0]["epistemic_state"] = "NEEDS_REVALIDATION"
        with (
            patch.object(self.ledger, "current_projection", return_value=projection),
            patch("signal_opportunity_materializer._git_head", return_value=MAIN),
        ):
            result = materialize_signal_opportunity(
                REPO_ROOT,
                self.ledger,
                draft(),
                expected_coordinator_main=MAIN,
                domain_authority_descriptors=[],
                domain_authority_observations=[],
            )
        self.assertEqual(result["reason"], "S0C_SIGNAL_EPISTEMIC_STATE_INELIGIBLE")

    def test_06_current_coordinator_main_is_required_even_for_reuse(self) -> None:
        with patch("signal_opportunity_materializer._git_head", return_value="f" * 40):
            with self.assertRaisesRegex(SignalOpportunityMaterializerError, "CANONICAL_MAIN_DRIFT"):
                materialize_signal_opportunity(
                    REPO_ROOT,
                    self.ledger,
                    draft(),
                    expected_coordinator_main=MAIN,
                    domain_authority_descriptors=[],
                    domain_authority_observations=[],
                )

    def test_07_unresolved_owner_authority_needs_revalidation(self) -> None:
        result = self.run_materializer(binding=owner_binding(False))
        self.assertEqual(result["disposition"], "NEEDS_REVALIDATION")
        self.assertEqual(result["reason"], "DOMAIN_ROUTE_UNRESOLVED")

    def test_08_ai_film_dogfood_exact_backlink_reuses_existing_work(self) -> None:
        with patch("signal_opportunity_materializer.evaluate_trusted_release_proposal") as r150:
            with (
                patch("signal_opportunity_materializer._git_head", return_value=MAIN),
                patch("signal_opportunity_materializer._resolve_owner_authority", return_value=owner_binding()),
            ):
                result = materialize_signal_opportunity(
                    REPO_ROOT,
                    self.ledger,
                    draft(),
                    expected_coordinator_main=MAIN,
                    domain_authority_descriptors=[],
                    domain_authority_observations=[],
                    owner_observer=FakeOwnerObserver(body=reuse_body()),
                )
        self.assertEqual(result["disposition"], "REUSE_EXISTING_OWNER_WORK")
        self.assertIn("issuecomment-100", " ".join(result["evidence_refs"]))
        r150.assert_not_called()

    def test_09_reuse_record_is_stale_after_owner_issue_closes(self) -> None:
        result = self.run_materializer(
            observer=FakeOwnerObserver(body=reuse_body(), issue_state="closed")
        )
        self.assertEqual(result["disposition"], "NEEDS_REVALIDATION")
        self.assertEqual(result["reason"], "OWNER_REUSE_RECORD_STALE_AFTER_ISSUE_CLOSED")

    def test_10_satisfied_record_requires_closed_owner_issue(self) -> None:
        result = self.run_materializer(
            observer=FakeOwnerObserver(body=generic_body("ALREADY_SATISFIED"), issue_state="open")
        )
        self.assertEqual(result["disposition"], "NEEDS_REVALIDATION")
        self.assertEqual(result["reason"], "OWNER_SATISFIED_RECORD_REQUIRES_CLOSED_ISSUE")

    def test_11_satisfied_closed_owner_issue_produces_no_opportunity(self) -> None:
        result = self.run_materializer(
            observer=FakeOwnerObserver(body=generic_body("ALREADY_SATISFIED"), issue_state="closed")
        )
        self.assertEqual(result["disposition"], "ALREADY_SATISFIED")
        self.assertIsNone(result["opportunity"])

    def test_12_no_exact_signal_reconciliation_record_needs_revalidation(self) -> None:
        result = self.run_materializer(observer=FakeOwnerObserver(body="unrelated"))
        self.assertEqual(result["disposition"], "NEEDS_REVALIDATION")
        self.assertEqual(result["reason"], "OWNER_EXACT_SIGNAL_RECONCILIATION_RECORD_REQUIRED")

    def test_13_owner_main_drift_needs_revalidation(self) -> None:
        result = self.run_materializer(
            observer=FakeOwnerObserver(body=reuse_body(), main="f" * 40)
        )
        self.assertEqual(result["reason"], "OWNER_MAIN_DRIFT")

    def test_14_gap_with_existing_work_refs_needs_revalidation(self) -> None:
        result = self.run_materializer(
            observer=FakeOwnerObserver(
                body=generic_body("GAP_PROVEN", dependency_ready=True, work_refs="github://pr/17")
            )
        )
        self.assertEqual(result["reason"], "OWNER_GAP_CONFLICTS_WITH_EXISTING_WORK_REFS")

    def test_15_gap_without_dependency_readiness_needs_revalidation(self) -> None:
        result = self.run_materializer(
            observer=FakeOwnerObserver(body=generic_body("GAP_PROVEN", dependency_ready=False))
        )
        self.assertEqual(result["reason"], "OWNER_GAP_DEPENDENCY_NOT_READY")

    def test_16_planner_cannot_mutate_signal_domain(self) -> None:
        value = draft()
        value["task_release_proposal"]["signal_primary_domain"] = "SHARED_COGNITIVE_OS"
        result = self.run_materializer(
            draft_value=value,
            observer=FakeOwnerObserver(body=generic_body("GAP_PROVEN", dependency_ready=True)),
        )
        self.assertEqual(result["reason"], "PLANNER_SIGNAL_DOMAIN_MUTATION_FORBIDDEN")

    def test_17_cross_domain_auto_materialization_is_forbidden(self) -> None:
        value = draft()
        value["task_release_proposal"]["proposed_target_domain"] = "SHARED_COGNITIVE_OS"
        result = self.run_materializer(
            draft_value=value,
            observer=FakeOwnerObserver(body=generic_body("GAP_PROVEN", dependency_ready=True)),
        )
        self.assertEqual(result["reason"], "CROSS_DOMAIN_AUTO_MATERIALIZATION_FORBIDDEN")

    def test_18_planner_cannot_mutate_desired_effect(self) -> None:
        value = draft()
        value["task_release_proposal"]["desired_effect"] = "different goal"
        result = self.run_materializer(
            draft_value=value,
            observer=FakeOwnerObserver(body=generic_body("GAP_PROVEN", dependency_ready=True)),
        )
        self.assertEqual(result["reason"], "PLANNER_DESIRED_EFFECT_MUTATION_FORBIDDEN")

    def test_19_standing_exclusion_blocks_high_risk_surface(self) -> None:
        value = draft()
        value["task_release_proposal"]["proposed_write_surface"]["write_paths"] = ["production/deploy.py"]
        result = self.run_materializer(
            draft_value=value,
            observer=FakeOwnerObserver(body=generic_body("GAP_PROVEN", dependency_ready=True)),
        )
        self.assertEqual(result["disposition"], "INELIGIBLE_SIGNAL_STATE")
        self.assertEqual(result["reason"], "R151_STANDING_AUTO_RELEASE_EXCLUSION")

    def test_20_r150_nonreleaseable_disposition_blocks_materialization(self) -> None:
        result = self.run_materializer(
            observer=FakeOwnerObserver(body=generic_body("GAP_PROVEN", dependency_ready=True)),
            receipt=r150_receipt("NO_RELEASE_REUSE_EXISTING"),
        )
        self.assertEqual(result["disposition"], "NEEDS_REVALIDATION")
        self.assertIn("R150_NOT_RELEASEABLE", result["reason"])

    def test_21_valid_gap_materializes_exact_r151_opportunity(self) -> None:
        result = self.run_materializer(
            observer=FakeOwnerObserver(body=generic_body("GAP_PROVEN", dependency_ready=True))
        )
        self.assertEqual(result["disposition"], "MATERIALIZED_FOR_R151")
        opportunity = result["opportunity"]
        self.assertEqual(opportunity["schema_version"], "DigestedSignalOpportunity/v1")
        self.assertEqual(opportunity["signal_ref"], SIGNAL)
        self.assertEqual(opportunity["desired_effect"], signal_event()["public_safe_metadata"]["intent_envelope"]["desired_effect"])
        self.assertTrue(opportunity["desired_effect_gap_proven"])
        self.assertTrue(opportunity["dependency_ready"])
        self.assertIn("r150://receipt/", " ".join(opportunity["source_evidence_refs"]))

    def test_22_materialization_is_deterministic_for_same_inputs(self) -> None:
        kwargs = dict(
            observer=FakeOwnerObserver(body=generic_body("GAP_PROVEN", dependency_ready=True))
        )
        first = self.run_materializer(**kwargs)
        second = self.run_materializer(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(first["decision_digest"], second["decision_digest"])

    def test_23_materializer_decision_never_grants_mutation_authority(self) -> None:
        result = self.run_materializer(
            observer=FakeOwnerObserver(body=generic_body("GAP_PROVEN", dependency_ready=True))
        )
        self.assertEqual(result["schema_version"], DECISION_SCHEMA)
        boundary = result["authority_boundary"]
        self.assertTrue(boundary)
        self.assertFalse(any(boundary.values()))


if __name__ == "__main__":
    unittest.main()
