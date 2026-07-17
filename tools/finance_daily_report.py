"""Generate a daily stock-market theme report for Second Brain.

Input is a JSONL file with one item per line:
{"title": "...", "text": "...", "date": "YYYY-MM-DD", "source": "..."}

Optional watchlist CSV uses columns:
symbol,name,theme,csv_path,short_window,long_window

Stdlib only. It can optionally ingest the generated report into the local
Second Brain server.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.finance_advisor import analyze_hot_themes, load_price_csv, optimize_backtests, run_backtest_strategy, score_watchlist_candidates  # noqa: E402
from tools.finance_brain import ingest_report_once  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    items = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no} invalid JSON: {exc}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{line_no} must be a JSON object")
            items.append(item)
    return items


def load_watchlist(path: Path) -> list[dict]:
    import csv

    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("csv_path"):
                rows.append(row)
    return rows


def run_watchlist_backtests(rows: list[dict]) -> list[dict]:
    results = []
    for row in rows:
        try:
            bars = load_price_csv(row["csv_path"])
            strategy = row.get("strategy") or "optimize"
            if strategy == "optimize":
                optimized = optimize_backtests(bars)
                result = dict(optimized["best"] or {})
                result["optimized_candidates"] = optimized.get("candidates", [])[:5]
            else:
                result = run_backtest_strategy(
                    bars,
                    strategy=strategy,
                    short_window=int(row.get("short_window") or 5),
                    long_window=int(row.get("long_window") or 20),
                    breakout_window=int(row.get("breakout_window") or 20),
                    exit_window=int(row.get("exit_window") or 10),
                    rsi_window=int(row.get("rsi_window") or 14),
                    buy_below=float(row.get("buy_below") or 35),
                    sell_above=float(row.get("sell_above") or 55),
                )
            result["symbol"] = row.get("symbol", "")
            result["name"] = row.get("name", "")
            result["theme"] = row.get("theme", "")
            result["csv_path"] = row.get("csv_path", "")
            results.append(result)
        except Exception as exc:
            results.append({
                "symbol": row.get("symbol", ""),
                "name": row.get("name", ""),
                "theme": row.get("theme", ""),
                "csv_path": row.get("csv_path", ""),
                "error": f"{type(exc).__name__}: {exc}",
            })
    return results


def md_escape(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_report(trends: dict, backtests: list[dict], report_date: str, source_file: Path) -> str:
    lines = [
        f"# 股市 AI 每日题材与回测报告 - {report_date}",
        "",
        "用途: 盘后复盘、次日观察池、交易前风控。此报告只做概率和纪律辅助，不构成投资建议。",
        "",
        "## 今日题材热度",
        "",
    ]
    themes = trends.get("themes", [])
    if themes:
        lines.extend([
            "| 排名 | 题材 | 阶段 | 风险 | 优先级 | 热度分 | 提及 | 关键词 | 建议 |",
            "|---:|---|---|---|---:|---:|---:|---|---|",
        ])
        for row in themes:
            lines.append(
                f"| {row.get('rank', '')} | {md_escape(row.get('theme'))} | {md_escape(row.get('lifecycle'))} | "
                f"{md_escape(row.get('risk_level'))} | {row.get('action_priority', '')} | {row.get('score', '')} | "
                f"{row.get('mentions', '')} | {md_escape(', '.join(row.get('keywords', [])[:10]))} | "
                f"{md_escape(row.get('suggestion'))} |"
            )
    else:
        lines.append("暂无命中的题材。请检查输入文本是否包含题材关键词，或扩展 `DEFAULT_THEMES`。")

    lines.extend(["", "## 题材证据", ""])
    for row in themes:
        lines.append(f"### {row.get('rank')}. {row.get('theme')}")
        evidence = row.get("evidence", [])
        if not evidence:
            lines.append("- 暂无证据片段。")
            continue
        for ev in evidence:
            matched = ", ".join(ev.get("matched", []))
            lines.append(f"- {ev.get('date', '')} [{ev.get('source', '')}] {ev.get('title', '')}；命中: {matched}")

    lines.extend(["", "## 观察池回测", ""])
    if backtests:
        lines.extend([
            "| 标的 | 名称 | 题材 | 题材阶段 | 最佳策略 | 策略分 | 原始候选分 | 历史调整 | 纸面调整 | 候选分 | 收益 | 最大回撤 | 交易数 | 胜率 | 动作 |",
            "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ])
        for bt in backtests:
            if "error" in bt:
                lines.append(
                    f"| {md_escape(bt.get('symbol'))} | {md_escape(bt.get('name'))} | {md_escape(bt.get('theme'))} | "
                    f"- | - | - | 0 | - | - | - | - | {md_escape(bt.get('error'))} |"
                )
                continue
            lines.append(
                f"| {md_escape(bt.get('symbol'))} | {md_escape(bt.get('name'))} | {md_escape(bt.get('theme'))} | "
                f"{md_escape(bt.get('theme_lifecycle'))} | {md_escape(bt.get('strategy'))} | "
                f"{bt.get('risk_adjusted_score')} | {bt.get('candidate_score_raw', bt.get('candidate_score'))} | "
                f"{bt.get('signal_score_adjustment', 0)} | {bt.get('paper_score_adjustment', 0)} | {bt.get('candidate_score')} | "
                f"{bt.get('total_return')} | {bt.get('max_drawdown')} | {bt.get('trades_count')} | "
                f"{bt.get('win_rate')} | {md_escape(bt.get('candidate_action'))} |"
            )
    else:
        lines.append("未提供观察池 CSV，跳过回测。")

    lines.extend([
        "",
        "## 明日动作清单",
        "",
        "- 只把高热题材放入观察池，不因热度本身追高。",
        "- 每个候选标的必须写出三条反方证据。",
        "- 任何交易先过 `/api/finance/consult`，补齐周期、仓位、止损、最大亏损。",
        "- 若题材已经高潮一致，优先等待分歧或回踩确认。",
        "- 盘后把交易结果写成 `复盘:` 或 `教训:` 节点摄入第二大脑。",
        "",
        "## 元数据",
        "",
        f"- 输入文件: `{source_file}`",
        f"- 输入条数: {trends.get('items_count', 0)}",
        f"- 生成时间: {trends.get('generated_at', '')}",
    ])
    return "\n".join(lines) + "\n"


def ingest_report(report: str, title: str, brain_url: str) -> dict:
    return ingest_report_once(report, title, "finance-daily-report", brain_url)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate daily finance theme report.")
    parser.add_argument("--input", required=True, help="JSONL theme/news input file")
    parser.add_argument("--watchlist", help="Optional watchlist CSV for backtests")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    parser.add_argument("--ingest", action="store_true", help="Ingest report into Second Brain")
    parser.add_argument("--brain-url", default="http://localhost:8766")
    args = parser.parse_args()

    input_path = Path(args.input)
    items = load_jsonl(input_path)
    trends = analyze_hot_themes(items, top_k=10)
    raw_backtests = run_watchlist_backtests(load_watchlist(Path(args.watchlist))) if args.watchlist else []
    backtests = score_watchlist_candidates(raw_backtests, trends.get("themes", [])) if raw_backtests else []
    report = render_report(trends, backtests, args.date, input_path)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"finance-daily-report-{args.date}.md"
    output_path.write_text(report, encoding="utf-8")

    result = {"report_path": str(output_path), "themes": len(trends.get("themes", [])), "backtests": len(backtests)}
    if args.ingest:
        result["ingest"] = ingest_report(report, f"股市 AI 每日题材与回测报告 - {args.date}", args.brain_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
