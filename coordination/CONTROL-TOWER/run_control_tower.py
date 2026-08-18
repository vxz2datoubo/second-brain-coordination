from __future__ import annotations

import argparse
import json
from pathlib import Path

from control_tower import (
    AGENT_FILES,
    PROJECTION,
    load_yaml,
    normalize_route,
    projection_matches,
    render_projection_block,
    replace_projection_block,
    route_witness,
    scan_repository,
    verify_route_witness,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Program Control Tower fail-closed scanner/reconciler")
    parser.add_argument("command", choices=["check", "projection", "witness", "verify-witness"])
    parser.add_argument("--repo-root", default="../..")
    parser.add_argument("--agent", choices=sorted(AGENT_FILES))
    parser.add_argument("--witness-file")
    parser.add_argument("--write", action="store_true", help="write the generated projection block")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.repo_root).resolve()

    if args.command == "check":
        report = scan_repository(root)
        report["projection_matches"] = projection_matches(root)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if report["foundation_structural_check"] == "PASS" and report["projection_matches"] else 2

    if args.command == "projection":
        block = render_projection_block(root)
        if args.write:
            path = root / PROJECTION
            current = path.read_text(encoding="utf-8") if path.exists() else "# AI系统 Program Control Tower\n"
            path.write_text(replace_projection_block(current, block), encoding="utf-8")
            return 0
        print(block)
        return 0 if projection_matches(root) else 2

    if not args.agent:
        raise SystemExit("--agent is required")
    route = normalize_route(args.agent, load_yaml(root / AGENT_FILES[args.agent]))

    if args.command == "witness":
        print(json.dumps(route_witness(route), ensure_ascii=False, sort_keys=True, indent=2))
        return 0

    if not args.witness_file:
        raise SystemExit("--witness-file is required")
    expected = json.loads(Path(args.witness_file).read_text(encoding="utf-8"))
    ok = verify_route_witness(expected, route)
    print(
        json.dumps(
            {"agent": args.agent, "fresh": ok, "current": route_witness(route)},
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
