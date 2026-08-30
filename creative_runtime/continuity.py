from __future__ import annotations
from .saves import SavedSession
def director_sequence(session: SavedSession) -> tuple[str, str]:
    state = session.state(); return state.scene_id, state.beat_id
