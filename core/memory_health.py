"""
memory_health.py - 记忆健康管理引擎
解决记忆只增不减导致的噪声累积问题。

核心机制:
1. TTL三维衰减: 时间 × 重要性 × 访问频率
2. 矛盾检测: 相似记忆语义冲突→标记→裁决
3. 访问追踪: 每次检索记录访问，冷记忆降权
4. 自动修剪: 低分记忆定期淘汰（软删除→归档→真删除）

设计参考: Mem0 TTL机制 + Ebbinghaus遗忘曲线
"""
import json
import math
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


class MemoryHealthManager:
    """记忆健康管理器

    三维衰减模型:
    - 时间衰减 (Ebbinghaus): S(t) = S₀ × e^(-t/τ)  where τ = half_life / ln(2)
    - 重要性权重: importance ∈ [1,5], 5级记忆衰减更慢
    - 访问频率: 被检索越多衰减越慢, 冷记忆加速遗忘

    健康分数: health = base × (1 - time_decay) × imp_factor × access_factor
    health < THRESHOLD → 进入待淘汰队列
    """

    # 默认半衰期（小时）
    DEFAULT_HALF_LIFE = {
        5: 720,   # 极其重要: 30天半衰期
        4: 336,   # 很重要:   14天
        3: 168,   # 重要:     7天
        2: 72,    # 一般:     3天
        1: 24,    # 不重要:   1天
    }

    HEALTH_THRESHOLD = 0.15  # 低于此分进入软删除
    PURGE_THRESHOLD = 0.05   # 低于此分永久删除

    def __init__(self, graph, memory_engine, data_dir: Path):
        self.graph = graph
        self.memory = memory_engine
        self.data_dir = data_dir
        self.health_path = data_dir / "memory-health.json"
        self.archive_path = data_dir / "memory-archive.json"
        self.data = self._load(self.health_path, {
            "nodes": {},        # node_id -> {health_score, last_access, access_count, created, importance, half_life}
            "contradictions": [], # [{node_a, node_b, reason, resolved}]
            "purge_queue": [],  # 待淘汰 node_id 列表
            "meta": {"last_check": "", "total_purged": 0, "total_archived": 0}
        })
        self.archive = self._load(self.archive_path, {"archived": [], "meta": {}})

    def _load(self, path: Path, default: dict) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.health_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _save_archive(self):
        with open(self.archive_path, "w", encoding="utf-8") as f:
            json.dump(self.archive, f, ensure_ascii=False, indent=2)

    # ========== 注册新记忆 ==========
    def register(self, node_id: str, importance: int = 3):
        """新记忆加入健康追踪"""
        if node_id in self.data["nodes"]:
            return
        half_life = self.DEFAULT_HALF_LIFE.get(importance, 168)
        self.data["nodes"][node_id] = {
            "health_score": 1.0,
            "last_access": datetime.now().isoformat(),
            "access_count": 0,
            "created_at": datetime.now().isoformat(),
            "importance": importance,
            "half_life_hours": half_life,
            "review_count": 0,
            "last_review": "",
        }

    # ========== 访问追踪 ==========
    def touch(self, node_id: str):
        """记录一次访问（检索命中视为访问）"""
        if node_id not in self.data["nodes"]:
            # 新节点自动注册
            node = self.graph.get_node(node_id)
            imp = node.get("importance", 3) if node else 3
            self.register(node_id, imp)

        entry = self.data["nodes"][node_id]
        entry["access_count"] += 1
        entry["last_access"] = datetime.now().isoformat()
        # 访问为记忆"充电"：恢复部分健康值
        boost = 0.15 * min(1.0, entry["access_count"] / 10)
        entry["health_score"] = min(1.0, entry["health_score"] + boost)

    def touch_by_query(self, node_ids: list[str]):
        """批量记录检索命中"""
        for nid in node_ids:
            self.touch(nid)

    # ========== TTL 衰减计算 ==========
    def calculate_health(self, node_id: str) -> float:
        """计算某条记忆的当前健康分数"""
        entry = self.data["nodes"].get(node_id)
        if not entry:
            return 1.0

        now = datetime.now()
        try:
            created = datetime.fromisoformat(entry["created_at"])
            last_access = datetime.fromisoformat(entry["last_access"])
        except (ValueError, KeyError):
            return entry.get("health_score", 1.0)

        # 时间衰减 (Ebbinghaus 简化): decay = e^(-t/τ)
        age_hours = (now - created).total_seconds() / 3600
        tau = entry["half_life_hours"] / math.log(2)
        time_decay = math.exp(-age_hours / max(tau, 1))

        # 重要性因子: importance 越高衰减越慢
        imp_factor = entry["importance"] / 3.0  # 1→0.33, 3→1.0, 5→1.67

        # 访问频率因子: 冷记忆加速衰减
        idle_hours = (now - last_access).total_seconds() / 3600
        access_penalty = math.exp(-idle_hours / max(entry["half_life_hours"], 1))

        # 综合健康分
        health = time_decay * imp_factor * (0.6 + 0.4 * access_penalty)

        entry["health_score"] = round(health, 4)
        return health

    def calculate_all(self) -> dict:
        """计算所有记忆健康分，返回统计"""
        scores = {}
        for nid in self.data["nodes"]:
            scores[nid] = self.calculate_health(nid)

        if not scores:
            return {"avg": 1.0, "min": 1.0, "count": 0, "at_risk": 0}

        return {
            "avg": round(sum(scores.values()) / len(scores), 4),
            "min": round(min(scores.values()), 4),
            "count": len(scores),
            "at_risk": sum(1 for s in scores.values() if s < self.HEALTH_THRESHOLD),
            "critical": sum(1 for s in scores.values() if s < self.PURGE_THRESHOLD),
        }

    # ========== 矛盾检测 ==========
    def detect_contradictions(self, min_similarity: float = 0.4) -> list[dict]:
        """检测知识图谱中的矛盾记忆

        策略:
        1. 找标签高度重叠的节点对
        2. 提取两者的结论性语句
        3. 标记为潜在矛盾（需 LLM 裁决）
        """
        contradictions = []
        self.graph.reload()
        nodes = list(self.graph.data["nodes"].values())

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                a, b = nodes[i], nodes[j]
                # 标签 Jaccard 相似度
                tags_a = set(a.get("tags", []))
                tags_b = set(b.get("tags", []))
                if not tags_a or not tags_b:
                    continue
                jaccard = len(tags_a & tags_b) / len(tags_a | tags_b)
                if jaccard < min_similarity:
                    continue

                # 检测内容中是否有矛盾指示词
                content_a = (a.get("title", "") + " " + a.get("content", "")).lower()
                content_b = (b.get("title", "") + " " + b.get("content", "")).lower()

                conflict_markers = ["但是", "然而", "相反", "不过", "其实", "并非", "错误"]
                has_conflict = any(m in content_a or m in content_b for m in conflict_markers)

                if has_conflict or jaccard > 0.7:
                    contradictions.append({
                        "id": str(uuid.uuid4())[:8],
                        "node_a": a["id"],
                        "node_b": b["id"],
                        "title_a": a.get("title", "")[:60],
                        "title_b": b.get("title", "")[:60],
                        "jaccard": round(jaccard, 3),
                        "detected": datetime.now().isoformat(),
                        "resolved": False,
                        "resolution": "",
                    })

        # 更新持久化
        self.data["contradictions"] = contradictions
        return contradictions

    # ========== 自动修剪 ==========
    def prune(self, dry_run: bool = True) -> dict:
        """执行记忆修剪

        dry_run=True: 仅报告将要淘汰的，不实际操作
        dry_run=False: 软删除→归档→真删除
        """
        self.calculate_all()
        to_soft_delete = []   # 健康分 < HEALTH_THRESHOLD
        to_purge = []         # 健康分 < PURGE_THRESHOLD（从归档中）

        for nid, entry in self.data["nodes"].items():
            score = entry.get("health_score", 0)
            if score < self.PURGE_THRESHOLD:
                to_purge.append((nid, score))
            elif score < self.HEALTH_THRESHOLD:
                to_soft_delete.append((nid, score))

        if dry_run:
            return {
                "dry_run": True,
                "to_soft_delete": len(to_soft_delete),
                "to_purge": len(to_purge),
                "soft_delete_ids": [nid for nid, _ in to_soft_delete[:10]],
                "purge_ids": [nid for nid, _ in to_purge[:10]],
            }

        # 软删除：移到归档
        for nid, score in to_soft_delete:
            node = self.graph.get_node(nid)
            if node:
                self.archive["archived"].append({
                    "node": node,
                    "health_score": score,
                    "archived_at": datetime.now().isoformat(),
                    "reason": "health_decay",
                })
            # 从主图谱移除
            self.graph.remove_node(nid)
            del self.data["nodes"][nid]

        # 真删除：清除归档中极低分项
        for nid, score in to_purge:
            if nid in self.data["nodes"]:
                del self.data["nodes"][nid]

        self.data["meta"]["total_purged"] += len(to_purge)
        self.data["meta"]["total_archived"] += len(to_soft_delete)
        self.data["meta"]["last_check"] = datetime.now().isoformat()
        self._save()
        self._save_archive()

        return {
            "dry_run": False,
            "soft_deleted": len(to_soft_delete),
            "purged": len(to_purge),
            "remaining": len(self.data["nodes"]),
        }

    # ========== 强化学习——反馈驱动权重调整 ==========
    def reinforce(self, node_id: str, positive: bool = True):
        """用户反馈强化：好评→提升重要性/半衰期"""
        if node_id not in self.data["nodes"]:
            self.register(node_id)

        entry = self.data["nodes"][node_id]
        if positive:
            entry["importance"] = min(5, entry["importance"] + 1)
            entry["half_life_hours"] = self.DEFAULT_HALF_LIFE.get(entry["importance"], 168)
            entry["health_score"] = min(1.0, entry["health_score"] + 0.3)
            entry["review_count"] += 1
            entry["last_review"] = datetime.now().isoformat()
        else:
            entry["importance"] = max(1, entry["importance"] - 1)
            entry["half_life_hours"] = self.DEFAULT_HALF_LIFE.get(entry["importance"], 168)
            entry["health_score"] = max(0.01, entry["health_score"] - 0.3)
        self._save()

    # ========== 统计与诊断 ==========
    def stats(self) -> dict:
        health = self.calculate_all()
        return {
            "tracked": len(self.data["nodes"]),
            "contradictions": len(self.data["contradictions"]),
            "unresolved_contradictions": sum(1 for c in self.data["contradictions"] if not c["resolved"]),
            "archived": len(self.archive["archived"]),
            "total_purged": self.data["meta"]["total_purged"],
            "health": health,
        }

    def status_report(self) -> str:
        """人类可读的健康报告"""
        s = self.stats()
        h = s["health"]
        lines = [
            f"🧠 记忆健康报告",
            f"  追踪记忆: {s['tracked']} 条",
            f"  平均健康: {h['avg']:.2f}",
            f"  风险记忆: {h['at_risk']} 条 (健康<{self.HEALTH_THRESHOLD})",
            f"  临界记忆: {h['critical']} 条 (健康<{self.PURGE_THRESHOLD})",
            f"  未解矛盾: {s['unresolved_contradictions']} 对",
            f"  已归档: {s['archived']} | 已淘汰: {s['total_purged']}",
        ]
        return "\n".join(lines)
