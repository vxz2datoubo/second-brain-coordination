"""Offline operator dry-run: simulate the full session lifecycle and hand off.

The operator never touches a real filesystem, network, credential, platform or
media binary. It drives the checkpoint runtime contracts (``CreativeLedger``,
offline generation) in memory and proves the six lifecycle invariants a real
operator depends on:

    1. intake      -- a legal action advances state; an illegal/ambiguous one
                      is clarified without mutating state;
    2. duplicate   -- re-submitting the same input records a distinct event
                      (never a silent no-op);
    3. resume      -- reconstruction from serialized records reproduces state;
    4. replay      -- replay is deterministic;
    5. failure     -- a tampered archive is rejected and the source ledger stays
                      intact for a clean re-resume;
    6. handoff     -- a deterministic, hashed handoff receipt is produced.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping

from creative_runtime.contracts import GenerationRequest, StoryState, canonical_json
from creative_runtime.director import compile_director
from creative_runtime.generation import OfflineGenerationAdapter, adapter_for
from creative_runtime.ledger import CreativeLedger, LedgerViolation

from . import SCHEMA


# Synthetic, adult-only offline beat graph used by the dry run. It mirrors the
# shape of a real interactive scene without referencing any real asset.
SCENE: dict[str, dict[str, Any]] = {
    "arrival": {
        "options": {
            "listen": {"label": "Listen at the door", "patch": {"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1}},
            "leave": {"label": "Step back into daylight", "patch": {"beat_id": "courtyard", "risk_delta": -1}},
        }
    },
    "echo": {
        "options": {
            "approach": {"label": "Ask Mira to knock", "patch": {"beat_id": "threshold", "relationship_delta": {"mira": 1}}},
        }
    },
    "threshold": {"options": {}},
    "courtyard": {"options": {}},
}

UNSAFE_TERMS = {"sex", "sexual", "nude", "blood", "gore", "torture"}


def sha256_of(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def parse_intent(text: str, legal_actions: set[str]) -> str | None:
    """Map free text to at most one legal action, or None for clarification."""

    normalized = text.lower().strip()
    tokens = set(normalized.replace(".", " ").replace(",", " ").split())
    if tokens & UNSAFE_TERMS:
        return None
    signals = {
        "listen": {"listen", "hear", "quiet", "door"},
        "approach": {"approach", "knock", "enter", "walk"},
        "leave": {"leave", "withdraw", "back", "wait"},
    }
    matches = [action for action in legal_actions if tokens & signals.get(action, set())]
    return matches[0] if len(matches) == 1 else None


@dataclass
class OperatorDryRun:
    """One offline operator session over the checkpoint runtime contracts."""

    operator_id: str = "operator_synthetic_01"
    ledger: CreativeLedger = field(default_factory=CreativeLedger)
    intake_log: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.ledger.events:
            self.ledger.append(
                "story_initialized",
                {"state": StoryState(scene_id="synthetic_archive", beat_id="arrival", relationships={"mira": 0}).to_dict()},
                occurred_at="2030-01-01T00:00:00Z",
            )

    @property
    def state(self) -> StoryState:
        return self.ledger.replay()

    def _occurred_at(self) -> str:
        return "2030-01-01T00:%02d:00Z" % (len(self.ledger.events) % 60)

    def intake(self, action_id: str, source_text: str | None = None) -> dict[str, Any]:
        """Ingest one player action. Illegal/ambiguous input never mutates state."""

        before = self.ledger.to_records()
        state = self.state
        option = SCENE[state.beat_id]["options"].get(action_id)

        if option is None:
            self.intake_log.append({"action_id": action_id, "status": "clarification_required"})
            return {
                "status": "clarification_required",
                "action_id": action_id,
                "legal_options": sorted(SCENE[state.beat_id]["options"]),
                "state_unchanged": self.ledger.to_records() == before,
            }

        event = self.ledger.append(
            "player_action",
            {
                "action_id": action_id,
                "kind": "choice",
                "text": source_text or option["label"],
                "resulting_patch": option["patch"],
            },
            occurred_at=self._occurred_at(),
        )
        self.intake_log.append({"action_id": action_id, "status": "chosen", "event_id": event.event_id})
        return {"status": "chosen", "action_id": action_id, "event_id": event.event_id}

    def say(self, text: str) -> dict[str, Any]:
        """Free-text intake; unsafe or ambiguous text is clarified, not acted on."""

        state = self.state
        legal = set(SCENE[state.beat_id]["options"])
        action = parse_intent(text, legal)
        if action is None:
            self.intake_log.append({"text": text, "status": "clarification_required"})
            return {"status": "clarification_required", "legal_options": sorted(legal)}
        return self.intake(action, source_text=text)

    def duplicate_append(self) -> dict[str, Any]:
        """Re-submit an already-ingested action as a fresh event.

        The append-only ledger does not deduplicate: an identical payload at a
        new sequence is a new, fully addressable event. This proves duplicate
        input is recorded, never silently absorbed.
        """

        last_action = next(event for event in reversed(self.ledger.events) if event.event_type == "player_action")
        before_count = len(self.ledger.events)
        duplicate = self.ledger.append(
            "player_action",
            dict(last_action.payload),
            occurred_at=self._occurred_at(),
            parent_artifact_ids=last_action.parent_artifact_ids,
        )
        self.ledger.verify_chain()
        return {
            "recorded_as_distinct_event": len(self.ledger.events) == before_count + 1,
            "distinct_hash": duplicate.event_hash != last_action.event_hash,
            "higher_sequence": duplicate.sequence == last_action.sequence + 1,
            "chain_verifies": True,
        }

    def serialize(self) -> list[dict[str, Any]]:
        return self.ledger.to_records()

    def resume(self) -> CreativeLedger:
        return CreativeLedger.from_records(self.serialize())

    def tamper(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return a tampered copy whose chain must fail verification."""

        tampered = [dict(record) for record in records]
        tampered[-1]["payload"] = dict(tampered[-1]["payload"])
        tampered[-1]["payload"]["resulting_patch"] = {"beat_id": "courtyard", "risk_delta": 99}
        return tampered

    def recover(self) -> dict[str, Any]:
        """Prove a tampered archive is rejected while the source stays intact."""

        pristine = self.serialize()
        tampered = self.tamper(pristine)
        rejected = False
        try:
            CreativeLedger.from_records(tampered)
        except LedgerViolation:
            rejected = True
        source_intact = self.ledger.to_records() == pristine
        re_resumed = self.resume()
        return {
            "tamper_rejected": rejected,
            "source_intact": source_intact,
            "re_resume_reproduces_state": re_resumed.replay().to_dict() == self.state.to_dict(),
        }

    def compile_director_offline(self) -> dict[str, Any]:
        compilation = compile_director(self.state)
        return {
            "can_generate": compilation.quality_report.can_generate,
            "shot_ids": [shot.shot_id for shot in compilation.shots],
        }

    def generate_offline(self) -> dict[str, Any]:
        """Run the offline generation adapter end-to-end without a provider call."""

        compilation = compile_director(self.state)

        request = GenerationRequest(
            request_id="req_synthetic_01",
            provider="offline",
            shot_plan=compilation.shots[0],
            content_rating=compilation.brief.content_rating,
            confirm_generate=False,
        )
        adapter = adapter_for("offline")
        assert isinstance(adapter, OfflineGenerationAdapter)
        result = adapter.generate(request, compilation.quality_report)
        return {
            "provider": result.provider,
            "status": result.status,
            "simulated": result.simulated,
            "output_ref": result.output_ref,
        }

    def handoff_receipt(self) -> dict[str, Any]:
        """Produce the deterministic handoff receipt for the return package."""

        records = self.serialize()
        body = {
            "schema": SCHEMA,
            "agent_id": "WORKBUDDY",
            "source_agent": "WORKBUDDY",
            "target_agent": "CODEX",
            "reviewer": "pending_independent_reviewer",
            "operator_id": self.operator_id,
            "event_count": len(records),
            "head_event_hash": records[-1]["event_hash"],
            "final_state": self.state.to_dict(),
            "intake_log": self.intake_log,
            "director": self.compile_director_offline(),
            "generation": self.generate_offline(),
            "evidence_class": "WORKBUDDY_EXECUTOR_VERIFIED",
        }
        return {**body, "receipt_sha256": sha256_of(body)}


