"""E58 local lifecycle controls for public-safe synthetic execution."""

from .process_lifecycle import (
    HeavyStageMutex,
    OwnedProcessRegistry,
    ProcessLifecycleError,
    ResourceBudget,
    ResourceBudgetViolation,
)

__all__ = [
    "HeavyStageMutex",
    "OwnedProcessRegistry",
    "ProcessLifecycleError",
    "ResourceBudget",
    "ResourceBudgetViolation",
]
