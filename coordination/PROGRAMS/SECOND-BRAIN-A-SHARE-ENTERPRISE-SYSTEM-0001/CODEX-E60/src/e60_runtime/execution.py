"""The single E60 local child-process entry point.

No mutation or test helper may call ``subprocess.run`` directly. This wrapper
acquires one shared heavy-stage gate and keeps every process it starts in the
same ownership tree until bounded postflight cleanup completes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .resource_tree import OwnedProcessTree, ProcessLifecycleError, ResourceGate


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    purpose: str
    root_pid: int
    exit_code: int
    report: dict[str, object]


class WholeTaskResourceLease:
    """Serial E60 lease for a command and all observed descendants."""

    def __init__(self, *, task_id: str = "E60", max_owned_python_processes: int = 4) -> None:
        self._gate = ResourceGate(
            task_id,
            max_task_processes=max_owned_python_processes,
            max_shared_processes=max_owned_python_processes,
            max_task_cpu_workers=2,
            max_shared_cpu_workers=2,
            mutex_wait_seconds=1.0,
        )
        self._tree = OwnedProcessTree(task_id, gate=self._gate)
        self._entered = False

    def __enter__(self) -> "WholeTaskResourceLease":
        self._gate.acquire()
        self._entered = True
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            self._tree.cleanup("whole_task_lease_exit")
        finally:
            self._gate.release()
            self._entered = False

    def execute(self, command: Sequence[str], *, purpose: str, timeout_seconds: float = 5.0, expected_descendants: int = 0) -> ExecutionReceipt:
        if not self._entered:
            raise ProcessLifecycleError("WHOLE_TASK_RESOURCE_LEASE_NOT_HELD")
        root_pid = self._tree.spawn(command, purpose=purpose)
        exit_code: int | None = None
        try:
            if expected_descendants:
                self._tree.wait_for_descendants(root_pid, minimum=expected_descendants, timeout_seconds=timeout_seconds)
            exit_code = self._tree.wait(root_pid, timeout_seconds=timeout_seconds)
        finally:
            # This executes for normal, timeout, cancellation and root-error paths.
            self._tree.cleanup(f"whole_task_execute:{purpose}")
        if exit_code is None:
            raise ProcessLifecycleError("WHOLE_TASK_EXECUTION_EXIT_CODE_MISSING")
        # A receipt is evidence about the completed lifecycle, not a snapshot
        # taken while a root-exit-first grandchild is still awaiting cleanup.
        return ExecutionReceipt(purpose=purpose, root_pid=root_pid, exit_code=exit_code, report=self._tree.report())
