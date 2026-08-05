"""Fail-closed schema checks for public Provider evidence artifacts."""

from __future__ import annotations

import re
from typing import Mapping, Sequence

from .authority import AuthorityError


SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def validate_environment_evidence(environment: Mapping[str, object], *, expected_head: str, expected_test_count: int, expected_mutation_ids: Sequence[str]) -> None:
    if not SHA40.fullmatch(expected_head):
        raise AuthorityError("expected provider head must be a SHA-40")
    if environment.get("head_sha") != expected_head:
        raise AuthorityError("Provider environment head is not the exact tested head")
    if environment.get("test_count") != expected_test_count or not isinstance(expected_test_count, int) or expected_test_count <= 0:
        raise AuthorityError("Provider test count is missing or differs from the tested suite")
    ids = environment.get("mutation_ids")
    if not isinstance(ids, list) or sorted(ids) != sorted(expected_mutation_ids) or len(ids) != len(set(ids)):
        raise AuthorityError("Provider mutation IDs are incomplete, changed, or duplicated")
    if environment.get("mutation_count") != len(expected_mutation_ids):
        raise AuthorityError("Provider mutation count differs from the registered IDs")
    for field in ("command_sha256", "stdout_sha256", "stderr_sha256", "canonical_artifact_sha256"):
        value = environment.get(field)
        if not isinstance(value, str) or not SHA256.fullmatch(value):
            raise AuthorityError(f"Provider evidence has invalid {field}")
    if not isinstance(environment.get("python_version"), str) or not isinstance(environment.get("hash_seed"), str):
        raise AuthorityError("Provider runtime identity is incomplete")


def validate_matrix(environments: Sequence[Mapping[str, object]], *, expected_head: str, expected_test_count: int, expected_mutation_ids: Sequence[str], expected_python_versions: Sequence[str] = ("3.11", "3.13"), expected_seeds: Sequence[str] = ("0", "1", "777")) -> None:
    if len(environments) != len(expected_python_versions) * len(expected_seeds):
        raise AuthorityError("Provider matrix job count is not exact")
    observed: set[tuple[str, str]] = set()
    for environment in environments:
        validate_environment_evidence(environment, expected_head=expected_head, expected_test_count=expected_test_count, expected_mutation_ids=expected_mutation_ids)
        key = (str(environment["python_version"]), str(environment["hash_seed"]))
        observed.add(key)
    expected = {(version, seed) for version in expected_python_versions for seed in expected_seeds}
    if observed != expected:
        raise AuthorityError("Provider matrix lacks an exact version/seed pair")
