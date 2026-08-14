from __future__ import annotations

import argparse
import json
from pathlib import Path

from lane_claims import validate_claims


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Program Lane work claims and proposal-only release envelope")
    parser.add_argument("--repo-root", default="../..")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = validate_claims(Path(args.repo_root))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["claim_structural_check"] == "PASS" and report["proposal_only_candidate"] != "NOT_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
