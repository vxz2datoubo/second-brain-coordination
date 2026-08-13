# VENDORED SNAPSHOT (do not edit) — origin/main path: coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/private_candidate_ingestion.py
"""Local-only Daily-v2 report transport into the canonical W3 candidate path.

``DailyMemoryCandidate-v2`` remains the producer's human-readable layered
report.  ``DailyMemoryCandidateTransport-v1`` is its explicit, versioned,
machine transport serialization.  The inner ``W3PrivateCandidateEnvelope-v1``
is deliberately separate and is the only shape that reaches W3.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical import content_hash, normalize_text
from .conversation_memory import (
    ConversationEpisode,
    build_conversation_candidate,
    build_conversation_correction,
)
from .memory_store import MemoryStore
from .retrieval import ContextAssembler, QueryPlan


DAILY_MEMORY_CANDIDATE_V2 = "DailyMemoryCandidate-v2"
DAILY_MEMORY_CANDIDATE_TRANSPORT_V1 = "DailyMemoryCandidateTransport-v1"
W3_PRIVATE_CANDIDATE_ENVELOPE_V1 = "W3PrivateCandidateEnvelope-v1"
PRIVATE_LOCAL_CANDIDATE = "PRIVATE_LOCAL_CANDIDATE"
PRIVATE_SOURCE_BINDING_WAITING = "PRIVATE_SOURCE_BINDING_WAITING"
PRIVATE_SOURCE_BINDING_REJECTED = "PRIVATE_SOURCE_BINDING_REJECTED"
PRIVATE_SOURCE_BINDING_CONFIGURED = "PRIVATE_SOURCE_BINDING_CONFIGURED"
NO_ELIGIBLE_USER_MEMORY_CANDIDATES = "NO_ELIGIBLE_USER_MEMORY_CANDIDATES"
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
_DAILY_LAYERS = {
    "schema_version", "COVERAGE", "CONVERSATION_EPISODES",
    "MEMORY_CANDIDATES", "DERIVED_DAILY_PROJECTION", "VALIDATION",
}
_ENVELOPE_KEYS = {
    "schema_version", "candidate_id", "user_scope", "project_scope", "statement",
    "claim_role", "valid_from", "recorded_at", "source_episodes",
    "upstream_validation_status", "sensitivity_class", "valid_to",
    "correction_target_atom_id", "correction_relation_provenance",
    "correction_target_candidate_id", "external_candidate_id", "candidate_confidence",
}


@dataclass(frozen=True)
class PrivateCandidateIngestionResult:
    """Audit result for imported packets or a legitimate no-op Daily report."""

    import_results: tuple[dict[str, Any], ...]
    packets: tuple[dict[str, Any], ...]
    recalled_atom_ids: tuple[str, ...]
    non_imported_dispositions: tuple[dict[str, str], ...] = ()

    @property
    def exact_imported_atom_recalled(self) -> bool:
        expected = {atom["id"] for packet in self.packets for atom in packet["atoms"]}
        return bool(expected) and expected.issubset(set(self.recalled_atom_ids))

    def public_receipt(self) -> dict[str, Any]:
        """Return only aggregate hashes/counts and the actual import outcome."""

        imported = sum(item.get("status") == "IMPORTED" for item in self.import_results)
        duplicate = sum(item.get("status") == "IDEMPOTENT_DUPLICATE" for item in self.import_results)
        if not self.packets:
            status = NO_ELIGIBLE_USER_MEMORY_CANDIDATES
        elif duplicate == len(self.import_results):
            status = "IDEMPOTENT_DUPLICATE"
        elif imported == len(self.import_results):
            status = "IMPORTED"
        else:
            status = "PARTIALLY_IMPORTED"
        atoms = [atom for packet in self.packets for atom in packet["atoms"]]
        conversations = [atom["memory_metadata"]["conversation"] for atom in atoms]
        return {
            "schema_version": "1.0",
            "status": status,
            "validation_status": "PASS",
            "candidate_authority_only": True,
            "formal_project_global_write": "LOCKED",
            "source_hash": content_hash(sorted(packet["source_hash"] for packet in self.packets)),
            "pointer_hash": content_hash(sorted(
                item["source_pointer_hash"]
                for conversation in conversations
                for item in conversation.get("source_episodes", [])
            )),
            "episode_id_hash": content_hash(sorted(
                item["episode_id"]
                for conversation in conversations
                for item in conversation.get("source_episodes", [])
            )),
            "atom_id_hash": content_hash(sorted(atom["id"] for atom in atoms)),
            "scope_hash": content_hash(sorted({
                (conversation["user_scope"], conversation["project_scope"])
                for conversation in conversations
            })),
            "candidate_count": len(self.packets),
            "imported_count": imported,
            "duplicate_count": duplicate,
            "non_imported_count": len(self.non_imported_dispositions),
            "recall_count": len(self.recalled_atom_ids),
            "exact_imported_atom_recalled": self.exact_imported_atom_recalled,
            "recorded_at_hash": content_hash(sorted(
                conversation["recorded_at"] for conversation in conversations
            )),
        }


def normalize_daily_memory_candidate_v2_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Serialize enabled Daily-v2 report fields into the versioned transport.

    This is the producer-side compatibility boundary.  It preserves coverage
    partiality plus included/excluded source semantics, actor distinction,
    episode provenance, projection derivation and validation dispositions.
    Extra report presentation fields are intentionally not a transport error.
    """

    _require_fields(report, _DAILY_LAYERS - {"schema_version"}, "daily_v2_report_layers_missing")
    if report.get("schema_version") not in {None, DAILY_MEMORY_CANDIDATE_V2}:
        raise ValueError("daily_v2_schema_version_denied")
    coverage = _mapping(report["COVERAGE"], "daily_v2_coverage_invalid")
    coverage_state = str(coverage.get("coverage", "UNKNOWN")).upper()
    if coverage_state not in {"COMPLETE", "PARTIAL", "UNKNOWN"}:
        raise ValueError("daily_v2_coverage_invalid")
    included_sources = coverage.get("included_sources", [])
    excluded_sources = coverage.get("excluded_or_unknown_sources", [])
    if not isinstance(included_sources, list) or not isinstance(excluded_sources, list):
        raise ValueError("daily_v2_coverage_invalid")
    episodes = _sequence_of_mappings(report["CONVERSATION_EPISODES"], "daily_v2_episodes_invalid")
    normalized_episodes: list[dict[str, Any]] = []
    for episode in episodes:
        _require_fields(episode, {"episode_id", "source_scope"}, "daily_v2_episode_invalid")
        source_scope = _mapping(episode["source_scope"], "daily_v2_episode_scope_invalid")
        _require_fields(source_scope, {"user_scope", "project_scope"}, "daily_v2_episode_scope_invalid")
        actor = episode.get("speaker", episode.get("actor"))
        source_ref = episode.get("source_ref")
        provenance = episode.get("provenance")
        if source_ref is None and provenance is None:
            raise ValueError("daily_v2_episode_source_missing")
        observed_at = episode.get("observed_at", episode.get("valid_time"))
        valid_time = episode.get("valid_time", observed_at)
        for field, value in (("episode_id", episode["episode_id"]), ("actor", actor), ("observed_at", observed_at), ("valid_time", valid_time)):
            if not isinstance(value, str) or not normalize_text(value):
                raise ValueError("daily_v2_episode_invalid")
        _canonical_instant(observed_at)
        _canonical_instant(valid_time)
        if actor not in {"USER", "ASSISTANT", "SYSTEM", "PROJECT"}:
            raise ValueError("daily_v2_episode_actor_invalid")
        if not all(isinstance(source_scope[field], str) and normalize_text(source_scope[field]) for field in source_scope):
            raise ValueError("daily_v2_episode_scope_invalid")
        normalized_episodes.append({
            "episode_id": episode["episode_id"],
            "source_pointer": source_ref or "provenance://" + content_hash(provenance),
            "source_hash": content_hash({"source_ref": source_ref, "provenance": provenance}),
            "actor_type": actor,
            "recorded_at": _canonical_instant(observed_at),
            "valid_time": _canonical_instant(valid_time),
            "user_scope": source_scope["user_scope"],
            "project_scope": source_scope["project_scope"],
            "provenance_quality": str(episode.get("provenance_quality", "UNKNOWN")),
        })
    candidates = [dict(item) for item in _sequence_of_mappings(report["MEMORY_CANDIDATES"], "daily_v2_candidates_invalid")]
    candidate_ids = {item.get("candidate_id") for item in candidates}
    if not candidate_ids or None in candidate_ids or len(candidate_ids) != len(candidates):
        raise ValueError("daily_v2_candidate_identity_invalid")
    projection = _mapping(report["DERIVED_DAILY_PROJECTION"], "daily_v2_projection_invalid")
    _require_fields(projection, {"derivation"}, "daily_v2_projection_invalid")
    if projection["derivation"] != "ASSISTANT_SUMMARY":
        raise ValueError("daily_v2_projection_candidate_mismatch")
    supporting_candidate_ids = projection.get("supporting_candidate_ids", projection.get("candidate_ids", []))
    if not isinstance(supporting_candidate_ids, list) or not set(supporting_candidate_ids).issubset(candidate_ids):
        raise ValueError("daily_v2_projection_candidate_mismatch")
    supporting_episode_ids = projection.get("supporting_episode_ids", projection.get("episode_ids", []))
    if not isinstance(supporting_episode_ids, list) or not set(supporting_episode_ids).issubset({item["episode_id"] for item in normalized_episodes}):
        raise ValueError("daily_v2_projection_episode_mismatch")
    validation = _mapping(report["VALIDATION"], "daily_v2_validation_invalid")
    _require_fields(validation, {"status", "checklist"}, "daily_v2_validation_invalid")
    if validation["status"] != "VALIDATED" or not isinstance(validation["checklist"], list):
        raise ValueError("daily_v2_validation_required")
    raw_dispositions = validation.get("candidate_dispositions", {})
    dispositions = dict(raw_dispositions) if isinstance(raw_dispositions, Mapping) else {}
    rejected = {
        item.get("candidate_id") for item in validation.get("rejected_candidates", [])
        if isinstance(item, Mapping)
    }
    accepted = set(validation.get("accepted_candidate_ids", []))
    sensitivity = dict(validation.get("sensitivity_by_candidate", {})) if isinstance(validation.get("sensitivity_by_candidate", {}), Mapping) else {}
    episode_by_id = {item["episode_id"]: item for item in normalized_episodes}
    for candidate in candidates:
        _require_fields(candidate, {"candidate_id", "candidate_type", "statement", "supporting_episode_ids"}, "daily_v2_candidate_schema_invalid")
        candidate_id = candidate["candidate_id"]
        disposition = dispositions.get(candidate_id)
        if disposition is None:
            disposition = "REJECTED" if candidate_id in rejected else "ACCEPTED" if candidate_id in accepted else "NON_DURABLE"
        if disposition not in {"ACCEPTED", "REJECTED", "NON_DURABLE"}:
            raise ValueError("daily_v2_validation_invalid")
        dispositions[candidate_id] = disposition
        candidate_sensitivity = candidate.get("sensitivity_class", sensitivity.get(candidate_id, "PRIVATE_OR_SENSITIVE"))
        if candidate_id in sensitivity and candidate_sensitivity != sensitivity[candidate_id]:
            raise ValueError("daily_v2_sensitivity_mismatch")
        sensitivity[candidate_id] = candidate_sensitivity
        candidate["sensitivity_class"] = candidate_sensitivity
        candidate["valid_from"] = _candidate_temporal_value(
            candidate, episode_by_id, "valid_from", "valid_time"
        )
        candidate["valid_to"] = (
            _canonical_instant(candidate["valid_to"])
            if candidate.get("valid_to") is not None else None
        )
        candidate["recorded_at"] = _candidate_temporal_value(
            candidate, episode_by_id, "recorded_at", "recorded_at"
        )
        candidate["correction_target"] = candidate.get("correction_target")
        candidate["confidence"] = _normalize_confidence(candidate.get("confidence", "MEDIUM"))
    return {
        "schema_version": DAILY_MEMORY_CANDIDATE_TRANSPORT_V1,
        "producer_schema_version": DAILY_MEMORY_CANDIDATE_V2,
        "coverage": {"target_local_date": coverage.get("target_local_date"), "execution_time": coverage.get("execution_time"), "coverage": coverage_state, "included_sources": list(included_sources), "excluded_or_unknown_sources": list(excluded_sources)},
        "episodes": normalized_episodes,
        "candidates": [dict(item) for item in candidates],
        "projection": dict(projection),
        "validation": {
            "status": validation["status"],
            "candidate_dispositions": dict(dispositions),
            "sensitivity_by_candidate": dict(sensitivity),
        },
    }


