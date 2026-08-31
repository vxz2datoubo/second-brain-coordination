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

from creative_runtime.contracts import canonical_json
from creative_runtime.demo_routes import github_demo_actions
from creative_runtime.experience_library import build_synthetic_experience_artifact
from creative_runtime.experience_package import PACKAGE_MANIFEST_NAME, PACKAGE_MEMBER_NAMES, build_package_manifest, sha256_hex


DEFAULT_DEMO_SCENARIO = "night_signal"
DEMO_SLOT = "github_demo"
PLAYER_SOURCE = ROOT / "apps" / "web" / "verified_experience_player.html"
PLAYER_GUIDE_SOURCE = ROOT / "apps" / "web" / "README.md"


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


def expected_artifact(head_sha: str, scenario: str = DEFAULT_DEMO_SCENARIO) -> dict[str, Any]:
    """Build the sole fixed Actions demonstration without writing an artifact."""

    try:
        github_demo_actions(scenario)
    except ValueError as error:
        raise RuntimeError("Artifact declares an unsupported GitHub demo scenario") from error
    return build_synthetic_experience_artifact(head_sha, scenario)


def _verify_exact_package_file(path: Path, source: Path, label: str) -> str:
    """Require a downloaded package member to equal the checked-out source."""

    try:
        supplied = path.read_bytes()
        expected = source.read_bytes()
    except OSError as error:
        raise RuntimeError(label + " is not readable") from error
    if supplied != expected:
        raise RuntimeError(label + " does not exactly match the clean exact-head source file")
    return hashlib.sha256(supplied).hexdigest()


def _artifact_scenario(payload: Mapping[str, Any]) -> str:
    scenario = payload.get("scenario")
    if not isinstance(scenario, str):
        raise RuntimeError("Artifact must declare a string synthetic scenario")
    try:
        github_demo_actions(scenario)
    except ValueError as error:
        raise RuntimeError("Artifact declares an unsupported GitHub demo scenario") from error
    return scenario


def _read_fixed_package_member(package_dir: Path, name: str) -> bytes:
    """Read one non-symlink package member from a fixed, flat package layout."""

    if not package_dir.is_dir() or package_dir.is_symlink():
        raise RuntimeError("Experience package directory must be a real directory")
    try:
        names = {child.name for child in package_dir.iterdir()}
    except OSError as error:
        raise RuntimeError("Experience package directory is not readable") from error
    expected_names = set(PACKAGE_MEMBER_NAMES) | {PACKAGE_MANIFEST_NAME}
    if names != expected_names:
        raise RuntimeError("Experience package must contain exactly its fixed four public-safe files")
    path = package_dir / name
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Experience package member must be a regular file: " + name)
    try:
        return path.read_bytes()
    except OSError as error:
        raise RuntimeError("Experience package member is not readable: " + name) from error


def verify_artifact(
    path: Path,
    expected_head: str | None = None,
    *,
    require_clean_worktree: bool = True,
    player_path: Path | None = None,
    guide_path: Path | None = None,
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
    scenario = _artifact_scenario(supplied)
    expected = expected_artifact(head, scenario)
    if canonical_json(supplied) != canonical_json(expected):
        raise RuntimeError("Artifact does not exactly match the clean exact-head synthetic rebuild")
    player_hash = _verify_exact_package_file(player_path, PLAYER_SOURCE, "Static player") if player_path is not None else None
    guide_hash = _verify_exact_package_file(guide_path, PLAYER_GUIDE_SOURCE, "Static player guide") if guide_path is not None else None
    return {
        "schema": "CreativeRuntimeExperienceArtifactVerificationReceipt/v1",
        "status": "experience_artifact_exactly_verified",
        "head_sha": head,
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
        "player_sha256": player_hash,
        "guide_sha256": guide_hash,
        "package_members_verified": player_path is not None and guide_path is not None,
        "scenario": scenario,
        "action_count": len(expected["actions"]),
        "catalog_node_count": len(expected["catalog"]["nodes"]),
        "catalog_edge_count": len(expected["catalog"]["edges"]),
        "catalog_transition_count": len(expected["catalog"]["covered_transition_ids"]),
        "sequence_step_count": len(expected["sequence"]["steps"]),
        "sequence_total_duration_seconds": expected["sequence"]["total_duration_seconds"],
        "worktree_status": "clean_required_and_clean" if require_clean_worktree else "not_checked_for_verifier_self_test",
        "boundary": dict(expected["boundary"]),
        "authority_note": "Offline reproducibility evidence only; this verifier cannot approve release, deployment, or customer intake.",
    }


def verify_package(
    package_dir: Path,
    expected_head: str | None = None,
    *,
    require_clean_worktree: bool = True,
) -> dict[str, Any]:
    """Verify every member and the manifest of a downloaded synthetic package."""

    head = _git_head()
    if expected_head is not None and head != expected_head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    if require_clean_worktree:
        _require_clean_worktree()
    members = {name: _read_fixed_package_member(package_dir, name) for name in PACKAGE_MEMBER_NAMES}
    manifest_bytes = _read_fixed_package_member(package_dir, PACKAGE_MANIFEST_NAME)
    try:
        supplied_manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Experience package manifest is not readable UTF-8 JSON") from error
    expected_manifest = build_package_manifest(head, members)
    if canonical_json(supplied_manifest) != canonical_json(expected_manifest):
        raise RuntimeError("Experience package manifest does not exactly match its fixed members and exact head")
    try:
        supplied_artifact = json.loads(members["experience.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Experience package artifact is not readable UTF-8 JSON") from error
    if not isinstance(supplied_artifact, Mapping):
        raise RuntimeError("Experience package artifact root must be a JSON object")
    scenario = _artifact_scenario(supplied_artifact)
    expected = expected_artifact(head, scenario)
    if canonical_json(supplied_artifact) != canonical_json(expected):
        raise RuntimeError("Experience package artifact does not exactly match the clean exact-head synthetic rebuild")
    player_hash = _verify_exact_package_file(package_dir / "verified_experience_player.html", PLAYER_SOURCE, "Static player")
    guide_hash = _verify_exact_package_file(package_dir / "README.md", PLAYER_GUIDE_SOURCE, "Static player guide")
    return {
        "schema": "CreativeRuntimeExperiencePackageVerificationReceipt/v1",
        "status": "experience_package_exactly_verified",
        "head_sha": head,
        "scenario": scenario,
        "manifest_sha256": sha256_hex(manifest_bytes),
        "artifact_sha256": sha256_hex(members["experience.json"]),
        "player_sha256": player_hash,
        "guide_sha256": guide_hash,
        "package_member_count": len(PACKAGE_MEMBER_NAMES),
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
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--artifact", type=Path, help="Downloaded experience.json file.")
    input_group.add_argument("--package-dir", type=Path, help="Downloaded four-file synthetic experience package directory.")
    parser.add_argument("--player", type=Path, help="Downloaded verified_experience_player.html file to compare exactly.")
    parser.add_argument("--guide", type=Path, help="Downloaded player README.md file to compare exactly.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before verification.")
    args = parser.parse_args(argv)
    try:
        if args.package_dir is not None:
            if args.player is not None or args.guide is not None:
                raise RuntimeError("--player and --guide are only valid with --artifact")
            receipt = verify_package(args.package_dir, args.expected_head)
        else:
            receipt = verify_artifact(args.artifact, args.expected_head, player_path=args.player, guide_path=args.guide)
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
