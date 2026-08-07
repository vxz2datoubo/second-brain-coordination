"""Provider artifact verification with metadata and downloaded-byte binding."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Mapping, Sequence

from .authority import AuthorityError


SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_VERSIONS = ("3.11", "3.13")
EXPECTED_SEEDS = ("0", "1", "777")


@dataclass(frozen=True, slots=True)
class DownloadedArtifact:
    artifact_id: int
    name: str
    job_id: int | None
    payload: bytes
    recorded_sha256: str

    def verify_bytes(self) -> bool:
        return isinstance(self.payload, bytes) and sha256(self.payload).hexdigest() == self.recorded_sha256


def _require_sha40(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA40.fullmatch(value):
        raise AuthorityError(f"{field} must be a lowercase SHA-40")
    return value


def _require_positive(value: object, field: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise AuthorityError(f"{field} must be a positive integer")
    return value


def _expected_job_name(version: str, seed: str) -> str:
    return f"authority / py{version} / seed={seed}"


def _expected_artifact_name(kind: str, version: str, seed: str) -> str:
    return f"{kind}-py{version}-seed{seed}"


def validate_provider_evidence(
    run: Mapping[str, object],
    jobs: Sequence[Mapping[str, object]],
    artifacts: Sequence[DownloadedArtifact],
    *,
    expected_head: str,
    expected_workflow: str,
    expected_branch: str,
    expected_test_count: int,
    expected_mutation_ids: Sequence[str],
    expected_versions: Sequence[str] = EXPECTED_VERSIONS,
    expected_seeds: Sequence[str] = EXPECTED_SEEDS,
) -> str:
    """Bind a six-job provider matrix to actual metadata and downloaded bytes."""
    _require_sha40(expected_head, "expected_head")
    if run.get("head_sha") != expected_head or run.get("workflow") != expected_workflow or run.get("branch") != expected_branch:
        raise AuthorityError("provider run metadata does not match the exact route")
    if run.get("conclusion") != "success":
        raise AuthorityError("provider run did not succeed")
    _require_positive(run.get("run_id"), "provider run_id")
    expected_pairs = {(version, seed) for version in expected_versions for seed in expected_seeds}
    if len(jobs) != len(expected_pairs):
        raise AuthorityError("provider job count is not the exact version/seed matrix")
    jobs_by_pair: dict[tuple[str, str], Mapping[str, object]] = {}
    job_ids: set[int] = set()
    for job in jobs:
        version, seed = job.get("python_version"), job.get("hash_seed")
        if not isinstance(version, str) or not isinstance(seed, str) or (version, seed) not in expected_pairs:
            raise AuthorityError("provider job is outside the approved matrix")
        job_id = _require_positive(job.get("job_id"), "provider job_id")
        if job_id in job_ids or (version, seed) in jobs_by_pair:
            raise AuthorityError("provider jobs contain duplicate IDs or matrix pairs")
        job_ids.add(job_id)
        jobs_by_pair[(version, seed)] = job
        if job.get("name") != _expected_job_name(version, seed) or job.get("conclusion") != "success":
            raise AuthorityError("provider job name or conclusion differs from the required matrix")
        if job.get("head_sha") != expected_head or job.get("test_count") != expected_test_count:
            raise AuthorityError("provider job head or test count differs from the exact tested suite")
        ids = job.get("mutation_ids")
        if not isinstance(ids, list) or tuple(sorted(ids)) != tuple(sorted(expected_mutation_ids)) or len(ids) != len(set(ids)):
            raise AuthorityError("provider job mutation IDs are incomplete, changed, or duplicated")
    if set(jobs_by_pair) != expected_pairs:
        raise AuthorityError("provider matrix is incomplete")
    expected_artifact_keys = {
        (_expected_artifact_name(kind, version, seed), jobs_by_pair[(version, seed)]["job_id"])
        for version, seed in expected_pairs
        for kind in ("canonical", "environment")
    }
    observed_keys: set[tuple[str, int | None]] = set()
    artifact_ids: set[int] = set()
    payload_digests: list[str] = []
    compare: DownloadedArtifact | None = None
    for artifact in artifacts:
        if artifact.artifact_id in artifact_ids or not artifact.verify_bytes():
            raise AuthorityError("provider artifact ID is duplicated or downloaded bytes do not match its digest")
        artifact_ids.add(artifact.artifact_id)
        if artifact.name == "provider-compare":
            if artifact.job_id is not None or compare is not None:
                raise AuthorityError("provider compare artifact must be a unique run-level artifact")
            compare = artifact
            continue
        key = (artifact.name, artifact.job_id)
        if key not in expected_artifact_keys or key in observed_keys:
            raise AuthorityError("provider artifact name/job binding is unexpected or duplicated")
        observed_keys.add(key)
        payload_digests.append(artifact.recorded_sha256)
    if observed_keys != expected_artifact_keys or compare is None:
        raise AuthorityError("provider artifact set is incomplete")
    compare_expected = sha256("".join(sorted(payload_digests)).encode("ascii")).hexdigest()
    try:
        compare_body = json.loads(compare.payload.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthorityError("provider compare artifact is not strict JSON") from exc
    if not isinstance(compare_body, Mapping) or compare_body.get("artifact_digests") != sorted(payload_digests) or compare_body.get("combined_sha256") != compare_expected:
        raise AuthorityError("compare artifact body is not bound to downloaded job artifact byte digests")
    return compare_expected
