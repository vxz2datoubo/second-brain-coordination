"""Candidate Memory Library — Hybrid Retrieval Engine

Work Package D: multi-strategy retrieval combining:
  1. Exact ID lookup (O(1))
  2. Keyword / tokenized search (FTS5)
  3. Relation expansion (1-hop neighbors)
  4. Conflict-prioritized results
  5. UNKNOWN recall (open questions)
  6. Exclusion filters
  7. Time-range filtering
  8. Confidence / authority filtering

Design rules:
  - All retrieval strategies are composable
  - Empty results are reported, not swallowed
  - Conflict atoms are surfaced first when relevant
  - UNKNOWN recall ensures open questions aren't forgotten
  - Budget limits control result size, not content truncation
  - gpt_access = FULL_SEMANTIC_ACCESS by default
"""

import json
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class RetrievalStrategy(str, Enum):
    EXACT_ID = "exact_id"
    KEYWORD = "keyword"
    TOKEN = "token"
    RELATION_EXPAND = "relation_expand"
    CONFLICT_FIRST = "conflict_first"
    UNKNOWN_RECALL = "unknown_recall"
    TIME_RANGE = "time_range"
    SCOPE = "scope"
    TYPE_FILTER = "type_filter"


@dataclass
class RetrievalResult:
    """A single retrieval hit with metadata."""
    atom: Dict[str, Any]
    score: float = 1.0
    strategy: str = ""
    related_relations: List[Dict[str, Any]] = field(default_factory=list)
    related_conflicts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "atom_id": self.atom.get("id"),
            "canonical_statement": self.atom.get("canonical_statement"),
            "atom_type": self.atom.get("atom_type"),
            "confidence": self.atom.get("confidence"),
            "score": self.score,
            "strategy": self.strategy,
            "relation_count": len(self.related_relations),
            "conflict_count": len(self.related_conflicts),
        }


@dataclass
class RetrievalReport:
    """Complete retrieval report with results, unknowns, and exclusions."""
    query: str
    results: List[RetrievalResult] = field(default_factory=list)
    unknown_recall: List[Dict[str, Any]] = field(default_factory=list)
    excluded_count: int = 0
    total_scanned: int = 0
    strategies_used: List[str] = field(default_factory=list)
    budget_limited: bool = False

    def summary(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "result_count": len(self.results),
            "unknown_count": len(self.unknown_recall),
            "excluded": self.excluded_count,
            "scanned": self.total_scanned,
            "strategies": self.strategies_used,
            "budget_limited": self.budget_limited,
        }


