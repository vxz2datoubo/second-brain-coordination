"""Inspectable review-packet projection; it has no merge or knowledge authority."""

from __future__ import annotations

from typing import Any

from .saves import SavedSession
from .timeline import build_prefix_timeline


def build_review_packet(session: SavedSession) -> dict[str, Any]:
    """Return only state and evidence after the same fail-closed validation."""

    state = session.state()
    return {
        "schema": "CreativeReviewPacket/v1",
        "state": state.to_dict(),
        "timeline": [entry.to_dict() for entry in build_prefix_timeline(session)],
        "authoritative": False,
        "merge_authorized": False,
    }
