"""Deterministic candidate-only LearningPacket assembly and verification."""

from __future__ import annotations

import re
from typing import Any

from .canonical import atom_id, content_hash, normalize_text, packet_id, relation_id
from .security import contains_credential_value


SCHEMA_VERSION = "1.0.0"
PROCESSOR_VERSION = "p3-integrated-offline-memory-1.0.0"
_SECRET = re.compile(r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")


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
        statement = normalize_text(str(atom.get("statement", "")))
        atom_type = normalize_text(str(atom.get("atom_type", "observation"))).lower()
        scope = normalize_text(str(atom.get("scope", "")))
        normalized_atoms.append({
            "id": atom.get("id") or atom_id(statement, atom_type, scope),
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
    if contains_credential_value(packet):
        errors.append("credential_value_denied")
    atom_ids = [item.get("id") for item in packet.get("atoms", [])]
    if any(not item for item in atom_ids) or len(atom_ids) != len(set(atom_ids)):
        errors.append("atom_identity_invalid")
    atom_set = set(atom_ids)
    for relation in packet.get("relations", []):
        if relation.get("source_atom_id") not in atom_set or relation.get("target_atom_id") not in atom_set:
            errors.append("relation_endpoint_missing")
    if packet.get("packet_id") and packet.get("packet_content_hash"):
        expected_key = packet["packet_id"] + "-" + packet["packet_content_hash"][:16]
        if packet.get("idempotency_key") != expected_key:
            errors.append("idempotency_key_mismatch")
    return {"valid": not errors, "errors": errors}
