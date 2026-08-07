"""Fail closed unless every downloaded E59 canonical source manifest matches."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        raise SystemExit("usage: compare_provider_artifacts.py <artifact-root>")
    root = Path(arguments[1])
    manifests = sorted(root.rglob("canonical-source-manifest.json"))
    if len(manifests) != 6:
        raise SystemExit(f"EXPECTED_SIX_CANONICAL_MANIFESTS_GOT_{len(manifests)}")
    digests = {sha256(path.read_bytes()).hexdigest() for path in manifests}
    if len(digests) != 1:
        raise SystemExit("CANONICAL_INNER_FILES_NOT_BYTE_IDENTICAL")
    payload = {
        "schema_version": "1.0",
        "manifest_count": len(manifests),
        "canonical_manifest_sha256": next(iter(digests)),
        "status": "PASS",
    }
    Path("provider-compare.json").write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
