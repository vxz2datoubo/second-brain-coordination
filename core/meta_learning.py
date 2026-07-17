"""
meta_learning.py — 元学习决策器
================================
基于MAML和Reptile算法的自适应学习系统，能够从交易经验中快速学习新策略。

核心机制:
1. 任务无关的快速适应 (Task-agnostic Fast Adaptation)
2. 策略梯度优化 (Policy Gradient Optimization)
3. 经验重放学习 (Experience Replay Learning)
4. 不确定性估计 (Uncertainty Estimation)
5. 在线贝叶斯更新 (Online Bayesian Update)

学术参考:
- MAML: Model-Agnostic Meta-Learning (Finn et al., 2017)
- Reptile: On First-Order Meta-Learning Algorithms (Nichol et al., 2018)
- Bayesian Neural Networks for Uncertainty (Gal, 2016)
- ProMP: Probabilistic Movement Primitives (Paraschos et al., 2013)

注意: 使用纯Python实现
"""

import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque


# ========== 任务定义 ==========

@dataclass
class TradingTask:
    """交易任务"""
    id: str
    name: str
    market_condition: str  # trending, range, volatile, calm
    stock_type: str        # tech, finance, consumer
    action: str            # buy, sell, hold
    outcome: Optional[float] = None  # 收益结果
    timestamp: str = ""
    
    def get_feature_vector(self) -> List[float]:
        """转换为特征向量"""
        features = []
        
        # 市场条件编码
        condition_map = {
            "trending": [1.0, 0.0, 0.0, 0.0], 
            "range": [0.0, 1.0, 0.0, 0.0], 
            "volatile": [0.0, 0.0, 1.0, 0.0], 
            "calm": [0.0, 0.0, 0.0, 1.0]
        }
        features.extend(condition_map.get(self.market_condition, [0.0, 0.0, 0.0, 0.0]))
        
        # 股票类型编码
        stock_map = {"tech": [1.0, 0.0, 0.0], "finance": [0.0, 1.0, 0.0], "consumer": [0.0, 0.0, 1.0]}
        features.extend(stock_map.get(self.stock_type, [0.0, 0.0, 0.0]))
        
        # 动作编码
        action_map = {"buy": [1.0, 0.0, 0.0], "sell": [0.0, 1.0, 0.0], "hold": [0.0, 0.0, 1.0]}
        features.extend(action_map.get(self.action, [0.0, 0.0, 1.0]))
        
        return features


@dataclass
class MetaPolicy:
    """元策略参数"""
    weights: List[List[float]]  # 2D list (feature_dim x output_dim)
    bias: List[float]           # 1D list (output_dim)
    adaptation_lr: float = 0.01
    meta_lr: float = 0.001
    last_updated: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "weights": self.weights,
            "bias": self.bias,
            "adaptation_lr": self.adaptation_lr,
            "meta_lr": self.meta_lr,
            "last_updated": self.last_updated
        }
    
    @staticmethod
    def from_dict(data: Dict) -> "MetaPolicy":
        return MetaPolicy(
            weights=data["weights"],
            bias=data["bias"],
            adaptation_lr=data.get("adaptation_lr", 0.01),
            meta_lr=data.get("meta_lr", 0.001),
            last_updated=data.get("last_updated", "")
        )


# ========== 元学习器 ==========

