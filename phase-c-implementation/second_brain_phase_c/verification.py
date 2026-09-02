"""
Post-write verification: 5 tests every atom must pass before reporting success.
1. Exact recall: canonical_statement query returns atom in top-1
2. Paraphrase recall: predefined fixture paraphrase returns atom in top-3
3. Graph recall: reachable via entity/edge traversal
4. Scope isolation: atom does not appear in wrong-scope queries
5. Temporal status: CURRENT/HISTORICAL queries return correct status
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from difflib import SequenceMatcher

from .models import (
    KnowledgeAtom, AtomStatus, PrivacyClass, Scope, _now_iso,
)


@dataclass
class VerificationResult:
    atom_id: str
    exact_recall_pass: bool = False
    paraphrase_recall_pass: bool = False
    graph_recall_pass: bool = False
    scope_isolation_pass: bool = False
    temporal_status_pass: bool = False
    all_passed: bool = False
    details: Dict[str, str] = field(default_factory=dict)
    verified_at: str = field(default_factory=_now_iso)


class PostWriteVerifier:
    def __init__(self, atom_store):
        self._atoms = atom_store
        self._paraphrase_fixtures: Dict[str, List[str]] = {}

    def register_paraphrase_fixture(self, atom_id, paraphrases):
        self._paraphrase_fixtures[atom_id] = paraphrases

    def verify(self, atom):
        result = VerificationResult(atom_id=atom.atom_id)
        result.exact_recall_pass = self._test_exact_recall(atom)
        result.details["exact_recall"] = "PASS" if result.exact_recall_pass else "FAIL: atom not in top-1"
        result.paraphrase_recall_pass = self._test_paraphrase_recall(atom)
        result.details["paraphrase_recall"] = "PASS" if result.paraphrase_recall_pass else "FAIL: not in top-3"
        result.graph_recall_pass = self._test_graph_recall(atom)
        result.details["graph_recall"] = "PASS" if result.graph_recall_pass else "FAIL: not reachable"
        result.scope_isolation_pass = self._test_scope_isolation(atom)
        result.details["scope_isolation"] = "PASS" if result.scope_isolation_pass else "FAIL: scope leak"
        result.temporal_status_pass = self._test_temporal_status(atom)
        result.details["temporal_status"] = "PASS" if result.temporal_status_pass else "FAIL: wrong status"
        result.all_passed = all([
            result.exact_recall_pass, result.paraphrase_recall_pass,
            result.graph_recall_pass, result.scope_isolation_pass,
            result.temporal_status_pass,
        ])
        return result

    def _test_exact_recall(self, atom):
        query = atom.canonical_statement
        results = self._simple_search(query)
        if not results:
            return False
        return results[0][0] == atom.atom_id

    def _test_paraphrase_recall(self, atom):
        paraphrases = self._paraphrase_fixtures.get(atom.atom_id, [])
        if not paraphrases:
            paraphrases = [self._simple_paraphrase(atom.canonical_statement)]
        for para in paraphrases:
            results = self._simple_search(para)
            top3_ids = [r[0] for r in results[:3]]
            if atom.atom_id not in top3_ids:
                return False
        return True

    def _test_graph_recall(self, atom):
        if not atom.entities:
            if not atom.topic_tags:
                return True
            search_terms = atom.topic_tags
        else:
            search_terms = atom.entities
        for term in search_terms:
            results = self._entity_search(term)
            ids = [r[0] for r in results]
            if atom.atom_id in ids:
                return True
        return False

    def _test_scope_isolation(self, atom):
        wrong_scope = Scope(
            user_scope="different_user",
            project_scope=atom.scope.project_scope,
            privacy_class=atom.scope.privacy_class,
        )
        results = self._scoped_search(atom.canonical_statement, wrong_scope)
        ids = [r[0] for r in results]
        return atom.atom_id not in ids

    def _test_temporal_status(self, atom):
        if atom.is_current():
            current_results = self._current_search(atom.canonical_statement)
            current_ids = [r[0] for r in current_results]
            return atom.atom_id in current_ids
        else:
            current_results = self._current_search(atom.canonical_statement)
            current_ids = [r[0] for r in current_results]
            return atom.atom_id not in current_ids

    def _simple_search(self, query, top_k=10):
        query_terms = set(query.lower().split())
        results = []
        for atom in self._atoms.values():
            atom_terms = set(atom.canonical_statement.lower().split())
            if not query_terms or not atom_terms:
                score = SequenceMatcher(None, query, atom.canonical_statement).ratio()
            else:
                overlap = len(query_terms & atom_terms)
                score = overlap / len(query_terms) if query_terms else 0
            results.append((atom.atom_id, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _entity_search(self, entity, top_k=10):
        results = []
        for atom in self._atoms.values():
            if entity in atom.entities:
                results.append((atom.atom_id, 1.0))
            elif any(entity in e for e in atom.entities):
                results.append((atom.atom_id, 0.5))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _scoped_search(self, query, scope, top_k=10):
        results = self._simple_search(query, top_k=100)
        filtered = []
        for atom_id, score in results:
            atom = self._atoms.get(atom_id)
            if atom and atom.scope.matches(scope):
                filtered.append((atom_id, score))
        return filtered[:top_k]

    def _current_search(self, query, top_k=10):
        results = self._simple_search(query, top_k=100)
        filtered = []
        for atom_id, score in results:
            atom = self._atoms.get(atom_id)
            if atom and atom.is_current():
                filtered.append((atom_id, score))
        return filtered[:top_k]

    def _simple_paraphrase(self, text):
        words = text.split()
        if len(words) > 3:
            return " ".join(words[1:] + words[:1])
        return text
