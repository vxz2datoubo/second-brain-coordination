"""Paper-trade generated finance portfolio plans against future OHLCV bars.

This validates the actual daily plan, not just an isolated strategy backtest:
allowed candidates, planned entry, stop, quantity, and future bars determine
whether a simulated order fills, stops out, or exits at the horizon.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.finance_advisor import Bar, load_price_csv  # noqa: E402
from tools.finance_plan_review import parse_plan_markdown, to_float  # noqa: E402
from tools.finance_position_monitor import load_watchlist_csvs  # noqa: E402


def bars_after(bars: list[Bar], signal_date: str, horizon_days: int) -> list[Bar]:
    future = [bar for bar in bars if str(bar.date) > signal_date]
    return future[:horizon_days] if horizon_days > 0 else future


def simulate_candidate(
    plan: dict,
    bars: list[Bar],
    signal_date: str,
    horizon_days: int = 5,
    entry_tolerance: float = 0.0,
    fee_rate: float = 0.0003,
) -> dict:
    symbol = str(plan.get("symbol", ""))
    qty = int(to_float(plan.get("qty")))
    entry = to_float(plan.get("entry"))
    stop = to_float(plan.get("stop"))
    future = bars_after(bars, signal_date, horizon_days)
    result = {
        "symbol": symbol,
        "name": plan.get("name", ""),
        "theme": plan.get("theme", ""),
        "strategy": plan.get("strategy", ""),
        "planned_qty": qty,
        "planned_entry": entry,
        "planned_stop": stop,
        "signal_date": signal_date,
        "horizon_days": horizon_days,
        "status": "not_filled",
        "entry_date": "",
        "entry_price": 0.0,
        "exit_date": "",
        "exit_price": 0.0,
        "exit_reason": "",
        "gross_pnl": 0.0,
        "fees": 0.0,
        "net_pnl": 0.0,
        "return": 0.0,
        "bars_checked": len(future),
        "issues": [],
    }
    if not plan.get("allowed"):
        result["status"] = "blocked_by_plan"
        result["issues"].append("plan_not_allowed")
        return result
    if qty <= 0 or entry <= 0 or stop <= 0:
        result["status"] = "invalid_plan"
        result["issues"].append("missing_qty_entry_or_stop")
        return result
    if not future:
        result["status"] = "no_future_bars"
        result["issues"].append("no_bars_after_signal_date")
        return result

    filled = False
    entry_bar_index = -1
    max_entry = entry * (1 + entry_tolerance)
    for idx, bar in enumerate(future):
        if bar.low <= max_entry:
            fill_price = min(max(bar.open, entry), max_entry)
            result["status"] = "filled"
            result["entry_date"] = bar.date
            result["entry_price"] = round(fill_price, 4)
            entry_bar_index = idx
            filled = True
            break
    if not filled:
        return result

    exit_bar = future[-1]
    exit_price = exit_bar.close
    exit_reason = "horizon_exit"
    for bar in future[entry_bar_index:]:
        if bar.low <= stop:
            exit_bar = bar
            exit_price = stop
            exit_reason = "stop_loss"
            break

    gross = (exit_price - result["entry_price"]) * qty
    fees = (result["entry_price"] * qty + exit_price * qty) * fee_rate
    net = gross - fees
    cost = result["entry_price"] * qty
    result.update({
        "status": "closed",
        "exit_date": exit_bar.date,
        "exit_price": round(exit_price, 4),
        "exit_reason": exit_reason,
        "gross_pnl": round(gross, 2),
        "fees": round(fees, 2),
        "net_pnl": round(net, 2),
        "return": round(net / cost, 4) if cost > 0 else 0.0,
    })
    return result


def simulate_plan(
    plans: dict[str, dict],
    watchlist_csvs: dict[str, Path],
    signal_date: str,
    horizon_days: int = 5,
    entry_tolerance: float = 0.0,
    fee_rate: float = 0.0003,
) -> dict:
    trades = []
    for symbol, plan in sorted(plans.items()):
        if not plan.get("allowed"):
            continue
        csv_path = watchlist_csvs.get(symbol)
        if not csv_path or not Path(csv_path).exists():
            row = dict(plan)
            row.update({
                "status": "missing_csv",
                "signal_date": signal_date,
                "horizon_days": horizon_days,
                "net_pnl": 0.0,
                "return": 0.0,
                "issues": ["missing_market_csv"],
            })
            trades.append(row)
            continue
        try:
            bars = load_price_csv(csv_path)
            trades.append(simulate_candidate(plan, bars, signal_date, horizon_days, entry_tolerance, fee_rate))
        except Exception as exc:
            row = dict(plan)
            row.update({
                "status": "error",
                "signal_date": signal_date,
                "horizon_days": horizon_days,
                "net_pnl": 0.0,
                "return": 0.0,
                "issues": [f"{type(exc).__name__}: {exc}"],
            })
            trades.append(row)

    closed = [row for row in trades if row.get("status") == "closed"]
    filled = [row for row in trades if row.get("status") in {"closed", "filled"}]
    wins = [row for row in closed if to_float(row.get("net_pnl")) > 0]
    by_theme = defaultdict(lambda: {"net_pnl": 0.0, "closed": 0, "wins": 0})
    for row in closed:
        theme = str(row.get("theme", "")) or "未分类"
        by_theme[theme]["net_pnl"] += to_float(row.get("net_pnl"))
        by_theme[theme]["closed"] += 1
        if to_float(row.get("net_pnl")) > 0:
            by_theme[theme]["wins"] += 1

    theme_rows = []
    for theme, value in by_theme.items():
        closed_count = value["closed"]
        theme_rows.append({
            "theme": theme,
            "net_pnl": round(value["net_pnl"], 2),
            "closed": closed_count,
            "win_rate": round(value["wins"] / closed_count, 4) if closed_count else 0.0,
        })
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "signal_date": signal_date,
        "horizon_days": horizon_days,
        "planned": len([p for p in plans.values() if p.get("allowed")]),
        "filled": len(filled),
        "closed": len(closed),
        "win_rate": round(len(wins) / len(closed), 4) if closed else 0.0,
        "total_net_pnl": round(sum(to_float(row.get("net_pnl")) for row in closed), 2),
        "avg_return": round(sum(to_float(row.get("return")) for row in closed) / len(closed), 4) if closed else 0.0,
        "trades": trades,
        "by_theme": sorted(theme_rows, key=lambda row: row["net_pnl"], reverse=True),
    }


def md_escape(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict, plan_path: Path, watchlist_path: Path) -> str:
    lines = [
        f"# 纸面交易验证报告 - {report['signal_date']}",
        "",
        "用途：验证每日仓位计划在后续行情中的模拟执行表现。不构成投资建议，也不代表真实成交。",
        "",
        "## 总览",
        "",
        f"- 计划候选: {report['planned']}",
        f"- 触发入场: {report['filled']}",
        f"- 已闭合模拟交易: {report['closed']}",
        f"- 胜率: {report['win_rate']}",
        f"- 总净盈亏: {report['total_net_pnl']}",
        f"- 平均收益率: {report['avg_return']}",
        f"- 持有/验证天数: {report['horizon_days']}",
        "",
        "## 模拟交易",
        "",
        "| 标的 | 名称 | 题材 | 状态 | 入场日 | 入场价 | 退出日 | 退出价 | 原因 | 数量 | 净盈亏 | 收益率 | 问题 |",
        "|---|---|---|---|---|---:|---|---:|---|---:|---:|---:|---|",
    ]
    if report["trades"]:
        for row in report["trades"]:
            lines.append(
                f"| {md_escape(row.get('symbol'))} | {md_escape(row.get('name'))} | {md_escape(row.get('theme'))} | "
                f"{md_escape(row.get('status'))} | {md_escape(row.get('entry_date', ''))} | {row.get('entry_price', 0)} | "
                f"{md_escape(row.get('exit_date', ''))} | {row.get('exit_price', 0)} | {md_escape(row.get('exit_reason', ''))} | "
                f"{row.get('planned_qty', row.get('qty', 0))} | {row.get('net_pnl', 0)} | {row.get('return', 0)} | "
                f"{md_escape('；'.join(row.get('issues', [])))} |"
            )
    else:
        lines.append("| - | - | - | - | - | 0 | - | 0 | - | 0 | 0 | 0 | 无计划候选 |")

    lines.extend(["", "## 按题材归因", ""])
    if report["by_theme"]:
        lines.extend(["| 题材 | 净盈亏 | 闭合数 | 胜率 |", "|---|---:|---:|---:|"])
        for row in report["by_theme"]:
            lines.append(f"| {md_escape(row['theme'])} | {row['net_pnl']} | {row['closed']} | {row['win_rate']} |")
    else:
        lines.append("暂无闭合交易。")

    lines.extend([
        "",
        "## 解读",
        "",
        "- 连续多日纸面交易为负时，降低对应题材/策略权重，而不是继续放大仓位。",
        "- 入场触发少，说明计划价过严或行情未确认；不应追价补触发。",
        "- 止损触发多，优先检查题材生命周期、市场温度和止损距离。",
        "",
        "## 元数据",
        "",
        f"- 计划文件: `{plan_path}`",
        f"- 观察池文件: `{watchlist_path}`",
        f"- 生成时间: {report['generated_at']}",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Paper-trade a finance portfolio plan.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--watchlist", required=True)
    parser.add_argument("--signal-date", required=True)
    parser.add_argument("--horizon-days", type=int, default=5)
    parser.add_argument("--entry-tolerance", type=float, default=0.0)
    parser.add_argument("--fee-rate", type=float, default=0.0003)
    parser.add_argument("--date", default="")
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    args = parser.parse_args()

    plan_path = Path(args.plan)
    watchlist_path = Path(args.watchlist)
    report = simulate_plan(
        parse_plan_markdown(plan_path),
        load_watchlist_csvs(watchlist_path),
        args.signal_date,
        args.horizon_days,
        args.entry_tolerance,
        args.fee_rate,
    )
    output_date = args.date or args.signal_date
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"finance-paper-trade-{output_date}.json"
    md_path = output_dir / f"finance-paper-trade-{output_date}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report, plan_path, watchlist_path), encoding="utf-8")
    print(json.dumps({
        "success": True,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "planned": report["planned"],
        "filled": report["filled"],
        "closed": report["closed"],
        "total_net_pnl": report["total_net_pnl"],
        "win_rate": report["win_rate"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
