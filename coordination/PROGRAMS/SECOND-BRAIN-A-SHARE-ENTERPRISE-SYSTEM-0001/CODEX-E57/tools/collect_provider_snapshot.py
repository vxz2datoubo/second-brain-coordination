"""Download one public GitHub Actions evidence set without retaining payload bodies."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e57_authority.core import AuthorityError, stable_digest
from e57_authority.provider import E57_PROVIDER_CONTRACT, ProviderArtifact, ProviderEvidenceSet, ProviderJob, provider_evidence_to_mapping, verify_provider_evidence


def _api_json(endpoint: str) -> object:
    completed = subprocess.run(["gh", "api", endpoint], capture_output=True, check=False)
    if completed.returncode:
        raise AuthorityError(completed.stderr.decode("utf-8", "replace").strip() or f"GitHub API failed: {endpoint}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AuthorityError("GitHub API returned malformed JSON") from exc


def _download_archive(endpoint: str, destination: Path) -> None:
    completed = subprocess.run(["gh", "api", endpoint, "--output", str(destination)], capture_output=True, check=False)
    if completed.returncode:
        raise AuthorityError(completed.stderr.decode("utf-8", "replace").strip() or "artifact archive download failed")


def _inner_hash(archive: Path, artifact_name: str) -> str:
    required = "provider-compare.json" if artifact_name == "provider-compare" else ("canonical.json" if artifact_name.startswith("canonical-") else "environment.json")
    try:
        with ZipFile(archive) as bundle:
            matches = [name for name in bundle.namelist() if name.rsplit("/", 1)[-1] == required]
            if len(matches) != 1:
                raise AuthorityError(f"artifact {artifact_name} does not contain exactly one expected inner payload")
            return sha256(bundle.read(matches[0])).hexdigest()
    except AuthorityError:
        raise
    except Exception as exc:
        raise AuthorityError(f"artifact {artifact_name} is not a readable ZIP payload") from exc


def collect(*, repository: str, run_id: int, role: str, expected_head: str, out: Path) -> ProviderEvidenceSet:
    run = _api_json(f"repos/{repository}/actions/runs/{run_id}")
    if not isinstance(run, dict) or run.get("head_sha") != expected_head:
        raise AuthorityError("Provider run does not match the expected exact head")
    jobs_payload = _api_json(f"repos/{repository}/actions/runs/{run_id}/jobs?per_page=100")
    artifacts_payload = _api_json(f"repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100")
    if not isinstance(jobs_payload, dict) or not isinstance(artifacts_payload, dict):
        raise AuthorityError("Provider job or artifact response is malformed")
    jobs = tuple(
        ProviderJob(int(item["id"]), str(item["name"]), run_id, expected_head, str(item.get("conclusion")))
        for item in jobs_payload.get("jobs", [])
    )
    expected_binding = dict(E57_PROVIDER_CONTRACT.artifact_bindings)
    raw_artifacts = tuple(item for item in artifacts_payload.get("artifacts", []) if isinstance(item, dict) and item.get("name") in expected_binding)
    if len(raw_artifacts) != 13:
        raise AuthorityError("Provider run does not expose the required thirteen named artifacts")
    job_by_name = {job.name: job for job in jobs}
    out.mkdir(parents=True, exist_ok=True)
    artifacts: list[ProviderArtifact] = []
    with tempfile.TemporaryDirectory(prefix="e57-provider-download-") as temporary:
        temporary_root = Path(temporary)
        for item in raw_artifacts:
            name = str(item["name"])
            expected_job = expected_binding[name]
            job = job_by_name.get(expected_job)
            if job is None:
                raise AuthorityError(f"artifact {name} has no expected job in this run")
            archive = temporary_root / f"{int(item['id'])}.zip"
            _download_archive(f"repos/{repository}/actions/artifacts/{int(item['id'])}/zip", archive)
            artifacts.append(
                ProviderArtifact(
                    int(item["id"]),
                    name,
                    run_id,
                    job.job_id,
                    sha256(archive.read_bytes()).hexdigest(),
                    _inner_hash(archive, name),
                )
            )
    preimage = {
        "role": role,
        "run_id": run_id,
        "head_sha": expected_head,
        "jobs": [{"id": job.job_id, "name": job.name} for job in jobs],
        "artifacts": [{"id": artifact.artifact_id, "name": artifact.name, "archive": artifact.archive_sha256, "inner": artifact.inner_payload_sha256} for artifact in artifacts],
    }
    evidence = ProviderEvidenceSet(role, E57_PROVIDER_CONTRACT.workflow, E57_PROVIDER_CONTRACT.branch, expected_head, run_id, jobs, tuple(artifacts), stable_digest(preimage))
    verify_provider_evidence(evidence, E57_PROVIDER_CONTRACT, expected_role=role, expected_head=expected_head)
    out.write_bytes(json.dumps(provider_evidence_to_mapping(evidence), sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--role", required=True, choices=("TESTED", "RECEIPT"))
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--out", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        collect(repository=arguments.repository, run_id=arguments.run_id, role=arguments.role, expected_head=arguments.expected_head, out=arguments.out)
    except AuthorityError as exc:
        print(f"Provider collection failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
