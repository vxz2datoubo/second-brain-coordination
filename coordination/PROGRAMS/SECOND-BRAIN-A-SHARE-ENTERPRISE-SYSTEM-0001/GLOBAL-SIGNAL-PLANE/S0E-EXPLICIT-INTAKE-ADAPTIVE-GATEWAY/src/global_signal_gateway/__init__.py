"""R136 public-safe explicit intake and governed execution gateway."""

from .gateway import (
    GatewayError,
    SignalIntakeGateway,
    SystemAwarenessProjection,
    RuntimeInvocationReceipt,
    ai_film_directing_read_only_smoke,
    exact_git_read_records,
)
from .live_observation_provider import (
    DomainFreshnessTarget,
    LiveObservationProvider,
    LiveObservationRequest,
)
from .capability_execution_provider import (
    CapabilityExecutionRequest,
    CapabilityExecutionEvidenceBundle,
    CapabilityExecutionProof,
    ExactRepositoryCapabilityProvider,
    verify_capability_execution_proof,
    verify_historical_capability_execution_proof,
)

__all__ = ["GatewayError", "SignalIntakeGateway", "SystemAwarenessProjection", "RuntimeInvocationReceipt", "exact_git_read_records", "ai_film_directing_read_only_smoke", "DomainFreshnessTarget", "LiveObservationProvider", "LiveObservationRequest", "CapabilityExecutionRequest", "CapabilityExecutionEvidenceBundle", "CapabilityExecutionProof", "ExactRepositoryCapabilityProvider", "verify_capability_execution_proof", "verify_historical_capability_execution_proof"]
