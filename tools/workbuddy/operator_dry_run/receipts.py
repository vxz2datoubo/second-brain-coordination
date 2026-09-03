"""Hashed receipts and the offline CLI for the operator dry run (WB-S3)."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from typing import Any, Mapping, Sequence

from . import SCHEMA, operator


def sha256_of(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def environment() -> dict[str, Any]:
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "machine": platform.machine(),
        "schema": SCHEMA,
    }


def run() -> dict[str, Any]:
    body = operator.run_dry_run()
    body["environment"] = environment()
    body["receipt_sha256"] = sha256_of(body["handoff_receipt"])
    return body


def render(report: Mapping[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)


def _main(argv: Sequence[str]) -> int:
    print(render(run()))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
