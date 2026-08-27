from __future__ import annotations

import copy
from pathlib import Path
from unittest.mock import patch
import unittest

from signal_opportunity_materializer import (
    DRAFT_SCHEMA,
    DECISION_SCHEMA,
    SignalOpportunityMaterializerError,
    TRUSTED_NEUTRAL_RANKING,
    _load_s0c_ledger_type,
    materialize_signal_opportunity,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MAIN = "a" * 40
OWNER_MAIN = "b" * 40
OWNER_HEAD = "e" * 40
SIGNAL = "signal:r153-fixture"
OWNER_REPO = "vxz2datoubo/eustia-ai-film"
OWNER_PROJECT = "EUSTIA_AI_FILM"
OWNER_DOMAIN = "AI_FILM_SYSTEM"


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
        "primary_domain": OWNER_DOMAIN,
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
        "source_project": OWNER_PROJECT,
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
                "source_project": OWNER_PROJECT,
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


def status_event(*, execution: str = "NOT_STARTED", epistemic: str = "USER_EXPLICIT") -> dict:
    value = signal_event()
    value.update(
        event_id=f"r153:status:{execution}:{epistemic}",
        event_type="SIGNAL_STATUS_UPDATE",
        signal_kind="STATUS",
        execution_state=execution,
        epistemic_state=epistemic,
        idempotency_key=f"r153-status:{execution}:{epistemic}",
        occurred_at="2026-08-27T00:01:00+00:00",
        observed_at="2026-08-27T00:01:00+00:00",
        public_safe_metadata={},
    )
    return value


def proposal() -> dict:
    return {
        "schema_version": "TaskReleaseProposal/v1",
        "release_candidate_id": "R153-FIXTURE",
        "source_signal_refs": [SIGNAL, "issue://465"],
        "signal_primary_domain": OWNER_DOMAIN,
        "desired_effect": "Prove real canonical directing execution.",
        "proposed_target_domain": OWNER_DOMAIN,
        "proposed_write_surface": {
            "write_paths": ["tools/runtime_evidence_probe.py"],
            "read_paths": ["PROJECT_INDEX.yaml"],
            "interfaces": [
                {"name": "DirectorLearningRuntime", "mode": "read", "frozen": True}
            ],
            "read_domains": [OWNER_DOMAIN],
            "write_domains": [OWNER_DOMAIN],
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
        "priority_class": "P4_RESEARCH",
        "user_value_score": 99,
        "materiality_score": 98,
        "dependency_readiness_score": 97,
        "age_cycles": 999,
        "estimated_cost_score": 1,
        "task_release_proposal": proposal(),
    }


def owner_binding(valid: bool = True) -> dict:
    if not valid:
        return {"valid": False, "reason": "DOMAIN_ROUTE_UNRESOLVED", "authority_refs": []}
    return {
        "valid": True,
        "reason": "DOMAIN_CANONICAL_AUTHORITY_BOUND",
        "domain_id": OWNER_DOMAIN,
        "project_id": OWNER_PROJECT,
        "repository": OWNER_REPO,
        "canonical_commit": OWNER_MAIN,
        "writeback_owner": OWNER_DOMAIN,
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


def trusted_record(body: str, comment_id: int = 100) -> dict:
    return {
        "id": comment_id,
        "body": body,
        "html_url": f"https://github.com/{OWNER_REPO}/issues/16#issuecomment-{comment_id}",
        "user": {"login": "vxz1datoubo"},
        "author_association": "COLLABORATOR",
        "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
    }


def untrusted_record(body: str, comment_id: int = 101) -> dict:
    return {
        "id": comment_id,
        "body": body,
        "html_url": f"https://github.com/{OWNER_REPO}/issues/16#issuecomment-{comment_id}",
        "user": {"login": "random-user"},
        "author_association": "NONE",
        "performed_via_github_app": None,
    }


def reuse_body(*, exact_head: str = OWNER_HEAD, review_state: str = "WAITING_REVIEW") -> str:
    return f"""```yaml
schema: DURABLE_SIGNAL_OWNER_DOMAIN_REUSE_HANDOFF/v1
source_signal_id: {SIGNAL}
source_durable_receipt_id: durable-admission:fixture
source_proof_git_ref: signal-tower/ingress
owner_domain: {OWNER_PROJECT}
existing_issue: 16
existing_pr: 17
existing_exact_head: {exact_head}
current_main: {OWNER_MAIN}
review_queue: 15
review_state: {review_state}
reconciliation: REUSE_EXTEND_EXISTING_WORK
new_issue_required: false
new_pr_required: false
```"""


def generic_body(
    disposition: str,
    *,
    dependency_ready: bool = False,
    work_refs: str = "",
    reconciliation_issue: int = 16,
) -> str:
    extra = f"\nwork_refs: {work_refs}" if work_refs else ""
    return f"""```yaml
schema: SIGNAL_OWNER_RECONCILIATION/v1
signal_id: {SIGNAL}
owner_domain: {OWNER_DOMAIN}
owner_main: {OWNER_MAIN}
reconciliation_issue: {reconciliation_issue}
disposition: {disposition}
dependency_ready: {'true' if dependency_ready else 'false'}{extra}
```"""


def review_request_body(*, head: str = OWNER_HEAD) -> str:
    return f"""```yaml
schema: REVIEW_REQUEST/v1
project: {OWNER_PROJECT}
pr: 17
issue: 16
exact_head: {head}
base_branch: main
base_sha_at_request: {OWNER_MAIN}
status: WAITING_REVIEW
priority: 1
```"""


def review_result_body(verdict: str = "ACCEPT", *, head: str = OWNER_HEAD) -> str:
    return f"""```yaml
schema: REVIEW_RESULT/v1
project: {OWNER_PROJECT}
pr: 17
reviewed_head: {head}
verdict: {verdict}
review_evidence_ref: review://fixture
```"""


class FakeOwnerObserver:
    def __init__(
        self,
        *,
        records: list[dict] | None = None,
        issue_number: int = 16,
        issue_state: str = "open",
        main: str = OWNER_MAIN,
        referenced_issue_state: str = "open",
        pr_state: str = "open",
        pr_head: str = OWNER_HEAD,
        pr_base: str = OWNER_MAIN,
        merged_at=None,
        review_records: list[dict] | None = None,
        review_queue_state: str = "open",
    ) -> None:
        self.records = records if records is not None else [trusted_record(reuse_body())]
        self.issue_number = issue_number
        self.issue_state = issue_state
        self.main = main
        self.referenced_issue_state = referenced_issue_state
        self.pr_state = pr_state
        self.pr_head = pr_head
        self.pr_base = pr_base
        self.merged_at = merged_at
        self.review_records = review_records if review_records is not None else [
            trusted_record(review_request_body(), comment_id=200)
        ]
        self.review_queue_state = review_queue_state

    @staticmethod
    def _trusted_issue(number: int, state: str, body: str = "") -> dict:
        return {
            "number": number,
            "state": state,
            "body": body,
            "html_url": f"https://github.com/{OWNER_REPO}/issues/{number}",
            "user": {"login": "vxz1datoubo"},
            "author_association": "COLLABORATOR",
            "performed_via_github_app": {"slug": "chatgpt-codex-connector"},
        }

    def _get_json(self, path: str):
        if path.endswith("/git/ref/heads/main"):
            return {}, {"object": {"sha": self.main}}, {}
        if path.endswith(f"/issues/{self.issue_number}"):
            state = self.referenced_issue_state if self.issue_number == 16 else self.issue_state
            return {}, self._trusted_issue(self.issue_number, state), {}
        if path.endswith("/issues/15"):
            return {}, self._trusted_issue(15, self.review_queue_state), {}
        if path.endswith("/pulls/17"):
            return {}, {
                "number": 17,
                "state": self.pr_state,
                "merged_at": self.merged_at,
                "head": {"sha": self.pr_head},
                "base": {"ref": "main", "sha": self.pr_base},
            }, {}
        if f"/issues/{self.issue_number}/comments?" in path:
            page = int(path.rsplit("page=", 1)[1])
            return {}, list(self.records) if page == 1 else [], {}
        if "/issues/15/comments?" in path:
            page = int(path.rsplit("page=", 1)[1])
            return {}, list(self.review_records) if page == 1 else [], {}
        raise AssertionError(path)


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
        observer = observer or FakeOwnerObserver()
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
        with patch("signal_opportunity_materializer._git_head", return_value=MAIN):
            result = materialize_signal_opportunity(
                REPO_ROOT,
                object(),
                draft(),
                expected_coordinator_main=MAIN,
                domain_authority_descriptors=[],
                domain_authority_observations=[],
            )
        self.assertEqual(result["disposition"], "INELIGIBLE_SIGNAL_STATE")
        self.assertEqual(result["reason"], "CANONICAL_S0C_LEDGER_INSTANCE_REQUIRED")

    def test_02_transport_mapping_alone_is_not_s0c(self) -> None:
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

    def test_03_missing_projection_does_not_mutate_s0c_to_recover(self) -> None:
        self.ledger.discard_projection_for_recovery_test()
        with patch("signal_opportunity_materializer._git_head", return_value=MAIN):
            result = materialize_signal_opportunity(
                REPO_ROOT,
                self.ledger,
                draft(),
                expected_coordinator_main=MAIN,
                domain_authority_descriptors=[],
                domain_authority_observations=[],
            )
        self.assertEqual(result["reason"], "S0C_PROJECTION_REQUIRED")
        self.assertIsNone(self.ledger.current_projection())

    def test_04_same_revision_projection_content_tamper_fails_replay(self) -> None:
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
        self.assertEqual(result["reason"], "S0C_PROJECTION_REPLAY_MISMATCH")

    def test_05_projection_checksum_tamper_fails_closed(self) -> None:
        projection = copy.deepcopy(self.ledger.current_projection())
        projection["checksum"] = "f" * 64
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
        self.assertEqual(result["reason"], "S0C_PROJECTION_CHECKSUM_MISMATCH")

    def test_06_blocked_signal_cannot_materialize(self) -> None:
        self.assertEqual(self.ledger.ingest_raw(status_event(execution="BLOCKED"))["status"], "ADMITTED")
        result = self.run_materializer()
        self.assertEqual(result["reason"], "S0C_SIGNAL_EXECUTION_STATE_INELIGIBLE")

    def test_07_needs_revalidation_signal_cannot_materialize(self) -> None:
        self.assertEqual(
            self.ledger.ingest_raw(status_event(epistemic="NEEDS_REVALIDATION"))["status"],
            "ADMITTED",
        )
        result = self.run_materializer()
        self.assertEqual(result["reason"], "S0C_SIGNAL_EPISTEMIC_STATE_INELIGIBLE")

    def test_08_current_coordinator_main_required(self) -> None:
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

    def test_09_unresolved_owner_authority_needs_revalidation(self) -> None:
        result = self.run_materializer(binding=owner_binding(False))
        self.assertEqual(result["disposition"], "NEEDS_REVALIDATION")
        self.assertEqual(result["reason"], "DOMAIN_ROUTE_UNRESOLVED")

    def test_10_ai_film_exact_backlink_reuses_only_current_work(self) -> None:
        observer = FakeOwnerObserver()
        with (
            patch("signal_opportunity_materializer._git_head", return_value=MAIN),
            patch("signal_opportunity_materializer._resolve_owner_authority", return_value=owner_binding()),
            patch("signal_opportunity_materializer.evaluate_trusted_release_proposal") as r150,
        ):
            result = materialize_signal_opportunity(
                REPO_ROOT,
                self.ledger,
                draft(),
                expected_coordinator_main=MAIN,
                domain_authority_descriptors=[],
                domain_authority_observations=[],
                owner_observer=observer,
            )
        self.assertEqual(result["disposition"], "REUSE_EXISTING_OWNER_WORK")
        self.assertEqual(result["reason"], "EXACT_CURRENT_OWNER_WORK_VERIFIED")
        r150.assert_not_called()

    def test_11_untrusted_gap_comment_cannot_mint_gap(self) -> None:
        observer = FakeOwnerObserver(records=[untrusted_record(generic_body("GAP_PROVEN", dependency_ready=True))])
        result = self.run_materializer(observer=observer)
        self.assertEqual(result["disposition"], "NEEDS_REVALIDATION")
        self.assertEqual(result["reason"], "OWNER_RECONCILIATION_UNTRUSTED_PROVENANCE")

    def test_12_later_untrusted_comment_cannot_override_trusted_reuse(self) -> None:
        observer = FakeOwnerObserver(
            records=[
                trusted_record(reuse_body(), 100),
                untrusted_record(generic_body("GAP_PROVEN", dependency_ready=True), 999),
            ]
        )
        result = self.run_materializer(observer=observer)
        self.assertEqual(result["disposition"], "REUSE_EXISTING_OWNER_WORK")

    def test_13_unrelated_caller_selected_issue_cannot_mint_generic_gap(self) -> None:
        value = draft()
        value["owner_reconciliation_issue"] = 99
        observer = FakeOwnerObserver(
            issue_number=99,
            records=[trusted_record(generic_body("GAP_PROVEN", dependency_ready=True, reconciliation_issue=16))],
        )
        result = self.run_materializer(draft_value=value, observer=observer)
        self.assertEqual(result["disposition"], "NEEDS_REVALIDATION")
        self.assertEqual(result["reason"], "OWNER_RECONCILIATION_CONTAINER_UNBOUND")

    def test_14_referenced_pr_closed_needs_revalidation(self) -> None:
        result = self.run_materializer(observer=FakeOwnerObserver(pr_state="closed"))
        self.assertEqual(result["reason"], "OWNER_REFERENCED_PR_NOT_OPEN")

    def test_15_referenced_pr_head_moved_needs_revalidation(self) -> None:
        result = self.run_materializer(observer=FakeOwnerObserver(pr_head="f" * 40))
        self.assertEqual(result["reason"], "OWNER_REFERENCED_PR_HEAD_DRIFT")

    def test_16_referenced_pr_base_drift_needs_revalidation(self) -> None:
        result = self.run_materializer(observer=FakeOwnerObserver(pr_base="f" * 40))
        self.assertEqual(result["reason"], "OWNER_REFERENCED_PR_BASE_DRIFT")

    def test_17_referenced_issue_closed_needs_revalidation(self) -> None:
        result = self.run_materializer(observer=FakeOwnerObserver(referenced_issue_state="closed"))
        self.assertEqual(result["reason"], "OWNER_REFERENCED_ISSUE_NOT_OPEN")

    def test_18_review_ticket_head_moved_needs_revalidation(self) -> None:
        observer = FakeOwnerObserver(
            review_records=[trusted_record(review_request_body(head="f" * 40), 200)]
        )
        result = self.run_materializer(observer=observer)
        self.assertEqual(result["reason"], "OWNER_REVIEW_LINEAGE_STALE_HEAD")

    def test_19_review_ticket_result_makes_waiting_handoff_stale(self) -> None:
        observer = FakeOwnerObserver(
            review_records=[
                trusted_record(review_request_body(), 200),
                trusted_record(review_result_body("ACCEPT"), 201),
            ]
        )
        result = self.run_materializer(observer=observer)
        self.assertEqual(result["reason"], "OWNER_REVIEW_LINEAGE_STATE_DRIFT")

    def test_20_no_exact_reconciliation_record_needs_revalidation(self) -> None:
        result = self.run_materializer(observer=FakeOwnerObserver(records=[]))
        self.assertEqual(result["reason"], "OWNER_EXACT_SIGNAL_RECONCILIATION_RECORD_REQUIRED")

    def test_21_owner_main_drift_needs_revalidation(self) -> None:
        result = self.run_materializer(observer=FakeOwnerObserver(main="f" * 40))
        self.assertEqual(result["reason"], "OWNER_MAIN_DRIFT")

    def test_22_satisfied_record_requires_closed_reconciliation_issue(self) -> None:
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("ALREADY_SATISFIED"))],
            issue_state="open",
        )
        result = self.run_materializer(observer=observer)
        self.assertEqual(result["reason"], "OWNER_SATISFIED_RECORD_REQUIRES_CLOSED_ISSUE")

    def test_23_satisfied_closed_issue_produces_no_opportunity(self) -> None:
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("ALREADY_SATISFIED"))],
            referenced_issue_state="closed",
        )
        result = self.run_materializer(observer=observer)
        self.assertEqual(result["disposition"], "ALREADY_SATISFIED")
        self.assertIsNone(result["opportunity"])

    def test_24_gap_with_work_refs_needs_revalidation(self) -> None:
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("GAP_PROVEN", dependency_ready=True, work_refs="github://pr/17"))]
        )
        result = self.run_materializer(observer=observer)
        self.assertEqual(result["reason"], "OWNER_GAP_CONFLICTS_WITH_EXISTING_WORK_REFS")

    def test_25_gap_without_dependency_readiness_needs_revalidation(self) -> None:
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("GAP_PROVEN", dependency_ready=False))]
        )
        result = self.run_materializer(observer=observer)
        self.assertEqual(result["reason"], "OWNER_GAP_DEPENDENCY_NOT_READY")

    def test_26_planner_cannot_mutate_signal_domain(self) -> None:
        value = draft()
        value["task_release_proposal"]["signal_primary_domain"] = "SHARED_COGNITIVE_OS"
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("GAP_PROVEN", dependency_ready=True))]
        )
        result = self.run_materializer(draft_value=value, observer=observer)
        self.assertEqual(result["reason"], "PLANNER_SIGNAL_DOMAIN_MUTATION_FORBIDDEN")

    def test_27_cross_domain_auto_materialization_forbidden(self) -> None:
        value = draft()
        value["task_release_proposal"]["proposed_target_domain"] = "SHARED_COGNITIVE_OS"
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("GAP_PROVEN", dependency_ready=True))]
        )
        result = self.run_materializer(draft_value=value, observer=observer)
        self.assertEqual(result["reason"], "CROSS_DOMAIN_AUTO_MATERIALIZATION_FORBIDDEN")

    def test_28_planner_cannot_mutate_desired_effect(self) -> None:
        value = draft()
        value["task_release_proposal"]["desired_effect"] = "different goal"
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("GAP_PROVEN", dependency_ready=True))]
        )
        result = self.run_materializer(draft_value=value, observer=observer)
        self.assertEqual(result["reason"], "PLANNER_DESIRED_EFFECT_MUTATION_FORBIDDEN")

    def test_29_standing_exclusion_blocks_high_risk_surface(self) -> None:
        value = draft()
        value["task_release_proposal"]["proposed_write_surface"]["write_paths"] = ["production/deploy.py"]
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("GAP_PROVEN", dependency_ready=True))]
        )
        result = self.run_materializer(draft_value=value, observer=observer)
        self.assertEqual(result["disposition"], "INELIGIBLE_SIGNAL_STATE")
        self.assertEqual(result["reason"], "R151_STANDING_AUTO_RELEASE_EXCLUSION")

    def test_30_r150_nonreleaseable_disposition_blocks_materialization(self) -> None:
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("GAP_PROVEN", dependency_ready=True))]
        )
        result = self.run_materializer(
            observer=observer,
            receipt=r150_receipt("NO_RELEASE_REUSE_EXISTING"),
        )
        self.assertEqual(result["disposition"], "NEEDS_REVALIDATION")
        self.assertIn("R150_NOT_RELEASEABLE", result["reason"])

    def test_31_valid_gap_materializes_r151_opportunity(self) -> None:
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("GAP_PROVEN", dependency_ready=True))]
        )
        result = self.run_materializer(observer=observer)
        self.assertEqual(result["disposition"], "MATERIALIZED_FOR_R151")
        opportunity = result["opportunity"]
        self.assertEqual(opportunity["schema_version"], "DigestedSignalOpportunity/v1")
        self.assertEqual(opportunity["signal_ref"], SIGNAL)
        self.assertTrue(opportunity["desired_effect_gap_proven"])
        self.assertTrue(opportunity["dependency_ready"])
        for key, expected in TRUSTED_NEUTRAL_RANKING.items():
            self.assertEqual(opportunity[key], expected)
        self.assertIn("r150://receipt/", " ".join(opportunity["source_evidence_refs"]))

    def test_32_caller_score_inflation_cannot_change_authority_bearing_opportunity(self) -> None:
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("GAP_PROVEN", dependency_ready=True))]
        )
        low = draft()
        low.update(
            priority_class="P3_BOUNDED_IMPROVEMENT",
            user_value_score=0,
            materiality_score=0,
            dependency_readiness_score=0,
            age_cycles=0,
            estimated_cost_score=100,
        )
        high = draft()
        high.update(
            priority_class="P4_RESEARCH",
            user_value_score=100,
            materiality_score=100,
            dependency_readiness_score=100,
            age_cycles=1_000_000,
            estimated_cost_score=0,
        )
        first = self.run_materializer(draft_value=low, observer=observer)
        second = self.run_materializer(draft_value=high, observer=observer)
        self.assertEqual(first["opportunity"], second["opportunity"])
        self.assertEqual(first["decision_digest"], second["decision_digest"])

    def test_33_materialization_is_deterministic_for_same_inputs(self) -> None:
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("GAP_PROVEN", dependency_ready=True))]
        )
        first = self.run_materializer(observer=observer)
        second = self.run_materializer(observer=observer)
        self.assertEqual(first, second)

    def test_34_decision_never_grants_mutation_authority(self) -> None:
        observer = FakeOwnerObserver(
            records=[trusted_record(generic_body("GAP_PROVEN", dependency_ready=True))]
        )
        result = self.run_materializer(observer=observer)
        self.assertEqual(result["schema_version"], DECISION_SCHEMA)
        self.assertTrue(result["authority_boundary"])
        self.assertFalse(any(result["authority_boundary"].values()))


if __name__ == "__main__":
    unittest.main()
