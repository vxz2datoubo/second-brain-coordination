"""
super_strategy.py - 超级战略分析引擎
"""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, Counter


@dataclass
class StrategicDecision:
    decision_id: str
    timestamp: str
    situation: str
    context: dict
    recommended_action: str = ""
    confidence: float = 0.0
    risk_score: float = 0.0
    perspectives: List[dict] = field(default_factory=list)
    mental_model_insights: List[dict] = field(default_factory=list)
    game_analysis: Optional[dict] = None
    detective_report: Optional[dict] = None
    scenario_plan: Optional[dict] = None
    risks: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    biases_detected: List[dict] = field(default_factory=list)
    second_order_effects: List[dict] = field(default_factory=list)
    alternatives: List[dict] = field(default_factory=list)
    monitoring_plan: List[dict] = field(default_factory=list)
    outcome: Optional[str] = None
    was_correct: Optional[bool] = None


@dataclass
class LongTermThesis:
    thesis_id: str
    stock: str
    bull_case: str
    bear_case: str
    key_theses: List[str] = field(default_factory=list)
    catalysts: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    timeframe: str = "1-3年"
    milestones: List[dict] = field(default_factory=list)
    conviction_level: float = 0.5
    last_review: str = ""
    status: str = "active"


class SuperStrategyEngine:
    def __init__(self, graph, mental_models, game_theory, detective, scenario, anti_gaming, cognitive, reason, data_dir: Path):
        self.graph = graph
        self.mental_models = mental_models
        self.game_theory = game_theory
        self.detective = detective
        self.scenario = scenario
        self.anti_gaming = anti_gaming
        self.cognitive = cognitive
        self.reason = reason
        self.data_dir = data_dir
        self.state_path = data_dir / "super_strategy_state.json"
        self.state = self._load()
    
    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"decisions": [], "theses": {}, "meta": {"total_decisions": 0, "correct_predictions": 0, "accuracy_rate": 0.0}}
    
    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def analyze(self, situation: str, context: dict, mode: str = "comprehensive") -> StrategicDecision:
        decision_id = str(uuid.uuid4())[:8]
        decision = StrategicDecision(decision_id=decision_id, timestamp=datetime.now().isoformat(), situation=situation, context=context)
        
        # 1. 认知偏差检测
        decision.biases_detected = self._detect_cognitive_biases(situation, context)
        
        # 2. 心智模型分析
        decision.mental_model_insights = self._analyze_with_mental_models(situation, context)
        
        # 3. 博弈论分析
        decision.game_analysis = self._analyze_game(situation, context)
        
        # 4. 市场侦探
        decision.detective_report = self._analyze_detective(situation, context)
        
        # 5. 情景推演
        decision.scenario_plan = self._analyze_scenarios(situation, context)
        
        # 6. 二阶思维
        decision.second_order_effects = self._analyze_second_order(situation, context)
        
        # 7. 备选方案
        decision.alternatives = self._generate_alternatives(decision, context)
        
        # 8. 综合决策
        decision = self._synthesize_decision(decision, context)
        
        # 9. 监控计划
        decision.monitoring_plan = self._generate_monitoring_plan(decision, context)
        
        self._record_decision(decision)
        return decision
    
    def _detect_cognitive_biases(self, situation: str, context: dict) -> List[dict]:
        return self.mental_models.detect_bias(situation)
    
    def _analyze_with_mental_models(self, situation: str, context: dict) -> List[dict]:
        return self.mental_models.multi_perspective_analysis(situation, num_perspectives=5)
    
    def _analyze_game(self, situation: str, context: dict) -> Optional[dict]:
        try:
            price_data = {"open": context.get("current_price", 0) * 0.99, "high": context.get("current_price", 0) * 1.02, "low": context.get("current_price", 0) * 0.98, "close": context.get("current_price", 0), "change_pct": context.get("change_pct", 0)}
            volume_data = {"volume": context.get("volume", 0), "avg_volume": context.get("avg_volume", context.get("volume", 1)), "vwap": context.get("current_price", 0)}
            result = self.game_theory.analyze_market_game(context.get("stock", ""), price_data, volume_data, context.get("news", []))
            return {"game_type": result.detected_pattern, "confidence": result.confidence, "action": result.recommended_action, "risk_signals": result.risk_signals, "opportunities": result.opportunities}
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_detective(self, situation: str, context: dict) -> Optional[dict]:
        try:
            price_history = [{"open": context.get("current_price", 0) * 0.99, "close": context.get("current_price", 0), "change_pct": context.get("change_pct", 0)} for _ in range(10)]
            volume_history = [{"volume": context.get("avg_volume", context.get("volume", 1))} for _ in range(10)]
            volume_history[-1]["volume"] = context.get("volume", 0)
            report = self.detective.investigate(context.get("stock", ""), price_history, volume_history, None, context.get("news", []))
            return {"has_mainforce": report.has_mainforce, "confidence": report.confidence, "mainforce_type": report.mainforce_type, "verdict": report.verdict, "risk_signals": report.risk_signals, "opportunities": report.opportunities}
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_scenarios(self, situation: str, context: dict) -> Optional[dict]:
        try:
            market_state = {"trend": context.get("market_trend", "neutral"), "volatility": context.get("volatility", "medium"), "sentiment": context.get("market_sentiment", "neutral")}
            plan = self.scenario.create_scenario_plan(context.get("stock", ""), context.get("current_price", 0), market_state, context.get("position", None))
            return {"scenarios": [{"name": s.name, "prob": s.probability, "impact": s.impact} for s in plan.scenarios], "strategy": plan.recommended_strategy, "risk_limit": plan.risk_limit}
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_second_order(self, situation: str, context: dict) -> List[dict]:
        effects = []
        if context.get("change_pct", 0) > 3:
            effects.append({"order": "一阶", "effect": "股价上涨", "second_order": "追涨可能面临回调", "third_order": "主力可能借机出货"})
        if context.get("volume", 0) > context.get("avg_volume", 0) * 1.5:
            effects.append({"order": "一阶", "effect": "放量", "second_order": "主力参与", "third_order": "但也可能是出货"})
        return effects
    
    def _generate_alternatives(self, decision: StrategicDecision, context: dict) -> List[dict]:
        return [
            {"name": "激进方案", "action": self._get_aggressive_action(decision), "risk": "高", "condition": "需要高置信度确认", "max_loss": "-3%"},
            {"name": "标准方案", "action": decision.recommended_action, "risk": "中", "condition": "当前最优选择", "max_loss": "-2%"},
            {"name": "保守方案", "action": "观望等待明确信号", "risk": "低", "condition": "不确定性高时选择", "max_loss": "0%"}
        ]
    
    def _get_aggressive_action(self, decision: StrategicDecision) -> str:
        if decision.game_analysis and decision.game_analysis.get("action"):
            return "加倍执行: {decision.game_analysis[\'action\']}"
        return decision.recommended_action
    
    def _synthesize_decision(self, decision: StrategicDecision, context: dict) -> StrategicDecision:
        all_actions = []
        all_confidences = []
        all_risks = []
        all_opportunities = []
        
        if decision.game_analysis and "action" in decision.game_analysis:
            all_actions.append(decision.game_analysis["action"])
            all_confidences.append(decision.game_analysis.get("confidence", 0.5))
            all_risks.extend(decision.game_analysis.get("risk_signals", []))
            all_opportunities.extend(decision.game_analysis.get("opportunities", []))
        
        if decision.detective_report:
            all_risks.extend(decision.detective_report.get("risk_signals", []))
            all_opportunities.extend(decision.detective_report.get("opportunities", []))
        
        if decision.scenario_plan:
            all_actions.append(decision.scenario_plan.get("strategy", ""))
        
        for insight in decision.mental_model_insights:
            if insight.get("analysis", {}).get("action_recommendation"):
                all_actions.append(insight["analysis"]["action_recommendation"])
        
        if all_confidences:
            decision.confidence = min(0.95, sum(all_confidences) / len(all_confidences))
        else:
            decision.confidence = 0.5
        
        decision.risks = list(set(all_risks))[:5]
        decision.opportunities = list(set(all_opportunities))[:5]
        
        if all_actions:
            action_counter = Counter(all_actions)
            decision.recommended_action = action_counter.most_common(1)[0][0]
        
        decision.risk_score = self._calculate_risk_score(decision, context)
        return decision
    
    def _calculate_risk_score(self, decision: StrategicDecision, context: dict) -> float:
        score = 0.5
        if decision.biases_detected:
            score += len(decision.biases_detected) * 0.05
        if decision.risks:
            score += len(decision.risks) * 0.03
        if abs(context.get("change_pct", 0)) > 5:
            score += 0.1
        if decision.confidence < 0.5:
            score += 0.1
        return min(1.0, max(0.0, score))
    
    def _generate_monitoring_plan(self, decision: StrategicDecision, context: dict) -> List[dict]:
        plan = []
        if "持有" in decision.recommended_action or "加仓" in decision.recommended_action:
            plan.append({"what": "止损线", "condition": "跌破成本价3%", "action": "减仓50%"})
            plan.append({"what": "止盈线", "condition": "盈利达到5%", "action": "考虑减仓"})
        for risk in decision.risks[:2]:
            plan.append({"what": "风险: {risk[:20]}", "condition": "如果出现", "action": "重新评估"})
        return plan
    
    def _record_decision(self, decision: StrategicDecision):
        self.state["decisions"].append({"decision_id": decision.decision_id, "timestamp": decision.timestamp, "situation": decision.situation, "action": decision.recommended_action, "confidence": decision.confidence, "risk_score": decision.risk_score, "outcome": None, "was_correct": None})
        if len(self.state["decisions"]) > 500:
            self.state["decisions"] = self.state["decisions"][-500:]
        self.state["meta"]["total_decisions"] += 1
        self._save()
    
    def record_outcome(self, decision_id: str, outcome: str, was_correct: bool):
        for record in reversed(self.state["decisions"]):
            if record["decision_id"] == decision_id:
                record["outcome"] = outcome
                record["was_correct"] = was_correct
                break
        if was_correct:
            self.state["meta"]["correct_predictions"] += 1
        total = self.state["meta"]["total_decisions"]
        correct = self.state["meta"]["correct_predictions"]
        self.state["meta"]["accuracy_rate"] = correct / max(total, 1)
        self._save()
    
    def format_decision(self, decision: StrategicDecision) -> str:
        lines = []
        lines.append("{'='*60}")
        lines.append(" 超级战略分析报告")
        lines.append("{'='*60}")
        lines.append("决策ID: {decision.decision_id}")
        lines.append("时间: {decision.timestamp}")
        lines.append("情境: {decision.situation}")
        lines.append("置信度: {decision.confidence:.0%}")
        lines.append("风险评分: {decision.risk_score:.0%}")
        
        if decision.biases_detected:
            lines.append("认知偏差检测:")
            for bias in decision.biases_detected:
                lines.append("  - {bias[\'bias\']}: {bias[\'antidote\']}")
        
        if decision.mental_model_insights:
            lines.append("顶级智慧视角:")
            for insight in decision.mental_model_insights[:3]:
                lines.append("  [{insight[\'philosopher\']}] {insight[\'model_name\']}: {insight.get(\'analysis\', {}).get(\'action_recommendation\', \'\')}")
        
        if decision.game_analysis and "error" not in decision.game_analysis:
            lines.append("博弈分析: {decision.game_analysis.get(\'game_type\', \'未知\')} - {decision.game_analysis.get(\'action\', \'\')}")
        
        if decision.detective_report and "error" not in decision.detective_report:
            if decision.detective_report.get("has_mainforce"):
                lines.append("主力: {decision.detective_report.get(\'mainforce_type\', \'未知\')} - {decision.detective_report.get(\'verdict\', \'\')}")
        
        if decision.risks:
            lines.append("风险信号:")
            for risk in decision.risks[:3]:
                lines.append("  - {risk}")
        
        if decision.opportunities:
            lines.append("机会提示:")
            for opp in decision.opportunities[:3]:
                lines.append("  - {opp}")
        
        lines.append("最终决策: {decision.recommended_action}")
        
        if decision.alternatives:
            lines.append("备选方案:")
            for alt in decision.alternatives:
                lines.append("  [{alt[\'name\']}] {alt[\'action\']} (风险:{alt[\'risk\']})")
        
        return "\n".join(lines)
    
    def get_stats(self) -> dict:
        return {"total_decisions": self.state["meta"]["total_decisions"], "accuracy_rate": self.state["meta"]["accuracy_rate"], "recent_decisions": self.state["decisions"][-10:], "mental_models_stats": self.mental_models.get_stats() if self.mental_models else {}}