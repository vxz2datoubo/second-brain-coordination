"""Produce deterministic, public-safe source-manifest evidence for E59 CI."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys


TASK_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TASK_ROOT, text=True).strip()


def main() -> int:
    include_roots = [TASK_ROOT / "src", TASK_ROOT / "tests", TASK_ROOT / "tools"]
    files = sorted(path for root in include_roots for path in root.rglob("*.py"))
    entries = [
        {
            "path": path.relative_to(TASK_ROOT).as_posix(),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in files
    ]
    canonical = {
        "schema_version": "1.0",
        "task_id": "CODEX-E59",
        "files": entries,
        "source_bundle_sha256": sha256(json.dumps(entries, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest(),
    }
    provider = {
        "schema_version": "1.0",
        "task_id": "CODEX-E59",
        "tested_head": _git_head(),
        "python_version": sys.version.split()[0],
        "pythonhashseed": __import__("os").environ.get("PYTHONHASHSEED", "UNSET"),
        "canonical_source_manifest_sha256": sha256(json.dumps(canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest(),
    }
    (TASK_ROOT / "canonical-source-manifest.json").write_text(json.dumps(canonical, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (TASK_ROOT / "provider-evidence.json").write_text(json.dumps(provider, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
