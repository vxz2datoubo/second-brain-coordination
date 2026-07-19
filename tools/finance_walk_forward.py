"""Walk-forward validation for finance strategies.

This validates whether parameters selected on a training window still work on
the following test window. It is a guard against overfitting, not a prediction.
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

from core.finance_advisor import Bar, load_price_csv, optimize_backtests, run_backtest_strategy  # noqa: E402


def strip_runtime_params(params: dict) -> dict:
    return {k: v for k, v in (params or {}).items() if k not in {"initial_cash", "fee_rate"}}


def walk_forward_validate(
    bars: list[Bar],
    train_bars: int = 24,
    test_bars: int = 8,
    step_bars: int | None = None,
    initial_cash: float = 100000.0,
    fee_rate: float = 0.0003,
) -> dict:
    step = step_bars or test_bars
    windows = []
    start = 0
    while start + train_bars + test_bars <= len(bars):
        train = bars[start:start + train_bars]
        test = bars[start + train_bars:start + train_bars + test_bars]
        optimized = optimize_backtests(train, initial_cash, fee_rate)
        best = optimized.get("best") or {}
        if not best or "error" in best:
            windows.append({
                "train_start": train[0].date,
                "train_end": train[-1].date,
                "test_start": test[0].date,
                "test_end": test[-1].date,
                "error": best.get("error", "no valid training strategy"),
            })
            start += step
            continue
        strategy = best.get("strategy", "")
        params = strip_runtime_params(best.get("params", {}))
        try:
            test_result = run_backtest_strategy(test, strategy, initial_cash, fee_rate, **params)
            windows.append({
                "train_start": train[0].date,
                "train_end": train[-1].date,
                "test_start": test[0].date,
                "test_end": test[-1].date,
                "strategy": strategy,
                "params": params,
                "train_score": best.get("risk_adjusted_score"),
                "train_return": best.get("total_return"),
                "test_score": test_result.get("risk_adjusted_score"),
                "test_return": test_result.get("total_return"),
                "test_max_drawdown": test_result.get("max_drawdown"),
                "test_trades": test_result.get("trades_count"),
                "test_win_rate": test_result.get("win_rate"),
            })
        except Exception as exc:
            windows.append({
                "train_start": train[0].date,
                "train_end": train[-1].date,
                "test_start": test[0].date,
                "test_end": test[-1].date,
                "strategy": strategy,
                "params": params,
                "error": f"{type(exc).__name__}: {exc}",
            })
        start += step

    valid = [w for w in windows if "error" not in w]
    returns = [float(w.get("test_return", 0) or 0) for w in valid]
    drawdowns = [float(w.get("test_max_drawdown", 0) or 0) for w in valid]
    hit_count = len([r for r in returns if r > 0])
    avg_return = sum(returns) / len(returns) if returns else 0.0
    worst_return = min(returns) if returns else 0.0
    worst_drawdown = min(drawdowns) if drawdowns else 0.0
    consistency = hit_count / len(returns) if returns else 0.0
    stability_score = round(avg_return * 100 + consistency * 25 + worst_drawdown * 80, 2)
    if len(valid) < 2:
        stability_score -= 10
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "bars": len(bars),
        "start_date": bars[0].date if bars else "",
        "end_date": bars[-1].date if bars else "",
        "train_bars": train_bars,
        "test_bars": test_bars,
        "step_bars": step,
        "windows_count": len(windows),
        "valid_windows": len(valid),
        "summary": {
            "hit_rate": round(consistency, 4),
            "avg_test_return": round(avg_return, 4),
            "worst_test_return": round(worst_return, 4),
            "worst_test_drawdown": round(worst_drawdown, 4),
            "stability_score": round(stability_score, 2),
        },
        "windows": windows,
    }


def render_markdown(report: dict, source_path: Path) -> str:
    lines = [
        f"# Walk-forward 策略验证 - {source_path.name}",
        "",
        f"- 数据区间: {report['start_date']} -> {report['end_date']}",
        f"- K线数: {report['bars']}",
        f"- 训练窗口: {report['train_bars']}",
        f"- 测试窗口: {report['test_bars']}",
        f"- 有效窗口: {report['valid_windows']} / {report['windows_count']}",
        f"- 测试命中率: {report['summary']['hit_rate']}",
        f"- 平均测试收益: {report['summary']['avg_test_return']}",
        f"- 最差测试收益: {report['summary']['worst_test_return']}",
        f"- 最差测试回撤: {report['summary']['worst_test_drawdown']}",
        f"- 稳定性分: {report['summary']['stability_score']}",
        "",
        "## 窗口明细",
        "",
        "| 训练区间 | 测试区间 | 策略 | 训练分 | 训练收益 | 测试分 | 测试收益 | 测试回撤 | 交易数 | 胜率 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["windows"]:
        if "error" in row:
            lines.append(
                f"| {row.get('train_start')}~{row.get('train_end')} | {row.get('test_start')}~{row.get('test_end')} | "
                f"{row.get('strategy', '-')} | - | - | - | - | - | - | {row['error']} |"
            )
            continue
        lines.append(
            f"| {row['train_start']}~{row['train_end']} | {row['test_start']}~{row['test_end']} | "
            f"{row['strategy']} | {row['train_score']} | {row['train_return']} | {row['test_score']} | "
            f"{row['test_return']} | {row['test_max_drawdown']} | {row['test_trades']} | {row['test_win_rate']} |"
        )
    lines.extend([
        "",
        "## 使用原则",
        "",
        "- 训练分高但测试收益差，说明参数可能过拟合。",
        "- 有效窗口少时只作提示，不应用来放大仓位。",
        "- 稳定性分低的策略，即使单段回测漂亮，也应降权或剔除。",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Walk-forward validate finance strategies.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    parser.add_argument("--train-bars", type=int, default=24)
    parser.add_argument("--test-bars", type=int, default=8)
    parser.add_argument("--step-bars", type=int, default=0)
    args = parser.parse_args()

    csv_path = Path(args.csv)
    bars = load_price_csv(csv_path)
    report = walk_forward_validate(bars, args.train_bars, args.test_bars, args.step_bars or None)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = csv_path.stem.replace(" ", "-")
    json_path = output_dir / f"finance-walk-forward-{stem}-{args.date}.json"
    md_path = output_dir / f"finance-walk-forward-{stem}-{args.date}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report, csv_path), encoding="utf-8")
    print(json.dumps({
        "success": True,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "valid_windows": report["valid_windows"],
        "summary": report["summary"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
