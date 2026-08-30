"""Rebuild and verify a downloaded offline experience-library package."""

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
from creative_runtime.experience_library import build_verified_experience_library, verify_verified_experience_library
from creative_runtime.experience_library_package import (
    LIBRARY_PACKAGE_MANIFEST_NAME,
    LIBRARY_PACKAGE_MEMBER_NAMES,
    build_library_package_manifest,
)
from creative_runtime.experience_package import sha256_hex


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
        raise RuntimeError("Library verification requires a clean worktree; use a fresh clone or checkpoint first")


def _read_member(package_dir: Path, name: str) -> bytes:
    if not package_dir.is_dir() or package_dir.is_symlink():
        raise RuntimeError("Experience library package directory must be a real directory")
    try:
        names = {child.name for child in package_dir.iterdir()}
    except OSError as error:
        raise RuntimeError("Experience library package directory is not readable") from error
    expected_names = set(LIBRARY_PACKAGE_MEMBER_NAMES) | {LIBRARY_PACKAGE_MANIFEST_NAME}
    if names != expected_names:
        raise RuntimeError("Experience library package must contain exactly its fixed four public-safe files")
    path = package_dir / name
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Experience library package member must be a regular file: " + name)
    try:
        return path.read_bytes()
    except OSError as error:
        raise RuntimeError("Experience library package member is not readable: " + name) from error


def _verify_source_member(path: Path, expected: Path, label: str) -> str:
    try:
        actual_bytes = path.read_bytes()
        expected_bytes = expected.read_bytes()
    except OSError as error:
        raise RuntimeError(label + " is not readable") from error
    if actual_bytes != expected_bytes:
        raise RuntimeError(label + " does not exactly match the clean exact-head source file")
    return hashlib.sha256(actual_bytes).hexdigest()


def verify_library_package(
    package_dir: Path,
    expected_head: str | None = None,
    *,
    require_clean_worktree: bool = True,
) -> dict[str, Any]:
    """Return evidence only when every library package byte rebuilds exactly."""

    head = _git_head()
    if expected_head is not None and head != expected_head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    if require_clean_worktree:
        _require_clean_worktree()
    members = {name: _read_member(package_dir, name) for name in LIBRARY_PACKAGE_MEMBER_NAMES}
    manifest_bytes = _read_member(package_dir, LIBRARY_PACKAGE_MANIFEST_NAME)
    try:
        supplied_manifest = json.loads(manifest_bytes.decode("utf-8"))
        supplied_library = json.loads(members["experience_library.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Experience library package JSON is not readable") from error
    if not isinstance(supplied_manifest, Mapping) or not isinstance(supplied_library, Mapping):
        raise RuntimeError("Experience library package JSON roots must be objects")
    expected_manifest = build_library_package_manifest(head, members)
    if canonical_json(supplied_manifest) != canonical_json(expected_manifest):
        raise RuntimeError("Experience library package manifest does not exactly match its fixed members and exact head")
    try:
        expected_library = verify_verified_experience_library(head, supplied_library)
    except ValueError as error:
        raise RuntimeError("Experience library does not exactly match the clean exact-head synthetic rebuild") from error
    if canonical_json(supplied_library) != canonical_json(expected_library.to_dict()):
        raise RuntimeError("Experience library does not exactly match its declared exact-head rebuild")
    if canonical_json(supplied_library) != canonical_json(build_verified_experience_library(head).to_dict()):
        raise RuntimeError("Experience library omits or changes the required exact-head scenario set")
    player_hash = _verify_source_member(package_dir / "verified_experience_player.html", PLAYER_SOURCE, "Static player")
    guide_hash = _verify_source_member(package_dir / "README.md", PLAYER_GUIDE_SOURCE, "Static player guide")
    return {
        "schema": "CreativeRuntimeExperienceLibraryPackageVerificationReceipt/v1",
        "status": "experience_library_package_exactly_verified",
        "head_sha": head,
        "library_id": expected_library.library_id,
        "scenario_count": len(expected_library.entries),
        "scenarios": [entry["scenario"] for entry in expected_library.entries],
        "manifest_sha256": sha256_hex(manifest_bytes),
        "library_sha256": sha256_hex(members["experience_library.json"]),
        "player_sha256": player_hash,
        "guide_sha256": guide_hash,
        "package_member_count": len(LIBRARY_PACKAGE_MEMBER_NAMES),
        "worktree_status": "clean_required_and_clean" if require_clean_worktree else "not_checked_for_verifier_self_test",
        "boundary": dict(expected_library.to_dict()["boundary"]),
        "authority_note": "Offline reproducibility evidence only; this verifier cannot approve release, deployment, or customer intake.",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verify a downloaded offline multi-scenario experience-library package at an exact git head.")
    parser.add_argument("--package-dir", required=True, type=Path, help="Downloaded four-file library package directory.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before verification.")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify_library_package(args.package_dir, args.expected_head), ensure_ascii=False, sort_keys=True, indent=2))
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
