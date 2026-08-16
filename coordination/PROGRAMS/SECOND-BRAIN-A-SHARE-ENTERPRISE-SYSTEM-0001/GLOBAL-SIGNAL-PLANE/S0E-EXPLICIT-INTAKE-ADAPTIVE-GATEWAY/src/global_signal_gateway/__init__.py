"""R136 public-safe explicit intake and governed execution gateway."""

from .gateway import (
    GatewayError,
    SignalIntakeGateway,
    SystemAwarenessProjection,
    RuntimeInvocationReceipt,
    ai_film_directing_read_only_smoke,
    route_domain_learning_handoff,
    exact_git_read_records,
)
from .domain_learning_handoff import DomainLearningHandoffPacket, DomainLearningReceipt, DomainLearningHandoffLedger, ai_film_domain_learning_read_only_smoke, verify_packet, verify_receipt, require_exact_domain_revision, route_packet, stage_a_receipt
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

__all__ = ["GatewayError", "SignalIntakeGateway", "SystemAwarenessProjection", "RuntimeInvocationReceipt", "exact_git_read_records", "ai_film_directing_read_only_smoke", "route_domain_learning_handoff", "DomainFreshnessTarget", "LiveObservationProvider", "LiveObservationRequest", "CapabilityExecutionRequest", "CapabilityExecutionEvidenceBundle", "CapabilityExecutionProof", "ExactRepositoryCapabilityProvider", "verify_capability_execution_proof", "verify_historical_capability_execution_proof", "DomainLearningHandoffPacket", "DomainLearningReceipt", "DomainLearningHandoffLedger", "ai_film_domain_learning_read_only_smoke", "verify_packet", "verify_receipt", "require_exact_domain_revision", "route_packet", "stage_a_receipt"]
