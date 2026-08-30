from __future__ import annotations
from .saves import SavedSession
def build_timeline(session: SavedSession) -> list[dict[str, object]]:
    return [session.state().to_dict()]
