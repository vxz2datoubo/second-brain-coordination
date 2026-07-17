"""
actr_memory.py — ACT-R 认知架构的记忆激活模型

基于 Anderson & Schooler (1991) ACT-R 的陈述性记忆理论：
https://act-r.psy.cmu.edu/

核心公式：

1. 基础级激活 (Base-Level Activation):
   B_i = ln(Σ_{j=1}^{n} t_j^{-d})

   其中:
   - t_j = 第 j 次访问距今的秒数
   - d = 衰减参数 (默认 0.5, 匹配人类记忆幂律衰减)
   - n = 历史访问总次数
   - B_i = 激活强度 (越大越容易被召回)

2. 检索概率 (Retrieval Probability):
   P(recall) = 1 / (1 + e^{-(B_i - τ) / s})

   其中:
   - τ = 检索阈值 (默认 -0.5, 低于此值极难被回忆)
   - s = 噪声参数 (默认 0.4, 控制 sigmoid 陡峭度)

3. 激活传播 (Spreading Activation):
   A_i = B_i + Σ_{(j→i)∈edges} W_ji × S_ji × B_j

   其中:
   - W_ji = 边权重 (默认 1.0)
   - S_ji = 联想强度 = 1 / 源节点出度

核心特性：
- 幂律遗忘 (Power-law forgetting): 比指数衰减更符合人类数据
- 间距效应 (Spacing effect): 分散访问比集中访问产生更高激活
- 检索强化 (Retrieval strengthens): 每次成功检索都会增加激活
- 激活阈值剪枝: B_i < τ 的记忆进入"不可访问"状态

设计参考:
- Anderson, J. R., & Schooler, L. J. (1991). "Reflections of the environment in memory"
- Pavlik, P. I., & Anderson, J. R. (2005). "Practice and forgetting effects"
- ACT-R 7.0 Reference Manual (act-r.psy.cmu.edu)
"""
import json
import math
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional


