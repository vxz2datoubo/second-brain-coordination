"""Offline interactive creative CLI with fail-closed migration and timeline truth."""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creative_runtime.continuity import compile_director_sequence
from creative_runtime.contracts import PlayerAction, canonical_json
from creative_runtime.ledger import CreativeLedger, LedgerViolation
from creative_runtime.knowledge import KnowledgeBridgeViolation, KnowledgeReviewBridge
from creative_runtime.review import build_review_packet, stable_digest
from creative_runtime.saves import SaveSlotViolation, SaveStore, migrate_session
from creative_runtime.scene_graph import SceneGraph, SceneGraphViolation, synthetic_three_scene_manifest
from creative_runtime.timeline import TimelineViolation, build_prefix_timeline


DEFAULT_WORKSPACE = Path(".creative-runtime")
DEFAULT_SLOT = "default"
UNSAFE_TERMS = {"sex", "sexual", "nude", "blood", "gore", "torture"}


def session_path(workspace: Path) -> Path:
    return workspace / "saves" / f"{DEFAULT_SLOT}.json"


def legacy_session_path(workspace: Path) -> Path:
    return workspace / "session.json"


def _graph() -> SceneGraph:
    return SceneGraph(synthetic_three_scene_manifest())


def _store(workspace: Path) -> SaveStore:
    return SaveStore(workspace / "saves")


def _write_session(workspace: Path, ledger: CreativeLedger, slot: str = DEFAULT_SLOT) -> Path:
    return _store(workspace).save(slot, ledger, _graph().manifest_hash)


def _migrate_legacy_default(workspace: Path) -> tuple[CreativeLedger, tuple[str, ...]]:
    legacy_path = legacy_session_path(workspace)
    if not legacy_path.is_file():
        raise LedgerViolation("No legacy session exists")
    original_bytes = legacy_path.read_bytes()
    default_existed_before = session_path(workspace).exists()
    try:
        legacy_record = json.loads(original_bytes.decode("utf-8"))
        if not isinstance(legacy_record, dict):
            raise SaveSlotViolation("Legacy session payload must be an object")
        graph = _graph()
        migrated, migrations = migrate_session(legacy_record, graph.manifest_hash, graph)
        ledger = CreativeLedger.from_records(migrated["events"])
        graph.beat_for(ledger.replay())
        build_prefix_timeline(ledger, graph)
        _store(workspace).save_record(DEFAULT_SLOT, migrated, graph.manifest_hash)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        KeyError,
        LedgerViolation,
        SaveSlotViolation,
        SceneGraphViolation,
        TimelineViolation,
        TypeError,
        ValueError,
    ) as error:
        if not default_existed_before and session_path(workspace).exists():
            session_path(workspace).unlink(missing_ok=True)
        if legacy_path.read_bytes() != original_bytes:
            raise LedgerViolation("Legacy migration failed and source integrity changed unexpectedly") from error
        raise LedgerViolation(f"Legacy session is corrupt or incompatible; original preserved: {error}") from error
    if legacy_path.read_bytes() != original_bytes:
        if not default_existed_before:
            session_path(workspace).unlink(missing_ok=True)
        raise LedgerViolation("Legacy migration changed the source session; migrated copy removed")
    return ledger, migrations


def _load_session(workspace: Path, slot: str = DEFAULT_SLOT) -> CreativeLedger:
    graph = _graph()
    if slot == DEFAULT_SLOT and not session_path(workspace).exists() and legacy_session_path(workspace).is_file():
        ledger, _ = _migrate_legacy_default(workspace)
        return ledger
    try:
        loaded = _store(workspace).load(slot, graph.manifest_hash, graph)
        graph.beat_for(loaded.ledger.replay())
        build_prefix_timeline(loaded.ledger, graph)
        return loaded.ledger
    except (SaveSlotViolation, SceneGraphViolation, TimelineViolation) as error:
        raise LedgerViolation("No compatible session exists; run init first") from error


def _restore_slot(workspace: Path, slot: str) -> CreativeLedger:
    """Validate a sibling slot completely before atomically replacing default."""

    ledger = _load_session(workspace, slot)
    graph = _graph()
    build_prefix_timeline(ledger, graph)
    _write_session(workspace, ledger, DEFAULT_SLOT)
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
    _knowledge_path(workspace).write_text(
        canonical_json({"schema": "CreativeKnowledgeReview/v1", "candidates": bridge.to_records()}) + "\n",
        encoding="utf-8",
    )


def _timeline(ledger: CreativeLedger) -> list[dict[str, Any]]:
    return [entry.to_dict() for entry in build_prefix_timeline(ledger, _graph())]


def transcript(ledger: CreativeLedger) -> list[dict[str, Any]]:
    """Export deterministic turn text and the exact post-prefix state together."""

    graph = _graph()
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


