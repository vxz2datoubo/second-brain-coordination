"""Fake process adapter — the ONLY adapter automated tests may use.

This adapter never spawns, attaches to or kills a real process. It records
what WOULD have been launched. Any attempt to route a test through a real
adapter is a boundary violation and fails closed.

Boundary source: TASK-BRIEF.yaml
  - "fake process adapter used by all automated tests"
  - "no real WorkBuddy/CodeBuddy child process is spawned in CI or unit tests"
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import BridgeBoundaryError, LaunchPlan


@dataclass
class FakeProcessAdapter:
    """Records plans. Launches nothing. Ever."""

    adapter_id: str = "FAKE_PROCESS_ADAPTER"
    launched: list[LaunchPlan] = field(default_factory=list)
    _launch_calls: int = 0

    # -- ProcessAdapter protocol -----------------------------------------
    def identity(self) -> str:
        return self.adapter_id

    def plan(self, plan: LaunchPlan) -> LaunchPlan:
        """Planning is pure. No side effects."""
        return plan

    def launch(self, plan: LaunchPlan) -> dict:
        """Record the launch. Do NOT start anything."""
        if not plan.dry_run:
            # Even in shadow mode a non-dry-run plan is refused here.
            raise BridgeBoundaryError(
                "FakeProcessAdapter refuses non-dry-run plans; "
                "real activation requires independent review + canonicalization"
            )
        self._launch_calls += 1
        self.launched.append(plan)
        return {
            "adapter": self.adapter_id,
            "launched": False,
            "dry_run": True,
            "would_exec": plan.cli_path,
            "would_argv": list(plan.argv),
            "pid": None,
            "note": "shadow mode: no process was started",
        }

    # -- test helpers ----------------------------------------------------
    @property
    def launch_calls(self) -> int:
        return self._launch_calls
