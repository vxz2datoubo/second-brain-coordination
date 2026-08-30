"""Build one deterministic, offline multi-scenario experience-library package."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creative_runtime.contracts import canonical_json
from creative_runtime.experience_library import build_verified_experience_library
from creative_runtime.experience_library_package import (
    LIBRARY_PACKAGE_MANIFEST_NAME,
    LIBRARY_PACKAGE_MEMBER_NAMES,
    build_library_package_manifest,
)
from creative_runtime.experience_package import sha256_hex


def _git_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("Cannot resolve git HEAD: " + result.stderr.strip())
    return result.stdout.strip()


def build_library_package(output_dir: Path, expected_head: str | None = None) -> dict[str, object]:
    """Create a new fixed-layout package atomically and never overwrite it."""

    if output_dir.exists():
        raise RuntimeError("Experience library package output directory already exists")
    head = _git_head()
    if expected_head is not None and head != expected_head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_dir.with_name(output_dir.name + ".building-" + uuid.uuid4().hex)
    try:
        temporary.mkdir()
        library = build_verified_experience_library(head).to_dict()
        members = {
            "experience_library.json": (canonical_json(library) + "\n").encode("utf-8"),
            "verified_experience_player.html": (ROOT / "apps" / "web" / "verified_experience_player.html").read_bytes(),
            "README.md": (ROOT / "apps" / "web" / "README.md").read_bytes(),
        }
        manifest = build_library_package_manifest(head, members)
        for name in LIBRARY_PACKAGE_MEMBER_NAMES:
            (temporary / name).write_bytes(members[name])
        manifest_bytes = (canonical_json(manifest) + "\n").encode("utf-8")
        (temporary / LIBRARY_PACKAGE_MANIFEST_NAME).write_bytes(manifest_bytes)
        os.replace(temporary, output_dir)
    except OSError as error:
        raise RuntimeError("Cannot build deterministic experience library package") from error
    return {
        "status": "experience_library_package_built",
        "head_sha": head,
        "output_dir": str(output_dir),
        "scenario_count": library["entry_count"],
        "member_count": len(LIBRARY_PACKAGE_MEMBER_NAMES),
        "manifest_sha256": sha256_hex(manifest_bytes),
        "boundary": dict(library["boundary"]),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic offline multi-scenario interactive-film package directory.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before building.")
    parser.add_argument("--output-dir", required=True, type=Path, help="New output directory; it must not already exist.")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build_library_package(args.output_dir, args.expected_head), ensure_ascii=False, sort_keys=True))
    except (RuntimeError, ValueError) as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
