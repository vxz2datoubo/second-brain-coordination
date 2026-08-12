"""Local-only adapter from layered Daily Memory Candidate v2 into W3.

The outer DailyMemoryCandidate-v2 package is distinct from the inner
W3PrivateCandidateEnvelope-v1. The adapter validates coverage, episodes,
candidates, projection and validation before using the existing
ConversationEpisode -> LearningPacket -> MemoryStore -> QueryPlan path.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical import content_hash, normalize_text
from .conversation_memory import ConversationEpisode, build_conversation_candidate
from .memory_store import MemoryStore
from .retrieval import ContextAssembler, QueryPlan


DAILY_MEMORY_CANDIDATE_V2 = "DailyMemoryCandidate-v2"
W3_PRIVATE_CANDIDATE_ENVELOPE_V1 = "W3PrivateCandidateEnvelope-v1"
PRIVATE_LOCAL_CANDIDATE = "PRIVATE_LOCAL_CANDIDATE"
PRIVATE_SOURCE_BINDING_WAITING = "PRIVATE_SOURCE_BINDING_WAITING"
PRIVATE_SOURCE_BINDING_REJECTED = "PRIVATE_SOURCE_BINDING_REJECTED"
PRIVATE_SOURCE_BINDING_CONFIGURED = "PRIVATE_SOURCE_BINDING_CONFIGURED"
_PRIVATE_ROOT_ENV = "CLTM_PRIVATE_DATA_ROOT"
_PRIVATE_PACKAGE_ENV = "CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH"
_USER_MEMORY_TYPES = {
    "USER_ASSERTION": "USER_ASSERTION",
    "USER_PREFERENCE": "USER_PREFERENCE",
    "USER_DECISION": "USER_DECISION",
    "USER_CORRECTION": "USER_CORRECTION",
}
_ALLOWED_SENSITIVITY = {"PRIVATE_OR_SENSITIVE", "PRIVATE_LOCAL_CANDIDATE"}
_DENIED_SENSITIVITY = {
    "SECRET_CREDENTIAL", "AUTHENTICATION_SECRET", "PASSWORD", "API_KEY",
    "TOKEN", "COOKIE", "SESSION_CREDENTIAL", "MFA_OTP", "RECOVERY_CODE",
    "PAYMENT_CREDENTIAL", "BANK_CREDENTIAL", "BROKER_CREDENTIAL",
}
_SECRET = re.compile(
    r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)
_PACKAGE_KEYS = {
    "schema_version", "COVERAGE", "CONVERSATION_EPISODES",
    "MEMORY_CANDIDATES", "DERIVED_DAILY_PROJECTION", "VALIDATION",
}
_ENVELOPE_KEYS = {
    "schema_version", "candidate_id", "user_scope", "project_scope",
    "statement", "claim_role", "valid_from", "recorded_at",
    "source_episodes", "upstream_validation_status", "sensitivity_class",
    "valid_to",
}


@dataclass(frozen=True)
class PrivateCandidateIngestionResult:
    import_results: tuple[dict[str, Any], ...]
    packets: tuple[dict[str, Any], ...]
    recalled_atom_ids: tuple[str, ...]

    @property
    def exact_imported_atom_recalled(self) -> bool:
        expected = {atom["id"] for packet in self.packets for atom in packet["atoms"]}
        return bool(expected) and expected.issubset(set(self.recalled_atom_ids))

    def public_receipt(self) -> dict[str, Any]:
        packet = self.packets[0]
        conversation = packet["atoms"][0]["memory_metadata"]["conversation"]
        return {
            "schema_version": "1.0",
            "status": "IMPORTED",
            "validation_status": "PASS",
            "candidate_authority_only": True,
            "formal_project_global_write": "LOCKED",
            "source_hash": packet["source_hash"],
            "pointer_hash": packet["validation_report"]["source_pointer_hash"],
            "episode_id_hash": content_hash(packet["validation_report"]["episode_id"]),
            "atom_id_hash": content_hash(packet["atoms"][0]["id"]),
            "scope_hash": content_hash({
                "user_scope": conversation["user_scope"],
                "project_scope": conversation["project_scope"],
            }),
            "candidate_count": len(self.packets),
            "recall_count": len(self.recalled_atom_ids),
            "exact_imported_atom_recalled": self.exact_imported_atom_recalled,
            "recorded_at": conversation["recorded_at"],
        }


def daily_v2_package_to_w3_private_envelopes(package: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Validate a layered package and map eligible user candidates only."""

    _require_exact_keys(package, _PACKAGE_KEYS, "daily_v2_package_schema_invalid")
    if package.get("schema_version") != DAILY_MEMORY_CANDIDATE_V2:
        raise ValueError("daily_v2_schema_version_denied")
    coverage = _mapping(package["COVERAGE"], "daily_v2_coverage_invalid")
    episodes = _sequence_of_mappings(package["CONVERSATION_EPISODES"], "daily_v2_episodes_invalid")
    candidates = _sequence_of_mappings(package["MEMORY_CANDIDATES"], "daily_v2_candidates_invalid")
    projection = _mapping(package["DERIVED_DAILY_PROJECTION"], "daily_v2_projection_invalid")
    validation = _mapping(package["VALIDATION"], "daily_v2_validation_invalid")
    _validate_coverage(coverage, episodes)
    episodes_by_id = _validate_episodes(episodes)
    _validate_projection(projection, candidates)
    accepted, sensitivity = _validate_validation(validation, candidates)

    envelopes: list[dict[str, Any]] = []
    candidate_ids = {candidate.get("candidate_id") for candidate in candidates}
    for rejected in validation["rejected_candidates"]:
        if not isinstance(rejected, Mapping) or rejected.get("candidate_id") not in candidate_ids:
            raise ValueError("daily_v2_rejected_candidate_invalid")
    for candidate in candidates:
        if candidate.get("candidate_id") not in accepted:
            continue
        _require_exact_keys(
            candidate,
            {
                "candidate_id", "candidate_type", "statement", "source_episode_ids",
                "valid_from", "recorded_at", "sensitivity_class", "valid_to",
            },
            "daily_v2_candidate_schema_invalid",
        )
        candidate_type = candidate.get("candidate_type")
        if candidate_type not in _USER_MEMORY_TYPES:
            raise ValueError("daily_v2_non_user_candidate_denied")
        if candidate.get("sensitivity_class") != sensitivity.get(candidate["candidate_id"]):
            raise ValueError("daily_v2_sensitivity_mismatch")
        _validate_sensitivity(candidate["sensitivity_class"])
        source_ids = candidate.get("source_episode_ids")
        if not isinstance(source_ids, list) or not source_ids or len(source_ids) != len(set(source_ids)):
            raise ValueError("daily_v2_candidate_provenance_invalid")
        try:
            source_episodes = [episodes_by_id[item] for item in source_ids]
        except KeyError as error:
            raise ValueError("daily_v2_candidate_episode_missing") from error
        if any(item["actor_type"] != "USER" for item in source_episodes):
            raise ValueError("daily_v2_candidate_actor_denied")
        envelope = {
            "schema_version": W3_PRIVATE_CANDIDATE_ENVELOPE_V1,
            "candidate_id": candidate["candidate_id"],
            "user_scope": coverage["user_scope"],
            "project_scope": coverage["project_scope"],
            "statement": candidate["statement"],
            "claim_role": _USER_MEMORY_TYPES[candidate_type],
            "valid_from": candidate["valid_from"],
            "valid_to": candidate["valid_to"],
            "recorded_at": candidate["recorded_at"],
            "source_episodes": source_episodes,
            "upstream_validation_status": "VALIDATED",
            "sensitivity_class": candidate["sensitivity_class"],
        }
        _validate_w3_private_envelope(envelope)
        envelopes.append(envelope)
    if not envelopes:
        raise ValueError("daily_v2_no_eligible_user_memory_candidates")
    return envelopes


