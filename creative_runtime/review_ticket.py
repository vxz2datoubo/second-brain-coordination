"""Machine-readable binding shape used by the independent review request."""
from __future__ import annotations
from typing import Mapping

REQUIRED_FIELDS = {"effective_spec_snapshot_id", "effective_spec_snapshot_ref", "canonical_base", "exact_head", "engineering_handoff_ref"}

def validate_review_ticket(ticket: Mapping[str, object]) -> None:
    missing = REQUIRED_FIELDS - set(ticket)
    if missing or any(not isinstance(ticket[name], str) or not ticket[name] for name in REQUIRED_FIELDS):
        raise ValueError("Review ticket lacks canonical binding fields")
