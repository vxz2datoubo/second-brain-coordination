"""B3 tests — effect ledger (outbox/idempotency/budgets) + runtime lease fencing."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.durable_mission_kernel import effects, lease  # noqa: E402
from tools.durable_mission_kernel.schemas import EffectStatus, LeaseStatus  # noqa: E402


class B3EffectTests(unittest.TestCase):
    def test_idempotency_same_key_returns_same_effect(self):
        el = effects.EffectLedger()
        a = el.register("e1", "m1", "key-1")
        b = el.register("e2", "m1", "key-1")  # same key -> same effect
        self.assertIs(a, b)
        self.assertEqual(a.effect_id, "e1")

    def test_outcome_unknown_never_not_executed(self):
        el = effects.EffectLedger()
        rec = el.register("e1", "m1", "key-1")
        el.mark_outcome_unknown("e1", "ACK_LOSS")
        self.assertEqual(rec.status, EffectStatus.OUTCOME_UNKNOWN.value)
        self.assertNotEqual(rec.status, "NOT_EXECUTED")

    def test_executed_transition(self):
        el = effects.EffectLedger()
        rec = el.register("e1", "m1", "key-1")
        el.mark_executed("e1", {"ok": True})
        self.assertEqual(rec.status, EffectStatus.EXECUTED.value)

    def test_budget_max_effects_enforced(self):
        el = effects.EffectLedger(effects.BudgetEnvelope(max_effects=2))
        el.register("e1", "m1", "k1")
        el.register("e2", "m1", "k2")
        with self.assertRaises(effects.EffectsError):
            el.register("e3", "m1", "k3")

    def test_budget_wall_time_enforced(self):
        el = effects.EffectLedger(effects.BudgetEnvelope(max_wall_time_ms=1000))
        with self.assertRaises(effects.EffectsError):
            el.check_budget(2000, 0)

    def test_forbidden_action_rejected(self):
        el = effects.EffectLedger(effects.BudgetEnvelope(forbidden_actions=("TRADE", "FUNDS")))
        with self.assertRaises(effects.EffectsError):
            el.forbid_action("TRADE")

    def test_path_allowlist(self):
        el = effects.EffectLedger(effects.BudgetEnvelope(allowed_paths=("tools/durable_mission_kernel/**",)))
        self.assertTrue(el.is_path_allowed("tools/durable_mission_kernel/ledger.py"))
        self.assertFalse(el.is_path_allowed("coordination/GOVERNANCE/x.yaml"))


class B3LeaseTests(unittest.TestCase):
    def test_acquire_renew_release(self):
        lm = lease.LeaseManager()
        l = lm.acquire("l1", "m1", "exec-A", "domain-1")
        self.assertEqual(l.status, LeaseStatus.ACTIVE.value)
        lm.renew("l1")
        self.assertEqual(l.status, LeaseStatus.ACTIVE.value)
        lm.release("l1")
        self.assertEqual(l.status, LeaseStatus.RELEASED.value)

    def test_same_domain_second_writer_forbidden(self):
        lm = lease.LeaseManager()
        lm.acquire("l1", "m1", "exec-A", "domain-1")
        with self.assertRaises(lease.LeaseError):
            lm.acquire("l2", "m1", "exec-B", "domain-1")

    def test_stale_lease_allows_replacement(self):
        lm = lease.LeaseManager(ttl_ms=10)
        l1 = lm.acquire("l1", "m1", "exec-A", "domain-1")
        # force expiry by re-acquiring after TTL using a fake clock is complex;
        # simulate by directly aging the lease.
        l1.expiry_ts = 0
        l2 = lm.acquire("l2", "m1", "exec-B", "domain-1")
        self.assertEqual(l2.executor_id, "exec-B")
        self.assertEqual(l1.status, LeaseStatus.FENCED.value)

    def test_fenced_lease_cannot_emit_effects(self):
        lm = lease.LeaseManager()
        l = lm.acquire("l1", "m1", "exec-A", "domain-1")
        lm.release("l1")
        with self.assertRaises(lease.LeaseError):
            lm.assert_can_emit_effects("l1")

    def test_stale_leases_detected(self):
        lm = lease.LeaseManager(ttl_ms=10)
        l = lm.acquire("l1", "m1", "exec-A", "domain-1")
        l.expiry_ts = 0
        self.assertIn(l, lm.stale_leases())


if __name__ == "__main__":
    unittest.main()
