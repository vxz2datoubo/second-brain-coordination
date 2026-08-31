"""Verify a downloaded synthetic replay review board by exact derivation."""

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

from creative_runtime.replay_corpus import build_verified_synthetic_replay_corpus
from creative_runtime.replay_review import ReplayReviewViolation, verify_verified_replay_review_board


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
        raise RuntimeError("Replay review verification requires a clean worktree")


def verify_review_board(path: Path, expected_head: str | None = None, *, require_clean_worktree: bool = True) -> dict[str, Any]:
    """Read a review board and accept it only when source reconstruction agrees."""

    head = _git_head()
    if expected_head is not None and expected_head != head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    if require_clean_worktree:
        _require_clean_worktree()
    try:
        raw = path.read_bytes()
        board = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Replay review board is not readable UTF-8 JSON") from error
    if not isinstance(board, Mapping):
        raise RuntimeError("Replay review board root must be an object")
    corpus = build_verified_synthetic_replay_corpus(head).to_dict()
    try:
        verified = verify_verified_replay_review_board(head, corpus, board)
    except ReplayReviewViolation as error:
        raise RuntimeError("Replay review board cannot be exactly rebuilt at this Git head") from error
    return {
        "schema": "CreativeSyntheticReplayReviewBoardVerificationReceipt/v1",
        "status": "synthetic_replay_review_board_exactly_verified",
        "head_sha": head,
        "review_board_id": verified["review_board_id"],
        "corpus_id": verified["corpus_id"],
        "branch_point_count": verified["branch_point_count"],
        "review_board_sha256": hashlib.sha256(raw).hexdigest(),
        "worktree_status": "clean_required_and_clean" if require_clean_worktree else "not_checked_for_verifier_self_test",
        "boundary": dict(verified["boundary"]),
        "authority_note": "Offline synthetic review evidence only; this verifier cannot accept a product, release, deployment, generation, or customer intake.",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verify a synthetic replay review board at an exact Git head.")
    parser.add_argument("--board", required=True, type=Path, help="Downloaded/generated review board JSON file.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before verification.")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify_review_board(args.board, args.expected_head), ensure_ascii=False, sort_keys=True, indent=2))
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
