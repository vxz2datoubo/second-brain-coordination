"""Offline, private-adaptation interactive-scene command line tool.

It is deliberately a bounded state machine: free text maps to a legal action or
asks for clarification.  It never calls a model, reads credentials, or produces
media.  The fixture is synthetic and uses adult characters only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creative_runtime.contracts import PlayerAction, canonical_json
from creative_runtime.ledger import CreativeLedger, LedgerViolation
from creative_runtime.knowledge import KnowledgeBridgeViolation, KnowledgeReviewBridge
from creative_runtime.saves import SaveSlotViolation, SaveStore, migrate_session
from creative_runtime.scene_graph import SceneGraph, SceneGraphViolation, synthetic_three_scene_manifest


DEFAULT_WORKSPACE = Path(".creative-runtime")
UNSAFE_TERMS = {"sex", "sexual", "nude", "blood", "gore", "torture"}
DEFAULT_SLOT = "default"


def session_path(workspace: Path) -> Path:
    """Return the versioned default slot path used by all new sessions."""

    return workspace / "saves" / f"{DEFAULT_SLOT}.json"


def _legacy_session_path(workspace: Path) -> Path:
    return workspace / "session.json"


def _graph() -> SceneGraph:
    return SceneGraph(synthetic_three_scene_manifest())


def _store(workspace: Path) -> SaveStore:
    return SaveStore(workspace / "saves")


def _write_session(workspace: Path, ledger: CreativeLedger, slot: str = DEFAULT_SLOT) -> Path:
    return _store(workspace).save(slot, ledger, _graph().manifest_hash)


def _load_session(workspace: Path, slot: str = DEFAULT_SLOT) -> CreativeLedger:
    graph = _graph()
    try:
        ledger = _store(workspace).load(slot, graph.manifest_hash).ledger
        graph.beat_for(ledger.replay())
        return ledger
    except SaveSlotViolation as error:
        legacy_path = _legacy_session_path(workspace)
        if slot != DEFAULT_SLOT or not legacy_path.is_file():
            raise LedgerViolation("No compatible session exists; run init first") from error
        try:
            legacy_record = json.loads(legacy_path.read_text(encoding="utf-8"))
            migrated, _ = migrate_session(legacy_record, graph.manifest_hash)
            ledger = CreativeLedger.from_records(migrated["events"])
            graph.beat_for(ledger.replay())
        except (json.JSONDecodeError, KeyError, SaveSlotViolation, SceneGraphViolation, TypeError) as legacy_error:
            raise LedgerViolation("Legacy session is corrupt or incompatible") from legacy_error
        _write_session(workspace, ledger)
        return ledger


def _knowledge_path(workspace: Path) -> Path:
    return workspace / "knowledge-review.json"


def _load_knowledge(workspace: Path) -> KnowledgeReviewBridge:
    path = _knowledge_path(workspace)
    if not path.is_file():
        return KnowledgeReviewBridge()
    return KnowledgeReviewBridge.from_records(json.loads(path.read_text(encoding="utf-8")).get("candidates", []))


def _write_knowledge(workspace: Path, bridge: KnowledgeReviewBridge) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    _knowledge_path(workspace).write_text(canonical_json({"schema": "CreativeKnowledgeReview/v1", "candidates": bridge.to_records()}) + "\n", encoding="utf-8")


def _timeline(ledger: CreativeLedger) -> list[dict[str, Any]]:
    state = None
    timeline: list[dict[str, Any]] = []
    for event in ledger.events:
        if event.event_type == "story_initialized":
            state = event.payload["state"]
        elif event.event_type == "player_action":
            state = ledger.replay().to_dict() if event.sequence == len(ledger.events) - 1 else state
        timeline.append({"turn": event.sequence, "event_id": event.event_id, "event_type": event.event_type, "state": state})
    return timeline


def transcript(ledger: CreativeLedger) -> list[dict[str, Any]]:
    """Export deterministic, plain-text-friendly event records without hidden state."""

    graph = _graph()
    records: list[dict[str, Any]] = []
    state = graph.initial_state()
    records.append({"turn": 0, "scene_id": state.scene_id, "beat_id": state.beat_id, "text": graph.beat_for(state).text})
    for turn, event in enumerate(ledger.events[1:], start=1):
        action_id = str(event.payload.get("action", {}).get("action_id", ""))
        state, action = graph.apply(state, action_id)
        records.append({"turn": turn, "action_id": action_id, "label": action.label, "scene_id": state.scene_id, "beat_id": state.beat_id, "text": graph.beat_for(state).text})
    return records


def _view(ledger: CreativeLedger) -> dict[str, Any]:
    graph = _graph()
    state = ledger.replay()
    beat = graph.beat_for(state)
    options = [
        {"id": action.action_id, "label": action.label, "transition_id": action.transition_id}
        for action in beat.actions
    ]
    return {
        "status": "ready",
        "manifest_hash": graph.manifest_hash,
        "state": state.to_dict(),
        "recap": beat.recap,
        "text": beat.text,
        "options": options,
        "logical_turn": len(ledger.events) - 1,
        "timeline": _timeline(ledger),
    }


def initialize(workspace: Path) -> dict[str, Any]:
    if session_path(workspace).exists():
        return {"status": "already_initialized", "session": str(session_path(workspace))}
    ledger = CreativeLedger()
    ledger.append(
        "story_initialized",
        {"state": _graph().initial_state().to_dict()},
        "2030-01-01T00:00:00Z",
    )
    _write_session(workspace, ledger)
    return {**_view(ledger), "status": "initialized", "session": str(session_path(workspace))}


def choose(workspace: Path, action_id: str, source_text: str | None = None) -> dict[str, Any]:
    ledger = _load_session(workspace)
    state = ledger.replay()
    graph = _graph()
    try:
        next_state, option = graph.apply(state, action_id)
    except SceneGraphViolation:
        return {
            "status": "clarification_required",
            "message": "That action is not legal at this beat; choose one listed option.",
            "legal_options": sorted(action.action_id for action in graph.beat_for(state).actions),
        }
    ledger.append(
        "player_action",
        {
            "action": PlayerAction(action_id, "choice", source_text or option.label).to_dict(),
            "transition_id": option.transition_id,
            "resulting_patch": {**option.patch, "scene_id": next_state.scene_id, "beat_id": next_state.beat_id},
        },
        f"2030-01-01T00:{len(ledger.events):02d}:00Z",
    )
    _write_session(workspace, ledger)
    return {**_view(ledger), "status": "chosen", "action_id": action_id}


def parse_free_text(text: str, legal_actions: set[str]) -> tuple[str | None, float]:
    normalized = text.lower().strip()
    tokens = set(normalized.replace(".", " ").replace(",", " ").split())
    if tokens & UNSAFE_TERMS:
        return None, 0.0
    signals = {
        "listen": {"listen", "hear", "quiet"},
        "knock": {"knock", "announce", "tap"},
        "defer": {"defer", "daylight", "wait"},
        "record": {"record", "mark", "note"},
        "promise": {"promise", "listen", "safe"},
        "retreat": {"retreat", "withdraw", "leave"},
        "depart": {"depart", "leave", "daylight"},
    }
    matches = [action for action in legal_actions if tokens & signals.get(action, set())]
    if len(matches) != 1:
        return None, 0.0
    return matches[0], 0.9


def say(workspace: Path, text: str) -> dict[str, Any]:
    ledger = _load_session(workspace)
    state = ledger.replay()
    legal = {action.action_id for action in _graph().beat_for(state).actions}
    action, confidence = parse_free_text(text, legal)
    if action is None or confidence < 0.8:
        return {
            "status": "clarification_required",
            "message": "Use a clear, non-explicit intent or select an available option.",
            "legal_options": sorted(legal),
        }
    return choose(workspace, action, source_text=text)


def run(argv: list[str]) -> dict[str, Any]:
    parser = argparse.ArgumentParser(prog="creativectl")
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init")
    subparsers.add_parser("play")
    choose_parser = subparsers.add_parser("choose")
    choose_parser.add_argument("action_id")
    say_parser = subparsers.add_parser("say")
    say_parser.add_argument("text")
    subparsers.add_parser("resume")
    subparsers.add_parser("replay")
    slot_parser = subparsers.add_parser("slot")
    slot_subparsers = slot_parser.add_subparsers(dest="slot_command", required=True)
    slot_save = slot_subparsers.add_parser("save")
    slot_save.add_argument("name")
    slot_load = slot_subparsers.add_parser("load")
    slot_load.add_argument("name")
    slot_delete = slot_subparsers.add_parser("delete")
    slot_delete.add_argument("name")
    slot_subparsers.add_parser("list")
    subparsers.add_parser("transcript")
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("left_slot")
    compare_parser.add_argument("right_slot")
    knowledge_parser = subparsers.add_parser("knowledge")
    knowledge_subparsers = knowledge_parser.add_subparsers(dest="knowledge_command", required=True)
    knowledge_search = knowledge_subparsers.add_parser("search")
    knowledge_search.add_argument("query")
    knowledge_correct = knowledge_subparsers.add_parser("correct")
    knowledge_correct.add_argument("assertion")
    knowledge_correct.add_argument("--source-event-id", action="append", default=[])
    knowledge_correct.add_argument("--source-artifact-id", action="append", default=[])
    knowledge_review = knowledge_subparsers.add_parser("review")
    knowledge_review.add_argument("candidate_id")
    knowledge_review.add_argument("--reviewer", required=True)
    knowledge_review.add_argument("--approve", action="store_true")
    knowledge_review.add_argument("--note", default="")
    args = parser.parse_args(argv)
    if args.command == "init":
        return initialize(args.workspace)
    if args.command in {"play", "resume"}:
        return _view(_load_session(args.workspace))
    if args.command == "choose":
        return choose(args.workspace, args.action_id)
    if args.command == "say":
        return say(args.workspace, args.text)
    if args.command == "replay":
        ledger = _load_session(args.workspace)
        return {**_view(ledger), "status": "replayed", "event_count": len(ledger.events)}
    if args.command == "slot":
        store = _store(args.workspace)
        if args.slot_command == "list":
            return {"status": "slots", "slots": store.list_slots()}
        if args.slot_command == "save":
            path = _write_session(args.workspace, _load_session(args.workspace), args.name)
            return {"status": "saved", "slot": args.name, "session": str(path)}
        if args.slot_command == "load":
            return {**_view(_load_session(args.workspace, args.name)), "status": "loaded", "slot": args.name}
        if args.slot_command == "delete":
            return {"status": "deleted" if store.delete(args.name) else "not_found", "slot": args.name}
    if args.command == "transcript":
        ledger = _load_session(args.workspace)
        return {"status": "transcript", "manifest_hash": _graph().manifest_hash, "turns": transcript(ledger)}
    if args.command == "compare":
        left = _load_session(args.workspace, args.left_slot)
        right = _load_session(args.workspace, args.right_slot)
        left_state, right_state = left.replay(), right.replay()
        return {
            "status": "compared",
            "left_slot": args.left_slot,
            "right_slot": args.right_slot,
            "same_event_digest": canonical_json(left.to_records()) == canonical_json(right.to_records()),
            "left_state": left_state.to_dict(),
            "right_state": right_state.to_dict(),
            "same_final_state": left_state == right_state,
        }
    if args.command == "knowledge":
        bridge = _load_knowledge(args.workspace)
        if args.knowledge_command == "search":
            return {"status": "searched", "candidates": [item.to_dict() for item in bridge.search(args.query)]}
        if args.knowledge_command == "correct":
            candidate = bridge.correct(args.assertion, source_event_ids=args.source_event_id, source_artifact_ids=args.source_artifact_id)
            _write_knowledge(args.workspace, bridge)
            return {"status": "pending_human_review", "candidate": candidate.to_dict()}
        if args.knowledge_command == "review":
            candidate = bridge.review(args.candidate_id, args.reviewer, args.approve, args.note)
            _write_knowledge(args.workspace, bridge)
            return {"status": "reviewed", "candidate": candidate.to_dict(), "canonical_write": False}
    raise AssertionError("unreachable")


def main() -> int:
    try:
        print(json.dumps(run(sys.argv[1:]), ensure_ascii=False, sort_keys=True, indent=2))
    except (LedgerViolation, SaveSlotViolation, SceneGraphViolation, KnowledgeBridgeViolation, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
