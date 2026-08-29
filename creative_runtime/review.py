"""Reproducible offline review packets bound to exact ledger-prefix truth."""

from __future__ import annotations

import hashlib
from typing import Any

from .continuity import DirectorSequence, compile_director_sequence
from .contracts import canonical_json
from .ledger import CreativeLedger
from .scene_graph import SceneGraph
from .timeline import build_prefix_timeline


def stable_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def transcript_for_review(ledger: CreativeLedger, graph: SceneGraph) -> list[dict[str, Any]]:
    """Render transcript rows from the same validated prefix timeline used by S08."""

    rows: list[dict[str, Any]] = []
    for entry in build_prefix_timeline(ledger, graph):
        beat = graph.beat_for(entry.state)
        rows.append(
            {
                "turn": entry.turn,
                "event_id": entry.event_id,
                "event_type": entry.event_type,
                "action_id": entry.action_id,
                "transition_id": entry.transition_id,
                "scene_id": entry.state.scene_id,
                "beat_id": entry.state.beat_id,
                "text": beat.text,
                "state": entry.state.to_dict(),
            }
        )
    return rows


def build_review_packet(
    ledger: CreativeLedger,
    graph: SceneGraph,
    duration_budget_seconds: int = 90,
) -> dict[str, Any]:
    """Bind replay, continuity, and final-state evidence without generating media."""

    ledger.verify_chain()
    timeline = build_prefix_timeline(ledger, graph)
    sequence: DirectorSequence = compile_director_sequence(
        ledger,
        graph,
        duration_budget_seconds=duration_budget_seconds,
    )
    transcript = transcript_for_review(ledger, graph)
    final_state = timeline[-1].state.to_dict()
    packet = {
        "schema": "OfflineInteractiveFilmReviewPacket/v1",
        "manifest_hash": graph.manifest_hash,
        "session_schema": "CreativeSession/v2",
        "event_digest": stable_digest(ledger.to_records()),
        "event_count": len(ledger.events),
        "transcript": transcript,
        "timeline": [entry.to_dict() for entry in timeline],
        "director": sequence.to_dict(),
        "final_state": final_state,
        "final_state_digest": stable_digest(final_state),
        "generation_called": False,
        "canonical_knowledge_written": False,
    }
    return {**packet, "review_digest": stable_digest(packet)}
