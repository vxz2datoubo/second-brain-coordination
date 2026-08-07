from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e59_runtime.process_tree import (  # noqa: E402
    OwnedProcessTree,
    ProcessIdentity,
    ProcessLifecycleError,
    ResourceGate,
    ResourceViolation,
    descendant_root_program,
    resource_snapshot,
)


class OwnedProcessTreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._snapshot_patch = patch(
            "e59_runtime.process_tree.resource_snapshot",
            return_value={"available_ram_gib": 16.0, "cpu_percent": 5.0, "python_process_count": 1},
        )
        self._snapshot_patch.start()

    def tearDown(self) -> None:
        self._snapshot_patch.stop()

    def test_public_resource_snapshot_has_no_command_line(self) -> None:
        # This assertion exercises the real public snapshot rather than the
        # deterministic gate fixture used by lifecycle tests below.
        self._snapshot_patch.stop()
        try:
            snapshot = resource_snapshot()
        finally:
            self._snapshot_patch.start()
        self.assertIn("python_process_count", snapshot)
        self.assertNotIn("command_line", snapshot)

    def test_resource_snapshot_does_not_launch_powershell_or_cim(self) -> None:
        source = (TASK_ROOT / "src" / "e59_runtime" / "process_tree.py").read_text(encoding="utf-8")
        self.assertNotIn("Get-CimInstance", source)
        self.assertNotIn('"powershell"', source)

    def test_root_exit_first_keeps_grandchildren_owned_until_cleanup(self) -> None:
        gate = ResourceGate("E59-test-root-exits", max_task_processes=4)
        with gate, OwnedProcessTree("E59-test-root-exits", gate=gate) as tree:
            root = tree.spawn(descendant_root_program(grandchildren=2, root_exit_first=True), purpose="root-exits")
            descendants = tree.wait_for_descendants(root, minimum=2, timeout_seconds=8)
            self.assertEqual(len(descendants), 2)
            self.assertEqual(tree.wait(root, timeout_seconds=3), 0)
            self.assertGreaterEqual(tree.active_owned_count, 2)
            tree.cleanup("root_exit_first")
            self.assertEqual(tree.active_owned_count, 0)
            self.assertEqual(tree.report()["orphan_count"], 0)

    def test_timeout_cleanup_reclaims_observed_descendants(self) -> None:
        gate = ResourceGate("E59-test-timeout", max_task_processes=4)
        with gate, OwnedProcessTree("E59-test-timeout", gate=gate) as tree:
            root = tree.spawn(descendant_root_program(grandchildren=2, root_exit_first=False), purpose="timeout")
            tree.wait_for_descendants(root, minimum=2, timeout_seconds=8)
            with self.assertRaises(subprocess.TimeoutExpired):
                tree.wait(root, timeout_seconds=0.01)
            tree.cleanup("timeout")
            self.assertEqual(tree.active_owned_count, 0)
            self.assertEqual(tree.unrelated_terminated, 0)

    def test_exception_context_cleanup_reclaims_tree(self) -> None:
        tree = OwnedProcessTree("E59-test-exception")
        with self.assertRaisesRegex(RuntimeError, "intentional"):
            gate = ResourceGate("E59-test-exception", max_task_processes=4)
            with gate, OwnedProcessTree("E59-test-exception", gate=gate) as tree:
                root = tree.spawn(descendant_root_program(grandchildren=2, root_exit_first=False), purpose="exception")
                tree.wait_for_descendants(root, minimum=2, timeout_seconds=8)
                raise RuntimeError("intentional")
        self.assertEqual(tree.active_owned_count, 0)
        self.assertEqual(tree.report()["orphan_count"], 0)

    def test_keyboard_interrupt_context_cleanup_reclaims_tree(self) -> None:
        tree = OwnedProcessTree("E59-test-ctrl-c")
        with self.assertRaises(KeyboardInterrupt):
            gate = ResourceGate("E59-test-ctrl-c", max_task_processes=4)
            with gate, OwnedProcessTree("E59-test-ctrl-c", gate=gate) as tree:
                root = tree.spawn(descendant_root_program(grandchildren=2, root_exit_first=False), purpose="ctrl-c")
                tree.wait_for_descendants(root, minimum=2, timeout_seconds=8)
                raise KeyboardInterrupt
        self.assertEqual(tree.active_owned_count, 0)

    def test_gate_rejects_a_cap_exceeding_request(self) -> None:
        with ResourceGate("E59-test-cap", max_task_processes=2, max_shared_processes=2) as gate:
            with self.assertRaisesRegex(ResourceViolation, "PROCESS_CAP"):
                gate.admit(3)

    def test_second_gate_is_rejected_while_heavy_mutex_is_held(self) -> None:
        first = ResourceGate("E59-test-mutex-first", mutex_wait_seconds=0)
        second = ResourceGate("E59-test-mutex-second", mutex_wait_seconds=0)
        first.acquire()
        try:
            with self.assertRaisesRegex(ResourceViolation, "MUTEX"):
                second.acquire()
        finally:
            first.release()

    def test_gate_waits_for_a_known_holder_without_stealing_the_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "e59-gate"
            with patch.object(ResourceGate, "_ROOT", root), patch.object(ResourceGate, "_LOCK", root / "lock"), patch.object(ResourceGate, "_STATE", root / "state.json"), patch("e59_runtime.process_tree.resource_snapshot", return_value={"available_ram_gib": 16.0, "cpu_percent": 5.0, "python_process_count": 1}):
                first = ResourceGate("E59-test-wait-first", mutex_wait_seconds=0)
                second = ResourceGate("E59-test-wait-second", mutex_wait_seconds=1)
                first.acquire()
                releaser = threading.Thread(target=lambda: (time.sleep(0.1), first.release()), daemon=True)
                releaser.start()
                second.acquire()
                self.assertTrue(second._held)
                second.release()
                releaser.join(timeout=1)

    def test_pid_reuse_is_not_treated_as_same_owned_process(self) -> None:
        original = ProcessIdentity(42, 1, "100", "python.exe", "a" * 64, 42, "test")
        reused = ProcessIdentity(42, 1, "101", "python.exe", "b" * 64, 42, "test")
        self.assertFalse(original.matches(reused))

    def test_gate_rejects_cpu_worker_cap(self) -> None:
        with ResourceGate("E59-test-worker-cap", max_task_cpu_workers=1, max_shared_cpu_workers=1) as gate:
            with self.assertRaisesRegex(ResourceViolation, "CPU_WORKER_CAP"):
                gate.admit(1, cpu_workers=2)

    def test_gate_allows_a_transient_cpu_spike(self) -> None:
        with patch("e59_runtime.process_tree.resource_snapshot", return_value={"available_ram_gib": 16.0, "cpu_percent": 90.0, "python_process_count": 1}):
            with ResourceGate("E59-test-transient-cpu", cpu_throttle_sustain_seconds=15) as gate:
                gate.admit(1)
                self.assertIsNotNone(gate._cpu_above_threshold_since)

    def test_gate_rejects_cpu_load_only_after_the_sustain_window(self) -> None:
        with patch("e59_runtime.process_tree.resource_snapshot", return_value={"available_ram_gib": 16.0, "cpu_percent": 90.0, "python_process_count": 1}):
            with ResourceGate("E59-test-sustained-cpu", cpu_throttle_sustain_seconds=0.01) as gate:
                gate.admit(0)
                time.sleep(0.02)
                with self.assertRaisesRegex(ResourceViolation, "CPU_THROTTLE_REQUIRED"):
                    gate.admit(1)

    def test_legacy_recovery_is_noop_when_no_e59_lock_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "e59-gate"
            with patch.object(ResourceGate, "_ROOT", root), patch.object(ResourceGate, "_LOCK", root / "lock"), patch.object(ResourceGate, "_STATE", root / "state.json"):
                self.assertFalse(ResourceGate.recover_legacy_abandoned_lock())

    def test_release_removes_its_owner_aware_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "e59-gate"
            with patch.object(ResourceGate, "_ROOT", root), patch.object(ResourceGate, "_LOCK", root / "lock"), patch.object(ResourceGate, "_STATE", root / "state.json"), patch("e59_runtime.process_tree.resource_snapshot", return_value={"available_ram_gib": 16.0, "cpu_percent": 5.0, "python_process_count": 1}):
                gate = ResourceGate("E59-test-release")
                gate.acquire()
                self.assertTrue((root / "lock").exists())
                state = json.loads((root / "state.json").read_text(encoding="utf-8"))
                self.assertEqual(state["owner_pid"], os.getpid())
                gate.release()
                self.assertFalse((root / "lock").exists())

    def test_failed_acquire_releases_a_newly_created_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "e59-gate"
            with patch.object(ResourceGate, "_ROOT", root), patch.object(ResourceGate, "_LOCK", root / "lock"), patch.object(ResourceGate, "_STATE", root / "state.json"), patch("e59_runtime.process_tree.resource_snapshot", side_effect=RuntimeError("sample failure")):
                gate = ResourceGate("E59-test-acquire-cleanup", mutex_wait_seconds=0)
                with self.assertRaisesRegex(RuntimeError, "sample failure"):
                    gate.acquire()
                self.assertFalse((root / "lock").exists())

    def test_missing_state_lock_recovers_only_after_no_foreign_python_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "e59-gate"
            lock = root / "lock"
            lock.mkdir(parents=True)
            with patch.object(ResourceGate, "_ROOT", root), patch.object(ResourceGate, "_LOCK", lock), patch.object(ResourceGate, "_STATE", root / "state.json"), patch("e59_runtime.process_tree._windows_snapshot", return_value={}):
                self.assertTrue(ResourceGate.recover_legacy_abandoned_lock())
                self.assertFalse(lock.exists())

    def test_out_of_range_grandchild_request_is_rejected_before_spawn(self) -> None:
        with self.assertRaises(ValueError):
            descendant_root_program(grandchildren=3, root_exit_first=False)

    def test_cleanup_never_uses_an_executable_name_global_kill(self) -> None:
        source = (TASK_ROOT / "src" / "e59_runtime" / "process_tree.py").read_text(encoding="utf-8")
        self.assertNotIn("taskkill /IM", source)
        self.assertNotIn('"taskkill", "/IM"', source)
        self.assertNotIn("Get-Process python", source)

    def test_taskkill_timeout_is_recorded_and_does_not_abort_the_force_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "e59-gate"
            with patch.object(ResourceGate, "_ROOT", root), patch.object(ResourceGate, "_LOCK", root / "lock"), patch.object(ResourceGate, "_STATE", root / "state.json"), patch("e59_runtime.process_tree.resource_snapshot", return_value={"available_ram_gib": 16.0, "cpu_percent": 5.0, "python_process_count": 1}):
                with ResourceGate("E59-test-taskkill-timeout") as gate:
                    tree = OwnedProcessTree("E59-test-taskkill-timeout", gate=gate)
                    owned = ProcessIdentity(404, 1, "100", "python.exe", "digest", 404, "test")
                    with patch("e59_runtime.process_tree.subprocess.run", side_effect=subprocess.TimeoutExpired(["taskkill"], 5)):
                        tree._request_termination(owned, force=False)
                    self.assertIn("termination_request_timeout", [event.event for event in tree.events])


if __name__ == "__main__":
    unittest.main(verbosity=2)
