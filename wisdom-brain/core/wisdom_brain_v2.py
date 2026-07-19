"""
Wisdom Brain v2 - 智慧大脑核心系统
整合: 原子化知识节点 + 双向链接 + 间隔复习
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.knowledge_node import KnowledgeNode, KnowledgeNodeStore, KnowledgeCategory, Importance
from core.bidirectional_links import BidirectionalLinks, LinkResolver
from core.spaced_repetition import SpacedRepetition

class WisdomBrain:
    """
    智慧大脑核心类
    
    整合三大系统:
    1. KnowledgeNode - 原子化知识节点
    2. BidirectionalLinks - 双向链接
    3. SpacedRepetition - 间隔复习
    """
    
    def __init__(self, base_path: str = "F:/aidanao/wisdom-brain"):
        self.base_path = Path(base_path)
        
        # 初始化子系统
        self.nodes = KnowledgeNodeStore(base_path)
        self.links = BidirectionalLinks(base_path)
        self.srs = SpacedRepetition(base_path)
        
        # 链接解析器
        self.resolver = LinkResolver()
    
    # ========== 节点操作 ==========
    
    def create_node(
        self,
        title: str,
        content: str,
        category: str = "",
        tags: List[str] = None,
        importance: int = 3,
        auto_link: bool = True
    ) -> Dict:
        """
        创建知识节点
        """
        # 创建节点
        node = KnowledgeNode(
            title=title,
            content=content,
            category=category,
            tags=tags or [],
            importance=importance
        )
        
        # 自动提取链接
        if auto_link:
            linked_ids = self.links.parse_wikilinks(content)
            for link_id in linked_ids:
                node.add_link(link_id)
        
        # 保存节点
        node_id = self.nodes.save(node)
        
        # 更新链接索引
        if auto_link:
            self.links.extract_links_from_content(node_id, content)
        
        # 加入复习计划
        self._schedule_review(node_id)
        
        return {
            "success": True,
            "node_id": node_id,
            "title": title
        }
    
    def update_node(self, node_id: str, **kwargs) -> Dict:
        """
        更新知识节点
        """
        node = self.nodes.load(node_id)
        if not node:
            return {"success": False, "error": "Node not found"}
        
        old_content = node.content
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)
        
        # 如果内容变化，重新提取链接
        if "content" in kwargs and old_content != node.content:
            self.links.extract_links_from_content(node_id, node.content)
        
        # 保存
        self.nodes.save(node)
        
        return {
            "success": True,
            "node_id": node_id
        }
    
    def delete_node(self, node_id: str) -> Dict:
        """
        删除知识节点
        """
        success = self.nodes.delete(node_id)
        
        if success:
            return {"success": True}
        else:
            return {"success": False, "error": "Node not found"}
    
    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """获取节点"""
        return self.nodes.load(node_id)
    
    # ========== 链接操作 ==========
    
    def add_link(self, source_id: str, target_id: str) -> Dict:
        """添加链接"""
        source = self.nodes.load(source_id)
        if not source:
            return {"success": False, "error": "Source node not found"}
        
        target = self.nodes.load(target_id)
        if not target:
            return {"success": False, "error": "Target node not found"}
        
        source.add_link(target_id)
        self.nodes.save(source)
        
        # 更新链接索引
        self.links.extract_links_from_content(source_id, source.content)
        
        return {"success": True}
    
    def get_node_links(self, node_id: str, depth: int = 1) -> Dict:
        """获取节点的链接"""
        return self.nodes.get_linked_nodes(node_id, depth)
    
    def search_links(self, query: str) -> List[Dict]:
        """搜索链接"""
        # 搜索包含 query 的链接
        results = []
        
        for node_id in self.nodes.get_all_ids():
            node = self.nodes.load(node_id)
            if not node:
                continue
            
            # 检查链接目标
            for link_id in node.links:
                linked = self.nodes.load(link_id)
                if linked and query.lower() in linked.title.lower():
                    results.append({
                        "source_id": node_id,
                        "source_title": node.title,
                        "target_id": link_id,
                        "target_title": linked.title
                    })
        
        return results
    
    # ========== 复习操作 ==========
    
    def review_node(self, node_id: str, quality: int) -> Dict:
        """
        复习节点
        quality: 0-5 回忆质量
        """
        node = self.nodes.load(node_id)
        if not node:
            return {"success": False, "error": "Node not found"}
        
        # 记录复习
        result = self.srs.record_review(
            node_id=node_id,
            quality=quality,
            current_ef=node.ease_factor,
            current_interval=self._get_current_interval(node),
            review_count=node.review_count
        )
        
        # 更新节点
        node.ease_factor = result["ease_factor"]
        node.next_review = result["next_review"]
        node.review_count = result["repetitions"]
        node.strength = min(1.0, node.strength + 0.05 * quality)
        
        self.nodes.save(node)
        
        return {
            "success": True,
            "next_review": result["next_review"],
            "new_interval": result["interval"],
            "new_ef": result["ease_factor"]
        }
    
    def get_due_reviews(self) -> List[Dict]:
        """获取需要复习的节点"""
        due = self.srs.get_due_nodes()
        
        results = []
        for node_id in due["overdue"] + due["due_today"]:
            node = self.nodes.load(node_id)
            if node:
                results.append({
                    "node_id": node_id,
                    "title": node.title,
                    "is_overdue": node_id in due["overdue"],
                    "next_review": node.next_review,
                    "importance": node.importance
                })
        
        # 按重要度和过期状态排序
        results.sort(key=lambda x: (not x["is_overdue"], -x["importance"]))
        
        return results
    
    def _get_current_interval(self, node: KnowledgeNode) -> int:
        """获取当前复习间隔"""
        try:
            if node.last_reviewed:
                last = datetime.fromisoformat(node.last_reviewed)
                if node.next_review:
                    next_time = datetime.fromisoformat(node.next_review)
                    return max(1, (next_time - last).days)
        except:
            pass
        return 1
    
    def _schedule_review(self, node_id: str):
        """将节点加入复习计划"""
        # 立即安排第一次复习
        self.srs.record_review(
            node_id=node_id,
            quality=3,  # 默认质量
            current_ef=2.5,
            current_interval=1,
            review_count=0
        )
    
    # ========== 搜索与检索 ==========
    
    def search(self, query: str, filters: Dict = None) -> List[Dict]:
        """
        搜索知识库
        """
        results = []
        
        for node_id in self.nodes.get_all_ids():
            node = self.nodes.load(node_id)
            if not node:
                continue
            
            # 应用过滤器
            if filters:
                if "category" in filters and node.category != filters["category"]:
                    continue
                if "min_importance" in filters and node.importance < filters["min_importance"]:
                    continue
                if "tags" in filters and not any(tag in node.tags for tag in filters["tags"]):
                    continue
            
            # 搜索
            query_lower = query.lower()
            if (query_lower in node.title.lower() or
                query_lower in node.content.lower() or
                any(query_lower in tag.lower() for tag in node.tags)):
                
                results.append({
                    "node_id": node_id,
                    "title": node.title,
                    "content": node.content[:200] + "..." if len(node.content) > 200 else node.content,
                    "category": node.category,
                    "tags": node.tags,
                    "importance": node.importance,
                    "needs_review": node.needs_review(),
                    "link_count": len(node.links) + len(node.backlinks)
                })
        
        # 排序: 重要度 > 链接数 > 相关性
        results.sort(key=lambda x: (-x["importance"], -x["link_count"]))
        
        return results
    
    # ========== 知识图谱 ==========
    
    def get_knowledge_graph(self, node_id: str = None, depth: int = 2) -> Dict:
        """获取知识图谱"""
        return self.links.get_link_graph(node_id, depth)
    
    def get_hubs_and_authorities(self) -> Dict:
        """获取枢纽节点和权威节点"""
        stats = self.links.get_stats()
        
        # 获取节点详情
        hubs = []
        for node_id in stats.get("hubs", [])[:5]:
            node = self.nodes.load(node_id)
            if node:
                hubs.append({
                    "id": node_id,
                    "title": node.title,
                    "link_count": len(node.links) + len(node.backlinks)
                })
        
        authorities = []
        for node_id in stats.get("authorities", [])[:5]:
            node = self.nodes.load(node_id)
            if node:
                authorities.append({
                    "id": node_id,
                    "title": node.title,
                    "backlink_count": len(node.backlinks)
                })
        
        return {"hubs": hubs, "authorities": authorities}
    
    # ========== 统计与报告 ==========
    
    def get_stats(self) -> Dict:
        """获取系统统计"""
        return {
            "nodes": self.nodes.get_stats(),
            "links": self.links.get_stats(),
            "reviews": self.srs.get_stats()
        }
    
    def get_dashboard(self) -> Dict:
        """获取仪表盘数据"""
        stats = self.get_stats()
        due_reviews = self.get_due_reviews()
        
        # 按分类统计
        category_stats = {}
        for node_id in self.nodes.get_all_ids():
            node = self.nodes.load(node_id)
            if node:
                cat = node.category or "uncategorized"
                if cat not in category_stats:
                    category_stats[cat] = {"count": 0, "total_importance": 0}
                category_stats[cat]["count"] += 1
                category_stats[cat]["total_importance"] += node.importance
        
        return {
            "total_nodes": stats["nodes"]["total"],
            "total_links": stats["links"]["total_link_count"],
            "due_reviews": len(due_reviews),
            "overdue_reviews": len([r for r in due_reviews if r["is_overdue"]]),
            "review_stats": stats["reviews"],
            "category_stats": category_stats,
            "hubs_authorities": self.get_hubs_and_authorities()
        }
    
    # ========== 辅助功能 ==========
    
    def resolve_wikilinks(self, content: str) -> str:
        """解析内容中的 wikilinks"""
        return self.links.resolve_wikilinks(content, self.nodes)
    
    def suggest_links(self, node_id: str) -> List[Dict]:
        """建议可能的链接"""
        node = self.nodes.load(node_id)
        if not node:
            return []
        
        # 获取所有节点
        all_nodes = []
        for nid in self.nodes.get_all_ids():
            n = self.nodes.load(nid)
            if n:
                all_nodes.append({
                    "id": nid,
                    "title": n.title,
                    "tags": n.tags,
                    "category": n.category
                })
        
        return self.links.get_link_suggestions(
            node_id=node_id,
            existing_links=node.links,
            all_nodes=all_nodes,
            limit=5
        )
    
    def find_orphans(self) -> List[str]:
        """找出孤立节点"""
        return self.links.find_orphans()
    
    def get_review_history(self, node_id: str) -> Dict:
        """获取复习历史"""
        return self.srs.get_review_stats(node_id)
    
    def predict_forgetting(self, node_id: str) -> Dict:
        """预测遗忘曲线"""
        return self.srs.predict_forgetting(node_id)


# 便捷函数
def quick_add(title: str, content: str, tags: List[str] = None) -> str:
    """快速添加知识"""
    brain = WisdomBrain()
    result = brain.create_node(title, content, tags=tags)
    return result["node_id"]


# 测试
if __name__ == "__main__":
    wb = WisdomBrain()
    
    print("=== Wisdom Brain v2 Test ===")
    print(f"Stats: {wb.get_stats()}")
    
    # 测试创建节点
    print("\n--- Create Nodes ---")
    r1 = wb.create_node(
        title="交易红线：追高必亏",
        content="在大盘下跌趋势时追高买入是导致亏损的主要原因。统计数据表明，追高买入的成功率低于40%。",
        category="trading_rule",
        tags=["追高", "亏损", "红线"],
        importance=5
    )
    print(f"Created: {r1['node_id']}")
    
    r2 = wb.create_node(
        title="量价齐升是健康信号",
        content="成交量放大配合价格上涨，表明市场参与度高，趋势健康。见 [[量价背离]]。",
        category="market_analysis",
        tags=["量价", "健康信号"],
        importance=4
    )
    print(f"Created: {r2['node_id']}")
    
    # 添加链接
    wb.add_link(r1["node_id"], r2["node_id"])
    
    # 测试搜索
    print("\n--- Search ---")
    results = wb.search("交易")
    print(f"Found {len(results)} results")
    
    # 测试复习
    print("\n--- Reviews ---")
    due = wb.get_due_reviews()
    print(f"Due: {len(due)}")
    
    # 测试仪表盘
    print("\n--- Dashboard ---")
    dashboard = wb.get_dashboard()
    print(f"Total nodes: {dashboard['total_nodes']}")
    print(f"Due reviews: {dashboard['due_reviews']}")
    
    print("\n=== Test Complete ===")