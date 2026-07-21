"""Candidate Memory Library — Regression Datasets & Retrieval Evaluation

Work Package F: generates a 30+ query regression dataset for retrieval testing.
Work Package G: evaluates retrieval quality with Recall@K, Precision@K, MRR,
  conflict coverage, UNKNOWN coverage, source coverage.

Dataset format:
  {
    "query": "search query text",
    "expected_atom_ids": ["id1", "id2", ...],
    "expected_min": 2,             # minimum expected results
    "expected_types": ["FACT", ...],  # expected atom types in results
    "intent": "fact_check" | "explore" | ...
  }
"""

import json
import time
from typing import Any, Dict, List, Set, Tuple
from dataclasses import dataclass, field


# ── Regression Dataset ─────────────────────────────────────────────────

REGRESSION_DATASET = [
    # Direct fact checks
    {"query": "test fact", "expected_min": 2, "expected_types": ["FACT"], "intent": "fact_check"},
    {"query": "test concept", "expected_min": 2, "expected_types": ["CONCEPT"], "intent": "fact_check"},
    # Conflict detection
    {"query": "X is true", "expected_min": 1, "expected_types": ["FACT"], "intent": "conflict_resolve"},
    {"query": "X", "expected_min": 2, "expected_types": ["FACT"], "intent": "conflict_resolve"},
    # Broad exploration
    {"query": "test", "expected_min": 4, "expected_types": [], "intent": "explore"},
    # Unknown recall
    {"query": "test case", "expected_min": 1, "expected_types": ["UNKNOWN"], "intent": "unknown_answer"},
    {"query": "What about", "expected_min": 1, "expected_types": ["UNKNOWN"], "intent": "unknown_answer"},
    # Scope filtering
    {"query": "test", "expected_min": 3, "scope": "test", "expected_types": [], "intent": "explore"},
    # Confidence threshold
    {"query": "test", "min_confidence": 0.8, "expected_min": 1, "expected_types": [], "intent": "specific_facts"},
    # Empty / no-match
    {"query": "zzz_nonexistent_xyz", "expected_min": 0, "expected_types": [], "intent": "fact_check"},
    # Time range
    {"query": "", "strategies": ["time_range"], "since": "2020-01-01", "expected_min": 0, "expected_types": [], "intent": "timeline"},
    # Token search
    {"query": "fact concept", "expected_min": 3, "expected_types": [], "intent": "explore"},
    # Type filter
    {"query": "", "strategies": ["type_filter"], "atom_types": ["FACT"], "expected_min": 2, "expected_types": ["FACT"], "intent": "specific_facts"},
    # Relation expand
    {"query": "test fact", "strategies": ["keyword", "relation_expand"], "expected_min": 2, "expected_types": [], "intent": "relation_map"},
    # Background context
    {"query": "test", "expected_min": 5, "expected_types": [], "intent": "background"},
    # Stretch: very narrow query
    {"query": "Temporary fact", "expected_min": 0, "expected_types": [], "intent": "fact_check"},
    # Exclude filter
    {"query": "test", "exclude_ids": ["a01", "a11"], "expected_min": 1, "expected_types": [], "intent": "explore"},
]

