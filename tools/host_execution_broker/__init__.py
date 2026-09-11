"""Synthetic Host Execution Broker R1 candidate for Issue #310."""

from .broker import BrokerError, FencingError, HostExecutionBroker, ProcessOwnershipError
from .models import (
    AdmissionDecision, AuthorityState, DecisionOutcome, EpisodeBudgetDecision,
    EpisodeBudgetOutcome, ExecutionRequest, LeaseBinding, ProcessStartReceipt,
    ProgressObservation, ProgressState, ResourceClaim, ResourceMode, ResourceType,
    TransportState, WorkerIdentity,
)

__all__ = [
    "AdmissionDecision", "AuthorityState", "BrokerError", "DecisionOutcome",
    "EpisodeBudgetDecision", "EpisodeBudgetOutcome", "ExecutionRequest",
    "FencingError", "HostExecutionBroker", "LeaseBinding", "ProcessOwnershipError",
    "ProcessStartReceipt", "ProgressObservation", "ProgressState", "ResourceClaim",
    "ResourceMode", "ResourceType", "TransportState", "WorkerIdentity",
]
