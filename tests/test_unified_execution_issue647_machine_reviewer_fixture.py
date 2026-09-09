"""Deterministic fixture checks for Issue #647 machine-reviewer capability canary."""
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "machine-reviewer-capability" / "issue647-fixture-artifact.txt"
EXPECTED_SHA256 = "613c4724858ce4cda21601c5c5619916deda8b658c1a2c957f84942c96ba5c90"
EXPECTED_CONTENT = (
    "ISSUE-647 DISPOSABLE MACHINE-REVIEWER CAPABILITY FIXTURE\n"
    "========================================================\n"
    "\n"
    "This artifact exists only to provide a stable exact-head review target for Issue #647.\n"
    "It has no production, runtime, domain, trading, governance-authority, or deployment effect.\n"
    "\n"
    "fixture_id: ISSUE647-DISPOSABLE-MACHINE-REVIEWER-CAPABILITY\n"
    "source_issue: 647\n"
    "parent_defect: 646\n"
    "required_reviewer: second-brain-reviewer-vxz2[bot]\n"
    "required_canonicalizer: second-brain-canonicalizer-vxz2[bot]\n"
    "review_identity_rule: EXACT_HEAD_ONLY\n"
    "head_movement_rule: OLD_REVIEW_INVALID\n"
)


class Issue647MachineReviewerFixtureTests(unittest.TestCase):
    def test_fixture_exists(self) -> None:
        self.assertTrue(FIXTURE.is_file())

    def test_fixture_content_is_exact(self) -> None:
        self.assertEqual(FIXTURE.read_text(encoding="utf-8"), EXPECTED_CONTENT)

    def test_fixture_digest_is_exact(self) -> None:
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), EXPECTED_SHA256)

    def test_fixture_binds_three_distinct_roles(self) -> None:
        text = FIXTURE.read_text(encoding="utf-8")
        self.assertIn("required_reviewer: second-brain-reviewer-vxz2[bot]", text)
        self.assertIn("required_canonicalizer: second-brain-canonicalizer-vxz2[bot]", text)
        self.assertIn("review_identity_rule: EXACT_HEAD_ONLY", text)
        self.assertIn("head_movement_rule: OLD_REVIEW_INVALID", text)


if __name__ == "__main__":
    unittest.main()
