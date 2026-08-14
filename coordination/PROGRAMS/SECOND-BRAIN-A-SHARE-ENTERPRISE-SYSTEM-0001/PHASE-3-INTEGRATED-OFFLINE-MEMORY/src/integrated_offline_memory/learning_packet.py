"""Deterministic candidate-only LearningPacket assembly and verification."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .canonical import atom_id, content_hash, normalize_text, packet_id, relation_id


SCHEMA_VERSION = "1.0.0"
PROCESSOR_VERSION = "p3-integrated-offline-memory-1.0.0"
_SECRET = re.compile(r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
_CONVERSATION_ROLES = {
    "USER_ASSERTION", "USER_PREFERENCE", "USER_DECISION", "USER_CORRECTION",
    "USER_PLAN", "USER_GOAL", "USER_COMMITMENT", "USER_EVENT_REPORT",
    "USER_EVALUATION", "USER_CREDIBILITY_JUDGMENT", "USER_BIAS_JUDGMENT",
}
_CONVERSATION_REQUIRED = {
    "episode_manifest_id", "user_scope", "project_scope", "privacy_class",
    "coverage", "source_class", "claim_role", "valid_from", "recorded_at",
}
_CONVERSATION_SOURCE_CLASSIFICATIONS = {
    ("PUBLIC_SAFE_SYNTHETIC", "synthetic"): "SYNTHETIC_PUBLIC_SAFE",
    ("PRIVATE_LOCAL_CANDIDATE", "private_local"): "PRIVATE_LOCAL_AUTHORIZED",
}
_PROMPT_INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt",
    "developer message",
    "disregard instructions",
    "jailbreak",
    "<system>",
    "忽略之前指令",
    "忽略所有指令",
    "系统提示",
    "开发者消息",
)
_CONVERSATION_DERIVED_FIELDS = {"effective_valid_to", "superseded_by"}
_CONVERSATION_OPTIONAL = {
    "source_episode_manifest_ids", "source_episodes", "daily_candidate_id_hash",
    "daily_candidate_id_hashes", "candidate_confidence",
}
_KNOWLEDGE_ROLES = {
    "FACT_CLAIM", "SOURCE_CLAIM", "SOURCE_INTERPRETATION", "VALUE_JUDGMENT",
    "MECHANISM", "CONDITION", "COUNTEREXAMPLE", "METHOD", "OPEN_QUESTION",
    "USER_STANCE", "ASSISTANT_ANALYSIS", "MODEL_INFERENCE",
}
_KNOWLEDGE_REQUIRED = {
    "schema_version", "episode_manifest_ids", "source_episodes", "user_scope",
    "project_scope", "privacy_domain", "identity_domain_hash", "proposition_id",
    "epistemic_role", "taxonomy_version", "valid_from", "recorded_at",
    "provenance_quality", "freshness_profile", "safety_class", "source_trust",
}
_PUBLIC_SAFE_SYNTHETIC_DOMAIN = re.compile(r"synthetic-[a-z0-9][a-z0-9-]{0,63}")


def build_learning_packet(
    *,
    source_manifest_ids: list[str],
    source_hash: str,
    validation_report: dict[str, Any],
    evidence_refs: list[str],
    atoms: list[dict[str, Any]],
    relations: list[dict[str, Any]] | None = None,
    unknowns: list[dict[str, Any]] | None = None,
    conflicts: list[dict[str, Any]] | None = None,
    base_knowledge_version: str = "candidate-r0",
) -> dict[str, Any]:
    normalized_atoms: list[dict[str, Any]] = []
    for atom in atoms:
        # Reassembly paths may provide a previously normalized atom; retain
        # its canonical statement instead of silently replacing it with empty.
        statement = normalize_text(str(atom.get("statement", atom.get("canonical_statement", ""))))
        atom_type = normalize_text(str(atom.get("atom_type", "observation"))).lower()
        scope = normalize_text(str(atom.get("scope", "")))
        memory_metadata = atom.get("memory_metadata", {})
        conversation = memory_metadata.get("conversation") if isinstance(memory_metadata, dict) else None
        knowledge = memory_metadata.get("knowledge") if isinstance(memory_metadata, dict) else None
        if atom_type == "conversation_memory" and isinstance(conversation, dict):
            memory_metadata = {
                **memory_metadata,
                "conversation": _normalized_conversation_metadata(conversation),
            }
            conversation = memory_metadata["conversation"]
        if atom_type == "knowledge_atom" and isinstance(knowledge, dict):
            memory_metadata = {**memory_metadata, "knowledge": _normalized_knowledge_metadata(knowledge)}
            knowledge = memory_metadata["knowledge"]
        canonical_id = atom_id(statement, atom_type, scope)
        if atom_type == "conversation_memory" and isinstance(conversation, dict):
            # Keep malformed generic input on the verifier path so it receives
            # a deterministic contract error instead of an identity exception.
            try:
                canonical_id = conversation_atom_id(statement, conversation)
            except (AttributeError, TypeError, ValueError):
                pass
        if atom_type == "knowledge_atom" and isinstance(knowledge, dict):
            try:
                canonical_id = knowledge_atom_id(statement, knowledge)
            except (AttributeError, TypeError, ValueError):
                pass
        normalized_atoms.append({
            "id": atom.get("id") or canonical_id,
            "atom_type": atom_type,
            "canonical_statement": statement,
            "scope": scope,
            "confidence": float(atom.get("confidence", 0.5)),
            "verification_status": atom.get("verification_status", "PARTIALLY_VERIFIED"),
            "evidence_quality": atom.get("evidence_quality", "PARTIAL_FIELD_EVIDENCE"),
            "knowledge_status": atom.get("knowledge_status", "candidate"),
            "gpt_access": atom.get("gpt_access", "FULL_SEMANTIC_ACCESS"),
            "transport_visibility": atom.get("transport_visibility", "PUBLIC_SAFE_METADATA_ONLY"),
            "authority_level": "CANDIDATE_ONLY",
            "source_refs": sorted(set(atom.get("source_refs", evidence_refs))),
            "premises": atom.get("premises", []),
            "exceptions": atom.get("exceptions", []),
            "failure_conditions": atom.get("failure_conditions", []),
            # Additive metadata is retained by the canonical packet/store path.
            # ConversationEpisode uses it for bitemporal and scope admission;
            # it deliberately contains no raw source pointer or body.
            "memory_metadata": memory_metadata,
        })
    normalized_atoms.sort(key=lambda item: item["id"])

    normalized_relations: list[dict[str, Any]] = []
    for relation in relations or []:
        source = relation["source_atom_id"]
        target = relation["target_atom_id"]
        relation_type = normalize_text(str(relation.get("relation_type", "related_to"))).lower()
        normalized_relations.append({
            "id": relation.get("id") or relation_id(source, target, relation_type),
            "source_atom_id": source,
            "target_atom_id": target,
            "relation_type": relation_type,
            "confidence": float(relation.get("confidence", 0.5)),
            "context": normalize_text(str(relation.get("context", ""))),
            "knowledge_status": relation.get("knowledge_status", "candidate"),
            # A correction packet may refer to a pre-existing atom.  The store
            # verifies that endpoint atomically before it writes the relation.
            "target_existing": bool(relation.get("target_existing", False)),
        })
    normalized_relations.sort(key=lambda item: item["id"])

    validation_hash = content_hash(validation_report)
    semantic_id = packet_id(source_hash, [item["id"] for item in normalized_atoms], validation_hash)
    core = {
        "schema_version": SCHEMA_VERSION,
        "packet_id": semantic_id,
        "status": "candidate",
        "authority_write": False,
        "no_trade_gate": True,
        "processor_version": PROCESSOR_VERSION,
        "base_knowledge_version": base_knowledge_version,
        "source_manifest_ids": sorted(set(source_manifest_ids)),
        "source_hash": source_hash,
        "validation_report": validation_report,
        "evidence_refs": sorted(set(evidence_refs)),
        "atoms": normalized_atoms,
        "relations": normalized_relations,
        "unknowns": unknowns or [],
        "conflicts": conflicts or [],
    }
    packet_content_hash = content_hash(core)
    packet = {
        **core,
        "packet_content_hash": packet_content_hash,
        "idempotency_key": semantic_id + "-" + packet_content_hash[:16],
    }
    verdict = verify_learning_packet(packet)
    if not verdict["valid"]:
        raise ValueError("invalid_learning_packet:" + ",".join(verdict["errors"]))
    return packet


def verify_learning_packet(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = {
        "schema_version", "packet_id", "packet_content_hash", "idempotency_key",
        "status", "authority_write", "no_trade_gate", "source_manifest_ids",
        "source_hash", "validation_report", "evidence_refs", "atoms", "relations",
    }
    missing = required - set(packet)
    if missing:
        errors.append("missing:" + ",".join(sorted(missing)))
    if packet.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported_schema_version")
    if packet.get("status") != "candidate" or packet.get("authority_write") is not False:
        errors.append("candidate_authority_boundary")
    if packet.get("no_trade_gate") is not True:
        errors.append("no_trade_gate_required")
    if _SECRET.search(str(packet)):
        errors.append("credential_value_denied")
    atom_ids = [item.get("id") for item in packet.get("atoms", [])]
    if any(not item for item in atom_ids) or len(atom_ids) != len(set(atom_ids)):
        errors.append("atom_identity_invalid")
    atom_set = set(atom_ids)
    for relation in packet.get("relations", []):
        if relation.get("source_atom_id") not in atom_set:
            errors.append("relation_endpoint_missing")
        elif relation.get("target_atom_id") not in atom_set and not relation.get("target_existing", False):
            errors.append("relation_endpoint_missing")
    for atom in packet.get("atoms", []):
        errors.extend(_conversation_contract_errors(atom))
        errors.extend(_conversation_packet_errors(packet, atom))
        errors.extend(_knowledge_contract_errors(atom))
        errors.extend(_knowledge_packet_errors(packet, atom))
    if packet.get("packet_id") and packet.get("packet_content_hash"):
        expected_key = packet["packet_id"] + "-" + packet["packet_content_hash"][:16]
        if packet.get("idempotency_key") != expected_key:
            errors.append("idempotency_key_mismatch")
    return {"valid": not errors, "errors": errors}


def _conversation_contract_errors(atom: dict[str, Any]) -> list[str]:
    """Validate CLTM atoms even when callers bypass the episode adapter."""
    conversation = atom.get("memory_metadata", {}).get("conversation")
    if atom.get("atom_type") != "conversation_memory" and conversation is None:
        return []
    if atom.get("atom_type") != "conversation_memory" or not isinstance(conversation, dict):
        return ["conversation_metadata_required"]
    if _CONVERSATION_REQUIRED - set(conversation):
        return ["conversation_metadata_required"]
    if any(not isinstance(conversation[key], str) or not conversation[key] for key in _CONVERSATION_REQUIRED):
        return ["conversation_metadata_invalid"]
    expected_source_class = _CONVERSATION_SOURCE_CLASSIFICATIONS.get(
        (conversation["privacy_class"], conversation["coverage"])
    )
    if expected_source_class is None or conversation["source_class"] != expected_source_class:
        return ["conversation_privacy_denied"]
    expected_visibility = (
        "LOCAL_PRIVATE_CANDIDATE_ONLY"
        if conversation["privacy_class"] == "PRIVATE_LOCAL_CANDIDATE"
        else "PUBLIC_SAFE_METADATA_ONLY"
    )
    if atom.get("transport_visibility") != expected_visibility:
        return ["conversation_transport_visibility_denied"]
    if conversation["claim_role"] not in _CONVERSATION_ROLES:
        return ["conversation_claim_role_denied"]
    if atom.get("scope") != conversation["project_scope"]:
        return ["conversation_project_scope_inconsistent"]
    if "conversation://" + conversation["episode_manifest_id"] not in atom.get("source_refs", []):
        return ["conversation_provenance_missing"]
    related_manifests = conversation.get("source_episode_manifest_ids")
    if related_manifests is not None:
        if (
            not isinstance(related_manifests, list)
            or not related_manifests
            or any(not isinstance(item, str) or not item for item in related_manifests)
            or conversation["episode_manifest_id"] not in related_manifests
        ):
            return ["conversation_related_provenance_invalid"]
    try:
        valid_from = _instant(conversation["valid_from"])
        valid_to = conversation.get("valid_to")
        if valid_to is not None and _instant(valid_to) <= valid_from:
            return ["conversation_valid_time_invalid"]
        effective_valid_to = conversation.get("effective_valid_to")
        if effective_valid_to is not None and _instant(effective_valid_to) <= valid_from:
            return ["conversation_effective_valid_time_invalid"]
        _instant(conversation["recorded_at"])
    except (TypeError, ValueError):
        return ["conversation_time_invalid"]
    if _is_prompt_injection(atom.get("canonical_statement", "")):
        return ["conversation_prompt_injection_denied"]
    if atom.get("id") != conversation_atom_id(atom.get("canonical_statement", ""), conversation):
        return ["conversation_identity_invalid"]
    return []


def conversation_atom_id(statement: str, conversation: dict[str, Any]) -> str:
    """Immutable CLTM identity excludes derived correction closure state."""
    return "at-conversation-" + content_hash({
        "episode": conversation.get("episode_manifest_id"),
        "statement": normalize_text(statement),
        "role": conversation.get("claim_role"),
        "valid_from": _canonical_instant(conversation.get("valid_from")),
        "valid_to": (
            _canonical_instant(conversation["valid_to"])
            if conversation.get("valid_to") is not None else None
        ),
    })[:20]


def knowledge_atom_id(statement: str, knowledge: dict[str, Any]) -> str:
    """Versioned semantic identity; provenance remains explicitly outside it."""
    return "at-knowledge-" + content_hash({
        "identity_version": "knowledge-proposition-domain-v1",
        "statement": normalize_text(statement),
        "role": knowledge.get("epistemic_role"),
        "taxonomy_version": knowledge.get("taxonomy_version"),
        "identity_domain_hash": knowledge.get("identity_domain_hash"),
    })[:20]


def _knowledge_contract_errors(atom: dict[str, Any]) -> list[str]:
    """Fail closed for governed P1 atoms, even for non-adapter callers."""
    knowledge = atom.get("memory_metadata", {}).get("knowledge")
    if atom.get("atom_type") != "knowledge_atom" and knowledge is None:
        return []
    if atom.get("atom_type") != "knowledge_atom" or not isinstance(knowledge, dict):
        return ["knowledge_metadata_required"]
    if _KNOWLEDGE_REQUIRED - set(knowledge):
        return ["knowledge_metadata_required"]
    string_fields = _KNOWLEDGE_REQUIRED - {"episode_manifest_ids", "source_episodes"}
    if any(not isinstance(knowledge.get(key), str) or not knowledge[key] for key in string_fields):
        return ["knowledge_metadata_invalid"]
    if knowledge["schema_version"] != "knowledge-atom-v1":
        return ["knowledge_schema_unsupported"]
    if (
        knowledge["safety_class"] != "PUBLIC_SAFE_SYNTHETIC"
        or not (knowledge["privacy_domain"] == "PUBLIC_SAFE_SYNTHETIC" or _PUBLIC_SAFE_SYNTHETIC_DOMAIN.fullmatch(knowledge["privacy_domain"]))
    ):
        return ["knowledge_privacy_denied"]
    if knowledge["source_trust"] not in {"SOURCE_DATA", "UNTRUSTED_INERT"}:
        return ["knowledge_source_trust_invalid"]
    if knowledge["epistemic_role"] not in _KNOWLEDGE_ROLES:
        return ["knowledge_epistemic_role_denied"]
    if knowledge["taxonomy_version"] != "knowledge-taxonomy-v1":
        return ["knowledge_taxonomy_unsupported"]
    expected_domain = content_hash({
        "user_scope": knowledge["user_scope"], "project_scope": knowledge["project_scope"],
        "privacy_domain": knowledge["privacy_domain"],
    })
    if knowledge["identity_domain_hash"] != expected_domain:
        return ["knowledge_identity_domain_invalid"]
    expected_proposition = "proposition-" + content_hash({
        "identity_version": "knowledge-proposition-domain-v1",
        "statement": normalize_text(atom.get("canonical_statement", "")),
        "epistemic_role": knowledge["epistemic_role"], "taxonomy_version": knowledge["taxonomy_version"],
        "identity_domain_hash": knowledge["identity_domain_hash"],
    })[:20]
    if knowledge["proposition_id"] != expected_proposition:
        return ["knowledge_proposition_identity_invalid"]
    if atom.get("scope") != knowledge["project_scope"]:
        return ["knowledge_project_scope_inconsistent"]
    if not isinstance(knowledge["episode_manifest_ids"], list) or not knowledge["episode_manifest_ids"]:
        return ["knowledge_provenance_missing"]
    if knowledge["episode_manifest_ids"] != sorted(set(knowledge["episode_manifest_ids"])):
        return ["knowledge_provenance_invalid"]
    if any("knowledge://" + item not in atom.get("source_refs", []) for item in knowledge["episode_manifest_ids"]):
        return ["knowledge_provenance_missing"]
    if not isinstance(knowledge["source_episodes"], list) or not knowledge["source_episodes"]:
        return ["knowledge_provenance_invalid"]
    episode_ids = []
    for item in knowledge["source_episodes"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"episode_manifest_id", "episode_id", "source_pointer_hash", "recorded_at", "available_at", "source_span", "provenance_quality", "source_trust", "extraction_binding"}
            or not all(
                isinstance(item.get(key), str) and item[key]
                for key in ("episode_manifest_id", "episode_id", "source_pointer_hash", "recorded_at", "available_at", "source_span", "provenance_quality", "source_trust")
            )
            or not re.fullmatch(r"[0-9a-f]{64}", item["source_pointer_hash"])
            or item["source_trust"] not in {"SOURCE_DATA", "UNTRUSTED_INERT"}
            or not _knowledge_extraction_binding_valid(item["extraction_binding"])
        ):
            return ["knowledge_provenance_invalid"]
        try:
            _instant(item["recorded_at"])
            _instant(item["available_at"])
        except (TypeError, ValueError):
            return ["knowledge_provenance_invalid"]
        episode_ids.append(item["episode_manifest_id"])
    if sorted(episode_ids) != knowledge["episode_manifest_ids"]:
        return ["knowledge_provenance_invalid"]
    expected_source_trust = (
        "UNTRUSTED_INERT"
        if any(item["source_trust"] == "UNTRUSTED_INERT" for item in knowledge["source_episodes"])
        else "SOURCE_DATA"
    )
    if knowledge["source_trust"] != expected_source_trust:
        return ["knowledge_source_trust_aggregate_invalid"]
    try:
        valid_from = _instant(knowledge["valid_from"])
        if knowledge.get("valid_to") is not None and _instant(knowledge["valid_to"]) <= valid_from:
            return ["knowledge_valid_time_invalid"]
        _instant(knowledge["recorded_at"])
    except (TypeError, ValueError):
        return ["knowledge_time_invalid"]
    if atom.get("id") != knowledge_atom_id(atom.get("canonical_statement", ""), knowledge):
        return ["knowledge_identity_invalid"]
    return []


def _knowledge_packet_errors(packet: dict[str, Any], atom: dict[str, Any]) -> list[str]:
    knowledge = atom.get("memory_metadata", {}).get("knowledge")
    if not knowledge:
        return []
    if not isinstance(knowledge, dict):
        return ["knowledge_packet_metadata_invalid"]
    manifests = knowledge.get("episode_manifest_ids", [])
    if any(item not in packet.get("source_manifest_ids", []) for item in manifests):
        return ["knowledge_packet_manifest_mismatch"]
    if any("knowledge://" + item not in packet.get("evidence_refs", []) for item in manifests):
        return ["knowledge_packet_evidence_mismatch"]
    report = packet.get("validation_report")
    if not isinstance(report, dict):
        return ["knowledge_packet_validation_missing"]
    fields = (
        "episode_manifest_ids", "source_episodes", "user_scope", "project_scope", "privacy_domain",
        "identity_domain_hash", "proposition_id", "epistemic_role", "taxonomy_version", "provenance_quality",
        "freshness_profile", "valid_to", "safety_class", "source_trust",
    )
    if any(report.get(field) != knowledge.get(field) for field in fields):
        return ["knowledge_packet_validation_mismatch"]
    if any(
        item["extraction_binding"]["full_source_hash"] != packet.get("source_hash")
        for item in knowledge["source_episodes"]
    ):
        return ["knowledge_packet_extraction_binding_mismatch"]
    try:
        if _instant(report.get("valid_from")) != _instant(knowledge.get("valid_from")):
            return ["knowledge_packet_validation_mismatch"]
        if _instant(report.get("recorded_at")) != _instant(knowledge.get("recorded_at")):
            return ["knowledge_packet_validation_mismatch"]
    except (TypeError, ValueError):
        return ["knowledge_packet_validation_mismatch"]
    source_pointer_hash = report.get("source_pointer_hash")
    if not isinstance(source_pointer_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", source_pointer_hash):
        return ["knowledge_packet_source_pointer_hash_required"]
    return []


def _normalized_knowledge_metadata(knowledge: dict[str, Any]) -> dict[str, Any]:
    result = dict(knowledge)
    for field in ("valid_from", "valid_to", "recorded_at"):
        if result.get(field) is not None:
            result[field] = _canonical_instant(result[field])
    if isinstance(result.get("episode_manifest_ids"), list):
        result["episode_manifest_ids"] = sorted(set(result["episode_manifest_ids"]))
    if isinstance(result.get("source_episodes"), list):
        result["source_episodes"] = sorted(result["source_episodes"], key=lambda item: item.get("episode_manifest_id", ""))
    return result


def _knowledge_extraction_binding_valid(binding: Any) -> bool:
    if not isinstance(binding, dict) or set(binding) != {
        "schema_version", "full_source_hash", "extracted_passage_hash", "normalized_start", "normalized_end",
    }:
        return False
    if binding["schema_version"] != "knowledge-extraction-binding-v1":
        return False
    if not all(isinstance(binding[field], str) and re.fullmatch(r"[0-9a-f]{64}", binding[field]) for field in ("full_source_hash", "extracted_passage_hash")):
        return False
    return (
        isinstance(binding["normalized_start"], int)
        and isinstance(binding["normalized_end"], int)
        and 0 <= binding["normalized_start"] < binding["normalized_end"]
    )


def _conversation_packet_errors(packet: dict[str, Any], atom: dict[str, Any]) -> list[str]:
    """Bind a conversation atom to the canonical packet provenance surface."""
    conversation = atom.get("memory_metadata", {}).get("conversation")
    if not conversation:
        return []
    if not isinstance(conversation, dict):
        return ["conversation_packet_metadata_invalid"]
    if _CONVERSATION_DERIVED_FIELDS.intersection(conversation):
        return ["conversation_packet_derived_state_denied"]
    episode_manifest_id = conversation.get("episode_manifest_id")
    source_ref = "conversation://" + str(episode_manifest_id)
    if episode_manifest_id not in packet.get("source_manifest_ids", []):
        return ["conversation_packet_manifest_mismatch"]
    if source_ref not in packet.get("evidence_refs", []):
        return ["conversation_packet_evidence_mismatch"]
    related_manifests = conversation.get("source_episode_manifest_ids", [episode_manifest_id])
    if any(item not in packet.get("source_manifest_ids", []) for item in related_manifests):
        return ["conversation_packet_related_manifest_mismatch"]
    if any("conversation://" + item not in packet.get("evidence_refs", []) for item in related_manifests):
        return ["conversation_packet_related_evidence_mismatch"]
    report = packet.get("validation_report")
    if not isinstance(report, dict):
        return ["conversation_packet_validation_missing"]
    if report.get("source_episode_manifest_ids", related_manifests) != related_manifests:
        return ["conversation_packet_related_manifest_mismatch"]
    source_episodes = conversation.get("source_episodes")
    if source_episodes is not None:
        if not isinstance(source_episodes, list) or not source_episodes:
            return ["conversation_packet_related_provenance_invalid"]
        projected_manifests = [item.get("episode_manifest_id") for item in source_episodes if isinstance(item, dict)]
        if sorted(projected_manifests) != sorted(related_manifests):
            return ["conversation_packet_related_provenance_invalid"]
        for item in source_episodes:
            if (
                not isinstance(item, dict)
                or set(item) != {
                    "episode_manifest_id", "episode_id", "source_pointer_hash", "recorded_at",
                    "valid_time", "provenance_quality",
                }
                or not all(isinstance(item.get(field), str) and item[field] for field in item)
                or not re.fullmatch(r"[0-9a-f]{64}", item["source_pointer_hash"])
            ):
                return ["conversation_packet_related_provenance_invalid"]
        if report.get("source_episodes", source_episodes) != source_episodes:
            return ["conversation_packet_related_provenance_invalid"]
    external_id_hash = conversation.get("daily_candidate_id_hash")
    if external_id_hash is not None and (
        not isinstance(external_id_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", external_id_hash)
    ):
        return ["conversation_external_candidate_identity_invalid"]
    external_id_hashes = conversation.get("daily_candidate_id_hashes", [])
    if (
        not isinstance(external_id_hashes, list)
        or external_id_hashes != sorted(set(external_id_hashes))
        or any(not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{64}", item) for item in external_id_hashes)
        or (external_id_hash is not None and external_id_hash not in external_id_hashes)
    ):
        return ["conversation_external_candidate_identity_invalid"]
    confidence = conversation.get("candidate_confidence")
    if confidence is not None and (
        not isinstance(confidence, (int, float)) or isinstance(confidence, bool)
        or not 0.0 <= float(confidence) <= 1.0 or float(atom.get("confidence", -1)) != float(confidence)
    ):
        return ["conversation_candidate_confidence_invalid"]
    fields = ("user_scope", "project_scope", "privacy_class", "coverage", "source_class", "claim_role")
    if any(report.get(field) != conversation.get(field) for field in fields):
        return ["conversation_packet_validation_mismatch"]
    try:
        if _instant(report.get("valid_from")) != _instant(conversation.get("valid_from")):
            return ["conversation_packet_validation_mismatch"]
        if _instant(report.get("recorded_at")) != _instant(conversation.get("recorded_at")):
            return ["conversation_packet_validation_mismatch"]
        report_valid_to = report.get("valid_to")
        atom_valid_to = conversation.get("valid_to")
        if (report_valid_to is None) != (atom_valid_to is None):
            return ["conversation_packet_validation_mismatch"]
        if report_valid_to is not None and _instant(report_valid_to) != _instant(atom_valid_to):
            return ["conversation_packet_validation_mismatch"]
    except (TypeError, ValueError):
        return ["conversation_packet_validation_mismatch"]
    source_pointer_hash = report.get("source_pointer_hash")
    if not isinstance(source_pointer_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", source_pointer_hash):
        return ["conversation_packet_source_pointer_hash_required"]
    return []


def _normalized_conversation_metadata(conversation: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize accepted instants before packet identity and storage."""
    normalized = dict(conversation)
    for field in ("valid_from", "recorded_at"):
        if isinstance(normalized.get(field), str):
            normalized[field] = _canonical_instant(normalized[field])
    if isinstance(normalized.get("valid_to"), str):
        normalized["valid_to"] = _canonical_instant(normalized["valid_to"])
    return normalized


def _is_prompt_injection(value: Any) -> bool:
    text = normalize_text(str(value)).casefold()
    return any(marker in text for marker in _PROMPT_INJECTION_MARKERS) or bool(re.search(
        r"ignore\s+(?:all\s+)?(?:previous|earlier)\s+instructions|"
        r"disregard\s+(?:all\s+)?instructions|忽略(?:之前|先前|所有)?指令",
        text,
    ))


def _instant(value: str):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone_required")
    return parsed.astimezone(timezone.utc)


def _canonical_instant(value: str) -> str:
    return _instant(value).isoformat().replace("+00:00", "Z")
