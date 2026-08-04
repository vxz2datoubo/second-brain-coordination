"""E50 fail-closed release validation primitives.

E49 treated the stdout of ``git merge-base --is-ancestor`` as evidence. Git
uses the exit status instead, so E50 exposes that fact directly and keeps
caller-authored provider documents outside the authority boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


_TASK_ID = "CODEX-BRAINOPS-TRUSTED-PROVIDER-ATTESTATION-CORRECT-GIT-GRAPH-CLEAN-CLONE-REPRODUCTION-AND-STRICT-RECEIPT-VALIDATION-CLOSURE-0046-E50"
_ROUTE_EPOCH = 52
_AGENT = "CODEX"
_COMPLETION_SIGNAL = "CODEX_BRAINOPS_E50_TRUSTED_PROVIDER_RELEASE_VALIDATION_READY_FOR_GPT_REVIEW"
_PROGRAM = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/"
_PLAN = _PROGRAM + "E50/E50-EXECUTION-PLAN.md"
_RECEIPT = _PROGRAM + "E50/RECEIPT/"
_ATTESTATION_PATH = "coordination/PROVIDER-ATTESTATIONS/CODEX-E50-POST-RUN-PROVIDER-ATTESTATION.json"
_REQUIRED_RECEIPT_FILES = (
    "AMED-EXECUTION-RECEIPT.yaml",
    "TEST-RUN-RECEIPT.json",
    "PROVIDER-EVIDENCE-TESTED-HEAD.json",
    "UNKNOWN-REGISTRY.yaml",
    "AI_HANDOFF.yaml",
    "RESEARCH-LEDGER.md",
    "UNPLANNED-IMPROVEMENT-LEDGER.md",
    "SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md",
    "WORK-PROCESS-AND-COORDINATION-REPORT.md",
    "RECEIPT-MANIFEST.json",
)
_FORBIDDEN_RECEIPT_TOKENS = (
    "receipt_commit_sha",
    "self_commit_sha",
    "RESOLVED_MECHANICALLY_AFTER_COMMIT",
    "TODO",
    "TBD",
    "$head",
)


class E50GitGraphCode(str, Enum):
    ANCESTOR = "ANCESTOR"
    NOT_ANCESTOR = "NOT_ANCESTOR"
    GIT_UNAVAILABLE = "GIT_UNAVAILABLE"


@dataclass(frozen=True)
class E50GitGraphResult:
    code: E50GitGraphCode
    stderr: str = ""


class E50ProviderAuthorityCode(str, Enum):
    UNTRUSTED_CALLER_DOCUMENT = "UNTRUSTED_CALLER_DOCUMENT"
    TRUSTED_MAIN_ATTESTATION = "TRUSTED_MAIN_ATTESTATION"
    ATTESTATION_INVALID = "ATTESTATION_INVALID"


@dataclass(frozen=True)
class E50ProviderAuthorityResult:
    code: E50ProviderAuthorityCode


def evaluate_git_ancestry(
    repository_root: Path, ancestor: str, descendant: str
) -> E50GitGraphResult:
    """Interpret the documented ``--is-ancestor`` exit status, not stdout."""

    completed = subprocess.run(
        ["git", "-C", str(repository_root), "merge-base", "--is-ancestor", ancestor, descendant],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode == 0:
        return E50GitGraphResult(E50GitGraphCode.ANCESTOR)
    if completed.returncode == 1:
        return E50GitGraphResult(E50GitGraphCode.NOT_ANCESTOR)
    return E50GitGraphResult(E50GitGraphCode.GIT_UNAVAILABLE, completed.stderr.strip())


def reject_caller_provider_document(_document: object) -> E50ProviderAuthorityResult:
    """Raw JSON-shaped input cannot become external provider authority."""

    return E50ProviderAuthorityResult(E50ProviderAuthorityCode.UNTRUSTED_CALLER_DOCUMENT)


class E50ReleaseCode(str, Enum):
    READY_FOR_INDEPENDENT_REVIEW = "READY_FOR_INDEPENDENT_REVIEW"
    GIT_GRAPH_NOT_ANCESTOR = "GIT_GRAPH_NOT_ANCESTOR"
    GIT_GRAPH_UNAVAILABLE = "GIT_GRAPH_UNAVAILABLE"
    RECEIPT_SCHEMA_INVALID = "RECEIPT_SCHEMA_INVALID"
    PROVIDER_ATTESTATION_INVALID = "PROVIDER_ATTESTATION_INVALID"
    PROVIDER_FACT_MISMATCH = "PROVIDER_FACT_MISMATCH"
    RECEIPT_TOPOLOGY_INVALID = "RECEIPT_TOPOLOGY_INVALID"


@dataclass(frozen=True)
class E50ReleaseResult:
    code: E50ReleaseCode
    findings: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.code is E50ReleaseCode.READY_FOR_INDEPENDENT_REVIEW

    def canonical_json(self) -> str:
        return json.dumps(
            {"code": self.code.value, "findings": list(self.findings)},
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )


@dataclass(frozen=True)
class TrustedMainAttestation:
    document: dict[str, Any]
    source_commit: str
    source_blob_sha1: str
    payload_sha256: str


def _git(repository_root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _git_output(repository_root: Path, *arguments: str) -> str:
    completed = _git(repository_root, *arguments)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout.strip()


def _canonical_payload_sha256(document: dict[str, Any]) -> str:
    encoded = json.dumps(document, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_payload_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(document, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _outside_repository(path: Path, repository_root: Path) -> bool:
    try:
        path.resolve().relative_to(repository_root.resolve())
    except ValueError:
        return True
    return False


def load_trusted_main_attestation(
    repository_root: Path, external_path: Path
) -> tuple[E50ProviderAuthorityResult, TrustedMainAttestation | None]:
    """Trust only a byte-identical attestation committed on canonical main."""

    if not _outside_repository(external_path, repository_root):
        return E50ProviderAuthorityResult(E50ProviderAuthorityCode.ATTESTATION_INVALID), None
    try:
        raw = external_path.read_bytes()
        envelope = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return E50ProviderAuthorityResult(E50ProviderAuthorityCode.ATTESTATION_INVALID), None
    if not isinstance(envelope, dict):
        return E50ProviderAuthorityResult(E50ProviderAuthorityCode.ATTESTATION_INVALID), None
    required = {
        "source_commit",
        "source_path",
        "source_blob_sha1",
        "payload_sha256",
        "payload",
    }
    if set(envelope) != required or not isinstance(envelope.get("payload"), dict):
        return E50ProviderAuthorityResult(E50ProviderAuthorityCode.ATTESTATION_INVALID), None
    document = envelope["payload"]
    if (
        document.get("task_id") != _TASK_ID
        or document.get("route_epoch") != _ROUTE_EPOCH
        or document.get("agent_id") != _AGENT
        or document.get("completion_signal") != _COMPLETION_SIGNAL
        or not isinstance(document.get("provider_evidence"), dict)
        or envelope.get("source_path") != _ATTESTATION_PATH
        or not isinstance(envelope.get("source_commit"), str)
        or not isinstance(envelope.get("source_blob_sha1"), str)
        or not isinstance(envelope.get("payload_sha256"), str)
        or envelope["payload_sha256"] != _canonical_payload_sha256(document)
    ):
        return E50ProviderAuthorityResult(E50ProviderAuthorityCode.ATTESTATION_INVALID), None
    fetch = _git(repository_root, "fetch", "origin", "main")
    if fetch.returncode:
        return E50ProviderAuthorityResult(E50ProviderAuthorityCode.ATTESTATION_INVALID), None
    # A single-branch clean clone may not maintain refs/remotes/origin/main.
    # FETCH_HEAD is the exact ref returned by the read-only fetch above.
    remote_main = _git_output(repository_root, "rev-parse", "FETCH_HEAD")
    ancestry = evaluate_git_ancestry(repository_root, envelope["source_commit"], remote_main)
    if ancestry.code is not E50GitGraphCode.ANCESTOR:
        return E50ProviderAuthorityResult(E50ProviderAuthorityCode.ATTESTATION_INVALID), None
    try:
        blob_sha1 = _git_output(repository_root, "rev-parse", f"{envelope['source_commit']}:{_ATTESTATION_PATH}")
        source_bytes = subprocess.run(
            ["git", "-C", str(repository_root), "show", f"{envelope['source_commit']}:{_ATTESTATION_PATH}"],
            check=True,
            capture_output=True,
        ).stdout
    except (RuntimeError, subprocess.CalledProcessError):
        return E50ProviderAuthorityResult(E50ProviderAuthorityCode.ATTESTATION_INVALID), None
    if blob_sha1 != envelope["source_blob_sha1"] or source_bytes != _canonical_payload_bytes(document):
        return E50ProviderAuthorityResult(E50ProviderAuthorityCode.ATTESTATION_INVALID), None
    return (
        E50ProviderAuthorityResult(E50ProviderAuthorityCode.TRUSTED_MAIN_ATTESTATION),
        TrustedMainAttestation(document, envelope["source_commit"], blob_sha1, envelope["payload_sha256"]),
    )


def _read_receipt_documents(repository_root: Path) -> tuple[dict[str, str], E50ReleaseResult | None]:
    directory = repository_root / _RECEIPT
    documents: dict[str, str] = {}
    try:
        for name in _REQUIRED_RECEIPT_FILES:
            content = (directory / name).read_text(encoding="utf-8")
            if not content.strip():
                return {}, E50ReleaseResult(E50ReleaseCode.RECEIPT_SCHEMA_INVALID, (f"empty_{name}",))
            documents[name] = content
    except (OSError, UnicodeDecodeError):
        return {}, E50ReleaseResult(E50ReleaseCode.RECEIPT_SCHEMA_INVALID, ("required_receipt_document_missing",))
    return documents, None


def _strict_json(documents: dict[str, str], name: str) -> dict[str, Any] | None:
    try:
        value = json.loads(documents[name])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _receipt_schema_result(
    documents: dict[str, str],
    *,
    base_head: str,
    plan_head: str,
    tested_head: str,
) -> tuple[dict[str, Any] | None, E50ReleaseResult | None]:
    structured_names = (
        "AMED-EXECUTION-RECEIPT.yaml",
        "TEST-RUN-RECEIPT.json",
        "PROVIDER-EVIDENCE-TESTED-HEAD.json",
        "UNKNOWN-REGISTRY.yaml",
        "AI_HANDOFF.yaml",
        "RECEIPT-MANIFEST.json",
    )
    structured = {name: _strict_json(documents, name) for name in structured_names}
    if any(value is None for value in structured.values()):
        return None, E50ReleaseResult(E50ReleaseCode.RECEIPT_SCHEMA_INVALID, ("structured_receipt_json_required",))
    metadata = {
        "task_id": _TASK_ID,
        "route_epoch": _ROUTE_EPOCH,
        "agent_id": _AGENT,
        "completion_signal": _COMPLETION_SIGNAL,
        "base_head": base_head,
        "plan_head": plan_head,
        "tested_head": tested_head,
    }
    for name, value in structured.items():
        if any(value.get(key) != expected for key, expected in metadata.items()):
            return None, E50ReleaseResult(E50ReleaseCode.RECEIPT_SCHEMA_INVALID, (f"metadata_mismatch_{name}",))
    for name in _REQUIRED_RECEIPT_FILES[5:9]:
        content = documents[name]
        if len(content.strip()) < 32 or any(f"{key}: {value}" not in content for key, value in metadata.items()):
            return None, E50ReleaseResult(E50ReleaseCode.RECEIPT_SCHEMA_INVALID, (f"markdown_metadata_mismatch_{name}",))
    combined = "\n".join(documents.values())
    if any(token in combined for token in _FORBIDDEN_RECEIPT_TOKENS):
        return None, E50ReleaseResult(E50ReleaseCode.RECEIPT_SCHEMA_INVALID, ("receipt_forbidden_token",))
    manifest = structured["RECEIPT-MANIFEST.json"]
    if manifest.get("receipt_commit_identity") != "EXTERNAL_POST_COMMIT_PROVIDER_FACT":
        return None, E50ReleaseResult(E50ReleaseCode.RECEIPT_SCHEMA_INVALID, ("external_identity_marker_missing",))
    command = manifest.get("reproduction_command")
    required_arguments = {
        "-m",
        "brainops_control_plane.e50_release_verifier",
        "--repository-root",
        "--trusted-attestation",
        "--base-head",
        "--plan-head",
        "--tested-head",
        "--receipt-head",
    }
    if (
        not isinstance(command, list)
        or not all(isinstance(argument, str) and argument for argument in command)
        or not required_arguments.issubset(command)
    ):
        return None, E50ReleaseResult(E50ReleaseCode.RECEIPT_SCHEMA_INVALID, ("reproduction_command_schema_invalid",))
    return structured, None


def _validate_provider_run(run: object, head: str) -> bool:
    if not isinstance(run, dict) or run.get("head_sha") != head:
        return False
    if run.get("conclusion") != "success" or run.get("status") != "completed":
        return False
    jobs = {job.get("python_version"): job for job in run.get("jobs", []) if isinstance(job, dict)}
    artifacts = {artifact.get("name"): artifact for artifact in run.get("artifacts", []) if isinstance(artifact, dict)}
    for version in ("3.11", "3.13"):
        job = jobs.get(version)
        artifact = artifacts.get(f"e50-release-evidence-{version}")
        if (
            not isinstance(job, dict)
            or not isinstance(artifact, dict)
            or job.get("head_sha") != head
            or job.get("conclusion") != "success"
            or not isinstance(job.get("job_id"), int)
            or job["job_id"] <= 0
            or artifact.get("head_sha") != head
            or artifact.get("expired") is not False
            or not isinstance(artifact.get("artifact_id"), int)
            or artifact["artifact_id"] <= 0
            or not isinstance(artifact.get("digest"), str)
            or not artifact["digest"].startswith("sha256:")
            or len(artifact["digest"]) != 71
        ):
            return False
    return True


def _validate_provider_evidence(evidence: object, tested_head: str, receipt_head: str) -> bool:
    if not isinstance(evidence, dict):
        return False
    tested = evidence.get("tested")
    receipt = evidence.get("receipt")
    if not isinstance(tested, dict) or not isinstance(receipt, dict):
        return False
    if tested.get("tested_head") != tested_head or receipt.get("receipt_head") != receipt_head:
        return False
    if receipt.get("remote_branch_head") != receipt_head:
        return False
    return _validate_provider_run(tested.get("run"), tested_head) and _validate_provider_run(
        receipt.get("run"), receipt_head
    )


def validate_e50_release(
    repository_root: Path,
    trusted_attestation_path: Path,
    *,
    base_head: str,
    plan_head: str,
    tested_head: str,
    receipt_head: str,
) -> E50ReleaseResult:
    """Validate E50 using a main-bound provider attestation, never caller JSON."""

    if _git_output(repository_root, "rev-parse", f"{plan_head}^") != base_head:
        return E50ReleaseResult(E50ReleaseCode.RECEIPT_TOPOLOGY_INVALID, ("plan_parent_mismatch",))
    first_paths = tuple(line for line in _git_output(repository_root, "diff", "--name-only", f"{base_head}..{plan_head}").splitlines() if line)
    if first_paths != (_PLAN,):
        return E50ReleaseResult(E50ReleaseCode.RECEIPT_TOPOLOGY_INVALID, ("plan_not_single_file",))
    ancestry = evaluate_git_ancestry(repository_root, plan_head, tested_head)
    if ancestry.code is E50GitGraphCode.NOT_ANCESTOR:
        return E50ReleaseResult(E50ReleaseCode.GIT_GRAPH_NOT_ANCESTOR, ("plan_not_ancestor_of_tested",))
    if ancestry.code is not E50GitGraphCode.ANCESTOR:
        return E50ReleaseResult(E50ReleaseCode.GIT_GRAPH_UNAVAILABLE, ("git_ancestry_unavailable",))
    if _git_output(repository_root, "rev-parse", f"{receipt_head}^") != tested_head:
        return E50ReleaseResult(E50ReleaseCode.RECEIPT_TOPOLOGY_INVALID, ("receipt_parent_mismatch",))
    receipt_paths = tuple(line for line in _git_output(repository_root, "diff", "--name-only", f"{tested_head}..{receipt_head}").splitlines() if line)
    if not receipt_paths or any(not path.startswith(_RECEIPT) for path in receipt_paths):
        return E50ReleaseResult(E50ReleaseCode.RECEIPT_TOPOLOGY_INVALID, ("receipt_scope_invalid",))
    if _git_output(repository_root, "rev-parse", "HEAD") != receipt_head:
        return E50ReleaseResult(E50ReleaseCode.RECEIPT_TOPOLOGY_INVALID, ("post_receipt_commit_detected",))
    documents, read_failure = _read_receipt_documents(repository_root)
    if read_failure is not None:
        return read_failure
    structured, schema_failure = _receipt_schema_result(documents, base_head=base_head, plan_head=plan_head, tested_head=tested_head)
    if schema_failure is not None or structured is None:
        return schema_failure or E50ReleaseResult(E50ReleaseCode.RECEIPT_SCHEMA_INVALID)
    provider_status, attestation = load_trusted_main_attestation(repository_root, trusted_attestation_path)
    if provider_status.code is not E50ProviderAuthorityCode.TRUSTED_MAIN_ATTESTATION or attestation is None:
        return E50ReleaseResult(E50ReleaseCode.PROVIDER_ATTESTATION_INVALID, ("trusted_main_attestation_invalid",))
    provider_document = structured["PROVIDER-EVIDENCE-TESTED-HEAD.json"]
    trusted_evidence = attestation.document["provider_evidence"]
    if (
        not isinstance(trusted_evidence, dict)
        or provider_document != trusted_evidence.get("tested")
        or not _validate_provider_evidence(trusted_evidence, tested_head, receipt_head)
    ):
        return E50ReleaseResult(E50ReleaseCode.PROVIDER_FACT_MISMATCH, ("provider_receipt_crosscheck_failed",))
    return E50ReleaseResult(E50ReleaseCode.READY_FOR_INDEPENDENT_REVIEW)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--trusted-attestation", required=True)
    parser.add_argument("--base-head", required=True)
    parser.add_argument("--plan-head", required=True)
    parser.add_argument("--tested-head", required=True)
    parser.add_argument("--receipt-head", required=True)
    arguments = parser.parse_args(argv)
    receipt_head = (
        _git_output(Path(arguments.repository_root), "rev-parse", "HEAD")
        if arguments.receipt_head == "@HEAD"
        else arguments.receipt_head
    )
    result = validate_e50_release(
        Path(arguments.repository_root),
        Path(arguments.trusted_attestation),
        base_head=arguments.base_head,
        plan_head=arguments.plan_head,
        tested_head=arguments.tested_head,
        receipt_head=receipt_head,
    )
    print(result.canonical_json())
    return 0 if result.ready else 1


if __name__ == "__main__":
    sys.exit(main())
