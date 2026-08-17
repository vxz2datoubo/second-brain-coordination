from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
import iagl_synthetic_supervisor as runtime  # noqa: E402
from iagl_synthetic_supervisor import (  # noqa: E402
    Decision, GovernanceMode, ImprovementSlice, P0ApprovalBinding, P0Disposition, Priority,
    ReconciliationSnapshot, SyntheticSupervisor, WorkingStateStore,
)

REPO = "vxz2datoubo/second-brain-coordination"
PATHS = ("synthetic/allowed.py",)


class B22B24OccurrenceRegressions(unittest.TestCase):
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

    def bound_disposition(self, event_key: str, ref: str, binding: P0ApprovalBinding | None = None, decision: str = "DENIED") -> P0Disposition:
        active = binding or self.store.current_p0_approval(event_key)
        self.assertIsNotNone(active)
        return P0Disposition(event_key, decision, ref, active.occurrence_key, active.approval_epoch)

    def dispose_first_occurrence(self):
        event, inserted = self.sup.ingest(self.risk("risk-occurrence-1", "occurrence-1"))
        self.assertTrue(inserted)
        first = self.sup.reconcile(self.snapshot())
        self.assertEqual(Decision.USER_GATE, self.sup.choose(first, [self.safe_slice()]).decision)
        disposed = self.sup.reconcile(self.snapshot(
            observed_at=2,
            p0_dispositions=(self.bound_disposition(event.semantic_key, "user:decision:1"),),
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
        self.assertIsNone(self.store.current_p0_approval(event.semantic_key))
        self.assertEqual(("occurrence-1",), self.store.occurrence_idempotencies(event.semantic_key))
        self.assertEqual((("DENIED", "user:decision:1"),), self.store.p0_disposition_history(event.semantic_key))
        self.assertEqual(
            traces_before,
            self.store.connection.execute(
                "SELECT trace_id,state FROM event_traces WHERE semantic_key=? ORDER BY trace_id",
                (event.semantic_key,),
            ).fetchall(),
        )
        self.assertEqual("safe-duplicate", self.sup.choose(disposed, [self.safe_slice("safe-duplicate")]).slice.slice_id)

        retry, inserted = self.sup.ingest(self.risk("transport-retry", "occurrence-1", observed_at=9))
        self.assertFalse(inserted)
        self.assertEqual(event.semantic_key, retry.semantic_key)
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(event.semantic_key))
        self.assertIsNone(self.store.current_p0_approval(event.semantic_key))
        self.assertEqual(("occurrence-1",), self.store.occurrence_idempotencies(event.semantic_key))
        trace_states = tuple(row[0] for row in self.store.connection.execute(
            "SELECT state FROM event_traces WHERE semantic_key=? ORDER BY observed_at,trace_id",
            (event.semantic_key,),
        ).fetchall())
        self.assertIn("DUPLICATE_REDELIVERY", trace_states)
        self.assertEqual((("DENIED", "user:decision:1"),), self.store.p0_disposition_history(event.semantic_key))
        self.assertEqual("safe-retry", self.sup.choose(disposed, [self.safe_slice("safe-retry")]).slice.slice_id)

    def test_b22_genuine_new_occurrence_regates_and_requires_new_current_disposition(self) -> None:
        event, disposed = self.dispose_first_occurrence()
        recurrent, inserted = self.sup.ingest(self.risk("risk-occurrence-2", "occurrence-2", observed_at=3))
        self.assertFalse(inserted)
        self.assertEqual(event.semantic_key, recurrent.semantic_key)
        self.assertEqual(("occurrence-1", "occurrence-2"), self.store.occurrence_idempotencies(event.semantic_key))
        binding2 = self.store.current_p0_approval(event.semantic_key)
        self.assertIsNotNone(binding2)
        self.assertEqual(2, binding2.approval_epoch)
        self.assertEqual("PENDING", self.store.event_state(event.semantic_key))
        stale = self.sup.choose(disposed, [self.safe_slice("stale")])
        self.assertEqual(Decision.BLOCKED, stale.decision)
        self.assertEqual("FRESH_RECONCILIATION_REQUIRED_FOR_PENDING_EVENT", stale.reason)

        regated = self.sup.reconcile(self.snapshot(observed_at=3))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(regated, [self.safe_slice()]).decision)

        first_binding = P0ApprovalBinding(event.semantic_key, runtime.digest({"semantic_key": event.semantic_key, "idempotency_key": "occurrence-1"}), 1, 1)
        old_disposition_replay = self.sup.reconcile(self.snapshot(
            observed_at=4,
            p0_dispositions=(self.bound_disposition(event.semantic_key, "user:decision:1", first_binding),),
        ))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(old_disposition_replay, [self.safe_slice()]).decision)
        self.assertEqual((("DENIED", "user:decision:1"),), self.store.p0_disposition_history(event.semantic_key))

        newly_disposed = self.sup.reconcile(self.snapshot(
            observed_at=5,
            p0_dispositions=(self.bound_disposition(event.semantic_key, "user:decision:2", binding2),),
        ))
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(event.semantic_key))
        self.assertEqual(
            (("DENIED", "user:decision:1"), ("DENIED", "user:decision:2")),
            self.store.p0_disposition_history(event.semantic_key),
        )
        self.assertEqual("safe-again", self.sup.choose(newly_disposed, [self.safe_slice("safe-again")]).slice.slice_id)

    def test_b23_old_unused_prior_occurrence_disposition_is_stale_until_current_bound_disposition(self) -> None:
        event, _ = self.sup.ingest(self.risk("risk-occurrence-1", "occurrence-1"))
        gate1 = self.store.current_p0_approval(event.semantic_key)
        self.assertIsNotNone(gate1)
        old_unused_a = self.bound_disposition(event.semantic_key, "user:old-unused-A", gate1)
        self.sup.reconcile(self.snapshot(observed_at=1))

        resolved1 = self.sup.reconcile(self.snapshot(
            observed_at=2,
            p0_dispositions=(self.bound_disposition(event.semantic_key, "user:decision-B", gate1),),
        ))
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(event.semantic_key))
        self.assertEqual("safe-1", self.sup.choose(resolved1, [self.safe_slice("safe-1")]).slice.slice_id)

        self.sup.ingest(self.risk("risk-occurrence-2", "occurrence-2", observed_at=3))
        gate2 = self.store.current_p0_approval(event.semantic_key)
        self.assertIsNotNone(gate2)
        self.assertNotEqual(gate1.occurrence_key, gate2.occurrence_key)
        self.assertGreater(gate2.approval_epoch, gate1.approval_epoch)

        stale = self.sup.reconcile(self.snapshot(observed_at=4, p0_dispositions=(old_unused_a,)))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(stale, [self.safe_slice()]).decision)
        attempts = self.store.p0_disposition_attempt_history(event.semantic_key)
        self.assertEqual("STALE_APPROVAL", attempts[-1][1])
        self.assertEqual("user:old-unused-A", attempts[-1][0])
        self.assertEqual(gate1.occurrence_key, attempts[-1][2])
        self.assertEqual(gate2.occurrence_key, attempts[-1][4])
        self.assertEqual((("DENIED", "user:decision-B"),), self.store.p0_disposition_history(event.semantic_key))

        resolved2 = self.sup.reconcile(self.snapshot(
            observed_at=5,
            p0_dispositions=(self.bound_disposition(event.semantic_key, "user:decision-C", gate2),),
        ))
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(event.semantic_key))
        self.assertEqual("safe-2", self.sup.choose(resolved2, [self.safe_slice("safe-2")]).slice.slice_id)
        self.assertEqual(
            (("DENIED", "user:decision-B"), ("DENIED", "user:decision-C")),
            self.store.p0_disposition_history(event.semantic_key),
        )

    def test_b23_multiple_genuine_occurrences_pending_coalesce_one_gate_and_advance_epoch(self) -> None:
        event1, inserted1 = self.sup.ingest(self.risk("risk-1", "occurrence-1", observed_at=1))
        self.assertTrue(inserted1)
        gate1 = self.store.current_p0_approval(event1.semantic_key)
        self.assertIsNotNone(gate1)
        stale_for_first = self.bound_disposition(event1.semantic_key, "user:first-issued", gate1)

        event2, inserted2 = self.sup.ingest(self.risk("risk-2", "occurrence-2", observed_at=2))
        self.assertFalse(inserted2)
        self.assertEqual(event1.semantic_key, event2.semantic_key)
        gate2 = self.store.current_p0_approval(event1.semantic_key)
        self.assertIsNotNone(gate2)
        self.assertEqual(2, gate2.approval_epoch)
        self.assertEqual(2, gate2.coalesced_occurrences)
        self.assertEqual(1, self.store.connection.execute("SELECT COUNT(*) FROM events WHERE semantic_key=?", (event1.semantic_key,)).fetchone()[0])

        retry, inserted_retry = self.sup.ingest(self.risk("risk-2-retry", "occurrence-2", observed_at=3))
        self.assertFalse(inserted_retry)
        self.assertEqual(event1.semantic_key, retry.semantic_key)
        self.assertEqual(gate2, self.store.current_p0_approval(event1.semantic_key))

        stale = self.sup.reconcile(self.snapshot(observed_at=4, p0_dispositions=(stale_for_first,)))
        self.assertEqual(Decision.USER_GATE, self.sup.choose(stale, [self.safe_slice()]).decision)
        self.assertEqual("STALE_APPROVAL", self.store.p0_disposition_attempt_history(event1.semantic_key)[-1][1])

        current = self.sup.reconcile(self.snapshot(
            observed_at=5,
            p0_dispositions=(self.bound_disposition(event1.semantic_key, "user:coalesced-current", gate2),),
        ))
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(event1.semantic_key))
        self.assertEqual("safe", self.sup.choose(current, [self.safe_slice()]).slice.slice_id)

    def test_b24_pre_b22_db_upgrade_restart_backfills_occurrence_and_old_retry_does_not_regate(self) -> None:
        self.store.close()
        db = Path(self.temp.name) / "pre_b22.sqlite"
        raw = sqlite3.connect(db)
        raw.execute(
            "CREATE TABLE events (semantic_key TEXT PRIMARY KEY, event_json TEXT NOT NULL, priority INTEGER NOT NULL, adjudication_generation INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'PENDING')"
        )
        old_event = runtime.NormalizedEvent.from_mapping(self.risk("legacy-risk", "legacy-occurrence", observed_at=1))
        raw.execute(
            "INSERT INTO events VALUES (?,?,?,?,?)",
            (old_event.semantic_key, runtime._event_to_json(old_event), int(Priority.P0_USER_OR_HIGH_RISK), 1, "P0_DISPOSITION_TRACE"),
        )
        raw.commit(); raw.close()

        upgraded = WorkingStateStore(db)
        upgraded.close()
        self.store = WorkingStateStore(db)
        self.sup = SyntheticSupervisor(REPO, self.store, budget_limit=10)
        self.assertEqual(("legacy-occurrence",), self.store.occurrence_idempotencies(old_event.semantic_key))
        retry, inserted = self.sup.ingest(self.risk("legacy-retry-envelope", "legacy-occurrence", observed_at=9))
        self.assertFalse(inserted)
        self.assertEqual(old_event.semantic_key, retry.semantic_key)
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(old_event.semantic_key))
        self.assertIsNone(self.store.current_p0_approval(old_event.semantic_key))
        trace_states = tuple(row[0] for row in self.store.connection.execute(
            "SELECT state FROM event_traces WHERE semantic_key=? ORDER BY observed_at,trace_id",
            (old_event.semantic_key,),
        ).fetchall())
        self.assertIn("DUPLICATE_REDELIVERY", trace_states)


if __name__ == "__main__":
    unittest.main(verbosity=2)