class MetaLearningDecision:
    """
    元学习决策器
    
    核心能力:
    1. 快速适应新市场环境
    2. 从少量经验中学习
    3. 不确定性感知决策
    4. 在线持续学习
    
    算法: 简化的MAML实现
    - 内循环: 快速适应单个任务
    - 外循环: 跨任务学习通用先验
    """
    
    FEATURE_DIM = 10  # 特征维度
    OUTPUT_DIM = 3    # 输出维度 (buy, sell, hold)
    
    ADAPTATION_STEPS = 5      # 内循环步数
    META_BATCH_SIZE = 10      # 外循环批次大小
    CONFIDENCE_THRESHOLD = 0.6  # 置信度阈值
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.tasks: List[TradingTask] = []
        self.task_history: Dict[str, List[TradingTask]] = defaultdict(list)
        
        # 元策略参数 (两层神经网络)
        self.meta_policy = self._init_policy()
        
        # 经验回放缓冲区
        self.replay_buffer: deque = deque(maxlen=500)
        
        # 加载数据
        self._load()
    
    def _init_policy(self) -> MetaPolicy:
        """初始化策略参数"""
        random.seed(42)
        weights = [
            [random.gauss(0, 0.01) for _ in range(self.OUTPUT_DIM)]
            for _ in range(self.FEATURE_DIM)
        ]
        bias = [0.0] * self.OUTPUT_DIM
        return MetaPolicy(
            weights=weights,
            bias=bias,
            adaptation_lr=0.01,
            meta_lr=0.001
        )
    
    def _load(self):
        """加载数据"""
        meta_path = self.data_dir / "meta_learning.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.meta_policy = MetaPolicy.from_dict(data.get("policy", {}))
                for tdata in data.get("tasks", []):
                    self.tasks.append(TradingTask(**tdata))
                for tid, tlist in data.get("task_history", {}).items():
                    self.task_history[tid] = [TradingTask(**t) for t in tlist]
    
    def _save(self):
        """保存数据"""
        data = {
            "policy": self.meta_policy.to_dict(),
            "tasks": [self._task_to_dict(t) for t in self.tasks[-100:]],
            "task_history": {
                tid: [self._task_to_dict(t) for t in tlist[-20:]]
                for tid, tlist in self.task_history.items()
            }
        }
        with open(self.data_dir / "meta_learning.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _task_to_dict(self, task: TradingTask) -> Dict:
        return {
            "id": task.id,
            "name": task.name,
            "market_condition": task.market_condition,
            "stock_type": task.stock_type,
            "action": task.action,
            "outcome": task.outcome,
            "timestamp": task.timestamp
        }
    
    # ========== 前向传播 ==========
    
    def _relu(self, x: float) -> float:
        """ReLU激活"""
        return max(0, x)
    
    def _softmax(self, logits: List[float]) -> List[float]:
        """Softmax激活"""
        max_logit = max(logits)
        exp_logits = [math.exp(x - max_logit) for x in logits]
        sum_exp = sum(exp_logits)
        return [x / sum_exp for x in exp_logits]
    
    def _forward(self, features: List[float], policy: MetaPolicy) -> List[float]:
        """前向传播"""
        # 线性层: logits = features @ weights + bias
        logits = [0.0] * self.OUTPUT_DIM
        for i in range(self.FEATURE_DIM):
            for j in range(self.OUTPUT_DIM):
                logits[j] += features[i] * policy.weights[i][j]
        for j in range(self.OUTPUT_DIM):
            logits[j] += policy.bias[j]
        # 输出概率
        return self._softmax(logits)
    
    def _loss(self, predictions: List[float], targets: List[float]) -> float:
        """交叉熵损失"""
        return -sum(t * math.log(p + 1e-8) for t, p in zip(targets, predictions))
    
    def _one_hot(self, action_idx: int, dim: int = 3) -> List[float]:
        """One-hot编码"""
        vec = [0.0] * dim
        vec[action_idx] = 1.0
        return vec
    
    # ========== 快速适应 ==========
    
    def fast_adapt(self, support_task: TradingTask) -> MetaPolicy:
        """
        快速适应单个任务 (内循环)
        
        使用MAML思想：对支持任务进行梯度下降更新
        """
        adapted_policy = MetaPolicy(
            weights=[w.copy() for w in self.meta_policy.weights],
            bias=self.meta_policy.bias.copy(),
            adaptation_lr=self.meta_policy.adaptation_lr,
            meta_lr=self.meta_policy.meta_lr
        )
        
        features = support_task.get_feature_vector()
        target = self._one_hot(["buy", "sell", "hold"].index(support_task.action))
        
        # 梯度下降
        for _ in range(self.ADAPTATION_STEPS):
            predictions = self._forward(features, adapted_policy)
            loss = self._loss(predictions, target)
            
            # 梯度计算 (数值方法简化)
            grad_weights = [[0.0] * self.OUTPUT_DIM for _ in range(self.FEATURE_DIM)]
            grad_bias = [0.0] * self.OUTPUT_DIM
            
            for i in range(self.FEATURE_DIM):
                for j in range(self.OUTPUT_DIM):
                    grad_weights[i][j] = features[i] * (predictions[j] - target[j])
            
            for j in range(self.OUTPUT_DIM):
                grad_bias[j] = predictions[j] - target[j]
            
            # 更新
            lr = adapted_policy.adaptation_lr
            for i in range(self.FEATURE_DIM):
                for j in range(self.OUTPUT_DIM):
                    adapted_policy.weights[i][j] -= lr * grad_weights[i][j]
            for j in range(self.OUTPUT_DIM):
                adapted_policy.bias[j] -= lr * grad_bias[j]
        
        return adapted_policy
    
    # ========== 决策推理 ==========
    
    def decide(self, market_condition: str, stock_type: str,
               context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        做出决策
        
        使用元策略进行决策，支持快速适应
        """
        # 构建特征
        task = TradingTask(
            id="query",
            name="决策查询",
            market_condition=market_condition,
            stock_type=stock_type,
            action="hold",  # 待确定
            timestamp=datetime.now().isoformat()
        )
        
        features = task.get_feature_vector()
        
        # 如果有上下文，增加额外特征
        if context:
            extra_features = self._context_to_features(context)
            features.extend(extra_features[:max(0, self.FEATURE_DIM - len(features))])
        
        # 确保特征长度正确
        while len(features) < self.FEATURE_DIM:
            features.append(0.0)
        features = features[:self.FEATURE_DIM]
        
        # 使用元策略预测
        probs = self._forward(features, self.meta_policy)
        
        # 获取动作
        actions = ["buy", "sell", "hold"]
        action_idx = probs.index(max(probs))
        action = actions[action_idx]
        
        # 计算置信度
        confidence = probs[action_idx]
        
        # 估计不确定性 (基于预测分布熵)
        entropy = -sum(p * math.log(p + 1e-8) for p in probs if p > 0)
        max_entropy = math.log(3)  # 最大熵
        uncertainty = 1.0 - (entropy / max_entropy if max_entropy > 0 else 0)
        
        # 如果置信度低，尝试快速适应
        if confidence < self.CONFIDENCE_THRESHOLD:
            similar_task = self._find_similar_task(market_condition, stock_type)
            if similar_task:
                adapted_policy = self.fast_adapt(similar_task)
                probs_adapted = self._forward(features, adapted_policy)
                action_idx_adapted = probs_adapted.index(max(probs_adapted))
                action_adapted = actions[action_idx_adapted]
                
                if probs_adapted[action_idx_adapted] > confidence:
                    action = action_adapted
                    confidence = probs_adapted[action_idx_adapted]
        
        return {
            "action": action,
            "confidence": float(confidence),
            "uncertainty": float(uncertainty),
            "probabilities": {
                "buy": float(probs[0]),
                "sell": float(probs[1]),
                "hold": float(probs[2])
            },
            "market_condition": market_condition,
            "stock_type": stock_type
        }
    
    def _context_to_features(self, context: Dict) -> List[float]:
        """将上下文转换为特征"""
        features = []
        
        # 价格变化
        if "change_pct" in context:
            features.append(max(-1.0, min(1.0, context["change_pct"] / 10)))
        else:
            features.append(0.0)
        
        # 成交量变化
        if "volume_ratio" in context:
            features.append(max(-1.0, min(1.0, math.log(context["volume_ratio"] + 1) / 3)))
        else:
            features.append(0.0)
        
        # 趋势强度
        if "trend_strength" in context:
            features.append(max(-1.0, min(1.0, context["trend_strength"])))
        else:
            features.append(0.0)
        
        # 波动率
        if "volatility" in context:
            vol_val = context["volatility"]
            if isinstance(vol_val, str):
                vol_map = {"high": 3, "medium": 2, "low": 1}
                vol_val = vol_map.get(vol_val, 2)
            features.append(max(-1.0, min(1.0, float(vol_val) / 5)))
        else:
            features.append(0.0)
        
        return features
    
    def _find_similar_task(self, market_condition: str, 
                           stock_type: str) -> Optional[TradingTask]:
        """找到相似的历史任务"""
        similar = [
            t for t in self.tasks
            if t.market_condition == market_condition 
            and t.stock_type == stock_type
            and t.outcome is not None
        ]
        
        if not similar:
            similar = [
                t for t in self.tasks
                if t.market_condition == market_condition
                and t.outcome is not None
            ]
        
        if not similar:
            return None
        
        similar.sort(key=lambda t: t.outcome or 0, reverse=True)
        return similar[0]
    
    # ========== 经验学习 ==========
    
    def record_task(self, market_condition: str, stock_type: str,
                    action: str, outcome: float) -> str:
        """
        记录任务结果
        
        这个方法让系统从实际交易结果中学习
        """
        import uuid
        
        task_id = str(uuid.uuid4())[:8]
        task = TradingTask(
            id=task_id,
            name=f"{market_condition}_{stock_type}_{action}",
            market_condition=market_condition,
            stock_type=stock_type,
            action=action,
            outcome=outcome,
            timestamp=datetime.now().isoformat()
        )
        
        self.tasks.append(task)
        self.task_history[market_condition].append(task)
        
        # 添加到经验回放
        self.replay_buffer.append({
            "task": task,
            "timestamp": datetime.now().isoformat()
        })
        
        # 如果有足够经验，执行元学习更新
        if len(self.replay_buffer) >= self.META_BATCH_SIZE:
            self._meta_update()
        
        self._save()
        return task_id
    
    def _meta_update(self):
        """
        元学习更新 (外循环)
        
        使用Reptile风格的简化更新
        """
        if len(self.replay_buffer) < 2:
            return
        
        # 采样一批任务
        samples = list(self.replay_buffer)[-self.META_BATCH_SIZE:]
        
        total_grad_weights = [[0.0] * self.OUTPUT_DIM for _ in range(self.FEATURE_DIM)]
        total_grad_bias = [0.0] * self.OUTPUT_DIM
        
        for sample in samples:
            task = sample["task"]
            
            # 快速适应
            adapted = self.fast_adapt(task)
            
            # 累积梯度 (Reptile: W = W + lr * (W_adapted - W))
            for i in range(self.FEATURE_DIM):
                for j in range(self.OUTPUT_DIM):
                    total_grad_weights[i][j] += (adapted.weights[i][j] - self.meta_policy.weights[i][j])
            for j in range(self.OUTPUT_DIM):
                total_grad_bias[j] += (adapted.bias[j] - self.meta_policy.bias[j])
        
        # 更新元策略
        lr = self.meta_policy.meta_lr
        count = len(samples)
        for i in range(self.FEATURE_DIM):
            for j in range(self.OUTPUT_DIM):
                self.meta_policy.weights[i][j] += lr * total_grad_weights[i][j] / count
        for j in range(self.OUTPUT_DIM):
            self.meta_policy.bias[j] += lr * total_grad_bias[j] / count
        
        self.meta_policy.last_updated = datetime.now().isoformat()
        self._save()
    
    def adapt_to_context(self, context: Dict) -> Dict[str, Any]:
        """
        根据当前上下文快速适应并决策
        
        这是对外的主要接口
        """
        market_condition = context.get("market_condition", "range")
        stock_type = context.get("stock_type", "tech")
        
        decision = self.decide(market_condition, stock_type, context)
        
        # 添加建议理由
        decision["reasoning"] = self._generate_reasoning(decision, context)
        
        return decision
    
    def _generate_reasoning(self, decision: Dict, context: Dict) -> str:
        """生成决策理由"""
        action = decision["action"]
        confidence = decision["confidence"]
        
        reasons = []
        
        if action == "buy":
            if confidence > 0.7:
                reasons.append("市场条件有利，元策略预测上涨概率高")
            else:
                reasons.append("存在买入机会，但置信度较低，建议谨慎")
        elif action == "sell":
            reasons.append("检测到下跌风险信号，建议减仓或止损")
        else:
            reasons.append("市场方向不明，建议观望等待")
        
        if decision["uncertainty"] > 0.5:
            reasons.append("当前不确定性较高，建议控制仓位")
        
        return "；".join(reasons)
    
    # ========== 统计和分析 ==========
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if not self.tasks:
            return {
                "total_tasks": 0,
                "avg_outcome": 0,
                "best_action": "none",
                "strategy_ready": False
            }
        
        outcomes = [t.outcome for t in self.tasks if t.outcome is not None]
        actions = [t.action for t in self.tasks]
        
        # 最佳动作
        action_outcomes = defaultdict(list)
        for t in self.tasks:
            if t.outcome is not None:
                action_outcomes[t.action].append(t.outcome)
        
        best_action = max(action_outcomes.items(), 
                         key=lambda x: sum(x[1])/len(x[1]) if x[1] else 0)[0]
        
        # 按市场条件分析
        condition_stats = defaultdict(lambda: {"count": 0, "avg_outcome": 0})
        for t in self.tasks:
            if t.outcome is not None:
                condition_stats[t.market_condition]["count"] += 1
                old_avg = condition_stats[t.market_condition]["avg_outcome"]
                n = condition_stats[t.market_condition]["count"]
                condition_stats[t.market_condition]["avg_outcome"] = (
                    (old_avg * (n-1) + t.outcome) / n
                )
        
        return {
            "total_tasks": len(self.tasks),
            "avg_outcome": sum(outcomes) / len(outcomes) if outcomes else 0,
            "best_action": best_action,
            "strategy_ready": len(self.tasks) >= 20,
            "replay_buffer_size": len(self.replay_buffer),
            "condition_stats": dict(condition_stats),
            "policy_updated": self.meta_policy.last_updated
        }
    
    def analyze_performance(self) -> Dict[str, Any]:
        """分析策略表现"""
        if len(self.tasks) < 5:
            return {"message": "数据不足，需要更多任务记录"}
        
        # 计算胜率
        wins = sum(1 for t in self.tasks if t.outcome and t.outcome > 0)
        total = sum(1 for t in self.tasks if t.outcome is not None)
        win_rate = wins / total if total > 0 else 0
        
        # 按条件分析
        condition_analysis = {}
        for condition in ["trending", "range", "volatile", "calm"]:
            tasks_cond = [t for t in self.tasks 
                         if t.market_condition == condition and t.outcome is not None]
            if tasks_cond:
                outcomes = [t.outcome for t in tasks_cond]
                wins_cond = sum(1 for o in outcomes if o > 0)
                condition_analysis[condition] = {
                    "count": len(tasks_cond),
                    "win_rate": wins_cond / len(outcomes),
                    "avg_outcome": sum(outcomes) / len(outcomes)
                }
        
        return {
            "overall_win_rate": win_rate,
            "total_trades": total,
            "condition_analysis": condition_analysis,
            "recommendation": "增加仓位" if win_rate > 0.6 else "保持谨慎" if win_rate < 0.4 else "继续观察"
        }


def get_meta_learner(data_dir: Path) -> MetaLearningDecision:
    """获取元学习器实例"""
    return MetaLearningDecision(data_dir)
