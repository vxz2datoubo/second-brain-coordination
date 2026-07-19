"""
cognitive_engine.py — 第二大脑核心认知引擎

让AI大脑具备独立思考、跨领域联想、闭环学习的能力
"""

import json
import math
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, List, Dict
from dataclasses import dataclass, field


@dataclass
class CognitiveSignal:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    topic: str = ""
    context: dict = field(default_factory=dict)
    query: str = ""
    retrieved_nodes: list = field(default_factory=list)
    associated_nodes: list = field(default_factory=list)
    reasoning_chain: list = field(default_factory=list)
    decision: str = ""
    confidence: float = 0.0
    alternatives: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    blind_spot_detected: bool = False
    reasoning_gaps: list = field(default_factory=list)
    self_correction: str = ""


class CognitiveEngine:
    """第二大脑核心认知引擎
    
    设计原则:
    - 像精英大脑一样思考：慢速、深思熟虑、多角度验证
    - 永不重复同样的错误：每个错误都转化为规则
    - 跨领域联想：从一个知识点自然延伸到相关领域
    - 闭环学习：决策→执行→复盘→改进
    """
    
    COGNITIVE_MODES = {
        "deliberate": {"speed": "slow", "depth": "deep", "verify": True},
        "intuitive": {"speed": "fast", "depth": "shallow", "verify": False},
        "critical": {"speed": "slow", "depth": "deep", "verify": True},
        "creative": {"speed": "medium", "depth": "medium", "verify": False},
    }
    
    def __init__(self, graph, memory, digester, searcher, health, human_thinking, self_verify, data_dir: Path):
        self.graph = graph
        self.memory = memory
        self.digester = digester
        self.searcher = searcher
        self.health = health
        self.human = human_thinking
        self.verify = self_verify
        self.data_dir = data_dir
        self.state_path = data_dir / "cognitive_state.json"
        self.state = self._load()
        self._cache = {}
        self._cache_ttl = 300
    
    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "cognitive_history": [],
                "decision_outcomes": [],
                "learned_patterns": {},
                "blind_spots": [],
                "meta": {"total_decisions": 0, "correct_decisions": 0, "accuracy_rate": 0.0, "last_update": ""}
            }
    
    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def think(self, topic: str, context: Optional[dict] = None, mode: str = "deliberate", depth: int = 3, require_cross_domain: bool = True) -> CognitiveSignal:
        """核心思考方法"""
        signal = CognitiveSignal(topic=topic, context=context or {})
        signal.retrieved_nodes = self._retrieve_knowledge(topic, depth)
        if require_cross_domain:
            signal.associated_nodes = self._cross_domain_associate(signal.retrieved_nodes, depth)
        signal.reasoning_chain = self._build_reasoning_chain(topic, signal.retrieved_nodes, signal.associated_nodes, mode)
        signal = self._meta_cognition_check(signal, mode)
        signal.decision, signal.confidence, signal.alternatives = self._generate_decision(signal, mode)
        signal.warnings = self._generate_warnings(signal)
        self._record_cognition(signal)
        return signal
    
    def _retrieve_knowledge(self, topic: str, depth: int) -> list:
        results = []
        if self.searcher:
            results.extend(self.searcher.search(topic, top_k=10) or [])
        if depth >= 2:
            for node in results[:5]:
                neighbors = self.graph.get_neighbors(node.get("id", ""), depth=1)
                for nid, neighbor in neighbors.get("nodes", {}).items():
                    if nid not in [r.get("id") for r in results]:
                        neighbor["relevance"] = "extended"
                        results.append(neighbor)
        seen_ids = set()
        unique_results = [r for r in results if r.get("id") and r["id"] not in seen_ids and not seen_ids.add(r["id"])]
        return unique_results[:15]
    
    def _cross_domain_associate(self, seed_nodes: list, depth: int) -> list:
        if not seed_nodes:
            return []
        seed_ids = [n.get("id") for n in seed_nodes[:5] if n.get("id")]
        associations = self.human.associative_recall(seed_ids, max_depth=depth, max_results=10) if self.human else []
        seed_categories = {n.get("category") for n in seed_nodes}
        cross_domain = []
        for assoc in associations:
            assoc_node = self.graph.get_node(assoc.get("id"))
            if assoc_node and assoc_node.get("category") not in seed_categories:
                assoc["association_type"] = "cross_domain"
                cross_domain.append(assoc)
        return cross_domain[:8]
    
    def _build_reasoning_chain(self, topic: str, retrieved: list, associated: list, mode: str) -> list:
        chain = []
        if retrieved:
            chain.append({"step": 1, "type": "foundation", "content": f"基于{len(retrieved)}个相关知识节点", "nodes": [n.get("id") for n in retrieved[:3]]})
        if associated:
            chain.append({"step": 2, "type": "cross_domain", "content": f"发现{len(associated)}个跨领域关联", "nodes": [n.get("id") for n in associated[:3]]})
        warnings = self._check_risks(topic, retrieved)
        if warnings:
            chain.append({"step": 3, "type": "risk_assessment", "content": f"识别{len(warnings)}个潜在风险", "warnings": warnings})
        lessons = self._check_lessons(topic)
        if lessons:
            chain.append({"step": 4, "type": "lesson_check", "content": f"命中{len(lessons)}条历史教训", "lessons": lessons})
        chain.append({"step": len(chain) + 1, "type": "conclusion", "content": "综合分析得出结论"})
        return chain
    
    def _check_risks(self, topic: str, nodes: list) -> list:
        risks = []
        risk_keywords = {"追高": "存在追高/FOMO风险", "满仓": "满仓/重仓风险", "补仓": "补仓需基于新证据", "单一": "单一信息源风险", "消息": "消息驱动需交叉验证"}
        text = topic.lower()
        for node in nodes:
            text += " " + node.get("title", "").lower() + " " + node.get("content", "").lower()
        for keyword, risk in risk_keywords.items():
            if keyword in text and risk not in risks:
                risks.append(risk)
        return risks
    
    def _check_lessons(self, topic: str) -> list:
        lessons_file = Path(self.data_dir).parent / "second-brain" / "lessons.md"
        if not lessons_file.exists():
            return []
        try:
            content = lessons_file.read_text(encoding="utf-8")
            matched = []
            for keyword in ["追高", "卖出后", "涨停", "开盘"]:
                if keyword in topic and keyword in content:
                    matched.append({"keyword": keyword, "type": "negative_lesson"})
            return matched
        except:
            return []
    
    def _meta_cognition_check(self, signal: CognitiveSignal, mode: str) -> CognitiveSignal:
        gaps = []
        if len(signal.retrieved_nodes) < 3:
            gaps.append("信息检索不足，建议扩展搜索范围")
        has_negative = any("不要" in n.get("title", "") or "教训" in n.get("title", "") for n in signal.retrieved_nodes)
        if not has_negative and signal.topic:
            gaps.append("未找到反面证据，建议主动搜索负面案例")
        if not signal.associated_nodes and len(signal.retrieved_nodes) > 5:
            gaps.append("思考局限于单一领域，建议联想其他领域")
        signal.reasoning_gaps = gaps
        signal.blind_spot_detected = len(gaps) > 0
        if gaps:
            signal.self_correction = f"识别到{len(gaps)}个推理缺口，需要补充信息"
        return signal
    
    def _generate_decision(self, signal: CognitiveSignal, mode: str) -> tuple:
        score = 0
        score += min(40, len(signal.retrieved_nodes) * 5)
        score += min(30, len(signal.associated_nodes) * 8)
        score += 10 if signal.warnings else 0
        score += 20 if not signal.blind_spot_detected else 5
        confidence = score / 100.0
        if confidence >= 0.8:
            decision = f"高置信度决策：{signal.topic}"
        elif confidence >= 0.6:
            decision = f"中等置信度决策，建议进一步验证：{signal.topic}"
        else:
            decision = f"低置信度，需要更多信息：{signal.topic}"
        alternatives = [{"option": assoc.get("title", ""), "type": "cross_domain_alternative"} for assoc in signal.associated_nodes[:3]]
        return decision, confidence, alternatives
    
    def _generate_warnings(self, signal: CognitiveSignal) -> list:
        warnings = []
        for step in signal.reasoning_chain:
            if step.get("type") == "risk_assessment":
                warnings.extend(step.get("warnings", []))
            if step.get("type") == "lesson_check":
                for lesson in step.get("lessons", []):
                    warnings.append(f"命中教训: {lesson.get('keyword')}")
        if signal.blind_spot_detected:
            warnings.append(f"存在{len(signal.reasoning_gaps)}个推理盲点")
        return warnings
    
    def _record_cognition(self, signal: CognitiveSignal):
        self.state["cognitive_history"].append({"id": signal.id, "timestamp": signal.timestamp, "topic": signal.topic, "confidence": signal.confidence, "has_warnings": len(signal.warnings) > 0, "blind_spot": signal.blind_spot_detected})
        if len(self.state["cognitive_history"]) > 100:
            self.state["cognitive_history"] = self.state["cognitive_history"][-100:]
        self._save()
    
    def make_decision(self, decision_type: str, context: dict, options: list, reasoning: str = "") -> dict:
        topic = context.get("topic", f"{decision_type}决策")
        signal = self.think(topic, context, mode="deliberate")
        chosen = options[0] if options else signal.decision
        for opt in options:
            if not any(w for w in signal.warnings if opt in str(w)):
                chosen = opt
                break
        decision_id = str(uuid.uuid4())[:8]
        self.state["decision_outcomes"].append({"id": decision_id, "timestamp": datetime.now().isoformat(), "type": decision_type, "context": context, "options": options, "chosen": chosen, "reasoning": reasoning or signal.self_correction, "confidence": signal.confidence, "warnings": signal.warnings, "outcome": None})
        self.state["meta"]["total_decisions"] += 1
        self._save()
        return {"decision_id": decision_id, "chosen": chosen, "confidence": signal.confidence, "warnings": signal.warnings, "reasoning_chain": signal.reasoning_chain, "alternatives": signal.alternatives}
    
    def record_outcome(self, decision_id: str, outcome: str, was_correct: bool, lessons: Optional[list] = None) -> dict:
        decision = next((d for d in self.state["decision_outcomes"] if d["id"] == decision_id), None)
        if not decision:
            return {"error": "decision not found"}
        decision["outcome"] = outcome
        decision["was_correct"] = was_correct
        if was_correct:
            self.state["meta"]["correct_decisions"] += 1
        else:
            self._learn_from_error(decision, outcome, lessons or [])
        total = self.state["meta"]["total_decisions"]
        correct = self.state["meta"]["correct_decisions"]
        self.state["meta"]["accuracy_rate"] = correct / total if total > 0 else 0
        if was_correct:
            self._learn_pattern(decision)
        self._save()
        return {"success": True, "accuracy": self.state["meta"]["accuracy_rate"], "lessons_learned": lessons or []}
    
    def _learn_from_error(self, decision: dict, outcome: str, lessons: list):
        blind_spot = {"id": str(uuid.uuid4())[:8], "timestamp": datetime.now().isoformat(), "decision_type": decision.get("type"), "context": decision.get("context", {}), "chosen": decision.get("chosen"), "outcome": outcome, "reasoning": decision.get("reasoning"), "lessons": lessons}
        self.state["blind_spots"].append(blind_spot)
        if lessons:
            for lesson in lessons:
                rule_key = f"rule_{decision.get('type')}_{len(self.state['learned_patterns'])}"
                self.state["learned_patterns"][rule_key] = {"type": "learned_rule", "trigger": decision.get("context", {}), "lesson": lesson, "created_at": datetime.now().isoformat(), "success_count": 0, "failure_count": 1}
        recent_blind_spots = [bs for bs in self.state["blind_spots"] if bs.get("decision_type") == decision.get("type")]
        if len(recent_blind_spots) >= 5:
            self.state["learned_patterns"]["systemic_" + decision.get("type", "unknown")] = {"type": "systemic_blind_spot", "decision_type": decision.get("type"), "error_count": len(recent_blind_spots), "recommendation": f"在{decision.get('type')}决策中存在系统性盲点，建议全面检查"}
    
    def _learn_pattern(self, decision: dict):
        rule_key = f"success_{decision.get('type')}_{len(self.state['learned_patterns'])}"
        existing_key = next((key for key, pattern in self.state["learned_patterns"].items() if pattern.get("type") == "learned_rule" and pattern.get("trigger") == decision.get("context")), None)
        if existing_key:
            self.state["learned_patterns"][existing_key]["success_count"] += 1
        else:
            self.state["learned_patterns"][rule_key] = {"type": "success_pattern", "trigger": decision.get("context"), "chosen": decision.get("chosen"), "created_at": datetime.now().isoformat(), "success_count": 1, "failure_count": 0}
    
    def get_cognition_stats(self) -> dict:
        return {"total_cognitions": len(self.state["cognitive_history"]), "total_decisions": self.state["meta"]["total_decisions"], "accuracy_rate": self.state["meta"]["accuracy_rate"], "learned_rules": len([p for p in self.state["learned_patterns"].values() if p.get("type") == "learned_rule"]), "success_patterns": len([p for p in self.state["learned_patterns"].values() if p.get("type") == "success_pattern"]), "blind_spots": len(self.state["blind_spots"])}
    
    def get_recent_decisions(self, limit: int = 10) -> list:
        return list(reversed(self.state["decision_outcomes"][-limit:]))
    
    def get_learned_rules(self) -> list:
        return list(self.state["learned_patterns"].values())
    
    def check_learned_rules(self, context: dict) -> list:
        matched = []
        for key, rule in self.state["learned_patterns"].items():
            if rule.get("type") == "learned_rule":
                trigger = rule.get("trigger", {})
                match = all(context.get(k) == v for k, v in trigger.items() if v)
                if match:
                    matched.append({"rule": rule.get("lesson", ""), "source": "learned", "confidence": rule.get("success_count", 0) / max(1, rule.get("success_count", 0) + rule.get("failure_count", 0))})
        return matched
    
    def suggest_improvements(self) -> list:
        suggestions = []
        blind_spot_types = {}
        for bs in self.state["blind_spots"]:
            t = bs.get("decision_type", "unknown")
            blind_spot_types[t] = blind_spot_types.get(t, 0) + 1
        for dtype, count in blind_spot_types.items():
            if count >= 3:
                suggestions.append(f"{dtype}决策存在{count}次错误，建议重点检查相关知识库")
        accuracy = self.state["meta"]["accuracy_rate"]
        if accuracy < 0.5:
            suggestions.append("准确率低于50%，建议减少决策频率，先加强知识积累")
        elif accuracy > 0.8:
            suggestions.append("准确率较高，可以考虑适度扩大决策范围")
        learned_rules = [p for p in self.state["learned_patterns"].values() if p.get("type") == "learned_rule"]
        if learned_rules:
            suggestions.append(f"已从错误中学习{len(learned_rules)}条规则")
        return suggestions
    
    def format_think_output(self, signal: CognitiveSignal) -> str:
        lines = [f"🧠 认知思考报告", f"{'='*50}", f"主题: {signal.topic}", f"置信度: {signal.confidence:.1%}", ""]
        if signal.reasoning_chain:
            lines.append("📋 推理链:")
            for step in signal.reasoning_chain:
                lines.append(f"  {step.get('step')}. [{step.get('type')}] {step.get('content')}")
            lines.append("")
        if signal.associated_nodes:
            lines.append("🔗 跨领域联想:")
            for node in signal.associated_nodes[:3]:
                lines.append(f"  → {node.get('title', '')[:40]} (关联度: {node.get('activation', 0):.2f})")
            lines.append("")
        if signal.warnings:
            lines.append("⚠️ 风险警告:")
            for w in signal.warnings:
                lines.append(f"  • {w}")
            lines.append("")
        if signal.reasoning_gaps:
            lines.append("🔍 推理盲点:")
            for gap in signal.reasoning_gaps:
                lines.append(f"  • {gap}")
            lines.append("")
        lines.append("🎯 最终决策:")
        lines.append(f"  {signal.decision}")
        if signal.alternatives:
            lines.append("")
            lines.append("📌 备选方案:")
            for alt in signal.alternatives[:3]:
                lines.append(f"  • {alt.get('option', '')}")
        return "\n".join(lines)
