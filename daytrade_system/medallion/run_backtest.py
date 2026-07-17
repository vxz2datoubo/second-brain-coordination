"""run_backtest.py — 99日历史回测启动脚本

运行大奖章系统的完整回测，验证正期望。
对比新旧参数体系的表现差异。
"""

import sys, os, json, traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from medallion.backtest_medallion import (
    BacktestMedallion, run_backtest_for_code,
    format_backtest_report, tdx_to_kbar,
)
from engine.tdx_parser import read_minute_kline, read_daily_kline, group_by_date
from engine.indicators import KBar


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_full_backtest():
    """完整回测：两只股票"""
    codes = ["300418", "300058"]
    results = {}
    reports = []

    for code in codes:
        print(f"\n{'='*60}")
        print(f"  回测 {code} ...")
        print(f"{'='*60}")

        try:
            result = run_backtest_for_code(code)
            results[code] = result

            # 格式化报告
            report = format_backtest_report(result)
            reports.append(report)
            print(report)

            # 保存结果JSON
            out_path = os.path.join(OUTPUT_DIR, f"backtest_{code}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n  → 已保存: {out_path}")

        except Exception as e:
            print(f"  回测失败: {e}")
            traceback.print_exc()

    # 综合对比报告
    if len(results) == 2:
        summary_path = os.path.join(OUTPUT_DIR, "backtest_summary.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("\n".join(reports))
        print(f"\n{'='*60}")
        print(f"  综合报告已保存: {summary_path}")

    return results


def quick_test():
    """快速测试：运行一天数据"""
    print("快速测试模式...")

    from engine.tdx_parser import read_minute_kline, read_daily_kline
    from engine.indicators import KBar

    # 读蓝色最近1天数据
    day_path = r"F:\tongdaxin\vipdoc\sz\lday\sz300418.day"
    min5_path = r"F:\tongdaxin\vipdoc\sz\fzline\sz300418.lc5"

    daily_raw = read_daily_kline(day_path)
    min5_raw = read_minute_kline(min5_path)

    daily_bars = [tdx_to_kbar(b) for b in daily_raw]
    min5_bars = [tdx_to_kbar(b) for b in min5_raw]

    print(f"日K: {len(daily_bars)}根")
    print(f"5分K: {len(min5_bars)}根")
    print(f"5分K日期范围: {min5_bars[0].date} ~ {min5_bars[-1].date}")
    print(f"日K日期范围: {daily_bars[0].date} ~ {daily_bars[-1].date}")

    # 单日回测
    bt = BacktestMedallion("300418")
    last_day = min5_bars[-1].date
    import collections
    days = collections.defaultdict(list)
    for b in min5_bars:
        days[b.date].append(b)

    print(f"\n测试日: {last_day}  | 5分K数量: {len(days[last_day])}")

    daily_index = {b.date: b for b in daily_bars}
    prev_close = daily_index[days[last_day][0].date[-8:]].close if last_day in daily_index else None

    single_result = bt._backtest_day(
        last_day, days[last_day],
        daily_index.get(last_day, days[last_day][0]),
        prev_close, daily_bars
    )

    print(f"该日交易: {len(single_result.trades)}笔")
    print(f"该日盈亏: {single_result.pnl:+.2f}%")
    print(f"市场状态: {single_result.regime}")

    for t in single_result.trades:
        print(f"  #{t.slot_id} {t.entry_time}→{t.exit_time} {t.profit_pct:+.3f}%")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="快速测试")
    args = parser.parse_args()

    if args.quick:
        quick_test()
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\n大奖章系统 99日回测 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"输出目录: {OUTPUT_DIR}")
        results = run_full_backtest()

        # 打印综合结论
        if "300418" in results and "300058" in results:
            r418 = results["300418"]
            r058 = results["300058"]
            print(f"\n{'#'*60}")
            print(f"# 综合结论")
            print(f"{'#'*60}")
            checks_418 = [
                ("胜率≥65%", r418["win_rate"] >= 65, f"蓝色胜率{r418['win_rate']}%"),
                ("盈亏比≥1.5", r418["profit_factor"] != "N/A" and float(r418["profit_factor"]) >= 1.5, f"蓝色盈亏比{r418['profit_factor']}"),
                ("累计收益>0", r418["total_pnl"] > 0, f"蓝色累计{r418['total_pnl']:+.2f}%"),
            ]
            checks_058 = [
                ("胜率≥65%", r058["win_rate"] >= 65, f"昆仑胜率{r058['win_rate']}%"),
                ("盈亏比≥1.5", r058["profit_factor"] != "N/A" and float(r058["profit_factor"]) >= 1.5, f"昆仑盈亏比{r058['profit_factor']}"),
                ("累计收益>0", r058["total_pnl"] > 0, f"昆仑累计{r058['total_pnl']:+.2f}%"),
            ]

            print("\n蓝色光标(300418):")
            for name, passed, value in checks_418:
                print(f"  {'[PASS]' if passed else '[FAIL]'} {name}: {value}")

            print("\n昆仑万维(300058):")
            for name, passed, value in checks_058:
                print(f"  {'[PASS]' if passed else '[FAIL]'} {name}: {value}")
