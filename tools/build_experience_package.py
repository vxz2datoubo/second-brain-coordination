"""Build one deterministic, public-safe GitHub experience package directory."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import uuid


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creative_runtime.contracts import canonical_json
from creative_runtime.demo_routes import GITHUB_DEMO_ROUTES
from creative_runtime.experience_package import PACKAGE_MANIFEST_NAME, PACKAGE_MEMBER_NAMES, build_package_manifest, sha256_hex
from build_experience_demo import build_demo_artifact


def build_package(output_dir: Path, expected_head: str | None = None, scenario: str = "night_signal") -> dict[str, object]:
    """Create a new package directory atomically; refuse to overwrite an output."""

    if output_dir.exists():
        raise RuntimeError("Experience package output directory already exists")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_dir.with_name(output_dir.name + ".building-" + uuid.uuid4().hex)
    try:
        temporary.mkdir()
        artifact = build_demo_artifact(expected_head, scenario)
        members = {
            "experience.json": (canonical_json(artifact) + "\n").encode("utf-8"),
            "verified_experience_player.html": (ROOT / "apps" / "web" / "verified_experience_player.html").read_bytes(),
            "README.md": (ROOT / "apps" / "web" / "README.md").read_bytes(),
        }
        manifest = build_package_manifest(artifact["head_sha"], members)
        for name in PACKAGE_MEMBER_NAMES:
            (temporary / name).write_bytes(members[name])
        manifest_bytes = (canonical_json(manifest) + "\n").encode("utf-8")
        (temporary / PACKAGE_MANIFEST_NAME).write_bytes(manifest_bytes)
        os.replace(temporary, output_dir)
    except OSError as error:
        raise RuntimeError("Cannot build deterministic experience package") from error
    return {
        "status": "experience_package_built",
        "head_sha": artifact["head_sha"],
        "scenario": scenario,
        "output_dir": str(output_dir),
        "member_count": len(PACKAGE_MEMBER_NAMES),
        "manifest_sha256": sha256_hex(manifest_bytes),
        "boundary": dict(artifact["boundary"]),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic synthetic interactive-film package directory.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before building.")
    parser.add_argument("--scenario", choices=sorted(GITHUB_DEMO_ROUTES), default="night_signal", help="Reviewed synthetic scenario to package.")
    parser.add_argument("--output-dir", required=True, type=Path, help="New output directory; it must not already exist.")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build_package(args.output_dir, args.expected_head, args.scenario), ensure_ascii=False, sort_keys=True))
    except (RuntimeError, ValueError) as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
