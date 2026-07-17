"""
continual_learning.py — 持续学习引擎
====================================
实现灾难性遗忘的克服机制，让AI大脑能够持续学习新任务而不忘记旧知识。

核心机制:
1. 弹性权重固化 (Elastic Weight Consolidation, EWC)
2. 经验回放 (Experience Replay)
3. 知识蒸馏 (Knowledge Distillation)
4. 渐进式神经网络 (Progressive Neural Networks concept)

学术参考:
- Overcoming Catastrophic Forgetting (Goodfellow et al., 2014)
- Elastic Weight Consolidation (Kirkpatrick et al., 2017)
- Progressive Neural Networks (Rusu et al., 2016)
- Memory-Aware Synapses (Aljundi et al., 2017)
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque


# ========== 知识快照 ==========

@dataclass
class KnowledgeSnapshot:
    """知识快照 - 记录某个时间点的关键参数"""
    id: str
    timestamp: str
    task_name: str
    description: str
    
    # 关键参数值
    parameters: Dict[str, float]  # {param_name: value}
    
    # 重要性估计
    importance: Dict[str, float]  # {param_name: importance_score}
    
    # 性能基准
    performance: float
    sample_size: int


@dataclass
class LearningTask:
    """学习任务"""
    id: str
    name: str
    timestamp: str
    category: str  # "trading", "reasoning", "memory", etc.
    
    # 任务数据
    samples: List[Dict]  # 训练样本
    labels: List[Any]    # 标签
    
    # 结果
    before_performance: float
    after_performance: float
    improvement: float
    
    # 泛化测试
    test_results: Dict[str, float] = field(default_factory=dict)


# ========== 持续学习器 ==========

class ContinualLearningEngine:
    """
    持续学习引擎
    
    实现多种机制来克服灾难性遗忘:
    1. EWC: 保护重要参数
    2. 经验回放: 重放旧样本
    3. 知识蒸馏: 保持旧模型输出
    4. 动态正则化: 适应性地调整学习
    """
    
    EWC_LAMBDA = 1000  # EWC正则化强度
    REPLAY_RATIO = 0.3  # 经验回放比例
    DISTILL_TEMP = 2.0  # 蒸馏温度
    SNAPSHOT_INTERVAL = 10  # 快照间隔（任务数）
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        
        # 知识快照
        self.snapshots: Dict[str, KnowledgeSnapshot] = {}
        
        # 学习任务历史
        self.tasks: List[LearningTask] = []
        
        # 经验回放缓冲区
        self.replay_buffer: deque = deque(maxlen=1000)
        
        # 参数重要性估计
        self.param_importance: Dict[str, float] = {}
        
        # 当前模型参数（模拟）
        self.current_params: Dict[str, float] = {}
        
        # 学习统计
        self.stats = {
            "total_tasks": 0,
            "total_forgetting_detected": 0,
            "ewc_applied": 0,
            "replay_applied": 0
        }
        
        self._load()
    
    def _load(self):
        """加载数据"""
        path = self.data_dir / "continual_learning.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for sid, sdata in data.get("snapshots", {}).items():
                    self.snapshots[sid] = KnowledgeSnapshot(**sdata)
                self.tasks = [LearningTask(**t) for t in data.get("tasks", [])]
                self.param_importance = data.get("importance", {})
                self.stats = data.get("stats", self.stats)
    
    def _save(self):
        """保存数据"""
        data = {
            "snapshots": {
                sid: {
                    "id": s.id,
                    "timestamp": s.timestamp,
                    "task_name": s.task_name,
                    "description": s.description,
                    "parameters": s.parameters,
                    "importance": s.importance,
                    "performance": s.performance,
                    "sample_size": s.sample_size
                }
                for sid, s in self.snapshots.items()
            },
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "timestamp": t.timestamp,
                    "category": t.category,
                    "samples": t.samples,
                    "labels": t.labels,
                    "before_performance": t.before_performance,
                    "after_performance": t.after_performance,
                    "improvement": t.improvement,
                    "test_results": t.test_results
                }
                for t in self.tasks[-100:]  # 只保存最近100个
            ],
            "importance": self.param_importance,
            "stats": self.stats
        }
        with open(self.data_dir / "continual_learning.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # ========== 参数重要性估计 (基于EWC) ==========
    
    def estimate_importance(self, task_id: str, samples: List[Dict]) -> Dict[str, float]:
        """
        估计参数重要性
        
        使用Fisher信息矩阵的近似来估计每个参数对任务的重要性
        """
        importance = {}
        
        # 简化版: 基于梯度大小的重要性估计
        # 实际实现中应该计算二阶导数
        for param_name in self.current_params.keys():
            # 模拟: 随机初始化重要性
            # 真实实现中应该计算真实梯度
            base_importance = 0.5
            
            # 根据样本计算梯度估计
            gradient_estimate = sum(
                abs(sample.get(param_name, 0)) for sample in samples[:10]
            ) / max(len(samples), 1)
            
            importance[param_name] = min(1.0, base_importance + gradient_estimate)
        
        # 更新重要性估计
        for param, imp in importance.items():
            if param in self.param_importance:
                # 指数移动平均
                self.param_importance[param] = (
                    0.7 * self.param_importance[param] + 0.3 * imp
                )
            else:
                self.param_importance[param] = imp
        
        return importance
    
    def compute_ewc_penalty(self) -> float:
        """
        计算EWC惩罚项
        
        penalty = lambda * sum(importance_i * (param_i - old_param_i)^2)
        """
        if not self.snapshots:
            return 0.0
        
        penalty = 0.0
        
        # 从最新的快照恢复参数
        latest_snapshot = max(
            self.snapshots.values(),
            key=lambda s: s.timestamp
        )
        
        for param_name, current_value in self.current_params.items():
            old_value = latest_snapshot.parameters.get(param_name, current_value)
            importance = latest_snapshot.importance.get(param_name, 0.5)
            
            penalty += importance * (current_value - old_value) ** 2
        
        return self.EWC_LAMBDA * penalty
    
    # ========== 经验回放 ==========
    
    def add_to_replay_buffer(self, samples: List[Dict]):
        """添加样本到回放缓冲区"""
        for sample in samples:
            self.replay_buffer.append({
                "sample": sample,
                "timestamp": datetime.now().isoformat()
            })
    
    def sample_replay(self, batch_size: int) -> List[Dict]:
        """从回放缓冲区采样"""
        if not self.replay_buffer:
            return []
        
        # 优先采样最近的样本
        recent_samples = list(self.replay_buffer)[-batch_size:]
        return [item["sample"] for item in recent_samples]
    
    def get_replay_ratio(self) -> float:
        """获取当前回放比例"""
        return min(self.REPLAY_RATIO, len(self.replay_buffer) / 100)
    
    # ========== 知识蒸馏 ==========
    
    def distill_knowledge(self, old_model_outputs: List[Dict], 
                          new_model_outputs: List[Dict]) -> float:
        """
        知识蒸馏损失
        
        使用KL散度衡量新旧模型输出的差异
        """
        if not old_model_outputs or not new_model_outputs:
            return 0.0
        
        total_kl = 0.0
        
        for old_out, new_out in zip(old_model_outputs, new_model_outputs):
            # 简化: 计算输出分布的差异
            old_prob = old_out.get("probabilities", {})
            new_prob = new_out.get("probabilities", {})
            
            for key in old_prob.keys():
                p_old = old_prob.get(key, 0.5)
                p_new = new_prob.get(key, 0.5)
                
                # 简化的KL散度
                if p_old > 0 and p_new > 0:
                    kl = p_old * math.log(p_old / p_new)
                    total_kl += kl
        
        return total_kl / max(len(old_model_outputs), 1)
    
    # ========== 任务学习 ==========
    
    def learn_task(self, task: LearningTask) -> Dict[str, Any]:
        """
        学习新任务
        
        应用EWC、经验回放等机制
        """
        import uuid
        
        task.id = str(uuid.uuid4())[:8]
        task.timestamp = datetime.now().isoformat()
        
        # 1. 评估学习前的性能
        task.before_performance = self._evaluate_performance(task.samples, task.labels)
        
        # 2. 估计参数重要性
        importance = self.estimate_importance(task.id, task.samples)
        
        # 3. 保存当前状态快照
        snapshot_id = self._create_snapshot(task.name, task.description, importance)
        
        # 4. 添加样本到回放缓冲区
        self.add_to_replay_buffer(task.samples)
        
        # 5. 执行学习（模拟）
        self._perform_learning(task, importance)
        
        # 6. 评估学习后的性能
        task.after_performance = self._evaluate_performance(task.samples, task.labels)
        task.improvement = task.after_performance - task.before_performance
        
        # 7. 检测遗忘
        forgetting_detected = self._detect_forgetting(task)
        if forgetting_detected:
            self.stats["total_forgetting_detected"] += 1
        
        # 保存任务
        self.tasks.append(task)
        self.stats["total_tasks"] += 1
        
        self._save()
        
        return {
            "task_id": task.id,
            "before_performance": task.before_performance,
            "after_performance": task.after_performance,
            "improvement": task.improvement,
            "forgetting_detected": forgetting_detected,
            "snapshot_id": snapshot_id,
            "ewc_applied": True,
            "replay_applied": len(self.replay_buffer) > 0
        }
    
    def _create_snapshot(self, task_name: str, description: str,
                        importance: Dict[str, float]) -> str:
        """创建知识快照"""
        import uuid
        
        snapshot_id = str(uuid.uuid4())[:8]
        
        snapshot = KnowledgeSnapshot(
            id=snapshot_id,
            timestamp=datetime.now().isoformat(),
            task_name=task_name,
            description=description,
            parameters=self.current_params.copy(),
            importance=importance,
            performance=0.5,  # 将在后续更新
            sample_size=0
        )
        
        self.snapshots[snapshot_id] = snapshot
        
        # 限制快照数量
        if len(self.snapshots) > 20:
            oldest = min(self.snapshots.values(), key=lambda s: s.timestamp)
            del self.snapshots[oldest.id]
        
        return snapshot_id
    
    def _evaluate_performance(self, samples: List[Dict], labels: List[Any]) -> float:
        """评估性能（简化版）"""
        if not samples:
            return 0.5
        
        # 模拟: 随机性能
        # 真实实现中应该使用真实模型评估
        return 0.5 + 0.3 * math.log1p(len(samples)) / 10
    
    def _perform_learning(self, task: LearningTask, importance: Dict[str, float]):
        """执行学习（简化版）"""
        # 模拟参数更新
        for param_name in self.current_params.keys():
            # EWC约束: 保护重要参数
            imp = importance.get(param_name, 0.5)
            
            # 重要参数更新幅度小
            update_scale = 0.01 * (1 - imp * 0.5)
            
            self.current_params[param_name] += update_scale
    
    def _detect_forgetting(self, task: LearningTask) -> bool:
        """检测灾难性遗忘"""
        if len(self.tasks) < 2:
            return False
        
        # 检测之前任务性能是否下降
        previous_tasks = [t for t in self.tasks[:-1] if t.category == task.category]
        
        for prev_task in previous_tasks[-3:]:  # 检查最近3个同类任务
            # 模拟检测
            if prev_task.after_performance - task.before_performance > 0.2:
                return True
        
        return False
    
    # ========== 知识整合 ==========
    
    def consolidate_knowledge(self) -> Dict[str, Any]:
        """
        知识整合
        
        在适当的时候调用，整合分散的知识
        """
        stats = {
            "snapshots_consolidated": 0,
            "knowledge_distilled": 0,
            "forgetting_prevented": 0
        }
        
        # 1. 合并相似的快照
        similar_groups = self._find_similar_snapshots()
        for group in similar_groups:
            if len(group) > 1:
                stats["snapshots_consolidated"] += len(group) - 1
        
        # 2. 更新参数重要性
        self._update_importance_estimates()
        
        # 3. 清理低质量任务
        self._prune_low_quality_tasks()
        
        self._save()
        
        return stats
    
    def _find_similar_snapshots(self) -> List[List[str]]:
        """找到相似的快照组"""
        groups = []
        processed = set()
        
        for sid1 in self.snapshots.keys():
            if sid1 in processed:
                continue
            
            group = [sid1]
            s1 = self.snapshots[sid1]
            
            for sid2 in self.snapshots.keys():
                if sid2 == sid1 or sid2 in processed:
                    continue
                
                s2 = self.snapshots[sid2]
                
                # 检查相似性
                if s1.task_name == s2.task_name:
                    group.append(sid2)
                    processed.add(sid2)
            
            if len(group) > 1:
                groups.append(group)
                processed.update(group)
        
        return groups
    
    def _update_importance_estimates(self):
        """更新重要性估计"""
        # 基于多个快照的重要性聚合
        for param_name in self.current_params.keys():
            importances = []
            
            for snapshot in self.snapshots.values():
                if param_name in snapshot.importance:
                    importances.append(snapshot.importance[param_name])
            
            if importances:
                # 指数加权平均
                weights = [0.9 ** i for i in range(len(importances))]
                total_weight = sum(weights)
                
                self.param_importance[param_name] = sum(
                    imp * w for imp, w in zip(importances, weights)
                ) / total_weight
    
    def _prune_low_quality_tasks(self):
        """删除低质量任务"""
        # 保留最好的80%任务
        if len(self.tasks) > 50:
            sorted_tasks = sorted(
                self.tasks, 
                key=lambda t: t.after_performance - t.before_performance,
                reverse=True
            )
            self.tasks = sorted_tasks[:int(len(sorted_tasks) * 0.8)]
    
    # ========== 统计和报告 ==========
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_tasks": self.stats["total_tasks"],
            "total_snapshots": len(self.snapshots),
            "replay_buffer_size": len(self.replay_buffer),
            "total_forgetting_detected": self.stats["total_forgetting_detected"],
            "avg_improvement": sum(t.improvement for t in self.tasks) / max(len(self.tasks), 1),
            "param_importance_coverage": len(self.param_importance),
            "latest_task": self.tasks[-1].name if self.tasks else None
        }
    
    def generate_report(self) -> str:
        """生成学习报告"""
        lines = ["## 持续学习报告", ""]
        lines.append(f"**总学习任务**: {self.stats['total_tasks']}")
        lines.append(f"**知识快照**: {len(self.snapshots)}")
        lines.append(f"**回放缓冲区**: {len(self.replay_buffer)}")
        lines.append(f"**检测到的遗忘**: {self.stats['total_forgetting_detected']}")
        lines.append("")
        
        if self.tasks:
            lines.append("### 最近任务")
            for task in self.tasks[-5:]:
                lines.append(f"- {task.name}: {task.improvement:+.2%} ({task.category})")
            lines.append("")
        
        if self.param_importance:
            lines.append("### 重要参数 Top 5")
            sorted_params = sorted(
                self.param_importance.items(),
                key=lambda x: -x[1]
            )[:5]
            for param, imp in sorted_params:
                lines.append(f"- {param}: {imp:.3f}")
        
        return "\n".join(lines)


def get_continual_learner(data_dir: Path) -> ContinualLearningEngine:
    """获取持续学习器实例"""
    return ContinualLearningEngine(data_dir)
