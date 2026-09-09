"""B0 — State-machine schemas, role contracts, result classes, event types.

All constants are frozen by this module and used consistently across the kernel.
They encode the minimal state machine from the R188 Task Brief and the required
result classes from the R188 Evidence Contract. No mutable global state lives here.
"""

from __future__ import annotations

from enum import Enum


# ---------------------------------------------------------------------------
# State machine (B0)
# ---------------------------------------------------------------------------
class MissionState(str, Enum):
    """Minimal states required by the R188 Task Brief state machine."""

    CREATED = "CREATED"
    PLANNING = "PLANNING"
    READY = "READY"
    EPISODE_RUNNING = "EPISODE_RUNNING"
    CHECKPOINTED = "CHECKPOINTED"
    VERIFYING = "VERIFYING"
    REMEDIATING = "REMEDIATING"
    REVIEW_READY = "REVIEW_READY"
    REVIEWING = "REVIEWING"
    CANONICALIZATION_READY = "CANONICALIZATION_READY"
    CANONICALIZING = "CANONICALIZING"
    COMPLETE = "COMPLETE"


class WaitState(str, Enum):
    """Terminal-or-wait states."""

    PAUSED_OWNER_GATE = "PAUSED_OWNER_GATE"
    PAUSED_DEPENDENCY = "PAUSED_DEPENDENCY"
    BLOCKED = "BLOCKED"
    FAILED_CIRCUIT_BREAKER = "FAILED_CIRCUIT_BREAKER"
    CANCELLED = "CANCELLED"


ALL_STATES = frozenset(s.value for s in MissionState) | frozenset(s.value for s in WaitState)
ACTIVE_STATES = frozenset(s.value for s in MissionState)
WAIT_STATES = frozenset(s.value for s in WaitState)


# ---------------------------------------------------------------------------
# Roles / independence contract (B0)
# ---------------------------------------------------------------------------
class Role(str, Enum):
    AUTHOR = "AUTHOR"
    REVIEWER = "REVIEWER"
    CANONICALIZER = "CANONICALIZER"


# author != reviewer != canonicalizer (independence contract)
ROLE_INDEPENDENCE_RULE = "AUTHOR != REVIEWER != CANONICALIZER"


# ---------------------------------------------------------------------------
# Result classes (B0) — from R188 Evidence Contract
# ---------------------------------------------------------------------------
class ResultClass(str, Enum):
    SYNTHETIC_KERNEL_RESULT = "SYNTHETIC_KERNEL_RESULT"
    WINDOWS_CONTAINMENT_RESULT = "WINDOWS_CONTAINMENT_RESULT"
    HEADLESS_ADAPTER_RESULT = "HEADLESS_ADAPTER_RESULT"
    SDK_ADAPTER_RESULT = "SDK_ADAPTER_RESULT"
    SYNTHETIC_REVIEW_CANONICALIZATION_RESULT = "SYNTHETIC_REVIEW_CANONICALIZATION_RESULT"
    REAL_CANONICALIZER_CAPABILITY_RESULT = "REAL_CANONICALIZER_CAPABILITY_RESULT"
    EXACT_HEAD_CI_RESULT = "EXACT_HEAD_CI_RESULT"
    INDEPENDENT_REVIEW_RESULT = "INDEPENDENT_REVIEW_RESULT"
    CANONICALIZATION_RESULT = "CANONICALIZATION_RESULT"


class ResultValue(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    NOT_TESTED = "NOT_TESTED"
    UNKNOWN_REQUIRING_EVIDENCE = "UNKNOWN_REQUIRING_EVIDENCE"


# ---------------------------------------------------------------------------
# Event types (B1)
# ---------------------------------------------------------------------------
class EventType(str, Enum):
    GENESIS = "GENESIS"
    PLAN_STARTED = "PLAN_STARTED"
    PLAN_COMPLETED = "PLAN_COMPLETED"
    EPISODE_STARTED = "EPISODE_STARTED"
    CHECKPOINT_REACHED = "CHECKPOINT_REACHED"
    EPISODE_RESUMED = "EPISODE_RESUMED"
    VERIFICATION_STARTED = "VERIFICATION_STARTED"
    VERIFICATION_PASSED = "VERIFICATION_PASSED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    REMEDIATION_COMPLETED = "REMEDIATION_COMPLETED"
    REVIEW_STARTED = "REVIEW_STARTED"
    REVIEW_APPROVED = "REVIEW_APPROVED"
    REVIEW_REJECTED = "REVIEW_REJECTED"
    CANONICALIZATION_STARTED = "CANONICALIZATION_STARTED"
    CANONICALIZATION_COMPLETED = "CANONICALIZATION_COMPLETED"
    CIRCUIT_BREAKER_TRIPPED = "CIRCUIT_BREAKER_TRIPPED"
    PAUSED_OWNER_GATE = "PAUSED_OWNER_GATE"
    PAUSED_DEPENDENCY = "PAUSED_DEPENDENCY"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    WORKER_FAILURE_INJECTED = "WORKER_FAILURE_INJECTED"
    CONTEXT_ROLLOVER = "CONTEXT_ROLLOVER"


# ---------------------------------------------------------------------------
# Effect status (B3)
# ---------------------------------------------------------------------------
class EffectStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    # NOT_EXECUTED must never be auto-assigned; see B3 invariants.


# ---------------------------------------------------------------------------
# Lease status (B3)
# ---------------------------------------------------------------------------
class LeaseStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    FENCED = "FENCED"
    RELEASED = "RELEASED"


# ---------------------------------------------------------------------------
# Write surfaces (B0) — exact, machine-checkable
# ---------------------------------------------------------------------------
AUTHORIZED_WRITE_SURFACES = (
    "tools/durable_mission_kernel/**",
    "tests/durable_mission_kernel/**",
    "tests/test_unified_execution_durable_mission_kernel.py",
    "coordination/EXECUTION/PHASE-B-DURABLE-MISSION-KERNEL/**",
    "coordination/EXECUTION/WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL/**",
)

# Paths this kernel must never mutate (R175/R184 retained + protected governance).
PROTECTED_SURFACES = (
    "coordination/ACTIVE-WORKBUDDY-TASK.yaml",
    "coordination/EXECUTION/ACTIVE-WORKBUDDY-R184-LOCAL-BRIDGE.yaml",
    "coordination/EXECUTION/ACTIVE-TASK-INDEX-REGISTRY.json",
    "coordination/EXECUTION/unified_active_task_registry.py",
    ".github/workflows/unified-execution-fabric.yml",
    "coordination/GOVERNANCE/**",
    "tests/workbuddy/**",
    "tools/workbuddy/**",
    "tools/local_workbuddy_bridge/**",
    "tests/fixtures/local_workbuddy_bridge/**",
    "tests/test_unified_execution_local_bridge.py",
)


def is_authorized_write_path(rel_path: str) -> bool:
    """Return True if ``rel_path`` falls under an authorized write surface (B0)."""
    p = rel_path.replace("\\", "/")
    for surface in AUTHORIZED_WRITE_SURFACES:
        if surface.endswith("/**"):
            prefix = surface[: -len("/**")]
            if p == prefix or p.startswith(prefix + "/"):
                return True
        elif p == surface:
            return True
    return False


def is_protected_path(rel_path: str) -> bool:
    """Return True if ``rel_path`` is a protected surface the kernel must not touch."""
    p = rel_path.replace("\\", "/")
    for surface in PROTECTED_SURFACES:
        if surface.endswith("/**"):
            prefix = surface[: -len("/**")]
            if p == prefix or p.startswith(prefix + "/"):
                return True
        elif p == surface:
            return True
    return False
