"""Create a byte-bound compare manifest from downloaded provider artifacts."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.root)
    artifacts: list[dict[str, object]] = []
    for environment in sorted(root.rglob("environment.json")):
        directory = environment.parent
        if not directory.name.startswith("environment-"):
            raise RuntimeError(f"unexpected environment artifact directory {directory.name}")
        canonical = root / directory.name.replace("environment-", "canonical-", 1) / "canonical.json"
        if not canonical.exists():
            raise RuntimeError(f"missing canonical peer for {environment}")
        artifacts.append({"path": environment.relative_to(root).as_posix(), "sha256": digest(environment)})
        artifacts.append({"path": canonical.relative_to(root).as_posix(), "sha256": digest(canonical)})
    if len(artifacts) != 12:
        raise RuntimeError("expected exactly six canonical and six environment evidence files")
    digest_list = sorted(str(item["sha256"]) for item in artifacts)
    body = {"schema": "e55-provider-compare-v1", "artifacts": artifacts, "artifact_digests": digest_list, "combined_sha256": sha256("".join(digest_list).encode("ascii")).hexdigest()}
    Path(args.output).write_bytes(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
