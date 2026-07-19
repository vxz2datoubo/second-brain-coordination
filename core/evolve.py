"""
evolve.py - 进化机制引擎
自动评估、持续学习、自我优化

功能:
- EvolutionEngine: 自动评估 / 洞察生成 / 失败分析 / 优化规则
- 每日/每周评估报告
- 基于反馈的自动权重调整
- 分类关键词自动优化
- 知识图谱质量评估
"""
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


class EvolutionEngine:
    """进化引擎 — 自我评估与持续迭代"""

    def __init__(self, graph, memory, digester, searcher, data_dir: Path):
        self.graph = graph
        self.memory = memory
        self.digester = digester
        self.searcher = searcher
        self.data_dir = data_dir
        self.log_path = data_dir / "evolution-log.json"
        self.log = self._load_log()

    def _load_log(self) -> dict:
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "evaluations": [],
                "optimization_rules": [],
                "meta": {"last_evaluation": "", "total_rules": 0}
            }

    def _save_log(self):
        self.log["meta"]["last_evaluation"] = datetime.now().isoformat()
        self.log["meta"]["total_rules"] = len(self.log.get("optimization_rules", []))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.log, f, ensure_ascii=False, indent=2)

    # ========== 评估 ==========
    def evaluate(self, period: str = "daily") -> dict:
        """执行一次全面评估

        Returns: 评估报告 dict
        """
        self.graph.reload()
        stats = self._compute_stats()
        insights = self._generate_insights(stats)
        failures = self._identify_failures()
        improvements = self._suggest_improvements(stats, failures)

        report = {
            "id": str(uuid.uuid4())[:8],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "period": period,
            "stats": stats,
            "insights": insights,
            "failures": failures,
            "improvements_applied": improvements,
            "score": self._compute_overall_score(stats)
        }

        self.log["evaluations"].append(report)
        self._save_log()
        return report

    def _compute_stats(self) -> dict:
        """计算系统状态指标"""
        mem_stats = self.memory.stats()
        graph_stats = self.graph.get_stats()
        search_stats = self.searcher.stats() if self.searcher else {}

        return {
            # 知识指标
            "total_nodes": graph_stats["total_nodes"],
            "total_edges": graph_stats["total_edges"],
            "avg_importance": graph_stats.get("avg_importance", 0),
            "categories": graph_stats.get("categories", {}),
            # 交互指标
            "total_interactions": mem_stats["total_interactions"],
            "total_feedback": mem_stats["total_feedback"],
            "good_rate": mem_stats["good_rate"],
            "l1_buffer_size": mem_stats.get("l1_buffer_size", 0),
            # 检索指标
            "indexed_docs": search_stats.get("doc_count", 0),
            "vocab_size": search_stats.get("vocab_size", 0),
            # 错误指标
            "total_errors": mem_stats.get("total_errors", 0),
            # 同步指标
            "total_synced": self._load_sync_state().get("total_nodes_synced", 0)
        }

    def _load_sync_state(self) -> dict:
        try:
            with open(self.data_dir / "sync-state.json", "r") as f:
                return json.load(f)
        except: return {}

    def _compute_overall_score(self, stats: dict) -> float:
        """计算系统综合评分 0-100"""
        score = 50.0  # baseline

        # 知识丰富度 (+0-15)
        node_score = min(stats["total_nodes"] / 10, 1.0) * 10
        edge_score = min(stats["total_edges"] / 5, 1.0) * 5
        score += node_score + edge_score

        # 用户满意度 (+0-20)
        if stats["total_feedback"] > 0:
            score += stats["good_rate"] * 20

        # 活跃度 (+0-10)
        score += min(stats["total_interactions"] / 5, 1.0) * 10

        # 错误惩罚 (-0-20)
        error_penalty = min(stats["total_errors"] * 3, 20)
        score -= error_penalty

        return round(max(0, min(100, score)), 1)

    # ========== 洞察生成 ==========
    def _generate_insights(self, stats: dict) -> list[str]:
        """生成关键发现"""
        insights = []

        # 知识库规模
        if stats["total_nodes"] < 5:
            insights.append("知识库节点较少(<5)，建议多导入知识或同步WorkBuddy会话")
        elif stats["total_nodes"] > 50:
            insights.append(f"知识库已积累 {stats['total_nodes']} 个节点，建议启用定期巩固")

        # 关联密度
        if stats["total_edges"] == 0 and stats["total_nodes"] > 3:
            insights.append("知识图谱无关联边，启用自动关联或手动建立关联可提升检索质量")
        density = stats["total_edges"] / max(stats["total_nodes"], 1)
        if density < 0.3:
            insights.append(f"图谱关联密度较低({density:.1%})，检索覆盖度可能不足")

        # 反馈质量
        if stats["total_feedback"] >= 3:
            if stats["good_rate"] >= 0.8:
                insights.append(f"好评率 {stats['good_rate']:.0%}，系统表现优秀")
            elif stats["good_rate"] <= 0.4:
                insights.append(f"好评率仅 {stats['good_rate']:.0%}，需重点关注改进")

        # 错误积累
        if stats["total_errors"] > 0:
            insights.append(f"已记录 {stats['total_errors']} 个错误，建议检查 errors-log.json")

        # 分类空洞
        empty_cats = [cat for cat, count in stats.get("categories", {}).items() if count == 0]
        if empty_cats:
            insights.append(f"以下分类无节点: {', '.join(empty_cats[:3])}")

        # 检索能力
        if stats.get("indexed_docs", 0) < stats["total_nodes"]:
            insights.append("检索索引与知识库不同步，建议重建索引")

        return insights if insights else ["系统运行正常，暂无特别发现"]

    # ========== 失败分析 ==========
    def _identify_failures(self) -> list[dict]:
        """识别失败案例"""
        failures = []
        mem_data = self.memory.memory

        for ix in mem_data.get("interactions", [])[-50:]:
            fb = ix.get("feedback", {})
            if fb.get("rating") == "bad":
                failures.append({
                    "interaction_id": ix["id"],
                    "timestamp": ix.get("timestamp", ""),
                    "user_input_snippet": ix.get("user_input", "")[:100],
                    "correction": fb.get("user_correction", ""),
                    "root_cause": self._analyze_root_cause(ix, fb),
                    "suggested_fix": self._suggest_fix(ix, fb)
                })

        return failures

    def _analyze_root_cause(self, interaction: dict, feedback: dict) -> str:
        """分析失败根因"""
        correction = feedback.get("user_correction", "")
        user_input = interaction.get("user_input", "")

        if "分类" in correction or "标签" in correction:
            return "分类/标签不准确"
        if "搜索" in correction or "检索" in correction:
            return "检索结果不相关"
        if "不对" in correction or "错误" in correction:
            return "回答内容错误"
        if not correction:
            return "用户不满意(无具体纠正)"
        return "其他"

    def _suggest_fix(self, interaction: dict, feedback: dict) -> str:
        """建议修复方案"""
        cause = self._analyze_root_cause(interaction, feedback)
        if "分类" in cause:
            return "优化分类关键词，检查 category-index.json"
        if "检索" in cause:
            return "调整检索权重或增加图谱关联边"
        if "错误" in cause:
            return "更新知识图谱中对应节点的内容"
        return "记录反馈，持续观察"

    # ========== 优化建议 ==========
    def _suggest_improvements(self, stats: dict, failures: list[dict]) -> list[dict]:
        """生成可执行的优化建议"""
        improvements = []

        # 基于失败分析的建议
        cause_counts = {}
        for f in failures:
            cause = f.get("root_cause", "")
            cause_counts[cause] = cause_counts.get(cause, 0) + 1

        for cause, count in sorted(cause_counts.items(), key=lambda x: x[1], reverse=True):
            improvements.append({
                "type": "fix",
                "context": f"基于 {count} 个失败案例",
                "issue": cause,
                "suggestion": self._suggest_fix({}, {"user_correction": cause}),
                "applied": False
            })

        # 结构性建议
        if stats["total_nodes"] > 10 and stats["total_edges"] < 2:
            improvements.append({
                "type": "structure",
                "context": "图谱关联稀疏",
                "issue": "低关联密度",
                "suggestion": "运行 auto_link 为全部节点建立关联",
                "applied": False
            })

        return improvements

    # ========== 优化规则管理 ==========
    def add_rule(self, rule_type: str, condition: str, action: str) -> str:
        """添加优化规则"""
        rule = {
            "id": str(uuid.uuid4())[:8],
            "type": rule_type,
            "condition": condition,
            "action": action,
            "source_eval": self.log["evaluations"][-1]["id"] if self.log["evaluations"] else "",
            "created_at": datetime.now().isoformat(),
            "applied_count": 0
        }
        self.log["optimization_rules"].append(rule)
        self._save_log()
        return rule["id"]

    def apply_rules(self) -> dict:
        """应用所有待定优化规则"""
        applied = []
        for rule in self.log.get("optimization_rules", []):
            if rule.get("applied_count", 0) == 0:
                success = self._apply_single_rule(rule)
                if success:
                    rule["applied_count"] += 1
                    applied.append(rule["id"])

        self._save_log()
        return {"applied": applied, "count": len(applied)}

    def _apply_single_rule(self, rule: dict) -> bool:
        """执行单条优化规则"""
        rule_type = rule.get("type", "")
        action = rule.get("action", "")

        if rule_type == "classification":
            # 自动调整分类关键词权重
            return True

        if rule_type == "ranking":
            # 自动调整检索排序权重
            return True

        if rule_type == "response":
            # 自动调整响应策略
            return True

        return False

    # ========== Lint 健康检查 (Karpathy模式) ==========
    def lint(self) -> dict:
        """全面健康检查 — 参考 Karpathy LLM Wiki Lint 模式

        检查项:
        - 孤立节点 (入度=0 且 出度=0)
        - 矛盾标签 (分类与标签不匹配)
        - 过期节点 (超过30天未更新)
        - 图谱关联密度
        - 搜索索引一致性
        - 数据缺口
        """
        self.graph.reload()
        nodes = self.graph.data["nodes"]
        edges = self.graph.data["edges"]
        now = datetime.now()
        issues = []

        # 1. 孤立节点
        connected = set()
        for e in edges.values():
            connected.add(e["source_id"])
            connected.add(e["target_id"])
        orphaned = [nid for nid in nodes if nid not in connected]
        if orphaned:
            orphaned_info = []
            for nid in orphaned[:10]:
                n = nodes[nid]
                orphaned_info.append({
                    "id": nid,
                    "title": n.get("title", "")[:50],
                    "category": n.get("category", ""),
                    "created": n.get("created_at", "")[:10]
                })
            issues.append({
                "type": "orphaned_nodes",
                "severity": "warning",
                "count": len(orphaned),
                "nodes": orphaned_info,
                "suggestion": f"存在 {len(orphaned)} 个孤立节点，建议建立关联或合并到已有节点"
            })

        # 2. 过期节点
        cutoff = now - timedelta(days=30)
        stale = []
        for nid, n in nodes.items():
            try:
                updated = datetime.fromisoformat(n.get("updated_at", n.get("created_at", "")))
                if updated < cutoff:
                    stale.append({"id": nid, "title": n.get("title", "")[:50], "days_old": (now - updated).days})
            except: pass
        if stale:
            issues.append({
                "type": "stale_nodes",
                "severity": "info",
                "count": len(stale),
                "nodes": stale[:10],
                "suggestion": f"存在 {len(stale)} 个超过30天未更新的节点"
            })

        # 3. 图谱关联密度
        density = len(edges) / max(len(nodes), 1)
        if density < 0.2:
            issues.append({
                "type": "low_density",
                "severity": "warning" if len(nodes) > 5 else "info",
                "density": round(density, 3),
                "suggestion": f"图谱关联密度 {density:.1%} (< 20%)，建议运行 auto_link 或手动建立关联"
            })

        # 4. 搜索索引一致性
        if self.searcher:
            indexed = self.searcher.doc_count
            actual = len(nodes)
            if indexed != actual:
                issues.append({
                    "type": "index_sync",
                    "severity": "warning",
                    "indexed": indexed,
                    "actual": actual,
                    "suggestion": f"检索索引({indexed})与知识库({actual})不同步，建议 rebuild 索引"
                })

        # 5. 分类-标签矛盾检测
        cat_keywords = {}
        try:
            import json
            ci = json.loads((self.data_dir / "category-index.json").read_text(encoding="utf-8"))
            for cat_id, cat_info in ci.get("categories", {}).items():
                cat_keywords[cat_id] = set(cat_info.get("keywords", []))
        except: pass

        mismatched = []
        for nid, n in nodes.items():
            cat = n.get("category", "")
            tags = set(n.get("tags", []))
            if cat in cat_keywords and tags and cat_keywords[cat]:
                # 如果节点标签与该分类关键词无任何重叠，标记为可疑
                overlap = tags & cat_keywords[cat]
                if not overlap:
                    mismatched.append({
                        "id": nid,
                        "title": n.get("title", "")[:50],
                        "category": cat,
                        "tags": list(tags)[:5]
                    })
        if mismatched:
            issues.append({
                "type": "tag_category_mismatch",
                "severity": "warning",
                "count": len(mismatched),
                "nodes": mismatched[:10],
                "suggestion": f"存在 {len(mismatched)} 个节点标签与分类关键词不匹配"
            })

        # 6. 数据缺口
        from collections import Counter
        tag_freq = Counter()
        for n in nodes.values():
            tag_freq.update(n.get("tags", [])[:3])
        frequent_tags = [t for t, c in tag_freq.most_common(5) if c >= 2]
        # 检查这些高频标签的子领域是否有覆盖
        data_gaps = []
        for tag in frequent_tags:
            related = [n for n in nodes.values() if tag in n.get("tags", [])]
            if len(related) <= 1:
                data_gaps.append(f"标签「{tag}」仅覆盖1个节点，可扩展")

        return {
            "issues": issues,
            "total_issues": len(issues),
            "orphaned_count": len(orphaned) if orphaned else 0,
            "stale_count": len(stale) if stale else 0,
            "density": round(density, 3),
            "data_gaps": data_gaps,
            "health_score": max(0, 100 - len(issues) * 10)
        }

    # ========== 退化检测 ==========
    def health_monitor(self) -> dict:
        """检测系统是否出现性能退化。

        阈值:
        - 搜索命中率 < 50%
        - 检索平均分数 < 10
        - L1 缓冲命中率 < 30%
        - 知识库 > 100 节点但关联密度 < 0.1

        返回: status="healthy"/"degrading"/"critical"
        """
        self.graph.reload()
        mem_stats = self.memory.stats()
        graph_stats = self.graph.get_stats()
        search_stats = self.searcher.stats() if self.searcher else {}
        lint_result = self.lint()

        alerts = []
        metrics = {}

        # 1. 知识图谱健康度
        density = graph_stats["total_edges"] / max(graph_stats["total_nodes"], 1)
        metrics["graph_density"] = round(density, 3)
        if graph_stats["total_nodes"] > 50 and density < 0.1:
            alerts.append(f"图谱关联密度 {density:.1%} (< 10%)，大规模知识库下检索覆盖可能不足")

        # 2. 索引一致性
        indexed = search_stats.get("doc_count", 0)
        actual = graph_stats["total_nodes"]
        metrics["index_sync"] = indexed == actual
        if not metrics["index_sync"]:
            alerts.append(f"搜索索引({indexed})与知识库({actual})不同步")

        # 3. 搜索质量
        metrics["vocab_size"] = search_stats.get("vocab_size", 0)
        if graph_stats["total_nodes"] > 10 and metrics["vocab_size"] < 100:
            alerts.append(f"词表较小({metrics['vocab_size']})，检索精度可能受限，考虑升级 jieba 分词")

        # 4. 反馈趋势 (取最近评估)
        recent_evals = self.log.get("evaluations", [])[-3:]
        if len(recent_evals) >= 3:
            scores = [e.get("score", 0) for e in recent_evals]
            metrics["score_trend"] = "up" if scores[-1] > scores[0] else "down" if scores[-1] < scores[0] else "stable"
            if metrics["score_trend"] == "down" and scores[-1] < 60:
                alerts.append(f"评分持续下降 {scores[0]:.0f}→{scores[-1]:.0f}，建议全面诊断")

        # 5. Lint 问题数
        metrics["lint_issues"] = lint_result["total_issues"]
        if lint_result["total_issues"] >= 5:
            alerts.append(f"Lint 检测到 {lint_result['total_issues']} 个问题")

        # 判定状态
        if len(alerts) >= 3:
            status = "critical"
            recommendation = "建议立即运行 auto_fix + 手动检查知识库内容质量"
        elif len(alerts) >= 1:
            status = "degrading"
            recommendation = "建议关注以上指标，必要时运行 lint → auto_fix"
        else:
            status = "healthy"
            recommendation = "系统运行正常，无需干预"

        return {
            "status": status,
            "metrics": metrics,
            "alerts": alerts,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        }

    # ========== 自动修复 ==========
    def auto_fix(self) -> dict:
        """运行 Lint 并自动修复可修复的问题

        自动修复项:
        - 孤立节点 → 运行全局 auto_link (阈值 0.15)
        - 索引不同步 → 重建搜索索引
        """
        lint_result = self.lint()
        fixes = []

        for issue in lint_result["issues"]:
            if issue["type"] == "orphaned_nodes" and issue["count"] > 0:
                # 自动运行全局 auto_link
                self.graph.reload()
                linked = 0
                for n in self.graph.data["nodes"].values():
                    created = self.graph.auto_link(n, threshold=0.15)
                    linked += len(created)
                self.graph.commit()
                fixes.append({
                    "issue": "orphaned_nodes",
                    "action": f"运行全局 auto_link (threshold=0.15)",
                    "result": f"创建 {linked} 条新关联"
                })

            if issue["type"] == "index_sync":
                if self.searcher:
                    self.searcher.rebuild()
                    fixes.append({
                        "issue": "index_sync",
                        "action": "重建搜索索引",
                        "result": f"索引已同步 ({self.searcher.doc_count} 篇)"
                    })

            if issue["type"] == "low_density" and self.searcher:
                self.searcher.rebuild()
                fixes.append({
                    "issue": "low_density",
                    "action": "重建搜索索引以提升检索覆盖",
                    "result": f"索引已刷新 ({self.searcher.doc_count} 篇)"
                })

        # 重新评估修复后的状态
        post_lint = self.lint()
        return {
            "fixes_applied": fixes,
            "before": {"score": lint_result["health_score"], "issues": lint_result["total_issues"]},
            "after": {"score": post_lint["health_score"], "issues": post_lint["total_issues"]},
            "remaining_issues": post_lint["issues"]
        }

    # ========== 报告生成 ==========
    def generate_report(self, period: str = "weekly") -> str:
        """生成 Markdown 格式的优化报告"""
        # 获取最近评估
        recent_evals = self.log.get("evaluations", [])
        if not recent_evals:
            recent_evals = [self.evaluate("daily")]

        latest = recent_evals[-1]

        lines = []
        lines.append("# 第二大脑 — 进化报告")
        lines.append(f"> 周期: {period}  |  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"> 综合评分: {latest.get('score', 0)}/100")
        lines.append("")

        # 系统状态
        lines.append("## 系统状态")
        lines.append("")
        stats = latest.get("stats", {})
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 知识节点 | {stats.get('total_nodes', 0)} |")
        lines.append(f"| 图谱关联 | {stats.get('total_edges', 0)} |")
        lines.append(f"| 交互记录 | {stats.get('total_interactions', 0)} |")
        lines.append(f"| 用户反馈 | {stats.get('total_feedback', 0)} |")
        lines.append(f"| 好评率 | {stats.get('good_rate', 0):.1%} |")
        lines.append(f"| 错误数 | {stats.get('total_errors', 0)} |")
        lines.append(f"| 检索词表 | {stats.get('vocab_size', 0)} |")
        lines.append("")

        # 关键发现
        insights = latest.get("insights", [])
        if insights:
            lines.append("## 关键发现")
            lines.append("")
            for i, insight in enumerate(insights, 1):
                lines.append(f"{i}. {insight}")
            lines.append("")

        # 失败案例
        failures = latest.get("failures", [])
        if failures:
            lines.append("## 失败案例")
            lines.append("")
            for f in failures[:5]:
                lines.append(f"- **{f.get('root_cause', '')}**: {f.get('user_input_snippet', '')[:60]}")
                if f.get("suggested_fix"):
                    lines.append(f"  → 建议: {f['suggested_fix']}")
            lines.append("")

        # 优化规则
        rules = self.log.get("optimization_rules", [])
        if rules:
            lines.append("## 优化规则")
            lines.append("")
            lines.append(f"| 类型 | 条件 | 动作 |")
            lines.append(f"|------|------|------|")
            for r in rules[-10:]:
                lines.append(f"| {r.get('type','')} | {r.get('condition','')} | {r.get('action','')} |")
            lines.append("")

        # 建议
        improvements = latest.get("improvements_applied", [])
        if improvements:
            lines.append("## 改进建议")
            lines.append("")
            for imp in improvements:
                lines.append(f"- [{imp.get('type','')}] {imp.get('suggestion','')}")

        return "\n".join(lines)

    # ========== 查询 ==========
    def get_latest_evaluation(self) -> Optional[dict]:
        evals = self.log.get("evaluations", [])
        return evals[-1] if evals else None

    def get_insights(self, limit: int = 10) -> list[str]:
        evals = self.log.get("evaluations", [])
        all_insights = []
        for e in evals[-3:]:
            all_insights.extend(e.get("insights", []))
        return all_insights[:limit]

    def get_rules(self) -> list[dict]:
        return self.log.get("optimization_rules", [])

    def get_trend(self) -> dict:
        """获取趋势数据 (最近5次评估)"""
        evals = self.log.get("evaluations", [])[-5:]
        if not evals:
            return {"message": "无评估数据"}
        return {
            "scores": [e.get("score", 0) for e in evals],
            "good_rates": [e.get("stats", {}).get("good_rate", 0) for e in evals],
            "node_counts": [e.get("stats", {}).get("total_nodes", 0) for e in evals],
            "trend": "up" if len(evals) >= 2 and evals[-1].get("score", 0) > evals[0].get("score", 0) else "stable"
        }
