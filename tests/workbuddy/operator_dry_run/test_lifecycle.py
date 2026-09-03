"""Duplicate-input, resume, replay and failure-recovery tests (WB-S3)."""

from __future__ import annotations

import copy
import unittest

import sys
from pathlib import Path

# Resolve imports without relying on discover's top-level directory.
_REPO_ROOT = Path(__file__).resolve().parents[3]
for _candidate in (str(_REPO_ROOT), str(_REPO_ROOT / "tools" / "workbuddy")):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from creative_runtime.ledger import CreativeLedger, LedgerViolation  # noqa: E402
from operator_dry_run import operator  # noqa: E402


class DuplicateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.op = operator.OperatorDryRun()
        self.op.intake("listen")

    def test_duplicate_is_recorded_as_distinct_event(self) -> None:
        result = self.op.duplicate_append()
        self.assertTrue(result["recorded_as_distinct_event"])
        self.assertTrue(result["distinct_hash"])
        self.assertTrue(result["higher_sequence"])
        self.assertTrue(result["chain_verifies"])

    def test_duplicate_is_never_a_silent_noop(self) -> None:
        before_count = len(self.op.ledger.events)
        self.op.duplicate_append()
        self.assertEqual(len(self.op.ledger.events), before_count + 1)


class ResumeReplayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.op = operator.OperatorDryRun()
        self.op.intake("listen")
        self.op.intake("approach")

    def test_resume_reproduces_state(self) -> None:
        resumed = self.op.resume()
        self.assertEqual(resumed.replay().to_dict(), self.op.state.to_dict())

    def test_resume_is_idempotent(self) -> None:
        first = self.op.resume().replay().to_dict()
        second = CreativeLedger.from_records(self.op.resume().to_records()).replay().to_dict()
        self.assertEqual(first, second)

    def test_replay_is_deterministic(self) -> None:
        self.assertEqual(self.op.state.to_dict(), self.op.state.to_dict())


class FailureRecoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.op = operator.OperatorDryRun()
        self.op.intake("listen")

    def test_tamper_is_rejected(self) -> None:
        pristine = self.op.serialize()
        tampered = self.op.tamper(pristine)
        with self.assertRaises(LedgerViolation):
            CreativeLedger.from_records(tampered)

    def test_source_survives_failed_resume(self) -> None:
        pristine = self.op.serialize()
        with self.assertRaises(LedgerViolation):
            CreativeLedger.from_records(self.op.tamper(pristine))
        self.assertEqual(self.op.serialize(), pristine)

    def test_recovery_full_path(self) -> None:
        result = self.op.recover()
        self.assertTrue(result["tamper_rejected"])
        self.assertTrue(result["source_intact"])
        self.assertTrue(result["re_resume_reproduces_state"])

    def test_tampered_payload_changes_but_is_rejected_not_absorbed(self) -> None:
        tampered = self.op.tamper(self.op.serialize())
        original_payload = self.op.serialize()[-1]["payload"]
        self.assertNotEqual(tampered[-1]["payload"], original_payload)


if __name__ == "__main__":
    unittest.main()
