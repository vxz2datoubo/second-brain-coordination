from __future__ import annotations

import argparse
from pathlib import Path

from claim_projection import claim_projection_matches, render_claim_projection_block, replace_claim_projection_block
from control_tower import PROJECTION


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or verify the Control Tower work-claim projection")
    parser.add_argument("command", choices=["check", "write", "show"])
    parser.add_argument("--repo-root", default="../..")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.repo_root).resolve()
    block = render_claim_projection_block(root)
    if args.command == "show":
        print(block)
        return 0
    if args.command == "check":
        ok = claim_projection_matches(root)
        print("CLAIM_PROJECTION_MATCH" if ok else "CLAIM_PROJECTION_DRIFT")
        return 0 if ok else 2
    path = root / PROJECTION
    current = path.read_text(encoding="utf-8")
    path.write_text(replace_claim_projection_block(current, block), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
