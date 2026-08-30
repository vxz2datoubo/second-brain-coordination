"""Validated prefix timeline.  No consumer gets a state before session validation."""
from __future__ import annotations
from .saves import SavedSession

def build_timeline(session: SavedSession) -> list[dict[str, object]]:
    session.validate()
    result: list[dict[str, object]] = []
    records = session.ledger.to_records()
    required_prefix = len(session._expected_migrated_ledger().events) if session.migration is not None else 1
    for end in range(required_prefix, len(records) + 1):
        prefix = SavedSession(type(session.ledger).from_records(records[:end]), session.migration)
        result.append(prefix.state().to_dict())
    return result
