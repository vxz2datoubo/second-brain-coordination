"""Independently fetch and byte-verify one E55 GitHub Actions Provider run.

The tool reads only public GitHub run/job/artifact endpoints through the
configured GitHub CLI. It never reads local credentials or repository config.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from e55_authority.mutations import MUTATION_SPECS  # noqa: E402
from e55_authority.provider import DownloadedArtifact, validate_provider_evidence  # noqa: E402


REPO = "vxz2datoubo/second-brain-coordination"
PAIR = re.compile(r"^(canonical|environment)-py(3\.11|3\.13)-seed(0|1|777)$")
WORKFLOW_PATH = ".github/workflows/codex-e55-authority-closure.yml"
BRANCH = "codex/e54-post-receipt-authority-closure-0051-e55"


def _gh_json(endpoint: str) -> dict[str, Any]:
    completed = subprocess.run(["gh", "api", endpoint], capture_output=True, check=False)
    if completed.returncode:
        raise RuntimeError("GitHub metadata request failed")
    return json.loads(completed.stdout.decode("utf-8", "strict"))


def _gh_bytes(endpoint: str) -> bytes:
    completed = subprocess.run(["gh", "api", endpoint], capture_output=True, check=False)
    if completed.returncode:
        raise RuntimeError("GitHub artifact byte request failed")
    return completed.stdout


def _zip_member(payload: bytes, filename: str) -> bytes:
    with ZipFile(BytesIO(payload)) as archive:
        candidates = [name for name in archive.namelist() if name.endswith("/" + filename) or name == filename]
        if len(candidates) != 1:
            raise RuntimeError(f"artifact archive lacks exactly one {filename}")
        return archive.read(candidates[0])


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, type=int)
    args = parser.parse_args()
    run = _gh_json(f"repos/{REPO}/actions/runs/{args.run_id}")
    jobs = _gh_json(f"repos/{REPO}/actions/runs/{args.run_id}/jobs?per_page=100").get("jobs", [])
    artifacts = _gh_json(f"repos/{REPO}/actions/runs/{args.run_id}/artifacts?per_page=100").get("artifacts", [])
    if run.get("conclusion") != "success" or run.get("head_branch") != BRANCH or run.get("path") != WORKFLOW_PATH:
        raise RuntimeError("run identity, branch, workflow path, or conclusion is not exact")
    if not isinstance(run.get("head_sha"), str) or len(run["head_sha"]) != 40:
        raise RuntimeError("run has no exact tested head")
    jobs_by_name = {str(job.get("name")): job for job in jobs}
    inner: list[DownloadedArtifact] = []
    outer: list[dict[str, object]] = []
    environment_payloads: dict[tuple[str, str], dict[str, object]] = {}
    canonical_payloads: dict[tuple[str, str], bytes] = {}
    compare: DownloadedArtifact | None = None
    for metadata in artifacts:
        artifact_id = metadata.get("id")
        name = metadata.get("name")
        if not isinstance(artifact_id, int) or not isinstance(name, str):
            raise RuntimeError("artifact metadata is incomplete")
        outer_bytes = _gh_bytes(f"repos/{REPO}/actions/artifacts/{artifact_id}/zip")
        outer_digest = _sha(outer_bytes)
        declared = metadata.get("digest")
        if declared != f"sha256:{outer_digest}":
            raise RuntimeError("downloaded artifact archive digest differs from GitHub metadata")
        outer.append({"artifact_id": artifact_id, "name": name, "archive_sha256": outer_digest, "size_in_bytes": metadata.get("size_in_bytes")})
        match = PAIR.fullmatch(name)
        if match:
            kind, version, seed = match.groups()
            job_name = f"authority / py{version} / seed={seed}"
            job = jobs_by_name.get(job_name)
            if not isinstance(job, dict) or job.get("conclusion") != "success" or not isinstance(job.get("id"), int):
                raise RuntimeError("matrix artifact does not bind to one successful external job")
            filename = "canonical.json" if kind == "canonical" else "environment.json"
            payload = _zip_member(outer_bytes, filename)
            artifact = DownloadedArtifact(artifact_id, name, int(job["id"]), payload, _sha(payload))
            inner.append(artifact)
            if kind == "canonical":
                canonical_payloads[(version, seed)] = payload
            else:
                environment_payloads[(version, seed)] = json.loads(payload.decode("utf-8", "strict"))
            continue
        if name == "provider-compare":
            payload = _zip_member(outer_bytes, "provider-compare.json")
            compare = DownloadedArtifact(artifact_id, name, None, payload, _sha(payload))
            continue
        raise RuntimeError("unexpected artifact name in exact Provider run")
    expected_pairs = {(version, seed) for version in ("3.11", "3.13") for seed in ("0", "1", "777")}
    if set(canonical_payloads) != expected_pairs or set(environment_payloads) != expected_pairs or compare is None:
        raise RuntimeError("Provider artifacts do not cover the exact six-pair matrix plus compare artifact")
    if len(set(canonical_payloads.values())) != 1:
        raise RuntimeError("canonical artifact bytes differ across Provider matrix pairs")
    expected_mutations = [item.mutation_id for item in MUTATION_SPECS]
    test_counts = {payload.get("test_count") for payload in environment_payloads.values()}
    if len(test_counts) != 1 or not isinstance(next(iter(test_counts)), int):
        raise RuntimeError("environment evidence has inconsistent test counts")
    job_records: list[dict[str, object]] = []
    for version, seed in sorted(expected_pairs):
        payload = environment_payloads[(version, seed)]
        job = jobs_by_name[f"authority / py{version} / seed={seed}"]
        if payload.get("head_sha") != run["head_sha"] or payload.get("workflow") != WORKFLOW_PATH or payload.get("branch") != BRANCH:
            raise RuntimeError("environment evidence route fields differ from external run metadata")
        job_records.append(
            {
                "job_id": job["id"], "name": job["name"], "python_version": version, "hash_seed": seed,
                "conclusion": job["conclusion"], "head_sha": payload["head_sha"], "test_count": payload["test_count"],
                "mutation_ids": payload["mutation_ids"],
            }
        )
    combined = validate_provider_evidence(
        {"run_id": run["id"], "head_sha": run["head_sha"], "workflow": run["path"], "branch": run["head_branch"], "conclusion": run["conclusion"]},
        job_records,
        inner + [compare],
        expected_head=run["head_sha"], expected_workflow=WORKFLOW_PATH, expected_branch=BRANCH,
        expected_test_count=next(iter(test_counts)), expected_mutation_ids=expected_mutations,
    )
    summary = {
        "schema": "e55-independent-provider-verification-v1",
        "run_id": run["id"], "head_sha": run["head_sha"], "workflow": run["path"], "branch": run["head_branch"],
        "job_ids": [record["job_id"] for record in job_records], "artifact_archives": outer,
        "provider_compare_sha256": combined, "test_count": next(iter(test_counts)), "mutation_ids": expected_mutations,
    }
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
