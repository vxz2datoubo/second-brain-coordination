from __future__ import annotations

import ast
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
import iagl_synthetic_supervisor as runtime  # noqa: E402
from iagl_synthetic_supervisor import (  # noqa: E402
    Decision, GovernanceMode, ImprovementSlice, P0Disposition, P2Resolution,
    Priority, ReconciliationSnapshot, SupervisorError, SyntheticSupervisor,
    WorkingStateStore,
)

REPO = "vxz2datoubo/second-brain-coordination"
PATHS = ("synthetic/allowed.py",)


class B19B21Regressions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = WorkingStateStore(Path(self.temp.name) / "state.sqlite")
        self.sup = SyntheticSupervisor(REPO, self.store, budget_limit=10)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def snapshot(self, **overrides: object) -> ReconciliationSnapshot:
        data: dict[str, object] = {
            "repository": REPO,
            "exact_head": "A",
            "route_id": "R141",
            "governance_mode": GovernanceMode.AUTONOMOUS,
            "allowed_write_paths": PATHS,
            "observed_at": 1,
            "domain_revision": "domain-1",
        }
        data.update(overrides)
        return ReconciliationSnapshot(**data)

    def slice(self, ident: str = "safe", **overrides: object) -> ImprovementSlice:
        data: dict[str, object] = {
            "slice_id": ident,
            "priority": Priority.P3_BOUNDED_IMPROVEMENT,
            "changed_paths": PATHS,
            "source_signal_refs": ("signal",),
            "problem_signature": "signature",
            "goal": "bounded goal",
            "materiality": "MATERIAL",
            "evidence_target": "evidence",
            "allowed_tools": ("stdlib-only",),
            "allowed_data_classes": ("PUBLIC_SAFE_SYNTHETIC",),
            "risk_class": "P3_SYNTHETIC",
            "time_budget_minutes": 1,
            "compute_budget": 1,
            "expected_artifact": "artifact",
            "falsifier": "falsifier",
            "stop_conditions": ("stop",),
            "writeback_plan": "NO_CANONICAL_WRITE",
            "owner": "GPT_ENGINEERING_WORKER",
        }
        data.update(overrides)
        return ImprovementSlice(**data)

    def risk(self, event_id: str = "risk") -> dict[str, object]:
        return {
            "event_id": event_id,
            "event_class": "SIGNAL_MATERIALITY_CHANGED",
            "source": "synthetic",
            "repository": REPO,
            "observed_at": 1,
            "target_ref": "refs/heads/main",
            "target_identity": "A",
            "payload": {"request": "secret permission"},
            "idempotency_key": event_id,
            "priority_hint": int(Priority.P4_RESEARCH),
        }

    def test_b19_single_canonical_runtime_has_no_shadow_and_rejects_incompatible_store(self) -> None:
        source_path = ROOT / "src" / "iagl_synthetic_supervisor.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        self.assertEqual(1, classes.count("SyntheticSupervisor"))
        self.assertEqual(1, classes.count("WorkingStateStore"))
        self.assertFalse((ROOT / "src" / "iagl_synthetic_supervisor_core.py").exists())
        self.assertIsNone(importlib.util.find_spec("iagl_synthetic_supervisor_core"))
        self.assertIs(SyntheticSupervisor, runtime.SyntheticSupervisor)
        self.assertIs(WorkingStateStore, runtime.WorkingStateStore)

        class IncompatibleStore(WorkingStateStore):
            pass

        temp = tempfile.TemporaryDirectory()
        bad_store = IncompatibleStore(Path(temp.name) / "bad.sqlite")
        try:
            with self.assertRaisesRegex(SupervisorError, "CANONICAL_WORKING_STATE_STORE_REQUIRED"):
                SyntheticSupervisor(REPO, bad_store)
        finally:
            bad_store.close()
            temp.cleanup()

    def test_b20_zero_prior_event_authoritative_p2_blocks_then_explicit_resolution_recovers(self) -> None:
        self.assertEqual(0, self.store.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])
        active = self.sup.reconcile(self.snapshot(
            active_p2_classes=("ROUTE_DRIFT",),
            p2_observation_status="AUTHORITATIVE_COMPLETE",
            p2_observation_ref="provider:route-active",
        ))
        result = self.sup.choose(active, [self.slice()])
        self.assertEqual(Decision.BLOCKED, result.decision)
        event = self.store.highest_event(active.generation)
        self.assertIsNotNone(event)
        self.assertEqual("reconciliation", event.source)
        self.assertEqual("ROUTE_DRIFT", event.event_class)
        self.assertEqual(Priority.P2_BLOCKER_OR_DRIFT, self.store.event_priority(event.semantic_key))

        resolved = self.sup.reconcile(self.snapshot(
            observed_at=2,
            p2_observation_status="AUTHORITATIVE_COMPLETE",
            p2_observation_ref="provider:route-resolved",
            p2_resolutions=(P2Resolution(event.semantic_key, "resolution:route-fixed"),),
        ))
        self.assertEqual("RESOLVED_TRACE", self.store.event_state(event.semantic_key))
        plan = self.sup.choose(resolved, [self.slice()])
        self.assertEqual("safe", plan.slice.slice_id)

    def test_b21_identical_high_risk_recurrence_regates_and_preserves_decision_history(self) -> None:
        event, _ = self.sup.ingest(self.risk())
        first = self.sup.reconcile(self.snapshot())
        self.assertEqual(Decision.USER_GATE, self.sup.choose(first, [self.slice()]).decision)

        disposed = self.sup.reconcile(self.snapshot(
            observed_at=2,
            p0_dispositions=(P0Disposition(event.semantic_key, "DENIED", "user:decision:1"),),
        ))
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(event.semantic_key))
        self.assertEqual("safe", self.sup.choose(disposed, [self.slice()]).slice.slice_id)
        self.assertEqual((("DENIED", "user:decision:1"),), self.store.p0_disposition_history(event.semantic_key))

        recurrent, inserted = self.sup.ingest(self.risk("risk-recurred"))
        self.assertFalse(inserted)
        self.assertEqual(event.semantic_key, recurrent.semantic_key)
        self.assertEqual("PENDING", self.store.event_state(event.semantic_key))

        reused_old_decision = self.sup.reconcile(self.snapshot(
            observed_at=3,
            p0_dispositions=(P0Disposition(event.semantic_key, "DENIED", "user:decision:1"),),
        ))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(reused_old_decision, [self.slice()]).decision)
        self.assertEqual((("DENIED", "user:decision:1"),), self.store.p0_disposition_history(event.semantic_key))

        newly_disposed = self.sup.reconcile(self.snapshot(
            observed_at=4,
            p0_dispositions=(P0Disposition(event.semantic_key, "DENIED", "user:decision:2"),),
        ))
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(event.semantic_key))
        self.assertEqual(
            (("DENIED", "user:decision:1"), ("DENIED", "user:decision:2")),
            self.store.p0_disposition_history(event.semantic_key),
        )
        self.assertEqual("safe", self.sup.choose(newly_disposed, [self.slice()]).slice.slice_id)

    def test_b16_recurrence_remains_mechanical_after_single_runtime_collapse(self) -> None:
        raw = {
            "event_id": "p2",
            "event_class": "ACTIVE_BLOCKER",
            "source": "synthetic",
            "repository": REPO,
            "observed_at": 1,
            "target_ref": "refs/heads/main",
            "target_identity": "A",
            "payload": {"blocker": "recurring"},
            "idempotency_key": "p2",
            "priority_hint": int(Priority.P4_RESEARCH),
        }
        event, _ = self.sup.ingest(raw)
        active = self.sup.reconcile(self.snapshot(
            active_p2_event_keys=(event.semantic_key,),
            p2_observation_status="AUTHORITATIVE_COMPLETE",
            p2_observation_ref="provider:active",
        ))
        self.assertEqual(Decision.BLOCKED, self.sup.choose(active, [self.slice()]).decision)
        resolved = self.sup.reconcile(self.snapshot(
            observed_at=2,
            p2_observation_status="AUTHORITATIVE_COMPLETE",
            p2_observation_ref="provider:resolved",
            p2_resolutions=(P2Resolution(event.semantic_key, "resolution:first"),),
        ))
        self.assertEqual("safe", self.sup.choose(resolved, [self.slice()]).slice.slice_id)
        recurrent = self.sup.reconcile(self.snapshot(
            observed_at=3,
            active_p2_event_keys=(event.semantic_key,),
            p2_observation_status="AUTHORITATIVE_COMPLETE",
            p2_observation_ref="provider:active-again",
        ))
        self.assertEqual(Decision.BLOCKED, self.sup.choose(recurrent, [self.slice()]).decision)
        self.assertEqual(("RESOLVED", "REACTIVATED"), self.store.p2_lifecycle(event.semantic_key))


if __name__ == "__main__":
    unittest.main(verbosity=2)