class HybridRetrieval:
    """Multi-strategy retrieval over MemoryStore."""

    # Budget defaults — result count limits, NOT content truncation
    DEFAULT_BUDGET = 50
    MAX_EXPANSION_DEPTH = 2

    def __init__(self, store):
        self.store = store

    # ── Main Entry ────────────────────────────────────────────────────

    def retrieve(self, query: str,
                 strategies: Optional[List[RetrievalStrategy]] = None,
                 budget: int = DEFAULT_BUDGET,
                 exclude_ids: Optional[Set[str]] = None,
                 atom_type_filter: Optional[Set[str]] = None,
                 scope_filter: Optional[str] = None,
                 min_confidence: float = 0.0,
                 since: Optional[str] = None,
                 before: Optional[str] = None,
                 ) -> RetrievalReport:
        """
        Main retrieval entry point.

        Args:
            query: Search query string
            strategies: Which strategies to use (default: KEYWORD + CONFLICT_FIRST + UNKNOWN_RECALL)
            budget: Max results
            exclude_ids: Atom IDs to exclude
            atom_type_filter: Only return these atom types
            scope_filter: Only return this scope
            min_confidence: Minimum confidence threshold
            since: ISO timestamp — only atoms created/updated after
            before: ISO timestamp — only atoms created/updated before

        Returns:
            RetrievalReport with results, unknown recall, and metadata
        """
        if strategies is None:
            strategies = [
                RetrievalStrategy.KEYWORD,
                RetrievalStrategy.CONFLICT_FIRST,
                RetrievalStrategy.UNKNOWN_RECALL,
            ]

        report = RetrievalReport(query=query)
        exclude_ids = exclude_ids or set()
        all_results: List[RetrievalResult] = []

        for strategy in strategies:
            if len(all_results) >= budget:
                report.budget_limited = True
                break
            remaining = budget - len(all_results)
            strategy_results = self._run_strategy(
                strategy, query, remaining, exclude_ids, atom_type_filter,
                scope_filter, min_confidence, since, before
            )
            all_results.extend(strategy_results)
            report.strategies_used.append(strategy.value)

        # Post-filter: deduplicate by atom_id, sort by score
        seen: Set[str] = set()
        unique: List[RetrievalResult] = []
        for r in all_results:
            aid = r.atom.get("id", "")
            if aid not in seen:
                seen.add(aid)
                # Apply type_filter to final results (except when type_filter includes UNKNOWN)
                if atom_type_filter and r.atom.get("atom_type") not in atom_type_filter:
                    if r.atom.get("atom_type") != "UNKNOWN" or "UNKNOWN" not in atom_type_filter:
                        continue
                unique.append(r)
        unique.sort(key=lambda x: x.score, reverse=True)

        # Enrich with relations + conflicts
        for r in unique:
            r.related_relations = self.store.get_relations_around(r.atom.get("id", ""))

        report.results = unique[:budget]
        report.total_scanned = len(all_results)
        if len(unique) > budget:
            report.budget_limited = True

        return report

    def _run_strategy(self, strategy: RetrievalStrategy, query: str,
                      budget: int, exclude_ids: Set[str],
                      type_filter: Optional[Set[str]],
                      scope_filter: Optional[str],
                      min_confidence: float,
                      since: Optional[str], before: Optional[str],
                      ) -> List[RetrievalResult]:
        """Run a single retrieval strategy."""

        if strategy == RetrievalStrategy.EXACT_ID:
            return self._exact_id(query, budget, exclude_ids, type_filter, scope_filter, min_confidence, since, before)

        if strategy == RetrievalStrategy.KEYWORD:
            return self._keyword(query, budget, exclude_ids, type_filter, scope_filter, min_confidence, since, before)

        if strategy == RetrievalStrategy.TOKEN:
            return self._token(query, budget, exclude_ids, type_filter, scope_filter, min_confidence, since, before)

        if strategy == RetrievalStrategy.CONFLICT_FIRST:
            return self._conflict_first(budget, exclude_ids, type_filter, scope_filter, min_confidence, since, before)

        if strategy == RetrievalStrategy.RELATION_EXPAND:
            return self._relation_expand(query, budget, exclude_ids, type_filter, scope_filter, min_confidence, since, before)

        if strategy == RetrievalStrategy.UNKNOWN_RECALL:
            return self._unknown_recall(query, budget)

        if strategy == RetrievalStrategy.TIME_RANGE:
            return self._time_range(query, budget, exclude_ids, type_filter, scope_filter, min_confidence)

        if strategy == RetrievalStrategy.SCOPE:
            return self._scope(query, budget, exclude_ids, type_filter, min_confidence, since, before)

        if strategy == RetrievalStrategy.TYPE_FILTER:
            return self._type_filter(query, budget, exclude_ids, min_confidence, since, before)

        return []

    # ── Individual Strategies ───────────────────────────────────────

    def _exact_id(self, query: str, budget: int, exclude_ids: Set[str],
                  type_filter: Optional[Set[str]], scope_filter: Optional[str],
                  min_confidence: float, since: Optional[str], before: Optional[str],
                  ) -> List[RetrievalResult]:
        """Exact atom ID lookup."""
        results = []
        for atom_id in query.split(","):
            atom_id = atom_id.strip()
            if atom_id in exclude_ids:
                continue
            atom = self.store.get_atom(atom_id)
            if atom and self._passes_filters(atom, type_filter, scope_filter, min_confidence, since, before):
                results.append(RetrievalResult(atom=atom, score=1.0, strategy="exact_id"))
        return results[:budget]

    def _keyword(self, query: str, budget: int, exclude_ids: Set[str],
                 type_filter: Optional[Set[str]], scope_filter: Optional[str],
                 min_confidence: float, since: Optional[str], before: Optional[str],
                 ) -> List[RetrievalResult]:
        """FTS5-based keyword search."""
        try:
            raw = self.store.search_fts(query, limit=budget * 2)
        except Exception:
            return []

        results = []
        for atom in raw:
            aid = atom.get("id", "")
            if aid in exclude_ids:
                continue
            if self._passes_filters(atom, type_filter, scope_filter, min_confidence, since, before):
                results.append(RetrievalResult(
                    atom=atom,
                    score=atom.get("confidence", 0.5) or 0.5,
                    strategy="keyword"
                ))
        return results[:budget]

    def _token(self, query: str, budget: int, exclude_ids: Set[str],
               type_filter: Optional[Set[str]], scope_filter: Optional[str],
               min_confidence: float, since: Optional[str], before: Optional[str],
               ) -> List[RetrievalResult]:
        """Tokenized search — split query into tokens, search individually, merge."""
        tokens = query.lower().split()
        all_hits: List[RetrievalResult] = []
        seen_ids: Set[str] = set()

        for token in tokens[:6]:  # max 6 tokens
            raw = self.store.search_fts(token, limit=budget)
            for atom in raw:
                aid = atom.get("id", "")
                if aid in seen_ids or aid in exclude_ids:
                    continue
                if self._passes_filters(atom, type_filter, scope_filter, min_confidence, since, before):
                    seen_ids.add(aid)
                    all_hits.append(RetrievalResult(
                        atom=atom,
                        score=atom.get("confidence", 1.0) or 1.0,
                        strategy="token"
                    ))

        all_hits.sort(key=lambda x: x.score, reverse=True)
        return all_hits[:budget]

    def _relation_expand(self, query: str, budget: int, exclude_ids: Set[str],
                         type_filter: Optional[Set[str]], scope_filter: Optional[str],
                         min_confidence: float, since: Optional[str], before: Optional[str],
                         ) -> List[RetrievalResult]:
        """Start from keyword hits, expand 1-hop via relations."""
        # Start with keyword hits
        keyword_hits = self._keyword(query, 10, exclude_ids, type_filter, scope_filter, min_confidence, since, before)
        visited: Set[str] = {r.atom["id"] for r in keyword_hits}

        results: List[RetrievalResult] = list(keyword_hits)

        # Expand
        for hit in keyword_hits:
            if len(results) >= budget:
                break
            relations = self.store.get_relations_around(hit.atom["id"])
            for rel in relations:
                neighbor_id = rel["from_atom_id"] if rel["to_atom_id"] == hit.atom["id"] else rel["to_atom_id"]
                if neighbor_id in visited or neighbor_id in exclude_ids:
                    continue
                atom = self.store.get_atom(neighbor_id)
                if atom and self._passes_filters(atom, type_filter, scope_filter, min_confidence, since, before):
                    visited.add(neighbor_id)
                    results.append(RetrievalResult(
                        atom=atom,
                        score=atom.get("confidence", 0.5) or 0.5,
                        strategy="relation_expand"
                    ))

        return results[:budget]

    def _conflict_first(self, budget: int, exclude_ids: Set[str],
                        type_filter: Optional[Set[str]], scope_filter: Optional[str],
                        min_confidence: float, since: Optional[str], before: Optional[str],
                        ) -> List[RetrievalResult]:
        """Surface atoms involved in unresolved conflicts."""
        results = []
        conflicts = self.store.get_unresolved_conflicts()
        for con in conflicts:
            if len(results) >= budget:
                break
            for aid in [con.get("atom_id_a"), con.get("atom_id_b")]:
                if aid in exclude_ids:
                    continue
                atom = self.store.get_atom(aid)
                if atom and self._passes_filters(atom, type_filter, scope_filter, min_confidence, since, before):
                    results.append(RetrievalResult(
                        atom=atom,
                        score=1.5,  # boosted for conflict
                        strategy="conflict_first"
                    ))

        return results[:budget]

    def _unknown_recall(self, query: str, budget: int) -> List[RetrievalResult]:
        """Surface open unknowns related to query."""
        unknowns = self.store.get_open_unknowns()
        results = []
        query_lower = query.lower()
        for unk in unknowns:
            if len(results) >= budget:
                break
            question = unk.get("question", "").lower()
            scope = (unk.get("scope") or "").lower()
            if query_lower in question or query_lower in scope or any(
                q in question for q in query_lower.split()
            ):
                # Create a synthetic atom from the unknown
                synthetic_atom = {
                    "id": unk.get("id", ""),
                    "atom_type": "UNKNOWN",
                    "canonical_statement": f"[OPEN QUESTION] {unk.get('question')}",
                    "scope": unk.get("scope"),
                    "confidence": 0.0,
                    "verification_status": "UNVERIFIED",
                }
                results.append(RetrievalResult(
                    atom=synthetic_atom,
                    score=0.3,
                    strategy="unknown_recall",
                ))

        return results[:budget]

    def _time_range(self, query: str, budget: int, exclude_ids: Set[str],
                    type_filter: Optional[Set[str]], scope_filter: Optional[str],
                    min_confidence: float,
                    ) -> List[RetrievalResult]:
        """Time-range filtered retrieval (query = ISO range 'since|before')."""
        parts = query.split("|")
        since = parts[0].strip() if len(parts) > 0 and parts[0].strip() else None
        before = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None

        sql = "SELECT * FROM atoms WHERE 1=1"
        params: List[Any] = []

        if since:
            sql += " AND created_at >= ?"
            params.append(since)
        if before:
            sql += " AND created_at <= ?"
            params.append(before)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(budget * 2)

        rows = self.store.conn.execute(sql, params).fetchall()
        results = []
        for row in rows:
            atom = dict(row)
            aid = atom.get("id", "")
            if aid in exclude_ids:
                continue
            if self._passes_filters(atom, type_filter, scope_filter, min_confidence, since, before):
                results.append(RetrievalResult(
                    atom=atom,
                    score=atom.get("confidence", 0.5) or 0.5,
                    strategy="time_range"
                ))

        return results[:budget]

    def _scope(self, query: str, budget: int, exclude_ids: Set[str],
               type_filter: Optional[Set[str]], min_confidence: float,
               since: Optional[str], before: Optional[str],
               ) -> List[RetrievalResult]:
        """Scope-filtered retrieval."""
        rows = self.store.conn.execute(
            "SELECT * FROM atoms WHERE scope=? ORDER BY confidence DESC LIMIT ?",
            (query, budget * 2)
        ).fetchall()

        results = []
        for row in rows:
            atom = dict(row)
            if self._passes_filters(atom, type_filter, query, min_confidence, since, before):
                results.append(RetrievalResult(
                    atom=atom,
                    score=atom.get("confidence", 0.5) or 0.5,
                    strategy="scope"
                ))
        return results[:budget]

    def _type_filter(self, query: str, budget: int, exclude_ids: Set[str],
                     min_confidence: float, since: Optional[str], before: Optional[str],
                     ) -> List[RetrievalResult]:
        """Atom type filtered retrieval."""
        atom_types = [t.strip() for t in query.split(",")]
        placeholders = ",".join("?" * len(atom_types))
        rows = self.store.conn.execute(
            f"SELECT * FROM atoms WHERE atom_type IN ({placeholders}) ORDER BY confidence DESC LIMIT ?",
            atom_types + [budget * 2]
        ).fetchall()

        results = []
        for row in rows:
            atom = dict(row)
            if self._passes_filters(atom, None, None, min_confidence, since, before):
                results.append(RetrievalResult(
                    atom=atom,
                    score=atom.get("confidence", 0.5) or 0.5,
                    strategy="type_filter"
                ))
        return results[:budget]

    # ── Filter Helpers ──────────────────────────────────────────────

    def _passes_filters(self, atom: Dict[str, Any],
                        type_filter: Optional[Set[str]],
                        scope_filter: Optional[str],
                        min_confidence: float,
                        since: Optional[str],
                        before: Optional[str]) -> bool:
        """Check if an atom passes all filters."""
        if type_filter and atom.get("atom_type") not in type_filter:
            return False
        if scope_filter and atom.get("scope") != scope_filter:
            return False
        if min_confidence > 0 and (atom.get("confidence", 0) or 0) < min_confidence:
            return False
        if since and atom.get("created_at", "") < since:
            return False
        if before and atom.get("created_at", "") > before:
            return False
        return True

    # ── Direct Queries ──────────────────────────────────────────────

    def get_all_atoms(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all atoms (paginated)."""
        rows = self.store.conn.execute(
            "SELECT * FROM atoms ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self.store._atom_row_to_dict(r) for r in rows]

    def get_atoms_by_type(self, atom_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get atoms by type."""
        rows = self.store.conn.execute(
            "SELECT * FROM atoms WHERE atom_type=? ORDER BY confidence DESC LIMIT ?",
            (atom_type, limit)
        ).fetchall()
        return [self.store._atom_row_to_dict(r) for r in rows]

    def count(self) -> Dict[str, int]:
        """Return counts for all entity types."""
        return self.store.stats()
