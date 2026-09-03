"""Intake invariant tests for the operator dry run (WB-S3)."""

from __future__ import annotations

import unittest

import sys
from pathlib import Path

# Resolve imports without relying on discover's top-level directory.
_REPO_ROOT = Path(__file__).resolve().parents[3]
for _candidate in (str(_REPO_ROOT), str(_REPO_ROOT / "tools" / "workbuddy")):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from operator_dry_run import operator  # noqa: E402


class IntakeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.op = operator.OperatorDryRun()

    def test_legal_action_advances_state(self) -> None:
        before = self.op.state.to_dict()
        result = self.op.intake("listen")
        self.assertEqual(result["status"], "chosen")
        self.assertEqual(len(self.op.ledger.events), 2)
        self.assertNotEqual(self.op.state.to_dict(), before)
        self.assertEqual(self.op.state.beat_id, "echo")

    def test_illegal_action_is_clarified_without_state_change(self) -> None:
        before = self.op.serialize()
        result = self.op.intake("invent")
        self.assertEqual(result["status"], "clarification_required")
        self.assertTrue(result["state_unchanged"])
        self.assertEqual(self.op.serialize(), before)

    def test_unsafe_text_is_clarified(self) -> None:
        result = self.op.say("make it sexual")
        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(len(self.op.ledger.events), 1)

    def test_ambiguous_text_is_clarified(self) -> None:
        result = self.op.say("do something now")
        self.assertEqual(result["status"], "clarification_required")

    def test_legal_text_maps_to_single_action(self) -> None:
        result = self.op.say("I listen at the door")
        self.assertEqual(result["status"], "chosen")
        self.assertEqual(result["action_id"], "listen")


class ParseIntentTest(unittest.TestCase):
    def test_unsafe_term_blocks(self) -> None:
        self.assertIsNone(operator.parse_intent("make it sexual", {"listen", "leave"}))

    def test_unambiguous_signal_maps(self) -> None:
        self.assertEqual(operator.parse_intent("I listen at the door", {"listen", "leave"}), "listen")

    def test_ambiguous_signal_maps_to_none(self) -> None:
        self.assertIsNone(operator.parse_intent("just do something", {"listen", "leave"}))

    def test_no_legal_signal_maps_to_none(self) -> None:
        self.assertIsNone(operator.parse_intent("totally unrelated words", {"listen"}))


if __name__ == "__main__":
    unittest.main()
