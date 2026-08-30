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

from creative_runtime.contracts import PlayerAction, StoryState, canonical_json
from creative_runtime.continuity import TimelineViolation, default_story_graph, graph_for_ledger, replay_timeline, timeline_hash
from creative_runtime.director import compile_verified_director
from creative_runtime.ledger import CreativeLedger, LedgerViolation
from creative_runtime.knowledge import KnowledgeBridgeViolation, KnowledgeReviewBridge, correct_from_verified_timeline
from creative_runtime.understanding import bind_verified_timeline
from creative_runtime.session import SessionViolation, migrate_legacy_session


SCHEMA = "CreativeSession/v1"
DEFAULT_WORKSPACE = Path(".creative-runtime")
# The runtime is non-explicit in every supported interaction language.  Phrases
# are checked before intent matching so unsafe text cannot become a legal action
# simply because it also contains a word such as "listen" or "leave".
UNSAFE_TERMS = {"sex", "sexual", "nude", "blood", "gore", "torture"}
UNSAFE_PHRASES = {
    "sex", "sexual", "nude", "blood", "gore", "torture",
    "性爱", "性行为", "色情", "裸露", "裸体", "露骨", "血腥", "酷刑", "虐待",
}
SCENARIOS = {
    "legacy_archive": StoryState(scene_id="synthetic_archive", beat_id="arrival", relationships={"mira": 0}),
    "three_scene": StoryState(scene_id="archive_gate", beat_id="arrival", relationships={"mira": 0}),
}


def synthetic_scene() -> dict[str, dict[str, Any]]:
    """Render the canonical graph; the CLI no longer owns a shadow graph."""

    return default_story_graph().to_cli_scene()


def session_path(workspace: Path) -> Path:
    return workspace / "session.json"


def _write_session(workspace: Path, ledger: CreativeLedger) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    session_path(workspace).write_text(
        canonical_json({"schema": SCHEMA, "events": ledger.to_records()}) + "\n",
        encoding="utf-8",
    )


def _load_session(workspace: Path) -> CreativeLedger:
    path = session_path(workspace)
    if not path.is_file():
        raise LedgerViolation("No session exists; run init first")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise LedgerViolation("Unsupported session schema")
    return CreativeLedger.from_records(data.get("events", []))


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


def _view(ledger: CreativeLedger) -> dict[str, Any]:
    state = ledger.replay()
    beat = graph_for_ledger(ledger).to_cli_scene()[state.beat_id]
    options = [
        {"id": action_id, "label": option["label"]}
        for action_id, option in beat["options"].items()
    ]
    return {"status": "ready", "state": state.to_dict(), "text": beat["text"], "options": options}


def initialize(workspace: Path, scenario: str = "legacy_archive") -> dict[str, Any]:
    if session_path(workspace).exists():
        return {"status": "already_initialized", "session": str(session_path(workspace))}
    initial = SCENARIOS.get(scenario)
    if initial is None:
        raise LedgerViolation("Unknown scenario: " + scenario)
    ledger = CreativeLedger()
    ledger.append(
        "story_initialized",
        {"state": initial.to_dict()},
        "2030-01-01T00:00:00Z",
    )
    _write_session(workspace, ledger)
    return {**_view(ledger), "status": "initialized", "session": str(session_path(workspace))}


def choose(workspace: Path, action_id: str, source_text: str | None = None) -> dict[str, Any]:
    ledger = _load_session(workspace)
    state = ledger.replay()
    graph = graph_for_ledger(ledger)
    beat = graph.to_cli_scene()[state.beat_id]
    option = beat["options"].get(action_id)
    if option is None:
        return {
            "status": "clarification_required",
            "message": "That action is not legal at this beat; choose one listed option.",
            "legal_options": sorted(beat["options"]),
        }
    ledger.append(
        "player_action",
        {
            "action": PlayerAction(action_id, "choice", source_text or option["label"]).to_dict(),
            "resulting_patch": option["patch"],
            "transition_id": option["transition_id"],
            "graph_revision": graph.revision,
        },
        f"2030-01-01T00:{len(ledger.events):02d}:00Z",
    )
    _write_session(workspace, ledger)
    return {**_view(ledger), "status": "chosen", "action_id": action_id}


def parse_free_text(text: str, legal_actions: set[str]) -> tuple[str | None, float]:
    normalized = text.lower().strip()
    if any(term in normalized for term in UNSAFE_PHRASES):
        return None, 0.0
    tokens = set(normalized.replace(".", " ").replace(",", " ").split())
    if tokens & UNSAFE_TERMS:
        return None, 0.0
    signals = {
        "listen": {"listen", "hear", "quiet", "door", "听", "倾听", "聆听"},
        "approach": {"approach", "knock", "enter", "walk", "敲门", "靠近", "进入"},
        "leave": {"leave", "withdraw", "back", "wait", "离开", "撤退", "后退", "等待"},
    }
    matches = [
        action
        for action in legal_actions
        if tokens & signals.get(action, set()) or any(signal in normalized for signal in signals.get(action, set()) if len(signal) > 1)
    ]
    if len(matches) != 1:
        return None, 0.0
    return matches[0], 0.9


