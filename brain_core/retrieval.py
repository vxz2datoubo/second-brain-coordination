"""Hybrid retrieval v0.1: keyword retrieval plus vector-store interface mock."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .knowledge import tokenize
from .storage import BrainStore


@dataclass
class SearchHit:
    atom_id: str
    title: str
    content: str
    score: float
    matched_terms: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    why: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "atom_id": self.atom_id,
            "title": self.title,
            "content": self.content,
            "score": round(self.score, 4),
            "matched_terms": self.matched_terms,
            "source_ids": self.source_ids,
            "evidence_ids": self.evidence_ids,
            "confidence": self.confidence,
            "why": self.why,
        }


@dataclass
class LearningHit:
    learning_entry_id: str
    entry_type: str
    target_type: str
    summary: str
    score: float
    matched_terms: list[str] = field(default_factory=list)
    target_ids: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    improvement_items: list[str] = field(default_factory=list)
    created_at: str = ""
    why: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_entry_id": self.learning_entry_id,
            "entry_type": self.entry_type,
            "target_type": self.target_type,
            "summary": self.summary,
            "score": round(self.score, 4),
            "matched_terms": self.matched_terms,
            "target_ids": self.target_ids,
            "lessons": self.lessons,
            "improvement_items": self.improvement_items,
            "created_at": self.created_at,
            "why": self.why,
        }


class HybridRetriever:
    def __init__(self, store: BrainStore):
        self.store = store
        self.target_table_map = {
            "atom": "atoms",
            "evidence": "evidence",
            "decision": "decisions",
            "forecast": "forecasts",
            "reasoning_trace": "reasoning_traces",
            "review": "reviews",
            "feedback": "feedback_records",
        }
        self.prefix_table_map = {
            "src_": "sources",
            "ev_": "evidence",
            "atom_": "atoms",
            "rel_": "relations",
            "epi_": "episodes",
            "decision_": "decisions",
            "forecast_": "forecasts",
            "review_": "reviews",
            "feedback_": "feedback_records",
            "reason_": "reasoning_traces",
            "learn_": "learning_entries",
            "evo_": "evolution_logs",
            "trace_": "agent_traces",
            "approval_": "risk_approvals",
        }

    def search(self, query: str, top_k: int = 5) -> dict[str, Any]:
        query = (query or "").strip()
        if not query:
            return {"query": query, "results": [], "vector": self.vector_status()}
        q_tokens = set(tokenize(query))
        hits: list[SearchHit] = []
        for atom in self.store.all_atoms():
            recommended_tags = atom.metadata.get("recommended_tags", []) if isinstance(atom.metadata, dict) else []
            haystack = " ".join([
                atom.title,
                atom.content,
                " ".join(atom.tags),
                " ".join(atom.categories),
                " ".join(recommended_tags),
            ])
            h_tokens = set(tokenize(haystack))
            matched = sorted(q_tokens & h_tokens)
            if not matched and query not in haystack:
                continue
            title_boost = 1.5 if any(t in atom.title for t in matched) else 1.0
            tag_boost = 1.2 if set(atom.tags) & q_tokens else 1.0
            recommended_boost = 1.15 if set(recommended_tags) & q_tokens else 1.0
            score = (len(matched) + (2 if query in haystack else 0)) * title_boost * tag_boost * recommended_boost
            score *= 0.5 + atom.confidence
            hits.append(
                SearchHit(
                    atom_id=atom.id,
                    title=atom.title,
                    content=atom.content,
                    score=score,
                    matched_terms=matched,
                    source_ids=atom.source_ids,
                    evidence_ids=atom.evidence_ids,
                    confidence=atom.confidence,
                    why="keyword overlap + confidence weighting + recommended tag support",
                )
            )
        hits.sort(key=lambda h: h.score, reverse=True)
        return {
            "query": query,
            "results": [h.to_dict() for h in hits[: int(top_k)]],
            "vector": self.vector_status(),
        }

    def search_learning_entries(self, query: str, top_k: int = 5) -> dict[str, Any]:
        query = (query or "").strip()
        if not query:
            return {"query": query, "results": [], "summary": self.learning_summary(limit=top_k)}
        q_tokens = set(tokenize(query))
        hits: list[LearningHit] = []
        for entry in self.store.list_records("learning_entries", limit=100000):
            haystack_parts = [
                entry.get("entry_type", ""),
                entry.get("target_type", ""),
                entry.get("summary", ""),
                " ".join(entry.get("lessons", [])),
                " ".join(entry.get("improvement_items", [])),
            ]
            haystack = " ".join(haystack_parts)
            h_tokens = set(tokenize(haystack))
            matched = sorted(q_tokens & h_tokens)
            if not matched and query not in haystack:
                continue
            lesson_boost = 1.25 if any(token in " ".join(entry.get("lessons", [])) for token in matched) else 1.0
            improvement_boost = 1.25 if any(token in " ".join(entry.get("improvement_items", [])) for token in matched) else 1.0
            score = (len(matched) + (2 if query in haystack else 0)) * lesson_boost * improvement_boost
            score *= 1.0 + abs(float(entry.get("confidence_delta", 0.0)))
            hits.append(
                LearningHit(
                    learning_entry_id=entry["id"],
                    entry_type=entry.get("entry_type", ""),
                    target_type=entry.get("target_type", ""),
                    summary=entry.get("summary", ""),
                    score=score,
                    matched_terms=matched,
                    target_ids=entry.get("target_ids", []),
                    lessons=entry.get("lessons", []),
                    improvement_items=entry.get("improvement_items", []),
                    created_at=entry.get("created_at", ""),
                    why="keyword overlap across learning summary, lessons and improvement items",
                )
            )
        hits.sort(key=lambda h: (h.score, h.created_at), reverse=True)
        return {
            "query": query,
            "results": [h.to_dict() for h in hits[: int(top_k)]],
            "summary": self.learning_summary(limit=top_k),
        }

    def learning_summary(self, limit: int = 5) -> dict[str, Any]:
        entries = self.store.list_records("learning_entries", limit=100000)
        entry_type_counts: dict[str, int] = {}
        target_type_counts: dict[str, int] = {}
        lesson_counts: dict[str, int] = {}
        improvement_counts: dict[str, int] = {}
        recent_entries: list[dict[str, Any]] = []
        for entry in entries:
            entry_type = entry.get("entry_type", "unknown") or "unknown"
            target_type = entry.get("target_type", "unknown") or "unknown"
            entry_type_counts[entry_type] = entry_type_counts.get(entry_type, 0) + 1
            target_type_counts[target_type] = target_type_counts.get(target_type, 0) + 1
            for lesson in entry.get("lessons", []):
                if lesson:
                    lesson_counts[lesson] = lesson_counts.get(lesson, 0) + 1
            for item in entry.get("improvement_items", []):
                if item:
                    improvement_counts[item] = improvement_counts.get(item, 0) + 1
        for entry in entries[: int(limit)]:
            recent_entries.append(
                {
                    "id": entry["id"],
                    "entry_type": entry.get("entry_type", ""),
                    "target_type": entry.get("target_type", ""),
                    "summary": entry.get("summary", ""),
                    "created_at": entry.get("created_at", ""),
                }
            )
        return {
            "total_learning_entries": len(entries),
            "entry_type_counts": entry_type_counts,
            "target_type_counts": target_type_counts,
            "top_lessons": self._top_items(lesson_counts, limit),
            "top_improvement_items": self._top_items(improvement_counts, limit),
            "recent_entries": recent_entries,
            "implementation_status": "Implemented",
        }

    def feedback_summary(
        self,
        limit: int = 5,
        target_type: str = "",
        target_id: str = "",
    ) -> dict[str, Any]:
        entries = self.store.list_records("feedback_records", limit=100000)
        filtered: list[dict[str, Any]] = []
        target_type = (target_type or "").strip()
        target_id = (target_id or "").strip()
        for entry in entries:
            if target_type and entry.get("target_type", "") != target_type:
                continue
            if target_id and target_id not in entry.get("target_ids", []):
                continue
            filtered.append(entry)

        target_type_counts: dict[str, int] = {}
        tag_add_counts: dict[str, int] = {}
        tag_remove_counts: dict[str, int] = {}
        improvement_counts: dict[str, int] = {}
        net_confidence_delta = 0.0
        positive_confidence_count = 0
        negative_confidence_count = 0
        related_atom_link_count = 0
        support_link_count = 0
        refute_link_count = 0
        recent_feedback: list[dict[str, Any]] = []

        for entry in filtered:
            current_target_type = entry.get("target_type", "unknown") or "unknown"
            target_type_counts[current_target_type] = target_type_counts.get(current_target_type, 0) + 1
            delta = float(entry.get("confidence_delta", 0.0) or 0.0)
            net_confidence_delta += delta
            if delta > 0:
                positive_confidence_count += 1
            elif delta < 0:
                negative_confidence_count += 1
            related_atom_link_count += len(entry.get("related_atom_ids", []))
            support_link_count += len(entry.get("support_ids", []))
            refute_link_count += len(entry.get("refute_ids", []))
            for tag in entry.get("tags_to_add", []):
                if tag:
                    tag_add_counts[tag] = tag_add_counts.get(tag, 0) + 1
            for tag in entry.get("tags_to_remove", []):
                if tag:
                    tag_remove_counts[tag] = tag_remove_counts.get(tag, 0) + 1
            for item in entry.get("improvement_items", []):
                if item:
                    improvement_counts[item] = improvement_counts.get(item, 0) + 1

        for entry in filtered[: int(limit)]:
            recent_feedback.append(
                {
                    "id": entry.get("id", ""),
                    "target_type": entry.get("target_type", ""),
                    "target_ids": entry.get("target_ids", []),
                    "feedback_text": entry.get("feedback_text", ""),
                    "confidence_delta": entry.get("confidence_delta", 0.0),
                    "tags_to_add": entry.get("tags_to_add", []),
                    "tags_to_remove": entry.get("tags_to_remove", []),
                    "improvement_items": entry.get("improvement_items", []),
                    "created_at": entry.get("created_at", ""),
                }
            )

        return {
            "filters": {
                "target_type": target_type,
                "target_id": target_id,
                "limit": int(limit),
                "implementation_status": "Implemented",
            },
            "summary": {
                "total_feedback_records": len(filtered),
                "target_type_counts": target_type_counts,
                "top_tags_added": self._top_items(tag_add_counts, limit),
                "top_tags_removed": self._top_items(tag_remove_counts, limit),
                "top_improvement_items": self._top_items(improvement_counts, limit),
                "net_confidence_delta": round(net_confidence_delta, 4),
                "positive_confidence_feedback_count": positive_confidence_count,
                "negative_confidence_feedback_count": negative_confidence_count,
                "related_atom_link_count": related_atom_link_count,
                "support_link_count": support_link_count,
                "refute_link_count": refute_link_count,
                "implementation_status": "Implemented",
            },
            "target_snapshot": self._feedback_target_snapshot(target_type, target_id),
            "recent_feedback": recent_feedback,
            "implementation_status": "Implemented",
        }

    def feedback_memory_candidates(self, limit: int = 5, min_count: int = 2) -> dict[str, Any]:
        entries = self.store.list_records("feedback_records", limit=100000)
        improvement_groups = self._build_feedback_pattern_groups(entries, "improvement_items", "feedback_improvement_item")
        tag_add_groups = self._build_feedback_pattern_groups(entries, "tags_to_add", "feedback_tag_add")
        tag_remove_groups = self._build_feedback_pattern_groups(entries, "tags_to_remove", "feedback_tag_remove")

        candidates = [
            self._finalize_feedback_pattern_candidate(group, int(min_count))
            for group in improvement_groups + tag_add_groups + tag_remove_groups
        ]
        candidates.sort(
            key=lambda item: (
                -item["priority_score"],
                item["pattern_type"],
                item["text"],
            )
        )
        returned = candidates[: int(limit)]
        return {
            "candidates": returned,
            "summary": {
                "total_feedback_records": len(entries),
                "total_candidates": len(candidates),
                "immediate_candidate_count": len([item for item in candidates if item["migration_status"] == "immediate_candidate"]),
                "need_more_evidence_count": len([item for item in candidates if item["migration_status"] == "need_more_evidence"]),
                "single_observation_noise_count": len([item for item in candidates if item["migration_status"] == "single_observation_noise"]),
                "min_count": int(min_count),
                "returned_candidate_count": len(returned),
                "implementation_status": "Implemented",
            },
            "integration_note": {
                "implementation_status": "Implemented",
                "current_route": "feedback_records -> feedback_memory_candidates -> human review -> learning_chains / migration decisions",
                "future_route": "TODO: connect high-confidence candidates into automatic learning-chain promotion or long-term memory migration ranking.",
            },
            "implementation_status": "Implemented",
        }

    def inspect_learning_entry(self, learning_entry_id: str) -> dict[str, Any]:
        entry = self.store.get("learning_entries", learning_entry_id)
        if not entry:
            raise ValueError(f"learning entry not found: {learning_entry_id}")

        source_record = self._resolve_record(
            preferred_table=self._infer_source_table(entry),
            record_id=entry.get("source_record_id", ""),
        )
        target_records = self._resolve_targets(
            target_type=entry.get("target_type", ""),
            target_ids=entry.get("target_ids", []),
        )
        evidence_records = self._resolve_records_by_ids(entry.get("evidence_ids", []))
        counter_evidence_records = self._resolve_records_by_ids(entry.get("counter_evidence_ids", []))
        related_logs = self._related_evolution_logs(entry)

        return {
            "learning_entry": entry,
            "source_record": source_record,
            "targets": target_records,
            "evidence": evidence_records,
            "counter_evidence": counter_evidence_records,
            "related_evolution_logs": related_logs,
            "traceability": {
                "target_count": len(target_records),
                "evidence_count": len(evidence_records),
                "counter_evidence_count": len(counter_evidence_records),
                "has_source_record": source_record is not None,
                "related_evolution_log_count": len(related_logs),
                "implementation_status": "Implemented",
            },
        }

    def learning_chains(self, limit: int = 5, min_count: int = 2) -> dict[str, Any]:
        entries = self.store.list_records("learning_entries", limit=100000)
        lesson_groups = self._build_learning_groups(entries, "lessons", "lesson")
        improvement_groups = self._build_learning_groups(entries, "improvement_items", "improvement_item")
        filtered_lessons = [group for group in lesson_groups if group["entry_count"] >= int(min_count)]
        filtered_improvements = [group for group in improvement_groups if group["entry_count"] >= int(min_count)]
        filtered_lessons = filtered_lessons[: int(limit)]
        filtered_improvements = filtered_improvements[: int(limit)]
        return {
            "lesson_chains": filtered_lessons,
            "improvement_chains": filtered_improvements,
            "summary": {
                "total_learning_entries": len(entries),
                "returned_lesson_chains": len(filtered_lessons),
                "returned_improvement_chains": len(filtered_improvements),
                "min_count": int(min_count),
                "implementation_status": "Implemented",
            },
        }

    def inspect_atom_writeback(self, atom_id: str) -> dict[str, Any]:
        atom = self.store.get("atoms", atom_id)
        if not atom:
            raise ValueError(f"atom not found: {atom_id}")
        metadata = atom.get("metadata", {})
        recommended_tags = metadata.get("recommended_tags", []) if isinstance(metadata, dict) else []
        learning_chain_refs = metadata.get("learning_chain_refs", []) if isinstance(metadata, dict) else []
        relations = self._relations_for_atom(atom_id, relation_type="learning_chain_related")
        related_learning_entries = self._learning_entries_for_atom(atom_id, learning_chain_refs)
        related_logs = self._evolution_logs_for_atom(atom_id)
        importance_history = self._estimate_importance_history(atom, learning_chain_refs)
        latest_apply_audit = metadata.get("last_learning_apply", {}) if isinstance(metadata, dict) else {}
        return {
            "atom": atom,
            "recommended_tags": recommended_tags,
            "learning_chain_refs": learning_chain_refs,
            "learning_chain_relations": relations,
            "related_learning_entries": related_learning_entries,
            "related_evolution_logs": related_logs,
            "importance_audit": importance_history,
            "latest_apply_audit": latest_apply_audit,
            "writeback_audit": {
                "recommended_tag_count": len(recommended_tags),
                "learning_chain_ref_count": len(learning_chain_refs),
                "relation_count": len(relations),
                "related_learning_entry_count": len(related_learning_entries),
                "related_evolution_log_count": len(related_logs),
                "implementation_status": "Implemented",
            },
        }

    def writeback_overview(self, limit: int = 10) -> dict[str, Any]:
        atoms = self.store.list_records("atoms", limit=100000)
        atom_rows: list[dict[str, Any]] = []
        recommended_tag_counts: dict[str, int] = {}
        chain_text_counts: dict[str, int] = {}
        latest_apply_buckets = {
            "new_or_changed": [],
            "confirmed_only": [],
            "no_recent_apply_state": [],
        }
        for atom in atoms:
            metadata = atom.get("metadata", {})
            recommended_tags = metadata.get("recommended_tags", []) if isinstance(metadata, dict) else []
            learning_chain_refs = metadata.get("learning_chain_refs", []) if isinstance(metadata, dict) else []
            latest_apply_audit = metadata.get("last_learning_apply", {}) if isinstance(metadata, dict) else {}
            if not recommended_tags and not learning_chain_refs:
                continue
            relation_count = len(self._relations_for_atom(atom["id"], relation_type="learning_chain_related"))
            score = len(recommended_tags) + len(learning_chain_refs) + relation_count
            latest_new_ref_count = len(latest_apply_audit.get("new_chain_refs", []))
            latest_updated_ref_count = len(latest_apply_audit.get("updated_chain_refs", []))
            latest_unchanged_ref_count = len(latest_apply_audit.get("unchanged_chain_refs", []))
            latest_created_relation_count = len(latest_apply_audit.get("created_relation_ids", []))
            latest_updated_relation_count = len(latest_apply_audit.get("updated_relation_ids", []))
            latest_confirmed_relation_count = len(latest_apply_audit.get("confirmed_relation_ids", []))
            if latest_new_ref_count or latest_updated_ref_count or latest_created_relation_count or latest_updated_relation_count:
                latest_apply_state = "new_or_changed"
            elif latest_unchanged_ref_count or latest_confirmed_relation_count:
                latest_apply_state = "confirmed_only"
            else:
                latest_apply_state = "no_recent_apply_state"
            atom_rows.append(
                {
                    "atom_id": atom["id"],
                    "title": atom.get("title", ""),
                    "recommended_tag_count": len(recommended_tags),
                    "learning_chain_ref_count": len(learning_chain_refs),
                    "relation_count": relation_count,
                    "importance": atom.get("importance", 0.0),
                    "writeback_score": score,
                    "latest_apply_state": latest_apply_state,
                    "latest_apply_new_ref_count": latest_new_ref_count,
                    "latest_apply_updated_ref_count": latest_updated_ref_count,
                    "latest_apply_unchanged_ref_count": latest_unchanged_ref_count,
                    "latest_apply_created_relation_count": latest_created_relation_count,
                    "latest_apply_updated_relation_count": latest_updated_relation_count,
                    "latest_apply_confirmed_relation_count": latest_confirmed_relation_count,
                    "suggest_human_review": relation_count >= 4 or len(recommended_tags) >= 4,
                }
            )
            latest_apply_buckets[latest_apply_state].append(atom["id"])
            for tag in recommended_tags:
                if tag:
                    recommended_tag_counts[tag] = recommended_tag_counts.get(tag, 0) + 1
            for ref in learning_chain_refs:
                text = ref.get("text", "")
                if text:
                    chain_text_counts[text] = chain_text_counts.get(text, 0) + 1

        atom_rows.sort(
            key=lambda item: (
                -item["writeback_score"],
                -float(item["importance"]),
                item["atom_id"],
            )
        )
        top_atoms = atom_rows[: int(limit)]
        flagged_atoms = [row for row in top_atoms if row["suggest_human_review"]]
        return {
            "top_writeback_atoms": top_atoms,
            "top_recommended_tags": self._top_items(recommended_tag_counts, limit),
            "top_chain_texts": self._top_items(chain_text_counts, limit),
            "flagged_for_review": flagged_atoms,
            "latest_apply_buckets": {
                "new_or_changed_count": len(latest_apply_buckets["new_or_changed"]),
                "confirmed_only_count": len(latest_apply_buckets["confirmed_only"]),
                "no_recent_apply_state_count": len(latest_apply_buckets["no_recent_apply_state"]),
                "new_or_changed_atom_ids": latest_apply_buckets["new_or_changed"][: int(limit)],
                "confirmed_only_atom_ids": latest_apply_buckets["confirmed_only"][: int(limit)],
            },
            "summary": {
                "atoms_with_writeback": len(atom_rows),
                "flagged_atom_count": len(flagged_atoms),
                "returned_atom_count": len(top_atoms),
                "implementation_status": "Implemented",
            },
        }

    @staticmethod
    def _top_items(counter: dict[str, int], limit: int) -> list[dict[str, Any]]:
        ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        return [{"text": text, "count": count} for text, count in ranked[: int(limit)]]

    def _infer_source_table(self, entry: dict[str, Any]) -> str | None:
        source_id = entry.get("source_record_id", "")
        if source_id:
            return self._table_for_id(source_id)
        entry_type = entry.get("entry_type", "")
        return self.target_table_map.get(entry_type)

    def _resolve_targets(self, target_type: str, target_ids: list[str]) -> list[dict[str, Any]]:
        preferred_table = self.target_table_map.get(target_type)
        resolved: list[dict[str, Any]] = []
        for record_id in target_ids:
            record = self._resolve_record(preferred_table, record_id)
            if record is not None:
                resolved.append(record)
        return resolved

    def _resolve_records_by_ids(self, record_ids: list[str]) -> list[dict[str, Any]]:
        resolved: list[dict[str, Any]] = []
        for record_id in record_ids:
            record = self._resolve_record(self._table_for_id(record_id), record_id)
            if record is not None:
                resolved.append(record)
            else:
                resolved.append({"id": record_id, "implementation_status": "Interface", "status": "unresolved_reference"})
        return resolved

    def _resolve_record(self, preferred_table: str | None, record_id: str) -> dict[str, Any] | None:
        if not record_id:
            return None
        tables_to_try: list[str] = []
        if preferred_table:
            tables_to_try.append(preferred_table)
        inferred = self._table_for_id(record_id)
        if inferred and inferred not in tables_to_try:
            tables_to_try.append(inferred)
        for table in tables_to_try:
            record = self.store.get(table, record_id)
            if record is not None:
                return {"table": table, "record": record}
        return None

    def _feedback_target_snapshot(self, target_type: str, target_id: str) -> dict[str, Any] | None:
        if not target_type or not target_id:
            return None
        table = self.target_table_map.get(target_type)
        if not table:
            return {
                "target_type": target_type,
                "target_id": target_id,
                "implementation_status": "Interface",
                "reason": "Unsupported target_type for feedback snapshot.",
            }
        target = self.store.get(table, target_id)
        if not target:
            return None
        metadata = target.get("metadata", {}) or {}
        feedback_log = metadata.get("feedback_log", [])
        snapshot = {
            "target_type": target_type,
            "target_id": target_id,
            "confidence": target.get("confidence"),
            "feedback_log_count": len(feedback_log),
            "latest_feedback_id": feedback_log[-1]["feedback_id"] if feedback_log else "",
            "improvement_items": metadata.get("improvement_items", []),
            "feedback_tags": metadata.get("feedback_tags", []),
            "implementation_status": "Implemented",
        }
        if target_type == "atom":
            snapshot["tags"] = target.get("tags", [])
            snapshot["related_ids"] = target.get("related_ids", [])
        elif target_type == "evidence":
            snapshot["supports"] = target.get("supports", [])
            snapshot["refutes"] = target.get("refutes", [])
        return snapshot

    def _related_evolution_logs(self, entry: dict[str, Any]) -> list[dict[str, Any]]:
        related_ids = set(entry.get("target_ids", []))
        related_ids.update(
            item for item in [
                entry.get("id", ""),
                entry.get("source_record_id", ""),
            ] if item
        )
        results: list[dict[str, Any]] = []
        for log in self.store.list_records("evolution_logs", limit=100000):
            affected_ids = set(log.get("affected_ids", []))
            if affected_ids & related_ids:
                results.append(log)
        results.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return results

    def _table_for_id(self, record_id: str) -> str | None:
        for prefix, table in self.prefix_table_map.items():
            if record_id.startswith(prefix):
                return table
        return None

    def _relations_for_atom(self, atom_id: str, relation_type: str = "") -> list[dict[str, Any]]:
        rows = self.store.list_records("relations", limit=100000)
        results: list[dict[str, Any]] = []
        for relation in rows:
            if relation.get("source_atom_id") != atom_id and relation.get("target_atom_id") != atom_id:
                continue
            if relation_type and relation.get("relation_type") != relation_type:
                continue
            results.append(relation)
        results.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return results

    def _learning_entries_for_atom(self, atom_id: str, learning_chain_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        entries = self.store.list_records("learning_entries", limit=100000)
        ref_texts = {ref.get("text", "") for ref in learning_chain_refs if ref.get("text")}
        results: list[dict[str, Any]] = []
        for entry in entries:
            has_direct_link = atom_id in entry.get("target_ids", []) or entry.get("source_record_id") == atom_id
            has_chain_match = bool(ref_texts & (set(entry.get("lessons", [])) | set(entry.get("improvement_items", []))))
            if has_direct_link or has_chain_match:
                results.append(entry)
        results.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return results

    def _evolution_logs_for_atom(self, atom_id: str) -> list[dict[str, Any]]:
        logs = self.store.list_records("evolution_logs", limit=100000)
        results = [log for log in logs if atom_id in log.get("affected_ids", [])]
        results.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return results

    @staticmethod
    def _estimate_importance_history(atom: dict[str, Any], learning_chain_refs: list[dict[str, Any]]) -> dict[str, Any]:
        current_importance = float(atom.get("importance", 0.5))
        estimated_delta = 0.0
        for ref in learning_chain_refs:
            estimated_delta += float(ref.get("applied_delta", min(0.12, 0.02 * int(ref.get("entry_count", 0)))))
        estimated_base = max(0.0, current_importance - estimated_delta)
        return {
            "estimated_base_importance": round(estimated_base, 6),
            "estimated_writeback_delta": round(estimated_delta, 6),
            "current_importance": round(current_importance, 6),
            "note": "Estimated from learning_chain_refs because v0.1 stores current importance, not a full historical timeseries.",
            "implementation_status": "Implemented",
        }

    def _build_learning_groups(
        self,
        entries: list[dict[str, Any]],
        field_name: str,
        chain_type: str,
    ) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, Any]] = {}
        for entry in entries:
            values = [item for item in entry.get(field_name, []) if item]
            for value in values:
                group = groups.setdefault(
                    value,
                    {
                        "chain_type": chain_type,
                        "text": value,
                        "entry_ids": [],
                        "entry_types": set(),
                        "target_types": set(),
                        "target_ids": set(),
                        "source_record_ids": set(),
                        "evidence_ids": set(),
                        "counter_evidence_ids": set(),
                        "examples": [],
                        "latest_created_at": "",
                    },
                )
                group["entry_ids"].append(entry["id"])
                group["entry_types"].add(entry.get("entry_type", ""))
                group["target_types"].add(entry.get("target_type", ""))
                group["target_ids"].update(entry.get("target_ids", []))
                if entry.get("source_record_id"):
                    group["source_record_ids"].add(entry["source_record_id"])
                group["evidence_ids"].update(entry.get("evidence_ids", []))
                group["counter_evidence_ids"].update(entry.get("counter_evidence_ids", []))
                created_at = entry.get("created_at", "")
                if created_at > group["latest_created_at"]:
                    group["latest_created_at"] = created_at
                if len(group["examples"]) < 3:
                    group["examples"].append(
                        {
                            "learning_entry_id": entry["id"],
                            "entry_type": entry.get("entry_type", ""),
                            "target_type": entry.get("target_type", ""),
                            "summary": entry.get("summary", ""),
                            "target_ids": entry.get("target_ids", []),
                            "created_at": created_at,
                        }
                    )
        ranked: list[dict[str, Any]] = []
        for value, group in groups.items():
            target_type_counts: dict[str, int] = {}
            for entry in entries:
                if value in [item for item in entry.get(field_name, []) if item]:
                    target_type = entry.get("target_type", "unknown") or "unknown"
                    target_type_counts[target_type] = target_type_counts.get(target_type, 0) + 1
            ranked.append(
                {
                    "chain_type": chain_type,
                    "text": value,
                    "entry_count": len(group["entry_ids"]),
                    "entry_ids": group["entry_ids"],
                    "entry_types": sorted(item for item in group["entry_types"] if item),
                    "target_types": sorted(item for item in group["target_types"] if item),
                    "target_type_counts": target_type_counts,
                    "target_ids": sorted(group["target_ids"]),
                    "source_record_ids": sorted(group["source_record_ids"]),
                    "evidence_ids": sorted(group["evidence_ids"]),
                    "counter_evidence_ids": sorted(group["counter_evidence_ids"]),
                    "latest_created_at": group["latest_created_at"],
                    "examples": group["examples"],
                }
            )
        ranked.sort(key=lambda item: (-item["entry_count"], item["text"]))
        return ranked

    def _build_feedback_pattern_groups(
        self,
        entries: list[dict[str, Any]],
        field_name: str,
        pattern_type: str,
    ) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, Any]] = {}
        for entry in entries:
            values = [item for item in entry.get(field_name, []) if item]
            for value in values:
                group = groups.setdefault(
                    value,
                    {
                        "pattern_type": pattern_type,
                        "text": value,
                        "feedback_ids": [],
                        "target_types": set(),
                        "target_ids": set(),
                        "source_record_ids": set(),
                        "related_atom_ids": set(),
                        "latest_created_at": "",
                        "net_confidence_delta": 0.0,
                        "examples": [],
                    },
                )
                group["feedback_ids"].append(entry["id"])
                group["target_types"].add(entry.get("target_type", ""))
                group["target_ids"].update(entry.get("target_ids", []))
                group["source_record_ids"].add(entry["id"])
                group["related_atom_ids"].update(entry.get("related_atom_ids", []))
                group["net_confidence_delta"] += float(entry.get("confidence_delta", 0.0) or 0.0)
                created_at = entry.get("created_at", "")
                if created_at > group["latest_created_at"]:
                    group["latest_created_at"] = created_at
                if len(group["examples"]) < 3:
                    group["examples"].append(
                        {
                            "feedback_id": entry["id"],
                            "target_type": entry.get("target_type", ""),
                            "target_ids": entry.get("target_ids", []),
                            "feedback_text": entry.get("feedback_text", ""),
                            "confidence_delta": entry.get("confidence_delta", 0.0),
                            "created_at": created_at,
                        }
                    )
        rows: list[dict[str, Any]] = []
        for value, group in groups.items():
            target_type_counts: dict[str, int] = {}
            for entry in entries:
                if value in [item for item in entry.get(field_name, []) if item]:
                    current_target_type = entry.get("target_type", "unknown") or "unknown"
                    target_type_counts[current_target_type] = target_type_counts.get(current_target_type, 0) + 1
            rows.append(
                {
                    "pattern_type": pattern_type,
                    "text": value,
                    "feedback_count": len(group["feedback_ids"]),
                    "feedback_ids": group["feedback_ids"],
                    "target_types": sorted(item for item in group["target_types"] if item),
                    "target_type_counts": target_type_counts,
                    "target_ids": sorted(group["target_ids"]),
                    "source_record_ids": sorted(group["source_record_ids"]),
                    "related_atom_ids": sorted(group["related_atom_ids"]),
                    "latest_created_at": group["latest_created_at"],
                    "net_confidence_delta": round(group["net_confidence_delta"], 4),
                    "examples": group["examples"],
                }
            )
        rows.sort(key=lambda item: (-item["feedback_count"], item["text"]))
        return rows

    @staticmethod
    def _finalize_feedback_pattern_candidate(group: dict[str, Any], min_count: int) -> dict[str, Any]:
        feedback_count = int(group["feedback_count"])
        target_count = len(group["target_ids"])
        if feedback_count >= int(min_count) and target_count >= 2:
            migration_status = "immediate_candidate"
            reason = "Repeated feedback already spans multiple targets, so this looks like a stable long-term pattern."
        elif feedback_count >= int(min_count):
            migration_status = "need_more_evidence"
            reason = "Repeated feedback exists, but it is still concentrated on too few targets for a stable long-term update."
        else:
            migration_status = "single_observation_noise"
            reason = "This pattern has appeared only once and should stay observable rather than shaping long-term defaults."
        priority_score = feedback_count * 10 + target_count * 3 + min(2.0, abs(float(group["net_confidence_delta"]))) * 2
        return {
            **group,
            "migration_status": migration_status,
            "migration_reason": reason,
            "priority_score": round(priority_score, 4),
            "suggested_route": "Review with learning_chains and legacy migration views before promoting to long-term defaults.",
            "implementation_status": "Implemented",
        }

    @staticmethod
    def vector_status() -> dict[str, str]:
        return {
            "implementation_status": "Mock",
            "reason": "v0.1 exposes the interface but does not require a vector database.",
        }
