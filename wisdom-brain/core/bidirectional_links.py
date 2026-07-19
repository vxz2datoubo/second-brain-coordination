"""
Bidirectional Links System - 双向链接系统
基于 Obsidian/Roam Research 的双向链接理念
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict

class BidirectionalLinks:
    """
    双向链接管理器
    
    功能:
    1. 自动维护 [[wikilink]] 格式的链接
    2. 自动追踪 backlinks
    3. 支持嵌入式内容 (transclusions)
    4. 链接图谱可视化数据
    """
    
    def __init__(self, base_path: str = "F:/aidanao/wisdom-brain"):
        self.base_path = Path(base_path)
        self.links_dir = self.base_path / "knowledge" / "links"
        self.links_dir.mkdir(parents=True, exist_ok=True)
        
        # 链接索引文件
        self.index_file = self.links_dir / "_links_index.json"
        
        # 加载索引
        self._load_index()
    
    def _load_index(self):
        """加载链接索引"""
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8-sig") as f:
                self.index = json.load(f)
        else:
            self._init_index()
    
    def _init_index(self):
        """初始化索引"""
        self.index = {
            "forward_links": {},  # node_id -> [target_ids]
            "backlinks": {},     # node_id -> [source_ids]
            "link_count": 0,
            "orphans": [],       # 没有入链也没有出链的节点
            "hubs": [],          # 高度链接的节点（枢纽）
            "authorities": []    # 被很多节点链接的节点
        }
    
    def _save_index(self):
        """保存索引"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def parse_wikilinks(self, content: str) -> List[str]:
        """
        解析 wikilink 格式的链接
        支持: [[node_id]], [[node_id|alias]], [[#heading]]
        """
        import re
        # 匹配 [[...]]
        pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
        matches = re.findall(pattern, content)
        
        # 过滤标签和分类
        node_ids = []
        for match in matches:
            # 跳过 heading
            if match.startswith("#"):
                continue
            node_ids.append(match)
        
        return node_ids
    
    def extract_links_from_content(self, node_id: str, content: str):
        """
        从内容中提取链接并更新索引
        """
        # 解析链接
        linked_ids = self.parse_wikilinks(content)
        
        # 获取旧的链接
        old_links = set(self.index["forward_links"].get(node_id, []))
        new_links = set(linked_ids)
        
        # 计算差异
        added_links = new_links - old_links
        removed_links = old_links - new_links
        
        # 更新正向链接
        self.index["forward_links"][node_id] = list(new_links)
        
        # 更新反向链接
        # 1. 移除旧的回指
        for old_id in removed_links:
            if old_id in self.index["backlinks"]:
                if node_id in self.index["backlinks"][old_id]:
                    self.index["backlinks"][old_id].remove(node_id)
        
        # 2. 添加新的回指
        for new_id in added_links:
            if new_id not in self.index["backlinks"]:
                self.index["backlinks"][new_id] = []
            if node_id not in self.index["backlinks"][new_id]:
                self.index["backlinks"][new_id].append(node_id)
        
        # 清理空的回指
        self.index["backlinks"] = {k: v for k, v in self.index["backlinks"].items() if v}
        
        # 更新链接计数
        self.index["link_count"] = sum(len(links) for links in self.index["forward_links"].values())
        
        # 更新枢纽和权威节点
        self._update_hubs_and_authorities()
        
        # 保存索引
        self._save_index()
        
        return {"added": list(added_links), "removed": list(removed_links)}
    
    def get_backlinks(self, node_id: str) -> List[Dict]:
        """
        获取指向某节点的回指链接
        返回: [{"source_id": ..., "context": ...}]
        """
        source_ids = self.index["backlinks"].get(node_id, [])
        
        # 需要从节点内容中提取上下文
        # 这里假设节点内容已经保存，我们重新解析
        # 实际使用时可以从 KnowledgeNodeStore 获取
        
        return [{"source_id": sid} for sid in source_ids]
    
    def get_forward_links(self, node_id: str) -> List[str]:
        """获取节点指向的链接"""
        return self.index["forward_links"].get(node_id, [])
    
    def _update_hubs_and_authorities(self):
        """更新枢纽节点和权威节点"""
        # 枢纽：有很多出链的节点
        forward_counts = [(node_id, len(links)) for node_id, links in self.index["forward_links"].items()]
        forward_counts.sort(key=lambda x: x[1], reverse=True)
        self.index["hubs"] = [node_id for node_id, count in forward_counts[:10] if count > 0]
        
        # 权威：有很多入链的节点
        backward_counts = [(node_id, len(links)) for node_id, links in self.index["backlinks"].items()]
        backward_counts.sort(key=lambda x: x[1], reverse=True)
        self.index["authorities"] = [node_id for node_id, count in backward_counts[:10] if count > 0]
    
    def get_link_graph(self, node_id: str = None, depth: int = 2) -> Dict:
        """
        获取链接图谱数据
        用于可视化
        """
        if node_id:
            return self._get_subgraph(node_id, depth)
        else:
            return self._get_full_graph()
    
    def _get_subgraph(self, center_id: str, depth: int) -> Dict:
        """获取以某节点为中心的子图"""
        nodes = set()
        edges = []
        
        def traverse(current_id: str, current_depth: int):
            if current_depth > depth or current_id in nodes:
                return
            
            nodes.add(current_id)
            
            # 出链
            for target_id in self.index["forward_links"].get(current_id, []):
                edges.append({"source": current_id, "target": target_id, "type": "forward"})
                traverse(target_id, current_depth + 1)
            
            # 入链
            for source_id in self.index["backlinks"].get(current_id, []):
                edges.append({"source": source_id, "target": current_id, "type": "backward"})
                nodes.add(source_id)
        
        traverse(center_id, 0)
        
        return {
            "nodes": [{"id": nid} for nid in nodes],
            "edges": edges,
            "center": center_id
        }
    
    def _get_full_graph(self) -> Dict:
        """获取完整图谱"""
        all_nodes = set(self.index["forward_links"].keys())
        all_nodes.update(self.index["backlinks"].keys())
        
        edges = []
        for source, targets in self.index["forward_links"].items():
            for target in targets:
                edges.append({"source": source, "target": target})
        
        return {
            "nodes": [{"id": nid} for nid in all_nodes],
            "edges": edges,
            "stats": {
                "total_nodes": len(all_nodes),
                "total_edges": len(edges),
                "hubs": self.index["hubs"][:5],
                "authorities": self.index["authorities"][:5]
            }
        }
    
    def find_orphans(self) -> List[str]:
        """找出孤立节点（没有链接的）"""
        all_nodes = set(self.index["forward_links"].keys())
        all_nodes.update(self.index["backlinks"].keys())
        
        orphans = []
        for node_id in all_nodes:
            has_forward = len(self.index["forward_links"].get(node_id, [])) > 0
            has_backward = len(self.index["backlinks"].get(node_id, [])) > 0
            
            if not has_forward and not has_backward:
                orphans.append(node_id)
        
        return orphans
    
    def find_bridges(self) -> List[Dict]:
        """
        找出桥接节点（连接不同聚类的节点）
        """
        # 简单的启发式方法：高度数节点连接不同区域
        bridges = []
        
        for node_id in self.index["hubs"]:
            forward = set(self.index["forward_links"].get(node_id, []))
            backward = set(self.index["backlinks"].get(node_id, []))
            all_links = forward | backward
            
            # 检查链接到不同分类
            bridges.append({
                "node_id": node_id,
                "link_count": len(all_links),
                "forward_count": len(forward),
                "backward_count": len(backward)
            })
        
        return bridges
    
    def resolve_wikilinks(self, content: str, nodes_store=None) -> str:
        """
        将 wikilink 解析为可显示的 HTML
        
        [[node_id]] -> <span class="wikilink">标题</span>
        [[node_id|display]] -> <span class="wikilink">display</span>
        """
        import re
        
        def replace_link(match):
            link_content = match.group(1)
            parts = link_content.split("|")
            node_id = parts[0]
            display_text = parts[1] if len(parts) > 1 else None
            
            # 尝试获取节点标题
            if nodes_store:
                node = nodes_store.load(node_id)
                if node:
                    display_text = display_text or node.title
                    return f'<a class="wikilink" href="#{node_id}">{display_text}</a>'
            
            # 无法找到节点
            return f'<span class="wikilink broken">{display_text or node_id}</span>'
        
        pattern = r'\[\[([^\]]+)\]\]'
        return re.sub(pattern, replace_link, content)
    
    def get_unlinked_references(self, content: str, potential_links: List[str]) -> List[str]:
        """
        找出内容中可能存在但未链接的引用
        """
        found = []
        content_lower = content.lower()
        
        for node_id in potential_links:
            # 简单匹配：检查 node_id 是否在内容中
            if node_id.lower() in content_lower:
                # 进一步检查是否是真正的引用
                if node_id not in self.parse_wikilinks(content):
                    found.append(node_id)
        
        return found
    
    def get_link_suggestions(self, current_node_id: str, existing_links: List[str], 
                            all_nodes: List[Dict], limit: int = 5) -> List[Dict]:
        """
        基于当前内容推荐可能的链接
        """
        # 获取当前节点的分类
        current_tags = set()
        
        # 基于共同标签推荐
        suggestions = []
        
        for node in all_nodes:
            if node["id"] == current_node_id:
                continue
            if node["id"] in existing_links:
                continue
            
            # 计算相似度
            node_tags = set(node.get("tags", []))
            common_tags = len(current_tags & node_tags)
            
            if common_tags > 0:
                suggestions.append({
                    "node_id": node["id"],
                    "title": node.get("title", ""),
                    "common_tags": common_tags,
                    "score": common_tags
                })
        
        # 排序并返回 top N
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:limit]
    
    def get_stats(self) -> Dict:
        """获取链接统计"""
        return {
            "total_forward_links": len(self.index["forward_links"]),
            "total_backlinks": len(self.index["backlinks"]),
            "total_link_count": self.index["link_count"],
            "orphan_count": len(self.find_orphans()),
            "hub_count": len(self.index["hubs"]),
            "authority_count": len(self.index["authorities"])
        }


