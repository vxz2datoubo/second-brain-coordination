"""Decision, forecast, review, feedback and learning workflows."""

from __future__ import annotations

from typing import Any

from .contracts import DecisionRecord, FeedbackRecord, ForecastRecord, LearningEntry, ReasoningTrace, RelationEdge, ReviewRecord, clamp, new_id, to_dict
from .evolution import EvolutionManager
from .governance import GovernancePolicy
from .reasoning import BiasDetector
from .storage import BrainStore


class DecisionManager:
    def __init__(self, store: BrainStore, evolution: EvolutionManager):
        self.store = store
        self.evolution = evolution
        self.bias = BiasDetector()
        self.policy = GovernancePolicy()

    def create_decision(
        self,
        decision_type: str,
        question: str,
        context: dict[str, Any] | None = None,
        options: list[str] | None = None,
        chosen: str = "",
        evidence_ids: list[str] | None = None,
        counter_evidence_ids: list[str] | None = None,
        confidence: float = 0.5,
        rationale: str = "",
        action: str = "",
        skip_trade_gate: bool = False,
    ) -> dict[str, Any]:
        context = context or {}
        evidence_ids = evidence_ids or []
        counter_evidence_ids = counter_evidence_ids or []
        bias_text = " ".join([question, rationale, " ".join(map(str, options or [])), str(context)])
        bias_check = self.bias.check(bias_text)
        approval = self.policy.assess_action(action or decision_type, context)
        self.store.save("risk_approvals", approval)
        warnings = list(bias_check.warnings)
        if approval.requires_approval and not approval.approved:
            warnings.append("requires_human_approval")
        if decision_type in {"trade", "buy", "sell"} and not skip_trade_gate:
            gate = self.policy.trading_gate({**context, "confidence": confidence})
            action = gate["action"]
            warnings.extend(gate["warnings"])
        record = DecisionRecord(
            decision_type=decision_type,
            question=question,
            context=context,
            options=options or ["trade", "wait", "no_trade"] if decision_type in {"trade", "buy", "sell"} else (options or []),
            chosen=chosen or action or "wait",
            action=action or chosen or "wait",
            evidence_ids=evidence_ids,
            counter_evidence_ids=counter_evidence_ids,
            confidence=confidence,
            rationale=rationale,
            warnings=sorted(set(warnings)),
            risk_level=max([bias_check.risk_level, approval.risk_level], key=["low", "medium", "high"].index),
            approval_id=approval.id,
            metadata={"implementation_status": "Implemented"},
        )
        self.store.save("decisions", record)
        return {"decision": to_dict(record), "approval": to_dict(approval)}

    def create_forecast(
        self,
        question: str,
        horizon: str,
        probability: float,
        scenarios: list[dict[str, Any]] | None = None,
        evidence_ids: list[str] | None = None,
        counter_evidence_ids: list[str] | None = None,
        confidence: float = 0.5,
        triggers: list[str] | None = None,
        invalidation_conditions: list[str] | None = None,
        risk_exposure: str = "",
        review_at: str = "",
    ) -> dict[str, Any]:
        record = ForecastRecord(
            question=question,
            horizon=horizon,
            probability=probability,
            scenarios=scenarios or [],
            evidence_ids=evidence_ids or [],
            counter_evidence_ids=counter_evidence_ids or [],
            confidence=confidence,
            triggers=triggers or [],
            invalidation_conditions=invalidation_conditions or [],
            risk_exposure=risk_exposure,
            review_at=review_at,
            metadata={"implementation_status": "Implemented"},
        )
        self.store.save("forecasts", record)
        return {"forecast": to_dict(record)}

    def create_reasoning_trace(
        self,
        question: str,
        trace_type: str = "analysis",
        steps: list[dict[str, Any]] | None = None,
        evidence_ids: list[str] | None = None,
        counter_evidence_ids: list[str] | None = None,
        conclusion: str = "",
        confidence: float = 0.5,
        uncertainty: str = "",
        next_action: str = "wait",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        steps = steps or []
        evidence_ids = evidence_ids or []
        counter_evidence_ids = counter_evidence_ids or []
        metadata = metadata or {}
        bias_text = " ".join([question, conclusion, uncertainty, str(steps)])
        bias_check = self.bias.check(bias_text)
        trace = ReasoningTrace(
            question=question,
            trace_type=trace_type,
            steps=steps,
            evidence_ids=evidence_ids,
            counter_evidence_ids=counter_evidence_ids,
            conclusion=conclusion,
            confidence=confidence,
            uncertainty=uncertainty,
            next_action=next_action,
            metadata={
                "implementation_status": "Implemented",
                "bias_warnings": bias_check.warnings,
                **metadata,
            },
        )
        self.store.save("reasoning_traces", trace)
        learning = self._record_learning_entry(
            entry_type="reasoning_trace",
            target_type="reasoning_trace",
            target_ids=[trace.id],
            source_record_id=trace.id,
            summary=conclusion or question,
            evidence_ids=evidence_ids,
            counter_evidence_ids=counter_evidence_ids,
            lessons=[],
            improvement_items=[],
            confidence_delta=0.0,
            metadata={
                "implementation_status": "Implemented",
                "trace_type": trace_type,
                "next_action": next_action,
                "uncertainty": uncertainty,
            },
            evolution_trigger="reasoning_trace_learning",
            observation=conclusion or uncertainty or question,
            proposed_update="Captured reasoning trace for later review, retrieval and pattern analysis.",
            applied=True,
            metrics={
                "trace_step_count": len(steps),
                "confidence": trace.confidence,
            },
        )
        return {
            "reasoning_trace": to_dict(trace),
            "learning_entry": to_dict(learning["learning_entry"]),
            "evolution_log": to_dict(learning["evolution_log"]),
        }

    def review(
        self,
        target_type: str,
        target_id: str,
        actual_outcome: str,
        actual_score: float | None = None,
        notes: str = "",
        lessons: list[str] | None = None,
    ) -> dict[str, Any]:
        metrics: dict[str, Any] = {}
        if target_type == "forecast":
            forecast = self.store.get("forecasts", target_id)
            if not forecast:
                raise ValueError("forecast not found")
            if actual_score is not None:
                brier = (float(forecast["probability"]) - float(actual_score)) ** 2
                forecast["actual_score"] = float(actual_score)
                forecast["brier_score"] = round(brier, 6)
                forecast["outcome"] = actual_outcome
                metrics["brier_score"] = forecast["brier_score"]
                self.store.update_data("forecasts", target_id, forecast)
        elif target_type == "decision":
            decision = self.store.get("decisions", target_id)
            if not decision:
                raise ValueError("decision not found")
            decision["outcome"] = actual_outcome
            self.store.update_data("decisions", target_id, decision)
        else:
            raise ValueError("target_type must be decision or forecast")
        review = ReviewRecord(
            target_type=target_type,
            target_id=target_id,
            actual_outcome=actual_outcome,
            actual_score=actual_score,
            notes=notes,
            metrics=metrics,
            lessons=lessons or [],
        )
        self.store.save("reviews", review)
        learning = self._record_learning_entry(
            entry_type="review",
            target_type=target_type,
            target_ids=[target_id],
            source_record_id=review.id,
            summary=notes or actual_outcome,
            evidence_ids=[],
            counter_evidence_ids=[],
            lessons=review.lessons,
            improvement_items=review.lessons,
            confidence_delta=0.0,
            metadata={
                "implementation_status": "Implemented",
                "review_id": review.id,
                "actual_outcome": actual_outcome,
            },
            evolution_trigger=f"{target_type}_review",
            observation=notes or actual_outcome,
            proposed_update="Update related rules or confidence if repeated error appears.",
            applied=False,
            metrics=metrics,
        )
        return {
            "review": to_dict(review),
            "learning_entry": to_dict(learning["learning_entry"]),
            "evolution_log": to_dict(learning["evolution_log"]),
        }

    def submit_feedback(
        self,
        target_type: str,
        target_ids: list[str],
        feedback_text: str = "",
        tags_to_add: list[str] | None = None,
        tags_to_remove: list[str] | None = None,
        confidence_delta: float = 0.0,
        related_atom_ids: list[str] | None = None,
        support_ids: list[str] | None = None,
        refute_ids: list[str] | None = None,
        improvement_items: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if target_type not in {"atom", "decision", "forecast", "evidence"}:
            raise ValueError("v0.1 feedback supports target_type in {'atom','decision','forecast','evidence'} only")
        tags_to_add = tags_to_add or []
        tags_to_remove = tags_to_remove or []
        related_atom_ids = related_atom_ids or []
        support_ids = support_ids or []
        refute_ids = refute_ids or []
        improvement_items = improvement_items or []
        metadata = metadata or {}
        feedback = FeedbackRecord(
            target_type=target_type,
            target_ids=target_ids,
            feedback_text=feedback_text,
            tags_to_add=tags_to_add,
            tags_to_remove=tags_to_remove,
            confidence_delta=confidence_delta,
            related_atom_ids=related_atom_ids,
            support_ids=support_ids,
            refute_ids=refute_ids,
            improvement_items=improvement_items,
            metadata={"implementation_status": "Implemented", **metadata},
        )
        self.store.save("feedback_records", feedback)

        updated_targets: list[dict[str, Any]] = []
        created_relations: list[dict[str, Any]] = []
        for target_id in target_ids:
            if target_type == "atom":
                updated_targets.append(
                    self._apply_atom_feedback(
                        target_id=target_id,
                        feedback=feedback,
                        tags_to_add=tags_to_add,
                        tags_to_remove=tags_to_remove,
                        confidence_delta=confidence_delta,
                        related_atom_ids=related_atom_ids,
                        improvement_items=improvement_items,
                        created_relations=created_relations,
                    )
                )
            elif target_type == "decision":
                updated_targets.append(
                    self._apply_generic_feedback(
                        table="decisions",
                        target_id=target_id,
                        feedback=feedback,
                        confidence_delta=confidence_delta,
                        tags_to_add=tags_to_add,
                        tags_to_remove=tags_to_remove,
                        improvement_items=improvement_items,
                    )
                )
            elif target_type == "forecast":
                updated_targets.append(
                    self._apply_generic_feedback(
                        table="forecasts",
                        target_id=target_id,
                        feedback=feedback,
                        confidence_delta=confidence_delta,
                        tags_to_add=tags_to_add,
                        tags_to_remove=tags_to_remove,
                        improvement_items=improvement_items,
                    )
                )
            elif target_type == "evidence":
                updated_targets.append(
                    self._apply_evidence_feedback(
                        target_id=target_id,
                        feedback=feedback,
                        confidence_delta=confidence_delta,
                        support_ids=support_ids,
                        refute_ids=refute_ids,
                        improvement_items=improvement_items,
                    )
                )

        learning = self._record_learning_entry(
            entry_type="feedback",
            target_type=target_type,
            target_ids=target_ids,
            source_record_id=feedback.id,
            summary=feedback_text or "feedback applied",
            evidence_ids=support_ids,
            counter_evidence_ids=refute_ids,
            lessons=[],
            improvement_items=improvement_items,
            confidence_delta=confidence_delta,
            metadata={
                "implementation_status": "Implemented",
                "feedback_id": feedback.id,
                "related_atom_ids": related_atom_ids,
                "tags_to_add": tags_to_add,
                "tags_to_remove": tags_to_remove,
            },
            evolution_trigger="user_feedback",
            observation=feedback_text or "feedback applied",
            proposed_update="Applied direct user feedback to atom tags, confidence, relations and improvement items.",
            applied=True,
            metrics={
                "target_type": target_type,
                "updated_target_count": len(updated_targets),
                "created_relation_count": len(created_relations),
                "confidence_delta": confidence_delta,
            },
        )
        return {
            "feedback": to_dict(feedback),
            "updated_targets": updated_targets,
            "created_relations": created_relations,
            "learning_entry": to_dict(learning["learning_entry"]),
            "evolution_log": to_dict(learning["evolution_log"]),
        }

    def create_learning_entry(
        self,
        entry_type: str,
        target_type: str,
        target_ids: list[str],
        summary: str = "",
        source_record_id: str = "",
        evidence_ids: list[str] | None = None,
        counter_evidence_ids: list[str] | None = None,
        lessons: list[str] | None = None,
        improvement_items: list[str] | None = None,
        confidence_delta: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        evolution_trigger = entry_type if entry_type.endswith("_learning") else f"{entry_type}_learning"
        learning = self._record_learning_entry(
            entry_type=entry_type,
            target_type=target_type,
            target_ids=target_ids,
            source_record_id=source_record_id,
            summary=summary,
            evidence_ids=evidence_ids or [],
            counter_evidence_ids=counter_evidence_ids or [],
            lessons=lessons or [],
            improvement_items=improvement_items or [],
            confidence_delta=confidence_delta,
            metadata={"implementation_status": "Implemented", **(metadata or {})},
            evolution_trigger=evolution_trigger,
            observation=summary or entry_type,
            proposed_update="Recorded a reusable learning entry for later adaptation and retrieval.",
            applied=True,
            metrics={
                "target_count": len(target_ids),
                "confidence_delta": confidence_delta,
            },
        )
        return {
            "learning_entry": to_dict(learning["learning_entry"]),
            "evolution_log": to_dict(learning["evolution_log"]),
        }

    def _record_learning_entry(
        self,
        entry_type: str,
        target_type: str,
        target_ids: list[str],
        source_record_id: str,
        summary: str,
        evidence_ids: list[str],
        counter_evidence_ids: list[str],
        lessons: list[str],
        improvement_items: list[str],
        confidence_delta: float,
        metadata: dict[str, Any],
        evolution_trigger: str,
        observation: str,
        proposed_update: str,
        applied: bool,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry = LearningEntry(
            entry_type=entry_type,
            target_type=target_type,
            target_ids=target_ids,
            source_record_id=source_record_id,
            summary=summary,
            evidence_ids=evidence_ids,
            counter_evidence_ids=counter_evidence_ids,
            lessons=lessons,
            improvement_items=improvement_items,
            confidence_delta=confidence_delta,
            metadata=metadata,
        )
        self.store.save("learning_entries", entry)
        evo = self.evolution.record(
            trigger=evolution_trigger,
            observation=observation,
            change_type="learning_entry",
            affected_ids=[item for item in target_ids + [entry.id, source_record_id] if item],
            proposed_update=proposed_update,
            applied=applied,
            metrics=metrics or {},
        )
        return {"learning_entry": entry, "evolution_log": evo}

    def _append_feedback_metadata(
        self,
        target: dict[str, Any],
        feedback: FeedbackRecord,
        confidence_delta: float,
        improvement_items: list[str],
        tags_to_add: list[str] | None = None,
        tags_to_remove: list[str] | None = None,
    ) -> dict[str, Any]:
        target.setdefault("metadata", {})
        improvement_log = target["metadata"].setdefault("improvement_items", [])
        for item in improvement_items:
            if item and item not in improvement_log:
                improvement_log.append(item)
        feedback_log = target["metadata"].setdefault("feedback_log", [])
        feedback_log.append(
            {
                "feedback_id": feedback.id,
                "text": feedback.feedback_text,
                "confidence_delta": confidence_delta,
                "target_type": feedback.target_type,
            }
        )
        if tags_to_add or tags_to_remove:
            tag_state = target["metadata"].setdefault("feedback_tags", [])
            tag_set = set(tag_state)
            tag_set.update(t for t in (tags_to_add or []) if t)
            tag_set.difference_update(t for t in (tags_to_remove or []) if t)
            target["metadata"]["feedback_tags"] = sorted(tag_set)
        return target

    def _apply_atom_feedback(
        self,
        target_id: str,
        feedback: FeedbackRecord,
        tags_to_add: list[str],
        tags_to_remove: list[str],
        confidence_delta: float,
        related_atom_ids: list[str],
        improvement_items: list[str],
        created_relations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        atom = self.store.get("atoms", target_id)
        if not atom:
            raise ValueError(f"atom not found: {target_id}")
        current_tags = set(atom.get("tags", []))
        current_tags.update(t for t in tags_to_add if t)
        current_tags.difference_update(t for t in tags_to_remove if t)
        atom["tags"] = sorted(current_tags)
        atom["confidence"] = clamp(float(atom.get("confidence", 0.5)) + float(confidence_delta))
        atom = self._append_feedback_metadata(atom, feedback, confidence_delta, improvement_items, tags_to_add, tags_to_remove)
        atom.setdefault("related_ids", [])
        for related_id in related_atom_ids:
            if related_id != target_id and related_id not in atom["related_ids"]:
                atom["related_ids"].append(related_id)
                relation = RelationEdge(
                    id=new_id("rel", f"{target_id}:{related_id}:{feedback.id}"),
                    source_atom_id=target_id,
                    target_atom_id=related_id,
                    relation_type="feedback_related",
                    confidence=0.6,
                    evidence_ids=atom.get("evidence_ids", []),
                    metadata={"feedback_id": feedback.id, "implementation_status": "Implemented"},
                )
                self.store.save("relations", relation)
                created_relations.append(to_dict(relation))
        return self.store.update_data("atoms", target_id, atom)

    def _apply_generic_feedback(
        self,
        table: str,
        target_id: str,
        feedback: FeedbackRecord,
        confidence_delta: float,
        tags_to_add: list[str],
        tags_to_remove: list[str],
        improvement_items: list[str],
    ) -> dict[str, Any]:
        target = self.store.get(table, target_id)
        if not target:
            raise ValueError(f"{table[:-1]} not found: {target_id}")
        target["confidence"] = clamp(float(target.get("confidence", 0.5)) + float(confidence_delta))
        target = self._append_feedback_metadata(target, feedback, confidence_delta, improvement_items, tags_to_add, tags_to_remove)
        return self.store.update_data(table, target_id, target)

    def _apply_evidence_feedback(
        self,
        target_id: str,
        feedback: FeedbackRecord,
        confidence_delta: float,
        support_ids: list[str],
        refute_ids: list[str],
        improvement_items: list[str],
    ) -> dict[str, Any]:
        evidence = self.store.get("evidence", target_id)
        if not evidence:
            raise ValueError(f"evidence not found: {target_id}")
        evidence["confidence"] = clamp(float(evidence.get("confidence", 0.6)) + float(confidence_delta))
        supports = set(evidence.get("supports", []))
        supports.update(s for s in support_ids if s)
        refutes = set(evidence.get("refutes", []))
        refutes.update(r for r in refute_ids if r)
        evidence["supports"] = sorted(supports)
        evidence["refutes"] = sorted(refutes)
        evidence = self._append_feedback_metadata(evidence, feedback, confidence_delta, improvement_items)
        return self.store.update_data("evidence", target_id, evidence)
