"""E47 red-to-green tests for restart-safe lifecycle transitions."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.durable_authority import (  # noqa: E402
    ClaimHolder,
    OwnerType,
    SyntheticFileCasGateway,
)
from brainops_control_plane.execution_evidence import CapabilityTarget  # noqa: E402
from brainops_control_plane.recoverable_lifecycle import (  # noqa: E402
    JournalPhase,
    LifecycleJournal,
    LifecycleBinding,
    LifecycleCode,
    LifecycleStage,
    RecoverableLifecycleAuthority,
    TerminalEvidence,
)
from brainops_control_plane.models import ValidationError  # noqa: E402


class PostApplyResponseLossGateway:
    """Persist a CAS first, then simulate the caller losing its response."""

    def __init__(self, backing: SyntheticFileCasGateway) -> None:
        self.backing = backing
        self.lose_next_applied_response = False
        self.loss_after_applied_write: int | None = None
        self.applied_writes: Counter[str] = Counter()

    def read(self, object_id: str):  # type: ignore[no-untyped-def]
        return self.backing.read(object_id)

    def compare_and_set(self, object_id, expected_revision, payload):  # type: ignore[no-untyped-def]
        result = self.backing.compare_and_set(object_id, expected_revision, payload)
        if result.applied:
            self.applied_writes[object_id] += 1
        applied_total = sum(self.applied_writes.values())
        if result.applied and (
            self.lose_next_applied_response
            or self.loss_after_applied_write == applied_total
        ):
            self.lose_next_applied_response = False
            self.loss_after_applied_write = None
            raise OSError("synthetic post-apply response loss")
        return result


def _binding() -> LifecycleBinding:
    return LifecycleBinding(
        lease_id="a" * 64,
        claim_id="claim.e47.one",
        provenance_digest="b" * 64,
        storage_id="c" * 64,
        holder=ClaimHolder(OwnerType.CURRENT_CODEX_APP_SESSION, "owner.e47.one", "correlation.e47.one"),
        target=CapabilityTarget.CODEX_APP,
        task_id="task.e47.one",
        route_epoch=49,
        canary_id="canary.e47.none",
        nonce="nonce.e47.one",
        expires_at="2026-08-04T03:30:00Z",
    )


def _authority(root: Path, *, lease_gateway=None, claim_gateway=None, journal_gateway=None) -> RecoverableLifecycleAuthority:
    return RecoverableLifecycleAuthority(
        "e47.lifecycle",
        lease_gateway or SyntheticFileCasGateway(root / "lease"),
        claim_gateway or SyntheticFileCasGateway(root / "claim"),
        journal_gateway or SyntheticFileCasGateway(root / "journal"),
    )


class E47RecoverableLifecycleTests(unittest.TestCase):
    def _started(self, root: Path, **gateways):
        authority = _authority(root, **gateways)
        binding = _binding()
        created = authority.attest_capability(binding, "2026-08-04T03:00:00Z")
        self.assertEqual(created.code, LifecycleCode.CAPABILITY_ATTESTED)
        return authority, binding

    @staticmethod
    def _evidence() -> TerminalEvidence:
        return TerminalEvidence("evidence.e47.one", "completed", "synthetic_terminal", "2026-08-04T03:03:00Z")

    def _at_invocation(self, root: Path, **gateways):
        authority, binding = self._started(root, **gateways)
        self.assertEqual(authority.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:00Z").code, LifecycleCode.EFFECT_AUTHORIZED)
        self.assertEqual(authority.attach_invocation(binding, "invocation.e47.one", "2026-08-04T03:02:00Z").code, LifecycleCode.INVOCATION_ATTACHED)
        return authority, binding

    def _at_terminal(self, root: Path, **gateways):
        authority, binding = self._at_invocation(root, **gateways)
        self.assertEqual(authority.attest_terminal(binding, self._evidence(), "2026-08-04T03:03:01Z").code, LifecycleCode.TERMINAL_ATTESTED)
        return authority, binding

    def test_effect_response_loss_recovers_identical_request_without_second_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backing = SyntheticFileCasGateway(root / "lease")
            loss = PostApplyResponseLossGateway(backing)
            authority, binding = self._started(root, lease_gateway=loss)
            writes_before = sum(loss.applied_writes.values())
            loss.lose_next_applied_response = True
            lost = authority.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:00Z")
            self.assertEqual(lost.code, LifecycleCode.RESPONSE_LOST)
            writes_after_loss = sum(loss.applied_writes.values())

            restarted = _authority(root, lease_gateway=backing)
            recovered = restarted.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:01Z")
            mismatched = restarted.authorize_effect(binding, "effect.e47.two", "2026-08-04T03:01:02Z")

        self.assertEqual(recovered.code, LifecycleCode.ALREADY_EFFECT_AUTHORIZED)
        self.assertEqual(mismatched.code, LifecycleCode.BINDING_MISMATCH)
        self.assertEqual(writes_after_loss, writes_before + 1)
        self.assertEqual(sum(loss.applied_writes.values()), writes_after_loss)

    def test_journal_response_loss_after_effect_mutation_recovers_from_durable_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            journal_backing = SyntheticFileCasGateway(root / "journal")
            journal_loss = PostApplyResponseLossGateway(journal_backing)
            authority, binding = self._started(root, journal_gateway=journal_loss)
            # First journal write is REQUESTED; the second is LEASE_APPLIED.
            journal_loss.loss_after_applied_write = 2
            lost = authority.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:00Z")
            restarted = _authority(root, journal_gateway=journal_backing)
            recovered = restarted.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:01Z")

        self.assertEqual(lost.code, LifecycleCode.RESPONSE_LOST)
        self.assertEqual(recovered.code, LifecycleCode.ALREADY_EFFECT_AUTHORIZED)

    def test_terminal_attestation_response_loss_recovers_evidence_without_second_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backing = SyntheticFileCasGateway(root / "lease")
            loss = PostApplyResponseLossGateway(backing)
            authority, binding = self._started(root, lease_gateway=loss)
            self.assertEqual(authority.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:00Z").code, LifecycleCode.EFFECT_AUTHORIZED)
            self.assertEqual(authority.attach_invocation(binding, "invocation.e47.one", "2026-08-04T03:02:00Z").code, LifecycleCode.INVOCATION_ATTACHED)
            writes_before = sum(loss.applied_writes.values())
            loss.lose_next_applied_response = True
            evidence = TerminalEvidence("evidence.e47.one", "completed", "synthetic_terminal", "2026-08-04T03:03:00Z")
            lost = authority.attest_terminal(binding, evidence, "2026-08-04T03:03:01Z")
            self.assertEqual(lost.code, LifecycleCode.RESPONSE_LOST)
            writes_after_loss = sum(loss.applied_writes.values())

            restarted = _authority(root, lease_gateway=backing)
            recovered = restarted.attest_terminal(binding, evidence, "2026-08-04T03:03:02Z")
            mismatched = restarted.attest_terminal(
                binding,
                TerminalEvidence("evidence.e47.two", "completed", "synthetic_terminal", "2026-08-04T03:03:00Z"),
                "2026-08-04T03:03:03Z",
            )

        self.assertEqual(recovered.code, LifecycleCode.ALREADY_TERMINAL_ATTESTED)
        self.assertEqual(mismatched.code, LifecycleCode.BINDING_MISMATCH)
        self.assertEqual(writes_after_loss, writes_before + 1)
        self.assertEqual(sum(loss.applied_writes.values()), writes_after_loss)

    def test_claim_invocation_response_loss_recovers_without_second_claim_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim_backing = SyntheticFileCasGateway(root / "claim")
            claim_loss = PostApplyResponseLossGateway(claim_backing)
            authority, binding = self._started(root, claim_gateway=claim_loss)
            self.assertEqual(authority.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:00Z").code, LifecycleCode.EFFECT_AUTHORIZED)
            writes_before = sum(claim_loss.applied_writes.values())
            claim_loss.lose_next_applied_response = True
            lost = authority.attach_invocation(binding, "invocation.e47.one", "2026-08-04T03:02:00Z")
            writes_after_loss = sum(claim_loss.applied_writes.values())

            restarted = _authority(root, claim_gateway=claim_backing)
            recovered = restarted.attach_invocation(binding, "invocation.e47.one", "2026-08-04T03:02:01Z")
            mismatched = restarted.attach_invocation(binding, "invocation.e47.two", "2026-08-04T03:02:02Z")

        self.assertEqual(lost.code, LifecycleCode.RESPONSE_LOST)
        self.assertEqual(recovered.code, LifecycleCode.INVOCATION_ATTACHED)
        self.assertEqual(mismatched.code, LifecycleCode.BINDING_MISMATCH)
        self.assertEqual(writes_after_loss, writes_before + 1)
        self.assertEqual(sum(claim_loss.applied_writes.values()), writes_after_loss)

    def test_lease_invocation_response_loss_recovers_only_missing_lease_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lease_backing = SyntheticFileCasGateway(root / "lease")
            lease_loss = PostApplyResponseLossGateway(lease_backing)
            authority, binding = self._started(root, lease_gateway=lease_loss)
            self.assertEqual(authority.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:00Z").code, LifecycleCode.EFFECT_AUTHORIZED)

            # Capability and effect consume two lease writes.  The claim-side
            # mirror is third, so the fourth write is the actual lease
            # invocation attachment whose response this test loses.
            lease_loss.loss_after_applied_write = 4
            first_loss = authority.attach_invocation(binding, "invocation.e47.one", "2026-08-04T03:02:00Z")
            restarted = _authority(root, lease_gateway=lease_backing)
            self.assertEqual(restarted.attach_invocation(binding, "invocation.e47.one", "2026-08-04T03:02:01Z").code, LifecycleCode.ALREADY_INVOCATION_ATTACHED)
            writes_before_second_loss = sum(lease_loss.applied_writes.values())

            # A repeated exact request reaches only the already-applied stage.
            exact_replay = restarted.attach_invocation(binding, "invocation.e47.one", "2026-08-04T03:02:02Z")

        self.assertEqual(first_loss.code, LifecycleCode.RESPONSE_LOST)
        self.assertEqual(exact_replay.code, LifecycleCode.ALREADY_INVOCATION_ATTACHED)
        self.assertEqual(sum(lease_loss.applied_writes.values()), writes_before_second_loss)

    def test_claim_terminal_response_loss_recovers_without_second_claim_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim_backing = SyntheticFileCasGateway(root / "claim")
            claim_loss = PostApplyResponseLossGateway(claim_backing)
            authority, binding = self._at_terminal(root, claim_gateway=claim_loss)
            writes_before = sum(claim_loss.applied_writes.values())
            claim_loss.lose_next_applied_response = True
            lost = authority.commit_terminal(binding, "terminal.commit.e47.one", "2026-08-04T03:04:00Z")
            writes_after_loss = sum(claim_loss.applied_writes.values())

            restarted = _authority(root, claim_gateway=claim_backing)
            recovered = restarted.commit_terminal(binding, "terminal.commit.e47.one", "2026-08-04T03:04:01Z")
            mismatched = restarted.commit_terminal(binding, "terminal.commit.e47.two", "2026-08-04T03:04:02Z")

        self.assertEqual(lost.code, LifecycleCode.RESPONSE_LOST)
        self.assertEqual(recovered.code, LifecycleCode.TERMINAL_COMMITTED)
        self.assertEqual(mismatched.code, LifecycleCode.BINDING_MISMATCH)
        self.assertEqual(writes_after_loss, writes_before + 1)
        self.assertEqual(sum(claim_loss.applied_writes.values()), writes_after_loss)

    def test_lease_terminal_response_loss_reconciles_without_repeating_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lease_backing = SyntheticFileCasGateway(root / "lease")
            lease_loss = PostApplyResponseLossGateway(lease_backing)
            authority, binding = self._at_terminal(root, lease_gateway=lease_loss)
            # Five lease writes have occurred by terminal attestation.  The
            # sixth is the claim-terminal mirror and the seventh is the actual
            # lease terminal commit whose response this test loses.
            lease_loss.loss_after_applied_write = 7
            first_loss = authority.commit_terminal(binding, "terminal.commit.e47.one", "2026-08-04T03:04:00Z")
            restarted = _authority(root, lease_gateway=lease_backing)
            recovered = restarted.commit_terminal(binding, "terminal.commit.e47.one", "2026-08-04T03:04:01Z")
            writes_after_recovery = sum(lease_loss.applied_writes.values())
            exact_replay = restarted.commit_terminal(binding, "terminal.commit.e47.one", "2026-08-04T03:04:02Z")

        self.assertEqual(first_loss.code, LifecycleCode.RESPONSE_LOST)
        self.assertEqual(recovered.code, LifecycleCode.ALREADY_TERMINAL_COMMITTED)
        self.assertEqual(exact_replay.code, LifecycleCode.ALREADY_TERMINAL_COMMITTED)
        self.assertEqual(sum(lease_loss.applied_writes.values()), writes_after_recovery)

    def test_full_lifecycle_has_all_durable_stages_and_journals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, binding = self._at_terminal(root)
            committed = authority.commit_terminal(binding, "terminal.commit.e47.one", "2026-08-04T03:04:00Z")
            read = authority.read(binding)
            journal_files = list((root / "journal").glob("*.json"))

        self.assertEqual(committed.code, LifecycleCode.TERMINAL_COMMITTED)
        self.assertEqual(read.record.state, LifecycleStage.LEASE_TERMINAL_COMMITTED)
        self.assertEqual([receipt.stage for receipt in read.record.receipts], list(LifecycleStage))
        self.assertEqual([receipt.purpose for receipt in read.record.receipts], [stage.purpose for stage in LifecycleStage])
        self.assertEqual(len(journal_files), 6)

    def test_illegal_stage_order_is_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            authority, binding = self._started(Path(directory))
            before = authority.read(binding).record
            result = authority.attest_terminal(binding, self._evidence(), "2026-08-04T03:03:01Z")
            after = authority.read(binding).record

        self.assertEqual(result.code, LifecycleCode.ILLEGAL_TRANSITION)
        self.assertEqual(before, after)

    def test_journal_rejects_phase_skip_repeat_and_reversal(self):
        binding = _binding()
        journal = LifecycleJournal.start(binding, LifecycleStage.EFFECT_AUTHORIZED, "d" * 64, "LEASE", "2026-08-04T03:01:00Z")
        with self.assertRaises(ValidationError):
            journal.advance(JournalPhase.COMPLETED, "2026-08-04T03:01:01Z", {"bad": "skip"})
        advanced = journal.advance(JournalPhase.LEASE_APPLIED, "2026-08-04T03:01:01Z", {"ok": "apply"})
        completed = advanced.advance(JournalPhase.COMPLETED, "2026-08-04T03:01:02Z", {"ok": "complete"})
        with self.assertRaises(ValidationError):
            completed.advance(JournalPhase.RECONCILED, "2026-08-04T03:01:03Z", {"bad": "reverse"})

    def test_tampered_journal_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, binding = self._started(root)
            self.assertEqual(authority.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:00Z").code, LifecycleCode.EFFECT_AUTHORIZED)
            journal_path = next((root / "journal").glob("*.json"))
            document = json.loads(journal_path.read_text(encoding="utf-8"))
            document["events"][0]["phase"] = "COMPLETED"
            journal_path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
            restarted = _authority(root)
            result = restarted.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:01Z")

        self.assertEqual(result.code, LifecycleCode.TAMPERED)

    def test_tampered_or_deleted_request_digest_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, binding = self._started(root)
            self.assertEqual(authority.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:00Z").code, LifecycleCode.EFFECT_AUTHORIZED)
            lease_path = next((root / "lease").glob("*.json"))
            document = json.loads(lease_path.read_text(encoding="utf-8"))
            del document["receipts"][1]["request_digest"]
            lease_path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
            restarted = _authority(root)
            result = restarted.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:01Z")

        self.assertEqual(result.code, LifecycleCode.TAMPERED)

    def test_cross_claim_route_holder_and_target_bindings_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, binding = self._started(root)
            self.assertEqual(authority.authorize_effect(binding, "effect.e47.one", "2026-08-04T03:01:00Z").code, LifecycleCode.EFFECT_AUTHORIZED)
            foreign_bindings = (
                replace(binding, claim_id="claim.e47.two"),
                replace(binding, route_epoch=50),
                replace(binding, holder=ClaimHolder(binding.holder.owner_type, "owner.e47.two", binding.holder.claimant_correlation_id)),
                replace(binding, target=CapabilityTarget.CODEX_CLI),
            )
            results = [authority.authorize_effect(foreign, "effect.e47.one", "2026-08-04T03:01:01Z") for foreign in foreign_bindings]
            original = authority.read(binding)

        self.assertEqual([result.code for result in results], [LifecycleCode.BINDING_MISMATCH] * 4)
        self.assertEqual(original.record.state, LifecycleStage.EFFECT_AUTHORIZED)

    def test_cross_terminal_evidence_replay_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            authority, binding = self._at_invocation(Path(directory))
            first = authority.attest_terminal(binding, self._evidence(), "2026-08-04T03:03:01Z")
            wrong = authority.attest_terminal(
                binding,
                TerminalEvidence("evidence.e47.two", "completed", "synthetic_terminal", "2026-08-04T03:03:00Z"),
                "2026-08-04T03:03:02Z",
            )

        self.assertEqual(first.code, LifecycleCode.TERMINAL_ATTESTED)
        self.assertEqual(wrong.code, LifecycleCode.BINDING_MISMATCH)


if __name__ == "__main__":
    unittest.main()
