"""
differentiable_reasoner.py — 可微分推理引擎
=============================================
基于神经符号推理的最新研究，实现可端到端训练的推理系统。

核心机制:
1. 软逻辑操作 (Soft Logic Operations) - 可微分的AND/OR/NOT
2. 推理路径学习 (Reasoning Path Learning) - 类比Neural LP
3. 嵌入空间推理 (Embedding Space Reasoning) - 类比端到端推理
4. 注意力路由 (Attention Routing) - 决定使用哪些规则

学术参考:
- Neural Logic Programming (Yang et al., 2017)
- Differentiable Reasoning (Evans & Grefenstette, 2018)
- Neural Theorem Proving (Rocktaschel & Riedel, 2017)
- DeepProbLog (Manhaeve et al., 2018)
- TensorLog (Cohen, 2020)

注意: 使用纯Python实现
"""

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict


# ========== 可微分逻辑操作 ==========

class DifferentiableLogic:
    """
    可微分逻辑操作 - 实现软逻辑 (Soft Logic)
    
    将传统的布尔逻辑替换为连续的、可微分的操作
    """
    
    @staticmethod
    def _sigmoid(x: float) -> float:
        """Sigmoid函数"""
        if x > 10:
            return 1.0
        if x < -10:
            return 0.0
        return 1.0 / (1.0 + math.exp(-x))
    
    @staticmethod
    def soft_and(*values, temperature: float = 0.1) -> float:
        """软AND操作 (Product T-norm)"""
        if not values:
            return 1.0
        # 使用sigmoid聚合
        logits = [-v / temperature for v in values]
        return DifferentiableLogic._sigmoid(-sum(logits))
    
    @staticmethod
    def soft_or(*values, temperature: float = 0.1) -> float:
        """软OR操作 (Probabilistic Sum)"""
        if not values:
            return 0.0
        # 使用sigmoid聚合
        logits = [v / temperature for v in values]
        return DifferentiableLogic._sigmoid(sum(logits))
    
    @staticmethod
    def soft_not(value: float) -> float:
        """软NOT操作"""
        return 1.0 - value
    
    @staticmethod
    def soft_xor(value1: float, value2: float) -> float:
        """软XOR操作"""
        return abs(value1 - value2)
    
    @staticmethod
    def soft_implies(antecedent: float, consequent: float, 
                     temperature: float = 0.1) -> float:
        """软蕴含操作: A -> B 等价于 NOT A OR B"""
        not_a = DifferentiableLogic.soft_not(antecedent)
        return DifferentiableLogic.soft_or(not_a, consequent, temperature=temperature)
    
    @staticmethod
    def weighted_sum(values: List[float], weights: List[float]) -> float:
        """加权求和"""
        if not values or not weights:
            return 0.0
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0
        return sum(v * w for v, w in zip(values, weights)) / total_weight


# ========== 推理规则 ==========

@dataclass
class Rule:
    """推理规则"""
    id: str
    name: str
    antecedent: List[str]  # 前件变量列表
    consequent: str        # 后件变量
    confidence: float = 0.8  # 规则置信度
    support: int = 0         # 支持次数
    usage_count: int = 0     # 使用次数
    
    def to_string(self) -> str:
        """转换为字符串"""
        if not self.antecedent:
            return f"{self.consequent} (置信度: {self.confidence:.2f})"
        return f"{self.antecedent} => {self.consequent} (置信度: {self.confidence:.2f})"


@dataclass 
class ReasoningStep:
    """推理步骤"""
    step_id: int
    rule_id: str
    rule_name: str
    inputs: Dict[str, float]  # 输入变量值
    output: float             # 输出值
    confidence: float
    explanation: str


# ========== 可微分推理机 ==========

