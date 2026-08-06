"""Emit one canonical and one environment artifact from actual E57 execution."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e57_authority.canonical import execute_evaluation
from e57_authority.core import AuthorityError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        canonical, environment = execute_evaluation(TASK_ROOT)
        arguments.out.mkdir(parents=True, exist_ok=True)
        (arguments.out / "canonical.json").write_bytes(canonical)
        (arguments.out / "environment.json").write_bytes(environment)
    except AuthorityError as exc:
        print(f"E57 evaluation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
