"""Synthetic candidate-mode ConversationEpisode adapter for the canonical W3 path.

This module deliberately contains no ChatGPT account integration, persistence
authority, or raw private conversation fixture.  It produces only the existing
candidate-only LearningPacket shape for later import by ``MemoryStore``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from .canonical import content_hash, normalize_text
from .learning_packet import build_learning_packet, conversation_atom_id


_ALLOWED_CLAIM_ROLES = {
    "USER_ASSERTION",
    "USER_PREFERENCE",
    "USER_DECISION",
    "USER_CORRECTION",
    "ASSISTANT_ANALYSIS",
    "ASSISTANT_HYPOTHESIS",
}
_PROMPT_INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt",
    "developer message",
)


@dataclass(frozen=True)
class ConversationEpisode:
    """A privacy-minimized pointer to a synthetic conversation episode."""

    episode_id: str
    user_scope: str
    project_scope: str
    source_pointer: str
    source_hash: str
    privacy_class: str
    recorded_at: str
    coverage: str = "synthetic"

    def validate(self) -> None:
        if not all((self.episode_id, self.user_scope, self.project_scope, self.source_pointer, self.source_hash)):
            raise ValueError("conversation_episode_identity_required")
        if self.privacy_class != "PUBLIC_SAFE_SYNTHETIC":
            raise ValueError("conversation_episode_private_source_denied")
        if self.coverage != "synthetic":
            raise ValueError("conversation_episode_coverage_denied")
        _normalized_instant(self.recorded_at)

    @property
    def manifest_id(self) -> str:
        self.validate()
        return "conversation-episode-" + content_hash(asdict(self))[:20]


def build_conversation_candidate(
    *,
    episode: ConversationEpisode,
    statement: str,
    claim_role: str,
    valid_from: str,
    valid_to: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic candidate packet using the existing W3 contract."""

    episode.validate()
    if claim_role not in _ALLOWED_CLAIM_ROLES:
        raise ValueError("conversation_claim_role_denied")
    if claim_role.startswith("ASSISTANT_"):
        raise ValueError("assistant_claim_cannot_be_user_memory")
    if not normalize_text(statement):
        raise ValueError("conversation_statement_required")
    if any(marker in normalize_text(statement).casefold() for marker in _PROMPT_INJECTION_MARKERS):
        raise ValueError("conversation_prompt_injection_denied")
    normalized_valid_from = _normalized_instant(valid_from)
    normalized_valid_to = _normalized_instant(valid_to) if valid_to is not None else None
    if normalized_valid_to is not None and normalized_valid_to <= normalized_valid_from:
        raise ValueError("conversation_valid_time_invalid")
    source_ref = "conversation://" + episode.manifest_id
    validation = {
        "episode_id": episode.episode_id,
        "user_scope": episode.user_scope,
        "project_scope": episode.project_scope,
        "claim_role": claim_role,
        "valid_from": normalized_valid_from,
        "valid_to": normalized_valid_to,
        "recorded_at": _normalized_instant(episode.recorded_at),
        "privacy_class": episode.privacy_class,
        "source_pointer_hash": content_hash(episode.source_pointer),
    }
    return build_learning_packet(
        source_manifest_ids=[episode.manifest_id],
        source_hash=episode.source_hash,
        validation_report=validation,
        evidence_refs=[source_ref],
        atoms=[{
            "id": conversation_atom_id(
                statement, _conversation_metadata(episode, claim_role, normalized_valid_from, normalized_valid_to)
            ),
            "statement": statement,
            "atom_type": "conversation_memory",
            "scope": episode.project_scope,
            "source_refs": [source_ref],
            "knowledge_status": "candidate",
            "memory_metadata": {"conversation": _conversation_metadata(
                episode, claim_role, normalized_valid_from, normalized_valid_to
            )},
        }],
    )


def build_conversation_correction(
    *,
    episode: ConversationEpisode,
    statement: str,
    replaces_atom_id: str,
    valid_from: str,
    valid_to: str | None = None,
) -> dict[str, Any]:
    """Append a USER_CORRECTION linked to a pre-existing candidate atom."""
    if not replaces_atom_id or len(replaces_atom_id) > 128:
        raise ValueError("conversation_correction_target_invalid")
    candidate = build_conversation_candidate(
        episode=episode,
        statement=statement,
        claim_role="USER_CORRECTION",
        valid_from=valid_from,
        valid_to=valid_to,
    )
    correction_id = candidate["atoms"][0]["id"]
    candidate["relations"] = [{
        "source_atom_id": correction_id,
        "target_atom_id": replaces_atom_id,
        "relation_type": "supersedes",
        "context": "append_preserving_user_correction",
        "target_existing": True,
    }]
    # Relations are part of the content-addressed packet; rebuild through the
    # existing builder so verification, identity, and idempotency remain exact.
    return build_learning_packet(
        source_manifest_ids=candidate["source_manifest_ids"],
        source_hash=candidate["source_hash"],
        validation_report=candidate["validation_report"],
        evidence_refs=candidate["evidence_refs"],
        atoms=candidate["atoms"],
        relations=candidate["relations"],
    )


def _conversation_metadata(
    episode: ConversationEpisode, claim_role: str, valid_from: str, valid_to: str | None
) -> dict[str, str | None]:
    return {
        "episode_manifest_id": episode.manifest_id,
        "user_scope": episode.user_scope,
        "project_scope": episode.project_scope,
        "privacy_class": episode.privacy_class,
        "claim_role": claim_role,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "recorded_at": _normalized_instant(episode.recorded_at),
    }


def _normalized_instant(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("conversation_time_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
