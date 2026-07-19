"""
tfidf.py - TF-IDF 检索引擎
零外部依赖。纯 Python stdlib 实现。

功能:
- Bigram 中文分词索引
- TF-IDF 相关性计算
- 标签匹配加权
- 文档索引管理 (add/remove/rebuild)
- 搜索结果格式化

使用方式:
    from core.graph import KnowledgeGraph
    from core.digest import TextDigester
    from core.tfidf import SearchEngine

    graph = KnowledgeGraph(data_dir)
    digester = TextDigester(graph, data_dir)
    engine = SearchEngine(graph, digester)
    results = engine.search("Python 机器学习", top_k=5)
"""
import math
from typing import Optional


class SearchEngine:
    """TF-IDF 搜索引擎 — 零依赖中文全文检索

    索引策略:
    - 中文: Bigram + 单字 (从 TextDigester.tokenize 获取)
    - 英文: 正则提取 (从 TextDigester.tokenize 获取)
    - 停用词: 过滤 (在 TextDigester 中处理)

    评分策略:
    - 基础: TF-IDF (binary TF, standard IDF)
    - 加权: 查询标签与文档标签 Jaccard 重叠 × 0.3
    """

    def __init__(self, graph, digester):
        """
        Args:
            graph: KnowledgeGraph 实例 (读取节点)
            digester: TextDigester 实例 (提供 tokenize/extract_tags)
        """
        self.graph = graph
        self.digester = digester
        self.doc_tokens = {}    # node_id -> set(token)
        self.doc_freq = {}      # token -> doc_count
        self.doc_count = 0
        self.rebuild()

    # ========== 索引管理 ==========
    def rebuild(self):
        """从知识图谱重建全文索引"""
        self.graph.reload()
        self.doc_tokens = {}
        self.doc_freq = {}
        self.doc_count = 0

        for node_id, node in self.graph.data["nodes"].items():
            text = node.get("title", "") + " " + node.get("content", "")
            tokens = set(self.digester.tokenize(text))
            self.doc_tokens[node_id] = tokens
            for token in tokens:
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1
            self.doc_count += 1

    def add_document(self, node_id: str, title: str, content: str):
        """增量添加单篇文档到索引"""
        text = title + " " + content
        tokens = set(self.digester.tokenize(text))
        self.doc_tokens[node_id] = tokens
        for token in tokens:
            self.doc_freq[token] = self.doc_freq.get(token, 0) + 1
        self.doc_count += 1

    def remove_document(self, node_id: str):
        """从索引移除文档"""
        if node_id in self.doc_tokens:
            tokens = self.doc_tokens.pop(node_id)
            for token in tokens:
                # 全局 df 是近似维护的（不重建全索引时略有误差）
                pass
            self.doc_count -= 1

    # ========== 检索 ==========
    def search_raw(self, query: str, top_k: int = 10, category: Optional[str] = None) -> list[tuple[str, float, dict]]:
        """原始搜索结果: [(node_id, score, node_dict), ...]

        Args:
            query: 搜索词
            top_k: 返回前 N 条
            category: 可选, 限定只在指定分类中搜索 (None=全部分类)
        """
        query_terms = self.digester.tokenize(query)
        if not query_terms:
            return []

        scores = {}
        self.graph.reload()
        query_term_set = set(query_terms)

        # TF-IDF 计算
        for term in query_term_set:
            df = self.doc_freq.get(term, 0)
            if df == 0:
                continue
            idf = math.log(self.doc_count / (1 + df))
            for node_id, doc_tokens in self.doc_tokens.items():
                if term in doc_tokens:
                    scores[node_id] = scores.get(node_id, 0) + idf  # binary TF = 1

        # 标签匹配加权
        query_tags = set(self.digester.extract_tags(query))
        for node_id, node in self.graph.data["nodes"].items():
            if node_id in scores:
                node_tags = set(node.get("tags", []))
                tag_overlap = len(query_tags & node_tags)
                scores[node_id] += tag_overlap * 0.3

        # category 过滤 (在算分后裁剪, 保证 top_k 仍然是过滤后最相关的)
        if category:
            scores = {
                nid: s for nid, s in scores.items()
                if self.graph.data["nodes"].get(nid, {}).get("category") == category
            }

        # 排序
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for node_id, score in ranked[:top_k]:
            node = self.graph.data["nodes"].get(node_id, {})
            results.append((node_id, round(score, 4), node))

        return results

    def search(self, query: str, top_k: int = 10, category: Optional[str] = None) -> list[dict]:
        """格式化搜索结果 — 适合 API 直接返回

        Args:
            query: 搜索词
            top_k: 返回前 N 条
            category: 可选, 限定分类
        """
        results = self.search_raw(query, top_k, category=category)
        return [{
            "id": node_id,
            "title": node.get("title", ""),
            "summary": node.get("summary", ""),
            "category": node.get("category", ""),
            "tags": node.get("tags", []),
            "score": score,
            "importance": node.get("importance", 1),
            "source": node.get("source", ""),
            "created_at": node.get("created_at", "")
        } for node_id, score, node in results]

    # ========== 诊断 ==========
    def explain(self, query: str, node_id: str) -> dict:
        """解释某节点为什么被检索到"""
        query_terms = self.digester.tokenize(query)
        tokens = self.doc_tokens.get(node_id, set())
        matched = [t for t in set(query_terms) if t in tokens]
        idf_scores = {}
        for t in matched:
            df = self.doc_freq.get(t, 0)
            idf_scores[t] = math.log(self.doc_count / (1 + df)) if df > 0 else 0

        query_tags = set(self.digester.extract_tags(query))
        node = self.graph.data["nodes"].get(node_id, {})
        node_tags = set(node.get("tags", []))
        matched_tags = query_tags & node_tags

        return {
            "node_id": node_id,
            "query_terms": query_terms,
            "matched_terms": matched,
            "idf_scores": idf_scores,
            "matched_tags": list(matched_tags),
            "tag_bonus": len(matched_tags) * 0.3,
            "total_score": sum(idf_scores.values()) + len(matched_tags) * 0.3
        }

    # ========== 状态 ==========
    def stats(self) -> dict:
        """索引统计"""
        return {
            "doc_count": self.doc_count,
            "vocab_size": len(self.doc_freq),
            "avg_doc_length": sum(len(t) for t in self.doc_tokens.values()) / max(self.doc_count, 1)
        }
