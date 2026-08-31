"""A non-authoritative review packet gated by validated narrative state."""

from __future__ import annotations

from typing import Any

from .saves import SavedSession


def build_review_packet(session: SavedSession) -> dict[str, Any]:
    state = session.state()
    return {"schema": "CreativeReviewPacket/v1", "state": state.to_dict(), "event_count": len(session.ledger.events), "migration": session.migration_receipt is not None, "authority": "non_canonical_candidate_only"}
