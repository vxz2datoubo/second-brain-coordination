"""
tasks.py — 日常任务引擎 (Phase 3)
蓝图 §11: 自然语言创建任务、状态流转、提醒、任务复盘

设计原则:
- 任务核心由 SuperBrain 管理，MaiBot 只做对话入口
- 状态流转遵循 TASK_STATUS_FLOW 有向图
- 提醒与 EventEngine 互操作（任务有due_at → 自动事件）
- 复盘写入 LearningEntry 供自我进化使用
"""
import json
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

# Import contracts (handle both brain_core/ and core/ paths)
try:
    from brain_core.contracts import TaskRecord, TASK_STATUS_FLOW, new_id, now_iso
except ImportError:
    from contracts import TaskRecord, TASK_STATUS_FLOW, new_id, now_iso


class TaskEngine:
    """日常任务引擎 — 任务全生命周期管理"""

    PRIORITY_KEYWORDS = {
        "urgent": ["紧急", "马上", "立刻", "deadline", "截止", "必须", "最重要"],
        "high":   ["重要", "优先", "尽快", "抓紧", "关键", "面试", "合同", "交付"],
        "medium": ["正常", "一般", "需要", "要", "做", "完成", "整理", "写"],
        "low":    ["顺便", "有空", "不急", "以后", "看看", "逛逛"],
    }

    ENERGY_KEYWORDS = {
        "high":   ["创作", "写作", "编码", "设计", "决策", "分析", "规划", "演讲"],
        "medium": ["会议", "讨论", "学习", "阅读", "整理", "回复", "沟通"],
        "low":    ["行政", "填表", "归档", "清理", "重复", "简单"],
    }

    def __init__(self, data_dir: Path, graph=None, memory=None, events_engine=None):
        self.data_dir = Path(data_dir)
        self.tasks_file = self.data_dir / "tasks.json"
        self.graph = graph
        self.memory = memory
        self.events = events_engine  # EventEngine instance for cross-engine ops
        self._tasks: list[dict] = []
        self._load()

    def _load(self):
        if self.tasks_file.exists():
            try:
                self._tasks = json.loads(self.tasks_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._tasks = []
        else:
            self._tasks = []

    def _save(self):
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
        self.tasks_file.write_text(
            json.dumps(self._tasks, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    # ── Task Creation ──

    def create(self, title: str, description: str = "", **kwargs) -> dict:
        """从自然语言或结构化数据创建任务。
        
        Args:
            title: 任务标题（自然语言亦可，引擎会提取结构化字段）
            description: 补充描述
            **kwargs: 覆盖字段（due_at, priority, energy_level, estimated_minutes 等）
        
        Returns:
            创建的 TaskRecord dict
        """
        task = TaskRecord(
            id=new_id("task"),
            title=title.strip(),
            description=description.strip(),
            created_at=now_iso(),
            status="Captured",
        )

        # Parse structured fields BEFORE auto-advancing status
        if "priority" not in kwargs or not kwargs.get("priority"):
            task.priority = self._detect_priority(title)
        if "energy_level" not in kwargs or not kwargs.get("energy_level"):
            task.energy_level = self._detect_energy(title + " " + description)
        if "due_at" not in kwargs or not kwargs.get("due_at"):
            task.due_at = self._extract_due_date(title)
        if "estimated_minutes" not in kwargs or not kwargs.get("estimated_minutes"):
            task.estimated_minutes = self._estimate_duration(title)

        # Apply overrides
        for key, val in kwargs.items():
            if val and hasattr(task, key):
                setattr(task, key, val)

        # Auto-advance: if enough info, skip Clarifying → Planned
        has_enough_info = bool(task.due_at or task.description or task.estimated_minutes)
        if has_enough_info:
            task.status = "Planned"

        # If task has a due date, create an event too (cross-engine)
        if task.due_at and self.events:
            try:
                self.events.record(
                    f"{task.title} (任务, ID: {task.id})",
                    force_date=task.due_at,
                )
            except Exception:
                pass

        record = self._to_dict(task)
        self._tasks.append(record)
        self._save()
        return record

    def _detect_priority(self, text: str) -> str:
        for level, keywords in self.PRIORITY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return level
        return "medium"

    def _detect_energy(self, text: str) -> str:
        for level, keywords in self.ENERGY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return level
        return "medium"

    def _extract_due_date(self, text: str) -> str:
        """Extract due date from natural language. Returns ISO string or ''."""
        now = datetime.now(timezone.utc).replace(microsecond=0)
        now_naive = datetime.now().replace(microsecond=0)

        # Explicit date: "2026-07-15" or "7月15日"
        m = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", text)
        if m:
            return m.group(1).replace("/", "-")

        m = re.search(r"(\d{1,2})月(\d{1,2})[日号]", text)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            year = now_naive.year
            if month < now_naive.month:
                year += 1
            return f"{year}-{month:02d}-{day:02d}"

        # Relative: "明天", "后天", "下周X", "X天后"
        if "明天" in text:
            d = now_naive + timedelta(days=1)
            return d.strftime("%Y-%m-%d")
        if "后天" in text:
            d = now_naive + timedelta(days=2)
            return d.strftime("%Y-%m-%d")
        if "大后天" in text:
            d = now_naive + timedelta(days=3)
            return d.strftime("%Y-%m-%d")

        m = re.search(r"(\d+)天后", text)
        if m:
            d = now_naive + timedelta(days=int(m.group(1)))
            return d.strftime("%Y-%m-%d")

        # Weekdays: "下周一", "下周三"
        WEEKDAY_MAP = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
        m = re.search(r"下周([一二三四五六日天])", text)
        if m:
            target_weekday = WEEKDAY_MAP.get(m.group(1), 0)
            days_ahead = (7 - now_naive.weekday()) + target_weekday
            d = now_naive + timedelta(days=days_ahead)
            return d.strftime("%Y-%m-%d")

        m = re.search(r"周([一二三四五六日天])", text)
        if m:
            target_weekday = WEEKDAY_MAP.get(m.group(1), 0)
            days_ahead = (target_weekday - now_naive.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            d = now_naive + timedelta(days=days_ahead)
            return d.strftime("%Y-%m-%d")

        return ""

    def _estimate_duration(self, text: str) -> int:
        """Estimate task duration in minutes from text cues."""
        # Explicit: "30分钟", "2小时"
        m = re.search(r"(\d+)\s*分钟", text)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d+)\s*小时", text)
        if m:
            return int(m.group(1)) * 60

        # Heuristic by energy level
        energy = self._detect_energy(text)
        if energy == "high":
            return 90
        elif energy == "medium":
            return 45
        return 15

    # ── Status Transitions ──

    def transition(self, task_id: str, new_status: str, note: str = "") -> dict:
        """Transition task to new status (validated against TASK_STATUS_FLOW).
        
        Returns updated task dict, or error dict.
        """
        idx = self._find_task(task_id)
        if idx is None:
            return {"error": f"Task not found: {task_id}"}

        task = self._tasks[idx]
        current = task.get("status", "Captured")
        allowed = TASK_STATUS_FLOW.get(current, [])

        if new_status not in allowed:
            return {
                "error": f"Invalid transition: {current} → {new_status}",
                "allowed": allowed,
            }

        task["status"] = new_status
        task["note"] = note
        task["last_reviewed_at"] = now_iso()

        if new_status in ("Done", "Cancelled"):
            task["completed_at"] = now_iso()

        self._tasks[idx] = task
        self._save()

        # If cancelled, also update associated events
        if new_status == "Cancelled" and self.events:
            try:
                # Cancel events that mention this task ID
                for evt in self.events._events:
                    if task_id in evt.get("title", ""):
                        self.events.update_status(evt["event_id"], "cancelled", note=note)
            except Exception:
                pass

        return task

    def _find_task(self, task_id: str) -> Optional[int]:
        """Find task index by fuzzy ID match."""
        for i, t in enumerate(self._tasks):
            tid = t.get("id", "")
            if tid == task_id or tid.startswith(task_id) or task_id in tid:
                return i
        return None

    # ── Query & Search ──

    def query(self, status: str = "", priority: str = "", due_before: str = "", limit: int = 20) -> list[dict]:
        """Query tasks by filters."""
        results = self._tasks[:]

        if status:
            results = [t for t in results if t.get("status") == status]
        if priority:
            results = [t for t in results if t.get("priority") == priority]
        if due_before:
            results = [t for t in results if t.get("due_at", "") and t["due_at"] <= due_before]

        # Sort by priority desc, then due date asc
        pri_map = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        results.sort(key=lambda t: (pri_map.get(t.get("priority", "medium"), 2), t.get("due_at", "z")))

        return results[:limit]

    def search(self, keyword: str, limit: int = 10) -> list[dict]:
        """Full-text search across task titles and descriptions."""
        kw = keyword.lower()
        results = []
        for t in self._tasks:
            title = t.get("title", "").lower()
            desc = t.get("description", "").lower()
            if kw in title or kw in desc:
                results.append(t)
        return results[:limit]

    # ── Reminders ──

    def get_reminders(self, window_hours: int = 24) -> list[dict]:
        """Get tasks that need reminders within the next N hours."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=window_hours)

        reminders = []
        for t in self._tasks:
            if t.get("status") in ("Done", "Cancelled", "Archived"):
                continue
            due = t.get("due_at", "")
            if not due:
                continue
            try:
                due_dt = datetime.fromisoformat(due)
                if now <= due_dt <= cutoff:
                    t_copy = dict(t)
                    t_copy["hours_until"] = round((due_dt - now).total_seconds() / 3600, 1)
                    reminders.append(t_copy)
            except (ValueError, TypeError):
                continue

        reminders.sort(key=lambda t: t.get("hours_until", 999))
        return reminders

    def overdue(self) -> list[dict]:
        """Get overdue tasks (due date passed, not yet done/cancelled)."""
        now = datetime.now(timezone.utc)
        overdue = []
        for t in self._tasks:
            if t.get("status") in ("Done", "Cancelled", "Archived"):
                continue
            due = t.get("due_at", "")
            if not due:
                continue
            try:
                if datetime.fromisoformat(due) < now:
                    t_copy = dict(t)
                    t_copy["days_overdue"] = (now - datetime.fromisoformat(due)).days
                    overdue.append(t_copy)
            except (ValueError, TypeError):
                continue

        overdue.sort(key=lambda t: t.get("days_overdue", 0), reverse=True)
        return overdue

    # ── Review / Retrospective ──

    def get_reviewable(self, days: int = 7) -> list[dict]:
        """Get tasks marked Done within the last N days that haven't been reviewed."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        reviewable = []
        for t in self._tasks:
            if t.get("status") != "Done":
                continue
            completed = t.get("completed_at", "")
            if completed and completed >= cutoff:
                reviewable.append(t)
        return reviewable

    def review(self, task_id: str, rating: int = 0, learnings: str = "", note: str = "") -> dict:
        """Review a completed task: rate it and capture learnings.
        
        Also writes a LearningEntry if memory is available.
        """
        result = self.transition(task_id, "Reviewed", note=note)
        if "error" in result:
            return result

        result["review_rating"] = rating
        result["review_learnings"] = learnings

        # Write learning entry for self-evolution
        if self.memory and learnings:
            try:
                self.memory.record_learning(
                    source=f"task_review:{task_id}",
                    learning=learnings,
                    rating=rating,
                )
            except Exception:
                pass

        self._tasks[self._find_task(task_id)] = result
        self._save()
        return result

    # ── Stats ──

    def stats(self) -> dict:
        """Get task statistics."""
        counts = {}
        for t in self._tasks:
            s = t.get("status", "Captured")
            counts[s] = counts.get(s, 0) + 1

        pri_counts = {}
        for t in self._tasks:
            p = t.get("priority", "medium")
            pri_counts[p] = pri_counts.get(p, 0) + 1

        overdue_count = len(self.overdue())

        return {
            "total": len(self._tasks),
            "by_status": counts,
            "by_priority": pri_counts,
            "overdue": overdue_count,
            "active": len(self._tasks) - counts.get("Archived", 0) - counts.get("Cancelled", 0),
        }

    # ── Helpers ──

    def _to_dict(self, task: TaskRecord) -> dict:
        """Convert TaskRecord to dict (strip empty optionals for clean JSON)."""
        d = {
            "id": task.id,
            "user_id": task.user_id,
            "title": task.title,
            "description": task.description,
            "source_message_id": task.source_message_id,
            "created_at": task.created_at,
            "due_at": task.due_at or "",
            "scheduled_start": task.scheduled_start or "",
            "scheduled_end": task.scheduled_end or "",
            "priority": task.priority,
            "energy_level": task.energy_level,
            "estimated_minutes": task.estimated_minutes,
            "status": task.status,
            "dependencies": task.dependencies,
            "related_goals": task.related_goals,
            "related_memories": task.related_memories,
            "reminders": task.reminders,
            "conflict_records": task.conflict_records,
            "last_reviewed_at": task.last_reviewed_at or "",
            "completed_at": task.completed_at or "",
            "note": task.note or "",
            "metadata": task.metadata,
        }
        return d
