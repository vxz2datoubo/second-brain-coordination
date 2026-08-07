"""Synthetic Provider fixtures shared by E57 tests only."""

from __future__ import annotations

from e57_authority.provider import E57_PROVIDER_CONTRACT, ProviderArtifact, ProviderEvidenceSet, ProviderJob


def provider_evidence(role: str, head: str, run_id: int, offset: int) -> ProviderEvidenceSet:
    contract = E57_PROVIDER_CONTRACT
    jobs = tuple(ProviderJob(offset + index + 1, name, run_id, head, "success") for index, name in enumerate(contract.job_names))
    job_ids = {job.name: job.job_id for job in jobs}
    artifacts = tuple(
        ProviderArtifact(
            artifact_id=offset + 100 + index,
            name=name,
            run_id=run_id,
            job_id=job_ids[job_name],
            archive_sha256=f"{index + 1:064x}",
            inner_payload_sha256=f"{index + 101:064x}",
        )
        for index, (name, job_name) in enumerate(contract.artifact_bindings)
    )
    return ProviderEvidenceSet(role, contract.workflow, contract.branch, head, run_id, jobs, artifacts, "f" * 64)
