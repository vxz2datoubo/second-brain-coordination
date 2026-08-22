"""Fail closed unless the six canonical artifacts are byte-identical."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    arguments = parser.parse_args()
    candidates = tuple(sorted(arguments.root.rglob("canonical.json")))
    if len(candidates) != 6:
        print(f"expected six canonical artifacts, found {len(candidates)}", file=sys.stderr)
        return 1
    payloads = tuple(path.read_bytes() for path in candidates)
    if len(set(payloads)) != 1:
        print("canonical artifacts differ", file=sys.stderr)
        return 1
    arguments.out.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": "e57-provider-compare-v1",
        "canonical_count": len(candidates),
        "canonical_sha256": sha256(payloads[0]).hexdigest(),
        "paths": [path.as_posix() for path in candidates],
    }
    (arguments.out / "provider-compare.json").write_bytes(json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