def serialize_daily_memory_candidate_v2_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Backward-compatible name for the tolerant human-report normalizer."""

    return normalize_daily_memory_candidate_v2_report(report)


def daily_memory_candidate_transport_to_w3_private_envelopes(
    transport: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Map a validated transport to W3 envelopes plus explicit no-op records."""

    _require_exact_keys(transport, {"schema_version", "producer_schema_version", "coverage", "episodes", "candidates", "projection", "validation"}, "daily_transport_schema_invalid")
    if transport.get("schema_version") != DAILY_MEMORY_CANDIDATE_TRANSPORT_V1 or transport.get("producer_schema_version") != DAILY_MEMORY_CANDIDATE_V2:
        raise ValueError("daily_transport_schema_version_denied")
    episodes = _sequence_of_mappings(transport["episodes"], "daily_transport_episode_invalid")
    episode_by_id = {item.get("episode_id"): item for item in episodes}
    if len(episode_by_id) != len(episodes) or None in episode_by_id:
        raise ValueError("daily_transport_episode_invalid")
    validation = _mapping(transport["validation"], "daily_transport_validation_invalid")
    dispositions = _mapping(validation.get("candidate_dispositions"), "daily_transport_validation_invalid")
    sensitivity = _mapping(validation.get("sensitivity_by_candidate"), "daily_transport_validation_invalid")
    envelopes: list[dict[str, Any]] = []
    no_ops: list[dict[str, str]] = []
    for candidate in _sequence_of_mappings(transport["candidates"], "daily_transport_candidate_invalid"):
        candidate_id = candidate.get("candidate_id")
        disposition = dispositions.get(candidate_id)
        if disposition != "ACCEPTED":
            no_ops.append({"candidate_id": str(candidate_id), "reason": "UPSTREAM_" + str(disposition)})
            continue
        candidate_type = candidate.get("candidate_type")
        if candidate_type not in _USER_MEMORY_TYPES:
            no_ops.append({"candidate_id": str(candidate_id), "reason": "OUT_OF_SCOPE_CANDIDATE_TYPE"})
            continue
        _validate_sensitivity(sensitivity.get(candidate_id))
        if candidate.get("sensitivity_class") != sensitivity.get(candidate_id):
            raise ValueError("daily_v2_sensitivity_mismatch")
        source_ids = candidate.get("supporting_episode_ids")
        if not isinstance(source_ids, list) or not source_ids or len(source_ids) != len(set(source_ids)):
            raise ValueError("daily_v2_candidate_provenance_invalid")
        try:
            source_episodes = [episode_by_id[item] for item in source_ids]
        except KeyError as error:
            raise ValueError("daily_v2_candidate_episode_missing") from error
        if any(item.get("actor_type") != "USER" for item in source_episodes):
            raise ValueError("daily_v2_candidate_actor_denied")
        scopes = {(item.get("user_scope"), item.get("project_scope")) for item in source_episodes}
        if len(scopes) != 1 or any(not isinstance(value, str) or not value for pair in scopes for value in pair):
            raise ValueError("daily_v2_candidate_scope_invalid")
        correction_target = candidate.get("correction_target")
        target_candidate_id: str | None = None
        if candidate_type == "USER_CORRECTION":
            target = _mapping(correction_target, "daily_v2_correction_target_required")
            _require_exact_keys(target, {"replaces_candidate_id", "relation_provenance"}, "daily_v2_correction_target_required")
            target_candidate_id = target.get("replaces_candidate_id")
            if not isinstance(target_candidate_id, str) or not target_candidate_id:
                raise ValueError("daily_v2_correction_target_required")
        elif correction_target is not None:
            raise ValueError("daily_v2_correction_target_unexpected")
        user_scope, project_scope = next(iter(scopes))
        envelope = {
            "schema_version": W3_PRIVATE_CANDIDATE_ENVELOPE_V1,
            "candidate_id": candidate_id,
            "user_scope": user_scope,
            "project_scope": project_scope,
            "statement": candidate.get("statement"),
            "claim_role": _USER_MEMORY_TYPES[candidate_type],
            "valid_from": candidate.get("valid_from"),
            "valid_to": candidate.get("valid_to"),
            "recorded_at": candidate.get("recorded_at"),
            "source_episodes": source_episodes,
            "upstream_validation_status": validation.get("status"),
            "sensitivity_class": candidate.get("sensitivity_class"),
            "correction_target_atom_id": None,
            "correction_relation_provenance": target["relation_provenance"] if candidate_type == "USER_CORRECTION" else None,
            "correction_target_candidate_id": target_candidate_id,
            "external_candidate_id": candidate_id,
            "candidate_confidence": candidate.get("confidence"),
        }
        envelopes.append(_validate_w3_private_envelope(envelope))
    return envelopes, no_ops


