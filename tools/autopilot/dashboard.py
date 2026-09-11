"""控制塔 Web 看板生成器。

从任务真源（ACTIVE-*.yaml、ACTIVE-PROGRAM-LANES.yaml）生成一个自包含的
静态 HTML 看板，供 GitHub Pages 部署。无外部依赖，内联 CSS，中英混合界面。

这是「deploy」目标的产物：睡觉醒来打开网页即可看到各泳道/Agent 的进度、
冲突与 gate 状态。
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class LaneRow:
    lane_id: str
    desired: str
    observed: str
    owner: str
    implementation_owner: str
    next_gate: str
    trading_authorized: bool


@dataclass
class AgentRow:
    agent: str
    task_id: str
    status: str
    execution_allowed: bool
    merge_authorized: bool
    issue: Optional[int]
    branch: Optional[str]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}


def collect(root: Path) -> dict[str, Any]:
    lanes = _load_yaml(root / "coordination" / "ACTIVE-PROGRAM-LANES.yaml")
    lane_rows: list[LaneRow] = []
    for l in lanes.get("program_lanes", []):
        lane_rows.append(LaneRow(
            lane_id=str(l.get("lane_id", "?")),
            desired=str(l.get("desired_state", "?")),
            observed=str(l.get("observed_state", "?")),
            owner=str(l.get("owner", "?")),
            implementation_owner=str(l.get("implementation_owner") or "NONE"),
            next_gate=str(l.get("next_gate", "?")),
            trading_authorized=bool(l.get("trading_authorized", False)),
        ))

    agent_files = {
        "CODEX": "coordination/ACTIVE-CODEX-TASK.yaml",
        "WORKBUDDY": "coordination/ACTIVE-WORKBUDDY-TASK.yaml",
    }
    agent_rows: list[AgentRow] = []
    for agent, rel in agent_files.items():
        d = _load_yaml(root / rel)
        agent_rows.append(AgentRow(
            agent=agent,
            task_id=str(d.get("task_id", "—")),
            status=str(d.get("status", "—")),
            execution_allowed=bool(d.get("execution_allowed", False)),
            merge_authorized=bool(d.get("merge_authorized", False)),
            issue=d.get("active_issue") if isinstance(d.get("active_issue"), int) else None,
            branch=str(d.get("implementation_branch", "")) or None,
        ))

    # GPT engineering worker slots（激活态的）
    gpt_workers = _load_yaml(root / "coordination" / "ACTIVE-GPT-ENGINEERING-WORKERS.yaml")
    for slot in gpt_workers.get("worker_slots", []):
        if slot.get("execution_allowed"):
            agent_rows.append(AgentRow(
                agent="GPT-WORKER",
                task_id=str(slot.get("task_id", "—")),
                status=str(slot.get("status", "—")),
                execution_allowed=bool(slot.get("execution_allowed", False)),
                merge_authorized=False,
                issue=slot.get("issue") if isinstance(slot.get("issue"), int) else None,
                branch=str(slot.get("branch", "")) or None,
            ))

    return {
        "lanes": lane_rows,
        "agents": agent_rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lanes_meta": {
            "status": lanes.get("status", "?"),
            "decision": lanes.get("current_user_release_policy", {}).get("decision", "?"),
        },
    }


def render(data: dict[str, Any]) -> str:
    def esc(s: Any) -> str:
        return html.escape(str(s))

    lane_rows_html = ""
    for l in data["lanes"]:
        lane_rows_html += f"""
        <tr>
          <td class="mono">{esc(l.lane_id)}</td>
          <td>{esc(l.desired)}</td>
          <td class="obs">{esc(l.observed)}</td>
          <td>{esc(l.owner)}</td>
          <td>{esc(l.implementation_owner)}</td>
          <td class="gate">{esc(l.next_gate)}</td>
          <td>{'<span class="pill no">NO_TRADE</span>' if not l.trading_authorized else '<span class="pill yes">TRADE</span>'}</td>
        </tr>"""

    agent_rows_html = ""
    for a in data["agents"]:
        ready = a.execution_allowed
        merge = a.merge_authorized
        agent_rows_html += f"""
        <tr>
          <td class="mono">{esc(a.agent)}</td>
          <td class="mono">{esc(a.task_id)}</td>
          <td>{esc(a.status)}</td>
          <td>{'<span class="pill yes">ALLOWED</span>' if ready else '<span class="pill no">LOCKED</span>'}</td>
          <td>{'<span class="pill yes">YES</span>' if merge else '<span class="pill no">NO</span>'}</td>
          <td>{f'<a href="https://github.com/vxz2datoubo/second-brain-coordination/issues/{a.issue}">#{a.issue}</a>' if a.issue else '—'}</td>
          <td class="mono">{esc(a.branch or '—')}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>控制塔 · Control Tower Dashboard</title>
