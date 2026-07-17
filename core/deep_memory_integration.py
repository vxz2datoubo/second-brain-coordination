"""
deep_memory_integration.py — 深度记忆与推理集成模块
=====================================================
整合神经记忆网络、可微分推理引擎和元学习决策器，
构建端到端的深度学习增强认知系统。

功能:
1. 统一记忆接口 - 融合向量记忆和符号记忆
2. 混合推理引擎 - 结合神经网络和符号推理
3. 自适应决策 - 元学习驱动的快速适应
4. 持续学习闭环 - 从经验中不断优化

集成架构:
┌─────────────────────────────────────────────────────────────┐
│                    DeepMemoryIntegration                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ NeuralMemory    │  │ Differentiable  │  │ MetaLearning│ │
│  │ Network         │  │ Reasoner        │  │ Decision    │ │
│  │ (长期记忆)       │  │ (符号推理)       │  │ (快速适应)   │ │
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘ │
│           │                    │                   │        │
│           └────────────────────┼───────────────────┘        │
│                                │                            │
│                    ┌───────────┴───────────┐                │
│                    │   UnifiedBrain        │                │
│                    │   (统一大脑接口)       │                │
│                    └───────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from core.neural_memory import NeuralMemoryNetwork, get_neural_memory
from core.differentiable_reasoner import DifferentiableReasoner, get_differentiable_reasoner
from core.meta_learning import MetaLearningDecision, get_meta_learner


# ========== 推理链节点 ==========

@dataclass
class ReasoningNode:
    """推理链中的节点"""
    id: str
    type: str  # "memory", "rule", "context", "decision"
    content: str
    confidence: float
    source: str  # 来自哪个模块
    metadata: Dict = field(default_factory=dict)


@dataclass
class ReasoningChain:
    """完整推理链"""
    id: str
    query: str
    nodes: List[ReasoningNode]
    final_decision: str
    confidence: float
    timestamp: str
    alternatives: List[Dict] = field(default_factory=list)


# ========== 统一大脑接口 ==========

class UnifiedBrain:
    """
    统一大脑接口
    
    整合三大深度学习增强模块，提供统一的认知接口
    """
    
    def __init__(self, graph, data_dir: Path):
        self.graph = graph
        self.data_dir = data_dir
        
        # 初始化三大模块
        self.neural_memory = get_neural_memory(data_dir)
        self.differentiable_reasoner = get_differentiable_reasoner(graph, data_dir)
        self.meta_learner = get_meta_learner(data_dir)
        
        # 推理历史
        self.reasoning_chains: List[ReasoningChain] = []
        
        # 置信度融合权重
        self.fusion_weights = {
            "memory": 0.3,
            "reasoner": 0.4,
            "meta_learner": 0.3
        }
    
    def think(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        深度思考 - 整合三种推理方式
        
        流程:
        1. 神经记忆检索 - 获取相关记忆
        2. 符号推理 - 使用规则推导
        3. 元学习决策 - 快速适应决策
        4. 融合输出 - 综合三种结果
        """
        import uuid
        
        chain_id = str(uuid.uuid4())[:8]
        nodes = []
        
        # 阶段1: 神经记忆检索
        memory_results = self.neural_memory.read(query, top_k=5)
        memory_confidence = sum(r["score"] for r in memory_results) / max(len(memory_results), 1) if memory_results else 0.5
        memory_node = ReasoningNode(
            id=f"{chain_id}_mem",
            type="memory",
            content=f"检索到{len(memory_results)}条相关记忆",
            confidence=memory_confidence,
            source="neural_memory",
            metadata={"results": memory_results}
        )
        nodes.append(memory_node)
        
        # 阶段2: 符号推理
        facts = self._context_to_facts(context or {})
        reasoning_result = self.differentiable_reasoner.infer(
            facts,
            mode="forward",
            max_depth=3
        )
        reasoner_confidence = reasoning_result.get("confidence", 0.5)
        
        reasoner_node = ReasoningNode(
            id=f"{chain_id}_reason",
            type="rule",
            content=f"推理出{len(reasoning_result.get('conclusions', {}))}个结论",
            confidence=reasoner_confidence,
            source="differentiable_reasoner",
            metadata={"reasoning": reasoning_result}
        )
        nodes.append(reasoner_node)
        
        # 阶段3: 元学习决策
        if context:
            decision_result = self.meta_learner.adapt_to_context(context)
        else:
            market_condition = self._infer_market_condition(memory_results)
            decision_result = self.meta_learner.decide(market_condition, "tech")
        
        meta_node = ReasoningNode(
            id=f"{chain_id}_meta",
            type="decision",
            content=f"决策: {decision_result.get('action')} (置信度: {decision_result.get('confidence', 0):.2f})",
            confidence=decision_result.get('confidence', 0.5),
            source="meta_learner",
            metadata={"decision": decision_result}
        )
        nodes.append(meta_node)
        
        # 阶段4: 融合决策
        final_confidence = (
            self.fusion_weights["memory"] * memory_confidence +
            self.fusion_weights["reasoner"] * reasoner_confidence +
            self.fusion_weights["meta_learner"] * decision_result.get('confidence', 0.5)
        )
        
        # 选择最终动作
        action = decision_result.get("action", "hold")
        if memory_results:
            for r in memory_results:
                if r["score"] > 0.8:
                    if "买" in r["content"] or "买入" in r["content"]:
                        action = "buy"
                    elif "卖" in r["content"] or "止损" in r["content"]:
                        action = "sell"
        
        # 检查推理结论
        conclusions = reasoning_result.get("conclusions", {})
        if conclusions:
            # 从结论中提取动作建议
            if "execute_buy" in conclusions and conclusions["execute_buy"] > 0.7:
                action = "buy"
            elif "stop_loss" in conclusions and conclusions["stop_loss"] > 0.7:
                action = "sell"
        
        # 构建推理链
        chain = ReasoningChain(
            id=chain_id,
            query=query,
            nodes=nodes,
            final_decision=action,
            confidence=final_confidence,
            timestamp=datetime.now().isoformat(),
            alternatives=self._generate_alternatives(decision_result, reasoning_result)
        )
        
        self.reasoning_chains.append(chain)
        if len(self.reasoning_chains) > 100:
            self.reasoning_chains = self.reasoning_chains[-100:]
        
        # 写入记忆
        self.neural_memory.write(
            f"思考: {query} -> 决策: {action} (置信度: {final_confidence:.2f})",
            importance=0.6,
            tags=["思考", "决策", query[:10] if len(query) > 10 else query]
        )
        
        return self._format_result(chain, memory_results, reasoning_result, decision_result)
    
    def _context_to_facts(self, context: Dict) -> Dict[str, float]:
        """将上下文转换为推理事实"""
        facts = {}
        
        # 市场趋势
        trend = context.get("market_trend", "neutral")
        facts["market_trend_up"] = 1.0 if trend == "up" else 0.0
        facts["market_trend_down"] = 1.0 if trend == "down" else 0.0
        
        # 波动性
        volatility = context.get("volatility", "medium")
        facts["high_volatility"] = 1.0 if volatility == "high" else 0.0
        
        # 信号
        if context.get("buy_signal"):
            facts["buy_signal"] = 0.8
        if context.get("volume_surge"):
            facts["volume_surge"] = 0.8
        if context.get("price_breakout"):
            facts["price_breakout"] = 0.7
        
        # 新闻
        if context.get("news_positive"):
            facts["news_positive"] = 0.8
        if context.get("news_negative"):
            facts["news_negative"] = 0.8
        
        # 盈亏
        if context.get("loss_exceeds_limit"):
            facts["loss_exceeds_limit"] = 1.0
        if context.get("profit_reaches_target"):
            facts["profit_reaches_target"] = 0.8
        
        return facts
    
    def _infer_market_condition(self, memory_results: List[Dict]) -> str:
        """从记忆中推断市场状态"""
        if not memory_results:
            return "range"
        
        avg_score = sum(r["score"] for r in memory_results) / len(memory_results)
        
        if avg_score > 0.7:
            return "trending"
        elif avg_score > 0.5:
            return "range"
        else:
            return "volatile"
    
    def _generate_alternatives(self, decision: Dict, reasoning: Dict) -> List[Dict]:
        """生成备选方案"""
        alternatives = []
        action = decision.get("action", "hold")
        
        if action == "buy":
            alternatives.append({
                "action": "hold",
                "reason": "保守策略：等待更明确信号",
                "confidence": decision.get("confidence", 0.5) * 0.8
            })
            alternatives.append({
                "action": "sell",
                "reason": "反向策略：检测到潜在风险",
                "confidence": 0.3
            })
        elif action == "sell":
            alternatives.append({
                "action": "hold",
                "reason": "观察策略：等待反弹机会",
                "confidence": decision.get("confidence", 0.5) * 0.7
            })
        else:
            alternatives.append({
                "action": "buy",
                "reason": "激进策略：确认趋势后买入",
                "confidence": 0.4
            })
            alternatives.append({
                "action": "sell",
                "reason": "清仓策略：规避不确定性",
                "confidence": 0.3
            })
        
        return alternatives
    
    def _format_result(self, chain: ReasoningChain,
                       memory_results: List[Dict],
                       reasoning_result: Dict,
                       decision_result: Dict) -> Dict[str, Any]:
        """格式化输出"""
        return {
            "chain_id": chain.id,
            "query": chain.query,
            "decision": chain.final_decision,
            "confidence": chain.confidence,
            "reasoning_chain": [
                {
                    "type": n.type,
                    "content": n.content,
                    "confidence": n.confidence,
                    "source": n.source
                }
                for n in chain.nodes
            ],
            "memory_insights": [
                {
                    "content": r["content"][:100] if len(r["content"]) > 100 else r["content"],
                    "score": r["score"]
                }
                for r in memory_results[:3]
            ],
            "reasoning_conclusions": list(reasoning_result.get("conclusions", {}).keys())[:5],
            "decision_probabilities": decision_result.get("probabilities", {}),
            "alternatives": chain.alternatives,
            "timestamp": chain.timestamp
        }
    
    def learn_from_feedback(self, chain_id: str, outcome: float, correct: bool):
        """
        从反馈中学习
        
        更新三个模块:
        1. 强化相关记忆
        2. 更新规则置信度
        3. 记录元学习任务
        """
        chain = None
        for c in reversed(self.reasoning_chains):
            if c.id == chain_id:
                chain = c
                break
        
        if not chain:
            return {"error": "Chain not found"}
        
        # 1. 更新元学习器
        market_condition = self._infer_market_condition(
            chain.nodes[0].metadata.get("results", [])
        )
        self.meta_learner.record_task(
            market_condition=market_condition,
            stock_type="tech",
            action=chain.final_decision,
            outcome=outcome
        )
        
        # 2. 更新推理器规则
        self.differentiable_reasoner.learn_from_feedback(chain_id, correct)
        
        # 3. 强化记忆
        for memory in chain.nodes[0].metadata.get("results", []):
            if memory["score"] > 0.5 and memory["id"] in self.neural_memory.memories:
                self.neural_memory.memories[memory["id"]].strength = min(
                    1.0, 
                    self.neural_memory.memories[memory["id"]].strength * 1.1
                )
        
        return {
            "chain_id": chain_id,
            "outcome": outcome,
            "learned": True
        }
    
    def consolidate(self) -> Dict:
        """记忆巩固"""
        stats = {
            "neural_memory": self.neural_memory.consolidate(),
            "timestamp": datetime.now().isoformat()
        }
        return stats
    
    def get_full_stats(self) -> Dict:
        """获取完整统计"""
        return {
            "neural_memory": self.neural_memory.get_stats(),
            "differentiable_reasoner": self.differentiable_reasoner.get_stats(),
            "meta_learner": self.meta_learner.get_stats(),
            "reasoning_chains": len(self.reasoning_chains)
        }


# ========== 便捷访问函数 ==========

_unified_brain: Optional[UnifiedBrain] = None


def get_unified_brain(graph, data_dir: Path) -> UnifiedBrain:
    """获取统一大脑实例"""
    global _unified_brain
    if _unified_brain is None:
        _unified_brain = UnifiedBrain(graph, data_dir)
    return _unified_brain


def reset_unified_brain():
    """重置统一大脑（用于测试）"""
    global _unified_brain
    _unified_brain = None
