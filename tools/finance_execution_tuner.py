"""Sweep paper-trade execution rules for a generated portfolio plan.

When forward signals look good but paper trades lose money, the issue may be
entry, stop distance, or holding horizon. This tool tests conservative rule
variants without changing the original plan.
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

from tools.finance_paper_trade import simulate_plan  # noqa: E402
from tools.finance_plan_review import parse_plan_markdown, to_float  # noqa: E402
from tools.finance_position_monitor import load_watchlist_csvs  # noqa: E402


def parse_float_list(text: str) -> list[float]:
    return [float(part.strip()) for part in str(text).split(",") if part.strip()]


def parse_int_list(text: str) -> list[int]:
    return [int(float(part.strip())) for part in str(text).split(",") if part.strip()]


def widen_stops(plans: dict[str, dict], stop_buffer_pct: float) -> dict[str, dict]:
    adjusted = {}
    for symbol, plan in plans.items():
        row = dict(plan)
        stop = to_float(row.get("stop"))
        if stop > 0:
            row["stop"] = round(stop * (1 - stop_buffer_pct), 4)
            row["original_stop"] = stop
            row["stop_buffer_pct"] = stop_buffer_pct
        adjusted[symbol] = row
    return adjusted


def stop_loss_rate(report: dict) -> float:
    closed = [row for row in report.get("trades", []) if row.get("status") == "closed"]
    if not closed:
        return 0.0
    stopped = [row for row in closed if row.get("exit_reason") == "stop_loss"]
    return round(len(stopped) / len(closed), 4)


def run_sweep(
    plans: dict[str, dict],
    watchlist_csvs: dict[str, Path],
    signal_date: str,
    horizons: list[int],
    entry_tolerances: list[float],
    stop_buffers: list[float],
    fee_rate: float = 0.0003,
) -> dict:
    rows = []
    for horizon in horizons:
        for entry_tolerance in entry_tolerances:
            for stop_buffer in stop_buffers:
                adjusted_plans = widen_stops(plans, stop_buffer)
                report = simulate_plan(adjusted_plans, watchlist_csvs, signal_date, horizon, entry_tolerance, fee_rate)
                rows.append({
                    "horizon_days": horizon,
                    "entry_tolerance": entry_tolerance,
                    "stop_buffer_pct": stop_buffer,
                    "planned": report["planned"],
                    "filled": report["filled"],
                    "closed": report["closed"],
                    "win_rate": report["win_rate"],
                    "avg_return": report["avg_return"],
                    "total_net_pnl": report["total_net_pnl"],
                    "stop_loss_rate": stop_loss_rate(report),
                })
    rows.sort(key=lambda row: (row["total_net_pnl"], row["avg_return"], -row["stop_loss_rate"]), reverse=True)
    best = rows[0] if rows else {}
    baseline = next(
        (
            row for row in rows
            if row["horizon_days"] == horizons[0]
            and row["entry_tolerance"] == entry_tolerances[0]
            and row["stop_buffer_pct"] == stop_buffers[0]
        ),
        rows[0] if rows else {},
    )
    diagnosis = diagnose(best, baseline)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "signal_date": signal_date,
        "tested": len(rows),
        "best": best,
        "baseline": baseline,
        "diagnosis": diagnosis,
        "results": rows,
    }


def diagnose(best: dict, baseline: dict) -> list[str]:
    notes = []
    if not best:
        return ["没有可用调参结果"]
    if best.get("total_net_pnl", 0) <= 0:
        notes.append("所有测试组合仍未显示正收益，优先暂停或极小仓验证")
    elif baseline and best.get("total_net_pnl", 0) > baseline.get("total_net_pnl", 0):
        notes.append("存在优于基线的执行规则组合，后续应小样本验证而非直接实盘放大")
    if best.get("stop_buffer_pct", 0) > 0:
        notes.append("最佳组合需要更宽止损，原计划止损可能过紧")
    if best.get("entry_tolerance", 0) == 0:
        notes.append("最佳组合不需要追价容忍，继续坚持不追高")
    elif best.get("entry_tolerance", 0) > 0:
        notes.append("最佳组合允许一定入场容忍，需警惕追价导致滑点")
    if best.get("stop_loss_rate", 0) >= 0.5:
        notes.append("即使最佳组合止损率仍偏高，应检查题材阶段或入场触发条件")
    return notes


def md_escape(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict, plan_path: Path, watchlist_path: Path) -> str:
    best = report.get("best") or {}
    baseline = report.get("baseline") or {}
    lines = [
        f"# 执行规则敏感性分析 - {report['signal_date']}",
        "",
        "用途：比较不同入场容忍、止损缓冲、持有天数下的纸面交易表现。不构成投资建议。",
        "",
        "## 结论",
        "",
        f"- 测试组合数: {report['tested']}",
        f"- 基线净盈亏: {baseline.get('total_net_pnl', 0)}",
        f"- 最佳净盈亏: {best.get('total_net_pnl', 0)}",
        f"- 最佳组合: horizon={best.get('horizon_days')} entry_tolerance={best.get('entry_tolerance')} stop_buffer={best.get('stop_buffer_pct')}",
        f"- 最佳胜率: {best.get('win_rate', 0)}",
        f"- 最佳止损率: {best.get('stop_loss_rate', 0)}",
        "",
        "## 诊断",
        "",
    ]
    lines.extend([f"- {note}" for note in report.get("diagnosis", [])])
    lines.extend([
        "",
        "## 前十组合",
        "",
        "| 排名 | 持有天数 | 入场容忍 | 止损缓冲 | 触发 | 闭合 | 胜率 | 平均收益 | 净盈亏 | 止损率 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for rank, row in enumerate(report.get("results", [])[:10], 1):
        lines.append(
            f"| {rank} | {row['horizon_days']} | {row['entry_tolerance']} | {row['stop_buffer_pct']} | "
            f"{row['filled']} | {row['closed']} | {row['win_rate']} | {row['avg_return']} | "
            f"{row['total_net_pnl']} | {row['stop_loss_rate']} |"
        )
    lines.extend([
        "",
        "## 使用原则",
        "",
        "- 只有连续多期敏感性分析都改善，才考虑修改默认执行规则。",
        "- 如果最佳组合仍为负，先暂停或极小仓，不用调参掩盖无效信号。",
        "- 如果需要大幅放宽止损才盈利，要重新核算单笔风险和仓位。",
        "",
        "## 元数据",
        "",
        f"- 计划文件: `{plan_path}`",
        f"- 观察池文件: `{watchlist_path}`",
        f"- 生成时间: {report['generated_at']}",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sweep execution rules for paper trading.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--watchlist", required=True)
    parser.add_argument("--signal-date", required=True)
    parser.add_argument("--horizons", default="3,5,10")
    parser.add_argument("--entry-tolerances", default="0,0.01,0.02")
    parser.add_argument("--stop-buffers", default="0,0.01,0.02,0.03")
    parser.add_argument("--fee-rate", type=float, default=0.0003)
    parser.add_argument("--date", default="")
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    args = parser.parse_args()

    plan_path = Path(args.plan)
    watchlist_path = Path(args.watchlist)
    report = run_sweep(
        parse_plan_markdown(plan_path),
        load_watchlist_csvs(watchlist_path),
        args.signal_date,
        parse_int_list(args.horizons),
        parse_float_list(args.entry_tolerances),
        parse_float_list(args.stop_buffers),
        args.fee_rate,
    )
    output_date = args.date or args.signal_date
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"finance-execution-tuner-{output_date}.json"
    md_path = output_dir / f"finance-execution-tuner-{output_date}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report, plan_path, watchlist_path), encoding="utf-8")
    print(json.dumps({
        "success": True,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "tested": report["tested"],
        "best": report["best"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
