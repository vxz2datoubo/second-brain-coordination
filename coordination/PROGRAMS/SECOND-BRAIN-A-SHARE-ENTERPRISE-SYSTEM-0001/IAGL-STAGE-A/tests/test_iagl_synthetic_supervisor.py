"""Frozen canonical IAGL-E001..E018 plus R141 B09-B12 regressions."""
from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
from iagl_synthetic_supervisor import (  # noqa: E402
    _ALLOWED, Checkpoint, Decision, GovernanceMode, ImprovementSlice, LeaseGrant,
    Priority, ReconciliationSnapshot, RetrievalCompletenessProof, ReviewEvidence,
    ReviewWorkIdentity, SupervisorError, SupervisorState, SyntheticSupervisor,
    WorkingStateStore, digest,
)

REPO = "vxz2datoubo/second-brain-coordination"
PATHS = ("synthetic/allowed.py",)
RESUME_PRECONDITIONS = ("FRESH_RECONCILIATION", "AUTONOMOUS", "NO_PENDING_P0", "MATCHING_SLICE", "NEW_FENCE")


class CanonicalStageAEvaluations(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = WorkingStateStore(Path(self.temp.name) / "state.sqlite")
        self.sup = SyntheticSupervisor(REPO, self.store, budget_limit=10, no_value_limit=10)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def snap(self, head: str = "A", **overrides: object) -> ReconciliationSnapshot:
        data: dict[str, object] = {
            "repository": REPO, "exact_head": head, "route_id": "R141",
            "governance_mode": GovernanceMode.AUTONOMOUS, "allowed_write_paths": PATHS,
            "observed_at": 1, "pending_p0": False, "domain_revision": "domain-1",
        }
        data.update(overrides)
        return ReconciliationSnapshot(**data)

    def slice(self, ident: str = "p3", **overrides: object) -> ImprovementSlice:
        data: dict[str, object] = {
            "slice_id": ident, "priority": Priority.P3_BOUNDED_IMPROVEMENT,
            "changed_paths": PATHS, "source_signal_refs": ("signal:synthetic",),
            "problem_signature": "digest:problem", "goal": "bounded-synthetic-goal",
            "materiality": "MATERIAL", "evidence_target": "evidence:synthetic",
            "allowed_tools": ("stdlib-only",), "allowed_data_classes": ("PUBLIC_SAFE_SYNTHETIC",),
            "risk_class": "P3_SYNTHETIC", "time_budget_minutes": 1, "compute_budget": 1,
            "expected_artifact": "synthetic-receipt", "falsifier": "falsifier:synthetic",
            "stop_conditions": ("bounded-stop",), "writeback_plan": "NO_CANONICAL_WRITE",
            "owner": "GPT_ENGINEERING_WORKER", "estimated_cost": 1, "evidence_value": 1,
        }
        data.update(overrides)
        return ImprovementSlice(**data)

    def event(
        self, head: str, priority: Priority, source: str = "webhook", key: str = "key",
        event_class: str = "PR_HEAD_CHANGED", payload: object | None = None,
    ) -> dict[str, object]:
        return {
            "event_id": f"{source}-{head}-{key}", "event_class": event_class, "source": source,
            "repository": REPO, "observed_at": 1, "target_ref": "refs/heads/main",
            "target_identity": head, "payload": {"head": head} if payload is None else payload,
            "idempotency_key": key, "priority_hint": int(priority),
        }

    def start_p3(self, head: str = "A"):
        grant = self.sup.reconcile(self.snap(head))
        plan = self.sup.choose(grant, [self.slice()])
        self.assertFalse(hasattr(plan, "reason"))
        lease = self.store.acquire_lease("p3", "worker-a")
        self.assertIsNotNone(lease)
        self.assertEqual(Decision.EXECUTED, self.sup.execute(plan, lease).decision)
        return grant, plan, lease

    def review_evidence(self, work: ReviewWorkIdentity) -> ReviewEvidence:
        return ReviewEvidence(work.target_head, work.target_head, work.target_head, "synthetic-reviewer", work)

    def test_iagl_e001_p3_preempted_by_new_head_then_fresh_reconcile_resume(self) -> None:
        _, plan, lease_a = self.start_p3("A")
        self.sup.ingest(self.event("B", Priority.P1_EXACT_HEAD_REVIEW))
        paused = self.sup.safepoint(plan, lease_a)
        self.assertEqual(Decision.PREEMPTED, paused.decision)
        review_grant = self.sup.reconcile(self.snap("B"))
        work = self.sup.choose(review_grant, [])
        self.assertIsInstance(work, ReviewWorkIdentity)
        self.assertEqual(Decision.EXECUTED, self.sup.review(work, self.review_evidence(work)).decision)
        fresh = self.sup.reconcile(self.snap("B", observed_at=2))
        lease_new = self.store.acquire_lease("p3", "worker-a")
        resumed = self.sup.resume_or_replan(paused.checkpoint_id or "", fresh, lease_new)
        self.assertEqual("FRESH_RECONCILE_RESUME_OR_REPLAN", resumed.reason)

    def test_iagl_e002_a_b_trace_only_c_alone_creates_and_consumes_current_review(self) -> None:
        event_a, _ = self.sup.ingest(self.event("A", Priority.P1_EXACT_HEAD_REVIEW, key="a"))
        event_b, _ = self.sup.ingest(self.event("B", Priority.P1_EXACT_HEAD_REVIEW, key="b"))
        event_c, _ = self.sup.ingest(self.event("C", Priority.P1_EXACT_HEAD_REVIEW, key="c"))
        grant = self.sup.reconcile(self.snap("C"))
        self.assertEqual("TRACE_ONLY", self.store.event_state(event_a.semantic_key))
        self.assertEqual("TRACE_ONLY", self.store.event_state(event_b.semantic_key))
        work = self.sup.choose(grant, [])
        self.assertIsInstance(work, ReviewWorkIdentity)
        self.assertEqual(event_c.semantic_key, work.semantic_event_key)
        self.assertEqual(Decision.EXECUTED, self.sup.review(work, self.review_evidence(work)).decision)
        self.assertEqual("CONSUMED", self.store.event_state(event_c.semantic_key))
        fresh = self.sup.reconcile(self.snap("C", observed_at=2, eligible_work_queue_complete=True))
        self.assertEqual(Decision.IDLE, self.sup.choose(fresh, []).decision)

    def test_stale_event_arriving_after_reconciliation_is_classified_trace_only_before_review(self) -> None:
        self.sup.reconcile(self.snap("C"))
        stale, _ = self.sup.ingest(self.event("A", Priority.P1_EXACT_HEAD_REVIEW, key="late-a"))
        current, _ = self.sup.ingest(self.event("C", Priority.P1_EXACT_HEAD_REVIEW, key="late-c"))
        work = self.sup.choose(self.store.current_snapshot()[0], [])
        self.assertEqual("TRACE_ONLY", self.store.event_state(stale.semantic_key))
        self.assertEqual(current.semantic_key, work.semantic_event_key)

    def test_iagl_e003_green_ci_with_wrong_receipt_head_blocks(self) -> None:
        self.sup.ingest(self.event("C", Priority.P1_EXACT_HEAD_REVIEW))
        grant = self.sup.reconcile(self.snap("C")); work = self.sup.choose(grant, [])
        evidence = ReviewEvidence("C", "C", "A", "reviewer", work)
        self.assertEqual(Decision.BLOCKED, self.sup.review(work, evidence).decision)

    def test_iagl_e004_ten_no_value_slices_stop(self) -> None:
        for index in range(10):
            grant = self.sup.reconcile(self.snap("A", observed_at=index + 1))
            plan = self.sup.choose(grant, [self.slice(f"s{index}")])
            lease = self.store.acquire_lease(f"s{index}", "worker-a")
            self.sup.execute(plan, lease); self.sup.complete_atomic_slice(0)
        grant = self.sup.reconcile(self.snap("A", observed_at=11))
        stopped = self.sup.choose(grant, [self.slice("next")])
        self.assertEqual("VOI_STOP", stopped.reason)

    def test_iagl_e005_crash_restart_requires_fresh_reconcile(self) -> None:
        _, plan, lease = self.start_p3()
        self.sup.ingest(self.event("B", Priority.P1_EXACT_HEAD_REVIEW)); checkpoint = self.sup.safepoint(plan, lease)
        self.store.close(); self.store = WorkingStateStore(Path(self.temp.name) / "state.sqlite")
        self.sup = SyntheticSupervisor(REPO, self.store)
        review_grant = self.sup.reconcile(self.snap("B", observed_at=2)); work = self.sup.choose(review_grant, [])
        self.assertEqual(Decision.EXECUTED, self.sup.review(work, self.review_evidence(work)).decision)
        fresh = self.sup.reconcile(self.snap("B", observed_at=3)); lease_new = self.store.acquire_lease("p3", "worker-a")
        self.assertEqual(Decision.EXECUTED, self.sup.resume_or_replan(checkpoint.checkpoint_id or "", fresh, lease_new).decision)

    def test_iagl_e006_webhook_watchdog_same_target_deduplicated(self) -> None:
        _, first = self.sup.ingest(self.event("A", Priority.P1_EXACT_HEAD_REVIEW, "webhook", "one"))
        _, duplicate = self.sup.ingest(self.event("A", Priority.P4_RESEARCH, "watchdog", "two"))
        self.assertTrue(first); self.assertFalse(duplicate)

    def test_iagl_e007_execution_safepoint_resume_reject_cross_slice_genuine_lease(self) -> None:
        grant = self.sup.reconcile(self.snap("A")); plan = self.sup.choose(grant, [self.slice("slice-x")])
        lease_y = self.store.acquire_lease("slice-y", "worker-b")
        self.assertEqual(Decision.BLOCKED, self.sup.execute(plan, lease_y).decision)
        lease_x = self.store.acquire_lease("slice-x", "worker-a")
        self.assertEqual(Decision.EXECUTED, self.sup.execute(plan, lease_x).decision)
        self.sup.ingest(self.event("B", Priority.P1_EXACT_HEAD_REVIEW))
        self.assertEqual(Decision.BLOCKED, self.sup.safepoint(plan, lease_y).decision)
        paused = self.sup.safepoint(plan, lease_x)
        fresh = self.sup.reconcile(self.snap("B", observed_at=2))
        self.assertEqual(Decision.BLOCKED, self.sup.resume_or_replan(paused.checkpoint_id or "", fresh, lease_y).decision)

    def test_iagl_e008_user_controlled_queued_work_cannot_execute(self) -> None:
        grant = self.sup.reconcile(self.snap("A")); plan = self.sup.choose(grant, [self.slice()])
        user_grant = self.sup.reconcile(self.snap("A", governance_mode=GovernanceMode.USER_CONTROLLED, observed_at=2))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(user_grant, [self.slice()]).decision)
        self.assertEqual(Decision.BLOCKED, self.sup.execute(plan, self.store.acquire_lease("p3", "worker-a")).decision)

    def test_iagl_e009_user_controlled_to_autonomous_requires_fresh_reconcile_and_invalidates_plan(self) -> None:
        autonomous = self.sup.reconcile(self.snap("A")); stale_plan = self.sup.choose(autonomous, [self.slice()])
        user = self.sup.reconcile(self.snap("A", governance_mode=GovernanceMode.USER_CONTROLLED, observed_at=2))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(user, [self.slice()]).decision)
        fresh = self.sup.reconcile(self.snap("A", governance_mode=GovernanceMode.AUTONOMOUS, observed_at=3))
        self.assertNotEqual(autonomous, fresh)
        self.assertEqual(Decision.BLOCKED, self.sup.execute(stale_plan, self.store.acquire_lease("p3", "worker-a")).decision)

    def test_iagl_e010_secret_permission_request_is_p0_user_gate(self) -> None:
        self.sup.ingest(self.event("A", Priority.P4_RESEARCH, event_class="SECRET_PERMISSION", payload={"kind": "permission"}))
        grant = self.sup.reconcile(self.snap())
        self.assertEqual(Decision.USER_GATE, self.sup.choose(grant, [self.slice()]).decision)

    def test_iagl_e011_contradiction_is_candidate_only(self) -> None:
        grant = self.sup.reconcile(self.snap())
        candidate = self.slice(authority_metadata={"contradiction": "candidate"})
        self.assertEqual(candidate, self.sup.choose(grant, [candidate]).slice)
        self.assertEqual("domain-1", self.store.current_snapshot()[1].domain_revision)

    def test_iagl_e012_success_report_with_outside_path_hard_blocks(self) -> None:
        grant = self.sup.reconcile(self.snap())
        with self.assertRaisesRegex(SupervisorError, "OUTSIDE_ALLOWLIST"):
            self.sup.choose(grant, [self.slice(changed_paths=("outside.py",))])

    def test_iagl_e013_caller_authored_authority_unverified(self) -> None:
        grant = self.sup.reconcile(self.snap())
        with self.assertRaisesRegex(SupervisorError, "CALLER_AUTHORITY_UNTRUSTED"):
            self.sup.choose(grant, [self.slice(authority_metadata={"authority": "trusted"})])

    def test_iagl_e014_incomplete_retrieval_is_unknown_not_unsupported_or_idle(self) -> None:
        grant = self.sup.reconcile(self.snap())
        result = self.sup.resolve_recall(grant, "request:has-domain-object", None)
        self.assertEqual(Decision.UNKNOWN, result.decision)
        self.assertEqual("INCOMPLETE", result.process_compliance)
        self.assertEqual("RETRIEVAL_COMPLETENESS_UNPROVEN", result.reason)

    def test_iagl_e015_resource_guard_has_no_pool_daemon_or_subprocess(self) -> None:
        tree = ast.parse((ROOT / "src" / "iagl_synthetic_supervisor.py").read_text(encoding="utf-8"))
        imports = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertFalse({"subprocess", "multiprocessing", "threading", "socket", "requests"} & imports)

    def test_iagl_e016_p0_remains_before_p1(self) -> None:
        self.sup.ingest(self.event("A", Priority.P1_EXACT_HEAD_REVIEW, key="review"))
        self.sup.ingest(self.event("A", Priority.P4_RESEARCH, key="permission", event_class="SECRET_PERMISSION", payload={"kind": "permission"}))
        grant = self.sup.reconcile(self.snap())
        self.assertEqual(Decision.USER_GATE, self.sup.choose(grant, [self.slice()]).decision)

    def test_iagl_e017_old_domain_checkpoint_is_invalidated(self) -> None:
        _, plan, lease = self.start_p3(); self.sup.ingest(self.event("B", Priority.P1_EXACT_HEAD_REVIEW)); checkpoint = self.sup.safepoint(plan, lease)
        fresh = self.sup.reconcile(self.snap("B", domain_revision="domain-2", observed_at=2)); replacement = self.store.acquire_lease("p3", "worker-a")
        self.assertEqual(Decision.BLOCKED, self.sup.resume_or_replan(checkpoint.checkpoint_id or "", fresh, replacement).decision)

    def test_iagl_e018_only_trusted_complete_empty_work_queue_is_bounded_idle(self) -> None:
        grant = self.sup.reconcile(self.snap(eligible_work_queue_complete=True))
        result = self.sup.choose(grant, [])
        self.assertEqual(SupervisorState.IDLE_NO_ELIGIBLE_WORK, result.state)
        self.assertEqual("TRUSTED_COMPLETE_EMPTY_WORK_QUEUE", result.reason)


