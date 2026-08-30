"""Build a public-safe, deterministic interactive-film demonstration artifact.

The artifact contains only the repository's synthetic adult-only route.  It is
intended for a GitHub Actions artifact or a reviewer-owned local file, never as
a customer workspace, provider request, or publication payload.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creative_runtime.contracts import canonical_json


def _git_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("Cannot resolve git HEAD: " + result.stderr.strip())
    return result.stdout.strip()


def _load_cli() -> Any:
    path = ROOT / "apps" / "cli" / "creativectl.py"
    spec = importlib.util.spec_from_file_location("creative_runtime_experience_demo_cli", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load creativectl")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_demo_artifact(expected_head: str | None = None) -> dict[str, Any]:
    """Create a deterministic multi-scene example without touching user data."""

    head = _git_head()
    if expected_head is not None and head != expected_head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    cli = _load_cli()
    with tempfile.TemporaryDirectory(prefix="creative-runtime-experience-") as directory:
        workspace = Path(directory)
        prefix = ["--workspace", str(workspace), "--slot", "github_demo"]
        cli.run([*prefix, "init", "--scenario", "night_signal"])
        for action_id in ("listen", "approach", "listen", "listen", "leave"):
            cli.run([*prefix, "choose", action_id])
        experience = cli.run([*prefix, "experience"])
        sequence = cli.run([*prefix, "sequence"])
        catalogue = cli.run(["catalog", "--scenario", "night_signal"])
    return {
        "schema": "CreativeRuntimeExperienceArtifact/v1",
        "status": "experience_artifact_verified",
        "head_sha": head,
        "scenario": "night_signal",
        "actions": ["listen", "approach", "listen", "listen", "leave"],
        "experience": experience,
        "sequence": sequence,
        "catalog": catalogue,
        "boundary": {
            "synthetic_only": True,
            "customer_data_present": False,
            "external_provider_called": False,
            "publication_authorized": False,
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic synthetic interactive-film experience artifact.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before building.")
    parser.add_argument("--output", required=True, type=Path, help="Output JSON file; intended for a temporary or artifact directory.")
    args = parser.parse_args(argv)
    try:
        artifact = build_demo_artifact(args.expected_head)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(canonical_json(artifact) + "\n", encoding="utf-8")
        print(json.dumps({"status": artifact["status"], "head_sha": artifact["head_sha"], "output": str(args.output)}, sort_keys=True))
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "message": str(error)}, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