def daily_v2_package_to_w3_private_envelopes(package: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Compatibility entry point for a real Daily-v2 report."""

    envelopes, _ = daily_memory_candidate_transport_to_w3_private_envelopes(
        serialize_daily_memory_candidate_v2_report(package)
    )
    return envelopes


def build_private_w3_candidate_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Build one canonical W3 candidate or canonical correction packet."""

    normalized = _validate_w3_private_envelope(envelope)
    episodes = tuple(_episode_model(item, normalized) for item in normalized["source_episodes"])
    build_kwargs = {
        "episode": episodes[0], "additional_episodes": episodes[1:],
        "statement": normalized["statement"], "valid_from": normalized["valid_from"],
        "valid_to": normalized.get("valid_to"),
        "external_candidate_id": normalized["external_candidate_id"],
        "candidate_confidence": normalized["candidate_confidence"],
    }
    if normalized["claim_role"] == "USER_CORRECTION":
        return build_conversation_correction(
            **build_kwargs,
            replaces_atom_id=normalized["correction_target_atom_id"],
            correction_context=normalized["correction_relation_provenance"],
        )
    return build_conversation_candidate(**build_kwargs, claim_role=normalized["claim_role"])


def ingest_daily_memory_candidate_v2(
    package: Mapping[str, Any], store: MemoryStore, *, context_assembler: ContextAssembler | None = None,
) -> PrivateCandidateIngestionResult:
    """Ingest only eligible user candidates and prove exact atom recall."""

    envelopes, no_ops = daily_memory_candidate_transport_to_w3_private_envelopes(
        serialize_daily_memory_candidate_v2_report(package)
    )
    resolved = tuple(_resolve_correction_target(envelope, store) for envelope in envelopes)
    _preflight_correction_lifecycle(resolved, store)
    packets = tuple(build_private_w3_candidate_envelope(envelope) for envelope in resolved)
    # The existing W3 store owns one transaction for the entire Daily package.
    # Any later import invariant failure rolls back every earlier package item.
    import_results = tuple(store.import_learning_packets_atomic(packets))
    assembler = context_assembler or ContextAssembler(store)
    recalled: set[str] = set()
    for envelope, packet in zip(resolved, packets):
        bundle = assembler.assemble(QueryPlan(
            query_text=envelope["statement"], scopes=(envelope["project_scope"],),
            user_scope=envelope["user_scope"], valid_at=envelope["valid_from"],
            truth_states=("candidate",),
        ))
        current = {atom["id"] for atom in bundle.atoms}
        recalled.update(current)
        expected = {atom["id"] for atom in packet["atoms"]}
        if not expected.issubset(current):
            raise ValueError("private_candidate_exact_recall_not_proven")
    return PrivateCandidateIngestionResult(import_results, packets, tuple(sorted(recalled)), tuple(no_ops))


def validate_private_data_paths(input_path: Path, store_path: Path, private_root: Path) -> tuple[Path, Path, Path]:
    """Fail closed unless input and persistent store are under private root."""

    root = private_root.expanduser().resolve(strict=False)
    input_resolved = input_path.expanduser().resolve(strict=False)
    store_resolved = store_path.expanduser().resolve(strict=False)
    public_root = _public_repository_root()
    if not root.exists() or not root.is_dir() or _is_within(root, public_root):
        raise ValueError("private_data_root_invalid")
    if not _is_within(input_resolved, root) or not _is_within(store_resolved, root) or _is_within(input_resolved, public_root) or _is_within(store_resolved, public_root):
        raise ValueError("private_data_path_policy_denied")
    return input_resolved, store_resolved, root


def load_daily_memory_candidate_v2(path: Path, private_root: Path) -> dict[str, Any]:
    """Load and validate one local report without exposing the private path."""

    input_path, _, _ = validate_private_data_paths(path, path.with_suffix(".probe"), private_root)
    try:
        loaded = json.loads(input_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError("private_candidate_source_unavailable") from error
    except json.JSONDecodeError as error:
        raise ValueError("private_candidate_source_invalid") from error
    if not isinstance(loaded, dict):
        raise ValueError("private_candidate_mapping_required")
    serialize_daily_memory_candidate_v2_report(loaded)
    return loaded


def private_source_binding_status(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return only waiting/rejected/configured capability states, never paths."""

    env = os.environ if environment is None else environment
    root_value, source_value = env.get(_PRIVATE_ROOT_ENV), env.get(_PRIVATE_PACKAGE_ENV)
    if not root_value or not source_value:
        return {"status": PRIVATE_SOURCE_BINDING_WAITING, "reason": "explicit private data-root and Candidate v2 transport binding required"}
    try:
        root, source = Path(root_value), Path(source_value)
        input_path, _, _ = validate_private_data_paths(source, source.with_suffix(".probe"), root)
        if not input_path.is_file() or not os.access(input_path, os.R_OK):
            return {"status": PRIVATE_SOURCE_BINDING_WAITING, "reason": "configured private Candidate v2 source is not accessible"}
        load_daily_memory_candidate_v2(input_path, root)
    except ValueError as error:
        if str(error) == "private_candidate_source_unavailable":
            return {"status": PRIVATE_SOURCE_BINDING_WAITING, "reason": "configured private Candidate v2 source is not accessible"}
        return {"status": PRIVATE_SOURCE_BINDING_REJECTED, "reason": "configured private Candidate v2 source failed validation"}
    return {"status": PRIVATE_SOURCE_BINDING_CONFIGURED, "reason": "validated local binding"}


def _episode_model(episode: Mapping[str, Any], envelope: Mapping[str, Any]) -> ConversationEpisode:
    return ConversationEpisode(
        episode_id=episode["episode_id"], user_scope=envelope["user_scope"], project_scope=envelope["project_scope"],
        source_pointer=episode["source_pointer"], source_hash=episode["source_hash"],
        privacy_class=PRIVATE_LOCAL_CANDIDATE, recorded_at=episode["recorded_at"],
        coverage="private_local", source_class="PRIVATE_LOCAL_AUTHORIZED",
        valid_time=episode["valid_time"], provenance_quality=episode["provenance_quality"],
    )


def _validate_w3_private_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    _require_exact_keys(envelope, _ENVELOPE_KEYS, "w3_private_envelope_schema_invalid")
    if envelope.get("schema_version") != W3_PRIVATE_CANDIDATE_ENVELOPE_V1 or envelope.get("upstream_validation_status") != "VALIDATED":
        raise ValueError("daily_v2_validation_required")
    _validate_sensitivity(envelope.get("sensitivity_class"))
    normalized = dict(envelope)
    for field in ("candidate_id", "user_scope", "project_scope", "statement", "claim_role", "valid_from", "recorded_at"):
        if not isinstance(normalized.get(field), str) or not normalize_text(normalized[field]) or len(normalized[field]) > 8192:
            raise ValueError("w3_private_envelope_field_invalid")
    if normalized["claim_role"] not in _USER_MEMORY_TYPES.values():
        raise ValueError("daily_v2_non_user_candidate_denied")
    if normalized["claim_role"] == "USER_CORRECTION":
        if not isinstance(normalized.get("correction_target_candidate_id"), str) or not normalized["correction_target_candidate_id"]:
            raise ValueError("daily_v2_correction_target_required")
        if not isinstance(normalized.get("correction_relation_provenance"), str) or not normalize_text(normalized["correction_relation_provenance"]):
            raise ValueError("daily_v2_correction_target_required")
    elif any(normalized.get(field) is not None for field in ("correction_target_atom_id", "correction_target_candidate_id", "correction_relation_provenance")):
        raise ValueError("daily_v2_correction_target_unexpected")
    source_episodes = _sequence_of_mappings(normalized.get("source_episodes"), "w3_private_envelope_provenance_invalid")
    if not source_episodes:
        raise ValueError("w3_private_envelope_provenance_invalid")
    seen: set[str] = set()
    normalized_episodes: list[dict[str, Any]] = []
    for episode in source_episodes:
        _require_fields(episode, {"episode_id", "source_pointer", "source_hash", "actor_type", "recorded_at", "valid_time", "provenance_quality", "user_scope", "project_scope"}, "w3_private_envelope_episode_invalid")
        if episode.get("actor_type") != "USER" or episode.get("user_scope") != normalized["user_scope"] or episode.get("project_scope") != normalized["project_scope"]:
            raise ValueError("daily_v2_candidate_actor_denied")
        episode_id = episode.get("episode_id")
        if not isinstance(episode_id, str) or not episode_id or episode_id in seen or not isinstance(episode.get("source_hash"), str) or not re.fullmatch(r"[0-9a-f]{64}", episode["source_hash"]):
            raise ValueError("w3_private_envelope_episode_invalid")
        seen.add(episode_id)
        normalized_episodes.append(dict(episode))
    normalized["source_episodes"] = normalized_episodes
    if normalized.get("valid_to") is not None and not isinstance(normalized["valid_to"], str):
        raise ValueError("w3_private_envelope_field_invalid")
    if not isinstance(normalized.get("external_candidate_id"), str) or not normalize_text(normalized["external_candidate_id"]):
        raise ValueError("w3_private_envelope_field_invalid")
    if not isinstance(normalized.get("candidate_confidence"), (int, float)) or isinstance(normalized["candidate_confidence"], bool) or not 0.0 <= float(normalized["candidate_confidence"]) <= 1.0:
        raise ValueError("w3_private_envelope_field_invalid")
    if any(_SECRET.search(value) for value in _iter_strings(normalized)):
        raise ValueError("credential_value_denied")
    return normalized


def _resolve_correction_target(envelope: Mapping[str, Any], store: MemoryStore) -> dict[str, Any]:
    """Resolve producer-known identity locally before any packet is imported."""

    normalized = dict(envelope)
    if normalized["claim_role"] != "USER_CORRECTION":
        return normalized
    wanted = content_hash(normalized["correction_target_candidate_id"])
    matches = []
    closed_matches = []
    for atom in store.all_atoms():
        conversation = atom.get("memory_metadata", {}).get("conversation", {})
        aliases = set(conversation.get("daily_candidate_id_hashes", []))
        if conversation.get("daily_candidate_id_hash"):
            aliases.add(conversation["daily_candidate_id_hash"])
        if (
            wanted in aliases
            and conversation.get("user_scope") == normalized["user_scope"]
            and conversation.get("project_scope") == normalized["project_scope"]
            and _canonical_instant(conversation.get("valid_from")) < _canonical_instant(normalized["valid_from"])
        ):
            (closed_matches if atom.get("knowledge_status") == "superseded" or conversation.get("superseded_by") else matches).append(atom["id"])
    if closed_matches:
        raise ValueError("daily_v2_correction_target_already_closed")
    if len(matches) != 1:
        raise ValueError("daily_v2_correction_target_unresolved")
    normalized["correction_target_atom_id"] = matches[0]
    return _validate_w3_private_envelope(normalized)


def _preflight_correction_lifecycle(envelopes: Sequence[Mapping[str, Any]], store: MemoryStore) -> None:
    """Reject lifecycle conflicts before the batch enters the W3 transaction."""

    targets = [
        envelope["correction_target_atom_id"] for envelope in envelopes
        if envelope["claim_role"] == "USER_CORRECTION"
    ]
    if len(targets) != len(set(targets)):
        raise ValueError("daily_v2_correction_target_duplicate_in_batch")
    for target_id in targets:
        target = store.get_atom(target_id)
        conversation = (target or {}).get("memory_metadata", {}).get("conversation", {})
        if target is None or target.get("knowledge_status") == "superseded" or conversation.get("superseded_by"):
            raise ValueError("daily_v2_correction_target_already_closed")


def _candidate_temporal_value(
    candidate: Mapping[str, Any], episode_by_id: Mapping[str, Mapping[str, Any]], field: str, episode_field: str,
) -> str:
    """Use an explicit candidate instant or one unambiguous supporting instant."""

    explicit = candidate.get(field)
    if explicit is not None:
        return _canonical_instant(explicit)
    source_ids = candidate.get("supporting_episode_ids")
    if not isinstance(source_ids, list) or not source_ids or len(source_ids) != len(set(source_ids)):
        raise ValueError("daily_v2_candidate_provenance_invalid")
    try:
        values = {_canonical_instant(episode_by_id[source_id][episode_field]) for source_id in source_ids}
    except KeyError as error:
        raise ValueError("daily_v2_candidate_episode_missing") from error
    if len(values) != 1:
        raise ValueError("daily_v2_candidate_time_ambiguous")
    return values.pop()


def _normalize_confidence(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 0.0 <= float(value) <= 1.0:
        return float(value)
    mapped = {"HIGH": 0.9, "MEDIUM": 0.6, "LOW": 0.3}.get(str(value).upper())
    if mapped is None:
        raise ValueError("daily_v2_candidate_confidence_invalid")
    return mapped


def _canonical_instant(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("daily_v2_time_invalid")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("daily_v2_time_invalid")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_sensitivity(value: Any) -> None:
    if value in _DENIED_SENSITIVITY:
        raise ValueError("daily_v2_secret_or_sensitive_candidate_denied")
    if value not in _ALLOWED_SENSITIVITY:
        raise ValueError("daily_v2_sensitivity_not_admitted")


def _require_exact_keys(value: Mapping[str, Any], allowed: set[str], error: str) -> None:
    if not isinstance(value, Mapping) or set(value) != allowed:
        raise ValueError(error)


def _require_fields(value: Mapping[str, Any], required: set[str], error: str) -> None:
    if not isinstance(value, Mapping) or not required.issubset(value):
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


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
