"""Run E57 Provider evidence verification from an exact disposable Git archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e57_authority.clean_archive import verify_from_clean_archive
from e57_authority.core import AuthorityError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--head", required=True)
    parser.add_argument("--tested", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--tested-head", required=True)
    parser.add_argument("--receipt-head", required=True)
    parser.add_argument("--expected-tested-evidence-digest", required=True)
    parser.add_argument("--expected-receipt-evidence-digest", required=True)
    parser.add_argument("--out", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        result = verify_from_clean_archive(
            repo=arguments.repo,
            head=arguments.head,
            tested_path=arguments.tested,
            receipt_path=arguments.receipt,
            tested_head=arguments.tested_head,
            receipt_head=arguments.receipt_head,
            expected_tested_evidence_digest=arguments.expected_tested_evidence_digest,
            expected_receipt_evidence_digest=arguments.expected_receipt_evidence_digest,
        )
        arguments.out.write_bytes(json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    except AuthorityError as exc:
        print(f"Clean-archive Provider verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
