"""Read-only local validation CLI. It prints aggregate receipts, never raw records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from local_adapter.contracts import deserialize_contract

from .contracts import SourceActivationPolicy
from .tdx_day import TdxDaySourceAdapter


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("mapping_required")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="p3-offline-memory")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate-day", help="Validate one local .day artifact read-only")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--activation-policy", type=Path, required=True)
    validate.add_argument("--artifact", type=Path, required=True)
    validate.add_argument("--as-of", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "validate-day":
        return 2
    manifest = deserialize_contract("SourceManifest", _load_yaml(args.manifest))
    policy = SourceActivationPolicy(**_load_yaml(args.activation_policy))
    result = TdxDaySourceAdapter(args.artifact, policy).load(manifest, args.as_of)
    print(json.dumps({
        "status": result.status.value,
        "reason_codes": list(result.reason_codes),
        "payload": result.payload,
        "authority_write": result.authority_write,
        "no_trade_gate": result.no_trade_gate,
    }, ensure_ascii=True, sort_keys=True))
    return 0 if result.status.value == "PARTIALLY_VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
