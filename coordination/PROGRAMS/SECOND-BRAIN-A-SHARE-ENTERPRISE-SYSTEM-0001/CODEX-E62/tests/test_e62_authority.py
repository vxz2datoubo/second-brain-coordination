from datetime import datetime, timedelta, timezone
import unittest

from src.e62_authority import (
    ApprovalGrantLedger, ApprovalRecord, AuthorityError, AuthorityPolicy, DigestBundle,
    GrantState, GrantVerifier, PrivateGitWriteGate, RequesterContext, SyntheticTestSigner,
)


NOW = datetime(2026, 8, 11, tzinfo=timezone.utc)
HEX = "a" * 64


def context(policy):
    return RequesterContext(policy.repository, policy.workflow_ref, policy.ref, policy.audience, policy.route_epoch, policy.task_id)


class E62AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.policy = AuthorityPolicy("vxz2datoubo/second-brain-coordination", ".github/workflows/certify.yml@refs/heads/main")
        self.ledger = ApprovalGrantLedger(self.policy, SyntheticTestSigner())
        self.verifier = GrantVerifier(self.policy, SyntheticTestSigner())
        self.gate = PrivateGitWriteGate(self.ledger, self.verifier)
        self.bundle = DigestBundle(HEX, "b" * 64, "c" * 64, "d" * 16)
        self.record = ApprovalRecord("grant-1", self.bundle, "PROJECT", "future-private-git-knowledge", "approval-1", "human-mfa-ref", NOW + timedelta(hours=1), "nonce-1")
        self.ledger.load_external_preapproval(self.record)

    def signed(self):
        self.ledger.claim("grant-1", context(self.policy), "request-1", NOW)
        return self.ledger.sign_claim("grant-1", context(self.policy), "request-1", NOW)

    def test_short_hash_cannot_be_only_digest(self):
        with self.assertRaises(AuthorityError):
            DigestBundle("d" * 16, "b" * 64, "c" * 64)

    def test_requester_context_substitution_rejected(self):
        wrong = RequesterContext(self.policy.repository, self.policy.workflow_ref, "refs/heads/other", self.policy.audience, 69, self.policy.task_id)
        with self.assertRaises(AuthorityError):
            self.ledger.claim("grant-1", wrong, "request-1", NOW)

    def test_duplicate_claim_rejected(self):
        self.ledger.claim("grant-1", context(self.policy), "request-1", NOW)
        with self.assertRaises(AuthorityError):
            self.ledger.claim("grant-1", context(self.policy), "request-2", NOW)

    def test_same_request_is_idempotent(self):
        self.ledger.claim("grant-1", context(self.policy), "request-1", NOW)
        grant1 = self.ledger.sign_claim("grant-1", context(self.policy), "request-1", NOW)
        grant2 = self.ledger.sign_claim("grant-1", context(self.policy), "request-1", NOW)
        self.assertEqual(grant1, grant2)

    def test_unknown_kms_outcome_cannot_resign_without_reconciliation(self):
        self.ledger.claim("grant-1", context(self.policy), "request-1", NOW)
        self.ledger.mark_kms_outcome_unknown("grant-1", "request-1", "kms-query-1")
        with self.assertRaises(AuthorityError):
            self.ledger.sign_claim("grant-1", context(self.policy), "request-1", NOW)
        self.ledger.reconcile_unknown_as_not_signed("grant-1", "kms-query-1")
        self.assertEqual(self.ledger.sign_claim("grant-1", context(self.policy), "request-1", NOW).grant_id, "grant-1")

    def test_fake_grant_signature_rejected(self):
        grant = self.signed()
        forged = type(grant)(**{**grant.__dict__, "scope": "GLOBAL"})
        with self.assertRaises(AuthorityError):
            self.verifier.verify(forged, NOW)

    def test_altered_full_digest_rejected(self):
        grant = self.signed()
        altered = DigestBundle("f" * 64, grant.bundle.canonical_semantic_sha256, grant.bundle.l0_provenance_sha256)
        forged = type(grant)(**{**grant.__dict__, "bundle": altered})
        with self.assertRaises(AuthorityError):
            self.verifier.verify(forged, NOW)

    def test_wrong_route_and_key_rejected(self):
        grant = self.signed()
        wrong_route = RequesterContext(self.policy.repository, self.policy.workflow_ref, self.policy.ref, self.policy.audience, 70, self.policy.task_id)
        with self.assertRaises(AuthorityError):
            self.verifier.verify(type(grant)(**{**grant.__dict__, "requester": wrong_route}), NOW)
        with self.assertRaises(AuthorityError):
            self.verifier.verify(type(grant)(**{**grant.__dict__, "key_id": "other-key"}), NOW)

    def test_wrong_approval_actor_rejected(self):
        grant = self.signed()
        forged = type(grant)(**{**grant.__dict__, "approval_identity_ref": "ordinary-caller"})
        with self.assertRaises(AuthorityError):
            self.verifier.verify(forged, NOW)

    def test_revoked_grant_rejected_by_private_gate(self):
        grant = self.signed()
        self.ledger.revoke("grant-1")
        with self.assertRaises(AuthorityError):
            self.gate.consume(grant, "parent-1", "parent-1", "e" * 64, NOW)

    def test_expired_approval_cannot_claim(self):
        self.record.expires_at = NOW - timedelta(seconds=1)
        with self.assertRaises(AuthorityError):
            self.ledger.claim("grant-1", context(self.policy), "request-1", NOW)
        self.assertEqual(self.record.state, GrantState.EXPIRED)

    def test_expired_signed_grant_rejected(self):
        self.record.expires_at = NOW + timedelta(seconds=1)
        grant = self.signed()
        with self.assertRaises(AuthorityError):
            self.verifier.verify(grant, NOW + timedelta(seconds=2))

    def test_wrong_claim_token_cannot_drive_state_transition(self):
        self.ledger.claim("grant-1", context(self.policy), "request-1", NOW)
        with self.assertRaises(AuthorityError):
            self.ledger.mark_retryable_before_sign("grant-1", "request-2")

    def test_private_gate_consumes_once(self):
        grant = self.signed()
        receipt = self.gate.consume(grant, "parent-1", "parent-1", "e" * 64, NOW)
        self.assertEqual(receipt.grant_id, "grant-1")
        with self.assertRaises(AuthorityError):
            self.gate.consume(grant, "parent-1", "parent-1", "e" * 64, NOW)

    def test_private_gate_rejects_stale_parent(self):
        with self.assertRaises(AuthorityError):
            self.gate.consume(self.signed(), "parent-1", "parent-2", "e" * 64, NOW)

    def test_wrong_target_rejected(self):
        self.record.target = "other-target"
        with self.assertRaises(AuthorityError):
            self.gate.consume(self.signed(), "parent-1", "parent-1", "e" * 64, NOW)


if __name__ == "__main__":
    unittest.main()
