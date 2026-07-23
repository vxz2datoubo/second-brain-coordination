"""Public-safe delivery scan for the integrated Phase 3 surface."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[3]
SCAN_ROOTS = (
    ROOT,
    REPO_ROOT / "coordination" / "PROGRAMS" / "SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001" / "PHASE-4-FULL-KNOWLEDGE-GATEWAY",
    REPO_ROOT / "coordination" / "EVIDENCE" / "WORKBUDDY-LOCAL-MOTHER-SYSTEM-READONLY-PROBE-0001",
    REPO_ROOT / ".github" / "workflows" / "phase3-integrated-offline-memory.yml",
)
FORBIDDEN_SUFFIXES = {
    ".day", ".sqlite", ".sqlite3", ".db", ".wal", ".shm", ".log", ".pyc", ".dll", ".zip"
}
SECRET_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


def scan() -> dict[str, object]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if root.is_file():
            files.append(root)
        elif root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file())
    files = sorted({path.resolve() for path in files})
    issues: list[str] = []
    scanned = 0
    for path in files:
        if "__pycache__" in path.parts or path.suffix.casefold() == ".pyc":
            continue
        scanned += 1
        if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            issues.append(f"forbidden_artifact:{path.relative_to(REPO_ROOT)}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            issues.append(f"non_text_artifact:{path.relative_to(REPO_ROOT)}")
            continue
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            issues.append(f"secret_shaped_value:{path.relative_to(REPO_ROOT)}")
    return {
        "status": "PASS" if not issues else "FAIL",
        "files_scanned": scanned,
        "issues": issues,
        "scope": "phase3_package_pr52_public_safe_evidence_and_ci_workflow",
    }


def main() -> int:
    report = scan()
    print(f"status={report['status']} files_scanned={report['files_scanned']} issues={len(report['issues'])}")
    for issue in report["issues"]:
        print(issue)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
