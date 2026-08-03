"""E45 adversarial tests for attested witness and recovery enforcement.

All fixtures are synthetic and file-backed.  They exercise the same durable
claim APIs as the control-plane contracts without issuing a live request.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_ROOT / "src"))
sys.path.insert(0, str(TEST_ROOT))

from test_e44_durable_challenge import CANARY, HASH, NONCE, TASK, _claimed, _holder  # noqa: E402
from brainops_control_plane.durable_authority import (  # noqa: E402
    DurableClaimResultCode,
    DurableClaimState,
    OwnerType,
    SyntheticFileCasGateway,
)
from brainops_control_plane.durable_challenge import (  # noqa: E402
    AutomationTerminalEvidence,
    CapabilityDecisionUseLedger,
    CapabilityWitness,
    CliTerminalEvidence,
    DurableChallengeLedger,
    LedgerCode,
    ManualAppTerminalEvidence,
    RecoveryAuthorizationLedger,
    _mint_challenge,
    _synthetic_transport_witness_verifier,
    bind_challenge_decision,
    evaluate_challenge_capability,
    recovery_grant_from_claim,
    validate_owner_terminal_evidence,
)
from brainops_control_plane.execution_evidence import CapabilityTarget  # noqa: E402
from brainops_control_plane.models import CapabilityStatus, ValidationError  # noqa: E402


OBSERVED = "2026-08-02T12:05:00Z"
CHECKED = "2026-08-02T12:05:01Z"
TRANSPORT = "transport.e45"
ATTESTOR = "attestor.e45"


class LossAfterLedgerWriteGateway(SyntheticFileCasGateway):
    """Apply the grant consumption, then lose the actual recovery write reply."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.fail_after_next_write = False
        self._writes_after_arm = 0

    def compare_and_set(self, object_id, expected_revision, payload):  # type: ignore[no-untyped-def]
        if self.fail_after_next_write:
            if self._writes_after_arm >= 1:
                raise OSError("synthetic lost response after recovery-ledger consumption")
            self._writes_after_arm += 1
        return super().compare_and_set(object_id, expected_revision, payload)


