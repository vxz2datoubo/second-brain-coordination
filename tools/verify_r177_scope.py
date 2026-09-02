"""Fail closed when an R177 change leaves its authorized write surface."""

from __future__ import annotations

import argparse
from pathlib import PurePosixPath
import subprocess
import sys


DEFAULT_BASE = "0ba071a14b7d945de6f008a382b5f43554b1030e"
ALLOWED_PREFIXES = (
    "creative_runtime/",
    "tests/",
    "tools/",
    "coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/CODEX-R177-A1-2/",
)
ALLOWED_FILES = {".github/workflows/creative-runtime-offline.yml"}
FORBIDDEN_PREFIXES = (
    "tests/workbuddy/",
    "tools/workbuddy/",
    "coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/WORKBUDDY-R175/",
    "coordination/PROGRAMS/REALTIME-INTERACTIVE-FILM-GAME-0002/SINGLE-V2-AUTHORITY-R172/",
)
FORBIDDEN_FILES = {
    "creative_runtime/session_v2.py",
    "apps/cli/creativectl.py",
    "coordination/ACTIVE-WORKBUDDY-TASK.yaml",
    "coordination/ROUTES/WORKBUDDY-R175-ORDERED-BATCH.yaml",
}


def changed_files(base: str, head: str) -> tuple[str, ...]:
    output = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
    ).stdout
    return tuple(line.strip().replace("\\", "/") for line in output.splitlines() if line.strip())


def validate(paths: tuple[str, ...]) -> tuple[str, ...]:
    violations: list[str] = []
    for raw_path in paths:
        path = PurePosixPath(raw_path).as_posix()
        if path in FORBIDDEN_FILES or any(path.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            violations.append(f"FORBIDDEN_OVERLAP:{path}")
        elif path not in ALLOWED_FILES and not any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            violations.append(f"OUTSIDE_ALLOWLIST:{path}")
    return tuple(violations)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    paths = changed_files(args.base, args.head)
    violations = validate(paths)
    print(f"base={args.base}")
    print(f"head={args.head}")
    print(f"changed_files={len(paths)}")
    for path in paths:
        print(f"ALLOW {path}")
    for violation in violations:
        print(f"DENY {violation}", file=sys.stderr)
    print("scope_verdict=" + ("PASS" if not violations else "FAIL"))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
