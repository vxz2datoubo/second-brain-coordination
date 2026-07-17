"""Monitor open finance positions against plan stops and latest market data.

This is a post-entry risk gate. It reads the trade journal, portfolio plan, and
latest OHLCV CSVs, then flags positions that need action before the next trade.
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

from core.finance_advisor import Bar, load_price_csv  # noqa: E402
from tools.finance_plan_review import parse_plan_markdown, to_float  # noqa: E402
from tools.finance_trade_journal import compute_attribution, load_jsonl  # noqa: E402


def parse_date(value: str) -> datetime | None:
    text = str(value or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def business_days_between(start: str, end: str) -> int | None:
    start_dt = parse_date(start)
    end_dt = parse_date(end)
    if not start_dt or not end_dt:
        return None
    if start_dt > end_dt:
        return 0
    days = 0
    current = start_dt
    while current.date() < end_dt.date():
        current = current.replace(day=current.day)  # keep type checkers calm
        current = datetime.fromordinal(current.toordinal() + 1)
        if current.weekday() < 5:
            days += 1
    return days


def load_watchlist_csvs(path: Path) -> dict[str, Path]:
    if not path.exists():
        return {}
    mapping: dict[str, Path] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = str(row.get("symbol", "")).strip()
            csv_path = str(row.get("csv_path", "")).strip()
            if symbol and csv_path:
                mapping[symbol] = Path(csv_path)
    return mapping


def find_market_csv(symbol: str, watchlist_csvs: dict[str, Path], market_dir: Path | None) -> Path | None:
    if symbol in watchlist_csvs and watchlist_csvs[symbol].exists():
        return watchlist_csvs[symbol]
    if not market_dir or not market_dir.exists():
        return None
    exact = market_dir / f"{symbol}.csv"
    if exact.exists():
        return exact
    matches = sorted(market_dir.glob(f"{symbol}-*.csv"))
    return matches[0] if matches else None


def latest_bar_for(symbol: str, watchlist_csvs: dict[str, Path], market_dir: Path | None) -> tuple[Bar | None, str]:
    csv_path = find_market_csv(symbol, watchlist_csvs, market_dir)
    if not csv_path:
        return None, ""
    bars = load_price_csv(csv_path)
    if not bars:
        return None, str(csv_path)
    return bars[-1], str(csv_path)


def monitor_positions(
    plans: dict[str, dict],
    trades: list[dict],
    watchlist_csvs: dict[str, Path] | None = None,
    market_dir: Path | None = None,
    report_date: str = "",
    max_stale_business_days: int = 2,
) -> dict:
    watchlist_csvs = watchlist_csvs or {}
    attribution = compute_attribution(trades)
    rows = []
    action_required = 0
    warnings_total = 0

    for pos in attribution["open_positions"]:
        symbol = str(pos.get("symbol", "")).strip()
        plan = plans.get(symbol, {})
        bar, csv_path = latest_bar_for(symbol, watchlist_csvs, market_dir)
        issues = []
        warnings = []
        status = "ok"

        if not plan:
            issues.append("计划外持仓")
        elif not plan.get("allowed"):
            issues.append("计划不允许但仍有持仓")

        planned_qty = to_float(plan.get("qty"))
        qty = to_float(pos.get("qty"))
        stop = to_float(plan.get("stop"))
        avg_cost = to_float(pos.get("avg_cost"))

        if planned_qty and qty > planned_qty * 1.05:
            issues.append(f"持仓数量超过计划: {qty} > {planned_qty}")

        latest_close = bar.close if bar else 0.0
        latest_low = bar.low if bar else 0.0
        latest_date = bar.date if bar else ""
        if not bar:
            warnings.append("找不到最新行情CSV")
        else:
            if stop and latest_low <= stop:
                issues.append(f"盘中最低价触及止损: {latest_low} <= {stop}")
            elif stop and latest_close <= stop:
                issues.append(f"收盘价跌破止损: {latest_close} <= {stop}")
            if report_date:
                stale_days = business_days_between(latest_date, report_date)
                if stale_days is not None and stale_days > max_stale_business_days:
                    warnings.append(f"行情已过期 {stale_days} 个交易日")

        if issues:
            status = "action_required"
            action_required += 1
        elif warnings:
            status = "watch"
            warnings_total += 1

        unrealized_pnl = (latest_close - avg_cost) * qty if latest_close and avg_cost else 0.0
        cost = to_float(pos.get("cost"))
        rows.append({
            "symbol": symbol,
            "name": plan.get("name", ""),
            "theme": plan.get("theme", ""),
            "status": status,
            "qty": qty,
            "planned_qty": planned_qty,
            "avg_cost": avg_cost,
            "cost": cost,
            "latest_date": latest_date,
            "latest_close": latest_close,
            "latest_low": latest_low,
            "stop": stop,
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_return": round(unrealized_pnl / cost, 4) if cost > 0 else 0.0,
            "issues": issues,
            "warnings": warnings,
            "csv_path": csv_path,
        })

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "report_date": report_date,
        "open_count": len(rows),
        "action_required": action_required,
        "watch_count": warnings_total,
        "positions": rows,
        "attribution": attribution,
    }


def md_escape(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_markdown(result: dict, plan_path: Path, journal_path: Path) -> str:
    lines = [
        f"# 持仓监控与止损检查 - {result['report_date']}",
        "",
        "用途：盘中或盘后检查已有持仓是否触发止损、超计划、缺行情或需要人工复核。不构成投资建议。",
        "",
        "## 总览",
        "",
        f"- 未平仓持仓: {result['open_count']}",
        f"- 需要处理: {result['action_required']}",
        f"- 需要观察: {result['watch_count']}",
        "",
        "## 持仓明细",
        "",
        "| 状态 | 标的 | 名称 | 题材 | 数量 | 计划数量 | 成本价 | 最新日期 | 收盘 | 最低 | 止损 | 浮盈亏 | 问题 |",
        "|---|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|---|",
    ]
    if result["positions"]:
        for row in result["positions"]:
            notes = "；".join(row["issues"] + row["warnings"]) or "无"
            lines.append(
                f"| {row['status']} | {md_escape(row['symbol'])} | {md_escape(row['name'])} | "
                f"{md_escape(row['theme'])} | {row['qty']} | {row['planned_qty']} | {row['avg_cost']} | "
                f"{md_escape(row['latest_date'])} | {row['latest_close']} | {row['latest_low']} | "
                f"{row['stop']} | {row['unrealized_pnl']} | {md_escape(notes)} |"
            )
    else:
        lines.append("| ok | - | - | - | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 无未平仓持仓 |")

    lines.extend([
        "",
        "## 执行动作",
        "",
        "- `action_required`：先处理风险，再考虑新开仓。",
        "- 触及止损时按计划退出或降仓，不能用补仓掩盖亏损。",
        "- 行情过期或缺行情时，不允许把监控结果当成有效信号。",
        "",
        "## 元数据",
        "",
        f"- 计划文件: `{plan_path}`",
        f"- 账本文件: `{journal_path}`",
        f"- 生成时间: {result['generated_at']}",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor open positions against stops and latest prices.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--journal", required=True)
    parser.add_argument("--watchlist", default="")
    parser.add_argument("--market-dir", default="")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--max-stale-business-days", type=int, default=2)
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    args = parser.parse_args()

    plan_path = Path(args.plan)
    journal_path = Path(args.journal)
    watchlist_csvs = load_watchlist_csvs(Path(args.watchlist)) if args.watchlist else {}
    market_dir = Path(args.market_dir) if args.market_dir else None
    result = monitor_positions(
        parse_plan_markdown(plan_path),
        load_jsonl(journal_path),
        watchlist_csvs,
        market_dir,
        args.date,
        args.max_stale_business_days,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"finance-position-monitor-{args.date}.json"
    md_path = output_dir / f"finance-position-monitor-{args.date}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(result, plan_path, journal_path), encoding="utf-8")
    print(json.dumps({
        "success": True,
        "open_count": result["open_count"],
        "action_required": result["action_required"],
        "watch_count": result["watch_count"],
        "json_path": str(json_path),
        "md_path": str(md_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
