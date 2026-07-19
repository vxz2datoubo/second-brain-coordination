"""
neural_memory.py — 神经记忆网络 (Neural Memory Network)
=========================================================
基于最新深度学习研究的长期记忆系统，融合：

1. 可微分神经记忆 (Differentiable Neural Memory) - 类比NTM/DNC
2. 注意力机制检索 (Attention-based Retrieval) - 类比Transformer
3. 记忆巩固 (Memory Consolidation) - 类比记忆重播机制
4. 遗忘机制 (Forgetting Mechanism) - 基于Hebbian学习规则

学术参考:
- Neural Turing Machines (Graves et al., 2014)
- Differentiable Neural Computer (Graves et al., 2016)
- Memory Networks (Weston et al., 2015)
- Transformer Memory (Vaswani et al., 2017)
- Holographic Reduced Representations (Plate, 1995)

注意: 使用纯Python实现，无需numpy依赖
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict


# ========== 向量工具 (纯Python实现) ==========

class VectorStore:
    """简化版向量存储和检索 (无需外部依赖)"""
    
    def __init__(self, dim: int = 64):
        self.dim = dim
        self.vectors: Dict[str, List[float]] = {}
        self.metadata: Dict[str, dict] = {}
    
    def add(self, key: str, vector: List[float], metadata: dict = None):
        """添加向量"""
        if len(vector) != self.dim:
            vector = self._resize(vector)
        self.vectors[key] = vector
        self.metadata[key] = metadata or {}
    
    def _resize(self, v: List[float]) -> List[float]:
        """调整向量维度"""
        if len(v) < self.dim:
            return v + [0.0] * (self.dim - len(v))
        return v[:self.dim]
    
    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """余弦相似度"""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(a * a for a in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
    
    def search(self, query: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        """向量检索"""
        if len(query) != self.dim:
            query = self._resize(query)
        
        scores = []
        for key, vec in self.vectors.items():
            sim = self.cosine_similarity(query, vec)
            scores.append((key, sim))
        
        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]


# ========== 记忆项 ==========

@dataclass
class MemoryItem:
    """记忆项"""
    id: str
    content: str
    embedding: List[float]
    key: List[float]  # 用于内容寻址的键
    importance: float = 0.5
    strength: float = 0.5  # 记忆强度
    last_accessed: str = ""
    access_count: int = 0
    decay_rate: float = 0.01  # 遗忘速率
    tags: List[str] = field(default_factory=list)
    source: str = "unknown"


# ========== 神经记忆网络 ==========

class NeuralMemoryNetwork:
    """
    神经记忆网络 - 实现类脑记忆系统
    
    核心机制:
    1. 内容寻址 (Content-based Addressing) - 基于余弦相似度
    2. 位置寻址 (Location-based Addressing) - 基于最近访问
    3. 读写门控 (Read/Write Gating) - 控制信息流动
    4. 记忆强度更新 - Hebbian学习规则
    5. 主动遗忘 - 低于阈值记忆被清除
    """
    
    MEMORY_SIZE = 1000  # 记忆容量
    SIMILARITY_THRESHOLD = 0.6  # 相似度阈值
    STRENGTH_DECAY = 0.995  # 每次访问后的衰减
    FORGET_THRESHOLD = 0.1  # 遗忘阈值
    ATTENTION_WINDOW = 50  # 注意力窗口大小
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.vector_store = VectorStore(dim=64)
        self.memories: Dict[str, MemoryItem] = {}
        self.associations: Dict[str, Set[str]] = defaultdict(set)  # 记忆关联
        
        # 加载已有数据
        self._load()
    
    def _load(self):
        """加载记忆数据"""
        memory_path = self.data_dir / "neural_memory.json"
        if memory_path.exists():
            with open(memory_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for mid, mdata in data.get("memories", {}).items():
                self.memories[mid] = MemoryItem(
                    id=mdata["id"],
                    content=mdata["content"],
                    embedding=mdata["embedding"],
                    key=mdata["key"],
                    importance=mdata.get("importance", 0.5),
                    strength=mdata.get("strength", 0.5),
                    last_accessed=mdata.get("last_accessed", ""),
                    access_count=mdata.get("access_count", 0),
                    decay_rate=mdata.get("decay_rate", 0.01),
                    tags=mdata.get("tags", []),
                    source=mdata.get("source", "unknown")
                )
                self.vector_store.add(mid, self.memories[mid].embedding)
            
            self.associations = defaultdict(set, data.get("associations", {}))
    
    def _save(self):
        """保存记忆数据"""
        data = {
            "memories": {
                mid: {
                    "id": m.id,
                    "content": m.content,
                    "embedding": m.embedding,
                    "key": m.key,
                    "importance": m.importance,
                    "strength": m.strength,
                    "last_accessed": m.last_accessed,
                    "access_count": m.access_count,
                    "decay_rate": m.decay_rate,
                    "tags": m.tags,
                    "source": m.source
                }
                for mid, m in self.memories.items()
            },
            "associations": {k: list(v) for k, v in self.associations.items()}
        }
        
        with open(self.data_dir / "neural_memory.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _text_to_embedding(self, text: str) -> List[float]:
        """文本转嵌入 (简化版，基于词频哈希)"""
        dim = self.vector_store.dim
        vec = [0.0] * dim
        
        # 简单的词哈希嵌入
        words = text.lower().split()
        for i, word in enumerate(words[:min(len(words), dim)]):
            word_hash = sum(ord(c) * (31 ** j) for j, c in enumerate(word[:10]))
            vec[i % dim] += word_hash % 100
        
        # 添加字符级特征
        for i, char in enumerate(text[:dim]):
            vec[i % dim] += ord(char) % 10
        
        # 归一化
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        
        return vec
    
    def write(self, content: str, importance: float = 0.5, 
              tags: List[str] = None, source: str = "unknown") -> str:
        """
        写入记忆 (Write Operation)
        
        使用内容寻址找到相似记忆并决定是否合并或新建
        """
        import uuid
        
        embedding = self._text_to_embedding(content)
        key = embedding  # 内容键
        
        # 内容寻址：查找相似记忆
        candidates = self.vector_store.search(embedding, top_k=5)
        
        # 检查是否需要合并
        for mid, similarity in candidates:
            if similarity > 0.85 and mid in self.memories:
                # 高相似度记忆：强化连接
                self._strengthen_memory(mid)
                self.memories[mid].access_count += 1
                self.memories[mid].last_accessed = datetime.now().isoformat()
                self._save()
                return mid
        
        # 新建记忆
        memory_id = str(uuid.uuid4())[:8]
        memory = MemoryItem(
            id=memory_id,
            content=content,
            embedding=embedding,
            key=key,
            importance=importance,
            strength=0.3,  # 新记忆强度较低
            last_accessed=datetime.now().isoformat(),
            access_count=1,
            tags=tags or [],
            source=source
        )
        
        self.memories[memory_id] = memory
        self.vector_store.add(memory_id, embedding)
        
        # 关联相似记忆
        for mid, sim in candidates:
            if sim > 0.5:
                self.associations[memory_id].add(mid)
                self.associations[mid].add(memory_id)
        
        # 检查容量，遗忘低强度记忆
        self._prune_if_needed()
        self._save()
        
        return memory_id
    
    def _strengthen_memory(self, memory_id: str):
        """强化记忆 (Hebbian学习)"""
        if memory_id not in self.memories:
            return
        
        m = self.memories[memory_id]
        # Hebbian规则: 同时激活的连接强化
        m.strength = min(1.0, m.strength * 1.1)
        m.strength = max(0.1, m.strength - self.STRENGTH_DECAY)  # 衰减
    
    def read(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        读取记忆 (Read Operation)
        
        使用内容寻址 + 注意力机制检索相关记忆
        """
        query_embedding = self._text_to_embedding(query)
        
        # 阶段1: 内容寻址
        content_scores = self.vector_store.search(query_embedding, top_k=top_k * 2)
        
        # 阶段2: 注意力加权
        results = []
        now = datetime.now()
        
        for mid, content_sim in content_scores:
            if mid not in self.memories:
                continue
            
            m = self.memories[mid]
            
            # 计算时间衰减因子
            try:
                last_access = datetime.fromisoformat(m.last_accessed)
                days_passed = (now - last_access).total_seconds() / 86400
                time_decay = math.exp(-m.decay_rate * days_passed)
            except:
                time_decay = 0.5
            
            # 访问频率因子
            freq_factor = math.log1p(m.access_count) / 10
            
            # 综合评分
            final_score = (
                content_sim * 0.4 +           # 内容相似度
                m.strength * 0.25 +            # 记忆强度
                m.importance * 0.15 +          # 重要性
                time_decay * 0.15 +            # 时间衰减
                freq_factor * 0.05             # 访问频率
            )
            
            # 更新访问信息
            m.last_accessed = now.isoformat()
            m.access_count += 1
            m.strength = min(1.0, m.strength * 1.05)  # 轻微强化
            
            results.append({
                "id": m.id,
                "content": m.content,
                "score": final_score,
                "content_similarity": content_sim,
                "strength": m.strength,
                "importance": m.importance,
                "last_accessed": m.last_accessed,
                "tags": m.tags,
                "source": m.source
            })
        
        # 按综合评分排序
        results.sort(key=lambda x: -x["score"])
        self._save()
        
        return results[:top_k]
    
    def associate(self, memory_id1: str, memory_id2: str):
        """建立记忆关联"""
        if memory_id1 in self.memories and memory_id2 in self.memories:
            self.associations[memory_id1].add(memory_id2)
            self.associations[memory_id2].add(memory_id1)
            self._save()
    
    def get_associated(self, memory_id: str, depth: int = 1) -> List[Dict]:
        """获取关联记忆 (多跳)"""
        if memory_id not in self.memories:
            return []
        
        visited = {memory_id}
        current_level = {memory_id}
        
        for _ in range(depth):
            next_level = set()
            for mid in current_level:
                for associated_id in self.associations.get(mid, []):
                    if associated_id not in visited and associated_id in self.memories:
                        next_level.add(associated_id)
                        visited.add(associated_id)
            current_level = next_level
        
        results = []
        for mid in visited:
            if mid != memory_id:
                m = self.memories[mid]
                results.append({
                    "id": m.id,
                    "content": m.content,
                    "strength": m.strength,
                    "tags": m.tags
                })
        
        return results
    
    def _prune_if_needed(self):
        """主动遗忘：删除低于阈值或容量超载的记忆"""
        # 容量超载时，删除最低强度的记忆
        if len(self.memories) > self.MEMORY_SIZE:
            # 按综合评分排序
            scored = []
            now = datetime.now()
            for mid, m in self.memories.items():
                try:
                    last_access = datetime.fromisoformat(m.last_accessed)
                    days = (now - last_access).total_seconds() / 86400
                    time_factor = math.exp(-m.decay_rate * days)
                except:
                    time_factor = 0.5
                
                score = m.strength * m.importance * time_factor
                scored.append((mid, score))
            
            scored.sort(key=lambda x: x[1])
            
            # 删除最低的20%
            to_delete = scored[:len(scored) // 5]
            for mid, _ in to_delete:
                if mid in self.memories:
                    del self.memories[mid]
                    self.vector_store.vectors.pop(mid, None)
        
        # 遗忘低于阈值
        to_forget = []
        for mid, m in self.memories.items():
            if m.strength < self.FORGET_THRESHOLD:
                to_forget.append(mid)
        
        for mid in to_forget:
            del self.memories[mid]
            self.vector_store.vectors.pop(mid, None)
    
    def consolidate(self) -> Dict:
        """
        记忆巩固 (Memory Consolidation)
        
        在睡眠/休息期间，将短期记忆整合为长期记忆
        1. 强化高强度记忆
        2. 弱化低强度记忆
        3. 建立新的关联
        """
        stats = {
            "strengthened": 0,
            "weakened": 0,
            "forgotten": 0,
            "new_associations": 0
        }
        
        # 计算平均强度
        if not self.memories:
            return stats
        
        strengths = [m.strength for m in self.memories.values()]
        avg_strength = sum(strengths) / len(strengths)
        
        # 强度调整
        for mid, m in self.memories.items():
            if m.strength > avg_strength:
                # 高于平均：强化
                m.strength = min(1.0, m.strength * 1.05)
                m.importance = min(1.0, m.importance * 1.02)
                stats["strengthened"] += 1
            else:
                # 低于平均：弱化
                m.strength *= 0.95
                stats["weakened"] += 1
            
            # 访问过少则遗忘
            if m.access_count < 2 and m.strength < 0.2:
                stats["forgotten"] += 1
        
        # 建立跨域关联
        self._build_cross_domain_associations()
        
        self._prune_if_needed()
        self._save()
        
        return stats
    
    def _build_cross_domain_associations(self):
        """建立跨领域关联"""
        # 按标签分组
        tag_groups: Dict[str, List[str]] = defaultdict(list)
        for mid, m in self.memories.items():
            for tag in m.tags:
                tag_groups[tag].append(mid)
        
        # 同一标签的记忆互相关联
        for tag, mids in tag_groups.items():
            if len(mids) >= 2:
                for i, mid1 in enumerate(mids):
                    for mid2 in mids[i+1:]:
                        if mid2 not in self.associations.get(mid1, set()):
                            self.associations[mid1].add(mid2)
                            self.associations[mid2].add(mid1)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if not self.memories:
            return {
                "total_memories": 0,
                "avg_strength": 0,
                "avg_importance": 0,
                "total_associations": sum(len(v) for v in self.associations.values()) // 2
            }
        
        strengths = [m.strength for m in self.memories.values()]
        importances = [m.importance for m in self.memories.values()]
        
        return {
            "total_memories": len(self.memories),
            "avg_strength": sum(strengths) / len(strengths),
            "avg_importance": sum(importances) / len(importances),
            "total_associations": sum(len(v) for v in self.associations.values()) // 2,
            "strong_memories": sum(1 for s in strengths if s > 0.7),
            "weak_memories": sum(1 for s in strengths if s < 0.3),
            "memory_capacity_used": len(self.memories) / self.MEMORY_SIZE
        }


def get_neural_memory(data_dir: Path) -> NeuralMemoryNetwork:
    """获取神经记忆网络实例"""
    return NeuralMemoryNetwork(data_dir)
