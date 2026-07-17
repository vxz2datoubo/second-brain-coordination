"""
super_cognitive.py — 超级认知引擎
==========================================
整合所有高级认知能力，构建真正的"超级人类大脑"。
这不是简单的模块堆砌，而是让各能力协同工作，产生1+1>2的效果。

核心理念：
1. 整合性思考：博弈论+市场侦探+消息验证+情景推演+反操纵检测
2. 元认知监控：思考自己的思考，识别盲点和偏差
3. 快速决策 vs 慢速思考：适时切换模式
4. 知识融合：跨领域知识的创新组合

设计参考：
- Kahneman的双系统理论（系统1快思考、系统2慢思考）
- 大奖章基金的量化博弈思维
- 桥水达里奥的极度透明和有意义的工作
"""

import json
import uuid
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class CognitiveSnapshot:
    """认知快照"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    situation: str = ""                    # 当前情境
    questions: List[str] = field(default_factory=list)  # 关键问题
    analysis_results: Dict[str, Any] = field(default_factory=dict)  # 各引擎分析结果
    final_judgment: str = ""             # 最终判断
    confidence: float = 0.0              # 置信度
    reasoning_chain: List[dict] = field(default_factory=list)  # 推理链
    warnings: List[str] = field(default_factory=list)   # 警告
    opportunities: List[str] = field(default_factory=list)  # 机会
    recommended_action: str = ""         # 推荐行动
    alternatives: List[dict] = field(default_factory=list)  # 备选方案
    self_correction: str = ""            # 自我修正


@dataclass
class MarketContext:
    """市场上下文"""
    stock: str = ""
    current_price: float = 0.0
    change_pct: float = 0.0
    volume: float = 0.0
    avg_volume: float = 0.0
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    market_trend: str = "neutral"        # up/down/neutral
    market_sentiment: str = "neutral"    # bullish/bearish/neutral
    volatility: str = "medium"           # high/medium/low
    recent_news: List[dict] = field(default_factory=list)
    position: Optional[dict] = None      # 持仓情况


@dataclass
class ThinkingMode:
    """思考模式"""
    mode: str = "deliberate"             # deliberate/intuitive/critical/creative
    speed: str = "slow"                  # slow/medium/fast
    depth: int = 3                       # 思考深度
    verify: bool = True                  # 是否验证
    cross_domain: bool = True            # 是否跨域思考


class SuperCognitiveEngine:
    """超级认知引擎
    
    整合以下能力：
    1. 博弈论引擎 — 分析市场博弈结构
    2. 市场侦探 — 识别主力行为和资金流向
    3. 消息验证 — 判断消息真伪和时效性
    4. 情景推演 — 多路径未来推演
    5. 反坐庄检测 — 识别庄家陷阱
    6. 知识图谱 — 历史知识和经验
    7. 人类思维模拟 — 记忆、联想、推理
    
    思考流程：
    1. 理解情境 — 当前市场状态
    2. 提出问题 — 需要回答的关键问题
    3. 多维度分析 — 各引擎分别分析
    4. 综合判断 — 整合所有分析
    5. 元认知检查 — 思考是否有盲点
    6. 决策输出 — 明确的行动建议
    """
    
    def __init__(
        self,
        graph,
        game_theory,
        detective,
        news_verifier,
        scenario_planner,
        anti_gaming,
        cognitive,
        reason,
        data_dir: Path
    ):
        # 核心依赖
        self.graph = graph
        self.game_theory = game_theory
        self.detective = detective
        self.news_verifier = news_verifier
        self.scenario_planner = scenario_planner
        self.anti_gaming = anti_gaming
        self.cognitive = cognitive
        self.reason = reason
        self.data_dir = data_dir
        
        self.state_path = data_dir / "super_cognitive_state.json"
        self.state = self._load()
    
    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "cognitive_history": [],
                "decision_records": [],
                "meta": {
                    "total_cognitions": 0,
                    "correct_decisions": 0,
                    "accuracy_rate": 0.0
                }
            }
    
    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    # ========== 核心思考方法 ==========
    
    def think(
        self,
        situation: str,
        context: MarketContext,
        mode: str = "deliberate",
        depth: int = 3
    ) -> CognitiveSnapshot:
        """超级思考
        
        Args:
            situation: 当前情境描述
            context: 市场上下文
            mode: 思考模式
            depth: 思考深度
        
        Returns:
            CognitiveSnapshot: 认知快照
        """
        snapshot = CognitiveSnapshot()
        snapshot.situation = situation
        snapshot.questions = self._generate_questions(situation, context)
        
        # 选择思考模式
        think_mode = self._select_mode(mode, situation, context)
        
        # 1. 博弈论分析
        if think_mode.verify:
            game_result = self._analyze_game_theory(context)
            snapshot.analysis_results["game_theory"] = game_result
        
        # 2. 市场侦探分析
        if think_mode.verify:
            detective_result = self._analyze_with_detective(context)
            snapshot.analysis_results["market_detective"] = detective_result
        
        # 3. 反坐庄检测
        if think_mode.verify:
            anti_gaming_result = self._analyze_with_anti_gaming(context)
            snapshot.analysis_results["anti_gaming"] = anti_gaming_result
        
        # 4. 消息验证（如果有新闻）
        if context.recent_news:
            news_result = self._analyze_news(context)
            snapshot.analysis_results["news_verification"] = news_result
        
        # 5. 情景推演
        scenario_result = self._analyze_scenarios(context)
        snapshot.analysis_results["scenarios"] = scenario_result
        
        # 6. 知识检索
        knowledge_result = self._retrieve_knowledge(situation, context)
        snapshot.analysis_results["knowledge"] = knowledge_result
        
        # 7. 跨领域推理
        if think_mode.cross_domain:
            cross_domain_result = self._reason_cross_domain(situation, knowledge_result)
            snapshot.analysis_results["cross_domain"] = cross_domain_result
        
        # 8. 构建推理链
        snapshot.reasoning_chain = self._build_reasoning_chain(snapshot.analysis_results)
        
        # 9. 元认知检查
        snapshot = self._meta_cognitive_check(snapshot, think_mode)
        
        # 10. 生成最终判断
        snapshot = self._generate_final_judgment(snapshot, context)
        
        # 11. 生成备选方案
        snapshot.alternatives = self._generate_alternatives(snapshot, context)
        
        # 记录
        self._record_cognition(snapshot)
        
        return snapshot
    
    def _select_mode(
        self,
        requested_mode: str,
        situation: str,
        context: MarketContext
    ) -> ThinkingMode:
        """选择思考模式"""
        mode = ThinkingMode()
        
        # 基础模式
        mode_map = {
            "deliberate": {"speed": "slow", "depth": 3, "verify": True, "cross_domain": True},
            "intuitive": {"speed": "fast", "depth": 1, "verify": False, "cross_domain": False},
            "critical": {"speed": "slow", "depth": 3, "verify": True, "cross_domain": True},
            "creative": {"speed": "medium", "depth": 2, "verify": False, "cross_domain": True}
        }
        
        defaults = mode_map.get(requested_mode, mode_map["deliberate"])
        mode.mode = requested_mode
        mode.speed = defaults["speed"]
        mode.depth = defaults["depth"]
        mode.verify = defaults["verify"]
        mode.cross_domain = defaults["cross_domain"]
        
        # 紧急情况自动切换
        if abs(context.change_pct) > 5:
            mode.verify = True
            mode.depth = 3
        
        # 高风险情况加强验证
        if any(kw in situation for kw in ["追高", "满仓", "重仓"]):
            mode.verify = True
            mode.cross_domain = True
        
        return mode
    
    def _generate_questions(
        self,
        situation: str,
        context: MarketContext
    ) -> List[str]:
        """生成关键问题"""
        questions = []
        
        # 基于情境生成问题
        if "涨" in situation or context.change_pct > 2:
            questions.append("这是真突破还是诱多？")
            questions.append("主力是否在出货？")
            questions.append("追高的风险有多大？")
        elif "跌" in situation or context.change_pct < -2:
            questions.append("这是洗盘还是真跌？")
            questions.append("要不要止损？")
            questions.append("是否可以抄底？")
        else:
            questions.append("当前市场博弈结构如何？")
            questions.append("主力在做什么？")
            questions.append("是否有明显的机会或风险？")
        
        # 持仓相关
        if context.position:
            questions.append("当前持仓是否安全？")
            questions.append("是否需要调整仓位？")
        
        # 新闻相关
        if context.recent_news:
            questions.append("这些消息是否可信？")
            questions.append("市场是否已消化？")
            questions.append("是否有提前泄露的可能？")
        
        return questions
    
    def _analyze_game_theory(self, context: MarketContext) -> dict:
        """博弈论分析"""
        price_data = {
            "open": context.current_price * 0.99,
            "high": context.current_price * 1.02,
            "low": context.current_price * 0.98,
            "close": context.current_price,
            "change_pct": context.change_pct
        }
        
        volume_data = {
            "volume": context.volume,
            "avg_volume": context.avg_volume,
            "vwap": context.current_price
        }
        
        try:
            game_state = self.game_theory.analyze_market_game(
                context.stock,
                price_data,
                volume_data,
                context.recent_news
            )
            
            return {
                "game_type": game_state.detected_pattern,
                "confidence": game_state.confidence,
                "action": game_state.recommended_action,
                "risk_signals": game_state.risk_signals,
                "opportunities": game_state.opportunities,
                "reasoning": [
                    {"step": r.get("step"), "content": r.get("content")}
                    for r in game_state.reasoning_chain[:3]
                ]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_with_detective(self, context: MarketContext) -> dict:
        """市场侦探分析"""
        # 构造历史数据（简化版）
        price_history = [
            {
                "open": context.current_price * 0.99,
                "high": context.current_price * 1.01,
                "low": context.current_price * 0.98,
                "close": context.current_price * (1 + context.change_pct / 100),
                "change_pct": context.change_pct
            }
            for _ in range(10)
        ]
        
        volume_history = [
            {"volume": context.avg_volume, "change_pct": 0}
            for _ in range(10)
        ]
        volume_history[-1]["volume"] = context.volume
        
        try:
            report = self.detective.investigate(
                context.stock,
                price_history,
                volume_history,
                None,
                context.recent_news
            )
            
            return {
                "has_mainforce": report.has_mainforce,
                "confidence": report.confidence,
                "mainforce_type": report.mainforce_type,
                "verdict": report.verdict,
                "risk_signals": report.risk_signals,
                "opportunities": report.opportunities
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_with_anti_gaming(self, context: MarketContext) -> dict:
        """反坐庄检测"""
        price_history = [
            {
                "open": context.current_price * 0.99,
                "high": context.current_price * 1.01,
                "low": context.current_price * 0.98,
                "close": context.current_price * (1 + context.change_pct / 100)
            }
            for _ in range(10)
        ]
        
        volume_history = [
            {"volume": context.avg_volume}
            for _ in range(10)
        ]
        volume_history[-1]["volume"] = context.volume
        
        try:
            report = self.anti_gaming.detect(
                context.stock,
                price_history,
                volume_history
            )
            
            return {
                "is_gamed": report.is_gamed,
                "confidence": report.confidence,
                "survival_score": report.survival_score,
                "patterns": [
                    {"stage": p.stage, "risk": p.risk_level}
                    for p in report.patterns
                ],
                "action": report.recommended_action,
                "warnings": report.warnings
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_news(self, context: MarketContext) -> dict:
        """消息验证"""
        if not context.recent_news:
            return {"status": "no_news"}
        
        results = []
        for news in context.recent_news[:3]:
            try:
                verification = self.news_verifier.verify(
                    news,
                    context.stock,
                    {
                        "change_pct": context.change_pct,
                        "volume_ratio": context.volume / max(context.avg_volume, 1)
                    }
                )
                
                results.append({
                    "title": news.get("title", ""),
                    "verdict": verification.verdict,
                    "authenticity": verification.authenticity_score,
                    "manipulation_score": verification.manipulation_score,
                    "prior_leakage": verification.prior_leakage
                })
            except Exception as e:
                results.append({"error": str(e)})
        
        return {"news_analysis": results}
    
    def _analyze_scenarios(self, context: MarketContext) -> dict:
        """情景推演"""
        try:
            market_state = {
                "trend": context.market_trend,
                "volatility": context.volatility,
                "sentiment": context.market_sentiment
            }
            
            plan = self.scenario_planner.create_scenario_plan(
                context.stock,
                context.current_price,
                market_state,
                context.position
            )
            
            return {
                "scenarios": [
                    {"name": s.name, "prob": s.probability, "impact": s.impact}
                    for s in plan.scenarios
                ],
                "strategy": plan.recommended_strategy,
                "risk_limit": plan.risk_limit
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _retrieve_knowledge(self, situation: str, context: MarketContext) -> dict:
        """知识检索"""
        # 使用认知引擎检索相关知识
        try:
            signal = self.cognitive.think(
                f"{context.stock} {situation}",
                {"market": context.market_trend, "sentiment": context.market_sentiment},
                mode="deliberate"
            )
            
            return {
                "relevant_nodes": [
                    {"title": n.get("title", ""), "id": n.get("id", "")}
                    for n in signal.retrieved_nodes[:5]
                ],
                "warnings": signal.warnings,
                "confidence": signal.confidence
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _reason_cross_domain(self, situation: str, knowledge_result: dict) -> dict:
        """跨领域推理"""
        try:
            result = self.reason.reason(
                situation,
                knowledge_result.get("relevant_nodes", []),
                depth=2
            )
            
            return {
                "domains": result.get("discovered_domains", []),
                "insights": result.get("insights", []),
                "reasoning_chain": result.get("reasoning_chain", [])
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _build_reasoning_chain(self, analysis_results: Dict[str, Any]) -> List[dict]:
        """构建推理链"""
        chain = []
        step = 1
        
        # 博弈论
        if "game_theory" in analysis_results and "error" not in analysis_results["game_theory"]:
            gt = analysis_results["game_theory"]
            chain.append({
                "step": step,
                "type": "game_theory",
                "content": f"博弈分析: {gt.get('game_type', '未知')}",
                "conclusion": gt.get("action", "")
            })
            step += 1
        
        # 市场侦探
        if "market_detective" in analysis_results and "error" not in analysis_results["market_detective"]:
            md = analysis_results["market_detective"]
            if md.get("has_mainforce"):
                chain.append({
                    "step": step,
                    "type": "detective",
                    "content": f"主力检测: {md.get('mainforce_type', '未知')}",
                    "conclusion": md.get("verdict", "")
                })
                step += 1
        
        # 反坐庄
        if "anti_gaming" in analysis_results and "error" not in analysis_results["anti_gaming"]:
            ag = analysis_results["anti_gaming"]
            if ag.get("is_gamed"):
                chain.append({
                    "step": step,
                    "type": "anti_gaming",
                    "content": f"风险检测: {ag.get('patterns', [{}])[0].get('stage', '未知')}",
                    "conclusion": f"生存分数: {ag.get('survival_score', 0):.0f}"
                })
                step += 1
        
        # 情景推演
        if "scenarios" in analysis_results and "error" not in analysis_results["scenarios"]:
            sc = analysis_results["scenarios"]
            if sc.get("scenarios"):
                best = max(sc["scenarios"], key=lambda x: x["prob"])
                chain.append({
                    "step": step,
                    "type": "scenario",
                    "content": f"最可能情景: {best['name']} ({best['prob']:.0%})",
                    "conclusion": sc.get("strategy", "")
                })
        
        return chain
    
    def _meta_cognitive_check(
        self,
        snapshot: CognitiveSnapshot,
        mode: ThinkingMode
    ) -> CognitiveSnapshot:
        """元认知检查"""
        warnings = []
        corrections = []
        
        # 检查点1：信息是否充足
        if len(snapshot.analysis_results) < 3:
            warnings.append("分析维度不足，可能遗漏重要信息")
        
        # 检查点2：各分析结果是否一致
        actions = []
        for key, result in snapshot.analysis_results.items():
            if isinstance(result, dict) and "action" in result:
                actions.append(result["action"])
        
        if len(set(actions)) > 2:
            warnings.append("各分析结果不一致，需要权衡")
            corrections.append("建议以风险最高的判断为准")
        
        # 检查点3：是否过度自信
        if snapshot.confidence > 0.9:
            warnings.append("置信度过高，可能存在盲点")
            corrections.append("建议降低置信度，增加安全边际")
        
        # 检查点4：是否有反面证据
        has_negative = any("风险" in str(w) or "警告" in str(w) for w in warnings)
        if not has_negative and mode.verify:
            warnings.append("未发现明显风险，可能遗漏")
        
        # 检查点5：历史经验
        # 简化的历史教训检查
        if snapshot.analysis_results.get("knowledge"):
            kn = snapshot.analysis_results["knowledge"]
            if kn.get("warnings"):
                for w in kn["warnings"]:
                    warnings.append(f"知识库警告: {w}")
        
        snapshot.warnings = warnings
        snapshot.self_correction = "; ".join(corrections) if corrections else "无需修正"
        
        return snapshot
    
    def _generate_final_judgment(
        self,
        snapshot: CognitiveSnapshot,
        context: MarketContext
    ) -> CognitiveSnapshot:
        """生成最终判断"""
        # 综合各分析结果
        all_actions = []
        all_confidences = []
        all_risks = []
        all_opportunities = []
        
        for key, result in snapshot.analysis_results.items():
            if not isinstance(result, dict):
                continue
            
            if "action" in result:
                all_actions.append(result["action"])
            if "confidence" in result:
                all_confidences.append(result["confidence"])
            if "risk_signals" in result:
                all_risks.extend(result["risk_signals"])
            if "opportunities" in result:
                all_opportunities.extend(result["opportunities"])
        
        # 综合风险
        snapshot.risk_signals = list(set(all_risks))[:5]
        
        # 综合机会
        snapshot.opportunities = list(set(all_opportunities))[:5]
        
        # 最终置信度
        if all_confidences:
            snapshot.confidence = min(0.95, sum(all_confidences) / len(all_confidences))
        
        # 最终行动建议
        if all_actions:
            # 简单投票
            action_counter = Counter(all_actions)
            snapshot.final_judgment = action_counter.most_common(1)[0][0]
        
        # 结合风险生成推荐行动
        snapshot.recommended_action = self._synthesize_action(
            snapshot.final_judgment,
            snapshot.risk_signals,
            snapshot.opportunities,
            context
        )
        
        return snapshot
    
    def _synthesize_action(
        self,
        judgment: str,
        risks: List[str],
        opportunities: List[str],
        context: MarketContext
    ) -> str:
        """综合生成行动建议"""
        # 风险优先原则
        if any("危险" in r or "止损" in r or "清仓" in r for r in risks):
            return "风险优先：减仓或清仓"
        
        if any("洗盘" in r or "假突破" in r for r in risks):
            return "警惕陷阱：观望或减仓"
        
        # 机会导向
        if opportunities and not risks:
            if "加仓" in judgment or "持有" in judgment:
                return "顺势操作：可适当加仓"
            else:
                return judgment
        
        # 默认为观望
        return judgment if judgment else "建议观望，等待明确信号"
    
    def _generate_alternatives(
        self,
        snapshot: CognitiveSnapshot,
        context: MarketContext
    ) -> List[dict]:
        """生成备选方案"""
        alternatives = []
        
        # 方案1：激进
        if snapshot.recommended_action and "减仓" not in snapshot.recommended_action:
            alternatives.append({
                "option": "激进方案",
                "action": "如果确认趋势，可加仓操作",
                "risk": "高",
                "condition": "需要突破确认且量能配合"
            })
        
        # 方案2：保守
        alternatives.append({
            "option": "保守方案",
            "action": snapshot.recommended_action,
            "risk": "中",
            "condition": "当前最优选择"
        })
        
        # 方案3：观望
        alternatives.append({
            "option": "观望方案",
            "action": "等待更明确信号再操作",
            "risk": "低",
            "condition": "适合不确定性高的情况"
        })
        
        return alternatives
    
    def _record_cognition(self, snapshot: CognitiveSnapshot):
        """记录认知"""
        self.state["cognitive_history"].append({
            "id": str(uuid.uuid4())[:8],
            "timestamp": snapshot.timestamp,
            "situation": snapshot.situation,
            "confidence": snapshot.confidence,
            "action": snapshot.recommended_action,
            "warnings_count": len(snapshot.warnings)
        })
        
        if len(self.state["cognitive_history"]) > 200:
            self.state["cognitive_history"] = self.state["cognitive_history"][-200:]
        
        self.state["meta"]["total_cognitions"] += 1
        self._save()
    
    # ========== 决策记录和反馈 ==========
    
    def record_decision(
        self,
        situation: str,
        action: str,
        context: MarketContext,
        reasoning: str
    ) -> str:
        """记录决策"""
        decision_id = str(uuid.uuid4())[:8]
        
        self.state["decision_records"].append({
            "id": decision_id,
            "timestamp": datetime.now().isoformat(),
            "situation": situation,
            "action": action,
            "stock": context.stock,
            "price": context.current_price,
            "reasoning": reasoning,
            "outcome": None,
            "was_correct": None
        })
        
        self._save()
        return decision_id
    
    def record_outcome(
        self,
        decision_id: str,
        outcome: str,
        was_correct: bool,
        lessons: Optional[List[str]] = None
    ):
        """记录结果"""
        for record in reversed(self.state["decision_records"]):
            if record["id"] == decision_id:
                record["outcome"] = outcome
                record["was_correct"] = was_correct
                if lessons:
                    record["lessons"] = lessons
                break
        
        if was_correct:
            self.state["meta"]["correct_decisions"] += 1
        else:
            # 从错误中学习
            self._learn_from_error(decision_id, lessons or [])
        
        total = self.state["meta"]["total_cognitions"]
        correct = self.state["meta"]["correct_decisions"]
        self.state["meta"]["accuracy_rate"] = correct / max(total, 1)
        
        self._save()
    
    def _learn_from_error(self, decision_id: str, lessons: List[str]):
        """从错误中学习"""
        for record in self.state["decision_records"]:
            if record["id"] == decision_id:
                # 可以在这里触发知识库的更新
                # 简化实现：记录到错误历史
                self.state.setdefault("error_history", []).append({
                    "timestamp": datetime.now().isoformat(),
                    "decision": record,
                    "lessons": lessons
                })
                break
    
    # ========== 格式化输出 ==========
    
    def format_snapshot(self, snapshot: CognitiveSnapshot) -> str:
        """格式化认知快照"""
        lines = []
        lines.append(f"🧠 超级认知思考报告")
        lines.append(f"{'='*55}")
        lines.append(f"时间: {snapshot.timestamp}")
        lines.append(f"情境: {snapshot.situation}")
        lines.append(f"置信度: {snapshot.confidence:.0%}")
        lines.append("")
        
        # 关键问题
        if snapshot.questions:
            lines.append("❓ 关键问题:")
            for q in snapshot.questions[:3]:
                lines.append(f"  • {q}")
            lines.append("")
        
        # 推理链
        if snapshot.reasoning_chain:
            lines.append("📋 推理链:")
            for step in snapshot.reasoning_chain:
                lines.append(f"  {step.get('step')}. [{step.get('type')}] {step.get('content')}")
                if step.get('conclusion'):
                    lines.append(f"     → {step['conclusion']}")
            lines.append("")
        
        # 风险信号
        if snapshot.risk_signals:
            lines.append("⚠️ 风险信号:")
            for signal in snapshot.risk_signals[:3]:
                lines.append(f"  • {signal}")
            lines.append("")
        
        # 机会
        if snapshot.opportunities:
            lines.append("💡 机会:")
            for opp in snapshot.opportunities[:3]:
                lines.append(f"  • {opp}")
            lines.append("")
        
        # 元认知警告
        if snapshot.warnings:
            lines.append("🔍 元认知警告:")
            for warning in snapshot.warnings:
                lines.append(f"  • {warning}")
            if snapshot.self_correction:
                lines.append(f"  修正: {snapshot.self_correction}")
            lines.append("")
        
        # 最终判断
        lines.append(f"🎯 最终判断:")
        lines.append(f"  {snapshot.final_judgment}")
        lines.append("")
        
        # 推荐行动
        lines.append(f"📌 推荐行动:")
        lines.append(f"  {snapshot.recommended_action}")
        lines.append("")
        
        # 备选方案
        if snapshot.alternatives:
            lines.append("📊 备选方案:")
            for alt in snapshot.alternatives:
                lines.append(f"  【{alt['option']}】{alt['action']} (风险:{alt['risk']})")
            lines.append("")
        
        return "\n".join(lines)
    
    # ========== 统计 ==========
    
    def get_stats(self) -> dict:
        """获取统计"""
        return {
            "total_cognitions": self.state["meta"]["total_cognitions"],
            "accuracy_rate": self.state["meta"]["accuracy_rate"],
            "recent_cognitions": self.state["cognitive_history"][-10:],
            "recent_decisions": [
                {"id": d["id"], "action": d["action"], "correct": d.get("was_correct")}
                for d in self.state["decision_records"][-10:]
            ]
        }
