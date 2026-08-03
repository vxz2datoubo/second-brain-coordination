"""Synthetic-only deterministic rules package for D1."""

from .engine import reduce_order
from .types import OutcomeStatus, SessionPhase

__all__ = ("OutcomeStatus", "SessionPhase", "reduce_order")
