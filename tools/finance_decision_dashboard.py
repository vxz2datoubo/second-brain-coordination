"""Build a compact daily decision dashboard for the finance advisor.

The dashboard stitches together the daily pipeline summary, theme/backtest
report, portfolio plan, and optional position monitor into a one-page action
view. It does not fetch live data or make certain predictions.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.finance_plan_review import parse_plan_markdown  # noqa: E402


def load_json(path: Path) -> dict:
    if not path or not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_markdown_tables(path: Path) -> dict[str, list[dict]]:
    if not path.exists():
        return {}
    tables: dict[str, list[dict]] = {}
    section = "root"
    headers: list[str] = []
    rows: list[dict] = []
    in_table = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            if headers and rows:
                tables[section] = rows
            section = line.lstrip("#").strip()
            headers = []
            rows = []
            in_table = False
            continue
        if not line.startswith("|"):
            if in_table and headers and rows:
                tables[section] = rows
                headers = []
                rows = []
            in_table = False
            continue
        if "---" in line:
            in_table = True
            continue
        cells = split_table_row(line)
        if not headers:
            headers = cells
            rows = []
            in_table = True
            continue
        if len(cells) < len(headers):
            continue
        rows.append({headers[i]: cells[i] for i in range(len(headers))})
    if headers and rows:
        tables[section] = rows
    return tables


def first_existing(paths: list[str]) -> Path | None:
    for path in paths:
        if path and Path(path).exists():
            return Path(path)
    return None


def pick_table(tables: dict[str, list[dict]], *keywords: str) -> list[dict]:
    for name, rows in tables.items():
        if all(keyword in name for keyword in keywords):
            return rows
    return []


def to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value).strip().replace("%", ""))
    except (TypeError, ValueError):
        return default


def build_dashboard(
    pipeline: dict,
    daily_tables: dict[str, list[dict]],
    plans: dict[str, dict],
    position_monitor: dict | None = None,
    theme_trends: dict | None = None,
    edge_audit: dict | None = None,
) -> dict:
    position_monitor = position_monitor or {}
    theme_trends = theme_trends or {}
    edge_audit = edge_audit or {}
    themes = pick_table(daily_tables, "题材") or pick_table(daily_tables, "棰樻潗")
    backtests = pick_table(daily_tables, "回测") or pick_table(daily_tables, "洖娴")
    plan_rows = sorted(
        [row for row in plans.values() if row.get("allowed")],
        key=lambda row: to_float(row.get("score")),
        reverse=True,
    )
    positions = position_monitor.get("positions") or []
    risk_actions = [row for row in positions if row.get("status") == "action_required"]
    watch_positions = [row for row in positions if row.get("status") == "watch"]

    hot_themes = []
    for row in themes[:5]:
        hot_themes.append({
            "rank": row.get("排名") or row.get("鎺掑悕") or "",
            "theme": row.get("题材") or row.get("棰樻潗") or "",
            "stage": row.get("阶段") or row.get("闃舵") or "",
            "risk": row.get("风险") or row.get("椋庨櫓") or "",
            "priority": row.get("优先级") or row.get("浼樺厛绾") or "",
            "suggestion": row.get("建议") or row.get("寤鸿") or "",
        })

    candidates = []
    by_symbol = {str(row.get("symbol", "")): row for row in plan_rows}
    for row in backtests:
        symbol = row.get("标的") or row.get("鏍囩殑") or ""
        plan = by_symbol.get(symbol, {})
        candidates.append({
            "symbol": symbol,
            "name": row.get("名称") or row.get("鍚嶇О") or plan.get("name", ""),
            "theme": row.get("题材") or row.get("棰樻潗") or plan.get("theme", ""),
            "stage": row.get("题材阶段") or row.get("棰樻潗闃舵") or "",
            "strategy": row.get("最佳策略") or row.get("鏈€浣崇瓥鐣") or plan.get("strategy", ""),
            "candidate_score": row.get("候选分") or row.get("鍊欓€夊垎") or plan.get("score", ""),
            "entry": plan.get("entry", ""),
            "stop": plan.get("stop", ""),
            "qty": plan.get("qty", ""),
            "risk_pct": plan.get("risk_pct", ""),
            "action": row.get("动作") or row.get("鍔ㄤ綔") or "",
        })
    if not candidates:
        for plan in plan_rows:
            candidates.append({
                "symbol": plan.get("symbol", ""),
                "name": plan.get("name", ""),
                "theme": plan.get("theme", ""),
                "stage": "",
                "strategy": plan.get("strategy", ""),
                "candidate_score": plan.get("score", ""),
                "entry": plan.get("entry", ""),
                "stop": plan.get("stop", ""),
                "qty": plan.get("qty", ""),
                "risk_pct": plan.get("risk_pct", ""),
                "action": "按计划观察，交易前 consult",
            })

    gates = []
    if pipeline.get("quality_failed", 0):
        gates.append(f"行情质量失败 {pipeline.get('quality_failed')} 个，失败标的不交易")
    if pipeline.get("market_regime") == "risk_off":
        gates.append("市场温度 risk_off，只允许降风险，不放大仓位")
    if risk_actions:
        gates.append("存在持仓风险处理项，先处理持仓再开新仓")
    if pipeline.get("risk_mode") in {"cautious", "freeze"}:
        gates.append(f"风控模式 {pipeline.get('risk_mode')}，按节流后的仓位执行")
    gates.extend([
        "未进入组合计划的标的不交易",
        "下单前必须通过 pretrade check 或 /api/finance/consult",
        "触发止损先执行，不用补仓掩盖亏损",
    ])

    next_actions = []
    if risk_actions:
        next_actions.append("先处理 action_required 持仓")
    if candidates:
        next_actions.append("只从计划内候选里等待入场条件")
    if hot_themes:
        next_actions.append("复核排名靠前题材是否处于启动/确认/分歧，而非高潮退潮")
    next_actions.append("盘后记录真实交易并跑 plan_review/risk_state")
    trend_rows = []
    for row in (theme_trends.get("themes") or [])[:8]:
        trend_rows.append({
            "theme": row.get("theme", ""),
            "trend": row.get("trend", ""),
            "active_days": row.get("active_days", 0),
            "latest_score": row.get("latest_score", 0),
            "score_change": row.get("score_change", 0),
            "latest_lifecycle": row.get("latest_lifecycle", ""),
            "latest_risk": row.get("latest_risk", ""),
        })

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "date": pipeline.get("date", ""),
        "risk": {
            "mode": pipeline.get("risk_mode", "normal"),
            "market_regime": pipeline.get("market_regime", "unknown"),
            "market_risk_multiplier": pipeline.get("market_risk_multiplier", 1.0),
            "risk_per_trade": pipeline.get("risk_per_trade"),
            "max_position_pct": pipeline.get("max_position_pct"),
            "max_total_exposure": pipeline.get("max_total_exposure"),
            "max_theme_exposure_pct": pipeline.get("max_theme_exposure_pct"),
            "planned_exposure": pipeline.get("planned_exposure", 0),
            "risk_reasons": pipeline.get("risk_reasons", []),
        },
        "counts": {
            "watchlist": pipeline.get("watchlist_count", 0),
            "themes": pipeline.get("themes_count", len(hot_themes)),
            "backtests": pipeline.get("backtests_count", len(candidates)),
            "selected": pipeline.get("selected_count", len(candidates)),
            "open_positions": position_monitor.get("open_count", 0),
            "position_action_required": position_monitor.get("action_required", 0),
        },
        "hot_themes": hot_themes,
        "theme_trends": trend_rows,
        "edge_audit": {
            "verdict": edge_audit.get("verdict", pipeline.get("edge_verdict", "")),
            "edge_score": edge_audit.get("edge_score", pipeline.get("edge_score", "")),
            "risk_action": edge_audit.get("risk_action", pipeline.get("edge_risk_action", "")),
            "reasons": (edge_audit.get("reasons") or [])[:5],
            "actions": (edge_audit.get("actions") or [])[:5],
        },
        "candidates": candidates[:10],
        "risk_actions": risk_actions,
        "watch_positions": watch_positions,
        "gates": gates,
        "next_actions": next_actions,
        "sources": {
            "pipeline": pipeline.get("pipeline_path", ""),
            "daily_report": pipeline.get("daily_report_path", ""),
            "portfolio_plan": pipeline.get("portfolio_plan_path", ""),
            "position_monitor": position_monitor.get("source_path", ""),
            "theme_trends": theme_trends.get("source_path", ""),
            "edge_audit": edge_audit.get("source_path", pipeline.get("edge_audit_json_path", "")),
        },
    }


def md_escape(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_markdown(dashboard: dict) -> str:
    risk = dashboard["risk"]
    counts = dashboard["counts"]
    lines = [
        f"# 炒股 AI 每日决策面板 - {dashboard['date']}",
        "",
        "用途：把题材热度、回测候选、仓位计划、持仓风险合成一页执行清单。不构成投资建议，不保证盈利。",
        "",
        "## 今日结论",
        "",
        f"- 风控模式: {risk['mode']}",
        f"- 市场环境: {risk['market_regime']}，风险倍率 {risk['market_risk_multiplier']}",
        f"- 观察池: {counts['watchlist']}，热点题材: {counts['themes']}，计划内候选: {counts['selected']}",
        f"- 未平仓持仓: {counts['open_positions']}，需先处理: {counts['position_action_required']}",
        f"- 计划总暴露: {risk['planned_exposure']}",
        "",
        "## 先做什么",
        "",
    ]
    lines.extend([f"- {item}" for item in dashboard["next_actions"]])
    lines.extend(["", "## 风控闸门", ""])
    lines.extend([f"- {item}" for item in dashboard["gates"]])
    if risk.get("risk_reasons"):
        lines.extend(["", "## 降风险原因", ""])
        lines.extend([f"- {reason}" for reason in risk["risk_reasons"]])

    edge = dashboard.get("edge_audit") or {}
    lines.extend([
        "",
        "## 盈利边际审计",
        "",
        f"- Verdict: {edge.get('verdict', '') or '未提供'}",
        f"- Edge score: {edge.get('edge_score', '')}",
        f"- Risk action: {edge.get('risk_action', '')}",
    ])
    if edge.get("reasons"):
        lines.extend(["", "审计理由:"])
        lines.extend([f"- {reason}" for reason in edge["reasons"]])
    if edge.get("actions"):
        lines.extend(["", "建议动作:"])
        lines.extend([f"- {action}" for action in edge["actions"]])

    lines.extend([
        "",
        "## 最近题材趋势",
        "",
        "| 题材 | 趋势 | 活跃天数 | 最新热度 | 热度变化 | 最新阶段 | 最新风险 |",
        "|---|---|---:|---:|---:|---|---|",
    ])
    if dashboard.get("theme_trends"):
        for row in dashboard["theme_trends"]:
            lines.append(
                f"| {md_escape(row['theme'])} | {md_escape(row['trend'])} | {row['active_days']} | "
                f"{row['latest_score']} | {row['score_change']} | {md_escape(row['latest_lifecycle'])} | "
                f"{md_escape(row['latest_risk'])} |"
            )
    else:
        lines.append("| - | - | 0 | 0 | 0 | - | 未提供多日趋势报告 |")

    lines.extend([
        "",
        "## 热门题材",
        "",
        "| 排名 | 题材 | 阶段 | 风险 | 优先级 | 建议 |",
        "|---:|---|---|---|---:|---|",
    ])
    if dashboard["hot_themes"]:
        for row in dashboard["hot_themes"]:
            lines.append(
                f"| {md_escape(row['rank'])} | {md_escape(row['theme'])} | {md_escape(row['stage'])} | "
                f"{md_escape(row['risk'])} | {md_escape(row['priority'])} | {md_escape(row['suggestion'])} |"
            )
    else:
        lines.append("| - | - | - | - | - | 未找到题材表 |")

    lines.extend([
        "",
        "## 计划内候选",
        "",
        "| 标的 | 名称 | 题材 | 策略 | 候选分 | 入场 | 止损 | 数量 | 风险 | 动作 |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---|",
    ])
    if dashboard["candidates"]:
        for row in dashboard["candidates"]:
            lines.append(
                f"| {md_escape(row['symbol'])} | {md_escape(row['name'])} | {md_escape(row['theme'])} | "
                f"{md_escape(row['strategy'])} | {md_escape(row['candidate_score'])} | {md_escape(row['entry'])} | "
                f"{md_escape(row['stop'])} | {md_escape(row['qty'])} | {md_escape(row['risk_pct'])} | "
                f"{md_escape(row['action'])} |"
            )
    else:
        lines.append("| - | - | - | - | 0 | 0 | 0 | 0 | 0 | 今日无计划内候选 |")

    lines.extend([
        "",
        "## 持仓风险",
        "",
        "| 状态 | 标的 | 数量 | 收盘 | 止损 | 浮盈亏 | 问题 |",
        "|---|---|---:|---:|---:|---:|---|",
    ])
    rows = dashboard["risk_actions"] + dashboard["watch_positions"]
    if rows:
        for row in rows:
            notes = "；".join((row.get("issues") or []) + (row.get("warnings") or []))
            lines.append(
                f"| {md_escape(row.get('status', ''))} | {md_escape(row.get('symbol', ''))} | "
                f"{md_escape(row.get('qty', ''))} | {md_escape(row.get('latest_close', ''))} | "
                f"{md_escape(row.get('stop', ''))} | {md_escape(row.get('unrealized_pnl', ''))} | "
                f"{md_escape(notes or '无')} |"
            )
    else:
        lines.append("| ok | - | 0 | 0 | 0 | 0 | 无需先处理的持仓风险 |")

    sources = dashboard["sources"]
    lines.extend([
        "",
        "## 来源",
        "",
        f"- 流水线: `{sources.get('pipeline', '')}`",
        f"- 日报: `{sources.get('daily_report', '')}`",
        f"- 仓位计划: `{sources.get('portfolio_plan', '')}`",
        f"- 持仓监控: `{sources.get('position_monitor', '')}`",
        f"- 题材趋势: `{sources.get('theme_trends', '')}`",
        f"- 盈利边际审计: `{sources.get('edge_audit', '')}`",
        f"- 生成时间: {dashboard['generated_at']}",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the daily finance decision dashboard.")
    parser.add_argument("--pipeline", required=True)
    parser.add_argument("--daily-report", default="")
    parser.add_argument("--portfolio-plan", default="")
    parser.add_argument("--position-monitor", default="")
    parser.add_argument("--theme-trends", default="")
    parser.add_argument("--edge-audit", default="")
    parser.add_argument("--date", default="")
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    args = parser.parse_args()

    pipeline_path = Path(args.pipeline)
    pipeline = load_json(pipeline_path)
    pipeline["pipeline_path"] = str(pipeline_path)
    date = args.date or pipeline.get("date") or datetime.now().strftime("%Y-%m-%d")
    pipeline["date"] = date

    daily_path = first_existing([args.daily_report, pipeline.get("daily_report_path", "")])
    plan_path = first_existing([args.portfolio_plan, pipeline.get("portfolio_plan_path", "")])
    position_path = first_existing([args.position_monitor, str(pipeline_path.parent / f"finance-position-monitor-{date}.json")])
    theme_trends_path = first_existing([args.theme_trends, str(pipeline_path.parent / f"finance-theme-trends-{date}.json")])
    edge_audit_path = first_existing([args.edge_audit, str(pipeline_path.parent / f"finance-edge-audit-{date}.json")])

    daily_tables = parse_markdown_tables(daily_path) if daily_path else {}
    plans = parse_plan_markdown(plan_path) if plan_path else {}
    position_monitor = load_json(position_path) if position_path else {}
    if position_monitor:
        position_monitor["source_path"] = str(position_path)
    theme_trends = load_json(theme_trends_path) if theme_trends_path else {}
    if theme_trends:
        theme_trends["source_path"] = str(theme_trends_path)
    edge_audit = load_json(edge_audit_path) if edge_audit_path else {}
    if edge_audit:
        edge_audit["source_path"] = str(edge_audit_path)

    dashboard = build_dashboard(pipeline, daily_tables, plans, position_monitor, theme_trends, edge_audit)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"finance-decision-dashboard-{date}.json"
    md_path = output_dir / f"finance-decision-dashboard-{date}.md"
    json_path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(dashboard), encoding="utf-8")
    print(json.dumps({
        "success": True,
        "date": date,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "selected": dashboard["counts"]["selected"],
        "position_action_required": dashboard["counts"]["position_action_required"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
