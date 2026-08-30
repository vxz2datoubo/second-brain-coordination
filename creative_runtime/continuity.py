"""Validated director-sequence entry point."""

from __future__ import annotations

from .director import DirectorCompilation, compile_director
from .saves import SavedSession


def compile_director_sequence(session: SavedSession) -> DirectorCompilation:
    return compile_director(session.state())
