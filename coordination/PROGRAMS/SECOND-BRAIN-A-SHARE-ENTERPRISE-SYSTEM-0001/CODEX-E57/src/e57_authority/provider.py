"""Separate tested-head and receipt-head Provider evidence records."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Sequence

from .core import AuthorityError, stable_digest


SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ProviderContract:
    workflow: str
    branch: str
    python_versions: tuple[str, ...] = ("3.11", "3.13")
    seeds: tuple[str, ...] = ("0", "1", "777")
    matrix_job_prefix: str = "e57-authority"
    compare_job_name: str = "provider-compare"

    @property
    def job_names(self) -> tuple[str, ...]:
        return tuple(f"{self.matrix_job_prefix} / py{version} / seed={seed}" for version in self.python_versions for seed in self.seeds) + (
            self.compare_job_name,
        )

    @property
    def artifact_bindings(self) -> tuple[tuple[str, str], ...]:
        bindings: list[tuple[str, str]] = []
        for version in self.python_versions:
            for seed in self.seeds:
                job = f"{self.matrix_job_prefix} / py{version} / seed={seed}"
                suffix = f"py{version}-seed{seed}"
                bindings.extend(((f"canonical-{suffix}", job), (f"environment-{suffix}", job)))
        bindings.append(("provider-compare", self.compare_job_name))
        return tuple(bindings)


E57_PROVIDER_CONTRACT = ProviderContract(
    workflow=".github/workflows/codex-e57-capability-authority-closure.yml",
    branch="codex/e56-post-receipt-capability-authority-closure-0053-e57",
)


@dataclass(frozen=True, slots=True)
class ProviderJob:
    job_id: int
    name: str
    run_id: int
    head_sha: str
    conclusion: str


@dataclass(frozen=True, slots=True)
class ProviderArtifact:
    artifact_id: int
    name: str
    run_id: int
    job_id: int
    archive_sha256: str
    inner_payload_sha256: str


@dataclass(frozen=True, slots=True)
class ProviderEvidenceSet:
    evidence_role: str
    workflow: str
    branch: str
    head_sha: str
    run_id: int
    jobs: tuple[ProviderJob, ...]
    artifacts: tuple[ProviderArtifact, ...]
    verifier_output_sha256: str

    def digest(self) -> str:
        return stable_digest(
            {
                "evidence_role": self.evidence_role,
                "workflow": self.workflow,
                "branch": self.branch,
                "head_sha": self.head_sha,
                "run_id": self.run_id,
                "jobs": [job.__dict__ if hasattr(job, "__dict__") else {"job_id": job.job_id, "name": job.name, "run_id": job.run_id, "head_sha": job.head_sha, "conclusion": job.conclusion} for job in self.jobs],
                "artifacts": [
                    {
                        "artifact_id": artifact.artifact_id,
                        "name": artifact.name,
                        "run_id": artifact.run_id,
                        "job_id": artifact.job_id,
                        "archive_sha256": artifact.archive_sha256,
                        "inner_payload_sha256": artifact.inner_payload_sha256,
                    }
                    for artifact in self.artifacts
                ],
                "verifier_output_sha256": self.verifier_output_sha256,
            }
        )


@dataclass(frozen=True, slots=True)
class DualProviderEvidence:
    tested_provider_evidence: ProviderEvidenceSet
    receipt_provider_evidence: ProviderEvidenceSet


def provider_evidence_to_mapping(evidence: ProviderEvidenceSet) -> Mapping[str, object]:
    return {
        "evidence_role": evidence.evidence_role,
        "workflow": evidence.workflow,
        "branch": evidence.branch,
        "head_sha": evidence.head_sha,
        "run_id": evidence.run_id,
        "jobs": [
            {"job_id": job.job_id, "name": job.name, "run_id": job.run_id, "head_sha": job.head_sha, "conclusion": job.conclusion}
            for job in evidence.jobs
        ],
        "artifacts": [
            {
                "artifact_id": artifact.artifact_id,
                "name": artifact.name,
                "run_id": artifact.run_id,
                "job_id": artifact.job_id,
                "archive_sha256": artifact.archive_sha256,
                "inner_payload_sha256": artifact.inner_payload_sha256,
            }
            for artifact in evidence.artifacts
        ],
        "verifier_output_sha256": evidence.verifier_output_sha256,
    }


def provider_evidence_from_mapping(value: Mapping[str, object]) -> ProviderEvidenceSet:
    try:
        jobs = tuple(
            ProviderJob(int(item["job_id"]), str(item["name"]), int(item["run_id"]), str(item["head_sha"]), str(item["conclusion"]))
            for item in value["jobs"]
        )
        artifacts = tuple(
            ProviderArtifact(
                int(item["artifact_id"]),
                str(item["name"]),
                int(item["run_id"]),
                int(item["job_id"]),
                str(item["archive_sha256"]),
                str(item["inner_payload_sha256"]),
            )
            for item in value["artifacts"]
        )
        return ProviderEvidenceSet(
            str(value["evidence_role"]),
            str(value["workflow"]),
            str(value["branch"]),
            str(value["head_sha"]),
            int(value["run_id"]),
            jobs,
            artifacts,
            str(value["verifier_output_sha256"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthorityError("Provider evidence mapping is malformed") from exc


def _check_sha(value: str, width: int, label: str) -> None:
    matcher = SHA40 if width == 40 else SHA64
    if not isinstance(value, str) or not matcher.fullmatch(value):
        raise AuthorityError(f"{label} must be a lowercase SHA-{width}")


def verify_provider_evidence(evidence: ProviderEvidenceSet, contract: ProviderContract, *, expected_role: str, expected_head: str) -> None:
    if evidence.evidence_role != expected_role:
        raise AuthorityError("Provider evidence role differs from its fixed route role")
    if evidence.workflow != contract.workflow or evidence.branch != contract.branch:
        raise AuthorityError("Provider evidence route identity differs from the fixed contract")
    _check_sha(evidence.head_sha, 40, "Provider head")
    if evidence.head_sha != expected_head:
        raise AuthorityError("Provider evidence head differs from the expected exact head")
    if not isinstance(evidence.run_id, int) or evidence.run_id <= 0:
        raise AuthorityError("Provider run ID is invalid")
    if len(evidence.jobs) != 7 or {job.name for job in evidence.jobs} != set(contract.job_names):
        raise AuthorityError("Provider evidence must have exactly six matrix jobs and one compare job")
    if len({job.job_id for job in evidence.jobs}) != 7:
        raise AuthorityError("Provider job IDs must be unique")
    jobs_by_name = {job.name: job for job in evidence.jobs}
    for job in evidence.jobs:
        if job.run_id != evidence.run_id or job.head_sha != evidence.head_sha or job.conclusion != "success":
            raise AuthorityError("Provider job does not prove exact successful execution")
    if len(evidence.artifacts) != 13 or len({artifact.artifact_id for artifact in evidence.artifacts}) != 13:
        raise AuthorityError("Provider evidence must have exactly thirteen unique artifacts")
    expected_bindings = dict(contract.artifact_bindings)
    if {artifact.name for artifact in evidence.artifacts} != set(expected_bindings):
        raise AuthorityError("Provider artifact names differ from the fixed route contract")
    for artifact in evidence.artifacts:
        job = jobs_by_name[expected_bindings[artifact.name]]
        if artifact.run_id != evidence.run_id or artifact.job_id != job.job_id:
            raise AuthorityError("Provider artifact is not bound to its exact run and job")
        _check_sha(artifact.archive_sha256, 64, "artifact archive")
        _check_sha(artifact.inner_payload_sha256, 64, "artifact inner payload")
    _check_sha(evidence.verifier_output_sha256, 64, "Provider verifier output")


def verify_dual_provider_evidence(evidence: DualProviderEvidence, contract: ProviderContract, *, tested_head: str, receipt_head: str) -> None:
    verify_provider_evidence(evidence.tested_provider_evidence, contract, expected_role="TESTED", expected_head=tested_head)
    verify_provider_evidence(evidence.receipt_provider_evidence, contract, expected_role="RECEIPT", expected_head=receipt_head)
    tested, receipt = evidence.tested_provider_evidence, evidence.receipt_provider_evidence
    if tested.run_id == receipt.run_id:
        raise AuthorityError("tested and receipt Provider evidence must be distinct runs")
    if {job.job_id for job in tested.jobs} & {job.job_id for job in receipt.jobs}:
        raise AuthorityError("tested and receipt Provider evidence share job IDs")
    if {artifact.artifact_id for artifact in tested.artifacts} & {artifact.artifact_id for artifact in receipt.artifacts}:
        raise AuthorityError("tested and receipt Provider evidence share artifact IDs")
