"""Candidate Memory Library — QueryPlan & ContextBundle

Work Package E: structured query planning and context assembly for
knowledge retrieval. Implements:

  QueryPlan: specifies retrieval intent, strategies, filters, and budget
  ContextBundle: the assembled response containing atoms, relations,
    conflicts, unknowns, and retrieval metadata

Design rules:
  - QueryPlan is the declarative interface for retrieval
  - ContextBundle packs everything GPT needs in one structured response
  - Budget limits are explicit — no silent truncation
  - Omitted content is reported (excluded_count, budget_limited)
  - gpt_access = FULL_SEMANTIC_ACCESS on all content
  - transport_visibility only affects WHERE content is stored, not WHAT is returned
"""

import json
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class QueryIntent(str, Enum):
    """What the caller actually wants."""
    FACT_CHECK = "fact_check"           # Verify a specific claim
    EXPLORE = "explore"                 # Broad topic exploration
    CONFLICT_RESOLVE = "conflict_resolve"  # Resolve conflicting knowledge
    UNKNOWN_ANSWER = "unknown_answer"   # Try to answer an open question
    SKILL_LOOKUP = "skill_lookup"       # Find relevant procedures/skills
    TIMELINE = "timeline"               # Time-ordered knowledge
    RELATION_MAP = "relation_map"       # Map of how things connect
    BACKGROUND = "background"           # General context for a task
    SPECIFIC_FACTS = "specific_facts"   # Targeted fact retrieval
    AUDIT = "audit"                     # Audit trail / history


@dataclass
class QueryPlan:
    """Declarative retrieval specification."""
    intent: QueryIntent
    query_text: str = ""
    strategies: List[str] = field(default_factory=list)
    atom_types: Optional[List[str]] = None
    scope: Optional[str] = None
    exclude_ids: Optional[List[str]] = None
    min_confidence: float = 0.0
    budget: int = 50
    relation_expand: bool = False
    since: Optional[str] = None
    before: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "query": self.query_text,
            "strategies": self.strategies,
            "atom_types": self.atom_types,
            "scope": self.scope,
            "min_confidence": self.min_confidence,
            "budget": self.budget,
            "relation_expand": self.relation_expand,
            "since": self.since,
            "before": self.before,
        }

    @classmethod
    def for_fact_check(cls, claim: str) -> "QueryPlan":
        return cls(
            intent=QueryIntent.FACT_CHECK,
            query_text=claim,
            strategies=["keyword", "token", "conflict_first"],
            min_confidence=0.3,
            budget=20,
        )

    @classmethod
    def for_explore(cls, topic: str, budget: int = 50) -> "QueryPlan":
        return cls(
            intent=QueryIntent.EXPLORE,
            query_text=topic,
            strategies=["keyword", "relation_expand", "unknown_recall"],
            relation_expand=True,
            budget=budget,
        )

    @classmethod
    def for_conflict_resolve(cls, topic: str) -> "QueryPlan":
        return cls(
            intent=QueryIntent.CONFLICT_RESOLVE,
            query_text=topic,
            strategies=["keyword", "conflict_first", "unknown_recall"],
            budget=30,
        )

    @classmethod
    def for_procedure(cls, task_description: str) -> "QueryPlan":
        return cls(
            intent=QueryIntent.SKILL_LOOKUP,
            query_text=task_description,
            strategies=["keyword", "token"],
            atom_types=["PROCEDURE", "SKILL", "RULE"],
            budget=10,
        )

    @classmethod
    def for_context(cls, task_description: str, budget: int = 50) -> "QueryPlan":
        return cls(
            intent=QueryIntent.BACKGROUND,
            query_text=task_description,
            strategies=["keyword", "relation_expand", "conflict_first", "unknown_recall"],
            relation_expand=True,
            budget=budget,
        )


@dataclass
class ContextBundle:
    """Assembled knowledge context for downstream consumption (GPT / CLI / API)."""

    plan: QueryPlan
    query_id: str = ""
    atoms: List[Dict[str, Any]] = field(default_factory=list)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    unknowns: List[Dict[str, Any]] = field(default_factory=list)
    skills: List[Dict[str, Any]] = field(default_factory=list)
    excluded_count: int = 0
    budget_limited: bool = False
    search_time_ms: float = 0.0
    retrieval_report: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "plan": self.plan.to_dict(),
            "atoms": self._serialize_atoms(),
            "relations": self.relations,
            "conflicts": self.conflicts,
            "unknowns": self.unknowns,
            "skills": self.skills,
            "counts": {
                "atoms": len(self.atoms),
                "relations": len(self.relations),
                "conflicts": len(self.conflicts),
                "unknowns": len(self.unknowns),
                "skills": len(self.skills),
                "excluded": self.excluded_count,
            },
            "budget_limited": self.budget_limited,
            "search_time_ms": self.search_time_ms,
            "retrieval_report": self.retrieval_report,
        }

    def _serialize_atoms(self) -> List[Dict[str, Any]]:
        """Serialize atoms with transport_visibility properly captured."""
        result = []
        for atom in self.atoms:
            d = dict(atom) if not isinstance(atom, dict) else atom
            # Ensure transport_visibility is reported
            if "transport_visibility" not in d:
                d["transport_visibility"] = "LOCAL"
            result.append(d)
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, default=str)

    def to_text_summary(self) -> str:
        """Human-readable summary for chat embedding."""
        lines = [f"## Knowledge Context: {self.plan.query_text}"]
        lines.append(f"Found: {len(self.atoms)} atoms, {len(self.relations)} relations, "
                     f"{len(self.conflicts)} conflicts, {len(self.unknowns)} unknowns")
        if self.budget_limited:
            lines.append(f"⚠️ Budget limited — {self.excluded_count} items excluded")

        if self.conflicts:
            lines.append("\n### Active Conflicts")
            for c in self.conflicts:
                lines.append(f"- {c.get('conflict_type', 'DIRECT')}: {c.get('resolution_status', 'UNRESOLVED')}")

        if self.unknowns:
            lines.append("\n### Open Questions")
            for u in self.unknowns:
                lines.append(f"- {u.get('question', '?')}")

        if self.atoms:
            lines.append("\n### Knowledge Atoms")
            for a in self.atoms[:10]:
                conf = a.get("confidence", "?")
                lines.append(f"- [{a.get('atom_type', '?')}] {a.get('canonical_statement', '?')} (confidence: {conf})")
            if len(self.atoms) > 10:
                lines.append(f"  ... and {len(self.atoms)-10} more")

        return "\n".join(lines)


