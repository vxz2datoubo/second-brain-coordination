"""Verify a downloaded synthetic replay corpus by exact source reconstruction."""

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

from creative_runtime.replay_corpus import ReplayCorpusViolation, verify_verified_synthetic_replay_corpus


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
        raise RuntimeError("Replay corpus verification requires a clean worktree")


def verify_corpus(
    path: Path,
    expected_head: str | None = None,
    *,
    require_clean_worktree: bool = True,
) -> dict[str, Any]:
    """Read one corpus file and accept it only when its exact rebuild agrees."""

    head = _git_head()
    if expected_head is not None and expected_head != head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    if require_clean_worktree:
        _require_clean_worktree()
    try:
        raw = path.read_bytes()
        supplied = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Replay corpus is not readable UTF-8 JSON") from error
    if not isinstance(supplied, Mapping):
        raise RuntimeError("Replay corpus root must be a JSON object")
    try:
        verified = verify_verified_synthetic_replay_corpus(head, supplied)
    except ReplayCorpusViolation as error:
        raise RuntimeError("Replay corpus cannot be exactly rebuilt at this Git head") from error
    return {
        "schema": "CreativeSyntheticReplayCorpusVerificationReceipt/v1",
        "status": "synthetic_replay_corpus_exactly_verified",
        "head_sha": head,
        "corpus_id": verified.corpus_id,
        "entry_count": len(verified.entries),
        "scenario_ids": [entry for entry in supplied["scenario_ids"]],
        "corpus_sha256": hashlib.sha256(raw).hexdigest(),
        "worktree_status": "clean_required_and_clean" if require_clean_worktree else "not_checked_for_verifier_self_test",
        "authority_note": "Offline synthetic regression evidence only; this verifier cannot approve release, deployment, paid generation, or customer intake.",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verify an exhaustive synthetic replay corpus at an exact Git head.")
    parser.add_argument("--corpus", required=True, type=Path, help="Downloaded/generated synthetic replay corpus JSON file.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before verification.")
    args = parser.parse_args(argv)
    try:
        receipt = verify_corpus(args.corpus, args.expected_head)
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
