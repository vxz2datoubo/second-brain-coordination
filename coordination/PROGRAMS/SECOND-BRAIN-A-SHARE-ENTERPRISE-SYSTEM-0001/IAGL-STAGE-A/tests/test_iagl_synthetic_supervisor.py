"""Frozen canonical IAGL-E001..E018 plus R141 B09R2-B15 regressions."""
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
    _ALLOWED, Checkpoint, Decision, GovernanceMode, ImprovementSlice, P0Disposition,
    P2Resolution, Priority, ReconciliationSnapshot, RetrievalProviderObservation,
    ReviewEvidence, ReviewWorkIdentity, SupervisorError, SupervisorState,
    SyntheticRetrievalProvider, SyntheticSupervisor, WorkingStateStore,
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
        self.store.close(); self.temp.cleanup()

    def snap(self, head: str = "A", **overrides: object) -> ReconciliationSnapshot:
        data: dict[str, object] = {
            "repository": REPO, "exact_head": head, "route_id": "R141",
            "governance_mode": GovernanceMode.AUTONOMOUS, "allowed_write_paths": PATHS,
            "observed_at": 1, "pending_p0": False, "domain_revision": "domain-1",
        }
        data.update(overrides); return ReconciliationSnapshot(**data)

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
        data.update(overrides); return ImprovementSlice(**data)

    def event(self, head: str, priority: Priority, source: str = "webhook", key: str = "key", event_class: str = "PR_HEAD_CHANGED", payload: object | None = None) -> dict[str, object]:
        return {
            "event_id": f"{source}-{head}-{key}", "event_class": event_class, "source": source,
            "repository": REPO, "observed_at": 1, "target_ref": "refs/heads/main",
            "target_identity": head, "payload": {"head": head} if payload is None else payload,
            "idempotency_key": key, "priority_hint": int(priority),
        }

    def start_p3(self, head: str = "A"):
        grant = self.sup.reconcile(self.snap(head)); plan = self.sup.choose(grant, [self.slice()])
        lease = self.store.acquire_lease("p3", "worker-a"); self.assertIsNotNone(lease)
        self.assertEqual(Decision.EXECUTED, self.sup.execute(plan, lease).decision)
        return grant, plan, lease

    def review_evidence(self, work: ReviewWorkIdentity) -> ReviewEvidence:
        return ReviewEvidence(work.target_head, work.target_head, work.target_head, "synthetic-reviewer", work)

    def test_iagl_e001_p3_preempted_by_new_head_then_fresh_reconcile_resume(self) -> None:
        _, plan, lease_a = self.start_p3("A")
        self.sup.ingest(self.event("B", Priority.P4_RESEARCH))
        paused = self.sup.safepoint(plan, lease_a); self.assertEqual(Decision.PREEMPTED, paused.decision)
        review_grant = self.sup.reconcile(self.snap("B")); work = self.sup.choose(review_grant, [])
        self.assertIsInstance(work, ReviewWorkIdentity); self.assertEqual(Decision.EXECUTED, self.sup.review(work, self.review_evidence(work)).decision)
        fresh = self.sup.reconcile(self.snap("B", observed_at=2)); lease_new = self.store.acquire_lease("p3", "worker-a")
        self.assertEqual(Decision.EXECUTED, self.sup.resume_or_replan(paused.checkpoint_id or "", fresh, lease_new).decision)

    def test_iagl_e002_a_b_trace_only_c_alone_creates_and_consumes_current_review(self) -> None:
        event_a, _ = self.sup.ingest(self.event("A", Priority.P4_RESEARCH, key="a"))
        event_b, _ = self.sup.ingest(self.event("B", Priority.P4_RESEARCH, key="b"))
        event_c, _ = self.sup.ingest(self.event("C", Priority.P4_RESEARCH, key="c"))
        grant = self.sup.reconcile(self.snap("C"))
        self.assertEqual("TRACE_ONLY", self.store.event_state(event_a.semantic_key)); self.assertEqual("TRACE_ONLY", self.store.event_state(event_b.semantic_key))
        work = self.sup.choose(grant, []); self.assertEqual(event_c.semantic_key, work.semantic_event_key)
        self.assertEqual(Decision.EXECUTED, self.sup.review(work, self.review_evidence(work)).decision); self.assertEqual("CONSUMED", self.store.event_state(event_c.semantic_key))
        fresh = self.sup.reconcile(self.snap("C", observed_at=2, eligible_work_queue_complete=True)); self.assertEqual(Decision.IDLE, self.sup.choose(fresh, []).decision)

    def test_stale_event_arriving_after_reconciliation_is_trace_only_after_fresh_reconcile(self) -> None:
        self.sup.reconcile(self.snap("C"))
        stale, _ = self.sup.ingest(self.event("A", Priority.P4_RESEARCH, key="late-a")); current, _ = self.sup.ingest(self.event("C", Priority.P4_RESEARCH, key="late-c"))
        blocked = self.sup.choose(self.store.current_snapshot()[0], []); self.assertEqual("FRESH_RECONCILIATION_REQUIRED_FOR_PENDING_EVENT", blocked.reason)
        grant = self.sup.reconcile(self.snap("C", observed_at=2)); work = self.sup.choose(grant, [])
        self.assertEqual("TRACE_ONLY", self.store.event_state(stale.semantic_key)); self.assertEqual(current.semantic_key, work.semantic_event_key)

    def test_iagl_e003_green_ci_with_wrong_receipt_head_blocks(self) -> None:
        self.sup.ingest(self.event("C", Priority.P4_RESEARCH)); grant = self.sup.reconcile(self.snap("C")); work = self.sup.choose(grant, [])
        self.assertEqual(Decision.BLOCKED, self.sup.review(work, ReviewEvidence("C", "C", "A", "reviewer", work)).decision)

    def test_iagl_e004_ten_no_value_slices_stop(self) -> None:
        for index in range(10):
            grant = self.sup.reconcile(self.snap("A", observed_at=index + 1)); plan = self.sup.choose(grant, [self.slice(f"s{index}")]); lease = self.store.acquire_lease(f"s{index}", "worker-a")
            self.sup.execute(plan, lease); self.sup.complete_atomic_slice(0)
        grant = self.sup.reconcile(self.snap("A", observed_at=11)); self.assertEqual("VOI_STOP", self.sup.choose(grant, [self.slice("next")]).reason)

    def test_iagl_e005_crash_restart_requires_fresh_reconcile(self) -> None:
        _, plan, lease = self.start_p3(); self.sup.ingest(self.event("B", Priority.P4_RESEARCH)); checkpoint = self.sup.safepoint(plan, lease)
        self.store.close(); self.store = WorkingStateStore(Path(self.temp.name) / "state.sqlite"); self.sup = SyntheticSupervisor(REPO, self.store)
        review_grant = self.sup.reconcile(self.snap("B", observed_at=2)); work = self.sup.choose(review_grant, [])
        self.assertEqual(Decision.EXECUTED, self.sup.review(work, self.review_evidence(work)).decision)
        fresh = self.sup.reconcile(self.snap("B", observed_at=3)); lease_new = self.store.acquire_lease("p3", "worker-a")
        self.assertEqual(Decision.EXECUTED, self.sup.resume_or_replan(checkpoint.checkpoint_id or "", fresh, lease_new).decision)

    def test_iagl_e006_webhook_watchdog_same_semantic_target_deduplicated(self) -> None:
        webhook, first = self.sup.ingest(self.event("A", Priority.P1_EXACT_HEAD_REVIEW, "webhook", "one", event_class="PR_HEAD_CHANGED"))
        watchdog, duplicate = self.sup.ingest(self.event("A", Priority.P4_RESEARCH, "watchdog", "two", event_class="WATCHDOG_TICK"))
        self.assertEqual(webhook.semantic_key, watchdog.semantic_key); self.assertTrue(first); self.assertFalse(duplicate)
        self.assertEqual(("watchdog", "webhook"), self.store.trace_sources(webhook.semantic_key))

    def test_iagl_e007_execution_safepoint_resume_reject_cross_slice_genuine_lease(self) -> None:
        grant = self.sup.reconcile(self.snap("A")); plan = self.sup.choose(grant, [self.slice("slice-x")]); lease_y = self.store.acquire_lease("slice-y", "worker-b")
        self.assertEqual(Decision.BLOCKED, self.sup.execute(plan, lease_y).decision)
        lease_x = self.store.acquire_lease("slice-x", "worker-a"); self.assertEqual(Decision.EXECUTED, self.sup.execute(plan, lease_x).decision)
        self.sup.ingest(self.event("B", Priority.P4_RESEARCH)); self.assertEqual(Decision.BLOCKED, self.sup.safepoint(plan, lease_y).decision)
        paused = self.sup.safepoint(plan, lease_x); fresh = self.sup.reconcile(self.snap("B", observed_at=2)); self.assertEqual(Decision.BLOCKED, self.sup.resume_or_replan(paused.checkpoint_id or "", fresh, lease_y).decision)

    def test_iagl_e008_user_controlled_queued_work_cannot_execute(self) -> None:
        grant = self.sup.reconcile(self.snap("A")); plan = self.sup.choose(grant, [self.slice()]); user_grant = self.sup.reconcile(self.snap("A", governance_mode=GovernanceMode.USER_CONTROLLED, observed_at=2))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(user_grant, [self.slice()]).decision); self.assertEqual(Decision.BLOCKED, self.sup.execute(plan, self.store.acquire_lease("p3", "worker-a")).decision)

    def test_iagl_e009_user_controlled_to_autonomous_requires_fresh_reconcile_and_invalidates_plan(self) -> None:
        autonomous = self.sup.reconcile(self.snap("A")); stale_plan = self.sup.choose(autonomous, [self.slice()]); user = self.sup.reconcile(self.snap("A", governance_mode=GovernanceMode.USER_CONTROLLED, observed_at=2))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(user, [self.slice()]).decision); fresh = self.sup.reconcile(self.snap("A", governance_mode=GovernanceMode.AUTONOMOUS, observed_at=3))
        self.assertNotEqual(autonomous, fresh); self.assertEqual(Decision.BLOCKED, self.sup.execute(stale_plan, self.store.acquire_lease("p3", "worker-a")).decision)

    def test_iagl_e010_low_class_research_secret_permission_materiality_forces_p0(self) -> None:
        event, _ = self.sup.ingest(self.event("A", Priority.P4_RESEARCH, event_class="SIGNAL_MATERIALITY_CHANGED", payload={"finding": "API secret", "permission": "GitHub permission expansion"}))
        self.assertIn("secret", event.risk_markers); grant = self.sup.reconcile(self.snap())
        self.assertEqual(Priority.P0_USER_OR_HIGH_RISK, self.store.event_priority(event.semantic_key)); self.assertEqual(Decision.USER_GATE, self.sup.choose(grant, [self.slice()]).decision)

    def test_iagl_e011_contradiction_is_candidate_only(self) -> None:
        grant = self.sup.reconcile(self.snap()); candidate = self.slice(authority_metadata={"contradiction": "candidate"})
        self.assertEqual(candidate, self.sup.choose(grant, [candidate]).slice); self.assertEqual("domain-1", self.store.current_snapshot()[1].domain_revision)

    def test_iagl_e012_success_report_with_outside_path_hard_blocks(self) -> None:
        grant = self.sup.reconcile(self.snap())
        with self.assertRaisesRegex(SupervisorError, "OUTSIDE_ALLOWLIST"):
            self.sup.choose(grant, [self.slice(changed_paths=("outside.py",))])

    def test_iagl_e013_caller_authored_authority_unverified(self) -> None:
        grant = self.sup.reconcile(self.snap())
        with self.assertRaisesRegex(SupervisorError, "CALLER_AUTHORITY_UNTRUSTED"):
            self.sup.choose(grant, [self.slice(authority_metadata={"authority": "trusted"})])

    def test_iagl_e014_incomplete_retrieval_is_unknown_not_unsupported_or_idle(self) -> None:
        grant = self.sup.reconcile(self.snap()); result = self.sup.resolve_recall(grant, "request:has-domain-object", None)
        self.assertEqual(Decision.UNKNOWN, result.decision); self.assertEqual("INCOMPLETE", result.process_compliance)

    def test_iagl_e015_resource_guard_has_no_pool_daemon_or_subprocess(self) -> None:
        tree = ast.parse((ROOT / "src" / "iagl_synthetic_supervisor.py").read_text(encoding="utf-8")); imports = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertFalse({"subprocess", "multiprocessing", "threading", "socket", "requests"} & imports)

    def test_iagl_e016_p0_remains_before_p1(self) -> None:
        self.sup.ingest(self.event("A", Priority.P1_EXACT_HEAD_REVIEW, key="review")); self.sup.ingest(self.event("A", Priority.P4_RESEARCH, key="permission", event_class="SIGNAL_MATERIALITY_CHANGED", payload={"request": "secret permission"}))
        grant = self.sup.reconcile(self.snap()); self.assertEqual(Decision.USER_GATE, self.sup.choose(grant, [self.slice()]).decision)

    def test_iagl_e017_old_domain_checkpoint_is_invalidated(self) -> None:
        _, plan, lease = self.start_p3(); self.sup.ingest(self.event("B", Priority.P4_RESEARCH)); checkpoint = self.sup.safepoint(plan, lease)
        fresh = self.sup.reconcile(self.snap("B", domain_revision="domain-2", observed_at=2)); replacement = self.store.acquire_lease("p3", "worker-a")
        self.assertEqual(Decision.BLOCKED, self.sup.resume_or_replan(checkpoint.checkpoint_id or "", fresh, replacement).decision)

    def test_iagl_e018_only_trusted_complete_empty_work_queue_is_bounded_idle(self) -> None:
        grant = self.sup.reconcile(self.snap(eligible_work_queue_complete=True)); result = self.sup.choose(grant, [])
        self.assertEqual(SupervisorState.IDLE_NO_ELIGIBLE_WORK, result.state); self.assertEqual("TRUSTED_COMPLETE_EMPTY_WORK_QUEUE", result.reason)