class ContextAssembler:
    """Assembles QueryPlans into ContextBundles using HybridRetrieval."""

    def __init__(self, store, retrieval_engine=None):
        self.store = store
        if retrieval_engine is None:
            from retrieval import HybridRetrieval
            retrieval_engine = HybridRetrieval(store)
        self.retrieval = retrieval_engine

    def assemble(self, plan: QueryPlan) -> ContextBundle:
        """Execute a QueryPlan and assemble a ContextBundle."""
        import time
        start = time.time()

        bundle = ContextBundle(plan=plan)
        bundle.query_id = hashlib.sha256(
            f"{plan.intent.value}|{plan.query_text}|{time.time()}".encode()
        ).hexdigest()[:16]

        # Determine strategies from plan
        from retrieval import RetrievalStrategy
        strategy_map = {
            "exact_id": RetrievalStrategy.EXACT_ID,
            "keyword": RetrievalStrategy.KEYWORD,
            "token": RetrievalStrategy.TOKEN,
            "relation_expand": RetrievalStrategy.RELATION_EXPAND,
            "conflict_first": RetrievalStrategy.CONFLICT_FIRST,
            "unknown_recall": RetrievalStrategy.UNKNOWN_RECALL,
            "time_range": RetrievalStrategy.TIME_RANGE,
            "scope": RetrievalStrategy.SCOPE,
            "type_filter": RetrievalStrategy.TYPE_FILTER,
        }
        strategies = [
            strategy_map[s] for s in plan.strategies if s in strategy_map
        ]

        # If relation expand is requested separately
        if plan.relation_expand and RetrievalStrategy.RELATION_EXPAND not in strategies:
            strategies.append(RetrievalStrategy.RELATION_EXPAND)

        # Run retrieval
        report = self.retrieval.retrieve(
            query=plan.query_text,
            strategies=strategies or None,
            budget=plan.budget,
            exclude_ids=set(plan.exclude_ids or []),
            atom_type_filter=set(plan.atom_types) if plan.atom_types else None,
            scope_filter=plan.scope,
            min_confidence=plan.min_confidence,
            since=plan.since,
            before=plan.before,
        )

        # Populate bundle
        bundle.atoms = [r.atom for r in report.results]
        bundle.relations = [r.related_relations for r in report.results if r.related_relations]
        bundle.relations = [item for sublist in bundle.relations for item in sublist]  # flatten

        # Map synthesized unknowns (from report) back to store unknowns
        for r in report.results:
            if r.atom.get("atom_type") == "UNKNOWN":
                aid = r.atom.get("id", "")
                unknown = self.store.conn.execute(
                    "SELECT * FROM unknowns WHERE id=?", (aid,)
                ).fetchone()
                if unknown:
                    bundle.unknowns.append(dict(unknown))
                else:
                    bundle.unknowns.append(r.atom)

        # Also add explicit unknown recall (these bypass type_filter to ensure UNKNOWN always surfaces)
        bundle.unknowns.extend(report.unknown_recall)

        # Get conflicts related to retrieved atoms
        conflict_ids: Set[str] = set()
        for atom_id in [a.get("id", "") for a in bundle.atoms]:
            for rel in self.store.get_relations_around(atom_id):
                if rel.get("relation_type") == "CONTRADICTS":
                    # Find the actual conflict record
                    rows = self.store.conn.execute(
                        "SELECT * FROM conflicts WHERE (atom_id_a=? AND atom_id_b=?) OR (atom_id_a=? AND atom_id_b=?)",
                        (atom_id, rel.get("to_atom_id"), rel.get("to_atom_id"), atom_id)
                    ).fetchall()
                    for row in rows:
                        cid = row["id"]
                        if cid not in conflict_ids:
                            conflict_ids.add(cid)
                            bundle.conflicts.append(dict(row))

        bundle.excluded_count = report.excluded_count
        bundle.budget_limited = report.budget_limited
        bundle.search_time_ms = (time.time() - start) * 1000
        bundle.retrieval_report = report.summary()

        return bundle

    def quick_search(self, query: str, budget: int = 20) -> ContextBundle:
        """Convenience: quick keyword-based search."""
        plan = QueryPlan(
            intent=QueryIntent.BACKGROUND,
            query_text=query,
            strategies=["keyword", "conflict_first", "unknown_recall"],
            budget=budget,
        )
        return self.assemble(plan)

    def deep_search(self, topic: str, budget: int = 100) -> ContextBundle:
        """Convenience: deep exploration with relations."""
        plan = QueryPlan(
            intent=QueryIntent.EXPLORE,
            query_text=topic,
            strategies=["keyword", "token", "relation_expand", "conflict_first", "unknown_recall"],
            relation_expand=True,
            budget=budget,
        )
        return self.assemble(plan)