def _event_summary(ledger: CreativeLedger) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for event in ledger.events:
        item: dict[str, Any] = {"turn": event.sequence, "event_type": event.event_type}
        if event.event_type == "player_action":
            action = event.payload.get("action", {})
            item["action_id"] = str(action.get("action_id", "")) if isinstance(action, dict) else ""
            item["transition_id"] = event.payload.get("transition_id")
        elif event.event_type == "state_patch":
            item["patch"] = event.payload.get("patch")
        summary.append(item)
    return summary


def _view(ledger: CreativeLedger) -> dict[str, Any]:
    graph = _graph()
    state = ledger.replay()
    beat = graph.beat_for(state)
    return {
        "status": "ready",
        "manifest_hash": graph.manifest_hash,
        "state": state.to_dict(),
        "recap": beat.recap,
        "text": beat.text,
        "options": [
            {"id": action.action_id, "label": action.label, "transition_id": action.transition_id}
            for action in beat.actions
        ],
        "logical_turn": len(ledger.events) - 1,
        "timeline": _timeline(ledger),
    }


def initialize(workspace: Path) -> dict[str, Any]:
    if session_path(workspace).exists():
        return {"status": "already_initialized", "session": str(session_path(workspace))}
    if legacy_session_path(workspace).is_file():
        ledger, migrations = _migrate_legacy_default(workspace)
        return {
            **_view(ledger),
            "status": "migrated_legacy",
            "session": str(session_path(workspace)),
            "legacy_session": str(legacy_session_path(workspace)),
            "migrations": list(migrations),
        }
    ledger = CreativeLedger()
    ledger.append("story_initialized", {"state": _graph().initial_state().to_dict()}, "2030-01-01T00:00:00Z")
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
            "resulting_patch": {**dict(option.patch), "scene_id": next_state.scene_id, "beat_id": next_state.beat_id},
        },
        f"2030-01-01T00:{len(ledger.events):02d}:00Z",
    )
    build_prefix_timeline(ledger, graph)
    _write_session(workspace, ledger)
    return {**_view(ledger), "status": "chosen", "action_id": action_id}