class E45AttestedWitnessEnforcementTests(unittest.TestCase):
    def _challenge(self, holder, *, target=CapabilityTarget.CODEX_APP, nonce=NONCE):
        return _mint_challenge(
            "challenge.e45.one",
            target,
            holder,
            TASK,
            44,
            CANARY,
            nonce,
            "2026-08-02T12:03:00Z",
            "2026-08-02T12:10:00Z",
            60,
        )

    @staticmethod
    def _raw(challenge, *, status=CapabilityStatus.SUPPORTED, nonce=None, transport=TRANSPORT):
        return CapabilityWitness(
            challenge.challenge_id,
            challenge.target,
            challenge.holder,
            challenge.task_id,
            challenge.route_epoch,
            challenge.canary_id,
            nonce or challenge.nonce,
            OBSERVED,
            status,
            HASH,
            transport,
        )

    def _bound_decision(self, root: Path, claim, challenge=None):
        challenge = challenge or self._challenge(claim.holder)
        ledger = DurableChallengeLedger("ledger.e45.challenge", SyntheticFileCasGateway(root / "challenge"))
        self.assertEqual(ledger.issue(challenge).code, LedgerCode.ISSUED)
        attested = _synthetic_transport_witness_verifier(TRANSPORT, ATTESTOR).attest(self._raw(challenge), CHECKED)
        consumed = ledger.consume(challenge, attested, CHECKED)
        self.assertEqual(consumed.code, LedgerCode.CONSUMED)
        return bind_challenge_decision(consumed.decision, claim, "2026-08-02T12:05:02Z")

    @staticmethod
    def _finalized(root: Path, holder=None):
        authority, provenance, holder, claimed = _claimed(root, holder=holder)
        attached = authority.attach_invocation(provenance, claimed.record.claim_id, holder, "invoke.e45.one")
        final = authority.finalize(
            provenance,
            attached.record.claim_id,
            holder,
            DurableClaimState.SUCCEEDED,
            "synthetic_terminal",
            "2026-08-02T12:05:00Z",
            invocation_id=attached.record.invocation_id,
        )
        return authority, provenance, holder, final.record

    @staticmethod
    def _manual(claim, *, holder=None, transport=TRANSPORT):
        holder = holder or claim.holder
        return ManualAppTerminalEvidence(
            claim.claim_id,
            claim.invocation_id,
            holder,
            CapabilityTarget.CODEX_APP,
            "completed",
            claim.terminal_at,
            "session.e45",
            HASH,
            HASH,
            HASH,
            holder.owner_instance_id,
            holder.claimant_correlation_id,
            transport,
        )

    def test_caller_constructed_witness_is_rejected_before_consumption(self):
        with tempfile.TemporaryDirectory() as directory:
            _authority, _provenance, holder, claim = _claimed(Path(directory))
            challenge = self._challenge(holder)
            ledger = DurableChallengeLedger("ledger.e45.raw", SyntheticFileCasGateway(Path(directory) / "ledger"))
            self.assertEqual(ledger.issue(challenge).code, LedgerCode.ISSUED)
            result = ledger.consume(challenge, self._raw(challenge), CHECKED)
        self.assertEqual(result.code, LedgerCode.UNATTESTED)

    def test_wrong_attestor_transport_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            _authority, _provenance, holder, _claim = _claimed(Path(directory))
            challenge = self._challenge(holder)
            with self.assertRaises(ValidationError):
                _synthetic_transport_witness_verifier("transport.other", ATTESTOR).attest(self._raw(challenge), CHECKED)

    def test_cross_nonce_attested_witness_cannot_consume(self):
        with tempfile.TemporaryDirectory() as directory:
            _authority, _provenance, holder, _claim = _claimed(Path(directory))
            challenge = self._challenge(holder)
            ledger = DurableChallengeLedger("ledger.e45.nonce", SyntheticFileCasGateway(Path(directory) / "ledger"))
            ledger.issue(challenge)
            raw = self._raw(challenge, nonce="nonce.e45.other")
            witness = _synthetic_transport_witness_verifier(TRANSPORT, ATTESTOR).attest(raw, CHECKED)
            result = ledger.consume(challenge, witness, CHECKED)
        self.assertEqual(result.code, LedgerCode.BINDING_MISMATCH)

    def test_predecision_cannot_be_used_as_positive_capability(self):
        with tempfile.TemporaryDirectory() as directory:
            _authority, _provenance, holder, _claim = _claimed(Path(directory))
            challenge = self._challenge(holder)
            ledger = DurableChallengeLedger("ledger.e45.pre", SyntheticFileCasGateway(Path(directory) / "ledger"))
            ledger.issue(challenge)
            witness = _synthetic_transport_witness_verifier(TRANSPORT, ATTESTOR).attest(self._raw(challenge), CHECKED)
            preliminary = ledger.consume(challenge, witness, CHECKED).decision
        result = evaluate_challenge_capability(CapabilityTarget.CODEX_APP, preliminary)
        self.assertEqual(result.status, CapabilityStatus.BLOCKED)
        self.assertEqual(result.reason_code, "claim_bound_attested_capability_required")

    def test_claim_bound_decision_is_globally_one_shot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _authority, _provenance, _holder_value, claim = _claimed(root)
            bound = self._bound_decision(root, claim.record)
            uses = CapabilityDecisionUseLedger("ledger.e45.uses", SyntheticFileCasGateway(root / "uses"))
            first = evaluate_challenge_capability(CapabilityTarget.CODEX_APP, bound, use_ledger=uses, checked_at="2026-08-02T12:05:03Z")
            restarted = CapabilityDecisionUseLedger("ledger.e45.uses", SyntheticFileCasGateway(root / "uses"))
            replay = evaluate_challenge_capability(CapabilityTarget.CODEX_APP, bound, use_ledger=restarted, checked_at="2026-08-02T12:05:04Z")
        self.assertEqual(first.status, CapabilityStatus.SUPPORTED)
        self.assertEqual(replay.status, CapabilityStatus.BLOCKED)
        self.assertEqual(replay.reason_code, "decision_use_decision_already_used")

    def test_expired_decision_is_blocked_before_use(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _authority, _provenance, _holder_value, claim = _claimed(root)
            bound = self._bound_decision(root, claim.record)
            result = evaluate_challenge_capability(
                CapabilityTarget.CODEX_APP,
                bound,
                use_ledger=CapabilityDecisionUseLedger("ledger.e45.expired", SyntheticFileCasGateway(root / "uses")),
                checked_at="2026-08-02T12:10:00Z",
            )
        self.assertEqual(result.status, CapabilityStatus.BLOCKED)
        self.assertEqual(result.reason_code, "challenge_decision_expired")

    def test_decision_cannot_be_rebound_to_other_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _a, _p, _h, first = _claimed(root / "one")
            _a2, _p2, other_holder, second = _claimed(root / "two", holder=_holder(instance="owner.e45.other", correlation="corr.e45.other"))
            bound = self._bound_decision(root / "one", first.record)
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(second.record, bound, self._manual(second.record, holder=other_holder))

    def test_manual_identity_splice_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _authority, _provenance, _holder_value, claim = self._finalized(root)
            bound = self._bound_decision(root, claim)
            spliced = ManualAppTerminalEvidence(**{**self._manual(claim).__dict__, "attested_correlation_id": "corr.e45.splice"})
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(claim, bound, spliced)

    def test_manual_transport_splice_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _authority, _provenance, _holder_value, claim = self._finalized(root)
            bound = self._bound_decision(root, claim)
            spliced = ManualAppTerminalEvidence(**{**self._manual(claim).__dict__, "attested_transport_id": "transport.e45.splice"})
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(claim, bound, spliced)

    def test_automation_and_cli_identity_splices_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            auto_holder = _holder(OwnerType.APP_AUTOMATION_NEW_RUN, "owner.e45.auto", "corr.e45.auto")
            _authority, _provenance, _holder_value, auto_claim = self._finalized(root / "auto", auto_holder)
            auto_bound = self._bound_decision(root / "auto", auto_claim)
            auto = AutomationTerminalEvidence(auto_claim.claim_id, auto_claim.invocation_id, auto_holder, CapabilityTarget.CODEX_APP, "completed", auto_claim.terminal_at, "dispatch.e45", "run.e45", "callback.e45", "callback.identity.e45", HASH, HASH, HASH, auto_holder.owner_instance_id, "corr.e45.splice", TRANSPORT)
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(auto_claim, auto_bound, auto)
            cli_holder = _holder(OwnerType.CODEX_CLI_PROCESS, "owner.e45.cli", "corr.e45.cli")
            _authority, _provenance, _holder_value, cli_claim = self._finalized(root / "cli", cli_holder)
            cli_bound = self._bound_decision(root / "cli", cli_claim, self._challenge(cli_holder, target=CapabilityTarget.CODEX_CLI))
            cli = CliTerminalEvidence(cli_claim.claim_id, cli_claim.invocation_id, cli_holder, CapabilityTarget.CODEX_CLI, "completed", cli_claim.terminal_at, "launcher.e45", 42, HASH, 0, "CLEAN", HASH, HASH, cli_holder.owner_instance_id, cli_holder.claimant_correlation_id, "transport.e45.splice")
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(cli_claim, cli_bound, cli)

    def test_legacy_recovery_path_is_non_mutating_and_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, claimed = _claimed(Path(directory))
            result = authority.recover_expired_claim(provenance, claimed.record.claim_id, holder, "2026-08-02T12:08:00Z", 1)
            reread = authority.read(provenance)
        self.assertEqual(result.code, DurableClaimResultCode.RECOVERY_UNAUTHORIZED)
        self.assertEqual(reread.record.state, DurableClaimState.CLAIMED)

    def test_recovery_requires_durable_grant_consumption_at_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, provenance, _holder_value, claimed = _claimed(root)
            grant = recovery_grant_from_claim("grant.e45.one", claimed.record, "2026-08-02T12:05:00Z", "2026-08-02T12:10:00Z", "timeout")
            ledger = RecoveryAuthorizationLedger("ledger.e45.recovery", SyntheticFileCasGateway(root / "recovery"))
            self.assertEqual(ledger.issue(grant).code, LedgerCode.ISSUED)
            result = authority.governed_recover_expired_claim(provenance, grant, ledger, "2026-08-02T12:06:00Z")
            replay = authority.governed_recover_expired_claim(provenance, grant, ledger, "2026-08-02T12:06:01Z")
        self.assertEqual(result.code, DurableClaimResultCode.RECOVERY_RECONCILED)
        self.assertEqual(replay.code, DurableClaimResultCode.TERMINAL_EXISTS)

    def test_lost_response_after_grant_consumption_never_reports_recovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gateway = LossAfterLedgerWriteGateway(root / "shared")
            authority, provenance, _holder_value, claimed = _claimed(root / "claim")
            # Recreate the claim through the controlled gateway used by the recovery call.
            authority = type(authority)("vxz2datoubo/second-brain-coordination", "e42.claim", gateway)
            claimed = authority.claim(provenance, "claim.e45.loss", _holder(), "2026-08-02T12:03:00Z")
            grant = recovery_grant_from_claim("grant.e45.loss", claimed.record, "2026-08-02T12:05:00Z", "2026-08-02T12:10:00Z", "timeout")
            ledger = RecoveryAuthorizationLedger("ledger.e45.loss", gateway)
            self.assertEqual(ledger.issue(grant).code, LedgerCode.ISSUED)
            gateway.fail_after_next_write = True
            result = authority.governed_recover_expired_claim(provenance, grant, ledger, "2026-08-02T12:06:00Z")
            reread = authority.read(provenance)
            consumed_again = ledger.consume(grant, claimed.record, "2026-08-02T12:06:01Z")
        self.assertEqual(result.code, DurableClaimResultCode.AUTHORITY_UNAVAILABLE)
        self.assertEqual(reread.record.state, DurableClaimState.CLAIMED)
        self.assertEqual(consumed_again.code, LedgerCode.ALREADY_CONSUMED)
