"""Verify R175 changed paths without modifying the canonical policy floor."""

from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path
import subprocess
import sys


BASELINE = "740788a3847a402923bf2e89093d910eda0c89d0"
FORBIDDEN = "coordination/GOVERNANCE/CREATIVE-RUNTIME-PUBLIC-SAFE-POLICY-FLOOR-v1.yaml"
ALLOWED = (
    ".github/workflows/creative-runtime-offline.yml",
    "creative_runtime/**",
    "apps/cli/**",
    "apps/web/**",
    "tools/**",
    "tests/**",
    "coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/CODEX-R175/**",
    ".gitignore",
)


def changed_paths(repo: Path, head: str = "HEAD") -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{BASELINE}...{head}"],
        cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def verify_scope(paths: list[str]) -> None:
    if FORBIDDEN in paths:
        raise ValueError("R175 candidate must not modify the canonical policy floor")
    rejected = [path for path in paths if not any(fnmatch.fnmatchcase(path, pattern) for pattern in ALLOWED)]
    if rejected:
        raise ValueError("Out-of-scope R175 paths: " + ", ".join(sorted(rejected)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    try:
        paths = changed_paths(args.repo, args.head)
        verify_scope(paths)
        print(f"R175_SCOPE_PASS files={len(paths)}")
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"R175_SCOPE_FAIL {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
