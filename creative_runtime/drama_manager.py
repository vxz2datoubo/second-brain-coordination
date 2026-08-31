"""Offline narrative proposals and fail-closed dramatic-beat selection.

This is intentionally not a free-form story author.  The simulator may offer
dialogue and presentation candidates, but a proposal becomes usable only if it
matches the exact legal graph edge for the current verified state.  It never
appends events or mutates a campaign ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable, Mapping

from .continuity import StoryGraph, graph_for_ledger, replay_timeline, timeline_hash
from .contracts import ChoiceIntent, DramaticBeatSelection, NarrativeProposal, StoryState, canonical_json
from .director_context import campaign_id_for_ledger


class DramaManagerViolation(ValueError):
    """Raised when a candidate cannot be tied to a verified story edge."""


DRAMA_POLICY_REVISION = "OfflineDramaPolicy/v1"


def _hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _state_hash(state: StoryState) -> str:
    return _hash(state.to_dict())


def _intent(ledger: Any, action_id: str) -> ChoiceIntent:
    graph = graph_for_ledger(ledger)
    state = ledger.replay()
    graph.transition_for(state, action_id)
    campaign_id = campaign_id_for_ledger(ledger)
    material = {"campaign_id": campaign_id, "state": state.to_dict(), "action_id": action_id}
    return ChoiceIntent(
        intent_id="intent_" + _hash(material)[:20],
        campaign_id=campaign_id,
        source_type="offline_declared_choice",
        normalized_choice_id=action_id,
        confidence=1.0,
        clarification_required=False,
        content_gate_status="non_explicit_pass",
    )


def propose_offline_narrative(ledger: Any, action_id: str) -> NarrativeProposal:
    """Produce a deterministic, non-authoritative candidate for one legal edge."""

    ledger.verify_chain()
    graph = graph_for_ledger(ledger)
    state = ledger.replay()
    transition = graph.transition_for(state, action_id)
    intent = _intent(ledger, action_id)
    material = {
        "campaign_id": intent.campaign_id,
        "state_hash": _state_hash(state),
        "intent_id": intent.intent_id,
        "transition_id": transition.transition_id,
        "policy": DRAMA_POLICY_REVISION,
    }
    return NarrativeProposal(
        proposal_id="proposal_" + _hash(material)[:20],
        campaign_id=intent.campaign_id,
        based_on_state_hash=_state_hash(state),
        choice_intent_id=intent.intent_id,
        candidate_dialogue=("Mira acknowledges the player's declared choice and keeps the established boundary visible.",),
        candidate_character_reactions={"mira": "responds only to facts already in the verified state"},
        candidate_beat_ids=(transition.from_beat_id, str(transition.resulting_patch.get("beat_id", transition.from_beat_id))),
        candidate_presentation={"feedback_type": feedback_type_for_patch(transition.resulting_patch), "content_rating": "non_explicit"},
        model_or_simulator_ref="offline_deterministic_proposal_simulator/v1",
        policy_revision=DRAMA_POLICY_REVISION,
        proposed_transition_id=transition.transition_id,
    )


def feedback_type_for_patch(patch: Mapping[str, Any]) -> str:
    """Choose one player-visible feedback type from a verified state consequence."""

    if patch.get("reveal_facts"):
        return "new_clue"
    if patch.get("relationship_delta"):
        return "companion_reaction"
    if patch.get("risk_delta"):
        return "risk_shift"
    if patch.get("flags"):
        return "task_or_record_progress"
    if patch.get("scene_id") or patch.get("beat_id"):
        return "scene_progress"
    raise DramaManagerViolation("approved primary choice has no visible feedback consequence")


def select_verified_dramatic_beat(ledger: Any, proposal: NarrativeProposal) -> DramaticBeatSelection:
    """Accept only a proposal identical to the current legal transition identity."""

    if proposal.schema != "NarrativeProposal/v1" or proposal.policy_revision != DRAMA_POLICY_REVISION:
        raise DramaManagerViolation("proposal schema or policy is unapproved")
    ledger.verify_chain()
    graph = graph_for_ledger(ledger)
    state = ledger.replay()
    campaign_id = campaign_id_for_ledger(ledger)
    if proposal.campaign_id != campaign_id or proposal.based_on_state_hash != _state_hash(state):
        raise DramaManagerViolation("proposal does not bind to the current verified campaign state")
    if not proposal.choice_intent_id.startswith("intent_"):
        raise DramaManagerViolation("proposal lacks an immutable choice-intent reference")
    legal = graph.legal_actions(state)
    transition_by_id = {transition.transition_id: transition for transition in legal}
    transition = transition_by_id.get(proposal.proposed_transition_id)
    if transition is None:
        raise DramaManagerViolation("proposal transition is not legal at the current verified beat")
    destination = str(transition.resulting_patch.get("beat_id", transition.from_beat_id))
    if proposal.candidate_beat_ids != (transition.from_beat_id, destination):
        raise DramaManagerViolation("proposal candidate beats diverge from the approved transition")
    if proposal.candidate_presentation.get("feedback_type") != feedback_type_for_patch(transition.resulting_patch):
        raise DramaManagerViolation("proposal feedback type does not match the approved consequence")
    facts_hash = _hash({"known_facts": list(state.known_facts), "relationships": dict(state.relationships), "flags": dict(state.flags)})
    material = {"campaign_id": campaign_id, "transition_id": transition.transition_id, "facts_hash": facts_hash}
    return DramaticBeatSelection(
        selection_id="selection_" + _hash(material)[:20],
        campaign_id=campaign_id,
        eligible_beat_ids=tuple(transition.from_beat_id for transition in legal),
        selected_beat_id=destination,
        selection_reason="exact_legal_transition_and_preserved_player_facts",
        preserved_player_facts_hash=facts_hash,
        policy_revision=DRAMA_POLICY_REVISION,
    )


@dataclass(frozen=True)
class ChoiceConsequenceEntry:
    transition_id: str
    changed_dimensions: tuple[str, ...]
    feedback_type: str

    def to_dict(self) -> dict[str, Any]:
        return {"transition_id": self.transition_id, "changed_dimensions": list(self.changed_dimensions), "feedback_type": self.feedback_type}


def _changed_dimensions(before: StoryState, patch: Mapping[str, Any]) -> tuple[str, ...]:
    from .ledger import apply_state_patch

    after = apply_state_patch(before, patch)
    changed: list[str] = []
    if before.scene_id != after.scene_id or before.beat_id != after.beat_id:
        changed.append("scene_or_ending_path")
    if before.known_facts != after.known_facts:
        changed.append("clue")
    if dict(before.relationships) != dict(after.relationships):
        changed.append("relationship")
    if before.risk_level != after.risk_level:
        changed.append("risk")
    if dict(before.flags) != dict(after.flags):
        changed.append("quest_or_record")
    return tuple(changed)


def primary_choice_consequence_coverage(graph: StoryGraph) -> dict[str, Any]:
    """Check every graph edge for durable consequence and visible feedback."""

    entries: list[ChoiceConsequenceEntry] = []
    for transition in graph.transitions():
        before = StoryState(transition.scene_id, transition.from_beat_id)
        changed = _changed_dimensions(before, transition.resulting_patch)
        if not changed:
            raise DramaManagerViolation("transition has no durable player consequence: " + transition.transition_id)
        entries.append(ChoiceConsequenceEntry(transition.transition_id, changed, feedback_type_for_patch(transition.resulting_patch)))
    ordered = tuple(sorted(entries, key=lambda item: item.transition_id))
    material = {"graph_revision": graph.revision, "entries": [entry.to_dict() for entry in ordered]}
    return {
        "schema": "PrimaryChoiceConsequenceCoverage/v1",
        "status": "primary_choice_consequences_verified",
        "graph_revision": graph.revision,
        "coverage_percent": 100 if ordered else 0,
        "entries": [entry.to_dict() for entry in ordered],
        "report_hash": _hash(material),
        "authority_note": "Every approved edge has a durable state difference and one source-bound visible feedback type; this report does not choose for the player.",
    }
