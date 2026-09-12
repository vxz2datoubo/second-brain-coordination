"""Local WorkBuddy Bridge — Phase 2B shadow mode (dry-run).

This package reconciles registered GitHub-governed task authority with a local
WorkBuddy/CodeBuddy runtime WITHOUT ever starting a real child process.

Hard boundaries (from WORKBUDDY-R184-LOCAL-WORKBUDDY-BRIDGE/TASK-BRIEF.yaml):
  - DRY_RUN_NEW_BRIDGE_BY_DEFAULT
  - NO_REAL_BRIDGE_PROCESS_ACTIVATION_BEFORE_INDEPENDENT_REVIEW_AND_CANONICALIZATION
  - NO_REAL_WORKBUDDY_CHILD_PROCESS_FROM_TESTS_OR_CI
  - NO_SECOND_CONTROL_TOWER_OR_SECOND_TRUST_GATE
  - NO_WEAK_REIMPLEMENTATION_OF_PROTECTED_GIT_TRANSPORT

The bridge is a composition layer over EXISTING governance:
it wraps unified_execution_trust_gate + unified_active_task_registry and the
HostExecutionBroker. It never reimplements them.
"""

from .contracts import (
    BridgeBoundaryError,
    BridgeDecision,
    LaunchPlan,
    ModelPreflightResult,
    ProcessAdapter,
    ReturnPackage,
)
from .fake_process_adapter import FakeProcessAdapter
from .launch_plan import AuthorityView, normalize_domain, plan_launch
from .model_preflight import preflight_model
from .receipt_store import LaunchReceiptStore
from .redaction import assert_no_secrets, redact
from .registry_adapter import RegisteredTask, RegistryAdapter
from .return_package import build_return_package
from .watcher import BridgeResult, LocalWorkBuddyBridge
from .worktree import WorktreePlan, plan_isolated_worktree, worktrees_collide

__all__ = [
    "AuthorityView",
    "BridgeBoundaryError",
    "BridgeDecision",
    "BridgeResult",
    "FakeProcessAdapter",
    "LaunchPlan",
    "LaunchReceiptStore",
    "LocalWorkBuddyBridge",
    "ModelPreflightResult",
    "ProcessAdapter",
    "RegisteredTask",
    "RegistryAdapter",
    "ReturnPackage",
    "WorktreePlan",
    "assert_no_secrets",
    "build_return_package",
    "normalize_domain",
    "plan_isolated_worktree",
    "plan_launch",
    "preflight_model",
    "redact",
    "worktrees_collide",
]
