"""Write one exact-head, exhaustive synthetic replay corpus without overwriting."""

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
from creative_runtime.replay_corpus import ReplayCorpusViolation, build_verified_synthetic_replay_corpus


def _git_head(expected_head: str | None) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("Cannot resolve replay corpus source Git head: " + result.stderr.strip())
    head = result.stdout.strip()
    if expected_head is not None and expected_head != head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    return head


def build_corpus(output_file: Path, expected_head: str | None = None) -> dict[str, object]:
    """Create a new corpus file; reject pre-existing paths rather than replace."""

    if output_file.exists() or output_file.is_symlink():
        raise RuntimeError("Replay corpus output file already exists")
    head = _git_head(expected_head)
    corpus = build_verified_synthetic_replay_corpus(head).to_dict()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_file.write_text(canonical_json(corpus) + "\n", encoding="utf-8", newline="\n")
    except OSError as error:
        raise RuntimeError("Cannot write replay corpus output file") from error
    return {
        "schema": "CreativeSyntheticReplayCorpusBuildReceipt/v1",
        "status": "synthetic_replay_corpus_built",
        "head_sha": head,
        "corpus_id": corpus["corpus_id"],
        "entry_count": corpus["entry_count"],
        "scenario_route_counts": corpus["scenario_route_counts"],
        "output_file": str(output_file),
        "boundary": dict(corpus["boundary"]),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build an exhaustive, synthetic-only replay corpus at an exact Git head.")
    parser.add_argument("--expected-head", help="Require this exact source Git SHA before building.")
    parser.add_argument("--output-file", required=True, type=Path, help="New JSON output file; it must not already exist.")
    args = parser.parse_args(argv)
    try:
        receipt = build_corpus(args.output_file, args.expected_head)
    except (ReplayCorpusViolation, RuntimeError, OSError) as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
