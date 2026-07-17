"""
Knowledge Node System v2 - 原子化知识节点
基于 Zettelkasten 理念：每个知识点独立存储 + 双向链接
"""

import json
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict, field
from enum import Enum

class KnowledgeCategory(Enum):
    """知识分类 - PARA方法"""
    PROJECT = "project"           # 项目
    AREA = "area"               # 领域
    RESOURCE = "resource"        # 资源
    ARCHIVE = "archive"          # 归档
    # 扩展分类
    TRADING_RULE = "trading_rule"    # 交易规则
    LESSON = "lesson"               # 经验教训
    MARKET_ANALYSIS = "market_analysis"  # 市场分析
    PERSONAL_GROWTH = "personal_growth"  # 个人成长

class Importance(Enum):
    """重要度等级"""
    CRITICAL = 5   # 关键（红线、熔断线）
    HIGH = 4       # 高（核心规则）
    MEDIUM = 3     # 中（常规知识）
    LOW = 2        # 低（一般信息）
    TRIVIAL = 1    # 琐碎

@dataclass
class KnowledgeNode:
    """
    原子化知识节点
    
    设计原则（借鉴 Zettelkasten）:
    1. 原子性：每个节点只包含一个知识点
    2. 独立性：节点可独立存在
    3. 连接性：通过链接形成知识网络
    4. 自包含：节点包含足够的上下文
    """
    
    # 基础信息
    id: str = ""                          # 唯一标识
    title: str = ""                       # 标题
    content: str = ""                      # 内容（核心）
    
    # 分类与标签
    category: str = ""                    # 主分类
    tags: List[str] = field(default_factory=list)  # 标签
    keywords: List[str] = field(default_factory=list)  # 关键词
    
    # 重要度与记忆
    importance: int = 3                   # 重要度 1-5
    strength: float = 1.0                 # 记忆强度 0-1
    mastery: float = 0.0                  # 掌握程度 0-1
    
    # 链接系统（原子化的关键）
    links: List[str] = field(default_factory=list)      # 出链 -> 其他节点ID
    backlinks: List[str] = field(default_factory=list)  # 入链 <- 其他节点ID
    
    # 复习系统
    next_review: str = ""                  # 下次复习时间 ISO格式
    review_count: int = 0                 # 复习次数
    last_reviewed: str = ""               # 上次复习时间
    ease_factor: float = 2.5              # SM-2  ease factor
    
    # 时间戳
    created_at: str = ""                   # 创建时间
    updated_at: str = ""                  # 更新时间
    
    # 元数据
    source: str = ""                       # 来源
    author: str = ""                       # 作者
    language: str = "zh"                   # 语言
    version: int = 1                       # 版本
    
    # 关联交易信息
    related_stocks: List[str] = field(default_factory=list)  # 相关股票
    related_trades: List[str] = field(default_factory=list)  # 相关交易
    
    def __post_init__(self):
        """初始化默认值"""
        if not self.id:
            self.id = self._generate_id()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.next_review:
            self.next_review = self.created_at
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        raw = f"{self.title}{self.content}{now}"
        hash_val = hashlib.md5(raw.encode()).hexdigest()[:8]
        return f"kn_{now}_{hash_val}"
    
    def add_link(self, target_id: str):
        """添加出链"""
        if target_id not in self.links:
            self.links.append(target_id)
    
    def remove_link(self, target_id: str):
        """移除出链"""
        if target_id in self.links:
            self.links.remove(target_id)
    
    def add_backlink(self, source_id: str):
        """添加入链"""
        if source_id not in self.backlinks:
            self.backlinks.append(source_id)
    
    def remove_backlink(self, source_id: str):
        """移除入链"""
        if source_id in self.backlinks:
            self.backlinks.remove(source_id)
    
    def add_tag(self, tag: str):
        """添加标签"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeNode":
        """从字典创建"""
        return cls(**data)
    
    def get_summary(self, max_length: int = 100) -> str:
        """获取摘要"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
    
    def needs_review(self) -> bool:
        """是否需要复习"""
        if not self.next_review:
            return True
        try:
            next_time = datetime.fromisoformat(self.next_review)
            return datetime.now() >= next_time
        except:
            return True
    
    def calculate_next_review(self, quality: int = 3):
        """
        SM-2 算法计算下次复习时间
        quality: 0-5 回忆质量
        """
        # 更新 ease factor
        self.ease_factor = max(1.3, self.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        
        # 计算间隔
        if quality < 3:
            # 失败，重置间隔
            interval = 1
        else:
            if self.review_count == 0:
                interval = 1
            elif self.review_count == 1:
                interval = 6
            else:
                # 之前的间隔 * ease factor
                prev_interval = 1
                if len(str(self.last_reviewed)) > 0:
                    prev_interval = 6 * (self.ease_factor ** (self.review_count - 1))
                interval = int(prev_interval * self.ease_factor)
        
        self.review_count += 1
        self.last_reviewed = datetime.now().isoformat()
        self.next_review = (datetime.now() + datetime.timedelta(days=interval)).isoformat()
        
        # 更新记忆强度
        self.strength = min(1.0, self.strength + 0.1 * (quality / 5))
    
    def __repr__(self):
        return f"KnowledgeNode(id={self.id[:20]}..., title={self.title[:30]}...)"


class KnowledgeNodeStore:
    """
    知识节点存储管理器
    负责节点的持久化和索引
    """
    
    def __init__(self, base_path: str = "F:/aidanao/wisdom-brain"):
        self.base_path = Path(base_path)
        self.nodes_dir = self.base_path / "knowledge" / "nodes"
        self.index_file = self.base_path / "knowledge" / "_node_index.json"
        
        # 创建目录
        self.nodes_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载索引
        self._load_index()
    
    def _load_index(self):
        """加载索引"""
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8-sig") as f:
                self.index = json.load(f)
        else:
            self.index = {
                "total": 0,
                "by_category": {},
                "by_tag": {},
                "by_importance": {},
                "nodes": {}  # id -> metadata
            }
    
    def _save_index(self):
        """保存索引"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def save(self, node: KnowledgeNode) -> str:
        """
        保存知识节点
        自动维护索引和双向链接
        """
        # 更新时间戳
        node.updated_at = datetime.now().isoformat()
        
        # 保存节点文件
        node_file = self.nodes_dir / f"{node.id}.json"
        with open(node_file, "w", encoding="utf-8") as f:
            json.dump(node.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 更新索引
        self._update_index(node)
        self._save_index()
        
        # 维护双向链接
        self._update_backlinks(node)
        
        return node.id
    
    def load(self, node_id: str) -> Optional[KnowledgeNode]:
        """加载知识节点"""
        node_file = self.nodes_dir / f"{node_id}.json"
        if not node_file.exists():
            return None
        
        with open(node_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return KnowledgeNode.from_dict(data)
    
    def delete(self, node_id: str) -> bool:
        """删除知识节点"""
        node = self.load(node_id)
        if not node:
            return False
        
        # 移除与其他节点的链接
        for link_id in node.links:
            linked_node = self.load(link_id)
            if linked_node:
                linked_node.remove_backlink(node_id)
                self.save(linked_node)
        
        # 从入链节点移除引用
        for backlink_id in node.backlinks:
            linked_node = self.load(backlink_id)
            if linked_node:
                linked_node.remove_link(node_id)
                self.save(linked_node)
        
        # 删除文件
        node_file = self.nodes_dir / f"{node_id}.json"
        if node_file.exists():
            node_file.unlink()
        
        # 更新索引
        self._remove_from_index(node)
        self._save_index()
        
        return True
    
    def _update_index(self, node: KnowledgeNode):
        """更新索引"""
        self.index["total"] += 1
        self.index["nodes"][node.id] = {
            "title": node.title,
            "category": node.category,
            "tags": node.tags,
            "importance": node.importance,
            "created_at": node.created_at,
            "link_count": len(node.links) + len(node.backlinks)
        }
        
        # 按分类索引
        if node.category not in self.index["by_category"]:
            self.index["by_category"][node.category] = []
        if node.id not in self.index["by_category"][node.category]:
            self.index["by_category"][node.category].append(node.id)
        
        # 按标签索引
        for tag in node.tags:
            if tag not in self.index["by_tag"]:
                self.index["by_tag"][tag] = []
            if node.id not in self.index["by_tag"][tag]:
                self.index["by_tag"][tag].append(node.id)
        
        # 按重要度索引
        imp_key = str(node.importance)
        if imp_key not in self.index["by_importance"]:
            self.index["by_importance"][imp_key] = []
        if node.id not in self.index["by_importance"][imp_key]:
            self.index["by_importance"][imp_key].append(node.id)
    
    def _remove_from_index(self, node: KnowledgeNode):
        """从索引移除"""
        self.index["total"] = max(0, self.index["total"] - 1)
        
        # 从分类移除
        if node.category in self.index["by_category"]:
            if node.id in self.index["by_category"][node.category]:
                self.index["by_category"][node.category].remove(node.id)
        
        # 从标签移除
        for tag in node.tags:
            if tag in self.index["by_tag"]:
                if node.id in self.index["by_tag"][tag]:
                    self.index["by_tag"][tag].remove(node.id)
        
        # 从重要度移除
        imp_key = str(node.importance)
        if imp_key in self.index["by_importance"]:
            if node.id in self.index["by_importance"][imp_key]:
                self.index["by_importance"][imp_key].remove(node.id)
        
        # 从节点列表移除
        if node.id in self.index["nodes"]:
            del self.index["nodes"][node.id]
    
    def _update_backlinks(self, node: KnowledgeNode):
        """更新双向链接"""
        # 遍历出链，添加回指链接
        for link_id in node.links:
            linked_node = self.load(link_id)
            if linked_node:
                if node.id not in linked_node.backlinks:
                    linked_node.add_backlink(node.id)
                    # 保存更新后的节点（不触发递归更新）
                    node_file = self.nodes_dir / f"{link_id}.json"
                    with open(node_file, "w", encoding="utf-8") as f:
                        json.dump(linked_node.to_dict(), f, ensure_ascii=False, indent=2)
    
    def get_all_ids(self) -> List[str]:
        """获取所有节点ID"""
        return list(self.index["nodes"].keys())
    
    def get_by_category(self, category: str) -> List[KnowledgeNode]:
        """按分类获取节点"""
        node_ids = self.index["by_category"].get(category, [])
        return [self.load(nid) for nid in node_ids if self.load(nid)]
    
    def get_by_tag(self, tag: str) -> List[KnowledgeNode]:
        """按标签获取节点"""
        node_ids = self.index["by_tag"].get(tag, [])
        return [self.load(nid) for nid in node_ids if self.load(nid)]
    
    def get_by_importance(self, min_importance: int) -> List[KnowledgeNode]:
        """按重要度获取节点"""
        result = []
        for imp in range(min_importance, 6):
            node_ids = self.index["by_importance"].get(str(imp), [])
            for nid in node_ids:
                node = self.load(nid)
                if node:
                    result.append(node)
        return result
    
    def get_needing_review(self) -> List[KnowledgeNode]:
        """获取需要复习的节点"""
        nodes = []
        for node_id in self.get_all_ids():
            node = self.load(node_id)
            if node and node.needs_review():
                nodes.append(node)
        return nodes
    
    def search(self, query: str) -> List[KnowledgeNode]:
        """搜索节点"""
        query_lower = query.lower()
        results = []
        
        for node_id in self.get_all_ids():
            node = self.load(node_id)
            if not node:
                continue
            
            # 搜索标题、内容、标签、关键词
            if (query_lower in node.title.lower() or
                query_lower in node.content.lower() or
                any(query_lower in tag.lower() for tag in node.tags) or
                any(query_lower in kw.lower() for kw in node.keywords)):
                results.append(node)
        
        return results
    
    def get_linked_nodes(self, node_id: str, depth: int = 1) -> Dict[str, List[KnowledgeNode]]:
        """
        获取链接的节点
        返回: {"outgoing": [...], "incoming": [...], "level_2": [...]}
        """
        node = self.load(node_id)
        if not node:
            return {}
        
        result = {
            "outgoing": [],  # 直接出链
            "incoming": [],   # 直接入链
            "level_2": []    # 二级链接
        }
        
        # 出链
        for link_id in node.links:
            linked = self.load(link_id)
            if linked:
                result["outgoing"].append(linked)
        
        # 入链
        for link_id in node.backlinks:
            linked = self.load(link_id)
            if linked:
                result["incoming"].append(linked)
        
        # 二级链接
        if depth >= 2:
            seen_ids = {node_id}
            for linked in result["outgoing"] + result["incoming"]:
                seen_ids.add(linked.id)
            
            for linked in result["outgoing"] + result["incoming"]:
                for l2_id in linked.links + linked.backlinks:
                    if l2_id not in seen_ids:
                        l2_node = self.load(l2_id)
                        if l2_node:
                            result["level_2"].append(l2_node)
                            seen_ids.add(l2_id)
        
        return result
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total": self.index["total"],
            "by_category": {k: len(v) for k, v in self.index["by_category"].items()},
            "by_importance": {k: len(v) for k, v in self.index["by_importance"].items()},
            "needing_review": len(self.get_needing_review())
        }


# 便捷函数
def create_node(
    title: str,
    content: str,
    category: str = "",
    tags: List[str] = None,
    importance: int = 3,
    links: List[str] = None
) -> KnowledgeNode:
    """创建知识节点的便捷函数"""
    node = KnowledgeNode(
        title=title,
        content=content,
        category=category,
        tags=tags or [],
        importance=importance
    )
    if links:
        for link_id in links:
            node.add_link(link_id)
    return node


# 测试
if __name__ == "__main__":
    store = KnowledgeNodeStore()
    
    # 创建示例节点
    node1 = create_node(
        title="交易红线：追高必亏",
        content="在大盘下跌趋势时追高买入是导致亏损的主要原因。统计数据表明，追高买入的成功率低于40%。",
        category="trading_rule",
        tags=["追高", "亏损", "红线"],
        importance=5
    )
    
    node2 = create_node(
        title="量价齐升是健康信号",
        content="成交量放大配合价格上涨，表明市场参与度高，趋势健康。",
        category="market_analysis",
        tags=["量价", "健康信号"],
        importance=4
    )
    
    # 链接节点
    node1.add_link(store.save(node2))
    
    # 保存主节点
    node1_id = store.save(node1)
    print(f"Created node: {node1_id}")
    
    # 测试加载
    loaded = store.load(node1_id)
    print(f"Loaded: {loaded.title}")
    print(f"Links: {loaded.links}")
    
    # 测试搜索
    results = store.search("交易")
    print(f"Search results: {len(results)}")
    
    # 统计
    print(f"Stats: {store.get_stats()}")