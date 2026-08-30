"""Independently reproduce and verify a downloaded synthetic experience artifact.

The verifier performs no network access.  Given a file downloaded from the
GitHub Actions artifact, it regenerates the fixed synthetic demonstration from
the checked-out source and compares canonical JSON exactly.  This is evidence
verification, not a release or deployment command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creative_runtime.continuity import graph_for_initial_state
from creative_runtime.contracts import canonical_json
from creative_runtime.coverage import coverage_for_scenario, ledger_for_route
from creative_runtime.experience import build_verified_experience, build_verified_scenario_catalog
from creative_runtime.sequence import build_verified_sequence


DEMO_SCENARIO = "night_signal"
DEMO_ACTIONS = ("listen", "approach", "listen", "listen", "leave")
DEMO_SLOT = "github_demo"


def _git_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("Cannot resolve git HEAD: " + result.stderr.strip())
    return result.stdout.strip()


def _require_clean_worktree() -> None:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("Cannot determine worktree status: " + result.stderr.strip())
    if result.stdout.strip():
        raise RuntimeError("Artifact verification requires a clean worktree; use a fresh clone or checkpoint first")


def expected_artifact(head_sha: str) -> dict[str, Any]:
    """Build the sole fixed Actions demonstration without writing an artifact."""

    report = coverage_for_scenario(DEMO_SCENARIO)
    graph = graph_for_initial_state(report.initial_state)
    ledger = ledger_for_route(graph, report.initial_state, DEMO_ACTIONS)
    return {
        "schema": "CreativeRuntimeExperienceArtifact/v1",
        "status": "experience_artifact_verified",
        "head_sha": head_sha,
        "scenario": DEMO_SCENARIO,
        "actions": list(DEMO_ACTIONS),
        "experience": build_verified_experience(ledger, slot=DEMO_SLOT).to_dict(),
        "sequence": build_verified_sequence(ledger, slot=DEMO_SLOT).to_dict(),
        "catalog": build_verified_scenario_catalog(DEMO_SCENARIO).to_dict(),
        "boundary": {
            "synthetic_only": True,
            "customer_data_present": False,
            "external_provider_called": False,
            "publication_authorized": False,
        },
    }


def verify_artifact(
    path: Path,
    expected_head: str | None = None,
    *,
    require_clean_worktree: bool = True,
) -> dict[str, Any]:
    """Return a receipt only when the downloaded bytes match a clean rebuild."""

    head = _git_head()
    if expected_head is not None and head != expected_head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    if require_clean_worktree:
        _require_clean_worktree()
    try:
        raw = path.read_bytes()
        supplied = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Artifact is not readable UTF-8 JSON") from error
    if not isinstance(supplied, Mapping):
        raise RuntimeError("Artifact root must be a JSON object")
    expected = expected_artifact(head)
    if canonical_json(supplied) != canonical_json(expected):
        raise RuntimeError("Artifact does not exactly match the clean exact-head synthetic rebuild")
    return {
        "schema": "CreativeRuntimeExperienceArtifactVerificationReceipt/v1",
        "status": "experience_artifact_exactly_verified",
        "head_sha": head,
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
        "scenario": DEMO_SCENARIO,
        "action_count": len(DEMO_ACTIONS),
        "catalog_node_count": len(expected["catalog"]["nodes"]),
        "catalog_edge_count": len(expected["catalog"]["edges"]),
        "catalog_transition_count": len(expected["catalog"]["covered_transition_ids"]),
        "sequence_step_count": len(expected["sequence"]["steps"]),
        "sequence_total_duration_seconds": expected["sequence"]["total_duration_seconds"],
        "worktree_status": "clean_required_and_clean" if require_clean_worktree else "not_checked_for_verifier_self_test",
        "boundary": dict(expected["boundary"]),
        "authority_note": "Offline reproducibility evidence only; this verifier cannot approve release, deployment, or customer intake.",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verify a downloaded synthetic interactive experience artifact at an exact git head.")
    parser.add_argument("--artifact", required=True, type=Path, help="Downloaded experience.json file.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before verification.")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify_artifact(args.artifact, args.expected_head), ensure_ascii=False, sort_keys=True, indent=2))
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
