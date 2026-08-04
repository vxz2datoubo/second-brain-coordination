"""Fail-closed E49 release evidence verification.

The module deliberately separates an in-job observation from an external
post-run provider fact.  A workflow job can prepare an observation for review,
but it cannot certify that its own run is complete or that the branch received
no later commit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys
from typing import Iterable


_TASK_ID = (
    "CODEX-BRAINOPS-CRASH-COMPLETE-STAGE-JOURNAL-PROVIDER-RELEASE-"
    "EVIDENCE-AND-PLACEHOLDER-FREE-RECEIPT-CLOSURE-0045-E49"
)
_PROGRAM = (
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
    "BRAINOPS-APP-FIRST-CONTROL-PLANE/"
)
_PLAN = _PROGRAM + "E49/E49-EXECUTION-PLAN.md"
_RECEIPT = _PROGRAM + "E49/RECEIPT/"
_ROUTE = "coordination/ACTIVE-CODEX-TASK.yaml"
_BRIEF = (
    "coordination/TASK-BRIEFS/CODEX-BRAINOPS-CRASH-COMPLETE-STAGE-JOURNAL-"
    "PROVIDER-RELEASE-EVIDENCE-AND-PLACEHOLDER-FREE-RECEIPT-CLOSURE-0045-E49-AMED.yaml"
)
_WORKFLOW = "brainops-e49.yml"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_RECEIPT_TOKENS = (
    "RESOLVED_MECHANICALLY_AFTER_COMMIT",
    "receipt_commit_sha",
    "self_commit_sha",
    "TODO",
    "TBD",
    "$head",
)


class E49ReleaseCode(str, Enum):
    PRE_REVIEW_EVIDENCE_RECORDED = "PRE_REVIEW_EVIDENCE_RECORDED"
    READY_FOR_INDEPENDENT_REVIEW = "READY_FOR_INDEPENDENT_REVIEW"
    PROVIDER_EVIDENCE_UNTRUSTED = "PROVIDER_EVIDENCE_UNTRUSTED"
    PROVIDER_RUN_INVALID = "PROVIDER_RUN_INVALID"
    PROVIDER_JOB_INVALID = "PROVIDER_JOB_INVALID"
    PROVIDER_ARTIFACT_INVALID = "PROVIDER_ARTIFACT_INVALID"
    ROUTE_BINDING_INVALID = "ROUTE_BINDING_INVALID"
    GIT_GRAPH_INVALID = "GIT_GRAPH_INVALID"
    RECEIPT_TOPOLOGY_INVALID = "RECEIPT_TOPOLOGY_INVALID"
    RECEIPT_PLACEHOLDER = "RECEIPT_PLACEHOLDER"
    EVIDENCE_FAMILY_MISSING = "EVIDENCE_FAMILY_MISSING"
    REPRODUCTION_INVALID = "REPRODUCTION_INVALID"


@dataclass(frozen=True)
class ProviderJob:
    job_id: int
    name: str
    python_version: str
    head_sha: str
    conclusion: str
    test_count: int


@dataclass(frozen=True)
class ProviderArtifact:
    artifact_id: int
    name: str
    head_sha: str
    digest: str
    expired: bool


@dataclass(frozen=True)
class ProviderRun:
    run_id: int
    workflow: str
    head_sha: str
    status: str
    conclusion: str
    jobs: tuple[ProviderJob, ...]
    artifacts: tuple[ProviderArtifact, ...]


@dataclass(frozen=True)
class E49ProviderEvidence:
    provider_source: str | None
    declared_success: bool
    tested_head: str | None
    receipt_head: str | None
    remote_branch_head: str | None
    runs: tuple[ProviderRun, ...]

    @classmethod
    def from_document(cls, value: object) -> "E49ProviderEvidence":
        if not isinstance(value, dict):
            return cls(None, False, None, None, None, ())
        runs: list[ProviderRun] = []
        for candidate in value.get("runs", []):
            if not isinstance(candidate, dict):
                continue
            jobs = tuple(
                ProviderJob(
                    item.get("job_id", -1),
                    item.get("name", ""),
                    item.get("python_version", ""),
                    item.get("head_sha", ""),
                    item.get("conclusion", ""),
                    item.get("test_count", -1),
                )
                for item in candidate.get("jobs", [])
                if isinstance(item, dict)
            )
            artifacts = tuple(
                ProviderArtifact(
                    item.get("artifact_id", -1),
                    item.get("name", ""),
                    item.get("head_sha", ""),
                    item.get("digest", ""),
                    bool(item.get("expired", True)),
                )
                for item in candidate.get("artifacts", [])
                if isinstance(item, dict)
            )
            runs.append(
                ProviderRun(
                    candidate.get("run_id", -1),
                    candidate.get("workflow", ""),
                    candidate.get("head_sha", ""),
                    candidate.get("status", ""),
                    candidate.get("conclusion", ""),
                    jobs,
                    artifacts,
                )
            )
        return cls(
            value.get("provider_source") if isinstance(value.get("provider_source"), str) else None,
            value.get("declared_success") is True,
            value.get("tested_head") if isinstance(value.get("tested_head"), str) else None,
            value.get("receipt_head") if isinstance(value.get("receipt_head"), str) else None,
            value.get("remote_branch_head") if isinstance(value.get("remote_branch_head"), str) else None,
            tuple(runs),
        )


@dataclass(frozen=True)
class E49ReleaseResult:
    code: E49ReleaseCode
    findings: tuple[str, ...] = ()
    evidence: dict[str, object] | None = None

    @property
    def ready(self) -> bool:
        return self.code is E49ReleaseCode.READY_FOR_INDEPENDENT_REVIEW

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "code": self.code.value,
                "evidence": self.evidence or {},
                "findings": list(self.findings),
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _git(repository_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout.strip()


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _provider_run_for(evidence: E49ProviderEvidence, head: str) -> ProviderRun | None:
    for run in evidence.runs:
        if (
            run.workflow == _WORKFLOW
            and run.head_sha == head
            and run.status == "completed"
            and run.conclusion == "success"
            and isinstance(run.run_id, int)
            and run.run_id > 0
        ):
            return run
    return None


def _validate_provider_run(run: ProviderRun, head: str) -> E49ReleaseResult | None:
    jobs = {job.python_version: job for job in run.jobs}
    for version in ("3.11", "3.13"):
        job = jobs.get(version)
        if (
            job is None
            or job.job_id <= 0
            or job.head_sha != head
            or job.conclusion != "success"
            or job.test_count <= 0
        ):
            return E49ReleaseResult(
                E49ReleaseCode.PROVIDER_JOB_INVALID,
                (f"missing_or_invalid_python_{version}_job",),
            )
    artifacts = {artifact.name: artifact for artifact in run.artifacts}
    for version in ("3.11", "3.13"):
        artifact = artifacts.get(f"e49-release-evidence-{version}")
        if (
            artifact is None
            or artifact.artifact_id <= 0
            or artifact.head_sha != head
            or artifact.expired
            or _DIGEST.fullmatch(artifact.digest) is None
        ):
            return E49ReleaseResult(
                E49ReleaseCode.PROVIDER_ARTIFACT_INVALID,
                (f"missing_or_invalid_python_{version}_artifact",),
            )
    return None


def _documents_text(documents: dict[str, str] | None) -> str:
    if not documents:
        return ""
    return "\n".join(f"{name}\n{content}" for name, content in sorted(documents.items()))


def read_e49_receipt_documents(repository_root: Path) -> dict[str, str]:
    """Read only public-safe E49 receipt files from the checked-out tree."""

    directory = repository_root / _RECEIPT
    documents: dict[str, str] = {}
    try:
        candidates = tuple(directory.iterdir())
    except OSError:
        return documents
    for path in candidates:
        if path.is_file() and path.suffix in {".md", ".yaml", ".json"}:
            try:
                documents[path.name] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return {}
    return documents


def _validate_receipt_documents(
    documents: dict[str, str] | None, tested_head: str
) -> E49ReleaseResult | None:
    if not documents:
        return E49ReleaseResult(E49ReleaseCode.EVIDENCE_FAMILY_MISSING, ("receipt_documents_missing",))
    names = set(documents)
    required = {
        "AMED-EXECUTION-RECEIPT.yaml",
        "TEST-RUN-RECEIPT.json",
        "UNKNOWN-REGISTRY.yaml",
        "AI_HANDOFF.yaml",
        "RESEARCH-LEDGER.md",
        "UNPLANNED-IMPROVEMENT-LEDGER.md",
        "SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md",
        "WORK-PROCESS-AND-COORDINATION-REPORT.md",
        "RECEIPT-MANIFEST.json",
    }
    missing = tuple(sorted(required - names))
    if missing:
        return E49ReleaseResult(E49ReleaseCode.EVIDENCE_FAMILY_MISSING, missing)
    combined = _documents_text(documents)
    if any(token in combined for token in _FORBIDDEN_RECEIPT_TOKENS):
        return E49ReleaseResult(E49ReleaseCode.RECEIPT_PLACEHOLDER, ("forbidden_receipt_token",))
    if "receipt_commit_identity: EXTERNAL_POST_COMMIT_PROVIDER_FACT" not in combined:
        return E49ReleaseResult(
            E49ReleaseCode.RECEIPT_PLACEHOLDER,
            ("external_non_self_identity_marker_missing",),
        )
    command = "python -m brainops_control_plane.release_verifier"
    if command not in combined or tested_head not in combined:
        return E49ReleaseResult(
            E49ReleaseCode.REPRODUCTION_INVALID,
            ("executable_e49_reproduction_command_missing",),
        )
    return None


def _route_and_brief_are_bound(repository_root: Path) -> bool:
    try:
        route = (repository_root / _ROUTE).read_text(encoding="utf-8")
        brief = (repository_root / _BRIEF).read_text(encoding="utf-8")
    except OSError:
        return False
    required = (_TASK_ID, "route_epoch: 51", "planned_branch: \"codex/brainops-crash-complete-stage-journal-release-evidence-0045-e49\"")
    return all(value in route for value in required) and _TASK_ID in brief


def receipt_paths_are_e49_evidence_only(paths: Iterable[str]) -> bool:
    checked = tuple(paths)
    return bool(checked) and all(
        path.startswith(_RECEIPT) and path.endswith((".md", ".yaml", ".json"))
        for path in checked
    )


def _validate_git_graph(
    repository_root: Path,
    base_head: str,
    plan_head: str,
    tested_head: str,
    receipt_head: str | None,
) -> E49ReleaseResult | None:
    try:
        if _git(repository_root, "rev-parse", f"{plan_head}^") != base_head:
            return E49ReleaseResult(E49ReleaseCode.GIT_GRAPH_INVALID, ("plan_parent_mismatch",))
        first_paths = tuple(
            line
            for line in _git(repository_root, "diff", "--name-only", f"{base_head}..{plan_head}").splitlines()
            if line
        )
        if first_paths != (_PLAN,):
            return E49ReleaseResult(E49ReleaseCode.GIT_GRAPH_INVALID, ("first_commit_not_plan_only",))
        if _git(repository_root, "merge-base", "--is-ancestor", plan_head, tested_head) != plan_head:
            return E49ReleaseResult(E49ReleaseCode.GIT_GRAPH_INVALID, ("plan_not_ancestor_of_tested",))
        if receipt_head is not None:
            if _git(repository_root, "rev-parse", f"{receipt_head}^") != tested_head:
                return E49ReleaseResult(E49ReleaseCode.RECEIPT_TOPOLOGY_INVALID, ("receipt_parent_mismatch",))
            changed = tuple(
                line
                for line in _git(repository_root, "diff", "--name-only", f"{tested_head}..{receipt_head}").splitlines()
                if line
            )
            if not receipt_paths_are_e49_evidence_only(changed):
                return E49ReleaseResult(E49ReleaseCode.RECEIPT_TOPOLOGY_INVALID, ("receipt_scope_invalid",))
    except RuntimeError:
        return E49ReleaseResult(E49ReleaseCode.GIT_GRAPH_INVALID, ("git_fact_unavailable",))
    return None


def validate_e49_release(
    repository_root: Path,
    evidence: E49ProviderEvidence,
    tested_head: str,
    receipt_head: str | None,
    *,
    base_head: str | None = None,
    plan_head: str | None = None,
    receipt_documents: dict[str, str] | None = None,
    mode: str = "final",
) -> E49ReleaseResult:
    """Validate E49 evidence without accepting a caller-declared conclusion."""

    if not _valid_sha(tested_head) or (receipt_head is not None and not _valid_sha(receipt_head)):
        return E49ReleaseResult(E49ReleaseCode.GIT_GRAPH_INVALID, ("full_sha_required",))
    if evidence.declared_success:
        return E49ReleaseResult(E49ReleaseCode.PROVIDER_EVIDENCE_UNTRUSTED, ("caller_declared_success_forbidden",))
    if mode == "pre_review":
        if evidence.provider_source != "IN_JOB_POLICY_AND_CURRENT_JOB_OBSERVATION_ONLY":
            return E49ReleaseResult(E49ReleaseCode.PROVIDER_EVIDENCE_UNTRUSTED, ("in_job_marker_required",))
        return E49ReleaseResult(E49ReleaseCode.PRE_REVIEW_EVIDENCE_RECORDED)
    if evidence.provider_source != "EXTERNAL_READ_ONLY_API":
        return E49ReleaseResult(E49ReleaseCode.PROVIDER_EVIDENCE_UNTRUSTED, ("external_provider_marker_required",))
    receipt_check = _validate_receipt_documents(receipt_documents, tested_head)
    if receipt_check is not None:
        return receipt_check
    if (
        evidence.tested_head != tested_head
        or evidence.receipt_head != receipt_head
        or evidence.remote_branch_head != receipt_head
    ):
        return E49ReleaseResult(E49ReleaseCode.PROVIDER_RUN_INVALID, ("provider_head_binding_mismatch",))
    for head in (tested_head, receipt_head):
        if head is None:
            continue
        run = _provider_run_for(evidence, head)
        if run is None:
            return E49ReleaseResult(E49ReleaseCode.PROVIDER_RUN_INVALID, ("completed_exact_head_run_missing",))
        run_check = _validate_provider_run(run, head)
        if run_check is not None:
            return run_check
    if not _route_and_brief_are_bound(repository_root):
        return E49ReleaseResult(E49ReleaseCode.ROUTE_BINDING_INVALID, ("route_or_brief_binding_invalid",))
    if base_head is None or plan_head is None or receipt_head is None:
        return E49ReleaseResult(E49ReleaseCode.GIT_GRAPH_INVALID, ("base_plan_receipt_heads_required",))
    graph_check = _validate_git_graph(repository_root, base_head, plan_head, tested_head, receipt_head)
    if graph_check is not None:
        return graph_check
    return E49ReleaseResult(
        E49ReleaseCode.READY_FOR_INDEPENDENT_REVIEW,
        evidence={
            "tested_head": tested_head,
            "receipt_head": receipt_head,
            "provider_source": evidence.provider_source,
            "final_provider_conclusion": "PENDING_GPT_REMOTE_HEAD_RECHECK",
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--provider-evidence", required=True)
    parser.add_argument("--tested-head", required=True)
    parser.add_argument("--receipt-head")
    parser.add_argument("--base-head")
    parser.add_argument("--plan-head")
    parser.add_argument("--mode", choices=("pre_review", "final"), default="final")
    parser.add_argument("--output")
    arguments = parser.parse_args(argv)
    try:
        document = json.loads(Path(arguments.provider_evidence).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        document = None
    result = validate_e49_release(
        Path(arguments.repository_root),
        E49ProviderEvidence.from_document(document),
        arguments.tested_head,
        arguments.receipt_head,
        base_head=arguments.base_head,
        plan_head=arguments.plan_head,
        receipt_documents=(
            None
            if arguments.mode == "pre_review"
            else read_e49_receipt_documents(Path(arguments.repository_root))
        ),
        mode=arguments.mode,
    )
    payload = result.canonical_json()
    if arguments.output:
        Path(arguments.output).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result.code in {
        E49ReleaseCode.PRE_REVIEW_EVIDENCE_RECORDED,
        E49ReleaseCode.READY_FOR_INDEPENDENT_REVIEW,
    } else 1


if __name__ == "__main__":
    sys.exit(main())
