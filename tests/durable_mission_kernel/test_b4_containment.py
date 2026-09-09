"""B4 tests — Windows Job Object hard containment + no-silent-downgrade."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.durable_mission_kernel import containment  # noqa: E402

_SLEEP_SCRIPT = "import time; time.sleep(30)"


def _spawn_sleeper():
    return subprocess.Popen([sys.executable, "-c", _SLEEP_SCRIPT])


class B4ContainmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = containment.probe_support()

    def test_probe_is_honest(self):
        if self.report.supported:
            self.assertEqual(self.report.mode, "HARD_JOB_OBJECT")
        else:
            self.assertIn(self.report.mode, ("PARTIAL", "BLOCKED"))
            self.assertFalse(self.report.supported)

    def test_terminate_job_kills_owned_process(self):
        if not self.report.supported:
            self.skipTest("Job Object hard containment unavailable on this machine")
        job, rep = containment.build_provider()
        self.assertIsNotNone(job)
        self.assertEqual(rep.mode, "HARD_JOB_OBJECT")
        child = _spawn_sleeper()
        try:
            job.assign(child.pid)
            self.assertTrue(job.terminate())
            child.wait(timeout=10)
            self.assertIsNotNone(child.poll(), "owned child must be terminated by job")
        finally:
            job.close()
            if child.poll() is None:
                child.kill()

    def test_kill_on_close_terminates_owned_process(self):
        if not self.report.supported:
            self.skipTest("Job Object hard containment unavailable on this machine")
        job = containment.WindowsJobObject(kill_on_close=True)
        child = _spawn_sleeper()
        try:
            job.assign(child.pid)
            job.close()  # KILL_ON_JOB_CLOSE must terminate assigned descendants
            child.wait(timeout=10)
            self.assertIsNotNone(child.poll(), "child must be terminated on job close")
        finally:
            if child.poll() is None:
                child.kill()

    def test_unrelated_process_survives(self):
        if not self.report.supported:
            self.skipTest("Job Object hard containment unavailable on this machine")
        unrelated = _spawn_sleeper()
        job, _ = containment.build_provider()
        owned = None
        try:
            owned = _spawn_sleeper()
            job.assign(owned.pid)
            job.terminate()
            owned.wait(timeout=10)
            self.assertIsNone(unrelated.poll(), "unrelated (non-owned) process must survive")
        finally:
            job.close()
            for p in (unrelated, owned):
                if p is not None and p.poll() is None:
                    p.kill()
                    p.wait(timeout=5)

    def test_no_silent_downgrade_contract(self):
        # On a machine where probe reports unsupported, build_provider must return
        # None (never a bare-process fallback). On supported machines it returns a
        # hard Job Object.
        job, rep = containment.build_provider()
        if rep.supported:
            self.assertIsNotNone(job)
            self.assertEqual(rep.mode, "HARD_JOB_OBJECT")
        else:
            self.assertIsNone(job)
            self.assertIn(rep.mode, ("PARTIAL", "BLOCKED"))


if __name__ == "__main__":
    unittest.main()
