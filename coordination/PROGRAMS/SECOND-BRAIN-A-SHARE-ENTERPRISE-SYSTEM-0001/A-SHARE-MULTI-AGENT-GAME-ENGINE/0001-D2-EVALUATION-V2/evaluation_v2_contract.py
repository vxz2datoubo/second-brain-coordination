"""Public-safe deterministic contracts for E22 Evaluation V2.

This module deliberately has no dependency on production D2 reducers.  It is
used only by the synthetic evaluation harness and its receipts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


EXPECTED_D2_CORE_SHA256 = "0bc7c7fba622440113bacb476c43f12245504fff35b3492969b485ac0f619afb"
SYNTHETIC_ONLY = "SYNTHETIC_ONLY"


def public_value(value: Any) -> Any:
    """Convert immutable synthetic carriers to stable, JSON-safe primitives."""
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


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    family: str
    variant: int
    requirement_id: str
    test_id: str


@dataclass(frozen=True)
class InvariantSpec:
    invariant_id: str
    requirement_id: str
    fixture_id: str
    predicate_id: str
    failure_oracle_id: str
    test_id: str


@dataclass(frozen=True)
class NegativeCaseSpec:
    negative_id: str
    family: str
    variant: int
    expected_failure_class: str
    test_id: str


@dataclass(frozen=True)
class EpisodeSpec:
    episode_id: str
    variant: int
    requirement_id: str
    test_id: str


@dataclass(frozen=True)
class CounterfactualSpec:
    pair_id: str
    variant: int
    changed_assumption_id: str
    test_id: str


@dataclass(frozen=True)
class CrossFamilySpec:
    interaction_id: str
    mutant_id: str
    property_id: str
    test_id: str


@dataclass(frozen=True)
class MutationActivation:
    mutant_id: str
    family: str
    fixture_id: str
    baseline_digest: str
    mutated_digest: str
    behavior_changed: bool
    killer_test_ids: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class MutationKill:
    mutant_id: str
    test_id: str
    oracle_id: str
    killed: bool
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
    passed: bool
    observation: str
    baseline_digest: str
    transformed_digest: str


def report_row(value: Any) -> dict[str, Any]:
    """Return a sorted public row for JSONL-like receipts without file I/O."""
    row = public_value(value)
    if not isinstance(row, dict):
        raise TypeError("REPORT_ROW_REQUIRES_MAPPING")
    return {key: row[key] for key in sorted(row)}
