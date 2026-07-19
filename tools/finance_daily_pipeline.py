"""One-command daily pipeline for the stock AI advisor.

Pipeline:
1. Scan local market CSV directory and build watchlist.
2. Generate daily theme/backtest report.
3. Generate portfolio risk/position plan.
4. Optionally ingest reports into Second Brain.
5. Write a compact pipeline summary.

Stdlib-only orchestration. The individual tools own the actual calculations.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.finance_build_watchlist import build_watchlist, load_meta  # noqa: E402
from tools.finance_daily_report import (  # noqa: E402
    ingest_report as ingest_daily_report,
    load_jsonl,
    load_watchlist,
    render_report as render_daily_report,
    run_watchlist_backtests,
)
from tools.finance_data_quality import check_market_dir, render_markdown as render_quality_report  # noqa: E402
from tools.finance_decision_dashboard import (  # noqa: E402
    build_dashboard,
    load_json as load_dashboard_json,
    parse_markdown_tables,
    render_markdown as render_dashboard_markdown,
)
from tools.finance_edge_audit import build_edge_audit, discover as discover_edge_reports, render_markdown as render_edge_audit  # noqa: E402
from tools.finance_market_regime import analyze_market_regime, render_markdown as render_regime_report  # noqa: E402
from tools.finance_plan_review import parse_plan_markdown  # noqa: E402
from tools.finance_portfolio_plan import (  # noqa: E402
    build_plan,
    ingest_report as ingest_plan_report,
    load_watchlist as load_plan_watchlist,
    render_report as render_plan_report,
)
from tools.finance_theme_trends import analyze_theme_trends, load_daily_series, render_markdown as render_theme_trends  # noqa: E402
from core.finance_advisor import analyze_hot_themes, score_watchlist_candidates  # noqa: E402


DEFAULTS = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "market_dir": "",
    "market_meta": "",
    "items": "",
    "output_dir": str(ROOT / "qclaw-output"),
    "min_bars": 120,
    "strategy": "optimize",
    "account_equity": 100000.0,
    "risk_per_trade": 0.005,
    "max_position_pct": 0.2,
    "max_total_exposure": 0.6,
    "max_theme_exposure_pct": 0.35,
    "atr_multiple": 2.0,
    "min_score": 15.0,
    "risk_state": str(ROOT / "qclaw-output" / "finance-risk-state.json"),
    "quality_check": True,
    "quality_min_score": 70,
    "quality_max_gap_business_days": 10,
    "quality_max_abs_return": 0.35,
    "signal_scorecard": str(ROOT / "qclaw-output" / "finance-signal-scorecard.json"),
    "paper_scorecard": str(ROOT / "qclaw-output" / "finance-paper-scorecard.json"),
    "market_index_csv": "",
    "market_breadth": "",
    "theme_trend_days": 10,
    "trade_journal": str(ROOT / "qclaw-output" / "finance-trade-journal.jsonl"),
    "edge_horizon": 3,
    "ingest": False,
    "brain_url": "http://localhost:8766",
}


def load_config(path: str) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config not found: {p}")
    with p.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    return data


def resolve_args(args: argparse.Namespace) -> argparse.Namespace:
    config = load_config(args.config)
    values = dict(DEFAULTS)
    unknown = sorted(set(config) - set(values))
    if unknown:
        raise ValueError(f"unknown config keys: {', '.join(unknown)}")
    values.update(config)

    for key in values:
        cli_value = getattr(args, key, None)
        if cli_value is not None:
            values[key] = cli_value

    missing = [key for key in ("market_dir", "items") if not values.get(key)]
    if missing:
        raise ValueError(f"missing required option(s): {', '.join(missing)}")

    return argparse.Namespace(config=args.config, **values)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_risk_state(path: str) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_signal_scorecard(path: str) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def apply_signal_scorecard(backtests: list[dict], scorecard: dict) -> list[dict]:
    themes = scorecard.get("themes") or {}
    if not themes:
        return backtests
    adjusted = []
    for item in backtests:
        row = dict(item)
        theme = str(row.get("theme", ""))
        score_info = themes.get(theme, {})
        adjustment = float(score_info.get("score_adjustment", 0) or 0)
        original = float(row.get("candidate_score", 0) or 0)
        row["candidate_score_raw"] = round(original, 2)
        row["signal_score_adjustment"] = round(adjustment, 2)
        row["signal_score_sample_count"] = score_info.get("count", 0)
        row["candidate_score"] = round(original + adjustment, 2)
        if adjustment > 0:
            row["candidate_action"] = f"{row.get('candidate_action', '')}；历史前向表现加分"
        elif adjustment < 0:
            row["candidate_action"] = f"{row.get('candidate_action', '')}；历史前向表现扣分"
        adjusted.append(row)
    return sorted(adjusted, key=lambda x: x.get("candidate_score", 0), reverse=True)


def apply_paper_scorecard(backtests: list[dict], scorecard: dict) -> list[dict]:
    themes = scorecard.get("themes") or {}
    if not themes:
        return backtests
    adjusted = []
    for item in backtests:
        row = dict(item)
        theme = str(row.get("theme", ""))
        score_info = themes.get(theme, {})
        adjustment = float(score_info.get("score_adjustment", 0) or 0)
        original = float(row.get("candidate_score", 0) or 0)
        if "candidate_score_raw" not in row:
            row["candidate_score_raw"] = round(original, 2)
        row["paper_score_adjustment"] = round(adjustment, 2)
        row["paper_score_sample_count"] = score_info.get("count", 0)
        row["paper_score_net_pnl"] = score_info.get("net_pnl", 0)
        row["candidate_score"] = round(original + adjustment, 2)
        if adjustment > 0:
            row["candidate_action"] = f"{row.get('candidate_action', '')}；纸面交易反馈加分"
        elif adjustment < 0:
            row["candidate_action"] = f"{row.get('candidate_action', '')}；纸面交易反馈扣分"
        adjusted.append(row)
    return sorted(adjusted, key=lambda x: x.get("candidate_score", 0), reverse=True)


def filter_watchlist_by_quality(watchlist_path: Path, quality_report: dict, min_score: float) -> dict:
    allowed = {
        item["path"]: item
        for item in quality_report.get("files", [])
        if item.get("status") == "pass" and float(item.get("score", 0)) >= min_score
    }
    with watchlist_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    kept = []
    skipped = []
    for row in rows:
        csv_path = str(row.get("csv_path", "")).replace("\\", "/")
        if csv_path in allowed:
            kept.append(row)
        else:
            skipped.append({
                "symbol": row.get("symbol", ""),
                "name": row.get("name", ""),
                "csv_path": csv_path,
                "reason": "quality_check_failed",
            })

    with watchlist_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)

    return {"kept": len(kept), "skipped": skipped}


def render_summary(summary: dict) -> str:
    lines = [
        f"# 炒股 AI 日更流水线摘要 - {summary['date']}",
        "",
        "用途: 一键生成观察池、每日题材回测报告、组合仓位风控计划，并可摄入第二大脑。",
        "",
        "## 结果",
        "",
        f"- 观察池文件: `{summary['watchlist_path']}`",
        f"- 观察池标的数: {summary['watchlist_count']}",
        f"- 行情质量报告: `{summary.get('quality_report_path', '')}`",
        f"- 行情质量失败数: {summary.get('quality_failed', 0)}",
        f"- 质量过滤剔除数: {summary.get('quality_skipped_count', 0)}",
        f"- 日报文件: `{summary['daily_report_path']}`",
        f"- 题材数: {summary['themes_count']}",
        f"- 回测标的数: {summary['backtests_count']}",
        f"- 信号评分卡: `{summary.get('signal_scorecard_path', '')}`",
        f"- 信号评分卡题材数: {summary.get('signal_scorecard_themes', 0)}",
        f"- 纸面评分卡: `{summary.get('paper_scorecard_path', '')}`",
        f"- 纸面评分卡题材数: {summary.get('paper_scorecard_themes', 0)}",
        f"- 市场环境报告: `{summary.get('market_regime_path', '')}`",
        f"- 市场环境: {summary.get('market_regime', 'unknown')} ({summary.get('market_risk_multiplier', 1.0)})",
        f"- 盈利边际审计: `{summary.get('edge_audit_path', '')}`",
        f"- 盈利边际结论: {summary.get('edge_verdict', '')} ({summary.get('edge_score', '')})",
        f"- 盈利边际风控动作: {summary.get('edge_risk_action', '')}",
        f"- 仓位计划文件: `{summary['portfolio_plan_path']}`",
        f"- 允许交易候选数: {summary['selected_count']}",
        f"- 计划总暴露: {summary['planned_exposure']}",
        f"- 风控模式: {summary.get('risk_mode', 'normal')}",
        f"- 单笔风险: {summary.get('risk_per_trade')}",
        f"- 单标的仓位上限: {summary.get('max_position_pct')}",
        f"- 组合总暴露上限: {summary.get('max_total_exposure')}",
        f"- 单题材暴露上限: {summary.get('max_theme_exposure_pct')}",
        "",
        "## 第二大脑摄入",
        "",
    ]
    daily_node = summary.get("daily_ingest_node") or {}
    plan_node = summary.get("plan_ingest_node") or {}
    daily_status = "已存在，跳过摄入" if summary.get("daily_ingest_skipped") else "新摄入"
    plan_status = "已存在，跳过摄入" if summary.get("plan_ingest_skipped") else "新摄入"
    if not daily_node:
        daily_status = "未摄入"
    if not plan_node:
        plan_status = "未摄入"
    lines.extend([
        f"- 日报节点: {daily_node.get('id', '未摄入')} {daily_node.get('title', '')} ({daily_status})",
        f"- 仓位计划节点: {plan_node.get('id', '未摄入')} {plan_node.get('title', '')} ({plan_status})",
        "",
        "## 风控调整原因",
        "",
    ])
    reasons = summary.get("risk_reasons") or []
    if reasons:
        lines.extend([f"- {reason}" for reason in reasons])
    else:
        lines.append("- 无额外风控节流。")
    lines.extend([
        "",
        "## 下一步",
        "",
        "- 先看题材生命周期，避开高潮和退潮。",
        "- 再看观察池候选分和策略分。",
        "- 最后按仓位计划执行；未列入计划的不交易。",
        "- 下单前调用 `/api/finance/consult` 做红线检查。",
        "- 盘后用 `finance_trade_journal.py` 记录真实交易并归因。",
        "- 盘后用 `finance_plan_review.py` 对照仓位计划检查是否超量、追高或计划外交易。",
    ])
    return "\n".join(lines) + "\n"


def render_summary(summary: dict) -> str:
    lines = [
        f"# 炒股 AI 每日流水线摘要 - {summary['date']}",
        "",
        "用途: 一键生成观察池、每日题材回测报告、组合仓位风控计划，并可摄入第二大脑。",
        "",
        "## 结果",
        "",
        f"- 观察池文件: `{summary['watchlist_path']}`",
        f"- 观察池标的数: {summary['watchlist_count']}",
        f"- 日报文件: `{summary['daily_report_path']}`",
        f"- 题材数: {summary['themes_count']}",
        f"- 回测标的数: {summary['backtests_count']}",
        f"- 仓位计划文件: `{summary['portfolio_plan_path']}`",
        f"- 允许交易候选数: {summary['selected_count']}",
        f"- 计划总暴露: {summary['planned_exposure']}",
        f"- 风控模式: {summary.get('risk_mode', 'normal')}",
        f"- 单笔风险: {summary.get('risk_per_trade')}",
        f"- 单标的仓位上限: {summary.get('max_position_pct')}",
        f"- 组合总暴露上限: {summary.get('max_total_exposure')}",
        f"- 单题材暴露上限: {summary.get('max_theme_exposure_pct')}",
        "",
        "## 第二大脑摄入",
        "",
    ]
    daily_node = summary.get("daily_ingest_node") or {}
    plan_node = summary.get("plan_ingest_node") or {}
    lines.extend([
        f"- 日报节点: {daily_node.get('id', '未摄入')} {daily_node.get('title', '')}",
        f"- 仓位计划节点: {plan_node.get('id', '未摄入')} {plan_node.get('title', '')}",
        "",
        "## 风控调整原因",
        "",
    ])
    reasons = summary.get("risk_reasons") or []
    if reasons:
        lines.extend([f"- {reason}" for reason in reasons])
    else:
        lines.append("- 无额外风控节流。")
    lines.extend([
        "",
        "## 下一步",
        "",
        "- 先看题材生命周期，避开高潮和退潮。",
        "- 再看观察池候选分和策略分。",
        "- 最后按仓位计划执行；未列入计划的不交易。",
        "- 下单前调用 `/api/finance/consult` 做红线检查。",
        "- 盘后用 `finance_trade_journal.py` 记录真实交易并归因。",
        "- 盘后用 `finance_plan_review.py` 对照仓位计划检查是否超量、追高或计划外交易。",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run daily finance advisor pipeline.")
    parser.add_argument("--config", default="", help="JSON config file; CLI options override it")
    parser.add_argument("--date", default=None)
    parser.add_argument("--market-dir", default=None)
    parser.add_argument("--market-meta", default=None)
    parser.add_argument("--items", default=None, help="Daily theme/news JSONL")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--min-bars", type=int, default=None)
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--account-equity", type=float, default=None)
    parser.add_argument("--risk-per-trade", type=float, default=None)
    parser.add_argument("--max-position-pct", type=float, default=None)
    parser.add_argument("--max-total-exposure", type=float, default=None)
    parser.add_argument("--max-theme-exposure-pct", type=float, default=None)
    parser.add_argument("--atr-multiple", type=float, default=None)
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--risk-state", default=None)
    parser.add_argument("--quality-check", action="store_true", default=None)
    parser.add_argument("--skip-quality-check", action="store_false", dest="quality_check")
    parser.add_argument("--quality-min-score", type=float, default=None)
    parser.add_argument("--quality-max-gap-business-days", type=int, default=None)
    parser.add_argument("--quality-max-abs-return", type=float, default=None)
    parser.add_argument("--signal-scorecard", default=None)
    parser.add_argument("--paper-scorecard", default=None)
    parser.add_argument("--market-index-csv", default=None)
    parser.add_argument("--market-breadth", default=None)
    parser.add_argument("--theme-trend-days", type=int, default=None)
    parser.add_argument("--trade-journal", default=None)
    parser.add_argument("--edge-horizon", type=int, default=None)
    parser.add_argument("--ingest", action="store_true", default=None)
    parser.add_argument("--no-ingest", action="store_false", dest="ingest")
    parser.add_argument("--brain-url", default=None)
    args = resolve_args(parser.parse_args())

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    risk_state = load_risk_state(args.risk_state)
    risk_per_trade = float(risk_state.get("risk_per_trade", args.risk_per_trade))
    max_position_pct = float(risk_state.get("max_position_pct", args.max_position_pct))
    max_total_exposure = float(risk_state.get("max_total_exposure", args.max_total_exposure))
    max_theme_exposure_pct = float(risk_state.get("max_theme_exposure_pct", args.max_theme_exposure_pct))

    market_regime = {}
    market_regime_path = ""
    if args.market_index_csv or args.market_breadth:
        market_regime = analyze_market_regime(args.market_index_csv or "", args.market_breadth or "")
        regime_json_path = output_dir / f"finance-market-regime-{args.date}.json"
        regime_md_path = output_dir / f"finance-market-regime-{args.date}.md"
        write_text(regime_json_path, json.dumps(market_regime, ensure_ascii=False, indent=2))
        write_text(regime_md_path, render_regime_report(market_regime))
        market_regime_path = str(regime_md_path)
        market_multiplier = float(market_regime.get("risk_multiplier", 1.0) or 1.0)
        risk_per_trade = round(risk_per_trade * market_multiplier, 6)
        max_position_pct = round(max_position_pct * market_multiplier, 6)
        max_total_exposure = round(max_total_exposure * max(market_multiplier, 0.25), 6)
        max_theme_exposure_pct = round(max_theme_exposure_pct * max(market_multiplier, 0.25), 6)

    quality_report = None
    quality_report_path = ""
    quality_skipped = []
    if args.quality_check:
        quality_report = check_market_dir(
            Path(args.market_dir),
            min_bars=args.min_bars,
            max_gap_business_days=args.quality_max_gap_business_days,
            max_abs_return=args.quality_max_abs_return,
        )
        quality_json_path = output_dir / f"finance-data-quality-{args.date}.json"
        quality_md_path = output_dir / f"finance-data-quality-{args.date}.md"
        write_text(quality_json_path, json.dumps(quality_report, ensure_ascii=False, indent=2))
        write_text(quality_md_path, render_quality_report(quality_report))
        quality_report_path = str(quality_md_path)

    watchlist_path = output_dir / f"finance-watchlist-{args.date}.csv"
    watchlist_result = build_watchlist(
        Path(args.market_dir),
        watchlist_path,
        meta=load_meta(args.market_meta),
        min_bars=args.min_bars,
        strategy=args.strategy,
    )
    if quality_report:
        filtered = filter_watchlist_by_quality(watchlist_path, quality_report, args.quality_min_score)
        quality_skipped = filtered["skipped"]
        watchlist_result["quality_skipped"] = quality_skipped
        watchlist_result["count"] = filtered["kept"]

    input_path = Path(args.items)
    items = load_jsonl(input_path)
    trends = analyze_hot_themes(items, top_k=10)
    raw_backtests = run_watchlist_backtests(load_watchlist(watchlist_path))
    backtests = score_watchlist_candidates(raw_backtests, trends.get("themes", []))
    signal_scorecard = load_signal_scorecard(args.signal_scorecard)
    backtests = apply_signal_scorecard(backtests, signal_scorecard)
    paper_scorecard = load_signal_scorecard(args.paper_scorecard)
    backtests = apply_paper_scorecard(backtests, paper_scorecard)
    daily_report = render_daily_report(trends, backtests, args.date, input_path)
    daily_report_path = output_dir / f"finance-daily-report-{args.date}.md"
    write_text(daily_report_path, daily_report)

    plan = build_plan(
        load_plan_watchlist(watchlist_path),
        account_equity=args.account_equity,
        risk_per_trade=risk_per_trade,
        max_position_pct=max_position_pct,
        max_total_exposure=max_total_exposure,
        max_theme_exposure_pct=max_theme_exposure_pct,
        atr_multiple=args.atr_multiple,
        min_score=args.min_score,
    )
    plan_report = render_plan_report(plan, args.date, watchlist_path)
    plan_report_path = output_dir / f"finance-portfolio-plan-{args.date}.md"
    write_text(plan_report_path, plan_report)

    daily_ingest = None
    plan_ingest = None
    if args.ingest:
        daily_ingest = ingest_daily_report(daily_report, f"股市 AI 每日题材与回测报告 - {args.date}", args.brain_url)
        plan_ingest = ingest_plan_report(plan_report, f"组合仓位与风险计划 - {args.date}", args.brain_url)

    summary = {
        "date": args.date,
        "watchlist_path": str(watchlist_path),
        "watchlist_count": watchlist_result["count"],
        "watchlist_skipped": watchlist_result["skipped"],
        "quality_report_path": quality_report_path,
        "quality_count": (quality_report or {}).get("count", 0),
        "quality_failed": (quality_report or {}).get("failed", 0),
        "quality_warned": (quality_report or {}).get("warned", 0),
        "quality_skipped": quality_skipped,
        "quality_skipped_count": len(quality_skipped),
        "daily_report_path": str(daily_report_path),
        "themes_count": len(trends.get("themes", [])),
        "backtests_count": len(backtests),
        "signal_scorecard_path": args.signal_scorecard if signal_scorecard else "",
        "signal_scorecard_themes": len((signal_scorecard or {}).get("themes", {})),
        "paper_scorecard_path": args.paper_scorecard if paper_scorecard else "",
        "paper_scorecard_themes": len((paper_scorecard or {}).get("themes", {})),
        "market_regime_path": market_regime_path,
        "market_regime": market_regime.get("regime", ""),
        "market_regime_score": market_regime.get("score", 0),
        "market_risk_multiplier": market_regime.get("risk_multiplier", 1.0),
        "market_regime_reasons": market_regime.get("reasons", []),
        "portfolio_plan_path": str(plan_report_path),
        "selected_count": plan["selected_count"],
        "planned_exposure": plan["planned_exposure"],
        "risk_mode": risk_state.get("mode", "normal"),
        "risk_per_trade": risk_per_trade,
        "max_position_pct": max_position_pct,
        "max_total_exposure": max_total_exposure,
        "max_theme_exposure_pct": max_theme_exposure_pct,
        "risk_reasons": risk_state.get("reasons", []),
        "daily_ingest_node": (daily_ingest or {}).get("node"),
        "plan_ingest_node": (plan_ingest or {}).get("node"),
        "daily_ingest_skipped": (daily_ingest or {}).get("skipped"),
        "plan_ingest_skipped": (plan_ingest or {}).get("skipped"),
    }
    summary_json_path = output_dir / f"finance-daily-pipeline-{args.date}.json"
    summary_md_path = output_dir / f"finance-daily-pipeline-{args.date}.md"
    dashboard_json_path = output_dir / f"finance-decision-dashboard-{args.date}.json"
    dashboard_md_path = output_dir / f"finance-decision-dashboard-{args.date}.md"
    position_monitor_path = output_dir / f"finance-position-monitor-{args.date}.json"
    theme_trends_json_path = output_dir / f"finance-theme-trends-{args.date}.json"
    theme_trends_md_path = output_dir / f"finance-theme-trends-{args.date}.md"
    edge_audit_json_path = output_dir / f"finance-edge-audit-{args.date}.json"
    edge_audit_md_path = output_dir / f"finance-edge-audit-{args.date}.md"
    summary["pipeline_path"] = str(summary_json_path)
    summary["decision_dashboard_json_path"] = str(dashboard_json_path)
    summary["decision_dashboard_path"] = str(dashboard_md_path)
    summary["theme_trends_json_path"] = str(theme_trends_json_path)
    summary["theme_trends_path"] = str(theme_trends_md_path)
    edge_audit = build_edge_audit(
        Path(args.trade_journal),
        discover_edge_reports(output_dir, "finance-paper-trade-*.json"),
        discover_edge_reports(output_dir, "finance-forward-eval-*.json"),
        args.edge_horizon,
    )
    edge_audit["source_path"] = str(edge_audit_json_path)
    write_text(edge_audit_json_path, json.dumps(edge_audit, ensure_ascii=False, indent=2))
    write_text(edge_audit_md_path, render_edge_audit(edge_audit))
    summary["edge_audit_json_path"] = str(edge_audit_json_path)
    summary["edge_audit_path"] = str(edge_audit_md_path)
    summary["edge_verdict"] = edge_audit["verdict"]
    summary["edge_score"] = edge_audit["edge_score"]
    summary["edge_risk_action"] = edge_audit["risk_action"]
    theme_series = load_daily_series(output_dir, "finance-daily-items-*.jsonl", "finance-daily-report-*.md", args.theme_trend_days)
    theme_trends = analyze_theme_trends(theme_series) if theme_series else {}
    if theme_trends:
        theme_trends["source_path"] = str(theme_trends_json_path)
        write_text(theme_trends_json_path, json.dumps(theme_trends, ensure_ascii=False, indent=2))
        write_text(theme_trends_md_path, render_theme_trends(theme_trends, theme_trends_json_path))
    position_monitor = load_dashboard_json(position_monitor_path) if position_monitor_path.exists() else {}
    if position_monitor:
        position_monitor["source_path"] = str(position_monitor_path)
    dashboard = build_dashboard(
        summary,
        parse_markdown_tables(daily_report_path),
        parse_plan_markdown(plan_report_path),
        position_monitor,
        theme_trends,
        edge_audit,
    )
    write_text(dashboard_json_path, json.dumps(dashboard, ensure_ascii=False, indent=2))
    write_text(dashboard_md_path, render_dashboard_markdown(dashboard))
    write_text(summary_json_path, json.dumps(summary, ensure_ascii=False, indent=2))
    write_text(summary_md_path, render_summary(summary))

    print(json.dumps({
        "success": True,
        "summary_json": str(summary_json_path),
        "summary_md": str(summary_md_path),
        "decision_dashboard": str(dashboard_md_path),
        "theme_trends": str(theme_trends_md_path) if theme_trends else "",
        "watchlist_count": summary["watchlist_count"],
        "themes_count": summary["themes_count"],
        "backtests_count": summary["backtests_count"],
        "selected_count": summary["selected_count"],
        "planned_exposure": summary["planned_exposure"],
        "quality_failed": summary["quality_failed"],
        "quality_skipped_count": summary["quality_skipped_count"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
