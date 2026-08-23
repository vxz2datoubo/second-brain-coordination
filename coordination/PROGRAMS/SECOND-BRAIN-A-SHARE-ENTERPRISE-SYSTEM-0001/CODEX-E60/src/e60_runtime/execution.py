"""The single E60 local child-process entry point.

No mutation or test helper may call ``subprocess.run`` directly. This wrapper
acquires one shared heavy-stage gate and keeps every process it starts in the
same ownership tree until bounded postflight cleanup completes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import time
from typing import Callable, Mapping, Sequence

from .resource_tree import OwnedProcessTree, ProcessLifecycleError, ResourceGate
from .resource_policy import AdaptiveResourceController, WorkloadClass


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    purpose: str
    root_pid: int
    exit_code: int
    resource_decision: dict[str, object]
    report: dict[str, object]


class WholeTaskResourceLease:
    """Serial E60 lease for a command and all observed descendants."""

    def __init__(
        self,
        *,
        task_id: str = "E60",
        sample_provider: Callable[[], Mapping[str, object]] | None = None,
        monotonic_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        sample_provider = sample_provider or self._default_sample_provider
        self._resources = AdaptiveResourceController(sample_provider, monotonic_clock)
        self._gate = ResourceGate(
            task_id,
            max_task_processes=2,
            max_shared_processes=4,
            max_task_cpu_workers=1,
            max_shared_cpu_workers=1,
            mutex_wait_seconds=1.0,
            cpu_throttle_percent=35.0,
            cpu_throttle_sustain_seconds=3.0,
        )
        self._tree = OwnedProcessTree(task_id, gate=self._gate)
        self._entered = False

    @staticmethod
    def _default_sample_provider() -> Mapping[str, object]:
        from .resource_tree import resource_snapshot

        return resource_snapshot()

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

    def report(self) -> dict[str, object]:
        """Return the current ownership-scoped state for exception-path tests."""

        return self._tree.report()

    def execute(
        self,
        command: Sequence[str],
        *,
        purpose: str,
        timeout_seconds: float = 5.0,
        expected_descendants: int = 0,
        workload: WorkloadClass = WorkloadClass.LIFECYCLE_CANARY,
        env: dict[str, str] | None = None,
    ) -> ExecutionReceipt:
        if not self._entered:
            raise ProcessLifecycleError("WHOLE_TASK_RESOURCE_LEASE_NOT_HELD")
        if expected_descendants > 1:
            raise ProcessLifecycleError("LOCAL_CANARY_DESCENDANT_CAP_EXCEEDED")
        resource_decision = self._resources.require_local_spawn(workload)
        root_pid = self._tree.spawn(command, purpose=purpose, env=env)
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
        return ExecutionReceipt(
            purpose=purpose,
            root_pid=root_pid,
            exit_code=exit_code,
            resource_decision=asdict(resource_decision),
            report=self._tree.report(),
        )
