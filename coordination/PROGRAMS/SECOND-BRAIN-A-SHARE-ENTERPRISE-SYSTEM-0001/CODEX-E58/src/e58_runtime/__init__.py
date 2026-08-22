"""E58 local lifecycle controls for public-safe synthetic execution."""

from .process_lifecycle import (
    HeavyStageMutex,
    OwnedProcessRegistry,
    ProcessLifecycleError,
    ResourceBudget,
    ResourceBudgetViolation,
)
from .semantic_execution import (
    ByteRange,
    EvidenceStatement,
    ExecutionReceipt,
    IssuedPacket,
    JsonlOwnershipError,
    PolicyRef,
    Polarity,
    Proposition,
    SemanticAtom,
    SemanticExecutionError,
    TrustedSemanticExecutor,
    VerifierCapability,
    bootstrap_trusted_runtime,
    parse_jsonl_whole_source,
)
from .mutations import MutationResult, MutationSpec, run_catalog

__all__ = [
    "HeavyStageMutex",
    "OwnedProcessRegistry",
    "ProcessLifecycleError",
    "ResourceBudget",
    "ResourceBudgetViolation",
    "ByteRange",
    "EvidenceStatement",
    "ExecutionReceipt",
    "IssuedPacket",
    "JsonlOwnershipError",
    "PolicyRef",
    "Polarity",
    "Proposition",
    "SemanticAtom",
    "SemanticExecutionError",
    "TrustedSemanticExecutor",
    "VerifierCapability",
    "bootstrap_trusted_runtime",
    "parse_jsonl_whole_source",
    "MutationResult",
    "MutationSpec",
    "run_catalog",
]
