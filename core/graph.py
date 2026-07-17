"""
graph.py - JSON-based 知识图谱引擎
轻量级图谱操作，零外部依赖。纯 Python stdlib 实现。

功能:
- 节点 CRUD (添加/查询/更新/删除)
- 边管理 (添加/查询/删除)
- BFS 子图遍历 (多深度)
- 最短路径查找
- 自动关联 (标签/标题重叠)
- 分类/标签过滤
- 图谱统计与持久化
"""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional


# ---- 分词工具 (duplicated from server.py for module independence) ----
def _tokenize(text: str) -> set[str]:
    """Bigram 中文分词"""
    import re
    tokens = set()
    for match in re.finditer(r'[a-zA-Z0-9]+', text):
        tokens.add(match.group().lower())
    chinese = "".join(c for c in text if '\u4e00' <= c <= '\u9fff')
    for i in range(len(chinese) - 1):
        tokens.add(chinese[i:i + 2])
    for c in chinese:
        tokens.add(c)
    return tokens


class KnowledgeGraph:
    """JSON 知识图谱管理器

    数据存储结构 (knowledge-graph.json):
    {
      "nodes": { "id": { ... } },
      "edges": { "id": { source_id, target_id, relation, strength } },
      "meta": { total_nodes, total_edges, last_updated }
    }
    """

    RELATION_TYPES = [
        "related_to", "prerequisite_of", "derived_from",
        "contradicts", "supports", "example_of"
    ]

    def __init__(self, data_dir: Path, filename: str = "knowledge-graph.json"):
        self.path = data_dir / filename
        self.data = self._load()

    # ========== 持久化 ==========
    def _load(self) -> dict:
        """从 JSON 加载图谱"""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 确保结构完整
            data.setdefault("nodes", {})
            data.setdefault("edges", {})
            data.setdefault("meta", {"total_nodes": 0, "total_edges": 0, "last_updated": ""})
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "nodes": {},
                "edges": {},
                "meta": {"total_nodes": 0, "total_edges": 0, "last_updated": ""}
            }

    def _save(self):
        """持久化到 JSON"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def reload(self):
        """重新从磁盘加载"""
        self.data = self._load()

    def commit(self):
        """保存 + 更新 meta"""
        self.data["meta"]["total_nodes"] = len(self.data["nodes"])
        self.data["meta"]["total_edges"] = len(self.data["edges"])
        self.data["meta"]["last_updated"] = datetime.now().isoformat()
        self._save()

    # ========== 节点操作 ==========
    def add_node(self, node: dict) -> str:
        """添加知识节点，返回 node_id。若 node 无 id 则自动生成。"""
        if "id" not in node:
            node["id"] = str(uuid.uuid4())[:8]
        node_id = node["id"]

        # 填充默认字段
        node.setdefault("type", "knowledge")
        node.setdefault("title", "")
        node.setdefault("content", "")
        node.setdefault("summary", "")
        node.setdefault("source", "manual")
        node.setdefault("source_path", "")
        node.setdefault("tags", [])
        node.setdefault("category", "life")
        node.setdefault("importance", 1)
        node.setdefault("created_at", datetime.now().isoformat())
        node.setdefault("updated_at", datetime.now().isoformat())
        node.setdefault("access_count", 0)
        node.setdefault("feedback_score", 0.0)
        node.setdefault("metadata", {})

        self.data["nodes"][node_id] = node
        return node_id

    def get_node(self, node_id: str) -> Optional[dict]:
        """获取单个节点"""
        return self.data["nodes"].get(node_id)

    def update_node(self, node_id: str, updates: dict) -> bool:
        """更新节点字段。返回 True 表示成功。"""
        node = self.data["nodes"].get(node_id)
        if not node:
            return False
        # 不允许更改 id
        updates.pop("id", None)
        node.update(updates)
        node["updated_at"] = datetime.now().isoformat()
        return True

    def remove_node(self, node_id: str) -> bool:
        """删除节点及其关联的所有边"""
        if node_id not in self.data["nodes"]:
            return False
        del self.data["nodes"][node_id]
        # 清理关联边
        self.data["edges"] = {
            eid: e for eid, e in self.data["edges"].items()
            if e["source_id"] != node_id and e["target_id"] != node_id
        }
        return True

    def search_nodes(self, query: str, field: str = "title") -> list[dict]:
        """按字段搜索节点 (简单子串匹配)"""
        results = []
        q = query.lower()
        for node in self.data["nodes"].values():
            val = str(node.get(field, "")).lower()
            if q in val:
                results.append(node)
        return results

    def list_nodes(
        self, category: str = None, tag: str = None,
        source: str = None, sort_by: str = "created_at",
        reverse: bool = True, limit: int = 100
    ) -> list[dict]:
        """列出节点，支持过滤和排序"""
        nodes = list(self.data["nodes"].values())

        if category:
            nodes = [n for n in nodes if n.get("category") == category]
        if tag:
            nodes = [n for n in nodes if tag in n.get("tags", [])]
        if source:
            nodes = [n for n in nodes if n.get("source") == source]

        nodes.sort(key=lambda n: n.get(sort_by, ""), reverse=reverse)
        return nodes[:limit]

    def touch_node(self, node_id: str):
        """增加节点访问计数"""
        node = self.data["nodes"].get(node_id)
        if node:
            node["access_count"] = node.get("access_count", 0) + 1

    # ========== 边操作 ==========
    def add_edge(
        self, source_id: str, target_id: str,
        relation: str = "related_to", strength: float = 0.5
    ) -> Optional[str]:
        """添加边。返回 edge_id。若节点不存在返回 None。"""
        if source_id not in self.data["nodes"] or target_id not in self.data["nodes"]:
            return None
        if source_id == target_id:
            return None

        # 去重检查
        for eid, e in self.data["edges"].items():
            if (e["source_id"] == source_id and e["target_id"] == target_id) or \
               (e["source_id"] == target_id and e["target_id"] == source_id):
                return eid  # 已存在，返回现有边ID

        edge_id = str(uuid.uuid4())[:8]
        self.data["edges"][edge_id] = {
            "id": edge_id,
            "source_id": source_id,
            "target_id": target_id,
            "relation": relation if relation in self.RELATION_TYPES else "related_to",
            "strength": max(0.0, min(1.0, strength)),
            "created_at": datetime.now().isoformat()
        }
        return edge_id

    def get_edge(self, edge_id: str) -> Optional[dict]:
        return self.data["edges"].get(edge_id)

    def remove_edge(self, edge_id: str) -> bool:
        if edge_id in self.data["edges"]:
            del self.data["edges"][edge_id]
            return True
        return False

    def get_edges_between(self, node_a: str, node_b: str) -> list[dict]:
        """获取两节点间的所有边"""
        results = []
        for e in self.data["edges"].values():
            if (e["source_id"] == node_a and e["target_id"] == node_b) or \
               (e["source_id"] == node_b and e["target_id"] == node_a):
                results.append(e)
        return results

    # ========== 图遍历 ==========
    def get_neighbors(self, node_id: str, depth: int = 1) -> dict:
        """BFS 获取节点的邻居子图 (包含源节点)"""
        if node_id not in self.data["nodes"]:
            return {"nodes": {}, "edges": {}, "meta": {"error": "node not found"}}

        visited_nodes = {node_id}
        visited_edges = set()
        frontier = {node_id}

        for _ in range(depth):
            next_frontier = set()
            for nid in frontier:
                for eid, edge in self.data["edges"].items():
                    src, tgt = edge["source_id"], edge["target_id"]
                    if src == nid and tgt not in visited_nodes:
                        visited_nodes.add(tgt)
                        visited_edges.add(eid)
                        next_frontier.add(tgt)
                    elif tgt == nid and src not in visited_nodes:
                        visited_nodes.add(src)
                        visited_edges.add(eid)
                        next_frontier.add(src)
            frontier = next_frontier
            if not frontier:
                break

        return {
            "nodes": {nid: self.data["nodes"][nid] for nid in visited_nodes},
            "edges": {eid: self.data["edges"][eid] for eid in visited_edges},
            "meta": {"total_nodes": len(visited_nodes), "total_edges": len(visited_edges)}
        }

    def find_path(self, source_id: str, target_id: str) -> list[str]:
        """BFS 查找两节点间最短路径。返回节点ID列表。"""
        if source_id not in self.data["nodes"] or target_id not in self.data["nodes"]:
            return []

        visited = {source_id}
        parent = {source_id: None}
        queue = [source_id]

        while queue:
            current = queue.pop(0)
            if current == target_id:
                # 回溯路径
                path = []
                while current is not None:
                    path.append(current)
                    current = parent[current]
                path.reverse()
                return path

            for edge in self.data["edges"].values():
                src, tgt = edge["source_id"], edge["target_id"]
                neighbor = None
                if src == current and tgt not in visited:
                    neighbor = tgt
                elif tgt == current and src not in visited:
                    neighbor = src

                if neighbor:
                    visited.add(neighbor)
                    parent[neighbor] = current
                    queue.append(neighbor)

        return []  # 无路径

    # ========== 过滤 ==========
    def filter_by_category(self, category: str) -> dict:
        """按分类获取子图"""
        nodes = {nid: n for nid, n in self.data["nodes"].items() if n.get("category") == category}
        edges = {
            eid: e for eid, e in self.data["edges"].items()
            if e["source_id"] in nodes or e["target_id"] in nodes
        }
        return {
            "nodes": nodes, "edges": edges,
            "meta": {"total_nodes": len(nodes), "total_edges": len(edges)}
        }

    def filter_by_tag(self, tag: str) -> dict:
        """按标签获取子图"""
        nodes = {nid: n for nid, n in self.data["nodes"].items() if tag in n.get("tags", [])}
        edges = {
            eid: e for eid, e in self.data["edges"].items()
            if e["source_id"] in nodes or e["target_id"] in nodes
        }
        return {
            "nodes": nodes, "edges": edges,
            "meta": {"total_nodes": len(nodes), "total_edges": len(edges)}
        }

    # ========== 自动关联 ==========
    def auto_link(self, new_node: dict, threshold: float = 0.2) -> list[str]:
        """为新节点自动建立关联边。
        策略: 标签 Jaccard 重叠率 + 标题 Bigram 重叠率。
        返回创建的 edge_id 列表。
        """
        created_edges = []
        new_tags = set(new_node.get("tags", []))
        new_title_tokens = _tokenize(new_node.get("title", ""))
        nid = new_node["id"]

        for existing_id, existing in self.data["nodes"].items():
            if existing_id == nid:
                continue

            # 策略1: 标签 Jaccard 重叠
            existing_tags = set(existing.get("tags", []))
            if new_tags and existing_tags:
                jaccard = len(new_tags & existing_tags) / len(new_tags | existing_tags)
                if jaccard >= threshold:
                    eid = self.add_edge(nid, existing_id, "related_to", min(jaccard * 2, 1.0))
                    if eid and eid not in created_edges:
                        created_edges.append(eid)
                    continue

            # 策略2: 标题 Bigram 重叠
            existing_tokens = _tokenize(existing.get("title", ""))
            if new_title_tokens and existing_tokens:
                jaccard = len(new_title_tokens & existing_tokens) / max(len(new_title_tokens | existing_tokens), 1)
                if jaccard >= threshold * 2:
                    eid = self.add_edge(nid, existing_id, "related_to", min(jaccard * 2, 1.0))
                    if eid and eid not in created_edges:
                        created_edges.append(eid)

        return created_edges

    # ========== 统计 ==========
    def get_full_graph(self) -> dict:
        """返回完整知识图谱数据 (节点 + 边)"""
        self.reload()
        return {"nodes": self.data.get("nodes", {}), "edges": self.data.get("edges", [])}

    def get_stats(self) -> dict:
        """图谱统计信息"""
        nodes = self.data["nodes"]
        edges = self.data["edges"]

        # 分类分布
        categories = {}
        for n in nodes.values():
            cat = n.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        # 来源分布
        sources = {}
        for n in nodes.values():
            src = n.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1

        # 度分布
        degrees = {nid: 0 for nid in nodes}
        for e in edges.values():
            degrees[e["source_id"]] = degrees.get(e["source_id"], 0) + 1
            degrees[e["target_id"]] = degrees.get(e["target_id"], 0) + 1

        # 平均重要度
        avg_importance = sum(n.get("importance", 1) for n in nodes.values()) / max(len(nodes), 1)

        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "categories": categories,
            "sources": sources,
            "top_connected": sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:10],
            "avg_importance": round(avg_importance, 2),
            "last_updated": self.data["meta"].get("last_updated", "")
        }

    # ========== 图谱导入/导出 ==========
    def export_subgraph(self, node_ids: list[str]) -> dict:
        """导出指定节点及其关联边"""
        node_set = set(node_ids)
        sub_nodes = {nid: self.data["nodes"][nid] for nid in node_set if nid in self.data["nodes"]}
        sub_edges = {
            eid: e for eid, e in self.data["edges"].items()
            if e["source_id"] in node_set and e["target_id"] in node_set
        }
        return {"nodes": sub_nodes, "edges": sub_edges}

    def clear(self):
        """清空图谱"""
        self.data = {
            "nodes": {},
            "edges": {},
            "meta": {"total_nodes": 0, "total_edges": 0, "last_updated": ""}
        }