def build_private_w3_candidate_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Build one existing canonical W3 packet from a validated inner envelope."""

    normalized = _validate_w3_private_envelope(envelope)
    episode_models = tuple(
        ConversationEpisode(
            episode_id=episode["episode_id"],
            user_scope=normalized["user_scope"],
            project_scope=normalized["project_scope"],
            source_pointer=episode["source_pointer"],
            source_hash=episode["source_hash"],
            privacy_class=PRIVATE_LOCAL_CANDIDATE,
            recorded_at=episode["recorded_at"],
            coverage="private_local",
            source_class="PRIVATE_LOCAL_AUTHORIZED",
        )
        for episode in normalized["source_episodes"]
    )
    return build_conversation_candidate(
        episode=episode_models[0],
        additional_episodes=episode_models[1:],
        statement=normalized["statement"],
        claim_role=normalized["claim_role"],
        valid_from=normalized["valid_from"],
        valid_to=normalized.get("valid_to"),
    )


def ingest_daily_memory_candidate_v2(
    package: Mapping[str, Any],
    store: MemoryStore,
    *,
    context_assembler: ContextAssembler | None = None,
) -> PrivateCandidateIngestionResult:
    """Import through W3 and prove every exact imported atom was recalled."""

    envelopes = daily_v2_package_to_w3_private_envelopes(package)
    packets = tuple(build_private_w3_candidate_envelope(envelope) for envelope in envelopes)
    import_results = tuple(store.import_learning_packet(packet) for packet in packets)
    assembler = context_assembler or ContextAssembler(store)
    recalled: set[str] = set()
    for envelope, packet in zip(envelopes, packets):
        bundle = assembler.assemble(QueryPlan(
            query_text=envelope["statement"],
            scopes=(envelope["project_scope"],),
            user_scope=envelope["user_scope"],
            valid_at=envelope["valid_from"],
            truth_states=("candidate",),
        ))
        current = {atom["id"] for atom in bundle.atoms}
        recalled.update(current)
        expected = {atom["id"] for atom in packet["atoms"]}
        if not expected.issubset(current):
            raise ValueError("private_candidate_exact_recall_not_proven")
    return PrivateCandidateIngestionResult(import_results, packets, tuple(sorted(recalled)))


def validate_private_data_paths(input_path: Path, store_path: Path, private_root: Path) -> tuple[Path, Path, Path]:
    """Fail closed unless input and persistent store are under private root."""

    root = private_root.expanduser().resolve(strict=False)
    input_resolved = input_path.expanduser().resolve(strict=False)
    store_resolved = store_path.expanduser().resolve(strict=False)
    public_root = _public_repository_root()
    if not root.exists() or not root.is_dir() or _is_within(root, public_root):
        raise ValueError("private_data_root_invalid")
    if (
        not _is_within(input_resolved, root)
        or not _is_within(store_resolved, root)
        or _is_within(input_resolved, public_root)
        or _is_within(store_resolved, public_root)
    ):
        raise ValueError("private_data_path_policy_denied")
    return input_resolved, store_resolved, root


def load_daily_memory_candidate_v2(path: Path, private_root: Path) -> dict[str, Any]:
    """Load an admitted local package without including a path in errors."""

    input_path, _, _ = validate_private_data_paths(path, path.with_suffix(".probe"), private_root)
    try:
        loaded = json.loads(input_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError("private_candidate_source_unavailable") from error
    except json.JSONDecodeError as error:
        raise ValueError("private_candidate_source_invalid") from error
    if not isinstance(loaded, dict):
        raise ValueError("private_candidate_mapping_required")
    daily_v2_package_to_w3_private_envelopes(loaded)
    return loaded


def private_source_binding_status(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return waiting, rejected, or configured without leaking a path."""

    env = os.environ if environment is None else environment
    root_value = env.get(_PRIVATE_ROOT_ENV)
    source_value = env.get(_PRIVATE_PACKAGE_ENV)
    if not root_value or not source_value:
        return {
            "status": PRIVATE_SOURCE_BINDING_WAITING,
            "reason": "explicit private data-root and Candidate v2 transport binding required",
        }
    try:
        root = Path(root_value)
        source = Path(source_value)
        input_path, _, _ = validate_private_data_paths(source, source.with_suffix(".probe"), root)
        if not input_path.is_file() or not os.access(input_path, os.R_OK):
            return {
                "status": PRIVATE_SOURCE_BINDING_WAITING,
                "reason": "configured private Candidate v2 source is not accessible",
            }
        load_daily_memory_candidate_v2(input_path, root)
    except ValueError as error:
        if str(error) == "private_candidate_source_unavailable":
            return {
                "status": PRIVATE_SOURCE_BINDING_WAITING,
                "reason": "configured private Candidate v2 source is not accessible",
            }
        return {
            "status": PRIVATE_SOURCE_BINDING_REJECTED,
            "reason": "configured private Candidate v2 source failed validation",
        }
    return {"status": PRIVATE_SOURCE_BINDING_CONFIGURED, "reason": "validated local binding"}


