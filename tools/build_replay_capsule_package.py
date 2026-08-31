"""Build a portable package for one verified, synthetic interactive replay."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.cli import creativectl
from creative_runtime.contracts import canonical_json
from creative_runtime.replay_capsule import ReplayCapsuleViolation, verify_verified_replay_capsule
from creative_runtime.replay_capsule_package import (
    REPLAY_CAPSULE_PACKAGE_MANIFEST_NAME,
    REPLAY_CAPSULE_PACKAGE_MEMBER_NAMES,
    build_replay_capsule_package_manifest,
)


PLAYER_SOURCE = ROOT / "apps" / "web" / "verified_replay_capsule_player.html"
GUIDE_SOURCE = ROOT / "apps" / "web" / "replay_capsule_README.md"


def _git_head(expected_head: str | None) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("Cannot resolve package source Git head: " + result.stderr.strip())
    head = result.stdout.strip()
    if expected_head is not None and expected_head != head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    return head


def build_package(
    output_dir: Path,
    workspace: Path,
    *,
    slot: str = "default",
    expected_head: str | None = None,
) -> dict[str, Any]:
    """Write a new fixed package, never overwriting a caller path.

    The runtime rebuild rejects any caller-authored ``say`` text before this
    function can write an output directory.  The resulting package is therefore
    limited to a fixed-graph, synthetic-choice route even if it originated from
    a local workspace.
    """

    if output_dir.exists():
        raise RuntimeError("Replay capsule package output directory already exists")
    head = _git_head(expected_head)
    capsule = creativectl.run(["--workspace", str(workspace), "--slot", slot, "replay-capsule"])
    verified = verify_verified_replay_capsule(capsule)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_dir.with_name(output_dir.name + ".building-" + uuid.uuid4().hex)
    try:
        temporary.mkdir()
        members = {
            "replay_capsule.json": (canonical_json(verified.to_dict()) + "\n").encode("utf-8"),
            "verified_replay_capsule_player.html": PLAYER_SOURCE.read_bytes(),
            "README.md": GUIDE_SOURCE.read_bytes(),
        }
        manifest = build_replay_capsule_package_manifest(head, members)
        for name in REPLAY_CAPSULE_PACKAGE_MEMBER_NAMES:
            (temporary / name).write_bytes(members[name])
        (temporary / REPLAY_CAPSULE_PACKAGE_MANIFEST_NAME).write_text(
            canonical_json(manifest) + "\n", encoding="utf-8"
        )
        os.replace(temporary, output_dir)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return {
        "schema": "CreativeSyntheticReplayCapsulePackageBuildReceipt/v1",
        "status": "replay_capsule_package_built",
        "head_sha": head,
        "scenario": verified.scenario,
        "capsule_id": verified.capsule_id,
        "timeline_hash": verified.timeline_hash,
        "event_count": verified.event_count,
        "output_dir": str(output_dir),
        "member_count": len(REPLAY_CAPSULE_PACKAGE_MEMBER_NAMES),
        "boundary": dict(verified.payload["boundary"]),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build a fixed, synthetic-only verified replay capsule package.")
    parser.add_argument("--workspace", required=True, type=Path, help="Local workspace containing a synthetic fixed-choice route.")
    parser.add_argument("--slot", default="default", help="Validated runtime save-slot identifier.")
    parser.add_argument("--expected-head", help="Require this exact source Git SHA before building.")
    parser.add_argument("--output-dir", required=True, type=Path, help="New package directory; it must not already exist.")
    args = parser.parse_args(argv)
    try:
        receipt = build_package(args.output_dir, args.workspace, slot=args.slot, expected_head=args.expected_head)
    except (ReplayCapsuleViolation, RuntimeError, ValueError, OSError) as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
