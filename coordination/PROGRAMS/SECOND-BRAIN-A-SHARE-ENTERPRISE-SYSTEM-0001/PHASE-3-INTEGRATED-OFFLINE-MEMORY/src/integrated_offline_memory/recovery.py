"""Deterministic local rebuild support for the canonical memory runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .canonical import content_hash
from .memory_store import MemoryStore
from .security import assert_no_credential_value


@dataclass(frozen=True)
class MemoryRebuildBundle:
    schema_version: str
    packets: tuple[dict[str, Any], ...]
    knowledge_sources: tuple[dict[str, Any], ...]
    unknown_statuses: tuple[dict[str, str], ...]
    feedback_receipts: tuple[dict[str, Any], ...]
    bundle_hash: str
    local_only: bool = True
    authority_write: bool = False
    no_trade_gate: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for name in ("packets", "knowledge_sources", "unknown_statuses", "feedback_receipts"):
            payload[name] = list(payload[name])
        return payload


@dataclass(frozen=True)
class RebuildReceipt:
    schema_version: str
    bundle_hash: str
    packet_count: int
    atom_count: int
    semantic_state_hash: str
    integrity_ok: bool
    authority_write: bool = False
    no_trade_gate: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def export_rebuild_bundle(store: MemoryStore) -> MemoryRebuildBundle:
    core = {
        "schema_version": "1.0.0",
        "packets": store.all_learning_packets(),
        "knowledge_sources": store.all_knowledge_sources(),
        "unknown_statuses": store.all_unknown_statuses(),
        "feedback_receipts": [
            {key: value for key, value in item.items() if key != "recorded_at"}
            for item in store.all_feedback_receipts()
        ],
        "local_only": True,
        "authority_write": False,
        "no_trade_gate": True,
    }
    assert_no_credential_value(core)
    bundle_hash = content_hash(core)
    return MemoryRebuildBundle(
        schema_version="1.0.0",
        packets=tuple(core["packets"]),
        knowledge_sources=tuple(core["knowledge_sources"]),
        unknown_statuses=tuple(core["unknown_statuses"]),
        feedback_receipts=tuple(core["feedback_receipts"]),
        bundle_hash=bundle_hash,
    )


def rebuild_memory_store(bundle: MemoryRebuildBundle, db_path: str | Path = ":memory:") -> tuple[MemoryStore, RebuildReceipt]:
    if bundle.schema_version != "1.0.0":
        raise ValueError("rebuild_bundle_schema_unsupported")
    if bundle.authority_write or not bundle.no_trade_gate or not bundle.local_only:
        raise ValueError("rebuild_bundle_governance_boundary")
    if bundle.bundle_hash != _bundle_hash(bundle):
        raise ValueError("rebuild_bundle_hash_mismatch")
    assert_no_credential_value(bundle.to_dict())
    store = MemoryStore(db_path).connect()
    try:
        for source in bundle.knowledge_sources:
            store.register_knowledge_source(
                manifest_id=source["manifest_id"],
                manifest_hash=source["manifest_hash"],
                policy_id=source["policy_id"],
                public_metadata=source["public_metadata"],
            )
        for packet in bundle.packets:
            store.import_learning_packet(packet)
        for state in bundle.unknown_statuses:
            if state["status"] != "OPEN":
                store.restore_unknown_status(state["unknown_id"], state["status"])
        for source in bundle.knowledge_sources:
            if source["status"] == "REVOKED":
                store.revoke_knowledge_source(source["manifest_id"], "rebuild_preserved_revocation")
        for receipt in bundle.feedback_receipts:
            store.record_feedback_receipt(receipt)
        integrity = store.integrity_check()
        result = RebuildReceipt(
            schema_version="1.0.0",
            bundle_hash=bundle.bundle_hash,
            packet_count=len(bundle.packets),
            atom_count=store.stats()["atoms"],
            semantic_state_hash=store.semantic_state_hash(),
            integrity_ok=integrity["integrity_ok"],
        )
        return store, result
    except Exception:
        store.close()
        raise


def _bundle_hash(bundle: MemoryRebuildBundle) -> str:
    payload = bundle.to_dict()
    payload.pop("bundle_hash")
    return content_hash(payload)