class R141B09ToB12Regressions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(); self.store = WorkingStateStore(Path(self.temp.name) / "state.sqlite")
        self.sup = SyntheticSupervisor(REPO, self.store, budget_limit=10)

    def tearDown(self) -> None:
        self.store.close(); self.temp.cleanup()

    def snapshot(self, **overrides: object) -> ReconciliationSnapshot:
        data: dict[str, object] = {
            "repository": REPO, "exact_head": "A", "route_id": "R141",
            "governance_mode": GovernanceMode.AUTONOMOUS, "allowed_write_paths": PATHS,
            "observed_at": 1, "domain_revision": "domain-1",
        }
        data.update(overrides); return ReconciliationSnapshot(**data)

    def slice(self, ident: str = "p3", **overrides: object) -> ImprovementSlice:
        data: dict[str, object] = {
            "slice_id": ident, "priority": Priority.P3_BOUNDED_IMPROVEMENT, "changed_paths": PATHS,
            "source_signal_refs": ("signal",), "problem_signature": "signature", "goal": "bounded goal",
            "materiality": "MATERIAL", "evidence_target": "evidence", "allowed_tools": ("stdlib-only",),
            "allowed_data_classes": ("PUBLIC_SAFE_SYNTHETIC",), "risk_class": "P3_SYNTHETIC",
            "time_budget_minutes": 1, "compute_budget": 1, "expected_artifact": "artifact", "falsifier": "falsifier",
            "stop_conditions": ("stop",), "writeback_plan": "NO_CANONICAL_WRITE", "owner": "GPT_ENGINEERING_WORKER",
        }
        data.update(overrides); return ImprovementSlice(**data)

    def event(self, event_class: str, hint: Priority, key: str, target: str = "A") -> dict[str, object]:
        return {
            "event_id": key, "event_class": event_class, "source": "synthetic", "repository": REPO,
            "observed_at": 1, "target_ref": "refs/heads/main", "target_identity": target,
            "payload": {"kind": event_class, "target": target}, "idempotency_key": key, "priority_hint": int(hint),
        }

    def start_and_checkpoint_same_head(self):
        grant = self.sup.reconcile(self.snapshot())
        plan = self.sup.choose(grant, [self.slice()]); lease = self.store.acquire_lease("p3", "worker")
        self.assertEqual(Decision.EXECUTED, self.sup.execute(plan, lease).decision)
        self.sup.ingest(self.event("WORKFLOW_COMPLETED", Priority.P4_RESEARCH, "same-head-p1"))
        cp = self.sup.safepoint(plan, lease)
        self.assertEqual(Decision.PREEMPTED, cp.decision)
        review_grant = self.sup.reconcile(self.snapshot(observed_at=2))
        work = self.sup.choose(review_grant, [])
        evidence = ReviewEvidence("A", "A", "A", "synthetic-reviewer", work)
        self.assertEqual(Decision.EXECUTED, self.sup.review(work, evidence).decision)
        return cp

    def test_b09_caller_p4_hint_cannot_downgrade_secret_permission_p0(self) -> None:
        event, _ = self.sup.ingest(self.event("SECRET_PERMISSION", Priority.P4_RESEARCH, "secret"))
        self.assertEqual(Priority.P4_RESEARCH, event.priority_hint)
        self.assertEqual(Priority.P0_USER_OR_HIGH_RISK, event.trusted_priority)
        grant = self.sup.reconcile(self.snapshot())
        self.assertEqual(Decision.USER_GATE, self.sup.choose(grant, [self.slice()]).decision)

    def test_b09_pending_p2_preempts_p3_even_when_hint_is_p4(self) -> None:
        event, _ = self.sup.ingest(self.event("ROUTE_DRIFT", Priority.P4_RESEARCH, "drift"))
        self.assertEqual(Priority.P2_BLOCKER_OR_DRIFT, event.trusted_priority)
        grant = self.sup.reconcile(self.snapshot())
        result = self.sup.choose(grant, [self.slice()])
        self.assertEqual(Decision.BLOCKED, result.decision)
        self.assertEqual("P2_RECONCILIATION_OR_SECURITY_BLOCKER", result.reason)

    def test_b10_same_semantic_snapshot_newer_generation_can_resume(self) -> None:
        cp = self.start_and_checkpoint_same_head()
        fresh = self.sup.reconcile(self.snapshot(observed_at=3))
        self.assertEqual(cp.checkpoint_id is not None, True)
        loaded = self.store.load_checkpoint(cp.checkpoint_id or "")
        self.assertEqual(loaded.snapshot_identity, fresh.identity)
        self.assertGreater(fresh.generation, loaded.reconciliation_generation)
        lease = self.store.acquire_lease("p3", "worker")
        self.assertEqual(Decision.EXECUTED, self.sup.resume_or_replan(cp.checkpoint_id or "", fresh, lease).decision)

    def test_b10_narrowed_write_allowlist_invalidates_checkpointed_slice(self) -> None:
        cp = self.start_and_checkpoint_same_head()
        fresh = self.sup.reconcile(self.snapshot(observed_at=3, allowed_write_paths=("synthetic/other.py",)))
        lease = self.store.acquire_lease("p3", "worker")
        result = self.sup.resume_or_replan(cp.checkpoint_id or "", fresh, lease)
        self.assertEqual(Decision.BLOCKED, result.decision)
        self.assertEqual("CHECKPOINTED_SLICE_POLICY_DRIFT", result.reason)

    def test_b10_risk_policy_drift_invalidates_checkpointed_slice(self) -> None:
        cp = self.start_and_checkpoint_same_head()
        fresh = self.sup.reconcile(self.snapshot(observed_at=3, allowed_risk_classes=("P4_SYNTHETIC",)))
        lease = self.store.acquire_lease("p3", "worker")
        result = self.sup.resume_or_replan(cp.checkpoint_id or "", fresh, lease)
        self.assertEqual(Decision.BLOCKED, result.decision)
        self.assertEqual("CHECKPOINTED_SLICE_POLICY_DRIFT", result.reason)

    def test_b11_invalid_goals_fail_closed(self) -> None:
        grant = self.sup.reconcile(self.snapshot())
        for goal in ("improve system generally", "research indefinitely", "browse until something interesting appears"):
            with self.assertRaisesRegex(SupervisorError, "SLICE_INVALID_GOAL"):
                self.sup.choose(grant, [self.slice(goal=goal)])

    def test_b11_forbidden_nonempty_tool_data_risk_and_writeback_fail_closed(self) -> None:
        grant = self.sup.reconcile(self.snapshot())
        cases = (
            (self.slice(allowed_tools=("shell",)), "FORBIDDEN_TOOL"),
            (self.slice(allowed_data_classes=("PRIVATE_CONVERSATION",)), "FORBIDDEN_DATA"),
            (self.slice(risk_class="PRODUCTION_HIGH_RISK"), "FORBIDDEN_RISK"),
            (self.slice(writeback_plan="W3_CANONICAL_WRITE"), "WRITEBACK_POLICY"),
        )
        for invalid, marker in cases:
            with self.assertRaisesRegex(SupervisorError, marker):
                self.sup.choose(grant, [invalid])

    def test_b11_non_public_checkpoint_privacy_fails_closed(self) -> None:
        checkpoint = Checkpoint(
            "cp", "mission", "slice", "SAFEPOINT_CHECKPOINT", 1, "snapshot", ("source",), ("digest",),
            ("step",), ("unknown",), "resume", "used:1", "lease", "fence", "P1",
            RESUME_PRECONDITIONS, "PRIVATE", "snapshot", 1, 1, "A", "R141", "domain-1",
        )
        with self.assertRaisesRegex(SupervisorError, "PRIVACY_NOT_PUBLIC_SAFE"):
            self.store.save_checkpoint(checkpoint)

    def test_b12_forged_field_perfect_caller_proof_is_untrusted(self) -> None:
        grant = self.sup.reconcile(self.snapshot())
        genuine = self.sup.issue_retrieval_complete_empty_proof(grant, "request", "scope", "evidence")
        forged = replace(genuine, issuance_ref="stage-a:forged-caller")
        result = self.sup.resolve_recall(grant, "request", forged)
        self.assertEqual(Decision.UNKNOWN, result.decision)
        self.assertEqual("UNTRUSTED", result.process_compliance)
        self.assertEqual("RETRIEVAL_COMPLETENESS_UNTRUSTED", result.reason)
        self.assertEqual(Decision.IDLE, self.sup.resolve_recall(grant, "request", genuine).decision)


class SupportingContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(); self.store = WorkingStateStore(Path(self.temp.name) / "state.sqlite")
        self.sup = SyntheticSupervisor(REPO, self.store, budget_limit=3)

    def tearDown(self) -> None:
        self.store.close(); self.temp.cleanup()

    def snapshot(self) -> ReconciliationSnapshot:
        return ReconciliationSnapshot(REPO, "A", "R141", GovernanceMode.AUTONOMOUS, PATHS, 1)

    def complete_slice(self, ident: str = "x") -> ImprovementSlice:
        return ImprovementSlice(ident, Priority.P3_BOUNDED_IMPROVEMENT, PATHS, ("signal:synthetic",), "signature", "goal", "MATERIAL", "evidence", ("stdlib-only",), ("PUBLIC_SAFE_SYNTHETIC",), "P3_SYNTHETIC", 1, 1, "artifact", "falsifier", ("stop",), "NO_CANONICAL_WRITE", "GPT_ENGINEERING_WORKER")

    def test_exact_frozen_transition_table(self) -> None:
        self.assertEqual({SupervisorState.GLOBAL_RECONCILIATION, SupervisorState.EMERGENCY_STOP}, _ALLOWED[SupervisorState.BOOT])
        self.assertEqual({SupervisorState.REVIEW, SupervisorState.USER_GATE, SupervisorState.GLOBAL_RECONCILIATION}, _ALLOWED[SupervisorState.PAUSED_FOR_HIGHER_PRIORITY])
        self.assertEqual({SupervisorState.GLOBAL_RECONCILIATION, SupervisorState.EMERGENCY_STOP}, _ALLOWED[SupervisorState.FAILED_CLOSED])

    def test_budget_boundary_never_reserves_past_limit(self) -> None:
        grant = self.sup.reconcile(self.snapshot()); plan = self.sup.choose(grant, [replace(self.complete_slice("over"), estimated_cost=4)])
        self.assertEqual("BUDGET_EXHAUSTED_PRE_EXECUTION", plan.reason); self.assertEqual(0, self.store.value("budget_used"))

    def test_no_current_event_cannot_create_or_complete_trusted_review(self) -> None:
        grant = self.sup.reconcile(self.snapshot())
        self.assertEqual(Decision.UNKNOWN, self.sup.choose(grant, []).decision)
        forged = ReviewWorkIdentity("event:absent", "A", grant.identity, grant.generation)
        self.sup.state = SupervisorState.REVIEW
        evidence = ReviewEvidence("A", "A", "A", "synthetic", forged)
        self.assertEqual(Decision.BLOCKED, self.sup.review(forged, evidence).decision)

    def test_retrieval_complete_empty_must_bind_reconciliation_and_issuance(self) -> None:
        grant = self.sup.reconcile(self.snapshot())
        proof = self.sup.issue_retrieval_complete_empty_proof(grant, "request", "scope", "evidence")
        self.assertEqual(Decision.UNKNOWN, self.sup.resolve_recall(grant, "other", proof).decision)
        self.assertEqual(Decision.IDLE, self.sup.resolve_recall(grant, "request", proof).decision)

    def test_slice_contract_rejects_missing_risk_stop_or_writeback(self) -> None:
        grant = self.sup.reconcile(self.snapshot())
        for invalid in (replace(self.complete_slice(), risk_class=""), replace(self.complete_slice(), stop_conditions=()), replace(self.complete_slice(), writeback_plan="")):
            with self.assertRaisesRegex(SupervisorError, "FROZEN_CONTRACT"):
                self.sup.choose(grant, [invalid])

    def test_checkpoint_contract_rejects_missing_resume_precondition_or_privacy(self) -> None:
        checkpoint = Checkpoint("cp", "mission", "slice", "SAFEPOINT_CHECKPOINT", 1, "snapshot", ("source",), ("digest",), ("step",), ("unknown",), "resume", "used:1", "lease", "fence", "P1", RESUME_PRECONDITIONS, "PUBLIC_SAFE_SYNTHETIC", "snapshot", 1, 1, "A", "R141", "domain")
        self.store.save_checkpoint(checkpoint)
        invalid_resume = replace(checkpoint, resume_preconditions=RESUME_PRECONDITIONS[:-1])
        with self.assertRaisesRegex(SupervisorError, "RESUME_PRECONDITIONS"):
            self.store.save_checkpoint(invalid_resume)
        with self.assertRaisesRegex(SupervisorError, "FROZEN_CONTRACT"):
            self.store.save_checkpoint(replace(checkpoint, privacy_class=""))

    def test_stale_resume_preconditions_fail_closed(self) -> None:
        grant = self.sup.reconcile(self.snapshot()); plan = self.sup.choose(grant, [self.complete_slice("slice-x")]); lease = self.store.acquire_lease("slice-x", "owner")
        self.sup.execute(plan, lease)
        self.sup.ingest({"event_id": "p1", "event_class": "PR_HEAD_CHANGED", "source": "synthetic", "repository": REPO, "observed_at": 1, "target_ref": "refs/heads/main", "target_identity": "B", "payload": {"head": "B"}, "idempotency_key": "p1", "priority_hint": 1})
        cp = self.sup.safepoint(plan, lease); loaded = self.store.load_checkpoint(cp.checkpoint_id or "")
        record = self.store.connection.execute("SELECT record FROM checkpoints WHERE checkpoint_id=?", (loaded.checkpoint_id,)).fetchone()[0]
        forged = json.loads(record); forged["resume_preconditions"] = []
        self.store.connection.execute("UPDATE checkpoints SET record=? WHERE checkpoint_id=?", (json.dumps(forged), loaded.checkpoint_id)); self.store.connection.commit()
        fresh = self.sup.reconcile(ReconciliationSnapshot(REPO, "B", "R141", GovernanceMode.AUTONOMOUS, PATHS, 2))
        lease_new = self.store.acquire_lease("slice-x", "owner")
        self.assertEqual(Decision.BLOCKED, self.sup.resume_or_replan(cp.checkpoint_id or "", fresh, lease_new).decision)


if __name__ == "__main__":
    unittest.main(verbosity=2)
