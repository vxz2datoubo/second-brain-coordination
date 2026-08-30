"""Public-safe contract for a future local customer-intake boundary.

This module intentionally has no filesystem, network, credential, media, or
customer-content handling.  It validates only an opaque local reference and
fixed governance coordinates so the eventual local service can project private
data into the creative runtime without teaching GitHub code to store it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any


INTAKE_SCHEMA = "CreativeLocalIntakeProjection/v1"
_REQUEST_PATTERN = re.compile(r"req_[a-f0-9]{20}")
_CUSTOMER_REFERENCE_PATTERN = re.compile(r"cust_[a-f0-9]{16}")
_CONSENT_PATTERN = re.compile(r"consent-v[1-9][0-9]*")
_HASH_PATTERN = re.compile(r"[a-f0-9]{64}")


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


def validate_local_intake(
    projection: LocalIntakeProjection,
    *,
    observed_at: str,
    maximum_cost_limit_minor: int,
) -> None:
    """Fail closed on identity, consent, retention, content, or cost drift."""

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
    if projection.content_rating != "non_explicit":
        raise LocalIntakeViolation("local intake may enter this runtime only with non_explicit content")
    if isinstance(projection.cost_limit_minor, bool) or not isinstance(projection.cost_limit_minor, int) or projection.cost_limit_minor < 0:
        raise LocalIntakeViolation("cost_limit_minor must be a non-negative integer")
    if isinstance(maximum_cost_limit_minor, bool) or not isinstance(maximum_cost_limit_minor, int) or maximum_cost_limit_minor < 0:
        raise LocalIntakeViolation("maximum_cost_limit_minor must be a non-negative integer")
    if projection.cost_limit_minor > maximum_cost_limit_minor:
        raise LocalIntakeViolation("local intake cost limit exceeds the approved local ceiling")
    # A true confirmation is merely an explicit data point. It is never a
    # provider invocation authorization in this offline/GitHub runtime.
    if not isinstance(projection.provider_confirmation, bool):
        raise LocalIntakeViolation("provider_confirmation must be boolean")


def local_intake_gate_report(
    projection: LocalIntakeProjection,
    *,
    observed_at: str,
    maximum_cost_limit_minor: int,
) -> dict[str, Any]:
    """Return a clear boundary report after deterministic validation only."""

    validate_local_intake(
        projection,
        observed_at=observed_at,
        maximum_cost_limit_minor=maximum_cost_limit_minor,
    )
    return {
        "schema": "CreativeLocalIntakeGateReport/v1",
        "status": "local_intake_projection_valid",
        "projection": projection.to_dict(),
        "external_provider_authorized": False,
        "customer_vault_accessed": False,
        "canonical_knowledge_write": False,
        "note": "Validation of an opaque projection only; no customer material is read or stored by this module.",
    }
