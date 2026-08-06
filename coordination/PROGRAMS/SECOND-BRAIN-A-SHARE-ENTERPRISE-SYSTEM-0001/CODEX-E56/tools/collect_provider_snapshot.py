"""Collect public GitHub Actions evidence without reading private configuration."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from e56_authority.authority import AuthorityError  # noqa: E402
from e56_authority.provider import DEFAULT_PROVIDER_CONTRACT, ProviderContract  # noqa: E402


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def build_snapshot(
    contract: ProviderContract,
    *,
    run: Mapping[str, object],
    jobs: Sequence[Mapping[str, object]],
    artifacts: Sequence[Mapping[str, object]],
    archive_records: Mapping[int, Mapping[str, object]],
    expected_head: str,
) -> dict[str, object]:
    """Bind exact public metadata and archive byte hashes into verifier input."""

    run_id = run.get("id")
    if (
        not isinstance(run_id, int)
        or run.get("head_sha") != expected_head
        or run.get("head_branch") != contract.branch
        or run.get("event") != "pull_request"
        or run.get("name") != "codex-e56-canonical-authority-closure"
    ):
        raise AuthorityError("workflow run metadata is not the exact E56 pull-request run")
    expected_jobs = set(contract.matrix_job_names) | {contract.compare_job_name}
    selected_jobs = [item for item in jobs if item.get("name") in expected_jobs]
    if len(selected_jobs) != 7:
        raise AuthorityError("workflow API did not expose exactly the E56 matrix and compare jobs")
    jobs_by_name = {str(item["name"]): item for item in selected_jobs}
    expected_bindings = dict(contract.matrix_artifact_bindings)
    selected_artifacts = [item for item in artifacts if item.get("name") in expected_bindings]
    if len(selected_artifacts) != contract.artifact_count:
        raise AuthorityError("workflow API did not expose exactly the E56 evidence artifacts")
    bound_artifacts: list[dict[str, object]] = []
    for artifact_name, job_name in contract.matrix_artifact_bindings:
        source = next((item for item in selected_artifacts if item.get("name") == artifact_name), None)
        if source is None or not isinstance(source.get("id"), int):
            raise AuthorityError("expected E56 artifact is missing an immutable API id")
        record = archive_records.get(source["id"])
        job = jobs_by_name[job_name]
        if (
            not isinstance(record, Mapping)
            or not isinstance(record.get("archive_file"), str)
            or not isinstance(record.get("archive_sha256"), str)
            or len(str(record["archive_sha256"])) != 64
            or job.get("run_id") != run_id
        ):
            raise AuthorityError("artifact archive record or exact job/run linkage is invalid")
        bound_artifacts.append(
            {
                "id": source["id"],
                "name": artifact_name,
                "job_name": job_name,
                "job_id": job["id"],
                "run_id": run_id,
                "archive_file": record["archive_file"],
                "archive_sha256": record["archive_sha256"],
            }
        )
    return {
        "schema": "e56-provider-public-snapshot-v1",
        "workflow": contract.workflow,
        "branch": contract.branch,
        "head_sha": expected_head,
        "run_id": run_id,
        "jobs": [
            {"id": item["id"], "name": item["name"], "conclusion": item.get("conclusion"), "head_sha": item.get("head_sha"), "run_id": item.get("run_id")}
            for item in selected_jobs
        ],
        "artifacts": bound_artifacts,
    }


def _gh_json(*args: str) -> Mapping[str, Any]:
    result = subprocess.run(("gh", "api", *args), capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError("GitHub API command failed without exposing its output in the public receipt")
    try:
        value = json.loads(result.stdout.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("GitHub API did not return valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("GitHub API response is not an object")
    return value


def collect(repo: str, run_id: int, archive_root: Path, expected_head: str) -> dict[str, object]:
    """Fetch only public Actions metadata and binary archives into a caller path."""

    archive_root.mkdir(parents=True, exist_ok=True)
    run = _gh_json(f"repos/{repo}/actions/runs/{run_id}")
    jobs = _gh_json(f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100").get("jobs")
    artifacts = _gh_json(f"repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100").get("artifacts")
    if not isinstance(jobs, list) or not isinstance(artifacts, list):
        raise RuntimeError("GitHub Actions response lacks jobs or artifacts")
    archives: dict[int, Mapping[str, object]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, Mapping) or artifact.get("name") not in dict(DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings):
            continue
        artifact_id = artifact.get("id")
        if not isinstance(artifact_id, int):
            raise RuntimeError("GitHub artifact lacks a numeric id")
        destination = archive_root / f"artifact-{artifact_id}.zip"
        result = subprocess.run(("gh", "api", f"repos/{repo}/actions/artifacts/{artifact_id}/zip", "--output", str(destination)), capture_output=True, check=False)
        if result.returncode or not destination.is_file():
            raise RuntimeError("GitHub artifact download failed without exposing output in the public receipt")
        archives[artifact_id] = {"archive_file": destination.name, "archive_sha256": digest(destination.read_bytes())}
    return build_snapshot(DEFAULT_PROVIDER_CONTRACT, run=run, jobs=jobs, artifacts=artifacts, archive_records=archives, expected_head=expected_head)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--archive-root", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    snapshot = collect(args.repo, args.run_id, Path(args.archive_root), args.expected_head)
    Path(args.output).write_bytes(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
