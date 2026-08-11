"""Synthetic candidate-mode ConversationEpisode adapter for the canonical W3 path.

This module deliberately contains no ChatGPT account integration, persistence
authority, or raw private conversation fixture.  It produces only the existing
candidate-only LearningPacket shape for later import by ``MemoryStore``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from .canonical import content_hash, normalize_text
from .learning_packet import build_learning_packet


_ALLOWED_CLAIM_ROLES = {
    "USER_ASSERTION",
    "USER_PREFERENCE",
    "USER_DECISION",
    "USER_CORRECTION",
    "ASSISTANT_ANALYSIS",
    "ASSISTANT_HYPOTHESIS",
}


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
        datetime.fromisoformat(self.recorded_at.replace("Z", "+00:00"))

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
    datetime.fromisoformat(valid_from.replace("Z", "+00:00"))
    if valid_to is not None:
        datetime.fromisoformat(valid_to.replace("Z", "+00:00"))
    source_ref = "conversation://" + episode.manifest_id
    validation = {
        "episode_id": episode.episode_id,
        "user_scope": episode.user_scope,
        "project_scope": episode.project_scope,
        "claim_role": claim_role,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "recorded_at": episode.recorded_at,
        "privacy_class": episode.privacy_class,
        "source_pointer_hash": content_hash(episode.source_pointer),
    }
    return build_learning_packet(
        source_manifest_ids=[episode.manifest_id],
        source_hash=episode.source_hash,
        validation_report=validation,
        evidence_refs=[source_ref],
        atoms=[{
            "statement": statement,
            "atom_type": "conversation_memory",
            "scope": episode.project_scope,
            "source_refs": [source_ref],
            "knowledge_status": "candidate",
        }],
    )
