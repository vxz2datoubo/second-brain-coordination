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

from creative_runtime.contracts import StoryState, canonical_json
from creative_runtime.ledger import CreativeLedger, LedgerViolation
from creative_runtime.knowledge import KnowledgeBridgeViolation, KnowledgeReviewBridge
from creative_runtime.saves import SaveStore, SaveViolation, SavedSession
from creative_runtime.scene_graph import SceneGraph


DEFAULT_WORKSPACE = Path(".creative-runtime")
UNSAFE_TERMS = {"sex", "sexual", "nude", "blood", "gore", "torture"}


def synthetic_scene() -> dict[str, dict[str, Any]]:
    """A non-explicit fixture with distinct choices and observable consequences."""

    return {
        "arrival": {
            "text": "Two adult archivists pause outside a locked, rain-lit archive door.",
            "options": {
                "listen": {
                    "label": "Listen at the door",
                    "patch": {"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1},
                },
                "approach": {
                    "label": "Knock and announce yourself",
                    "patch": {"beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}},
                },
                "leave": {
                    "label": "Step back and call for daylight",
                    "patch": {"beat_id": "courtyard", "risk_delta": -1, "flags": {"arrival": "deferred"}},
                },
            },
        },
        "echo": {
            "text": "A low voice names an old case number; Mira watches the corridor.",
            "options": {
                "approach": {"label": "Ask Mira to knock", "patch": {"beat_id": "threshold", "relationship_delta": {"mira": 1}}},
                "leave": {"label": "Mark the clue and withdraw", "patch": {"beat_id": "courtyard", "flags": {"clue": "recorded"}}},
            },
        },
        "threshold": {
            "text": "The door opens a handspan. The unseen witness asks whether the archive is safe.",
            "options": {
                "listen": {"label": "Promise to listen before acting", "patch": {"beat_id": "resolution", "relationship_delta": {"mira": 1}, "risk_delta": -1}},
                "leave": {"label": "Leave a safe meeting place", "patch": {"beat_id": "courtyard", "flags": {"meeting": "offered"}}},
            },
        },
        "courtyard": {
            "text": "Morning light reaches the courtyard. The case is paused, not erased.",
            "options": {},
        },
        "resolution": {
            "text": "The group agrees to preserve the record and meet in daylight.",
            "options": {},
        },
    }


def session_path(workspace: Path) -> Path:
    return workspace / "session.json"


def _write_session(workspace: Path, session: SavedSession) -> None:
    SaveStore(workspace).save(session)


def _load_saved_session(workspace: Path) -> SavedSession:
    return SaveStore(workspace).load()


def _load_session(workspace: Path) -> CreativeLedger:
    """Compatibility surface for existing offline knowledge callers."""
    return _load_saved_session(workspace).ledger


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


def _view(session: SavedSession) -> dict[str, Any]:
    state = session.state()
    beat = synthetic_scene()[{"accord": "resolution", "return": "courtyard"}.get(state.beat_id, state.beat_id)]
    options = [
        {"id": action_id, "label": option["label"]}
        for action_id, option in beat["options"].items()
    ]
    return {"status": "ready", "state": state.to_dict(), "text": beat["text"], "options": options}


def initialize(workspace: Path) -> dict[str, Any]:
    store = SaveStore(workspace)
    if store.path_for().exists() or session_path(workspace).exists():
        return {"status": "already_initialized", "session": str(store.path_for())}
    session = store.create_initial()
    store.save(session)
    return {**_view(session), "status": "initialized", "session": str(store.path_for())}


def _normalize_action(state: StoryState, action_id: str) -> str | None:
    legal = set(SceneGraph().legal_actions(state))
    aliases = {
        "approach": "knock",
        "leave": "defer" if state.beat_id == "arrival" else "record" if state.beat_id == "echo" else "retreat",
    }
    proposed = aliases.get(action_id, action_id)
    return proposed if proposed in legal else None


def choose(workspace: Path, action_id: str, source_text: str | None = None) -> dict[str, Any]:
    store = SaveStore(workspace)
    session = store.load()
    state = session.state()
    graph_action = _normalize_action(state, action_id)
    if graph_action is None:
        return {
            "status": "clarification_required",
            "message": "That action is not legal at this beat; choose one listed option.",
            "legal_options": sorted(SceneGraph().legal_actions(state)),
        }
    session = store.append_choice(
        session,
        graph_action,
        source_text or action_id,
        f"2030-01-01T00:{len(session.ledger.events):02d}:00Z",
    )
    store.save(session)
    return {**_view(session), "status": "chosen", "action_id": action_id}


def parse_free_text(text: str, legal_actions: set[str]) -> tuple[str | None, float]:
    normalized = text.lower().strip()
    tokens = set(normalized.replace(".", " ").replace(",", " ").split())
    if tokens & UNSAFE_TERMS:
        return None, 0.0
    signals = {
        "listen": {"listen", "hear", "quiet", "door"},
        "approach": {"approach", "knock", "enter", "walk"},
        "leave": {"leave", "withdraw", "back", "wait"},
        "knock": {"knock", "announce", "enter"},
        "promise": {"promise", "assure"},
        "defer": {"defer", "daylight", "wait"},
        "record": {"record", "mark", "note"},
        "retreat": {"retreat", "meeting", "withdraw"},
    }
    matches = [action for action in legal_actions if tokens & signals.get(action, set())]
    if len(matches) != 1:
        return None, 0.0
    return matches[0], 0.9


def say(workspace: Path, text: str) -> dict[str, Any]:
    state = _load_saved_session(workspace).state()
    legal = set(SceneGraph().legal_actions(state))
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
        return _view(_load_saved_session(args.workspace))
    if args.command == "choose":
        return choose(args.workspace, args.action_id)
    if args.command == "say":
        return say(args.workspace, args.text)
    if args.command == "replay":
        session = _load_saved_session(args.workspace)
        return {**_view(session), "status": "replayed", "event_count": len(session.ledger.events)}
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
    except (LedgerViolation, SaveViolation, KnowledgeBridgeViolation, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
