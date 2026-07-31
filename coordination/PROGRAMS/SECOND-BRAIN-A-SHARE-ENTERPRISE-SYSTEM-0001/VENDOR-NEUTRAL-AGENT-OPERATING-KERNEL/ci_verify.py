"""Emit deterministic, public-safe CI evidence for the candidate kernel."""

from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import subprocess
import unittest

import yaml


KERNEL_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = KERNEL_ROOT.parents[3]
TEST_ROOT = KERNEL_ROOT / "tests"
SOURCE_ROOT = KERNEL_ROOT / "src"
SKILL_PATH = (
    REPOSITORY_ROOT
    / "coordination"
    / "SKILLS"
    / "VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL-GOVERNANCE-SKILL-v1.0.yaml"
)
SOURCE_AUDIT_PATH = KERNEL_ROOT / "SOURCE-EXPRESSION-AUDIT.yaml"
CASE_MANIFEST_PATH = KERNEL_ROOT / "CASE-MANIFEST.yaml"


class _StrictLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "duplicate key: " + str(key),
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


class _CaseLedger(unittest.TestResult):
    def __init__(self) -> None:
        super().__init__()
        self.case_ids: list[str] = []
        self.failure_ids: list[str] = []
        self.error_ids: list[str] = []
        self.skipped_ids: list[str] = []

    def startTest(self, test) -> None:  # noqa: N802 - unittest API
        super().startTest(test)
        self.case_ids.append(test.id())

    def addFailure(self, test, err) -> None:  # noqa: N802 - unittest API
        super().addFailure(test, err)
        self.failure_ids.append(test.id())

    def addError(self, test, err) -> None:  # noqa: N802 - unittest API
        super().addError(test, err)
        self.error_ids.append(test.id())

    def addSkip(self, test, reason) -> None:  # noqa: N802 - unittest API
        super().addSkip(test, reason)
        self.skipped_ids.append(test.id())


def _sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _run_tests() -> _CaseLedger:
    sys.path[:0] = [str(SOURCE_ROOT), str(TEST_ROOT)]
    suite = unittest.defaultTestLoader.discover(str(TEST_ROOT), pattern="test_*.py")
    result = _CaseLedger()
    suite.run(result)
    return result


def _strict_yaml_check() -> int:
    paths = tuple(sorted(KERNEL_ROOT.rglob("*.yaml"))) + (SKILL_PATH,)
    for path in paths:
        yaml.load(_read_text(path), Loader=_StrictLoader)
    return len(paths)


def _ast_check() -> int:
    paths = tuple(sorted(KERNEL_ROOT.rglob("*.py")))
    for path in paths:
        ast.parse(_read_text(path), filename=str(path))
    return len(paths)


def _read_changed_files(path: Path | None) -> tuple[Path, ...]:
    if path is None:
        return tuple(sorted(item for item in KERNEL_ROOT.rglob("*") if item.is_file()))
    changed: list[Path] = []
    for line in _read_text(path).splitlines():
        candidate = line.strip().lstrip("\ufeff")
        if not candidate:
            continue
        resolved = REPOSITORY_ROOT / candidate
        if not resolved.is_file():
            raise ValueError("CHANGED_FILE_NOT_PRESENT:" + candidate)
        changed.append(resolved)
    return tuple(sorted(set(changed)))


