"""Immutable public-safe event and relation contracts for S0C."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Any, Mapping
from types import MappingProxyType


class SignalPlaneError(ValueError):
    """A stable, public-safe validation or integrity error."""

    def __init__(self, code: str, path: str, message: str):
        super().__init__(message)
        self.code, self.path = code, path


REQUIRED_EVENT_FIELDS = frozenset({
    "schema_version", "signal_id", "event_id", "event_source", "event_type", "occurred_at",
    "observed_at", "source_type", "source_ref", "source_project", "source_actor",
    "primary_domain", "related_domains", "signal_kind", "planning_state", "execution_state",
    "epistemic_state", "privacy_scope_ref", "authority_targets", "touch_set", "related_signal_refs",
    "supersedes_refs", "revokes_refs", "cross_domain_candidate", "summary_ref",
})
OPTIONAL_EVENT_FIELDS = frozenset({
    "event_subject", "source_sequence", "ledger_partition", "ledger_offset", "idempotency_key",
    "causation_event_refs", "correlation_refs", "trace_context_ref", "source_window_ref", "raw_content_ref",
    "payload_schema_ref", "content_hash", "expected_projection_version", "public_safe_metadata",
})
ALLOWED_EVENT_FIELDS = REQUIRED_EVENT_FIELDS | OPTIONAL_EVENT_FIELDS
FORBIDDEN_FIELD_NAMES = frozenset({"raw_secret", "credential_value", "access_token", "api_key", "private_key", "private_chain_of_thought", "raw_source_body", "password"})
RELATION_TYPES = frozenset({
    "DUPLICATE", "EXTENDS", "REINFORCES", "CONTRADICTS", "SUPERSEDES", "DEPENDS_ON", "BLOCKS",
    "SHARED_SURFACE", "SHARED_EVIDENCE", "AUTHORITY_COLLISION", "CAN_MERGE", "CAN_PARALLEL",
    "MUST_SERIALIZE", "REVIEWER_CANDIDATE", "COUNTERFACTUAL_PAIR", "CROSS_DOMAIN_TRANSFER_CANDIDATE",
})
PLANNING_STATES = frozenset({"CAPTURED", "TRIAGED", "IDEA_ONLY", "WATCH", "CANDIDATE", "ROUTE_TO_MISSION", "MERGED_WITH_OTHER_SIGNAL", "DEFERRED", "CONFLICTED", "SUPERSEDED", "REJECTED", "CLOSED_NO_ACTION"})
EXECUTION_STATES = frozenset({"NOT_STARTED", "AUTHORIZED", "EXECUTING", "REVIEW", "DONE", "BLOCKED", "CANCELLED"})
EPISTEMIC_STATES = frozenset({"USER_EXPLICIT", "CONFIRMED_FACT", "HIGH_CONFIDENCE_INFERENCE", "CANDIDATE_HYPOTHESIS", "UNKNOWN", "NEEDS_REVALIDATION"})


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _timestamp(value: str, path: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise SignalPlaneError("INVALID_TIMESTAMP", path, "timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise SignalPlaneError("NAIVE_TIMESTAMP_FORBIDDEN", path, "timestamp must carry an offset")


def _reject_private(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            if key in FORBIDDEN_FIELD_NAMES:
                raise SignalPlaneError("PRIVATE_OR_SECRET_FIELD_FORBIDDEN", child_path, "private or secret material is not admissible")
            _reject_private(child, child_path)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_private(child, f"{path}/{index}")
    elif isinstance(value, str) and any(token in value.lower() for token in ("ghp_", "sk-", "-----begin private key", "password=")):
        raise SignalPlaneError("PRIVATE_OR_SECRET_VALUE_FORBIDDEN", path or "/", "secret-like value is not admissible")


@dataclass(frozen=True)
class SignalEvent:
    """An immutable admitted-event candidate; the ledger persists its canonical snapshot."""

    data: Mapping[str, Any]

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SignalEvent":
        if not isinstance(payload, Mapping):
            raise SignalPlaneError("EVENT_NOT_OBJECT", "/", "event must be an object")
        missing = sorted(REQUIRED_EVENT_FIELDS - set(payload))
        if missing:
            raise SignalPlaneError("MISSING_REQUIRED_FIELD", f"/{missing[0]}", "required event field is missing")
        unexpected = sorted(set(payload) - ALLOWED_EVENT_FIELDS)
        if unexpected:
            raise SignalPlaneError("UNRECOGNIZED_OR_PRIVATE_FIELD", f"/{unexpected[0]}", "unrecognized fields are rejected fail-closed")
        _reject_private(payload)
        for name in ("schema_version", "signal_id", "event_id", "event_source", "event_type", "source_type", "source_ref", "source_project", "source_actor", "primary_domain", "signal_kind", "privacy_scope_ref", "summary_ref"):
            if not isinstance(payload[name], str) or not payload[name].strip():
                raise SignalPlaneError("INVALID_STRING", f"/{name}", "must be a non-empty string")
        _timestamp(payload["occurred_at"], "/occurred_at")
        _timestamp(payload["observed_at"], "/observed_at")
        for name in ("related_domains", "authority_targets", "touch_set", "related_signal_refs", "supersedes_refs", "revokes_refs"):
            if not isinstance(payload[name], list):
                raise SignalPlaneError("INVALID_ARRAY", f"/{name}", "must be an array")
        if not isinstance(payload["cross_domain_candidate"], bool):
            raise SignalPlaneError("INVALID_BOOLEAN", "/cross_domain_candidate", "must be boolean")
        if payload["planning_state"] not in PLANNING_STATES:
            raise SignalPlaneError("INVALID_PLANNING_STATE", "/planning_state", "unknown planning state")
        if payload["execution_state"] not in EXECUTION_STATES:
            raise SignalPlaneError("INVALID_EXECUTION_STATE", "/execution_state", "unknown execution state")
        if payload["epistemic_state"] not in EPISTEMIC_STATES:
            raise SignalPlaneError("INVALID_EPISTEMIC_STATE", "/epistemic_state", "unknown epistemic state")
        if payload["execution_state"] == "AUTHORIZED" and "CONTROL_TOWER_310" not in payload["authority_targets"]:
            raise SignalPlaneError("MISSING_EXECUTION_AUTHORIZATION", "/authority_targets", "Signal Plane cannot self-authorize execution")
        snapshot = json.loads(_canonical(dict(payload)))
        event = cls(MappingProxyType(snapshot))
        supplied_hash = snapshot.get("content_hash")
        if supplied_hash is not None and supplied_hash != event.semantic_hash:
            raise SignalPlaneError("SEMANTIC_CONTENT_HASH_MISMATCH", "/content_hash", "declared content hash does not match canonical semantic content")
        return event

    @property
    def semantic_hash(self) -> str:
        value = dict(self.data)
        value.pop("observed_at", None)
        value.pop("content_hash", None)
        return _hash(value)

    @property
    def idempotency_key(self) -> str:
        return str(self.data.get("idempotency_key") or f"{self.data['event_source']}:{self.data['event_id']}")

    def as_dict(self) -> dict[str, Any]:
        return json.loads(_canonical(dict(self.data)))


@dataclass(frozen=True)
class SignalLink:
    link_id: str
    from_signal_ref: str
    to_signal_ref: str
    relation_type: str
    evidence_refs: tuple[str, ...]
    created_at: str
    created_by: str

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SignalLink":
        required = ("link_id", "from_signal_ref", "to_signal_ref", "relation_type", "evidence_refs", "created_at", "created_by")
        for field in required:
            if field not in payload:
                raise SignalPlaneError("MISSING_REQUIRED_FIELD", f"/{field}", "required relation field is missing")
        _reject_private(payload)
        if payload["relation_type"] not in RELATION_TYPES:
            raise SignalPlaneError("INVALID_RELATION_TYPE", "/relation_type", "unknown relation")
        if not isinstance(payload["evidence_refs"], list) or not payload["evidence_refs"]:
            raise SignalPlaneError("LINK_PROVENANCE_REQUIRED", "/evidence_refs", "links require public-safe provenance refs")
        _timestamp(payload["created_at"], "/created_at")
        return cls(*(str(payload[field]) if field != "evidence_refs" else tuple(map(str, payload[field])) for field in required))

    def as_dict(self) -> dict[str, Any]:
        return {"link_id": self.link_id, "from_signal_ref": self.from_signal_ref, "to_signal_ref": self.to_signal_ref, "relation_type": self.relation_type, "evidence_refs": list(self.evidence_refs), "created_at": self.created_at, "created_by": self.created_by}
