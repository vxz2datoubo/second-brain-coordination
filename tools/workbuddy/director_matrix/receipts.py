"""Hashed receipts and the offline CLI for the director coverage matrix (WB-S2).

The receipt stores SHA-256 digests and counts, matching the runbook rule that
captured output is represented by hashes rather than copied bodies.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from typing import Any, Mapping, Sequence

from . import SCHEMA, matrix


def sha256_of(payload: Any) -> str:
    """Return the SHA-256 of a canonical JSON rendering of ``payload``."""

    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def environment() -> dict[str, Any]:
    """Declare the local runtime used for one matrix run."""

    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "machine": platform.machine(),
        "schema": SCHEMA,
    }


def run() -> dict[str, Any]:
    """Run the matrix and return the full receipt body."""

    body = matrix.run_matrix()
    body["environment"] = environment()
    body["evidence_class"] = "WORKBUDDY_EXECUTOR_VERIFIED"
    body["receipt_sha256"] = sha256_of(body["rows"])
    return body


def render(report: Mapping[str, Any]) -> str:
    """Render a receipt as canonical JSON text."""

    return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)


def _main(argv: Sequence[str]) -> int:
    print(render(run()))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
