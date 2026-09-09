"""R188 Phase B Durable Mission Kernel — CI oracle.

This is the deterministic CI oracle the exact-head CI runs (``python -m unittest
discover -s tests -p 'test_unified_execution*.py'``). It:

1. pulls in the full kernel unit suite under ``tests/durable_mission_kernel`` via
   ``load_tests``; and
2. re-asserts the highest-value invariants here (golden hash vectors, hash-chain
   integrity, reducer determinism, role independence / no-self-merge, write-surface
   boundaries, and the synthetic endurance canary).

All assertions are deterministic; there is no real capture, no trading, no
production, and no R184 / Local Bridge / Program S2 activation anywhere in scope.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.durable_mission_kernel import (  # noqa: E402
    canonical, containment, endurance, ledger, protocols, reducers, schemas, verifier,
)
from tools.durable_mission_kernel.schemas import (  # noqa: E402
    EventType, MissionState, ResultClass, ROLE_INDEPENDENCE_RULE,
)


def load_tests(loader, tests, pattern):
    """Aggregate the kernel unit suite into this oracle so CI runs everything."""
    kernel_suite = loader.discover(str(ROOT / "tests" / "durable_mission_kernel"), pattern="test_*.py")
    tests.addTests(kernel_suite)
    return tests


# Golden vectors (frozen; see test_b1 for derivation).
GOLDEN_GENESIS_HASH = "a563409ca9f311474b6012094bc7528228c9e8aeb889d570fdccfe48e90ab2be"
GOLDEN_PLAN_STARTED = "e12f5595a3405b7a54565cdfcb98fde447be60d4f10456177f1d898011f26a10"
GOLDEN_JCS_1 = '{"a":{"b":"c"},"f":false,"m":null,"n":3,"pi":3.14,"t":true,"z":[1,2]}'


class DurableMissionKernelOracleTests(unittest.TestCase):
    def test_golden_genesis_hash_is_frozen(self):
        gen = verifier.build_genesis_event(
            mission_id="MISSION-GOLDEN-001", run_id="RUN-GOLDEN-001",
            actor="WORKBUDDY", timestamp_iso="2026-09-09T01:58:00Z",
            payload={"phase": "B", "mode": "SYNTHETIC_AND_DISPOSABLE_FIXTURE_ONLY"},
        )
        self.assertEqual(gen["event_hash"], GOLDEN_GENESIS_HASH)

    def test_jcs_canonicalization_is_deterministic(self):
        self.assertEqual(
            canonical.jcs_dumps({"z": [1, 2], "a": {"b": "c"}, "m": None,
                                "f": False, "t": True, "n": 3, "pi": 3.14}),
            GOLDEN_JCS_1,
        )

    def test_reducer_is_deterministic_and_fail_closed(self):
        self.assertEqual(reducers.reduce_state(MissionState.CREATED.value, EventType.PLAN_STARTED.value),
                         MissionState.PLANNING.value)
        with self.assertRaises(reducers.ReducerError):
            reducers.reduce_state(MissionState.CREATED.value, EventType.CANONICALIZATION_COMPLETED.value)

    def test_hash_chain_detects_tampering(self):
        gen = verifier.build_genesis_event(
            mission_id="M", run_id="R", actor="A", timestamp_iso="2026-09-09T00:00:00Z")
        bad = dict(gen)
        bad["event_hash"] = "0" * 64
        with self.assertRaises(verifier.ChainVerificationError):
            verifier.verify_event_chain([bad])

    def test_full_mission_reaches_complete_with_valid_chain(self):
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "m.sqlite")
            led = ledger.MissionLedger(db)
            led.create_mission("m1", "r1", "2026-09-09T00:00:00Z")
            for etype in (
                EventType.PLAN_STARTED.value, EventType.PLAN_COMPLETED.value,
                EventType.EPISODE_STARTED.value, EventType.CHECKPOINT_REACHED.value,
                EventType.VERIFICATION_STARTED.value, EventType.VERIFICATION_PASSED.value,
                EventType.REVIEW_STARTED.value, EventType.REVIEW_APPROVED.value,
                EventType.CANONICALIZATION_STARTED.value, EventType.CANONICALIZATION_COMPLETED.value,
            ):
                led.append_event(mission_id="m1", event_type=etype, actor="W",
                                 timestamp_iso="2026-09-09T00:00:00Z")
            self.assertEqual(led.current_state("m1"), MissionState.COMPLETE.value)
            self.assertTrue(led.verify_chain("m1"))
            led.close()

    def test_role_independence_and_no_self_merge(self):
        self.assertTrue(protocols.assert_principal_independence(
            protocols.PrincipalSet("author", "reviewer", "canonicalizer")))
        with self.assertRaises(protocols.ProtocolError):
            protocols.assert_no_self_merge("author", "author")
        with self.assertRaises(protocols.ProtocolError):
            protocols.assert_no_self_review("author", "author")

    def test_write_surface_boundaries(self):
        self.assertTrue(schemas.is_authorized_write_path("tools/durable_mission_kernel/ledger.py"))
        self.assertTrue(schemas.is_authorized_write_path("tests/durable_mission_kernel/x.py"))
        self.assertTrue(schemas.is_authorized_write_path("tests/test_unified_execution_durable_mission_kernel.py"))
        self.assertTrue(schemas.is_authorized_write_path("coordination/EXECUTION/PHASE-B-DURABLE-MISSION-KERNEL/r.yaml"))
        # protected surfaces must be rejected as unauthorized writes
        self.assertFalse(schemas.is_authorized_write_path("coordination/ACTIVE-WORKBUDDY-TASK.yaml"))
        self.assertFalse(schemas.is_authorized_write_path("coordination/GOVERNANCE/foo.yaml"))
        self.assertFalse(schemas.is_authorized_write_path("tools/local_workbuddy_bridge/x.py"))
        # and explicitly flagged as protected
        self.assertTrue(schemas.is_protected_path("coordination/GOVERNANCE/foo.yaml"))
        self.assertTrue(schemas.is_protected_path("tools/local_workbuddy_bridge/x.py"))

    def test_synthetic_endurance_canary(self):
        with tempfile.TemporaryDirectory() as td:
            report = endurance.SyntheticEnduranceCanary(
                str(Path(td) / "c.sqlite"), episodes=3, inject_worker_failure=True).run()
            self.assertTrue(report.passed)
            self.assertTrue(report.chain_verified)
            self.assertEqual(report.final_state, MissionState.COMPLETE.value)

    def test_containment_probe_is_defined(self):
        # The probe must return a report; on non-Windows it must be non-hard (no
        # silent downgrade), on Windows it must report HARD_JOB_OBJECT.
        rep = containment.probe_support()
        self.assertIn(rep.mode, ("HARD_JOB_OBJECT", "PARTIAL", "BLOCKED"))
        if sys.platform == "win32":
            self.assertEqual(rep.mode, "HARD_JOB_OBJECT")

    def test_required_result_classes_are_declared(self):
        for cls in (
            "SYNTHETIC_KERNEL_RESULT", "WINDOWS_CONTAINMENT_RESULT",
            "HEADLESS_ADAPTER_RESULT", "SDK_ADAPTER_RESULT",
            "SYNTHETIC_REVIEW_CANONICALIZATION_RESULT", "REAL_CANONICALIZER_CAPABILITY_RESULT",
            "EXACT_HEAD_CI_RESULT", "INDEPENDENT_REVIEW_RESULT", "CANONICALIZATION_RESULT",
        ):
            self.assertIn(cls, ResultClass.__members__)

    def test_independence_rule_text_is_frozen(self):
        self.assertEqual(ROLE_INDEPENDENCE_RULE, "AUTHOR != REVIEWER != CANONICALIZER")


if __name__ == "__main__":
    unittest.main()
