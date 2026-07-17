"""
fast_index.py - 记忆快速索引引擎
多层索引加速检索，解决 TF-IDF 全表扫描慢的问题。

核心机制:
1. 倒排索引: token → sorted[(node_id, tf_score)]  O(1) 直接命中
2. 热门令牌缓存 (Hot Tier): 前100高频token常驻内存 + 预计算top-k
3. 布隆过滤器: 快速判断token是否在索引中，避免无效扫描
4. 前缀树 (Trie): 自动补全 & 模糊匹配
5. 分层检索: Hot Tier → Warm Tier → Cold Tier 逐级降级

性能目标: 172节点下 <5ms 检索延迟
"""
import json
import math
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional


class TrieNode:
    """前缀树节点"""
    __slots__ = ("children", "is_word", "token")
    def __init__(self):
        self.children = {}
        self.is_word = False
        self.token = ""


class FastIndex:
    """快速索引引擎

    数据结构:
    - inverted: {token: [(node_id, term_freq, tfidf_precomputed)]}
    - hot_cache: 前 N 个高频token的预计算结果
    - bloom: 布隆过滤器位图 (用于快速否定)
    - trie: 前缀树 (用于自动补全)
    """

    HOT_CACHE_SIZE = 100   # 热门缓存大小
    BLOOM_SIZE = 2**16     # 布隆过滤器位图大小 (8KB)

    def __init__(self, graph, digester, data_dir: Path):
        self.graph = graph
        self.digester = digester
        self.data_dir = data_dir
        self.index_path = data_dir / "fast-index.json"

        # 核心数据结构
        self.inverted: dict[str, list] = {}     # token → [(nid, tf, tfidf)]
        self.doc_lengths: dict[str, int] = {}    # node_id → token_count
        self.hot_cache: dict[str, list] = {}     # 热门token预计算
        self.bloom: int = 0                      # 布隆过滤器
        self.trie = TrieNode()                   # 前缀树
        self.token_freq: dict[str, int] = {}     # token频率
        self.doc_count: int = 0
        self.avg_doc_len: float = 0

        # 增量更新队列
        self._dirty_nodes: set[str] = set()

        # BM25F 字段加权
        self.bm25f_field_weights = {"title": 3.0, "summary": 2.0, "tags": 1.5, "content": 1.0}
        self.bm25f_k1 = 1.5
        self.bm25f_b = 0.75
        self.field_lengths: dict[str, dict[str, int]] = {}
        self.avg_field_lengths: dict[str, float] = {}

        # 加载或构建
        if self.index_path.exists():
            self._load()
        else:
            self.rebuild()

    # ========== 布隆过滤器 ==========
    def _bloom_hash(self, token: str, seed: int) -> int:
        """简单双哈希布隆"""
        h = seed
        for c in token:
            h = ((h * 31) + ord(c)) % self.BLOOM_SIZE
        return h

    def _bloom_add(self, token: str):
        self.bloom |= (1 << self._bloom_hash(token, 0))
        self.bloom |= (1 << self._bloom_hash(token, 1))
        self.bloom |= (1 << self._bloom_hash(token, 7))

    def _bloom_contains(self, token: str) -> bool:
        """可能包含（无假阴性，有概率假阳性）"""
        return all(
            (self.bloom >> self._bloom_hash(token, s)) & 1
            for s in (0, 1, 7)
        )

    # ========== 前缀树 ==========
    def _trie_insert(self, token: str):
        node = self.trie
        for c in token:
            if c not in node.children:
                node.children[c] = TrieNode()
            node = node.children[c]
        node.is_word = True
        node.token = token

    def _trie_search(self, prefix: str, limit: int = 10) -> list[str]:
        """前缀搜索 → 自动补全"""
        node = self.trie
        for c in prefix:
            if c not in node.children:
                return []
            node = node.children[c]

        results = []
        def _dfs(n: TrieNode):
            if n.is_word:
                results.append(n.token)
            for child in n.children.values():
                if len(results) < limit:
                    _dfs(child)
        _dfs(node)
        return results

    # ========== 索引构建 ==========
    def rebuild(self):
        """从知识图谱全量重建索引"""
        t0 = time.time()
        self.graph.reload()
        self.inverted = {}
        self.doc_lengths = {}
        self.token_freq = defaultdict(int)
        self.bloom = 0
        self.trie = TrieNode()
        self.doc_count = 0

        # 扫描所有节点
        for node_id, node in self.graph.data["nodes"].items():
            text = node.get("title", "") + " " + node.get("content", "")
            tokens = list(self.digester.tokenize(text))
            self.doc_lengths[node_id] = len(tokens)
            self.doc_count += 1

            # BM25F 字段长度
            self.field_lengths[node_id] = {
                "title": len(list(self.digester.tokenize(node.get("title", "")))),
                "summary": len(list(self.digester.tokenize(node.get("summary", "")))),
                "tags": len(node.get("tags", [])),
                "content": len(list(self.digester.tokenize(node.get("content", "")))),
            }

            # 词频统计
            tf_map = defaultdict(int)
            for t in tokens:
                tf_map[t] += 1
                self.token_freq[t] += 1

            # 写入倒排索引
            for token, freq in tf_map.items():
                if token not in self.inverted:
                    self.inverted[token] = []
                    self._bloom_add(token)
                    self._trie_insert(token)
                self.inverted[token].append((node_id, freq, 0.0))  # TFIDF 稍后批量计算

        # 批量计算 TF-IDF
        self._batch_tfidf()

        # 计算字段平均长度 (for BM25F)
        if self.field_lengths:
            for field in ["title", "summary", "tags", "content"]:
                lens = [fl.get(field, 0) for fl in self.field_lengths.values()]
                self.avg_field_lengths[field] = sum(lens) / max(len(lens), 1)

        # 构建热门缓存
        self._build_hot_cache()

        self._save()
        elapsed = (time.time() - t0) * 1000
        print(f"[FastIndex] 重建完成: {self.doc_count} 文档, {len(self.inverted)} 词, {elapsed:.1f}ms")

    def _batch_tfidf(self):
        """批量计算所有 TF-IDF 分数"""
        for token, postings in self.inverted.items():
            df = len(postings)  # 文档频率
            idf = math.log(self.doc_count / (1 + df))
            for i, (nid, tf, _) in enumerate(postings):
                doc_len = self.doc_lengths.get(nid, 1)
                tf_norm = tf / doc_len  # 归一化词频
                self.inverted[token][i] = (nid, tf, round(tf_norm * idf, 4))

        self.avg_doc_len = sum(self.doc_lengths.values()) / max(self.doc_count, 1)

    def _build_hot_cache(self):
        """构建热门令牌缓存"""
        # 取前 HOT_CACHE_SIZE 个高频token
        hot_tokens = sorted(self.token_freq.items(), key=lambda x: x[1], reverse=True)[:self.HOT_CACHE_SIZE]
        for token, _ in hot_tokens:
            postings = self.inverted.get(token, [])
            # 预排序：按 TF-IDF 降序
            self.hot_cache[token] = sorted(postings, key=lambda x: x[2], reverse=True)[:20]
        print(f"[FastIndex] 热门缓存: {len(self.hot_cache)} 个令牌")

    # ========== 增量更新 ==========
    def add_document(self, node_id: str, title: str, content: str):
        """增量添加文档"""
        text = title + " " + content
        tokens = list(self.digester.tokenize(text))
        self.doc_lengths[node_id] = len(tokens)
        self.doc_count += 1

        tf_map = defaultdict(int)
        for t in tokens:
            tf_map[t] += 1
            self.token_freq[t] += 1

        for token, freq in tf_map.items():
            if token not in self.inverted:
                self.inverted[token] = []
                self._bloom_add(token)
                self._trie_insert(token)
            doc_len = max(len(tokens), 1)
            df = max(len(self.inverted[token]), 1)
            idf = math.log(self.doc_count / df) if df > 0 else 0
            tf_norm = freq / doc_len
            self.inverted[token].append((node_id, freq, round(tf_norm * idf, 4)))

        # 失效热门缓存，延迟重建
        self._dirty_nodes.add(node_id)

    def remove_document(self, node_id: str):
        """从索引移除文档"""
        if node_id in self.doc_lengths:
            del self.doc_lengths[node_id]
            self.doc_count -= 1

        # 从倒排索引清除
        for token in list(self.inverted.keys()):
            before = len(self.inverted[token])
            self.inverted[token] = [(n, f, s) for n, f, s in self.inverted[token] if n != node_id]
            if not self.inverted[token]:
                del self.inverted[token]

    def refresh_hot_cache(self):
        """刷新热门缓存（增量更新后调用）"""
        if self._dirty_nodes:
            self._build_hot_cache()
            self._dirty_nodes.clear()

    # ========== 检索 ==========
    def search(self, query: str, top_k: int = 10, category: Optional[str] = None) -> list[dict]:
        """快速检索

        检索流程:
        1. 分词 + 布隆过滤 (排除无效token)
        2. 按token稀有度排序 (优先用稀有token，区分度高)
        3. Hot Cache 命中 → 直接返回预计算结果
        4. 倒排索引合并 (TAAT: Term-At-A-Time 累加)
        5. 标签加权 + 分类过滤
        """
        query_tokens = list(self.digester.tokenize(query))
        if not query_tokens:
            return []

        # 布隆过滤: 只保留实际在索引中的token
        valid_tokens = [t for t in query_tokens if self._bloom_contains(t)]
        if not valid_tokens:
            return []

        # 按稀有度排序: 稀有token(低df)区分度更高, 优先处理
        valid_tokens.sort(key=lambda t: len(self.inverted.get(t, [])))

        # 累加得分
        scores: dict[str, float] = defaultdict(float)

        for token in valid_tokens:
            # 优先查热门缓存
            if token in self.hot_cache:
                postings = self.hot_cache[token]
            else:
                postings = self.inverted.get(token, [])

            for nid, tf, tfidf in postings:
                scores[nid] += tfidf

        # 标签加权
        query_tags = set(self.digester.extract_tags(query))
        for nid in list(scores.keys()):
            node = self.graph.data["nodes"].get(nid, {})
            node_tags = set(node.get("tags", []))
            tag_bonus = len(query_tags & node_tags) * 0.3
            scores[nid] += tag_bonus

        # 分类过滤
        if category:
            scores = {
                nid: s for nid, s in scores.items()
                if self.graph.data["nodes"].get(nid, {}).get("category") == category
            }

        # 排序 + top-k
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return [{
            "id": nid,
            "title": self.graph.data["nodes"].get(nid, {}).get("title", ""),
            "summary": self.graph.data["nodes"].get(nid, {}).get("summary", ""),
            "category": self.graph.data["nodes"].get(nid, {}).get("category", ""),
            "tags": self.graph.data["nodes"].get(nid, {}).get("tags", []),
            "score": round(score, 4),
            "importance": self.graph.data["nodes"].get(nid, {}).get("importance", 1),
        } for nid, score in ranked]

    # ========== v2.1: 混合检索 (Multi-Signal RRF Fusion) ==========
    RRF_K = 60  # RRF 平滑常数

    def _search_signal_sparse(self, query: str, top_k: int = 30) -> dict[str, float]:
        """信号1: 稀疏检索 (TF-IDF 倒排索引)"""
        query_tokens = list(self.digester.tokenize(query))
        if not query_tokens:
            return {}

        valid_tokens = [t for t in query_tokens if self._bloom_contains(t)]
        if not valid_tokens:
            return {}

        valid_tokens.sort(key=lambda t: len(self.inverted.get(t, [])))
        scores: dict[str, float] = defaultdict(float)

        for token in valid_tokens:
            postings = self.hot_cache.get(token) or self.inverted.get(token, [])
            for nid, tf, tfidf in postings:
                scores[nid] += tfidf

        # 归一化到 [0, 1]
        if scores:
            max_s = max(scores.values())
            if max_s > 0:
                scores = {k: v / max_s for k, v in scores.items()}

        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k])

    def _search_signal_bm25f(self, query: str, top_k: int = 30) -> dict[str, float]:
        """信号1 (升级): BM25F 字段加权检索

        BM25F 公式 (Robertson et al., 2004):
          weighted_tf(d) = Σ_f w_f × tf_f / (1 - b_f + b_f × len_f / avg_len_f)
          BM25F(q, d) = Σ_i IDF(q_i) × weighted_tf(d) / (k1 + weighted_tf(d))

        字段权重: title(3.0) > summary(2.0) > tags(1.5) > content(1.0)

        """
        q_tokens = list(self.digester.tokenize(query))
        if not q_tokens:
            return {}

        valid = [t for t in q_tokens if self._bloom_contains(t)]
        if not valid:
            return {}

        scores: dict[str, float] = defaultdict(float)

        for token in valid:
            postings = self.inverted.get(token, [])
            df = len(postings)
            # BM25 IDF
            idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)

            for nid, raw_tf, _ in postings:
                node = self.graph.data["nodes"].get(nid, {})
                fl = self.field_lengths.get(nid, {})

                # 计算字段加权 TF
                weighted_tf = 0.0
                for field, w_f in self.bm25f_field_weights.items():
                    tf_f = 0
                    len_f = fl.get(field, 0)
                    avg_len_f = self.avg_field_lengths.get(field, 1.0)
                    b_f = 0.0 if field == "title" else self.bm25f_b

                    if field == "title":
                        tf_f = len([t for t in self.digester.tokenize(node.get("title", "")) if t == token])
                    elif field == "summary":
                        tf_f = len([t for t in self.digester.tokenize(node.get("summary", "")) if t == token])
                    elif field == "tags":
                        tf_f = len([t for t in node.get("tags", []) if t == token])
                    elif field == "content":
                        tf_f = len([t for t in self.digester.tokenize(node.get("content", "")) if t == token])

                    if tf_f > 0:
                        norm_factor = 1.0 - b_f + b_f * (len_f / max(avg_len_f, 1))
                        weighted_tf += w_f * tf_f / max(norm_factor, 0.1)

                if weighted_tf > 0:
                    scores[nid] += idf * weighted_tf / (self.bm25f_k1 + weighted_tf)

        # 归一化
        if scores:
            max_s = max(scores.values())
            if max_s > 0:
                scores = {k: v / max_s for k, v in scores.items()}

        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k])

    def _search_signal_graph(self, query: str, top_k: int = 30) -> dict[str, float]:
        """信号2: 图谱关联得分 (基于共享标签 + 共享关键词)"""
        scores: dict[str, float] = defaultdict(float)
        query_tokens = set(self.digester.tokenize(query))
        query_tags = set(self.digester.extract_tags(query))

        for node_id, node in self.graph.data["nodes"].items():
            node_tags = set(node.get("tags", []))
            # Jaccard 标签相似度
            if query_tags or node_tags:
                union = len(query_tags | node_tags)
                if union > 0:
                    tag_sim = len(query_tags & node_tags) / union
                    scores[node_id] += tag_sim * 0.5

            # 标题/摘要 token 重叠
            node_text = node.get("title", "") + " " + node.get("summary", "")
            node_tokens = set(self.digester.tokenize(node_text))
            if query_tokens and node_tokens:
                token_overlap = len(query_tokens & node_tokens) / max(len(query_tokens), 1)
                scores[node_id] += token_overlap * 0.5

        # 归一化
        if scores:
            max_s = max(scores.values())
            if max_s > 0:
                scores = {k: v / max_s for k, v in scores.items()}

        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k])

    def _search_signal_recency(self, top_k: int = 30) -> dict[str, float]:
        """信号3: 时间近度得分 (最近创建的优先)"""
        scores: dict[str, float] = {}
        now = datetime.now()

        for node_id, node in self.graph.data["nodes"].items():
            ts = node.get("created", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    days_ago = (now - dt).total_seconds() / 86400
                    # 指数衰减: 7天内高分, 30天后趋零
                    scores[node_id] = math.exp(-days_ago / 7)
                except (ValueError, TypeError):
                    scores[node_id] = 0.1
            else:
                scores[node_id] = 0.1

        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k])

    def _search_signal_importance(self, top_k: int = 30) -> dict[str, float]:
        """信号4: 重要性得分"""
        scores: dict[str, float] = {}
        for node_id, node in self.graph.data["nodes"].items():
            imp = node.get("importance", 1)
            scores[node_id] = imp / 5.0  # 归一化到 [0, 1]

        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k])

    # 中英文同义词映射 — 弥补词法搜索语义盲区
    SYNONYM_GROUPS: list[set[str]] = [
        {"ai", "人工智能", "机器学习", "深度学习", "神经网络", "智能"},
        {"模型", "model", "算法", "网络"},
        {"编程", "代码", "coding", "开发", "编写"},
        {"第二大脑", "知识库", "记忆系统", "知识图谱"},
        {"视频", "影像", "动画", "画面", "影片"},
        {"搜索", "检索", "查询", "查找"},
        {"数据", "信息", "资料"},
        {"llm", "大模型", "语言模型", "大语言模型"},
        {"系统", "平台", "架构", "框架"},
        {"优化", "改进", "提升", "增强"},
        {"提示词", "prompt", "提示"},
        {"投资", "买入", "交易", "持仓"},
        {"pcb", "印刷电路板", "电路板", "印制板"},
        {"神经网络", "transformer", "attention"},
        {"工作", "项目", "任务"},
        {"导演", "拍摄", "运镜", "镜头"},
    ]

    def _build_synonym_map(self) -> dict[str, set[str]]:
        """构建双向同义词映射"""
        m: dict[str, set[str]] = {}
        for group in self.SYNONYM_GROUPS:
            for word in group:
                m[word] = group
        return m

    def expand_query(self, query: str) -> list[str]:
        """查询扩展: 将'AI 搜索'扩展为 ['ai', '人工智能', '机器学习', '搜索', '检索', '查询']"""
        tokens = self.digester.tokenize(query)
        synonym_map = self._build_synonym_map()
        expanded = set()
        for token in tokens:
            expanded.add(token)
            group = synonym_map.get(token.lower(), set())
            expanded.update(group)
        return list(expanded)

    def _rrf_fusion(self, signal_results: list[dict[str, float]], top_k: int = 20) -> list[tuple[str, float]]:
        """
        Reciprocal Rank Fusion: 融合多路检索信号

        公式: RRF(d) = Σ 1/(k + rank_i(d))
        优点: 不依赖分数量纲，只看排名，工业界标准
        """
        rrf_scores: dict[str, float] = defaultdict(float)

        for signal in signal_results:
            rank = 1
            for node_id in signal:
                rrf_scores[node_id] += 1.0 / (self.RRF_K + rank)
                rank += 1

        # 去零，排序
        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def search_hybrid(self, query: str, top_k: int = 10,
                      category: Optional[str] = None) -> list[dict]:
        """
        v2.1 混合检索：4路信号 RRF 融合

        信号1: 稀疏检索 (TF-IDF 倒排索引) — 精确关键词匹配
        信号2: 图谱关联 (标签Jaccard + token重叠) — 语义相关性
        信号3: 近度 (指数衰减) — 新鲜度偏好
        信号4: 重要性 (1-5分) — 信息价值

        融合: RRF (Reciprocal Rank Fusion, k=60)
        """
        # v2.2: 查询扩展 — 同义词丰富召回
        query_expanded = " ".join(self.expand_query(query))

        # 并行召回 (4路信号) — v2.2: signal1升级为BM25F字段加权
        signal1 = self._search_signal_bm25f(query_expanded, top_k=30)
        signal2 = self._search_signal_graph(query_expanded, top_k=30)
        signal3 = self._search_signal_recency(top_k=30)
        signal4 = self._search_signal_importance(top_k=30)

        # RRF 融合
        fused = self._rrf_fusion([signal1, signal2, signal3, signal4], top_k=top_k * 2)

        # 分类过滤
        if category:
            fused = [
                (nid, s) for nid, s in fused
                if self.graph.data["nodes"].get(nid, {}).get("category") == category
            ]

        fused = fused[:top_k]

        return [{
            "id": nid,
            "title": self.graph.data["nodes"].get(nid, {}).get("title", ""),
            "summary": self.graph.data["nodes"].get(nid, {}).get("summary", ""),
            "category": self.graph.data["nodes"].get(nid, {}).get("category", ""),
            "tags": self.graph.data["nodes"].get(nid, {}).get("tags", []),
            "score": round(score, 4),
            "importance": self.graph.data["nodes"].get(nid, {}).get("importance", 1),
        } for nid, score in fused]

    # ========== v2.1: 重排序 (Cross-Signal Reranker) ==========
    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        """
        重排序：对候选结果进行交叉信号精排

        从混合检索的 Top-20 中精排 Top-5，考虑：
        1. 关键词密度 (30%) — query token 在文档中的覆盖率
        2. 标签Jaccard (20%) — 标签精确匹配
        3. 标题命中 (25%) — 标题是否包含 query token (信号强)
        4. 重要性加权 (15%) — 信息价值
        5. 近度加权 (10%) — 时间新鲜度
        """
        if not candidates:
            return []

        expanded_tokens = set(self.expand_query(query))
        query_tokens = set(self.digester.tokenize(query))
        query_tokens_expanded = query_tokens | expanded_tokens
        if not query_tokens_expanded:
            return candidates[:top_k]

        now = datetime.now()
        reranked = []

        for cand in candidates:
            nid = cand["id"]
            node = self.graph.data["nodes"].get(nid, {})
            node_text = node.get("title", "") + " " + node.get("summary", "") + " " + node.get("content", "")
            node_tokens = self.digester.tokenize(node_text)
            node_tags = set(node.get("tags", []))
            query_tags = set(self.digester.extract_tags(query))

            # 1. 关键词密度 (30%)
            hit_count = sum(1 for t in node_tokens if t in query_tokens_expanded)
            kw_density = hit_count / max(len(node_tokens), 1)

            # 2. 标签Jaccard (20%)
            if query_tags or node_tags:
                tag_jaccard = len(query_tags & node_tags) / max(len(query_tags | node_tags), 1)
            else:
                tag_jaccard = 0

            # 3. 标题命中 (25%)
            title = node.get("title", "")
            title_tokens = set(self.digester.tokenize(title))
            title_hit = len(query_tokens_expanded & title_tokens) / max(len(query_tokens_expanded), 1)

            # 4. 重要性 (15%)
            imp = node.get("importance", 1) / 5.0

            # 5. 近度 (10%)
            ts = node.get("created", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    days_ago = (now - dt).total_seconds() / 86400
                    recency = math.exp(-days_ago / 14)  # 14天半衰期
                except (ValueError, TypeError):
                    recency = 0.3
            else:
                recency = 0.3

            # 加权总分
            final = (
                kw_density * 0.30 +
                tag_jaccard * 0.20 +
                title_hit * 0.25 +
                imp * 0.15 +
                recency * 0.10
            )

            reranked.append({
                **cand,
                "rerank_score": round(final, 4),
                "breakdown": {
                    "kw_density": round(kw_density, 3),
                    "tag_jaccard": round(tag_jaccard, 3),
                    "title_hit": round(title_hit, 3),
                    "importance": round(imp, 3),
                    "recency": round(recency, 3),
                }
            })

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]

    def autocomplete(self, prefix: str, limit: int = 10) -> list[str]:
        """自动补全"""
        return self._trie_search(prefix, limit)

    def token_exists(self, token: str) -> bool:
        """快速判断 token 是否在索引中 (布隆过滤器)"""
        return self._bloom_contains(token)

    # ========== 持久化 ==========
    def _save(self):
        """保存索引（仅持久化倒排索引元数据，不保存全量 postings——太大）"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "doc_count": self.doc_count,
            "vocab_size": len(self.inverted),
            "avg_doc_len": round(self.avg_doc_len, 2),
            "hot_tokens": list(self.hot_cache.keys()),
            "bloom_hex": hex(self.bloom),
            "updated": datetime.now().isoformat(),
        }
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        """加载索引元数据，触发重建"""
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            print(f"[FastIndex] 检测到已有索引 ({meta.get('doc_count', 0)} 文档), 重建中...")
            # 恢复布隆过滤器
            if "bloom_hex" in meta:
                self.bloom = int(meta["bloom_hex"], 16)
        except Exception:
            pass
        self.rebuild()

    def stats(self) -> dict:
        return {
            "doc_count": self.doc_count,
            "vocab_size": len(self.inverted),
            "hot_cache_size": len(self.hot_cache),
            "avg_doc_len": round(self.avg_doc_len, 2),
            "bloom_bits": bin(self.bloom).count("1"),
        }
