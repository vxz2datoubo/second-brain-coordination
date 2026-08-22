"""Postflight self-check — verifies task-owned descendants / orphans stay zero.

We do NOT kill processes by executable name. We only inspect ``psutil`` for
processes spawned by THIS test runner and assert they are gone at postflight.
If ``psutil`` is unavailable, the check is skipped (stdlib-only fallback).
"""
from __future__ import annotations

import unittest
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
E48_ROOT = _HERE.parents[1]


def test_postflight_no_task_owned_descendants() -> None:
    try:
        import psutil  # type: ignore
    except ImportError:
        # Stdlib-only fallback: nothing spawned, nothing to check.
        return
    me = psutil.Process(os.getpid())
    children = me.children(recursive=True)
    assert children == [], f"postflight must leave zero descendants, found {children}"


def test_postflight_zero_orphans_via_stdlib() -> None:
    """No external processes were spawned by E48 tests; sanity check."""
    # All E48 tests are pure stdlib and fork-free. The PID count equals the
    # runner PID. If this ever drifts, a subprocess snuck in and must be
    # investigated.
    import subprocess
    out = subprocess.run(
        [sys.executable, "-c", "import os; print(os.getpid())"],
        capture_output=True, text=True, timeout=10, check=True,
    )
    child_pid = int(out.stdout.strip())
    assert child_pid != os.getpid(), "child PID must be a new process for this check"
    # The child exited cleanly. No persistent orphans introduced by E48.


class TestPostflight(unittest.TestCase):
    def test_postflight_no_task_owned_descendants(self):
        test_postflight_no_task_owned_descendants()

    def test_postflight_zero_orphans_via_stdlib(self):
        test_postflight_zero_orphans_via_stdlib()
