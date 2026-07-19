"""
episodic_memory.py — 情境记忆系统
==================================
基于情境的体验记忆存储与检索，模拟人类的情景记忆系统。

核心概念:
1. 情境编码 (Situation Encoding) - 将决策情境编码为向量
2. 情景记忆 (Episodic Memory) - 存储"在什么情况下做了什么决策"
3. 情景检索 (Episodic Retrieval) - 基于当前情境检索相似经验
4. 记忆整合 (Memory Consolidation) - 将短期情景记忆整合为长期知识

学术参考:
- Hippocampal Memory System (O'Keefe & Nadel, 1978)
- Episodic Memory (Tulving, 1972)
- Complementary Learning Systems (McClelland et al., 1995)
- Neural Context Vectors (Miller et al., 2016)
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict


# ========== 情景定义 ==========

@dataclass
class Episode:
    """情景记忆"""
    id: str
    timestamp: str
    
    # 情境描述
    situation_type: str          # "bull_market", "bear_market", "volatile", "range"
    market_trend: str            # "up", "down", "neutral"
    volatility: str              # "high", "medium", "low"
    
    # 市场状态
    price_change: float          # 价格变化百分比
    volume_ratio: float          # 量比
    sector_performance: float    # 板块表现
    
    # 决策信息
    action: str                  # "buy", "sell", "hold"
    position_size: float         # 仓位比例
    confidence: float            # 决策置信度
    
    # 结果
    outcome: Optional[float] = None  # 收益结果
    outcome_time: str = ""           # 结果记录时间
    
    # 反思
    reflection: str = ""         # 事后反思
    lessons: List[str] = field(default_factory=list)  # 学到的教训
    
    # 元数据
    stock_code: str = ""
    stock_name: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class SituationVector:
    """情境向量"""
    vector: List[float]          # 情境编码向量
    key_components: Dict[str, float] = field(default_factory=dict)  # 关键分量


# ========== 情景编码器 ==========

class SituationEncoder:
    """
    情境编码器
    
    将市场情境转换为高维向量表示
    """
    
    DIM = 32  # 情境向量维度
    
    def encode(self, episode: Episode) -> SituationVector:
        """将情景编码为向量"""
        vec = [0.0] * self.DIM
        
        # 1. 市场状态编码 (0-7)
        market_state = self._encode_market_state(episode)
        vec[0] = market_state
        
        # 2. 趋势编码 (8-11)
        trend_encoding = self._encode_trend(episode)
        vec[1] = trend_encoding[0]
        vec[2] = trend_encoding[1]
        
        # 3. 价格变化编码 (12-15)
        price_encoding = self._encode_price_change(episode.price_change)
        vec[3] = price_encoding[0]
        vec[4] = price_encoding[1]
        
        # 4. 成交量编码 (16-19)
        volume_encoding = self._encode_volume(episode.volume_ratio)
        vec[5] = volume_encoding[0]
        vec[6] = volume_encoding[1]
        
        # 5. 决策类型编码 (20-23)
        action_encoding = self._encode_action(episode.action)
        vec[7] = action_encoding[0]
        vec[8] = action_encoding[1]
        
        # 6. 置信度编码 (24-27)
        vec[9] = episode.confidence
        
        # 7. 仓位编码 (28-31)
        vec[10] = episode.position_size
        
        # 归一化
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        
        # 提取关键分量
        key_components = {
            "market_state": market_state,
            "trend_strength": abs(trend_encoding[0]),
            "price_signal": price_encoding[0],
            "volume_signal": volume_encoding[0],
            "action": episode.action,
            "confidence": episode.confidence
        }
        
        return SituationVector(vector=vec, key_components=key_components)
    
    def _encode_market_state(self, episode: Episode) -> float:
        """编码市场状态"""
        state_map = {
            ("up", "high"): 0.8,
            ("up", "medium"): 0.6,
            ("up", "low"): 0.4,
            ("neutral", "high"): 0.3,
            ("neutral", "medium"): 0.0,
            ("neutral", "low"): -0.2,
            ("down", "high"): -0.8,
            ("down", "medium"): -0.6,
            ("down", "low"): -0.4,
        }
        return state_map.get((episode.market_trend, episode.volatility), 0.0)
    
    def _encode_trend(self, episode: Episode) -> Tuple[float, float]:
        """编码趋势"""
        # x: 方向, y: 强度
        direction_map = {"up": 1.0, "neutral": 0.0, "down": -1.0}
        direction = direction_map.get(episode.market_trend, 0.0)
        return (direction, abs(episode.price_change) / 10.0)
    
    def _encode_price_change(self, change: float) -> Tuple[float, float]:
        """编码价格变化"""
        # x: 方向和幅度, y: 变化速率
        normalized = max(-1.0, min(1.0, change / 10.0))
        return (normalized, abs(normalized))
    
    def _encode_volume(self, ratio: float) -> Tuple[float, float]:
        """编码成交量"""
        # x: 量比方向, y: 量比强度
        if ratio > 1.5:
            return (0.8, (ratio - 1) / 2.0)
        elif ratio < 0.6:
            return (-0.8, (1 - ratio) / 0.6)
        else:
            return (0.0, 0.0)
    
    def _encode_action(self, action: str) -> Tuple[float, float]:
        """编码行动"""
        action_map = {
            "buy": (1.0, 0.0),
            "hold": (0.0, 0.0),
            "sell": (-1.0, 0.5)
        }
        return action_map.get(action, (0.0, 0.0))


# ========== 情景记忆系统 ==========

class EpisodicMemory:
    """
    情景记忆系统
    
    存储和检索交易决策的情景经验
    """
    
    SIMILARITY_THRESHOLD = 0.7  # 相似度阈值
    RECENCY_WEIGHT = 0.3        # 近因效应权重
    OUTCOME_WEIGHT = 0.5        # 结果权重
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.encoder = SituationEncoder()
        self.episodes: Dict[str, Episode] = {}
        self.situation_vectors: Dict[str, List[float]] = {}
        self.similarity_index: Dict[str, List[str]] = defaultdict(list)  # 快速检索
        
        self._load()
    
    def _load(self):
        """加载数据"""
        path = self.data_dir / "episodic_memory.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for eid, edata in data.get("episodes", {}).items():
                    self.episodes[eid] = Episode(**edata)
                self.situation_vectors = data.get("vectors", {})
    
    def _save(self):
        """保存数据"""
        data = {
            "episodes": {
                eid: {
                    "id": e.id,
                    "timestamp": e.timestamp,
                    "situation_type": e.situation_type,
                    "market_trend": e.market_trend,
                    "volatility": e.volatility,
                    "price_change": e.price_change,
                    "volume_ratio": e.volume_ratio,
                    "sector_performance": e.sector_performance,
                    "action": e.action,
                    "position_size": e.position_size,
                    "confidence": e.confidence,
                    "outcome": e.outcome,
                    "outcome_time": e.outcome_time,
                    "reflection": e.reflection,
                    "lessons": e.lessons,
                    "stock_code": e.stock_code,
                    "stock_name": e.stock_name,
                    "tags": e.tags
                }
                for eid, e in self.episodes.items()
            },
            "vectors": self.situation_vectors
        }
        with open(self.data_dir / "episodic_memory.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def record(self, episode: Episode) -> str:
        """记录情景记忆"""
        import uuid
        
        episode.id = str(uuid.uuid4())[:8]
        episode.timestamp = datetime.now().isoformat()
        
        # 编码情境
        vec = self.encoder.encode(episode)
        self.situation_vectors[episode.id] = vec.vector
        
        # 存储
        self.episodes[episode.id] = episode
        
        # 更新相似度索引
        self._update_similarity_index(episode.id)
        
        self._save()
        return episode.id
    
    def _update_similarity_index(self, episode_id: str):
        """更新相似度索引"""
        if episode_id not in self.situation_vectors:
            return
        
        vec = self.situation_vectors[episode_id]
        
        # 找到相似的情景
        similar = []
        for other_id, other_vec in self.situation_vectors.items():
            if other_id == episode_id:
                continue
            
            sim = self._cosine_similarity(vec, other_vec)
            if sim > 0.5:
                similar.append((other_id, sim))
        
        similar.sort(key=lambda x: -x[1])
        self.similarity_index[episode_id] = [sid for sid, _ in similar[:10]]
    
    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(a * a for a in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
    
    def retrieve(self, situation: Dict, top_k: int = 5) -> List[Dict]:
        """
        基于当前情境检索相似经验
        
        Args:
            situation: 当前市场情境
                - market_trend: "up", "down", "neutral"
                - volatility: "high", "medium", "low"
                - price_change: float
                - volume_ratio: float
                - action: "buy", "sell", "hold"
        
        Returns:
            相似情景经验列表
        """
        # 构建伪情景
        query_episode = Episode(
            id="query",
            timestamp=datetime.now().isoformat(),
            situation_type=situation.get("situation_type", "range"),
            market_trend=situation.get("market_trend", "neutral"),
            volatility=situation.get("volatility", "medium"),
            price_change=situation.get("price_change", 0.0),
            volume_ratio=situation.get("volume_ratio", 1.0),
            sector_performance=situation.get("sector_performance", 0.0),
            action=situation.get("action", "hold"),
            position_size=situation.get("position_size", 0.5),
            confidence=situation.get("confidence", 0.5)
        )
        
        # 编码查询情境
        query_vec = self.encoder.encode(query_episode)
        
        # 计算与所有情景的相似度
        scored_episodes = []
        now = datetime.now()
        
        for eid, episode in self.episodes.items():
            if eid == "query":
                continue
            
            episode_vec = self.situation_vectors.get(eid, [])
            if not episode_vec:
                continue
            
            # 基础相似度
            similarity = self._cosine_similarity(query_vec.vector, episode_vec)
            
            # 近因效应调整
            try:
                age = (now - datetime.fromisoformat(episode.timestamp)).total_seconds() / 86400
                recency_factor = math.exp(-age / 30)  # 30天衰减
            except:
                recency_factor = 0.5
            
            # 结果调整
            outcome_factor = 0.5
            if episode.outcome is not None:
                if episode.outcome > 0:
                    outcome_factor = 0.8 + min(0.2, episode.outcome)
                else:
                    outcome_factor = 0.8 + max(-0.3, episode.outcome)
            
            # 综合评分
            final_score = (
                similarity * 0.4 +
                recency_factor * self.RECENCY_WEIGHT +
                outcome_factor * self.OUTCOME_WEIGHT
            )
            
            scored_episodes.append({
                "id": eid,
                "episode": episode,
                "similarity": similarity,
                "recency_factor": recency_factor,
                "outcome": episode.outcome,
                "final_score": final_score,
                "action": episode.action,
                "confidence": episode.confidence,
                "reflection": episode.reflection,
                "lessons": episode.lessons
            })
        
        # 排序
        scored_episodes.sort(key=lambda x: -x["final_score"])
        
        return scored_episodes[:top_k]
    
    def update_outcome(self, episode_id: str, outcome: float, reflection: str = "", 
                       lessons: List[str] = None):
        """更新情景结果"""
        if episode_id not in self.episodes:
            return
        
        episode = self.episodes[episode_id]
        episode.outcome = outcome
        episode.outcome_time = datetime.now().isoformat()
        episode.reflection = reflection
        if lessons:
            episode.lessons = lessons
        
        self._save()
    
    def get_action_advice(self, situation: Dict) -> Dict[str, Any]:
        """获取行动建议"""
        similar = self.retrieve(situation, top_k=10)
        
        if not similar:
            return {
                "advice": "hold",
                "confidence": 0.3,
                "reasoning": "没有找到相似经验，建议观望",
                "similar_experiences": 0
            }
        
        # 统计历史行动的成功率
        action_stats = {"buy": [], "sell": [], "hold": []}
        
        for s in similar:
            action = s["action"]
            outcome = s["episode"].outcome
            if outcome is not None:
                action_stats[action].append(outcome)
        
        # 计算最佳行动
        best_action = "hold"
        best_avg_outcome = 0.0
        
        for action, outcomes in action_stats.items():
            if outcomes:
                avg = sum(outcomes) / len(outcomes)
                if avg > best_avg_outcome:
                    best_avg_outcome = avg
                    best_action = action
        
        # 生成建议
        best_similar = similar[0]
        advice = {
            "advice": best_action,
            "confidence": best_similar["final_score"],
            "reasoning": self._generate_reasoning(best_action, best_similar, action_stats),
            "similar_experiences": len(similar),
            "success_rate": self._calculate_success_rate(action_stats.get(best_action, [])),
            "avg_outcome": best_avg_outcome,
            "lessons": best_similar.get("lessons", []),
            "reflection": best_similar.get("reflection", "")
        }
        
        return advice
    
    def _generate_reasoning(self, action: str, similar: Dict, 
                           action_stats: Dict) -> str:
        """生成推理说明"""
        outcomes = action_stats.get(action, [])
        if not outcomes:
            return f"没有'{action}'行动的记录，建议谨慎"
        
        avg_outcome = sum(outcomes) / len(outcomes)
        wins = sum(1 for o in outcomes if o > 0)
        win_rate = wins / len(outcomes)
        
        reasoning = f"基于{len(outcomes)}个相似情景，'{action}'行动平均收益{avg_outcome:.2%}，胜率{win_rate:.0%}。"
        
        if avg_outcome > 0:
            reasoning += "历史表现良好，建议执行。"
        else:
            reasoning += "历史表现一般，建议谨慎。"
        
        return reasoning
    
    def _calculate_success_rate(self, outcomes: List[float]) -> float:
        """计算胜率"""
        if not outcomes:
            return 0.0
        return sum(1 for o in outcomes if o > 0) / len(outcomes)
    
    def get_stats(self) -> Dict:
        """获取统计"""
        total = len(self.episodes)
        with_outcome = sum(1 for e in self.episodes.values() if e.outcome is not None)
        
        outcomes = [e.outcome for e in self.episodes.values() if e.outcome is not None]
        
        return {
            "total_episodes": total,
            "with_outcome": with_outcome,
            "avg_outcome": sum(outcomes) / len(outcomes) if outcomes else 0.0,
            "win_rate": sum(1 for o in outcomes if o > 0) / len(outcomes) if outcomes else 0.0,
            "action_distribution": {
                action: sum(1 for e in self.episodes.values() if e.action == action)
                for action in ["buy", "sell", "hold"]
            }
        }


def get_episodic_memory(data_dir: Path) -> EpisodicMemory:
    """获取情景记忆实例"""
    return EpisodicMemory(data_dir)
