from __future__ import annotations

import sys
import unittest

from e60_runtime.execution import WholeTaskResourceLease
from e60_runtime.resource_tree import descendant_root_program


class WholeTaskResourceLeaseTests(unittest.TestCase):
    def test_lease_tracks_root_and_grandchild_then_returns_to_zero(self) -> None:
        with WholeTaskResourceLease(task_id="E60-test-grandchild") as lease:
            receipt = lease.execute(
                descendant_root_program(grandchildren=1, root_exit_first=True, sleep_seconds=1.0),
                purpose="root-exit-first-canary",
                timeout_seconds=4.0,
                expected_descendants=1,
            )
        self.assertEqual(receipt.exit_code, 0)
        self.assertGreaterEqual(int(receipt.report["peak_task_owned_processes"]), 2)
        self.assertEqual(receipt.report["postflight_task_owned_process_count"], 0)
        self.assertEqual(receipt.report["orphan_count"], 0)
        self.assertEqual(receipt.report["unrelated_terminated"], 0)

    def test_execute_requires_outer_lease(self) -> None:
        lease = WholeTaskResourceLease(task_id="E60-test-unheld")
        with self.assertRaisesRegex(RuntimeError, "WHOLE_TASK_RESOURCE_LEASE_NOT_HELD"):
            lease.execute([sys.executable, "-c", "raise SystemExit(0)"], purpose="unheld")


if __name__ == "__main__":
    unittest.main()
