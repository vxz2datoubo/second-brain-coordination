"""Candidate-only bridge from governed replay evidence into semantic memory."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .canonical import atom_id, content_hash
from .learning_packet import build_learning_packet
from .memory_store import MemoryStore
from .replay_bridge import ReplayReceipt
from .retrieval import ContextAssembler, ContextBundle, QueryPlan


FLOW_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class IntegratedFlowReceipt:
    schema_version: str
    run_id: str
    trace_id: str
    packet_id: str
    packet_content_hash: str
    idempotency_key: str
    import_status: str
    knowledge_version: str
    query_plan_hash: str
    context_bundle_hash: str
    retrieved_atom_ids: tuple[str, ...]
    unknown_ids: tuple[str, ...]
    source_lineage: tuple[str, ...]
    research_only: bool = True
    no_trade_gate: bool = True
    authority_write: bool = False
    raw_records_exported: bool = False

    def public_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        for field_name in ("retrieved_atom_ids", "unknown_ids", "source_lineage"):
            payload[field_name] = list(payload[field_name])
        return payload


def replay_receipt_to_learning_packet(receipt: ReplayReceipt) -> dict[str, Any]:
    """Convert an aggregate-only replay receipt into a candidate packet."""
    _validate_replay_boundary(receipt)
    source_refs = [
        f"manifest:{receipt.source_manifest_id}",
        f"artifact-sha256:{receipt.artifact_sha256}",
        f"replay-run:{receipt.run_id}",
        f"replay-core:{receipt.replay_core_hash}",
    ]
    atom_specs = [
        {
            "atom_type": "observation",
            "statement": (
                f"TDX day source {receipt.symbol}.{receipt.exchange} produced "
                f"{receipt.accepted_bar_count} accepted historical daily bars from "
                f"{receipt.first_date} through {receipt.last_date}."
            ),
            "scope": "a_share.offline_market_data",
            "confidence": 0.75,
            "verification_status": receipt.source_validation_status,
            "evidence_quality": "PARTIAL_FIELD_EVIDENCE",
            "source_refs": source_refs,
            "failure_conditions": [
                "artifact_sha256_changes",
                "manifest_or_activation_policy_changes",
                "parser_semantics_version_changes",
            ],
        },
        {
            "atom_type": "validation_result",
            "statement": (
                f"P2 deterministic replay {receipt.run_id} completed with replay core hash "
                f"{receipt.replay_core_hash}; this establishes reproducibility only, not alpha or profitability."
            ),
            "scope": "a_share.offline_replay",
            "confidence": 0.8,
            "verification_status": receipt.strategy_validation_status,
            "evidence_quality": "DETERMINISTIC_LOCAL_REPLAY",
            "source_refs": source_refs,
            "premises": ["research_only", "no_trade", "aggregate_only_receipt"],
            "exceptions": ["market_validity_not_established", "profitability_not_established"],
        },
        {
            "atom_type": "governance_rule",
            "statement": (
                "TDX day amount and reserved fields remain excluded from authoritative features, "
                "and the vendor volume unit remains unknown."
            ),
            "scope": "a_share.field_semantics",
            "confidence": 0.9,
            "verification_status": "PARTIALLY_VERIFIED",
            "evidence_quality": "PARTIAL_FIELD_EVIDENCE",
            "source_refs": source_refs,
            "failure_conditions": ["official_vendor_field_documentation_supersedes_current_decision"],
        },
    ]
    atom_ids = [
        atom_id(spec["statement"], spec["atom_type"], spec["scope"])
        for spec in atom_specs
    ]
    unknowns = [
        {
            "id": "unk-" + content_hash({"run_id": receipt.run_id, "unknown": unknown})[:20],
            "question": unknown,
            "scope": "a_share.offline_replay",
            "related_atom_ids": atom_ids,
            "source_refs": source_refs,
            "status": "OPEN",
        }
        for unknown in receipt.unknowns
    ]
    validation_report = {
        "schema_version": receipt.schema_version,
        "run_id": receipt.run_id,
        "trace_id": receipt.trace_id,
        "source_validation_status": receipt.source_validation_status,
        "strategy_validation_status": receipt.strategy_validation_status,
        "accepted_bar_count": receipt.accepted_bar_count,
        "parser_quarantine_count": receipt.parser_quarantine_count,
        "replay_quarantine_count": receipt.replay_quarantine_count,
        "parse_core_hash": receipt.parse_core_hash,
        "replay_core_hash": receipt.replay_core_hash,
        "replay_input_hash": receipt.replay_input_hash,
        "availability_policy_version": receipt.availability_policy_version,
        "economic_or_alpha_claim": "NOT_ESTABLISHED",
        "research_only": True,
        "no_trade_gate": True,
        "authority_write": False,
    }
    return build_learning_packet(
        source_manifest_ids=[receipt.source_manifest_id],
        source_hash=receipt.artifact_sha256,
        validation_report=validation_report,
        evidence_refs=source_refs,
        atoms=atom_specs,
        unknowns=unknowns,
    )


def run_integrated_flow(
    receipt: ReplayReceipt,
    store: MemoryStore,
    *,
    query_plan: QueryPlan | None = None,
) -> tuple[IntegratedFlowReceipt, dict[str, Any], ContextBundle]:
    """Import a candidate packet and retrieve it through the governed query path."""
    packet = replay_receipt_to_learning_packet(receipt)
    import_result = store.import_learning_packet(packet)
    plan = query_plan or QueryPlan(
        query_text="TDX day deterministic replay field semantics",
        scopes=(
            "a_share.offline_market_data",
            "a_share.offline_replay",
            "a_share.field_semantics",
        ),
        include_conflicts=True,
        include_unknowns=True,
        relation_depth=1,
        budget=50,
    )
    bundle = ContextAssembler(store).assemble(plan)
    packet_atom_ids = {item["id"] for item in packet["atoms"]}
    retrieved_atom_ids = tuple(item["id"] for item in bundle.atoms if item["id"] in packet_atom_ids)
    if not retrieved_atom_ids:
        raise RuntimeError("candidate_packet_not_retrievable")
    flow_receipt = IntegratedFlowReceipt(
        schema_version=FLOW_SCHEMA_VERSION,
        run_id=receipt.run_id,
        trace_id=receipt.trace_id,
        packet_id=packet["packet_id"],
        packet_content_hash=packet["packet_content_hash"],
        idempotency_key=packet["idempotency_key"],
        import_status=import_result["status"],
        knowledge_version=bundle.knowledge_version,
        query_plan_hash=plan.plan_hash,
        context_bundle_hash=context_bundle_semantic_hash(bundle),
        retrieved_atom_ids=retrieved_atom_ids,
        unknown_ids=tuple(item["id"] for item in bundle.unknowns),
        source_lineage=bundle.source_lineage,
    )
    return flow_receipt, packet, bundle


def context_bundle_semantic_hash(bundle: ContextBundle) -> str:
    """Hash semantic context while excluding database wall-clock metadata."""
    payload = bundle.to_dict()
    payload["atoms"] = [
        {key: value for key, value in atom.items() if key not in {"created_at", "updated_at"}}
        for atom in payload["atoms"]
    ]
    return content_hash(payload)


def _validate_replay_boundary(receipt: ReplayReceipt) -> None:
    if not receipt.research_only or not receipt.no_trade_gate:
        raise ValueError("replay_research_boundary_required")
    if receipt.authority_write:
        raise ValueError("replay_authority_write_denied")
    if receipt.raw_records_exported:
        raise ValueError("raw_record_export_denied")
    if receipt.source_validation_status not in {"PARTIALLY_VERIFIED", "UNVERIFIED"}:
        raise ValueError("source_validation_overclaim_denied")
