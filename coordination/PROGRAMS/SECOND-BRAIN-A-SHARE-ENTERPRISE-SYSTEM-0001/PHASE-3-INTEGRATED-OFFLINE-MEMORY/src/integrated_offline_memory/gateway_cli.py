"""Public-safe command line checks for local candidate gateway artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .learning_packet import verify_learning_packet


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="superbrain-knowledge-gateway")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate-packet")
    validate.add_argument("--input", required=True)
    try:
        args = parser.parse_args(argv)
        if args.command == "validate-packet":
            return _validate_packet(Path(args.input))
    except SystemExit as exc:
        return int(exc.code)
    return 2


def _validate_packet(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        _error("PACKET_READ_OR_JSON_INVALID", "provide_a_readable_utf8_json_learning_packet")
        return 2
    verdict = verify_learning_packet(payload)
    if not verdict["valid"]:
        _error("PACKET_VALIDATION_FAILED", "repair_reported_contract_fields_before_import", verdict["errors"])
        return 3
    print(json.dumps({
        "status": "VALID",
        "packet_id": payload["packet_id"],
        "authority_write": False,
        "no_trade_gate": True,
    }, sort_keys=True))
    return 0


def _error(error_code: str, repair_hint: str, errors: list[str] | None = None) -> None:
    print(json.dumps({
        "status": "ERROR",
        "error_code": error_code,
        "errors": errors or [],
        "repair_hint": repair_hint,
    }, sort_keys=True), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
