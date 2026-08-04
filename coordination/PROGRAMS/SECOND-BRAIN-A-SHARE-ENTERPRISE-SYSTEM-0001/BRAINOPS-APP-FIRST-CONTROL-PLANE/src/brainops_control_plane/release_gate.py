"""Repository-backed, fail-closed E48 pre-receipt release gate.

The gate derives repository facts itself.  A provider manifest from the same
job is only *pre-evidence*: it cannot certify that the workflow ultimately
finished or that no later branch commit exists.  Those two facts remain an
independent review-time gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

from .authority_surface import validate_single_positive_authority
from .receipt_scope import receipt_paths_are_evidence_only
from .workflow_policy import validate_e48_workflow


class ReleaseGateCode(str, Enum):
    PRE_EVIDENCE_READY = "PRE_EVIDENCE_READY"
    GIT_UNAVAILABLE = "GIT_UNAVAILABLE"
    HEAD_MISMATCH = "HEAD_MISMATCH"
    BASE_NOT_ANCESTOR = "BASE_NOT_ANCESTOR"
    PATH_OUTSIDE_ALLOWLIST = "PATH_OUTSIDE_ALLOWLIST"
    REQUIRED_INPUT_MISSING = "REQUIRED_INPUT_MISSING"
    AUTHORITY_SURFACE_INVALID = "AUTHORITY_SURFACE_INVALID"
    PROVIDER_PRE_EVIDENCE_INVALID = "PROVIDER_PRE_EVIDENCE_INVALID"
    WORKTREE_DIRTY = "WORKTREE_DIRTY"
    WORKFLOW_POLICY_INVALID = "WORKFLOW_POLICY_INVALID"


@dataclass(frozen=True)
class ReleaseGateResult:
    code: ReleaseGateCode
    evidence: dict[str, object]
    findings: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.code is ReleaseGateCode.PRE_EVIDENCE_READY

    def canonical_json(self) -> str:
        document = {
            "code": self.code.value,
            "evidence": self.evidence,
            "findings": list(self.findings),
        }
        return json.dumps(document, ensure_ascii=True, sort_keys=True, separators=(",", ":"))

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ReceiptTopologyResult:
    ready: bool
    receipt_head: str
    tested_head: str
    changed_paths: tuple[str, ...]
    findings: tuple[str, ...] = ()

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "changed_paths": list(self.changed_paths),
                "findings": list(self.findings),
                "receipt_head": self.receipt_head,
                "ready": self.ready,
                "tested_head": self.tested_head,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )


_PROGRAM = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/"
_WORKFLOW = ".github/workflows/brainops-e48.yml"
_REQUIRED_FILES = (
    _PROGRAM + "E48/E48-EXECUTION-PLAN.md",
    _PROGRAM + "E48/IMPORTED-SOURCE-MANIFEST.yaml",
)


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout.strip()


def _provider_pre_evidence(path: Path | None, head: str) -> tuple[dict[str, object] | None, str | None]:
    if path is None:
        return None, None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "provider_pre_evidence_unreadable"
    if not isinstance(value, dict):
        return None, "provider_pre_evidence_not_object"
    expected = {
        "workflow": "brainops-e48.yml",
        "head_sha": head,
        "python_versions": ["3.11", "3.13"],
    }
    if any(value.get(key) != expected[key] for key in expected):
        return None, "provider_pre_evidence_binding_mismatch"
    return {key: value[key] for key in expected}, None


def validate_repository_release_gate(
    repository_root: Path,
    program_root: Path,
    expected_head: str,
    base_head: str,
    provider_pre_evidence: Path | None = None,
) -> ReleaseGateResult:
    """Validate checked-out facts; never accept a caller-created success object."""

    try:
        head = _git(repository_root, "rev-parse", "HEAD")
        _git(repository_root, "cat-file", "-e", f"{head}^{{commit}}")
        dirty_paths = tuple(
            line
            for line in _git(repository_root, "status", "--porcelain", "--untracked-files=all").splitlines()
            if line
        )
        ancestor = subprocess.run(
            ["git", "-C", str(repository_root), "merge-base", "--is-ancestor", base_head, head],
            check=False,
            capture_output=True,
        ).returncode == 0
    except (OSError, RuntimeError):
        return ReleaseGateResult(ReleaseGateCode.GIT_UNAVAILABLE, {}, ("git_facts_unavailable",))
    if head != expected_head:
        return ReleaseGateResult(ReleaseGateCode.HEAD_MISMATCH, {"observed_head": head}, ("expected_head_mismatch",))
    provider, provider_error = _provider_pre_evidence(provider_pre_evidence, head)
    if provider_error is not None:
        return ReleaseGateResult(
            ReleaseGateCode.PROVIDER_PRE_EVIDENCE_INVALID,
            {"head": head},
            (provider_error,),
        )
    if dirty_paths:
        return ReleaseGateResult(
            ReleaseGateCode.WORKTREE_DIRTY,
            {"head": head, "dirty_paths": list(dirty_paths)},
            ("checked_out_tree_is_not_exact_commit",),
        )
    if not ancestor:
        return ReleaseGateResult(
            ReleaseGateCode.BASE_NOT_ANCESTOR,
            {"head": head, "base_head": base_head},
            ("base_is_not_ancestor",),
        )
    changed = tuple(
        line
        for line in _git(repository_root, "diff", "--name-only", f"{base_head}..{head}").splitlines()
        if line
    )
    outside = tuple(path for path in changed if not (path.startswith(_PROGRAM) or path == _WORKFLOW))
    if outside:
        return ReleaseGateResult(
            ReleaseGateCode.PATH_OUTSIDE_ALLOWLIST,
            {"head": head, "base_head": base_head, "changed_paths": list(changed)},
            outside,
        )
    missing = tuple(path for path in _REQUIRED_FILES if not (repository_root / path).is_file())
    if missing:
        return ReleaseGateResult(
            ReleaseGateCode.REQUIRED_INPUT_MISSING,
            {"head": head, "base_head": base_head},
            missing,
        )
    workflow = validate_e48_workflow(repository_root / _WORKFLOW)
    if not workflow.ready:
        return ReleaseGateResult(
            ReleaseGateCode.WORKFLOW_POLICY_INVALID,
            {"head": head, "workflow_policy": {"code": workflow.code.value, "findings": list(workflow.findings)}},
            workflow.findings,
        )
    surface = validate_single_positive_authority(program_root)
    if not surface.ready:
        return ReleaseGateResult(
            ReleaseGateCode.AUTHORITY_SURFACE_INVALID,
            {"head": head, "authority_surface": surface.document()},
            surface.violations,
        )
    return ReleaseGateResult(
        ReleaseGateCode.PRE_EVIDENCE_READY,
        {
            "head": head,
            "base_head": base_head,
            "changed_paths": list(changed),
            "authority_surface": surface.document(),
            "provider_pre_evidence": provider,
            "final_provider_conclusion": "PENDING_INDEPENDENT_REVIEW",
            "post_receipt_immutability": "PENDING_GPT_REMOTE_HEAD_RECHECK",
        },
    )


def validate_receipt_topology(
    repository_root: Path,
    tested_head: str,
    receipt_head: str,
) -> ReceiptTopologyResult:
    """Ensure the final receipt is a nonempty evidence-only child of tested head."""

    try:
        actual_parent = _git(repository_root, "rev-parse", f"{receipt_head}^")
        changed_paths = tuple(
            line
            for line in _git(repository_root, "diff", "--name-only", f"{tested_head}..{receipt_head}").splitlines()
            if line
        )
    except (OSError, RuntimeError):
        return ReceiptTopologyResult(False, receipt_head, tested_head, (), ("git_facts_unavailable",))
    findings: list[str] = []
    if actual_parent != tested_head:
        findings.append("receipt_parent_is_not_tested_head")
    if not changed_paths:
        findings.append("receipt_commit_is_empty")
    if changed_paths and not receipt_paths_are_evidence_only(changed_paths):
        findings.append("receipt_contains_runtime_or_out_of_scope_path")
    return ReceiptTopologyResult(
        not findings,
        receipt_head,
        tested_head,
        changed_paths,
        tuple(findings),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--program-root", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--base-head", required=True)
    parser.add_argument("--provider-pre-evidence")
    parser.add_argument("--output")
    arguments = parser.parse_args(argv)
    result = validate_repository_release_gate(
        Path(arguments.repository_root),
        Path(arguments.program_root),
        arguments.expected_head,
        arguments.base_head,
        None if arguments.provider_pre_evidence is None else Path(arguments.provider_pre_evidence),
    )
    payload = result.canonical_json()
    if arguments.output:
        Path(arguments.output).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result.ready else 1


if __name__ == "__main__":
    sys.exit(main())
