from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
import iagl_synthetic_supervisor as runtime  # noqa: E402
from iagl_synthetic_supervisor import (  # noqa: E402
    Decision, GovernanceMode, ImprovementSlice, P0Disposition, Priority,
    ReconciliationSnapshot, SyntheticSupervisor, WorkingStateStore,
)

REPO = "vxz2datoubo/second-brain-coordination"
PATHS = ("synthetic/allowed.py",)


class B25ReachableLegacySnapshotMigration(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "pre_b23_reachable.sqlite"

    def tearDown(self) -> None:
        store = getattr(self, "store", None)
        if store is not None:
            store.close()
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

    def risk(self, event_id: str, idempotency_key: str, observed_at: int) -> dict[str, object]:
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

    @staticmethod
    def legacy_snapshot_json(snapshot: ReconciliationSnapshot, disposition: dict[str, object]) -> str:
        value = asdict(snapshot)
        value["governance_mode"] = snapshot.governance_mode.value
        for name in (
            "allowed_write_paths", "allowed_tools", "allowed_data_classes",
            "allowed_risk_classes", "allowed_writeback_plans",
            "active_p2_event_keys", "active_p2_classes",
        ):
            value[name] = list(value[name])
        value["p0_dispositions"] = [disposition]
        value["p2_resolutions"] = []
        return json.dumps(value, sort_keys=True)

    @staticmethod
    def legacy_snapshot_identity(snapshot: ReconciliationSnapshot, disposition: dict[str, object]) -> str:
        return runtime.digest({
            "repository": snapshot.repository,
            "head": snapshot.exact_head,
            "route": snapshot.route_id,
            "governance": snapshot.governance_mode.value,
            "allowed": snapshot.allowed_write_paths,
            "p0": snapshot.pending_p0,
            "domain": snapshot.domain_revision,
            "queue_complete": snapshot.eligible_work_queue_complete,
            "allowed_tools": snapshot.allowed_tools,
            "allowed_data_classes": snapshot.allowed_data_classes,
            "allowed_risk_classes": snapshot.allowed_risk_classes,
            "allowed_writeback_plans": snapshot.allowed_writeback_plans,
            "active_p2_event_keys": snapshot.active_p2_event_keys,
            "active_p2_classes": snapshot.active_p2_classes,
            "p0_dispositions": (disposition,),
            "p2_observation_status": snapshot.p2_observation_status,
            "p2_observation_ref": snapshot.p2_observation_ref,
            "p2_resolutions": (),
        })

    def seed_reachable_pre_b23_state(self):
        old_event = runtime.NormalizedEvent.from_mapping(
            self.risk("legacy-risk", "legacy-occurrence-1", observed_at=1)
        )
        legacy_disposition = {
            "event_key": old_event.semantic_key,
            "decision": "DENIED",
            "decision_ref": "legacy:user:decision-1",
            "authority_source": "USER_DECISION",
        }
        legacy_snapshot = self.snapshot(observed_at=2)
        legacy_identity = self.legacy_snapshot_identity(legacy_snapshot, legacy_disposition)
        occurrence_key = runtime.digest({
            "semantic_key": old_event.semantic_key,
            "idempotency_key": "legacy-occurrence-1",
        })
        history_id = runtime.digest({
            "event_key": old_event.semantic_key,
            "decision_ref": legacy_disposition["decision_ref"],
            "identity": legacy_identity,
            "generation": 2,
        })
        trace_id = runtime.digest({
            "event_id": old_event.event_id,
            "source": old_event.source,
            "class": old_event.event_class,
            "observed_at": old_event.observed_at,
            "idempotency": old_event.supplied_idempotency_key,
        })

        raw = sqlite3.connect(self.db)
        raw.executescript("""
        CREATE TABLE reconciliation (
            slot INTEGER PRIMARY KEY CHECK(slot=1),
            identity TEXT NOT NULL,
            generation INTEGER NOT NULL,
            snapshot TEXT NOT NULL
        );
        CREATE TABLE events (
            semantic_key TEXT PRIMARY KEY,
            event_json TEXT NOT NULL,
            priority INTEGER NOT NULL,
            adjudication_generation INTEGER NOT NULL DEFAULT 0,
            state TEXT NOT NULL DEFAULT 'PENDING'
        );
        CREATE TABLE event_traces (
            trace_id TEXT PRIMARY KEY,
            semantic_key TEXT NOT NULL,
            source TEXT NOT NULL,
            event_class TEXT NOT NULL,
            target_identity TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            observed_at INTEGER NOT NULL,
            state TEXT NOT NULL
        );
        CREATE TABLE event_occurrences (
            occurrence_key TEXT PRIMARY KEY,
            semantic_key TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            event_id TEXT NOT NULL,
            source TEXT NOT NULL,
            first_observed_at INTEGER NOT NULL,
            UNIQUE(semantic_key,idempotency_key)
        );
        CREATE TABLE p0_disposition_history (
            history_id TEXT PRIMARY KEY,
            event_key TEXT NOT NULL,
            decision TEXT NOT NULL,
            decision_ref TEXT NOT NULL,
            reconciliation_identity TEXT NOT NULL,
            reconciliation_generation INTEGER NOT NULL
        );
        """)
        raw.execute(
            "INSERT INTO reconciliation VALUES (1,?,?,?)",
            (legacy_identity, 2, self.legacy_snapshot_json(legacy_snapshot, legacy_disposition)),
        )
        raw.execute(
            "INSERT INTO events VALUES (?,?,?,?,?)",
            (
                old_event.semantic_key,
                runtime._event_to_json(old_event),
                int(Priority.P0_USER_OR_HIGH_RISK),
                2,
                "P0_DISPOSITION_TRACE",
            ),
        )
        raw.execute(
            "INSERT INTO event_traces VALUES (?,?,?,?,?,?,?,?)",
            (
                trace_id, old_event.semantic_key, old_event.source, old_event.event_class,
                old_event.target_identity, old_event.payload_digest, old_event.observed_at, "OBSERVED",
            ),
        )
        raw.execute(
            "INSERT INTO event_occurrences VALUES (?,?,?,?,?,?)",
            (
                occurrence_key, old_event.semantic_key, old_event.supplied_idempotency_key,
                old_event.event_id, old_event.source, old_event.observed_at,
            ),
        )
        raw.execute(
            "INSERT INTO p0_disposition_history VALUES (?,?,?,?,?,?)",
            (
                history_id, old_event.semantic_key, "DENIED",
                "legacy:user:decision-1", legacy_identity, 2,
            ),
        )
        raw.commit()
        raw.close()
        return old_event

    def test_b25_reachable_pre_b23_snapshot_drops_unbound_approval_fail_closed_then_current_binding_resolves(self) -> None:
        old_event = self.seed_reachable_pre_b23_state()
        self.store = WorkingStateStore(self.db)
        self.sup = SyntheticSupervisor(REPO, self.store, budget_limit=10)

        current = self.store.current_snapshot()
        self.assertIsNotNone(current)
        self.assertEqual((), current[1].p0_dispositions)
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(old_event.semantic_key))
        self.assertEqual(
            (("DENIED", "legacy:user:decision-1"),),
            self.store.p0_disposition_history(old_event.semantic_key),
        )
        audit = self.store.connection.execute(
            "SELECT decision_ref,outcome FROM reconciliation_migration_audit WHERE event_key=?",
            (old_event.semantic_key,),
        ).fetchall()
        self.assertEqual(
            [("legacy:user:decision-1", "LEGACY_UNBOUND_P0_DISPOSITION_DROPPED_FAIL_CLOSED")],
            audit,
        )

        recurrent, inserted = self.sup.ingest(
            self.risk("current-risk-occurrence-2", "current-occurrence-2", observed_at=3)
        )
        self.assertFalse(inserted)
        self.assertEqual(old_event.semantic_key, recurrent.semantic_key)
        binding = self.store.current_p0_approval(old_event.semantic_key)
        self.assertIsNotNone(binding)
        self.assertEqual(2, binding.approval_epoch)
        self.assertEqual("PENDING", self.store.event_state(old_event.semantic_key))

        fresh = self.sup.reconcile(self.snapshot(observed_at=4))
        self.assertEqual(
            Decision.USER_GATE,
            self.sup.choose(fresh, [self.safe_slice()]).decision,
        )
        self.assertEqual(
            (("DENIED", "legacy:user:decision-1"),),
            self.store.p0_disposition_history(old_event.semantic_key),
        )
        self.assertEqual(
            1,
            self.store.connection.execute(
                "SELECT COUNT(*) FROM reconciliation_migration_audit WHERE event_key=?",
                (old_event.semantic_key,),
            ).fetchone()[0],
        )

        current_disposition = P0Disposition(
            old_event.semantic_key,
            "DENIED",
            "current:user:decision-2",
            binding.occurrence_key,
            binding.approval_epoch,
        )
        resolved = self.sup.reconcile(self.snapshot(
            observed_at=5,
            p0_dispositions=(current_disposition,),
        ))
        self.assertEqual("P0_DISPOSITION_TRACE", self.store.event_state(old_event.semantic_key))
        self.assertEqual(
            (
                ("DENIED", "legacy:user:decision-1"),
                ("DENIED", "current:user:decision-2"),
            ),
            self.store.p0_disposition_history(old_event.semantic_key),
        )
        self.assertEqual("safe", self.sup.choose(resolved, [self.safe_slice()]).slice.slice_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