def _validate_w3_private_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    _require_exact_keys(envelope, _ENVELOPE_KEYS, "w3_private_envelope_schema_invalid")
    if envelope.get("schema_version") != W3_PRIVATE_CANDIDATE_ENVELOPE_V1:
        raise ValueError("w3_private_envelope_schema_version_denied")
    if envelope.get("upstream_validation_status") != "VALIDATED":
        raise ValueError("daily_v2_validation_required")
    _validate_sensitivity(envelope.get("sensitivity_class"))
    normalized = dict(envelope)
    for field in (
        "candidate_id", "user_scope", "project_scope", "statement", "claim_role",
        "valid_from", "recorded_at",
    ):
        value = normalized.get(field)
        if not isinstance(value, str) or not normalize_text(value) or len(value) > 8192:
            raise ValueError("w3_private_envelope_field_invalid")
    if normalized["claim_role"] not in _USER_MEMORY_TYPES.values():
        raise ValueError("daily_v2_non_user_candidate_denied")
    source_episodes = _sequence_of_mappings(normalized.get("source_episodes"), "w3_private_envelope_provenance_invalid")
    if not source_episodes:
        raise ValueError("w3_private_envelope_provenance_invalid")
    seen: set[str] = set()
    normalized_episodes: list[dict[str, str]] = []
    for episode in source_episodes:
        _require_exact_keys(
            episode,
            {"episode_id", "source_pointer", "source_hash", "actor_type", "recorded_at"},
            "w3_private_envelope_episode_invalid",
        )
        if episode.get("actor_type") != "USER":
            raise ValueError("daily_v2_candidate_actor_denied")
        episode_id = episode.get("episode_id")
        if not isinstance(episode_id, str) or not episode_id or episode_id in seen:
            raise ValueError("w3_private_envelope_episode_invalid")
        seen.add(episode_id)
        if not isinstance(episode.get("source_hash"), str) or not re.fullmatch(r"[0-9a-f]{64}", episode["source_hash"]):
            raise ValueError("w3_private_envelope_episode_invalid")
        for field in ("source_pointer", "recorded_at"):
            if not isinstance(episode.get(field), str) or not normalize_text(episode[field]):
                raise ValueError("w3_private_envelope_episode_invalid")
        normalized_episodes.append(dict(episode))
    normalized["source_episodes"] = normalized_episodes
    if normalized.get("valid_to") is not None and (
        not isinstance(normalized["valid_to"], str) or not normalize_text(normalized["valid_to"])
    ):
        raise ValueError("w3_private_envelope_field_invalid")
    if any(_SECRET.search(value) for value in _iter_strings(normalized)):
        raise ValueError("credential_value_denied")
    return normalized


