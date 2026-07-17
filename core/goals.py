"""
goals.py — 长期目标与未来推演引擎 (Phase 5)

蓝图 §5.2 Goals & Future Simulation:
- GoalRecord: 嵌套层次 life > yearly > quarterly > monthly > weekly > daily
- FuturePath: 多路径推演 (乐观/悲观/最可能/黑天鹅)
- WeekPlan: 周计划快照
- 复盘闭环: Goal→Milestone→Task→Review→Reflection→Adjust

设计原则:
- 零外部依赖 (纯 Python + stdlib)
- 按 blueprint 层次结构构建: GoalTree (parent/child)
- Review 自动触发: review_interval_days + last_reviewed_at 比较
"""
from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from brain_core.contracts import (
    GoalRecord, FuturePath, WeekPlan, GOAL_STATUS_FLOW,
    new_id, now_iso, to_dict, from_dict,
)
# Backward compat for non-brain_core import
try:
    from contracts import GoalRecord as _GR, FuturePath as _FP, WeekPlan as _WP, GOAL_STATUS_FLOW as _GSF, new_id as _ni, now_iso as _ni2, to_dict as _td, from_dict as _fd
except ImportError:
    pass


class GoalEngine:
    """长期目标管理系统 — Phase 5 核心

    核心概念:
    - Goal Tree: 嵌套层次结构 (life → yearly → quarterly → monthly → weekly → daily)
    - Milestones: 里程碑检查点
    - Future Simulation: 多路径推演 (5种路径类型)
    - Weekly Planning: 周计划生成
    - Auto Review: 基于 review_interval_days 自动触发
    """

    GOAL_TYPES = ["daily", "weekly", "monthly", "quarterly", "yearly", "life"]
    TIME_HORIZONS = ["short", "medium", "long", "lifelong"]
    PATH_TYPES = ["optimistic", "pessimistic", "most_likely", "wildcard", "baseline"]
    PRIORITIES = ["low", "medium", "high", "critical"]

    def __init__(self, data_dir: Path, graph=None, memory=None, tasks=None, events=None):
        self.data_dir = data_dir
        self.graph = graph
        self.memory = memory
        self.tasks = tasks        # TaskEngine ref for cross-linking
        self.events = events      # EventEngine ref for conflict awareness
        self.path = data_dir / "goals_state.json"
        self.state = self._load()

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self._default_state()

    def _default_state(self) -> dict:
        return {
            "goals": {},           # goal_id → GoalRecord as dict
            "future_paths": {},    # path_id → FuturePath as dict
            "week_plans": {},      # week_start → WeekPlan as dict
            "goal_tree": {},       # parent_goal_id → [child_goal_ids]
            "reviews_due": [],     # goal_ids needing review
            "stats": {
                "total_goals": 0,
                "active_goals": 0,
                "achieved_goals": 0,
                "total_paths": 0,
                "total_plans": 0,
            },
        }

    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    # ═══════════════════════════════════════════
    # CRUD: Goals
    # ═══════════════════════════════════════════

    def create_goal(self, title: str, goal_type: str = "monthly",
                    description: str = "", parent_goal_id: str = "",
                    target_date: str = "", priority: str = "medium",
                    success_criteria: list[str] = None,
                    motivation: str = "", time_horizon: str = "",
                    energy_required: str = "medium",
                    review_interval_days: int = 7) -> dict:
        """创建目标

        Args:
            title: 目标标题
            goal_type: daily|weekly|monthly|quarterly|yearly|life
            description: 详细描述
            parent_goal_id: 父目标ID (用于嵌套)
            target_date: 目标完成日期 (ISO date)
            priority: low|medium|high|critical
            success_criteria: 可量化成功标准
            motivation: 为什么这个目标重要
            time_horizon: 自动推断，可覆盖
            energy_required: 预估精力
            review_interval_days: 复盘间隔
        """
        if goal_type not in self.GOAL_TYPES:
            return {"error": f"goal_type must be one of {self.GOAL_TYPES}"}
        if priority not in self.PRIORITIES:
            return {"error": f"priority must be one of {self.PRIORITIES}"}

        # Auto-infer time_horizon
        if not time_horizon:
            horizon_map = {
                "daily": "short", "weekly": "short", "monthly": "medium",
                "quarterly": "medium", "yearly": "long", "life": "lifelong",
            }
            time_horizon = horizon_map.get(goal_type, "medium")

        goal = GoalRecord(
            id=new_id("goal"),
            title=title,
            description=description,
            goal_type=goal_type,
            time_horizon=time_horizon,
            parent_goal_id=parent_goal_id,
            target_date=target_date,
            priority=priority,
            success_criteria=success_criteria or [],
            motivation=motivation,
            energy_required=energy_required,
            review_interval_days=review_interval_days,
            status="dreaming",
            next_review_at=(datetime.now(timezone.utc) + timedelta(days=review_interval_days)).isoformat(),
        )

        self.state["goals"][goal.id] = to_dict(goal)

        # Register in goal tree
        if parent_goal_id and parent_goal_id in self.state["goals"]:
            self.state["goal_tree"].setdefault(parent_goal_id, []).append(goal.id)
            # Update parent's sub_goal_ids
            parent = self.state["goals"][parent_goal_id]
            parent["sub_goal_ids"].append(goal.id)

        self.state["stats"]["total_goals"] += 1
        self.state["stats"]["active_goals"] += 1
        self._save()
        return to_dict(goal)

    def update_goal(self, goal_id: str, **updates) -> dict:
        """更新目标字段"""
        if goal_id not in self.state["goals"]:
            return {"error": f"Goal {goal_id} not found"}

        goal = self.state["goals"][goal_id]
        valid_fields = {f for f in [
            "title", "description", "goal_type", "time_horizon", "target_date",
            "priority", "status", "progress", "motivation", "energy_required",
            "review_interval_days", "blockers", "risk_factors", "tags", "metadata",
        ]}

        for k, v in updates.items():
            if k in valid_fields:
                goal[k] = v
        goal["updated_at"] = now_iso()

        self.state["goals"][goal_id] = goal
        self._save()
        return goal

    def transition_goal(self, goal_id: str, new_status: str) -> dict:
        """推进目标状态 (GOAL_STATUS_FLOW 约束)"""
        if goal_id not in self.state["goals"]:
            return {"error": f"Goal {goal_id} not found"}

        goal = self.state["goals"][goal_id]
        current = goal.get("status", "dreaming")
        allowed = GOAL_STATUS_FLOW.get(current, [])
        if new_status not in allowed:
            return {"error": f"Invalid transition: {current} → {new_status}. Allowed: {allowed}"}

        goal["status"] = new_status
        now = now_iso()

        if new_status == "in_progress" and not goal.get("started_at"):
            goal["started_at"] = now
        elif new_status in ("achieved", "archived", "abandoned"):
            # Update stats
            self.state["stats"]["active_goals"] -= 1
            if new_status == "achieved":
                self.state["stats"]["achieved_goals"] += 1

        goal["updated_at"] = now
        self._save()
        return goal

    def add_milestone(self, goal_id: str, text: str, target_date: str = "", achieved: bool = False) -> dict:
        """为目标添加里程碑"""
        if goal_id not in self.state["goals"]:
            return {"error": f"Goal {goal_id} not found"}

        goal = self.state["goals"][goal_id]
        milestone = {
            "date": target_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "text": text,
            "achieved": achieved,
        }
        goal["milestones"].append(milestone)

        # Update progress
        total = len(goal["milestones"])
        done = sum(1 for m in goal["milestones"] if m["achieved"])
        goal["progress"] = round(done / total, 2) if total > 0 else 0.0

        self._save()
        return goal

    def review_goal(self, goal_id: str, progress_rating: int = 3, reflection: str = "") -> dict:
        """复盘目标 — 更新进度评估 + 反思"""
        if goal_id not in self.state["goals"]:
            return {"error": f"Goal {goal_id} not found"}

        goal = self.state["goals"][goal_id]
        progress_rating = max(1, min(5, progress_rating))

        review = {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "text": reflection,
            "progress_rating": progress_rating,
        }
        goal["reflections"].append(review)
        goal["last_reviewed_at"] = now_iso()
        goal["next_review_at"] = (datetime.now(timezone.utc) +
            timedelta(days=goal.get("review_interval_days", 7))).isoformat()

        # Auto-adjust status if needed
        if progress_rating >= 4 and goal["status"] not in ("achieved", "archived"):
            if all(m.get("achieved") for m in goal.get("milestones", [])):
                goal["status"] = "achieved"
                self.state["stats"]["active_goals"] -= 1
                self.state["stats"]["achieved_goals"] += 1

        self._save()
        return goal

    def delete_goal(self, goal_id: str) -> dict:
        """删除目标 (级联删除子目标)"""
        if goal_id not in self.state["goals"]:
            return {"error": f"Goal {goal_id} not found"}

        # Cascade delete children
        child_ids = self.state["goal_tree"].get(goal_id, [])
        for cid in child_ids:
            if cid in self.state["goals"]:
                del self.state["goals"][cid]
                self.state["stats"]["total_goals"] -= 1
                if self.state["goals"][cid].get("status") not in ("achieved", "archived", "abandoned"):
                    self.state["stats"]["active_goals"] -= 1

        # Remove from parent
        parent_id = self.state["goals"][goal_id].get("parent_goal_id")
        if parent_id and parent_id in self.state["goals"]:
            parent = self.state["goals"][parent_id]
            parent["sub_goal_ids"] = [x for x in parent.get("sub_goal_ids", []) if x != goal_id]

        del self.state["goals"][goal_id]
        if goal_id in self.state["goal_tree"]:
            del self.state["goal_tree"][goal_id]

        self.state["stats"]["total_goals"] -= 1
        self.state["stats"]["active_goals"] -= 1
        self._save()
        return {"success": True, "deleted": goal_id, "cascade_deleted": len(child_ids)}

    # ═══════════════════════════════════════════
    # Query
    # ═══════════════════════════════════════════

    def get_goal(self, goal_id: str) -> dict | None:
        return self.state["goals"].get(goal_id)

    def list_goals(self, goal_type: str = "", status: str = "",
                   parent_goal_id: str = "", time_horizon: str = "",
                   limit: int = 50) -> list[dict]:
        """列出目标，支持多维度筛选"""
        goals = list(self.state["goals"].values())

        if goal_type:
            goals = [g for g in goals if g.get("goal_type") == goal_type]
        if status:
            goals = [g for g in goals if g.get("status") == status]
        if parent_goal_id:
            child_ids = set(self.state["goal_tree"].get(parent_goal_id, []))
            goals = [g for g in goals if g["id"] in child_ids]
        if time_horizon:
            goals = [g for g in goals if g.get("time_horizon") == time_horizon]

        # Sort: active first, then by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        goals.sort(key=lambda g: (
            0 if g.get("status") not in ("achieved", "archived", "abandoned") else 1,
            priority_order.get(g.get("priority", "medium"), 2),
        ))
        return goals[:limit]

    def get_goal_tree(self, root_goal_id: str = "") -> dict:
        """获取目标树 (嵌套结构)"""
        if not root_goal_id:
            # Find all root goals (no parent)
            all_ids = set(self.state["goals"].keys())
            child_ids = set()
            for children in self.state["goal_tree"].values():
                child_ids.update(children)
            root_ids = all_ids - child_ids
            return {"roots": [self._build_subtree(rid) for rid in root_ids]}

        return self._build_subtree(root_goal_id)

    def _build_subtree(self, goal_id: str) -> dict:
        goal = self.state["goals"].get(goal_id, {})
        result = {
            "id": goal.get("id", ""),
            "title": goal.get("title", ""),
            "goal_type": goal.get("goal_type", ""),
            "status": goal.get("status", ""),
            "progress": goal.get("progress", 0),
            "priority": goal.get("priority", "medium"),
            "children": [self._build_subtree(cid) for cid in self.state["goal_tree"].get(goal_id, [])],
        }
        return result

    def get_reviews_due(self) -> list[dict]:
        """获取需要复盘的 goal (next_review_at <= now)"""
        now = datetime.now(timezone.utc)
        due = []
        for g in self.state["goals"].values():
            nra = g.get("next_review_at", "")
            if nra and datetime.fromisoformat(nra) <= now and g.get("status") not in ("archived", "abandoned"):
                due.append(g)
        return due

    # ═══════════════════════════════════════════
    # Future Simulation
    # ═══════════════════════════════════════════

    def simulate_future(self, goal_id: str = "", description: str = "",
                        time_horizon_months: int = 6) -> dict:
        """为指定目标生成多路径推演

        生成 5 种路径:
        - optimistic: 一切顺利
        - pessimistic: 出问题了
        - most_likely: 最可能的中间路径
        - baseline: 不出意外
        - wildcard: 黑天鹅

        基于:
        - Goal 的 milestones/success_criteria/risk_factors
        - 历史成就率 (stats)
        - Events 冲突检测
        """
        goal = self.state["goals"].get(goal_id, {})
        title = goal.get("title", description or "未命名目标")
        milestones = goal.get("milestones", [])
        risks = goal.get("risk_factors", [])
        blockers = goal.get("blockers", [])

        base_date = datetime.now(timezone.utc)
        horizon_date = base_date + timedelta(days=time_horizon_months * 30)

        # Historical achievement rate
        total = self.state["stats"]["total_goals"] or 1
        achieved = self.state["stats"]["achieved_goals"]
        achievement_rate = achieved / total if total > 0 else 0.6

        paths = []

        for pt in self.PATH_TYPES:
            prob, conf = self._path_probability(pt, achievement_rate, len(blockers))
            path = FuturePath(
                path_type=pt,
                probability=round(prob, 2),
                confidence=round(conf, 2),
                description=self._describe_path(pt, title, milestones, risks),
                key_milestones=[m.get("text", "") for m in milestones[:5]],
                risk_events=risks[:5] + (["突发事件干扰"] if pt in ("pessimistic", "wildcard") else []),
                required_actions=self._required_actions(pt, blockers),
                early_signals=self._early_signals(pt, milestones),
                best_outcome=self._outcome_best(pt, title),
                worst_outcome=self._outcome_worst(pt, title, risks),
                expected_outcome=self._outcome_expected(pt, title, achievement_rate),
            )
            paths.append(to_dict(path))
            self.state["future_paths"][path.id] = to_dict(path)

        self.state["stats"]["total_paths"] += 5
        self._save()

        return {
            "goal_id": goal_id,
            "goal_title": title,
            "time_horizon_months": time_horizon_months,
            "horizon_date": horizon_date.strftime("%Y-%m-%d"),
            "achievement_rate": round(achievement_rate, 2),
            "paths": paths,
        }

    def _path_probability(self, path_type: str, achievement_rate: float, blocker_count: int) -> tuple[float, float]:
        """计算路径概率"""
        base = {
            "optimistic": (0.25, 0.4),
            "pessimistic": (0.15, 0.5),
            "most_likely": (0.45, 0.7),
            "baseline": (0.10, 0.8),
            "wildcard": (0.05, 0.2),
        }
        prob, conf = base[path_type]
        prob *= (0.7 + 0.3 * achievement_rate)
        prob *= (0.95 ** blocker_count)
        return prob, conf

    def _describe_path(self, pt: str, title: str, milestones: list, risks: list) -> str:
        desc = {
            "optimistic": f"一切超预期：{title} 比计划提前完成，{len(milestones)}个里程碑全部达成",
            "pessimistic": f"遇到阻碍：{title} 因{risks[0] if risks else '未预见的困难'}受阻，可能延迟或范围缩减",
            "most_likely": f"大概率路径：{title} 按部就班推进，{len(milestones)}个里程碑完成大部分",
            "baseline": f"基准路径：{title} 无意外、无惊喜，稳步完成",
            "wildcard": f"黑天鹅：{title} 因突发事件或外部变化发生根本性改变",
        }
        return desc.get(pt, "")

    def _required_actions(self, pt: str, blockers: list) -> list[str]:
        actions = {
            "optimistic": ["制定风险缓冲计划", "保持当前的执行节奏"],
            "pessimistic": ["识别关键依赖并建立backup方案", "降低目标复杂度或分阶段达成"],
            "most_likely": ["按优先级推进milestones", "定期复盘调整"],
            "baseline": ["做好时间管理", "保持节奏不变"],
            "wildcard": ["建立预警机制", "搭建灵活应变框架"],
        }
        result = actions.get(pt, [])
        if blockers:
            result.append(f"关键需要解决: {', '.join(blockers[:2])}")
        return result

    def _early_signals(self, pt: str, milestones: list) -> list[str]:
        signals = {
            "optimistic": ["所有milestones按时或提前达成", "额外资源或机会出现"],
            "pessimistic": ["连续2个milestones延迟", "关键资源无法获取"],
            "most_likely": ["milestones大部分达标", "无重大偏差"],
            "baseline": ["进度符合预期", "无意外发生"],
            "wildcard": ["外部环境突变", "核心假设被推翻"],
        }
        return signals.get(pt, [])

    def _outcome_best(self, pt: str, title: str) -> str:
        return f"完美达成 '{title}'，超越预期"

    def _outcome_worst(self, pt: str, title: str, risks: list) -> str:
        risk_text = risks[0] if risks else "意外事件"
        return f"'{title}' 因 {risk_text} 严重受阻或被迫放弃"

    def _outcome_expected(self, pt: str, title: str, rate: float) -> str:
        if pt == "most_likely":
            return f"'{title}' 大概率稳步完成 (成功率{rate:.0%})"
        return f"'{title}' {pt} 路径预判"

    def get_paths(self, goal_id: str = "") -> list[dict]:
        """获取目标相关的推演路径"""
        return list(self.state["future_paths"].values())  # 简化，后续可按goal关联

    # ═══════════════════════════════════════════
    # Weekly Planning
    # ═══════════════════════════════════════════

    def create_week_plan(self, week_start: str = "") -> dict:
        """生成周计划: 聚合当周目标+任务+关注领域"""
        if not week_start:
            # Find this Monday
            today = datetime.now(timezone.utc)
            week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

        # Gather active goals for this period
        active_goals = [g for g in self.state["goals"].values()
                       if g.get("status") not in ("archived", "abandoned", "achieved")]

        # Rank by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        active_goals.sort(key=lambda g: priority_order.get(g.get("priority", "medium"), 2))

        goal_ids = [g["id"] for g in active_goals[:10]]

        # Gather related tasks
        task_ids = []
        for g in active_goals[:10]:
            task_ids.extend(g.get("related_tasks", []))

        # Determine focus areas (top 3 priority types)
        type_counts = defaultdict(int)
        for g in active_goals:
            type_counts[g.get("goal_type", "monthly")] += 1
        focus_areas = [t for t, _ in sorted(type_counts.items(), key=lambda x: -x[1])[:3]]

        # Energy budget
        high_energy = sum(1 for g in active_goals if g.get("energy_required") == "high")
        energy_budget = "high" if high_energy >= 3 else ("medium" if high_energy >= 1 else "low")

        plan = WeekPlan(
            week_start=week_start,
            goal_ids=goal_ids,
            task_ids=task_ids[:20],  # Cap at 20
            focus_areas=focus_areas,
            energy_budget=energy_budget,
        )
        self.state["week_plans"][week_start] = to_dict(plan)
        self.state["stats"]["total_plans"] += 1
        self._save()

        return {
            "plan": to_dict(plan),
            "active_goals": len(active_goals),
            "focus_areas": focus_areas,
            "energy_budget": energy_budget,
            "goal_count": len(goal_ids),
            "task_count": len(task_ids),
        }

    def get_week_plan(self, week_start: str = "") -> dict:
        """获取周计划"""
        if not week_start:
            today = datetime.now(timezone.utc)
            week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        return self.state["week_plans"].get(week_start, {"note": "No plan yet", "week_start": week_start})

    # ═══════════════════════════════════════════
    # Analytics
    # ═══════════════════════════════════════════

    def stats(self) -> dict:
        """获取目标系统统计"""
        goals = self.state["goals"]
        by_type = defaultdict(int)
        by_status = defaultdict(int)
        by_priority = defaultdict(int)
        total_progress = 0
        active_count = 0

        for g in goals.values():
            by_type[g.get("goal_type", "unknown")] += 1
            by_status[g.get("status", "unknown")] += 1
            by_priority[g.get("priority", "medium")] += 1
            if g.get("status") not in ("archived", "abandoned"):
                total_progress += g.get("progress", 0)
                active_count += 1

        avg_progress = round(total_progress / active_count, 2) if active_count > 0 else 0

        return {
            **self.state["stats"],
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "by_priority": dict(by_priority),
            "avg_progress": avg_progress,
            "active_goals": active_count,
            "reviews_due": len(self.get_reviews_due()),
            "total_plans": len(self.state["week_plans"]),
            "total_paths": len(self.state["future_paths"]),
        }

    def health_check(self) -> dict:
        """健康检查: 是否有逾期目标/复盘未做/进度停滞"""
        now = datetime.now(timezone.utc)
        issues = []

        for g in self.state["goals"].values():
            gid = g["id"]
            title = g.get("title", "")

            # Overdue
            target = g.get("target_date", "")
            if target and g.get("status") in ("in_progress", "planned", "dreaming"):
                try:
                    td = datetime.fromisoformat(target)
                    if td < now:
                        issues.append({
                            "goal_id": gid, "title": title,
                            "type": "overdue", "severity": "high",
                            "detail": f"目标已逾期 ({target})",
                        })
                except:
                    pass

            # Review due
            nra = g.get("next_review_at", "")
            if nra:
                try:
                    nr = datetime.fromisoformat(nra)
                    if nr < now and g.get("status") not in ("archived", "abandoned"):
                        issues.append({
                            "goal_id": gid, "title": title,
                            "type": "review_due", "severity": "medium",
                            "detail": f"逾期 {max(1, (now - nr).days)} 天未复盘",
                        })
                except:
                    pass

            # Stagnant (no progress and no review in 14 days)
            lra = g.get("last_reviewed_at", g.get("created_at", ""))
            if lra and g.get("progress", 0) < 0.3 and g.get("status") not in ("archived", "abandoned", "achieved"):
                try:
                    lr = datetime.fromisoformat(lra)
                    if (now - lr).days >= 14:
                        issues.append({
                            "goal_id": gid, "title": title,
                            "type": "stagnant", "severity": "medium",
                            "detail": f"停滞 {(now - lr).days} 天",
                        })
                except:
                    pass

        return {
            "healthy": len(issues) == 0,
            "issue_count": len(issues),
            "issues": issues[:10],  # Cap at 10
        }