class R141R2AndB13B15Regressions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(); self.store = WorkingStateStore(Path(self.temp.name) / "state.sqlite"); self.sup = SyntheticSupervisor(REPO, self.store, budget_limit=10)

    def tearDown(self) -> None:
        self.store.close(); self.temp.cleanup()

    def snapshot(self, **overrides: object) -> ReconciliationSnapshot:
        data: dict[str, object] = {"repository": REPO, "exact_head": "A", "route_id": "R141", "governance_mode": GovernanceMode.AUTONOMOUS, "allowed_write_paths": PATHS, "observed_at": 1, "domain_revision": "domain-1"}
        data.update(overrides); return ReconciliationSnapshot(**data)

    def slice(self, ident: str = "same", **overrides: object) -> ImprovementSlice:
        data: dict[str, object] = {"slice_id": ident, "priority": Priority.P3_BOUNDED_IMPROVEMENT, "changed_paths": PATHS, "source_signal_refs": ("signal",), "problem_signature": "signature", "goal": "bounded goal", "materiality": "MATERIAL", "evidence_target": "evidence", "allowed_tools": ("stdlib-only",), "allowed_data_classes": ("PUBLIC_SAFE_SYNTHETIC",), "risk_class": "P3_SYNTHETIC", "time_budget_minutes": 1, "compute_budget": 1, "expected_artifact": "artifact", "falsifier": "falsifier", "stop_conditions": ("stop",), "writeback_plan": "NO_CANONICAL_WRITE", "owner": "GPT_ENGINEERING_WORKER"}
        data.update(overrides); return ImprovementSlice(**data)

    def raw_event(self, event_class: str, payload: object, key: str = "event", priority: Priority = Priority.P4_RESEARCH, target: str = "A", source: str = "synthetic") -> dict[str, object]:
        return {"event_id": key, "event_class": event_class, "source": source, "repository": REPO, "observed_at": 1, "target_ref": "refs/heads/main", "target_identity": target, "payload": payload, "idempotency_key": key, "priority_hint": int(priority)}

    def test_b09r2_low_transport_class_high_risk_structured_materiality_forces_p0(self) -> None:
        event, _ = self.sup.ingest(self.raw_event("SIGNAL_MATERIALITY_CHANGED", {"category": "research", "result": {"requires": "github_permission", "secret": "requested"}}))
        self.assertEqual(Priority.P3_BOUNDED_IMPROVEMENT, event.class_priority_hint)
        grant = self.sup.reconcile(self.snapshot()); self.assertEqual(Priority.P0_USER_OR_HIGH_RISK, self.store.event_priority(event.semantic_key))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(grant, [self.slice()]).decision)

    def test_b09r2_transient_p2_requires_complete_explicit_resolution_before_lower_work(self) -> None:
        event, _ = self.sup.ingest(self.raw_event("ROUTE_DRIFT", {"observed": "drift"}, key="drift", priority=Priority.P4_RESEARCH))
        active = self.sup.reconcile(self.snapshot(active_p2_event_keys=(event.semantic_key,)))
        self.assertEqual(Decision.BLOCKED, self.sup.choose(active, [self.slice()]).decision)
        fresh = self.sup.reconcile(self.snapshot(
            observed_at=2, p2_observation_status="AUTHORITATIVE_COMPLETE", p2_observation_ref="provider:route:complete",
            p2_resolutions=(P2Resolution(event.semantic_key, "resolution:route-fixed"),),
        ))
        self.assertEqual("RESOLVED_TRACE", self.store.event_state(event.semantic_key)); plan = self.sup.choose(fresh, [self.slice()]); self.assertEqual("same", plan.slice.slice_id)

    def test_b09r2_unresolved_p2_remains_blocking_after_new_generation(self) -> None:
        event, _ = self.sup.ingest(self.raw_event("FALSE_GREEN", {"check": "receipt"}, key="fg"))
        first = self.sup.reconcile(self.snapshot(active_p2_event_keys=(event.semantic_key,))); self.assertEqual(Decision.BLOCKED, self.sup.choose(first, [self.slice()]).decision)
        second = self.sup.reconcile(self.snapshot(observed_at=2, active_p2_event_keys=(event.semantic_key,))); self.assertEqual(Decision.BLOCKED, self.sup.choose(second, [self.slice()]).decision)
        self.assertEqual("PENDING", self.store.event_state(event.semantic_key))

    def test_b10r2_checkpoint_exact_plan_identity_cannot_switch_to_same_slice_id_plan(self) -> None:
        grant = self.sup.reconcile(self.snapshot())
        original = self.slice("same", priority=Priority.P3_BOUNDED_IMPROVEMENT, risk_class="P3_SYNTHETIC")
        alternate = self.slice("same", priority=Priority.P4_RESEARCH, risk_class="P4_SYNTHETIC", goal="alternate safe payload")
        plan_original = self.store.create_plan(grant, original); plan_alternate = self.store.create_plan(grant, alternate)
        self.assertNotEqual(plan_original.plan_id, plan_alternate.plan_id)
        lease = self.store.acquire_lease("same", "worker"); self.assertEqual(Decision.EXECUTED, self.sup.execute(plan_original, lease).decision)
        self.sup.ingest(self.raw_event("WORKFLOW_COMPLETED", {"head": "A"}, key="review")); cp = self.sup.safepoint(plan_original, lease)
        review_grant = self.sup.reconcile(self.snapshot(observed_at=2)); work = self.sup.choose(review_grant, []); self.assertEqual(Decision.EXECUTED, self.sup.review(work, ReviewEvidence("A", "A", "A", "reviewer", work)).decision)
        self.store.connection.execute("DELETE FROM plans WHERE plan_id=?", (plan_original.plan_id,)); self.store.connection.commit()
        fresh = self.sup.reconcile(self.snapshot(observed_at=3, allowed_risk_classes=("P4_SYNTHETIC",))); new_lease = self.store.acquire_lease("same", "worker")
        result = self.sup.resume_or_replan(cp.checkpoint_id or "", fresh, new_lease); self.assertEqual("CHECKPOINT_PLAN_OR_SLICE_IDENTITY_MISMATCH", result.reason)

    def test_b10r2_checkpoint_digest_detects_exact_plan_payload_tamper(self) -> None:
        grant = self.sup.reconcile(self.snapshot()); plan = self.store.create_plan(grant, self.slice("same")); lease = self.store.acquire_lease("same", "worker"); self.sup.execute(plan, lease)
        self.sup.ingest(self.raw_event("WORKFLOW_COMPLETED", {"head": "A"}, key="review2")); cp = self.sup.safepoint(plan, lease); loaded = self.store.load_checkpoint(cp.checkpoint_id or "")
        current_raw = self.store.connection.execute("SELECT slice_json FROM plans WHERE plan_id=?", (plan.plan_id,)).fetchone()[0]
        self.store.connection.execute("UPDATE plans SET slice_json=? WHERE plan_id=?", (current_raw.replace("bounded goal", "tampered goal"), plan.plan_id)); self.store.connection.commit()
        review_grant = self.sup.reconcile(self.snapshot(observed_at=2)); work = self.sup.choose(review_grant, []); self.sup.review(work, ReviewEvidence("A", "A", "A", "reviewer", work))
        fresh = self.sup.reconcile(self.snapshot(observed_at=3)); new_lease = self.store.acquire_lease("same", "worker")
        self.assertEqual("CHECKPOINT_PLAN_OR_SLICE_IDENTITY_MISMATCH", self.sup.resume_or_replan(loaded.checkpoint_id, fresh, new_lease).reason)

    def test_b11r2_snapshot_cannot_widen_stage_a_hard_ceiling(self) -> None:
        unsafe = (
            (self.snapshot(allowed_tools=("bash",)), "TOOL_CEILING"),
            (self.snapshot(allowed_data_classes=("RAW_CONVERSATION",)), "DATA_CEILING"),
            (self.snapshot(allowed_risk_classes=("C3_PRODUCTION",)), "RISK_CEILING"),
            (self.snapshot(allowed_writeback_plans=("W3_CANONICAL_WRITE",)), "WRITEBACK_CEILING"),
        )
        for snapshot, marker in unsafe:
            with self.assertRaisesRegex(SupervisorError, marker): snapshot.validate(REPO)

    def test_b11r2_alias_hard_denies_are_not_snapshot_widenable(self) -> None:
        safe = self.snapshot(); safe.validate(REPO)
        for invalid, marker in (
            (self.slice(allowed_tools=("bash",)), "FORBIDDEN_TOOL"),
            (self.slice(allowed_data_classes=("RAW_CONVERSATION",)), "FORBIDDEN_DATA"),
            (self.slice(risk_class="C4_TRADING"), "FORBIDDEN_RISK"),
            (self.slice(writeback_plan="DOMAIN_CANONICAL_WRITE"), "FORBIDDEN_WRITEBACK"),
        ):
            with self.assertRaisesRegex(SupervisorError, marker): invalid.validate(safe)

    def test_b12r2_arbitrary_complete_empty_request_without_provider_observation_is_unknown(self) -> None:
        grant = self.sup.reconcile(self.snapshot()); proof = self.sup.issue_retrieval_complete_empty_proof(grant, "caller-arbitrary-request", "caller-arbitrary-scope")
        self.assertIsNone(proof); result = self.sup.resolve_recall(grant, "caller-arbitrary-request", proof)
        self.assertEqual(Decision.UNKNOWN, result.decision); self.assertEqual("INCOMPLETE", result.process_compliance)

    def test_b12r2_preexisting_provider_observation_can_issue_but_forged_envelope_cannot(self) -> None:
        self.store.close(); observation = RetrievalProviderObservation("obs-1", "SYNTHETIC_RETRIEVAL_PROVIDER", REPO, "A", "request", "scope", "provider:evidence", True)
        provider = SyntheticRetrievalProvider((observation,)); self.store = WorkingStateStore(Path(self.temp.name) / "provider.sqlite"); self.sup = SyntheticSupervisor(REPO, self.store, retrieval_provider=provider)
        grant = self.sup.reconcile(self.snapshot()); proof = self.sup.issue_retrieval_complete_empty_proof(grant, "request", "scope"); self.assertIsNotNone(proof)
        forged = replace(proof, issuance_ref="stage-a:forged")
        self.assertEqual("UNTRUSTED", self.sup.resolve_recall(grant, "request", forged).process_compliance)
        self.assertEqual(Decision.IDLE, self.sup.resolve_recall(grant, "request", proof).decision)

    def test_b13_real_webhook_watchdog_cross_class_dedupe_preserves_both_traces_and_one_review(self) -> None:
        self.sup.reconcile(self.snapshot(exact_head="A"))
        webhook, first = self.sup.ingest(self.raw_event("PR_HEAD_CHANGED", {"head": "B"}, key="webhook-b", priority=Priority.P1_EXACT_HEAD_REVIEW, target="B", source="webhook"))
        watchdog, second = self.sup.ingest(self.raw_event("WATCHDOG_TICK", {"poll": "B"}, key="watchdog-b", priority=Priority.P4_RESEARCH, target="B", source="watchdog"))
        self.assertEqual(webhook.semantic_key, watchdog.semantic_key); self.assertTrue(first); self.assertFalse(second)
        grant = self.sup.reconcile(self.snapshot(exact_head="B", observed_at=2)); work = self.sup.choose(grant, [])
        self.assertIsInstance(work, ReviewWorkIdentity); self.assertEqual("B", work.target_head)
        self.assertEqual(("reconciliation", "watchdog", "webhook"), self.store.trace_sources(webhook.semantic_key))
        self.assertEqual(1, self.store.connection.execute("SELECT COUNT(*) FROM review_work WHERE semantic_key=?", (webhook.semantic_key,)).fetchone()[0])

    def test_b13_missed_webhook_real_watchdog_fresh_reconciliation_new_head_forces_p1(self) -> None:
        self.sup.reconcile(self.snapshot(exact_head="A"))
        tick, inserted = self.sup.ingest(self.raw_event("WATCHDOG_TICK", {"poll": "tick-only-no-head-authority"}, key="watchdog-only", target="A", source="watchdog"))
        self.assertTrue(inserted); self.assertEqual(Priority.P4_RESEARCH, tick.class_priority_hint)
        fresh = self.sup.reconcile(self.snapshot(exact_head="B", observed_at=2)); work = self.sup.choose(fresh, [self.slice("safe")])
        self.assertIsInstance(work, ReviewWorkIdentity); self.assertEqual("B", work.target_head)
        self.assertNotEqual(tick.semantic_key, work.semantic_event_key)
        self.assertIn("reconciliation", self.store.trace_sources(work.semantic_event_key))

    def test_b13_missed_webhook_watchdog_preempts_active_p3_then_reconciled_new_head_routes_p1(self) -> None:
        grant = self.sup.reconcile(self.snapshot(exact_head="A")); plan = self.sup.choose(grant, [self.slice("running")]); lease = self.store.acquire_lease("running", "worker")
        self.assertEqual(Decision.EXECUTED, self.sup.execute(plan, lease).decision)
        tick, _ = self.sup.ingest(self.raw_event("WATCHDOG_TICK", {"watchdog": "poll"}, key="watchdog-active", target="A", source="watchdog"))
        self.assertEqual(Priority.P4_RESEARCH, tick.class_priority_hint)
        paused = self.sup.safepoint(plan, lease); self.assertEqual(Decision.PREEMPTED, paused.decision)
        fresh = self.sup.reconcile(self.snapshot(exact_head="B", observed_at=2)); work = self.sup.choose(fresh, [])
        self.assertIsInstance(work, ReviewWorkIdentity); self.assertEqual("B", work.target_head); self.assertEqual(Priority.P1_EXACT_HEAD_REVIEW, self.store.event_priority(work.semantic_event_key))

    def test_b14_p0_user_disposition_requires_fresh_reconcile_preserves_trace_and_safe_work_recovers(self) -> None:
        self.sup.reconcile(self.snapshot())
        event, _ = self.sup.ingest(self.raw_event("SIGNAL_MATERIALITY_CHANGED", {"research": "needs secret", "permission": "github_permission"}, key="risk"))
        gated_grant = self.sup.reconcile(self.snapshot(observed_at=2)); self.assertEqual(Decision.USER_GATE, self.sup.choose(gated_grant, [self.slice("safe")]).decision)
        disposition = P0Disposition(event.semantic_key, "APPROVED_SEPARATE_GATED_ACTION", "user-decision:approve-separate-gate-1")
        fresh = self.sup.reconcile(self.snapshot(observed_at=3, p0_dispositions=(disposition,)))
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(event.semantic_key))
        plan = self.sup.choose(fresh, [self.slice("safe")]); self.assertEqual("safe", plan.slice.slice_id)
        with self.assertRaisesRegex(SupervisorError, "FORBIDDEN_RISK"):
            self.slice("unsafe", risk_class="C4_TRADING").validate(self.store.current_snapshot()[1])
        history = self.store.connection.execute("SELECT decision,decision_ref FROM p0_disposition_history WHERE event_key=?", (event.semantic_key,)).fetchone()
        self.assertEqual(("APPROVED_SEPARATE_GATED_ACTION", "user-decision:approve-separate-gate-1"), history)

    def test_b15_partial_empty_does_not_resolve_p2(self) -> None:
        event, _ = self.sup.ingest(self.raw_event("ROUTE_DRIFT", {"drift": "route"}, key="p2-partial"))
        active = self.sup.reconcile(self.snapshot(active_p2_event_keys=(event.semantic_key,)))
        self.assertEqual(Decision.BLOCKED, self.sup.choose(active, [self.slice()]).decision)
        partial = self.sup.reconcile(self.snapshot(observed_at=2, active_p2_event_keys=(), p2_observation_status="PARTIAL_OBSERVATION"))
        result = self.sup.choose(partial, [self.slice()]); self.assertEqual(Decision.BLOCKED, result.decision)
        self.assertEqual("PENDING", self.store.event_state(event.semantic_key))

    def test_b15_authoritative_complete_without_explicit_resolution_still_blocks(self) -> None:
        event, _ = self.sup.ingest(self.raw_event("FALSE_GREEN", {"false_green": "active"}, key="p2-complete-no-resolution"))
        self.sup.reconcile(self.snapshot(active_p2_event_keys=(event.semantic_key,)))
        complete = self.sup.reconcile(self.snapshot(observed_at=2, p2_observation_status="AUTHORITATIVE_COMPLETE", p2_observation_ref="provider:complete"))
        self.assertEqual(Decision.BLOCKED, self.sup.choose(complete, [self.slice()]).decision); self.assertEqual("PENDING", self.store.event_state(event.semantic_key))

    def test_b15_authoritative_complete_plus_explicit_resolution_unblocks(self) -> None:
        event, _ = self.sup.ingest(self.raw_event("ACTIVE_BLOCKER", {"blocker": "x"}, key="p2-resolve"))
        self.sup.reconcile(self.snapshot(active_p2_event_keys=(event.semantic_key,)))
        fresh = self.sup.reconcile(self.snapshot(
            observed_at=2, p2_observation_status="AUTHORITATIVE_COMPLETE", p2_observation_ref="provider:complete:2",
            p2_resolutions=(P2Resolution(event.semantic_key, "resolution:blocker-closed"),),
        ))
        self.assertEqual("RESOLVED_TRACE", self.store.event_state(event.semantic_key)); self.assertEqual("same", self.sup.choose(fresh, [self.slice()]).slice.slice_id)
        history = self.store.connection.execute("SELECT resolution_ref,observation_ref FROM p2_resolution_history WHERE event_key=?", (event.semantic_key,)).fetchone()
        self.assertEqual(("resolution:blocker-closed", "provider:complete:2"), history)


class SupportingContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(); self.store = WorkingStateStore(Path(self.temp.name) / "state.sqlite"); self.sup = SyntheticSupervisor(REPO, self.store, budget_limit=3)

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

    def test_same_governance_reconcile_from_check_priority_uses_legal_bridge(self) -> None:
        first = self.sup.reconcile(self.snapshot()); second = self.sup.reconcile(replace(self.snapshot(), observed_at=2)); self.assertGreater(second.generation, first.generation); self.assertEqual(SupervisorState.CHECK_PRIORITY, self.sup.state)

    def test_budget_boundary_never_reserves_past_limit(self) -> None:
        grant = self.sup.reconcile(self.snapshot()); plan = self.sup.choose(grant, [replace(self.complete_slice("over"), estimated_cost=4)])
        self.assertEqual("BUDGET_EXHAUSTED_PRE_EXECUTION", plan.reason); self.assertEqual(0, self.store.value("budget_used"))

    def test_no_current_event_cannot_create_or_complete_trusted_review(self) -> None:
        grant = self.sup.reconcile(self.snapshot()); self.assertEqual(Decision.UNKNOWN, self.sup.choose(grant, []).decision)
        forged = ReviewWorkIdentity("event:absent", "A", grant.identity, grant.generation); self.sup.state = SupervisorState.REVIEW
        self.assertEqual(Decision.BLOCKED, self.sup.review(forged, ReviewEvidence("A", "A", "A", "synthetic", forged)).decision)

    def test_retrieval_complete_empty_requires_preexisting_provider_observation(self) -> None:
        self.store.close(); observation = RetrievalProviderObservation("obs", "SYNTHETIC_RETRIEVAL_PROVIDER", REPO, "A", "request", "scope", "evidence", True)
        self.store = WorkingStateStore(Path(self.temp.name) / "provider.sqlite"); self.sup = SyntheticSupervisor(REPO, self.store, retrieval_provider=SyntheticRetrievalProvider((observation,)))
        grant = self.sup.reconcile(self.snapshot()); proof = self.sup.issue_retrieval_complete_empty_proof(grant, "request", "scope"); self.assertEqual(Decision.IDLE, self.sup.resolve_recall(grant, "request", proof).decision)

    def test_slice_contract_rejects_missing_risk_stop_or_writeback(self) -> None:
        grant = self.sup.reconcile(self.snapshot())
        for invalid in (replace(self.complete_slice(), risk_class=""), replace(self.complete_slice(), stop_conditions=()), replace(self.complete_slice(), writeback_plan="")):
            with self.assertRaisesRegex(SupervisorError, "FROZEN_CONTRACT"): self.sup.choose(grant, [invalid])

    def test_checkpoint_contract_rejects_missing_exact_plan_binding_or_privacy(self) -> None:
        checkpoint = Checkpoint("cp", "mission", "slice", "plan", "slice-digest", "SAFEPOINT_CHECKPOINT", 1, "snapshot", ("source",), ("digest",), ("step",), ("unknown",), "resume", "used:1", "lease", "fence", "P1", RESUME_PRECONDITIONS, "PUBLIC_SAFE_SYNTHETIC", "snapshot", 1, 1, "A", "R141", "domain")
        self.store.save_checkpoint(checkpoint)
        for invalid in (replace(checkpoint, plan_id=""), replace(checkpoint, slice_digest=""), replace(checkpoint, privacy_class="")):
            with self.assertRaises(SupervisorError): self.store.save_checkpoint(invalid)

    def test_stale_resume_preconditions_fail_closed(self) -> None:
        grant = self.sup.reconcile(self.snapshot()); plan = self.sup.choose(grant, [self.complete_slice("slice-x")]); lease = self.store.acquire_lease("slice-x", "owner"); self.sup.execute(plan, lease)
        self.sup.ingest({"event_id": "p1", "event_class": "PR_HEAD_CHANGED", "source": "synthetic", "repository": REPO, "observed_at": 1, "target_ref": "refs/heads/main", "target_identity": "B", "payload": {"head": "B"}, "idempotency_key": "p1", "priority_hint": 1})
        cp = self.sup.safepoint(plan, lease); loaded = self.store.load_checkpoint(cp.checkpoint_id or ""); record = self.store.connection.execute("SELECT record FROM checkpoints WHERE checkpoint_id=?", (loaded.checkpoint_id,)).fetchone()[0]
        forged = json.loads(record); forged["resume_preconditions"] = []; self.store.connection.execute("UPDATE checkpoints SET record=? WHERE checkpoint_id=?", (json.dumps(forged), loaded.checkpoint_id)); self.store.connection.commit()
        fresh = self.sup.reconcile(ReconciliationSnapshot(REPO, "B", "R141", GovernanceMode.AUTONOMOUS, PATHS, 2)); lease_new = self.store.acquire_lease("slice-x", "owner")
        self.assertEqual(Decision.BLOCKED, self.sup.resume_or_replan(cp.checkpoint_id or "", fresh, lease_new).decision)


if __name__ == "__main__":
    unittest.main(verbosity=2)
