"""Approved-for-authoring flagship season bible with mechanical choice gates.

The season is content data, not a generator prompt.  It gives later graph and
director slices a finite, reviewable source for a 45-60 minute season while
making every major choice carry a state change, feedback, and cost.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from .contracts import canonical_json


class FlagshipSeasonViolation(ValueError):
    pass


DIMENSIONS = frozenset({"clue", "relationship", "resource", "risk", "quest", "scene", "ending"})
FEEDBACK = frozenset({"new_clue", "companion_reaction", "resource_unlock", "risk_shift", "quest_progress", "emotional_payoff", "spectacle", "ending_unlock"})


FLAGSHIP_SEASON_01: dict[str, Any] = {
    "schema": "FlagshipSeasonBible/v1",
    "script_id": "glass-harbor-season-01",
    "script_revision": "GlassHarborSeason01/v1",
    "title": "Glass Harbor",
    "approval_status": "approved_for_authoring_not_runtime",
    "content_rating": "non_explicit_adult_roles",
    "genre": ["adventure", "mystery", "crime", "emotion"],
    "target_duration_minutes": {"min": 45, "max": 60},
    "theme": "Truth is not ownership: people earn trust by carrying evidence without treating people as evidence.",
    "world_bible": "A storm-damaged harbor city is rebuilding its civic records after a blackout. A public signal appears to expose a sealed fraud, but every shortcut risks turning a witness into a tool.",
    "companions": [
        {"character_id": "mira", "adult": True, "want": "protect a witness without repeating an old institutional betrayal", "fear": "that caution will become silence", "arc": "from controlled distance to accountable trust"},
        {"character_id": "ren", "adult": True, "want": "restore a lost community radio archive", "fear": "that public truth will hurt the people he promised to protect", "arc": "from performative certainty to listening"},
    ],
    "antagonist": {"character_id": "zhou_wen", "adult": True, "want": "keep a civic reconstruction contract from being traced to its victims", "secret_boundary": "The antagonist knows the blackout route but not the player's earned private choices.", "counterplay": "offers convenient but incomplete records, public pressure, and false closure; never mind-control or overrides player facts."},
    "acts": [
        {"act": 1, "name": "The Signal", "chapters": ["C1", "C2"]},
        {"act": 2, "name": "The Price of Proof", "chapters": ["C3", "C4"]},
        {"act": 3, "name": "Daylight Record", "chapters": ["C5", "C6"]},
    ],
    "chapters": [
        {"id": "C1", "title": "Beacon Without a Sender", "act": 1, "goal": "Choose how to approach the returning harbor signal.", "choices": [
            {"id": "C1_A", "label": "Trace the rhythm with Mira", "changes": ["clue", "relationship", "risk"], "feedback": "new_clue", "cost": "The beacon learns someone is listening.", "echo": "Mira later shares a withheld detail."},
            {"id": "C1_B", "label": "Broadcast a cautious public question with Ren", "changes": ["quest", "resource", "risk"], "feedback": "resource_unlock", "cost": "The city notices before the group is ready.", "echo": "A caller provides a contested route."},
        ]},
        {"id": "C2", "title": "The Unclaimed Ledger", "act": 1, "goal": "Decide whether evidence is protected or immediately exposed.", "choices": [
            {"id": "C2_A", "label": "Seal the ledger and request a witness", "changes": ["quest", "relationship", "scene"], "feedback": "companion_reaction", "cost": "The lead goes cold for a night.", "echo": "A witness agrees to meet in daylight."},
            {"id": "C2_B", "label": "Compare the ledger against the public archive", "changes": ["clue", "risk", "scene"], "feedback": "quest_progress", "cost": "A forged page enters the public record.", "echo": "The forgery points toward the contractor."},
        ]},
        {"id": "C3", "title": "A Friend's Frequency", "act": 2, "goal": "Handle Ren's private connection to the blackout archive.", "choices": [
            {"id": "C3_A", "label": "Ask Ren to name what he is protecting", "changes": ["relationship", "clue", "risk"], "feedback": "emotional_payoff", "cost": "Trust becomes a promise with consequences.", "echo": "Ren reveals a route only he can verify."},
            {"id": "C3_B", "label": "Keep the case procedural and exclude Ren", "changes": ["resource", "relationship", "quest"], "feedback": "risk_shift", "cost": "The team gains safety but loses warmth.", "echo": "Ren may challenge the final record."},
        ]},
        {"id": "C4", "title": "The Contract's Shadow", "act": 2, "goal": "Respond to Zhou Wen's offer of a convenient explanation.", "choices": [
            {"id": "C4_A", "label": "Accept the archive access but log every condition", "changes": ["resource", "clue", "risk"], "feedback": "resource_unlock", "cost": "The antagonist can test the team's patience.", "echo": "A condition exposes a missing name."},
            {"id": "C4_B", "label": "Refuse and follow the harbor workers' route", "changes": ["scene", "relationship", "risk"], "feedback": "spectacle", "cost": "The route is dangerous and time-limited.", "echo": "Mira sees the human cost behind the fraud."},
        ]},
        {"id": "C5", "title": "What the Witness Owes", "act": 3, "goal": "Choose how much burden to place on the witness.", "choices": [
            {"id": "C5_A", "label": "Let the witness speak only to verified facts", "changes": ["relationship", "quest", "ending"], "feedback": "emotional_payoff", "cost": "Some public questions remain unanswered.", "echo": "The humane ending becomes available."},
            {"id": "C5_B", "label": "Use the signal to force an immediate hearing", "changes": ["risk", "quest", "ending"], "feedback": "risk_shift", "cost": "The public gets speed, not certainty.", "echo": "The decisive ending becomes available."},
        ]},
        {"id": "C6", "title": "Daylight Record", "act": 3, "goal": "Close the chapter with an accountable public act.", "choices": [
            {"id": "C6_A", "label": "Publish a limited record and keep the witness safe", "changes": ["ending", "relationship", "quest"], "feedback": "ending_unlock", "cost": "The contractor remains partly unexposed.", "echo": "Ending: Accountable Dawn."},
            {"id": "C6_B", "label": "Release the full verified chain with the team beside you", "changes": ["ending", "clue", "relationship"], "feedback": "ending_unlock", "cost": "Every ally must live with the aftermath.", "echo": "Ending: Harbor in the Open."},
        ]},
    ],
}


def validate_flagship_season(season: Mapping[str, Any] = FLAGSHIP_SEASON_01) -> dict[str, Any]:
    if season.get("schema") != "FlagshipSeasonBible/v1" or season.get("approval_status") != "approved_for_authoring_not_runtime":
        raise FlagshipSeasonViolation("flagship season must be an approved-for-authoring bible, not a runtime package")
    acts = season.get("acts")
    chapters = season.get("chapters")
    if not isinstance(acts, list) or len(acts) != 3 or not isinstance(chapters, list) or len(chapters) != 6:
        raise FlagshipSeasonViolation("flagship season requires exactly 3 acts and 6 chapters")
    choices = [choice for chapter in chapters for choice in chapter.get("choices", [])]
    if len(choices) != 12 or len({choice.get("id") for choice in choices}) != 12:
        raise FlagshipSeasonViolation("flagship season requires exactly 12 unique primary choices")
    for chapter in chapters:
        if chapter.get("act") not in {1, 2, 3} or len(chapter.get("choices", [])) != 2:
            raise FlagshipSeasonViolation("every chapter requires one valid act and exactly two primary choices")
    for choice in choices:
        changed = set(choice.get("changes", []))
        if not changed or not changed <= DIMENSIONS:
            raise FlagshipSeasonViolation("primary choice has an invalid durable-change dimension")
        if choice.get("feedback") not in FEEDBACK or not choice.get("cost") or not choice.get("echo"):
            raise FlagshipSeasonViolation("primary choice requires feedback, cost, and later echo")
    duration = season.get("target_duration_minutes", {})
    if duration.get("min") != 45 or duration.get("max") != 60:
        raise FlagshipSeasonViolation("flagship duration must remain 45-60 minutes")
    material = {"script_id": season["script_id"], "revision": season["script_revision"], "choices": choices}
    return {"schema": "FlagshipSeasonValidation/v1", "status": "flagship_season_authoring_valid", "act_count": 3, "chapter_count": 6, "primary_choice_count": 12, "choice_coverage_percent": 100, "content_hash": hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest(), "runtime_ready": False}


def flagship_season_catalog() -> dict[str, Any]:
    validation = validate_flagship_season()
    return {"season": FLAGSHIP_SEASON_01, "validation": validation, "boundary": {"runtime_graph_compiled": False, "external_assets_loaded": False, "generated_media_loaded": False, "authority_note": "Authoring blueprint only. A later approved graph and asset slice must compile it before campaign creation."}}
