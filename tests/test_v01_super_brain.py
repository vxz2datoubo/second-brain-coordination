from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from brain_core import SuperBrainV01
from brain_core.contracts import DecisionRecord, EvidenceItem, FeedbackRecord, KnowledgeAtom, ReasoningTrace, SourceRecord
from brain_core.governance import GovernancePolicy


class ContractTests(unittest.TestCase):
    def test_high_confidence_decision_requires_evidence(self):
        with self.assertRaises(ValueError):
            DecisionRecord(question="Will this work?", confidence=0.9)

    def test_atom_requires_source_and_evidence(self):
        source = SourceRecord(source_type="manual", title="test")
        evidence = EvidenceItem(source_id=source.id, quote="atomic fact")
        atom = KnowledgeAtom(content="atomic fact", source_ids=[source.id], evidence_ids=[evidence.id])
        self.assertEqual(atom.source_ids, [source.id])
        self.assertEqual(atom.evidence_ids, [evidence.id])

    def test_feedback_requires_targets(self):
        with self.assertRaises(ValueError):
            FeedbackRecord(target_ids=[])

    def test_reasoning_trace_requires_question(self):
        with self.assertRaises(ValueError):
            ReasoningTrace(question="")


class SuperBrainFlowTests(unittest.TestCase):
    def make_brain(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return SuperBrainV01(Path(tmp.name))

    def test_ingest_search_keeps_traceability(self):
        brain = self.make_brain()
        result = brain.ingest_text({
            "title": "risk rule",
            "text": "交易决策必须包含止损、仓位和复盘。不要因为追高情绪直接买入。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        self.assertTrue(result["source"]["id"].startswith("src_"))
        self.assertGreaterEqual(len(result["atoms"]), 2)
        for atom in result["atoms"]:
            self.assertTrue(atom["source_ids"])
            self.assertTrue(atom["evidence_ids"])

        search = brain.search({"query": "止损 复盘", "top_k": 3})
        self.assertGreaterEqual(len(search["results"]), 1)
        self.assertEqual(search["vector"]["implementation_status"], "Mock")

    def test_decision_bias_and_approval_gate(self):
        brain = self.make_brain()
        ingested = brain.ingest_text({
            "text": "高风险交易需要先验证证据，实盘动作必须人工确认。",
            "source_type": "manual",
            "reliability": 0.9,
        })
        evidence_id = ingested["evidence"][0]["id"]
        decision = brain.create_decision({
            "decision_type": "trade",
            "question": "是否追高买入",
            "context": {"expected_edge_pct": 0.01, "cost_pct": 0.0015, "position_pct": 0.05},
            "evidence_ids": [evidence_id],
            "confidence": 0.7,
            "rationale": "不能错过，马上冲，但需要研究模式约束。",
        })
        data = decision["decision"]
        self.assertEqual(data["action"], "trade")
        self.assertIn("fomo", data["warnings"])
        self.assertFalse(decision["approval"]["metadata"]["live_trading_enabled"])

        high_risk = brain.create_decision({
            "decision_type": "system",
            "question": "Place a real order",
            "action": "live_trade",
            "confidence": 0.5,
        })
        self.assertTrue(high_risk["approval"]["requires_approval"])
        self.assertIn("requires_human_approval", high_risk["decision"]["warnings"])

    def test_forecast_review_brier_and_evolution_log(self):
        brain = self.make_brain()
        ingested = brain.ingest_text({
            "text": "预测必须记录概率、反证和失效条件。",
            "source_type": "manual",
            "reliability": 0.85,
        })
        evidence_id = ingested["evidence"][0]["id"]
        forecast = brain.create_forecast({
            "question": "MVP tests will pass",
            "horizon": "next run",
            "probability": 0.7,
            "confidence": 0.7,
            "evidence_ids": [evidence_id],
            "triggers": ["unit tests pass"],
            "invalidation_conditions": ["compile error"],
        })
        forecast_id = forecast["forecast"]["id"]
        review = brain.review({
            "target_type": "forecast",
            "target_id": forecast_id,
            "actual_outcome": "passed",
            "actual_score": 1.0,
            "notes": "The prediction resolved true.",
            "lessons": ["Keep Brier scoring in the loop."],
        })
        self.assertAlmostEqual(review["review"]["metrics"]["brier_score"], 0.09)
        logs = brain.evolution_log(5)
        self.assertEqual(len(logs["logs"]), 1)
        self.assertEqual(logs["logs"][0]["trigger"], "forecast_review")
        self.assertEqual(review["learning_entry"]["entry_type"], "review")
        self.assertEqual(brain.status()["counts"]["learning_entries"], 1)

    def test_status_reports_safety_and_legacy_read_only(self):
        brain = self.make_brain()
        status = brain.status()
        self.assertEqual(status["version"], "v0.1")
        self.assertFalse(status["safety"]["live_trading_enabled"])
        self.assertIn(status["module_status"]["vector_retrieval"], {"Mock"})
        self.assertTrue(status["announcement_board"].endswith("super-second-brain-v01-board.md"))

    def test_board_status_and_update(self):
        brain = self.make_brain()
        board = brain.board_status()
        self.assertEqual(board["status"], "进行中")
        self.assertTrue(Path(board["path"]).exists())
        self.assertNotIn("trading_status", board)
        self.assertNotIn("latest_trading_bulletin_state", board)
        updated = brain.board_update({
            "completed": ["a", "b"],
            "in_progress": ["c"],
            "next_step": "d",
            "summary": "board updated in test",
        })
        self.assertEqual(updated["completed"], ["a", "b"])
        board_after = brain.board_status()
        self.assertEqual(board_after["next_step"], "d")
        self.assertEqual(board_after["recent_events"][-1]["summary"], "board updated in test")

    def test_feedback_updates_atoms_relations_and_board(self):
        brain = self.make_brain()
        ingest_a = brain.ingest_text({
            "title": "atom a",
            "text": "交易系统需要可审计的反馈闭环。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        ingest_b = brain.ingest_text({
            "title": "atom b",
            "text": "知识原子之间需要可追踪关系。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        atom_a = ingest_a["atoms"][0]["id"]
        atom_b = ingest_b["atoms"][0]["id"]
        original_confidence = ingest_a["atoms"][0]["confidence"]

        result = brain.feedback({
            "target_type": "atom",
            "target_ids": [atom_a],
            "feedback_text": "这条应明确标为反馈学习，并补充审计标签。",
            "tags_to_add": ["反馈学习", "审计"],
            "confidence_delta": 0.15,
            "related_atom_ids": [atom_b],
            "improvement_items": ["增加明确的用户反馈入口"],
        })
        updated_atom = result["updated_targets"][0]
        self.assertIn("反馈学习", updated_atom["tags"])
        self.assertIn("审计", updated_atom["tags"])
        self.assertGreater(updated_atom["confidence"], original_confidence)
        self.assertIn(atom_b, updated_atom["related_ids"])
        self.assertEqual(result["created_relations"][0]["relation_type"], "feedback_related")
        self.assertEqual(result["evolution_log"]["trigger"], "user_feedback")
        self.assertEqual(result["learning_entry"]["entry_type"], "feedback")

        board = brain.board_status()
        self.assertEqual(board["recent_events"][-1]["type"], "feedback_applied")

    def test_feedback_updates_decision_forecast_and_evidence(self):
        brain = self.make_brain()
        ingested = brain.ingest_text({
            "title": "feedback targets",
            "text": "证据需要被支持或反驳，预测和决策也需要根据反馈更新。",
            "source_type": "manual",
            "reliability": 0.83,
        })
        evidence_id = ingested["evidence"][0]["id"]

        decision = brain.create_decision({
            "decision_type": "general",
            "question": "是否继续观察",
            "confidence": 0.4,
            "evidence_ids": [evidence_id],
            "rationale": "当前只做观察。",
        })["decision"]
        decision_feedback = brain.feedback({
            "target_type": "decision",
            "target_ids": [decision["id"]],
            "feedback_text": "这个决策需要更明确的风险注释。",
            "tags_to_add": ["风险复核"],
            "confidence_delta": 0.1,
            "improvement_items": ["补充风险说明"],
        })
        self.assertGreater(decision_feedback["updated_targets"][0]["confidence"], decision["confidence"])
        self.assertIn("风险复核", decision_feedback["updated_targets"][0]["metadata"]["feedback_tags"])

        forecast = brain.create_forecast({
            "question": "测试预测是否成立",
            "horizon": "tomorrow",
            "probability": 0.6,
            "confidence": 0.45,
            "evidence_ids": [evidence_id],
        })["forecast"]
        forecast_feedback = brain.feedback({
            "target_type": "forecast",
            "target_ids": [forecast["id"]],
            "feedback_text": "这个预测需要更高的不确定性说明。",
            "tags_to_add": ["不确定性"],
            "confidence_delta": -0.1,
            "improvement_items": ["补充失效条件"],
        })
        self.assertLess(forecast_feedback["updated_targets"][0]["confidence"], forecast["confidence"])
        self.assertIn("补充失效条件", forecast_feedback["updated_targets"][0]["metadata"]["improvement_items"])

        evidence_feedback = brain.feedback({
            "target_type": "evidence",
            "target_ids": [evidence_id],
            "feedback_text": "这条证据支持某个判断，也被另一条信息反驳。",
            "confidence_delta": 0.05,
            "support_ids": ["claim_a"],
            "refute_ids": ["claim_b"],
            "improvement_items": ["补充来源背景"],
        })
        updated_evidence = evidence_feedback["updated_targets"][0]
        self.assertIn("claim_a", updated_evidence["supports"])
        self.assertIn("claim_b", updated_evidence["refutes"])
        self.assertIn("补充来源背景", updated_evidence["metadata"]["improvement_items"])
        self.assertEqual(brain.status()["counts"]["learning_entries"], 3)

    def test_feedback_summary_exposes_feedback_shaping_signals(self):
        brain = self.make_brain()
        ingest_a = brain.ingest_text({
            "title": "summary atom a",
            "text": "反馈应该能被审计，而不是只留下静默状态变化。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        ingest_b = brain.ingest_text({
            "title": "summary atom b",
            "text": "相关原子之间要保留反馈驱动的关系线索。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        atom_a = ingest_a["atoms"][0]["id"]
        atom_b = ingest_b["atoms"][0]["id"]
        evidence_id = ingest_a["evidence"][0]["id"]

        brain.feedback({
            "target_type": "atom",
            "target_ids": [atom_a],
            "feedback_text": "这条原子需要增加审计与反馈学习标签。",
            "tags_to_add": ["反馈学习", "审计"],
            "confidence_delta": 0.15,
            "related_atom_ids": [atom_b],
            "improvement_items": ["增加反馈影响概览"],
        })
        brain.feedback({
            "target_type": "atom",
            "target_ids": [atom_a],
            "feedback_text": "第二次反馈继续强化审计视角。",
            "tags_to_add": ["审计"],
            "tags_to_remove": ["反馈学习"],
            "confidence_delta": -0.05,
            "improvement_items": ["补充反馈复盘摘要"],
        })
        brain.feedback({
            "target_type": "evidence",
            "target_ids": [evidence_id],
            "feedback_text": "证据还需要支持与反驳引用。",
            "confidence_delta": 0.1,
            "support_ids": ["claim_a"],
            "refute_ids": ["claim_b"],
            "improvement_items": ["补充证据对照表"],
        })

        filtered = brain.feedback_summary({"limit": 5, "target_type": "atom", "target_id": atom_a})
        self.assertEqual(filtered["summary"]["total_feedback_records"], 2)
        self.assertAlmostEqual(filtered["summary"]["net_confidence_delta"], 0.1, places=4)
        self.assertEqual(filtered["summary"]["related_atom_link_count"], 1)
        self.assertEqual(filtered["summary"]["positive_confidence_feedback_count"], 1)
        self.assertEqual(filtered["summary"]["negative_confidence_feedback_count"], 1)
        self.assertEqual(filtered["summary"]["top_tags_added"][0]["text"], "审计")
        self.assertEqual(filtered["summary"]["top_improvement_items"][0]["count"], 1)
        self.assertEqual(filtered["target_snapshot"]["target_id"], atom_a)
        self.assertEqual(filtered["target_snapshot"]["feedback_log_count"], 2)
        self.assertIn("审计", filtered["target_snapshot"]["tags"])
        self.assertNotIn("反馈学习", filtered["target_snapshot"]["tags"])
        self.assertIn(atom_b, filtered["target_snapshot"]["related_ids"])
        self.assertEqual(len(filtered["recent_feedback"]), 2)

        overall = brain.feedback_summary({"limit": 5})
        self.assertEqual(overall["summary"]["total_feedback_records"], 3)
        self.assertEqual(overall["summary"]["target_type_counts"]["atom"], 2)
        self.assertEqual(overall["summary"]["target_type_counts"]["evidence"], 1)
        self.assertEqual(overall["summary"]["support_link_count"], 1)
        self.assertEqual(overall["summary"]["refute_link_count"], 1)
        self.assertIsNone(overall["target_snapshot"])

    def test_feedback_memory_candidates_bridge_feedback_into_long_term_review_queue(self):
        brain = self.make_brain()
        ingest_a = brain.ingest_text({
            "title": "feedback candidate a",
            "text": "系统需要识别重复的反馈改进项。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        ingest_b = brain.ingest_text({
            "title": "feedback candidate b",
            "text": "另一个目标上也出现了相同的反馈模式。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        atom_a = ingest_a["atoms"][0]["id"]
        atom_b = ingest_b["atoms"][0]["id"]

        brain.feedback({
            "target_type": "atom",
            "target_ids": [atom_a],
            "feedback_text": "第一次要求补充反馈复盘摘要。",
            "tags_to_add": ["复盘"],
            "confidence_delta": 0.1,
            "improvement_items": ["补充反馈复盘摘要"],
        })
        brain.feedback({
            "target_type": "atom",
            "target_ids": [atom_b],
            "feedback_text": "第二次还是要求补充反馈复盘摘要。",
            "tags_to_add": ["复盘"],
            "confidence_delta": 0.05,
            "improvement_items": ["补充反馈复盘摘要"],
        })
        brain.feedback({
            "target_type": "atom",
            "target_ids": [atom_a],
            "feedback_text": "只出现一次的标签移除先不要长期化。",
            "tags_to_remove": ["临时标签"],
            "confidence_delta": -0.05,
            "improvement_items": ["观察一次性标签移除"],
        })

        candidates = brain.feedback_memory_candidates({"limit": 10, "min_count": 2})
        self.assertEqual(candidates["summary"]["implementation_status"], "Implemented")
        self.assertGreaterEqual(candidates["summary"]["immediate_candidate_count"], 2)
        improvement_candidate = next(
            item for item in candidates["candidates"]
            if item["pattern_type"] == "feedback_improvement_item" and item["text"] == "补充反馈复盘摘要"
        )
        self.assertEqual(improvement_candidate["migration_status"], "immediate_candidate")
        self.assertEqual(improvement_candidate["feedback_count"], 2)
        self.assertEqual(len(improvement_candidate["target_ids"]), 2)
        self.assertIn("learning_chains", improvement_candidate["suggested_route"])

        tag_add_candidate = next(
            item for item in candidates["candidates"]
            if item["pattern_type"] == "feedback_tag_add" and item["text"] == "复盘"
        )
        self.assertEqual(tag_add_candidate["migration_status"], "immediate_candidate")
        self.assertEqual(tag_add_candidate["target_type_counts"]["atom"], 2)

        tag_remove_candidate = next(
            item for item in candidates["candidates"]
            if item["pattern_type"] == "feedback_tag_remove" and item["text"] == "临时标签"
        )
        self.assertEqual(tag_remove_candidate["migration_status"], "single_observation_noise")
        self.assertIn("appeared only once", tag_remove_candidate["migration_reason"])
        self.assertIn("feedback_records -> feedback_memory_candidates", candidates["integration_note"]["current_route"])

    def test_unified_memory_review_queue_merges_legacy_feedback_and_learning_views(self):
        brain = self.make_brain()
        legacy_dir = brain.root / "second-brain"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "lessons.md").write_text("# 历史教训库\n\n教训: 风险说明要明确\n", encoding="utf-8")

        ingest_a = brain.ingest_text({
            "title": "unified queue a",
            "text": "风险说明要明确，并且反馈复盘摘要会反复出现。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        ingest_b = brain.ingest_text({
            "title": "unified queue b",
            "text": "第二个目标上也出现了相同的问题模式。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        atom_a = ingest_a["atoms"][0]["id"]
        atom_b = ingest_b["atoms"][0]["id"]
        evidence_a = ingest_a["evidence"][0]["id"]
        evidence_b = ingest_b["evidence"][0]["id"]

        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_a],
            "summary": "第一次发现风险说明不清楚。",
            "source_record_id": atom_a,
            "evidence_ids": [evidence_a],
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_b],
            "summary": "第二次还是缺少风险说明。",
            "source_record_id": atom_b,
            "evidence_ids": [evidence_b],
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.feedback({
            "target_type": "atom",
            "target_ids": [atom_a],
            "feedback_text": "第一次要求补充反馈复盘摘要。",
            "tags_to_add": ["复盘"],
            "confidence_delta": 0.1,
            "improvement_items": ["补充反馈复盘摘要"],
        })
        brain.feedback({
            "target_type": "atom",
            "target_ids": [atom_b],
            "feedback_text": "第二次还是要求补充反馈复盘摘要。",
            "tags_to_add": ["复盘"],
            "confidence_delta": 0.05,
            "improvement_items": ["补充反馈复盘摘要"],
        })
        brain.apply_learning_chains({"limit": 10, "min_count": 2})

        queue = brain.unified_memory_review_queue({"limit": 20, "min_count": 2, "profile": "legacy-first"})
        self.assertEqual(queue["summary"]["implementation_status"], "Implemented")
        self.assertEqual(queue["summary"]["profile"], "legacy-first")
        self.assertIn("legacy_memory_decision_view", queue["summary"]["source_view_counts"])
        self.assertIn("feedback_memory_candidates", queue["summary"]["source_view_counts"])
        self.assertIn("learning_chains", queue["summary"]["source_view_counts"])
        self.assertGreaterEqual(queue["summary"]["queue_bucket_counts"]["review_now"], 1)
        self.assertEqual(queue["items"][0]["queue_bucket"], "review_now")

        legacy_item = next(item for item in queue["items"] if item["source_view"] == "legacy_memory_decision_view")
        self.assertEqual(legacy_item["label"], "风险说明要明确")
        feedback_item = next(item for item in queue["items"] if item["source_view"] == "feedback_memory_candidates" and item["label"] == "补充反馈复盘摘要")
        self.assertEqual(feedback_item["queue_bucket"], "review_now")
        chain_item = next(item for item in queue["items"] if item["source_view"] == "learning_chains" and item["label"] == "补充风险说明")
        self.assertEqual(chain_item["candidate_type"], "improvement_chain")
        self.assertIn("human review", queue["integration_note"]["current_route"])

    def test_unified_memory_review_confirmation_writes_back_to_shared_learning_pipeline(self):
        brain = self.make_brain()
        queue_item = {
            "source_view": "feedback_memory_candidates",
            "candidate_type": "feedback_improvement_item",
            "label": "补充反馈复盘摘要",
            "queue_bucket": "review_now",
        }
        result = brain.confirm_unified_memory_review_item({
            **queue_item,
            "decision": "accepted",
            "profile": "legacy-first",
            "min_count": 2,
            "lessons": ["重复反馈改进项值得进入统一整理队列。"],
            "improvement_items": ["后续把统一队列确认结果接回调权逻辑。"],
        })
        self.assertEqual(result["learning_entry"]["target_type"], "unified_memory_candidate")
        self.assertEqual(result["learning_entry"]["entry_type"], "unified_memory_review_confirmation")
        self.assertEqual(result["learning_entry"]["metadata"]["source_view"], "feedback_memory_candidates")
        self.assertEqual(result["learning_entry"]["metadata"]["decision"], "accepted")
        self.assertEqual(result["learning_entry"]["metadata"]["queue_bucket"], "review_now")
        self.assertEqual(result["evolution_log"]["trigger"], "unified_memory_review_confirmation_learning")

        board = brain.board_status()
        self.assertEqual(board["recent_events"][-1]["type"], "unified_memory_review_confirmed")
        self.assertIn("补充反馈复盘摘要", board["recent_events"][-1]["summary"])

        brain.confirm_unified_memory_review_item({
            "source_view": "feedback_memory_candidates",
            "candidate_type": "feedback_improvement_item",
            "label": "补充反馈复盘摘要",
            "queue_bucket": "watchlist",
            "decision": "deferred",
        })
        brain.confirm_unified_memory_review_item({
            "source_view": "learning_chains",
            "candidate_type": "improvement_chain",
            "label": "补充风险说明",
            "queue_bucket": "review_now",
            "decision": "rejected",
        })
        summary = brain.unified_memory_review_summary({"limit": 5})
        self.assertEqual(summary["summary"]["total_confirmations"], 3)
        self.assertEqual(summary["summary"]["accepted_count"], 1)
        self.assertEqual(summary["summary"]["deferred_count"], 1)
        self.assertEqual(summary["summary"]["rejected_count"], 1)
        self.assertAlmostEqual(summary["summary"]["acceptance_rate"], 0.3333, places=4)
        self.assertEqual(summary["summary"]["source_view_counts"]["feedback_memory_candidates"], 2)
        self.assertEqual(summary["summary"]["candidate_type_counts"]["feedback_improvement_item"], 2)
        self.assertEqual(summary["summary"]["queue_bucket_counts"]["review_now"], 2)
        self.assertEqual(summary["summary"]["decision_counts"]["rejected"], 1)
        self.assertEqual(summary["top_accepted_candidates"][0]["label"], "补充反馈复盘摘要")
        self.assertEqual(summary["top_deferred_candidates"][0]["label"], "补充反馈复盘摘要")
        self.assertEqual(summary["top_rejected_candidates"][0]["label"], "补充风险说明")
        self.assertEqual(summary["implementation_status"], "Implemented")

        signals = brain.unified_memory_review_signals({"min_confirmations": 1})
        self.assertEqual(signals["summary"]["implementation_status"], "Implemented")
        self.assertGreaterEqual(signals["summary"]["source_view_signal_count"], 2)
        feedback_signal = next(item for item in signals["source_view_signals"] if item["key"] == "feedback_memory_candidates")
        self.assertEqual(feedback_signal["accepted_count"], 1)
        self.assertEqual(feedback_signal["deferred_count"], 1)
        self.assertEqual(feedback_signal["weight_signal"], "observe")
        learning_chain_signal = next(item for item in signals["source_view_signals"] if item["key"] == "learning_chains")
        self.assertEqual(learning_chain_signal["rejected_count"], 1)
        self.assertEqual(learning_chain_signal["weight_signal"], "downgrade_watch")
        feedback_candidate_signal = next(item for item in signals["candidate_type_signals"] if item["key"] == "feedback_improvement_item")
        self.assertEqual(feedback_candidate_signal["total_confirmations"], 2)
        review_now_signal = next(item for item in signals["queue_bucket_signals"] if item["key"] == "review_now")
        self.assertEqual(review_now_signal["accepted_count"], 1)
        self.assertIn("unified_memory_review_summary -> unified_memory_review_signals", signals["integration_note"]["current_route"])

        suggestions = brain.unified_memory_review_ranking_suggestions({"min_confirmations": 1, "profile": "legacy-first"})
        self.assertEqual(suggestions["summary"]["implementation_status"], "Implemented")
        self.assertEqual(suggestions["summary"]["profile"], "legacy-first")
        self.assertGreaterEqual(suggestions["summary"]["source_view_suggestion_count"], 2)
        feedback_suggestion = next(item for item in suggestions["source_view_suggestions"] if item["key"] == "feedback_memory_candidates")
        self.assertEqual(feedback_suggestion["weight_signal"], "observe")
        self.assertEqual(feedback_suggestion["suggested_weight_delta"], 0)
        learning_chain_suggestion = next(item for item in suggestions["source_view_suggestions"] if item["key"] == "learning_chains")
        self.assertEqual(learning_chain_suggestion["weight_signal"], "downgrade_watch")
        self.assertLess(learning_chain_suggestion["suggested_weight_delta"], 0)
        feedback_candidate_suggestion = next(item for item in suggestions["candidate_type_suggestions"] if item["key"] == "feedback_improvement_item")
        self.assertEqual(feedback_candidate_suggestion["total_confirmations"], 2)
        review_now_suggestion = next(item for item in suggestions["queue_bucket_suggestions"] if item["key"] == "review_now")
        self.assertEqual(review_now_suggestion["dimension"], "queue_bucket")
        self.assertIn("unified_memory_review_signals -> unified_memory_review_ranking_suggestions", suggestions["integration_note"]["current_route"])

        diff = brain.unified_memory_review_ranking_diff({"limit": 10, "min_confirmations": 1, "profile": "legacy-first"})
        self.assertEqual(diff["summary"]["implementation_status"], "Implemented")
        self.assertEqual(diff["summary"]["profile"], "legacy-first")
        self.assertGreaterEqual(diff["summary"]["total_candidates"], 1)
        changed_item = next(item for item in diff["items"] if item["source_view"] == "learning_chains")
        self.assertTrue(changed_item["rank_changed"])
        self.assertLess(changed_item["score_delta"], 0)
        self.assertTrue(any(part["dimension"] == "source_view" for part in changed_item["suggestion_parts"]))
        self.assertIn("unified_memory_review_queue + unified_memory_review_ranking_suggestions", diff["integration_note"]["current_route"])

        diff_confirm = brain.confirm_unified_memory_review_ranking_diff_item({
            "label": changed_item["label"],
            "source_view": changed_item["source_view"],
            "candidate_type": changed_item["candidate_type"],
            "decision": "accepted",
            "profile": "legacy-first",
            "current_rank": changed_item["current_rank"],
            "suggested_rank": changed_item["suggested_rank"],
            "score_delta": changed_item["score_delta"],
            "lessons": ["排序变化建议需要进入统一治理历史。"],
            "improvement_items": ["后续把排序变化确认结果接回 profile diff。"],
        })
        self.assertEqual(diff_confirm["learning_entry"]["target_type"], "unified_memory_ranking_diff")
        self.assertEqual(diff_confirm["learning_entry"]["entry_type"], "unified_memory_review_ranking_diff_confirmation")
        self.assertEqual(diff_confirm["learning_entry"]["metadata"]["source_view"], changed_item["source_view"])
        self.assertEqual(diff_confirm["learning_entry"]["metadata"]["decision"], "accepted")
        self.assertEqual(diff_confirm["learning_entry"]["metadata"]["current_rank"], changed_item["current_rank"])
        self.assertEqual(diff_confirm["learning_entry"]["metadata"]["suggested_rank"], changed_item["suggested_rank"])
        self.assertEqual(diff_confirm["evolution_log"]["trigger"], "unified_memory_review_ranking_diff_confirmation_learning")
        board_after_diff_confirm = brain.board_status()
        self.assertEqual(board_after_diff_confirm["recent_events"][-1]["type"], "unified_memory_review_ranking_diff_confirmed")

        brain.confirm_unified_memory_review_ranking_diff_item({
            "label": "补充反馈复盘摘要",
            "source_view": "feedback_memory_candidates",
            "candidate_type": "feedback_improvement_item",
            "decision": "deferred",
            "profile": "legacy-first",
            "current_rank": 2,
            "suggested_rank": 2,
            "score_delta": 0.0,
        })
        brain.confirm_unified_memory_review_ranking_diff_item({
            "label": "风险说明要明确",
            "source_view": "legacy_memory_decision_view",
            "candidate_type": "legacy_lesson",
            "decision": "rejected",
            "profile": "pair-first",
            "current_rank": 1,
            "suggested_rank": 3,
            "score_delta": -5.0,
        })
        diff_summary = brain.unified_memory_review_ranking_diff_summary({"limit": 5})
        self.assertEqual(diff_summary["summary"]["implementation_status"], "Implemented")
        self.assertEqual(diff_summary["summary"]["total_confirmations"], 3)
        self.assertEqual(diff_summary["summary"]["accepted_count"], 1)
        self.assertEqual(diff_summary["summary"]["deferred_count"], 1)
        self.assertEqual(diff_summary["summary"]["rejected_count"], 1)
        self.assertAlmostEqual(diff_summary["summary"]["acceptance_rate"], 0.3333, places=4)
        self.assertEqual(diff_summary["summary"]["source_view_counts"]["feedback_memory_candidates"], 1)
        self.assertEqual(diff_summary["summary"]["candidate_type_counts"]["legacy_lesson"], 1)
        self.assertEqual(diff_summary["summary"]["decision_counts"]["rejected"], 1)
        self.assertEqual(diff_summary["summary"]["profile_counts"]["legacy-first"], 2)
        self.assertEqual(diff_summary["top_accepted_candidates"][0]["label"], changed_item["label"])
        self.assertEqual(diff_summary["top_deferred_candidates"][0]["label"], "补充反馈复盘摘要")
        self.assertEqual(diff_summary["top_rejected_candidates"][0]["label"], "风险说明要明确")
        self.assertEqual(diff_summary["top_accepted_candidates"][0]["latest_suggested_rank"], changed_item["suggested_rank"])
        self.assertIn(
            "unified_memory_review_ranking_diff_confirmation -> unified_memory_review_ranking_diff_summary",
            diff_summary["integration_note"]["current_route"],
        )

        diff_signals = brain.unified_memory_review_ranking_diff_signals({"min_confirmations": 1})
        self.assertEqual(diff_signals["summary"]["implementation_status"], "Implemented")
        self.assertGreaterEqual(diff_signals["summary"]["profile_signal_count"], 2)
        legacy_profile_signal = next(item for item in diff_signals["profile_signals"] if item["key"] == "legacy-first")
        self.assertEqual(legacy_profile_signal["accepted_count"], 1)
        self.assertEqual(legacy_profile_signal["deferred_count"], 1)
        self.assertEqual(legacy_profile_signal["weight_signal"], "observe")
        pair_profile_signal = next(item for item in diff_signals["profile_signals"] if item["key"] == "pair-first")
        self.assertEqual(pair_profile_signal["rejected_count"], 1)
        self.assertEqual(pair_profile_signal["weight_signal"], "downgrade_watch")
        feedback_source_signal = next(item for item in diff_signals["source_view_signals"] if item["key"] == "feedback_memory_candidates")
        self.assertEqual(feedback_source_signal["total_confirmations"], 1)
        legacy_candidate_signal = next(item for item in diff_signals["candidate_type_signals"] if item["key"] == "legacy_lesson")
        self.assertEqual(legacy_candidate_signal["rejected_count"], 1)
        self.assertIn(
            "unified_memory_review_ranking_diff_confirmation -> unified_memory_review_ranking_diff_summary -> unified_memory_review_ranking_diff_signals",
            diff_signals["integration_note"]["current_route"],
        )

        policy_suggestions = brain.unified_memory_review_ranking_policy_suggestions({
            "min_confirmations": 1,
            "profile": "legacy-first",
        })
        self.assertEqual(policy_suggestions["summary"]["implementation_status"], "Implemented")
        self.assertEqual(policy_suggestions["summary"]["profile"], "legacy-first")
        self.assertGreaterEqual(policy_suggestions["summary"]["profile_suggestion_count"], 2)
        legacy_policy = next(item for item in policy_suggestions["profile_suggestions"] if item["key"] == "legacy-first")
        self.assertEqual(legacy_policy["weight_signal"], "observe")
        self.assertEqual(legacy_policy["suggested_weight_delta"], 0)
        pair_policy = next(item for item in policy_suggestions["profile_suggestions"] if item["key"] == "pair-first")
        self.assertEqual(pair_policy["weight_signal"], "downgrade_watch")
        self.assertLess(pair_policy["suggested_weight_delta"], 0)
        source_policy = next(item for item in policy_suggestions["source_view_suggestions"] if item["key"] == "feedback_memory_candidates")
        self.assertEqual(source_policy["dimension"], "source_view")
        candidate_policy = next(item for item in policy_suggestions["candidate_type_suggestions"] if item["key"] == "legacy_lesson")
        self.assertEqual(candidate_policy["rejected_count"], 1)
        self.assertIn(
            "unified_memory_review_ranking_diff_signals -> unified_memory_review_ranking_policy_suggestions",
            policy_suggestions["integration_note"]["current_route"],
        )
        self.assertIn("read-only policy suggestion layer", policy_suggestions["integration_note"]["future_route"])

        policy_approve = brain.confirm_unified_memory_review_ranking_policy_suggestion({
            "dimension": "profile",
            "key": "pair-first",
            "decision": "accepted",
            "profile": "legacy-first",
            "weight_signal": pair_policy["weight_signal"],
            "suggested_weight_delta": pair_policy["suggested_weight_delta"],
            "lessons": ["排序策略建议也需要进入可审计的人工审批闭环。"],
            "improvement_items": ["后续再汇总策略建议的审批历史。"],
        })
        self.assertEqual(policy_approve["learning_entry"]["target_type"], "unified_memory_ranking_policy")
        self.assertEqual(policy_approve["learning_entry"]["entry_type"], "unified_memory_review_ranking_policy_approval")
        self.assertEqual(policy_approve["learning_entry"]["metadata"]["dimension"], "profile")
        self.assertEqual(policy_approve["learning_entry"]["metadata"]["key"], "pair-first")
        self.assertEqual(policy_approve["learning_entry"]["metadata"]["decision"], "accepted")
        self.assertEqual(policy_approve["learning_entry"]["metadata"]["suggested_weight_delta"], pair_policy["suggested_weight_delta"])
        self.assertEqual(policy_approve["evolution_log"]["trigger"], "unified_memory_review_ranking_policy_approval_learning")
        board_after_policy_approve = brain.board_status()
        self.assertEqual(board_after_policy_approve["recent_events"][-1]["type"], "unified_memory_review_ranking_policy_approved")

        brain.confirm_unified_memory_review_ranking_policy_suggestion({
            "dimension": "source_view",
            "key": "feedback_memory_candidates",
            "decision": "deferred",
            "profile": "legacy-first",
            "weight_signal": "observe",
            "suggested_weight_delta": 0,
        })
        brain.confirm_unified_memory_review_ranking_policy_suggestion({
            "dimension": "candidate_type",
            "key": "legacy_lesson",
            "decision": "rejected",
            "profile": "pair-first",
            "weight_signal": "downgrade_watch",
            "suggested_weight_delta": -8,
        })
        policy_summary = brain.unified_memory_review_ranking_policy_approval_summary({"limit": 5})
        self.assertEqual(policy_summary["summary"]["implementation_status"], "Implemented")
        self.assertEqual(policy_summary["summary"]["total_approvals"], 3)
        self.assertEqual(policy_summary["summary"]["accepted_count"], 1)
        self.assertEqual(policy_summary["summary"]["deferred_count"], 1)
        self.assertEqual(policy_summary["summary"]["rejected_count"], 1)
        self.assertAlmostEqual(policy_summary["summary"]["acceptance_rate"], 0.3333, places=4)
        self.assertEqual(policy_summary["summary"]["dimension_counts"]["profile"], 1)
        self.assertEqual(policy_summary["summary"]["key_counts"]["pair-first"], 1)
        self.assertEqual(policy_summary["summary"]["decision_counts"]["rejected"], 1)
        self.assertEqual(policy_summary["summary"]["profile_counts"]["legacy-first"], 2)
        self.assertEqual(policy_summary["top_accepted_policy_suggestions"][0]["key"], "pair-first")
        self.assertEqual(policy_summary["top_deferred_policy_suggestions"][0]["key"], "feedback_memory_candidates")
        self.assertEqual(policy_summary["top_rejected_policy_suggestions"][0]["key"], "legacy_lesson")
        self.assertEqual(policy_summary["top_accepted_policy_suggestions"][0]["latest_suggested_weight_delta"], pair_policy["suggested_weight_delta"])
        self.assertIn(
            "unified_memory_review_ranking_policy_approval -> unified_memory_review_ranking_policy_approval_summary",
            policy_summary["integration_note"]["current_route"],
        )

        policy_signals = brain.unified_memory_review_ranking_policy_approval_signals({"min_confirmations": 1})
        self.assertEqual(policy_signals["summary"]["implementation_status"], "Implemented")
        self.assertGreaterEqual(policy_signals["summary"]["dimension_signal_count"], 3)
        dimension_signal = next(item for item in policy_signals["dimension_signals"] if item["key"] == "profile")
        self.assertEqual(dimension_signal["accepted_count"], 1)
        self.assertEqual(dimension_signal["weight_signal"], "observe")
        key_signal = next(item for item in policy_signals["key_signals"] if item["key"] == "legacy_lesson")
        self.assertEqual(key_signal["rejected_count"], 1)
        self.assertEqual(key_signal["weight_signal"], "downgrade_watch")
        profile_signal = next(item for item in policy_signals["profile_signals"] if item["key"] == "legacy-first")
        self.assertEqual(profile_signal["accepted_count"], 1)
        self.assertEqual(profile_signal["deferred_count"], 1)
        self.assertEqual(profile_signal["weight_signal"], "observe")
        self.assertIn(
            "unified_memory_review_ranking_policy_approval -> unified_memory_review_ranking_policy_approval_summary -> unified_memory_review_ranking_policy_approval_signals",
            policy_signals["integration_note"]["current_route"],
        )

        change_candidates = brain.unified_memory_review_ranking_policy_change_candidates({
            "min_confirmations": 1,
            "profile": "legacy-first",
        })
        self.assertEqual(change_candidates["summary"]["implementation_status"], "Implemented")
        self.assertEqual(change_candidates["summary"]["profile"], "legacy-first")
        self.assertGreaterEqual(change_candidates["summary"]["total_candidates"], 3)
        self.assertGreaterEqual(change_candidates["summary"]["downgrade_candidate_count"], 1)
        self.assertGreaterEqual(change_candidates["summary"]["observe_only_count"], 1)
        legacy_lesson_candidate = next(item for item in change_candidates["candidates"] if item["dimension"] == "key" and item["key"] == "legacy_lesson")
        self.assertEqual(legacy_lesson_candidate["change_bucket"], "downgrade_candidate")
        self.assertLess(legacy_lesson_candidate["suggested_weight_delta"], 0)
        profile_candidate = next(item for item in change_candidates["candidates"] if item["dimension"] == "profile" and item["key"] == "legacy-first")
        self.assertEqual(profile_candidate["change_bucket"], "observe_only")
        self.assertEqual(profile_candidate["weight_signal"], "observe")
        self.assertIn(
            "unified_memory_review_ranking_policy_approval_signals -> unified_memory_review_ranking_policy_change_candidates",
            change_candidates["integration_note"]["current_route"],
        )

        candidate_approve = brain.confirm_unified_memory_review_ranking_policy_change_candidate({
            "dimension": legacy_lesson_candidate["dimension"],
            "key": legacy_lesson_candidate["key"],
            "decision": "accepted",
            "profile": "legacy-first",
            "change_bucket": legacy_lesson_candidate["change_bucket"],
            "weight_signal": legacy_lesson_candidate["weight_signal"],
            "suggested_weight_delta": legacy_lesson_candidate["suggested_weight_delta"],
            "lessons": ["候选配置变更也需要进入统一审批闭环。"],
            "improvement_items": ["后续再汇总候选变更审批历史。"],
        })
        self.assertEqual(candidate_approve["learning_entry"]["target_type"], "unified_memory_ranking_policy_change_candidate")
        self.assertEqual(candidate_approve["learning_entry"]["entry_type"], "unified_memory_review_ranking_policy_change_candidate_approval")
        self.assertEqual(candidate_approve["learning_entry"]["metadata"]["dimension"], legacy_lesson_candidate["dimension"])
        self.assertEqual(candidate_approve["learning_entry"]["metadata"]["key"], legacy_lesson_candidate["key"])
        self.assertEqual(candidate_approve["learning_entry"]["metadata"]["decision"], "accepted")
        self.assertEqual(candidate_approve["learning_entry"]["metadata"]["change_bucket"], "downgrade_candidate")
        self.assertEqual(candidate_approve["learning_entry"]["metadata"]["suggested_weight_delta"], legacy_lesson_candidate["suggested_weight_delta"])
        self.assertEqual(candidate_approve["evolution_log"]["trigger"], "unified_memory_review_ranking_policy_change_candidate_approval_learning")
        board_after_candidate_approve = brain.board_status()
        self.assertEqual(board_after_candidate_approve["recent_events"][-1]["type"], "unified_memory_review_ranking_policy_change_candidate_approved")

        brain.confirm_unified_memory_review_ranking_policy_change_candidate({
            "dimension": "profile",
            "key": "legacy-first",
            "decision": "deferred",
            "profile": "legacy-first",
            "change_bucket": "observe_only",
            "weight_signal": "observe",
            "suggested_weight_delta": 0,
        })
        brain.confirm_unified_memory_review_ranking_policy_change_candidate({
            "dimension": "dimension",
            "key": "profile",
            "decision": "rejected",
            "profile": "pair-first",
            "change_bucket": "observe_only",
            "weight_signal": "observe",
            "suggested_weight_delta": 0,
        })
        candidate_summary = brain.unified_memory_review_ranking_policy_change_candidate_approval_summary({"limit": 5})
        self.assertEqual(candidate_summary["summary"]["implementation_status"], "Implemented")
        self.assertEqual(candidate_summary["summary"]["total_approvals"], 3)
        self.assertEqual(candidate_summary["summary"]["accepted_count"], 1)
        self.assertEqual(candidate_summary["summary"]["deferred_count"], 1)
        self.assertEqual(candidate_summary["summary"]["rejected_count"], 1)
        self.assertAlmostEqual(candidate_summary["summary"]["acceptance_rate"], 0.3333, places=4)
        self.assertEqual(candidate_summary["summary"]["dimension_counts"]["key"], 1)
        self.assertEqual(candidate_summary["summary"]["key_counts"]["legacy_lesson"], 1)
        self.assertEqual(candidate_summary["summary"]["decision_counts"]["rejected"], 1)
        self.assertEqual(candidate_summary["summary"]["profile_counts"]["legacy-first"], 2)
        self.assertEqual(candidate_summary["summary"]["change_bucket_counts"]["observe_only"], 2)
        self.assertEqual(candidate_summary["top_accepted_change_candidates"][0]["key"], "legacy_lesson")
        self.assertEqual(candidate_summary["top_deferred_change_candidates"][0]["key"], "legacy-first")
        self.assertEqual(candidate_summary["top_rejected_change_candidates"][0]["key"], "profile")
        self.assertEqual(candidate_summary["top_accepted_change_candidates"][0]["latest_suggested_weight_delta"], legacy_lesson_candidate["suggested_weight_delta"])
        self.assertIn(
            "unified_memory_review_ranking_policy_change_candidate_approval -> unified_memory_review_ranking_policy_change_candidate_approval_summary",
            candidate_summary["integration_note"]["current_route"],
        )

    def test_reasoning_trace_is_recorded_without_decision(self):
        brain = self.make_brain()
        ingested = brain.ingest_text({
            "title": "trace source",
            "text": "市场信息不足时，系统应该允许只记录推理而不强行下结论。",
            "source_type": "manual",
            "reliability": 0.82,
        })
        evidence_id = ingested["evidence"][0]["id"]
        trace = brain.create_reasoning_trace({
            "question": "现在是否应该直接交易？",
            "trace_type": "pretrade_analysis",
            "steps": [
                {"index": 1, "content": "检索到市场信息不足。"},
                {"index": 2, "content": "已有证据不足以支持高置信决策。"},
            ],
            "evidence_ids": [evidence_id],
            "conclusion": "暂不生成正式交易决策。",
            "confidence": 0.46,
            "uncertainty": "缺少更完整的市场数据和反证。",
            "next_action": "wait",
        })
        data = trace["reasoning_trace"]
        self.assertEqual(data["trace_type"], "pretrade_analysis")
        self.assertEqual(data["next_action"], "wait")
        self.assertEqual(len(data["steps"]), 2)
        self.assertEqual(data["evidence_ids"], [evidence_id])
        self.assertIn("bias_warnings", data["metadata"])
        self.assertEqual(trace["learning_entry"]["entry_type"], "reasoning_trace")

        board = brain.board_status()
        self.assertEqual(board["recent_events"][-1]["type"], "reasoning_trace_created")

    def test_manual_learning_entry_uses_shared_pipeline(self):
        brain = self.make_brain()
        ingested = brain.ingest_text({
            "title": "manual learn",
            "text": "系统应该把经验沉淀成可复用的学习记录。",
            "source_type": "manual",
            "reliability": 0.81,
        })
        atom_id = ingested["atoms"][0]["id"]
        evidence_id = ingested["evidence"][0]["id"]
        result = brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_id],
            "summary": "这条经验值得沉淀为统一学习记录。",
            "evidence_ids": [evidence_id],
            "lessons": ["统一学习入口可以降低分叉逻辑。"],
            "improvement_items": ["后续把 review 和 feedback 仪表盘串起来"],
            "confidence_delta": 0.05,
        })
        self.assertEqual(result["learning_entry"]["target_ids"], [atom_id])
        self.assertEqual(result["learning_entry"]["evidence_ids"], [evidence_id])
        self.assertEqual(result["evolution_log"]["trigger"], "manual_learning")

        board = brain.board_status()
        self.assertEqual(board["recent_events"][-1]["type"], "learning_entry_created")

    def test_learning_search_and_summary_surface_repeated_patterns(self):
        brain = self.make_brain()
        ingested = brain.ingest_text({
            "title": "learning summary seed",
            "text": "系统需要能回看重复出现的错误模式和改进项。",
            "source_type": "manual",
            "reliability": 0.79,
        })
        atom_id = ingested["atoms"][0]["id"]
        evidence_id = ingested["evidence"][0]["id"]

        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_id],
            "summary": "复盘显示风险说明经常缺失。",
            "evidence_ids": [evidence_id],
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.learning_entry({
            "entry_type": "feedback",
            "target_type": "decision",
            "target_ids": ["decision_x"],
            "summary": "用户再次指出风险说明不足。",
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.learning_entry({
            "entry_type": "review",
            "target_type": "forecast",
            "target_ids": ["forecast_x"],
            "summary": "预测复盘发现失效条件记录不够完整。",
            "lessons": ["失效条件需要前置"],
            "improvement_items": ["补充失效条件"],
        })

        search = brain.search_learning_entries({"query": "风险说明", "top_k": 2})
        self.assertEqual(len(search["results"]), 2)
        self.assertIn("decision", {item["target_type"] for item in search["results"]})
        self.assertTrue(any("风险说明要明确" in item["lessons"] for item in search["results"]))
        self.assertEqual(search["summary"]["implementation_status"], "Implemented")

        summary = brain.learning_summary({"limit": 3})
        self.assertEqual(summary["total_learning_entries"], 3)
        self.assertEqual(summary["entry_type_counts"]["manual_learning"], 1)
        self.assertEqual(summary["target_type_counts"]["forecast"], 1)
        self.assertEqual(summary["top_lessons"][0]["text"], "风险说明要明确")
        self.assertEqual(summary["top_lessons"][0]["count"], 2)
        self.assertEqual(summary["top_improvement_items"][0]["text"], "补充风险说明")
        self.assertEqual(len(summary["recent_entries"]), 3)

    def test_learning_inspect_links_back_to_targets_evidence_and_logs(self):
        brain = self.make_brain()
        ingested = brain.ingest_text({
            "title": "traceability seed",
            "text": "一条学习记录应该能反向追到证据、原始推理和进化日志。",
            "source_type": "manual",
            "reliability": 0.84,
        })
        evidence_id = ingested["evidence"][0]["id"]
        trace = brain.create_reasoning_trace({
            "question": "当前是否应该直接下正式判断？",
            "trace_type": "analysis",
            "steps": [{"index": 1, "content": "证据不足，先保留推理记录。"}],
            "evidence_ids": [evidence_id],
            "counter_evidence_ids": ["ev_missing_counter"],
            "conclusion": "先记录 reasoning trace。",
            "confidence": 0.42,
            "uncertainty": "缺少更多反证。",
            "next_action": "wait",
        })
        learning_entry_id = trace["learning_entry"]["id"]

        inspected = brain.inspect_learning_entry({"learning_entry_id": learning_entry_id})
        self.assertEqual(inspected["learning_entry"]["id"], learning_entry_id)
        self.assertEqual(inspected["source_record"]["table"], "reasoning_traces")
        self.assertEqual(inspected["targets"][0]["table"], "reasoning_traces")
        self.assertEqual(inspected["targets"][0]["record"]["id"], trace["reasoning_trace"]["id"])
        self.assertEqual(inspected["evidence"][0]["table"], "evidence")
        self.assertEqual(inspected["evidence"][0]["record"]["id"], evidence_id)
        self.assertEqual(inspected["counter_evidence"][0]["status"], "unresolved_reference")
        self.assertGreaterEqual(inspected["traceability"]["related_evolution_log_count"], 1)
        self.assertTrue(any(log["trigger"] == "reasoning_trace_learning" for log in inspected["related_evolution_logs"]))

    def test_learning_chains_group_repeated_lessons_and_improvements(self):
        brain = self.make_brain()
        ingested = brain.ingest_text({
            "title": "chain seed",
            "text": "系统应该把重复 lesson 聚成跨记录学习链。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        atom_id = ingested["atoms"][0]["id"]
        evidence_id = ingested["evidence"][0]["id"]

        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_id],
            "summary": "第一次发现风险说明不清楚。",
            "source_record_id": atom_id,
            "evidence_ids": [evidence_id],
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.learning_entry({
            "entry_type": "feedback",
            "target_type": "decision",
            "target_ids": ["decision_y"],
            "summary": "第二次还是卡在风险说明。",
            "source_record_id": "feedback_y",
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.learning_entry({
            "entry_type": "review",
            "target_type": "forecast",
            "target_ids": ["forecast_y"],
            "summary": "另外一个主题是失效条件。",
            "source_record_id": "review_y",
            "lessons": ["失效条件需要前置"],
            "improvement_items": ["补充失效条件"],
        })

        chains = brain.learning_chains({"limit": 5, "min_count": 2})
        self.assertEqual(chains["summary"]["implementation_status"], "Implemented")
        self.assertEqual(chains["summary"]["returned_lesson_chains"], 1)
        self.assertEqual(chains["lesson_chains"][0]["text"], "风险说明要明确")
        self.assertEqual(chains["lesson_chains"][0]["entry_count"], 2)
        self.assertIn("atom", chains["lesson_chains"][0]["target_types"])
        self.assertIn("decision", chains["lesson_chains"][0]["target_types"])
        self.assertEqual(chains["improvement_chains"][0]["text"], "补充风险说明")
        self.assertEqual(chains["improvement_chains"][0]["target_type_counts"]["decision"], 1)

    def test_learning_apply_writes_recommended_tags_relations_and_affects_search(self):
        brain = self.make_brain()
        ingest_a = brain.ingest_text({
            "title": "apply a",
            "text": "这里记录第一条原子。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        ingest_b = brain.ingest_text({
            "title": "apply b",
            "text": "这里记录第二条原子。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        atom_a = ingest_a["atoms"][0]["id"]
        atom_b = ingest_b["atoms"][0]["id"]

        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_a],
            "summary": "第一次发现风险说明不足。",
            "source_record_id": atom_a,
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_b],
            "summary": "第二次还是风险说明不足。",
            "source_record_id": atom_b,
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })

        applied = brain.apply_learning_chains({"limit": 5, "min_count": 2})
        self.assertEqual(applied["evolution_log"]["trigger"], "learning_chain_apply")
        self.assertEqual(len(applied["updated_atoms"]), 2)
        self.assertGreaterEqual(len(applied["created_relations"]), 2)
        audit_atom_a = next(item for item in applied["atom_apply_audit"] if item["atom_id"] == atom_a)
        self.assertIn("风险说明要明确", audit_atom_a["new_chain_refs"])

        updated_atom_a = next(item for item in applied["updated_atoms"] if item["id"] == atom_a)
        self.assertIn("风险说明要明确", updated_atom_a["metadata"]["recommended_tags"])
        self.assertTrue(any(ref["text"] == "风险说明要明确" for ref in updated_atom_a["metadata"]["learning_chain_refs"]))
        self.assertIn(atom_b, updated_atom_a["related_ids"])

        search = brain.search({"query": "风险说明要明确", "top_k": 5})
        self.assertTrue(any(item["atom_id"] == atom_a for item in search["results"]))
        self.assertTrue(any(item["atom_id"] == atom_b for item in search["results"]))

        board = brain.board_status()
        self.assertEqual(board["recent_events"][-1]["type"], "learning_chain_applied")

    def test_atom_writeback_inspect_explains_tags_relations_and_importance(self):
        brain = self.make_brain()
        ingest_a = brain.ingest_text({
            "title": "audit a",
            "text": "原子 A。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        ingest_b = brain.ingest_text({
            "title": "audit b",
            "text": "原子 B。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        atom_a = ingest_a["atoms"][0]["id"]
        atom_b = ingest_b["atoms"][0]["id"]
        base_importance = ingest_a["atoms"][0]["importance"]

        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_a],
            "summary": "第一次风险说明不足。",
            "source_record_id": atom_a,
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_b],
            "summary": "第二次风险说明不足。",
            "source_record_id": atom_b,
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.apply_learning_chains({"limit": 5, "min_count": 2})

        audited = brain.inspect_atom_writeback({"atom_id": atom_a})
        self.assertEqual(audited["atom"]["id"], atom_a)
        self.assertIn("风险说明要明确", audited["recommended_tags"])
        self.assertTrue(any(ref["text"] == "风险说明要明确" for ref in audited["learning_chain_refs"]))
        self.assertTrue(any(rel["relation_type"] == "learning_chain_related" for rel in audited["learning_chain_relations"]))
        self.assertTrue(any(entry["id"].startswith("learn_") for entry in audited["related_learning_entries"]))
        self.assertTrue(any(log["trigger"] == "learning_chain_apply" for log in audited["related_evolution_logs"]))
        self.assertGreater(audited["importance_audit"]["current_importance"], base_importance)
        self.assertGreater(audited["writeback_audit"]["relation_count"], 0)
        self.assertIn("风险说明要明确", audited["latest_apply_audit"]["new_chain_refs"])

    def test_writeback_overview_surfaces_top_atoms_and_patterns(self):
        brain = self.make_brain()
        atoms: list[str] = []
        for label in ["A", "B", "C"]:
            ingested = brain.ingest_text({
                "title": f"overview {label}",
                "text": f"原子 {label}。",
                "source_type": "manual",
                "reliability": 0.8,
            })
            atoms.append(ingested["atoms"][0]["id"])

        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atoms[0]],
            "summary": "模式一第一次出现。",
            "source_record_id": atoms[0],
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atoms[1]],
            "summary": "模式一第二次出现。",
            "source_record_id": atoms[1],
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atoms[2]],
            "summary": "模式二第一次出现。",
            "source_record_id": atoms[2],
            "lessons": ["失效条件需要前置"],
            "improvement_items": ["补充失效条件"],
        })
        brain.apply_learning_chains({"limit": 5, "min_count": 2})

        overview = brain.writeback_overview({"limit": 5})
        self.assertEqual(overview["summary"]["implementation_status"], "Implemented")
        self.assertEqual(overview["summary"]["atoms_with_writeback"], 2)
        self.assertGreaterEqual(len(overview["top_writeback_atoms"]), 2)
        self.assertEqual(overview["top_recommended_tags"][0]["text"], "补充风险说明")
        self.assertIn("风险说明要明确", {item["text"] for item in overview["top_chain_texts"]})
        self.assertIn("补充风险说明", {item["text"] for item in overview["top_chain_texts"]})
        self.assertTrue(any(row["atom_id"] == atoms[0] for row in overview["top_writeback_atoms"]))
        self.assertEqual(overview["latest_apply_buckets"]["new_or_changed_count"], 2)

    def test_writeback_snapshot_and_compare_show_score_delta_and_state_migration(self):
        brain = self.make_brain()
        ingest_a = brain.ingest_text({
            "title": "snapshot a",
            "text": "原子甲。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        ingest_b = brain.ingest_text({
            "title": "snapshot b",
            "text": "原子乙。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        atom_a = ingest_a["atoms"][0]["id"]
        atom_b = ingest_b["atoms"][0]["id"]

        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_a],
            "summary": "第一次风险说明不足。",
            "source_record_id": atom_a,
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_b],
            "summary": "第二次风险说明不足。",
            "source_record_id": atom_b,
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.apply_learning_chains({"limit": 5, "min_count": 2})
        snapshot = brain.capture_writeback_snapshot({"limit": 10, "name": "baseline"})
        snapshot_id = snapshot["snapshot"]["id"]
        self.assertEqual(snapshot["evolution_log"]["trigger"], "writeback_snapshot_capture")
        self.assertEqual(snapshot["snapshot"]["metadata"]["latest_apply_buckets"]["new_or_changed_count"], 2)

        brain.apply_learning_chains({"limit": 5, "min_count": 2})

        comparison = brain.compare_writeback_snapshot({"limit": 10, "snapshot_id": snapshot_id})
        self.assertEqual(comparison["summary"]["implementation_status"], "Implemented")
        self.assertEqual(comparison["baseline_snapshot"]["id"], snapshot_id)
        self.assertGreaterEqual(comparison["summary"]["atoms_with_changed_scores"], 0)
        self.assertGreaterEqual(comparison["summary"]["atoms_with_apply_state_transition"], 2)
        self.assertEqual(comparison["bucket_migration"]["count_deltas"]["new_or_changed_delta"], -2)
        self.assertEqual(comparison["bucket_migration"]["count_deltas"]["confirmed_only_delta"], 2)
        self.assertTrue(any(item["transition"] == "new_or_changed->confirmed_only" for item in comparison["bucket_migration"]["state_transitions"]))
        self.assertTrue(all(
            row["baseline_latest_apply_state"] == "new_or_changed" and row["current_latest_apply_state"] == "confirmed_only"
            for row in comparison["atom_deltas"][:2]
        ))

    def test_legacy_lessons_map_bridges_learning_entries_to_read_only_lessons_file(self):
        brain = self.make_brain()
        legacy_dir = brain.root / "second-brain"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "lessons.md").write_text(
            "# 历史教训库\n\n"
            "教训: 风险说明要明确\n"
            "教训: 涨停次日不追高\n",
            encoding="utf-8",
        )

        atom_ids: list[str] = []
        for label in ["A", "B", "C", "D", "E"]:
            ingested = brain.ingest_text({
                "title": f"legacy map {label}",
                "text": f"原子 {label}。",
                "source_type": "manual",
                "reliability": 0.8,
            })
            atom_ids.append(ingested["atoms"][0]["id"])

        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_ids[0]],
            "summary": "第一次风险说明不足。",
            "source_record_id": atom_ids[0],
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_ids[1]],
            "summary": "第二次风险说明不足。",
            "source_record_id": atom_ids[1],
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.apply_learning_chains({"limit": 10, "min_count": 2})

        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_ids[2]],
            "summary": "第一次失效条件问题。",
            "source_record_id": atom_ids[2],
            "lessons": ["失效条件需要前置"],
            "improvement_items": ["补充失效条件"],
        })
        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_ids[3]],
            "summary": "第二次失效条件问题。",
            "source_record_id": atom_ids[3],
            "lessons": ["失效条件需要前置"],
            "improvement_items": ["补充失效条件"],
        })
        brain.apply_learning_chains({"limit": 10, "min_count": 2})
        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_ids[4]],
            "summary": "只出现一次的波动噪声。",
            "source_record_id": atom_ids[4],
            "lessons": ["临时噪声不要过度总结"],
            "improvement_items": ["暂不调整系统"],
        })

        mapping = brain.legacy_lessons_mapping()
        self.assertEqual(mapping["summary"]["legacy_file_status"], "read_only")
        self.assertEqual(mapping["summary"]["implementation_status"], "Implemented")
        self.assertEqual(mapping["summary"]["mapped_confirmed_only_count"], 1)
        self.assertEqual(mapping["summary"]["legacy_only_count"], 1)
        self.assertEqual(mapping["summary"]["emerging_immediate_candidate_count"], 1)
        self.assertEqual(mapping["summary"]["emerging_single_noise_count"], 1)
        self.assertEqual(mapping["summary"]["improvement_immediate_candidate_count"], 2)
        self.assertEqual(mapping["summary"]["improvement_single_noise_count"], 1)
        self.assertEqual(mapping["summary"]["lesson_improvement_pair_count"], 3)
        self.assertEqual(mapping["summary"]["pair_immediate_candidate_count"], 2)
        self.assertEqual(mapping["summary"]["legacy_memory_candidate_count"], 6)
        self.assertEqual(mapping["summary"]["legacy_memory_candidate_type_counts"]["legacy_lesson_confirmation"], 1)
        self.assertEqual(mapping["summary"]["legacy_memory_candidate_group_counts"]["confirm_legacy_lessons"], 1)
        self.assertEqual(mapping["summary"]["legacy_memory_candidate_group_counts"]["promote_lesson_improvement_pairs"], 2)
        self.assertEqual(mapping["summary"]["legacy_memory_candidate_group_counts"]["promote_new_lessons"], 1)
        self.assertEqual(mapping["summary"]["legacy_memory_candidate_group_counts"]["promote_improvement_actions"], 2)
        self.assertEqual(mapping["summary"]["legacy_memory_promote_now_count"], 3)
        self.assertEqual(mapping["summary"]["legacy_memory_watch_downgrade_count"], 3)
        self.assertEqual(mapping["summary"]["legacy_memory_decision_weight_profile"], "legacy-first")
        self.assertIn("仍需补证据", mapping["summary"]["audit_conclusion"]["overall"])
        self.assertEqual(mapping["summary"]["audit_conclusion"]["lesson_primary_gap"], "当前没有仍需补证据的 lessons。")
        self.assertEqual(mapping["summary"]["audit_conclusion"]["improvement_primary_gap"], "当前没有仍需补证据的 improvement_items。")
        self.assertIn("配对级缺口是重复次数不够", mapping["summary"]["audit_conclusion"]["pair_primary_gap"])
        self.assertIn("继续观察重复出现的教训-改进配对", mapping["summary"]["audit_conclusion"]["next_action"])
        self.assertEqual(mapping["summary"]["audit_conclusion"]["top_gaps"][0]["scope"], "pair")
        self.assertEqual(mapping["summary"]["audit_conclusion"]["top_gaps"][0]["gap_type"], "missing_repeat_count")
        self.assertTrue(any("教训-改进配对" in item["summary"] for item in mapping["summary"]["audit_conclusion"]["top_gaps"]))
        self.assertTrue(any("优先回看近期 learning entries" in item for item in mapping["summary"]["audit_conclusion"]["action_recommendations"]))
        self.assertIn("优先沉淀稳定出现的教训-改进配对模式", mapping["summary"]["audit_conclusion"]["candidate_focus"])
        self.assertEqual(mapping["legacy_memory_candidates"][0]["candidate_type"], "legacy_lesson_confirmation")
        self.assertEqual(mapping["legacy_memory_candidates"][0]["label"], "风险说明要明确")
        self.assertIn("type_rank", mapping["legacy_memory_candidates"][0]["priority_components"])
        self.assertIn("ranking_reason", mapping["legacy_memory_candidates"][0])
        self.assertEqual(mapping["legacy_memory_candidates"][0]["governance_signals"]["evidence_count"], 2)
        self.assertTrue(mapping["legacy_memory_candidates"][0]["governance_signals"]["writeback_confirmed"])
        self.assertIn("高优先级修订任务", mapping["legacy_memory_candidates"][0]["governance_signals"]["upgrade_recommendation"])
        self.assertTrue(any(item["candidate_type"] == "lesson_improvement_pair_candidate" for item in mapping["legacy_memory_candidates"]))
        pair_candidate = next(item for item in mapping["legacy_memory_candidates"] if item["candidate_type"] == "lesson_improvement_pair_candidate")
        self.assertEqual(pair_candidate["governance_signals"]["atom_count"], 2)
        self.assertTrue(pair_candidate["governance_signals"]["writeback_present"])
        self.assertIn("长期默认规则候选", pair_candidate["governance_signals"]["upgrade_recommendation"])
        self.assertIn("writeback 状态变化", pair_candidate["governance_signals"]["next_review_trigger"])
        improvement_candidate = next(item for item in mapping["legacy_memory_candidates"] if item["candidate_type"] == "improvement_candidate")
        self.assertIn("一次性 workaround", improvement_candidate["governance_signals"]["downgrade_risk"])
        self.assertEqual(mapping["legacy_memory_decision_view"]["promote_now"][0]["label"], "风险说明要明确")
        self.assertEqual(mapping["legacy_memory_decision_view"]["promote_now"][0]["candidate_type"], "legacy_lesson_confirmation")
        self.assertIn("profile=legacy-first", mapping["legacy_memory_decision_view"]["promote_now"][0]["score_explanation"])
        self.assertIn("高优先级修订任务", mapping["legacy_memory_decision_view"]["promote_now"][0]["why_now"])
        self.assertEqual(mapping["legacy_memory_decision_view"]["decision_weight_config"]["profile"], "legacy-first")
        self.assertIn("profile=legacy-first", mapping["legacy_memory_decision_view"]["summary"]["profile_explanation"])
        self.assertIn("旧 lesson 再验证", mapping["legacy_memory_decision_view"]["summary"]["profile_explanation"])
        self.assertEqual(mapping["legacy_memory_decision_view"]["watch_for_downgrade"][0]["candidate_type"], "improvement_candidate")
        self.assertIn("一次性 workaround", mapping["legacy_memory_decision_view"]["watch_for_downgrade"][0]["risk_reason"])
        self.assertIn("当前最值得马上整理的是 风险说明要明确", mapping["legacy_memory_decision_view"]["summary"]["focus_now"])
        self.assertEqual(mapping["legacy_memory_candidate_groups"]["confirm_legacy_lessons"]["queue_rank"], 1)
        self.assertEqual(mapping["legacy_memory_candidate_groups"]["confirm_legacy_lessons"]["items"][0]["label"], "风险说明要明确")
        self.assertIn("再验证", mapping["legacy_memory_candidate_groups"]["confirm_legacy_lessons"]["group_membership_reason"])
        self.assertIn("高优先级修订任务", mapping["legacy_memory_candidate_groups"]["confirm_legacy_lessons"]["upgrade_condition"])
        self.assertIn("暂不调整旧 lesson", mapping["legacy_memory_candidate_groups"]["confirm_legacy_lessons"]["downgrade_condition"])
        self.assertEqual(mapping["legacy_memory_candidate_groups"]["promote_lesson_improvement_pairs"]["candidate_count"], 2)
        self.assertIn("问题 -> 修正动作", mapping["legacy_memory_candidate_groups"]["promote_lesson_improvement_pairs"]["manual_action"])
        self.assertIn("决策模板", mapping["legacy_memory_candidate_groups"]["promote_lesson_improvement_pairs"]["group_membership_reason"])
        self.assertIn("长期默认规则", mapping["legacy_memory_candidate_groups"]["promote_lesson_improvement_pairs"]["upgrade_condition"])
        self.assertIn("降级回单独的新 lesson / improvement 候选", mapping["legacy_memory_candidate_groups"]["promote_lesson_improvement_pairs"]["downgrade_condition"])
        self.assertIn("confirmed_only", mapping["legacy_memory_candidate_groups"]["promote_lesson_improvement_pairs"]["review_trigger"])
        self.assertEqual(mapping["legacy_memory_candidate_groups"]["promote_new_lessons"]["candidate_count"], 1)
        self.assertIn("最小稳定证据", mapping["legacy_memory_candidate_groups"]["promote_new_lessons"]["group_membership_reason"])
        self.assertEqual(mapping["legacy_memory_candidate_groups"]["promote_improvement_actions"]["candidate_count"], 2)
        self.assertIn("一次性 workaround", mapping["legacy_memory_candidate_groups"]["promote_improvement_actions"]["downgrade_condition"])
        self.assertEqual(mapping["improvement_item_mapping"]["implementation_status"], "Implemented")
        self.assertEqual(mapping["lesson_improvement_pair_mapping"]["implementation_status"], "Implemented")
        self.assertEqual(mapping["positive_experience_mapping"]["implementation_status"], "TODO")

        risk_row = next(item for item in mapping["legacy_lessons"] if item["lesson_text"] == "风险说明要明确")
        self.assertEqual(risk_row["mapping_status"], "mapped_confirmed_only")
        self.assertEqual(risk_row["current_apply_state"], "confirmed_only")
        self.assertEqual(risk_row["current_learning_count"], 2)

        untouched_row = next(item for item in mapping["legacy_lessons"] if item["lesson_text"] == "涨停次日不追高")
        self.assertEqual(untouched_row["mapping_status"], "legacy_only")
        self.assertEqual(untouched_row["current_learning_count"], 0)

        emerging_row = next(item for item in mapping["emerging_learning_lessons"] if item["lesson_text"] == "失效条件需要前置")
        self.assertEqual(emerging_row["migration_status"], "immediate_candidate")
        self.assertEqual(emerging_row["current_apply_state"], "new_or_changed")
        self.assertEqual(emerging_row["current_learning_count"], 2)
        self.assertIn("cross-atom writeback pattern", emerging_row["migration_reason"])
        self.assertEqual(emerging_row["evidence_gap"]["primary_gap"], "none")
        self.assertIn("较稳定的长期记忆候选", emerging_row["audit_explanation"])

        noise_row = next(item for item in mapping["emerging_learning_lessons"] if item["lesson_text"] == "临时噪声不要过度总结")
        self.assertEqual(noise_row["migration_status"], "single_observation_noise")
        self.assertEqual(noise_row["current_apply_state"], "not_in_learning_chain_writeback")
        self.assertEqual(noise_row["current_learning_count"], 1)
        self.assertEqual(noise_row["evidence_gap"]["primary_gap"], "single_observation")
        self.assertIn("只有单次观察", noise_row["audit_explanation"])

        improvement_row = next(item for item in mapping["emerging_improvement_items"] if item["improvement_item_text"] == "补充失效条件")
        self.assertEqual(improvement_row["migration_status"], "immediate_candidate")
        self.assertEqual(improvement_row["current_apply_state"], "new_or_changed")
        self.assertEqual(improvement_row["current_learning_count"], 2)
        self.assertEqual(improvement_row["evidence_gap"]["primary_gap"], "none")
        self.assertIn("改进项", improvement_row["audit_explanation"])

        improvement_noise_row = next(item for item in mapping["emerging_improvement_items"] if item["improvement_item_text"] == "暂不调整系统")
        self.assertEqual(improvement_noise_row["migration_status"], "single_observation_noise")
        self.assertEqual(improvement_noise_row["current_learning_count"], 1)
        self.assertEqual(improvement_noise_row["evidence_gap"]["primary_gap"], "single_observation")

        pair_row = next(
            item for item in mapping["lesson_improvement_pairs"]
            if item["lesson_text"] == "失效条件需要前置" and item["improvement_item_text"] == "补充失效条件"
        )
        self.assertEqual(pair_row["migration_status"], "immediate_candidate")
        self.assertEqual(pair_row["pair_count"], 2)
        self.assertEqual(pair_row["lesson_current_apply_state"], "new_or_changed")
        self.assertEqual(pair_row["improvement_current_apply_state"], "new_or_changed")
        self.assertEqual(pair_row["evidence_gap"]["primary_gap"], "none")

        pair_noise_row = next(
            item for item in mapping["lesson_improvement_pairs"]
            if item["lesson_text"] == "临时噪声不要过度总结" and item["improvement_item_text"] == "暂不调整系统"
        )
        self.assertEqual(pair_noise_row["migration_status"], "need_more_evidence")
        self.assertEqual(pair_noise_row["pair_count"], 1)
        self.assertEqual(pair_noise_row["evidence_gap"]["primary_gap"], "missing_repeat_count")
        self.assertTrue(pair_noise_row["evidence_gap"]["missing_cross_atom_support"])
        self.assertTrue(pair_noise_row["evidence_gap"]["missing_writeback_confirmation"])
        self.assertEqual(mapping["summary"]["pair_gap_missing_repeat_count"], 1)
        self.assertIn("重复次数还不够", pair_noise_row["audit_explanation"])
        self.assertIn("跨 atom 支撑不足", pair_noise_row["audit_explanation"])

        decision_view_all = brain.legacy_memory_decision_view({"view": "all"})
        self.assertEqual(decision_view_all["view"], "all")
        self.assertEqual(decision_view_all["decision_view"]["promote_now"][0]["label"], "风险说明要明确")

        decision_view_promote = brain.legacy_memory_decision_view({"view": "promote-now"})
        self.assertEqual(decision_view_promote["view"], "promote-now")
        self.assertEqual(decision_view_promote["summary"]["item_count"], 3)
        self.assertEqual(decision_view_promote["items"][0]["candidate_type"], "legacy_lesson_confirmation")

        decision_view_watch = brain.legacy_memory_decision_view({"view": "watchlist"})
        self.assertEqual(decision_view_watch["view"], "watchlist")
        self.assertEqual(decision_view_watch["summary"]["item_count"], 3)
        self.assertEqual(decision_view_watch["items"][0]["candidate_type"], "improvement_candidate")

        decision_view_pair_first = brain.legacy_memory_decision_view({"view": "promote-now", "profile": "pair-first"})
        self.assertEqual(decision_view_pair_first["summary"]["decision_weight_profile"], "pair-first")
        self.assertEqual(decision_view_pair_first["items"][0]["candidate_type"], "lesson_improvement_pair_candidate")
        self.assertIn("profile=pair-first", decision_view_pair_first["summary"]["profile_explanation"])
        self.assertIn("配对模式", decision_view_pair_first["summary"]["profile_explanation"])
        self.assertIn("profile=pair-first", decision_view_pair_first["items"][0]["score_explanation"])

        decision_view_diff = brain.legacy_memory_decision_view({
            "view": "profile-diff",
            "left_profile": "legacy-first",
            "right_profile": "pair-first",
        })
        self.assertEqual(decision_view_diff["view"], "profile-diff")
        self.assertEqual(decision_view_diff["left_profile"], "legacy-first")
        self.assertEqual(decision_view_diff["right_profile"], "pair-first")
        self.assertEqual(decision_view_diff["left_top_candidate"]["candidate_type"], "legacy_lesson_confirmation")
        self.assertEqual(decision_view_diff["right_top_candidate"]["candidate_type"], "lesson_improvement_pair_candidate")
        self.assertFalse(decision_view_diff["difference_summary"]["same_top_candidate"])
        self.assertGreaterEqual(decision_view_diff["difference_summary"]["top3_change_count"], 1)
        self.assertGreaterEqual(decision_view_diff["difference_summary"]["action_change_count"], 1)
        self.assertTrue(any(item["rank_changed"] for item in decision_view_diff["rank_changes"]))
        self.assertEqual(decision_view_diff["rank_changes"][0]["left_rank"], 1)
        self.assertGreaterEqual(decision_view_diff["action_recommendations"]["summary"]["promote_count"], 1)
        self.assertGreaterEqual(decision_view_diff["action_recommendations"]["summary"]["defer_count"], 1)
        self.assertTrue(any("建议提前整理" in item["action"] for item in decision_view_diff["action_recommendations"]["promote_earlier"]))
        self.assertTrue(any("建议后移观察" in item["action"] for item in decision_view_diff["action_recommendations"]["defer_or_watch"]))
        self.assertIn("权重配置已经影响了人工整理优先级", decision_view_diff["difference_summary"]["changed_reason"])

        confirm_result = brain.confirm_legacy_memory_action({
            "candidate_label": "风险说明要明确",
            "candidate_type": "legacy_lesson_confirmation",
            "action_bucket": "promote_earlier",
            "accepted": True,
            "left_profile": "legacy-first",
            "right_profile": "pair-first",
            "lessons": ["人工确认后，旧 lesson 再验证仍应优先整理。"],
            "improvement_items": ["后续把人工确认结果接回 profile 调整策略。"],
        })
        self.assertEqual(confirm_result["learning_entry"]["target_type"], "legacy_memory_candidate")
        self.assertEqual(confirm_result["learning_entry"]["entry_type"], "legacy_memory_action_confirmation")
        self.assertTrue(confirm_result["learning_entry"]["metadata"]["accepted"])
        self.assertEqual(confirm_result["evolution_log"]["trigger"], "legacy_memory_action_confirmation_learning")
        board_after_confirm = brain.board_status()
        self.assertEqual(board_after_confirm["recent_events"][-1]["type"], "legacy_memory_action_confirmed")

        brain.confirm_legacy_memory_action({
            "candidate_label": "风险说明要明确",
            "candidate_type": "legacy_lesson_confirmation",
            "action_bucket": "promote_earlier",
            "accepted": False,
            "left_profile": "legacy-first",
            "right_profile": "pair-first",
        })
        brain.confirm_legacy_memory_action({
            "candidate_label": "补充跨 atom 证据",
            "candidate_type": "lesson_improvement_pair_candidate",
            "action_bucket": "defer_or_watch",
            "accepted": True,
            "left_profile": "legacy-first",
            "right_profile": "pair-first",
        })
        action_summary = brain.legacy_memory_action_summary({"limit": 5})
        self.assertEqual(action_summary["summary"]["total_confirmations"], 3)
        self.assertEqual(action_summary["summary"]["accepted_count"], 2)
        self.assertEqual(action_summary["summary"]["rejected_count"], 1)
        self.assertAlmostEqual(action_summary["summary"]["acceptance_rate"], 0.6667, places=4)
        self.assertEqual(action_summary["summary"]["candidate_type_counts"]["legacy_lesson_confirmation"], 2)
        self.assertEqual(action_summary["summary"]["action_bucket_counts"]["promote_earlier"], 2)
        self.assertEqual(action_summary["top_accepted_candidates"][0]["label"], "风险说明要明确")
        self.assertEqual(action_summary["top_accepted_candidates"][0]["accepted_count"], 1)
        self.assertEqual(action_summary["top_accepted_candidates"][0]["rejected_count"], 1)
        self.assertEqual(action_summary["top_rejected_candidates"][0]["label"], "风险说明要明确")
        self.assertEqual(action_summary["profile_feedback"][0]["profile_pair"], "legacy-first -> pair-first")
        self.assertEqual(action_summary["profile_feedback"][0]["accepted_count"], 2)
        self.assertEqual(action_summary["profile_feedback"][0]["rejected_count"], 1)
        self.assertEqual(action_summary["implementation_status"], "Implemented")

    def test_legacy_lessons_map_handles_need_more_evidence_path_without_runtime_error(self):
        brain = self.make_brain()
        legacy_dir = brain.root / "second-brain"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "lessons.md").write_text("# 历史教训库\n\n教训: 风险说明要明确\n", encoding="utf-8")

        ingested = brain.ingest_text({
            "title": "single lesson",
            "text": "原子甲。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        atom_id = ingested["atoms"][0]["id"]
        for _ in range(2):
            brain.learning_entry({
                "entry_type": "manual_learning",
                "target_type": "atom",
                "target_ids": [atom_id],
                "summary": "重复出现但仍缺跨 atom 支撑的失效条件问题。",
                "source_record_id": atom_id,
                "lessons": ["失效条件需要前置"],
                "improvement_items": ["补充失效条件"],
            })

        mapping = brain.legacy_lessons_mapping()
        emerging_row = next(item for item in mapping["emerging_learning_lessons"] if item["lesson_text"] == "失效条件需要前置")
        self.assertEqual(emerging_row["migration_status"], "need_more_evidence")
        self.assertEqual(emerging_row["evidence_gap"]["primary_gap"], "missing_cross_atom_support")
        self.assertTrue(emerging_row["evidence_gap"]["missing_writeback_confirmation"])

    def test_learning_apply_is_idempotent_for_same_chain_state(self):
        brain = self.make_brain()
        ingest_a = brain.ingest_text({
            "title": "idem a",
            "text": "原子甲。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        ingest_b = brain.ingest_text({
            "title": "idem b",
            "text": "原子乙。",
            "source_type": "manual",
            "reliability": 0.8,
        })
        atom_a = ingest_a["atoms"][0]["id"]
        atom_b = ingest_b["atoms"][0]["id"]
        base_importance = ingest_a["atoms"][0]["importance"]

        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_a],
            "summary": "第一次风险说明不足。",
            "source_record_id": atom_a,
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })
        brain.learning_entry({
            "entry_type": "manual_learning",
            "target_type": "atom",
            "target_ids": [atom_b],
            "summary": "第二次风险说明不足。",
            "source_record_id": atom_b,
            "lessons": ["风险说明要明确"],
            "improvement_items": ["补充风险说明"],
        })

        first = brain.apply_learning_chains({"limit": 5, "min_count": 2})
        first_atom = next(item for item in first["updated_atoms"] if item["id"] == atom_a)
        first_importance = first_atom["importance"]
        first_refs = list(first_atom["metadata"]["learning_chain_refs"])

        second = brain.apply_learning_chains({"limit": 5, "min_count": 2})
        second_atom = next(item for item in second["updated_atoms"] if item["id"] == atom_a)
        self.assertEqual(second_atom["importance"], first_importance)
        self.assertEqual(second_atom["metadata"]["learning_chain_refs"], first_refs)
        self.assertEqual(len(second["created_relations"]), 0)
        self.assertEqual(len(second["updated_relations"]), 0)
        self.assertGreaterEqual(len(second["confirmed_relations"]), 2)
        second_audit = next(item for item in second["atom_apply_audit"] if item["atom_id"] == atom_a)
        self.assertIn("风险说明要明确", second_audit["unchanged_chain_refs"])
        overview = brain.writeback_overview({"limit": 5})
        atom_row = next(item for item in overview["top_writeback_atoms"] if item["atom_id"] == atom_a)
        self.assertEqual(atom_row["latest_apply_state"], "confirmed_only")
        self.assertGreaterEqual(overview["latest_apply_buckets"]["confirmed_only_count"], 2)
        self.assertGreater(first_importance, base_importance)


class GovernanceTests(unittest.TestCase):
    def test_live_trade_requires_approval(self):
        policy = GovernancePolicy()
        approval = policy.assess_action("live_trade", {})
        self.assertTrue(approval.requires_approval)
        self.assertEqual(approval.risk_level, "high")


if __name__ == "__main__":
    unittest.main()
