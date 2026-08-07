from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from e56_authority.authority import AuthorityError
from e56_authority.hygiene import HygienePolicy, is_forbidden
from e56_authority.topology import ExternalProviderAnchor, RouteTopology, verify_topology


BASE = "a" * 40
PLAN = "b" * 40
TESTED = "c" * 40
RECEIPT = "d" * 40
PLAN_PATH = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CODEX-E56/PROJECT-PLAN.md"
RECEIPT_PATH = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CODEX-E56/RUN-RECEIPT.md"


class TopologyTests(unittest.TestCase):
    def route(self):
        return RouteTopology(BASE, PLAN, PLAN_PATH, TESTED, RECEIPT, (RECEIPT_PATH,))

    def anchor(self):
        return ExternalProviderAnchor(101, 102, ".github/workflows/codex-e56-canonical-authority-closure.yml", "codex/e55-post-receipt-canonical-authority-closure-0052-e56", TESTED, RECEIPT, (1, 2, 3, 4, 5, 6), 7, tuple(range(11, 24)), tuple(f"artifact-{index}" for index in range(13)), tuple("f" * 64 for _index in range(13)))

    def verify_with(self, parents):
        def fake_parent(_repo, commit):
            return parents[commit]
        def fake_git(_repo, *args):
            if args == ("diff", "--name-only", f"{BASE}..{PLAN}"):
                return PLAN_PATH
            if args == ("rev-list", "--reverse", f"{BASE}..{RECEIPT}"):
                return "\n".join((PLAN, TESTED, RECEIPT))
            if args == ("rev-parse", "HEAD"):
                return RECEIPT
            if args == ("diff", "--name-only", f"{TESTED}..{RECEIPT}"):
                return RECEIPT_PATH
            if args == ("show", f"{RECEIPT}:{RECEIPT_PATH}"):
                return "receipt"
            if args == ("rev-parse", f"{RECEIPT}^{{tree}}"):
                return "e" * 40
            raise AssertionError(args)
        with patch("e56_authority.topology._one_parent", side_effect=fake_parent), patch("e56_authority.topology._git", side_effect=fake_git):
            return verify_topology(Path("."), self.route(), self.anchor())

    def test_plan_parent_and_path_are_strict(self):
        with self.assertRaises(AuthorityError):
            self.verify_with({PLAN: "z" * 40, TESTED: PLAN, RECEIPT: TESTED})

    def test_linear_chain_rejects_unexpected_parent(self):
        with self.assertRaises(AuthorityError):
            self.verify_with({PLAN: BASE, TESTED: "y" * 40, RECEIPT: TESTED})

    def test_valid_linear_topology_passes(self):
        report = self.verify_with({PLAN: BASE, TESTED: PLAN, RECEIPT: TESTED})
        self.assertEqual(report.plan_parent, BASE)
        self.assertEqual(report.receipt_parent, TESTED)


class HygieneTests(unittest.TestCase):
    def test_task_defined_pattern_is_enforced(self):
        policy = HygienePolicy("fixture-v1", ("**/*.private",))
        self.assertTrue(is_forbidden("sensitive/record.private", policy))

    def test_builtin_like_path_can_be_versioned(self):
        policy = HygienePolicy("fixture-v1", ("**/cache/**", "**/*.jsonl"))
        self.assertTrue(is_forbidden("data/cache/item.txt", policy))
        self.assertTrue(is_forbidden("data/events.jsonl", policy))
        self.assertFalse(is_forbidden("src/authority.py", policy))


if __name__ == "__main__":
    unittest.main()