def _verify_exact_context(commit: str, tree: str) -> dict[str, str]:
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise ValueError("IMMUTABLE_CONTEXT_SHA_INVALID")
    git_dir = REPOSITORY_ROOT / ".git"
    if not git_dir.exists():
        return {"requested_commit": commit, "requested_tree": tree, "repository_check": "ARCHIVE_NO_GIT_METADATA"}
    head = subprocess.check_output(
        ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    actual_tree = subprocess.check_output(
        ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", f"{head}^{{tree}}"], text=True
    ).strip()
    if head != commit or actual_tree != tree:
        raise ValueError("IMMUTABLE_CONTEXT_MISMATCH")
    return {"requested_commit": commit, "requested_tree": tree, "repository_check": "EXACT_HEAD_AND_TREE"}


def _case_manifest_check(case_ids: tuple[str, ...]) -> int:
    manifest = yaml.load(_read_text(CASE_MANIFEST_PATH), Loader=_StrictLoader)
    if not isinstance(manifest, dict) or manifest.get("status") != "FROZEN_CANDIDATE_MANIFEST":
        raise ValueError("CASE_MANIFEST_STATUS_INVALID")
    expected = tuple(manifest.get("case_ids", ()))
    if expected != case_ids:
        raise ValueError("CASE_MANIFEST_MISMATCH")
    return len(expected)


def _public_safety_check(changed_files: tuple[Path, ...]) -> dict[str, int]:
    secret_pattern = re.compile(
        r"(?:ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})"
    )
    secret_matches = 0
    for path in changed_files:
        if path.suffix.lower() in {".py", ".md", ".yaml", ".yml", ".json", ".txt"}:
            secret_matches += len(secret_pattern.findall(_read_text(path)))
    if secret_matches:
        raise ValueError("CHANGED_FILE_SECRET_MATCHES:" + str(secret_matches))

    common_prompt = KERNEL_ROOT / "AGENT-OPERATING-KERNEL-PROMPT-v1.0.md"
    prohibited_tokens = ("anthropic", "claude", "openai", "chatgpt")
    prompt = _read_text(common_prompt).lower()
    leaked = tuple(token for token in prohibited_tokens if token in prompt)
    if leaked:
        raise ValueError("COMMON_PROMPT_VENDOR_LEAKAGE:" + ",".join(leaked))

    raw_files = tuple(
        path
        for path in KERNEL_ROOT.rglob("*")
        if path.is_file() and "opus-5.md" in path.name.lower()
    )
    if raw_files:
        raise ValueError("RAW_CAPTURE_FILE_PRESENT")

    source_audit = yaml.load(_read_text(SOURCE_AUDIT_PATH), Loader=_StrictLoader)
    if source_audit.get("conclusion") != "NO_DISTINCTIVE_EXPRESSION_OR_STRUCTURE_TRANSFER":
        raise ValueError("SOURCE_EXPRESSION_AUDIT_NOT_CLEAR")
    return {
        "changed_files_scanned": len(changed_files),
        "secret_matches": secret_matches,
        "common_prompt_vendor_matches": len(leaked),
        "raw_capture_files": len(raw_files),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--changed-files", type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tree", required=True)
    args = parser.parse_args()

    result = _run_tests()
    static = {
        "python_ast_files": _ast_check(),
        "strict_yaml_files": _strict_yaml_check(),
        **_public_safety_check(_read_changed_files(args.changed_files)),
    }
    case_ids = tuple(sorted(result.case_ids))
    error_ids = tuple(sorted(result.error_ids))
    failure_ids = tuple(sorted(result.failure_ids))
    skipped_ids = tuple(sorted(result.skipped_ids))
    manifest_count = _case_manifest_check(case_ids)
    exact_context = _verify_exact_context(args.commit, args.tree)
    status = "PASS" if not error_ids and not failure_ids else "FAIL"
    report = {
        "schema": "VNAK_CI_EVIDENCE_v1",
        "commit": args.commit,
        "tree": args.tree,
        "status": status,
        "tests_run": result.testsRun,
        "case_ids": case_ids,
        "failure_ids": failure_ids,
        "error_ids": error_ids,
        "skipped_ids": skipped_ids,
        "stdout_sha256": _sha256_text("\n".join(case_ids)),
        "stderr_sha256": _sha256_text("\n".join(error_ids + failure_ids)),
        "checks": static,
        "case_manifest_count": manifest_count,
        "exact_context": exact_context,
    }
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
