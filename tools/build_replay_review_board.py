"""Build a deterministic, exact-head synthetic replay review board."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creative_runtime.contracts import canonical_json
from creative_runtime.replay_corpus import build_verified_synthetic_replay_corpus
from creative_runtime.replay_review import ReplayReviewViolation, build_verified_replay_review_board


def _git_head(expected_head: str | None) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("Cannot resolve replay review source Git head: " + result.stderr.strip())
    head = result.stdout.strip()
    if expected_head is not None and expected_head != head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    return head


def build_review_board(output_file: Path, expected_head: str | None = None) -> dict[str, object]:
    """Write a new review board without overwriting any caller-supplied path."""

    if output_file.exists() or output_file.is_symlink():
        raise RuntimeError("Replay review board output file already exists")
    head = _git_head(expected_head)
    corpus = build_verified_synthetic_replay_corpus(head).to_dict()
    board = build_verified_replay_review_board(head, corpus)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_file.write_text(canonical_json(board) + "\n", encoding="utf-8", newline="\n")
    except OSError as error:
        raise RuntimeError("Cannot write replay review board output file") from error
    return {
        "schema": "CreativeSyntheticReplayReviewBoardBuildReceipt/v1",
        "status": "synthetic_replay_review_board_built",
        "head_sha": head,
        "review_board_id": board["review_board_id"],
        "corpus_id": board["corpus_id"],
        "branch_point_count": board["branch_point_count"],
        "output_file": str(output_file),
        "boundary": dict(board["boundary"]),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build a synthetic, exact-head replay review board without overwriting output.")
    parser.add_argument("--expected-head", help="Require this exact source Git SHA before building.")
    parser.add_argument("--output-file", required=True, type=Path, help="New JSON output file; it must not already exist.")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build_review_board(args.output_file, args.expected_head), ensure_ascii=False, sort_keys=True))
    except (ReplayReviewViolation, RuntimeError, OSError) as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
