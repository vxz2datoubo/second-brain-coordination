"""Manual-only CLI for validation or a locally approved, loopback console start."""

from __future__ import annotations

import argparse
import json

from .web import ConsoleSnapshot, create_server


def _snapshot() -> ConsoleSnapshot:
    return ConsoleSnapshot(
        status={"mode": "READ_ONLY_AND_SHADOW_ONLY", "automatic_dispatch": False},
        services=[],
        ports=[],
        audit=[],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="BrainOps E35 control-plane utility")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="print the static fail-closed status")
    serve = subparsers.add_parser("serve", help="manual loopback-only read-only console")
    serve.add_argument("--port", type=int, default=32100)
    args = parser.parse_args()
    if args.command == "validate":
        print(json.dumps(_snapshot().payload("status"), sort_keys=True))
        return 0
    server = create_server(_snapshot(), args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
