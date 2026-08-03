"""E43 trusted durable-authority and terminal-attestation contracts."""

from .durable_authority import (
    AuthorityProvenanceVerifier,
    ClaimHolder,
    DurableClaimAuthority,
    DurableClaimState,
    OwnerType,
    VerifiedAuthorityProvenance,
)
from .execution_evidence import ExecutionEvidenceType, RawInvocationReceipt, VerifiedInvocationReceipt
from .github_contents_cas import FixedGitHubContentsCasClient
from .models import ValidationError
from .terminal_attestation import (
    AttestationCode,
    InvocationLifecycleState,
    TerminalExecutionReconciler,
)
from .durable_challenge import (
    CapabilityWitness,
    DurableChallenge,
    DurableChallengeLedger,
    RecoveryAuthorizationLedger,
    evaluate_challenge_capability,
    validate_owner_terminal_evidence,
)

__all__ = [
    "AuthorityProvenanceVerifier",
    "AttestationCode",
    "ClaimHolder",
    "DurableClaimAuthority",
    "DurableClaimState",
    "ExecutionEvidenceType",
    "FixedGitHubContentsCasClient",
    "InvocationLifecycleState",
    "OwnerType",
    "RawInvocationReceipt",
    "TerminalExecutionReconciler",
    "CapabilityWitness",
    "DurableChallenge",
    "DurableChallengeLedger",
    "RecoveryAuthorizationLedger",
    "evaluate_challenge_capability",
    "validate_owner_terminal_evidence",
    "ValidationError",
    "VerifiedAuthorityProvenance",
    "VerifiedInvocationReceipt",
]
