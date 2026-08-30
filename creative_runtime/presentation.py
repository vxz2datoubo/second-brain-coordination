"""Verified interactive-film presentation frames for future clients.

The frame is a read-only projection of an already validated story ledger. It
does not decide transitions, infer hidden facts, generate media, or contact a
provider. Web, desktop, and future local clients can render this same frame
without reimplementing narrative authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .continuity import TimelineViolation, graph_for_ledger, replay_timeline, timeline_hash
from .contracts import canonical_json
from .director import compile_verified_director
from .ledger import CreativeLedger
from .session import DEFAULT_SLOT, validate_slot


class PresentationViolation(ValueError):
    """Raised when a client frame would lack verified story/director evidence."""


@dataclass(frozen=True)
class InteractiveFrame:
    frame_id: str
    slot_id: str
    graph_revision: str
    timeline_hash: str
    state: Mapping[str, Any]
    story_text: str
    legal_choices: tuple[Mapping[str, str], ...]
    recent_consequence: Mapping[str, Any]
    director: Mapping[str, Any]
    accessibility: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "InteractiveFrame/v1",
            "status": "interactive_frame_verified",
            "frame_id": self.frame_id,
            "slot_id": self.slot_id,
            "graph_revision": self.graph_revision,
            "timeline_hash": self.timeline_hash,
            "state": dict(self.state),
            "story_text": self.story_text,
            "legal_choices": [dict(choice) for choice in self.legal_choices],
            "recent_consequence": dict(self.recent_consequence),
            "director": dict(self.director),
            "accessibility": dict(self.accessibility),
        }


def build_interactive_frame(ledger: CreativeLedger, *, slot: str = DEFAULT_SLOT) -> InteractiveFrame:
    """Create a render-ready frame only after complete prefix verification."""

    normalized_slot = validate_slot(slot)
    try:
        graph = graph_for_ledger(ledger)
        timeline = replay_timeline(ledger, graph)
        compiled = compile_verified_director(ledger, graph=graph)
    except (TimelineViolation, KeyError, TypeError, ValueError) as error:
        raise PresentationViolation("Interactive frame requires a verified story timeline") from error
    if not compiled.compilation.quality_report.can_generate:
        raise PresentationViolation("Interactive frame is blocked by the director quality gate")
    state = compiled.verified_input.state
    beat = graph.beat_for(state)
    choices = tuple(
        {"action_id": transition.action_id, "label": transition.label}
        for transition in graph.legal_actions(state)
    )
    recent = timeline[-1]
    director = {
        "brief_id": compiled.compilation.brief.brief_id,
        "content_rating": compiled.compilation.brief.content_rating,
        "source_timeline_hash": compiled.verified_input.timeline_hash,
        "activated_skill_ids": list(compiled.compilation.brief.activated_skill_ids),
        "shots": [shot.to_dict() for shot in compiled.compilation.shots],
        "quality_metrics": compiled.compilation.quality_report.metrics.to_dict(),
    }
    accessibility = {
        "caption_text": beat.text,
        "sound_cue": compiled.compilation.shots[0].sound,
        "input_mode": "choice_or_safe_intent",
        "content_rating": "non_explicit",
        "known_facts_only": list(state.known_facts),
    }
    material = {
        "schema": "InteractiveFrame/v1",
        "slot_id": normalized_slot,
        "graph_revision": graph.revision,
        "timeline_hash": timeline_hash(timeline),
        "state": state.to_dict(),
        "story_text": beat.text,
        "legal_choices": list(choices),
        "recent_consequence": recent.consequence,
        "director": director,
        "accessibility": accessibility,
    }
    frame_id = "frame_" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:20]
    return InteractiveFrame(
        frame_id=frame_id,
        slot_id=normalized_slot,
        graph_revision=graph.revision,
        timeline_hash=timeline_hash(timeline),
        state=state.to_dict(),
        story_text=beat.text,
        legal_choices=choices,
        recent_consequence=recent.consequence,
        director=director,
        accessibility=accessibility,
    )
