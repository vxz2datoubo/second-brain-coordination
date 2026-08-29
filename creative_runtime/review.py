"""Reproducible, offline review packets for the interactive-film runtime."""

from __future__ import annotations

import hashlib
from typing import Any

from .continuity import DirectorSequence, compile_director_sequence
from .contracts import canonical_json
from .ledger import CreativeLedger
from .scene_graph import SceneGraph


def stable_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def transcript_for_review(ledger: CreativeLedger, graph: SceneGraph) -> list[dict[str, Any]]:
    """Build an exact replay transcript using only the manifest and ledger."""

    state = graph.initial_state()
    if ledger.events[0].payload.get("state") != state.to_dict():
        raise ValueError("Review packet requires the manifest's declared initial state")
    records = [{"turn": 0, "scene_id": state.scene_id, "beat_id": state.beat_id, "text": graph.beat_for(state).text}]
    for turn, event in enumerate(ledger.events[1:], start=1):
        action_id = str(event.payload.get("action", {}).get("action_id", ""))
        state, action = graph.apply(state, action_id)
        records.append({
            "turn": turn,
            "action_id": action_id,
            "transition_id": action.transition_id,
            "scene_id": state.scene_id,
            "beat_id": state.beat_id,
            "text": graph.beat_for(state).text,
        })
    return records


def build_review_packet(
    ledger: CreativeLedger,
    graph: SceneGraph,
    duration_budget_seconds: int = 90,
) -> dict[str, Any]:
    """Bind replay evidence and continuity diagnostics without generating media."""

    ledger.verify_chain()
    sequence: DirectorSequence = compile_director_sequence(
        ledger, graph, duration_budget_seconds=duration_budget_seconds,
    )
    transcript = transcript_for_review(ledger, graph)
    packet = {
        "schema": "OfflineInteractiveFilmReviewPacket/v1",
        "manifest_hash": graph.manifest_hash,
        "session_schema": "CreativeSession/v2",
        "event_digest": stable_digest(ledger.to_records()),
        "event_count": len(ledger.events),
        "transcript": transcript,
        "director": sequence.to_dict(),
        "generation_called": False,
        "canonical_knowledge_written": False,
    }
    return {**packet, "review_digest": stable_digest(packet)}