<style>
  :root {{
    --bg: #f6f7f9; --card: #ffffff; --border: #e3e6ea;
    --text: #1a2233; --muted: #6b7280;
    --red: #d64545; --green: #2e8b57; --amber: #c98a1b; --blue: #2b6cb0;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
        background: var(--bg); color: var(--text); line-height: 1.5; }}
  header {{ padding: 24px 32px; border-bottom: 1px solid var(--border); background: var(--card); }}
  header h1 {{ margin: 0 0 4px; font-size: 22px; }}
  header .sub {{ color: var(--muted); font-size: 13px; }}
  main {{ padding: 24px 32px; max-width: 1200px; margin: 0 auto; }}
  section {{ margin-bottom: 28px; }}
  h2 {{ font-size: 15px; text-transform: uppercase; letter-spacing: .5px; color: var(--muted); margin: 0 0 12px; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  th {{ background: #f0f2f5; font-weight: 600; color: var(--muted); font-size: 12px; }}
  tr:last-child td {{ border-bottom: none; }}
  .mono {{ font-family: "SFMono-Regular", Consolas, monospace; font-size: 12px; }}
  .obs {{ color: var(--blue); font-size: 12px; }}
  .gate {{ color: var(--amber); font-size: 12px; }}
  .pill {{ display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }}
  .pill.yes {{ background: #e6f4ea; color: var(--green); }}
  .pill.no  {{ background: #fdecea; color: var(--red); }}
  .meta {{ display: flex; gap: 24px; flex-wrap: wrap; color: var(--muted); font-size: 12px; }}
  a {{ color: var(--blue); text-decoration: none; }}
</style>
</head>
<body>
<header>
  <h1>控制塔 · Control Tower</h1>
  <div class="sub">vxz2datoubo/second-brain-coordination · 全自动推进看板 · 生成于 {esc(data['generated_at'])}</div>
</header>
<main>
  <section>
    <h2>全局状态</h2>
    <div class="card"><div class="meta" style="padding:14px">
      <span>Registry: <b>{esc(data['lanes_meta']['status'])}</b></span>
      <span>Release decision: <b>{esc(data['lanes_meta']['decision'])}</b></span>
    </div></div>
  </section>

  <section>
    <h2>Agent 路由</h2>
    <div class="card"><table>
      <thead><tr><th>Agent</th><th>task_id</th><th>status</th><th>execution</th><th>merge</th><th>issue</th><th>branch</th></tr></thead>
      <tbody>{agent_rows_html}</tbody>
    </table></div>
  </section>

  <section>
    <h2>程序泳道</h2>
    <div class="card"><table>
      <thead><tr><th>Lane</th><th>desired</th><th>observed</th><th>owner</th><th>impl</th><th>next gate</th><th>trade</th></tr></thead>
      <tbody>{lane_rows_html}</tbody>
    </table></div>
  </section>
</main>
</body>
</html>
"""


def generate(root: Path, out: Path) -> None:
    data = collect(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(data), encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="生成控制塔 Web 看板")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--out", default="docs/index.html")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    generate(root, Path(args.out))
    print(f"dashboard written to {args.out}")
