"""Announcement board for v0.1 progress visibility."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import now_iso
from .storage import BrainStore


BOARD_META_KEY = "v0_1_announcement_board"


class AnnouncementBoard:
    def __init__(self, store: BrainStore, root: Path):
        self.store = store
        self.root = Path(root)
        self.path = self.root / "bulletin" / "super-second-brain-v01-board.md"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_default()

    def _ensure_default(self) -> None:
        state = self.store.get_meta(BOARD_META_KEY)
        if state:
            self._render(state)
            return
        state = {
            "title": "超级第二大脑 v0.1 公告栏",
            "updated_at": now_iso(),
            "status": "进行中",
            "completed": [
                "v0.1 核心数据协议：SourceRecord、EvidenceItem、KnowledgeAtom、DecisionRecord、ForecastRecord、ReviewRecord、SelfEvolutionLog",
                "本地存储：SQLite 主库 + JSONL 审计日志",
                "最小 CLI：ingest-text、search、decision、forecast、review、status、evolution-log",
                "最小 API：/api/v0/ingest/text、/api/v0/search、/api/v0/decision、/api/v0/forecast、/api/v0/review、/api/v0/status、/api/v0/evolution/log",
                "基础测试：合同、摄取、检索、审批门、Brier score 复盘",
            ],
            "in_progress": [
                "公告栏自动记录与进度同步",
            ],
            "next_step": "接入用户反馈回写，基于 review/feedback 更新标签、置信度、关系和待改进事项。",
            "event_log": [
                {
                    "timestamp": now_iso(),
                    "type": "milestone",
                    "summary": "v0.1 第一条垂直切片已落地并通过测试。",
                }
            ],
        }
        self.store.set_meta(BOARD_META_KEY, state)
        self._render(state)

    def get_state(self) -> dict[str, Any]:
        state = self.store.get_meta(BOARD_META_KEY)
        if not state:
            self._ensure_default()
            state = self.store.get_meta(BOARD_META_KEY, {})
        return state

    def update(
        self,
        *,
        completed: list[str] | None = None,
        in_progress: list[str] | None = None,
        next_step: str | None = None,
        status: str | None = None,
        event_type: str = "progress_update",
        summary: str = "",
    ) -> dict[str, Any]:
        state = self.get_state()
        if completed is not None:
            state["completed"] = completed
        if in_progress is not None:
            state["in_progress"] = in_progress
        if next_step is not None:
            state["next_step"] = next_step
        if status is not None:
            state["status"] = status
        if summary:
            state.setdefault("event_log", []).append(
                {
                    "timestamp": now_iso(),
                    "type": event_type,
                    "summary": summary,
                }
            )
            state["event_log"] = state["event_log"][-20:]
        state["updated_at"] = now_iso()
        self.store.set_meta(BOARD_META_KEY, state)
        self._render(state)
        return state

    def status(self) -> dict[str, Any]:
        state = self.get_state()
        return {
            "path": str(self.path),
            "updated_at": state["updated_at"],
            "status": state["status"],
            "completed": state["completed"],
            "in_progress": state["in_progress"],
            "next_step": state["next_step"],
            "recent_events": state.get("event_log", [])[-5:],
        }

    def _render(self, state: dict[str, Any]) -> None:
        lines = [
            f"# {state['title']}",
            "",
            f"更新时间：{state['updated_at']}",
            f"状态：{state['status']}",
            "用途：记录超级第二大脑 v0.1 的当前完成项、进行中项、下一步和最近里程碑，方便下次继续。",
            "",
            "## 已完成",
        ]
        completed = state.get("completed", [])
        if completed:
            lines.extend(f"- {item}" for item in completed)
        else:
            lines.append("- （暂无）")
        lines.extend(["", "## 进行中"])
        in_progress = state.get("in_progress", [])
        if in_progress:
            lines.extend(f"- {item}" for item in in_progress)
        else:
            lines.append("- （暂无）")
        lines.extend(["", "## 下一步", state.get("next_step", "待补充"), "", "## 最近更新"])
        event_log = state.get("event_log", [])
        if event_log:
            for item in reversed(event_log[-10:]):
                lines.append(f"- [{item['timestamp']}] {item['type']}: {item['summary']}")
        else:
            lines.append("- （暂无）")
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
