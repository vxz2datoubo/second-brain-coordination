"""E49 hard-process crash tests for the actual durable claim/lease authority."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_ROOT / "src"))
sys.path.insert(0, str(TEST_ROOT))

from test_e44_durable_challenge import _holder, _provenance  # noqa: E402
from test_e46_execution_lease import (  # noqa: E402
    ATTACH_AT,
    EFFECT_AT,
    E46ExecutionLeaseTests,
)
from brainops_control_plane.durable_authority import (  # noqa: E402
    DurableClaimKey,
    DurableClaimAuthority,
    OwnerType,
    SyntheticFileCasGateway,
)
from brainops_control_plane.execution_evidence import CapabilityTarget  # noqa: E402
from brainops_control_plane.execution_lease import (  # noqa: E402
    DurableExecutionLeaseAuthority,
    ExecutionLeaseCode,
    ExecutionLeaseState,
    LeaseStageOperationPhase,
    LeaseStageOperationPurpose,
)


_CHILD = r'''
import json
import os
from pathlib import Path
import sys

root = Path(sys.argv[1])
cut = sys.argv[2]
sys.path.insert(0, sys.argv[3])
sys.path.insert(0, sys.argv[4])
from test_e46_execution_lease import E46ExecutionLeaseTests, EFFECT_AT, ATTACH_AT

def crash_after(point):
    if point == cut:
        os._exit(86)

case = E46ExecutionLeaseTests()
context = case._context(root, lease_after_mutation_hook=crash_after)
(root / "crash-facts.json").write_text(json.dumps({"lease_id": context["created"].record.lease_id}), encoding="utf-8")
if cut.startswith("effect_"):
    case.assertEqual(context["manager"].authorize_effect(context["provenance"], context["created"].record.lease_id, context["holder"], context["target"], EFFECT_AT).code, "unreachable")
else:
    effect = context["manager"].authorize_effect(context["provenance"], context["created"].record.lease_id, context["holder"], context["target"], EFFECT_AT)
    case.assertEqual(effect.code.value, "EFFECT_AUTHORIZED")
    case.assertEqual(context["manager"].attach_invocation(context["provenance"], effect.effect_permit, "invocation.e46.one", ATTACH_AT).code, "unreachable")
raise SystemExit("fault hook did not terminate child")
'''


class E49HardCrashRecoveryTests(unittest.TestCase):
    def _crash_then_restart(self, cut: str):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                _CHILD,
                str(root),
                cut,
                str(PROGRAM_ROOT / "src"),
                str(TEST_ROOT),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        facts = json.loads((root / "crash-facts.json").read_text(encoding="utf-8"))
        provenance = _provenance()
        holder = _holder(OwnerType.CURRENT_CODEX_APP_SESSION, "owner.e46.one", "corr.e46.one")
        claim_gateway = SyntheticFileCasGateway(root / "claim")
        lease_gateway = SyntheticFileCasGateway(root / "lease")
        claim_authority = DurableClaimAuthority(
            "vxz2datoubo/second-brain-coordination", "e42.claim", claim_gateway
        )
        manager = DurableExecutionLeaseAuthority("lease.e46", lease_gateway, claim_authority)
        return directory, completed, facts["lease_id"], provenance, holder, claim_gateway, lease_gateway, manager

    def _journal(self, manager, record, purpose, at, invocation_id=None):
        return manager._begin_stage_operation(purpose, record, at, invocation_id)

    def test_hard_kill_after_effect_lease_cas_recovers_without_second_lease_write(self):
        directory, child, lease_id, provenance, holder, _claim_gateway, lease_gateway, manager = self._crash_then_restart(
            "effect_lease_cas_before_stage_journal"
        )
        try:
            before = manager.read(provenance, lease_id, checked_at=EFFECT_AT).record
            before_snapshot = lease_gateway.read(manager._object_id(before.storage_id))
            recovered = manager.authorize_effect(
                provenance, lease_id, holder, CapabilityTarget.CODEX_APP, EFFECT_AT
            )
            after_snapshot = lease_gateway.read(manager._object_id(before.storage_id))
            journal = self._journal(
                manager,
                recovered.record,
                LeaseStageOperationPurpose.EFFECT_AUTHORIZATION,
                EFFECT_AT,
            )
        finally:
            directory.cleanup()

        self.assertEqual(child.returncode, 86)
        self.assertEqual(recovered.code, ExecutionLeaseCode.EFFECT_AUTHORIZED)
        self.assertIsNotNone(recovered.effect_permit)
        self.assertEqual(after_snapshot.revision, before_snapshot.revision)
        self.assertEqual(journal.phase, LeaseStageOperationPhase.COMPLETED)

    def test_hard_kill_after_claim_invocation_cas_recovers_only_missing_phases(self):
        directory, child, lease_id, provenance, holder, claim_gateway, lease_gateway, manager = self._crash_then_restart(
            "claim_invocation_cas_before_stage_journal"
        )
        try:
            effect = manager.authorize_effect(
                provenance, lease_id, holder, CapabilityTarget.CODEX_APP, EFFECT_AT
            )
            claim_before = claim_gateway.read(
                manager._claim_authority._object_id(DurableClaimKey(provenance))
            )
            lease_before = manager.read(provenance, lease_id, checked_at=ATTACH_AT).record
            attached = manager.attach_invocation(
                provenance, effect.effect_permit, "invocation.e46.one", ATTACH_AT
            )
            claim_after = claim_gateway.read(
                manager._claim_authority._object_id(DurableClaimKey(provenance))
            )
            lease_after = manager.read(provenance, lease_id, checked_at=ATTACH_AT).record
            journal = self._journal(
                manager,
                lease_after,
                LeaseStageOperationPurpose.INVOCATION_ATTACHMENT,
                ATTACH_AT,
                "invocation.e46.one",
            )
        finally:
            directory.cleanup()

        self.assertEqual(child.returncode, 86)
        self.assertEqual(attached.code, ExecutionLeaseCode.INVOCATION_ATTACHED)
        self.assertEqual(claim_after.revision, claim_before.revision)
        self.assertNotEqual(lease_after.version, lease_before.version)
        self.assertEqual(journal.phase, LeaseStageOperationPhase.COMPLETED)

    def test_hard_kill_after_invocation_lease_cas_recovers_journal_without_second_mutation(self):
        directory, child, lease_id, provenance, holder, claim_gateway, lease_gateway, manager = self._crash_then_restart(
            "invocation_lease_cas_before_stage_journal"
        )
        try:
            effect = manager.authorize_effect(
                provenance, lease_id, holder, CapabilityTarget.CODEX_APP, EFFECT_AT
            )
            self.assertEqual(effect.code, ExecutionLeaseCode.INVOCATION_ATTACHED)
            claim_before = claim_gateway.read(
                manager._claim_authority._object_id(DurableClaimKey(provenance))
            )
            lease_before = manager.read(provenance, lease_id, checked_at=ATTACH_AT).record
            attached = manager.attach_invocation(
                provenance, effect.effect_permit, "invocation.e46.one", ATTACH_AT
            )
            claim_after = claim_gateway.read(
                manager._claim_authority._object_id(DurableClaimKey(provenance))
            )
            lease_after = manager.read(provenance, lease_id, checked_at=ATTACH_AT).record
            journal = self._journal(
                manager,
                lease_after,
                LeaseStageOperationPurpose.INVOCATION_ATTACHMENT,
                ATTACH_AT,
                "invocation.e46.one",
            )
        finally:
            directory.cleanup()

        self.assertEqual(child.returncode, 86)
        self.assertEqual(attached.code, ExecutionLeaseCode.INVOCATION_ATTACHED)
        self.assertEqual(claim_after.revision, claim_before.revision)
        self.assertEqual(lease_after.version, lease_before.version)
        self.assertEqual(lease_after.state, ExecutionLeaseState.INVOCATION_ATTACHED)
        self.assertEqual(journal.phase, LeaseStageOperationPhase.COMPLETED)

    def test_hard_kill_after_journal_lease_phase_completes_without_second_mutation(self):
        directory, child, lease_id, provenance, holder, claim_gateway, lease_gateway, manager = self._crash_then_restart(
            "invocation_stage_journal_lease_mutation_before_complete"
        )
        try:
            effect = manager.authorize_effect(
                provenance, lease_id, holder, CapabilityTarget.CODEX_APP, EFFECT_AT
            )
            self.assertEqual(effect.code, ExecutionLeaseCode.INVOCATION_ATTACHED)
            claim_before = claim_gateway.read(
                manager._claim_authority._object_id(DurableClaimKey(provenance))
            )
            lease_before = manager.read(provenance, lease_id, checked_at=ATTACH_AT).record
            attached = manager.attach_invocation(
                provenance, effect.effect_permit, "invocation.e46.one", ATTACH_AT
            )
            claim_after = claim_gateway.read(
                manager._claim_authority._object_id(DurableClaimKey(provenance))
            )
            lease_after = manager.read(provenance, lease_id, checked_at=ATTACH_AT).record
            journal = self._journal(
                manager,
                lease_after,
                LeaseStageOperationPurpose.INVOCATION_ATTACHMENT,
                ATTACH_AT,
                "invocation.e46.one",
            )
        finally:
            directory.cleanup()

        self.assertEqual(child.returncode, 86)
        self.assertEqual(attached.code, ExecutionLeaseCode.INVOCATION_ATTACHED)
        self.assertEqual(claim_after.revision, claim_before.revision)
        self.assertEqual(lease_after.version, lease_before.version)
        self.assertEqual(journal.phase, LeaseStageOperationPhase.COMPLETED)

    def test_changed_effect_time_after_hard_crash_fails_closed_before_new_journal(self):
        directory, child, lease_id, provenance, holder, _claim_gateway, lease_gateway, manager = self._crash_then_restart(
            "effect_lease_cas_before_stage_journal"
        )
        try:
            before = manager.read(provenance, lease_id, checked_at=EFFECT_AT).record
            before_snapshot = lease_gateway.read(manager._object_id(before.storage_id))
            changed = manager.authorize_effect(
                provenance,
                lease_id,
                holder,
                CapabilityTarget.CODEX_APP,
                "2026-08-02T12:05:01Z",
            )
            after_snapshot = lease_gateway.read(manager._object_id(before.storage_id))
            original_journal = self._journal(
                manager,
                before,
                LeaseStageOperationPurpose.EFFECT_AUTHORIZATION,
                EFFECT_AT,
            )
        finally:
            directory.cleanup()

        self.assertEqual(child.returncode, 86)
        self.assertEqual(changed.code, ExecutionLeaseCode.BINDING_MISMATCH)
        self.assertEqual(after_snapshot.revision, before_snapshot.revision)
        self.assertEqual(original_journal.phase, LeaseStageOperationPhase.BINDINGS_VERIFIED)
