"""Frozen canonical IAGL-E001..E018 Stage-A mechanism regressions."""
from __future__ import annotations
import ast
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
from iagl_synthetic_supervisor import (  # noqa: E402
    _ALLOWED, Decision, GovernanceMode, ImprovementSlice, LeaseGrant, Priority,
    ReconciliationSnapshot, ReviewEvidence, SupervisorError, SupervisorState,
    SyntheticSupervisor, WorkingStateStore,
)

REPO = "vxz2datoubo/second-brain-coordination"
PATHS = ("synthetic/allowed.py",)


class CanonicalStageAEvaluations(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = WorkingStateStore(Path(self.temp.name) / "state.sqlite")
        self.sup = SyntheticSupervisor(REPO, self.store, budget_limit=10, no_value_limit=10)

    def tearDown(self) -> None:
        self.store.close(); self.temp.cleanup()

    def snap(self, head: str = "A", **overrides: object) -> ReconciliationSnapshot:
        data: dict[str, object] = {"repository": REPO, "exact_head": head, "route_id": "R141", "governance_mode": GovernanceMode.AUTONOMOUS, "allowed_write_paths": PATHS, "observed_at": 1, "pending_p0": False, "domain_revision": "domain-1"}
        data.update(overrides); return ReconciliationSnapshot(**data)

    def slice(self, ident: str = "p3", **overrides: object) -> ImprovementSlice:
        data: dict[str, object] = {"slice_id": ident, "priority": Priority.P3_BOUNDED_IMPROVEMENT, "changed_paths": PATHS, "estimated_cost": 1, "evidence_value": 1}
        data.update(overrides); return ImprovementSlice(**data)

    def event(self, head: str, priority: Priority, source: str = "webhook", key: str = "key") -> dict[str, object]:
        return {"event_id": f"{source}-{head}", "event_class": "PR_HEAD_CHANGED", "source": source, "repository": REPO, "observed_at": 1, "target_ref": "refs/heads/main", "target_identity": head, "payload": {"head": head}, "idempotency_key": key, "priority_hint": int(priority)}

    def start_p3(self, head: str = "A"):
        grant = self.sup.reconcile(self.snap(head)); plan = self.sup.choose(grant, [self.slice()]); self.assertFalse(hasattr(plan, "reason")); lease = self.store.acquire_lease("p3", "worker-a"); self.assertIsNotNone(lease); self.assertEqual(Decision.EXECUTED, self.sup.execute(plan, lease).decision); return grant, plan, lease

    def test_iagl_e001_p3_preempted_by_new_head_then_fresh_reconcile_resume(self) -> None:
        _, plan, lease_a = self.start_p3("A")
        self.sup.ingest(self.event("B", Priority.P1_EXACT_HEAD_REVIEW))
        paused = self.sup.safepoint(plan, lease_a)
        self.assertEqual(Decision.PREEMPTED, paused.decision)
        review_grant = self.sup.reconcile(self.snap("B"))
        self.assertEqual(Decision.REVIEW_REQUIRED, self.sup.choose(review_grant, []).decision)
        self.assertEqual(Decision.EXECUTED, self.sup.review(ReviewEvidence("B", "B", "B", "synthetic-reviewer")).decision)
        fresh = self.sup.reconcile(self.snap("B", observed_at=2))
        lease_new = self.store.acquire_lease("p3", "worker-a")
        resumed = self.sup.resume_or_replan(paused.checkpoint_id or "", fresh, lease_new)
        self.assertEqual("FRESH_RECONCILE_RESUME_OR_REPLAN", resumed.reason)

    def test_iagl_e002_only_latest_c_head_can_be_reviewed(self) -> None:
        self.sup.reconcile(self.snap("C")); self.sup.ingest(self.event("A", Priority.P1_EXACT_HEAD_REVIEW)); self.sup.ingest(self.event("B", Priority.P1_EXACT_HEAD_REVIEW)); self.sup.ingest(self.event("C", Priority.P1_EXACT_HEAD_REVIEW))
        self.assertEqual(Decision.REVIEW_REQUIRED, self.sup.choose(self.store.current_snapshot()[0], []).decision)
        blocked = self.sup.review(ReviewEvidence("A", "A", "A", "reviewer"))
        self.assertEqual("REVIEW_EXACT_HEAD_RECEIPT_MISMATCH", blocked.reason)
        store = WorkingStateStore(Path(self.temp.name) / "c.sqlite"); latest = SyntheticSupervisor(REPO, store); g = latest.reconcile(self.snap("C")); latest.ingest(self.event("C", Priority.P1_EXACT_HEAD_REVIEW)); latest.choose(g, [])
        self.assertEqual(Decision.EXECUTED, latest.review(ReviewEvidence("C", "C", "C", "reviewer")).decision); store.close()

    def test_iagl_e003_green_ci_with_wrong_receipt_head_blocks(self) -> None:
        g = self.sup.reconcile(self.snap("C")); self.sup.ingest(self.event("C", Priority.P1_EXACT_HEAD_REVIEW)); self.sup.choose(g, [])
        self.assertEqual(Decision.BLOCKED, self.sup.review(ReviewEvidence("C", "C", "A", "reviewer")).decision)

    def test_iagl_e004_ten_no_value_slices_stop(self) -> None:
        for index in range(10):
            grant = self.sup.reconcile(self.snap("A", observed_at=index + 1)); plan = self.sup.choose(grant, [self.slice(f"s{index}")]); lease = self.store.acquire_lease(f"s{index}", "worker-a"); self.sup.execute(plan, lease); self.sup.complete_atomic_slice(0)
        grant = self.sup.reconcile(self.snap("A", observed_at=11)); stopped = self.sup.choose(grant, [self.slice("next")])
        self.assertEqual("VOI_STOP", stopped.reason)

    def test_iagl_e005_crash_restart_requires_fresh_reconcile(self) -> None:
        _, plan, lease = self.start_p3(); self.sup.ingest(self.event("B", Priority.P1_EXACT_HEAD_REVIEW)); checkpoint = self.sup.safepoint(plan, lease)
        self.store.close(); self.store = WorkingStateStore(Path(self.temp.name) / "state.sqlite"); self.sup = SyntheticSupervisor(REPO, self.store)
        fresh = self.sup.reconcile(self.snap("B", observed_at=2)); lease_new = self.store.acquire_lease("p3", "worker-a")
        self.assertEqual(Decision.EXECUTED, self.sup.resume_or_replan(checkpoint.checkpoint_id or "", fresh, lease_new).decision)

    def test_iagl_e006_webhook_watchdog_same_target_deduplicated(self) -> None:
        _, first = self.sup.ingest(self.event("A", Priority.P1_EXACT_HEAD_REVIEW, "webhook", "one")); _, duplicate = self.sup.ingest(self.event("A", Priority.P1_EXACT_HEAD_REVIEW, "watchdog", "two"))
        self.assertTrue(first); self.assertFalse(duplicate)

    def test_iagl_e007_actual_execution_and_resume_reject_stale_fence(self) -> None:
        _, plan, lease_a = self.start_p3(); self.sup.ingest(self.event("B", Priority.P1_EXACT_HEAD_REVIEW)); checkpoint = self.sup.safepoint(plan, lease_a)
        lease_b = self.store.acquire_lease("p3", "worker-b"); self.assertIsNotNone(lease_b)
        self.assertEqual(Decision.BLOCKED, self.sup.execute(plan, lease_a).decision)
        forged = LeaseGrant("p3", "worker-b", lease_b.generation, "forged-token")
        self.assertEqual(Decision.BLOCKED, self.sup.execute(plan, forged).decision)
        fresh = self.sup.reconcile(self.snap("B", observed_at=2))
        self.assertEqual(Decision.BLOCKED, self.sup.resume_or_replan(checkpoint.checkpoint_id or "", fresh, lease_a).decision)

    def test_iagl_e008_user_controlled_queued_work_cannot_execute(self) -> None:
        grant, plan, lease = self.start_p3(); self.assertTrue(self.store.release_lease(lease))
        user_sup = SyntheticSupervisor(REPO, self.store); user_grant = user_sup.reconcile(self.snap("A", governance_mode=GovernanceMode.USER_CONTROLLED, observed_at=2))
        self.assertEqual(Decision.USER_GATE, user_sup.choose(user_grant, [self.slice()]).decision)
        self.assertEqual(Decision.BLOCKED, self.sup.execute(plan, self.store.acquire_lease("p3", "worker-a")).decision)

    def test_iagl_e009_autonomous_reenable_invalidates_stale_queued_plan(self) -> None:
        grant = self.sup.reconcile(self.snap("A")); plan = self.sup.choose(grant, [self.slice()]); self.sup.ingest(self.event("gate", Priority.P0_USER_OR_HIGH_RISK)); self.sup.choose(grant, [self.slice()])
        fresh = self.sup.reconcile(self.snap("A", observed_at=2)); lease = self.store.acquire_lease("p3", "worker-a")
        self.assertNotEqual(grant, fresh); self.assertEqual(Decision.BLOCKED, self.sup.execute(plan, lease).decision)

    def test_iagl_e010_secret_permission_request_is_p0_user_gate(self) -> None:
        grant = self.sup.reconcile(self.snap()); self.sup.ingest(self.event("secret-request", Priority.P0_USER_OR_HIGH_RISK))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(grant, [self.slice()]).decision)

    def test_iagl_e011_contradiction_is_candidate_only(self) -> None:
        grant = self.sup.reconcile(self.snap()); candidate = self.slice(authority_metadata={"contradiction": "candidate"})
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

    def test_iagl_e014_empty_recall_projection_is_unknown_not_unsupported(self) -> None:
        grant = self.sup.reconcile(self.snap()); result = self.sup.choose(grant, [])
        self.assertEqual(Decision.IDLE, result.decision); self.assertNotEqual("UNSUPPORTED", result.reason)

    def test_iagl_e015_resource_guard_has_no_pool_daemon_or_subprocess(self) -> None:
        tree = ast.parse((ROOT / "src" / "iagl_synthetic_supervisor.py").read_text(encoding="utf-8")); imports = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertFalse({"subprocess", "multiprocessing", "threading", "socket", "requests"} & imports)

    def test_iagl_e016_p0_remains_before_p1(self) -> None:
        grant = self.sup.reconcile(self.snap()); self.sup.ingest(self.event("review", Priority.P1_EXACT_HEAD_REVIEW)); self.sup.ingest(self.event("permission", Priority.P0_USER_OR_HIGH_RISK))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(grant, [self.slice()]).decision)

    def test_iagl_e017_old_domain_checkpoint_is_invalidated(self) -> None:
        _, plan, lease = self.start_p3(); self.sup.ingest(self.event("B", Priority.P1_EXACT_HEAD_REVIEW)); checkpoint = self.sup.safepoint(plan, lease)
        fresh = self.sup.reconcile(self.snap("B", domain_revision="domain-2", observed_at=2)); replacement = self.store.acquire_lease("p3", "worker-a")
        self.assertEqual(Decision.BLOCKED, self.sup.resume_or_replan(checkpoint.checkpoint_id or "", fresh, replacement).decision)

    def test_iagl_e018_tick_with_no_work_is_bounded_idle(self) -> None:
        grant = self.sup.reconcile(self.snap()); result = self.sup.choose(grant, [])
        self.assertEqual(SupervisorState.IDLE_NO_ELIGIBLE_WORK, result.state)


