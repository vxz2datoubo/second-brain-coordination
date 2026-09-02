"""Fail closed when an R179 change leaves its exact authorized surface."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import subprocess
import sys


DEFAULT_BASE = "a2ea1b35937f81a7f2b243cd063871d3250c8b6b"
ALLOWED_FILES = {
    "creative_runtime/story_graph.py", "creative_runtime/story_bibles.py",
    "creative_runtime/flagship_story_fixture.py", "creative_runtime/__init__.py",
    "creative_runtime/SCRIPT_PACKAGE_V1.md", "tests/test_creative_story_graph.py",
    "tests/test_creative_story_bibles.py", "tests/test_creative_flagship_story.py",
    "tools/verify_r179_scope.py", ".github/workflows/creative-runtime-offline.yml",
}
ALLOWED_PREFIX = "coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/CODEX-R179-A2-PRELUDE/"
FORBIDDEN_TOKENS = ("session_v2", "PlayerCampaign", "NarrativeState", "MediaJob", "GenerationRequest")


def changed_files(base: str, head: str) -> tuple[str, ...]:
    result = subprocess.run(["git", "diff", "--name-only", f"{base}...{head}"], check=True,
                            text=True, encoding="utf-8", capture_output=True)
    return tuple(line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip())


def validate(paths: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f"OUTSIDE_ALLOWLIST:{path}" for raw in paths
                 if (path := PurePosixPath(raw).as_posix()) not in ALLOWED_FILES and not path.startswith(ALLOWED_PREFIX))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    paths = changed_files(args.base, args.head)
    violations = list(validate(paths))
    for path in paths:
        if path.startswith("creative_runtime/") and path not in {"creative_runtime/__init__.py", "creative_runtime/SCRIPT_PACKAGE_V1.md"}:
            text = Path(path).read_text(encoding="utf-8")
            violations.extend(f"FORBIDDEN_AUTHORITY:{path}:{token}" for token in FORBIDDEN_TOKENS if token in text)
    print(f"base={args.base}\nhead={args.head}\nchanged_files={len(paths)}")
    for path in paths:
        print(f"ALLOW {path}")
    for violation in violations:
        print(f"DENY {violation}", file=sys.stderr)
    print("scope_verdict=" + ("PASS" if not violations else "FAIL"))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
