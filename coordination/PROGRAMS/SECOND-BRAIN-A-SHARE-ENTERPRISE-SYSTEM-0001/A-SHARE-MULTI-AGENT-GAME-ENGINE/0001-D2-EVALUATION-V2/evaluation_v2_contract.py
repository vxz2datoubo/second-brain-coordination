"""Public-safe contracts for the synthetic-only Evaluation V2 correction.

These records describe test evidence, not market participants, market data, or
trading instructions.  Normalized signatures are first-class evidence: a new
identifier alone can never make a duplicated semantic case count as coverage.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping


EXPECTED_D2_CORE_SHA256 = "0bc7c7fba622440113bacb476c43f12245504fff35b3492969b485ac0f619afb"
SYNTHETIC_ONLY = "SYNTHETIC_ONLY"


def public_value(value: Any) -> Any:
    """Convert immutable synthetic carriers to stable JSON-safe primitives."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: public_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [public_value(item) for item in value]
    if isinstance(value, list):
        return [public_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): public_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError("PUBLIC_VALUE_UNSUPPORTED_TYPE:" + type(value).__name__)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        public_value(value), ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def normalized_signature(kind: str, semantic_input: Mapping[str, Any], expected_relation: Mapping[str, Any]) -> tuple[str, str]:
    """Return input and relation hashes without admitting identifier-only diversity."""
    return (
        canonical_sha256({"kind": kind, "input": semantic_input}),
        canonical_sha256({"kind": kind, "expected_relation": expected_relation}),
    )


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    family: str
    variant: int
    semantic_input: tuple[tuple[str, Any], ...]
    expected_relation: tuple[tuple[str, Any], ...]
    requirement_id: str
    test_id: str

    @property
    def signatures(self) -> tuple[str, str]:
        return normalized_signature("scenario", dict(self.semantic_input), dict(self.expected_relation))


@dataclass(frozen=True)
class InvariantSpec:
    invariant_id: str
    fixture_id: str
    predicate_id: str
    semantic_input: tuple[tuple[str, Any], ...]
    expected_relation: tuple[tuple[str, Any], ...]
    requirement_id: str
    failure_oracle_id: str
    test_id: str

    @property
    def signatures(self) -> tuple[str, str]:
        return normalized_signature("invariant", dict(self.semantic_input), dict(self.expected_relation))


@dataclass(frozen=True)
class NegativeCaseSpec:
    negative_id: str
    family: str
    variant: int
    semantic_input: tuple[tuple[str, Any], ...]
    expected_relation: tuple[tuple[str, Any], ...]
    expected_failure_class: str
    test_id: str

    @property
    def signatures(self) -> tuple[str, str]:
        return normalized_signature("negative", dict(self.semantic_input), dict(self.expected_relation))


@dataclass(frozen=True)
class EpisodeSpec:
    episode_id: str
    variant: int
    semantic_input: tuple[tuple[str, Any], ...]
    expected_relation: tuple[tuple[str, Any], ...]
    requirement_id: str
    test_id: str

    @property
    def signatures(self) -> tuple[str, str]:
        return normalized_signature("episode", dict(self.semantic_input), dict(self.expected_relation))


@dataclass(frozen=True)
class CounterfactualSpec:
    pair_id: str
    variant: int
    changed_assumption_id: str
    semantic_input: tuple[tuple[str, Any], ...]
    expected_relation: tuple[tuple[str, Any], ...]
    test_id: str

    @property
    def signatures(self) -> tuple[str, str]:
        return normalized_signature("counterfactual", dict(self.semantic_input), dict(self.expected_relation))


@dataclass(frozen=True)
class CrossFamilySpec:
    interaction_id: str
    mutant_id: str
    property_id: str
    fixture_variant: int
    semantic_input: tuple[tuple[str, Any], ...]
    expected_relation: tuple[tuple[str, Any], ...]
    test_id: str

    @property
    def signatures(self) -> tuple[str, str]:
        return normalized_signature("cross_family", dict(self.semantic_input), dict(self.expected_relation))


@dataclass(frozen=True)
class MutationActivation:
    mutant_id: str
    family: str
    fixture_id: str
    source_sha256: str
    mutant_source_sha256: str
    baseline_semantic_digest: str
    mutant_semantic_digest: str
    behavior_changed: bool
    execution_mode: str
    status: str


@dataclass(frozen=True)
class MutationKill:
    mutant_id: str
    test_id: str
    oracle_id: str
    killed: bool
    reason_codes: tuple[str, ...]
    digest_only: bool
    observation: str


@dataclass(frozen=True)
class OracleReport:
    valid: bool
    reason_codes: tuple[str, ...]
    independent_digest: str
    checked_rules: tuple[str, ...]


@dataclass(frozen=True)
class PropertyReport:
    property_id: str
    paired_mutant_id: str
    transformation_id: str
    baseline_passed: bool
    mutant_detected: bool
    observation: str
    baseline_digest: str
    transformed_digest: str

    @property
    def passed(self) -> bool:
        return self.baseline_passed and self.mutant_detected


def report_row(value: Any) -> dict[str, Any]:
    """Return a sorted public row for deterministic in-memory receipts."""
    row = public_value(value)
    if not isinstance(row, dict):
        raise TypeError("REPORT_ROW_REQUIRES_MAPPING")
    return {key: row[key] for key in sorted(row)}