def _validate_coverage(coverage: Mapping[str, Any], episodes: Sequence[Mapping[str, Any]]) -> None:
    _require_exact_keys(
        coverage,
        {"coverage_id", "user_scope", "project_scope", "covered_episode_ids"},
        "daily_v2_coverage_invalid",
    )
    for field in ("coverage_id", "user_scope", "project_scope"):
        if not isinstance(coverage.get(field), str) or not normalize_text(coverage[field]):
            raise ValueError("daily_v2_coverage_invalid")
    ids = coverage.get("covered_episode_ids")
    if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
        raise ValueError("daily_v2_coverage_invalid")
    if set(ids) != {episode.get("episode_id") for episode in episodes}:
        raise ValueError("daily_v2_coverage_episode_mismatch")


def _validate_episodes(episodes: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for episode in episodes:
        _require_exact_keys(
            episode,
            {"episode_id", "source_pointer", "source_hash", "actor_type", "recorded_at"},
            "daily_v2_episode_invalid",
        )
        episode_id = episode.get("episode_id")
        if not isinstance(episode_id, str) or not episode_id or episode_id in result:
            raise ValueError("daily_v2_episode_invalid")
        if episode.get("actor_type") not in {"USER", "ASSISTANT", "SYSTEM", "PROJECT"}:
            raise ValueError("daily_v2_episode_actor_invalid")
        if not isinstance(episode.get("source_hash"), str) or not re.fullmatch(r"[0-9a-f]{64}", episode["source_hash"]):
            raise ValueError("daily_v2_episode_invalid")
        for field in ("source_pointer", "recorded_at"):
            if not isinstance(episode.get(field), str) or not normalize_text(episode[field]):
                raise ValueError("daily_v2_episode_invalid")
        result[episode_id] = dict(episode)
    return result


def _validate_projection(projection: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> None:
    _require_exact_keys(projection, {"projection_id", "candidate_ids"}, "daily_v2_projection_invalid")
    if not isinstance(projection.get("projection_id"), str) or not projection["projection_id"]:
        raise ValueError("daily_v2_projection_invalid")
    candidate_ids = {candidate.get("candidate_id") for candidate in candidates}
    if not isinstance(projection.get("candidate_ids"), list) or set(projection["candidate_ids"]) != candidate_ids:
        raise ValueError("daily_v2_projection_candidate_mismatch")


def _validate_validation(validation: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> tuple[set[str], dict[str, str]]:
    _require_exact_keys(
        validation,
        {"status", "accepted_candidate_ids", "rejected_candidates", "sensitivity_by_candidate"},
        "daily_v2_validation_invalid",
    )
    if validation.get("status") != "VALIDATED":
        raise ValueError("daily_v2_validation_required")
    candidate_ids = {candidate.get("candidate_id") for candidate in candidates}
    accepted = validation.get("accepted_candidate_ids")
    if not isinstance(accepted, list) or not accepted or not set(accepted).issubset(candidate_ids):
        raise ValueError("daily_v2_validation_invalid")
    rejected = validation.get("rejected_candidates")
    if not isinstance(rejected, list):
        raise ValueError("daily_v2_validation_invalid")
    rejected_ids = {item.get("candidate_id") for item in rejected if isinstance(item, Mapping)}
    if set(accepted).intersection(rejected_ids):
        raise ValueError("daily_v2_validation_overlap")
    sensitivity = validation.get("sensitivity_by_candidate")
    if not isinstance(sensitivity, Mapping) or set(sensitivity) != candidate_ids:
        raise ValueError("daily_v2_sensitivity_invalid")
    for candidate_id in accepted:
        _validate_sensitivity(sensitivity[candidate_id])
    if candidate_ids != set(accepted).union(rejected_ids):
        raise ValueError("daily_v2_validation_disposition_incomplete")
    return set(accepted), dict(sensitivity)


def _validate_sensitivity(value: Any) -> None:
    if value in _DENIED_SENSITIVITY:
        raise ValueError("daily_v2_secret_or_sensitive_candidate_denied")
    if value not in _ALLOWED_SENSITIVITY:
        raise ValueError("daily_v2_sensitivity_not_admitted")


def _require_exact_keys(value: Mapping[str, Any], allowed: set[str], error: str) -> None:
    if not isinstance(value, Mapping) or set(value) != allowed:
        raise ValueError(error)


def _mapping(value: Any, error: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(error)
    return value


def _sequence_of_mappings(value: Any, error: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        raise ValueError(error)
    return value


def _iter_strings(value: Any):
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)
    elif isinstance(value, str):
        yield value


def _public_repository_root() -> Path:
    return Path(__file__).resolve().parents[6]


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False
