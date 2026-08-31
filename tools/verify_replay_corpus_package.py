"""Rebuild and verify a downloaded exhaustive replay-corpus package offline."""

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
from creative_runtime.replay_corpus import ReplayCorpusViolation, verify_verified_synthetic_replay_corpus
from creative_runtime.replay_corpus_package import (
    REPLAY_CORPUS_PACKAGE_MANIFEST_NAME,
    REPLAY_CORPUS_PACKAGE_MEMBER_NAMES,
    build_replay_corpus_package_manifest,
)
from creative_runtime.replay_review import ReplayReviewViolation, verify_verified_replay_review_board


VIEWER_SOURCE = ROOT / "apps" / "web" / "verified_replay_corpus_viewer.html"
GUIDE_SOURCE = ROOT / "apps" / "web" / "replay_corpus_README.md"


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
        raise RuntimeError("Replay corpus package verification requires a clean worktree")


def _read_member(package_dir: Path, name: str) -> bytes:
    if not package_dir.is_dir() or package_dir.is_symlink():
        raise RuntimeError("Replay corpus package directory must be a real directory")
    try:
        names = {child.name for child in package_dir.iterdir()}
    except OSError as error:
        raise RuntimeError("Replay corpus package directory is not readable") from error
    expected_names = set(REPLAY_CORPUS_PACKAGE_MEMBER_NAMES) | {REPLAY_CORPUS_PACKAGE_MANIFEST_NAME}
    if names != expected_names:
        raise RuntimeError("Replay corpus package must contain exactly its fixed four synthetic-only files")
    path = package_dir / name
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Replay corpus package member must be a regular file: " + name)
    try:
        return path.read_bytes()
    except OSError as error:
        raise RuntimeError("Replay corpus package member is not readable: " + name) from error


def verify_package(
    package_dir: Path,
    expected_head: str | None = None,
    *,
    require_clean_worktree: bool = True,
) -> dict[str, Any]:
    """Accept the package only when every fixed byte and route rebuilds exactly."""

    head = _git_head()
    if expected_head is not None and expected_head != head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    if require_clean_worktree:
        _require_clean_worktree()
    members = {name: _read_member(package_dir, name) for name in REPLAY_CORPUS_PACKAGE_MEMBER_NAMES}
    manifest_bytes = _read_member(package_dir, REPLAY_CORPUS_PACKAGE_MANIFEST_NAME)
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        corpus = json.loads(members["replay_corpus.json"].decode("utf-8"))
        review_board = json.loads(members["replay_review_board.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Replay corpus package JSON is not readable UTF-8 JSON") from error
    if not isinstance(manifest, Mapping) or not isinstance(corpus, Mapping) or not isinstance(review_board, Mapping):
        raise RuntimeError("Replay corpus package JSON roots must be objects")
    expected_manifest = build_replay_corpus_package_manifest(head, members)
    if canonical_json(manifest) != canonical_json(expected_manifest):
        raise RuntimeError("Replay corpus package manifest does not match its exact head and fixed members")
    try:
        verified = verify_verified_synthetic_replay_corpus(head, corpus)
    except ReplayCorpusViolation as error:
        raise RuntimeError("Replay corpus package cannot be exactly rebuilt at this Git head") from error
    try:
        verified_review_board = verify_verified_replay_review_board(head, corpus, review_board)
    except ReplayReviewViolation as error:
        raise RuntimeError("Replay corpus package review board cannot be exactly rebuilt at this Git head") from error
    if members["verified_replay_corpus_viewer.html"] != VIEWER_SOURCE.read_bytes():
        raise RuntimeError("Replay corpus viewer does not match the exact-head source file")
    if members["README.md"] != GUIDE_SOURCE.read_bytes():
        raise RuntimeError("Replay corpus guide does not match the exact-head source file")
    return {
        "schema": "CreativeSyntheticReplayCorpusPackageVerificationReceipt/v1",
        "status": "replay_corpus_package_exactly_verified",
        "head_sha": head,
        "corpus_id": verified.corpus_id,
        "review_board_id": verified_review_board["review_board_id"],
        "entry_count": len(verified.entries),
        "branch_point_count": verified_review_board["branch_point_count"],
        "scenario_route_counts": verified.to_dict()["scenario_route_counts"],
        "corpus_sha256": sha256_hex(members["replay_corpus.json"]),
        "review_board_sha256": sha256_hex(members["replay_review_board.json"]),
        "manifest_sha256": sha256_hex(manifest_bytes),
        "package_member_count": len(REPLAY_CORPUS_PACKAGE_MEMBER_NAMES),
        "worktree_status": "clean_required_and_clean" if require_clean_worktree else "not_checked_for_verifier_self_test",
        "boundary": dict(verified.to_dict()["boundary"]),
        "authority_note": "Offline synthetic regression evidence only; this verifier cannot approve release, deployment, paid generation, or customer intake.",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verify a downloaded exhaustive replay-corpus package at an exact Git head.")
    parser.add_argument("--package-dir", required=True, type=Path, help="Downloaded fixed five-file package directory.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before verification.")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify_package(args.package_dir, args.expected_head), ensure_ascii=False, sort_keys=True, indent=2))
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
