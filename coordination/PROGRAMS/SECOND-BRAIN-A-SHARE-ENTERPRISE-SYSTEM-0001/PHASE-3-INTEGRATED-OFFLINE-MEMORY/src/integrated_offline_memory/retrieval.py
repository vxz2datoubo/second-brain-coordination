"""Structured multilingual retrieval and deterministic ContextBundle assembly."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .canonical import content_hash
from .memory_store import ALLOWED_TRUTH_STATES, DENIED_TRUTH_STATES, MemoryStore


@dataclass(frozen=True)
class QueryPlan:
    query_text: str = ""
    scopes: tuple[str, ...] = ()
    atom_types: tuple[str, ...] = ()
    truth_states: tuple[str, ...] = ("candidate", "approved", "conflict", "superseded", "unknown")
    min_confidence: float = 0.0
    time_start: str | None = None
    time_end: str | None = None
    include_conflicts: bool = True
    include_unknowns: bool = True
    relation_depth: int = 0
    budget: int = 50
    schema_version: str = "1.0.0"

    def validate(self) -> None:
        if self.schema_version.split(".", 1)[0] != "1":
            raise ValueError("query_plan_schema_major_unsupported")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("query_plan_confidence_invalid")
        if not 1 <= self.budget <= 1000:
            raise ValueError("query_plan_budget_invalid")
        if not 0 <= self.relation_depth <= 4:
            raise ValueError("query_plan_relation_depth_invalid")
        states = set(self.truth_states)
        if states.intersection(DENIED_TRUTH_STATES) or not states.issubset(ALLOWED_TRUTH_STATES):
            raise ValueError("query_plan_truth_state_denied_or_unknown")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        for field_name in ("scopes", "atom_types", "truth_states"):
            payload[field_name] = list(payload[field_name])
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "QueryPlan":
        unknown = set(payload) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError("query_plan_unknown_field")
        data = dict(payload)
        for field_name in ("scopes", "atom_types", "truth_states"):
            if field_name in data:
                data[field_name] = tuple(data[field_name])
        result = cls(**data)
        result.validate()
        return result

    @property
    def plan_hash(self) -> str:
        return content_hash(self.to_dict())


@dataclass(frozen=True)
class ContextBundle:
    schema_version: str
    query_id: str
    query_plan_hash: str
    knowledge_version: str
    atoms: tuple[dict[str, Any], ...]
    relations: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...]
    unknowns: tuple[dict[str, Any], ...]
    source_lineage: tuple[str, ...]
    omitted_due_to_budget: tuple[str, ...]
    context_budget: int
    semantic_access_state: str
    authority_write: bool = False
    no_trade_gate: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for field_name in ("atoms", "relations", "conflicts", "unknowns", "source_lineage", "omitted_due_to_budget"):
            payload[field_name] = list(payload[field_name])
        return payload


class ContextAssembler:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def assemble(self, plan: QueryPlan) -> ContextBundle:
        plan.validate()
        score_map = self.store.search_term_scores(plan.query_text)
        candidates: dict[str, float] = {}
        for atom_id, score in score_map.items():
            atom = self.store.get_atom(atom_id)
            if atom is not None and self._allowed(atom, plan):
                candidates[atom_id] = score

        frontier = set(candidates)
        visited = set(frontier)
        for depth in range(plan.relation_depth):
            related = self.store.related_atom_ids(frontier) - visited
            next_frontier: set[str] = set()
            for atom_id in related:
                atom = self.store.get_atom(atom_id)
                if atom is not None and self._allowed(atom, plan):
                    candidates[atom_id] = max(candidates.get(atom_id, 0.0), 0.5 / (depth + 1))
                    next_frontier.add(atom_id)
            visited.update(next_frontier)
            frontier = next_frontier
            if not frontier:
                break

        ranked_ids = sorted(candidates, key=lambda atom_id: (-candidates[atom_id], atom_id))
        selected_ids = ranked_ids[:plan.budget]
        omitted = ranked_ids[plan.budget:]
        atoms = tuple(self.store.get_atom(atom_id) for atom_id in selected_ids)
        selected_set = set(selected_ids)
        relations = tuple(self.store.relations_around(selected_set))
        conflicts = tuple(self.store.conflicts_for(selected_set)) if plan.include_conflicts else ()
        unknowns = tuple(self.store.unknowns_for(selected_set, include_all_open=not bool(plan.query_text))) if plan.include_unknowns else ()
        source_lineage = tuple(sorted({source for atom in atoms if atom for source in atom.get("source_refs", [])}))
        return ContextBundle(
            schema_version="1.0.0",
            query_id="query-" + plan.plan_hash[:16],
            query_plan_hash=plan.plan_hash,
            knowledge_version=self.store.latest_revision_id(),
            atoms=tuple(atom for atom in atoms if atom is not None),
            relations=relations,
            conflicts=conflicts,
            unknowns=unknowns,
            source_lineage=source_lineage,
            omitted_due_to_budget=tuple(omitted),
            context_budget=plan.budget,
            semantic_access_state="FULL_SEMANTIC_ACCESS_CANDIDATE_ONLY",
        )

    @staticmethod
    def _allowed(atom: dict[str, Any], plan: QueryPlan) -> bool:
        if atom["knowledge_status"] not in set(plan.truth_states):
            return False
        if atom["knowledge_status"] in DENIED_TRUTH_STATES:
            return False
        if atom["gpt_access"] != "FULL_SEMANTIC_ACCESS":
            return False
        if atom["transport_visibility"] == "RESTRICTED_NEVER_SYNC":
            return False
        if float(atom["confidence"]) < plan.min_confidence:
            return False
        if plan.scopes and atom["scope"] not in set(plan.scopes):
            return False
        if plan.atom_types and atom["atom_type"] not in set(plan.atom_types):
            return False
        if plan.time_start and atom["updated_at"] < plan.time_start:
            return False
        if plan.time_end and atom["updated_at"] > plan.time_end:
            return False
        return True
