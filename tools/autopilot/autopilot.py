"""Autopilot 主引擎 —— 本地全自动推进闭环。

把已有治理零件串成无人值守循环。引擎本身是「编排层」，不重写治理逻辑：

    sync -> discover -> claim -> execute -> verify -> report
         -> commit -> push -> PR -> tiered-merge -> next

SLEEP_AUTONOMY 语义（来自 OWNER-AGENT-BEHAVIOR-AND-INTERRUPTION-PROTOCOL）：
  - Owner 问题数必须为 0，不以沉默推导授权，不越过 Owner gate；
  - 遇 gate 就 checkpoint 当前项，继续其他合法/非依赖/非冲突工作；
  - 全部受阻则安全暂停。

执行分两层：机械治理（确定性、可全自动）由本引擎直接驱动；真实工程
实现（写代码/解任务）通过 executor 接口调度外部 headless agent。
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from . import github_client as gh
from .config import AutopilotConfig, MODE_SLEEP_AUTONOMY, MODE_WRAP_UP

ACTIVE_TASK_FILES = [
    "coordination/ACTIVE-CODEX-TASK.yaml",
    "coordination/ACTIVE-WORKBUDDY-TASK.yaml",
]

# 租约/碰撞单写者键：同一任务真源只允许一个本地进程持有执行权。
STATE_DIR_NAME = ".autopilot-state"
CLAIM_FILE = "claims.json"
LOG_FILE = "autopilot.log"


@dataclass
class TaskView:
    task_id: str
    agent: str
    status: str
    execution_allowed: bool
    merge_authorized: bool
    issue: Optional[int]
    branch: Optional[str]
    hard_locks: list[str]
    authorized_paths: list[str]
    source_file: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def has_self_merge_lock(self) -> bool:
        locks = {str(x).upper().replace(" ", "_") for x in self.hard_locks}
        return any(
            "SELF_MERGE" in x or "SELF_REVIEW" in x or "SELF_ACCEPT" in x
            for x in locks
        )

    @property
    def is_ready(self) -> bool:
        return self.status == "READY" and self.execution_allowed


@dataclass
class MergeDecision:
    pr_number: int
    tier: str
    allowed: bool
    reason: str


@dataclass
class CycleReport:
    started_at: str
    synced: bool
    discovered: int
    ready_tasks: list[str] = field(default_factory=list)
    claimed: list[str] = field(default_factory=list)
    executed: list[str] = field(default_factory=list)
    committed: list[str] = field(default_factory=list)
    pr_created: list[int] = field(default_factory=list)
    merged: list[int] = field(default_factory=list)
    review_requested: list[int] = field(default_factory=list)
    gate_paused: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    pr_task_map: dict[str, str] = field(default_factory=dict)
    stopped: bool = False
    stop_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


class AutopilotEngine:
    def __init__(self, config: AutopilotConfig):
        self.cfg = config
        self.root = config.local_root
        self.state_dir = config.state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._claims = self._load_claims()
        self._started = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # 状态 / 租约
    # ------------------------------------------------------------------
    def _load_claims(self) -> dict[str, Any]:
        p = self.state_dir / CLAIM_FILE
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
        return {"claims": {}}

    def _save_claims(self) -> None:
        p = self.state_dir / CLAIM_FILE
        p.write_text(json.dumps(self._claims, ensure_ascii=False, indent=2), encoding="utf-8")

    def log(self, msg: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        print(line)
        with (self.state_dir / LOG_FILE).open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    # ------------------------------------------------------------------
    # sync：本地-GitHub 双向同步（只读 fetch + ff-only，绝不覆盖工作区）
    # ------------------------------------------------------------------
    def sync(self) -> bool:
        if not gh.auth_ok():
            self.log("sync: gh auth failed, skip")
            return False
        if gh.worktree_dirty(self.root):
            self.log("sync: worktree dirty, skip ff-only merge (preserve local changes)")
            gh.fetch_default(self.root, self.cfg.default_branch)
            return True
        try:
            gh.fetch_default(self.root, self.cfg.default_branch)
            gh.merge_upstream(self.root, self.cfg.default_branch)
            return True
        except gh.GhError as e:
            self.log(f"sync: ff-only merge failed: {e}")
            return False

    # ------------------------------------------------------------------
    # discover：从任务真源发现 READY 任务
    # ------------------------------------------------------------------
    def discover(self) -> list[TaskView]:
        tasks: list[TaskView] = []
        for rel in ACTIVE_TASK_FILES:
            p = self.root / rel
            if not p.is_file():
                continue
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as e:
                self.log(f"discover: cannot parse {rel}: {e}")
                continue
            tasks.append(self._to_view(data, rel))
        return tasks

    @staticmethod
    def _to_view(data: dict[str, Any], source: str) -> TaskView:
        return TaskView(
            task_id=str(data.get("task_id", "UNKNOWN")),
            agent=str(data.get("target_agent", "UNKNOWN")),
            status=str(data.get("status", "UNKNOWN")),
            execution_allowed=bool(data.get("execution_allowed", False)),
            merge_authorized=bool(data.get("merge_authorized", False)),
            issue=data.get("active_issue") if isinstance(data.get("active_issue"), int) else None,
            branch=str(data.get("implementation_branch", "")) or None,
            hard_locks=[str(x) for x in (data.get("hard_locks") or [])],
            authorized_paths=[str(x) for x in (data.get("authorized_paths") or [])],
            source_file=source,
            raw=data,
        )

    # ------------------------------------------------------------------
    # claim：领取本地执行权（依赖 + 单写者）
    # ------------------------------------------------------------------
    def claim(self, task: TaskView) -> bool:
        claims = self._claims["claims"]
        if task.task_id in claims:
            return claims[task.task_id].get("claimed", False)
        claims[task.task_id] = {
            "claimed": True,
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "agent": task.agent,
            "issue": task.issue,
        }
        self._save_claims()
        self.log(f"claim: {task.task_id} (issue #{task.issue})")
        return True

    def release_claim(self, task: TaskView, outcome: str) -> None:
        claims = self._claims["claims"]
        if task.task_id in claims:
            claims[task.task_id]["released"] = True
            claims[task.task_id]["outcome"] = outcome
            claims[task.task_id]["released_at"] = datetime.now(timezone.utc).isoformat()
            self._save_claims()

    # ------------------------------------------------------------------
    # execute：机械治理（确定性动作），headless 由 executor 接口调度
    # ------------------------------------------------------------------
    def execute_mechanical(self, task: TaskView) -> list[str]:
        """运行控制塔一致性扫描（确定性、无网络副作用）。"""
        actions: list[str] = []
        ct_dir = self.root / "coordination" / "CONTROL-TOWER"
        runner = ct_dir / "run_control_tower.py"
        if runner.is_file():
            proc = subprocess.run(
                ["python", str(runner), "check", "--repo-root", str(self.root)],
                capture_output=True, text=True, encoding="utf-8",
            )
            if proc.returncode == 0:
                actions.append("CONTROL_TOWER_CHECK_PASS")
            else:
                actions.append("CONTROL_TOWER_CHECK_FAIL")
                self.log(f"execute: control tower check failed: {proc.stderr[-400:]}")
        return actions

    def execute(self, task: TaskView) -> list[str]:
        actions: list[str] = []
        if self.cfg.executors_mechanical:
            actions += self.execute_mechanical(task)
        if self.cfg.executors_headless:
            actions.append("HEADLESS_DELEGATED")  # 实际调度见 executor 接口
        return actions

    # ------------------------------------------------------------------
    # verify：跑测试（依赖现有 unittest 套件）
    # ------------------------------------------------------------------
    def verify(self) -> bool:
        proc = subprocess.run(
            ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
            cwd=str(self.root), capture_output=True, text=True, encoding="utf-8",
        )
        ok = proc.returncode == 0
        if not ok:
            tail = proc.stderr[-600:] or proc.stdout[-600:]
            self.log(f"verify: tests failed: {tail}")
        return ok

    # ------------------------------------------------------------------
    # commit / push / PR
    # ------------------------------------------------------------------
    def commit_push(self, task: TaskView) -> Optional[gh.PrInfo]:
        if not gh.worktree_dirty(self.root):
            self.log(f"commit: nothing to commit for {task.task_id}")
            return None
        branch = task.branch or f"autopilot/{task.task_id.lower()}"
        try:
            if branch not in gh.list_local_branches(self.root):
                gh.create_branch(self.root, branch)
            else:
                gh.switch_branch(self.root, branch)
        except gh.GhError:
            self.log(f"commit: branch switch failed for {branch}, skip")
            return None
        msg = f"autopilot: {task.task_id} (issue #{task.issue})"
        if not gh.commit_all(self.root, msg):
            return None
        gh.push(self.root, branch)
        body = f"Autopilot 全自动推进：{task.task_id}\n\n- issue: #{task.issue}\n- agent: {task.agent}\n"
        pr = gh.create_pr(self.root, msg, body, self.cfg.default_branch, branch)
        self.log(f"PR #{pr.number} created for {task.task_id}")
        return pr

    # ------------------------------------------------------------------
    # merge 决策：分层受治理
    # ------------------------------------------------------------------
    def decide_merge(self, task: TaskView, pr: gh.PrInfo) -> MergeDecision:
        if pr.draft:
            return MergeDecision(pr.number, "NONE", False, "PR is draft")
        if task.has_self_merge_lock or not task.merge_authorized:
            return MergeDecision(pr.number, "TIER2", False, "self-merge locked / merge not authorized")
        checks = gh.pr_checks(self.root, pr.number)
        if checks.conclusion != "success":
            return MergeDecision(pr.number, "TIER2", False, f"CI not green ({checks.conclusion})")
        if not self._is_tier1_paths(pr):
            return MergeDecision(pr.number, "TIER2", False, "substantive code change, needs independent review")
        if self.cfg.tier1_enabled:
            return MergeDecision(pr.number, "TIER1", True, "mechanical low-risk change, CI green")
        return MergeDecision(pr.number, "TIER2", False, "tier1 auto-merge disabled by config")

    def _is_tier1_paths(self, pr: gh.PrInfo) -> bool:
        proc = subprocess.run(
            ["git", "diff", "--name-only", f"origin/{pr.base_ref}...origin/{pr.head_ref}"],
            cwd=str(self.root), capture_output=True, text=True, encoding="utf-8",
        )
        changed = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        if not changed:
            return False
        import fnmatch
        for rel in changed:
            rel = rel.replace("\\", "/")
            if not any(fnmatch.fnmatch(rel, g) for g in self.cfg.tier1_path_globs):
                return False
            lower = rel.lower()
            if any(term in lower for term in self.cfg.tier1_forbidden_terms):
                return False
        return True

    # ------------------------------------------------------------------
    # 单次循环
    # ------------------------------------------------------------------
    def run_once(self) -> CycleReport:
        report = CycleReport(
            started_at=datetime.now(timezone.utc).isoformat(),
            synced=False,
            discovered=0,
        )
        report.synced = self.sync()
        tasks = self.discover()
        report.discovered = len(tasks)
        ready = [t for t in tasks if t.is_ready]
        report.ready_tasks = [t.task_id for t in ready]

        for task in ready:
            if not self.claim(task):
                continue
            report.claimed.append(task.task_id)

            actions = self.execute(task)
            report.executed.append(task.task_id)

            # 遇 gate（self-merge 锁 / merge 未授权 / 交易锁）→ checkpoint 继续下一个
            if task.has_self_merge_lock or not task.merge_authorized:
                report.gate_paused.append(task.task_id)
                self.log(f"gate: {task.task_id} has merge/self-review lock, checkpoint and continue")
                self.release_claim(task, "GATE_PAUSED")
                continue

            if not self.verify():
                report.blocked.append(task.task_id)
                self.release_claim(task, "VERIFY_FAILED")
                continue

            pr = self.commit_push(task)
            if pr is None:
                self.release_claim(task, "NOTHING_TO_COMMIT")
                continue
            report.pr_created.append(pr.number)
            report.pr_task_map[str(pr.number)] = task.task_id

            decision = self.decide_merge(task, pr)
            if decision.allowed:
                try:
                    gh.pr_approve(self.root, pr.number, "autopilot tier1 machine approval")
                    gh.pr_merge(self.root, pr.number, method="merge")
                    report.merged.append(pr.number)
                    self.log(f"merged PR #{pr.number} (tier1)")
                except gh.GhError as e:
                    report.blocked.append(task.task_id)
                    self.log(f"merge failed for PR #{pr.number}: {e}")
            else:
                report.review_requested.append(pr.number)
                self.log(f"PR #{pr.number} -> {decision.tier}: {decision.reason}")
            self.release_claim(task, decision.tier)

        return report

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------
    def _append_cycle(self, report: CycleReport) -> None:
        with (self.state_dir / "cycles.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(report.as_dict(), ensure_ascii=False) + "\n")

    def _write_handoff(self) -> str:
        from .handoff import generate_handoff
        out = self.state_dir / "handoff.md"
        generate_handoff(self.state_dir, out)
        self.log(f"handoff: written to {out}")
        return str(out)

    def run(self) -> CycleReport:
        deadline = self._started + timedelta(hours=self.cfg.max_duration_hours)
        last: Optional[CycleReport] = None
        self.log(f"autopilot start: mode={self.cfg.mode}, duration={self.cfg.max_duration_hours}h, repo={self.cfg.repo}")

        while True:
            last = self.run_once()
            self._append_cycle(last)
            now = datetime.now(timezone.utc)
            if now >= deadline:
                last.stopped = True
                last.stop_reason = f"max_duration_reached ({self.cfg.max_duration_hours}h)"
                break
            if self.cfg.is_wrap_up and not last.executed:
                last.stopped = True
                last.stop_reason = "wrap_up_idle"
                break
            if self.cfg.is_sleep_autonomy and last.blocked and not last.executed:
                last.stopped = True
                last.stop_reason = "sleep_autonomy_all_blocked"
                break
            time.sleep(self.cfg.poll_interval_seconds)

        self.log(f"autopilot stop: {last.stop_reason if last else 'no_cycles'}")
        self._write_handoff()
        return last if last is not None else CycleReport(started_at="", synced=False, discovered=0)


def run_from_cli(argv: list[str] | None = None) -> int:
    import argparse
    from .config import load_config

    parser = argparse.ArgumentParser(description="Local Autopilot — 全自动推进引擎")
    parser.add_argument("--config", default=None, help="path to autopilot config YAML")
    parser.add_argument("--repo-root", default=None, help="local repo root (default: cwd parent)")
    parser.add_argument("--mode", default=None, choices=[MODE_SLEEP_AUTONOMY, MODE_WRAP_UP])
    parser.add_argument("--once", action="store_true", help="run a single cycle then exit")
    parser.add_argument("--dry-run", action="store_true", help="discover + decide only, no side effects")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd()
    cfg = load_config(args.config, root)
    if args.mode:
        cfg.mode = args.mode

    engine = AutopilotEngine(cfg)
    if args.dry_run:
        engine.log("DRY RUN: discover only, no side effects")
        tasks = engine.discover()
        for t in tasks:
            print(f"  [{t.agent}] {t.task_id} status={t.status} allowed={t.execution_allowed} merge={t.merge_authorized}")
        return 0

    report = engine.run_once() if args.once else engine.run()
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_from_cli())
