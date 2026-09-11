"""Autopilot 收尾交接报告生成器。

OWNER 睡醒后说「收尾」，本模块把 8 小时自动驾驶期间的：
  已完成 / 待 review / 待独立验算 / 阻塞问题 / 租约状态 / 日志摘要
沉淀成一份交接 markdown，供 OWNER 醒来直接审阅，无需翻日志。

数据来源（都在 .autopilot-state/ 下，由主引擎在每轮循环后持久化）：
  - cycles.jsonl   : 每轮 CycleReport 的 JSON 行
  - claims.json    : 租约/单写者记录
  - autopilot.log  : 运行日志
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CYCLES_FILE = "cycles.jsonl"
HANDOFF_FILE = "handoff.md"
CLAIMS_FILE = "claims.json"
LOG_FILE = "autopilot.log"


def _read_cycles(state_dir: Path) -> list[dict[str, Any]]:
    p = state_dir / CYCLES_FILE
    if not p.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _read_claims(state_dir: Path) -> dict[str, Any]:
    p = state_dir / CLAIMS_FILE
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"claims": {}}
    return {"claims": {}}


def _read_log_tail(state_dir: Path, n: int = 100) -> list[str]:
    p = state_dir / LOG_FILE
    if not p.is_file():
        return []
    return p.read_text(encoding="utf-8").splitlines()[-n:]


def _uniq(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for it in items:
        key = str(it)
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def _fmt_pr(pr: Any, task_map: dict[str, str]) -> str:
    num = str(pr)
    task = task_map.get(num)
    if task:
        return f"#{num}（任务 `{task}`）"
    return f"#{num}"


def generate_handoff(state_dir: Path, out_path: Path | None = None) -> str:
    """聚合自动驾驶期间的运行状态，生成交接 markdown。返回 markdown 文本。"""
    cycles = _read_cycles(state_dir)
    claims = _read_claims(state_dir)
    log_tail = _read_log_tail(state_dir)

    merged: list[Any] = []
    pr_created: list[Any] = []
    review_requested: list[Any] = []
    gate_paused: list[Any] = []
    blocked: list[Any] = []
    claimed: list[Any] = []
    executed: list[Any] = []
    pr_task_map: dict[str, str] = {}

    for c in cycles:
        merged += c.get("merged", [])
        pr_created += c.get("pr_created", [])
        review_requested += c.get("review_requested", [])
        gate_paused += c.get("gate_paused", [])
        blocked += c.get("blocked", [])
        claimed += c.get("claimed", [])
        executed += c.get("executed", [])
        for k, v in (c.get("pr_task_map") or {}).items():
            pr_task_map.setdefault(str(k), str(v))

    merged = _uniq(merged)
    pr_created = _uniq(pr_created)
    review_requested = _uniq(review_requested)
    gate_paused = _uniq(gate_paused)
    blocked = _uniq(blocked)
    claimed = _uniq(claimed)
    executed = _uniq(executed)

    # 未释放的租约 = 可能仍持有执行权或异常中断，需 OWNER 关注
    open_claims: list[str] = []
    for tid, info in (claims.get("claims") or {}).items():
        if isinstance(info, dict) and not info.get("released"):
            open_claims.append(tid)

    now = datetime.now(timezone.utc).isoformat()
    lines: list[str] = []
    lines.append("# Autopilot 收尾交接报告")
    lines.append("")
    lines.append(f"- 生成时间：`{now}`")
    lines.append(f"- 运行周期数：`{len(cycles)}`")
    lines.append(f"- 发现/执行任务数：`{len(claimed)}` 领取 / `{len(executed)}` 执行")
    lines.append("")

    lines.append("## 一、需要你醒来处理（高优先级）")
    lines.append("")
    if review_requested:
        lines.append("### 待独立 review + 独立验算的 PR")
        lines.append("")
        lines.append("这些 PR 命中了 Tier2 门禁（实质代码/架构/交易变更，或有 self-merge 锁），")
        lines.append("引擎**没有**自动合并。建议你用 CLI 独立验算后，再走独立 review：")
        lines.append("")
        lines.append("```bash")
        lines.append("# 用快模型独立 review 每个 PR（双模型交叉验证）")
        lines.append("codex review -m v4.1-flash <PR_URL>")
        lines.append("```")
        lines.append("")
        for pr in review_requested:
            lines.append(f"- {_fmt_pr(pr, pr_task_map)}")
        lines.append("")
    else:
        lines.append("暂无待 review 的 PR。")
        lines.append("")

    if blocked:
        lines.append("### 阻塞 / 未通过验证的任务")
        lines.append("")
        lines.append("以下任务在验证环节失败或被阻塞，**未产生 PR**，需要你排查：")
        lines.append("")
        for t in blocked:
            lines.append(f"- `{t}`")
        lines.append("")
    if gate_paused:
        lines.append("### 遇到门禁 checkpoint 的任务（未推进，已安全挂起）")
        lines.append("")
        for t in gate_paused:
            lines.append(f"- `{t}`")
        lines.append("")

    lines.append("## 二、已完成（可交付）")
    lines.append("")
    if merged:
        lines.append("### 已自动合并的 PR（Tier1 机械低风险）")
        lines.append("")
        for pr in merged:
            lines.append(f"- {_fmt_pr(pr, pr_task_map)}")
        lines.append("")
    else:
        lines.append("本次未发生 Tier1 自动合并。")
        lines.append("")
    if pr_created:
        lines.append("### 已创建的全部 PR")
        lines.append("")
        for pr in pr_created:
            lines.append(f"- {_fmt_pr(pr, pr_task_map)}")
        lines.append("")
    if executed:
        lines.append("### 已执行的任务")
        lines.append("")
        for t in executed:
            lines.append(f"- `{t}`")
        lines.append("")

    lines.append("## 三、租约 / 单写者状态")
    lines.append("")
    if open_claims:
        lines.append("以下租约**未释放**（可能仍持有执行权或上次运行异常中断）：")
        lines.append("")
        for tid in open_claims:
            lines.append(f"- `{tid}`")
        lines.append("")
    else:
        lines.append("所有租约均已正常释放。")
        lines.append("")

    lines.append("## 四、日志摘要（尾部）")
    lines.append("")
    if log_tail:
        lines.append("```text")
        for ln in log_tail:
            lines.append(ln)
        lines.append("```")
    else:
        lines.append("（无日志）")

    text = "\n".join(lines) + "\n"

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")

    return text


def run_from_cli(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Autopilot 收尾交接报告生成器")
    parser.add_argument("--state-dir", required=True, help=".autopilot-state 目录")
    parser.add_argument("--out", default=None, help="输出 markdown 路径（默认打印到 stdout）")
    args = parser.parse_args(argv)

    text = generate_handoff(Path(args.state_dir), Path(args.out) if args.out else None)
    if not args.out:
        print(text)
    else:
        print(f"handoff written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_from_cli())
