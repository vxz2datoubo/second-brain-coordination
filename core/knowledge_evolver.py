"""
knowledge_evolver.py — 知识进化引擎
知识蒸馏、遗忘管理和自我进化
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import math


# 遗忘阈值
FORGET_THRESHOLD = 0.3  # 掌握度低于此值触发强化
DECAY_RATE = 0.05  # 每日遗忘率
REVIVAL_THRESHOLD = 0.6  # 复活阈值


@dataclass
class KnowledgeNode:
    id: str
    title: str
    content: str
    category: str
    importance: int
    mastery: float  # 掌握度 0-1
    activation: float  # 激活度 0-1
    last_accessed: str = ""
    created_at: str = ""
    access_count: int = 0
    successful_applications: int = 0
    failed_applications: int = 0
    related_nodes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class EvolutionEvent:
    timestamp: str
    event_type: str  # "strengthen" | "decay" | "prune" | "consolidate" | "distill"
    node_id: str
    description: str
    mastery_before: float = 0.0
    mastery_after: float = 0.0


class KnowledgeEvolver:
    """知识进化引擎"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "second-brain"
        self.knowledge_file = self.data_dir / "knowledge_evolution.json"
        self.events_file = self.data_dir / "evolution_events.json"
        self.knowledge = self._load_knowledge()
        self.events = self._load_events()
    
    def _load_knowledge(self) -> Dict[str, Dict]:
        try:
            with open(self.knowledge_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"nodes": {}, "clusters": {}, "meta": {"last_consolidation": ""}}
    
    def _save_knowledge(self):
        self.knowledge_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.knowledge_file, "w", encoding="utf-8") as f:
            json.dump(self.knowledge, f, ensure_ascii=False, indent=2)
    
    def _load_events(self) -> List[Dict]:
        try:
            with open(self.events_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    
    def _save_events(self):
        self.events_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.events_file, "w", encoding="utf-8") as f:
            json.dump(self.events, f, ensure_ascii=False, indent=2)
    
    def _record_event(self, event: EvolutionEvent):
        self.events.append(event.__dict__)
        if len(self.events) > 1000:
            self.events = self.events[-1000:]
        self._save_events()
    
    def add_knowledge(self, title: str, content: str, category: str = "", importance: int = 3, tags: Optional[List[str]] = None) -> str:
        import uuid
        node_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        
        node = KnowledgeNode(
            id=node_id, title=title, content=content, category=category,
            importance=importance, mastery=0.5, activation=0.5,
            last_accessed=now, created_at=now, tags=tags or []
        )
        
        self.knowledge["nodes"][node_id] = node.__dict__
        self._save_knowledge()
        
        return node_id
    
    def access_knowledge(self, node_id: str, application_success: Optional[bool] = None) -> float:
        """访问知识节点，更新掌握度和激活度"""
        if node_id not in self.knowledge["nodes"]:
            return 0.0
        
        node = self.knowledge["nodes"][node_id]
        now = datetime.now()
        now_iso = now.isoformat()
        
        # 计算时间间隔（天）
        last_access = datetime.fromisoformat(node["last_accessed"])
        days_passed = (now - last_access).total_seconds() / 86400
        
        # 更新激活度（基于时间衰减）
        decay_factor = math.exp(-DECAY_RATE * days_passed)
        node["activation"] = max(0.1, node["activation"] * decay_factor)
        
        # 更新掌握度
        if application_success is True:
            node["successful_applications"] += 1
            node["mastery"] = min(1.0, node["mastery"] + 0.1)
            node["activation"] = min(1.0, node["activation"] + 0.2)
        elif application_success is False:
            node["failed_applications"] += 1
            node["mastery"] = max(0.1, node["mastery"] - 0.05)
        
        # 每次访问都增加激活度
        node["activation"] = min(1.0, node["activation"] + 0.1)
        node["access_count"] += 1
        node["last_accessed"] = now_iso
        
        self._save_knowledge()
        return node["mastery"]
    
    def strengthen_connection(self, node_id1: str, node_id2: str) -> bool:
        """强化两个知识节点之间的连接"""
        for node_id in [node_id1, node_id2]:
            if node_id in self.knowledge["nodes"]:
                node = self.knowledge["nodes"][node_id]
                if node_id not in node["related_nodes"]:
                    node["related_nodes"].append(node_id)
        
        self._save_knowledge()
        return True
    
    def consolidate_knowledge(self) -> Dict:
        """知识整合：合并相似知识，强化关联"""
        nodes = self.knowledge["nodes"]
        consolidation_results = {"merged": 0, "strengthened": 0, "pruned": 0}
        
        # 1. 查找高激活度节点并强化其关联
        active_nodes = [n for n in nodes.values() if n["activation"] > 0.7]
        for node in active_nodes:
            if len(node["related_nodes"]) < 3:
                # 寻找相似节点建立连接
                for other in nodes.values():
                    if other["id"] != node["id"] and other["id"] not in node["related_nodes"]:
                        if self._calculate_similarity(node, other) > 0.5:
                            node["related_nodes"].append(other["id"])
                            other["related_nodes"].append(node["id"])
                            consolidation_results["strengthened"] += 1
                            break
        
        # 2. 剪枝低激活度节点
        nodes_to_prune = []
        for node in nodes.values():
            if node["activation"] < 0.2 and node["access_count"] < 2:
                nodes_to_prune.append(node["id"])
        
        for node_id in nodes_to_prune:
            if node_id in nodes:
                del nodes[node_id]
                consolidation_results["pruned"] += 1
        
        # 更新元数据
        self.knowledge["meta"]["last_consolidation"] = datetime.now().isoformat()
        self._save_knowledge()
        
        return consolidation_results
    
    def _calculate_similarity(self, node1: Dict, node2: Dict) -> float:
        """计算两个节点的相似度"""
        # 基于标签的相似度
        tags1 = set(node1.get("tags", []))
        tags2 = set(node2.get("tags", []))
        tag_sim = len(tags1 & tags2) / max(len(tags1 | tags2), 1)
        
        # 基于分类的相似度
        cat_sim = 1.0 if node1.get("category") == node2.get("category") else 0.0
        
        # 基于重要性的相似度
        imp_diff = abs(node1.get("importance", 3) - node2.get("importance", 3))
        imp_sim = max(0, 1 - imp_diff / 5)
        
        return (tag_sim * 0.5 + cat_sim * 0.3 + imp_sim * 0.2)
    
    def distill_knowledge(self, source_ids: List[str], distilled_title: str) -> str:
        """知识蒸馏：从多个源知识提炼核心要点"""
        source_nodes = [self.knowledge["nodes"].get(sid) for sid in source_ids if sid in self.knowledge["nodes"]]
        
        if not source_nodes:
            return ""
        
        # 合并内容
        merged_content = "\n\n".join([n.get("content", "") for n in source_nodes])
        
        # 提取关键词
        all_tags = set()
        for n in source_nodes:
            all_tags.update(n.get("tags", []))
        
        # 创建蒸馏后的知识
        distilled_id = self.add_knowledge(
            title=distilled_title,
            content=f"【知识蒸馏】\n{merged_content[:500]}",
            category=source_nodes[0].get("category", ""),
            importance=max(n.get("importance", 3) for n in source_nodes),
            tags=list(all_tags)[:5]
        )
        
        # 记录事件
        event = EvolutionEvent(
            timestamp=datetime.now().isoformat(),
            event_type="distill",
            node_id=distilled_id,
            description=f"从{len(source_nodes)}个节点蒸馏知识",
            mastery_before=0.5,
            mastery_after=0.6
        )
        self._record_event(event)
        
        return distilled_id
    
    def get_forgotten_knowledge(self) -> List[Dict]:
        """获取被遗忘的知识（需要复习）"""
        forgotten = []
        threshold = FORGET_THRESHOLD
        
        for node in self.knowledge["nodes"].values():
            if node["mastery"] < threshold:
                forgotten.append(node)
        
        forgotten.sort(key=lambda x: x["mastery"])
        return forgotten
    
    def get_evolution_stats(self) -> Dict:
        """获取进化统计"""
        nodes = self.knowledge["nodes"].values()
        
        return {
            "total_nodes": len(nodes),
            "avg_mastery": sum(n.get("mastery", 0) for n in nodes) / max(len(nodes), 1),
            "avg_activation": sum(n.get("activation", 0) for n in nodes) / max(len(nodes), 1),
            "forgotten_count": len(self.get_forgotten_knowledge()),
            "high_mastery_count": sum(1 for n in nodes if n.get("mastery", 0) > 0.8),
            "recent_events": len([e for e in self.events if datetime.fromisoformat(e["timestamp"]) > datetime.now() - timedelta(days=7)]),
            "categories": self._get_category_stats()
        }
    
    def _get_category_stats(self) -> Dict:
        stats = {}
        for node in self.knowledge["nodes"].values():
            cat = node.get("category", "未分类")
            stats[cat] = stats.get(cat, 0) + 1
        return stats
    
    def generate_insights_report(self) -> str:
        """生成洞察报告"""
        stats = self.get_evolution_stats()
        forgotten = self.get_forgotten_knowledge()
        
        lines = ["## 知识进化洞察报告", ""]
        lines.append(f"**总知识节点**: {stats['total_nodes']}")
        lines.append(f"**平均掌握度**: {stats['avg_mastery']:.1%}")
        lines.append(f"**平均激活度**: {stats['avg_activation']:.1%}")
        lines.append(f"**需要复习**: {len(forgotten)}个")
        lines.append("")
        
        if forgotten:
            lines.append("### 遗忘知识 (需要强化)")
            for node in forgotten[:5]:
                lines.append(f"- {node.get('title', '')} (掌握度: {node.get('mastery', 0):.1%})")
            lines.append("")
        
        lines.append("### 分类统计")
        for cat, count in stats.get("categories", {}).items():
            lines.append(f"- {cat}: {count}")
        
        return "\n".join(lines)
