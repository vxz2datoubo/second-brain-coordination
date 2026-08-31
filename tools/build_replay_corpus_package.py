"""Build a portable, exact-head package for exhaustive synthetic replay evidence."""

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

from creative_runtime.contracts import canonical_json
from creative_runtime.experience_package import sha256_hex
from creative_runtime.replay_corpus import build_verified_synthetic_replay_corpus
from creative_runtime.replay_corpus_package import (
    REPLAY_CORPUS_PACKAGE_MANIFEST_NAME,
    REPLAY_CORPUS_PACKAGE_MEMBER_NAMES,
    build_replay_corpus_package_manifest,
)


VIEWER_SOURCE = ROOT / "apps" / "web" / "verified_replay_corpus_viewer.html"
GUIDE_SOURCE = ROOT / "apps" / "web" / "replay_corpus_README.md"


def _git_head(expected_head: str | None) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("Cannot resolve replay corpus package source Git head: " + result.stderr.strip())
    head = result.stdout.strip()
    if expected_head is not None and expected_head != head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {head}")
    return head


def build_package(output_dir: Path, expected_head: str | None = None) -> dict[str, Any]:
    """Create a new four-file package atomically; never replace a caller path."""

    if output_dir.exists() or output_dir.is_symlink():
        raise RuntimeError("Replay corpus package output directory already exists")
    head = _git_head(expected_head)
    corpus = build_verified_synthetic_replay_corpus(head).to_dict()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_dir.with_name(output_dir.name + ".building-" + uuid.uuid4().hex)
    try:
        temporary.mkdir()
        members = {
            "replay_corpus.json": (canonical_json(corpus) + "\n").encode("utf-8"),
            "verified_replay_corpus_viewer.html": VIEWER_SOURCE.read_bytes(),
            "README.md": GUIDE_SOURCE.read_bytes(),
        }
        manifest = build_replay_corpus_package_manifest(head, members)
        for name in REPLAY_CORPUS_PACKAGE_MEMBER_NAMES:
            (temporary / name).write_bytes(members[name])
        manifest_bytes = (canonical_json(manifest) + "\n").encode("utf-8")
        (temporary / REPLAY_CORPUS_PACKAGE_MANIFEST_NAME).write_bytes(manifest_bytes)
        os.replace(temporary, output_dir)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return {
        "schema": "CreativeSyntheticReplayCorpusPackageBuildReceipt/v1",
        "status": "replay_corpus_package_built",
        "head_sha": head,
        "corpus_id": corpus["corpus_id"],
        "entry_count": corpus["entry_count"],
        "scenario_route_counts": corpus["scenario_route_counts"],
        "output_dir": str(output_dir),
        "member_count": len(REPLAY_CORPUS_PACKAGE_MEMBER_NAMES),
        "manifest_sha256": sha256_hex(manifest_bytes),
        "boundary": dict(corpus["boundary"]),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build a fixed, offline replay-corpus package at one exact Git head.")
    parser.add_argument("--expected-head", help="Require this exact source Git SHA before building.")
    parser.add_argument("--output-dir", required=True, type=Path, help="New package directory; it must not already exist.")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build_package(args.output_dir, args.expected_head), ensure_ascii=False, sort_keys=True))
    except (RuntimeError, ValueError, OSError) as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
