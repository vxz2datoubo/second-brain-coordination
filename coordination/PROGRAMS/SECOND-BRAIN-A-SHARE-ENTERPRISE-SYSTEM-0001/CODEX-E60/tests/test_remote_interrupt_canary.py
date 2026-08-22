"""Remote-only real interruption canary for E60 owned-process cleanup.

This intentionally uses one leased child and one Python-level interrupt.  It
is skipped everywhere except the bounded GitHub Actions job so a local user
machine never receives an interruption test merely by running the suite.
"""

from __future__ import annotations

import _thread
import os
import sys
import threading
import unittest

from e60_runtime.execution import WholeTaskResourceLease


class RemoteInterruptCanaryTests(unittest.TestCase):
    def test_remote_real_keyboard_interrupt_reaps_only_owned_child(self) -> None:
        if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("E60_REMOTE_INTERRUPT_CANARY") != "1":
            self.skipTest("REMOTE_GITHUB_ACTIONS_INTERRUPT_CANARY_ONLY")

        interrupted = threading.Event()

        def request_interrupt() -> None:
            interrupted.set()
            _thread.interrupt_main()

        with WholeTaskResourceLease(task_id="E60-remote-interrupt-canary") as lease:
            timer = threading.Timer(0.25, request_interrupt)
            timer.daemon = True
            timer.start()
            try:
                with self.assertRaises(KeyboardInterrupt):
                    lease.execute(
                        [sys.executable, "-c", "import time; time.sleep(10)"],
                        purpose="remote-real-keyboard-interrupt-canary",
                        timeout_seconds=5.0,
                    )
            finally:
                timer.cancel()
                timer.join(timeout=1.0)
            report = lease.report()

        self.assertTrue(interrupted.is_set())
        self.assertEqual(report["postflight_task_owned_process_count"], 0)
        self.assertEqual(report["orphan_count"], 0)
        self.assertEqual(report["unrelated_terminated"], 0)


if __name__ == "__main__":
    unittest.main()
