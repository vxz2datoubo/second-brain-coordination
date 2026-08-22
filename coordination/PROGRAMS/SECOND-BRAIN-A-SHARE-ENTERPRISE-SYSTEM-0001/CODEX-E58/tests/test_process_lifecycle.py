from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import time
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e58_runtime import (  # noqa: E402
    HeavyStageMutex,
    OwnedProcessRegistry,
    ProcessLifecycleError,
    ResourceBudget,
    ResourceBudgetViolation,
)


def _child(code: str) -> list[str]:
    return [sys.executable, "-c", code]


class ProcessLifecycleTests(unittest.TestCase):
    """P0 canary: task-owned children must be bounded and cleaned."""

    def test_normal_exit_is_recorded(self) -> None:
        with HeavyStageMutex(), OwnedProcessRegistry("E58-P0-normal") as registry:
            pid = registry.spawn(_child("raise SystemExit(0)"), purpose="normal")
            self.assertEqual(registry.wait(pid, timeout_seconds=5), 0)
            self.assertEqual(registry.active_count, 0)
            self.assertEqual(registry.peak_owned_processes, 1)
            self.assertEqual([event.event for event in registry.events], ["spawn", "exit"])

    def test_unexpected_exit_is_detected_and_unregistered(self) -> None:
        with HeavyStageMutex(), OwnedProcessRegistry("E58-P0-error") as registry:
            pid = registry.spawn(_child("raise SystemExit(7)"), purpose="error")
            with self.assertRaises(ProcessLifecycleError):
                registry.wait(pid, timeout_seconds=5)
            self.assertEqual(registry.active_count, 0)
            self.assertEqual(registry.events[-1].event, "exit")
            self.assertEqual(registry.events[-1].exit_code, 7)

    def test_timeout_cleanup_reclaims_only_owned_child(self) -> None:
        with HeavyStageMutex(), OwnedProcessRegistry("E58-P0-timeout") as registry:
            pid = registry.spawn(_child("import time; time.sleep(30)"), purpose="timeout")
            with self.assertRaises(subprocess.TimeoutExpired):
                registry.wait(pid, timeout_seconds=0.01)
            self.assertEqual(registry.active_count, 1)
            self.assertEqual(registry.cleanup("timeout"), 1)
            self.assertEqual(registry.active_count, 0)
            self.assertTrue(registry.events[-1].event.startswith("cleanup:timeout"))

    def test_exception_path_reclaims_owned_child(self) -> None:
        registry = OwnedProcessRegistry("E58-P0-exception")
        with self.assertRaisesRegex(RuntimeError, "simulated cancellation"):
            with HeavyStageMutex(), registry:
                registry.spawn(_child("import time; time.sleep(30)"), purpose="cancel")
                raise RuntimeError("simulated cancellation")
        self.assertEqual(registry.active_count, 0)
        self.assertTrue(any(event.event == "cleanup:context_exit" for event in registry.events))

    def test_keyboard_interrupt_path_reclaims_owned_child(self) -> None:
        registry = OwnedProcessRegistry("E58-P0-keyboard-interrupt")
        with self.assertRaises(KeyboardInterrupt):
            with HeavyStageMutex(), registry:
                registry.spawn(_child("import time; time.sleep(30)"), purpose="keyboard-interrupt")
                raise KeyboardInterrupt
        self.assertEqual(registry.active_count, 0)
        self.assertTrue(any(event.event == "cleanup:context_exit" for event in registry.events))

    def test_p0_canary_budget_rejects_third_worker(self) -> None:
        budget = ResourceBudget(max_task_python_processes=2, max_cpu_bound_workers=2, p0_canary_workers=2)
        with HeavyStageMutex(), OwnedProcessRegistry("E58-P0-budget", budget=budget) as registry:
            first = registry.spawn(_child("import time; time.sleep(30)"), purpose="one")
            second = registry.spawn(_child("import time; time.sleep(30)"), purpose="two")
            with self.assertRaises(ResourceBudgetViolation):
                registry.spawn(_child("raise SystemExit(0)"), purpose="third")
            self.assertEqual(registry.active_count, 2)
            self.assertEqual(registry.peak_owned_processes, 2)
            self.assertNotEqual(first, second)

    def test_mutex_rejects_second_owner_until_first_releases(self) -> None:
        first = HeavyStageMutex()
        second = HeavyStageMutex()
        try:
            first.acquire()
            with self.assertRaises(ResourceBudgetViolation):
                second.acquire(timeout_seconds=0)
        finally:
            first.close()
            second.close()

    def test_registry_close_is_idempotent(self) -> None:
        registry = OwnedProcessRegistry("E58-P0-close")
        registry.close()
        self.assertEqual(registry.close(), 0)
        with self.assertRaises(ProcessLifecycleError):
            registry.spawn(_child("raise SystemExit(0)"), purpose="closed")

    def test_command_ledger_exposes_digest_not_command_text(self) -> None:
        with HeavyStageMutex(), OwnedProcessRegistry("E58-P0-ledger") as registry:
            command = _child("raise SystemExit(0)")
            pid = registry.spawn(command, purpose="digest")
            active = registry.active_processes
            self.assertEqual(len(active), 1)
            self.assertEqual(len(active[0].command_digest), 64)
            self.assertNotIn(command[-1], active[0].command_digest)
            registry.wait(pid, timeout_seconds=5)
            self.assertEqual(len(registry.events), 2)
            self.assertEqual(len(registry._owned), 0)

    def test_containment_uses_job_or_explicit_process_group_fallback(self) -> None:
        with HeavyStageMutex(), OwnedProcessRegistry("E58-P0-containment") as registry:
            pid = registry.spawn(_child("raise SystemExit(0)"), purpose="containment")
            self.assertIn(registry.containment_mode, {"job_object", "process_group_fallback"})
            if registry.containment_mode == "process_group_fallback":
                self.assertIsNotNone(registry.containment_fallback_reason)
            registry.wait(pid, timeout_seconds=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
