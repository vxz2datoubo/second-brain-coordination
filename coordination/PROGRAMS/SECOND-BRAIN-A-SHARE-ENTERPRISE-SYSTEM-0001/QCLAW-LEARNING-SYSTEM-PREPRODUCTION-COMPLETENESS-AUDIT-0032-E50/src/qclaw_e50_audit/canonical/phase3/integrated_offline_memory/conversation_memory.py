# VENDORED SNAPSHOT (do not edit) — origin/main path: coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/conversation_memory.py
"""Candidate-mode ConversationEpisode adapter for the canonical W3 path.

This module deliberately contains no ChatGPT account integration or formal
persistence authority. Public fixtures remain synthetic; an explicitly
classified private/local episode is handled only by the local ingestion
boundary and produces the existing candidate-only LearningPacket shape.
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
_SOURCE_CLASSIFICATIONS = {
    ("PUBLIC_SAFE_SYNTHETIC", "synthetic"): "SYNTHETIC_PUBLIC_SAFE",
    ("PRIVATE_LOCAL_CANDIDATE", "private_local"): "PRIVATE_LOCAL_AUTHORIZED",
}


@dataclass(frozen=True)
class ConversationEpisode:
    """A privacy-minimized pointer to a classified conversation episode.

    ``source_pointer`` derives a manifest identity and pointer hash only; it is
    not placed in packet metadata or a public receipt.
    """

    episode_id: str
    user_scope: str
    project_scope: str
    source_pointer: str
    source_hash: str
    privacy_class: str
    recorded_at: str
    coverage: str = "synthetic"
    source_class: str = "SYNTHETIC_PUBLIC_SAFE"
    valid_time: str | None = None
    provenance_quality: str = "UNKNOWN"

    def validate(self) -> None:
        if not all((self.episode_id, self.user_scope, self.project_scope, self.source_pointer, self.source_hash)):
            raise ValueError("conversation_episode_identity_required")
        expected_class = _SOURCE_CLASSIFICATIONS.get((self.privacy_class, self.coverage))
        if expected_class is None and self.privacy_class == "SECRET_CREDENTIAL":
            raise ValueError("conversation_episode_private_source_denied")
        if expected_class is None or self.source_class != expected_class:
            raise ValueError("conversation_episode_source_classification_denied")
        _normalized_instant(self.recorded_at)
        if self.valid_time is not None:
            _normalized_instant(self.valid_time)
        if not isinstance(self.provenance_quality, str) or not normalize_text(self.provenance_quality):
            raise ValueError("conversation_episode_provenance_quality_required")

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
    additional_episodes: tuple[ConversationEpisode, ...] = (),
    external_candidate_id: str | None = None,
    candidate_confidence: float | None = None,
) -> dict[str, Any]:
    """Build a deterministic candidate packet using the existing W3 contract."""

    episode.validate()
    for related_episode in additional_episodes:
        related_episode.validate()
        if (
            related_episode.user_scope != episode.user_scope
            or related_episode.project_scope != episode.project_scope
            or related_episode.privacy_class != episode.privacy_class
        ):
            raise ValueError("conversation_related_episode_scope_or_privacy_denied")
    if claim_role not in _ALLOWED_CLAIM_ROLES:
        raise ValueError("conversation_claim_role_denied")
    if claim_role.startswith("ASSISTANT_"):
        raise ValueError("assistant_claim_cannot_be_user_memory")
    if not normalize_text(statement):
        raise ValueError("conversation_statement_required")
    if any(marker in normalize_text(statement).casefold() for marker in _PROMPT_INJECTION_MARKERS):
        raise ValueError("conversation_prompt_injection_denied")
    if external_candidate_id is not None and (not isinstance(external_candidate_id, str) or not normalize_text(external_candidate_id)):
        raise ValueError("conversation_external_candidate_identity_invalid")
    if candidate_confidence is not None and (
        not isinstance(candidate_confidence, (int, float)) or isinstance(candidate_confidence, bool)
        or not 0.0 <= float(candidate_confidence) <= 1.0
    ):
        raise ValueError("conversation_candidate_confidence_invalid")
    normalized_valid_from = _normalized_instant(valid_from)
    normalized_valid_to = _normalized_instant(valid_to) if valid_to is not None else None
    if normalized_valid_to is not None and normalized_valid_to <= normalized_valid_from:
        raise ValueError("conversation_valid_time_invalid")
    all_episodes = (episode, *additional_episodes)
    source_manifest_ids = sorted(item.manifest_id for item in all_episodes)
    evidence_refs = ["conversation://" + manifest_id for manifest_id in source_manifest_ids]
    source_ref = evidence_refs[0]
    validation = {
        "episode_id": episode.episode_id,
        "user_scope": episode.user_scope,
        "project_scope": episode.project_scope,
        "claim_role": claim_role,
        "valid_from": normalized_valid_from,
        "valid_to": normalized_valid_to,
        "recorded_at": _normalized_instant(episode.recorded_at),
        "privacy_class": episode.privacy_class,
        "coverage": episode.coverage,
        "source_class": episode.source_class,
        "source_pointer_hash": content_hash(episode.source_pointer),
        "source_episode_manifest_ids": sorted(source_manifest_ids),
        "source_pointer_hashes": [content_hash(item.source_pointer) for item in all_episodes],
        "source_episodes": _source_episode_provenance(all_episodes),
        "daily_candidate_id_hash": content_hash(external_candidate_id) if external_candidate_id else None,
        "daily_candidate_id_hashes": [content_hash(external_candidate_id)] if external_candidate_id else [],
        "candidate_confidence": float(candidate_confidence) if candidate_confidence is not None else None,
    }
    return build_learning_packet(
        source_manifest_ids=source_manifest_ids,
        source_hash=content_hash([item.source_hash for item in all_episodes]),
        validation_report=validation,
        evidence_refs=evidence_refs,
        atoms=[{
            "id": conversation_atom_id(
                statement, _conversation_metadata(
                    episode, claim_role, normalized_valid_from, normalized_valid_to, additional_episodes,
                    external_candidate_id, candidate_confidence,
                )
            ),
            "statement": statement,
            "atom_type": "conversation_memory",
            "scope": episode.project_scope,
            "confidence": float(candidate_confidence) if candidate_confidence is not None else 0.5,
            "source_refs": evidence_refs,
            "knowledge_status": "candidate",
            "transport_visibility": (
                "LOCAL_PRIVATE_CANDIDATE_ONLY"
                if episode.privacy_class == "PRIVATE_LOCAL_CANDIDATE"
                else "PUBLIC_SAFE_METADATA_ONLY"
            ),
            "memory_metadata": {"conversation": _conversation_metadata(
                episode, claim_role, normalized_valid_from, normalized_valid_to, additional_episodes,
                external_candidate_id, candidate_confidence,
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
    additional_episodes: tuple[ConversationEpisode, ...] = (),
    correction_context: str = "append_preserving_user_correction",
    external_candidate_id: str | None = None,
    candidate_confidence: float | None = None,
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
        additional_episodes=additional_episodes,
        external_candidate_id=external_candidate_id,
        candidate_confidence=candidate_confidence,
    )
    correction_id = candidate["atoms"][0]["id"]
    candidate["relations"] = [{
        "source_atom_id": correction_id,
        "target_atom_id": replaces_atom_id,
        "relation_type": "supersedes",
        "context": correction_context,
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
    episode: ConversationEpisode,
    claim_role: str,
    valid_from: str,
    valid_to: str | None,
    additional_episodes: tuple[ConversationEpisode, ...] = (),
    external_candidate_id: str | None = None,
    candidate_confidence: float | None = None,
) -> dict[str, Any]:
    return {
        "episode_manifest_id": episode.manifest_id,
        "user_scope": episode.user_scope,
        "project_scope": episode.project_scope,
        "privacy_class": episode.privacy_class,
        "coverage": episode.coverage,
        "source_class": episode.source_class,
        "claim_role": claim_role,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "recorded_at": _normalized_instant(episode.recorded_at),
        "source_episode_manifest_ids": sorted(
            item.manifest_id for item in (episode, *additional_episodes)
        ),
        "source_episodes": _source_episode_provenance((episode, *additional_episodes)),
        "daily_candidate_id_hash": content_hash(external_candidate_id) if external_candidate_id else None,
        "daily_candidate_id_hashes": [content_hash(external_candidate_id)] if external_candidate_id else [],
        "candidate_confidence": float(candidate_confidence) if candidate_confidence is not None else None,
    }


def _source_episode_provenance(
    episodes: tuple[ConversationEpisode, ...],
) -> list[dict[str, str]]:
    """Return privacy-minimized per-episode lineage for packet/bundle audit."""

    return sorted(({
        "episode_manifest_id": item.manifest_id,
        "episode_id": item.episode_id,
        "source_pointer_hash": content_hash(item.source_pointer),
        "recorded_at": _normalized_instant(item.recorded_at),
        "valid_time": _normalized_instant(item.valid_time or item.recorded_at),
        "provenance_quality": item.provenance_quality,
    } for item in episodes), key=lambda item: item["episode_manifest_id"])


def _normalized_instant(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("conversation_time_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
