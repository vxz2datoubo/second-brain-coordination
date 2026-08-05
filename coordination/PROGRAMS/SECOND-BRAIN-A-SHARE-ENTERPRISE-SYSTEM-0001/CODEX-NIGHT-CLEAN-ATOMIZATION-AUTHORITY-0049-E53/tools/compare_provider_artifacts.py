"""Fail closed unless exactly six canonical artifacts exist and match byte-for-byte."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidates = tuple(sorted(args.artifact_root.rglob("canonical-evidence.json")))
    if len(candidates) != 6:
        raise SystemExit(f"expected exactly 6 canonical artifacts, found {len(candidates)}")
    blobs = [path.read_bytes() for path in candidates]
    if any(blob != blobs[0] for blob in blobs[1:]):
        raise SystemExit("canonical evidence artifacts are not byte-identical")
    evidence = {
        "schema_version": "e53-provider-compare.1",
        "artifact_count": len(candidates),
        "canonical_sha256": sha256(blobs[0]).hexdigest(),
        "artifact_relative_paths": [str(path.relative_to(args.artifact_root)).replace("\\", "/") for path in candidates],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(json.dumps(evidence, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
