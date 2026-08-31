"""Public-safe contract for a future local customer-intake boundary.

This module intentionally has no filesystem, network, credential, media, or
customer-content handling.  It validates only an opaque local reference and
fixed governance coordinates so the eventual local service can project private
data into the creative runtime without teaching GitHub code to store it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import re
from typing import Any

from .contracts import canonical_json


INTAKE_SCHEMA = "CreativeLocalIntakeProjection/v1"
POLICY_SCHEMA = "CreativeLocalIntakePolicy/v1"
_REQUEST_PATTERN = re.compile(r"req_[a-f0-9]{20}")
_CUSTOMER_REFERENCE_PATTERN = re.compile(r"cust_[a-f0-9]{16}")
_CONSENT_PATTERN = re.compile(r"consent-v[1-9][0-9]*")
_HASH_PATTERN = re.compile(r"[a-f0-9]{64}")
_POLICY_PATTERN = re.compile(r"policy_[a-f0-9]{16}")


class LocalIntakeViolation(ValueError):
    """Raised before a private local intake can become a runtime projection."""


def _parse_utc(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise LocalIntakeViolation(field + " must be an RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise LocalIntakeViolation(field + " must include a timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class LocalIntakeProjection:
    """The only public-safe shape allowed to cross from a future local vault."""

    request_id: str
    customer_reference: str
    consent_revision: str
    input_hash: str
    received_at: str
    retention_deadline: str
    content_rating: str
    cost_limit_minor: int
    provider_confirmation: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": INTAKE_SCHEMA,
            "request_id": self.request_id,
            "customer_reference": self.customer_reference,
            "consent_revision": self.consent_revision,
            "input_hash": self.input_hash,
            "received_at": self.received_at,
            "retention_deadline": self.retention_deadline,
            "content_rating": self.content_rating,
            "cost_limit_minor": self.cost_limit_minor,
            "provider_confirmation": self.provider_confirmation,
        }


@dataclass(frozen=True)
class LocalIntakePolicy:
    """Immutable, public-safe approval coordinates for a future local adapter.

    This is not a customer policy store and it cannot grant provider access. It
    intentionally carries only exact, non-secret values that a later local
    operator must select before an opaque projection can be admitted.
    """

    policy_id: str
    approved_consent_revisions: tuple[str, ...]
    maximum_retention_seconds: int
    maximum_cost_limit_minor: int
    allowed_content_rating: str = "non_explicit"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": POLICY_SCHEMA,
            "policy_id": self.policy_id,
            "approved_consent_revisions": list(self.approved_consent_revisions),
            "maximum_retention_seconds": self.maximum_retention_seconds,
            "maximum_cost_limit_minor": self.maximum_cost_limit_minor,
            "allowed_content_rating": self.allowed_content_rating,
        }

    def fingerprint(self) -> str:
        """Return the stable SHA-256 identity of the selected policy values."""

        return sha256(canonical_json(self.to_dict()).encode("utf-8")).hexdigest()


def _require_non_negative_integer(value: Any, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LocalIntakeViolation(field + " must be a non-negative integer")


def _validate_policy(policy: LocalIntakePolicy) -> None:
    if not _POLICY_PATTERN.fullmatch(policy.policy_id):
        raise LocalIntakeViolation("policy_id must be a stable opaque policy_<16 lowercase hex> identifier")
    if not policy.approved_consent_revisions:
        raise LocalIntakeViolation("approved_consent_revisions must contain at least one exact consent revision")
    if len(set(policy.approved_consent_revisions)) != len(policy.approved_consent_revisions):
        raise LocalIntakeViolation("approved_consent_revisions must not contain duplicates")
    if any(not _CONSENT_PATTERN.fullmatch(value) for value in policy.approved_consent_revisions):
        raise LocalIntakeViolation("approved_consent_revisions must contain only versioned consent-vN identifiers")
    _require_non_negative_integer(policy.maximum_retention_seconds, "maximum_retention_seconds")
    if policy.maximum_retention_seconds == 0:
        raise LocalIntakeViolation("maximum_retention_seconds must be greater than zero")
    _require_non_negative_integer(policy.maximum_cost_limit_minor, "maximum_cost_limit_minor")
    if policy.allowed_content_rating != "non_explicit":
        raise LocalIntakeViolation("allowed_content_rating must remain non_explicit in this runtime")


def validate_local_intake(
    projection: LocalIntakeProjection,
    *,
    observed_at: str,
    policy: LocalIntakePolicy,
) -> None:
    """Fail closed on identity, policy, consent, retention, content, or cost drift."""

    _validate_policy(policy)
    if not _REQUEST_PATTERN.fullmatch(projection.request_id):
        raise LocalIntakeViolation("request_id must be a stable opaque req_<20 lowercase hex> identifier")
    if not _CUSTOMER_REFERENCE_PATTERN.fullmatch(projection.customer_reference):
        raise LocalIntakeViolation("customer_reference must be an opaque local cust_<16 lowercase hex> identifier")
    if not _CONSENT_PATTERN.fullmatch(projection.consent_revision):
        raise LocalIntakeViolation("consent_revision must be a versioned consent-vN identifier")
    if not _HASH_PATTERN.fullmatch(projection.input_hash):
        raise LocalIntakeViolation("input_hash must be a 64-character lowercase SHA-256 digest")
    received_at = _parse_utc(projection.received_at, "received_at")
    deadline = _parse_utc(projection.retention_deadline, "retention_deadline")
    observed = _parse_utc(observed_at, "observed_at")
    if deadline <= received_at:
        raise LocalIntakeViolation("retention_deadline must be after received_at")
    if observed >= deadline:
        raise LocalIntakeViolation("local intake retention deadline has expired")
    if (deadline - received_at).total_seconds() > policy.maximum_retention_seconds:
        raise LocalIntakeViolation("local intake retention window exceeds the selected policy")
    if projection.consent_revision not in policy.approved_consent_revisions:
        raise LocalIntakeViolation("consent_revision is not approved by the selected local policy")
    if projection.content_rating != policy.allowed_content_rating:
        raise LocalIntakeViolation("local intake content rating is not allowed by the selected policy")
    _require_non_negative_integer(projection.cost_limit_minor, "cost_limit_minor")
    if projection.cost_limit_minor > policy.maximum_cost_limit_minor:
        raise LocalIntakeViolation("local intake cost limit exceeds the approved local ceiling")
    # A true confirmation is merely an explicit data point. It is never a
    # provider invocation authorization in this offline/GitHub runtime.
    if not isinstance(projection.provider_confirmation, bool):
        raise LocalIntakeViolation("provider_confirmation must be boolean")


def local_intake_gate_report(
    projection: LocalIntakeProjection,
    *,
    observed_at: str,
    policy: LocalIntakePolicy,
) -> dict[str, Any]:
    """Return a clear boundary report after deterministic validation only."""

    validate_local_intake(
        projection,
        observed_at=observed_at,
        policy=policy,
    )
    return {
        "schema": "CreativeLocalIntakeGateReport/v1",
        "status": "local_intake_projection_valid",
        "projection": projection.to_dict(),
        "policy": policy.to_dict(),
        "policy_fingerprint": policy.fingerprint(),
        "external_provider_authorized": False,
        "customer_vault_accessed": False,
        "canonical_knowledge_write": False,
        "note": "Validation of an opaque projection only; no customer material is read or stored by this module.",
    }
