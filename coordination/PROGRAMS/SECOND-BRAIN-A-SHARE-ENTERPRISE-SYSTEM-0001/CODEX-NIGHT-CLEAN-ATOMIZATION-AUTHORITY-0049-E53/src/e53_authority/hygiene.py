"""Public-safe commit-range hygiene checks for the E53 delivery surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Iterable


FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".sqlite", ".db", ".jsonl", ".env")
FORBIDDEN_PARTS = ("__pycache__", "provider-artifacts", "local-artifacts", "private")


@dataclass(frozen=True, slots=True)
class HygieneReport:
    base: str
    head: str
    changed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not self.forbidden_paths


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=False, capture_output=True, text=True, encoding="utf-8", errors="strict")
    if result.returncode != 0:
        raise RuntimeError(f"git command failed: {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def scan_commit_range(repo: Path, base: str, head: str = "HEAD") -> HygieneReport:
    output = _git(repo, "diff", "--name-only", f"{base}..{head}")
    paths = tuple(sorted(path.replace("\\", "/") for path in output.splitlines() if path.strip()))
    forbidden = tuple(
        path
        for path in paths
        if path.lower().endswith(FORBIDDEN_SUFFIXES) or any(part in path.lower().split("/") for part in FORBIDDEN_PARTS)
    )
    return HygieneReport(base, _git(repo, "rev-parse", head).strip(), paths, forbidden)
