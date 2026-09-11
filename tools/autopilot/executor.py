"""批次执行器 —— 引擎真正「干活」的模块。

引擎的 execute 之前是空壳（只跑控制塔 check）。本模块实现真实任务执行：

1. ensure_checkpoint：切到任务 WORK-CLAIM 要求的 exact_head（前置依赖所在 commit）
2. load_batch：读 EXECUTABLE-BATCH.json，按 fixed_order + depends_on 逐个执行
3. 验证类批次（CLEAN_REPRODUCTION / RECOVERY_MATRIX / ADVERSARIAL_MATRIX /
   ENVIRONMENT_PROBE）：跑 acceptance_commands —— 确定性、可全自动
4. 实现类批次（SIMPLE_IMPLEMENTATION）：调 headless codebuddy 写代码 —— 默认关闭，
   需配置显式启用（无人审查下自动写代码 + push 是高风险动作）
5. generate_receipt：每个批次项落 receipt

安全护栏（对应任务 hard_boundaries）：
- 只在 authorized_paths 内写，不碰 codex_retained_write_surfaces
- 绝不 merge（NO_SELF_MERGE）
- 实现类默认关闭，验证类先行
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from .config import AutopilotConfig, ModelTier

# 验证类批次：只跑 acceptance_commands，不写代码
VERIFY_KINDS = {"CLEAN_REPRODUCTION", "RECOVERY_MATRIX", "ADVERSARIAL_MATRIX", "ENVIRONMENT_PROBE"}
# 实现类批次：需要写代码（默认关闭）
IMPL_KINDS = {"SIMPLE_IMPLEMENTATION"}

# 继承自 WorkBuddy host 的 env 会让子 codebuddy 端口冲突 → EADDRINUSE → 挂死（false-alive）。
# 启动 headless codebuddy 前必须 scrub 掉这些。
HOST_ENV_TO_SCRUB = [
    "SERVER__PORT", "CODEBUDDY_SESSION_ID", "CLAUDE_SESSION_ID", "BAGGAGE",
    "CODEBUDDY_GATEWAY_AUTH", "CODEBUDDY_GATEWAY_PASSWORD", "CODEBUDDY_GATEWAY_PORT",
    "CODEBUDDY_GATEWAY_URL", "CODEBUDDY_MCP_CONFIG", "CODEBUDDY_DISABLE_SESSION_HISTORY_CLEANUP",
]


@dataclass
class ItemResult:
    item_id: str
    kind: str
    status: str  # PASS / FAIL / SKIPPED / NOT_IMPLEMENTED
    output_tail: str = ""
    receipt_path: Optional[str] = None


@dataclass
class BatchReport:
    batch_id: str
    task_id: str
    items: list[ItemResult] = field(default_factory=list)
    checkpoint_head: str = ""

    @property
    def all_pass(self) -> bool:
        return bool(self.items) and all(i.status == "PASS" for i in self.items)


class BatchExecutor:
    def __init__(self, config: AutopilotConfig, log):
        self.cfg = config
        self.log = log

    # ------------------------------------------------------------------
    # 前置：切到任务 exact_head（前置依赖所在 commit）
    # ------------------------------------------------------------------
    def ensure_checkpoint(self, task) -> tuple[bool, str]:
        """切到 WORK-CLAIM 要求的 branch_parent_required / exact_head。"""
        head = (task.raw.get("source_checkpoint") or {}).get("exact_head")
        branch = (task.raw.get("source_checkpoint") or {}).get("branch") or task.branch
        if not head:
            self.log(f"executor: no exact_head for {task.task_id}, skip checkpoint switch")
            return False, ""
        root = self.cfg.local_root
        # 确认该 commit 可达
        probe = subprocess.run(
            ["git", "cat-file", "-t", head], cwd=str(root),
            capture_output=True, text=True, encoding="utf-8",
        )
        if probe.returncode != 0:
            self.log(f"executor: exact_head {head} not reachable: {probe.stderr.strip()}")
            return False, ""
        # 只在 worktree clean 时切换，避免覆盖未提交改动
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=str(root),
            capture_output=True, text=True, encoding="utf-8",
        )
        if dirty.stdout.strip():
            self.log("executor: worktree dirty, skip checkpoint switch (preserve changes)")
            return False, ""
        try:
            subprocess.run(
                ["git", "checkout", head], cwd=str(root),
                capture_output=True, text=True, encoding="utf-8", check=True,
            )
            self.log(f"executor: switched to exact_head {head[:12]}")
            return True, head
        except subprocess.CalledProcessError as e:
            self.log(f"executor: checkout {head[:12]} failed: {e.stderr.strip()[:300]}")
            return False, ""

    # ------------------------------------------------------------------
    # 批次加载
    # ------------------------------------------------------------------
    def load_batch(self, task) -> Optional[dict[str, Any]]:
        rel = task.raw.get("executable_batch")
        if not rel:
            return None
        p = self.cfg.local_root / rel
        if not p.is_file():
            self.log(f"executor: batch file missing: {rel}")
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            self.log(f"executor: batch parse failed: {e}")
            return None

    # ------------------------------------------------------------------
    # 执行单批次项
    # ------------------------------------------------------------------
    def execute_item(self, item: dict[str, Any], task) -> ItemResult:
        item_id = str(item.get("item_id", "?"))
        kind = str(item.get("kind", ""))
        cmds = item.get("acceptance_commands") or []
        write_paths = item.get("write_paths") or []

        if kind in IMPL_KINDS:
            if not self.cfg.executors_headless:
                return ItemResult(item_id, kind, "NOT_IMPLEMENTED",
                                  "headless executor disabled (executors.headless=false)")
            return self._run_implementation(item_id, kind, item, write_paths)

        if kind in VERIFY_KINDS:
            return self._run_verification(item_id, kind, cmds)

        return ItemResult(item_id, kind, "SKIPPED", f"unknown kind {kind!r}")

    def _run_verification(self, item_id: str, kind: str, cmds: list[str]) -> ItemResult:
        if not cmds:
            return ItemResult(item_id, kind, "SKIPPED", "no acceptance_commands")
        for cmd in cmds:
            argv = shlex.split(cmd)
            try:
                proc = subprocess.run(
                    argv, cwd=str(self.cfg.local_root),
                    capture_output=True, text=True, encoding="utf-8", timeout=300,
                )
            except subprocess.TimeoutExpired:
                return ItemResult(item_id, kind, "FAIL", f"timeout: {cmd}")
            tail = (proc.stdout or "")[-400:] or (proc.stderr or "")[-400:]
            if proc.returncode != 0:
                self.log(f"executor: {item_id} FAIL on: {cmd}")
                return ItemResult(item_id, kind, "FAIL", tail)
        return ItemResult(item_id, kind, "PASS", f"{len(cmds)} command(s) passed")

    def _run_implementation(self, item_id: str, kind: str, item: dict[str, Any],
                            write_paths: list[str]) -> ItemResult:
        """调 headless codebuddy 写代码。默认关闭（见 executors.headless）。"""
        outcome = str(item.get("outcome") or item.get("task_brief") or "")
        tier: ModelTier = self.cfg.default_tier
        prompt = (
            f"你在仓库 vxz2datoubo/second-brain-coordination 里执行一个批次项。\n"
            f"批次项: {item_id}（{kind}）\n"
            f"任务要求: {outcome}\n"
            f"允许写入路径（仅限这些）: {', '.join(write_paths) or '(无)'}\n"
            f"硬约束: 不改变架构、不改变验收 oracle、不碰 Codex 保留写入面、不 merge、"
            f"不访问凭据/真实用户数据/外部付费生成/交易。完成后运行自己的验收命令自检。"
        )
        env = {k: v for k, v in os.environ.items() if k not in HOST_ENV_TO_SCRUB}
        cmd = ["codebuddy", "-p", "--model", tier.model, "--permission-mode", "auto", prompt]
        try:
            proc = subprocess.run(
                cmd, cwd=str(self.cfg.local_root), env=env,
                capture_output=True, text=True, encoding="utf-8", timeout=1800,
            )
        except subprocess.TimeoutExpired:
            return ItemResult(item_id, kind, "FAIL", "headless codebuddy timeout (1800s)")
        tail = (proc.stdout or "")[-600:] or (proc.stderr or "")[-600:]
        status = "PASS" if proc.returncode == 0 else "FAIL"
        return ItemResult(item_id, kind, status, tail)

    # ------------------------------------------------------------------
    # 跑整个批次（按 fixed_order）
    # ------------------------------------------------------------------
    def run_batch(self, task) -> Optional[BatchReport]:
        batch = self.load_batch(task)
        if not batch:
            return None
        report = BatchReport(batch_id=str(batch.get("batch_id", "?")), task_id=task.task_id)
        fixed_order = task.raw.get("fixed_order") or [i.get("item_id") for i in batch.get("items", [])]
        items = {str(i.get("item_id")): i for i in batch.get("items", [])}

        for item_id in fixed_order:
            item = items.get(item_id)
            if not item:
                self.log(f"executor: item {item_id} not in batch, skip")
                continue
            result = self.execute_item(item, task)
            report.items.append(result)
            self.log(f"executor: {item_id} -> {result.status}")
            if result.status == "FAIL":
                self.log(f"executor: stop batch at {item_id} (FAIL)")
                break  # 有序批次：失败即停
        return report

    # ------------------------------------------------------------------
    # receipt
    # ------------------------------------------------------------------
    def write_receipt(self, task, report: BatchReport) -> Optional[str]:
        receipt_dir = self.cfg.local_root / "coordination" / "PROGRAMS" / \
            "CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001" / "WORKBUDDY-R175"
        receipt_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "batch_id": report.batch_id,
            "task_id": report.task_id,
            "checkpoint_head": report.checkpoint_head,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "items": [
                {"item_id": i.item_id, "kind": i.kind, "status": i.status, "output": i.output_tail}
                for i in report.items
            ],
            "all_pass": report.all_pass,
        }
        out = receipt_dir / f"WORKBUDDY-R175-EXECUTION-RECEIPT-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.yaml"
        out.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        self.log(f"executor: receipt -> {out}")
        return str(out)
