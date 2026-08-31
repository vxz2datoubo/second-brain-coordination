"""Mechanical shape checks for the canonical independent-review ticket."""

from __future__ import annotations

from typing import Mapping


class ReviewTicketViolation(ValueError):
    pass


REQUIRED_FIELDS = (
    "effective_spec_snapshot_id",
    "effective_spec_snapshot_ref",
    "canonical_base",
    "exact_head",
    "engineering_handoff_ref",
)
FORBIDDEN_ALIASES = ("prewrite_snapshot_id", "prewrite_snapshot_ref", "snapshot_canonical_governance_base")


def validate_review_request(ticket: Mapping[str, object]) -> None:
    missing = [field for field in REQUIRED_FIELDS if not isinstance(ticket.get(field), str) or not str(ticket[field]).strip()]
    if missing:
        raise ReviewTicketViolation("missing canonical review-ticket fields: " + ", ".join(missing))
    aliases = [field for field in FORBIDDEN_ALIASES if field in ticket]
    if aliases:
        raise ReviewTicketViolation("review-ticket aliases are forbidden: " + ", ".join(aliases))
    handoff = str(ticket["engineering_handoff_ref"])
    if "PENDING" in handoff.upper() or not handoff.startswith("issuecomment-"):
        raise ReviewTicketViolation("engineering_handoff_ref must be a real issue comment reference")
