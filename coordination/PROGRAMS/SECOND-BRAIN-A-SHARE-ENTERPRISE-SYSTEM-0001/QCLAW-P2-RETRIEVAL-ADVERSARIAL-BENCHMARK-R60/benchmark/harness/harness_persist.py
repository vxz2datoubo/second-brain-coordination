from __future__ import annotations
from harness_common import *

def _persist_conversation(store: Any, spec: dict[str, Any], index: int) -> PersistedFixture:
    from integrated_offline_memory.conversation_memory import (
        build_conversation_candidate,
        build_conversation_correction,
    )
    user = spec["user"]
    project = spec["project"]
    ep = _episode(user, project, f"fixture-{index}")
    valid_from = spec.get("valid_from", "2026-08-14T00:00:00Z")
    valid_to = spec.get("valid_to")
    base = build_conversation_candidate(
        episode=ep,
        statement=spec["stmt"],
        claim_role="USER_ASSERTION",
        valid_from=valid_from,
        valid_to=valid_to,
    )
    atom = copy.deepcopy(base["atoms"][0])

    # Packet-bound fixture state must be applied to the packet actually imported.
    # Derived supersession fields are intentionally NOT forged here.
    status = spec.get("status", "candidate")
    if status != "superseded":
        atom["knowledge_status"] = status
    if spec.get("visibility") is not None:
        atom["transport_visibility"] = spec["visibility"]
    # Q60-B06: materialize the corpus' missing-provenance fixture on the exact
    # atom sent through the canonical packet builder. The canonical validator
    # must then fail closed with conversation_provenance_missing; this condition
    # may not silently disappear behind builder-generated source_refs.
    if spec.get("no_source_refs"):
        atom["source_refs"] = []
    meta = copy.deepcopy(atom.get("memory_metadata", {}))
    conv = copy.deepcopy(meta.get("conversation", {}))
    if spec.get("palace") is not None:
        conv["memory_palace"] = copy.deepcopy(spec["palace"])
    elif spec.get("palace_freshness") is not None:
        conv["memory_palace"] = {
            "freshness_profile": spec["palace_freshness"],
            "freshness_horizon_hours": int(spec.get("palace_horizon", 1)),
            "last_verified_at": spec.get("palace_last_verified"),
            "revalidation_required": True,
        }
    if spec.get("no_packet_lineage"):
        conv.pop("episode_manifest_id", None)
        conv.pop("source_episode_manifest_ids", None)
        conv.pop("source_episodes", None)
    meta["conversation"] = conv
    atom["memory_metadata"] = meta
    packet = _rebuild_packet(base, atom)
    receipt = store.import_learning_packet(packet)
    actual_id = packet["atoms"][0]["id"]
    persisted = store.get_atom(actual_id)
    if receipt.get("status") not in {"IMPORTED", "IDEMPOTENT_DUPLICATE"} or persisted is None:
        raise AssertionError("conversation_fixture_not_persisted")

    # effective_valid_to/superseded_by are derived-only in the canonical contract.
    # Exercise them only through a real USER_CORRECTION.
    if status == "superseded" or spec.get("effective_valid_to") is not None or spec.get("superseded_by") is not None:
        correction_at = spec.get("effective_valid_to")
        if correction_at is None and status == "superseded" and valid_to is not None:
            correction_at = valid_to
        if correction_at is None:
            from datetime import datetime, timedelta, timezone
            raw_start = str(valid_from)
            parsed = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            correction_at = (parsed + timedelta(hours=1)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        correction = build_conversation_correction(
            episode=ep,
            statement=f"R60 synthetic correction for fixture {index}",
            replaces_atom_id=actual_id,
            valid_from=correction_at,
        )
        store.import_learning_packet(correction)
        persisted = store.get_atom(actual_id)
        if persisted is None:
            raise AssertionError("conversation_supersession_target_missing")
        conv_state = persisted.get("memory_metadata", {}).get("conversation", {})
        if persisted.get("knowledge_status") != "superseded":
            raise AssertionError("conversation_supersession_not_persisted")
        if spec.get("effective_valid_to") is not None and conv_state.get("effective_valid_to") != spec["effective_valid_to"]:
            raise AssertionError("conversation_effective_valid_to_not_persisted")
        # Fixture aliases may name a target, but canonical superseded_by must be the
        # actual correction atom identity. Never overwrite it with fixture prose.
        if not conv_state.get("superseded_by"):
            raise AssertionError("conversation_superseded_by_not_persisted")

    return PersistedFixture(index, spec, actual_id, persisted)


def _persist_knowledge(store: Any, spec: dict[str, Any], index: int) -> PersistedFixture:
    """Persist one governed synthetic knowledge fixture through the canonical packet/import path.

    This deliberately does not use optional fixture IDs.  The actual object
    identity is computed by the current knowledge contract and then resolved
    back from the store.  Negative contract fixtures (private safety or missing
    identity) fail on the same packet verifier used by production code.
    """
    from integrated_offline_memory.canonical import content_hash, normalize_text
    from integrated_offline_memory.learning_packet import build_learning_packet, knowledge_atom_id

    user = str(spec["user"])
    project = str(spec["project"])
    domain = str(spec.get("domain", "synthetic-alpha"))
    statement = str(spec["stmt"])
    recorded_at = "2026-08-14T00:00:00Z"
    valid_from = str(spec.get("valid_from", recorded_at))
    episode_id = f"r60-k-{index}"
    source_pointer = f"synthetic://r60/knowledge/{index}"
    source_hash = content_hash({"normalized_source_text": normalize_text(statement)})
    identity_domain_hash = content_hash({
        "user_scope": user, "project_scope": project, "privacy_domain": domain,
    })
    manifest_id = "knowledge-episode-" + content_hash({
        "episode_id": episode_id,
        "source_hash": source_hash,
        "recorded_at": recorded_at,
        "identity_domain_hash": identity_domain_hash,
    })[:20]
    epistemic_role = "SOURCE_CLAIM"
    proposition = "proposition-" + content_hash({
        "identity_version": "knowledge-proposition-domain-v1",
        "statement": normalize_text(statement),
        "epistemic_role": epistemic_role,
        "taxonomy_version": "knowledge-taxonomy-v1",
        "identity_domain_hash": identity_domain_hash,
    })[:20]
    source_episode = {
        "episode_manifest_id": manifest_id,
        "episode_id": episode_id,
        "source_pointer_hash": content_hash(source_pointer),
        "recorded_at": recorded_at,
        "available_at": recorded_at,
        "source_span": "full",
        "provenance_quality": "DIRECT",
        "source_trust": "SOURCE_DATA",
        "extraction_binding": {
            "schema_version": "knowledge-extraction-binding-v1",
            "full_source_hash": source_hash,
            "extracted_passage_hash": content_hash({"normalized_extracted_passage": normalize_text(statement)}),
            "normalized_start": 0,
            "normalized_end": len(normalize_text(statement)),
        },
    }
    knowledge = {
        "schema_version": "knowledge-atom-v1",
        "episode_manifest_ids": [manifest_id],
        "source_episodes": [source_episode],
        "user_scope": user,
        "project_scope": project,
        "privacy_domain": domain,
        "identity_domain_hash": identity_domain_hash,
        "proposition_id": proposition,
        "epistemic_role": epistemic_role,
        "taxonomy_version": "knowledge-taxonomy-v1",
        "valid_from": valid_from,
        "recorded_at": recorded_at,
        "provenance_quality": "DIRECT",
        "freshness_profile": str(spec.get("freshness", spec.get("freshness_profile", "STRUCTURAL"))),
        "safety_class": str(spec.get("safety_class", "PUBLIC_SAFE_SYNTHETIC")),
        "source_trust": "SOURCE_DATA",
    }
    if spec.get("reval_required") is not None:
        knowledge["revalidation_required"] = bool(spec.get("reval_required"))
    if spec.get("last_verified") is not None:
        knowledge["last_verified_at"] = str(spec["last_verified"])
    if spec.get("horizon") is not None:
        knowledge["freshness_horizon_hours"] = int(spec["horizon"])
    if spec.get("missing_identity"):
        knowledge.pop("identity_domain_hash", None)
        knowledge.pop("proposition_id", None)

    source_ref = "knowledge://" + manifest_id
    atom = {
        "id": knowledge_atom_id(statement, knowledge),
        "statement": statement,
        "atom_type": "knowledge_atom",
        "scope": project,
        "confidence": 0.5,
        "source_refs": [source_ref],
        "knowledge_status": str(spec.get("status", "candidate")),
        "transport_visibility": "PUBLIC_SAFE_METADATA_ONLY",
        "memory_metadata": {"knowledge": knowledge},
    }
    validation = dict(knowledge)
    validation["source_pointer_hash"] = content_hash(source_pointer)
    packet = build_learning_packet(
        source_manifest_ids=[manifest_id], source_hash=source_hash,
        validation_report=validation, evidence_refs=[source_ref], atoms=[atom],
    )
    receipt = store.import_learning_packet(packet)
    actual_id = packet["atoms"][0]["id"]
    persisted = store.get_atom(actual_id)
    if receipt.get("status") not in {"IMPORTED", "IDEMPOTENT_DUPLICATE"} or persisted is None:
        raise AssertionError("knowledge_fixture_not_persisted")
    return PersistedFixture(index, spec, actual_id, persisted)

def _persist_fixtures(store: Any, setup: dict[str, Any]) -> tuple[list[PersistedFixture], dict[str, str]]:
    records: list[PersistedFixture] = []
    aliases: dict[str, str] = {}
    for index, spec in enumerate(setup.get("atoms", [])):
        kind = spec.get("kind")
        if kind == "plain":
            atom = _plain_atom(spec["stmt"], spec.get("scope", "p1"), spec.get("status", "candidate"))
            store.insert_atom(atom)
            persisted = store.get_atom(atom["id"])
            if persisted is None:
                raise AssertionError("plain_fixture_not_persisted")
            record = PersistedFixture(index, spec, atom["id"], persisted)
        elif kind == "conversation":
            record = _persist_conversation(store, spec, index)
        elif kind == "knowledge":
            record = _persist_knowledge(store, spec, index)
        else:
            raise ValueError(f"unsupported_fixture_kind:{kind}")
        records.append(record)
        hint = spec.get("id_hint")
        if hint:
            aliases[str(hint)] = record.atom_id
        aliases[record.atom_id] = record.atom_id
    return records, aliases

def _persist_relations(store: Any, setup: dict[str, Any], aliases: dict[str, str]) -> None:
    from integrated_offline_memory.canonical import relation_id
    for spec in setup.get("relations", []):
        source = _resolve_alias(str(spec["source"]), aliases)
        target = _resolve_alias(str(spec["target"]), aliases)
        rel_type = spec.get("type", "supports")
        store.insert_relation({
            "id": relation_id(source, target, rel_type),
            "relation_type": rel_type,
            "source_atom_id": source,
            "target_atom_id": target,
            "confidence": 0.5,
        })


def _persist_unknowns(store: Any, setup: dict[str, Any], records: list[PersistedFixture], aliases: dict[str, str]) -> None:
    """Persist corpus unknown fixtures through LearningPacket import, not SQL shortcuts."""
    if not setup.get("unknowns"):
        return
    from integrated_offline_memory.canonical import content_hash
    from integrated_offline_memory.learning_packet import build_learning_packet
    if not records:
        raise ValueError("unknown_fixture_requires_anchor_atom")
    anchor = records[0].atom
    unknowns: list[dict[str, Any]] = []
    for index, spec in enumerate(setup.get("unknowns", [])):
        related = [_resolve_alias(str(item), aliases) for item in spec.get("related", [])]
        unknowns.append({
            "id": "unk-r60-" + content_hash({"index": index, "question": spec["question"], "related": related})[:20],
            "question": spec["question"],
            "scope": spec.get("scope", anchor.get("scope", "")),
            "related_atom_ids": related,
            "source_refs": [],
            "status": "OPEN",
        })
    packet = build_learning_packet(
        source_manifest_ids=["r60-synthetic-unknown-fixture"],
        source_hash=content_hash({"fixture": "r60-unknowns"}),
        validation_report={"fixture": "r60-public-safe-unknowns", "source_pointer_hash": "0" * 64},
        evidence_refs=[], atoms=[anchor], unknowns=unknowns,
    )
    store.import_learning_packet(packet)

__all__ = [name for name in globals() if not name.startswith("__")]
