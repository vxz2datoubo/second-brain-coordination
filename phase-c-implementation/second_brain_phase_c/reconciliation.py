"""
Reconciliation Engine: 12 evolution actions with confidence gating.
Compares candidate atoms against existing knowledge and selects the
correct evolution action rather than blind append.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any
from difflib import SequenceMatcher

from .models import (
    KnowledgeAtom, AtomStatus, ReconciliationAction,
    RelationType, EvidenceStrength, CounterEvidenceRef,
    ConflictType, AuditExecutionStatus, _now_iso,
)
from .audit import ReconciliationAuditLog, AuditLogStore
from .graph import GraphEvolutionManager

# Initial heuristic thresholds (NOT experimentally validated)
# Requires calibration in PHASE_F with real shadow usage data.
SEMANTIC_THRESHOLD = 0.85
HIGH_CONFIDENCE_THRESHOLD = 0.85
LOW_CONFIDENCE_THRESHOLD = 0.6


@dataclass
class ReconciliationDecision:
    action: ReconciliationAction
    target_atom_ids: List[str]
    confidence: float
    rationale: str
    retrieval_evidence_summary: str
    requires_human_review: bool = False


@dataclass
class RetrievalResult:
    atom: KnowledgeAtom
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    graph_score: float = 0.0
    structural_score: float = 0.0
    combined_score: float = 0.0


class ReconciliationEngine:
    def __init__(self, atom_store, graph_manager, audit_store):
        self._atoms = atom_store
        self._graph = graph_manager
        self._audit = audit_store
        self._audit.set_atom_store(atom_store)

    def reconcile(self, candidate, retrieval_results=None):
        if retrieval_results is None:
            retrieval_results = self._retrieve_candidates(candidate)
        filtered = self._filter_by_scope(candidate, retrieval_results)
        filtered = self._filter_by_time(filtered)
        if not filtered:
            decision = ReconciliationDecision(
                action=ReconciliationAction.NEW, target_atom_ids=[],
                confidence=0.9, rationale="No matching existing atoms found",
                retrieval_evidence_summary="0 candidates after scope/time filtering",
            )
        else:
            decision = self._compare_candidates(candidate, filtered)
        if decision.confidence >= HIGH_CONFIDENCE_THRESHOLD:
            decision.requires_human_review = False
        elif decision.confidence >= LOW_CONFIDENCE_THRESHOLD:
            decision.requires_human_review = True
        else:
            decision.action = ReconciliationAction.UNKNOWN
            decision.requires_human_review = False
        audit_log = self._execute_or_record(candidate, decision)
        return decision, audit_log

    def execute_pending(self, audit_id):
        log = self._audit.get(audit_id)
        if not log:
            raise ValueError(f"Audit log {audit_id} not found")
        if log.execution_status != AuditExecutionStatus.PENDING_HUMAN_REVIEW:
            raise ValueError(f"Audit log status is {log.execution_status}, not PENDING")
        candidate = self._atoms.get(log.candidate_atom_id)
        if not candidate:
            raise ValueError(f"Candidate atom {log.candidate_atom_id} not found")
        self._execute_action(candidate, log.action, log.target_atom_ids, log)
        log.execution_status = AuditExecutionStatus.EXECUTED
        log.executed_at = _now_iso()
        return log

    def _retrieve_candidates(self, candidate):
        results = []
        candidate_terms = set(self._tokenize(candidate.canonical_statement))
        candidate_entities = set(candidate.entities)
        candidate_tags = set(candidate.topic_tags)
        for atom in self._atoms.values():
            if atom.atom_id == candidate.atom_id:
                continue
            atom_terms = set(self._tokenize(atom.canonical_statement))
            lexical = self._jaccard(candidate_terms, atom_terms)
            atom_entities = set(atom.entities)
            entity_overlap = self._jaccard(candidate_entities, atom_entities)
            atom_tags = set(atom.topic_tags)
            tag_overlap = self._jaccard(candidate_tags, atom_tags)
            semantic = SequenceMatcher(
                None, candidate.canonical_statement, atom.canonical_statement
            ).ratio()
            combined = lexical * 0.3 + semantic * 0.4 + entity_overlap * 0.2 + tag_overlap * 0.1
            if combined > 0.1:
                results.append(RetrievalResult(
                    atom=atom, lexical_score=lexical, semantic_score=semantic,
                    graph_score=entity_overlap, structural_score=tag_overlap,
                    combined_score=combined,
                ))
        results.sort(key=lambda r: r.combined_score, reverse=True)
        return results[:10]

    def _tokenize(self, text):
        tokens = []
        current_word = []
        for ch in text.lower():
            if ch.isalnum() and ord(ch) < 128:
                current_word.append(ch)
            else:
                if current_word:
                    tokens.append("".join(current_word))
                    current_word = []
                if ch.strip():
                    tokens.append(ch)
        if current_word:
            tokens.append("".join(current_word))
        chinese_chars = [c for c in text if '\u4e00' <= c <= '\u9fff']
        for i in range(len(chinese_chars) - 1):
            tokens.append(chinese_chars[i] + chinese_chars[i + 1])
        return tokens

    def _jaccard(self, a, b):
        if not a and not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _filter_by_scope(self, candidate, results):
        return [r for r in results if candidate.scope.matches(r.atom.scope)]

    def _filter_by_time(self, results):
        return [r for r in results if r.atom.current_status not in (AtomStatus.REVOKED,)]

    def _compare_candidates(self, candidate, results):
        best = results[0]
        atom = best.atom
        is_semantically_equivalent = best.semantic_score >= SEMANTIC_THRESHOLD
        is_scope_equivalent = candidate.scope.matches(atom.scope)
        has_new_source = not any(
            sr.episode_id == candidate.source_refs[0].episode_id
            for sr in atom.source_refs
        ) if candidate.source_refs and atom.source_refs else True
        is_contradiction = self._detect_contradiction(candidate, atom)
        is_refinement = self._detect_refinement(candidate, atom)
        if is_semantically_equivalent and is_scope_equivalent and not has_new_source:
            return ReconciliationDecision(
                action=ReconciliationAction.DUPLICATE, target_atom_ids=[atom.atom_id],
                confidence=best.combined_score,
                rationale=f"Same semantic claim and scope, equivalent source. Score={best.combined_score:.2f}",
                retrieval_evidence_summary=f"Top match {atom.atom_id} score={best.combined_score:.2f}",
            )
        if is_semantically_equivalent and is_scope_equivalent and has_new_source:
            return ReconciliationDecision(
                action=ReconciliationAction.SUPPORT, target_atom_ids=[atom.atom_id],
                confidence=best.combined_score,
                rationale="Same proposition, new independent source provides support",
                retrieval_evidence_summary=f"Top match {atom.atom_id}, new source={has_new_source}",
            )
        if is_contradiction and best.combined_score >= 0.5:
            return ReconciliationDecision(
                action=ReconciliationAction.CONTRADICT, target_atom_ids=[atom.atom_id],
                confidence=best.combined_score,
                rationale="Materially incompatible claims detected",
                retrieval_evidence_summary=f"Contradiction with {atom.atom_id}",
            )
        if is_refinement and best.combined_score >= 0.6:
            return ReconciliationDecision(
                action=ReconciliationAction.REFINE, target_atom_ids=[atom.atom_id],
                confidence=best.combined_score,
                rationale="New evidence narrows or conditions existing claim",
                retrieval_evidence_summary=f"Refinement of {atom.atom_id}",
            )
        if best.combined_score >= SEMANTIC_THRESHOLD and not is_semantically_equivalent:
            if self._is_complementary(candidate, atom):
                return ReconciliationDecision(
                    action=ReconciliationAction.MERGE, target_atom_ids=[atom.atom_id],
                    confidence=best.combined_score * 0.9,
                    rationale="Complementary representations of same concept",
                    retrieval_evidence_summary=f"Merge candidate {atom.atom_id}",
                )
            else:
                return ReconciliationDecision(
                    action=ReconciliationAction.WEAKEN, target_atom_ids=[atom.atom_id],
                    confidence=best.combined_score * 0.8,
                    rationale="Related but conflicting evidence weakens existing claim",
                    retrieval_evidence_summary=f"Weakens {atom.atom_id}",
                )
        if best.combined_score < LOW_CONFIDENCE_THRESHOLD:
            return ReconciliationDecision(
                action=ReconciliationAction.UNKNOWN, target_atom_ids=[],
                confidence=best.combined_score,
                rationale="Low confidence match, cannot determine relationship",
                retrieval_evidence_summary=f"Best score {best.combined_score:.2f} below threshold",
            )
        return ReconciliationDecision(
            action=ReconciliationAction.NEW, target_atom_ids=[],
            confidence=1.0 - best.combined_score,
            rationale=f"No strong match (best score {best.combined_score:.2f})",
            retrieval_evidence_summary=f"Best match {atom.atom_id} score={best.combined_score:.2f}",
        )

    def _detect_contradiction(self, a, b):
        negation_keywords = ["不是", "并非", "不会", "不能", "错误", "不成立", "not", "false", "incorrect"]
        a_text = a.canonical_statement.lower()
        b_text = b.canonical_statement.lower()
        a_has_negation = any(k in a_text for k in negation_keywords)
        b_has_negation = any(k in b_text for k in negation_keywords)
        if a_has_negation != b_has_negation:
            shared_entities = set(a.entities) & set(b.entities)
            if shared_entities:
                return True
        if any(ce.atom_id == b.atom_id for ce in a.counterevidence):
            return True
        if any(ce.atom_id == a.atom_id for ce in b.counterevidence):
            return True
        return False

    def _detect_refinement(self, candidate, existing):
        if len(candidate.conditions) > len(existing.conditions):
            return True
        if len(candidate.exceptions) > len(existing.exceptions):
            return True
        if candidate.atom_type == existing.atom_type and candidate.canonical_statement in existing.canonical_statement:
            return True
        return False

    def _is_complementary(self, a, b):
        if self._detect_contradiction(a, b):
            return False
        a_aspects = set(a.topic_tags) | set(a.entities)
        b_aspects = set(b.topic_tags) | set(b.entities)
        overlap = a_aspects & b_aspects
        only_a = a_aspects - b_aspects
        only_b = b_aspects - a_aspects
        return bool(overlap) and bool(only_a) and bool(only_b)

    def _execute_or_record(self, candidate, decision):
        snapshots = {}
        all_atom_ids = [candidate.atom_id] + decision.target_atom_ids
        for aid in all_atom_ids:
            if aid in self._atoms:
                snapshots[aid] = self._atoms[aid].to_dict()
        log = ReconciliationAuditLog(
            candidate_atom_id=candidate.atom_id, action=decision.action,
            target_atom_ids=decision.target_atom_ids, confidence=decision.confidence,
            rationale=decision.rationale,
            retrieval_evidence_summary=decision.retrieval_evidence_summary,
            pre_action_snapshots=snapshots,
        )
        if decision.requires_human_review:
            log.execution_status = AuditExecutionStatus.PENDING_HUMAN_REVIEW
            self._audit.record(log)
            if candidate.atom_id not in self._atoms:
                self._atoms[candidate.atom_id] = candidate
            return log
        if decision.action == ReconciliationAction.UNKNOWN:
            log.execution_status = AuditExecutionStatus.EXECUTED
            self._audit.record(log)
            if candidate.atom_id not in self._atoms:
                self._atoms[candidate.atom_id] = candidate
            return log
        self._execute_action(candidate, decision.action, decision.target_atom_ids, log)
        log.execution_status = AuditExecutionStatus.EXECUTED
        self._audit.record(log)
        return log

    def _execute_action(self, candidate, action, target_ids, log):
        now = _now_iso()
        if action == ReconciliationAction.NEW:
            candidate.current_status = AtomStatus.ACTIVE
            candidate.lineage_head = True
            candidate.last_reconciled_at = now
            candidate.last_reconciliation_action = action.value
            candidate.last_reconciliation_audit_id = log.audit_id
            candidate.reconciliation_evidence = log.rationale
            self._atoms[candidate.atom_id] = candidate
        elif action == ReconciliationAction.DUPLICATE:
            candidate.current_status = AtomStatus.SUPERSEDED
            candidate.lineage_head = False
            candidate.last_reconciliation_action = action.value
            if target_ids:
                target = self._atoms[target_ids[0]]
                for sr in candidate.source_refs:
                    if not any(existing.episode_id == sr.episode_id for existing in target.source_refs):
                        target.source_refs.append(sr)
                target.last_reconciled_at = now
            self._atoms[candidate.atom_id] = candidate
        elif action == ReconciliationAction.MERGE:
            if target_ids:
                target = self._atoms[target_ids[0]]
                merged = KnowledgeAtom(
                    canonical_statement=f"{target.canonical_statement} | {candidate.canonical_statement}",
                    atom_type=candidate.atom_type,
                    entities=list(set(target.entities + candidate.entities)),
                    topic_tags=list(set(target.topic_tags + candidate.topic_tags)),
                    epistemic_role=candidate.epistemic_role,
                    source_refs=target.source_refs + candidate.source_refs,
                    confidence=max(target.confidence, candidate.confidence),
                    scope=candidate.scope,
                    assumptions=list(set(target.assumptions + candidate.assumptions)),
                    conditions=list(set(target.conditions + candidate.conditions)),
                    exceptions=list(set(target.exceptions + candidate.exceptions)),
                    predecessor_atom_ids=[target.atom_id, candidate.atom_id],
                    lineage_head=True, current_status=AtomStatus.ACTIVE,
                )
                target.current_status = AtomStatus.SUPERSEDED
                target.lineage_head = False
                target.successor_atom_ids.append(merged.atom_id)
                candidate.current_status = AtomStatus.SUPERSEDED
                candidate.lineage_head = False
                candidate.successor_atom_ids.append(merged.atom_id)
                self._atoms[merged.atom_id] = merged
                self._graph.set_supersession(target.atom_id, merged.atom_id)
        elif action == ReconciliationAction.REFINE:
            if target_ids:
                target = self._atoms[target_ids[0]]
                candidate.predecessor_atom_ids = [target.atom_id]
                candidate.lineage_head = True
                candidate.current_status = AtomStatus.ACTIVE
                target.current_status = AtomStatus.SUPERSEDED
                target.lineage_head = False
                target.successor_atom_ids = [candidate.atom_id]
                self._atoms[candidate.atom_id] = candidate
                self._graph.set_supersession(target.atom_id, candidate.atom_id)
        elif action == ReconciliationAction.SUPPORT:
            if target_ids:
                target = self._atoms[target_ids[0]]
                if candidate.atom_id not in self._atoms:
                    self._atoms[candidate.atom_id] = candidate
                self._graph.create_relation(
                    source_atom_id=candidate.atom_id, target_atom_id=target.atom_id,
                    relation_type=RelationType.SUPPORTS, confidence=candidate.confidence,
                    rationale="Independent source support",
                )
                target.confidence = min(0.95, target.confidence + 0.05)
                target.last_reconciled_at = now
                candidate.current_status = AtomStatus.ACTIVE
                self._atoms[candidate.atom_id] = candidate
        elif action == ReconciliationAction.WEAKEN:
            if target_ids:
                target = self._atoms[target_ids[0]]
                if candidate.atom_id not in self._atoms:
                    self._atoms[candidate.atom_id] = candidate
                target.counterevidence.append(CounterEvidenceRef(
                    atom_id=candidate.atom_id, evidence_strength=EvidenceStrength.MODERATE,
                    relation_type=RelationType.COUNTEREVIDENCE_FOR,
                ))
                target.confidence = max(0.1, target.confidence - 0.1)
                target.last_reconciled_at = now
                self._graph.create_relation(
                    source_atom_id=candidate.atom_id, target_atom_id=target.atom_id,
                    relation_type=RelationType.WEAKENS, confidence=candidate.confidence,
                    rationale="Counterevidence",
                )
                candidate.current_status = AtomStatus.ACTIVE
                self._atoms[candidate.atom_id] = candidate
        elif action == ReconciliationAction.CONTRADICT:
            if target_ids:
                target = self._atoms[target_ids[0]]
                self._graph.create_conflict_set(
                    member_atom_ids=[target.atom_id, candidate.atom_id],
                    conflict_type=ConflictType.FACTUAL,
                    description=f"Contradiction between {target.atom_id} and {candidate.atom_id}",
                )
                candidate.current_status = AtomStatus.CONFLICTED
                self._atoms[candidate.atom_id] = candidate
        elif action == ReconciliationAction.SUPERSEDE:
            if target_ids:
                target = self._atoms[target_ids[0]]
                candidate.predecessor_atom_ids = [target.atom_id]
                candidate.lineage_head = True
                candidate.current_status = AtomStatus.ACTIVE
                target.current_status = AtomStatus.SUPERSEDED
                target.lineage_head = False
                target.successor_atom_ids = [candidate.atom_id]
                self._atoms[candidate.atom_id] = candidate
                self._graph.set_supersession(target.atom_id, candidate.atom_id)
        elif action == ReconciliationAction.REVOKE:
            if target_ids:
                target = self._atoms[target_ids[0]]
                target.current_status = AtomStatus.REVOKED
                target.last_reconciled_at = now
                target.invalidation_conditions.append(candidate.canonical_statement)
        elif action == ReconciliationAction.REVALIDATE:
            if target_ids:
                target = self._atoms[target_ids[0]]
                target.current_status = AtomStatus.ACTIVE
                target.valid_from = now
                target.confidence = min(0.95, target.confidence + 0.1)
                target.last_reconciled_at = now
        elif action == ReconciliationAction.RESOLVE_UNKNOWN:
            if target_ids:
                target = self._atoms[target_ids[0]]
                target.current_status = AtomStatus.ACTIVE
                target.last_reconciled_at = now
        candidate.last_reconciled_at = now
        candidate.last_reconciliation_action = action.value
        candidate.last_reconciliation_audit_id = log.audit_id
        candidate.reconciliation_evidence = log.rationale