class LinkResolver:
    """
    链接解析器
    处理链接的解析、验证和转换
    """
    
    @staticmethod
    def parse_link_format(link: str) -> Dict:
        """
        解析链接格式
        支持:
        - [[node_id]]
        - [[node_id|display text]]
        - [[node_id#heading]]
        - [[node_id#heading|display]]
        """
        import re
        
        result = {
            "node_id": None,
            "heading": None,
            "display_text": None,
            "is_external": False
        }
        
        # 外部链接
        if link.startswith("http://") or link.startswith("https://"):
            result["is_external"] = True
            result["display_text"] = link
            return result
        
        # Wikilink 格式
        wikilink_match = re.match(r'\[\[([^\]]+)\]\]', link)
        if wikilink_match:
            content = wikilink_match.group(1)
            
            # 分割节点ID和heading/display
            parts = content.split("|")
            main_part = parts[0]
            result["display_text"] = parts[1] if len(parts) > 1 else None
            
            # 分割节点ID和heading
            heading_parts = main_part.split("#")
            result["node_id"] = heading_parts[0]
            result["heading"] = heading_parts[1] if len(heading_parts) > 1 else None
        
        return result
    
    @staticmethod
    def validate_node_id(node_id: str) -> bool:
        """验证节点ID格式"""
        import re
        # 格式: kn_YYYYMMDD_HHMMSS_XXXXXXXX
        pattern = r'^kn_\d{14}_[a-f0-9]{8}$'
        return bool(re.match(pattern, node_id))
    
    @staticmethod
    def generate_wikilink(node_id: str, display_text: str = None) -> str:
        """生成 wikilink"""
        if display_text:
            return f"[[{node_id}|{display_text}]]"
        return f"[[{node_id}]]"


# 测试
if __name__ == "__main__":
    bl = BidirectionalLinks()
    
    # 测试链接提取
    content = """
    这是一条关于 [[kn_20260706_abc123|交易规则]] 的笔记。
    还有 [[kn_20260706_def456]] 没有别名的链接。
    """
    
    links = bl.parse_wikilinks(content)
    print(f"Extracted links: {links}")
    
    # 测试链接解析
    resolver = LinkResolver()
    parsed = resolver.parse_link_format("[[kn_20260706_abc123|交易规则]]")
    print(f"Parsed link: {parsed}")
    
    # 统计
    print(f"Link stats: {bl.get_stats()}")