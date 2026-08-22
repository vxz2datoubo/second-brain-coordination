"""Run E58 tests under the named local heavy-stage mutex."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e58_runtime import HeavyStageMutex  # noqa: E402


def main() -> int:
    # Probe the shared lock before discovery. P0 tests acquire it themselves
    # around their owned-child canaries, so holding it across the entire suite
    # would create an artificial nested-lock failure.
    with HeavyStageMutex():
        pass
    suite = unittest.defaultTestLoader.discover(str(TASK_ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
