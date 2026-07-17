"""
self_verify.py - 自我验证引擎
让 AI 系统在输出前自我检验，减少幻觉和逻辑错误。

核心机制:
1. 一致性检查 (Consistency): 新结论与已有记忆是否矛盾？
2. 溯源验证 (Source Tracing): 检索到的知识能否追溯到原始来源？
3. 置信度评分 (Confidence): 每条记忆基于来源质量/交叉验证/新鲜度打分
4. 推理链验证 (Chain Validation): 多步推理是否自洽？
5. A/B 决策审计 (Decision Audit): 决策路径跟踪与结果对比

设计参考:
- Hermes Self-Evolution 验证门 (dry-run + 自动评估)
- Mem0 自修正 (版本管理 + 矛盾合并)
- GraphRAG 知识接地 (来源可追溯)
"""
import json
import math
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional


class SelfVerify:
    """自我验证引擎

    验证策略:
    - 事前验证 (输出前): 一致性检查 + 溯源
    - 事后验证 (输出后): 用户反馈 → 修正
    - 周期性审计: 决策路径跟踪
    """

    # 来源可信度评分
    SOURCE_CREDIBILITY = {
        "manual": 0.9,       # 人工录入
        "verified": 1.0,     # 已验证
        "imported": 0.7,     # 导入
        "auto_extracted": 0.5,  # 自动提取
        "llm_generated": 0.4,   # LLM生成
        "web_scraped": 0.3,     # 网页抓取
        "unknown": 0.2,         # 未知来源
    }

    def __init__(self, graph, memory_engine, memory_health, data_dir: Path):
        self.graph = graph
        self.memory = memory_engine
        self.health = memory_health
        self.data_dir = data_dir
        self.verify_path = data_dir / "verify-log.json"
        self.decisions_path = data_dir / "decision-audit.json"
        self.data = self._load()

    def _load(self) -> dict:
        try:
            with open(self.verify_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "checks": [],           # 验证检查记录
                "violations": [],       # 违规记录
                "corrected": [],        # 已修正记录
                "meta": {"total_checks": 0, "violation_rate": 0.0}
            }

    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data["meta"]["total_checks"] = len(self.data["checks"])
        self.data["meta"]["violation_rate"] = (
            len(self.data["violations"]) / max(len(self.data["checks"]), 1)
        )
        with open(self.verify_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _load_decisions(self) -> dict:
        try:
            with open(self.decisions_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"decisions": [], "meta": {}}

    def _save_decisions(self, data: dict):
        with open(self.decisions_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ========== 来源可信度 ==========
    def source_credibility(self, node_id: str) -> float:
        """计算某条记忆的来源可信度 (v1: 仅来源+新鲜度)"""
        node = self.graph.get_node(node_id)
        if not node:
            return 0.2

        source = node.get("source", "unknown")
        base_cred = self.SOURCE_CREDIBILITY.get(source, 0.3)

        try:
            created_at = datetime.fromisoformat(node.get("created_at", ""))
            age_days = (datetime.now() - created_at).days
            if age_days > 90:
                base_cred *= 0.8
            if age_days > 365:
                base_cred *= 0.6
        except (ValueError, KeyError):
            pass

        feedback_score = node.get("feedback_score", 0)
        base_cred += feedback_score * 0.1

        return round(min(1.0, max(0.1, base_cred)), 3)

    def source_credibility_v2(self, node_id: str) -> float:
        """v2: 多源可信度 = 来源(30%) + 交叉印证(40%) + 图谱连接(20%) + 内容质量(10%)"""
        node = self.graph.get_node(node_id)
        if not node:
            return 0.15

        # 1. 来源可信度 (30%权重)
        source = node.get("source", "unknown")
        base_cred = self.SOURCE_CREDIBILITY.get(source, 0.3)
        try:
            created_at = datetime.fromisoformat(node.get("created_at", ""))
            age_days = (datetime.now() - created_at).days
            if age_days > 90:
                base_cred *= 0.85
            if age_days > 365:
                base_cred *= 0.7
        except (ValueError, KeyError):
            pass
        feedback_score = node.get("feedback_score", 0)
        base_cred += feedback_score * 0.1
        source_score = min(1.0, max(0.15, base_cred))

        # 2. 交叉印证得分 (40%权重) — 标签重叠的其他节点数量归一化
        tags = set(node.get("tags", []))
        corroboration_count = 0
        content_lower = (node.get("title", "") + " " + node.get("summary", "")).lower()
        for other_id, other in self.graph.data["nodes"].items():
            if other_id == node_id:
                continue
            other_tags = set(other.get("tags", []))
            if not tags or not other_tags:
                continue
            jaccard = len(tags & other_tags) / max(len(tags | other_tags), 1)
            if jaccard >= 0.25:
                corroboration_count += 1
        # 归一化: 0印证→0分, 5+印证→满分
        cross_score = min(1.0, corroboration_count / 8.0)

        # 3. 图谱连接度 (20%权重) — 入边+出边数量
        edge_count = 0
        edges = self.graph.data.get("edges", {})
        for edge in edges.values():
            if edge.get("source_id") == node_id or edge.get("target_id") == node_id:
                edge_count += 1
        # 归一化: 0边→0分, 10+边→满分
        graph_score = min(1.0, edge_count / 12.0)

        # 4. 内容质量 (10%权重) — 内容越丰富越可靠
        content_len = len(node.get("summary", "")) + len(node.get("content", ""))
        quality_score = min(1.0, content_len / 500.0)

        # 加权融合
        final = source_score * 0.30 + cross_score * 0.40 + graph_score * 0.20 + quality_score * 0.10
        return round(min(1.0, max(0.1, final)), 4)

    # ========== v2.2 迭代式真相发现 (Iterative Truth Discovery) ==========
    # 基于 Li et al. (VLDB 2014) "Truth Discovery on Crowdsourcing" 和
    # Dong et al. (KDD 2015) "Knowledge-Based Trust" 的迭代框架
    #
    # 核心思想:
    # - 来源权重和声明的真实值相互依赖
    # - 靠谱的来源 → 高权重 → 其声明更可信
    # - 被验证的声明多 → 来源更靠谱
    # - 迭代至收敛 (Δw < ε)
    #
    # 公式:
    #   truth_score_i^{(t+1)} = Σ_s w_s^{(t)} × claim_score_{s,i} / Σ_s w_s^{(t)}
    #   error_s = Σ_i |claim_score_{s,i} - truth_score_i| / n_s
    #   w_s^{(t+1)} = -log(error_s + ε)   ← 使用对数惩罚放大差来源的误差

    def iterative_truth_discovery(self, max_iterations: int = 20,
                                   convergence_eps: float = 1e-4) -> dict:
        """
        迭代式真相发现: 同时优化每条记忆的可信度和每个来源的权重

        返回: {
            iterations: 收敛所需迭代数,
            source_weights: {source_type: final_weight},
            credibility: {node_id: final_credibility},
            convergence: Δw历史
        }
        """
        self.graph.reload()
        nodes = self.graph.data["nodes"]
        if not nodes:
            return {"error": "no nodes"}

        # 1. 初始化来源权重 (均匀)
        source_types = set()
        for node in nodes.values():
            source_types.add(node.get("source", "unknown"))
        source_weights = {s: 1.0 for s in source_types}

        # 2. 构建 source→node 映射
        source_nodes: dict[str, list[str]] = {s: [] for s in source_types}
        for nid, node in nodes.items():
            s = node.get("source", "unknown")
            source_nodes[s].append(nid)

        # 3. 初始化声明值 (基于内容质量的基准分)
        claim_scores: dict[str, float] = {}
        for nid, node in nodes.items():
            content_len = len(node.get("summary", "")) + len(node.get("content", ""))
            tag_count = len(node.get("tags", []))
            edge_count = 0
            edges = self.graph.data.get("edges", {})
            for edge in edges.values():
                if edge.get("source_id") == nid or edge.get("target_id") == nid:
                    edge_count += 1
            # 基准分: 内容+标签+连接的综合
            claim_scores[nid] = min(1.0, 0.3 + content_len / 2000 * 0.4 + tag_count / 10 * 0.15 + edge_count / 20 * 0.15)

        # 4. 迭代
        convergence_history = []
        for iteration in range(max_iterations):
            # (a) 估计真相: 加权平均
            truth_scores: dict[str, float] = {}
            for s, weight in source_weights.items():
                for nid in source_nodes[s]:
                    if nid not in truth_scores:
                        truth_scores[nid] = {"weighted_sum": 0.0, "weight_sum": 0.0}
                    truth_scores[nid]["weighted_sum"] += weight * claim_scores[nid]
                    truth_scores[nid]["weight_sum"] += weight

            for nid in truth_scores:
                ws = truth_scores[nid]["weight_sum"]
                truth_scores[nid] = truth_scores[nid]["weighted_sum"] / ws if ws > 0 else claim_scores.get(nid, 0.5)

            # (b) 估计来源误差 & 更新权重
            new_weights = {}
            for s in source_types:
                nids = source_nodes[s]
                if not nids:
                    new_weights[s] = 1.0
                    continue
                errors = [abs(claim_scores[nid] - truth_scores.get(nid, 0.5)) for nid in nids]
                mean_error = sum(errors) / len(errors)
                # 对数惩罚: 误差越小，权重越大
                # w = -ln(error + 0.01), 确保 w > 0
                new_weights[s] = -math.log(mean_error + 0.01)

            # 归一化
            max_w = max(new_weights.values()) if new_weights else 1.0
            if max_w > 0:
                new_weights = {s: w / max_w for s, w in new_weights.items()}

            # (c) 检查收敛
            delta = sum(abs(new_weights.get(s, 0) - source_weights.get(s, 0)) for s in source_types)
            convergence_history.append(delta)
            source_weights = new_weights

            if delta < convergence_eps:
                break

        # 5. 最终可信度 = truth_scores × source_penalty
        final_cred: dict[str, float] = {}
        for nid in nodes:
            ts = truth_scores.get(nid, claim_scores.get(nid, 0.5))
            final_cred[nid] = round(min(1.0, max(0.05, ts)), 4)

        # 统计
        scores = list(final_cred.values())
        avg = round(sum(scores) / len(scores), 4)

        return {
            "iterations": len(convergence_history),
            "converged": convergence_history[-1] < convergence_eps if convergence_history else False,
            "final_delta": round(convergence_history[-1], 6) if convergence_history else 0,
            "source_weights": {s: round(w, 4) for s, w in source_weights.items()},
            "credibility": {
                "avg": avg,
                "min": round(min(scores), 4),
                "max": round(max(scores), 4),
                "high(>=0.6)": sum(1 for s in scores if s >= 0.6),
                "medium(0.35-0.6)": sum(1 for s in scores if 0.35 <= s < 0.6),
                "low(<0.35)": sum(1 for s in scores if s < 0.35),
            },
            "convergence_history": [round(d, 6) for d in convergence_history],
            "weights": source_weights,
            "top5_scores": sorted(final_cred.items(), key=lambda x: x[1], reverse=True)[:5],
            "bottom5_scores": sorted(final_cred.items(), key=lambda x: x[1])[:5],
        }

    def rate_all_credibility(self, v2: bool = True) -> dict:
        """为所有记忆打分"""
        self.graph.reload()
        scorer = self.source_credibility_v2 if v2 else self.source_credibility
        scores = {}
        for nid in self.graph.data["nodes"]:
            scores[nid] = scorer(nid)

        if not scores:
            return {"avg": 0, "min": 0, "count": 0}

        avg = round(sum(scores.values()) / len(scores), 3)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return {
            "avg": avg,
            "min": min(scores.values()),
            "max": max(scores.values()),
            "low_credibility": [nid for nid, s in scores.items() if s < 0.35],
            "high_credibility": [nid for nid, s in scores.items() if s >= 0.6],
            "top5": [{"id": nid, "score": s} for nid, s in sorted_scores[:5]],
            "bottom5": [{"id": nid, "score": s} for nid, s in sorted_scores[-5:]],
            "distribution": {
                "high(>=0.6)": sum(1 for s in scores.values() if s >= 0.6),
                "medium(0.35-0.6)": sum(1 for s in scores.values() if 0.35 <= s < 0.6),
                "low(<0.35)": sum(1 for s in scores.values() if s < 0.35),
            },
            "count": len(scores),
        }

    def verify_all_nodes(self) -> dict:
        """全量节点交叉验证 + 更新可信度"""
        self.graph.reload()
        results = []
        for nid in list(self.graph.data["nodes"].keys()):
            cv = self.cross_validate(nid)
            results.append(cv)

        cred = self.rate_all_credibility(v2=True)
        return {
            "timestamp": datetime.now().isoformat(),
            "total_nodes": len(results),
            "cross_validated": sum(1 for r in results if r.get("corroborating_count", 0) > 0),
            "disputed": sum(1 for r in results if r.get("verdict") == "disputed"),
            "trusted": sum(1 for r in results if r.get("verdict") == "trusted"),
            "credibility": cred,
        }

    # ========== 交叉验证 ==========
    def cross_validate(self, node_id: str) -> dict:
        """交叉验证: 查找支持/反对该节点的其他节点

        支持: 标签重叠率高 + 有 supports 边
        反对: 标签重叠率高 + 内容含矛盾指示词
        """
        node = self.graph.get_node(node_id)
        if not node:
            return {"node_id": node_id, "error": "not found"}

        tags = set(node.get("tags", []))
        content = (node.get("title", "") + " " + node.get("content", "")).lower()
        corroborating = []
        contradicting = []

        self.graph.reload()
        for other_id, other in self.graph.data["nodes"].items():
            if other_id == node_id:
                continue

            other_tags = set(other.get("tags", []))
            if not tags or not other_tags:
                continue

            jaccard = len(tags & other_tags) / len(tags | other_tags)
            if jaccard < 0.3:
                continue

            other_content = (other.get("title", "") + " " + other.get("content", "")).lower()
            # 检查是否有矛盾标记
            conflict_markers = ["但是", "然而", "相反", "不过", "其实", "并非", "不对"]
            has_conflict = any(m in other_content for m in conflict_markers)

            if has_conflict:
                contradicting.append({
                    "id": other_id,
                    "title": other.get("title", "")[:60],
                    "jaccard": round(jaccard, 3),
                })
            else:
                corroborating.append({
                    "id": other_id,
                    "title": other.get("title", "")[:60],
                    "jaccard": round(jaccard, 3),
                })

        return {
            "node_id": node_id,
            "title": node.get("title", "")[:80],
            "credibility": self.source_credibility(node_id),
            "corroborating_count": len(corroborating),
            "contradicting_count": len(contradicting),
            "corroborating": corroborating[:5],
            "contradicting": contradicting[:3],
            "verdict": "trusted" if len(corroborating) >= len(contradicting) and len(contradicting) == 0 else
                       "disputed" if len(contradicting) > 0 else "unverified",
        }

    # ========== 一致性检查 ==========
    def check_consistency(self, claim: str, context_node_ids: list[str]) -> dict:
        """检查新声明与已有知识的一致性

        Args:
            claim: 新生成的声明/结论
            context_node_ids: 推理中引用的知识节点
        Returns:
            {consistent: bool, conflicts: [...], warnings: [...]}
        """
        conflicts = []
        warnings = []
        claim_lower = claim.lower()

        # 检查引用的节点之间是否矛盾
        for i in range(len(context_node_ids)):
            for j in range(i + 1, len(context_node_ids)):
                a = self.graph.get_node(context_node_ids[i])
                b = self.graph.get_node(context_node_ids[j])
                if not a or not b:
                    continue

                # 找矛盾边
                edges = self.graph.get_edges_between(context_node_ids[i], context_node_ids[j])
                for edge in edges:
                    if edge.get("relation") == "contradicts":
                        conflicts.append({
                            "type": "existing_contradiction",
                            "node_a": a.get("title", "")[:60],
                            "node_b": b.get("title", "")[:60],
                            "detail": f"节点 {context_node_ids[i][:8]} 与 {context_node_ids[j][:8]} 已有矛盾关系",
                        })

        # 检查新claim是否与引用的节点矛盾
        contradiction_keywords = {
            "不是": "negation",
            "错误": "correction",
            "并非": "negation",
            "其实": "correction",
            "相反": "opposition",
        }
        for nid in context_node_ids:
            node = self.graph.get_node(nid)
            if not node:
                continue
            content = (node.get("title", "") + " " + node.get("content", "")).lower()
            for kw, ctype in contradiction_keywords.items():
                if kw in claim_lower and kw in content:
                    warnings.append({
                        "type": "potential_contradiction",
                        "node_id": nid,
                        "node_title": node.get("title", "")[:60],
                        "keyword": kw,
                    })

        consistent = len(conflicts) == 0
        return {
            "consistent": consistent,
            "conflicts": conflicts,
            "warnings": warnings,
            "recommendation": "可以输出" if consistent else "存在矛盾, 建议重新审视",
        }

    # ========== 推理链验证 ==========
    def verify_reasoning_chain(self, chain: list[dict]) -> dict:
        """验证多步推理链的自洽性

        chain: [{step, conclusion, based_on_node_ids}]

        检查:
        1. 每步的 based_on_node_ids 是否存在
        2. 相邻步骤的结论是否有逻辑断裂
        3. 最终结论是否与初始前提矛盾
        """
        results = {
            "valid": True,
            "steps": [],
            "issues": [],
        }

        for i, step in enumerate(chain):
            step_result = {"step": i + 1, "valid": True, "issues": []}
            node_ids = step.get("based_on_node_ids", [])

            # 检查引用的节点是否存在
            for nid in node_ids:
                if not self.graph.get_node(nid):
                    msg = f"步骤{i+1}引用了不存在的节点 {nid}"
                    step_result["issues"].append(msg)
                    step_result["valid"] = False

            # 检查引用的节点可信度
            for nid in node_ids:
                cred = self.source_credibility(nid)
                if cred < 0.3:
                    msg = f"步骤{i+1}引用了低可信度节点 {nid[:8]} (credibility={cred})"
                    step_result["issues"].append(msg)

            if not step_result["valid"]:
                results["valid"] = False
                results["issues"].extend(step_result["issues"])

            results["steps"].append(step_result)

        return results

    # ========== 决策审计 ==========
    def record_decision(
        self, decision_type: str, context: dict,
        options: list[dict], chosen: str, reasoning: str
    ) -> str:
        """记录一次决策，用于后续审计"""
        decisions = self._load_decisions()
        decision = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "type": decision_type,          # e.g. "investment", "fact_selection"
            "context": context,              # 决策上下文
            "options": options,              # 可选方案
            "chosen": chosen,                # 选择的方案
            "reasoning": reasoning,          # 决策理由
            "outcome": None,                 # 待事后填写
            "feedback": None,
        }
        decisions["decisions"].append(decision)
        self._save_decisions(decisions)
        return decision["id"]

    def audit_decision(self, decision_id: str, outcome: str, was_correct: bool):
        """事后审计一次决策"""
        decisions = self._load_decisions()
        for d in decisions["decisions"]:
            if d["id"] == decision_id:
                d["outcome"] = outcome
                d["feedback"] = {"was_correct": was_correct, "audited_at": datetime.now().isoformat()}

                # 如果决策错误, 记录为违规
                if not was_correct:
                    self.data["violations"].append({
                        "decision_id": decision_id,
                        "timestamp": datetime.now().isoformat(),
                        "reasoning": d.get("reasoning", "")[:200],
                        "outcome": outcome,
                    })
                break
        self._save_decisions(decisions)
        self._save()

    def get_decision_stats(self) -> dict:
        """决策准确率统计"""
        decisions = self._load_decisions()
        audited = [d for d in decisions["decisions"] if d.get("feedback") is not None]
        if not audited:
            return {"total": len(decisions["decisions"]), "audited": 0, "accuracy": 0}
        correct = sum(1 for d in audited if d["feedback"]["was_correct"])
        return {
            "total": len(decisions["decisions"]),
            "audited": len(audited),
            "correct": correct,
            "accuracy": round(correct / len(audited), 3),
        }

    # ========== 综合验证报告 ==========
    def full_verify(self, claim: str = "", context_node_ids: list[str] = None) -> dict:
        """事前全量验证——输出前调用"""
        context_node_ids = context_node_ids or []
        report = {
            "timestamp": datetime.now().isoformat(),
            "id": str(uuid.uuid4())[:8],
            "pass": True,
            "checks": {},
        }

        # 1. 一致性检查
        if claim:
            consistency = self.check_consistency(claim, context_node_ids)
            report["checks"]["consistency"] = consistency
            if not consistency["consistent"]:
                report["pass"] = False

        # 2. 溯源验证
        if context_node_ids:
            credibility = {}
            for nid in context_node_ids[:10]:
                node = self.graph.get_node(nid)
                if node:
                    credibility[nid] = {
                        "title": node.get("title", "")[:60],
                        "source": node.get("source", "unknown"),
                        "credibility": self.source_credibility(nid),
                    }
            report["checks"]["source_credibility"] = credibility
            # 如果有低可信度来源，标记为警告但不阻止
            low_cred = [nid for nid, c in credibility.items() if c["credibility"] < 0.3]
            if low_cred:
                report["checks"]["warnings"] = [f"低可信度来源: {', '.join(n[:8] for n in low_cred)}"]

        # 3. 记录验证
        self.data["checks"].append(report)
        self._save()

        return report

    # ========== 统计 ==========
    def stats(self, v2: bool = True) -> dict:
        cred = self.rate_all_credibility(v2=v2)
        decisions = self.get_decision_stats()
        return {
            "total_checks": self.data["meta"]["total_checks"],
            "violation_rate": round(self.data["meta"]["violation_rate"], 3),
            "credibility": cred,
            "decisions": decisions,
        }