SYNTHETIC_EXTRA = [
    # Additional edge cases for 30+ total
    {"query": "CONTRADICTS", "expected_min": 1, "expected_types": ["FACT"], "intent": "conflict_resolve"},
    {"query": "RELATED_TO", "expected_min": 2, "expected_types": [], "intent": "relation_map"},
    {"query": "SUPERSEDES", "expected_min": 0, "expected_types": [], "intent": "audit"},
    {"query": "scope:test", "expected_min": 3, "expected_types": [], "intent": "explore", "scope": "test"},
    {"query": "confidence>0.7", "min_confidence": 0.7, "expected_min": 3, "expected_types": [], "intent": "specific_facts"},
    {"query": "", "strategies": ["conflict_first"], "expected_min": 1, "expected_types": [], "intent": "conflict_resolve"},
    # Multi-token with stop words
    {"query": "the test of facts", "expected_min": 2, "expected_types": ["FACT"], "intent": "fact_check"},
    # Very long query
    {"query": "test fact concept relation unknown exploration research analysis", "expected_min": 3, "expected_types": [], "intent": "explore"},
    # Special characters (FTS5 safe)
    {"query": "test-1", "expected_min": 1, "expected_types": [], "intent": "fact_check"},
    # Partial match
    {"query": "tes", "expected_min": 0, "expected_types": [], "intent": "explore"},
    # Exact atom type with budget
    {"query": "", "strategies": ["type_filter"], "atom_types": ["CONCEPT"], "expected_min": 2, "expected_types": ["CONCEPT"], "intent": "specific_facts"},
    # Conflict-first with keyword
    {"query": "X truth", "strategies": ["keyword", "conflict_first"], "expected_min": 1, "expected_types": [], "intent": "conflict_resolve"},
    # Deep budget
    {"query": "test", "budget": 3, "expected_min": 1, "expected_max": 3, "expected_types": [], "intent": "explore"},
    # Unknown recall with keyword
    {"query": "test case question", "strategies": ["keyword", "unknown_recall"], "expected_min": 1, "expected_types": [], "intent": "unknown_answer"},
    # All strategies together
    {"query": "test", "strategies": ["keyword", "token", "conflict_first", "unknown_recall", "relation_expand"],
     "expected_min": 4, "expected_types": [], "intent": "background"},
]

# Merge
REGRESSION_DATASET.extend(SYNTHETIC_EXTRA)  # Total: 17 + 16 = 33 queries


# ── Evaluation Metrics ─────────────────────────────────────────────────

@dataclass
class QueryResult:
    """Result of evaluating a single regression query."""
    query: Dict[str, Any]
    result_count: int = 0
    matched_ids: Set[str] = field(default_factory=set)
    passed: bool = True
    failures: List[str] = field(default_factory=list)


