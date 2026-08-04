"""Failing-first integration tests for the mandatory E46 authority path.

These tests deliberately describe the E48 requirement before its implementation:
an expiry boundary must fail closed even for terminal recovery, including a
response-loss restart.  They exercise the actual durable claim and lease
authorities, not a parallel model.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_ROOT / "src"))
sys.path.insert(0, str(TEST_ROOT))

from test_e46_execution_lease import (  # noqa: E402
    COMMITTED_AT,
    E46ExecutionLeaseTests,
    PostApplyResponseLossGateway,
)
from brainops_control_plane.durable_authority import (  # noqa: E402
    DurableClaimAuthority,
    SyntheticFileCasGateway,
)
from brainops_control_plane.execution_lease import (  # noqa: E402
    DurableExecutionLeaseAuthority,
    ExecutionLeaseCode,
)


class E48PreIntegrationFailures(E46ExecutionLeaseTests):
    def test_terminal_commit_at_expiry_fails_closed_without_claim_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._terminal(
                Path(directory),
                challenge_expires=COMMITTED_AT,
            )
            result = context["manager"].finalize_with_attested_terminal(
                context["provenance"],
                context["terminal_attested"].terminal_authorization,
                COMMITTED_AT,
            )
            claim = context["authority"].read(context["provenance"]).record

        self.assertEqual(result.code, ExecutionLeaseCode.LEASE_EXPIRED)
        self.assertFalse(claim.state.terminal)

    def test_response_loss_recovery_after_expiry_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim_gateway = PostApplyResponseLossGateway(
                SyntheticFileCasGateway(root / "claim")
            )
            context = self._terminal(
                root,
                claim_gateway=claim_gateway,
                challenge_expires="2026-08-02T12:04:15Z",
            )
            claim_gateway.loss_object_fragment = ".claim."
            claim_gateway.lose_next_applied_response = True
            ambiguous = context["manager"].finalize_with_attested_terminal(
                context["provenance"],
                context["terminal_attested"].terminal_authorization,
                COMMITTED_AT,
            )
            restarted_claim_authority = DurableClaimAuthority(
                "vxz2datoubo/second-brain-coordination",
                "e42.claim",
                claim_gateway,
            )
            restarted = DurableExecutionLeaseAuthority(
                "lease.e46",
                context["lease_gateway"],
                restarted_claim_authority,
            )
            recovered = restarted.reconcile_terminal(
                context["provenance"],
                context["terminal_attested"].terminal_authorization,
                "2026-08-02T12:04:15Z",
            )
            claim = restarted_claim_authority.read(context["provenance"]).record

        self.assertEqual(ambiguous.code, ExecutionLeaseCode.RECONCILIATION_REQUIRED)
        self.assertEqual(recovered.code, ExecutionLeaseCode.LEASE_EXPIRED)
        self.assertFalse(claim.state.terminal)
