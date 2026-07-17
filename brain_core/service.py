"""High-level v0.1 service used by API and CLI."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Callable

from .board import AnnouncementBoard
from .contracts import RelationEdge, WritebackSnapshot, clamp, new_id, to_dict
from .decision import DecisionManager
from .evolution import EvolutionManager
from .foundation_data_governance import FoundationDataGovernanceV01
from .ingestion import TextIngestor
from .retrieval import HybridRetriever
from .storage import BrainStore
from .trading_domain import TradingDomainV01


class SuperBrainV01:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.store = BrainStore(self.root)
        self.board = AnnouncementBoard(self.store, self.root)
        self.evolution = EvolutionManager(self.store)
        self.ingestor = TextIngestor(self.store)
        self.retriever = HybridRetriever(self.store)
        self.decisions = DecisionManager(self.store, self.evolution)
        self.trading = TradingDomainV01(self.store, self.decisions, self.evolution, self.board, self.root)
        self.foundation_data_governance = FoundationDataGovernanceV01(
            self.store, self.board, self.evolution, self.root, self.trading
        )

    def ingest_text(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.ingestor.ingest_text(
            text=payload.get("text", ""),
            title=payload.get("title", ""),
            source_type=payload.get("source_type", payload.get("source", "manual")),
            uri=payload.get("uri", ""),
            reliability=float(payload.get("reliability", 0.6)),
            metadata=payload.get("metadata", {}),
        )
        return {
            "success": True,
            "source": to_dict(result["source"]),
            "evidence": [to_dict(e) for e in result["evidence"]],
            "atoms": [to_dict(a) for a in result["atoms"]],
            "relations": [to_dict(r) for r in result["relations"]],
            "episode": to_dict(result["episode"]),
        }

    def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.retriever.search(payload.get("query", ""), int(payload.get("top_k", 5)))

    def search_learning_entries(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.retriever.search_learning_entries(payload.get("query", ""), int(payload.get("top_k", 5)))

    def learning_summary(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return self.retriever.learning_summary(int(payload.get("limit", 5)))

    def feedback_summary(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return self.retriever.feedback_summary(
            limit=int(payload.get("limit", 5)),
            target_type=payload.get("target_type", ""),
            target_id=payload.get("target_id", ""),
        )

    def feedback_memory_candidates(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return self.retriever.feedback_memory_candidates(
            limit=int(payload.get("limit", 5)),
            min_count=int(payload.get("min_count", 2)),
        )

    def unified_memory_review_queue(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        limit = int(payload.get("limit", 10))
        min_count = int(payload.get("min_count", 2))
        profile = str(payload.get("profile", "legacy-first") or "legacy-first")
        legacy_mapping = self.legacy_lessons_mapping({"profile": profile})
        feedback_candidates = self.feedback_memory_candidates({"limit": 1000, "min_count": min_count})
        learning_chains = self.learning_chains({"limit": 1000, "min_count": min_count})
        items = self._build_unified_memory_review_items(
            legacy_mapping=legacy_mapping,
            feedback_candidates=feedback_candidates,
            learning_chains=learning_chains,
        )
        ranked_items = sorted(
            items,
            key=lambda item: (
                self._review_bucket_rank(item.get("queue_bucket", "observe")),
                -float(item.get("priority_score", 0.0)),
                item.get("label", ""),
            ),
        )
        returned_items = ranked_items[:limit]
        return {
            "items": returned_items,
            "summary": {
                "total_candidates": len(items),
                "returned_candidates": len(returned_items),
                "queue_bucket_counts": self._count_queue_buckets(items),
                "source_view_counts": self._count_source_views(items),
                "profile": profile,
                "min_count": min_count,
                "implementation_status": "Implemented",
            },
            "integration_note": {
                "implementation_status": "Implemented",
                "current_route": "legacy_lessons_mapping + feedback_memory_candidates + learning_chains -> unified_memory_review_queue -> human review",
                "future_route": "TODO: connect review decisions back into long-term memory promotion, profile weighting, or automatic migration ranking.",
            },
            "implementation_status": "Implemented",
        }

    def confirm_unified_memory_review_item(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        source_view = str(payload.get("source_view", "") or "").strip()
        candidate_type = str(payload.get("candidate_type", "") or "").strip()
        label = str(payload.get("label", "") or "").strip()
        queue_bucket = str(payload.get("queue_bucket", "review_now") or "review_now").strip()
        decision = str(payload.get("decision", "accepted") or "accepted").strip()
        if not source_view:
            raise ValueError("source_view is required")
        if not candidate_type:
            raise ValueError("candidate_type is required")
        if not label:
            raise ValueError("label is required")
        if decision not in {"accepted", "deferred", "rejected"}:
            raise ValueError("decision must be one of {'accepted','deferred','rejected'}")
        target_id = new_id("memory_review", f"{source_view}:{candidate_type}:{label}")
        summary = str(payload.get("summary", "") or "").strip()
        if not summary:
            action_text = {
                "accepted": "采纳进入后续整理",
                "deferred": "暂缓处理，保留观察",
                "rejected": "暂不采纳，保留审计记录",
            }[decision]
            summary = f"人工确认 unified memory review 候选“{label}”，当前处理结果：{action_text}。"
        result = self.decisions.create_learning_entry(
            entry_type="unified_memory_review_confirmation",
            target_type="unified_memory_candidate",
            target_ids=[target_id],
            summary=summary,
            source_record_id=str(payload.get("source_record_id", "") or ""),
            evidence_ids=payload.get("evidence_ids", []),
            counter_evidence_ids=payload.get("counter_evidence_ids", []),
            lessons=payload.get("lessons", []),
            improvement_items=payload.get("improvement_items", []),
            confidence_delta=float(payload.get("confidence_delta", 0.0)),
            metadata={
                "implementation_status": "Implemented",
                "source_view": source_view,
                "candidate_type": candidate_type,
                "label": label,
                "queue_bucket": queue_bucket,
                "decision": decision,
                "profile": str(payload.get("profile", "") or ""),
                "min_count": int(payload.get("min_count", 0) or 0),
            },
        )
        self.board.update(
            summary=f"记录 unified memory review 确认：{label} -> {decision}（来源 {source_view}，队列 {queue_bucket}）。",
            event_type="unified_memory_review_confirmed",
        )
        return result

    def unified_memory_review_summary(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        limit = max(1, int(payload.get("limit", 5)))
        confirmations = self._list_unified_memory_review_confirmations()
        candidate_rows = self._summarize_unified_memory_review_candidates(confirmations)
        source_view_counts = self._count_text_field(confirmations, "source_view")
        candidate_type_counts = self._count_text_field(confirmations, "candidate_type")
        queue_bucket_counts = self._count_text_field(confirmations, "queue_bucket")
        decision_counts = self._count_text_field(confirmations, "decision")
        accepted_count = decision_counts.get("accepted", 0)
        deferred_count = decision_counts.get("deferred", 0)
        rejected_count = decision_counts.get("rejected", 0)
        return {
            "summary": {
                "total_confirmations": len(confirmations),
                "accepted_count": accepted_count,
                "deferred_count": deferred_count,
                "rejected_count": rejected_count,
                "acceptance_rate": round((accepted_count / len(confirmations)), 4) if confirmations else 0.0,
                "source_view_counts": source_view_counts,
                "candidate_type_counts": candidate_type_counts,
                "queue_bucket_counts": queue_bucket_counts,
                "decision_counts": decision_counts,
                "top_candidate_limit": limit,
                "implementation_status": "Implemented",
            },
            "top_accepted_candidates": [item for item in candidate_rows if item["accepted_count"] > 0][:limit],
            "top_deferred_candidates": [
                item
                for item in sorted(
                    candidate_rows,
                    key=lambda row: (-row["deferred_count"], -row["total_confirmations"], row["label"]),
                )
                if item["deferred_count"] > 0
            ][:limit],
            "top_rejected_candidates": [
                item
                for item in sorted(
                    candidate_rows,
                    key=lambda row: (-row["rejected_count"], -row["total_confirmations"], row["label"]),
                )
                if item["rejected_count"] > 0
            ][:limit],
            "implementation_status": "Implemented",
        }

    def unified_memory_review_signals(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        min_confirmations = max(1, int(payload.get("min_confirmations", 2)))
        confirmations = self._list_unified_memory_review_confirmations()
        source_rows = self._build_unified_signal_rows(confirmations, "source_view", min_confirmations)
        candidate_type_rows = self._build_unified_signal_rows(confirmations, "candidate_type", min_confirmations)
        queue_bucket_rows = self._build_unified_signal_rows(confirmations, "queue_bucket", min_confirmations)
        return {
            "source_view_signals": source_rows,
            "candidate_type_signals": candidate_type_rows,
            "queue_bucket_signals": queue_bucket_rows,
            "summary": {
                "total_confirmations": len(confirmations),
                "min_confirmations": min_confirmations,
                "source_view_signal_count": len(source_rows),
                "candidate_type_signal_count": len(candidate_type_rows),
                "queue_bucket_signal_count": len(queue_bucket_rows),
                "implementation_status": "Implemented",
            },
            "integration_note": {
                "implementation_status": "Implemented",
                "current_route": "unified_memory_review_confirmation -> unified_memory_review_summary -> unified_memory_review_signals",
                "future_route": "TODO: connect accepted signal rows into profile weighting or candidate ranking after more governance history accumulates.",
            },
            "implementation_status": "Implemented",
        }

    def unified_memory_review_ranking_suggestions(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        min_confirmations = max(1, int(payload.get("min_confirmations", 2)))
        profile = str(payload.get("profile", "legacy-first") or "legacy-first")
        signals = self.unified_memory_review_signals({"min_confirmations": min_confirmations})
        source_suggestions = self._build_ranking_suggestions_from_signals(
            signal_rows=signals.get("source_view_signals", []),
            dimension="source_view",
        )
        candidate_type_suggestions = self._build_ranking_suggestions_from_signals(
            signal_rows=signals.get("candidate_type_signals", []),
            dimension="candidate_type",
        )
        queue_bucket_suggestions = self._build_ranking_suggestions_from_signals(
            signal_rows=signals.get("queue_bucket_signals", []),
            dimension="queue_bucket",
        )
        return {
            "profile": profile,
            "source_view_suggestions": source_suggestions,
            "candidate_type_suggestions": candidate_type_suggestions,
            "queue_bucket_suggestions": queue_bucket_suggestions,
            "summary": {
                "min_confirmations": min_confirmations,
                "profile": profile,
                "source_view_suggestion_count": len(source_suggestions),
                "candidate_type_suggestion_count": len(candidate_type_suggestions),
                "queue_bucket_suggestion_count": len(queue_bucket_suggestions),
                "implementation_status": "Implemented",
            },
            "integration_note": {
                "implementation_status": "Implemented",
                "current_route": "unified_memory_review_signals -> unified_memory_review_ranking_suggestions -> human review",
                "future_route": "TODO: after enough governance history, allow approved suggestions to influence legacy profile or unified queue ranking inputs.",
            },
            "implementation_status": "Implemented",
        }

    def unified_memory_review_ranking_diff(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        limit = max(1, int(payload.get("limit", 10)))
        min_confirmations = max(1, int(payload.get("min_confirmations", 2)))
        profile = str(payload.get("profile", "legacy-first") or "legacy-first")
        queue = self.unified_memory_review_queue({
            "limit": 1000,
            "min_count": min_confirmations,
            "profile": profile,
        })
        suggestions = self.unified_memory_review_ranking_suggestions({
            "min_confirmations": min_confirmations,
            "profile": profile,
        })
        suggestion_index = self._build_unified_suggestion_index(suggestions)
        current_items = queue.get("items", [])
        diff_rows: list[dict[str, Any]] = []
        for index, item in enumerate(current_items, start=1):
            suggestion_parts = []
            suggested_score = float(item.get("priority_score", 0.0))
            for dimension in ("source_view", "candidate_type", "queue_bucket"):
                key = str(item.get(dimension, "") or "").strip()
                if not key:
                    continue
                suggestion = suggestion_index.get((dimension, key))
                if not suggestion:
                    continue
                delta = int(suggestion.get("suggested_weight_delta", 0))
                suggested_score += delta
                suggestion_parts.append({
                    "dimension": dimension,
                    "key": key,
                    "weight_signal": suggestion.get("weight_signal", "observe"),
                    "suggested_weight_delta": delta,
                })
            diff_rows.append(
                {
                    "current_rank": index,
                    "label": item.get("label", ""),
                    "source_view": item.get("source_view", ""),
                    "candidate_type": item.get("candidate_type", ""),
                    "queue_bucket": item.get("queue_bucket", ""),
                    "current_priority_score": float(item.get("priority_score", 0.0)),
                    "suggested_priority_score": round(suggested_score, 4),
                    "score_delta": round(suggested_score - float(item.get("priority_score", 0.0)), 4),
                    "suggestion_parts": suggestion_parts,
                    "implementation_status": "Implemented",
                }
            )
        sorted_rows = sorted(
            diff_rows,
            key=lambda item: (
                self._review_bucket_rank(item.get("queue_bucket", "observe")),
                -float(item.get("suggested_priority_score", 0.0)),
                item.get("label", ""),
            ),
        )
        for index, row in enumerate(sorted_rows, start=1):
            row["suggested_rank"] = index
            row["rank_changed"] = row["current_rank"] != row["suggested_rank"]
        sorted_rows.sort(
            key=lambda item: (
                not item["rank_changed"],
                item["suggested_rank"],
                item["current_rank"],
            )
        )
        returned_rows = sorted_rows[:limit]
        return {
            "items": returned_rows,
            "summary": {
                "profile": profile,
                "min_confirmations": min_confirmations,
                "total_candidates": len(diff_rows),
                "returned_candidates": len(returned_rows),
                "rank_changed_count": len([item for item in diff_rows if item.get("rank_changed")]),
                "implementation_status": "Implemented",
            },
            "integration_note": {
                "implementation_status": "Implemented",
                "current_route": "unified_memory_review_queue + unified_memory_review_ranking_suggestions -> unified_memory_review_ranking_diff",
                "future_route": "TODO: once ranking diffs look stable, allow human-approved suggestion sets to update real ranking inputs.",
            },
            "implementation_status": "Implemented",
        }

    def confirm_unified_memory_review_ranking_diff_item(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        label = str(payload.get("label", "") or "").strip()
        source_view = str(payload.get("source_view", "") or "").strip()
        candidate_type = str(payload.get("candidate_type", "") or "").strip()
        decision = str(payload.get("decision", "accepted") or "accepted").strip()
        if not label:
            raise ValueError("label is required")
        if not source_view:
            raise ValueError("source_view is required")
        if not candidate_type:
            raise ValueError("candidate_type is required")
        if decision not in {"accepted", "deferred", "rejected"}:
            raise ValueError("decision must be one of {'accepted','deferred','rejected'}")
        target_id = new_id("ranking_diff", f"{source_view}:{candidate_type}:{label}")
        summary = str(payload.get("summary", "") or "").strip()
        if not summary:
            action_text = {
                "accepted": "采纳这次排序变化建议",
                "deferred": "暂缓这次排序变化建议",
                "rejected": "否决这次排序变化建议",
            }[decision]
            summary = f"人工确认 unified memory ranking diff 候选“{label}”，当前处理结果：{action_text}。"
        result = self.decisions.create_learning_entry(
            entry_type="unified_memory_review_ranking_diff_confirmation",
            target_type="unified_memory_ranking_diff",
            target_ids=[target_id],
            summary=summary,
            source_record_id=str(payload.get("source_record_id", "") or ""),
            evidence_ids=payload.get("evidence_ids", []),
            counter_evidence_ids=payload.get("counter_evidence_ids", []),
            lessons=payload.get("lessons", []),
            improvement_items=payload.get("improvement_items", []),
            confidence_delta=float(payload.get("confidence_delta", 0.0)),
            metadata={
                "implementation_status": "Implemented",
                "label": label,
                "source_view": source_view,
                "candidate_type": candidate_type,
                "decision": decision,
                "profile": str(payload.get("profile", "") or ""),
                "current_rank": int(payload.get("current_rank", 0) or 0),
                "suggested_rank": int(payload.get("suggested_rank", 0) or 0),
                "score_delta": float(payload.get("score_delta", 0.0) or 0.0),
            },
        )
        self.board.update(
            summary=f"记录 unified memory ranking diff 确认：{label} -> {decision}（来源 {source_view}）。",
            event_type="unified_memory_review_ranking_diff_confirmed",
        )
        return result

    def unified_memory_review_ranking_diff_summary(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        limit = max(1, int(payload.get("limit", 5)))
        confirmations = self._list_unified_memory_review_ranking_diff_confirmations()
        candidate_rows = self._summarize_unified_memory_review_ranking_diff_candidates(confirmations)
        source_view_counts = self._count_text_field(confirmations, "source_view")
        candidate_type_counts = self._count_text_field(confirmations, "candidate_type")
        decision_counts = self._count_text_field(confirmations, "decision")
        profile_counts = self._count_text_field(confirmations, "profile")
        accepted_count = decision_counts.get("accepted", 0)
        deferred_count = decision_counts.get("deferred", 0)
        rejected_count = decision_counts.get("rejected", 0)
        return {
            "summary": {
                "total_confirmations": len(confirmations),
                "accepted_count": accepted_count,
                "deferred_count": deferred_count,
                "rejected_count": rejected_count,
                "acceptance_rate": round((accepted_count / len(confirmations)), 4) if confirmations else 0.0,
                "source_view_counts": source_view_counts,
                "candidate_type_counts": candidate_type_counts,
                "decision_counts": decision_counts,
                "profile_counts": profile_counts,
                "top_candidate_limit": limit,
                "implementation_status": "Implemented",
            },
            "top_accepted_candidates": [item for item in candidate_rows if item["accepted_count"] > 0][:limit],
            "top_deferred_candidates": [
                item
                for item in sorted(
                    candidate_rows,
                    key=lambda row: (-row["deferred_count"], -row["total_confirmations"], row["label"]),
                )
                if item["deferred_count"] > 0
            ][:limit],
            "top_rejected_candidates": [
                item
                for item in sorted(
                    candidate_rows,
                    key=lambda row: (-row["rejected_count"], -row["total_confirmations"], row["label"]),
                )
                if item["rejected_count"] > 0
            ][:limit],
            "integration_note": {
                "implementation_status": "Implemented",
                "current_route": "unified_memory_review_ranking_diff_confirmation -> unified_memory_review_ranking_diff_summary -> human governance baseline",
                "future_route": "TODO: after enough confirmation history, use accepted or rejected ranking diff patterns as evidence before allowing approved suggestion sets into real ranking configuration.",
            },
            "implementation_status": "Implemented",
        }

    def unified_memory_review_ranking_diff_signals(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        min_confirmations = max(1, int(payload.get("min_confirmations", 2)))
        confirmations = self._list_unified_memory_review_ranking_diff_confirmations()
        profile_rows = self._build_unified_signal_rows(confirmations, "profile", min_confirmations)
        source_rows = self._build_unified_signal_rows(confirmations, "source_view", min_confirmations)
        candidate_type_rows = self._build_unified_signal_rows(confirmations, "candidate_type", min_confirmations)
        return {
            "profile_signals": profile_rows,
            "source_view_signals": source_rows,
            "candidate_type_signals": candidate_type_rows,
            "summary": {
                "total_confirmations": len(confirmations),
                "min_confirmations": min_confirmations,
                "profile_signal_count": len(profile_rows),
                "source_view_signal_count": len(source_rows),
                "candidate_type_signal_count": len(candidate_type_rows),
                "implementation_status": "Implemented",
            },
            "integration_note": {
                "implementation_status": "Implemented",
                "current_route": "unified_memory_review_ranking_diff_confirmation -> unified_memory_review_ranking_diff_summary -> unified_memory_review_ranking_diff_signals",
                "future_route": "TODO: only after enough confirmation history, allow accepted ranking-diff signals to support human-approved ranking configuration changes.",
            },
            "implementation_status": "Implemented",
        }

    def unified_memory_review_ranking_policy_suggestions(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        min_confirmations = max(1, int(payload.get("min_confirmations", 2)))
        profile = str(payload.get("profile", "legacy-first") or "legacy-first")
        signals = self.unified_memory_review_ranking_diff_signals({"min_confirmations": min_confirmations})
        profile_suggestions = self._build_ranking_suggestions_from_signals(
            signal_rows=signals.get("profile_signals", []),
            dimension="profile",
        )
        source_suggestions = self._build_ranking_suggestions_from_signals(
            signal_rows=signals.get("source_view_signals", []),
            dimension="source_view",
        )
        candidate_type_suggestions = self._build_ranking_suggestions_from_signals(
            signal_rows=signals.get("candidate_type_signals", []),
            dimension="candidate_type",
        )
        return {
            "profile": profile,
            "profile_suggestions": profile_suggestions,
            "source_view_suggestions": source_suggestions,
            "candidate_type_suggestions": candidate_type_suggestions,
            "summary": {
                "profile": profile,
                "min_confirmations": min_confirmations,
                "profile_suggestion_count": len(profile_suggestions),
                "source_view_suggestion_count": len(source_suggestions),
                "candidate_type_suggestion_count": len(candidate_type_suggestions),
                "implementation_status": "Implemented",
            },
            "integration_note": {
                "implementation_status": "Implemented",
                "current_route": "unified_memory_review_ranking_diff_signals -> unified_memory_review_ranking_policy_suggestions -> human approval",
                "future_route": "TODO: keep this as a read-only policy suggestion layer until a separate approval gate is added for any real ranking configuration writeback.",
            },
            "implementation_status": "Implemented",
        }

    def confirm_unified_memory_review_ranking_policy_suggestion(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        dimension = str(payload.get("dimension", "") or "").strip()
        key = str(payload.get("key", "") or "").strip()
        decision = str(payload.get("decision", "accepted") or "accepted").strip()
        profile = str(payload.get("profile", "legacy-first") or "legacy-first").strip()
        if dimension not in {"profile", "source_view", "candidate_type"}:
            raise ValueError("dimension must be one of {'profile','source_view','candidate_type'}")
        if not key:
            raise ValueError("key is required")
        if decision not in {"accepted", "deferred", "rejected"}:
            raise ValueError("decision must be one of {'accepted','deferred','rejected'}")
        target_id = new_id("ranking_policy", f"{profile}:{dimension}:{key}")
        summary = str(payload.get("summary", "") or "").strip()
        if not summary:
            action_text = {
                "accepted": "采纳这条排序策略建议",
                "deferred": "暂缓这条排序策略建议",
                "rejected": "否决这条排序策略建议",
            }[decision]
            summary = f"人工确认 unified memory ranking policy 建议“{dimension}:{key}”，当前处理结果：{action_text}。"
        result = self.decisions.create_learning_entry(
            entry_type="unified_memory_review_ranking_policy_approval",
            target_type="unified_memory_ranking_policy",
            target_ids=[target_id],
            summary=summary,
            source_record_id=str(payload.get("source_record_id", "") or ""),
            evidence_ids=payload.get("evidence_ids", []),
            counter_evidence_ids=payload.get("counter_evidence_ids", []),
            lessons=payload.get("lessons", []),
            improvement_items=payload.get("improvement_items", []),
            confidence_delta=float(payload.get("confidence_delta", 0.0)),
            metadata={
                "implementation_status": "Implemented",
                "dimension": dimension,
                "key": key,
                "decision": decision,
                "profile": profile,
                "weight_signal": str(payload.get("weight_signal", "observe") or "observe"),
                "suggested_weight_delta": int(payload.get("suggested_weight_delta", 0) or 0),
            },
        )
        self.board.update(
            summary=f"记录 unified memory ranking policy 审批：{dimension}:{key} -> {decision}（profile {profile}）。",
            event_type="unified_memory_review_ranking_policy_approved",
        )
        return result

    def unified_memory_review_ranking_policy_approval_summary(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        limit = max(1, int(payload.get("limit", 5)))
        approvals = self._list_unified_memory_review_ranking_policy_approvals()
        candidate_rows = self._summarize_unified_memory_review_ranking_policy_approvals(approvals)
        dimension_counts = self._count_text_field(approvals, "dimension")
        key_counts = self._count_text_field(approvals, "key")
        decision_counts = self._count_text_field(approvals, "decision")
        profile_counts = self._count_text_field(approvals, "profile")
        accepted_count = decision_counts.get("accepted", 0)
        deferred_count = decision_counts.get("deferred", 0)
        rejected_count = decision_counts.get("rejected", 0)
        return {
            "summary": {
                "total_approvals": len(approvals),
                "accepted_count": accepted_count,
                "deferred_count": deferred_count,
                "rejected_count": rejected_count,
                "acceptance_rate": round((accepted_count / len(approvals)), 4) if approvals else 0.0,
                "dimension_counts": dimension_counts,
                "key_counts": key_counts,
                "decision_counts": decision_counts,
                "profile_counts": profile_counts,
                "top_candidate_limit": limit,
                "implementation_status": "Implemented",
            },
            "top_accepted_policy_suggestions": [item for item in candidate_rows if item["accepted_count"] > 0][:limit],
            "top_deferred_policy_suggestions": [
                item
                for item in sorted(
                    candidate_rows,
                    key=lambda row: (-row["deferred_count"], -row["total_approvals"], row["dimension"], row["key"]),
                )
                if item["deferred_count"] > 0
            ][:limit],
            "top_rejected_policy_suggestions": [
                item
                for item in sorted(
                    candidate_rows,
                    key=lambda row: (-row["rejected_count"], -row["total_approvals"], row["dimension"], row["key"]),
                )
                if item["rejected_count"] > 0
            ][:limit],
            "integration_note": {
                "implementation_status": "Implemented",
                "current_route": "unified_memory_review_ranking_policy_approval -> unified_memory_review_ranking_policy_approval_summary -> human governance baseline",
                "future_route": "TODO: after enough approval history, derive read-only approval signals before considering any configuration writeback gate.",
            },
            "implementation_status": "Implemented",
        }

    def unified_memory_review_ranking_policy_approval_signals(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        min_confirmations = max(1, int(payload.get("min_confirmations", 2)))
        approvals = self._list_unified_memory_review_ranking_policy_approvals()
        dimension_rows = self._build_unified_signal_rows(approvals, "dimension", min_confirmations)
        key_rows = self._build_unified_signal_rows(approvals, "key", min_confirmations)
        profile_rows = self._build_unified_signal_rows(approvals, "profile", min_confirmations)
        return {
            "dimension_signals": dimension_rows,
            "key_signals": key_rows,
            "profile_signals": profile_rows,
            "summary": {
                "total_approvals": len(approvals),
                "min_confirmations": min_confirmations,
                "dimension_signal_count": len(dimension_rows),
                "key_signal_count": len(key_rows),
                "profile_signal_count": len(profile_rows),
                "implementation_status": "Implemented",
            },
            "integration_note": {
                "implementation_status": "Implemented",
                "current_route": "unified_memory_review_ranking_policy_approval -> unified_memory_review_ranking_policy_approval_summary -> unified_memory_review_ranking_policy_approval_signals",
                "future_route": "TODO: keep these as read-only governance signals until a separate approval-to-configuration gate and rollback policy exist.",
            },
            "implementation_status": "Implemented",
        }

    def unified_memory_review_ranking_policy_change_candidates(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        min_confirmations = max(1, int(payload.get("min_confirmations", 2)))
        profile = str(payload.get("profile", "legacy-first") or "legacy-first")
        signals = self.unified_memory_review_ranking_policy_approval_signals(
            {"min_confirmations": min_confirmations}
        )
        candidates: list[dict[str, Any]] = []
        for rows, dimension in (
            (signals.get("dimension_signals", []), "dimension"),
            (signals.get("key_signals", []), "key"),
            (signals.get("profile_signals", []), "profile"),
        ):
            for item in self._build_ranking_suggestions_from_signals(rows, dimension):
                delta = int(item.get("suggested_weight_delta", 0))
                if delta > 0:
                    change_bucket = "promote_candidate"
                elif delta < 0:
                    change_bucket = "downgrade_candidate"
                else:
                    change_bucket = "observe_only"
                candidates.append(
                    {
                        "dimension": dimension,
                        "key": item.get("key", ""),
                        "profile": profile,
                        "weight_signal": item.get("weight_signal", "observe"),
                        "suggested_weight_delta": delta,
                        "change_bucket": change_bucket,
                        "reason": item.get("reason", ""),
                        "accepted_count": item.get("accepted_count", 0),
                        "deferred_count": item.get("deferred_count", 0),
                        "rejected_count": item.get("rejected_count", 0),
                        "total_confirmations": item.get("total_confirmations", 0),
                        "implementation_status": "Implemented",
                    }
                )
        candidates.sort(
            key=lambda item: (
                0 if item["change_bucket"] == "promote_candidate" else 1 if item["change_bucket"] == "downgrade_candidate" else 2,
                -abs(int(item["suggested_weight_delta"])),
                -int(item["total_confirmations"]),
                item["dimension"],
                item["key"],
            )
        )
        return {
            "profile": profile,
            "candidates": candidates,
            "summary": {
                "profile": profile,
                "min_confirmations": min_confirmations,
                "total_candidates": len(candidates),
                "promote_candidate_count": len([item for item in candidates if item["change_bucket"] == "promote_candidate"]),
                "downgrade_candidate_count": len([item for item in candidates if item["change_bucket"] == "downgrade_candidate"]),
                "observe_only_count": len([item for item in candidates if item["change_bucket"] == "observe_only"]),
                "implementation_status": "Implemented",
            },
            "integration_note": {
                "implementation_status": "Implemented",
                "current_route": "unified_memory_review_ranking_policy_approval_signals -> unified_memory_review_ranking_policy_change_candidates -> human review",
                "future_route": "TODO: after a separate approval and rollback layer exists, allow approved candidate bundles to be versioned as proposed configuration changes without directly mutating live configuration.",
            },
            "implementation_status": "Implemented",
        }

    def confirm_unified_memory_review_ranking_policy_change_candidate(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        dimension = str(payload.get("dimension", "") or "").strip()
        key = str(payload.get("key", "") or "").strip()
        decision = str(payload.get("decision", "accepted") or "accepted").strip()
        profile = str(payload.get("profile", "legacy-first") or "legacy-first").strip()
        change_bucket = str(payload.get("change_bucket", "observe_only") or "observe_only").strip()
        if dimension not in {"dimension", "key", "profile"}:
            raise ValueError("dimension must be one of {'dimension','key','profile'}")
        if not key:
            raise ValueError("key is required")
        if decision not in {"accepted", "deferred", "rejected"}:
            raise ValueError("decision must be one of {'accepted','deferred','rejected'}")
        target_id = new_id("ranking_change_candidate", f"{profile}:{dimension}:{key}:{change_bucket}")
        summary = str(payload.get("summary", "") or "").strip()
        if not summary:
            action_text = {
                "accepted": "采纳这条候选配置变更",
                "deferred": "暂缓这条候选配置变更",
                "rejected": "否决这条候选配置变更",
            }[decision]
            summary = f"人工确认 unified memory ranking policy 候选变更“{dimension}:{key}”，当前处理结果：{action_text}。"
        result = self.decisions.create_learning_entry(
            entry_type="unified_memory_review_ranking_policy_change_candidate_approval",
            target_type="unified_memory_ranking_policy_change_candidate",
            target_ids=[target_id],
            summary=summary,
            source_record_id=str(payload.get("source_record_id", "") or ""),
            evidence_ids=payload.get("evidence_ids", []),
            counter_evidence_ids=payload.get("counter_evidence_ids", []),
            lessons=payload.get("lessons", []),
            improvement_items=payload.get("improvement_items", []),
            confidence_delta=float(payload.get("confidence_delta", 0.0)),
            metadata={
                "implementation_status": "Implemented",
                "dimension": dimension,
                "key": key,
                "decision": decision,
                "profile": profile,
                "change_bucket": change_bucket,
                "weight_signal": str(payload.get("weight_signal", "observe") or "observe"),
                "suggested_weight_delta": int(payload.get("suggested_weight_delta", 0) or 0),
            },
        )
        self.board.update(
            summary=f"记录 unified memory ranking policy 候选变更审批：{dimension}:{key} -> {decision}（bucket {change_bucket}，profile {profile}）。",
            event_type="unified_memory_review_ranking_policy_change_candidate_approved",
        )
        return result

    def unified_memory_review_ranking_policy_change_candidate_approval_summary(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        limit = max(1, int(payload.get("limit", 5)))
        approvals = self._list_unified_memory_review_ranking_policy_change_candidate_approvals()
        candidate_rows = self._summarize_unified_memory_review_ranking_policy_change_candidate_approvals(approvals)
        dimension_counts = self._count_text_field(approvals, "dimension")
        key_counts = self._count_text_field(approvals, "key")
        decision_counts = self._count_text_field(approvals, "decision")
        profile_counts = self._count_text_field(approvals, "profile")
        change_bucket_counts = self._count_text_field(approvals, "change_bucket")
        accepted_count = decision_counts.get("accepted", 0)
        deferred_count = decision_counts.get("deferred", 0)
        rejected_count = decision_counts.get("rejected", 0)
        return {
            "summary": {
                "total_approvals": len(approvals),
                "accepted_count": accepted_count,
                "deferred_count": deferred_count,
                "rejected_count": rejected_count,
                "acceptance_rate": round((accepted_count / len(approvals)), 4) if approvals else 0.0,
                "dimension_counts": dimension_counts,
                "key_counts": key_counts,
                "decision_counts": decision_counts,
                "profile_counts": profile_counts,
                "change_bucket_counts": change_bucket_counts,
                "top_candidate_limit": limit,
                "implementation_status": "Implemented",
            },
            "top_accepted_change_candidates": [item for item in candidate_rows if item["accepted_count"] > 0][:limit],
            "top_deferred_change_candidates": [
                item
                for item in sorted(
                    candidate_rows,
                    key=lambda row: (-row["deferred_count"], -row["total_approvals"], row["dimension"], row["key"]),
                )
                if item["deferred_count"] > 0
            ][:limit],
            "top_rejected_change_candidates": [
                item
                for item in sorted(
                    candidate_rows,
                    key=lambda row: (-row["rejected_count"], -row["total_approvals"], row["dimension"], row["key"]),
                )
                if item["rejected_count"] > 0
            ][:limit],
            "integration_note": {
                "implementation_status": "Implemented",
                "current_route": "unified_memory_review_ranking_policy_change_candidate_approval -> unified_memory_review_ranking_policy_change_candidate_approval_summary -> human governance baseline",
                "future_route": "TODO: after enough candidate approval history, derive read-only signals before any configuration-bundle approval or rollback layer is allowed.",
            },
            "implementation_status": "Implemented",
        }

    def inspect_learning_entry(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.retriever.inspect_learning_entry(payload.get("learning_entry_id", ""))

    def inspect_atom_writeback(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.retriever.inspect_atom_writeback(payload.get("atom_id", ""))

    def writeback_overview(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return self.retriever.writeback_overview(int(payload.get("limit", 10)))

    def capture_writeback_snapshot(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        limit = int(payload.get("limit", 10))
        overview = self.retriever.writeback_overview(limit)
        snapshot = WritebackSnapshot(
            name=payload.get("name", "") or f"writeback_snapshot_{limit}",
            top_writeback_atoms=overview["top_writeback_atoms"],
            top_recommended_tags=overview["top_recommended_tags"],
            top_chain_texts=overview["top_chain_texts"],
            flagged_for_review=overview["flagged_for_review"],
            summary=overview["summary"],
            metadata={
                "implementation_status": "Implemented",
                "limit": limit,
                "latest_apply_buckets": overview.get("latest_apply_buckets", {}),
            },
        )
        self.store.save("writeback_snapshots", snapshot)
        evo = self.evolution.record(
            trigger="writeback_snapshot_capture",
            observation=f"Captured writeback overview snapshot {snapshot.id}.",
            change_type="audit_snapshot",
            affected_ids=[snapshot.id],
            proposed_update="Use periodic snapshots to compare how writeback intensity changes over time.",
            applied=True,
            metrics={
                "returned_atom_count": len(snapshot.top_writeback_atoms),
                "flagged_atom_count": len(snapshot.flagged_for_review),
                "new_or_changed_count": int(snapshot.metadata.get("latest_apply_buckets", {}).get("new_or_changed_count", 0)),
                "confirmed_only_count": int(snapshot.metadata.get("latest_apply_buckets", {}).get("confirmed_only_count", 0)),
            },
        )
        self.board.update(
            summary=f"捕获 writeback 快照 {snapshot.id}，可用于后续基线比较。",
            event_type="writeback_snapshot_captured",
        )
        return {"snapshot": to_dict(snapshot), "evolution_log": to_dict(evo)}

    def compare_writeback_snapshot(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        current_limit = int(payload.get("limit", 10))
        baseline_id = payload.get("snapshot_id", "")
        baseline = self._load_writeback_snapshot(baseline_id)
        current = self.retriever.writeback_overview(current_limit)
        baseline_atoms = {row["atom_id"]: row for row in baseline.get("top_writeback_atoms", [])}
        current_atoms = {row["atom_id"]: row for row in current.get("top_writeback_atoms", [])}
        all_atom_ids = sorted(set(baseline_atoms) | set(current_atoms))
        atom_deltas: list[dict[str, Any]] = []
        transition_counts: dict[str, int] = {}
        for atom_id in all_atom_ids:
            before = baseline_atoms.get(atom_id, {})
            after = current_atoms.get(atom_id, {})
            baseline_state = before.get("latest_apply_state", "not_in_snapshot")
            current_state = after.get("latest_apply_state", "not_in_current")
            transition_key = f"{baseline_state}->{current_state}"
            transition_counts[transition_key] = transition_counts.get(transition_key, 0) + 1
            atom_deltas.append(
                {
                    "atom_id": atom_id,
                    "title": after.get("title") or before.get("title", ""),
                    "baseline_score": before.get("writeback_score", 0),
                    "current_score": after.get("writeback_score", 0),
                    "score_delta": after.get("writeback_score", 0) - before.get("writeback_score", 0),
                    "baseline_recommended_tag_count": before.get("recommended_tag_count", 0),
                    "current_recommended_tag_count": after.get("recommended_tag_count", 0),
                    "baseline_latest_apply_state": baseline_state,
                    "current_latest_apply_state": current_state,
                    "latest_apply_state_changed": baseline_state != current_state,
                    "suggest_human_review": bool(after.get("suggest_human_review", False)),
                }
            )
        atom_deltas.sort(
            key=lambda item: (
                not item["latest_apply_state_changed"],
                -item["score_delta"],
                -item["current_score"],
                item["atom_id"],
            )
        )
        baseline_buckets = baseline.get("metadata", {}).get("latest_apply_buckets", {})
        current_buckets = current.get("latest_apply_buckets", {})
        bucket_migration = {
            "baseline": baseline_buckets,
            "current": current_buckets,
            "count_deltas": {
                "new_or_changed_delta": int(current_buckets.get("new_or_changed_count", 0)) - int(baseline_buckets.get("new_or_changed_count", 0)),
                "confirmed_only_delta": int(current_buckets.get("confirmed_only_count", 0)) - int(baseline_buckets.get("confirmed_only_count", 0)),
                "no_recent_apply_state_delta": int(current_buckets.get("no_recent_apply_state_count", 0)) - int(baseline_buckets.get("no_recent_apply_state_count", 0)),
            },
            "state_transitions": [
                {"transition": name, "count": count}
                for name, count in sorted(transition_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            "implementation_status": "Implemented",
        }
        return {
            "baseline_snapshot": baseline,
            "current_overview": current,
            "atom_deltas": atom_deltas,
            "bucket_migration": bucket_migration,
            "summary": {
                "baseline_snapshot_id": baseline.get("id", ""),
                "atoms_with_changed_scores": len([row for row in atom_deltas if row["score_delta"] != 0]),
                "atoms_with_apply_state_transition": len([row for row in atom_deltas if row["latest_apply_state_changed"]]),
                "current_flagged_atom_count": len(current.get("flagged_for_review", [])),
                "implementation_status": "Implemented",
            },
        }

    def legacy_lessons_mapping(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        legacy_path = self.root / "second-brain" / "lessons.md"
        if not legacy_path.exists():
            return {
                "legacy_file": str(legacy_path),
                "legacy_lessons": [],
                "emerging_learning_lessons": [],
                "summary": {
                    "legacy_file_status": "Interface",
                    "reason": "Legacy lessons file not found; mapping is read-only and requires second-brain/lessons.md.",
                },
                "positive_experience_mapping": {
                    "implementation_status": "TODO",
                    "reason": "v0.1 only maps explicit lesson lines and does not yet parse full positive-experience blocks.",
                },
            }
        legacy_lessons = self._read_legacy_lessons(legacy_path)
        learning_entries = self.store.list_records("learning_entries", limit=100000)
        lesson_counts = self._collect_text_counts(learning_entries, "lessons")
        improvement_counts = self._collect_text_counts(learning_entries, "improvement_items")
        chain_state_index = self._build_learning_chain_state_index()
        pair_counts, pair_atom_index = self._collect_lesson_improvement_pairs(learning_entries)

        mapped_legacy_lessons: list[dict[str, Any]] = []
        for lesson in legacy_lessons:
            normalized = self._normalize_lesson_text(lesson)
            state_info = chain_state_index.get(normalized, {})
            current_count = lesson_counts.get(normalized, 0)
            if current_count <= 0:
                mapping_status = "legacy_only"
            elif state_info.get("current_apply_state") == "new_or_changed":
                mapping_status = "mapped_new_or_changed"
            elif state_info.get("current_apply_state") == "confirmed_only":
                mapping_status = "mapped_confirmed_only"
            else:
                mapping_status = "mapped_without_recent_apply_state"
            mapped_legacy_lessons.append(
                {
                    "lesson_text": lesson,
                    "normalized_text": normalized,
                    "current_learning_count": current_count,
                    "current_apply_state": state_info.get("current_apply_state", "not_in_learning_chain_writeback"),
                    "matching_atom_ids": state_info.get("matching_atom_ids", []),
                    "mapping_status": mapping_status,
                    "implementation_status": "Implemented",
                }
            )

        legacy_lesson_set = {self._normalize_lesson_text(text) for text in legacy_lessons}
        emerging_learning_lessons: list[dict[str, Any]] = []
        for normalized, count in sorted(lesson_counts.items(), key=lambda item: (-item[1], item[0])):
            if normalized in legacy_lesson_set:
                continue
            state_info = chain_state_index.get(normalized, {})
            recommendation = self._classify_emerging_lesson(
                current_learning_count=count,
                current_apply_state=state_info.get("current_apply_state", "not_in_learning_chain_writeback"),
                matching_atom_ids=state_info.get("matching_atom_ids", []),
            )
            emerging_learning_lessons.append(
                {
                    "lesson_text": normalized,
                    "current_learning_count": count,
                    "current_apply_state": state_info.get("current_apply_state", "not_in_learning_chain_writeback"),
                    "matching_atom_ids": state_info.get("matching_atom_ids", []),
                    "migration_status": recommendation["migration_status"],
                    "migration_reason": recommendation["migration_reason"],
                    "evidence_gap": recommendation["evidence_gap"],
                    "audit_explanation": self._build_audit_explanation(
                        entity_type="lesson",
                        label=normalized,
                        evidence_gap=recommendation["evidence_gap"],
                    ),
                    "target_file": str(legacy_path),
                    "implementation_status": "Implemented",
                }
            )

        emerging_improvement_items: list[dict[str, Any]] = []
        for normalized, count in sorted(improvement_counts.items(), key=lambda item: (-item[1], item[0])):
            state_info = chain_state_index.get(normalized, {})
            recommendation = self._classify_emerging_lesson(
                current_learning_count=count,
                current_apply_state=state_info.get("current_apply_state", "not_in_learning_chain_writeback"),
                matching_atom_ids=state_info.get("matching_atom_ids", []),
            )
            emerging_improvement_items.append(
                {
                    "improvement_item_text": normalized,
                    "current_learning_count": count,
                    "current_apply_state": state_info.get("current_apply_state", "not_in_learning_chain_writeback"),
                    "matching_atom_ids": state_info.get("matching_atom_ids", []),
                    "migration_status": recommendation["migration_status"],
                    "migration_reason": recommendation["migration_reason"],
                    "evidence_gap": recommendation["evidence_gap"],
                    "audit_explanation": self._build_audit_explanation(
                        entity_type="improvement_item",
                        label=normalized,
                        evidence_gap=recommendation["evidence_gap"],
                    ),
                    "target_file": str(legacy_path),
                    "implementation_status": "Implemented",
                }
            )

        lesson_improvement_pairs: list[dict[str, Any]] = []
        for pair_key, pair_count in sorted(pair_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1])):
            lesson_text, improvement_text = pair_key
            lesson_state = chain_state_index.get(lesson_text, {}).get("current_apply_state", "not_in_learning_chain_writeback")
            improvement_state = chain_state_index.get(improvement_text, {}).get("current_apply_state", "not_in_learning_chain_writeback")
            matching_atom_ids = sorted(pair_atom_index.get(pair_key, set()))
            pair_recommendation = self._classify_lesson_improvement_pair(
                pair_count=pair_count,
                lesson_apply_state=lesson_state,
                improvement_apply_state=improvement_state,
                matching_atom_ids=matching_atom_ids,
            )
            lesson_improvement_pairs.append(
                {
                    "lesson_text": lesson_text,
                    "improvement_item_text": improvement_text,
                    "pair_count": pair_count,
                    "lesson_current_apply_state": lesson_state,
                    "improvement_current_apply_state": improvement_state,
                    "matching_atom_ids": matching_atom_ids,
                    "migration_status": pair_recommendation["migration_status"],
                    "migration_reason": pair_recommendation["migration_reason"],
                    "evidence_gap": pair_recommendation["evidence_gap"],
                    "audit_explanation": self._build_audit_explanation(
                        entity_type="lesson_improvement_pair",
                        label=f"{lesson_text} -> {improvement_text}",
                        evidence_gap=pair_recommendation["evidence_gap"],
                    ),
                    "implementation_status": "Implemented",
                }
            )

        legacy_memory_candidates = self._build_legacy_memory_candidates(
            legacy_lessons=mapped_legacy_lessons,
            emerging_learning_lessons=emerging_learning_lessons,
            emerging_improvement_items=emerging_improvement_items,
            lesson_improvement_pairs=lesson_improvement_pairs,
        )
        legacy_memory_candidate_groups = self._build_legacy_memory_candidate_groups(legacy_memory_candidates)
        decision_weight_config = self._resolve_legacy_memory_decision_weight_config(payload)
        legacy_memory_decision_view = self._build_legacy_memory_decision_view(legacy_memory_candidates, decision_weight_config)

        summary = {
            "legacy_file_status": "read_only",
            "legacy_lesson_count": len(mapped_legacy_lessons),
            "mapped_confirmed_only_count": len([item for item in mapped_legacy_lessons if item["mapping_status"] == "mapped_confirmed_only"]),
            "mapped_new_or_changed_count": len([item for item in mapped_legacy_lessons if item["mapping_status"] == "mapped_new_or_changed"]),
            "legacy_only_count": len([item for item in mapped_legacy_lessons if item["mapping_status"] == "legacy_only"]),
            "emerging_learning_lesson_count": len(emerging_learning_lessons),
            "emerging_immediate_candidate_count": len([item for item in emerging_learning_lessons if item["migration_status"] == "immediate_candidate"]),
            "emerging_need_more_evidence_count": len([item for item in emerging_learning_lessons if item["migration_status"] == "need_more_evidence"]),
            "emerging_single_noise_count": len([item for item in emerging_learning_lessons if item["migration_status"] == "single_observation_noise"]),
            "lesson_gap_missing_repeat_count": len([item for item in emerging_learning_lessons if item["evidence_gap"]["primary_gap"] == "missing_repeat_count"]),
            "lesson_gap_missing_cross_atom_support_count": len([item for item in emerging_learning_lessons if item["evidence_gap"]["primary_gap"] == "missing_cross_atom_support"]),
            "lesson_gap_missing_writeback_confirmation_count": len([item for item in emerging_learning_lessons if item["evidence_gap"]["primary_gap"] == "missing_writeback_confirmation"]),
            "emerging_improvement_item_count": len(emerging_improvement_items),
            "improvement_immediate_candidate_count": len([item for item in emerging_improvement_items if item["migration_status"] == "immediate_candidate"]),
            "improvement_need_more_evidence_count": len([item for item in emerging_improvement_items if item["migration_status"] == "need_more_evidence"]),
            "improvement_single_noise_count": len([item for item in emerging_improvement_items if item["migration_status"] == "single_observation_noise"]),
            "improvement_gap_missing_repeat_count": len([item for item in emerging_improvement_items if item["evidence_gap"]["primary_gap"] == "missing_repeat_count"]),
            "improvement_gap_missing_cross_atom_support_count": len([item for item in emerging_improvement_items if item["evidence_gap"]["primary_gap"] == "missing_cross_atom_support"]),
            "improvement_gap_missing_writeback_confirmation_count": len([item for item in emerging_improvement_items if item["evidence_gap"]["primary_gap"] == "missing_writeback_confirmation"]),
            "lesson_improvement_pair_count": len(lesson_improvement_pairs),
            "pair_immediate_candidate_count": len([item for item in lesson_improvement_pairs if item["migration_status"] == "immediate_candidate"]),
            "pair_need_more_evidence_count": len([item for item in lesson_improvement_pairs if item["migration_status"] == "need_more_evidence"]),
            "pair_gap_missing_repeat_count": len([item for item in lesson_improvement_pairs if item["evidence_gap"]["primary_gap"] == "missing_repeat_count"]),
            "pair_gap_missing_cross_atom_support_count": len([item for item in lesson_improvement_pairs if item["evidence_gap"]["primary_gap"] == "missing_cross_atom_support"]),
            "pair_gap_missing_writeback_confirmation_count": len([item for item in lesson_improvement_pairs if item["evidence_gap"]["primary_gap"] == "missing_writeback_confirmation"]),
            "legacy_memory_candidate_count": len(legacy_memory_candidates),
            "legacy_memory_candidate_type_counts": self._count_candidate_types(legacy_memory_candidates),
            "legacy_memory_candidate_group_counts": {
                key: int(value.get("candidate_count", 0))
                for key, value in legacy_memory_candidate_groups.items()
            },
            "legacy_memory_promote_now_count": len(legacy_memory_decision_view.get("promote_now", [])),
            "legacy_memory_watch_downgrade_count": len(legacy_memory_decision_view.get("watch_for_downgrade", [])),
            "legacy_memory_decision_weight_profile": decision_weight_config.get("profile", "legacy-first"),
            "implementation_status": "Implemented",
        }
        summary["audit_conclusion"] = self._build_summary_audit_conclusion(summary)

        return {
            "legacy_file": str(legacy_path),
            "legacy_lessons": mapped_legacy_lessons,
            "emerging_learning_lessons": emerging_learning_lessons,
            "emerging_improvement_items": emerging_improvement_items,
            "lesson_improvement_pairs": lesson_improvement_pairs,
            "legacy_memory_candidates": legacy_memory_candidates,
            "legacy_memory_candidate_groups": legacy_memory_candidate_groups,
            "legacy_memory_decision_view": legacy_memory_decision_view,
            "legacy_memory_decision_weight_config": decision_weight_config,
            "summary": summary,
            "improvement_item_mapping": {
                "implementation_status": "Implemented",
                "mode": "read_only_candidate_view",
                "reason": "Legacy lessons.md has no explicit improvement-item section, so v0.1 surfaces candidate migration items without rewriting the file.",
            },
            "lesson_improvement_pair_mapping": {
                "implementation_status": "Implemented",
                "mode": "read_only_cooccurrence_audit",
                "reason": "v0.1 now audits which lessons and improvement actions repeatedly co-occur, without rewriting legacy files.",
            },
            "positive_experience_mapping": {
                "implementation_status": "TODO",
                "reason": "v0.1 only maps explicit lesson lines and does not yet parse full positive-experience blocks.",
            },
        }

    def legacy_memory_decision_view(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        view = str(payload.get("view", "all") or "all")
        if view == "profile-diff":
            return self._legacy_memory_decision_profile_diff(payload)
        mapping = self.legacy_lessons_mapping(payload)
        decision_view = mapping.get("legacy_memory_decision_view", {})
        if view == "promote-now":
            return {
                "view": "promote-now",
                "items": decision_view.get("promote_now", []),
                "summary": {
                    "focus_now": decision_view.get("summary", {}).get("focus_now", ""),
                    "item_count": len(decision_view.get("promote_now", [])),
                    "decision_weight_profile": mapping.get("legacy_memory_decision_weight_config", {}).get("profile", "legacy-first"),
                    "profile_explanation": decision_view.get("summary", {}).get("profile_explanation", ""),
                    "implementation_status": "Implemented",
                },
                "implementation_status": "Implemented",
            }
        if view == "watchlist":
            return {
                "view": "watchlist",
                "items": decision_view.get("watch_for_downgrade", []),
                "summary": {
                    "highest_downgrade_risk": decision_view.get("summary", {}).get("highest_downgrade_risk", ""),
                    "item_count": len(decision_view.get("watch_for_downgrade", [])),
                    "decision_weight_profile": mapping.get("legacy_memory_decision_weight_config", {}).get("profile", "legacy-first"),
                    "profile_explanation": decision_view.get("summary", {}).get("profile_explanation", ""),
                    "implementation_status": "Implemented",
                },
                "implementation_status": "Implemented",
            }
        return {
            "view": "all",
            "decision_view": decision_view,
            "decision_weight_config": mapping.get("legacy_memory_decision_weight_config", {}),
            "implementation_status": "Implemented",
        }

    def confirm_legacy_memory_action(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        candidate_label = str(payload.get("candidate_label", "") or "").strip()
        candidate_type = str(payload.get("candidate_type", "") or "").strip()
        action_bucket = str(payload.get("action_bucket", "promote_earlier") or "promote_earlier").strip()
        if not candidate_label:
            raise ValueError("candidate_label is required")
        if not candidate_type:
            raise ValueError("candidate_type is required")
        raw_accepted = payload.get("accepted", True)
        accepted = raw_accepted if isinstance(raw_accepted, bool) else str(raw_accepted).strip().lower() not in {"false", "0", "no"}
        target_id = new_id("legacy_candidate", f"{candidate_type}:{candidate_label}")
        summary = str(payload.get("summary", "") or "").strip()
        if not summary:
            action_text = "提前整理" if action_bucket == "promote_earlier" else "后移观察"
            outcome_text = "已采纳" if accepted else "暂未采纳"
            summary = f"人工确认 legacy memory 候选“{candidate_label}”建议{action_text}，当前结果：{outcome_text}。"
        result = self.decisions.create_learning_entry(
            entry_type="legacy_memory_action_confirmation",
            target_type="legacy_memory_candidate",
            target_ids=[target_id],
            summary=summary,
            source_record_id=str(payload.get("source_record_id", "") or ""),
            evidence_ids=payload.get("evidence_ids", []),
            counter_evidence_ids=payload.get("counter_evidence_ids", []),
            lessons=payload.get("lessons", []),
            improvement_items=payload.get("improvement_items", []),
            confidence_delta=float(payload.get("confidence_delta", 0.0)),
            metadata={
                "implementation_status": "Implemented",
                "candidate_label": candidate_label,
                "candidate_type": candidate_type,
                "action_bucket": action_bucket,
                "accepted": accepted,
                "left_profile": str(payload.get("left_profile", "") or ""),
                "right_profile": str(payload.get("right_profile", "") or ""),
            },
        )
        self.board.update(
            summary=f"记录 legacy memory 动作确认：{candidate_label} -> {action_bucket}（{'采纳' if accepted else '暂不采纳'}）。",
            event_type="legacy_memory_action_confirmed",
        )
        return result

    def legacy_memory_action_summary(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        limit = max(1, int(payload.get("limit", 5)))
        confirmations = self._list_legacy_action_confirmations()
        candidate_rows = self._summarize_legacy_action_candidates(confirmations)
        profile_rows = self._summarize_legacy_action_profiles(confirmations)
        accepted_count = sum(1 for item in confirmations if item["accepted"])
        rejected_count = len(confirmations) - accepted_count
        return {
            "summary": {
                "total_confirmations": len(confirmations),
                "accepted_count": accepted_count,
                "rejected_count": rejected_count,
                "acceptance_rate": round((accepted_count / len(confirmations)), 4) if confirmations else 0.0,
                "candidate_type_counts": dict(Counter(item["candidate_type"] for item in confirmations)),
                "action_bucket_counts": dict(Counter(item["action_bucket"] for item in confirmations)),
                "top_candidate_limit": limit,
                "implementation_status": "Implemented",
            },
            "top_accepted_candidates": [item for item in candidate_rows if item["accepted_count"] > 0][:limit],
            "top_rejected_candidates": [
                item
                for item in sorted(
                    candidate_rows,
                    key=lambda row: (-row["rejected_count"], -row["total_confirmations"], row["label"]),
                )
                if item["rejected_count"] > 0
            ][:limit],
            "profile_feedback": profile_rows[:limit],
            "implementation_status": "Implemented",
        }

    def _legacy_memory_decision_profile_diff(self, payload: dict[str, Any]) -> dict[str, Any]:
        left_profile = str(payload.get("left_profile", payload.get("profile_a", "legacy-first")) or "legacy-first")
        right_profile = str(payload.get("right_profile", payload.get("profile_b", "pair-first")) or "pair-first")
        left_view = self.legacy_memory_decision_view({"view": "promote-now", "profile": left_profile})
        right_view = self.legacy_memory_decision_view({"view": "promote-now", "profile": right_profile})
        left_items = left_view.get("items", [])
        right_items = right_view.get("items", [])
        left_top = left_view.get("items", [{}])[0] if left_view.get("items") else {}
        right_top = right_view.get("items", [{}])[0] if right_view.get("items") else {}
        same_top = left_top.get("label", "") == right_top.get("label", "") and left_top.get("candidate_type", "") == right_top.get("candidate_type", "")
        rank_changes = self._build_profile_rank_changes(left_items, right_items)
        action_recommendations = self._build_profile_diff_actions(rank_changes, left_profile, right_profile)
        return {
            "view": "profile-diff",
            "left_profile": left_profile,
            "right_profile": right_profile,
            "left_top_candidate": left_top,
            "right_top_candidate": right_top,
            "rank_changes": rank_changes,
            "action_recommendations": action_recommendations,
            "difference_summary": {
                "same_top_candidate": same_top,
                "left_focus_now": left_view.get("summary", {}).get("focus_now", ""),
                "right_focus_now": right_view.get("summary", {}).get("focus_now", ""),
                "left_profile_explanation": left_view.get("summary", {}).get("profile_explanation", ""),
                "right_profile_explanation": right_view.get("summary", {}).get("profile_explanation", ""),
                "changed_reason": self._build_profile_diff_reason(left_top, right_top, left_profile, right_profile),
                "top3_change_count": len([item for item in rank_changes if item.get("rank_changed")]),
                "action_change_count": len(action_recommendations.get("promote_earlier", [])) + len(action_recommendations.get("defer_or_watch", [])),
                "implementation_status": "Implemented",
            },
            "implementation_status": "Implemented",
        }

    def learning_chains(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return self.retriever.learning_chains(
            limit=int(payload.get("limit", 5)),
            min_count=int(payload.get("min_count", 2)),
        )

    def apply_learning_chains(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        chains = self.retriever.learning_chains(
            limit=int(payload.get("limit", 5)),
            min_count=int(payload.get("min_count", 2)),
        )
        updated_atoms: dict[str, dict[str, Any]] = {}
        created_relations: list[dict[str, Any]] = []
        updated_relations: list[dict[str, Any]] = []
        confirmed_relations: list[dict[str, Any]] = []
        atom_apply_audit: dict[str, dict[str, Any]] = {}
        applied_chains: list[dict[str, Any]] = []
        for chain in chains["lesson_chains"] + chains["improvement_chains"]:
            atom_ids = self._collect_chain_atom_ids(chain)
            if not atom_ids:
                continue
            for atom_id in atom_ids:
                atom = self.store.get("atoms", atom_id)
                if not atom:
                    continue
                atom.setdefault("metadata", {})
                recommended_tags = atom["metadata"].setdefault("recommended_tags", [])
                audit = atom_apply_audit.setdefault(
                    atom_id,
                    {
                        "atom_id": atom_id,
                        "new_recommended_tags": [],
                        "existing_recommended_tags": [],
                        "new_chain_refs": [],
                        "updated_chain_refs": [],
                        "unchanged_chain_refs": [],
                        "importance_delta": 0.0,
                        "created_relation_ids": [],
                        "updated_relation_ids": [],
                        "confirmed_relation_ids": [],
                    },
                )
                if chain["text"] not in recommended_tags:
                    recommended_tags.append(chain["text"])
                    audit["new_recommended_tags"].append(chain["text"])
                else:
                    audit["existing_recommended_tags"].append(chain["text"])
                refs = atom["metadata"].setdefault("learning_chain_refs", [])
                ref_payload, importance_delta, ref_state = self._merge_learning_chain_ref(
                    refs=refs,
                    chain_type=chain["chain_type"],
                    text=chain["text"],
                    entry_count=chain["entry_count"],
                )
                audit_key = {
                    "new": "new_chain_refs",
                    "updated": "updated_chain_refs",
                    "unchanged": "unchanged_chain_refs",
                }[ref_state]
                audit[audit_key].append(ref_payload["text"])
                audit["importance_delta"] += importance_delta
                atom["importance"] = clamp(float(atom.get("importance", 0.5)) + importance_delta)
                atom["updated_at"] = atom.get("updated_at", atom.get("created_at", ""))
                atom["related_ids"] = sorted(set(atom.get("related_ids", [])) | {item for item in atom_ids if item != atom_id})
                atom["metadata"]["last_learning_apply"] = {
                    "new_recommended_tags": sorted(set(audit["new_recommended_tags"])),
                    "existing_recommended_tags": sorted(set(audit["existing_recommended_tags"])),
                    "new_chain_refs": sorted(set(audit["new_chain_refs"])),
                    "updated_chain_refs": sorted(set(audit["updated_chain_refs"])),
                    "unchanged_chain_refs": sorted(set(audit["unchanged_chain_refs"])),
                    "importance_delta": round(audit["importance_delta"], 6),
                    "created_relation_ids": sorted(set(audit["created_relation_ids"])),
                    "updated_relation_ids": sorted(set(audit["updated_relation_ids"])),
                    "confirmed_relation_ids": sorted(set(audit["confirmed_relation_ids"])),
                }
                updated_atoms[atom_id] = self.store.update_data("atoms", atom_id, atom)

            if len(atom_ids) >= 2:
                for left_index, left_id in enumerate(atom_ids):
                    for right_id in atom_ids[left_index + 1:]:
                        relation_id = new_id("rel", f"learning-chain:{chain['chain_type']}:{chain['text']}:{left_id}:{right_id}")
                        existed = self.store.get("relations", relation_id) is not None
                        relation = RelationEdge(
                            id=relation_id,
                            source_atom_id=left_id,
                            target_atom_id=right_id,
                            relation_type="learning_chain_related",
                            confidence=min(0.85, 0.35 + 0.1 * chain["entry_count"]),
                            evidence_ids=chain.get("evidence_ids", []),
                            metadata={
                                "implementation_status": "Implemented",
                                "chain_type": chain["chain_type"],
                                "chain_text": chain["text"],
                                "entry_count": chain["entry_count"],
                            },
                        )
                        if not existed:
                            saved = self.store.save("relations", relation)
                            created_relations.append(saved)
                            atom_apply_audit[left_id]["created_relation_ids"].append(saved["id"])
                            atom_apply_audit[right_id]["created_relation_ids"].append(saved["id"])
                        else:
                            previous = self.store.get("relations", relation_id) or {}
                            current = to_dict(relation)
                            semantic_previous = self._normalize_relation_for_comparison(previous)
                            semantic_current = self._normalize_relation_for_comparison(current)
                            if semantic_previous == semantic_current:
                                confirmed_relations.append(previous)
                                atom_apply_audit[left_id]["confirmed_relation_ids"].append(previous["id"])
                                atom_apply_audit[right_id]["confirmed_relation_ids"].append(previous["id"])
                            else:
                                current["created_at"] = previous.get("created_at", current.get("created_at", ""))
                                saved = self.store.save("relations", current)
                                updated_relations.append(saved)
                                atom_apply_audit[left_id]["updated_relation_ids"].append(saved["id"])
                                atom_apply_audit[right_id]["updated_relation_ids"].append(saved["id"])
            applied_chains.append(
                {
                    "chain_type": chain["chain_type"],
                    "text": chain["text"],
                    "atom_ids": atom_ids,
                    "entry_count": chain["entry_count"],
                }
            )

        evo = self.evolution.record(
            trigger="learning_chain_apply",
            observation="Applied repeated learning patterns back into atom recommendations and weak relations.",
            change_type="memory_organization",
            affected_ids=sorted(set(list(updated_atoms.keys()) + [item["id"] for item in created_relations] + [item["id"] for item in updated_relations] + [item["id"] for item in confirmed_relations])),
            proposed_update="Use repeated lessons and improvement items to influence retrieval and memory organization.",
            applied=True,
            metrics={
                "updated_atom_count": len(updated_atoms),
                "created_relation_count": len(created_relations),
                "updated_relation_count": len(updated_relations),
                "confirmed_relation_count": len(confirmed_relations),
                "applied_chain_count": len(applied_chains),
            },
        )
        self.board.update(
            summary=f"应用 {len(applied_chains)} 条 learning chains 到 {len(updated_atoms)} 个 atom，新增 {len(created_relations)} 条弱关系，更新 {len(updated_relations)} 条既有弱关系，确认 {len(confirmed_relations)} 条未变化关系。",
            event_type="learning_chain_applied",
        )
        return {
            "applied_chains": applied_chains,
            "updated_atoms": list(updated_atoms.values()),
            "atom_apply_audit": list(atom_apply_audit.values()),
            "created_relations": created_relations,
            "updated_relations": updated_relations,
            "confirmed_relations": confirmed_relations,
            "evolution_log": to_dict(evo),
        }

    def create_decision(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.decisions.create_decision(
            decision_type=payload.get("decision_type", payload.get("type", "general")),
            question=payload.get("question", payload.get("decision", "")),
            context=payload.get("context", {}),
            options=payload.get("options", []),
            chosen=payload.get("chosen", ""),
            evidence_ids=payload.get("evidence_ids", []),
            counter_evidence_ids=payload.get("counter_evidence_ids", []),
            confidence=float(payload.get("confidence", 0.5)),
            rationale=payload.get("rationale", ""),
            action=payload.get("action", ""),
        )

    def create_forecast(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.decisions.create_forecast(
            question=payload.get("question", ""),
            horizon=payload.get("horizon", ""),
            probability=float(payload.get("probability", 0.5)),
            scenarios=payload.get("scenarios", []),
            evidence_ids=payload.get("evidence_ids", []),
            counter_evidence_ids=payload.get("counter_evidence_ids", []),
            confidence=float(payload.get("confidence", 0.5)),
            triggers=payload.get("triggers", []),
            invalidation_conditions=payload.get("invalidation_conditions", []),
            risk_exposure=payload.get("risk_exposure", ""),
            review_at=payload.get("review_at", ""),
        )

    def create_reasoning_trace(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.decisions.create_reasoning_trace(
            question=payload.get("question", ""),
            trace_type=payload.get("trace_type", "analysis"),
            steps=payload.get("steps", []),
            evidence_ids=payload.get("evidence_ids", []),
            counter_evidence_ids=payload.get("counter_evidence_ids", []),
            conclusion=payload.get("conclusion", ""),
            confidence=float(payload.get("confidence", 0.5)),
            uncertainty=payload.get("uncertainty", ""),
            next_action=payload.get("next_action", "wait"),
            metadata=payload.get("metadata", {}),
        )
        self.board.update(
            summary="新增一条 ReasoningTrace，并同步写入统一学习入口，支持只记录推理过程而不强制生成决策。",
            event_type="reasoning_trace_created",
        )
        return result

    def review(self, payload: dict[str, Any]) -> dict[str, Any]:
        actual_score = payload.get("actual_score")
        return self.decisions.review(
            target_type=payload.get("target_type", ""),
            target_id=payload.get("target_id", ""),
            actual_outcome=payload.get("actual_outcome", payload.get("outcome", "")),
            actual_score=None if actual_score is None else float(actual_score),
            notes=payload.get("notes", ""),
            lessons=payload.get("lessons", []),
        )

    def feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.decisions.submit_feedback(
            target_type=payload.get("target_type", "atom"),
            target_ids=payload.get("target_ids", []),
            feedback_text=payload.get("feedback_text", payload.get("notes", "")),
            tags_to_add=payload.get("tags_to_add", []),
            tags_to_remove=payload.get("tags_to_remove", []),
            confidence_delta=float(payload.get("confidence_delta", 0.0)),
            related_atom_ids=payload.get("related_atom_ids", []),
            support_ids=payload.get("support_ids", []),
            refute_ids=payload.get("refute_ids", []),
            improvement_items=payload.get("improvement_items", []),
            metadata=payload.get("metadata", {}),
        )
        self.board.update(
            summary=f"应用 {payload.get('target_type', 'atom')} 反馈到 {len(result['updated_targets'])} 个目标，并同步进入统一学习入口。",
            event_type="feedback_applied",
        )
        return result

    def learning_entry(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.decisions.create_learning_entry(
            entry_type=payload.get("entry_type", "manual_learning"),
            target_type=payload.get("target_type", "knowledge"),
            target_ids=payload.get("target_ids", []),
            summary=payload.get("summary", ""),
            source_record_id=payload.get("source_record_id", ""),
            evidence_ids=payload.get("evidence_ids", []),
            counter_evidence_ids=payload.get("counter_evidence_ids", []),
            lessons=payload.get("lessons", []),
            improvement_items=payload.get("improvement_items", []),
            confidence_delta=float(payload.get("confidence_delta", 0.0)),
            metadata=payload.get("metadata", {}),
        )
        self.board.update(
            summary=f"新增统一学习记录 {result['learning_entry']['id']}，面向 {payload.get('target_type', 'knowledge')} 目标沉淀可复用经验。",
            event_type="learning_entry_created",
        )
        return result

    def trading_replay(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.trading.run_replay(payload)
        replay_summary = self._trading_replay_summary(result)
        result["replay_summary"] = replay_summary
        result["selected_candidate_summary"] = dict(replay_summary.get("selected_candidate_summary", {}))
        a_share_context = result.get("a_share_context", {}) or {}
        a_share_proxy_snapshot = result.get("a_share_proxy_snapshot", {}) or {}
        true_money_flow_snapshot = result.get("true_money_flow_snapshot", {}) or {}
        strategy_comparison = result.get("strategy_comparison", {}) or {}
        selection_state_summary = dict(strategy_comparison.get("selection_state_summary", {}) or {})
        summary = "交易域 replay 已写入统一母系统协议，产出 backtest/validation/decision/forecast/journal/evolution 全链路记录。"
        if a_share_context:
            proxy_label = str(a_share_proxy_snapshot.get("bias_label", "proxy_only") or "proxy_only")
            summary = (
                "交易域 replay 已写入统一母系统协议，产出 backtest/validation/decision/forecast/journal/evolution 全链路记录；"
                f"当前为 A股T+1 研究代理链，未接入真DDX/DDY，Seasoned/Fresh 仅为 {proxy_label} 代理推断。"
            )
            if true_money_flow_snapshot:
                summary += (
                    f" 本轮附带 TDX 真资金样本 ddx={float(true_money_flow_snapshot.get('ddx', 0.0) or 0.0):.4f},"
                    f" ddy={float(true_money_flow_snapshot.get('ddy', 0.0) or 0.0):.4f}，"
                    "但仍是 payload injected Experimental 上下文，不等于 live connector 已完成。"
                )
        if selection_state_summary:
            state_bits: list[str] = []
            if selection_state_summary.get("primary_gate"):
                state_bits.append(f"主门：{selection_state_summary.get('primary_gate')}")
            if selection_state_summary.get("queue_recommendation"):
                state_bits.append(f"队列建议：{selection_state_summary.get('queue_recommendation')}")
            if selection_state_summary.get("freeze_candidate_status"):
                state_bits.append(f"冻结状态：{selection_state_summary.get('freeze_candidate_status')}")
            if state_bits:
                summary += " " + "，".join(state_bits) + "。"
        self.board.update(
            summary=summary,
            event_type="trading_domain_synced",
        )
        return result

    @staticmethod
    def _replay_summary_state_fallback(
        *,
        active_state_summary: dict[str, Any],
        governance_primary_reason: str,
        governance_action: str,
        out_of_sample_result: str,
        sample_consistency: str,
        validation_warnings: list[str],
    ) -> dict[str, str]:
        summary = {
            "queue_recommendation": str(active_state_summary.get("queue_recommendation", "") or ""),
            "primary_gate": str(active_state_summary.get("primary_gate", "") or ""),
            "upgrade_candidate_status": str(active_state_summary.get("upgrade_candidate_status", "") or ""),
            "freeze_candidate_status": str(active_state_summary.get("freeze_candidate_status", "") or ""),
        }
        if all(summary.values()):
            return summary

        primary_gate = summary["primary_gate"]
        if not primary_gate:
            if out_of_sample_result != "pass":
                primary_gate = "out_of_sample"
            elif sample_consistency not in {"aligned", "oos_stronger_than_train"}:
                primary_gate = "consistency_gap"
            elif "a_share_proxy_guard_blocks_promotion" in validation_warnings:
                primary_gate = "a_share_proxy_guard"
            elif governance_primary_reason.startswith("research_queue_"):
                primary_gate = "governance_reason"
            else:
                primary_gate = "none"

        upgrade_status = summary["upgrade_candidate_status"]
        if not upgrade_status:
            if primary_gate == "none":
                upgrade_status = "ready_for_manual_promotion_review"
            elif primary_gate == "out_of_sample":
                upgrade_status = "blocked_by_out_of_sample"
            elif primary_gate == "consistency_gap":
                upgrade_status = "blocked_by_consistency"
            elif primary_gate == "a_share_proxy_guard":
                upgrade_status = "blocked_by_a_share_proxy_guard"
            else:
                upgrade_status = "blocked_by_governance_reason"

        freeze_status = summary["freeze_candidate_status"]
        if not freeze_status:
            if governance_action in {"retire_candidate", "freeze"} or out_of_sample_result == "fail":
                freeze_status = "freeze_candidate"
            elif sample_consistency in {"diverged", "train_stronger_than_test"}:
                freeze_status = "watch_consistency_gap"
            else:
                freeze_status = "observe"

        queue_recommendation = summary["queue_recommendation"]
        if not queue_recommendation:
            if governance_action == "retire_candidate":
                queue_recommendation = "retire_candidate_review"
            elif upgrade_status == "ready_for_manual_promotion_review":
                queue_recommendation = "ready_for_manual_promotion_review"
            elif freeze_status == "freeze_candidate":
                queue_recommendation = "freeze_candidate_watch"
            elif freeze_status == "watch_consistency_gap":
                queue_recommendation = "stay_experimental_watch_gap"
            else:
                queue_recommendation = "stay_experimental"

        return {
            "queue_recommendation": queue_recommendation,
            "primary_gate": primary_gate,
            "upgrade_candidate_status": upgrade_status,
            "freeze_candidate_status": freeze_status,
        }

    @staticmethod
    def _oos_surface_fields(
        *,
        metadata: dict[str, Any] | None = None,
        backtest: dict[str, Any] | None = None,
        fallback: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = dict(metadata or {})
        fallback = dict(fallback or {})
        backtest = dict(backtest or {})
        backtest_metadata = dict(backtest.get("metadata", {}) or {})
        sample_size_thresholds = dict(metadata.get("sample_size_thresholds", {}) or {})
        split_summary = dict(
            metadata.get("train_test_split", {}) or backtest_metadata.get("train_test_split", {}) or {}
        )
        return {
            "out_of_sample_result_reason": str(
                fallback.get("out_of_sample_result_reason", "")
                or split_summary.get("out_of_sample_result_reason", "")
                or sample_size_thresholds.get("out_of_sample_result_reason", "")
                or ""
            ),
            "out_of_sample_coverage_status": str(
                fallback.get("out_of_sample_coverage_status", "")
                or split_summary.get("out_of_sample_coverage_status", "")
                or sample_size_thresholds.get("out_of_sample_coverage_status", "")
                or ""
            ),
            "oos_trade_pairs_count": int(
                fallback.get(
                    "oos_trade_pairs_count",
                    split_summary.get(
                        "oos_trade_pairs_count",
                        sample_size_thresholds.get("oos_trade_pairs_count", 0),
                    ),
                )
                or 0
            ),
            "min_promotable_oos_trade_pairs": int(
                fallback.get(
                    "min_promotable_oos_trade_pairs",
                    split_summary.get(
                        "min_promotable_oos_trade_pairs",
                        sample_size_thresholds.get("min_oos_completed_trade_pairs", 0),
                    ),
                )
                or 0
            ),
            "promotion_ready": bool(
                fallback.get(
                    "promotion_ready",
                    split_summary.get(
                        "promotion_ready",
                        sample_size_thresholds.get("promotion_ready", False),
                    ),
                )
            ),
        }

    @staticmethod
    def _trading_replay_summary(result: dict[str, Any]) -> dict[str, Any]:
        strategy_comparison = result.get("strategy_comparison", {}) or {}
        selected_strategy = result.get("selected_strategy_definition")
        selected_validation = result.get("selected_validation_report")
        selected_backtest = result.get("selected_backtest_result") or {}
        fallback_validation = result.get("validation_report", {}) or {}
        active_validation = selected_validation or fallback_validation or {}
        market_data = result.get("market_data_record", {}) or {}
        a_share_context = result.get("a_share_context", {}) or {}
        candidate_strategies = result.get("candidate_strategies", []) or []
        candidate_names = [str(item.get("name", "") or "") for item in candidate_strategies if str(item.get("name", "") or "")]
        candidate_validation_index = {
            str(item.get("target_id", "") or item.get("strategy_id", "") or ""): item
            for item in (result.get("candidate_validations", []) or [])
            if str(item.get("target_id", "") or item.get("strategy_id", "") or "")
        }
        candidate_backtest_index = {
            str(item.get("strategy_id", "") or ""): item
            for item in (result.get("candidate_backtests", []) or [])
            if str(item.get("strategy_id", "") or "")
        }
        sample_comparison = dict((active_validation.get("metadata", {}) or {}).get("sample_comparison", {}) or {})
        candidate_summaries = []
        for item in strategy_comparison.get("candidates", []) or []:
            strategy_id = str(item.get("strategy_id", "") or "")
            validation = candidate_validation_index.get(strategy_id, {})
            backtest = candidate_backtest_index.get(strategy_id, {})
            validation_metadata = (validation.get("metadata", {}) or {}) if isinstance(validation, dict) else {}
            candidate_sample_comparison = dict(validation_metadata.get("sample_comparison", {}) or {})
            candidate_redline_check = dict(validation_metadata.get("a_share_redline_check", {}) or {})
            candidate_state_summary = dict(validation_metadata.get("state_summary", {}) or {})
            candidate_governance_explanation = dict(validation_metadata.get("governance_explanation", {}) or {})
            candidate_governance_rule_snapshot = dict(validation_metadata.get("governance_rule_snapshot", {}) or {})
            candidate_oos_surface = SuperBrainV01._oos_surface_fields(
                metadata=validation_metadata,
                backtest=backtest,
                fallback=item,
            )
            candidate_state_summary = SuperBrainV01._replay_summary_state_fallback(
                active_state_summary=candidate_state_summary,
                governance_primary_reason=str(candidate_governance_explanation.get("primary_reason", "") or ""),
                governance_action=str(item.get("governance_action", "") or ""),
                out_of_sample_result=str(item.get("out_of_sample_result", "not_run") or "not_run"),
                sample_consistency=str(candidate_sample_comparison.get("consistency", "not_run") or "not_run"),
                validation_warnings=list((validation.get("warnings", []) or []) if isinstance(validation, dict) else []),
            )
            candidate_summaries.append(
                {
                    "strategy_name": str(item.get("strategy_name", "") or ""),
                    "strategy_id": strategy_id,
                    "family": str(item.get("family", "") or ""),
                    "portfolio_action": "trade" if str(strategy_comparison.get("selected_strategy_id", "") or "") == strategy_id else "no_trade",
                    "selection_status": "selected" if str(strategy_comparison.get("selected_strategy_id", "") or "") == strategy_id else "candidate",
                    "governance_action": str(item.get("governance_action", "") or ""),
                    "validation_verdict": str(item.get("verdict", "") or ""),
                    "out_of_sample_result": str(item.get("out_of_sample_result", "not_run") or "not_run"),
                    "out_of_sample_result_reason": str(
                        candidate_oos_surface.get("out_of_sample_result_reason", "") or ""
                    ),
                    "out_of_sample_coverage_status": str(
                        candidate_oos_surface.get("out_of_sample_coverage_status", "") or ""
                    ),
                    "oos_trade_pairs_count": int(candidate_oos_surface.get("oos_trade_pairs_count", 0) or 0),
                    "min_promotable_oos_trade_pairs": int(
                        candidate_oos_surface.get("min_promotable_oos_trade_pairs", 0) or 0
                    ),
                    "promotion_ready": bool(candidate_oos_surface.get("promotion_ready", False)),
                    "sample_consistency": str(candidate_sample_comparison.get("consistency", "not_run") or "not_run"),
                    "sample_comparison_summary": str(candidate_sample_comparison.get("summary", "") or ""),
                    "train_total_return": float(candidate_sample_comparison.get("train_total_return", 0.0) or 0.0),
                    "test_total_return": float(candidate_sample_comparison.get("test_total_return", 0.0) or 0.0),
                    "total_return": float(item.get("total_return", 0.0) or 0.0),
                    "max_drawdown": float(item.get("max_drawdown", 0.0) or 0.0),
                    "risk_adjusted_score": float(item.get("risk_adjusted_score", 0.0) or 0.0),
                    "governance_primary_reason": str(candidate_governance_explanation.get("primary_reason", "") or ""),
                    "governance_rule_summary": str(candidate_governance_rule_snapshot.get("summary", "") or ""),
                    "queue_recommendation": str(candidate_state_summary.get("queue_recommendation", "") or ""),
                    "primary_gate": str(candidate_state_summary.get("primary_gate", "") or ""),
                    "upgrade_candidate_status": str(candidate_state_summary.get("upgrade_candidate_status", "") or ""),
                    "freeze_candidate_status": str(candidate_state_summary.get("freeze_candidate_status", "") or ""),
                    "a_share_redline_summary": str(candidate_redline_check.get("summary", "") or ""),
                    "a_share_redline_blocks_action": bool(candidate_redline_check.get("blocks_action", False)),
                    "a_share_redline_warning_count": len(list(candidate_redline_check.get("warnings", []) or [])),
                }
            )
        active_metadata = (active_validation.get("metadata", {}) or {}) if isinstance(active_validation, dict) else {}
        active_redline_check = dict(active_metadata.get("a_share_redline_check", {}) or {})
        active_state_summary = dict(active_metadata.get("state_summary", {}) or strategy_comparison.get("selection_state_summary", {}) or {})
        active_governance_explanation = dict(active_metadata.get("governance_explanation", {}) or {})
        active_governance_rule_snapshot = dict(active_metadata.get("governance_rule_snapshot", {}) or {})
        active_oos_surface = SuperBrainV01._oos_surface_fields(
            metadata=active_metadata,
            backtest=selected_backtest,
            fallback=active_validation,
        )
        active_state_summary = SuperBrainV01._replay_summary_state_fallback(
            active_state_summary=active_state_summary,
            governance_primary_reason=str(active_governance_explanation.get("primary_reason", "") or ""),
            governance_action=str(strategy_comparison.get("selection_governance_action", "") or ""),
            out_of_sample_result=str(active_validation.get("out_of_sample_result", "not_run") or "not_run"),
            sample_consistency=str(sample_comparison.get("consistency", "not_run") or "not_run"),
            validation_warnings=list(active_validation.get("warnings", []) or []),
        )
        selected_candidate_summary = {
            "selection_status": str(strategy_comparison.get("selection_status", "") or ""),
            "selected_strategy_name": str(strategy_comparison.get("selected_strategy_name", "") or ""),
            "selected_candidate_name": str(strategy_comparison.get("selected_candidate_name", "") or ""),
            "selected_strategy_family": str(strategy_comparison.get("selected_strategy_family", "") or ""),
            "selected_strategy_id": str(strategy_comparison.get("selected_strategy_id", "") or ""),
            "portfolio_action": str(strategy_comparison.get("portfolio_action", "") or ""),
            "selection_governance_action": str(strategy_comparison.get("selection_governance_action", "") or ""),
            "validation_verdict": str(active_validation.get("verdict", "") or ""),
            "out_of_sample_result": str(active_validation.get("out_of_sample_result", "not_run") or "not_run"),
            "out_of_sample_result_reason": str(active_oos_surface.get("out_of_sample_result_reason", "") or ""),
            "out_of_sample_coverage_status": str(active_oos_surface.get("out_of_sample_coverage_status", "") or ""),
            "oos_trade_pairs_count": int(active_oos_surface.get("oos_trade_pairs_count", 0) or 0),
            "min_promotable_oos_trade_pairs": int(
                active_oos_surface.get("min_promotable_oos_trade_pairs", 0) or 0
            ),
            "promotion_ready": bool(active_oos_surface.get("promotion_ready", False)),
            "selected_strategy_definition_attached": bool(selected_strategy),
            "train_total_return": float(sample_comparison.get("train_total_return", 0.0) or 0.0),
            "test_total_return": float(sample_comparison.get("test_total_return", 0.0) or 0.0),
            "sample_consistency": str(sample_comparison.get("consistency", "not_run") or "not_run"),
            "sample_comparison_summary": str(sample_comparison.get("summary", "") or ""),
            "selected_backtest_trades_count": int((selected_backtest or {}).get("trades_count", 0) or 0),
            "governance_primary_reason": str(active_governance_explanation.get("primary_reason", "") or ""),
            "governance_rule_summary": str(active_governance_rule_snapshot.get("summary", "") or ""),
            "queue_recommendation": str(active_state_summary.get("queue_recommendation", "") or ""),
            "primary_gate": str(active_state_summary.get("primary_gate", "") or ""),
            "upgrade_candidate_status": str(active_state_summary.get("upgrade_candidate_status", "") or ""),
            "freeze_candidate_status": str(active_state_summary.get("freeze_candidate_status", "") or ""),
            "a_share_redline_summary": str(active_redline_check.get("summary", "") or ""),
            "a_share_redline_blocks_action": bool(active_redline_check.get("blocks_action", False)),
            "a_share_redline_warning_count": len(list(active_redline_check.get("warnings", []) or [])),
        }
        return {
            "symbol": str(market_data.get("symbol", "") or ""),
            "market": str(a_share_context.get("market", "") or ""),
            "timeframe": str(market_data.get("timeframe", "") or ""),
            "record_path": str(market_data.get("record_path", "") or ""),
            "top_level_strategy_name": str((result.get("strategy_definition", {}) or {}).get("name", "") or ""),
            "candidate_names": candidate_names,
            "candidate_count": len(candidate_names),
            "selection_reason": str(strategy_comparison.get("selection_reason", "") or ""),
            "selected_candidate_summary": selected_candidate_summary,
            "candidate_summaries": candidate_summaries,
            "sample_comparison": sample_comparison,
            "validation_warnings": list(active_validation.get("warnings", []) or []),
            "implementation_status": "Implemented",
        }

    def trading_research_queue_approval_summary(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.research_queue_manual_promotion_summary(payload)

    def trading_replay_history_summary(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.replay_history_summary(payload)

    def trading_strategy_governance_summary(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.strategy_governance_summary(payload)

    def trading_research_queue_evidence_gap_summary(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.research_queue_evidence_gap_summary(payload)

    def trading_research_queue_consistency_diagnostics_summary(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.research_queue_consistency_diagnostics_summary(payload)

    def trading_research_queue_readiness_summary(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.research_queue_readiness_summary(payload)

    def trading_research_queue_approval_signals(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.research_queue_manual_promotion_signals(payload)

    def trading_research_queue_watchlist(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.research_queue_manual_promotion_watchlist(payload)

    def trading_research_queue_review_agenda(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.research_queue_manual_promotion_review_agenda(payload)

    def trading_research_queue_next_validation_slice(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.research_queue_next_validation_slice(payload)

    def trading_research_queue_run_next_validation_slice(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        result = self.trading.research_queue_run_next_validation_slice(payload)
        candidate_slug = str(result.get("replay_payload_used", {}).get("candidate_slug", "") or "")
        self.board.update(
            summary=f"执行交易 ResearchQueue 候选 {candidate_slug or 'unknown'} 的下一轮验证切片 replay，并将结果写回统一母系统协议。",
            event_type="trading_research_queue_next_validation_slice_executed",
        )
        if candidate_slug:
            sync_payload = {
                "candidate_slug": candidate_slug,
                "min_approvals": int(payload.get("min_approvals", 1) or 1),
                "top_limit": int(payload.get("top_limit", 3) or 3),
            }
            result["bulletin_sync"] = self.trading.research_queue_sync_bulletin_from_latest_validation(
                sync_payload
            )
        return result

    def trading_research_queue_latest_validation_summary(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.research_queue_latest_validation_summary(payload)

    def trading_research_queue_sync_bulletin_from_latest_validation(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.research_queue_sync_bulletin_from_latest_validation(payload)

    def trading_confirm_research_queue_manual_approval(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return self.trading.confirm_research_queue_manual_promotion(payload)

    def evolution_log(self, limit: int = 20) -> dict[str, Any]:
        return {"logs": self.evolution.recent(limit)}

    def board_status(self) -> dict[str, Any]:
        board = self.board.status()
        trading_status = self._latest_trading_status_snapshot()
        latest_workbuddy_authority_catalog = self._latest_workbuddy_authority_catalog_snapshot()
        latest_workbuddy_probability_fusion_mock = self._latest_workbuddy_probability_fusion_mock_snapshot()
        trading_governance_summary = self.trading.strategy_governance_summary({"limit": 10})
        latest_replay_bulletin_state = self._latest_trading_replay_bulletin_state_snapshot()
        latest_research_queue_bulletin_state = self._latest_trading_research_queue_bulletin_state_snapshot()
        latest_bulletin_state = latest_research_queue_bulletin_state or latest_replay_bulletin_state
        latest_validation_round = dict(
            (latest_bulletin_state or {}).get("validation_round", {}) or {}
        )
        latest_validation_round_summary = ""
        latest_validation_round_focus: dict[str, Any] = {}
        latest_validation_round_focus_summary = ""
        if latest_validation_round:
            round_key = str(latest_validation_round.get("validation_round_key", "") or "")
            round_index = int(latest_validation_round.get("validation_round_index", 0) or 0)
            round_reused = bool(latest_validation_round.get("validation_round_reused", False))
            candidate_slug = str((latest_bulletin_state or {}).get("candidate_slug", "") or "")
            primary_gate = str((latest_bulletin_state or {}).get("primary_gate", "") or "")
            primary_blocker = str((latest_bulletin_state or {}).get("primary_blocker", "") or "")
            queue_recommendation = str((latest_bulletin_state or {}).get("queue_recommendation", "") or "")
            out_of_sample_result = str((latest_bulletin_state or {}).get("out_of_sample_result", "") or "")
            focus_status = queue_recommendation or "unknown"
            focus_risk_level = "medium"
            focus_action_hint = "continue_research"
            focus_machine_state = "research_watch"
            next_validation_execution = dict(
                (latest_bulletin_state or {}).get("next_validation_execution", {}) or {}
            )
            next_validation_variant_key = str(
                (latest_bulletin_state or {}).get("next_validation_variant_key", "") or ""
            )
            next_validation_variant_label = str(
                (latest_bulletin_state or {}).get("next_validation_variant_label", "") or ""
            )
            next_validation_command_hint = str(
                (latest_bulletin_state or {}).get("next_validation_command_hint", "") or ""
            )
            execution_plan_status = str(
                (latest_bulletin_state or {}).get("execution_plan_status", "") or ""
            )
            latest_bulletin_metadata = dict((latest_bulletin_state or {}).get("metadata", {}) or {})
            consistency_snapshot_summary = str(
                (latest_bulletin_state or {}).get("consistency_snapshot_summary", "") or ""
            ) or self._consistency_snapshot_summary_from_metadata(latest_bulletin_metadata)
            round_oos_surface = self._oos_surface_fields(
                metadata=latest_bulletin_metadata,
                fallback={
                    "out_of_sample_result_reason": (latest_bulletin_state or {}).get(
                        "out_of_sample_result_reason",
                        "",
                    ),
                    "out_of_sample_coverage_status": (latest_bulletin_state or {}).get(
                        "out_of_sample_coverage_status",
                        "",
                    ),
                    "oos_trade_pairs_count": (latest_bulletin_state or {}).get(
                        "oos_trade_pairs_count",
                        0,
                    ),
                    "min_promotable_oos_trade_pairs": (latest_bulletin_state or {}).get(
                        "min_promotable_oos_trade_pairs",
                        0,
                    ),
                    "promotion_ready": (latest_bulletin_state or {}).get("promotion_ready", False),
                },
            )
            if queue_recommendation in {"freeze_candidate_watch", "retire_candidate_review"} or primary_gate in {"scaffold", "out_of_sample"}:
                focus_risk_level = "high"
            elif queue_recommendation in {"ready_for_manual_promotion_review"} and out_of_sample_result == "pass":
                focus_risk_level = "low"
            if queue_recommendation == "freeze_candidate_watch":
                focus_action_hint = "freeze_watch"
            elif queue_recommendation == "retire_candidate_review":
                focus_action_hint = "retire_review"
            elif queue_recommendation == "ready_for_manual_promotion_review":
                focus_action_hint = "ready_for_review"
            elif queue_recommendation in {"stay_experimental_watch_gap", "stay_experimental"}:
                focus_action_hint = "continue_research"
            if focus_action_hint == "retire_review":
                focus_machine_state = "retire_watch"
            elif focus_action_hint == "ready_for_review":
                focus_machine_state = "review_ready"
            elif focus_action_hint == "freeze_watch":
                focus_machine_state = "research_blocked"
            latest_validation_round_summary = (
                f"candidate={candidate_slug or 'unknown'}"
                f", round={round_key or 'not_set'}"
                f", index={round_index}"
                f", reused={round_reused}"
                f", primary_gate={primary_gate or 'unknown'}"
            )
            latest_validation_round_focus = {
                "candidate_slug": candidate_slug,
                "validation_round_key": round_key,
                "validation_round_index": round_index,
                "validation_round_reused": round_reused,
                "primary_gate": primary_gate,
                "primary_blocker": primary_blocker,
                "queue_recommendation": queue_recommendation,
                "out_of_sample_result": out_of_sample_result,
                "out_of_sample_result_reason": str(
                    round_oos_surface.get("out_of_sample_result_reason", "") or ""
                ),
                "out_of_sample_coverage_status": str(
                    round_oos_surface.get("out_of_sample_coverage_status", "") or ""
                ),
                "oos_trade_pairs_count": int(round_oos_surface.get("oos_trade_pairs_count", 0) or 0),
                "min_promotable_oos_trade_pairs": int(
                    round_oos_surface.get("min_promotable_oos_trade_pairs", 0) or 0
                ),
                "oos_promotion_ready": bool(round_oos_surface.get("promotion_ready", False)),
                "focus_status": focus_status,
                "focus_risk_level": focus_risk_level,
                "focus_action_hint": focus_action_hint,
                "focus_machine_state": focus_machine_state,
                "consistency_snapshot_summary": consistency_snapshot_summary,
                "execution_plan_status": execution_plan_status,
                "next_validation_variant_key": next_validation_variant_key,
                "next_validation_variant_label": next_validation_variant_label,
                "next_validation_command_hint": next_validation_command_hint,
                "next_validation_execution": next_validation_execution,
                "implementation_status": "Implemented",
            }
            latest_validation_round_focus_summary = (
                f"candidate={candidate_slug or 'unknown'}"
                f", blocker={primary_blocker or 'unknown'}"
                f", recommendation={queue_recommendation or 'unknown'}"
                f", oos={out_of_sample_result or 'unknown'}"
                f", oos_reason={str(round_oos_surface.get('out_of_sample_result_reason', '') or 'unknown')}"
                f", oos_coverage={str(round_oos_surface.get('out_of_sample_coverage_status', '') or 'unknown')}"
                f", oos_pairs={int(round_oos_surface.get('oos_trade_pairs_count', 0) or 0)}/"
                f"{int(round_oos_surface.get('min_promotable_oos_trade_pairs', 0) or 0)}"
                f", oos_promotion_ready={bool(round_oos_surface.get('promotion_ready', False))}"
                f", primary_gate={primary_gate or 'unknown'}"
                f", status={focus_status}"
                f", risk={focus_risk_level}"
                f", action={focus_action_hint}"
                f", machine_state={focus_machine_state}"
                f", consistency={consistency_snapshot_summary or 'not_available'}"
                f", next_variant={next_validation_variant_label or 'not_set'}"
                f"({next_validation_variant_key or 'unknown'})"
                f", plan={execution_plan_status or 'unknown'}"
            )
        if trading_status:
            board["trading_status"] = trading_status
        if latest_workbuddy_authority_catalog:
            board["latest_workbuddy_authority_catalog"] = latest_workbuddy_authority_catalog
            board["latest_workbuddy_authority_catalog_summary"] = str(
                latest_workbuddy_authority_catalog.get("summary_text", "") or ""
            )
        if latest_workbuddy_probability_fusion_mock:
            board["latest_workbuddy_probability_fusion_mock"] = latest_workbuddy_probability_fusion_mock
            board["latest_workbuddy_probability_fusion_mock_summary"] = str(
                latest_workbuddy_probability_fusion_mock.get("summary", "") or ""
            )
        if trading_governance_summary:
            board["trading_strategy_governance_summary"] = trading_governance_summary
        if latest_replay_bulletin_state:
            board["latest_trading_replay_bulletin_state"] = latest_replay_bulletin_state
        if latest_research_queue_bulletin_state:
            board["latest_trading_research_queue_bulletin_state"] = latest_research_queue_bulletin_state
        if latest_bulletin_state:
            board["latest_trading_bulletin_state"] = latest_bulletin_state
        if latest_validation_round:
            board["latest_trading_validation_round"] = latest_validation_round
            board["latest_trading_validation_round_summary"] = latest_validation_round_summary
            board["latest_trading_validation_round_focus"] = latest_validation_round_focus
            board["latest_trading_validation_round_focus_summary"] = latest_validation_round_focus_summary
        return board

    def board_update(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.board.update(
            completed=payload.get("completed"),
            in_progress=payload.get("in_progress"),
            next_step=payload.get("next_step"),
            status=payload.get("status"),
            event_type=payload.get("event_type", "progress_update"),
            summary=payload.get("summary", ""),
        )

    def trading_reconcile_a_share_authority(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.reconcile_a_share_authority_source(payload or {})

    def trading_workbuddy_skill_mapping_audit(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_workbuddy_skill_mapping_audit(payload or {})

    def trading_workbuddy_current_skill_catalog(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_workbuddy_current_skill_catalog(payload or {})

    def trading_workbuddy_probability_fusion_interface(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_workbuddy_probability_fusion_interface(payload or {})

    def trading_workbuddy_triple_decision_trees_interface(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.trading.report_workbuddy_triple_decision_trees_interface(payload or {})

    def trading_workbuddy_triple_decision_trees_scaffold(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.trading.report_workbuddy_triple_decision_trees_scaffold(payload or {})

    def trading_workbuddy_probability_fusion_mock(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_workbuddy_probability_fusion_mock(payload or {})

    def trading_a_share_authority_constraints_snapshot(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_a_share_authority_constraints_snapshot(payload or {})

    def trading_a_share_tdx_quote_snapshot(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_a_share_tdx_quote_snapshot(payload or {})

    def trading_a_share_tencent_qt_realtime_snapshot(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_a_share_tencent_qt_realtime_snapshot(payload or {})

    def trading_a_share_workbuddy_context_snapshot(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_a_share_workbuddy_context_snapshot(payload or {})

    def trading_a_share_westock_fund_flow_history_snapshot(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.trading.report_a_share_westock_fund_flow_history_snapshot(payload or {})

    def trading_a_share_tushare_moneyflow_history_fallback_snapshot(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.trading.report_a_share_tushare_moneyflow_history_fallback_snapshot(payload or {})

    def trading_a_share_realtime_crosscheck_summary(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_a_share_realtime_crosscheck_summary(payload or {})

    def trading_a_share_realtime_crosscheck_research_bridge(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.trading.report_a_share_realtime_crosscheck_research_bridge(payload or {})

    def trading_a_share_tdx_minute_kline_snapshot(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.trading.report_a_share_tdx_minute_kline_snapshot(payload or {})

    def trading_a_share_proxy_guard_source_coverage(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.trading.report_a_share_proxy_guard_source_coverage(payload or {})

    def trading_a_share_true_money_flow_readiness(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_a_share_true_money_flow_readiness(payload or {})

    def trading_a_share_real_data_source_registry(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_a_share_real_data_source_registry(payload or {})

    def trading_a_share_real_data_pull_plan(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_a_share_real_data_pull_plan(payload or {})

    def trading_a_share_connector_runtime_audit(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.trading.report_a_share_connector_runtime_audit(payload or {})

    def foundation_data_governance_report(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.foundation_data_governance.report(payload or {})

    def _latest_trading_status_snapshot(self) -> dict[str, Any]:
        rows = self.store.list_records("module_status_records", limit=50, newest=True)
        trading_row = next(
            (
                row for row in rows
                if str(row.get("module_name", "") or "") == "trading_domain_v0_1"
                and str(row.get("domain", "") or "") == "trading"
            ),
            None,
        )
        if not trading_row:
            return {}
        metadata = trading_row.get("metadata", {}) or {}
        selection_state_summary = dict(metadata.get("selection_state_summary", {}) or {})
        strategy_comparison = metadata.get("strategy_comparison", {}) or {}
        authority_catalog = self._latest_workbuddy_authority_catalog_snapshot()
        latest_probability_fusion_mock = self._latest_workbuddy_probability_fusion_mock_snapshot()
        execution_plan_snapshot = self._execution_plan_snapshot_from_metadata(metadata)
        base_oos_surface = self._oos_surface_fields(
            metadata=metadata,
            fallback={
                "out_of_sample_result_reason": metadata.get("latest_out_of_sample_reason", ""),
                "out_of_sample_coverage_status": metadata.get("latest_out_of_sample_coverage_status", ""),
                "oos_trade_pairs_count": metadata.get("latest_oos_trade_pairs_count", 0),
                "min_promotable_oos_trade_pairs": metadata.get("latest_min_promotable_oos_trade_pairs", 0),
                "promotion_ready": metadata.get("latest_oos_promotion_ready", False),
            },
        )
        base_snapshot = {
            "module_name": str(trading_row.get("module_name", "") or ""),
            "status": str(trading_row.get("status", "") or ""),
            "validation_status": str(trading_row.get("validation_status", "") or ""),
            "out_of_sample_result": str(trading_row.get("out_of_sample_result", "not_run") or "not_run"),
            "out_of_sample_result_reason": str(base_oos_surface.get("out_of_sample_result_reason", "") or ""),
            "out_of_sample_coverage_status": str(base_oos_surface.get("out_of_sample_coverage_status", "") or ""),
            "oos_trade_pairs_count": int(base_oos_surface.get("oos_trade_pairs_count", 0) or 0),
            "min_promotable_oos_trade_pairs": int(
                base_oos_surface.get("min_promotable_oos_trade_pairs", 0) or 0
            ),
            "oos_promotion_ready": bool(base_oos_surface.get("promotion_ready", False)),
            "failure_count": int(trading_row.get("failure_count", 0) or 0),
            "selection_status": str(metadata.get("selection_status", "") or ""),
            "selection_governance_action": str(metadata.get("governance_action", "") or ""),
            "selected_strategy_name": str(metadata.get("selected_strategy_name", "") or ""),
            "portfolio_action": str(metadata.get("portfolio_action", "") or ""),
            "selection_state_summary": selection_state_summary,
            "selection_state_summary_text": str(selection_state_summary.get("summary", "") or ""),
            "primary_gate": str(selection_state_summary.get("primary_gate", "") or ""),
            "queue_recommendation": str(selection_state_summary.get("queue_recommendation", "") or ""),
            "upgrade_candidate_status": str(selection_state_summary.get("upgrade_candidate_status", "") or ""),
            "freeze_candidate_status": str(selection_state_summary.get("freeze_candidate_status", "") or ""),
            "consistency_snapshot_summary": self._consistency_snapshot_summary_from_metadata(metadata),
            "execution_plan_status": str(execution_plan_snapshot.get("plan_status", "") or ""),
            "execution_plan_summary": str(execution_plan_snapshot.get("summary", "") or ""),
            "next_validation_variant_key": str(execution_plan_snapshot.get("default_variant_key", "") or ""),
            "next_validation_variant_label": str(execution_plan_snapshot.get("default_variant_label", "") or ""),
            "next_validation_variant_reason": str(execution_plan_snapshot.get("default_variant_reason", "") or ""),
            "next_validation_variant_changes": dict(execution_plan_snapshot.get("default_variant_changes", {}) or {}),
            "next_validation_command_hint": str(execution_plan_snapshot.get("command_hint", "") or ""),
            "next_validation_execution": execution_plan_snapshot,
            "candidate_count": len(strategy_comparison.get("candidates", []) or []),
            "implementation_status": "Implemented",
        }
        if authority_catalog:
            base_snapshot.update({
                "authority_mode": str(authority_catalog.get("authority_mode", "") or ""),
                "authority_catalog_status": str(authority_catalog.get("validation_status", "") or ""),
                "authority_catalog_summary": dict(authority_catalog.get("catalog_summary", {}) or {}),
                "authority_catalog_summary_text": str(authority_catalog.get("summary_text", "") or ""),
                "authority_catalog_alias_gap_count": int(authority_catalog.get("alias_gap_count", 0) or 0),
                "authority_catalog_focus_source": "latest_workbuddy_authority_catalog",
            })
        if latest_probability_fusion_mock:
            base_snapshot.update({
                "probability_fusion_runtime_status": str(
                    latest_probability_fusion_mock.get("runtime_status", "") or ""
                ),
                "probability_fusion_contract_status": str(
                    latest_probability_fusion_mock.get("contract_status", "") or ""
                ),
                "probability_fusion_dominant_direction": str(
                    latest_probability_fusion_mock.get("dominant_direction", "") or ""
                ),
                "probability_fusion_signal_label": str(
                    latest_probability_fusion_mock.get("signal_label", "") or ""
                ),
                "probability_fusion_execution_gate": str(
                    latest_probability_fusion_mock.get("execution_gate", "") or ""
                ),
                "probability_fusion_context_signal_attached": bool(
                    latest_probability_fusion_mock.get("context_signal_attached", False)
                ),
                "probability_fusion_context_signal_direction": str(
                    latest_probability_fusion_mock.get("context_signal_direction", "") or ""
                ),
                "probability_fusion_governance_blocker_summary": str(
                    latest_probability_fusion_mock.get("governance_blocker_summary", "") or ""
                ),
                "probability_fusion_focus_source": "latest_workbuddy_probability_fusion_mock",
            })
        research_queue_snapshot = self._latest_trading_research_queue_bulletin_state_snapshot()
        if not research_queue_snapshot:
            return base_snapshot
        if str(research_queue_snapshot.get("queue_type", "") or "") != "ResearchQueue":
            return base_snapshot
        merged_selection_summary = dict(research_queue_snapshot.get("selection_state_summary", {}) or {})
        research_queue_metadata = dict(research_queue_snapshot.get("metadata", {}) or {})
        rq_oos_surface = self._oos_surface_fields(
            metadata=research_queue_metadata,
            fallback={
                "out_of_sample_result_reason": (
                    research_queue_snapshot.get("out_of_sample_result_reason", "")
                    or research_queue_metadata.get("latest_out_of_sample_reason", "")
                ),
                "out_of_sample_coverage_status": (
                    research_queue_snapshot.get("out_of_sample_coverage_status", "")
                    or research_queue_metadata.get("latest_out_of_sample_coverage_status", "")
                ),
                "oos_trade_pairs_count": research_queue_snapshot.get(
                    "oos_trade_pairs_count",
                    research_queue_metadata.get("latest_oos_trade_pairs_count", 0),
                ),
                "min_promotable_oos_trade_pairs": research_queue_snapshot.get(
                    "min_promotable_oos_trade_pairs",
                    research_queue_metadata.get(
                        "latest_min_promotable_oos_trade_pairs",
                        research_queue_snapshot.get("min_oos_completed_trade_pairs", 0),
                    ),
                ),
                "promotion_ready": research_queue_snapshot.get(
                    "promotion_ready",
                    research_queue_metadata.get("latest_oos_promotion_ready", False),
                ),
            },
        )
        merged_snapshot = dict(base_snapshot)
        merged_snapshot.update({
            "status": str(research_queue_snapshot.get("status", "") or base_snapshot.get("status", "")),
            "validation_status": str(
                research_queue_snapshot.get("validation_status", "")
                or base_snapshot.get("validation_status", "")
            ),
            "out_of_sample_result": str(
                research_queue_snapshot.get("out_of_sample_result", "")
                or base_snapshot.get("out_of_sample_result", "not_run")
            ),
            "out_of_sample_result_reason": str(
                rq_oos_surface.get("out_of_sample_result_reason", "")
                or base_snapshot.get("out_of_sample_result_reason", "")
            ),
            "out_of_sample_coverage_status": str(
                rq_oos_surface.get("out_of_sample_coverage_status", "")
                or base_snapshot.get("out_of_sample_coverage_status", "")
            ),
            "oos_trade_pairs_count": int(
                rq_oos_surface.get("oos_trade_pairs_count", base_snapshot.get("oos_trade_pairs_count", 0))
                or 0
            ),
            "min_promotable_oos_trade_pairs": int(
                rq_oos_surface.get(
                    "min_promotable_oos_trade_pairs",
                    base_snapshot.get("min_promotable_oos_trade_pairs", 0),
                )
                or 0
            ),
            "oos_promotion_ready": bool(
                rq_oos_surface.get("promotion_ready", base_snapshot.get("oos_promotion_ready", False))
            ),
            "selection_status": str(
                research_queue_snapshot.get("selection_status", "")
                or base_snapshot.get("selection_status", "")
            ),
            "selection_governance_action": str(
                research_queue_snapshot.get("selection_governance_action", "")
                or base_snapshot.get("selection_governance_action", "")
            ),
            "selected_strategy_name": str(
                research_queue_snapshot.get("selected_strategy_name", "")
                or base_snapshot.get("selected_strategy_name", "")
            ),
            "portfolio_action": str(
                research_queue_snapshot.get("portfolio_action", "")
                or base_snapshot.get("portfolio_action", "")
            ),
            "selection_state_summary": merged_selection_summary or base_snapshot.get("selection_state_summary", {}),
            "selection_state_summary_text": str(
                research_queue_snapshot.get("selection_state_summary_text", "")
                or merged_selection_summary.get("summary", "")
                or base_snapshot.get("selection_state_summary_text", "")
            ),
            "primary_gate": str(
                research_queue_snapshot.get("primary_gate", "")
                or merged_selection_summary.get("primary_gate", "")
                or base_snapshot.get("primary_gate", "")
            ),
            "queue_recommendation": str(
                research_queue_snapshot.get("queue_recommendation", "")
                or merged_selection_summary.get("queue_recommendation", "")
                or base_snapshot.get("queue_recommendation", "")
            ),
            "upgrade_candidate_status": str(
                research_queue_snapshot.get("upgrade_candidate_status", "")
                or merged_selection_summary.get("upgrade_candidate_status", "")
                or base_snapshot.get("upgrade_candidate_status", "")
            ),
            "freeze_candidate_status": str(
                research_queue_snapshot.get("freeze_candidate_status", "")
                or merged_selection_summary.get("freeze_candidate_status", "")
                or base_snapshot.get("freeze_candidate_status", "")
            ),
            "consistency_snapshot_summary": (
                self._consistency_snapshot_summary_from_metadata(research_queue_metadata)
                or str(research_queue_snapshot.get("consistency_snapshot_summary", "") or "")
                or base_snapshot.get("consistency_snapshot_summary", "")
            ),
            "execution_plan_status": str(
                research_queue_snapshot.get("execution_plan_status", "")
                or base_snapshot.get("execution_plan_status", "")
            ),
            "execution_plan_summary": str(
                research_queue_snapshot.get("execution_plan_summary", "")
                or base_snapshot.get("execution_plan_summary", "")
            ),
            "next_validation_variant_key": str(
                research_queue_snapshot.get("next_validation_variant_key", "")
                or base_snapshot.get("next_validation_variant_key", "")
            ),
            "next_validation_variant_label": str(
                research_queue_snapshot.get("next_validation_variant_label", "")
                or base_snapshot.get("next_validation_variant_label", "")
            ),
            "next_validation_variant_reason": str(
                research_queue_snapshot.get("next_validation_variant_reason", "")
                or base_snapshot.get("next_validation_variant_reason", "")
            ),
            "next_validation_variant_changes": dict(
                research_queue_snapshot.get("next_validation_variant_changes", {})
                or base_snapshot.get("next_validation_variant_changes", {})
                or {}
            ),
            "next_validation_command_hint": str(
                research_queue_snapshot.get("next_validation_command_hint", "")
                or base_snapshot.get("next_validation_command_hint", "")
            ),
            "next_validation_execution": dict(
                research_queue_snapshot.get("next_validation_execution", {})
                or base_snapshot.get("next_validation_execution", {})
                or {}
            ),
            "queue_type": "ResearchQueue",
            "candidate_slug": str(research_queue_snapshot.get("candidate_slug", "") or ""),
            "candidate_name": str(research_queue_snapshot.get("candidate_name", "") or ""),
            "focus_source": "latest_trading_research_queue_bulletin_state",
        })
        candidate_slug = str(merged_snapshot.get("candidate_slug", "") or "")
        summary_overlay: dict[str, Any] = {}
        if candidate_slug:
            latest_validation_summary = self.trading.research_queue_latest_validation_summary({
                "candidate_slug": candidate_slug,
            })
            summary_overlay = dict(latest_validation_summary.get("summary", {}) or {})
        overlay_consistency = self._consistency_snapshot_summary_from_metadata(summary_overlay)
        current_consistency = str(merged_snapshot.get("consistency_snapshot_summary", "") or "")
        if overlay_consistency and ("not_run" in current_consistency or not current_consistency):
            merged_snapshot["consistency_snapshot_summary"] = overlay_consistency
        if summary_overlay:
            merged_snapshot["primary_blocker"] = str(
                merged_snapshot.get("primary_blocker", "") or summary_overlay.get("primary_blocker", "") or ""
            )
            merged_snapshot["execution_plan_status"] = str(
                merged_snapshot.get("execution_plan_status", "")
                or summary_overlay.get("execution_plan_status", "")
                or ""
            )
            merged_snapshot["execution_plan_summary"] = str(
                merged_snapshot.get("execution_plan_summary", "")
                or summary_overlay.get("execution_plan_summary", "")
                or ""
            )
        return merged_snapshot

    @staticmethod
    def _consistency_snapshot_summary_from_metadata(metadata: dict[str, Any]) -> str:
        metadata = metadata or {}
        recomputed = TradingDomainV01._consistency_snapshot_summary_from_summary_row(metadata)
        legacy = str(metadata.get("consistency_snapshot_summary", "") or "")
        if "market_regime_summary" in metadata and recomputed:
            return recomputed
        return legacy or recomputed

    def _latest_workbuddy_authority_catalog_snapshot(self) -> dict[str, Any]:
        row = self._latest_record_snapshot(
            "skill_registry_entries",
            lambda candidate: str(candidate.get("skill_name", "") or "") == "trading.workbuddy_current_skill_catalog",
            limit=200,
        )
        if not row:
            return {}
        metadata = dict(row.get("metadata", {}) or {})
        catalog_summary = dict(metadata.get("catalog_summary", {}) or {})
        alias_gaps = list(metadata.get("alias_gaps", []) or [])
        present_components = int(catalog_summary.get("present_component_count", 0) or 0)
        total_components = int(catalog_summary.get("top_component_total", 0) or 0)
        present_skills = int(catalog_summary.get("present_skill_count", 0) or 0)
        total_skills = int(catalog_summary.get("trading_skill_total", 0) or 0)
        missing_components = int(catalog_summary.get("missing_component_count", 0) or 0)
        missing_skills = int(catalog_summary.get("missing_skill_count", 0) or 0)
        disabled_components = int(catalog_summary.get("disabled_component_count", 0) or 0)
        disabled_skills = int(catalog_summary.get("disabled_skill_count", 0) or 0)
        summary_text = (
            f"components={present_components}/{total_components}, "
            f"trading_skills={present_skills}/{total_skills}, "
            f"missing_components={missing_components}, "
            f"missing_skills={missing_skills}, "
            f"disabled_components={disabled_components}, "
            f"disabled_skills={disabled_skills}, "
            f"alias_gaps={len(alias_gaps)}"
        )
        return {
            "skill_name": str(row.get("skill_name", "") or ""),
            "status": str(row.get("status", "") or ""),
            "validation_status": str(row.get("validation_status", "") or ""),
            "authority_mode": str(metadata.get("authority_mode", "") or ""),
            "catalog_summary": catalog_summary,
            "alias_gap_count": len(alias_gaps),
            "summary_text": summary_text,
            "implementation_status": "Implemented",
        }

    def _latest_workbuddy_probability_fusion_mock_snapshot(self) -> dict[str, Any]:
        row = self._latest_record_snapshot(
            "skill_registry_entries",
            lambda candidate: str(candidate.get("skill_name", "") or "") == "trading.workbuddy_probability_fusion_mock",
            limit=200,
        )
        if not row:
            return {}
        metadata = dict(row.get("metadata", {}) or {})
        fusion = dict(metadata.get("probability_fusion_mock", {}) or {})
        context_signal_summary = dict(fusion.get("context_signal_summary", {}) or {})
        return {
            "skill_name": str(row.get("skill_name", "") or ""),
            "status": str(row.get("status", "") or ""),
            "validation_status": str(row.get("validation_status", "") or ""),
            "out_of_sample_result": str(row.get("out_of_sample_result", "not_run") or "not_run"),
            "symbol": str(fusion.get("symbol", "") or ""),
            "timeframe": str(fusion.get("timeframe", "") or ""),
            "runtime_status": str(fusion.get("runtime_status", "") or ""),
            "contract_status": str(fusion.get("contract_status", "") or ""),
            "dominant_direction": str(fusion.get("dominant_direction", "") or ""),
            "signal_label": str(fusion.get("signal_label", "") or ""),
            "execution_gate": "research_only_no_trade",
            "context_signal_attached": bool(fusion.get("context_signal_attached", False)),
            "context_signal_direction": str(context_signal_summary.get("direction", "") or ""),
            "context_signal_label": str(context_signal_summary.get("signal_label", "") or ""),
            "governance_blocker_summary": str(metadata.get("governance_blocker_summary", "") or ""),
            "summary": str(fusion.get("summary", "") or ""),
            "authority_rule": str(metadata.get("authority_rule", "") or ""),
            "precedence_rule": str(metadata.get("precedence_rule", "") or ""),
            "effective_authority_order": list(metadata.get("effective_authority_order", []) or []),
            "implementation_status": "Implemented",
        }

    @staticmethod
    def _execution_plan_snapshot_from_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
        metadata = metadata or {}
        execution_plan = dict(metadata.get("execution_plan", {}) or {})
        return {
            "plan_status": str(
                metadata.get("execution_plan_status", "")
                or execution_plan.get("plan_status", "")
                or ""
            ),
            "summary": str(
                metadata.get("execution_plan_summary", "")
                or execution_plan.get("summary", "")
                or ""
            ),
            "target_blocker": str(
                execution_plan.get("target_blocker", "")
                or metadata.get("primary_blocker", "")
                or ""
            ),
            "default_variant_key": str(execution_plan.get("default_variant_key", "") or ""),
            "default_variant_label": str(execution_plan.get("default_variant_label", "") or ""),
            "default_variant_reason": str(execution_plan.get("default_variant_reason", "") or ""),
            "default_variant_changes": dict(execution_plan.get("default_variant_changes", {}) or {}),
            "command_hint": str(execution_plan.get("command_hint", "") or ""),
            "implementation_status": str(
                execution_plan.get("implementation_status", "")
                or metadata.get("implementation_status", "")
                or "Implemented"
            ),
        }

    def _serialize_trading_bulletin_state_snapshot(self, trading_row: dict[str, Any] | None) -> dict[str, Any]:
        if not trading_row:
            return {}
        metadata = trading_row.get("metadata", {}) or {}
        selection_state_summary = dict(metadata.get("selection_state_summary", {}) or {})
        execution_plan_snapshot = self._execution_plan_snapshot_from_metadata(metadata)
        priority_source_clearance_stage = str(
            metadata.get("a_share_proxy_guard_priority_source_clearance_stage", "")
            or metadata.get("priority_source_clearance_stage", "")
            or ""
        )
        priority_source_clearance_summary = str(
            metadata.get("a_share_proxy_guard_priority_source_clearance_summary", "")
            or metadata.get("priority_source_clearance_summary", "")
            or ""
        )
        priority_route_status = str(
            metadata.get("priority_route_status", "")
            or priority_source_clearance_stage
            or ""
        )
        oos_surface = self._oos_surface_fields(
            metadata=metadata,
            fallback={
                "out_of_sample_result_reason": metadata.get("latest_out_of_sample_reason", ""),
                "out_of_sample_coverage_status": metadata.get("latest_out_of_sample_coverage_status", ""),
                "oos_trade_pairs_count": metadata.get("latest_oos_trade_pairs_count", 0),
                "min_promotable_oos_trade_pairs": metadata.get("latest_min_promotable_oos_trade_pairs", 0),
                "promotion_ready": metadata.get("latest_oos_promotion_ready", False),
            },
        )
        return {
            "bulletin_id": str(trading_row.get("id", "") or ""),
            "status": str(trading_row.get("status", "") or ""),
            "summary": str(trading_row.get("summary", "") or ""),
            "queue_type": str(metadata.get("queue_type", "") or ""),
            "candidate_slug": str(metadata.get("candidate_slug", "") or ""),
            "sync_source": str(metadata.get("sync_source", "") or ""),
            "decision": str(metadata.get("decision", "") or ""),
            "selection_status": str(metadata.get("selection_status", "") or ""),
            "selection_governance_action": str(metadata.get("selection_governance_action", "") or ""),
            "selected_strategy_name": str(metadata.get("selected_strategy_name", "") or ""),
            "portfolio_action": str(metadata.get("portfolio_action", "") or ""),
            "selection_state_summary": selection_state_summary,
            "primary_gate": str(selection_state_summary.get("primary_gate", "") or ""),
            "queue_recommendation": str(selection_state_summary.get("queue_recommendation", "") or ""),
            "upgrade_candidate_status": str(selection_state_summary.get("upgrade_candidate_status", "") or ""),
            "freeze_candidate_status": str(selection_state_summary.get("freeze_candidate_status", "") or ""),
            "consistency_snapshot_summary": self._consistency_snapshot_summary_from_metadata(metadata),
            "execution_plan_status": str(execution_plan_snapshot.get("plan_status", "") or ""),
            "execution_plan_summary": str(execution_plan_snapshot.get("summary", "") or ""),
            "next_validation_variant_key": str(execution_plan_snapshot.get("default_variant_key", "") or ""),
            "next_validation_variant_label": str(execution_plan_snapshot.get("default_variant_label", "") or ""),
            "next_validation_variant_reason": str(execution_plan_snapshot.get("default_variant_reason", "") or ""),
            "next_validation_variant_changes": dict(execution_plan_snapshot.get("default_variant_changes", {}) or {}),
            "next_validation_command_hint": str(execution_plan_snapshot.get("command_hint", "") or ""),
            "next_validation_execution": execution_plan_snapshot,
            "primary_blocker": str(metadata.get("primary_blocker", "") or ""),
            "out_of_sample_result": str(trading_row.get("out_of_sample_result", "not_run") or "not_run"),
            "out_of_sample_result_reason": str(oos_surface.get("out_of_sample_result_reason", "") or ""),
            "out_of_sample_coverage_status": str(oos_surface.get("out_of_sample_coverage_status", "") or ""),
            "oos_trade_pairs_count": int(oos_surface.get("oos_trade_pairs_count", 0) or 0),
            "min_promotable_oos_trade_pairs": int(
                oos_surface.get("min_promotable_oos_trade_pairs", 0) or 0
            ),
            "promotion_ready": bool(oos_surface.get("promotion_ready", False)),
            "priority_route_status": priority_route_status,
            "priority_source_clearance_stage": priority_source_clearance_stage,
            "priority_source_clearance_summary": priority_source_clearance_summary,
            "validation_round": {
                "validation_round_key": str(metadata.get("validation_round_key", "") or ""),
                "validation_round_index": int(metadata.get("validation_round_index", 0) or 0),
                "validation_round_reused": bool(metadata.get("validation_round_reused", False)),
                "prior_validation_round_count": int(metadata.get("prior_validation_round_count", 0) or 0),
                "implementation_status": "Implemented",
            },
            "implementation_status": "Implemented",
        }

    def _latest_trading_research_queue_bulletin_state_snapshot(self) -> dict[str, Any]:
        rows = self.store.list_records("bulletin_state_records", limit=50, newest=True)
        research_queue_rows = [
            row
            for row in rows
            if str((row.get("metadata", {}) or {}).get("queue_type", "") or "") == "ResearchQueue"
        ]
        trading_row = next(
            (
                row
                for row in research_queue_rows
                if str((row.get("metadata", {}) or {}).get("sync_source", "") or "")
                == "trading_research_queue_latest_validation_summary"
            ),
            None,
        )
        if trading_row is None:
            trading_row = next(
                (
                    row
                    for row in research_queue_rows
                    if str((row.get("metadata", {}) or {}).get("validation_round_key", "") or "")
                ),
                research_queue_rows[0] if research_queue_rows else None,
            )
        snapshot = self._serialize_trading_bulletin_state_snapshot(trading_row)
        candidate_slug = str(snapshot.get("candidate_slug", "") or "")
        if not candidate_slug:
            return snapshot
        latest_candidate_row = next(
            (
                row
                for row in research_queue_rows
                if (
                    str((row.get("metadata", {}) or {}).get("candidate_slug", "") or "") == candidate_slug
                    and (
                        str((row.get("metadata", {}) or {}).get("sync_source", "") or "")
                        == "trading_research_queue_latest_validation_summary"
                    )
                )
            ),
            None,
        )
        if latest_candidate_row is None:
            latest_candidate_row = next(
                (
                    row
                    for row in research_queue_rows
                    if str((row.get("metadata", {}) or {}).get("candidate_slug", "") or "") == candidate_slug
                ),
                None,
            )
        if latest_candidate_row is not None:
            latest_candidate_snapshot = self._serialize_trading_bulletin_state_snapshot(latest_candidate_row)
            for key in (
                "sync_source",
                "priority_route_status",
                "priority_source_clearance_stage",
                "priority_source_clearance_summary",
            ):
                if latest_candidate_snapshot.get(key):
                    snapshot[key] = latest_candidate_snapshot[key]
        summary = self.trading.research_queue_manual_promotion_summary({
            "candidate_slug": candidate_slug,
            "limit": 5,
        })
        candidate_rows = summary.get("candidate_rows", []) or []
        candidate_row = candidate_rows[0] if candidate_rows else {}
        if not candidate_row:
            return snapshot
        approval_status = str(candidate_row.get("approval_status", "") or "")
        can_submit_now = bool(candidate_row.get("can_submit_now", False))
        latest_decision = str(candidate_row.get("latest_decision", "") or "")
        queue_recommendation = str(candidate_row.get("queue_recommendation", snapshot.get("queue_recommendation", "")) or "")
        primary_gate = str(candidate_row.get("primary_gate", snapshot.get("primary_gate", "")) or "")
        upgrade_candidate_status = str(candidate_row.get("upgrade_candidate_status", snapshot.get("upgrade_candidate_status", "")) or "")
        freeze_candidate_status = str(candidate_row.get("freeze_candidate_status", snapshot.get("freeze_candidate_status", "")) or "")
        selection_status = "abstain"
        selection_governance_action = "needs_review"
        if latest_decision == "rejected" or approval_status == "rejected":
            selection_governance_action = "freeze"
        elif latest_decision == "approved" and can_submit_now and queue_recommendation == "ready_for_manual_promotion_review":
            selection_governance_action = "keep"
        queue_recommendation = str(candidate_row.get("queue_recommendation", snapshot.get("queue_recommendation", "")) or "")
        primary_gate = str(candidate_row.get("primary_gate", snapshot.get("primary_gate", "")) or "")
        upgrade_candidate_status = str(candidate_row.get("upgrade_candidate_status", snapshot.get("upgrade_candidate_status", "")) or "")
        freeze_candidate_status = str(candidate_row.get("freeze_candidate_status", snapshot.get("freeze_candidate_status", "")) or "")
        selection_summary_text = (
            f"recommendation={queue_recommendation}, primary_gate={primary_gate}, "
            f"upgrade_status={upgrade_candidate_status}, freeze_status={freeze_candidate_status}, "
            f"approval_status={str(candidate_row.get('approval_status', '') or '')}, "
            f"ready={int(candidate_row.get('ready_count', 0) or 0)}/{int(candidate_row.get('total_count', 0) or 0)}, "
            f"decisions={int(candidate_row.get('approval_record_count', 0) or 0)}, "
            f"proxy_guard_blocked={bool(candidate_row.get('proxy_guard_blocked', False))}"
        )
        selection_state_summary = {
            "queue_recommendation": queue_recommendation,
            "primary_gate": primary_gate,
            "upgrade_candidate_status": upgrade_candidate_status,
            "freeze_candidate_status": freeze_candidate_status,
            "summary": selection_summary_text,
            "source": "research_queue_manual_promotion_summary",
        }
        snapshot.update({
            "candidate_name": str(candidate_row.get("candidate_name", "") or ""),
            "decision": latest_decision or approval_status,
            "approval_status": approval_status,
            "can_submit_now": can_submit_now,
            "missing_keys": list(candidate_row.get("missing_keys", []) or []),
            "ready_count": int(candidate_row.get("ready_count", 0) or 0),
            "total_count": int(candidate_row.get("total_count", 0) or 0),
            "proxy_guard_blocked": bool(candidate_row.get("proxy_guard_blocked", False)),
            "latest_decision": latest_decision,
            "out_of_sample_result": str(candidate_row.get("out_of_sample_result", "") or ""),
            "validation_status": str(candidate_row.get("validation_status", "") or ""),
            "replay_variant_governance_hint": str(candidate_row.get("replay_variant_governance_hint", "") or ""),
            "replay_variant_governance_priority_action": str(
                candidate_row.get("replay_variant_governance_priority_action", "") or ""
            ),
            "replay_variant_governance_summary": str(candidate_row.get("replay_variant_governance_summary", "") or ""),
            "a_share_proxy_preferred_action": str(
                ((candidate_row.get("a_share_proxy_guard", {}) or {}).get("preferred_action", "")) or ""
            ),
            "a_share_proxy_summary": str(
                ((candidate_row.get("a_share_proxy_guard", {}) or {}).get("summary", "")) or ""
            ),
            "selection_status": selection_status,
            "selection_governance_action": selection_governance_action,
            "portfolio_action": "no_trade",
            "selected_strategy_name": "NO_TRADE",
            "queue_recommendation": queue_recommendation,
            "primary_gate": primary_gate,
            "upgrade_candidate_status": upgrade_candidate_status,
            "freeze_candidate_status": freeze_candidate_status,
            "selection_state_summary": selection_state_summary,
            "selection_state_summary_text": selection_summary_text,
            "research_queue_summary": selection_summary_text,
        })
        return snapshot

    def _latest_trading_replay_bulletin_state_snapshot(self) -> dict[str, Any]:
        rows = self.store.list_records("bulletin_state_records", limit=50, newest=True)
        trading_row = self._latest_record_snapshot(
            "bulletin_state_records",
            lambda row: self._is_trading_replay_bulletin_state_row(row),
            limit=50,
        )
        return self._serialize_trading_bulletin_state_snapshot(trading_row)

    @staticmethod
    def _is_trading_replay_bulletin_state_row(row: dict[str, Any]) -> bool:
        metadata = dict((row or {}).get("metadata", {}) or {})
        selection_state_summary = dict(metadata.get("selection_state_summary", {}) or {})
        summary = str(row.get("summary", "") or "")
        selected_sample_summary = str(metadata.get("selected_sample_summary", "") or "")
        top_ranked_candidate_summary = str(metadata.get("top_ranked_candidate_summary", "") or "")
        queue_type = str(metadata.get("queue_type", "") or "")
        has_replay_writeback = bool(
            summary
            or selected_sample_summary
            or top_ranked_candidate_summary
            or metadata.get("cost_assumption_summary")
            or metadata.get("selected_sample_consistency")
        )
        if has_replay_writeback:
            return True
        if queue_type == "ResearchQueue":
            return False
        return bool(
            str(row.get("domain", "") or "") == "trading"
            or str(metadata.get("selected_strategy_name", "") or "")
            or selection_state_summary
        )

    def _latest_trading_bulletin_state_snapshot(self) -> dict[str, Any]:
        research_queue_snapshot = self._latest_trading_research_queue_bulletin_state_snapshot()
        if research_queue_snapshot:
            return research_queue_snapshot
        replay_snapshot = self._latest_trading_replay_bulletin_state_snapshot()
        if replay_snapshot:
            return replay_snapshot
        rows = self.store.list_records("bulletin_state_records", limit=50, newest=True)
        trading_candidates = [
            row
            for row in rows
            if (
                str(row.get("domain", "") or "") == "trading"
                or str((row.get("metadata", {}) or {}).get("selected_strategy_name", "") or "")
                or bool(((row.get("metadata", {}) or {}).get("selection_state_summary", {}) or {}))
                or str((row.get("metadata", {}) or {}).get("queue_type", "") or "") == "ResearchQueue"
                or str((row.get("metadata", {}) or {}).get("candidate_slug", "") or "")
            )
        ]
        return self._serialize_trading_bulletin_state_snapshot(trading_candidates[0] if trading_candidates else None)

    def _latest_record_snapshot(
        self,
        table: str,
        predicate: Callable[[dict[str, Any]], bool] | None = None,
        *,
        limit: int = 50,
    ) -> dict[str, Any] | None:
        rows = self.store.list_records(table, limit=limit, newest=True)
        if predicate is None:
            return rows[0] if rows else None
        for row in rows:
            if predicate(row):
                return row
        return None

    def _latest_priority_record_snapshot(
        self,
        table: str,
        predicates: list[Callable[[dict[str, Any]], bool]],
        *,
        limit: int = 50,
    ) -> dict[str, Any] | None:
        for predicate in predicates:
            row = self._latest_record_snapshot(table, predicate, limit=limit)
            if row is not None:
                return row
        return self._latest_record_snapshot(table, limit=limit)

    def status(self) -> dict[str, Any]:
        latest_trading_replay_bulletin_state = self._latest_trading_replay_bulletin_state_snapshot()
        latest_trading_research_queue_bulletin_state = self._latest_trading_research_queue_bulletin_state_snapshot()
        latest_trading_bulletin_state = (
            latest_trading_research_queue_bulletin_state or latest_trading_replay_bulletin_state
        )
        latest_self_evolution_log = self._latest_record_snapshot("evolution_logs")
        latest_skill_registry_entry = self._latest_record_snapshot("skill_registry_entries")
        latest_module_status_record = self._latest_record_snapshot("module_status_records")
        latest_bulletin_state_record = self._latest_record_snapshot("bulletin_state_records")
        latest_trading_self_evolution_log = self._latest_priority_record_snapshot(
            "evolution_logs",
            [
                lambda row: (
                    str(row.get("trigger", "") or "").startswith("trading_")
                    and (
                        str((row.get("metadata", {}) or {}).get("domain", "") or "") == "trading"
                        or str((row.get("metadata", {}) or {}).get("queue_type", "") or "") == "ResearchQueue"
                        or str((row.get("metadata", {}) or {}).get("candidate_slug", "") or "")
                        or str((row.get("metrics", {}) or {}).get("candidate_slug", "") or "")
                    )
                ),
                lambda row: (
                    str(row.get("trigger", "") or "").startswith("trading_")
                    and str(row.get("change_type", "") or "") in {"governance_enrichment", "governance_sync"}
                ),
                lambda row: (
                    str(row.get("trigger", "") or "") == "trading_research_queue_validation_summary_synced"
                    or str(row.get("change_type", "") or "") == "governance_sync"
                ),
            ],
            limit=200,
        )
        latest_trading_skill_registry_entry = self._latest_priority_record_snapshot(
            "skill_registry_entries",
            [
                lambda row: (
                    str((row.get("metadata", {}) or {}).get("sync_source", "") or "")
                    == "trading_research_queue_latest_validation_summary"
                ),
                lambda row: str(row.get("skill_name", "") or "").startswith("trading.research_queue."),
                lambda row: (
                    str((row.get("metadata", {}) or {}).get("queue_type", "") or "")
                    == "ResearchQueue"
                ),
                lambda row: (
                    str(row.get("domain", "") or "") == "trading"
                    and str(row.get("skill_name", "") or "").startswith("trading.")
                ),
            ],
            limit=200,
        )
        latest_trading_module_status_record = self._latest_priority_record_snapshot(
            "module_status_records",
            [
                lambda row: (
                    str((row.get("metadata", {}) or {}).get("sync_source", "") or "")
                    == "trading_research_queue_latest_validation_summary"
                ),
                lambda row: (
                    str((row.get("metadata", {}) or {}).get("queue_type", "") or "")
                    == "ResearchQueue"
                ),
                lambda row: (
                    str(row.get("domain", "") or "") == "trading"
                    and "trading" in str(row.get("module_name", "") or "").lower()
                ),
            ],
            limit=200,
        )
        latest_trading_bulletin_state_record = self._latest_priority_record_snapshot(
            "bulletin_state_records",
            [
                lambda row: (
                    str((row.get("metadata", {}) or {}).get("domain", "") or "") == "trading"
                    and str((row.get("metadata", {}) or {}).get("queue_type", "") or "") == "ResearchQueue"
                ),
                lambda row: (
                    str((row.get("metadata", {}) or {}).get("sync_source", "") or "")
                    == "trading_research_queue_latest_validation_summary"
                ),
                lambda row: (
                    (
                        str(row.get("domain", "") or "") == "trading"
                        or str((row.get("metadata", {}) or {}).get("domain", "") or "") == "trading"
                    )
                    and (
                        str(row.get("queue_type", "") or "") == "ResearchQueue"
                        or str((row.get("metadata", {}) or {}).get("queue_type", "") or "") == "ResearchQueue"
                        or str(row.get("candidate_slug", "") or "")
                        or str((row.get("metadata", {}) or {}).get("candidate_slug", "") or "")
                    )
                ),
            ],
            limit=200,
        )
        if latest_trading_bulletin_state_record and not latest_trading_bulletin_state_record.get("candidate_slug"):
            latest_trading_bulletin_state_record = dict(latest_trading_bulletin_state_record)
            latest_trading_bulletin_state_record["candidate_slug"] = str(
                (latest_trading_bulletin_state_record.get("metadata", {}) or {}).get("candidate_slug", "") or ""
            )
        latest_workbuddy_authority_catalog = self._latest_workbuddy_authority_catalog_snapshot()
        latest_workbuddy_probability_fusion_mock = self._latest_workbuddy_probability_fusion_mock_snapshot()
        return {
            "version": "v0.1",
            "storage": str(self.store.db_path),
            "audit_log": str(self.store.audit.path),
            "announcement_board": str(self.board.path),
            "counts": self.store.counts(),
            "legacy": self.store.legacy_status(),
            "trading_status": self._latest_trading_status_snapshot(),
            "latest_self_evolution_log": latest_self_evolution_log,
            "latest_skill_registry_entry": latest_skill_registry_entry,
            "latest_module_status_record": latest_module_status_record,
            "latest_bulletin_state_record": latest_bulletin_state_record,
            "latest_trading_self_evolution_log": latest_trading_self_evolution_log,
            "latest_trading_skill_registry_entry": latest_trading_skill_registry_entry,
            "latest_trading_module_status_record": latest_trading_module_status_record,
            "latest_trading_bulletin_state_record": latest_trading_bulletin_state_record,
            "latest_trading_replay_bulletin_state": latest_trading_replay_bulletin_state,
            "latest_trading_research_queue_bulletin_state": latest_trading_research_queue_bulletin_state,
            "latest_trading_bulletin_state": latest_trading_bulletin_state,
            "latest_workbuddy_authority_catalog": latest_workbuddy_authority_catalog,
            "latest_workbuddy_probability_fusion_mock": latest_workbuddy_probability_fusion_mock,
            "module_status": {
                "keyword_retrieval": "Implemented",
                "unified_learning_entry": "Implemented",
                "learning_review_view": "Implemented",
                "unified_memory_review_queue": "Implemented",
                "unified_memory_review_confirmation": "Implemented",
                "unified_memory_review_signals": "Implemented",
                "unified_memory_review_ranking_suggestions": "Implemented",
                "unified_memory_review_ranking_diff": "Implemented",
                "unified_memory_review_ranking_diff_confirmation": "Implemented",
                "unified_memory_review_ranking_diff_summary": "Implemented",
                "unified_memory_review_ranking_diff_signals": "Implemented",
                "unified_memory_review_ranking_policy_suggestions": "Implemented",
                "unified_memory_review_ranking_policy_approval": "Implemented",
                "unified_memory_review_ranking_policy_approval_summary": "Implemented",
                "unified_memory_review_ranking_policy_approval_signals": "Implemented",
                "unified_memory_review_ranking_policy_change_candidates": "Implemented",
                "unified_memory_review_ranking_policy_change_candidate_approval": "Implemented",
                "unified_memory_review_ranking_policy_change_candidate_approval_summary": "Implemented",
                "learning_traceability_view": "Implemented",
                "learning_chain_view": "Implemented",
                "learning_chain_writeback": "Implemented",
                "learning_chain_writeback_idempotent": "Implemented",
                "learning_writeback_audit_view": "Implemented",
                "learning_writeback_overview": "Implemented",
                "learning_writeback_snapshot": "Implemented",
                "legacy_lessons_mapping": "Implemented",
                "reasoning_trace": "Implemented",
                "trading_domain": "Implemented",
                "trading_replay_loop": "Implemented",
                "trading_skill_registry": "Implemented",
                "trading_validation_pipeline": "Implemented",
                "trading_replay_history_summary": "Implemented",
                "trading_strategy_governance_summary": "Implemented",
                "trading_research_queue_evidence_gap_summary": "Implemented",
                "trading_research_queue_consistency_diagnostics_summary": "Implemented",
                "trading_research_queue_readiness_summary": "Implemented",
                "trading_research_queue_approval_summary": "Implemented",
                "trading_research_queue_manual_approval_submission": "Implemented",
                "trading_research_queue_approval_signals": "Implemented",
                "trading_research_queue_watchlist": "Implemented",
                "trading_research_queue_review_agenda": "Implemented",
                "trading_research_queue_next_validation_slice": "Implemented",
                "trading_research_queue_run_next_validation_slice": "Implemented",
                "trading_research_queue_latest_validation_summary": "Implemented",
                "trading_research_queue_sync_bulletin_from_latest_validation": "Implemented",
                "trading_reconcile_a_share_authority": "Implemented",
                "trading_a_share_authority_constraints_snapshot": "Implemented",
                "trading_a_share_tdx_quote_snapshot": "Implemented",
                "trading_a_share_tencent_qt_realtime_snapshot": "Implemented",
                "trading_a_share_workbuddy_context_snapshot": "Implemented",
                "trading_a_share_westock_fund_flow_history_snapshot": "Implemented",
                "trading_a_share_tushare_moneyflow_history_fallback_snapshot": "Implemented",
                "trading_a_share_realtime_crosscheck_summary": "Implemented",
                "trading_a_share_realtime_crosscheck_research_bridge": "Implemented",
                "trading_a_share_tdx_minute_kline_snapshot": "Implemented",
                "trading_a_share_proxy_guard_source_coverage": "Implemented",
                "trading_a_share_true_money_flow_readiness": "Implemented",
                "trading_a_share_real_data_source_registry": "Implemented",
                "trading_a_share_connector_runtime_audit": "Implemented",
                "trading_a_share_real_data_pull_plan": "Implemented",
                "foundation_data_governance_v2": "Implemented",
                "order_book_ingestion": "Interface",
                "trade_print_ingestion": "Interface",
                "vector_retrieval": "Mock",
                "image_preference": "Mock",
                "maibot_adapter": "Mock",
                "geopolitical_graph": "Future Roadmap",
                "live_trading": "Not Implemented Yet",
            },
            "safety": {
                "research_mode": True,
                "live_trading_enabled": False,
                "high_risk_actions_require_approval": True,
            },
        }

    def _build_unified_memory_review_items(
        self,
        *,
        legacy_mapping: dict[str, Any],
        feedback_candidates: dict[str, Any],
        learning_chains: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        legacy_view = legacy_mapping.get("legacy_memory_decision_view", {})
        for item in legacy_view.get("promote_now", []):
            items.append(
                {
                    "queue_bucket": "review_now",
                    "source_view": "legacy_memory_decision_view",
                    "candidate_type": item.get("candidate_type", ""),
                    "label": item.get("label", ""),
                    "priority_score": float(item.get("action_score", 0.0)),
                    "reason": item.get("why_now", ""),
                    "evidence_signal": item.get("current_signal", ""),
                    "implementation_status": "Implemented",
                }
            )
        for item in legacy_view.get("watch_for_downgrade", []):
            items.append(
                {
                    "queue_bucket": "watchlist",
                    "source_view": "legacy_memory_decision_view",
                    "candidate_type": item.get("candidate_type", ""),
                    "label": item.get("label", ""),
                    "priority_score": float(item.get("risk_score", 0.0)),
                    "reason": item.get("risk_reason", ""),
                    "evidence_signal": item.get("next_review_trigger", ""),
                    "implementation_status": "Implemented",
                }
            )
        for item in feedback_candidates.get("candidates", []):
            queue_bucket = {
                "immediate_candidate": "review_now",
                "need_more_evidence": "watchlist",
                "single_observation_noise": "observe",
            }.get(item.get("migration_status", ""), "observe")
            items.append(
                {
                    "queue_bucket": queue_bucket,
                    "source_view": "feedback_memory_candidates",
                    "candidate_type": item.get("pattern_type", ""),
                    "label": item.get("text", ""),
                    "priority_score": float(item.get("priority_score", 0.0)),
                    "reason": item.get("migration_reason", ""),
                    "evidence_signal": f"feedback_count={item.get('feedback_count', 0)}, target_count={len(item.get('target_ids', []))}",
                    "implementation_status": "Implemented",
                }
            )
        for chain in learning_chains.get("lesson_chains", []):
            items.append(
                {
                    "queue_bucket": "review_now",
                    "source_view": "learning_chains",
                    "candidate_type": "lesson_chain",
                    "label": chain.get("text", ""),
                    "priority_score": float(chain.get("entry_count", 0) * 10 + len(chain.get("target_ids", [])) * 2),
                    "reason": "Repeated lesson chain is stable enough for human review and possible long-term consolidation.",
                    "evidence_signal": f"entry_count={chain.get('entry_count', 0)}, target_types={','.join(chain.get('target_types', []))}",
                    "implementation_status": "Implemented",
                }
            )
        for chain in learning_chains.get("improvement_chains", []):
            items.append(
                {
                    "queue_bucket": "review_now",
                    "source_view": "learning_chains",
                    "candidate_type": "improvement_chain",
                    "label": chain.get("text", ""),
                    "priority_score": float(chain.get("entry_count", 0) * 10 + len(chain.get("target_ids", [])) * 2),
                    "reason": "Repeated improvement chain is stable enough for human review and possible long-term consolidation.",
                    "evidence_signal": f"entry_count={chain.get('entry_count', 0)}, target_types={','.join(chain.get('target_types', []))}",
                    "implementation_status": "Implemented",
                }
            )
        return items

    @staticmethod
    def _review_bucket_rank(bucket: str) -> int:
        return {
            "review_now": 0,
            "watchlist": 1,
            "observe": 2,
        }.get(bucket, 3)

    @staticmethod
    def _count_queue_buckets(items: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items:
            bucket = str(item.get("queue_bucket", "unknown") or "unknown")
            counts[bucket] = counts.get(bucket, 0) + 1
        return counts

    @staticmethod
    def _count_source_views(items: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items:
            source_view = str(item.get("source_view", "unknown") or "unknown")
            counts[source_view] = counts.get(source_view, 0) + 1
        return counts

    @staticmethod
    def _collect_chain_atom_ids(chain: dict[str, Any]) -> list[str]:
        atom_ids = {item for item in chain.get("target_ids", []) if str(item).startswith("atom_")}
        atom_ids.update(item for item in chain.get("source_record_ids", []) if str(item).startswith("atom_"))
        return sorted(atom_ids)

    @staticmethod
    def _merge_learning_chain_ref(
        refs: list[dict[str, Any]],
        chain_type: str,
        text: str,
        entry_count: int,
    ) -> tuple[dict[str, Any], float, str]:
        target_delta = min(0.12, 0.02 * int(entry_count))
        for ref in refs:
            if ref.get("chain_type") == chain_type and ref.get("text") == text:
                previous_delta = float(ref.get("applied_delta", min(0.12, 0.02 * int(ref.get("entry_count", 0)))))
                previous_entry_count = int(ref.get("entry_count", 0))
                ref["entry_count"] = int(entry_count)
                ref["applied_delta"] = target_delta
                delta = max(0.0, target_delta - previous_delta)
                state = "updated" if previous_entry_count != int(entry_count) or previous_delta != target_delta else "unchanged"
                return ref, delta, state
        ref_payload = {
            "chain_type": chain_type,
            "text": text,
            "entry_count": int(entry_count),
            "applied_delta": target_delta,
        }
        refs.append(ref_payload)
        return ref_payload, target_delta, "new"

    @staticmethod
    def _normalize_relation_for_comparison(relation: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": relation.get("id", ""),
            "source_atom_id": relation.get("source_atom_id", ""),
            "target_atom_id": relation.get("target_atom_id", ""),
            "relation_type": relation.get("relation_type", ""),
            "confidence": float(relation.get("confidence", 0.0)),
            "evidence_ids": sorted(relation.get("evidence_ids", [])),
            "metadata": relation.get("metadata", {}),
        }

    def _build_learning_chain_state_index(self) -> dict[str, dict[str, Any]]:
        atoms = self.store.list_records("atoms", limit=100000)
        state_index: dict[str, dict[str, Any]] = {}
        for atom in atoms:
            metadata = atom.get("metadata", {})
            if not isinstance(metadata, dict):
                continue
            latest_apply = metadata.get("last_learning_apply", {})
            state = self._infer_latest_apply_state(latest_apply)
            for ref in metadata.get("learning_chain_refs", []):
                text = self._normalize_lesson_text(ref.get("text", ""))
                if not text:
                    continue
                info = state_index.setdefault(
                    text,
                    {
                        "current_apply_state": "not_in_learning_chain_writeback",
                        "matching_atom_ids": [],
                    },
                )
                info["current_apply_state"] = self._merge_apply_state_priority(info["current_apply_state"], state)
                if atom["id"] not in info["matching_atom_ids"]:
                    info["matching_atom_ids"].append(atom["id"])
        for info in state_index.values():
            info["matching_atom_ids"].sort()
        return state_index

    @staticmethod
    def _infer_latest_apply_state(latest_apply: dict[str, Any]) -> str:
        if not isinstance(latest_apply, dict):
            return "not_in_learning_chain_writeback"
        if latest_apply.get("new_chain_refs") or latest_apply.get("updated_chain_refs") or latest_apply.get("created_relation_ids") or latest_apply.get("updated_relation_ids"):
            return "new_or_changed"
        if latest_apply.get("unchanged_chain_refs") or latest_apply.get("confirmed_relation_ids"):
            return "confirmed_only"
        return "not_in_learning_chain_writeback"

    @staticmethod
    def _merge_apply_state_priority(previous: str, current: str) -> str:
        order = {
            "new_or_changed": 3,
            "confirmed_only": 2,
            "not_in_learning_chain_writeback": 1,
        }
        return current if order.get(current, 0) >= order.get(previous, 0) else previous

    @staticmethod
    def _normalize_lesson_text(text: str) -> str:
        return " ".join(str(text or "").strip().split())

    def _read_legacy_lessons(self, path: Path) -> list[str]:
        lessons: list[str] = []
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line.startswith("教训:"):
                    continue
                lesson = self._normalize_lesson_text(line.split(":", 1)[1])
                if lesson and lesson not in lessons:
                    lessons.append(lesson)
        return lessons

    def _collect_text_counts(self, learning_entries: list[dict[str, Any]], field_name: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in learning_entries:
            for text in entry.get(field_name, []):
                normalized = self._normalize_lesson_text(text)
                if normalized:
                    counts[normalized] = counts.get(normalized, 0) + 1
        return counts

    def _list_legacy_action_confirmations(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for entry in self.store.list_records("learning_entries", limit=100000, newest=False):
            if entry.get("entry_type") != "legacy_memory_action_confirmation":
                continue
            metadata = entry.get("metadata", {}) or {}
            rows.append(
                {
                    "id": entry.get("id", ""),
                    "created_at": entry.get("created_at", ""),
                    "candidate_label": str(metadata.get("candidate_label", "") or "").strip(),
                    "candidate_type": str(metadata.get("candidate_type", "") or "").strip(),
                    "action_bucket": str(metadata.get("action_bucket", "promote_earlier") or "promote_earlier").strip(),
                    "accepted": bool(metadata.get("accepted", False)),
                    "left_profile": str(metadata.get("left_profile", "") or "").strip(),
                    "right_profile": str(metadata.get("right_profile", "") or "").strip(),
                }
            )
        return rows

    def _list_unified_memory_review_confirmations(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for entry in self.store.list_records("learning_entries", limit=100000, newest=False):
            if entry.get("entry_type") != "unified_memory_review_confirmation":
                continue
            metadata = entry.get("metadata", {}) or {}
            rows.append(
                {
                    "id": entry.get("id", ""),
                    "created_at": entry.get("created_at", ""),
                    "source_view": str(metadata.get("source_view", "") or "").strip(),
                    "candidate_type": str(metadata.get("candidate_type", "") or "").strip(),
                    "label": str(metadata.get("label", "") or "").strip(),
                    "queue_bucket": str(metadata.get("queue_bucket", "") or "").strip(),
                    "decision": str(metadata.get("decision", "") or "").strip(),
                }
            )
        return rows

    def _list_unified_memory_review_ranking_diff_confirmations(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for entry in self.store.list_records("learning_entries", limit=100000, newest=False):
            if entry.get("entry_type") != "unified_memory_review_ranking_diff_confirmation":
                continue
            metadata = entry.get("metadata", {}) or {}
            rows.append(
                {
                    "id": entry.get("id", ""),
                    "created_at": entry.get("created_at", ""),
                    "label": str(metadata.get("label", "") or "").strip(),
                    "source_view": str(metadata.get("source_view", "") or "").strip(),
                    "candidate_type": str(metadata.get("candidate_type", "") or "").strip(),
                    "decision": str(metadata.get("decision", "") or "").strip(),
                    "profile": str(metadata.get("profile", "") or "").strip(),
                    "current_rank": int(metadata.get("current_rank", 0) or 0),
                    "suggested_rank": int(metadata.get("suggested_rank", 0) or 0),
                    "score_delta": float(metadata.get("score_delta", 0.0) or 0.0),
                }
            )
        return rows

    def _list_unified_memory_review_ranking_policy_approvals(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for entry in self.store.list_records("learning_entries", limit=100000, newest=False):
            if entry.get("entry_type") != "unified_memory_review_ranking_policy_approval":
                continue
            metadata = entry.get("metadata", {}) or {}
            rows.append(
                {
                    "id": entry.get("id", ""),
                    "created_at": entry.get("created_at", ""),
                    "dimension": str(metadata.get("dimension", "") or "").strip(),
                    "key": str(metadata.get("key", "") or "").strip(),
                    "decision": str(metadata.get("decision", "") or "").strip(),
                    "profile": str(metadata.get("profile", "") or "").strip(),
                    "weight_signal": str(metadata.get("weight_signal", "") or "").strip(),
                    "suggested_weight_delta": int(metadata.get("suggested_weight_delta", 0) or 0),
                }
            )
        return rows

    def _list_unified_memory_review_ranking_policy_change_candidate_approvals(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for entry in self.store.list_records("learning_entries", limit=100000, newest=False):
            if entry.get("entry_type") != "unified_memory_review_ranking_policy_change_candidate_approval":
                continue
            metadata = entry.get("metadata", {}) or {}
            rows.append(
                {
                    "id": entry.get("id", ""),
                    "created_at": entry.get("created_at", ""),
                    "dimension": str(metadata.get("dimension", "") or "").strip(),
                    "key": str(metadata.get("key", "") or "").strip(),
                    "decision": str(metadata.get("decision", "") or "").strip(),
                    "profile": str(metadata.get("profile", "") or "").strip(),
                    "change_bucket": str(metadata.get("change_bucket", "") or "").strip(),
                    "weight_signal": str(metadata.get("weight_signal", "") or "").strip(),
                    "suggested_weight_delta": int(metadata.get("suggested_weight_delta", 0) or 0),
                }
            )
        return rows

    @staticmethod
    def _count_text_field(rows: list[dict[str, Any]], field_name: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            key = str(row.get(field_name, "") or "").strip()
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
        return counts

    @staticmethod
    def _build_unified_signal_rows(
        confirmations: list[dict[str, Any]],
        field_name: str,
        min_confirmations: int,
    ) -> list[dict[str, Any]]:
        bucket: dict[str, dict[str, Any]] = {}
        for item in confirmations:
            key = str(item.get(field_name, "") or "").strip()
            if not key:
                continue
            row = bucket.setdefault(
                key,
                {
                    "key": key,
                    "accepted_count": 0,
                    "deferred_count": 0,
                    "rejected_count": 0,
                    "total_confirmations": 0,
                    "implementation_status": "Implemented",
                },
            )
            row["total_confirmations"] += 1
            decision = item.get("decision", "")
            if decision == "accepted":
                row["accepted_count"] += 1
            elif decision == "deferred":
                row["deferred_count"] += 1
            elif decision == "rejected":
                row["rejected_count"] += 1
        rows: list[dict[str, Any]] = []
        for row in bucket.values():
            if row["total_confirmations"] < min_confirmations:
                continue
            acceptance_rate = row["accepted_count"] / row["total_confirmations"] if row["total_confirmations"] else 0.0
            rejection_rate = row["rejected_count"] / row["total_confirmations"] if row["total_confirmations"] else 0.0
            row["acceptance_rate"] = round(acceptance_rate, 4)
            row["rejection_rate"] = round(rejection_rate, 4)
            if acceptance_rate >= 0.7 and row["accepted_count"] >= 2:
                row["weight_signal"] = "promote"
                row["signal_reason"] = "Governance history shows repeated acceptance, so this key is a candidate for higher default priority."
            elif rejection_rate >= 0.5 and row["rejected_count"] >= 1:
                row["weight_signal"] = "downgrade_watch"
                row["signal_reason"] = "Governance history shows repeated rejection pressure, so this key should stay under downgrade watch."
            else:
                row["weight_signal"] = "observe"
                row["signal_reason"] = "Governance history is still mixed, so this key should remain observable rather than directly reweighted."
            rows.append(row)
        rows.sort(key=lambda item: (-item["acceptance_rate"], -item["total_confirmations"], item["key"]))
        return rows

    @staticmethod
    def _build_ranking_suggestions_from_signals(signal_rows: list[dict[str, Any]], dimension: str) -> list[dict[str, Any]]:
        suggestions: list[dict[str, Any]] = []
        for row in signal_rows:
            signal = str(row.get("weight_signal", "observe") or "observe")
            if signal == "observe":
                suggested_delta = 0
            elif signal == "promote":
                suggested_delta = min(15, 5 + int(row.get("accepted_count", 0)) * 2)
            else:
                suggested_delta = -min(15, 5 + int(row.get("rejected_count", 0)) * 3)
            suggestions.append(
                {
                    "dimension": dimension,
                    "key": row.get("key", ""),
                    "weight_signal": signal,
                    "suggested_weight_delta": suggested_delta,
                    "accepted_count": row.get("accepted_count", 0),
                    "deferred_count": row.get("deferred_count", 0),
                    "rejected_count": row.get("rejected_count", 0),
                    "total_confirmations": row.get("total_confirmations", 0),
                    "acceptance_rate": row.get("acceptance_rate", 0.0),
                    "reason": row.get("signal_reason", ""),
                    "implementation_status": "Implemented",
                }
            )
        suggestions.sort(
            key=lambda item: (-abs(int(item["suggested_weight_delta"])), -int(item["total_confirmations"]), item["key"])
        )
        return suggestions

    @staticmethod
    def _build_unified_suggestion_index(suggestions: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
        index: dict[tuple[str, str], dict[str, Any]] = {}
        for field_name, dimension in (
            ("source_view_suggestions", "source_view"),
            ("candidate_type_suggestions", "candidate_type"),
            ("queue_bucket_suggestions", "queue_bucket"),
        ):
            for item in suggestions.get(field_name, []):
                key = str(item.get("key", "") or "").strip()
                if not key:
                    continue
                index[(dimension, key)] = item
        return index

    @staticmethod
    def _summarize_legacy_action_candidates(confirmations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bucket: dict[tuple[str, str], dict[str, Any]] = {}
        for item in confirmations:
            key = (item["candidate_label"], item["candidate_type"])
            row = bucket.setdefault(
                key,
                {
                    "label": item["candidate_label"],
                    "candidate_type": item["candidate_type"],
                    "accepted_count": 0,
                    "rejected_count": 0,
                    "total_confirmations": 0,
                    "latest_outcome": "not_reviewed",
                    "latest_confirmed_at": "",
                    "implementation_status": "Implemented",
                },
            )
            row["total_confirmations"] += 1
            if item["accepted"]:
                row["accepted_count"] += 1
                row["latest_outcome"] = "accepted"
            else:
                row["rejected_count"] += 1
                row["latest_outcome"] = "rejected"
            row["latest_confirmed_at"] = item["created_at"]
        ranked = sorted(
            bucket.values(),
            key=lambda row: (-row["accepted_count"], -row["total_confirmations"], row["label"]),
        )
        for row in ranked:
            row["acceptance_rate"] = round((row["accepted_count"] / row["total_confirmations"]), 4) if row["total_confirmations"] else 0.0
        return ranked

    @staticmethod
    def _summarize_unified_memory_review_candidates(confirmations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bucket: dict[tuple[str, str, str], dict[str, Any]] = {}
        for item in confirmations:
            key = (item["source_view"], item["candidate_type"], item["label"])
            row = bucket.setdefault(
                key,
                {
                    "source_view": item["source_view"],
                    "candidate_type": item["candidate_type"],
                    "label": item["label"],
                    "accepted_count": 0,
                    "deferred_count": 0,
                    "rejected_count": 0,
                    "total_confirmations": 0,
                    "latest_decision": "not_reviewed",
                    "latest_confirmed_at": "",
                    "implementation_status": "Implemented",
                },
            )
            row["total_confirmations"] += 1
            decision = item["decision"]
            if decision == "accepted":
                row["accepted_count"] += 1
            elif decision == "deferred":
                row["deferred_count"] += 1
            elif decision == "rejected":
                row["rejected_count"] += 1
            row["latest_decision"] = decision
            row["latest_confirmed_at"] = item["created_at"]
        ranked = sorted(
            bucket.values(),
            key=lambda row: (-row["accepted_count"], -row["total_confirmations"], row["label"]),
        )
        for row in ranked:
            row["acceptance_rate"] = round((row["accepted_count"] / row["total_confirmations"]), 4) if row["total_confirmations"] else 0.0
        return ranked

    @staticmethod
    def _summarize_unified_memory_review_ranking_diff_candidates(confirmations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bucket: dict[tuple[str, str, str], dict[str, Any]] = {}
        for item in confirmations:
            key = (item["source_view"], item["candidate_type"], item["label"])
            row = bucket.setdefault(
                key,
                {
                    "source_view": item["source_view"],
                    "candidate_type": item["candidate_type"],
                    "label": item["label"],
                    "accepted_count": 0,
                    "deferred_count": 0,
                    "rejected_count": 0,
                    "total_confirmations": 0,
                    "latest_decision": "not_reviewed",
                    "latest_confirmed_at": "",
                    "latest_profile": "",
                    "latest_current_rank": 0,
                    "latest_suggested_rank": 0,
                    "latest_score_delta": 0.0,
                    "implementation_status": "Implemented",
                },
            )
            row["total_confirmations"] += 1
            decision = item["decision"]
            if decision == "accepted":
                row["accepted_count"] += 1
            elif decision == "deferred":
                row["deferred_count"] += 1
            elif decision == "rejected":
                row["rejected_count"] += 1
            row["latest_decision"] = decision
            row["latest_confirmed_at"] = item["created_at"]
            row["latest_profile"] = item["profile"]
            row["latest_current_rank"] = item["current_rank"]
            row["latest_suggested_rank"] = item["suggested_rank"]
            row["latest_score_delta"] = item["score_delta"]
        ranked = sorted(
            bucket.values(),
            key=lambda row: (-row["accepted_count"], -row["total_confirmations"], row["label"]),
        )
        for row in ranked:
            row["acceptance_rate"] = round((row["accepted_count"] / row["total_confirmations"]), 4) if row["total_confirmations"] else 0.0
        return ranked

    @staticmethod
    def _summarize_unified_memory_review_ranking_policy_approvals(approvals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bucket: dict[tuple[str, str, str], dict[str, Any]] = {}
        for item in approvals:
            key = (item["dimension"], item["key"], item["profile"])
            row = bucket.setdefault(
                key,
                {
                    "dimension": item["dimension"],
                    "key": item["key"],
                    "profile": item["profile"],
                    "accepted_count": 0,
                    "deferred_count": 0,
                    "rejected_count": 0,
                    "total_approvals": 0,
                    "latest_decision": "not_reviewed",
                    "latest_approved_at": "",
                    "latest_weight_signal": "",
                    "latest_suggested_weight_delta": 0,
                    "implementation_status": "Implemented",
                },
            )
            row["total_approvals"] += 1
            decision = item["decision"]
            if decision == "accepted":
                row["accepted_count"] += 1
            elif decision == "deferred":
                row["deferred_count"] += 1
            elif decision == "rejected":
                row["rejected_count"] += 1
            row["latest_decision"] = decision
            row["latest_approved_at"] = item["created_at"]
            row["latest_weight_signal"] = item["weight_signal"]
            row["latest_suggested_weight_delta"] = item["suggested_weight_delta"]
        ranked = sorted(
            bucket.values(),
            key=lambda row: (-row["accepted_count"], -row["total_approvals"], row["dimension"], row["key"]),
        )
        for row in ranked:
            row["acceptance_rate"] = round((row["accepted_count"] / row["total_approvals"]), 4) if row["total_approvals"] else 0.0
        return ranked

    @staticmethod
    def _summarize_unified_memory_review_ranking_policy_change_candidate_approvals(
        approvals: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        bucket: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for item in approvals:
            key = (item["dimension"], item["key"], item["profile"], item["change_bucket"])
            row = bucket.setdefault(
                key,
                {
                    "dimension": item["dimension"],
                    "key": item["key"],
                    "profile": item["profile"],
                    "change_bucket": item["change_bucket"],
                    "accepted_count": 0,
                    "deferred_count": 0,
                    "rejected_count": 0,
                    "total_approvals": 0,
                    "latest_decision": "not_reviewed",
                    "latest_approved_at": "",
                    "latest_weight_signal": "",
                    "latest_suggested_weight_delta": 0,
                    "implementation_status": "Implemented",
                },
            )
            row["total_approvals"] += 1
            decision = item["decision"]
            if decision == "accepted":
                row["accepted_count"] += 1
            elif decision == "deferred":
                row["deferred_count"] += 1
            elif decision == "rejected":
                row["rejected_count"] += 1
            row["latest_decision"] = decision
            row["latest_approved_at"] = item["created_at"]
            row["latest_weight_signal"] = item["weight_signal"]
            row["latest_suggested_weight_delta"] = item["suggested_weight_delta"]
        ranked = sorted(
            bucket.values(),
            key=lambda row: (-row["accepted_count"], -row["total_approvals"], row["dimension"], row["key"]),
        )
        for row in ranked:
            row["acceptance_rate"] = round((row["accepted_count"] / row["total_approvals"]), 4) if row["total_approvals"] else 0.0
        return ranked

    @staticmethod
    def _summarize_legacy_action_profiles(confirmations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bucket: dict[tuple[str, str], dict[str, Any]] = {}
        for item in confirmations:
            key = (item["left_profile"], item["right_profile"])
            row = bucket.setdefault(
                key,
                {
                    "profile_pair": f"{item['left_profile'] or 'unknown'} -> {item['right_profile'] or 'unknown'}",
                    "accepted_count": 0,
                    "rejected_count": 0,
                    "total_confirmations": 0,
                    "implementation_status": "Implemented",
                },
            )
            row["total_confirmations"] += 1
            if item["accepted"]:
                row["accepted_count"] += 1
            else:
                row["rejected_count"] += 1
        ranked = sorted(
            bucket.values(),
            key=lambda row: (-row["total_confirmations"], -row["accepted_count"], row["profile_pair"]),
        )
        for row in ranked:
            row["acceptance_rate"] = round((row["accepted_count"] / row["total_confirmations"]), 4) if row["total_confirmations"] else 0.0
        return ranked

    def _collect_lesson_improvement_pairs(
        self,
        learning_entries: list[dict[str, Any]],
    ) -> tuple[dict[tuple[str, str], int], dict[tuple[str, str], set[str]]]:
        pair_counts: dict[tuple[str, str], int] = {}
        pair_atom_index: dict[tuple[str, str], set[str]] = {}
        for entry in learning_entries:
            lessons = [self._normalize_lesson_text(text) for text in entry.get("lessons", []) if self._normalize_lesson_text(text)]
            improvements = [self._normalize_lesson_text(text) for text in entry.get("improvement_items", []) if self._normalize_lesson_text(text)]
            if not lessons or not improvements:
                continue
            atom_ids = {
                str(item) for item in (entry.get("target_ids", []) + [entry.get("source_record_id", "")])
                if str(item).startswith("atom_")
            }
            for lesson_text in lessons:
                for improvement_text in improvements:
                    key = (lesson_text, improvement_text)
                    pair_counts[key] = pair_counts.get(key, 0) + 1
                    pair_atom_index.setdefault(key, set()).update(atom_ids)
        return pair_counts, pair_atom_index

    @staticmethod
    def _classify_emerging_lesson(
        current_learning_count: int,
        current_apply_state: str,
        matching_atom_ids: list[str],
    ) -> dict[str, Any]:
        atom_count = len(set(matching_atom_ids))
        if current_learning_count <= 1 and current_apply_state == "not_in_learning_chain_writeback":
            return {
                "migration_status": "single_observation_noise",
                "migration_reason": "Only one learning entry has mentioned this lesson and it has not yet become a repeated writeback pattern.",
                "evidence_gap": {
                    "primary_gap": "single_observation",
                    "missing_repeat_count": True,
                    "missing_cross_atom_support": atom_count < 2,
                    "missing_writeback_confirmation": True,
                },
            }
        if current_learning_count >= 2 and atom_count >= 2 and current_apply_state in {"new_or_changed", "confirmed_only"}:
            return {
                "migration_status": "immediate_candidate",
                "migration_reason": "Repeated learning entries already formed a cross-atom writeback pattern, so this is a strong candidate for legacy lessons.",
                "evidence_gap": {
                    "primary_gap": "none",
                    "missing_repeat_count": False,
                    "missing_cross_atom_support": False,
                    "missing_writeback_confirmation": False,
                },
            }
        missing_repeat = current_learning_count < 2
        missing_cross_atom = atom_count < 2
        missing_writeback = current_apply_state not in {"new_or_changed", "confirmed_only"}
        return {
            "migration_status": "need_more_evidence",
            "migration_reason": "The lesson has appeared, but it still lacks enough repeated or cross-atom evidence for a stable legacy-memory update.",
            "evidence_gap": {
                "primary_gap": SuperBrainV01._primary_gap_label(
                    missing_repeat_count=missing_repeat,
                    missing_cross_atom_support=missing_cross_atom,
                    missing_writeback_confirmation=missing_writeback,
                ),
                "missing_repeat_count": missing_repeat,
                "missing_cross_atom_support": missing_cross_atom,
                "missing_writeback_confirmation": missing_writeback,
            },
        }

    @staticmethod
    def _classify_lesson_improvement_pair(
        pair_count: int,
        lesson_apply_state: str,
        improvement_apply_state: str,
        matching_atom_ids: list[str],
    ) -> dict[str, Any]:
        atom_count = len(set(matching_atom_ids))
        if pair_count >= 2 and atom_count >= 2 and lesson_apply_state in {"new_or_changed", "confirmed_only"} and improvement_apply_state in {"new_or_changed", "confirmed_only"}:
            return {
                "migration_status": "immediate_candidate",
                "migration_reason": "This lesson/improvement pair recurs across multiple learning entries and atoms, so it is a strong long-term correction pattern.",
                "evidence_gap": {
                    "primary_gap": "none",
                    "missing_repeat_count": False,
                    "missing_cross_atom_support": False,
                    "missing_writeback_confirmation": False,
                },
            }
        missing_repeat = pair_count < 2
        missing_cross_atom = atom_count < 2
        missing_writeback = lesson_apply_state not in {"new_or_changed", "confirmed_only"} or improvement_apply_state not in {"new_or_changed", "confirmed_only"}
        return {
            "migration_status": "need_more_evidence",
            "migration_reason": "This lesson/improvement pairing exists, but it still needs more repeated co-occurrence evidence before it should shape long-term memory defaults.",
            "evidence_gap": {
                "primary_gap": SuperBrainV01._primary_gap_label(
                    missing_repeat_count=missing_repeat,
                    missing_cross_atom_support=missing_cross_atom,
                    missing_writeback_confirmation=missing_writeback,
                ),
                "missing_repeat_count": missing_repeat,
                "missing_cross_atom_support": missing_cross_atom,
                "missing_writeback_confirmation": missing_writeback,
            },
        }

    @staticmethod
    def _primary_gap_label(
        missing_repeat_count: bool,
        missing_cross_atom_support: bool,
        missing_writeback_confirmation: bool,
    ) -> str:
        if missing_repeat_count:
            return "missing_repeat_count"
        if missing_cross_atom_support:
            return "missing_cross_atom_support"
        if missing_writeback_confirmation:
            return "missing_writeback_confirmation"
        return "none"

    @staticmethod
    def _build_audit_explanation(
        entity_type: str,
        label: str,
        evidence_gap: dict[str, Any],
    ) -> str:
        primary_gap = evidence_gap.get("primary_gap", "none")
        type_label = {
            "lesson": "教训",
            "improvement_item": "改进项",
            "lesson_improvement_pair": "教训-改进配对",
        }.get(entity_type, entity_type)
        if primary_gap == "none":
            return f"{type_label}“{label}”已具备重复、跨 atom 和 writeback 证据，可以视为较稳定的长期记忆候选。"
        if primary_gap == "single_observation":
            return f"{type_label}“{label}”目前只有单次观察，既缺少重复出现，也缺少 writeback 确认，暂时更像噪声。"
        reasons: list[str] = []
        if evidence_gap.get("missing_repeat_count"):
            reasons.append("重复次数还不够")
        if evidence_gap.get("missing_cross_atom_support"):
            reasons.append("跨 atom 支撑不足")
        if evidence_gap.get("missing_writeback_confirmation"):
            reasons.append("还没有形成 writeback 确认")
        reason_text = "、".join(reasons) if reasons else "证据仍然不足"
        return f"{type_label}“{label}”暂时还不适合进入长期记忆，当前主要缺口是：{reason_text}。"

    @staticmethod
    def _build_summary_audit_conclusion(summary: dict[str, Any]) -> dict[str, str]:
        pair_primary_gap = "当前没有需要补证据的教训-改进配对。"
        if summary.get("pair_gap_missing_repeat_count", 0) > 0:
            pair_primary_gap = "当前最主要的配对级缺口是重复次数不够，说明不少修正模式只出现过一次。"
        elif summary.get("pair_gap_missing_cross_atom_support_count", 0) > 0:
            pair_primary_gap = "当前最主要的配对级缺口是跨 atom 支撑不足，说明模式还没有跨多个知识点重复出现。"
        elif summary.get("pair_gap_missing_writeback_confirmation_count", 0) > 0:
            pair_primary_gap = "当前最主要的配对级缺口是缺少 writeback 确认，说明模式还没有进入稳定的记忆组织层。"
        lesson_primary_gap = SuperBrainV01._build_primary_gap_summary_line(
            prefix="lesson",
            summary=summary,
            empty_line="当前没有仍需补证据的 lessons。"
        )
        improvement_primary_gap = SuperBrainV01._build_primary_gap_summary_line(
            prefix="improvement",
            summary=summary,
            empty_line="当前没有仍需补证据的 improvement_items。"
        )

        lesson_line = (
            f"lessons 侧已有 {summary.get('emerging_immediate_candidate_count', 0)} 条立即候选，"
            f"{summary.get('emerging_need_more_evidence_count', 0)} 条仍需补证据，"
            f"{summary.get('emerging_single_noise_count', 0)} 条更像单次噪声。"
        )
        improvement_line = (
            f"improvement_items 侧已有 {summary.get('improvement_immediate_candidate_count', 0)} 条立即候选，"
            f"{summary.get('improvement_need_more_evidence_count', 0)} 条仍需补证据，"
            f"{summary.get('improvement_single_noise_count', 0)} 条更像单次噪声。"
        )
        pair_line = (
            f"lesson/improvement 配对中已有 {summary.get('pair_immediate_candidate_count', 0)} 组较稳定模式，"
            f"{summary.get('pair_need_more_evidence_count', 0)} 组仍需补证据。"
        )
        next_action = SuperBrainV01._build_next_action_recommendation(summary)
        top_gaps = SuperBrainV01._build_top_gaps(summary)
        action_recommendations = SuperBrainV01._build_action_recommendations(summary)
        candidate_focus = SuperBrainV01._build_candidate_focus_recommendation(summary)
        overall = f"{lesson_line}{improvement_line}{pair_line}{lesson_primary_gap}{improvement_primary_gap}{pair_primary_gap}{next_action}"
        return {
            "overall": overall,
            "lessons": lesson_line,
            "improvements": improvement_line,
            "pairs": pair_line,
            "lesson_primary_gap": lesson_primary_gap,
            "improvement_primary_gap": improvement_primary_gap,
            "pair_primary_gap": pair_primary_gap,
            "next_action": next_action,
            "top_gaps": top_gaps,
            "action_recommendations": action_recommendations,
            "candidate_focus": candidate_focus,
        }

    @staticmethod
    def _build_primary_gap_summary_line(prefix: str, summary: dict[str, Any], empty_line: str) -> str:
        repeat_count = int(summary.get(f"{prefix}_gap_missing_repeat_count", 0))
        cross_atom_count = int(summary.get(f"{prefix}_gap_missing_cross_atom_support_count", 0))
        writeback_count = int(summary.get(f"{prefix}_gap_missing_writeback_confirmation_count", 0))
        if repeat_count <= 0 and cross_atom_count <= 0 and writeback_count <= 0:
            return empty_line
        if repeat_count > 0:
            return f"当前 {prefix} 侧最主要的缺口是重复次数不够，涉及 {repeat_count} 条候选。"
        if cross_atom_count > 0:
            return f"当前 {prefix} 侧最主要的缺口是跨 atom 支撑不足，涉及 {cross_atom_count} 条候选。"
        return f"当前 {prefix} 侧最主要的缺口是缺少 writeback 确认，涉及 {writeback_count} 条候选。"

    @staticmethod
    def _build_next_action_recommendation(summary: dict[str, Any]) -> str:
        if int(summary.get("pair_gap_missing_repeat_count", 0)) > 0:
            return "下一步应优先继续观察重复出现的教训-改进配对，确认它们是否会在后续学习记录中再次出现。"
        if int(summary.get("pair_gap_missing_cross_atom_support_count", 0)) > 0:
            return "下一步应优先寻找更多跨 atom 的同类模式，确认这些修正经验是否能跨多个知识点复现。"
        if int(summary.get("pair_gap_missing_writeback_confirmation_count", 0)) > 0:
            return "下一步应优先推动这些模式进入 writeback 层，确认它们是否会稳定影响记忆组织。"
        if int(summary.get("lesson_gap_missing_repeat_count", 0)) > 0 or int(summary.get("improvement_gap_missing_repeat_count", 0)) > 0:
            return "下一步应优先补足 lessons 或 improvement_items 的重复观察，避免把单次现象过早写进长期记忆。"
        return "当前迁移审计没有明显的高优先级证据缺口，可以继续扩大样本或准备人工整理 legacy memory。"

    @staticmethod
    def _build_top_gaps(summary: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = [
            ("pair", "missing_repeat_count", int(summary.get("pair_gap_missing_repeat_count", 0)), "教训-改进配对的重复次数不足"),
            ("pair", "missing_cross_atom_support", int(summary.get("pair_gap_missing_cross_atom_support_count", 0)), "教训-改进配对缺少跨 atom 支撑"),
            ("pair", "missing_writeback_confirmation", int(summary.get("pair_gap_missing_writeback_confirmation_count", 0)), "教训-改进配对缺少 writeback 确认"),
            ("lesson", "missing_repeat_count", int(summary.get("lesson_gap_missing_repeat_count", 0)), "lesson 候选的重复次数不足"),
            ("lesson", "missing_cross_atom_support", int(summary.get("lesson_gap_missing_cross_atom_support_count", 0)), "lesson 候选缺少跨 atom 支撑"),
            ("lesson", "missing_writeback_confirmation", int(summary.get("lesson_gap_missing_writeback_confirmation_count", 0)), "lesson 候选缺少 writeback 确认"),
            ("improvement", "missing_repeat_count", int(summary.get("improvement_gap_missing_repeat_count", 0)), "improvement 候选的重复次数不足"),
            ("improvement", "missing_cross_atom_support", int(summary.get("improvement_gap_missing_cross_atom_support_count", 0)), "improvement 候选缺少跨 atom 支撑"),
            ("improvement", "missing_writeback_confirmation", int(summary.get("improvement_gap_missing_writeback_confirmation_count", 0)), "improvement 候选缺少 writeback 确认"),
        ]
        ranked = sorted(
            [item for item in candidates if item[2] > 0],
            key=lambda item: (-item[2], {"pair": 0, "lesson": 1, "improvement": 2}.get(item[0], 9), item[1]),
        )
        return [
            {
                "scope": scope,
                "gap_type": gap_type,
                "count": count,
                "summary": text,
            }
            for scope, gap_type, count, text in ranked[:3]
        ]

    @staticmethod
    def _build_action_recommendations(summary: dict[str, Any]) -> list[str]:
        actions: list[str] = []
        if int(summary.get("pair_gap_missing_repeat_count", 0)) > 0:
            actions.append("优先回看近期 learning entries，确认同一教训-改进配对是否会再次出现。")
        if int(summary.get("pair_gap_missing_cross_atom_support_count", 0)) > 0:
            actions.append("优先寻找跨不同 atom 的相同修正模式，验证它们不是单点偶发现象。")
        if int(summary.get("pair_gap_missing_writeback_confirmation_count", 0)) > 0:
            actions.append("优先执行或等待下一轮 learning writeback，确认这些模式是否会稳定进入记忆组织层。")
        if int(summary.get("lesson_gap_missing_repeat_count", 0)) > 0:
            actions.append("优先补足 lesson 候选的重复观察，再决定是否写入 legacy lessons。")
        if int(summary.get("improvement_gap_missing_repeat_count", 0)) > 0:
            actions.append("优先补足 improvement 候选的重复观察，避免过早固化单次修正动作。")
        if not actions:
            actions.append("当前没有明显高优先级缺口，可开始人工整理 legacy memory 或继续扩大样本。")
        return actions[:3]

    @staticmethod
    def _count_candidate_types(candidates: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in candidates:
            key = str(item.get("candidate_type", "unknown"))
            counts[key] = counts.get(key, 0) + 1
        return counts

    @staticmethod
    def _build_candidate_focus_recommendation(summary: dict[str, Any]) -> str:
        counts = summary.get("legacy_memory_candidate_type_counts", {})
        if not isinstance(counts, dict) or not counts:
            return "当前还没有可供人工整理的 legacy memory 候选。"
        top_gaps = summary.get("audit_conclusion", {}).get("top_gaps", [])
        label_map = {
            "legacy_lesson_confirmation": "优先确认旧 lessons 中已被新系统再次验证的教训",
            "new_lesson_candidate": "优先新增反复出现的新 lessons",
            "improvement_candidate": "优先沉淀重复出现的改进动作",
            "lesson_improvement_pair_candidate": "优先沉淀稳定出现的教训-改进配对模式",
        }
        focus_priority = [
            ("pair", "lesson_improvement_pair_candidate"),
            ("lesson", "legacy_lesson_confirmation"),
            ("lesson", "new_lesson_candidate"),
            ("improvement", "improvement_candidate"),
        ]
        if isinstance(top_gaps, list):
            top_scope = next(
                (
                    str(item.get("scope"))
                    for item in top_gaps
                    if isinstance(item, dict) and counts.get({
                        "pair": "lesson_improvement_pair_candidate",
                        "lesson": "legacy_lesson_confirmation",
                        "improvement": "improvement_candidate",
                    }.get(str(item.get("scope")), ""), 0)
                ),
                None,
            )
            scope_type_map = {
                "pair": "lesson_improvement_pair_candidate",
                "lesson": "legacy_lesson_confirmation",
                "improvement": "improvement_candidate",
            }
            prioritized_type = scope_type_map.get(top_scope or "")
            if prioritized_type:
                return f"{label_map[prioritized_type]}，当前这类候选共有 {int(counts.get(prioritized_type, 0))} 条。"
        top_type = next(
            (
                candidate_type
                for _scope, candidate_type in focus_priority
                if int(counts.get(candidate_type, 0)) > 0
            ),
            None,
        )
        if not top_type:
            ranked = sorted(counts.items(), key=lambda item: (-int(item[1]), item[0]))
            top_type, _top_count = ranked[0]
        top_count = int(counts.get(top_type, 0))
        focus = label_map.get(top_type, f"优先整理 {top_type}")
        return f"{focus}，当前这类候选共有 {top_count} 条。"

    @staticmethod
    def _build_legacy_memory_candidate_groups(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        group_specs = [
            {
                "key": "confirm_legacy_lessons",
                "candidate_type": "legacy_lesson_confirmation",
                "queue_rank": 1,
                "title": "优先确认旧 lessons",
                "why": "这些教训已经存在于旧长期记忆中，当前工作重点是确认它们是否仍然有效，避免重复造新条目。",
                "entry_rule": "旧 lessons 中已有同名教训，且新系统再次观察到它。",
                "manual_action": "人工确认 wording 是否仍合适；如需要，只更新旧条目的描述，不新增重复 lesson。",
                "group_membership_reason": "当前候选更像对既有长期记忆的再验证，而不是新知识新增。",
                "upgrade_condition": "如果后续 learning entries 显示旧 lesson 的表达已经无法覆盖新证据，可升级为需要人工改写旧 lesson 的高优先级修订任务。",
                "downgrade_condition": "如果后续样本不再重复出现，或被更高质量证据否定，可降级为仅保留历史记录、暂不调整旧 lesson。",
                "review_trigger": "当同名 lesson 的重复次数明显增加，或出现与旧 wording 冲突的新证据时重新审查。",
            },
            {
                "key": "promote_lesson_improvement_pairs",
                "candidate_type": "lesson_improvement_pair_candidate",
                "queue_rank": 2,
                "title": "优先沉淀教训-改进配对模式",
                "why": "成对的修正模式最接近可执行经验，适合优先进入长期记忆，支撑以后复盘和推理。",
                "entry_rule": "同一教训与改进动作在多个 learning entries 中稳定共现，并形成 writeback 或跨 atom 支撑。",
                "manual_action": "人工把这类候选整理成“问题 -> 修正动作”形式，便于后续决策和复盘直接引用。",
                "group_membership_reason": "当前候选已经不只是单独教训，而是形成了更接近决策模板的稳定修正模式。",
                "upgrade_condition": "如果后续继续跨更多 atom 复现，可升级为长期默认规则或复盘模板中的核心配对模式。",
                "downgrade_condition": "如果后续只剩单次共现、失去 writeback 支撑，或 lesson 与改进动作开始分离，可降级回单独的新 lesson / improvement 候选。",
                "review_trigger": "当 pair_count 增加、跨 atom 范围扩大，或 writeback 状态从 new_or_changed 转为 confirmed_only 时重新审查。",
            },
            {
                "key": "promote_new_lessons",
                "candidate_type": "new_lesson_candidate",
                "queue_rank": 3,
                "title": "优先新增新 lessons",
                "why": "这些是旧长期记忆里没有、但已经积累到足够证据的新教训。",
                "entry_rule": "新 lesson 至少经过重复观察，并形成较稳定的跨 atom 或 writeback 支撑。",
                "manual_action": "人工新增到 legacy lessons 候选区，避免与已有 lesson 语义重复。",
                "group_membership_reason": "当前候选已经满足新 lesson 的最小稳定证据，但还没有沉淀进旧长期记忆文件。",
                "upgrade_condition": "如果后续出现稳定的配套改进动作并持续共现，可升级为教训-改进配对模式优先整理。",
                "downgrade_condition": "如果后续重复次数回落、跨 atom 支撑消失，或发现只是已有旧 lesson 的改写，可降级为待观察或合并回旧 lesson 确认。",
                "review_trigger": "当同一 lesson 再次出现、形成配套 improvement，或被人工发现与旧 lesson 语义重叠时重新审查。",
            },
            {
                "key": "promote_improvement_actions",
                "candidate_type": "improvement_candidate",
                "queue_rank": 4,
                "title": "补充独立改进动作",
                "why": "这些动作值得保留，但通常最好和具体 lesson 或配对模式一起整理。",
                "entry_rule": "改进动作重复出现，且不只是一次性的临时修补。",
                "manual_action": "优先检查它是否能并入已有 lesson 或配对；只有在无法归并时才独立沉淀。",
                "group_membership_reason": "当前候选体现了重复出现的行动修正，但单独存放的长期价值低于 lesson 或配对模式。",
                "upgrade_condition": "如果后续能稳定绑定到某条 lesson，或形成高频共现配对，可升级为教训-改进配对模式或新 lesson 的配套动作。",
                "downgrade_condition": "如果后续发现它只是一次性 workaround，或长期无法关联到任何 lesson，可降级为待观察记录，不进入长期记忆默认层。",
                "review_trigger": "当改进动作再次出现、开始绑定明确 lesson，或被新反馈判定为临时修补时重新审查。",
            },
        ]
        grouped: dict[str, dict[str, Any]] = {}
        for spec in group_specs:
            items = [item for item in candidates if item.get("candidate_type") == spec["candidate_type"]]
            grouped[spec["key"]] = {
                "queue_rank": spec["queue_rank"],
                "title": spec["title"],
                "candidate_type": spec["candidate_type"],
                "candidate_count": len(items),
                "why": spec["why"],
                "entry_rule": spec["entry_rule"],
                "manual_action": spec["manual_action"],
                "group_membership_reason": spec["group_membership_reason"],
                "upgrade_condition": spec["upgrade_condition"],
                "downgrade_condition": spec["downgrade_condition"],
                "review_trigger": spec["review_trigger"],
                "items": items,
                "implementation_status": "Implemented",
            }
        return grouped

    @staticmethod
    def _build_legacy_memory_candidates(
        legacy_lessons: list[dict[str, Any]],
        emerging_learning_lessons: list[dict[str, Any]],
        emerging_improvement_items: list[dict[str, Any]],
        lesson_improvement_pairs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        type_rank = {
            "legacy_lesson_confirmation": 0,
            "lesson_improvement_pair_candidate": 1,
            "new_lesson_candidate": 2,
            "improvement_candidate": 3,
        }
        candidates: list[dict[str, Any]] = []

        for row in legacy_lessons:
            if row.get("mapping_status") not in {"mapped_new_or_changed", "mapped_confirmed_only"}:
                continue
            priority_score = 100 + int(row.get("current_learning_count", 0))
            candidates.append(
                {
                    "candidate_type": "legacy_lesson_confirmation",
                    "label": row.get("lesson_text", ""),
                    "priority_score": priority_score,
                    "priority_components": {
                        "type_rank": type_rank["legacy_lesson_confirmation"],
                        "evidence_count": int(row.get("current_learning_count", 0)),
                    },
                    "ranking_reason": "旧 lessons 中已存在，且被新系统再次确认，默认优先级最高。",
                    "rationale": f"旧 lessons 已存在该教训，且新系统已将其识别为 {row.get('mapping_status')}。",
                    "governance_signals": SuperBrainV01._build_candidate_governance_signals(
                        candidate_type="legacy_lesson_confirmation",
                        evidence_count=int(row.get("current_learning_count", 0)),
                        atom_count=len(set(row.get("matching_atom_ids", []))),
                        apply_states=[str(row.get("current_apply_state", "not_in_learning_chain_writeback"))],
                        mapping_status=str(row.get("mapping_status", "")),
                    ),
                    "implementation_status": "Implemented",
                }
            )

        for row in emerging_learning_lessons:
            if row.get("migration_status") != "immediate_candidate":
                continue
            priority_score = 80 + int(row.get("current_learning_count", 0))
            candidates.append(
                {
                    "candidate_type": "new_lesson_candidate",
                    "label": row.get("lesson_text", ""),
                    "priority_score": priority_score,
                    "priority_components": {
                        "type_rank": type_rank["new_lesson_candidate"],
                        "evidence_count": int(row.get("current_learning_count", 0)),
                    },
                    "ranking_reason": "新 lesson 已形成稳定证据，但优先级低于旧 lesson 确认与配对模式。",
                    "rationale": row.get("audit_explanation", ""),
                    "governance_signals": SuperBrainV01._build_candidate_governance_signals(
                        candidate_type="new_lesson_candidate",
                        evidence_count=int(row.get("current_learning_count", 0)),
                        atom_count=len(set(row.get("matching_atom_ids", []))),
                        apply_states=[str(row.get("current_apply_state", "not_in_learning_chain_writeback"))],
                        mapping_status=str(row.get("migration_status", "")),
                    ),
                    "implementation_status": "Implemented",
                }
            )

        for row in emerging_improvement_items:
            if row.get("migration_status") != "immediate_candidate":
                continue
            priority_score = 60 + int(row.get("current_learning_count", 0))
            candidates.append(
                {
                    "candidate_type": "improvement_candidate",
                    "label": row.get("improvement_item_text", ""),
                    "priority_score": priority_score,
                    "priority_components": {
                        "type_rank": type_rank["improvement_candidate"],
                        "evidence_count": int(row.get("current_learning_count", 0)),
                    },
                    "ranking_reason": "改进动作值得沉淀，但通常需要结合 lesson 或配对模式一起整理。",
                    "rationale": row.get("audit_explanation", ""),
                    "governance_signals": SuperBrainV01._build_candidate_governance_signals(
                        candidate_type="improvement_candidate",
                        evidence_count=int(row.get("current_learning_count", 0)),
                        atom_count=len(set(row.get("matching_atom_ids", []))),
                        apply_states=[str(row.get("current_apply_state", "not_in_learning_chain_writeback"))],
                        mapping_status=str(row.get("migration_status", "")),
                    ),
                    "implementation_status": "Implemented",
                }
            )

        for row in lesson_improvement_pairs:
            if row.get("migration_status") != "immediate_candidate":
                continue
            priority_score = 90 + int(row.get("pair_count", 0))
            candidates.append(
                {
                    "candidate_type": "lesson_improvement_pair_candidate",
                    "label": f"{row.get('lesson_text', '')} -> {row.get('improvement_item_text', '')}",
                    "priority_score": priority_score,
                    "priority_components": {
                        "type_rank": type_rank["lesson_improvement_pair_candidate"],
                        "evidence_count": int(row.get("pair_count", 0)),
                    },
                    "ranking_reason": "稳定配对模式比单独的新 lesson 或改进项更接近可执行经验，因此优先级更高。",
                    "rationale": row.get("audit_explanation", ""),
                    "governance_signals": SuperBrainV01._build_candidate_governance_signals(
                        candidate_type="lesson_improvement_pair_candidate",
                        evidence_count=int(row.get("pair_count", 0)),
                        atom_count=len(set(row.get("matching_atom_ids", []))),
                        apply_states=[
                            str(row.get("lesson_current_apply_state", "not_in_learning_chain_writeback")),
                            str(row.get("improvement_current_apply_state", "not_in_learning_chain_writeback")),
                        ],
                        mapping_status=str(row.get("migration_status", "")),
                    ),
                    "implementation_status": "Implemented",
                }
            )

        candidates.sort(
            key=lambda item: (
                int(item.get("priority_components", {}).get("type_rank", 99)),
                -int(item.get("priority_components", {}).get("evidence_count", 0)),
                item.get("label", ""),
            )
        )
        return candidates[:10]

    @staticmethod
    def _build_candidate_governance_signals(
        candidate_type: str,
        evidence_count: int,
        atom_count: int,
        apply_states: list[str],
        mapping_status: str,
    ) -> dict[str, Any]:
        normalized_states = [str(item or "not_in_learning_chain_writeback") for item in apply_states]
        writeback_confirmed = all(item == "confirmed_only" for item in normalized_states)
        writeback_present = all(item in {"new_or_changed", "confirmed_only"} for item in normalized_states)
        if candidate_type == "legacy_lesson_confirmation":
            upgrade = (
                "如果同名旧 lesson 持续重复出现，且现有 wording 已无法覆盖新样本，建议升级为高优先级修订任务。"
                if evidence_count >= 2
                else "如果后续再次出现同名旧 lesson，可升级为高优先级修订任务。"
            )
            downgrade = (
                "如果后续不再重复出现，且没有新增 writeback 信号，可降级为仅保留历史确认。"
                if not writeback_confirmed
                else "如果后续证据减少或被反证覆盖，可降级为仅保留历史确认。"
            )
            trigger = "当旧 lesson 再次出现，或 confirmed_only 状态被新证据打破时复核。"
        elif candidate_type == "lesson_improvement_pair_candidate":
            upgrade = (
                "如果 pair_count 继续增加并覆盖更多 atom，建议升级为长期默认规则候选。"
                if atom_count >= 2 and writeback_present
                else "如果后续形成跨 atom 且具备 writeback 支撑，建议升级为长期默认规则候选。"
            )
            downgrade = (
                "如果后续只剩单次共现，或 lesson / improvement 的 writeback 支撑消失，建议降级回单独候选。"
            )
            trigger = "当 pair_count 增加、跨 atom 范围扩大，或任一侧 writeback 状态变化时复核。"
        elif candidate_type == "new_lesson_candidate":
            upgrade = (
                "如果后续出现稳定配套 improvement 并持续共现，建议升级为教训-改进配对模式。"
            )
            downgrade = (
                "如果重复次数回落、跨 atom 支撑消失，或被识别为旧 lesson 改写，建议降级为待观察或并回旧 lesson。"
            )
            trigger = "当 lesson 再次出现、形成 improvement 配套，或语义上接近旧 lesson 时复核。"
        else:
            upgrade = (
                "如果后续稳定绑定到某条 lesson，或形成高频共现配对，建议升级为配对模式或新 lesson 配套动作。"
            )
            downgrade = (
                "如果长期无法关联到 lesson，或被判定为一次性 workaround，建议降级为待观察记录。"
            )
            trigger = "当改进动作再次出现、开始绑定 lesson，或被反馈判定为临时修补时复核。"
        return {
            "evidence_count": int(evidence_count),
            "atom_count": int(atom_count),
            "apply_states": normalized_states,
            "writeback_present": writeback_present,
            "writeback_confirmed": writeback_confirmed,
            "mapping_status": mapping_status,
            "upgrade_recommendation": upgrade,
            "downgrade_risk": downgrade,
            "next_review_trigger": trigger,
            "implementation_status": "Implemented",
        }

    @staticmethod
    def _resolve_legacy_memory_decision_weight_config(payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        raw_profile = payload.get("profile", "legacy-first")
        if isinstance(raw_profile, list):
            raw_profile = raw_profile[0] if raw_profile else "legacy-first"
        profile = str(raw_profile or "legacy-first")
        configs = {
            "legacy-first": {
                "profile": "legacy-first",
                "promote_type_weights": {
                    "legacy_lesson_confirmation": 40,
                    "lesson_improvement_pair_candidate": 35,
                    "new_lesson_candidate": 25,
                    "improvement_candidate": 15,
                },
                "evidence_unit_weight": 5,
                "writeback_present_bonus": 5,
                "writeback_confirmed_bonus": 5,
                "implementation_status": "Implemented",
            },
            "pair-first": {
                "profile": "pair-first",
                "promote_type_weights": {
                    "legacy_lesson_confirmation": 35,
                    "lesson_improvement_pair_candidate": 45,
                    "new_lesson_candidate": 25,
                    "improvement_candidate": 15,
                },
                "evidence_unit_weight": 5,
                "writeback_present_bonus": 5,
                "writeback_confirmed_bonus": 5,
                "implementation_status": "Implemented",
            },
            "balanced": {
                "profile": "balanced",
                "promote_type_weights": {
                    "legacy_lesson_confirmation": 38,
                    "lesson_improvement_pair_candidate": 38,
                    "new_lesson_candidate": 25,
                    "improvement_candidate": 15,
                },
                "evidence_unit_weight": 5,
                "writeback_present_bonus": 5,
                "writeback_confirmed_bonus": 5,
                "implementation_status": "Implemented",
            },
        }
        return configs.get(profile, configs["legacy-first"])

    @staticmethod
    def _build_legacy_memory_decision_view(candidates: list[dict[str, Any]], decision_weight_config: dict[str, Any]) -> dict[str, Any]:
        promote_now = sorted(
            candidates,
            key=lambda item: (
                -SuperBrainV01._candidate_promote_score(item, decision_weight_config),
                int(item.get("priority_components", {}).get("type_rank", 99)),
                item.get("label", ""),
            ),
        )[:3]
        watch_for_downgrade = sorted(
            candidates,
            key=lambda item: (
                -SuperBrainV01._candidate_watch_score(item),
                int(item.get("priority_components", {}).get("type_rank", 99)),
                item.get("label", ""),
            ),
        )[:3]
        return {
            "promote_now": [
                {
                    "label": item.get("label", ""),
                    "candidate_type": item.get("candidate_type", ""),
                    "action_score": SuperBrainV01._candidate_promote_score(item, decision_weight_config),
                    "score_explanation": SuperBrainV01._build_candidate_score_explanation(item, decision_weight_config),
                    "why_now": item.get("governance_signals", {}).get("upgrade_recommendation", ""),
                    "current_signal": item.get("ranking_reason", ""),
                    "implementation_status": "Implemented",
                }
                for item in promote_now
            ],
            "watch_for_downgrade": [
                {
                    "label": item.get("label", ""),
                    "candidate_type": item.get("candidate_type", ""),
                    "risk_score": SuperBrainV01._candidate_watch_score(item),
                    "risk_reason": item.get("governance_signals", {}).get("downgrade_risk", ""),
                    "next_review_trigger": item.get("governance_signals", {}).get("next_review_trigger", ""),
                    "implementation_status": "Implemented",
                }
                for item in watch_for_downgrade
            ],
            "summary": {
                "focus_now": (
                    f"当前最值得马上整理的是 {promote_now[0].get('label', '')}。"
                    if promote_now
                    else "当前还没有可直接整理的 legacy memory 候选。"
                ),
                "decision_weight_profile": decision_weight_config.get("profile", "legacy-first"),
                "profile_explanation": SuperBrainV01._build_decision_profile_explanation(promote_now, decision_weight_config),
                "highest_downgrade_risk": (
                    f"当前最该先观察降级风险的是 {watch_for_downgrade[0].get('label', '')}。"
                    if watch_for_downgrade
                    else "当前没有需要优先观察降级风险的 legacy memory 候选。"
                ),
                "implementation_status": "Implemented",
            },
            "decision_weight_config": decision_weight_config,
            "implementation_status": "Implemented",
        }

    @staticmethod
    def _build_candidate_score_explanation(candidate: dict[str, Any], decision_weight_config: dict[str, Any]) -> str:
        candidate_type = str(candidate.get("candidate_type", ""))
        governance = candidate.get("governance_signals", {})
        evidence_count = int(governance.get("evidence_count", candidate.get("priority_components", {}).get("evidence_count", 0)))
        type_bonus = int(decision_weight_config.get("promote_type_weights", {}).get(candidate_type, 0))
        profile = str(decision_weight_config.get("profile", "legacy-first"))
        parts = [
            f"profile={profile}",
            f"type_bonus={type_bonus}",
            f"evidence_count={evidence_count}",
        ]
        if governance.get("writeback_present"):
            parts.append(f"writeback_present_bonus={int(decision_weight_config.get('writeback_present_bonus', 5))}")
        if governance.get("writeback_confirmed"):
            parts.append(f"writeback_confirmed_bonus={int(decision_weight_config.get('writeback_confirmed_bonus', 5))}")
        return "；".join(parts)

    @staticmethod
    def _build_decision_profile_explanation(promote_now: list[dict[str, Any]], decision_weight_config: dict[str, Any]) -> str:
        profile = str(decision_weight_config.get("profile", "legacy-first"))
        if not promote_now:
            return f"当前 profile={profile}，但还没有足够候选可进入 promote-now 视图。"
        top_candidate = promote_now[0]
        candidate_type = str(top_candidate.get("candidate_type", ""))
        type_label = {
            "legacy_lesson_confirmation": "旧 lesson 再验证",
            "lesson_improvement_pair_candidate": "教训-改进配对模式",
            "new_lesson_candidate": "新 lesson",
            "improvement_candidate": "独立改进动作",
        }.get(candidate_type, candidate_type)
        if profile == "pair-first":
            return f"当前 profile=pair-first，会提高配对模式权重；因此本次由 {type_label} 排在最前。"
        if profile == "balanced":
            return f"当前 profile=balanced，会尽量拉平旧 lesson 与配对模式的基础权重；本次由 {type_label} 以综合分数领先。"
        return f"当前 profile=legacy-first，会优先保留旧 lesson 再验证的治理稳定性；因此本次由 {type_label} 排在最前。"

    @staticmethod
    def _build_profile_diff_reason(left_top: dict[str, Any], right_top: dict[str, Any], left_profile: str, right_profile: str) -> str:
        if not left_top and not right_top:
            return "两个 profile 当前都没有可进入 promote-now 的候选。"
        if left_top.get("label", "") == right_top.get("label", "") and left_top.get("candidate_type", "") == right_top.get("candidate_type", ""):
            return f"{left_profile} 与 {right_profile} 当前都把同一候选排在首位，说明这两个 profile 在当前样本上还没有拉开排序差异。"
        return (
            f"{left_profile} 当前把 {left_top.get('candidate_type', 'unknown')} 放在首位，"
            f"而 {right_profile} 当前把 {right_top.get('candidate_type', 'unknown')} 放在首位，"
            "说明 profile 权重配置已经影响了人工整理优先级。"
        )

    @staticmethod
    def _build_profile_rank_changes(left_items: list[dict[str, Any]], right_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        left_index = {
            (str(item.get("label", "")), str(item.get("candidate_type", ""))): idx + 1
            for idx, item in enumerate(left_items)
        }
        right_index = {
            (str(item.get("label", "")), str(item.get("candidate_type", ""))): idx + 1
            for idx, item in enumerate(right_items)
        }
        keys = list(dict.fromkeys(list(left_index.keys()) + list(right_index.keys())))
        changes: list[dict[str, Any]] = []
        for label, candidate_type in keys:
            left_rank = left_index.get((label, candidate_type))
            right_rank = right_index.get((label, candidate_type))
            changes.append(
                {
                    "label": label,
                    "candidate_type": candidate_type,
                    "left_rank": left_rank,
                    "right_rank": right_rank,
                    "rank_changed": left_rank != right_rank,
                    "implementation_status": "Implemented",
                }
            )
        changes.sort(
            key=lambda item: (
                not item["rank_changed"],
                item["left_rank"] or 99,
                item["right_rank"] or 99,
                item["label"],
            )
        )
        return changes[:3]

    @staticmethod
    def _build_profile_diff_actions(rank_changes: list[dict[str, Any]], left_profile: str, right_profile: str) -> dict[str, Any]:
        promote_earlier: list[dict[str, Any]] = []
        defer_or_watch: list[dict[str, Any]] = []
        for item in rank_changes:
            left_rank = item.get("left_rank")
            right_rank = item.get("right_rank")
            if left_rank is None and right_rank is None:
                continue
            if left_rank is None or (right_rank is not None and left_rank is not None and right_rank < left_rank):
                promote_earlier.append(
                    {
                        "label": item.get("label", ""),
                        "candidate_type": item.get("candidate_type", ""),
                        "action": f"相对 {left_profile}，在 {right_profile} 下建议提前整理。",
                        "implementation_status": "Implemented",
                    }
                )
            elif right_rank is None or (left_rank is not None and right_rank is not None and right_rank > left_rank):
                defer_or_watch.append(
                    {
                        "label": item.get("label", ""),
                        "candidate_type": item.get("candidate_type", ""),
                        "action": f"相对 {left_profile}，在 {right_profile} 下建议后移观察。",
                        "implementation_status": "Implemented",
                    }
                )
        return {
            "promote_earlier": promote_earlier[:3],
            "defer_or_watch": defer_or_watch[:3],
            "summary": {
                "promote_count": len(promote_earlier),
                "defer_count": len(defer_or_watch),
                "implementation_status": "Implemented",
            },
            "implementation_status": "Implemented",
        }

    @staticmethod
    def _candidate_promote_score(candidate: dict[str, Any], decision_weight_config: dict[str, Any]) -> int:
        candidate_type = str(candidate.get("candidate_type", ""))
        governance = candidate.get("governance_signals", {})
        evidence_count = int(governance.get("evidence_count", candidate.get("priority_components", {}).get("evidence_count", 0)))
        type_bonus = int(decision_weight_config.get("promote_type_weights", {}).get(candidate_type, 0))
        score = type_bonus + evidence_count * int(decision_weight_config.get("evidence_unit_weight", 5))
        if governance.get("writeback_present"):
            score += int(decision_weight_config.get("writeback_present_bonus", 5))
        if governance.get("writeback_confirmed"):
            score += int(decision_weight_config.get("writeback_confirmed_bonus", 5))
        return score

    @staticmethod
    def _candidate_watch_score(candidate: dict[str, Any]) -> int:
        candidate_type = str(candidate.get("candidate_type", ""))
        governance = candidate.get("governance_signals", {})
        type_risk = {
            "improvement_candidate": 40,
            "new_lesson_candidate": 30,
            "lesson_improvement_pair_candidate": 20,
            "legacy_lesson_confirmation": 10,
        }.get(candidate_type, 0)
        score = type_risk
        if not governance.get("writeback_confirmed"):
            score += 10
        if int(governance.get("atom_count", 0)) < 2:
            score += 15
        return score

    def _load_writeback_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        if snapshot_id:
            snapshot = self.store.get("writeback_snapshots", snapshot_id)
            if not snapshot:
                raise ValueError(f"writeback snapshot not found: {snapshot_id}")
            return snapshot
        snapshots = self.store.list_records("writeback_snapshots", limit=1)
        if not snapshots:
            raise ValueError("no writeback snapshot available; capture one first")
        return snapshots[0]
