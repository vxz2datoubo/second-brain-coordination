"""Exact additive-only path and capability verifier for R180."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import subprocess
import sys


DEFAULT_BASE = "607fe934be3b098c32e31cd257de8b462cd20ccd"
ALLOWED_FILES = {
    "creative_runtime/director_beat_plan.py",
    "creative_runtime/DIRECTOR_BEAT_PLAN_V1.md",
    "tests/test_creative_director_beat_plan.py",
    "tools/verify_r180_scope.py",
    ".github/workflows/creative-runtime-r180-offline.yml",
}
ALLOWED_PREFIX = "coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/CODEX-R180-A2-1/"
FORBIDDEN_IMPORTS = ("requests", "urllib", "socket", "httpx", "openai", "anthropic", "boto3")


def changed_files(base: str, head: str) -> tuple[str, ...]:
    result = subprocess.run(["git", "diff", "--name-only", f"{base}...{head}"], check=True,
                            text=True, encoding="utf-8", capture_output=True)
    return tuple(line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    paths = changed_files(args.base, args.head)
    violations = []
    for raw in paths:
        path = PurePosixPath(raw).as_posix()
        if path not in ALLOWED_FILES and not path.startswith(ALLOWED_PREFIX):
            violations.append(f"OUTSIDE_ALLOWLIST:{path}")
    source = Path("creative_runtime/director_beat_plan.py")
    if source.exists():
        text = source.read_text(encoding="utf-8")
        for capability in FORBIDDEN_IMPORTS:
            if f"import {capability}" in text or f"from {capability}" in text:
                violations.append(f"FORBIDDEN_CAPABILITY:{capability}")
    print(f"base={args.base}\nhead={args.head}\nchanged_files={len(paths)}")
    for path in paths:
        print(f"ALLOW {path}")
    for violation in violations:
        print(f"DENY {violation}", file=sys.stderr)
    print("scope_verdict=" + ("PASS" if not violations else "FAIL"))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
