"""Deterministic quest, reward, relationship, and ending projections.

These projections are rebuilt from the verified ledger rather than stored as
another mutable source of truth.  Future scripts can add package-specific rules
without allowing an LLM or UI to write campaign facts directly.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .continuity import graph_for_ledger, replay_timeline, timeline_hash
from .contracts import AntagonistState, QuestState, RelationshipState, RewardState, canonical_json


class CampaignProgressionViolation(ValueError):
    pass


def _id(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:20]


def build_campaign_progression(ledger: Any) -> dict[str, Any]:
    ledger.verify_chain()
    graph = graph_for_ledger(ledger)
    timeline = replay_timeline(ledger, graph)
    if not timeline:
        raise CampaignProgressionViolation("campaign requires a verified timeline")
    final = timeline[-1]
    legal = graph.legal_actions(final.state)
    facts = tuple(final.state.known_facts)
    relationship = RelationshipState(
        character_id="mira",
        trust=int(final.state.relationships.get("mira", 0)),
        conflict=max(0, final.state.risk_level),
        commitment=1 if any(key in final.state.flags for key in {"handoff", "meeting", "record"}) else 0,
        known_by_character=facts,
    )
    quest = QuestState(
        quest_id=_id("quest_", {"graph": graph.revision, "start": timeline[0].event_id}),
        phase=final.state.scene_id + "/" + final.state.beat_id,
        objectives=("preserve safety", "resolve the verified public-safe lead"),
        pressure=final.state.risk_level,
        status="chapter_resolved" if not legal else "active",
    )
    # A0/A1 fixtures do not invent a named villain.  This explicit unresolved
    # opposition contract lets a later flagship package introduce one only from
    # approved story facts, rather than asking a model to manufacture motives.
    opposition = AntagonistState(
        antagonist_id="unresolved_opposition",
        objective="keep the verified lead unresolved until the player earns a lawful next fact",
        secret_boundary=facts,
        pressure=max(0, final.state.risk_level),
        countermeasure="restrict the next beat to approved evidence, relationship, and safety consequences",
        status="pressuring" if final.state.risk_level > 0 else "dormant",
    )
    rewards: list[RewardState] = []
    for entry in timeline[1:]:
        consequence = entry.consequence
        if consequence.get("new_facts"):
            rewards.append(RewardState(_id("reward_", {"event": entry.event_id, "type": "clue"}), "clue", entry.event_id, "A verified lead expands the next legal decision.", "The lead may increase responsibility."))
        if consequence.get("relationship_delta"):
            rewards.append(RewardState(_id("reward_", {"event": entry.event_id, "type": "relationship"}), "relationship", entry.event_id, "A companion visibly responds to the recorded choice.", "Trust can expose a later obligation."))
        if consequence.get("risk_delta", 0) < 0:
            rewards.append(RewardState(_id("reward_", {"event": entry.event_id, "type": "safety"}), "safety", entry.event_id, "A safer route creates breathing room.", "Safety may defer information or urgency."))
    material = {"graph_revision": graph.revision, "timeline_hash": timeline_hash(timeline), "quest": quest.to_dict(), "relationship": relationship.to_dict(), "opposition": opposition.to_dict(), "rewards": [reward.to_dict() for reward in rewards]}
    return {
        "schema": "PlayerCampaignProgression/v1",
        "status": "campaign_progression_verified",
        "timeline_hash": timeline_hash(timeline),
        "quest_state": quest.to_dict(),
        "relationship_states": [relationship.to_dict()],
        "antagonist_states": [opposition.to_dict()],
        "reward_states": [reward.to_dict() for reward in rewards],
        "ending": {"is_terminal": not legal, "current_path": quest.phase, "approved_terminal_only": True},
        "progression_hash": hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest(),
    }
