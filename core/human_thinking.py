"""
human_thinking.py - 人类思维模拟引擎
让 AI 记忆系统模拟人类认知特性，而非机械检索。

核心机制:
1. 联想回忆 (Associative Recall): 基于知识图谱边传播激活
2. Ebbinghaus 遗忘曲线: 记忆强度随时间指数衰减
3. 情感加标签 (Emotional Tagging): 高情感记忆检索权重×2
4. 首因/近因效应: 对话开头和结尾的记忆额外加分
5. 间隔重复 (Spaced Repetition): SM-2 算法驱动的记忆复习
6. 组块化 (Chunking): 自动发现记忆簇 → 形成高层概念
7. 上下文依赖: 编码环境相似的记忆更容易被召回

设计参考:
- A-MEM Zettelkasten 原子化笔记 + 动态链接
- Supermemo SM-2 间隔重复算法
- Ebbinghaus 遗忘曲线: R = e^(-t/S)
- 认知心理学: 首因效应、近因效应、情感增强
"""
import json
import math
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional


class HumanThinkingEngine:
    """人类思维模拟引擎

    在每次检索时注入人类认知偏差和优化:
    - 不返回"最匹配的结果"，而是返回"最可能被人类回忆起的结果"
    - 核心差异: 情感权重 × 遗忘曲线 × 联想激活
    """

    # SM-2 间隔重复参数
    SM2_EF_DEFAULT = 2.5      # 初始容易度因子
    SM2_EF_MIN = 1.3          # 最低容易度因子

    # 情感标签关键词
    EMOTION_KEYWORDS = {
        "激动": 2.0, "震惊": 2.0, "惊喜": 1.8, "喜欢": 1.6,
        "重要": 1.5, "关键": 1.5, "紧急": 1.5, "开心": 1.4,
        "担心": 1.3, "遗憾": 1.2, "困惑": 1.1, "失望": 1.0,
    }

    def __init__(self, graph, memory_engine, memory_health, data_dir: Path):
        self.graph = graph
        self.memory = memory_engine
        self.health = memory_health
        self.data_dir = data_dir
        self.state_path = data_dir / "human-thinking-state.json"
        self.data = self._load()

    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "repetition_cards": {},    # node_id → {ef, interval_days, next_review, reps, last_review}
                "emotion_tags": {},         # node_id → {emotion, strength}
                "chunks": {},               # chunk_id → {label, members: [node_id], strength}
                "session_memory": [],       # 当前会话的交互ID列表（首因/近因）
                "meta": {"total_reviews": 0, "total_chunks": 0}
            }

    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ========== 联想回忆 ==========
    def associative_recall(
        self, seed_nodes: list[str], max_depth: int = 3,
        max_results: int = 20, activation_decay: float = 0.5
    ) -> list[dict]:
        """从种子节点出发，激活传播→关联记忆

        模拟人类"想到A→联想到B→又想到C"的思维链。
        激活在知识图谱边上传播，每跳衰减50%。

        Args:
            seed_nodes: 种子节点ID列表
            max_depth: 最大传播深度
            max_results: 最多返回结果数
            activation_decay: 每跳激活衰减率
        """
        self.graph.reload()
        activated: dict[str, float] = {}
        visited = set()
        frontier = list(seed_nodes)

        # 种子节点初始激活: 1.0
        for nid in seed_nodes:
            activated[nid] = 1.0
            visited.add(nid)

        for depth in range(max_depth):
            next_frontier = []
            for nid in frontier:
                base_activation = activated.get(nid, 0.3)
                # 遍历邻边
                for eid, edge in self.graph.data["edges"].items():
                    src, tgt = edge["source_id"], edge["target_id"]
                    neighbor = None
                    if src == nid and tgt not in visited:
                        neighbor = tgt
                    elif tgt == nid and src not in visited:
                        neighbor = src

                    if neighbor:
                        edge_strength = edge.get("strength", 0.5)
                        new_activation = base_activation * activation_decay * edge_strength
                        activated[neighbor] = max(activated.get(neighbor, 0), new_activation)
                        visited.add(neighbor)
                        next_frontier.append(neighbor)

            frontier = list(set(next_frontier))
            if not frontier:
                break

        # 按激活值排序
        ranked = sorted(
            [(nid, act) for nid, act in activated.items() if nid not in seed_nodes],
            key=lambda x: x[1], reverse=True
        )[:max_results]

        return [{
            "id": nid,
            "title": self.graph.data["nodes"].get(nid, {}).get("title", ""),
            "activation": round(act, 4),
            "summary": self.graph.data["nodes"].get(nid, {}).get("summary", "")[:120],
        } for nid, act in ranked]

    # ========== 遗忘曲线 ==========
    def recall_probability(self, node_id: str) -> float:
        """Ebbinghaus 遗忘曲线: 计算某条记忆当前被回忆起的概率

        R = e^(-t/S)
        t: 自上次复习/访问以来的时间
        S: 相对记忆强度 (基于重要性 + 复习次数)
        """
        entry = self.health.data["nodes"].get(node_id, {})
        if not entry:
            return 0.5

        try:
            last_access = datetime.fromisoformat(entry.get("last_access", entry.get("created_at", "")))
        except (ValueError, KeyError):
            return 0.5

        t_hours = (datetime.now() - last_access).total_seconds() / 3600
        importance = entry.get("importance", 3)
        access_count = entry.get("access_count", 0)

        # 相对强度: 重要性越高 + 复习越多 → 遗忘越慢
        S = importance * 24 * (1 + math.log(1 + access_count))
        R = math.exp(-t_hours / max(S, 1))

        return round(R, 4)

    # ========== 情感加标签 ==========
    def tag_emotion(self, node_id: str, text: str):
        """检测文本情感并加标签"""
        emotions = []
        for keyword, weight in self.EMOTION_KEYWORDS.items():
            if keyword in text:
                emotions.append({"emotion": keyword, "strength": weight})

        if emotions:
            # 取最强情感
            strongest = max(emotions, key=lambda x: x["strength"])
            self.data["emotion_tags"][node_id] = {
                "emotion": strongest["emotion"],
                "strength": strongest["strength"],
                "tagged_at": datetime.now().isoformat(),
            }
            self._save()

    def get_emotion_boost(self, node_id: str) -> float:
        """情感记忆检索权重加成"""
        tag = self.data["emotion_tags"].get(node_id, {})
        if not tag:
            return 1.0

        strength = tag.get("strength", 1.0)

        # 情感衰减: 强烈情感也会随时间淡化
        try:
            tagged_at = datetime.fromisoformat(tag.get("tagged_at", ""))
            age_days = (datetime.now() - tagged_at).days
            decay = math.exp(-age_days / 30)  # 30天半衰
            strength *= (0.3 + 0.7 * decay)
        except ValueError:
            pass

        return strength

    # ========== 首因/近因效应 ==========
    def session_memory_bias(self, node_id: str) -> float:
        """首因/近因效应: 对话开头和结尾的记忆额外加分

        首因效应: 前3个记忆 × 1.3
        近因效应: 最后3个记忆 × 1.2
        """
        session = self.data["session_memory"]
        if not session or node_id not in session:
            return 1.0

        pos = session.index(node_id)
        n = len(session)

        if pos < 3:
            return 1.3  # 首因
        if pos > n - 4:
            return 1.2  # 近因
        return 1.0

    def add_to_session(self, node_id: str):
        """记录一次会话互动"""
        self.data["session_memory"].append(node_id)
        # 保持最近100条
        if len(self.data["session_memory"]) > 100:
            self.data["session_memory"] = self.data["session_memory"][-100:]

    # ========== SM-2 间隔重复 ==========
    def sm2_review(self, node_id: str, quality: int) -> dict:
        """SM-2 算法: 根据用户评分计算下次复习时间

        quality: 0-5 评分
        0-1: 完全忘记
        2: 不太记得
        3: 记得但困难
        4: 记得但有犹豫
        5: 完美回忆

        返回: {next_review, interval_days, ef}
        """
        card = self.data["repetition_cards"].get(node_id, {
            "ef": self.SM2_EF_DEFAULT,
            "interval_days": 1,
            "reps": 0,
            "next_review": "",
            "last_review": "",
        })

        if quality < 3:
            # 忘记了 → 重置
            card["reps"] = 0
            card["interval_days"] = 1
        else:
            ef = card["ef"] + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            card["ef"] = max(self.SM2_EF_MIN, ef)

            if card["reps"] == 0:
                card["interval_days"] = 1
            elif card["reps"] == 1:
                card["interval_days"] = 6
            else:
                card["interval_days"] = round(card["interval_days"] * card["ef"])

            card["reps"] += 1

        card["last_review"] = datetime.now().isoformat()
        card["next_review"] = (datetime.now() + timedelta(days=card["interval_days"])).isoformat()
        self.data["repetition_cards"][node_id] = card
        self.data["meta"]["total_reviews"] += 1
        self._save()
        return card

    def get_due_reviews(self, limit: int = 10) -> list[dict]:
        """获取到期需要复习的记忆"""
        now = datetime.now()
        due = []
        for nid, card in self.data["repetition_cards"].items():
            try:
                next_review = datetime.fromisoformat(card["next_review"])
                if next_review <= now:
                    node = self.graph.data["nodes"].get(nid, {})
                    due.append({
                        "id": nid,
                        "title": node.get("title", "")[:80],
                        "interval_days": card["interval_days"],
                        "reps": card["reps"],
                        "overdue_days": (now - next_review).days,
                    })
            except (ValueError, KeyError):
                continue

        due.sort(key=lambda x: x["overdue_days"], reverse=True)
        return due[:limit]

    # ========== 组块化 (Chunking) ==========
    def detect_chunks(self, min_cluster_size: int = 3, edge_threshold: float = 0.5) -> list[dict]:
        """自动发现记忆簇 → 形成高层概念组块

        模拟人类"把零散信息打包成概念"的能力。
        检测知识图谱中的密集子图 → 标记为组块。
        """
        self.graph.reload()
        # 计算每个节点的连通度
        degrees = defaultdict(int)
        for eid, edge in self.graph.data["edges"].items():
            if edge.get("strength", 0) >= edge_threshold:
                degrees[edge["source_id"]] += 1
                degrees[edge["target_id"]] += 1

        # 找经常共现的节点群
        visited = set()
        new_chunks = []

        for nid, deg in sorted(degrees.items(), key=lambda x: x[1], reverse=True):
            if nid in visited or deg < 2:
                continue

            # BFS 收集相关节点
            cluster = {nid}
            frontier = [nid]
            for _ in range(2):  # 2跳深度
                next_frontier = []
                for fnid in frontier:
                    for eid, edge in self.graph.data["edges"].items():
                        if edge.get("strength", 0) < edge_threshold:
                            continue
                        if edge["source_id"] == fnid and edge["target_id"] not in visited:
                            cluster.add(edge["target_id"])
                            next_frontier.append(edge["target_id"])
                        elif edge["target_id"] == fnid and edge["source_id"] not in visited:
                            cluster.add(edge["source_id"])
                            next_frontier.append(edge["source_id"])
                frontier = list(set(next_frontier))

            if len(cluster) >= min_cluster_size:
                visited.update(cluster)
                # 生成组块标签（用最高频标签）
                tag_freq = defaultdict(int)
                labels = []
                for cnid in cluster:
                    node = self.graph.data["nodes"].get(cnid, {})
                    for tag in node.get("tags", []):
                        tag_freq[tag] += 1
                    labels.append(node.get("title", "")[:30])

                top_tag = max(tag_freq, key=tag_freq.get) if tag_freq else "未分类"
                chunk = {
                    "id": str(uuid.uuid4())[:8],
                    "label": f"组块-{top_tag}",
                    "members": list(cluster),
                    "member_count": len(cluster),
                    "avg_degree": sum(degrees.get(c, 0) for c in cluster) / len(cluster),
                    "top_keywords": sorted(tag_freq, key=tag_freq.get, reverse=True)[:5],
                }
                new_chunks.append(chunk)

        # 更新持久化
        for chunk in new_chunks:
            self.data["chunks"][chunk["id"]] = chunk
        self.data["meta"]["total_chunks"] = len(self.data["chunks"])
        self._save()

        return new_chunks

    # ========== 综合检索（注入人类认知）==========
    def human_like_search(
        self, query: str, base_results: list[dict],
        seed_nodes: list[str] = None,
    ) -> list[dict]:
        """在基础检索结果上叠加人类认知层

        为每个结果计算"人类回忆总分":
        score = base_score × recall_prob × emotion_boost × session_bias

        然后额外注入联想回忆的结果。
        """
        modified = []

        for item in base_results:
            nid = item.get("id", "")
            base_score = item.get("score", 0.5)

            # 遗忘曲线修正
            recall = self.recall_probability(nid)

            # 情感增强
            emotion = self.get_emotion_boost(nid)

            # 首因/近因
            session = self.session_memory_bias(nid)

            # 综合人类回忆分
            human_score = base_score * recall * emotion * session
            item["human_score"] = round(human_score, 4)
            item["recall_prob"] = recall
            item["emotion_boost"] = round(emotion, 4)
            modified.append(item)

        # 排序
        modified.sort(key=lambda x: x["human_score"], reverse=True)

        # 注入联想回忆
        if seed_nodes:
            associative = self.associative_recall(seed_nodes, max_depth=2, max_results=5)
            # 联想结果标上低原始分（因为它们不是直接匹配的）
            for assoc in associative:
                modified.append({
                    "id": assoc["id"],
                    "title": assoc["title"],
                    "summary": assoc.get("summary", ""),
                    "score": 0.3,  # 联想来源
                    "human_score": assoc["activation"] * 0.8,
                    "recall_prob": 0.9,
                    "emotion_boost": 1.0,
                    "source": "associative",
                })

        return modified[:len(base_results) + 5]

    # ========== 统计 ==========
    def stats(self) -> dict:
        return {
            "repetition_cards": len(self.data["repetition_cards"]),
            "due_reviews": len(self.get_due_reviews(100)),
            "emotion_tagged": len(self.data["emotion_tags"]),
            "chunks": self.data["meta"]["total_chunks"],
            "session_length": len(self.data["session_memory"]),
            "total_reviews": self.data["meta"]["total_reviews"],
        }