def parse_free_text(text: str, legal_actions: set[str]) -> tuple[str | None, float]:
    normalized = text.lower().strip()
    tokens = set(normalized.replace(".", " ").replace(",", " ").split())
    if tokens & UNSAFE_TERMS:
        return None, 0.0
    signals = {
        "listen": {"listen", "hear", "quiet", "door"},
        "knock": {"knock", "announce", "approach", "enter", "walk"},
        "defer": {"defer", "daylight", "wait", "back"},
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


def _plain_timeline(ledger: CreativeLedger) -> str:
    lines = ["Exact consequence timeline:"]
    for entry in build_prefix_timeline(ledger, _graph()):
        state = entry.state
        action = f" action={entry.action_id}" if entry.action_id else ""
        lines.append(
            f"  turn={entry.turn} {state.scene_id}/{state.beat_id} risk={state.risk_level}"
            f" relationships={dict(state.relationships)} facts={list(state.known_facts)} flags={dict(state.flags)}{action}"
        )
    return "\n".join(lines)


def terminal_loop(
    workspace: Path,
    input_stream: io.TextIOBase | None = None,
    output_stream: io.TextIOBase | None = None,
) -> dict[str, Any]:
    """Offline terminal loop with deterministic turn timing and exact prefix history."""

    source = input_stream or sys.stdin
    output = output_stream or sys.stdout
    try:
        if not session_path(workspace).is_file():
            if legacy_session_path(workspace).is_file():
                _migrate_legacy_default(workspace)
            else:
                initialize(workspace)
    except LedgerViolation as error:
        output.write(f"Legacy session incompatible; original preserved. {error}\n")
        return {
            "status": "legacy_incompatible",
            "message": str(error),
            "legacy_session_preserved": legacy_session_path(workspace).is_file(),
            "default_session_created": session_path(workspace).is_file(),
        }

    output.write("Offline interactive film. Type help for commands; type quit to exit.\n")
    while True:
        ledger = _load_session(workspace)
        view = _view(ledger)
        options = ", ".join(item["id"] for item in view["options"]) or "(no further choices)"
        output.write(
            f"{view['state']['scene_id']} / {view['state']['beat_id']} | risk={view['state']['risk_level']}\n"
            f"{view['text']}\nChoices: {options}\n> "
        )
        output.flush()
        line = source.readline()
        if line == "":
            return {"status": "ended_at_eof", "logical_turn": view["logical_turn"]}
        command = line.strip()
        if command.casefold() in {"quit", "exit"}:
            return {"status": "quit", "logical_turn": view["logical_turn"]}
        if command.casefold() == "help":
            output.write("Commands: <choice>, choose <choice>, say <clear intent>, timeline, transcript, quit.\n")
            continue
        if command.casefold() == "timeline":
            output.write(_plain_timeline(ledger) + "\n")
            continue
        if command.casefold() == "transcript":
            output.write(json.dumps(transcript(ledger), ensure_ascii=False, sort_keys=True) + "\n")
            continue
        verb, _, remainder = command.partition(" ")
        if verb.casefold() == "say" and remainder:
            result = say(workspace, remainder)
        elif verb.casefold() == "choose" and remainder:
            result = choose(workspace, remainder)
        else:
            result = choose(workspace, command)
        if result["status"] == "clarification_required":
            output.write(result["message"] + "\n")


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
    subparsers.add_parser("timeline")
    subparsers.add_parser("transcript")
    director_parser = subparsers.add_parser("director")
    director_parser.add_argument("--duration-budget", type=int, default=90)
    review_parser = subparsers.add_parser("review-packet")
    review_parser.add_argument("--duration-budget", type=int, default=90)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("left_slot")
    compare_parser.add_argument("right_slot")
    subparsers.add_parser("interactive")
    slot_parser = subparsers.add_parser("slot")
    slot_subparsers = slot_parser.add_subparsers(dest="slot_command", required=True)
    slot_subparsers.add_parser("list")
    slot_save = slot_subparsers.add_parser("save")
    slot_save.add_argument("name")
    slot_load = slot_subparsers.add_parser("load")
    slot_load.add_argument("name")
    slot_delete = slot_subparsers.add_parser("delete")
    slot_delete.add_argument("name")
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
    if args.command == "timeline":
        ledger = _load_session(args.workspace)
        return {"status": "timeline", "manifest_hash": _graph().manifest_hash, "entries": _timeline(ledger)}
    if args.command == "transcript":
        ledger = _load_session(args.workspace)
        return {"status": "transcript", "manifest_hash": _graph().manifest_hash, "turns": transcript(ledger)}
    if args.command == "director":
        sequence = compile_director_sequence(
            _load_session(args.workspace),
            _graph(),
            duration_budget_seconds=args.duration_budget,
        )
        return {"status": "director_packet", "generation_called": False, **sequence.to_dict()}
    if args.command == "review-packet":
        return {
            "status": "review_packet",
            **build_review_packet(_load_session(args.workspace), _graph(), args.duration_budget),
        }
    if args.command == "compare":
        left = _load_session(args.workspace, args.left_slot)
        right = _load_session(args.workspace, args.right_slot)
        left_records = left.to_records()
        right_records = right.to_records()
        left_state = left.replay()
        right_state = right.replay()
        left_digest = stable_digest(left_records)
        right_digest = stable_digest(right_records)
        return {
            "status": "compared",
            "left_slot": args.left_slot,
            "right_slot": args.right_slot,
            "left_event_digest": left_digest,
            "right_event_digest": right_digest,
            "same_event_digest": left_digest == right_digest,
            "left_event_summary": _event_summary(left),
            "right_event_summary": _event_summary(right),
            "left_state": left_state.to_dict(),
            "right_state": right_state.to_dict(),
            "same_final_state": left_state == right_state,
        }
    if args.command == "interactive":
        return {"status": "interactive_ready", "workspace": str(args.workspace), "offline": True}
    if args.command == "slot":
        store = _store(args.workspace)
        if args.slot_command == "list":
            return {"status": "slots", "slots": store.list_slots()}
        if args.slot_command == "save":
            path = _write_session(args.workspace, _load_session(args.workspace), args.name)
            return {"status": "saved", "slot": args.name, "session": str(path)}
        if args.slot_command == "load":
            ledger = _restore_slot(args.workspace, args.name)
            return {**_view(ledger), "status": "loaded", "slot": args.name, "restored_to_default": True}
        if args.slot_command == "delete":
            return {"status": "deleted" if store.delete(args.name) else "not_found", "slot": args.name}
    if args.command == "knowledge":
        bridge = _load_knowledge(args.workspace)
        if args.knowledge_command == "search":
            return {"status": "searched", "candidates": [item.to_dict() for item in bridge.search(args.query)]}
        if args.knowledge_command == "correct":
            candidate = bridge.correct(
                args.assertion,
                source_event_ids=args.source_event_id,
                source_artifact_ids=args.source_artifact_id,
            )
            _write_knowledge(args.workspace, bridge)
            return {"status": "pending_human_review", "candidate": candidate.to_dict()}
        if args.knowledge_command == "review":
            candidate = bridge.review(args.candidate_id, args.reviewer, args.approve, args.note)
            _write_knowledge(args.workspace, bridge)
            return {"status": "reviewed", "candidate": candidate.to_dict(), "canonical_write": False}
    raise AssertionError("unreachable")


def main() -> int:
    try:
        result = run(sys.argv[1:])
        if result["status"] == "interactive_ready":
            terminal_loop(Path(result["workspace"]))
        else:
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    except (
        LedgerViolation,
        SaveSlotViolation,
        SceneGraphViolation,
        TimelineViolation,
        KnowledgeBridgeViolation,
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        print(json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