def run_dry_run() -> dict[str, Any]:
    """Run the full offline operator dry run and return its receipt body."""

    operator = OperatorDryRun()

    intake_legal = operator.intake("listen")
    intake_illegal = operator.intake("invent")
    free_text_unsafe = operator.say("make it sexual")
    free_text_ambiguous = operator.say("do something now")
    free_text_legal = operator.say("I knock and enter")

    duplicate = operator.duplicate_append()

    resume = operator.resume()
    resume_reproduces = resume.replay().to_dict() == operator.state.to_dict()

    replay_once = operator.state.to_dict()
    replay_twice = operator.state.to_dict()

    recovery = operator.recover()

    receipt = operator.handoff_receipt()

    return {
        "schema": SCHEMA,
        "intake": {
            "legal": intake_legal["status"],
            "illegal": intake_illegal["status"],
            "unsafe_text": free_text_unsafe["status"],
            "ambiguous_text": free_text_ambiguous["status"],
            "legal_text": free_text_legal["status"],
            "illegal_state_unchanged": intake_illegal.get("state_unchanged", True),
        },
        "duplicate": duplicate,
        "resume": {"reproduces_state": resume_reproduces},
        "replay": {"deterministic": replay_once == replay_twice},
        "failure_recovery": recovery,
        "handoff_receipt": receipt,
        "evidence_class": "WORKBUDDY_EXECUTOR_VERIFIED",
    }