class SupportingContracts(unittest.TestCase):
    def test_exact_frozen_transition_table(self) -> None:
        self.assertEqual({SupervisorState.GLOBAL_RECONCILIATION, SupervisorState.EMERGENCY_STOP}, _ALLOWED[SupervisorState.BOOT])
        self.assertEqual({SupervisorState.REVIEW, SupervisorState.USER_GATE, SupervisorState.GLOBAL_RECONCILIATION}, _ALLOWED[SupervisorState.PAUSED_FOR_HIGHER_PRIORITY])
        self.assertEqual({SupervisorState.GLOBAL_RECONCILIATION, SupervisorState.EMERGENCY_STOP}, _ALLOWED[SupervisorState.FAILED_CLOSED])

    def test_budget_boundary_never_reserves_past_limit(self) -> None:
        temp = tempfile.TemporaryDirectory(); store = WorkingStateStore(Path(temp.name) / "b.sqlite"); sup = SyntheticSupervisor(REPO, store, budget_limit=3); grant = sup.reconcile(ReconciliationSnapshot(REPO, "A", "R141", GovernanceMode.AUTONOMOUS, PATHS, 1)); plan = sup.choose(grant, [ImprovementSlice("over", Priority.P3_BOUNDED_IMPROVEMENT, PATHS, estimated_cost=4)])
        self.assertEqual("BUDGET_EXHAUSTED_PRE_EXECUTION", plan.reason); self.assertEqual(0, store.value("budget_used")); store.close(); temp.cleanup()


if __name__ == "__main__": unittest.main(verbosity=2)
