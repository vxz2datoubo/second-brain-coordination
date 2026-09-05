"""Vendor-neutral reference kernel for the SuperBrain candidate protocol."""

from .authority import AuthorityDirective, AuthorityKind, resolve_authority
from .completion import audit_completion
from .contracts import (
    AgentHandoff,
    AuthorityResolution,
    CapabilityAvailability,
    CapabilityDescriptor,
    CompletionReceipt,
    CompletionStatus,
    ContractMeta,
    EpistemicClaim,
    EpistemicLane,
    ExecutionCheckpoint,
    MemoryWriteProposal,
    ModelBehaviorProfile,
    QualityStatus,
    RequirementEvidence,
    RouteCandidate,
    SideEffectClass,
    SideEffectRecord,
    TaskIntent,
    ToolRouteDecision,
)
from .epistemic import propose_memory_write, revise_claim
from .intent import compile_intent
from .recovery import (
    ResumeDecision,
    build_checkpoint,
    record_side_effect,
    resume_checkpoint,
)
from .routing import CapabilityRequest, route_capability

__all__ = [
    "AgentHandoff",
    "AuthorityDirective",
    "AuthorityKind",
    "AuthorityResolution",
    "CapabilityAvailability",
    "CapabilityDescriptor",
    "CapabilityRequest",
    "CompletionReceipt",
    "CompletionStatus",
    "ContractMeta",
    "EpistemicClaim",
    "EpistemicLane",
    "ExecutionCheckpoint",
    "MemoryWriteProposal",
    "ModelBehaviorProfile",
    "QualityStatus",
    "RequirementEvidence",
    "ResumeDecision",
    "RouteCandidate",
    "SideEffectClass",
    "SideEffectRecord",
    "TaskIntent",
    "ToolRouteDecision",
    "audit_completion",
    "build_checkpoint",
    "compile_intent",
    "propose_memory_write",
    "record_side_effect",
    "resolve_authority",
    "resume_checkpoint",
    "revise_claim",
    "route_capability",
]