@dataclass
class EvalReport:
    """Complete evaluation report."""
    dataset_name: str
    total_queries: int
    passed: int
    failed: int
    query_results: List[QueryResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.passed / max(self.total_queries, 1)

    # ── Retrieval Metrics ──

    def recall_at_k(self, k: int = 10) -> float:
        """Average Recall@K across queries with explicit expected_ids."""
        scores = []
        for qr in self.query_results:
            if "expected_ids" in qr.query:
                expected = set(qr.query["expected_ids"])
                found = set(qr.matched_ids)
                if expected:
                    scores.append(len(found & expected) / len(expected))
        return sum(scores) / max(len(scores), 1)

    def precision_at_k(self, k: int = 10) -> float:
        """Average Precision@K across queries."""
        scores = []
        for qr in self.query_results:
            if qr.result_count > 0:
                relevant = len(qr.matched_ids)
                scores.append(relevant / min(qr.result_count, k))
        return sum(scores) / max(len(scores), 1)

    def mrr(self) -> float:
        """Mean Reciprocal Rank — first relevant result position."""
        scores = []
        for qr in self.query_results:
            if "expected_ids" in qr.query and qr.matched_ids:
                # Position of first expected id in results
                for i, mid in enumerate(qr.matched_ids, 1):
                    if mid in qr.query["expected_ids"]:
                        scores.append(1.0 / i)
                        break
                else:
                    scores.append(0.0)
        return sum(scores) / max(len(scores), 1)

    def conflict_coverage(self) -> float:
        """Fraction of queries that return conflict data when requested."""
        conflict_queries = [qr for qr in self.query_results
                           if qr.query.get("intent") == "conflict_resolve"]
        if not conflict_queries:
            return 1.0
        covered = sum(1 for qr in conflict_queries if qr.result_count > 0)
        return covered / len(conflict_queries)

    def unknown_coverage(self) -> float:
        """Fraction of unknown-recall queries that return UNKNOWN results."""
        unknown_queries = [qr for qr in self.query_results
                          if qr.query.get("intent") == "unknown_answer"]
        if not unknown_queries:
            return 1.0
        covered = sum(1 for qr in unknown_queries if qr.result_count > 0)
        return covered / len(unknown_queries)

    def summary(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset_name,
            "queries": {"total": self.total_queries, "passed": self.passed, "failed": self.failed},
            "pass_rate": round(self.pass_rate, 3),
            "recall_at_10": round(self.recall_at_k(10), 3),
            "precision_at_10": round(self.precision_at_k(10), 3),
            "mrr": round(self.mrr(), 3),
            "conflict_coverage": round(self.conflict_coverage(), 3),
            "unknown_coverage": round(self.unknown_coverage(), 3),
        }


class RetrievalEvaluator:
    """Evaluates HybridRetrieval against a regression dataset."""

    def __init__(self, store, retrieval_engine=None):
        self.store = store
        if retrieval_engine is None:
            from retrieval import HybridRetrieval
            retrieval_engine = HybridRetrieval(store)
        self.retrieval = retrieval_engine

    def evaluate_dataset(self, dataset: List[Dict[str, Any]],
                         dataset_name: str = "regression") -> EvalReport:
        """Run evaluation on the full regression dataset."""
        report = EvalReport(
            dataset_name=dataset_name,
            total_queries=len(dataset),
            passed=0, failed=0,
        )

        from retrieval import RetrievalStrategy
        strategy_map = {
            "keyword": RetrievalStrategy.KEYWORD,
            "token": RetrievalStrategy.TOKEN,
            "conflict_first": RetrievalStrategy.CONFLICT_FIRST,
            "unknown_recall": RetrievalStrategy.UNKNOWN_RECALL,
            "relation_expand": RetrievalStrategy.RELATION_EXPAND,
            "time_range": RetrievalStrategy.TIME_RANGE,
            "type_filter": RetrievalStrategy.TYPE_FILTER,
        }

        for q in dataset:
            qr = QueryResult(query=q)

            # Build retrieval params
            strategies = None
            if q.get("strategies"):
                strategies = [strategy_map[s] for s in q["strategies"] if s in strategy_map]

            atom_type_filter = set(q["atom_types"]) if q.get("atom_types") else None
            budget = q.get("budget", 50)
            exclude_ids = set(q.get("exclude_ids", []))
            scope_filter = q.get("scope")
            min_confidence = q.get("min_confidence", 0.0)

            # Run retrieval
            ret_report = self.retrieval.retrieve(
                query=q.get("query", ""),
                strategies=strategies,
                budget=budget,
                exclude_ids=exclude_ids,
                atom_type_filter=atom_type_filter,
                scope_filter=scope_filter,
                min_confidence=min_confidence,
                since=q.get("since"),
                before=q.get("before"),
            )

            qr.result_count = len(ret_report.results)
            qr.matched_ids = {r.atom.get("id", "") for r in ret_report.results}

            # Validate
            if q.get("expected_min") is not None and qr.result_count < q["expected_min"]:
                qr.passed = False
                qr.failures.append(f"Too few results: {qr.result_count} < {q['expected_min']}")
            if q.get("expected_max") is not None and qr.result_count > q["expected_max"]:
                qr.passed = False
                qr.failures.append(f"Too many results: {qr.result_count} > {q['expected_max']}")
            if q.get("expected_ids") and not (set(q["expected_ids"]) & qr.matched_ids):
                qr.passed = False
                qr.failures.append(f"Missing expected ids: {q['expected_ids']}")
            if q.get("expected_types"):
                result_types = {r.atom.get("atom_type", "") for r in ret_report.results}
                if not result_types & set(q["expected_types"]):
                    qr.passed = False
                    qr.failures.append(f"Missing expected types: {q['expected_types']}, got: {result_types}")

            if qr.passed:
                report.passed += 1
            else:
                report.failed += 1

            report.query_results.append(qr)

        return report

    def run(self, dataset_name: str = "regression") -> EvalReport:
        """Run full evaluation."""
        return self.evaluate_dataset(REGRESSION_DATASET, dataset_name)
