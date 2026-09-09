"""B1 — Pure deterministic state reducers.

Every transition is a pure function of ``(state, event_type)`` returning the next
state (or raising a :class:`ReducerError` for an illegal transition). There is no
I/O and no hidden global state here; this makes replay deterministic.
"""

from __future__ import annotations

from . import schemas
from .schemas import EventType, MissionState, WaitState


class ReducerError(ValueError):
    """Raised when an event is not legal from the current state."""


# Deterministic transition table: (current_state, event_type) -> next_state.
_TRANSITIONS = {
    (MissionState.CREATED.value, EventType.PLAN_STARTED.value): MissionState.PLANNING.value,
    (MissionState.PLANNING.value, EventType.PLAN_COMPLETED.value): MissionState.READY.value,
    (MissionState.READY.value, EventType.EPISODE_STARTED.value): MissionState.EPISODE_RUNNING.value,
    (MissionState.EPISODE_RUNNING.value, EventType.CHECKPOINT_REACHED.value): MissionState.CHECKPOINTED.value,
    (MissionState.EPISODE_RUNNING.value, EventType.CIRCUIT_BREAKER_TRIPPED.value): WaitState.FAILED_CIRCUIT_BREAKER.value,
    (MissionState.CHECKPOINTED.value, EventType.EPISODE_RESUMED.value): MissionState.EPISODE_RUNNING.value,
    (MissionState.CHECKPOINTED.value, EventType.VERIFICATION_STARTED.value): MissionState.VERIFYING.value,
    (MissionState.VERIFYING.value, EventType.VERIFICATION_PASSED.value): MissionState.REVIEW_READY.value,
    (MissionState.VERIFYING.value, EventType.VERIFICATION_FAILED.value): MissionState.REMEDIATING.value,
    (MissionState.REMEDIATING.value, EventType.REMEDIATION_COMPLETED.value): MissionState.VERIFYING.value,
    (MissionState.REVIEW_READY.value, EventType.REVIEW_STARTED.value): MissionState.REVIEWING.value,
    (MissionState.REVIEWING.value, EventType.REVIEW_APPROVED.value): MissionState.CANONICALIZATION_READY.value,
    (MissionState.REVIEWING.value, EventType.REVIEW_REJECTED.value): MissionState.REMEDIATING.value,
    (MissionState.CANONICALIZATION_READY.value, EventType.CANONICALIZATION_STARTED.value): MissionState.CANONICALIZING.value,
    (MissionState.CANONICALIZING.value, EventType.CANONICALIZATION_COMPLETED.value): MissionState.COMPLETE.value,
}


# Events that pause/cancel from any ACTIVE state (explicitly machine-validated).
_ANY_ACTIVE_PAUSES = {
    EventType.PAUSED_OWNER_GATE.value: WaitState.PAUSED_OWNER_GATE.value,
    EventType.PAUSED_DEPENDENCY.value: WaitState.PAUSED_DEPENDENCY.value,
    EventType.BLOCKED.value: WaitState.BLOCKED.value,
    EventType.CANCELLED.value: WaitState.CANCELLED.value,
}


def reduce_state(current_state: str, event_type: str) -> str:
    """Return the next state for ``(current_state, event_type)``.

    Raises :class:`ReducerError` on an illegal transition so callers fail closed
    instead of silently mis-tracking state.
    """
    if event_type == EventType.GENESIS.value:
        # GENESIS is the initial anchor; it does not change state.
        return current_state
    key = (current_state, event_type)
    if key in _TRANSITIONS:
        return _TRANSITIONS[key]
    # Pauses/cancellations are legal from any active state.
    if current_state in schemas.ACTIVE_STATES and event_type in _ANY_ACTIVE_PAUSES:
        return _ANY_ACTIVE_PAUSES[event_type]
    raise ReducerError(f"illegal transition: {current_state} --{event_type}-> ?")


def is_terminal_or_wait(state: str) -> bool:
    """Return True if ``state`` is a wait/terminal state."""
    return state in schemas.WAIT_STATES


def is_complete(state: str) -> bool:
    return state == MissionState.COMPLETE.value


def initial_state() -> str:
    return MissionState.CREATED.value
