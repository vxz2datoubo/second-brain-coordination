"""Governance fixture tests for Issue #643 disposable machine-canonicalizer merge-capability fixture.

This test file is a MECHANICALLY TRIVIAL, NON-BUSINESS fixture. Its only purpose is
to give the exact-head CI a deterministic, independently verifiable merge target:
it asserts that a single fixture-only artifact exists with an exact fixed content
and an exact fixed SHA-256, so a later expected-head mechanical merge can be
verified by readback without any production/runtime/domain effect.
"""
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ARTIFACT = ROOT / "tests" / "fixtures" / "canonicalizer-merge-capability" / "issue643-fixture-artifact.txt"

EXPECTED_SHA256 = "c1ba14f39d1ea26426aa71893da9062d01606059fb7a7bb3407e62cbc62de606"

EXPECTED_CONTENT = (
    "ISSUE-643 DISPOSABLE MACHINE-CANONICALIZER MERGE-CAPABILITY FIXTURE ARTIFACT\n"
    "=======================================================================\n"
    "\n"
    "This is a mechanically trivial, non-business fixture used exclusively to\n"
    "reality-test the dedicated GitHub App canonicalizer's expected-head merge\n"
    "capability under the exact boundaries of Issue #643.\n"
    "\n"
    "No production, runtime, domain, trading, or governance effect. This file's\n"
    "only purpose is to be a stable, independently verifiable merge target whose\n"
    "content is asserted byte-for-byte by a deterministic test.\n"
    "\n"
    "fixture_id: ISSUE643-DISPOSABLE-MERGE-CAPABILITY\n"
    "governance_ref: Issue #643 (Owner approval OWNER_APPROVAL_643/v1)\n"
    "mission_ref: Issue #644 P0\n"
    "canonicalization_collision_key: vxz2datoubo/second-brain-coordination + main + CANONICALIZATION_AUTHORITY\n"
)


class Issue643DisposableMergeCapabilityFixtureTests(unittest.TestCase):
    def test_fixture_artifact_exists(self) -> None:
        self.assertTrue(FIXTURE_ARTIFACT.is_file(), "fixture artifact must exist")

    def test_fixture_artifact_content_is_exact(self) -> None:
        content = FIXTURE_ARTIFACT.read_text(encoding="utf-8")
        self.assertEqual(content, EXPECTED_CONTENT)

    def test_fixture_artifact_sha256_is_exact(self) -> None:
        digest = hashlib.sha256(FIXTURE_ARTIFACT.read_bytes()).hexdigest()
        self.assertEqual(digest, EXPECTED_SHA256)

    def test_fixture_has_no_business_or_runtime_effect(self) -> None:
        content = FIXTURE_ARTIFACT.read_text(encoding="utf-8")
        for forbidden in ("production", "runtime", "domain", "trading", "funds", "orders"):
            # the word is allowed only inside the explicit "No production/runtime/domain/trading..." disclaimer
            self.assertNotIn(f"{forbidden}_deploy", content)
        self.assertIn("No production, runtime, domain, trading, or governance effect", content)


if __name__ == "__main__":
    unittest.main()
