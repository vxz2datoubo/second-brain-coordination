"""Deterministic evidence packaging on top of the canonical query runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .canonical import content_hash
from .memory_store import MemoryStore
from .retrieval import ContextAssembler, ContextBundle, QueryPlan
from .security import assert_no_credential_value


@dataclass(frozen=True)
class AnswerEvidenceBundle:
    schema_version: str
    bundle_id: str
    semantic_hash: str
    query_id: str
    query_plan_hash: str
    knowledge_version: str
    history_mode: str
    selected_evidence: tuple[dict[str, Any], ...]
    relations: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...]
    unknowns: tuple[dict[str, Any], ...]
    source_lineage: tuple[str, ...]
    omitted_evidence: tuple[dict[str, str], ...]
    abstained: bool
    abstention_reasons: tuple[str, ...]
    uncertainty_reasons: tuple[str, ...]
    semantic_access_state: str
    authority_write: bool = False
    no_trade_gate: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for name in (
            "selected_evidence", "relations", "conflicts", "unknowns",
            "source_lineage", "omitted_evidence", "abstention_reasons",
            "uncertainty_reasons",
        ):
            payload[name] = list(payload[name])
        return payload


class AnswerEvidenceCompiler:
    """Compile a ContextBundle without creating a second retrieval path."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.assembler = ContextAssembler(store)

    def compile(
        self,
        plan: QueryPlan,
        context: ContextBundle | None = None,
    ) -> AnswerEvidenceBundle:
        plan.validate()
        context = context or self.assembler.assemble(plan)
        if context.query_plan_hash != plan.plan_hash:
            raise ValueError("answer_evidence_query_plan_mismatch")
        assert_no_credential_value(plan.to_dict())
        assert_no_credential_value(context.to_dict())

        direct_scores = self.store.search_term_scores(plan.query_text)
        for alias in plan.query_aliases:
            for atom_id, score in self.store.search_term_scores(alias).items():
                direct_scores[atom_id] = direct_scores.get(atom_id, 0.0) + score
        relation_ids = {
            endpoint
            for relation in context.relations
            for endpoint in (relation["source_atom_id"], relation["target_atom_id"])
        }
        conflict_ids = {
            endpoint
            for conflict in context.conflicts
            for endpoint in (conflict["atom_id_a"], conflict["atom_id_b"])
        }
        selected: list[dict[str, Any]] = []
        for atom in context.atoms:
            atom_id = atom["id"]
            if direct_scores.get(atom_id, 0.0) > 0:
                reason = "DIRECT_QUERY_MATCH"
            elif atom_id in conflict_ids:
                reason = "CONFLICT_COUNTERPART"
            elif atom_id in relation_ids:
                reason = "RELATED_CONTEXT"
            else:
                reason = "STRUCTURED_FILTER_MATCH"
            selected.append({
                "atom_id": atom_id,
                "selection_reason": reason,
                "atom": atom,
            })

        abstention_reasons: list[str] = []
        if not selected:
            abstention_reasons.append("NO_RETRIEVABLE_EVIDENCE")
        if selected and not context.source_lineage:
            abstention_reasons.append("SOURCE_LINEAGE_MISSING")
        if selected and all(_is_unverified_unknown(item["atom"]) for item in selected):
            abstention_reasons.append("ONLY_UNVERIFIED_UNKNOWN_EVIDENCE")

        uncertainty_reasons: list[str] = []
        if context.conflicts:
            uncertainty_reasons.append("UNRESOLVED_CONFLICT_PRESENT")
        if context.unknowns:
            uncertainty_reasons.append("OPEN_UNKNOWN_PRESENT")
        if context.omitted_due_to_budget:
            uncertainty_reasons.append("CONTEXT_BUDGET_OMISSION")
        if any(item["atom"].get("exceptions") or item["atom"].get("failure_conditions") for item in selected):
            uncertainty_reasons.append("CONDITIONAL_EVIDENCE_PRESENT")

        semantic_payload = {
            "schema_version": "1.0.0",
            "query_id": context.query_id,
            "query_plan_hash": context.query_plan_hash,
            "knowledge_version": context.knowledge_version,
            "history_mode": plan.history_mode,
            "selected_evidence": [
                {**item, "atom": _semantic_atom(item["atom"])} for item in selected
            ],
            "relations": list(context.relations),
            "conflicts": list(context.conflicts),
            "unknowns": list(context.unknowns),
            "source_lineage": list(context.source_lineage),
            "omitted_evidence": [
                {"atom_id": atom_id, "reason": "CONTEXT_BUDGET_EXCEEDED"}
                for atom_id in context.omitted_due_to_budget
            ],
            "abstained": bool(abstention_reasons),
            "abstention_reasons": abstention_reasons,
            "uncertainty_reasons": uncertainty_reasons,
            "semantic_access_state": context.semantic_access_state,
            "authority_write": False,
            "no_trade_gate": True,
        }
        semantic_hash = content_hash(semantic_payload)
        result = AnswerEvidenceBundle(
            bundle_id="aeb-" + semantic_hash[:20],
            semantic_hash=semantic_hash,
            selected_evidence=tuple(selected),
            relations=context.relations,
            conflicts=context.conflicts,
            unknowns=context.unknowns,
            source_lineage=context.source_lineage,
            omitted_evidence=tuple(semantic_payload["omitted_evidence"]),
            abstained=bool(abstention_reasons),
            abstention_reasons=tuple(abstention_reasons),
            uncertainty_reasons=tuple(uncertainty_reasons),
            schema_version="1.0.0",
            query_id=context.query_id,
            query_plan_hash=context.query_plan_hash,
            knowledge_version=context.knowledge_version,
            history_mode=plan.history_mode,
            semantic_access_state=context.semantic_access_state,
        )
        assert_no_credential_value(result.to_dict())
        return result


def _is_unverified_unknown(atom: dict[str, Any]) -> bool:
    return (
        atom.get("verification_status") == "UNVERIFIED"
        and atom.get("evidence_quality") == "UNKNOWN"
    )


def _semantic_atom(atom: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in atom.items() if key not in {"created_at", "updated_at"}}
