"""One offline test entry for P1, P2, and Phase 3 synthetic contract regression."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUITES = (
    ROOT / "PHASE-1" / "tests",
    ROOT / "PHASE-2-OFFLINE-VERTICAL-SLICE" / "tests",
    Path(__file__).resolve().parent / "tests",
)


def main() -> int:
    for suite in SUITES:
        completed = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(suite), "-p", "test_*.py"], check=False)
        if completed.returncode:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