def say(workspace: Path, text: str) -> dict[str, Any]:
    ledger = _load_session(workspace)
    state = ledger.replay()
    legal = set(graph_for_ledger(ledger).to_cli_scene()[state.beat_id]["options"])
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
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="legacy_archive")
    subparsers.add_parser("play")
    choose_parser = subparsers.add_parser("choose")
    choose_parser.add_argument("action_id")
    say_parser = subparsers.add_parser("say")
    say_parser.add_argument("text")
    subparsers.add_parser("resume")
    subparsers.add_parser("replay")
    subparsers.add_parser("timeline")
    subparsers.add_parser("director")
    subparsers.add_parser("understanding")
    subparsers.add_parser("migrate")
    knowledge_parser = subparsers.add_parser("knowledge")
    knowledge_subparsers = knowledge_parser.add_subparsers(dest="knowledge_command", required=True)
    knowledge_search = knowledge_subparsers.add_parser("search")
    knowledge_search.add_argument("query")
    knowledge_correct = knowledge_subparsers.add_parser("correct")
    knowledge_correct.add_argument("assertion")
    knowledge_correct.add_argument("--source-event-id", action="append", default=[])
    knowledge_correct.add_argument("--source-artifact-id", action="append", default=[])
    knowledge_derive = knowledge_subparsers.add_parser("derive")
    knowledge_derive.add_argument("assertion")
    knowledge_review = knowledge_subparsers.add_parser("review")
    knowledge_review.add_argument("candidate_id")
    knowledge_review.add_argument("--reviewer", required=True)
    knowledge_review.add_argument("--approve", action="store_true")
    knowledge_review.add_argument("--note", default="")
    args = parser.parse_args(argv)
    if args.command == "init":
        return initialize(args.workspace, args.scenario)
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
        graph = graph_for_ledger(ledger)
        entries = replay_timeline(ledger, graph)
        return {
            "status": "timeline_verified",
            "graph_revision": graph.revision,
            "timeline_hash": timeline_hash(entries),
            "entries": [entry.to_dict() for entry in entries],
        }
    if args.command == "director":
        ledger = _load_session(args.workspace)
        compiled = compile_verified_director(ledger, graph=graph_for_ledger(ledger))
        return {
            "status": "director_verified",
            "verified_input": compiled.verified_input.to_dict(),
            "brief": compiled.compilation.brief.to_dict(),
            "shots": [shot.to_dict() for shot in compiled.compilation.shots],
            "quality_report": compiled.compilation.quality_report.to_dict(),
        }
    if args.command == "understanding":
        ledger = _load_session(args.workspace)
        verified = compile_verified_director(ledger, graph=graph_for_ledger(ledger)).verified_input
        mapped = bind_verified_timeline(verified, len(ledger.events), ledger.events[-1].occurred_at)
        return {
            "status": "understanding_mapped",
            "map": mapped.to_dict(),
            "drift_assessments": [assessment.to_dict() for assessment in mapped.assess()],
        }
    if args.command == "migrate":
        ledger = _load_session(args.workspace)
        return migrate_legacy_session(args.workspace, ledger.events[-1].occurred_at).to_dict()
    if args.command == "knowledge":
        bridge = _load_knowledge(args.workspace)
        if args.knowledge_command == "search":
            return {"status": "searched", "candidates": [item.to_dict() for item in bridge.search(args.query)]}
        if args.knowledge_command == "correct":
            candidate = bridge.correct(args.assertion, source_event_ids=args.source_event_id, source_artifact_ids=args.source_artifact_id)
            _write_knowledge(args.workspace, bridge)
            return {"status": "pending_human_review", "candidate": candidate.to_dict()}
        if args.knowledge_command == "derive":
            derived = correct_from_verified_timeline(
                bridge,
                args.assertion,
                _load_session(args.workspace),
                graph_for_ledger(_load_session(args.workspace)),
            )
            _write_knowledge(args.workspace, bridge)
            return {"status": "pending_human_review", "verified_timeline_candidate": derived.to_dict()}
        if args.knowledge_command == "review":
            candidate = bridge.review(args.candidate_id, args.reviewer, args.approve, args.note)
            _write_knowledge(args.workspace, bridge)
            return {"status": "reviewed", "candidate": candidate.to_dict(), "canonical_write": False}
    raise AssertionError("unreachable")


def main() -> int:
    try:
        print(json.dumps(run(sys.argv[1:]), ensure_ascii=False, sort_keys=True, indent=2))
    except (LedgerViolation, KnowledgeBridgeViolation, SessionViolation, TimelineViolation, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
