"""Write public-safe E54 canonical and environment evidence artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from e54_authority import MUTATION_SPECS
from e54_authority.provider_evidence import build_canonical_evidence, build_environment_evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--test-count", required=True, type=int)
    parser.add_argument("--command", required=True)
    parser.add_argument("--stdout", required=True, type=Path)
    parser.add_argument("--stderr", required=True, type=Path)
    parser.add_argument("--canonical-output", required=True, type=Path)
    parser.add_argument("--environment-output", required=True, type=Path)
    parser.add_argument("--hash-seed", required=True)
    args = parser.parse_args()
    mutation_ids = [item.mutation_id for item in MUTATION_SPECS]
    canonical = build_canonical_evidence(head_sha=args.head_sha, test_count=args.test_count, mutation_ids=mutation_ids)
    environment = build_environment_evidence(
        head_sha=args.head_sha, test_count=args.test_count, mutation_ids=mutation_ids,
        command=args.command, stdout=args.stdout.read_bytes(), stderr=args.stderr.read_bytes(),
        canonical_artifact=canonical, hash_seed=args.hash_seed,
    )
    args.canonical_output.parent.mkdir(parents=True, exist_ok=True)
    args.environment_output.parent.mkdir(parents=True, exist_ok=True)
    args.canonical_output.write_bytes(canonical)
    args.environment_output.write_text(json.dumps(environment, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
