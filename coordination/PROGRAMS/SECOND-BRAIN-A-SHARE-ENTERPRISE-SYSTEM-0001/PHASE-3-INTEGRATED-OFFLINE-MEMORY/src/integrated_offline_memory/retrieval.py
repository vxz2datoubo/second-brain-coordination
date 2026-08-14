"""Structured multilingual retrieval and deterministic ContextBundle assembly."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .canonical import content_hash
from .memory_store import ALLOWED_TRUTH_STATES, DENIED_TRUTH_STATES, MemoryStore


@dataclass(frozen=True)
class QueryPlan:
    query_text: str = ""
    scopes: tuple[str, ...] = ()
    atom_types: tuple[str, ...] = ()
    truth_states: tuple[str, ...] = ("candidate", "approved", "conflict", "unknown")
    min_confidence: float = 0.0
    time_start: str | None = None
    time_end: str | None = None
    include_conflicts: bool = True
    include_unknowns: bool = True
    relation_depth: int = 0
    budget: int = 50
    intent: str = "CURRENT"
    user_scope: str | None = None
    privacy_domains: tuple[str, ...] = ()
    valid_at: str | None = None
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
        if self.intent not in {"CURRENT", "HISTORICAL"}:
            raise ValueError("query_plan_intent_invalid")
        # Legacy 1.0 payloads could explicitly include superseded.  Preserve
        # their ability to load, but ContextAssembler still excludes that state
        # for CURRENT admission below.
        if self.intent == "CURRENT" and "superseded" in states and self.schema_version != "1.0.0":
            raise ValueError("query_plan_current_superseded_denied")
        if self.intent == "HISTORICAL" and not self.valid_at:
            raise ValueError("query_plan_historical_valid_time_required")
        if self.valid_at:
            _parse_instant(self.valid_at)
        if self.user_scope is not None and not self.user_scope:
            raise ValueError("query_plan_user_scope_invalid")
        if any(not isinstance(item, str) or not item for item in self.privacy_domains):
            raise ValueError("query_plan_privacy_domains_invalid")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        for field_name in ("scopes", "atom_types", "truth_states", "privacy_domains"):
            payload[field_name] = list(payload[field_name])
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "QueryPlan":
        unknown = set(payload) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError("query_plan_unknown_field")
        data = dict(payload)
        for field_name in ("scopes", "atom_types", "truth_states", "privacy_domains"):
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
    trust_gate: dict[str, Any] = field(default_factory=dict)
    provenance: tuple[dict[str, Any], ...] = ()
    authority_write: bool = False
    no_trade_gate: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for field_name in ("atoms", "relations", "conflicts", "unknowns", "source_lineage", "omitted_due_to_budget", "provenance"):
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
        provenance = tuple(item for atom in atoms if atom for item in self.store.provenance_for_atom(atom["id"]))
        gate = self._trust_gate(plan, atoms)
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
            trust_gate=gate,
            provenance=provenance,
        )

    def _allowed(self, atom: dict[str, Any], plan: QueryPlan) -> bool:
        if atom["knowledge_status"] not in set(plan.truth_states):
            return False
        if atom["knowledge_status"] in DENIED_TRUTH_STATES:
            return False
        if atom["knowledge_status"] in {"stale", "revoked"}:
            return False
        if plan.intent == "CURRENT" and atom["knowledge_status"] == "superseded":
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
        conversation = atom.get("memory_metadata", {}).get("conversation")
        knowledge = atom.get("memory_metadata", {}).get("knowledge")
        if conversation:
            # CLTM data fails closed: caller must bind both scopes and a valid
            # instant.  Non-conversation W3 atoms retain historic defaults.
            if not plan.scopes or plan.user_scope is None or not plan.valid_at:
                return False
            if atom["scope"] not in set(plan.scopes) or conversation.get("project_scope") not in set(plan.scopes):
                return False
            if conversation.get("user_scope") != plan.user_scope:
                return False
            if (conversation.get("privacy_class"), conversation.get("coverage"), conversation.get("source_class")) not in {
                ("PUBLIC_SAFE_SYNTHETIC", "synthetic", "SYNTHETIC_PUBLIC_SAFE"),
                ("PRIVATE_LOCAL_CANDIDATE", "private_local", "PRIVATE_LOCAL_AUTHORIZED"),
            }:
                return False
            if conversation.get("claim_role") not in {
                "USER_ASSERTION", "USER_PREFERENCE", "USER_DECISION", "USER_CORRECTION",
                "USER_PLAN", "USER_GOAL", "USER_COMMITMENT", "USER_EVENT_REPORT",
                "USER_EVALUATION", "USER_CREDIBILITY_JUDGMENT", "USER_BIAS_JUDGMENT",
            }:
                return False
            if plan.intent == "HISTORICAL" and not atom.get("source_refs"):
                return False
            if not self.store.provenance_for_atom(atom["id"]):
                return False
            instant = _parse_instant(plan.valid_at)
            if not _is_valid_at(conversation, instant):
                return False
            if plan.intent == "CURRENT" and _memory_palace_requires_revalidation(conversation, instant):
                return False
        elif knowledge:
            if not plan.scopes or plan.user_scope is None or not plan.privacy_domains or not plan.valid_at:
                return False
            if atom["scope"] not in set(plan.scopes) or knowledge.get("project_scope") not in set(plan.scopes):
                return False
            if knowledge.get("user_scope") != plan.user_scope or knowledge.get("privacy_domain") not in set(plan.privacy_domains):
                return False
            if knowledge.get("privacy_domain") != "PUBLIC_SAFE_SYNTHETIC":
                return False
            if knowledge.get("epistemic_role") not in {
                "FACT_CLAIM", "SOURCE_CLAIM", "SOURCE_INTERPRETATION", "VALUE_JUDGMENT", "MECHANISM", "CONDITION",
                "COUNTEREXAMPLE", "METHOD", "OPEN_QUESTION", "USER_STANCE", "ASSISTANT_ANALYSIS", "MODEL_INFERENCE",
            }:
                return False
            if not knowledge.get("proposition_id") or not knowledge.get("identity_domain_hash"):
                return False
            if plan.intent == "HISTORICAL" and not atom.get("source_refs"):
                return False
            if not self.store.provenance_for_atom(atom["id"]):
                return False
            instant = _parse_instant(plan.valid_at)
            if not _is_valid_at(knowledge, instant):
                return False
            if plan.intent == "CURRENT" and _knowledge_requires_revalidation(knowledge, instant):
                return False
        elif plan.user_scope is not None:
            return False
        return True

    @staticmethod
    def _trust_gate(plan: QueryPlan, atoms: tuple[dict[str, Any] | None, ...]) -> dict[str, Any]:
        admitted = [atom for atom in atoms if atom is not None]
        if not admitted:
            return {"outcome": "ABSTAIN", "reason": "no_in_scope_valid_candidate", "intent": plan.intent}
        return {
            "outcome": "ADMIT_CANDIDATE_ONLY",
            "reason": "scope_privacy_status_and_valid_time_passed",
            "intent": plan.intent,
        }


def _parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("query_plan_or_memory_time_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _is_valid_at(conversation: dict[str, Any], instant: datetime) -> bool:
    valid_from = _parse_instant(conversation["valid_from"])
    ends = [
        _parse_instant(value)
        for value in (conversation.get("valid_to"), conversation.get("effective_valid_to"))
        if value is not None
    ]
    return instant >= valid_from and (not ends or instant < min(ends))


def _memory_palace_requires_revalidation(conversation: dict[str, Any], instant: datetime) -> bool:
    """Keep short-lived market clues historical until explicitly revalidated."""

    palace = conversation.get("memory_palace")
    if not isinstance(palace, dict) or not palace.get("revalidation_required"):
        return False
    if palace.get("freshness_profile") not in {"TRANSIENT", "SHORT_CYCLE"}:
        return False
    last_verified = palace.get("last_verified_at")
    horizon_hours = palace.get("freshness_horizon_hours")
    if not isinstance(last_verified, str) or not isinstance(horizon_hours, int) or horizon_hours < 1:
        return True
    from datetime import timedelta
    return instant > _parse_instant(last_verified) + timedelta(hours=horizon_hours)


def _knowledge_requires_revalidation(knowledge: dict[str, Any], instant: datetime) -> bool:
    if not knowledge.get("revalidation_required"):
        return False
    if knowledge.get("freshness_profile") not in {"TRANSIENT", "SHORT_CYCLE"}:
        return False
    last_verified = knowledge.get("last_verified_at")
    horizon_hours = knowledge.get("freshness_horizon_hours")
    if not isinstance(last_verified, str) or not isinstance(horizon_hours, int) or horizon_hours < 1:
        return True
    from datetime import timedelta
    return instant > _parse_instant(last_verified) + timedelta(hours=horizon_hours)
