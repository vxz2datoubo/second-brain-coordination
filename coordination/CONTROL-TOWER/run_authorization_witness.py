from __future__ import annotations

import argparse
import json
from pathlib import Path

from authorization_witness import authorization_witness, verify_authorization_witness


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or verify a Program Lane durable-authorization witness")
    parser.add_argument("command", choices=["create", "verify"])
    parser.add_argument("--repo-root", default="../..")
    parser.add_argument("--lane", required=True)
    parser.add_argument("--witness-file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.repo_root)
    if args.command == "create":
        print(json.dumps(authorization_witness(root, args.lane), ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    if not args.witness_file:
        raise SystemExit("--witness-file is required for verify")
    witness = json.loads(Path(args.witness_file).read_text(encoding="utf-8"))
    report = verify_authorization_witness(root, witness)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["fresh"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
