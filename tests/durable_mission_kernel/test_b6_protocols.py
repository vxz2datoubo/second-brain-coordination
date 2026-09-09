"""B6 tests — reviewer/canonicalizer independence, no-self-merge, reroute/fail-closed."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.durable_mission_kernel import protocols  # noqa: E402


def _cap(principal, can_merge=True, can_write=False, verified=True):
    return protocols.CanonicalizerCapability(
        principal=principal, can_merge=can_merge, can_write=can_write,
        merge_permission_verified=verified, evidence="synthetic",
    )


class B6ProtocolTests(unittest.TestCase):
    def test_three_distinct_principals_ok(self):
        self.assertTrue(protocols.assert_principal_independence(
            protocols.PrincipalSet("author", "reviewer", "canonicalizer")))

    def test_author_reviewer_equal_violates(self):
        with self.assertRaises(protocols.ProtocolError):
            protocols.assert_principal_independence(
                protocols.PrincipalSet("same", "same", "canonicalizer"))

    def test_self_merge_forbidden(self):
        with self.assertRaises(protocols.ProtocolError):
            protocols.assert_no_self_merge("author", "author")

    def test_self_review_forbidden(self):
        with self.assertRaises(protocols.ProtocolError):
            protocols.assert_no_self_review("author", "author")

    def test_canonicalizer_ready_requires_merge_capability(self):
        self.assertTrue(protocols.canonicalizer_ready(_cap("canon", can_merge=True, verified=True)))
        with self.assertRaises(protocols.ProtocolError):
            protocols.canonicalizer_ready(_cap("canon", can_merge=False, verified=True))
        # read-only (no merge permission verified) must not be READY
        with self.assertRaises(protocols.ProtocolError):
            protocols.canonicalizer_ready(_cap("canon", can_merge=True, verified=False))

    def test_reroute_uses_legitimate_canonicalizer(self):
        principal = protocols.reroute_or_fail_closed(
            author="author", canonicalizer=_cap("canon"), fallback=None)
        self.assertEqual(principal, "canon")

    def test_reroute_never_self_merge(self):
        with self.assertRaises(protocols.ProtocolError):
            protocols.reroute_or_fail_closed(author="author", canonicalizer=_cap("author"), fallback=None)

    def test_reroute_fails_closed_when_no_capability(self):
        with self.assertRaises(protocols.ProtocolError):
            protocols.reroute_or_fail_closed(
                author="author", canonicalizer=_cap("c1", can_merge=False),
                fallback=_cap("c2", can_merge=False))


if __name__ == "__main__":
    unittest.main()
