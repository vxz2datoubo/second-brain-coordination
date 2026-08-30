"""Portable, verified interactive-film experience manifests.

This module deliberately produces a static projection from an append-only
ledger.  A browser, desktop shell, or later local customer adapter may render
the result, but cannot use it to invent a transition, disclose a hidden fact,
or bypass the director quality gate.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .continuity import TimelineViolation, graph_for_ledger, replay_timeline, timeline_hash
from .contracts import canonical_json
from .ledger import CreativeLedger
from .presentation import PresentationViolation, build_interactive_frame
from .session import DEFAULT_SLOT, validate_slot


class ExperienceViolation(ValueError):
    """Raised when a portable experience cannot be reproduced exactly."""


@dataclass(frozen=True)
class VerifiedExperienceManifest:
    """A render-only sequence of verified frames for one immutable ledger."""

    experience_id: str
    slot_id: str
    graph_revision: str
    timeline_hash: str
    source_event_ids: tuple[str, ...]
    frames: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "VerifiedInteractiveExperience/v1",
            "status": "experience_manifest_verified",
            "experience_id": self.experience_id,
            "slot_id": self.slot_id,
            "graph_revision": self.graph_revision,
            "timeline_hash": self.timeline_hash,
            "source_event_ids": list(self.source_event_ids),
            "frames": [dict(frame) for frame in self.frames],
            "provenance": {
                "class": "private_adaptation",
                "synthetic_only": True,
                "public_release_authorized": False,
                "customer_data_present": False,
                "external_provider_called": False,
            },
        }


def build_verified_experience(ledger: CreativeLedger, *, slot: str = DEFAULT_SLOT) -> VerifiedExperienceManifest:
    """Build one deterministic frame per verified ledger prefix.

    Each prefix is reconstructed as an independent ``CreativeLedger``.  This
    is intentionally more expensive than mutating a single display state: it
    prevents a final-state field from being silently backfilled into an earlier
    frame.
    """

    normalized_slot = validate_slot(slot)
    try:
        graph = graph_for_ledger(ledger)
        timeline = replay_timeline(ledger, graph)
        frames = tuple(
            build_interactive_frame(CreativeLedger(ledger.events[: index + 1]), slot=normalized_slot).to_dict()
            for index in range(len(timeline))
        )
    except (PresentationViolation, TimelineViolation, TypeError, ValueError) as error:
        raise ExperienceViolation("Verified experience requires a complete verified story timeline") from error
    if not frames:
        raise ExperienceViolation("Verified experience requires at least one frame")
    if frames[-1]["timeline_hash"] != timeline_hash(timeline):
        raise ExperienceViolation("Final experience frame is not bound to the full timeline")
    if len({str(frame["frame_id"]) for frame in frames}) != len(frames):
        raise ExperienceViolation("Experience contains duplicate verified frame identities")
    source_event_ids = tuple(event.event_id for event in ledger.events)
    material = {
        "schema": "VerifiedInteractiveExperience/v1",
        "slot_id": normalized_slot,
        "graph_revision": graph.revision,
        "timeline_hash": timeline_hash(timeline),
        "source_event_ids": list(source_event_ids),
        "frames": list(frames),
    }
    experience_id = "experience_" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:20]
    return VerifiedExperienceManifest(
        experience_id=experience_id,
        slot_id=normalized_slot,
        graph_revision=graph.revision,
        timeline_hash=timeline_hash(timeline),
        source_event_ids=source_event_ids,
        frames=frames,
    )


def verify_verified_experience(ledger: CreativeLedger, manifest: Mapping[str, Any], *, slot: str = DEFAULT_SLOT) -> VerifiedExperienceManifest:
    """Reject any byte-level or semantic change to a claimed experience."""

    expected = build_verified_experience(ledger, slot=slot)
    try:
        supplied = dict(manifest)
    except (TypeError, ValueError) as error:
        raise ExperienceViolation("Experience manifest must be a JSON object") from error
    if canonical_json(supplied) != canonical_json(expected.to_dict()):
        raise ExperienceViolation("Experience manifest does not exactly match the verified ledger")
    return expected
