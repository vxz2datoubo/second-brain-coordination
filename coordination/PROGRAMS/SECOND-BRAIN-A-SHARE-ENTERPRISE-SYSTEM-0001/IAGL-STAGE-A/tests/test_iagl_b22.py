from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
from iagl_synthetic_supervisor import (  # noqa: E402
    Decision, GovernanceMode, ImprovementSlice, P0Disposition, Priority,
    ReconciliationSnapshot, SyntheticSupervisor, WorkingStateStore,
)

REPO = "vxz2datoubo/second-brain-coordination"
PATHS = ("synthetic/allowed.py",)


class B22OccurrenceIdempotencyRegressions(unittest.TestCase):
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

    def safe_slice(self, ident: str = "safe") -> ImprovementSlice:
        return ImprovementSlice(
            slice_id=ident,
            priority=Priority.P3_BOUNDED_IMPROVEMENT,
            changed_paths=PATHS,
            source_signal_refs=("signal",),
            problem_signature="signature",
            goal="bounded goal",
            materiality="MATERIAL",
            evidence_target="evidence",
            allowed_tools=("stdlib-only",),
            allowed_data_classes=("PUBLIC_SAFE_SYNTHETIC",),
            risk_class="P3_SYNTHETIC",
            time_budget_minutes=1,
            compute_budget=1,
            expected_artifact="artifact",
            falsifier="falsifier",
            stop_conditions=("stop",),
            writeback_plan="NO_CANONICAL_WRITE",
            owner="GPT_ENGINEERING_WORKER",
        )

    def risk(self, event_id: str, idempotency_key: str, observed_at: int = 1) -> dict[str, object]:
        return {
            "event_id": event_id,
            "event_class": "SIGNAL_MATERIALITY_CHANGED",
            "source": "synthetic",
            "repository": REPO,
            "observed_at": observed_at,
            "target_ref": "refs/heads/main",
            "target_identity": "A",
            "payload": {"request": "secret permission"},
            "idempotency_key": idempotency_key,
            "priority_hint": int(Priority.P4_RESEARCH),
        }

    def dispose_first_occurrence(self):
        event, inserted = self.sup.ingest(self.risk("risk-occurrence-1", "occurrence-1"))
        self.assertTrue(inserted)
        first = self.sup.reconcile(self.snapshot())
        self.assertEqual(Decision.USER_GATE, self.sup.choose(first, [self.safe_slice()]).decision)
        disposed = self.sup.reconcile(self.snapshot(
            observed_at=2,
            p0_dispositions=(P0Disposition(event.semantic_key, "DENIED", "user:decision:1"),),
        ))
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(event.semantic_key))
        self.assertEqual("safe", self.sup.choose(disposed, [self.safe_slice()]).slice.slice_id)
        return event, disposed

    def test_b22_exact_duplicate_same_occurrence_and_idempotency_does_not_regate(self) -> None:
        event, disposed = self.dispose_first_occurrence()
        traces_before = self.store.connection.execute(
            "SELECT trace_id,state FROM event_traces WHERE semantic_key=? ORDER BY trace_id",
            (event.semantic_key,),
        ).fetchall()

        duplicate, inserted = self.sup.ingest(self.risk("risk-occurrence-1", "occurrence-1"))
        self.assertFalse(inserted)
        self.assertEqual(event.semantic_key, duplicate.semantic_key)
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(event.semantic_key))
        self.assertEqual(("occurrence-1",), self.store.occurrence_idempotencies(event.semantic_key))
        self.assertEqual(
            (("DENIED", "user:decision:1"),),
            self.store.p0_disposition_history(event.semantic_key),
        )
        self.assertEqual(
            traces_before,
            self.store.connection.execute(
                "SELECT trace_id,state FROM event_traces WHERE semantic_key=? ORDER BY trace_id",
                (event.semantic_key,),
            ).fetchall(),
        )
        self.assertEqual("safe-duplicate", self.sup.choose(disposed, [self.safe_slice("safe-duplicate")]).slice.slice_id)

        # A transport retry may alter its envelope event_id/time, but the same
        # idempotency key for the same semantic target state is still one occurrence.
        retry, inserted = self.sup.ingest(self.risk("transport-retry", "occurrence-1", observed_at=9))
        self.assertFalse(inserted)
        self.assertEqual(event.semantic_key, retry.semantic_key)
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(event.semantic_key))
        self.assertEqual(("occurrence-1",), self.store.occurrence_idempotencies(event.semantic_key))
        trace_states = tuple(row[0] for row in self.store.connection.execute(
            "SELECT state FROM event_traces WHERE semantic_key=? ORDER BY observed_at,trace_id",
            (event.semantic_key,),
        ).fetchall())
        self.assertIn("DUPLICATE_REDELIVERY", trace_states)
        self.assertEqual(
            (("DENIED", "user:decision:1"),),
            self.store.p0_disposition_history(event.semantic_key),
        )
        self.assertEqual("safe-retry", self.sup.choose(disposed, [self.safe_slice("safe-retry")]).slice.slice_id)

    def test_b22_genuine_new_occurrence_regates_and_requires_new_current_disposition(self) -> None:
        event, disposed = self.dispose_first_occurrence()
        recurrent, inserted = self.sup.ingest(self.risk("risk-occurrence-2", "occurrence-2", observed_at=3))
        self.assertFalse(inserted)  # semantic row already exists; occurrence is still new.
        self.assertEqual(event.semantic_key, recurrent.semantic_key)
        self.assertEqual(("occurrence-1", "occurrence-2"), self.store.occurrence_idempotencies(event.semantic_key))
        self.assertEqual("PENDING", self.store.event_state(event.semantic_key))
        stale = self.sup.choose(disposed, [self.safe_slice("stale")])
        self.assertEqual(Decision.BLOCKED, stale.decision)
        self.assertEqual("FRESH_RECONCILIATION_REQUIRED_FOR_PENDING_EVENT", stale.reason)

        regated = self.sup.reconcile(self.snapshot(observed_at=3))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(regated, [self.safe_slice()]).decision)

        old_disposition_replay = self.sup.reconcile(self.snapshot(
            observed_at=4,
            p0_dispositions=(P0Disposition(event.semantic_key, "DENIED", "user:decision:1"),),
        ))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(old_disposition_replay, [self.safe_slice()]).decision)
        self.assertEqual(
            (("DENIED", "user:decision:1"),),
            self.store.p0_disposition_history(event.semantic_key),
        )

        newly_disposed = self.sup.reconcile(self.snapshot(
            observed_at=5,
            p0_dispositions=(P0Disposition(event.semantic_key, "DENIED", "user:decision:2"),),
        ))
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(event.semantic_key))
        self.assertEqual(
            (("DENIED", "user:decision:1"), ("DENIED", "user:decision:2")),
            self.store.p0_disposition_history(event.semantic_key),
        )
        self.assertEqual("safe-again", self.sup.choose(newly_disposed, [self.safe_slice("safe-again")]).slice.slice_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
