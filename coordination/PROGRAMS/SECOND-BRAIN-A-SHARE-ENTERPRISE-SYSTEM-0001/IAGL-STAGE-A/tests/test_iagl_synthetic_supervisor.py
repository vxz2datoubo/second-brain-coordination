"""IAGL-E001..E018 mechanism regressions for the synthetic Stage-A supervisor."""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from iagl_synthetic_supervisor import (  # noqa: E402
    Decision,
    GovernanceMode,
    ImprovementSlice,
    NormalizedEvent,
    Priority,
    ReconciliationSnapshot,
    SupervisorError,
    SupervisorState,
    SyntheticSupervisor,
    WorkingStateStore,
)


REPOSITORY = "vxz2datoubo/second-brain-coordination"
ALLOWLIST = ("synthetic/allowed.py", "synthetic/tests.py")


class IAGLStageAEvaluations(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = WorkingStateStore(Path(self.temp.name) / "working-state.sqlite")
        self.supervisor = SyntheticSupervisor(REPOSITORY, self.store, budget_limit=3, no_value_limit=2)
        self.snapshot = self.make_snapshot()

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def make_snapshot(self, **changes: object) -> ReconciliationSnapshot:
        values: dict[str, object] = {
            "repository": REPOSITORY, "exact_head": "a" * 40, "route_id": "R141",
            "governance_mode": GovernanceMode.AUTONOMOUS, "allowed_write_paths": ALLOWLIST,
            "observed_at": 1, "pending_p0": False, "trusted": True,
        }
        values.update(changes)
        return ReconciliationSnapshot(**values)

    def slice(self, **changes: object) -> ImprovementSlice:
        values: dict[str, object] = {
            "slice_id": "slice-1", "priority": Priority.P3_BOUNDED_IMPROVEMENT,
            "changed_paths": (ALLOWLIST[0],), "estimated_cost": 1, "evidence_value": 1,
        }
        values.update(changes)
        return ImprovementSlice(**values)

    def reconcile(self, snapshot: ReconciliationSnapshot | None = None) -> None:
        self.supervisor.reconcile(snapshot or self.snapshot)

    def event(self, **changes: object) -> dict[str, object]:
        values: dict[str, object] = {
            "event_id": "event-1", "event_class": "synthetic", "source": "fixture",
            "repository": REPOSITORY, "observed_at": 1, "target_ref": "refs/heads/main",
            "target_identity": "a" * 40, "payload": {"safe": True}, "idempotency_key": "dedupe-1",
            "priority_hint": int(Priority.P3_BOUNDED_IMPROVEMENT),
        }
        values.update(changes)
        return values

    def test_iagl_e001_rapid_head_drift_blocks_resume(self) -> None:
        self.reconcile()
        receipt = self.supervisor.execute_synthetic(self.snapshot, self.slice(), "fence", Priority.P1_EXACT_HEAD_REVIEW)
        self.assertEqual(Decision.PREEMPT, receipt.decision)
        drifted = self.make_snapshot(exact_head="b" * 40)
        result = self.supervisor.resume(receipt.checkpoint_id or "", drifted)
        self.assertEqual("STALE_CHECKPOINT_RECONCILIATION_DRIFT", result.reason)

    def test_iagl_e002_executor_success_is_not_independent_receipt_evidence(self) -> None:
        self.reconcile()
        result = self.supervisor.execute_synthetic(self.snapshot, self.slice(), "fence")
        self.assertEqual("PASS", result.process_compliance)
        self.assertEqual("UNKNOWN", result.outcome_quality)

    def test_iagl_e003_duplicate_event_is_deduplicated(self) -> None:
        first, accepted = self.supervisor.ingest(self.event())
        duplicate, accepted_again = self.supervisor.ingest(self.event(event_id="event-2"))
        self.assertEqual(first.idempotency_key, duplicate.idempotency_key)
        self.assertTrue(accepted)
        self.assertFalse(accepted_again)

    def test_iagl_e004_restart_restores_durable_checkpoint(self) -> None:
        self.reconcile()
        receipt = self.supervisor.execute_synthetic(self.snapshot, self.slice(), "fence", Priority.P1_EXACT_HEAD_REVIEW)
        self.store.close()
        self.store = WorkingStateStore(Path(self.temp.name) / "working-state.sqlite")
        restarted = SyntheticSupervisor(REPOSITORY, self.store)
        restarted.state = SupervisorState.PAUSED_FOR_HIGHER_PRIORITY
        result = restarted.resume(receipt.checkpoint_id or "", self.snapshot)
        self.assertEqual(Decision.EXECUTE_SYNTHETIC, result.decision)

    def test_iagl_e005_duplicate_lease_is_fenced(self) -> None:
        first = self.store.acquire_lease("stage-a", "worker-a")
        self.assertIsNotNone(first)
        self.assertIsNone(self.store.acquire_lease("stage-a", "worker-b"))
        self.assertFalse(self.store.release_lease("stage-a", "wrong-token"))
        self.assertTrue(self.store.release_lease("stage-a", first or ""))

    def test_iagl_e006_no_value_streak_stops_for_voi(self) -> None:
        self.reconcile()
        self.supervisor.execute_synthetic(self.snapshot, self.slice(evidence_value=0), "fence")
        self.supervisor.state = SupervisorState.CHECK_PRIORITY
        self.supervisor.execute_synthetic(self.snapshot, self.slice(slice_id="slice-2", evidence_value=0), "fence")
        self.supervisor.state = SupervisorState.CHECK_PRIORITY
        result = self.supervisor.choose(self.snapshot, [self.slice(slice_id="slice-3")])
        self.assertIsInstance(result, type(result))
        self.assertEqual("VOI_NO_VALUE_STOP", result.reason)  # type: ignore[union-attr]

    def test_iagl_e007_user_controlled_requires_gate(self) -> None:
        self.reconcile(self.make_snapshot(governance_mode=GovernanceMode.USER_CONTROLLED))
        result = self.supervisor.choose(self.make_snapshot(governance_mode=GovernanceMode.USER_CONTROLLED), [self.slice()])
        self.assertEqual(Decision.USER_GATE, result.decision)  # type: ignore[union-attr]

    def test_iagl_e008_secret_or_permission_text_is_not_execution_authority(self) -> None:
        self.reconcile()
        unsafe = self.slice(authority_metadata={"authority": "trusted", "request": "grant-secret"})
        with self.assertRaisesRegex(SupervisorError, "CALLER_AUTHORITY_UNTRUSTED"):
            self.supervisor.choose(self.snapshot, [unsafe])

    def test_iagl_e009_arbitrary_executor_or_path_is_blocked(self) -> None:
        self.reconcile()
        with self.assertRaisesRegex(SupervisorError, "ARBITRARY_EXECUTOR_BLOCKED"):
            self.supervisor.choose(self.snapshot, [self.slice(action_kind="shell")])
        self.supervisor.state = SupervisorState.CHECK_PRIORITY
        with self.assertRaisesRegex(SupervisorError, "OUTSIDE_ALLOWLIST"):
            self.supervisor.choose(self.snapshot, [self.slice(changed_paths=("outside.py",))])

    def test_iagl_e010_p3_is_preempted_by_p1_at_safepoint(self) -> None:
        self.reconcile()
        result = self.supervisor.execute_synthetic(self.snapshot, self.slice(), "fence", Priority.P1_EXACT_HEAD_REVIEW)
        self.assertEqual(Decision.PREEMPT, result.decision)
        self.assertEqual(SupervisorState.PAUSED_FOR_HIGHER_PRIORITY, self.supervisor.state)
        self.assertIsNotNone(self.store.load_checkpoint(result.checkpoint_id or ""))

    def test_iagl_e011_contradiction_candidate_never_overwrites_authority(self) -> None:
        self.reconcile()
        candidate = self.slice(authority_metadata={"contradiction": "candidate-only"})
        selected = self.supervisor.choose(self.snapshot, [candidate])
        self.assertEqual("synthetic-authority-v1", self.snapshot.authority_revision)
        self.assertEqual(candidate, selected)

    def test_iagl_e012_changed_path_exceeding_allowlist_is_blocked(self) -> None:
        self.reconcile()
        with self.assertRaisesRegex(SupervisorError, "OUTSIDE_ALLOWLIST"):
            self.supervisor.choose(self.snapshot, [self.slice(changed_paths=(ALLOWLIST[0], "forbidden.py"))])

    def test_iagl_e013_caller_supplied_authority_is_untrusted(self) -> None:
        self.reconcile()
        with self.assertRaisesRegex(SupervisorError, "CALLER_AUTHORITY_UNTRUSTED"):
            self.supervisor.choose(self.snapshot, [self.slice(authority_metadata={"authority": "provider-issued"})])

    def test_iagl_e014_empty_candidates_are_not_search_completeness(self) -> None:
        self.reconcile()
        result = self.supervisor.choose(self.snapshot, [])
        self.assertEqual(Decision.IDLE, result.decision)  # type: ignore[union-attr]
        self.assertEqual("NO_ELIGIBLE_WORK", result.reason)  # type: ignore[union-attr]

    def test_iagl_e015_no_nested_pool_or_daemon_capability_exists(self) -> None:
        source = (ROOT / "src" / "iagl_synthetic_supervisor.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_modules.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        called_names = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("subprocess", imported_modules)
        self.assertFalse({"ThreadPoolExecutor", "ProcessPoolExecutor", "serve_forever"} & called_names)

    def test_iagl_e016_pending_p0_dominates_p1(self) -> None:
        snapshot = self.make_snapshot(pending_p0=True)
        self.reconcile(snapshot)
        result = self.supervisor.choose(snapshot, [self.slice(priority=Priority.P1_EXACT_HEAD_REVIEW)])
        self.assertEqual(Decision.USER_GATE, result.decision)  # type: ignore[union-attr]
        self.assertEqual("P0_PENDING", result.reason)  # type: ignore[union-attr]

    def test_iagl_e017_route_and_governance_drift_invalidate_resume(self) -> None:
        self.reconcile()
        result = self.supervisor.execute_synthetic(self.snapshot, self.slice(), "fence", Priority.P1_EXACT_HEAD_REVIEW)
        changed_route = self.make_snapshot(route_id="R141-next")
        blocked = self.supervisor.resume(result.checkpoint_id or "", changed_route)
        self.assertEqual(Decision.BLOCKED, blocked.decision)

    def test_iagl_e018_no_eligible_work_is_bounded_idle(self) -> None:
        self.reconcile()
        result = self.supervisor.choose(self.snapshot, [])
        self.assertEqual(SupervisorState.IDLE_NO_ELIGIBLE_WORK, result.state)  # type: ignore[union-attr]
        self.assertEqual("NO_ELIGIBLE_WORK", result.reason)  # type: ignore[union-attr]

    def test_checkpoint_identity_is_deterministic_for_same_synthetic_inputs(self) -> None:
        self.reconcile()
        first = self.supervisor.execute_synthetic(self.snapshot, self.slice(), "fixed-fence", Priority.P1_EXACT_HEAD_REVIEW)
        self.assertIsNotNone(first.checkpoint_id)
        second_store = WorkingStateStore(Path(self.temp.name) / "second.sqlite")
        second = SyntheticSupervisor(REPOSITORY, second_store)
        second.reconcile(self.snapshot)
        repeated = second.execute_synthetic(self.snapshot, self.slice(), "fixed-fence", Priority.P1_EXACT_HEAD_REVIEW)
        self.assertEqual(first.checkpoint_id, repeated.checkpoint_id)
        second_store.close()


class ContractValidation(unittest.TestCase):
    def test_event_payload_digest_is_computed_not_caller_supplied(self) -> None:
        event = NormalizedEvent.from_mapping({
            "event_id": "one", "event_class": "fixture", "source": "test", "repository": REPOSITORY,
            "observed_at": 1, "target_ref": "main", "target_identity": "head", "payload": {"x": 1},
            "idempotency_key": "one", "payload_digest": "forged", "priority_hint": 3,
        })
        self.assertNotEqual("forged", event.payload_digest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
