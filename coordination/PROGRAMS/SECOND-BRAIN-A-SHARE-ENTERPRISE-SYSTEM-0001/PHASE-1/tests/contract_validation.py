"""Minimal semantic gates for P1 public-safe fixtures; no runtime or market access."""

from __future__ import annotations

from datetime import datetime
import re


class ContractViolation(ValueError):
    """Raised when a public P1 contract gate rejects a record."""


_OBJECT_ID = re.compile(r"^[a-z][a-z0-9_.:-]{2,127}$")
_SEMVER = re.compile(r"^(?P<major>[0-9]+)\.(?P<minor>[0-9]+)\.(?P<patch>[0-9]+)$")
_STATUSES = {"candidate", "approved", "rejected", "superseded", "quarantined", "experimental", "active"}


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def compatible_version(version: str, supported_major: int = 1) -> bool:
    match = _SEMVER.fullmatch(version)
    return bool(match and int(match.group("major")) == supported_major)


def validate_shared(record: dict) -> None:
    required = ("object_id", "schema_version", "producer", "run_id", "trace_id", "status", "created_at", "lineage")
    missing = [name for name in required if not record.get(name)]
    if missing:
        raise ContractViolation(f"shared envelope missing: {', '.join(missing)}")
    if not _OBJECT_ID.fullmatch(record["object_id"]):
        raise ContractViolation("object_id is not stable-contract shaped")
    if not compatible_version(record["schema_version"]):
        raise ContractViolation("unsupported schema major version")
    if record["status"] not in _STATUSES:
        raise ContractViolation("unknown lifecycle status")
    if not isinstance(record["lineage"], list) or not record["lineage"]:
        raise ContractViolation("lineage must be a non-empty list")
    _time(record["created_at"])


def validate_temporal(record: dict) -> None:
    required = ("event_time", "observed_at", "receive_time", "entered_system_at", "available_at", "as_of", "timezone")
    missing = [name for name in required if not record.get(name)]
    if missing:
        raise ContractViolation(f"temporal fields missing: {', '.join(missing)}")
    event, observed, received, entered, available, as_of = (_time(record[name]) for name in required[:-1])
    if event > observed or received > entered:
        raise ContractViolation("temporal observation/entry order is invalid")
    if available > as_of:
        raise ContractViolation("future data leakage: available_at is after as_of")


def validate_lineage_quality(record: dict) -> None:
    for name in ("source_reliability", "quality_score"):
        value = record.get(name)
        if not isinstance(value, (float, int)) or not 0 <= value <= 1:
            raise ContractViolation(f"{name} must be within [0, 1]")
    for name in ("source_refs", "artifact_refs"):
        if not isinstance(record.get(name), list) or not record[name]:
            raise ContractViolation(f"{name} must be non-empty")


def validate_capability(record: dict) -> None:
    required = ("capability_id", "capability_level", "entitlement_id", "entitlement_status", "gate_result")
    if any(not record.get(name) for name in required):
        raise ContractViolation("capability/entitlement reference is missing")
    allowed = record["gate_result"] == "allowed"
    confirmed = record["entitlement_status"] == "confirmed"
    if allowed and not confirmed:
        raise ContractViolation("allowed capability requires confirmed entitlement")
    if not allowed and not record.get("abstention_reason"):
        raise ContractViolation("degraded/rejected capability requires abstention_reason")


def validate_approval(record: dict) -> None:
    if record.get("no_trade_gate") is not True:
        raise ContractViolation("P1 requires no_trade_gate=true")
    if not record.get("rollback_pointer"):
        raise ContractViolation("rollback_pointer is required")
    if record.get("proposed_action") == "execution":
        raise ContractViolation("execution is prohibited in P1")
    if record.get("change_class") == "irreversible" and not record.get("human_approval_ref"):
        raise ContractViolation("irreversible change requires human_approval_ref")
    if record.get("authority_write"):
        if record.get("status") == "candidate":
            raise ContractViolation("candidate cannot write authority")
        if not record.get("human_approval_ref"):
            raise ContractViolation("authority write requires human_approval_ref")


def validate_replay_envelope(record: dict) -> None:
    validate_shared(record)
    validate_temporal(record)
    validate_lineage_quality(record)
    validate_capability(record)
    validate_approval(record)
