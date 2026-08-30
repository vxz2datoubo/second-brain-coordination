"""Offline, private-adaptation interactive-scene command line tool.

It is deliberately a bounded state machine: free text maps to a legal action or
asks for clarification.  It never calls a model, reads credentials, or produces
media.  The fixture is synthetic and uses adult characters only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creative_runtime.contracts import PlayerAction, StoryState, canonical_json
from creative_runtime.continuity import TimelineViolation, default_story_graph, graph_for_ledger, replay_timeline, timeline_hash
from creative_runtime.coverage import RouteCoverageViolation, coverage_for_scenario, director_coverage_for_scenario
from creative_runtime.director import compile_verified_director
from creative_runtime.generation import GenerationViolation, offline_generation_receipt_path, record_offline_generation, verify_offline_generation_record
from creative_runtime.feedback import FeedbackViolation, build_feedback_record, feedback_path, load_feedback, record_feedback
from creative_runtime.experience import ExperienceViolation, build_verified_experience, build_verified_scenario_catalog
from creative_runtime.ledger import CreativeLedger, LedgerViolation
from creative_runtime.knowledge import KnowledgeBridgeViolation, KnowledgeReviewBridge, correct_from_verified_timeline
from creative_runtime.operations import build_operations_report
from creative_runtime.presentation import PresentationViolation, build_interactive_frame
from creative_runtime.sequence import SequenceViolation, build_verified_sequence
from creative_runtime.understanding import bind_verified_timeline
from creative_runtime.session import (
    DEFAULT_SLOT,
    SessionViolation,
    atomic_replace_text,
    legacy_session_path,
    migrate_legacy_session,
    session_mutation_lock,
    validate_slot,
    v2_session_path,
    verify_v2_source_binding,
)


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
_COMMAND_ID_PATTERN = re.compile(r"cmd_[a-f0-9]{20}")
SCENARIOS = {
    "legacy_archive": StoryState(scene_id="synthetic_archive", beat_id="arrival", relationships={"mira": 0}),
    "three_scene": StoryState(scene_id="archive_gate", beat_id="arrival", relationships={"mira": 0}),
    "night_signal": StoryState(scene_id="station_platform", beat_id="platform_arrival", relationships={"mira": 0}),
    "harbor_protocol": StoryState(scene_id="harbor_observatory", beat_id="dock_arrival", relationships={"mira": 0}),
}


def synthetic_scene() -> dict[str, dict[str, Any]]:
    """Render the canonical graph; the CLI no longer owns a shadow graph."""

    return default_story_graph().to_cli_scene()


def session_path(workspace: Path, slot: str = DEFAULT_SLOT) -> Path:
    """Keep the default v1 filename while isolating validated named slots."""

    return legacy_session_path(workspace, slot)


def _write_session(workspace: Path, ledger: CreativeLedger, slot: str = DEFAULT_SLOT) -> None:
    path = session_path(workspace, slot)
    atomic_replace_text(path, canonical_json({"schema": SCHEMA, "events": ledger.to_records()}) + "\n")


def _load_session(workspace: Path, slot: str = DEFAULT_SLOT) -> CreativeLedger:
    path = session_path(workspace, slot)
    if not path.is_file():
        raise LedgerViolation("No session exists; run init first")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LedgerViolation("Session is not valid UTF-8 JSON") from error
    if not isinstance(data, Mapping):
        raise LedgerViolation("Session root must be a JSON object")
    if data.get("schema") != SCHEMA:
        raise LedgerViolation("Unsupported session schema")
    events = data.get("events")
    if not isinstance(events, list):
        raise LedgerViolation("Session events must be a JSON array")
    try:
        return CreativeLedger.from_records(events)
    except (KeyError, TypeError, ValueError, LedgerViolation) as error:
        raise LedgerViolation("Session event chain is invalid") from error


def _knowledge_path(workspace: Path, slot: str = DEFAULT_SLOT) -> Path:
    normalized = validate_slot(slot)
    if normalized == DEFAULT_SLOT:
        return workspace / "knowledge-review.json"
    return workspace / "knowledge-review" / (normalized + ".json")


def _load_knowledge(workspace: Path, slot: str = DEFAULT_SLOT) -> KnowledgeReviewBridge:
    path = _knowledge_path(workspace, slot)
    if not path.is_file():
        return KnowledgeReviewBridge()
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise KnowledgeBridgeViolation("Knowledge review packet is not valid UTF-8 JSON") from error
    if not isinstance(record, Mapping) or record.get("schema") != "CreativeKnowledgeReview/v1":
        raise KnowledgeBridgeViolation("Unsupported knowledge review packet schema")
    candidates = record.get("candidates")
    if not isinstance(candidates, list):
        raise KnowledgeBridgeViolation("Knowledge review candidates must be a JSON array")
    try:
        return KnowledgeReviewBridge.from_records(candidates)
    except (KeyError, TypeError, ValueError) as error:
        raise KnowledgeBridgeViolation("Knowledge review candidate record is invalid") from error


def _write_knowledge(workspace: Path, bridge: KnowledgeReviewBridge, slot: str = DEFAULT_SLOT) -> None:
    path = _knowledge_path(workspace, slot)
    atomic_replace_text(path, canonical_json({"schema": "CreativeKnowledgeReview/v1", "candidates": bridge.to_records()}) + "\n")


def _audit_workspace(workspace: Path, slot: str = DEFAULT_SLOT) -> dict[str, Any]:
    """Return a read-only, source-bound map of the current local lifecycle."""

    normalized_slot = validate_slot(slot)
    ledger = _load_session(workspace, normalized_slot)
    graph = graph_for_ledger(ledger)
    timeline = replay_timeline(ledger, graph)
    compiled = compile_verified_director(ledger, graph=graph)
    final_time = ledger.events[-1].occurred_at
    v2 = {"status": "not_migrated"}
    if v2_session_path(workspace, normalized_slot).is_file():
        v2 = verify_v2_source_binding(workspace, normalized_slot).to_dict()
    receipt_directory = offline_generation_receipt_path(workspace, "gen_" + "0" * 20, normalized_slot).parent
    receipts: dict[str, Any] = {}
    for path in sorted(receipt_directory.glob("gen_*.json")) if receipt_directory.is_dir() else ():
        receipt = verify_offline_generation_record(
            workspace,
            compiled,
            final_event_occurred_at=final_time,
            receipt_id=path.stem,
            slot=normalized_slot,
        )
        receipts[receipt.receipt_id] = receipt
    feedback_directory = feedback_path(workspace, "fb_" + "0" * 20, normalized_slot).parent
    feedback_items: list[dict[str, Any]] = []
    for path in sorted(feedback_directory.glob("fb_*.json")) if feedback_directory.is_dir() else ():
        feedback = load_feedback(workspace, path.stem, normalized_slot)
        receipt = receipts.get(feedback.receipt_id)
        if receipt is None:
            raise FeedbackViolation("Feedback refers to an offline generation receipt that is absent or not verified")
        if feedback.source_timeline_hash != receipt.source_timeline_hash or feedback.source_receipt_hash != receipt.receipt_hash:
            raise FeedbackViolation("Feedback source binding does not match its verified offline generation receipt")
        feedback_items.append(feedback.to_dict())
    candidates = _load_knowledge(workspace, normalized_slot).to_records()
    status_counts: dict[str, int] = {}
    for candidate in candidates:
        status = str(candidate["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "schema": "CreativeRuntimeWorkspaceAudit/v1",
        "status": "workspace_audit_verified",
        "story": {
            "slot_id": normalized_slot,
            "graph_revision": graph.revision,
            "timeline_hash": timeline_hash(timeline),
            "event_count": len(ledger.events),
            "final_event_id": timeline[-1].event_id,
            "final_state": timeline[-1].state.to_dict(),
        },
        "director": {
            "can_generate": compiled.compilation.quality_report.can_generate,
            "quality_metrics": compiled.compilation.quality_report.metrics.to_dict(),
            "activated_skill_ids": list(compiled.compilation.brief.activated_skill_ids),
        },
        "evidence": {
            "v2_source_binding": v2,
            "verified_offline_generation_receipts": [receipt.to_dict() for receipt in receipts.values()],
            "verified_feedback": feedback_items,
            "knowledge_candidate_status_counts": status_counts,
            "canonical_knowledge_write": False,
            "external_generation": False,
        },
    }


def _view(ledger: CreativeLedger) -> dict[str, Any]:
    state = ledger.replay()
    beat = graph_for_ledger(ledger).cli_view_for(state)
    options = [
        {"id": action_id, "label": option["label"]}
        for action_id, option in beat["options"].items()
    ]
    return {"status": "ready", "state": state.to_dict(), "text": beat["text"], "options": options}


def _validate_command_id(command_id: str | None) -> str | None:
    """Accept only opaque, caller-generated IDs safe to persist in the ledger."""

    if command_id is None:
        return None
    if not isinstance(command_id, str) or not _COMMAND_ID_PATTERN.fullmatch(command_id):
        raise LedgerViolation("command_id must be a stable opaque cmd_<20 lowercase hex> identifier")
    return command_id


def _previous_and_result_frames(ledger: CreativeLedger, sequence: int, slot: str) -> tuple[str, str]:
    """Reconstruct the exact command boundary from immutable event prefixes."""

    if sequence < 1 or sequence >= len(ledger.events):
        raise LedgerViolation("command event sequence is outside the story ledger")
    previous = build_interactive_frame(CreativeLedger(ledger.events[:sequence]), slot=slot)
    result = build_interactive_frame(CreativeLedger(ledger.events[: sequence + 1]), slot=slot)
    return previous.frame_id, result.frame_id


def _existing_command_result(ledger: CreativeLedger, command_id: str, action_id: str, slot: str) -> dict[str, Any] | None:
    """Find a prior command without trusting mutable client-side state."""

    matches = [
        event for event in ledger.events[1:]
        if event.event_type == "player_action" and event.payload.get("command_id") == command_id
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise LedgerViolation("command_id appears more than once in the immutable story ledger")
    event = matches[0]
    recorded_action = event.payload.get("action")
    if not isinstance(recorded_action, Mapping) or recorded_action.get("action_id") != action_id:
        raise LedgerViolation("command_id was already used for a different action")
    prior_frame_id, current_frame_id = _previous_and_result_frames(ledger, event.sequence, slot)
    latest_frame_id = build_interactive_frame(ledger, slot=slot).frame_id
    return {
        "status": "command_already_applied",
        "command_id": command_id,
        "action_id": action_id,
        "slot_id": slot,
        "prior_frame_id": prior_frame_id,
        "current_frame_id": current_frame_id,
        "latest_frame_id": latest_frame_id,
        "event_id": event.event_id,
    }


def initialize(workspace: Path, scenario: str = "legacy_archive", slot: str = DEFAULT_SLOT) -> dict[str, Any]:
    normalized_slot = validate_slot(slot)
    with session_mutation_lock(workspace, normalized_slot):
        if session_path(workspace, normalized_slot).exists():
            return {"status": "already_initialized", "session": str(session_path(workspace, normalized_slot)), "slot_id": normalized_slot}
        initial = SCENARIOS.get(scenario)
        if initial is None:
            raise LedgerViolation("Unknown scenario: " + scenario)
        ledger = CreativeLedger()
        ledger.append(
            "story_initialized",
            {"state": initial.to_dict()},
            "2030-01-01T00:00:00Z",
        )
        _write_session(workspace, ledger, normalized_slot)
        return {**_view(ledger), "status": "initialized", "session": str(session_path(workspace, normalized_slot)), "slot_id": normalized_slot}


def choose(
    workspace: Path,
    action_id: str,
    source_text: str | None = None,
    slot: str = DEFAULT_SLOT,
    expected_frame_id: str | None = None,
    command_id: str | None = None,
) -> dict[str, Any]:
    normalized_slot = validate_slot(slot)
    normalized_command_id = _validate_command_id(command_id)
    if expected_frame_id is not None and (not isinstance(expected_frame_id, str) or not expected_frame_id.startswith("frame_")):
        raise LedgerViolation("expected_frame_id must be a frame_<stable digest> identity")
    with session_mutation_lock(workspace, normalized_slot):
        ledger = _load_session(workspace, normalized_slot)
        if normalized_command_id is not None:
            existing = _existing_command_result(ledger, normalized_command_id, action_id, normalized_slot)
            if existing is not None:
                return existing
        state = ledger.replay()
        graph = graph_for_ledger(ledger)
        prior_frame = build_interactive_frame(ledger, slot=normalized_slot)
        if expected_frame_id is not None and expected_frame_id != prior_frame.frame_id:
            raise LedgerViolation("Stale client frame; reload the verified frame before choosing")
        beat = graph.cli_view_for(state)
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
                **({"command_id": normalized_command_id} if normalized_command_id is not None else {}),
            },
            f"2030-01-01T00:{len(ledger.events):02d}:00Z",
        )
        _write_session(workspace, ledger, normalized_slot)
        current_frame = build_interactive_frame(ledger, slot=normalized_slot)
        return {
            **_view(ledger),
            "status": "chosen",
            "action_id": action_id,
            "slot_id": normalized_slot,
            "command_id": normalized_command_id,
            "prior_frame_id": prior_frame.frame_id,
            "current_frame_id": current_frame.frame_id,
        }


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


def say(
    workspace: Path,
    text: str,
    slot: str = DEFAULT_SLOT,
    expected_frame_id: str | None = None,
    command_id: str | None = None,
) -> dict[str, Any]:
    normalized_slot = validate_slot(slot)
    ledger = _load_session(workspace, normalized_slot)
    state = ledger.replay()
    legal = set(graph_for_ledger(ledger).cli_view_for(state)["options"])
    action, confidence = parse_free_text(text, legal)
    if action is None or confidence < 0.8:
        return {
            "status": "clarification_required",
            "message": "Use a clear, non-explicit intent or select an available option.",
            "legal_options": sorted(legal),
        }
    return choose(
        workspace,
        action,
        source_text=text,
        slot=normalized_slot,
        expected_frame_id=expected_frame_id,
        command_id=command_id,
    )


def run(argv: list[str]) -> dict[str, Any]:
    parser = argparse.ArgumentParser(prog="creativectl")
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--slot", default=DEFAULT_SLOT, help="Validated local story slot; default preserves session.json compatibility.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="legacy_archive")
    subparsers.add_parser("play")
    choose_parser = subparsers.add_parser("choose")
    choose_parser.add_argument("action_id")
    choose_parser.add_argument("--expected-frame-id")
    choose_parser.add_argument("--command-id")
    say_parser = subparsers.add_parser("say")
    say_parser.add_argument("text")
    say_parser.add_argument("--expected-frame-id")
    say_parser.add_argument("--command-id")
    subparsers.add_parser("resume")
    subparsers.add_parser("replay")
    subparsers.add_parser("timeline")
    subparsers.add_parser("director")
    subparsers.add_parser("understanding")
    subparsers.add_parser("migrate")
    subparsers.add_parser("verify-v2")
    generate_parser = subparsers.add_parser("generate-offline")
    generate_parser.add_argument("--shot-id")
    verify_generation_parser = subparsers.add_parser("verify-generation")
    verify_generation_parser.add_argument("receipt_id")
    feedback_parser = subparsers.add_parser("feedback")
    feedback_parser.add_argument("receipt_id")
    feedback_parser.add_argument("rating", type=int)
    feedback_parser.add_argument("note")
    subparsers.add_parser("audit")
    subparsers.add_parser("operations")
    subparsers.add_parser("frame")
    subparsers.add_parser("experience")
    subparsers.add_parser("sequence")
    catalog_parser = subparsers.add_parser("catalog")
    catalog_parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="night_signal")
    coverage_parser = subparsers.add_parser("coverage")
    coverage_parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="three_scene")
    director_coverage_parser = subparsers.add_parser("director-coverage")
    director_coverage_parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="three_scene")
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
    slot = validate_slot(args.slot)
    if args.command == "init":
        return initialize(args.workspace, args.scenario, slot)
    if args.command in {"play", "resume"}:
        return {**_view(_load_session(args.workspace, slot)), "slot_id": slot}
    if args.command == "choose":
        return choose(
            args.workspace,
            args.action_id,
            slot=slot,
            expected_frame_id=args.expected_frame_id,
            command_id=args.command_id,
        )
    if args.command == "say":
        return say(args.workspace, args.text, slot, args.expected_frame_id, args.command_id)
    if args.command == "replay":
        ledger = _load_session(args.workspace, slot)
        return {**_view(ledger), "status": "replayed", "event_count": len(ledger.events), "slot_id": slot}
    if args.command == "timeline":
        ledger = _load_session(args.workspace, slot)
        graph = graph_for_ledger(ledger)
        entries = replay_timeline(ledger, graph)
        return {
            "status": "timeline_verified",
            "graph_revision": graph.revision,
            "timeline_hash": timeline_hash(entries),
            "entries": [entry.to_dict() for entry in entries],
            "slot_id": slot,
        }
    if args.command == "director":
        ledger = _load_session(args.workspace, slot)
        compiled = compile_verified_director(ledger, graph=graph_for_ledger(ledger))
        return {
            "status": "director_verified",
            "verified_input": compiled.verified_input.to_dict(),
            "brief": compiled.compilation.brief.to_dict(),
            "shots": [shot.to_dict() for shot in compiled.compilation.shots],
            "quality_report": compiled.compilation.quality_report.to_dict(),
            "slot_id": slot,
        }
    if args.command == "understanding":
        ledger = _load_session(args.workspace, slot)
        verified = compile_verified_director(ledger, graph=graph_for_ledger(ledger)).verified_input
        mapped = bind_verified_timeline(verified, len(ledger.events), ledger.events[-1].occurred_at)
        return {
            "status": "understanding_mapped",
            "map": mapped.to_dict(),
            "drift_assessments": [assessment.to_dict() for assessment in mapped.assess()],
            "slot_id": slot,
        }
    if args.command == "migrate":
        ledger = _load_session(args.workspace, slot)
        return migrate_legacy_session(args.workspace, ledger.events[-1].occurred_at, slot).to_dict()
    if args.command == "verify-v2":
        return verify_v2_source_binding(args.workspace, slot).to_dict()
    if args.command == "generate-offline":
        ledger = _load_session(args.workspace, slot)
        compiled = compile_verified_director(ledger, graph=graph_for_ledger(ledger))
        return record_offline_generation(
            args.workspace,
            compiled,
            final_event_occurred_at=ledger.events[-1].occurred_at,
            shot_id=args.shot_id,
            slot=slot,
        ).to_dict()
    if args.command == "verify-generation":
        ledger = _load_session(args.workspace, slot)
        compiled = compile_verified_director(ledger, graph=graph_for_ledger(ledger))
        receipt = verify_offline_generation_record(
            args.workspace,
            compiled,
            final_event_occurred_at=ledger.events[-1].occurred_at,
            receipt_id=args.receipt_id,
            slot=slot,
        )
        return {"status": "offline_generation_verified", "receipt": receipt.to_dict()}
    if args.command == "feedback":
        ledger = _load_session(args.workspace, slot)
        compiled = compile_verified_director(ledger, graph=graph_for_ledger(ledger))
        receipt = verify_offline_generation_record(
            args.workspace,
            compiled,
            final_event_occurred_at=ledger.events[-1].occurred_at,
            receipt_id=args.receipt_id,
            slot=slot,
        )
        feedback = build_feedback_record(
            receipt,
            rating=args.rating,
            note=args.note,
            submitted_at=ledger.events[-1].occurred_at,
            slot=slot,
        )
        status, saved, path = record_feedback(args.workspace, feedback, slot)
        bridge = _load_knowledge(args.workspace, slot)
        candidate = bridge.correct(
            "Offline generation feedback " + saved.feedback_id + ": " + saved.note,
            source_event_ids=(receipt.source_final_event_id,),
            source_artifact_ids=(
                "offline_generation_receipt:" + receipt.receipt_id,
                "timeline_sha256:" + receipt.source_timeline_hash,
            ),
        )
        _write_knowledge(args.workspace, bridge, slot)
        return {
            "status": status,
            "feedback": saved.to_dict(),
            "feedback_path": str(path),
            "knowledge_candidate": candidate.to_dict(),
            "canonical_write": False,
            "slot_id": slot,
        }
    if args.command == "audit":
        return _audit_workspace(args.workspace, slot)
    if args.command == "operations":
        return build_operations_report(args.workspace)
    if args.command == "frame":
        return build_interactive_frame(_load_session(args.workspace, slot), slot=slot).to_dict()
    if args.command == "experience":
        return build_verified_experience(_load_session(args.workspace, slot), slot=slot).to_dict()
    if args.command == "sequence":
        return build_verified_sequence(_load_session(args.workspace, slot), slot=slot).to_dict()
    if args.command == "catalog":
        return build_verified_scenario_catalog(args.scenario).to_dict()
    if args.command == "coverage":
        return coverage_for_scenario(args.scenario).to_dict()
    if args.command == "director-coverage":
        return director_coverage_for_scenario(args.scenario).to_dict()
    if args.command == "knowledge":
        bridge = _load_knowledge(args.workspace, slot)
        if args.knowledge_command == "search":
            return {"status": "searched", "candidates": [item.to_dict() for item in bridge.search(args.query)]}
        if args.knowledge_command == "correct":
            candidate = bridge.correct(args.assertion, source_event_ids=args.source_event_id, source_artifact_ids=args.source_artifact_id)
            _write_knowledge(args.workspace, bridge, slot)
            return {"status": "pending_human_review", "candidate": candidate.to_dict()}
        if args.knowledge_command == "derive":
            derived = correct_from_verified_timeline(
                bridge,
                args.assertion,
                _load_session(args.workspace, slot),
                graph_for_ledger(_load_session(args.workspace, slot)),
            )
            _write_knowledge(args.workspace, bridge, slot)
            return {"status": "pending_human_review", "verified_timeline_candidate": derived.to_dict()}
        if args.knowledge_command == "review":
            candidate = bridge.review(args.candidate_id, args.reviewer, args.approve, args.note)
            _write_knowledge(args.workspace, bridge, slot)
            return {"status": "reviewed", "candidate": candidate.to_dict(), "canonical_write": False}
    raise AssertionError("unreachable")


def main() -> int:
    try:
        print(json.dumps(run(sys.argv[1:]), ensure_ascii=False, sort_keys=True, indent=2))
    except (ExperienceViolation, FeedbackViolation, GenerationViolation, LedgerViolation, KnowledgeBridgeViolation, PresentationViolation, RouteCoverageViolation, SequenceViolation, SessionViolation, TimelineViolation, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
