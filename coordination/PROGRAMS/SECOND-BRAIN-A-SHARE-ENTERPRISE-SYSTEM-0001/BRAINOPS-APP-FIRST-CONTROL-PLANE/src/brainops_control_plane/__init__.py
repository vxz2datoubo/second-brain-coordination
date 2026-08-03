"""Read-only, App-first BrainOps control-plane primitives for E35.

This package deliberately contains no executor.  It can inventory, model and
shadow-evaluate a route, but cannot start a process, dispatch an agent, or
change a service.
"""

from .models import ExecutionOwner, ShadowOutcome, ValidationError
from .reconciliation import ShadowReconciler

__all__ = ["ExecutionOwner", "ShadowOutcome", "ShadowReconciler", "ValidationError"]
