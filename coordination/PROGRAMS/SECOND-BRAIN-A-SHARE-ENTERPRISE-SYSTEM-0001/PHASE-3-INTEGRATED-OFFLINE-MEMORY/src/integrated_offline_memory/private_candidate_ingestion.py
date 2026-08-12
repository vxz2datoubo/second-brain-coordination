"""Local-only bridge for authorized Daily Memory Candidate v2 inputs.

This is intentionally a narrow data-plane adapter. It accepts one validated
private/local candidate package, reuses ConversationEpisode -> LearningPacket
-> MemoryStore, and emits a receipt whose public form contains only hashes,
counts, timestamps, and status. It creates neither a second memory authority
nor a formal-persistence path.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .canonical import content_hash, normalize_text
from .conversation_memory import ConversationEpisode, build_conversation_candidate
from .memory_store import MemoryStore
from .retrieval import ContextAssembler, QueryPlan


DAILY_MEMORY_CANDIDATE_V2 = "DailyMemoryCandidate-v2"
PRIVATE_LOCAL_CANDIDATE = "PRIVATE_LOCAL_CANDIDATE"
PRIVATE_SOURCE_BINDING_WAITING = "PRIVATE_SOURCE_BINDING_WAITING"
_REQUIRED_FIELDS = {
    "schema_version",
    "candidate_id",
    "source_pointer",
    "source_hash",
    "user_scope",
    "project_scope",
    "statement",
    "claim_role",
    "valid_from",
    "recorded_at",
}
_OPTIONAL_FIELDS = {"valid_to"}
_SECRET = re.compile(
    r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)


@dataclass(frozen=True)
class PrivateCandidateIngestionResult:
    """Local result; public_receipt is safe for public task evidence."""

    import_result: dict[str, Any]
    packet: dict[str, Any]
    recall_count: int

    def public_receipt(self) -> dict[str, Any]:
        conversation = self.packet["atoms"][0]["memory_metadata"]["conversation"]
        return {
            "schema_version": "1.0",
            "status": self.import_result["status"],
            "validation_status": "PASS",
            "candidate_authority_only": True,
            "formal_project_global_write": "LOCKED",
            "source_hash": self.packet["source_hash"],
            "pointer_hash": self.packet["validation_report"]["source_pointer_hash"],
            "episode_id_hash": content_hash(self.packet["validation_report"]["episode_id"]),
            "atom_id_hash": content_hash(self.packet["atoms"][0]["id"]),
            "scope_hash": content_hash({
                "user_scope": conversation["user_scope"],
                "project_scope": conversation["project_scope"],
            }),
            "candidate_count": len(self.packet["atoms"]),
            "recall_count": self.recall_count,
            "recorded_at": conversation["recorded_at"],
        }


def build_private_daily_memory_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one private/local Candidate v2 mapping and build a W3 packet.

    Values in payload are local-only. Callers must never publish this mapping,
    the resulting packet, or a database holding it to public GitHub.
    """

    normalized = _validate_payload(payload)
    episode = ConversationEpisode(
        episode_id=normalized["candidate_id"],
        user_scope=normalized["user_scope"],
        project_scope=normalized["project_scope"],
        source_pointer=normalized["source_pointer"],
        source_hash=normalized["source_hash"],
        privacy_class=PRIVATE_LOCAL_CANDIDATE,
        recorded_at=normalized["recorded_at"],
        coverage="private_local",
        source_class="PRIVATE_LOCAL_AUTHORIZED",
    )
    return build_conversation_candidate(
        episode=episode,
        statement=normalized["statement"],
        claim_role=normalized["claim_role"],
        valid_from=normalized["valid_from"],
        valid_to=normalized.get("valid_to"),
    )


def ingest_private_daily_memory_candidate(
    payload: Mapping[str, Any],
    store: MemoryStore,
    *,
    verify_scoped_recall: bool = True,
) -> PrivateCandidateIngestionResult:
    """Import through the existing store and optionally use existing recall."""

    normalized = _validate_payload(payload)
    packet = build_private_daily_memory_candidate(normalized)
    import_result = store.import_learning_packet(packet)
    recall_count = 0
    if verify_scoped_recall:
        bundle = ContextAssembler(store).assemble(QueryPlan(
            query_text=normalized["statement"],
            scopes=(normalized["project_scope"],),
            user_scope=normalized["user_scope"],
            valid_at=normalized["valid_from"],
            truth_states=("candidate",),
        ))
        recall_count = len(bundle.atoms)
    return PrivateCandidateIngestionResult(import_result, packet, recall_count)


def load_private_daily_memory_candidate_v2(path: Path) -> dict[str, Any]:
    """Read an explicitly supplied local package without echoing its path."""

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("private_candidate_source_unavailable_or_invalid") from error
    if not isinstance(loaded, dict):
        raise ValueError("private_candidate_mapping_required")
    return _validate_payload(loaded)


def private_source_binding_status(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    """Report availability only; never reveal a configured private path."""

    env = os.environ if environment is None else environment
    if not env.get("CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH"):
        return {
            "status": PRIVATE_SOURCE_BINDING_WAITING,
            "missing_capability": "CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH local transport binding",
        }
    return {"status": "PRIVATE_SOURCE_BINDING_CONFIGURED"}


def ingest_configured_private_canary(store: MemoryStore) -> PrivateCandidateIngestionResult | dict[str, str]:
    """Run one canary only when an explicit source binding exists."""

    status = private_source_binding_status()
    if status["status"] == PRIVATE_SOURCE_BINDING_WAITING:
        return status
    path = Path(os.environ["CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH"])
    payload = load_private_daily_memory_candidate_v2(path)
    return ingest_private_daily_memory_candidate(payload, store, verify_scoped_recall=True)


def _validate_payload(payload: Mapping[str, Any]) -> dict[str, str | None]:
    if not isinstance(payload, Mapping):
        raise ValueError("private_candidate_mapping_required")
    unknown = set(payload) - _REQUIRED_FIELDS - _OPTIONAL_FIELDS
    if unknown or _REQUIRED_FIELDS - set(payload):
        raise ValueError("private_candidate_schema_invalid")
    if payload.get("schema_version") != DAILY_MEMORY_CANDIDATE_V2:
        raise ValueError("private_candidate_schema_version_denied")

    normalized: dict[str, str | None] = {"schema_version": DAILY_MEMORY_CANDIDATE_V2}
    limits = {
        "candidate_id": 128,
        "source_pointer": 4096,
        "user_scope": 256,
        "project_scope": 256,
        "statement": 8192,
        "claim_role": 64,
        "valid_from": 64,
        "recorded_at": 64,
        "valid_to": 64,
    }
    for field in _REQUIRED_FIELDS - {"schema_version", "source_hash"}:
        value = payload.get(field)
        if not isinstance(value, str) or not normalize_text(value) or len(value) > limits[field]:
            raise ValueError("private_candidate_field_invalid")
        normalized[field] = value
    source_hash = payload.get("source_hash")
    if not isinstance(source_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", source_hash):
        raise ValueError("private_candidate_source_hash_invalid")
    normalized["source_hash"] = source_hash
    valid_to = payload.get("valid_to")
    if valid_to is not None:
        if not isinstance(valid_to, str) or not normalize_text(valid_to) or len(valid_to) > limits["valid_to"]:
            raise ValueError("private_candidate_field_invalid")
        normalized["valid_to"] = valid_to
    if any(_SECRET.search(value or "") for value in normalized.values()):
        raise ValueError("credential_value_denied")
    return normalized
