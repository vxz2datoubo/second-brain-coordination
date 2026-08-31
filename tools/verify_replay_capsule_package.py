"""Rebuild and verify a downloaded synthetic replay-capsule package offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creative_runtime.contracts import canonical_json
from creative_runtime.experience_package import sha256_hex
from creative_runtime.replay_capsule import ReplayCapsuleViolation, verify_verified_replay_capsule
from creative_runtime.replay_capsule_package import (
    REPLAY_CAPSULE_PACKAGE_MANIFEST_NAME,
    REPLAY_CAPSULE_PACKAGE_MEMBER_NAMES,
    build_replay_capsule_package_manifest,
)


PLAYER_SOURCE = ROOT / "apps" / "web" / "verified_replay_capsule_player.html"
GUIDE_SOURCE = ROOT / "apps" / "web" / "replay_capsule_README.md"


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
        raise RuntimeError("Replay capsule package verification requires a clean worktree")


def _read_member(package_dir: Path, name: str) -> bytes:
    if not package_dir.is_dir() or package_dir.is_symlink():
        raise RuntimeError("Replay capsule package directory must be a real directory")
    try:
        names = {child.name for child in package_dir.iterdir()}
    except OSError as error:
        raise RuntimeError("Replay capsule package directory is not readable") from error
    expected_names = set(REPLAY_CAPSULE_PACKAGE_MEMBER_NAMES) | {REPLAY_CAPSULE_PACKAGE_MANIFEST_NAME}
    if names != expected_names:
        raise RuntimeError("Replay capsule package must contain exactly its fixed four synthetic-only files")
    path = package_dir / name
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Replay capsule package member must be a regular file: " + name)
    try:
        return path.read_bytes()
    except OSError as error:
        raise RuntimeError("Replay capsule package member is not readable: " + name) from error


def verify_package(
    package_dir: Path,
    expected_head: str | None = None,
    *,
    require_clean_worktree: bool = True,
) -> dict[str, Any]:
    """Verify member bytes, manifest, exact head, and runtime reconstruction."""

    head = _git_head()
    if expected_head is not None and expected_head != head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    if require_clean_worktree:
        _require_clean_worktree()
    members = {name: _read_member(package_dir, name) for name in REPLAY_CAPSULE_PACKAGE_MEMBER_NAMES}
    manifest_bytes = _read_member(package_dir, REPLAY_CAPSULE_PACKAGE_MANIFEST_NAME)
    try:
        supplied_manifest = json.loads(manifest_bytes.decode("utf-8"))
        supplied_capsule = json.loads(members["replay_capsule.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Replay capsule package JSON is not readable UTF-8 JSON") from error
    expected_manifest = build_replay_capsule_package_manifest(head, members)
    if canonical_json(supplied_manifest) != canonical_json(expected_manifest):
        raise RuntimeError("Replay capsule package manifest does not match its exact head and fixed members")
    if not isinstance(supplied_capsule, Mapping):
        raise RuntimeError("Replay capsule package payload root must be an object")
    try:
        verified = verify_verified_replay_capsule(supplied_capsule)
    except ReplayCapsuleViolation as error:
        raise RuntimeError("Replay capsule package payload cannot be rebuilt safely") from error
    if members["verified_replay_capsule_player.html"] != PLAYER_SOURCE.read_bytes():
        raise RuntimeError("Replay capsule player does not match the exact-head source file")
    if members["README.md"] != GUIDE_SOURCE.read_bytes():
        raise RuntimeError("Replay capsule guide does not match the exact-head source file")
    return {
        "schema": "CreativeSyntheticReplayCapsulePackageVerificationReceipt/v1",
        "status": "replay_capsule_package_exactly_verified",
        "head_sha": head,
        "scenario": verified.scenario,
        "capsule_id": verified.capsule_id,
        "timeline_hash": verified.timeline_hash,
        "event_count": verified.event_count,
        "manifest_sha256": sha256_hex(manifest_bytes),
        "package_member_count": len(REPLAY_CAPSULE_PACKAGE_MEMBER_NAMES),
        "worktree_status": "clean_required_and_clean" if require_clean_worktree else "not_checked_for_verifier_self_test",
        "boundary": dict(verified.payload["boundary"]),
        "authority_note": "Offline reproducibility evidence only; this verifier cannot approve release, deployment, or customer intake.",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verify a downloaded synthetic replay capsule package at an exact Git head.")
    parser.add_argument("--package-dir", required=True, type=Path, help="Downloaded fixed replay capsule package directory.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before verification.")
    args = parser.parse_args(argv)
    try:
        receipt = verify_package(args.package_dir, args.expected_head)
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
