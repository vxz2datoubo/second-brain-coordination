"""Validated director-entry surface for interactive-session continuity."""

from __future__ import annotations

from dataclasses import dataclass

from .director import DirectorCompilation, compile_director
from .saves import SavedSession
from .timeline import TimelineEntry, build_prefix_timeline


@dataclass(frozen=True)
class DirectorSequence:
    compilation: DirectorCompilation
    timeline: tuple[TimelineEntry, ...]


def compile_director_sequence(session: SavedSession) -> DirectorSequence:
    """Validate storage authority before compiling any cinematic representation."""

    state = session.state()
    timeline = build_prefix_timeline(session)
    return DirectorSequence(compile_director(state), timeline)
