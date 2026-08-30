"""Minimal review-packet reader; it never accepts unauthenticated history."""
from __future__ import annotations
from .saves import SavedSession

def review_packet(session: SavedSession) -> dict[str, object]:
    state = session.state()
    return {"state": state.to_dict(), "event_count": len(session.ledger.events)}
