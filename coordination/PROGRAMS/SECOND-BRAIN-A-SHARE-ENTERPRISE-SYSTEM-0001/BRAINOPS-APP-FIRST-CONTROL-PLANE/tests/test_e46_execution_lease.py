"""E46 adversarial tests for the mandatory durable execution lease."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_ROOT / "src"))
sys.path.insert(0, str(TEST_ROOT))

from test_e44_durable_challenge import (  # noqa: E402
    CANARY,
    HASH,
    NONCE,
    TASK,
    _authority,
    _holder,
    _provenance,
    _route_snapshot,
)
from brainops_control_plane.durable_authority import (  # noqa: E402
    ClaimHolder,
    DurableClaimAuthority,
    DurableClaimResultCode,
    DurableClaimState,
    OwnerType,
    SyntheticFileCasGateway,
)
from brainops_control_plane.durable_challenge import (  # noqa: E402
    CapabilityWitness,
    DurableChallengeLedger,
    LedgerCode,
    ManualAppTerminalEvidence,
    _mint_challenge,
    _synthetic_transport_witness_verifier,
    bind_challenge_decision,
    validate_owner_terminal_evidence,
)
from brainops_control_plane.execution_evidence import CapabilityTarget, ExecutionEvidenceType  # noqa: E402
from brainops_control_plane.execution_lease import (  # noqa: E402
    AttestedExecutionIdentity,
    AttestedTerminalEvidence,
    DurableExecutionLeaseAuthority,
    ExecutionIdentityKind,
    ExecutionLeaseCode,
    ExecutionLeaseRecord,
    ExecutionLeaseState,
    JournaledTerminalMutationPermit,
    LeaseEffectPermit,
    OperationPhase,
    RawAutomationExecutionIdentity,
    RawCliExecutionIdentity,
    RawManualExecutionIdentity,
    RawTerminalObservation,
    TerminalMutationAuthorization,
    TransportCapturedIdentity,
    _execution_identity_verifier,
    _synthetic_execution_transport,
)
from brainops_control_plane.models import CapabilityStatus, ValidationError  # noqa: E402
from brainops_control_plane.terminal_attestation import RawInvocationTransportObservation, _bounded_transport_attestor, _one_shot_challenge  # noqa: E402


TRANSPORT = "transport.e46"
SOURCE = "source.e46"
VERIFIER = "verifier.e46"
CAPABILITY_AT = "2026-08-02T12:04:03Z"
EFFECT_AT = "2026-08-02T12:04:04Z"
ATTACH_AT = "2026-08-02T12:04:05Z"
IDENTITY_OBSERVED_AT = "2026-08-02T12:04:06Z"
IDENTITY_CAPTURED_AT = "2026-08-02T12:04:07Z"
IDENTITY_ATTESTED_AT = "2026-08-02T12:04:08Z"
TERMINAL_AT = "2026-08-02T12:04:09Z"
TERMINAL_CAPTURED_AT = "2026-08-02T12:04:10Z"
TERMINAL_VERIFIED_AT = "2026-08-02T12:04:11Z"
TERMINAL_ATTESTED_AT = "2026-08-02T12:04:12Z"
COMMITTED_AT = "2026-08-02T12:04:13Z"


class PostApplyResponseLossGateway:
    """Apply one claim CAS and then hide its response from the caller."""

    def __init__(self, backing: SyntheticFileCasGateway) -> None:
        self.backing = backing
        self.lose_next_applied_response = False
        self.loss_object_fragment: str | None = None
        self.applied_writes = 0

    def read(self, object_id):  # type: ignore[no-untyped-def]
        return self.backing.read(object_id)

    def compare_and_set(self, object_id, expected_revision, payload):  # type: ignore[no-untyped-def]
        result = self.backing.compare_and_set(object_id, expected_revision, payload)
        if result.applied:
            self.applied_writes += 1
        if self.lose_next_applied_response and result.applied and (self.loss_object_fragment is None or self.loss_object_fragment in object_id):
            self.lose_next_applied_response = False
            raise OSError("synthetic response loss after applied claim CAS")
        return result


class E46ExecutionLeaseTests(unittest.TestCase):
    def _context(
        self,
        root: Path,
        *,
        owner_type: OwnerType = OwnerType.CURRENT_CODEX_APP_SESSION,
        target: CapabilityTarget = CapabilityTarget.CODEX_APP,
        instance: str = "owner.e46.one",
        correlation: str = "corr.e46.one",
        claim_gateway=None,
        lease_gateway=None,
        challenge_expires: str = "2026-08-02T12:10:00Z",
    ):
        provenance = _provenance()
        holder = _holder(owner_type, instance, correlation)
        gateway = claim_gateway or SyntheticFileCasGateway(root / "claim")
        authority = DurableClaimAuthority("vxz2datoubo/second-brain-coordination", "e42.claim", gateway)
        claimed = authority.claim(provenance, "claim.e46.one", holder, "2026-08-02T12:03:00Z")
        self.assertEqual(claimed.code, DurableClaimResultCode.CLAIMED)
        challenge = _mint_challenge(
            "challenge.e46.one",
            target,
            holder,
            TASK,
            44,
            CANARY,
            NONCE,
            "2026-08-02T12:04:00Z",
            challenge_expires,
            60,
        )
        challenge_ledger = DurableChallengeLedger("ledger.e46.challenge", SyntheticFileCasGateway(root / "challenge"))
        self.assertEqual(challenge_ledger.issue(challenge).code, LedgerCode.ISSUED)
        raw_witness = CapabilityWitness(
            challenge.challenge_id,
            target,
            holder,
            TASK,
            44,
            CANARY,
            NONCE,
            "2026-08-02T12:04:01Z",
            CapabilityStatus.SUPPORTED,
            HASH,
            TRANSPORT,
        )
        witness = _synthetic_transport_witness_verifier(TRANSPORT, "attestor.e46").attest(raw_witness, "2026-08-02T12:04:02Z")
        consumed = challenge_ledger.consume(challenge, witness, "2026-08-02T12:04:02Z")
        self.assertEqual(consumed.code, LedgerCode.CONSUMED)
        lease_store = lease_gateway or SyntheticFileCasGateway(root / "lease")
        manager = DurableExecutionLeaseAuthority("lease.e46", lease_store, authority)
        created = manager.attest_capability(provenance, claimed.record.claim_id, holder, target, consumed.decision, CAPABILITY_AT)
        return {
            "root": root,
            "provenance": provenance,
            "holder": holder,
            "target": target,
            "authority": authority,
            "claim_gateway": gateway,
            "claim": claimed.record,
            "challenge": challenge,
            "decision": consumed.decision,
            "lease_gateway": lease_store,
            "manager": manager,
            "created": created,
        }

    def _attached(self, root: Path, **kwargs):
        context = self._context(root, **kwargs)
        created = context["created"]
        self.assertEqual(created.code, ExecutionLeaseCode.CAPABILITY_ATTESTED)
        effect = context["manager"].authorize_effect(context["provenance"], created.record.lease_id, context["holder"], context["target"], EFFECT_AT)
        self.assertEqual(effect.code, ExecutionLeaseCode.EFFECT_AUTHORIZED)
        attached = context["manager"].attach_invocation(context["provenance"], effect.effect_permit, "invocation.e46.one", ATTACH_AT)
        self.assertEqual(attached.code, ExecutionLeaseCode.INVOCATION_ATTACHED)
        context.update(effect=effect, attached=attached)
        return context

    @staticmethod
    def _raw_identity(context):
        holder = context["holder"]
        if holder.owner_type is OwnerType.CURRENT_CODEX_APP_SESSION:
            return RawManualExecutionIdentity("session.e46", holder.owner_instance_id, holder.claimant_correlation_id, TRANSPORT, IDENTITY_OBSERVED_AT)
        if holder.owner_type is OwnerType.APP_AUTOMATION_NEW_RUN:
            return RawAutomationExecutionIdentity("dispatch.e46", "run.e46", "callback.e46", "callback.identity.e46", holder.owner_instance_id, holder.claimant_correlation_id, TRANSPORT, IDENTITY_OBSERVED_AT)
        return RawCliExecutionIdentity("launcher.e46", 4242, HASH, "process.e46", holder.owner_instance_id, holder.claimant_correlation_id, TRANSPORT, IDENTITY_OBSERVED_AT)

    def _terminal(self, root: Path, **kwargs):
        context = self._attached(root, **kwargs)
        transport = _synthetic_execution_transport(TRANSPORT, SOURCE)
        verifier = _execution_identity_verifier(VERIFIER, SOURCE)
        identity_capture = transport.capture_identity(self._raw_identity(context), IDENTITY_CAPTURED_AT)
        identity = verifier.attest_identity(context["attached"].record, identity_capture, IDENTITY_ATTESTED_AT)
        exit_code = 0 if identity.kind is ExecutionIdentityKind.CLI else None
        raw_terminal = RawTerminalObservation(
            context["attached"].record.lease_id,
            context["claim"].claim_id,
            "invocation.e46.one",
            identity.identity_digest,
            "completed",
            "synthetic_terminal",
            TERMINAL_AT,
            HASH,
            HASH,
            TRANSPORT,
            exit_code,
        )
        terminal_capture = transport.capture_terminal(raw_terminal, TERMINAL_CAPTURED_AT)
        evidence = verifier.attest_terminal(context["attached"].record, identity, terminal_capture, TERMINAL_VERIFIED_AT)
        attested = context["manager"].attest_terminal(context["provenance"], evidence, TERMINAL_ATTESTED_AT)
        self.assertEqual(attested.code, ExecutionLeaseCode.TERMINAL_ATTESTED)
        context.update(transport=transport, verifier=verifier, identity=identity, raw_terminal=raw_terminal, evidence=evidence, terminal_attested=attested)
        return context

    def test_state_versions_are_monotonic(self):
        self.assertEqual([state.version for state in ExecutionLeaseState], [1, 2, 3, 4, 5])

    def test_capability_creates_durable_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
        self.assertEqual(context["created"].code, ExecutionLeaseCode.CAPABILITY_ATTESTED)
        self.assertEqual(context["created"].record.state, ExecutionLeaseState.CAPABILITY_ATTESTED)

    def test_lease_round_trip_is_hash_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            payload = context["created"].record.document_bytes
            restored = ExecutionLeaseRecord.from_document_bytes(payload, context["provenance"])
        self.assertEqual(restored, context["created"].record)

    def test_capability_replay_does_not_create_second_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            replay = context["manager"].attest_capability(context["provenance"], context["claim"].claim_id, context["holder"], context["target"], context["decision"], CAPABILITY_AT)
        self.assertEqual(replay.code, ExecutionLeaseCode.ALREADY_EXISTS)
        self.assertEqual(replay.record.lease_id, context["created"].record.lease_id)

    def test_unsealed_capability_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            result = context["manager"].attest_capability(context["provenance"], context["claim"].claim_id, context["holder"], context["target"], object(), CAPABILITY_AT)
        self.assertEqual(result.code, ExecutionLeaseCode.CAPABILITY_REQUIRED)

    def test_wrong_target_is_rejected_at_capability_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            result = context["manager"].attest_capability(context["provenance"], context["claim"].claim_id, context["holder"], CapabilityTarget.CODEX_CLI, context["decision"], CAPABILITY_AT)
        self.assertEqual(result.code, ExecutionLeaseCode.BINDING_MISMATCH)

    def test_wrong_holder_is_rejected_at_capability_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            wrong = ClaimHolder(context["holder"].owner_type, "owner.e46.other", context["holder"].claimant_correlation_id)
            result = context["manager"].attest_capability(context["provenance"], context["claim"].claim_id, wrong, context["target"], context["decision"], CAPABILITY_AT)
        self.assertEqual(result.code, ExecutionLeaseCode.BINDING_MISMATCH)

    def test_expired_lease_blocks_effect_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            result = context["manager"].authorize_effect(context["provenance"], context["created"].record.lease_id, context["holder"], context["target"], "2026-08-02T12:10:00Z")
        self.assertEqual(result.code, ExecutionLeaseCode.LEASE_EXPIRED)

    def test_effect_authorization_requires_exact_holder(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            wrong = ClaimHolder(context["holder"].owner_type, "owner.e46.other", context["holder"].claimant_correlation_id)
            result = context["manager"].authorize_effect(context["provenance"], context["created"].record.lease_id, wrong, context["target"], EFFECT_AT)
        self.assertEqual(result.code, ExecutionLeaseCode.BINDING_MISMATCH)

    def test_effect_authorization_requires_exact_target(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            result = context["manager"].authorize_effect(context["provenance"], context["created"].record.lease_id, context["holder"], CapabilityTarget.CODEX_CLI, EFFECT_AT)
        self.assertEqual(result.code, ExecutionLeaseCode.BINDING_MISMATCH)

    def test_effect_authorization_retry_returns_the_same_recoverable_continuation(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            first = context["manager"].authorize_effect(context["provenance"], context["created"].record.lease_id, context["holder"], context["target"], EFFECT_AT)
            second = context["manager"].authorize_effect(context["provenance"], context["created"].record.lease_id, context["holder"], context["target"], EFFECT_AT)
        self.assertEqual(first.code, ExecutionLeaseCode.EFFECT_AUTHORIZED)
        self.assertEqual(second.code, ExecutionLeaseCode.EFFECT_AUTHORIZED)
        self.assertEqual(second.effect_permit.permit_id, first.effect_permit.permit_id)

    def test_legacy_effect_permit_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            permit = context["authority"].acquire_effect_permit(context["provenance"], context["claim"].claim_id, context["holder"], EFFECT_AT)
        self.assertIsNone(permit)

    def test_effect_permit_constructor_is_sealed(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            effect = context["manager"].authorize_effect(context["provenance"], context["created"].record.lease_id, context["holder"], context["target"], EFFECT_AT)
            with self.assertRaises(ValidationError):
                LeaseEffectPermit(effect.record)

    def test_null_invocation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            effect = context["manager"].authorize_effect(context["provenance"], context["created"].record.lease_id, context["holder"], context["target"], EFFECT_AT)
            result = context["manager"].attach_invocation(context["provenance"], effect.effect_permit, None, ATTACH_AT)
        self.assertEqual(result.code, ExecutionLeaseCode.INVOCATION_INVALID)

    def test_empty_invocation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            effect = context["manager"].authorize_effect(context["provenance"], context["created"].record.lease_id, context["holder"], context["target"], EFFECT_AT)
            result = context["manager"].attach_invocation(context["provenance"], effect.effect_permit, "", ATTACH_AT)
        self.assertEqual(result.code, ExecutionLeaseCode.INVOCATION_INVALID)

    def test_unsealed_permit_cannot_attach(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            result = context["manager"].attach_invocation(context["provenance"], object(), "invocation.e46.one", ATTACH_AT)
        self.assertEqual(result.code, ExecutionLeaseCode.BINDING_MISMATCH)

    def test_legacy_direct_attach_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            result = context["authority"].attach_invocation(context["provenance"], context["claim"].claim_id, context["holder"], "invocation.e46.one")
        self.assertEqual(result.code, DurableClaimResultCode.EFFECT_BLOCKED)

    def test_invocation_attach_updates_claim_and_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._attached(Path(directory))
            claim = context["authority"].read(context["provenance"]).record
        self.assertEqual(context["attached"].record.invocation_id, "invocation.e46.one")
        self.assertEqual(claim.invocation_id, "invocation.e46.one")

    def test_permit_replay_cannot_attach_second_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._attached(Path(directory))
            replay = context["manager"].attach_invocation(context["provenance"], context["effect"].effect_permit, "invocation.e46.two", ATTACH_AT)
        self.assertEqual(replay.code, ExecutionLeaseCode.BINDING_MISMATCH)

    def test_foreign_lease_permit_cannot_attach(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = self._context(root / "one")
            effect = first["manager"].authorize_effect(first["provenance"], first["created"].record.lease_id, first["holder"], first["target"], EFFECT_AT)
            second = self._context(root / "two", instance="owner.e46.other", correlation="corr.e46.other")
            result = second["manager"].attach_invocation(second["provenance"], effect.effect_permit, "invocation.e46.foreign", ATTACH_AT)
        self.assertEqual(result.code, ExecutionLeaseCode.BINDING_MISMATCH)

    def test_claim_bound_decision_rejects_null_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            with self.assertRaises(ValidationError):
                bind_challenge_decision(context["decision"], context["claim"], CAPABILITY_AT)

    def test_direct_identity_constructor_is_sealed(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._attached(Path(directory))
            capture = _synthetic_execution_transport(TRANSPORT, SOURCE).capture_identity(self._raw_identity(context), IDENTITY_CAPTURED_AT)
            with self.assertRaises(ValidationError):
                AttestedExecutionIdentity(context["attached"].record, capture, VERIFIER, IDENTITY_ATTESTED_AT)

    def test_raw_identity_cannot_be_attested_directly(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._attached(Path(directory))
            verifier = _execution_identity_verifier(VERIFIER, SOURCE)
            with self.assertRaises(ValidationError):
                verifier.attest_identity(context["attached"].record, self._raw_identity(context), IDENTITY_ATTESTED_AT)

    def test_cloned_identity_strings_cannot_construct_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._attached(Path(directory))
            raw = self._raw_identity(context)
            with self.assertRaises(ValidationError):
                TransportCapturedIdentity(raw, SOURCE, IDENTITY_CAPTURED_AT)

    def test_wrong_identity_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._attached(Path(directory))
            capture = _synthetic_execution_transport(TRANSPORT, "source.e46.other").capture_identity(self._raw_identity(context), IDENTITY_CAPTURED_AT)
            with self.assertRaises(ValidationError):
                _execution_identity_verifier(VERIFIER, SOURCE).attest_identity(context["attached"].record, capture, IDENTITY_ATTESTED_AT)

    def test_wrong_identity_transport_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._attached(Path(directory))
            raw = replace(self._raw_identity(context), transport_id="transport.e46.other")
            capture = _synthetic_execution_transport("transport.e46.other", SOURCE).capture_identity(raw, IDENTITY_CAPTURED_AT)
            with self.assertRaises(ValidationError):
                _execution_identity_verifier(VERIFIER, SOURCE).attest_identity(context["attached"].record, capture, IDENTITY_ATTESTED_AT)

    def test_manual_identity_is_verifier_minted(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
        self.assertEqual(context["identity"].kind, ExecutionIdentityKind.MANUAL_APP)

    def test_automation_identity_is_verifier_minted(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory), owner_type=OwnerType.APP_AUTOMATION_NEW_RUN, instance="owner.e46.auto", correlation="corr.e46.auto")
        self.assertEqual(context["identity"].kind, ExecutionIdentityKind.AUTOMATION)

    def test_cli_identity_is_verifier_minted(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory), owner_type=OwnerType.CODEX_CLI_PROCESS, target=CapabilityTarget.CODEX_CLI, instance="owner.e46.cli", correlation="corr.e46.cli")
        self.assertEqual(context["identity"].kind, ExecutionIdentityKind.CLI)

    def test_non_cli_terminal_cannot_claim_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._attached(Path(directory))
            transport = _synthetic_execution_transport(TRANSPORT, SOURCE)
            verifier = _execution_identity_verifier(VERIFIER, SOURCE)
            identity = verifier.attest_identity(context["attached"].record, transport.capture_identity(self._raw_identity(context), IDENTITY_CAPTURED_AT), IDENTITY_ATTESTED_AT)
            raw = RawTerminalObservation(context["attached"].record.lease_id, context["claim"].claim_id, "invocation.e46.one", identity.identity_digest, "completed", "done", TERMINAL_AT, HASH, HASH, TRANSPORT, 0)
            with self.assertRaises(ValidationError):
                verifier.attest_terminal(context["attached"].record, identity, transport.capture_terminal(raw, TERMINAL_CAPTURED_AT), TERMINAL_VERIFIED_AT)

    def test_cli_success_requires_zero_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._attached(Path(directory), owner_type=OwnerType.CODEX_CLI_PROCESS, target=CapabilityTarget.CODEX_CLI, instance="owner.e46.cli", correlation="corr.e46.cli")
            transport = _synthetic_execution_transport(TRANSPORT, SOURCE)
            verifier = _execution_identity_verifier(VERIFIER, SOURCE)
            identity = verifier.attest_identity(context["attached"].record, transport.capture_identity(self._raw_identity(context), IDENTITY_CAPTURED_AT), IDENTITY_ATTESTED_AT)
            raw = RawTerminalObservation(context["attached"].record.lease_id, context["claim"].claim_id, "invocation.e46.one", identity.identity_digest, "completed", "done", TERMINAL_AT, HASH, HASH, TRANSPORT, 1)
            with self.assertRaises(ValidationError):
                verifier.attest_terminal(context["attached"].record, identity, transport.capture_terminal(raw, TERMINAL_CAPTURED_AT), TERMINAL_VERIFIED_AT)

    def test_raw_terminal_cannot_advance_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._attached(Path(directory))
            result = context["manager"].attest_terminal(context["provenance"], object(), TERMINAL_ATTESTED_AT)
        self.assertEqual(result.code, ExecutionLeaseCode.TERMINAL_EVIDENCE_REQUIRED)

    def test_process_local_old_attestor_cross_instance_replay_has_no_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._attached(Path(directory))
            challenge = _one_shot_challenge("challenge.e46.legacy", CapabilityTarget.CODEX_APP, context["holder"], TASK, 44, CANARY, NONCE, "2026-08-02T12:04:00Z", "2026-08-02T12:10:00Z", 60)
            raw = RawInvocationTransportObservation("challenge.e46.legacy", CapabilityTarget.CODEX_APP, context["claim"].claim_id, "invocation.e46.one", context["holder"], ExecutionEvidenceType.CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION, TASK, 44, CANARY, NONCE, ATTACH_AT, TERMINAL_AT, "completed", None, HASH, "transport.e46.legacy")
            first = _bounded_transport_attestor("transport.e46.legacy").attest(challenge, raw, TERMINAL_CAPTURED_AT)
            replayed_by_new_instance = _bounded_transport_attestor("transport.e46.legacy").attest(challenge, raw, TERMINAL_CAPTURED_AT)
            first_result = context["manager"].attest_terminal(context["provenance"], first, TERMINAL_ATTESTED_AT)
            second_result = context["manager"].attest_terminal(context["provenance"], replayed_by_new_instance, TERMINAL_ATTESTED_AT)
        self.assertEqual(first_result.code, ExecutionLeaseCode.TERMINAL_EVIDENCE_REQUIRED)
        self.assertEqual(second_result.code, ExecutionLeaseCode.TERMINAL_EVIDENCE_REQUIRED)

    def test_terminal_evidence_cannot_cross_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = self._terminal(root / "one")
            second = self._attached(root / "two", instance="owner.e46.other", correlation="corr.e46.other")
            result = second["manager"].attest_terminal(second["provenance"], first["evidence"], TERMINAL_ATTESTED_AT)
        self.assertEqual(result.code, ExecutionLeaseCode.BINDING_MISMATCH)

    def test_terminal_attestation_is_one_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
            replay = context["manager"].attest_terminal(context["provenance"], context["evidence"], TERMINAL_ATTESTED_AT)
        self.assertEqual(context["terminal_attested"].record.state, ExecutionLeaseState.TERMINAL_ATTESTED)
        self.assertEqual(replay.code, ExecutionLeaseCode.BINDING_MISMATCH)

    def test_direct_terminal_evidence_constructor_is_sealed(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._attached(Path(directory))
            transport = _synthetic_execution_transport(TRANSPORT, SOURCE)
            verifier = _execution_identity_verifier(VERIFIER, SOURCE)
            identity = verifier.attest_identity(context["attached"].record, transport.capture_identity(self._raw_identity(context), IDENTITY_CAPTURED_AT), IDENTITY_ATTESTED_AT)
            raw = RawTerminalObservation(context["attached"].record.lease_id, context["claim"].claim_id, "invocation.e46.one", identity.identity_digest, "completed", "done", TERMINAL_AT, HASH, HASH, TRANSPORT)
            capture = transport.capture_terminal(raw, TERMINAL_CAPTURED_AT)
            with self.assertRaises(ValidationError):
                AttestedTerminalEvidence(context["attached"].record, identity, capture, TERMINAL_VERIFIED_AT)

    def test_direct_terminal_authorization_constructor_is_sealed(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
            with self.assertRaises(ValidationError):
                TerminalMutationAuthorization(context["terminal_attested"].record, context["evidence"])

    def test_attested_authorization_cannot_bypass_operation_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
            result = context["authority"].finalize_with_attested_terminal(context["provenance"], context["terminal_attested"].terminal_authorization)
        self.assertEqual(result.code, DurableClaimResultCode.EFFECT_BLOCKED)

    def test_journaled_terminal_mutation_permit_constructor_is_sealed(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
            authorization = context["terminal_attested"].terminal_authorization
            journal = context["manager"]._journal.begin(authorization, COMMITTED_AT)
            with self.assertRaises(ValidationError):
                JournaledTerminalMutationPermit(authorization, journal, COMMITTED_AT)

    def test_legacy_owner_terminal_validator_is_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
            claim = context["authority"].read(context["provenance"]).record
            old = ManualAppTerminalEvidence(claim.claim_id, claim.invocation_id, claim.holder, CapabilityTarget.CODEX_APP, "completed", TERMINAL_AT, "session.e46", HASH, HASH, HASH, claim.holder.owner_instance_id, claim.holder.claimant_correlation_id, TRANSPORT)
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(claim, object(), old)

    def test_terminal_validator_accepts_only_current_lease_and_attested_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
            claim = context["authority"].read(context["provenance"]).record
            accepted = validate_owner_terminal_evidence(claim, context["attached"].record, context["evidence"])
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(claim, context["decision"], context["evidence"])
        self.assertIs(accepted, context["evidence"])

    def test_legacy_direct_finalize_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
            result = context["authority"].finalize(context["provenance"], context["claim"].claim_id, context["holder"], DurableClaimState.SUCCEEDED, "done", TERMINAL_AT, invocation_id="invocation.e46.one")
        self.assertEqual(result.code, DurableClaimResultCode.EFFECT_BLOCKED)

    def test_terminal_authorization_cannot_cross_owner_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = self._terminal(root / "one")
            second = self._terminal(root / "two", instance="owner.e46.other", correlation="corr.e46.other")
            result = second["manager"].finalize_with_attested_terminal(second["provenance"], first["terminal_attested"].terminal_authorization, COMMITTED_AT)
        self.assertEqual(result.code, ExecutionLeaseCode.BINDING_MISMATCH)

    def test_full_terminal_commit_returns_bound_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
            result = context["manager"].finalize_with_attested_terminal(context["provenance"], context["terminal_attested"].terminal_authorization, COMMITTED_AT)
            claim = context["authority"].read(context["provenance"]).record
        self.assertEqual(result.code, ExecutionLeaseCode.TERMINAL_COMMITTED)
        self.assertEqual(result.record.state, ExecutionLeaseState.TERMINAL_COMMITTED)
        self.assertEqual(result.terminal_receipt.claim_id, claim.claim_id)
        self.assertEqual(claim.state, DurableClaimState.SUCCEEDED)

    def test_committed_receipt_is_idempotently_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
            first = context["manager"].finalize_with_attested_terminal(context["provenance"], context["terminal_attested"].terminal_authorization, COMMITTED_AT)
            second = context["manager"].reconcile_terminal(context["provenance"], context["terminal_attested"].terminal_authorization, "2026-08-02T12:04:14Z")
        self.assertEqual(first.terminal_receipt.receipt_digest, second.terminal_receipt.receipt_digest)
        self.assertEqual(second.code, ExecutionLeaseCode.ALREADY_COMMITTED)

    def test_post_apply_response_loss_reconciles_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            loss_gateway = PostApplyResponseLossGateway(SyntheticFileCasGateway(root / "claim"))
            context = self._terminal(root, claim_gateway=loss_gateway)
            writes_before = loss_gateway.applied_writes
            loss_gateway.loss_object_fragment = ".claim."
            loss_gateway.lose_next_applied_response = True
            ambiguous = context["manager"].finalize_with_attested_terminal(context["provenance"], context["terminal_attested"].terminal_authorization, COMMITTED_AT)
            self.assertEqual(ambiguous.code, ExecutionLeaseCode.RECONCILIATION_REQUIRED)
            restarted_authority = DurableClaimAuthority("vxz2datoubo/second-brain-coordination", "e42.claim", loss_gateway)
            restarted = DurableExecutionLeaseAuthority("lease.e46", context["lease_gateway"], restarted_authority)
            recovered = restarted.reconcile_terminal(context["provenance"], context["terminal_attested"].terminal_authorization, "2026-08-02T12:04:14Z")
            writes_after = loss_gateway.applied_writes
            repeated = restarted.reconcile_terminal(context["provenance"], context["terminal_attested"].terminal_authorization, "2026-08-02T12:04:15Z")
        self.assertEqual(recovered.code, ExecutionLeaseCode.TERMINAL_COMMITTED)
        self.assertEqual(repeated.code, ExecutionLeaseCode.ALREADY_COMMITTED)
        self.assertEqual(writes_after - writes_before, 1)
        self.assertEqual(loss_gateway.applied_writes, writes_after)

    def test_post_apply_lease_commit_response_loss_reconciles_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lease_gateway = PostApplyResponseLossGateway(SyntheticFileCasGateway(root / "lease"))
            context = self._terminal(root, lease_gateway=lease_gateway)
            lease_gateway.loss_object_fragment = ".lease."
            lease_gateway.lose_next_applied_response = True
            ambiguous = context["manager"].finalize_with_attested_terminal(context["provenance"], context["terminal_attested"].terminal_authorization, COMMITTED_AT)
            self.assertEqual(ambiguous.code, ExecutionLeaseCode.RECONCILIATION_REQUIRED)
            restarted = DurableExecutionLeaseAuthority("lease.e46", lease_gateway, context["authority"])
            recovered = restarted.reconcile_terminal(context["provenance"], context["terminal_attested"].terminal_authorization, "2026-08-02T12:04:14Z")
            operation_id = context["manager"]._journal.begin(context["terminal_attested"].terminal_authorization, COMMITTED_AT).operation_id
            journal = restarted._journal.read(operation_id)
        self.assertEqual(recovered.code, ExecutionLeaseCode.ALREADY_COMMITTED)
        self.assertEqual(journal.phase, OperationPhase.TERMINAL_COMMITTED)

    def test_reconciliation_distinguishes_not_applied(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
            authorization = context["terminal_attested"].terminal_authorization
            journal = context["manager"]._journal.begin(authorization, COMMITTED_AT)
            journal = context["manager"]._journal.advance(journal.operation_id, OperationPhase.RESPONSE_LOST_UNKNOWN, COMMITTED_AT, "synthetic_unknown")
            context["manager"]._journal.advance(journal.operation_id, OperationPhase.RECONCILIATION_REQUIRED, COMMITTED_AT, "synthetic_reconcile")
            result = context["manager"].reconcile_terminal(context["provenance"], authorization, "2026-08-02T12:04:14Z")
        self.assertEqual(result.code, ExecutionLeaseCode.CLAIM_NOT_APPLIED)

    def test_operation_journal_rejects_illegal_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
            authorization = context["terminal_attested"].terminal_authorization
            journal = context["manager"]._journal.begin(authorization, COMMITTED_AT)
            with self.assertRaises(ValidationError):
                context["manager"]._journal.advance(journal.operation_id, OperationPhase.RECONCILED, COMMITTED_AT, "skip_required_states")

    def test_operation_journal_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(Path(directory))
            authorization = context["terminal_attested"].terminal_authorization
            journal = context["manager"]._journal.begin(authorization, COMMITTED_AT)
            object_id = context["manager"]._journal._object_id(journal.operation_id)
            snapshot = context["lease_gateway"].read(object_id)
            value = json.loads(snapshot.payload.decode("utf-8"))
            value["events"][0]["detail_hash"] = "b" * 64
            payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.assertTrue(context["lease_gateway"].compare_and_set(object_id, snapshot.revision, payload).applied)
            with self.assertRaises(ValidationError):
                context["manager"]._journal.read(journal.operation_id)

    def test_lease_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            record = context["created"].record
            object_id = context["manager"]._object_id(record.storage_id)
            snapshot = context["lease_gateway"].read(object_id)
            value = json.loads(snapshot.payload.decode("utf-8"))
            value["holder"]["owner_instance_id"] = "owner.e46.tampered"
            payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.assertTrue(context["lease_gateway"].compare_and_set(object_id, snapshot.revision, payload).applied)
            result = context["manager"].read(context["provenance"], record.lease_id)
        self.assertEqual(result.code, ExecutionLeaseCode.TAMPERED)

    def test_cross_provenance_substitution_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._context(Path(directory))
            substituted = _provenance(snapshot=_route_snapshot(commit_sha1="9" * 40, tree_sha1="8" * 40))
            result = context["manager"].read(substituted, context["created"].record.lease_id)
        self.assertEqual(result.code, ExecutionLeaseCode.TAMPERED)


if __name__ == "__main__":
    unittest.main()
