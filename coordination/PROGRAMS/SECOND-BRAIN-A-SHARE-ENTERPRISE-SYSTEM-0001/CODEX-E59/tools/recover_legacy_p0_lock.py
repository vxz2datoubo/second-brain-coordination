"""Safely recover only E59's ownerless first-run P0 mutex artifact."""

from __future__ import annotations

from pathlib import Path
import sys


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e59_runtime.process_tree import ResourceGate


if __name__ == "__main__":
    recovered = ResourceGate.recover_legacy_abandoned_lock()
    print(f"legacy_lock_recovered={str(recovered).lower()}")