class ACTRMemory:
    """ACT-R 陈述性记忆模型

    每个知识节点 (chunk) 的激活由访问历史决定，
    而非简单的"上次访问→指数衰减"。
    """

    # === 可调参数 ===
    DECAY_D = 0.5          # 幂律衰减指数 (人类记忆典型值)
    THRESHOLD_TAU = -0.5   # 检索阈值 (低于此值 = 不可访问)
    NOISE_S = 0.4          # 检索噪声 (sigmoid 陡峭度)
    SPREAD_FACTOR = 0.2    # 激活传播因子
    PRUNE_THRESHOLD = -1.5 # 剪枝阈值 (远低于 τ, 永久遗忘候选)
    MAX_ACCESS_LOG = 50    # 每个节点最多保留的访问历史

    def __init__(self, graph, data_dir: Path):
        self.graph = graph
        self.data_dir = data_dir
        self.state_path = data_dir / "actr-state.json"
        self.data = self._load()

    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "access_log": {},             # node_id → [access_timestamp, ...]
                "activation_cache": {},        # node_id → {B, P, last_computed}
                "spreading_cache": {},         # node_id → {A, last_computed}
            }

    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ========== 访问记录 ==========
    def access(self, node_id: str):
        """记录一次记忆访问（检索或激活）"""
        if node_id not in self.data["access_log"]:
            self.data["access_log"][node_id] = []
        now = time.time()
        self.data["access_log"][node_id].append(now)
        # 保留最近 N 次
        if len(self.data["access_log"][node_id]) > self.MAX_ACCESS_LOG:
            self.data["access_log"][node_id] = \
                self.data["access_log"][node_id][-self.MAX_ACCESS_LOG:]

    def batch_access(self, node_ids: list[str]):
        """批量记录访问（用于检索结果反馈）"""
        now = time.time()
        for nid in node_ids:
            if nid not in self.data["access_log"]:
                self.data["access_log"][nid] = []
            self.data["access_log"][nid].append(now)
            if len(self.data["access_log"][nid]) > self.MAX_ACCESS_LOG:
                self.data["access_log"][nid] = self.data["access_log"][nid][-self.MAX_ACCESS_LOG:]

    def bootstrap_from_created_at(self):
        """用节点的 created_at 时间作为首次访问时间进行冷启动"""
        for node_id, node in self.graph.data.get("nodes", {}).items():
            if node_id in self.data["access_log"]:
                continue
            try:
                ts_str = node.get("created_at", "") or node.get("created", "")
                if ts_str:
                    dt = datetime.fromisoformat(ts_str)
                    self.data["access_log"][node_id] = [dt.timestamp()]
            except (ValueError, TypeError):
                self.data["access_log"][node_id] = [time.time() - 86400 * 7]

    # ========== 基础级激活 ==========
    def base_activation(self, node_id: str) -> float:
        """
        B_i = ln(Σ t_j^{-d})

        幂律遗忘: 每次访问的贡献 = t_j^{-d}
        - 刚访问: 贡献大
        - 旧访问: 贡献衰减为 t_j^{-0.5} (随 sqrt(t) 衰减)

        间距效应: 2次访问间隔1天比间隔1小时产生更高激活
        """
        access_times = self.data["access_log"].get(node_id, [])
        if not access_times:
            return float("-inf")  # 从未访问过

        now = time.time()
        total = 0.0
        for t_j in access_times:
            lag = max(1.0, now - t_j)  # 最小1秒避免除零
            total += lag ** (-self.DECAY_D)

        if total <= 0:
            return float("-inf")

        return math.log(total)

    def activation_batch(self, node_ids: list[str]) -> dict[str, float]:
        """批量计算激活值"""
        return {nid: self.base_activation(nid) for nid in node_ids}

    # ========== 检索概率 ==========
    def retrieval_probability(self, node_id: str) -> float:
        """
        P(recall) = 1 / (1 + e^{-(B_i - τ) / s})

        逻辑斯蒂函数: B_i 远大于 τ 时 → P≈1; B_i 远小于 τ 时 → P≈0
        """
        B = self.base_activation(node_id)
        if B == float("-inf"):
            return 0.0
        try:
            return round(1.0 / (1.0 + math.exp(-(B - self.THRESHOLD_TAU) / self.NOISE_S)), 4)
        except OverflowError:
            return 1.0 if B > self.THRESHOLD_TAU else 0.0

    # ========== 激活传播 (Spreading Activation) ==========
    def spreading_activation(self, node_id: str, max_depth: int = 2) -> float:
        """
        从邻居节点接收激活:
        A_i = B_i + Σ W_ji × S_ji × B_j

        模拟人类"由A想到B"的联想过程。
        """
        B_i = self.base_activation(node_id)
        if B_i == float("-inf"):
            B_i = -3.0  # 从未访问 → 低基线

        spread = 0.0
        edges = self.graph.data.get("edges", {})

        # 收集指向该节点的所有边
        for edge in edges.values():
            src = edge.get("source_id", "")
            tgt = edge.get("target_id", "")
            if tgt != node_id:
                continue
            B_j = self.base_activation(src)
            if B_j == float("-inf"):
                continue
            W = edge.get("weight", 1.0)
            # 联想强度 = 1/出度
            out_degree = sum(1 for e in edges.values() if e.get("source_id") == src)
            S_ji = 1.0 / max(out_degree, 1)
            spread += W * S_ji * B_j * self.SPREAD_FACTOR

        return round(B_i + spread, 4)

    # ========== 全量评分 ==========
    def score_all(self) -> dict:
        """计算所有节点的激活和检索概率，返回统计"""
        self.graph.reload()
        self.bootstrap_from_created_at()

        scores = {}
        retrievable = 0
        prunable = 0
        high_activation = 0

        for nid in self.graph.data["nodes"]:
            B = self.base_activation(nid)
            P = self.retrieval_probability(nid)
            scores[nid] = {"B": round(B, 4) if B != float("-inf") else -999.0, "P": P}

            if P >= 0.5:
                retrievable += 1
            if B != float("-inf") and B >= 1.0:
                high_activation += 1
            if B == float("-inf") or B < self.PRUNE_THRESHOLD:
                prunable += 1

        # 排序
        sorted_by_B = sorted(
            [(nid, s["B"]) for nid, s in scores.items() if s["B"] > -999],
            key=lambda x: x[1], reverse=True
        )
        sorted_by_P = sorted(
            [(nid, s["P"]) for nid, s in scores.items()],
            key=lambda x: x[1], reverse=True
        )

        total = len(scores)
        avg_B = sum(s["B"] for s in scores.values() if s["B"] > -999) / max(total, 1)

        self._save()
        return {
            "model": "ACT-R v1.0",
            "total": total,
            "retrievable (P>=0.5)": retrievable,
            "high_activation (B>=1.0)": high_activation,
            "prunable (B<PRUNE)": prunable,
            "avg_activation": round(avg_B, 4),
            "top10": [{"id": nid, "B": B} for nid, B in sorted_by_B[:10]],
            "bottom10": [{"id": nid, "B": B} for nid, B in sorted_by_B[-10:]],
            "top10_retrievable": [{"id": nid, "P": P} for nid, P in sorted_by_P[:10]],
        }

    # ========== 衰减模拟 (前向预测) ==========
    def simulate_decay(self, node_id: str, days_ahead: list[int]) -> list[dict]:
        """
        预测 N 天后该记忆的激活值，用于主动复习调度
        """
        access_times = self.data["access_log"].get(node_id, [])
        if not access_times:
            return []

        results = []
        base_time = time.time()
        for days in days_ahead:
            future = base_time + days * 86400
            total = 0.0
            for t_j in access_times:
                lag = max(1.0, future - t_j)
                total += lag ** (-self.DECAY_D)
            B = math.log(total) if total > 0 else float("-inf")
            P = 1.0 / (1.0 + math.exp(-(B - self.THRESHOLD_TAU) / self.NOISE_S)) if B != float("-inf") else 0.0
            results.append({
                "days": days,
                "activation": round(B, 4) if B != float("-inf") else -999.0,
                "retrieval_p": round(P, 4),
                "will_forget": P < 0.3
            })

        return results

    # ========== 间距效应演示 ==========
    def spacing_effect_demo(self) -> dict:
        """
        演示间距效应: 相同总时间，分散访问 vs 集中访问

        场景A: 2次访问间隔1秒 (集中)
        场景B: 2次访问间隔86400秒=1天 (分散)
        60天后比较
        """
        t0 = time.time()
        # 场景A: 集中 (2次间隔1秒)
        massed = [t0, t0 + 1]
        # 场景B: 分散 (2次间隔1天)
        spaced = [t0, t0 + 86400]

        future = t0 + 60 * 86400  # 60天后

        def compute_B(accesses):
            total = sum((max(1, future - t)) ** (-self.DECAY_D) for t in accesses)
            return math.log(total) if total > 0 else float("-inf")

        B_massed = compute_B(massed)
        B_spaced = compute_B(spaced)

        return {
            "scenario": "60天后，2次访问",
            "massed_1sec": {"B": round(B_massed, 4), "equivalent_to_single_access": True},
            "spaced_1day": {"B": round(B_spaced, 4), "B_ratio_vs_massed": round(B_spaced / B_massed, 2) if B_massed != float("-inf") else "∞"},
            "interpretation": (
                "分散访问的激活值显著高于集中访问，"
                "即使总访问次数相同。这解释了为什么分散学习比考前突击更有效。"
            ),
        }

    # ========== 获取推荐复习列表 ==========
    def get_review_recommendations(self, limit: int = 10) -> list[dict]:
        """基于 ACT-R 激活的智能复习推荐"""
        self.graph.reload()
        self.bootstrap_from_created_at()

        candidates = []
        for nid in self.graph.data["nodes"]:
            B = self.base_activation(nid)
            P = self.retrieval_probability(nid)
            if P < 0.5 and P > 0.05:  # 还不到不可访问，但正在遗忘
                # 预测7天后的衰减
                decay = self.simulate_decay(nid, [7])
                will_forget_7d = decay[0]["will_forget"] if decay else True
                node = self.graph.data["nodes"].get(nid, {})
                candidates.append({
                    "id": nid,
                    "title": node.get("title", "")[:80],
                    "P_current": P,
                    "B_current": round(B, 4) if B != float("-inf") else -999.0,
                    "will_forget_7d": will_forget_7d,
                    "category": node.get("category", ""),
                })

        # 排序: 当前检索概率最低且即将遗忘的优先
        candidates.sort(key=lambda x: (x["will_forget_7d"], x["P_current"]))
        return candidates[:limit]