class DifferentiableReasoner:
    """
    可微分推理引擎
    
    核心能力:
    1. 基于规则的推理 - 使用预定义规则
    2. 嵌入空间推理 - 在向量空间中推理
    3. 置信度传播 - 跟踪推理置信度
    4. 反向推理 - 从目标反向推导
    5. 推理路径学习 - 学习最优推理路径
    
    推理模式:
    - Forward Chaining: 从已知推导结论
    - Backward Chaining: 从目标反向推导
    - Bidirectional: 双向推理
    """
    
    MAX_INFERENCE_DEPTH = 5
    CONFIDENCE_THRESHOLD = 0.3
    RULE_SIMILARITY_THRESHOLD = 0.7
    
    def __init__(self, graph, data_dir: Path):
        self.graph = graph
        self.data_dir = data_dir
        self.rules: Dict[str, Rule] = {}
        self.rule_index: Dict[str, List[str]] = defaultdict(list)  # 变量到规则的索引
        self.embeddings: Dict[str, List[float]] = {}
        
        # 推理历史
        self.inference_history: List[Dict] = []
        
        # 加载数据
        self._load()
        
        # 初始化默认规则
        if not self.rules:
            self._init_default_rules()
    
    def _load(self):
        """加载推理数据"""
        rules_path = self.data_dir / "differentiable_rules.json"
        if rules_path.exists():
            with open(rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for rid, rdata in data.get("rules", {}).items():
                    self.rules[rid] = Rule(**rdata)
                self.embeddings = data.get("embeddings", {})
    
    def _save(self):
        """保存推理数据"""
        data = {
            "rules": {
                rid: {
                    "id": r.id,
                    "name": r.name,
                    "antecedent": r.antecedent,
                    "consequent": r.consequent,
                    "confidence": r.confidence,
                    "support": r.support,
                    "usage_count": r.usage_count
                }
                for rid, r in self.rules.items()
            },
            "embeddings": self.embeddings
        }
        with open(self.data_dir / "differentiable_rules.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _init_default_rules(self):
        """初始化默认交易规则"""
        default_rules = [
            Rule(
                id="rule_trend_up",
                name="上升趋势买入规则",
                antecedent=["market_trend_up", "buy_signal"],
                consequent="execute_buy",
                confidence=0.8
            ),
            Rule(
                id="rule_trend_down",
                name="下跌趋势规则",
                antecedent=["market_trend_down"],
                consequent="avoid_buy",
                confidence=0.9
            ),
            Rule(
                id="rule_high_volatility",
                name="高波动规则",
                antecedent=["high_volatility"],
                consequent="reduce_position",
                confidence=0.75
            ),
            Rule(
                id="rule_volume_surge",
                name="量能突破规则",
                antecedent=["volume_surge", "price_breakout"],
                consequent="confirm_signal",
                confidence=0.85
            ),
            Rule(
                id="rule_loss_limit",
                name="亏损限制规则",
                antecedent=["loss_exceeds_limit"],
                consequent="stop_loss",
                confidence=0.95
            ),
            Rule(
                id="rule_profit_target",
                name="盈利目标规则",
                antecedent=["profit_reaches_target"],
                consequent="take_profit",
                confidence=0.85
            ),
            Rule(
                id="rule_news_positive",
                name="正面新闻规则",
                antecedent=["news_positive", "price_reaction"],
                consequent="bullish_signal",
                confidence=0.7
            ),
            Rule(
                id="rule_news_negative",
                name="负面新闻规则",
                antecedent=["news_negative"],
                consequent="bearish_signal",
                confidence=0.8
            ),
            Rule(
                id="rule_support_level",
                name="支撑位规则",
                antecedent=["at_support", "volume_increase"],
                consequent="potential_rebound",
                confidence=0.75
            ),
            Rule(
                id="rule_resistance_level",
                name="阻力位规则",
                antecedent=["at_resistance"],
                consequent="potential_reversal",
                confidence=0.75
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: Rule):
        """添加推理规则"""
        self.rules[rule.id] = rule
        
        # 更新索引
        for var in rule.antecedent:
            self.rule_index[var].append(rule.id)
        self.rule_index[rule.consequent].append(rule.id)
        
        self._save()
    
    def remove_rule(self, rule_id: str):
        """删除规则"""
        if rule_id in self.rules:
            rule = self.rules[rule_id]
            # 从索引中移除
            for var in rule.antecedent + [rule.consequent]:
                if rule_id in self.rule_index[var]:
                    self.rule_index[var].remove(rule_id)
            del self.rules[rule_id]
            self._save()
    
    def update_rule_confidence(self, rule_id: str, correct: bool):
        """更新规则置信度"""
        if rule_id not in self.rules:
            return
        
        rule = self.rules[rule_id]
        rule.usage_count += 1
        
        if correct:
            # 正确：提高置信度
            rule.confidence = min(0.99, rule.confidence * 1.05)
            rule.support += 1
        else:
            # 错误：降低置信度
            rule.confidence = max(0.1, rule.confidence * 0.9)
        
        self._save()
    
    def infer(self, facts: Dict[str, float], 
              target: Optional[str] = None,
              mode: str = "forward",
              max_depth: int = None) -> Dict[str, Any]:
        """
        执行推理
        
        Args:
            facts: 输入事实 {变量名: 置信度}
            target: 目标变量 (backward模式)
            mode: forward | backward | bidirectional
            max_depth: 最大推理深度
        
        Returns:
            推理结果包含结论、置信度、推理路径
        """
        if max_depth is None:
            max_depth = self.MAX_INFERENCE_DEPTH
        
        context = facts.copy()  # 当前已知事实
        conclusions = {}        # 推导出的结论
        reasoning_steps = []    # 推理步骤记录
        visited_rules = set()   # 避免循环推理
        
        step_id = 0
        
        if mode == "forward":
            # 前向链推理
            for depth in range(max_depth):
                new_facts = False
                
                # 找到可用的规则
                for var, value in context.items():
                    if value > self.CONFIDENCE_THRESHOLD:
                        for rule_id in self.rule_index.get(var, []):
                            if rule_id in visited_rules:
                                continue
                            
                            rule = self.rules[rule_id]
                            
                            # 检查是否所有前件都满足
                            all_antecedents_met = True
                            antecedent_values = {}
                            
                            for ant in rule.antecedent:
                                if ant in context:
                                    antecedent_values[ant] = context[ant]
                                elif ant in conclusions:
                                    antecedent_values[ant] = conclusions[ant]
                                else:
                                    all_antecedents_met = False
                                    break
                            
                            if all_antecedents_met and antecedent_values:
                                # 计算输出
                                antecedent_list = list(antecedent_values.values())
                                
                                # 使用软AND计算
                                output = DifferentiableLogic.soft_and(
                                    *antecedent_list,
                                    temperature=0.2
                                )
                                
                                # 乘以规则置信度
                                final_output = output * rule.confidence
                                
                                # 记录推理步骤
                                step = ReasoningStep(
                                    step_id=step_id,
                                    rule_id=rule.id,
                                    rule_name=rule.name,
                                    inputs=antecedent_values,
                                    output=final_output,
                                    confidence=rule.confidence,
                                    explanation=f"使用规则 '{rule.name}' 从 {antecedent_values} 推导出"
                                )
                                reasoning_steps.append(step)
                                
                                # 如果是新的有效结论
                                if final_output > self.CONFIDENCE_THRESHOLD:
                                    if rule.consequent not in conclusions or conclusions[rule.consequent] < final_output:
                                        conclusions[rule.consequent] = final_output
                                        context[rule.consequent] = final_output
                                        new_facts = True
                                        step_id += 1
                                        visited_rules.add(rule_id)
                                        
                                        # 如果达到目标，停止
                                        if target and rule.consequent == target:
                                            return self._format_result(
                                                target, conclusions[target],
                                                reasoning_steps, "forward"
                                            )
                
                if not new_facts:
                    break  # 没有新事实，停止
        
        elif mode == "backward" and target:
            # 反向链推理
            result = self._backward_chain(target, context, reasoning_steps, visited_rules, max_depth)
            if result:
                return result
        
        # 如果指定了目标，返回目标结果
        if target:
            if target in conclusions:
                return self._format_result(target, conclusions[target], reasoning_steps, mode)
            else:
                return {
                    "target": target,
                    "value": 0.0,
                    "confidence": 0.0,
                    "reachable": False,
                    "reasoning_steps": [self._step_to_dict(s) for s in reasoning_steps],
                    "mode": mode
                }
        
        # 返回所有结论
        return self._format_result(conclusions, 1.0, reasoning_steps, mode, all_conclusions=True)
    
    def _backward_chain(self, target: str, context: Dict[str, float],
                        reasoning_steps: List[ReasoningStep],
                        visited_rules: Set[str], max_depth: int,
                        depth: int = 0) -> Optional[Dict]:
        """反向链推理"""
        if depth >= max_depth:
            return None
        
        # 如果已知，直接返回
        if target in context:
            return {
                "target": target,
                "value": context[target],
                "confidence": context[target],
                "reachable": True,
                "reasoning_steps": [self._step_to_dict(s) for s in reasoning_steps],
                "mode": "backward"
            }
        
        # 查找可以推导出目标的规则
        for rule_id in self.rule_index.get(target, []):
            if rule_id in visited_rules:
                continue
            
            rule = self.rules[rule_id]
            
            # 尝试推导每个前件
            all_antecedents = {}
            all_confident = True
            
            for ant in rule.antecedent:
                if ant in context:
                    all_antecedents[ant] = context[ant]
                else:
                    # 递归推导前件
                    sub_result = self._backward_chain(
                        ant, context, reasoning_steps, visited_rules | {rule_id},
                        max_depth, depth + 1
                    )
                    if sub_result and sub_result.get("reachable"):
                        all_antecedents[ant] = sub_result["value"]
                    else:
                        all_confident = False
            
            if all_antecedents:
                # 使用软AND计算
                antecedent_list = list(all_antecedents.values())
                output = DifferentiableLogic.soft_and(*antecedent_list, temperature=0.2)
                final_output = output * rule.confidence
                
                # 记录推理步骤
                step = ReasoningStep(
                    step_id=len(reasoning_steps),
                    rule_id=rule.id,
                    rule_name=rule.name,
                    inputs=all_antecedents,
                    output=final_output,
                    confidence=rule.confidence,
                    explanation=f"反向推导: 使用规则 '{rule.name}' 证明 {target}"
                )
                reasoning_steps.append(step)
                
                return {
                    "target": target,
                    "value": final_output,
                    "confidence": rule.confidence,
                    "reachable": all_confident,
                    "reasoning_steps": [self._step_to_dict(s) for s in reasoning_steps],
                    "mode": "backward"
                }
        
        return None
    
    def _format_result(self, target, value, steps, mode, all_conclusions=False):
        """格式化结果"""
        if all_conclusions:
            return {
                "conclusions": target,
                "count": len(target),
                "reasoning_steps": [self._step_to_dict(s) for s in steps],
                "mode": mode
            }
        
        return {
            "target": target if isinstance(target, str) else "multi",
            "value": value,
            "confidence": value,
            "reachable": value > self.CONFIDENCE_THRESHOLD,
            "reasoning_steps": [self._step_to_dict(s) for s in steps],
            "mode": mode
        }
    
    def _step_to_dict(self, step: ReasoningStep) -> Dict:
        """推理步骤转字典"""
        return {
            "step_id": step.step_id,
            "rule_id": step.rule_id,
            "rule_name": step.rule_name,
            "inputs": step.inputs,
            "output": round(step.output, 4),
            "confidence": round(step.confidence, 4),
            "explanation": step.explanation
        }
    
    def learn_from_feedback(self, reasoning_id: str, correct: bool):
        """从反馈中学习"""
        # 找到对应的推理历史
        for history in reversed(self.inference_history):
            if history.get("id") == reasoning_id:
                for step in history.get("reasoning_steps", []):
                    rule_id = step.get("rule_id")
                    if rule_id:
                        self.update_rule_confidence(rule_id, correct)
                
                # 记录反馈
                history["feedback"] = "correct" if correct else "incorrect"
                self._save()
                break
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_rules": len(self.rules),
            "avg_confidence": sum(r.confidence for r in self.rules.values()) / max(len(self.rules), 1),
            "total_inferences": len(self.inference_history),
            "high_confidence_rules": sum(1 for r in self.rules.values() if r.confidence > 0.8),
            "low_confidence_rules": sum(1 for r in self.rules.values() if r.confidence < 0.5)
        }


def get_differentiable_reasoner(graph, data_dir: Path) -> DifferentiableReasoner:
    """获取可微分推理器实例"""
    return DifferentiableReasoner(graph, data_dir)
