"""Canonical aggregate for the two-job E60 Provider evidence matrix."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Mapping, Sequence


_HEX_40 = re.compile(r"^[0-9a-f]{40}$")
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_NUMERIC_ID = re.compile(r"^[1-9][0-9]*$")
_REQUIRED_PYTHON_VERSIONS = ("3.11", "3.13")


class ProviderEvidenceError(ValueError):
    """Provider evidence is incomplete, ambiguous, or non-canonical."""


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def _hex(value: object, length: int, field: str) -> str:
    text = str(value)
    matcher = _HEX_40 if length == 40 else _HEX_64
    if not matcher.fullmatch(text):
        raise ProviderEvidenceError(f"{field.upper()}_MALFORMED")
    return text


def _numeric_id(value: object, field: str) -> str:
    text = str(value)
    if not _NUMERIC_ID.fullmatch(text):
        raise ProviderEvidenceError(f"{field.upper()}_MALFORMED")
    return text


@dataclass(frozen=True, slots=True)
class ProviderJobArtifact:
    python_minor: str
    job_id: str
    artifact_id: str
    artifact_content_sha256: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "ProviderJobArtifact":
        required = {"python_minor", "job_id", "artifact_id", "artifact_content_sha256"}
        if set(value) != required:
            raise ProviderEvidenceError("PROVIDER_JOB_ARTIFACT_FIELD_SET_MISMATCH")
        python_minor = str(value["python_minor"])
        if python_minor not in _REQUIRED_PYTHON_VERSIONS:
            raise ProviderEvidenceError("PROVIDER_JOB_ARTIFACT_PYTHON_VERSION_UNSUPPORTED")
        return cls(
            python_minor=python_minor,
            job_id=_numeric_id(value["job_id"], "job_id"),
            artifact_id=_numeric_id(value["artifact_id"], "artifact_id"),
            artifact_content_sha256=_hex(value["artifact_content_sha256"], 64, "artifact_content_sha256"),
        )

    def mapping(self) -> dict[str, str]:
        return {
            "python_minor": self.python_minor,
            "job_id": self.job_id,
            "artifact_id": self.artifact_id,
            "artifact_content_sha256": self.artifact_content_sha256,
        }


@dataclass(frozen=True, slots=True)
class ProviderEvidenceAggregate:
    """A lossless, canonical binding for the mandatory 3.11/3.13 matrix."""

    task_id: str
    provider_run_id: str
    tested_head: str
    tested_parent: str
    tested_tree: str
    jobs: tuple[ProviderJobArtifact, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "ProviderEvidenceAggregate":
        required = {"schema_version", "task_id", "provider_run_id", "tested_head", "tested_parent", "tested_tree", "jobs"}
        if set(value) != required or value.get("schema_version") != "1.0":
            raise ProviderEvidenceError("PROVIDER_EVIDENCE_AGGREGATE_FIELD_SET_MISMATCH")
        raw_jobs = value["jobs"]
        if not isinstance(raw_jobs, Sequence) or isinstance(raw_jobs, (str, bytes)):
            raise ProviderEvidenceError("PROVIDER_EVIDENCE_AGGREGATE_JOBS_MALFORMED")
        jobs = tuple(ProviderJobArtifact.from_mapping(item) for item in raw_jobs if isinstance(item, Mapping))
        if len(jobs) != len(raw_jobs):
            raise ProviderEvidenceError("PROVIDER_EVIDENCE_AGGREGATE_JOB_NOT_MAPPING")
        if tuple(sorted(job.python_minor for job in jobs)) != _REQUIRED_PYTHON_VERSIONS:
            raise ProviderEvidenceError("PROVIDER_EVIDENCE_AGGREGATE_MATRIX_INCOMPLETE")
        return cls(
            task_id=str(value["task_id"]),
            provider_run_id=_numeric_id(value["provider_run_id"], "provider_run_id"),
            tested_head=_hex(value["tested_head"], 40, "tested_head"),
            tested_parent=_hex(value["tested_parent"], 40, "tested_parent"),
            tested_tree=_hex(value["tested_tree"], 40, "tested_tree"),
            jobs=tuple(sorted(jobs, key=lambda job: job.python_minor)),
        )

    def mapping(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "task_id": self.task_id,
            "provider_run_id": self.provider_run_id,
            "tested_head": self.tested_head,
            "tested_parent": self.tested_parent,
            "tested_tree": self.tested_tree,
            "jobs": [job.mapping() for job in self.jobs],
        }

    @property
    def digest(self) -> str:
        return sha256(canonical_json_bytes(self.mapping())).hexdigest()
