"""R141 B16/B17 adversarial recurrence and starvation/fairness regressions."""
from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
from iagl_synthetic_supervisor import (  # noqa: E402
    Decision, GovernanceMode, ImprovementSlice, P2Resolution, Priority,
    ReconciliationSnapshot, ReviewWorkIdentity, SyntheticSupervisor, WorkingStateStore,
)

REPO = "vxz2datoubo/second-brain-coordination"
PATHS = ("synthetic/allowed.py",)


class B16B17Regressions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = WorkingStateStore(Path(self.temp.name) / 'state.sqlite')
        self.sup = SyntheticSupervisor(REPO, self.store, budget_limit=10)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def snapshot(self, **overrides: object) -> ReconciliationSnapshot:
        data: dict[str, object] = {'repository': REPO, 'exact_head': 'A', 'route_id': 'R141', 'governance_mode': GovernanceMode.AUTONOMOUS, 'allowed_write_paths': PATHS, 'observed_at': 1, 'domain_revision': 'domain-1'}
        data.update(overrides)
        return ReconciliationSnapshot(**data)

    def slice(self, ident: str='same', **overrides: object) -> ImprovementSlice:
        data: dict[str, object] = {'slice_id': ident, 'priority': Priority.P3_BOUNDED_IMPROVEMENT, 'changed_paths': PATHS, 'source_signal_refs': ('signal',), 'problem_signature': 'signature', 'goal': 'bounded goal', 'materiality': 'MATERIAL', 'evidence_target': 'evidence', 'allowed_tools': ('stdlib-only',), 'allowed_data_classes': ('PUBLIC_SAFE_SYNTHETIC',), 'risk_class': 'P3_SYNTHETIC', 'time_budget_minutes': 1, 'compute_budget': 1, 'expected_artifact': 'artifact', 'falsifier': 'falsifier', 'stop_conditions': ('stop',), 'writeback_plan': 'NO_CANONICAL_WRITE', 'owner': 'GPT_ENGINEERING_WORKER'}
        data.update(overrides)
        return ImprovementSlice(**data)

    def raw_event(self, event_class: str, payload: object, key: str='event', priority: Priority=Priority.P4_RESEARCH, target: str='A', source: str='synthetic') -> dict[str, object]:
        return {'event_id': key, 'event_class': event_class, 'source': source, 'repository': REPO, 'observed_at': 1, 'target_ref': 'refs/heads/main', 'target_identity': target, 'payload': payload, 'idempotency_key': key, 'priority_hint': int(priority)}

    def test_b16_p2_resolved_blocker_reactivates_on_authoritative_recurrence(self) -> None:
        event, _ = self.sup.ingest(self.raw_event('ACTIVE_BLOCKER', {'blocker': 'recurring'}, key='p2-recurrence'))
        active = self.sup.reconcile(self.snapshot(active_p2_event_keys=(event.semantic_key,), p2_observation_status='AUTHORITATIVE_COMPLETE', p2_observation_ref='provider:active:1'))
        self.assertEqual(Decision.BLOCKED, self.sup.choose(active, [self.slice('safe')]).decision)
        resolved = self.sup.reconcile(self.snapshot(observed_at=2, p2_observation_status='AUTHORITATIVE_COMPLETE', p2_observation_ref='provider:complete:resolved', p2_resolutions=(P2Resolution(event.semantic_key, 'resolution:first-closure'),)))
        self.assertEqual('RESOLVED_TRACE', self.store.event_state(event.semantic_key))
        self.assertEqual('safe', self.sup.choose(resolved, [self.slice('safe')]).slice.slice_id)
        prior_resolution = self.store.connection.execute('SELECT resolution_ref,observation_ref FROM p2_resolution_history WHERE event_key=?', (event.semantic_key,)).fetchone()
        self.assertEqual(('resolution:first-closure', 'provider:complete:resolved'), prior_resolution)
        duplicate, inserted = self.sup.ingest(self.raw_event('ACTIVE_BLOCKER', {'blocker': 'recurring'}, key='p2-recurrence-duplicate', source='watchdog'))
        self.assertEqual(event.semantic_key, duplicate.semantic_key)
        self.assertFalse(inserted)
        recurrent = self.sup.reconcile(self.snapshot(observed_at=3, active_p2_event_keys=(event.semantic_key,), p2_observation_status='AUTHORITATIVE_COMPLETE', p2_observation_ref='provider:active:again'))
        self.assertEqual('PENDING', self.store.event_state(event.semantic_key))
        self.assertEqual(Priority.P2_BLOCKER_OR_DRIFT, self.store.event_priority(event.semantic_key))
        self.assertEqual(Decision.BLOCKED, self.sup.choose(recurrent, [self.slice('safe-again')]).decision)
        self.assertEqual(('RESOLVED', 'REACTIVATED'), self.store.p2_lifecycle(event.semantic_key))
        self.assertEqual(('resolution:first-closure', 'provider:complete:resolved'), self.store.connection.execute('SELECT resolution_ref,observation_ref FROM p2_resolution_history WHERE event_key=?', (event.semantic_key,)).fetchone())
        self.assertIn('watchdog', self.store.trace_sources(event.semantic_key))

    def test_b17_aged_items_are_visible_with_deterministic_reason(self) -> None:
        p3_a = self.slice('a-p3')
        p3_z = self.slice('z-p3')
        first = self.sup.reconcile(self.snapshot(observed_at=1))
        self.assertEqual('a-p3', self.sup.choose(first, [p3_a, p3_z]).slice.slice_id)
        second = self.sup.reconcile(self.snapshot(observed_at=2))
        self.assertEqual('a-p3', self.sup.choose(second, [p3_a, p3_z]).slice.slice_id)
        third = self.sup.reconcile(self.snapshot(observed_at=3))
        visible = {item.slice_id: item for item in self.sup.starvation_visibility(third, [p3_a, p3_z])}
        self.assertIn('z-p3', visible)
        self.assertTrue(visible['z-p3'].aged)
        self.assertEqual(2, visible['z-p3'].counter)
        self.assertEqual(Priority.P3_BOUNDED_IMPROVEMENT, visible['z-p3'].effective_priority)
        self.assertEqual('AGING+MATERIALITY+FRESH_RECONCILIATION:P3_WITHIN_CLASS', visible['z-p3'].reason)
        self.assertEqual('z-p3', self.sup.choose(third, [p3_a, p3_z]).slice.slice_id)

    def test_b17_aged_material_p4_is_boundedly_promoted_only_to_p3(self) -> None:
        p3 = self.slice('young-p3')
        p4 = self.slice('aged-p4', priority=Priority.P4_RESEARCH, risk_class='P4_SYNTHETIC')
        first = self.sup.reconcile(self.snapshot(observed_at=1))
        self.assertEqual('young-p3', self.sup.choose(first, [p3, p4]).slice.slice_id)
        second = self.sup.reconcile(self.snapshot(observed_at=2))
        self.assertEqual('young-p3', self.sup.choose(second, [p3, p4]).slice.slice_id)
        third = self.sup.reconcile(self.snapshot(observed_at=3))
        status = {item.slice_id: item for item in self.sup.starvation_visibility(third, [p3, p4])}['aged-p4']
        self.assertTrue(status.promoted)
        self.assertEqual(Priority.P4_RESEARCH, status.original_priority)
        self.assertEqual(Priority.P3_BOUNDED_IMPROVEMENT, status.effective_priority)
        self.assertEqual('AGING+MATERIALITY+FRESH_RECONCILIATION:P4_TO_P3', status.reason)
        self.assertEqual('aged-p4', self.sup.choose(third, [p3, p4]).slice.slice_id)

    def test_b17_promotion_requires_materiality_and_fresh_reconciliation(self) -> None:
        p3 = self.slice('young')
        p4_low = self.slice('old', priority=Priority.P4_RESEARCH, risk_class='P4_SYNTHETIC', materiality='LOW')
        for generation in (1, 2):
            grant = self.sup.reconcile(self.snapshot(observed_at=generation))
            self.assertEqual('young', self.sup.choose(grant, [p3, p4_low]).slice.slice_id)
        third = self.sup.reconcile(self.snapshot(observed_at=3))
        low_status = {item.slice_id: item for item in self.sup.starvation_visibility(third, [p3, p4_low])}['old']
        self.assertTrue(low_status.aged)
        self.assertFalse(low_status.promoted)
        self.assertEqual('AGING_PRESENT:MATERIALITY_REQUIRED', low_status.reason)
        self.assertEqual('young', self.sup.choose(third, [p3, p4_low]).slice.slice_id)
        p4_material = replace(p4_low, materiality='MATERIAL')
        same_generation = {item.slice_id: item for item in self.sup.starvation_visibility(third, [p3, p4_material])}['old']
        self.assertFalse(same_generation.fresh_reconciliation)
        self.assertFalse(same_generation.promoted)
        self.assertEqual('AGING_PRESENT:FRESH_RECONCILIATION_REQUIRED', same_generation.reason)
        fourth = self.sup.reconcile(self.snapshot(observed_at=4))
        fresh_status = {item.slice_id: item for item in self.sup.starvation_visibility(fourth, [p3, p4_material])}['old']
        self.assertTrue(fresh_status.fresh_reconciliation)
        self.assertTrue(fresh_status.promoted)
        self.assertEqual(Priority.P3_BOUNDED_IMPROVEMENT, fresh_status.effective_priority)

    def test_b17_aging_never_overrides_p0_user_gate(self) -> None:
        p3 = self.slice('young')
        p4 = self.slice('old-p4', priority=Priority.P4_RESEARCH, risk_class='P4_SYNTHETIC')
        for generation in (1, 2):
            grant = self.sup.reconcile(self.snapshot(observed_at=generation))
            self.sup.choose(grant, [p3, p4])
        risk, _ = self.sup.ingest(self.raw_event('SIGNAL_MATERIALITY_CHANGED', {'finding': 'secret', 'permission': 'github_permission'}, key='p0-fairness'))
        gated = self.sup.reconcile(self.snapshot(observed_at=3))
        result = self.sup.choose(gated, [p3, p4])
        self.assertEqual(Decision.USER_GATE, result.decision)
        self.assertEqual(Priority.P0_USER_OR_HIGH_RISK, self.store.event_priority(risk.semantic_key))

    def test_b17_aging_never_overrides_p1_exact_head_review(self) -> None:
        p3 = self.slice('young')
        p4 = self.slice('old-p4', priority=Priority.P4_RESEARCH, risk_class='P4_SYNTHETIC')
        for generation in (1, 2):
            grant = self.sup.reconcile(self.snapshot(observed_at=generation))
            self.sup.choose(grant, [p3, p4])
        self.sup.ingest(self.raw_event('PR_HEAD_CHANGED', {'head': 'A'}, key='p1-fairness', priority=Priority.P1_EXACT_HEAD_REVIEW, target='A', source='webhook'))
        review_grant = self.sup.reconcile(self.snapshot(observed_at=3))
        work = self.sup.choose(review_grant, [p3, p4])
        self.assertIsInstance(work, ReviewWorkIdentity)
        self.assertEqual('A', work.target_head)

    def test_b17_aging_never_weakens_p2_blocker_safety(self) -> None:
        p3 = self.slice('young')
        p4 = self.slice('old-p4', priority=Priority.P4_RESEARCH, risk_class='P4_SYNTHETIC')
        for generation in (1, 2):
            grant = self.sup.reconcile(self.snapshot(observed_at=generation))
            self.sup.choose(grant, [p3, p4])
        blocker, _ = self.sup.ingest(self.raw_event('ROUTE_DRIFT', {'route': 'drift'}, key='p2-fairness'))
        blocked_grant = self.sup.reconcile(self.snapshot(observed_at=3, active_p2_event_keys=(blocker.semantic_key,), p2_observation_status='AUTHORITATIVE_COMPLETE', p2_observation_ref='provider:p2-active'))
        status = {item.slice_id: item for item in self.sup.starvation_visibility(blocked_grant, [p3, p4])}['old-p4']
        self.assertTrue(status.promoted)
        self.assertEqual(Priority.P3_BOUNDED_IMPROVEMENT, status.effective_priority)
        result = self.sup.choose(blocked_grant, [p3, p4])
        self.assertEqual(Decision.BLOCKED, result.decision)
        self.assertEqual(Priority.P2_BLOCKER_OR_DRIFT, self.store.event_priority(blocker.semantic_key))


if __name__ == "__main__":
    unittest.main(verbosity=2)
