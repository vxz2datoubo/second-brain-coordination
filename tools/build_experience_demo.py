"""Build a public-safe, deterministic interactive-film demonstration artifact.

The artifact contains only the repository's synthetic adult-only route.  It is
intended for a GitHub Actions artifact or a reviewer-owned local file, never as
a customer workspace, provider request, or publication payload.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creative_runtime.contracts import canonical_json
from creative_runtime.demo_routes import GITHUB_DEMO_ROUTES, github_demo_actions
from creative_runtime.experience_library import build_synthetic_experience_artifact


def _git_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("Cannot resolve git HEAD: " + result.stderr.strip())
    return result.stdout.strip()


def build_demo_artifact(expected_head: str | None = None, scenario: str = "night_signal") -> dict[str, Any]:
    """Create a deterministic multi-scene example without touching user data.

    The runtime-owned factory is also used by the multi-scenario library and
    clean verifier, keeping one exact artifact reconstruction contract.
    """

    head = _git_head()
    if expected_head is not None and head != expected_head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    # Preserve this explicit lookup so a malformed scenario fails with the
    # same public-safe route registry that the CLI and Actions matrix use.
    github_demo_actions(scenario)
    return build_synthetic_experience_artifact(head, scenario)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic synthetic interactive-film experience artifact.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before building.")
    parser.add_argument("--scenario", choices=sorted(GITHUB_DEMO_ROUTES), default="night_signal", help="Reviewed synthetic scenario to package.")
    parser.add_argument("--output", required=True, type=Path, help="Output JSON file; intended for a temporary or artifact directory.")
    args = parser.parse_args(argv)
    try:
        artifact = build_demo_artifact(args.expected_head, args.scenario)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(canonical_json(artifact) + "\n", encoding="utf-8")
        print(json.dumps({"status": artifact["status"], "head_sha": artifact["head_sha"], "output": str(args.output)}, sort_keys=True))
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "message": str(error)}, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
