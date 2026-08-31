from __future__ import annotations
from .saves import SavedSession
def review_packet(session: SavedSession) -> dict[str, object]:
    return {"state": session.state().to_dict(), "events": len(session.ledger.events)}
