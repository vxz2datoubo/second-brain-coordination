"""
本地数据全面回测 — 从通达信二进制文件直接读取99天数据进行回测
支持1分钟K线分时图和5分钟K线回测
"""
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from engine.tdx_parser import (
    read_minute_kline, read_daily_kline, group_by_date,
    TDXBar, bars_to_dict_list
)
from engine.indicators import KBar, find_support_resistance
from engine.backtest import BacktestEngine, backtest_report
from engine.visualize import generate_chart_html

OUTPUT = os.path.join(ROOT, "output")
os.makedirs(OUTPUT, exist_ok=True)

# 数据路径
TDX_BASE = r"F:\tongdaxin\vipdoc\sz"

STOCKS = {
    "300418": {"name": "昆仑万维", "min1": "minline", "min5": "fzline", "day": "lday"},
    "300058": {"name": "蓝色光标", "min1": "minline", "min5": "fzline", "day": "lday"},
}


def tdx_bar_to_kbar(b: TDXBar) -> KBar:
    return KBar(
        date=b.date,
        time_sec=b.time_sec,
        open=b.open,
        high=b.high,
        low=b.low,
        close=b.close,
        amount=b.amount,
        volume=b.volume,
    )


def load_stock_from_tdx(code: str) -> dict:
    """从本地通达信文件加载完整数据"""
    cfg = STOCKS[code]

    # 日K
    day_path = os.path.join(TDX_BASE, cfg["day"], f"sz{code}.day")
    daily_raw = read_daily_kline(day_path)
    daily_bars = [tdx_bar_to_kbar(b) for b in daily_raw]

    # 5分钟K
    min5_path = os.path.join(TDX_BASE, cfg["min5"], f"sz{code}.lc5")
    min5_raw = read_minute_kline(min5_path)
    min5_bars = [tdx_bar_to_kbar(b) for b in min5_raw]

    # 1分钟K
    min1_path = os.path.join(TDX_BASE, cfg["min1"], f"sz{code}.lc1")
    min1_raw = read_minute_kline(min1_path)
    min1_bars = [tdx_bar_to_kbar(b) for b in min1_raw]

    # 分组
    min5_groups = group_by_date(min5_raw)
    min1_groups = group_by_date(min1_raw)

    return {
        "code": code,
        "name": cfg["name"],
        "daily_bars": daily_bars,
        "min5_bars": min5_bars,
        "min1_bars": min1_bars,
        "min5_days": min5_groups,
        "min1_days": min1_groups,
    }


def run_full_backtest():
    """主回测流程"""
    all_reports = []
    all_reports.append("# 🎯 昆仑 & 蓝色光标 — 99天全面回测报告")
    all_reports.append("")

    for code in ["300418", "300058"]:
        print(f"\n{'='*60}")
        print(f"  加载 {STOCKS[code]['name']}({code}) 本地数据...")
        stock = load_stock_from_tdx(code)
        name = stock["name"]

        min5_bars = stock["min5_bars"]
        min1_bars = stock["min1_bars"]
        min1_days = stock["min1_days"]
        min5_days = stock["min5_days"]
        daily_bars = stock["daily_bars"]

        all_dates = sorted(min5_days.keys())
        print(f"  99天数据就绪: {all_dates[0]} ~ {all_dates[-1]}")
        print(f"  5分钟K: {len(min5_bars)}条 | 1分钟K: {len(min1_bars)}条 | 日K: {len(daily_bars)}条")

        # ========== 回测 ==========
        print(f"  运行回测...")
        engine = BacktestEngine(slippage=0.001, min_profit_target=0.01, max_hold_bars=48)

        # Convert all 5-min bars to daily bar format for the engine
        # The engine's run() method groups by date, and we need daily bars indexed by date
        daily_map = {b.date: b for b in daily_bars}

        # Run on all days with 5-min data
        result = engine.run(daily_bars, min5_bars)

        report = backtest_report(result, name, code)
        all_reports.append(report)
        all_reports.append("")

        print(f"    总交易: {result['total_trades']}笔 | 胜率: {result['win_rate']}% | "
              f"盈亏比: {result['profit_factor']} | 累计: {result['total_profit_pct']:+.2f}%")
        print(f"    倒T: {result['reverse_t_count']}笔({result['reverse_t_win_rate']}%) | "
              f"正T: {result['long_t_count']}笔({result['long_t_win_rate']}%)")

        # ========== 生成每日走势图（最近5天，用1分钟数据） ==========
        recent_dates = sorted(min1_days.keys())[-5:]
        for day in recent_dates:
            print(f"  生成 {name} {day} 走势图...")

            # 获取当日1分钟K线
            day_bars_1m = [tdx_bar_to_kbar(b) for b in min1_days[day]]

            # 支撑压力位（用前N天日K计算）
            sr = find_support_resistance(daily_bars, day_bars_1m[-1].close if day_bars_1m else daily_bars[-1].close)
            sr_dict = {"s2": sr.s2, "s1": sr.s1, "pivot": sr.pivot, "r1": sr.r1, "r2": sr.r2}

            # 当天回测交易
            day_trades = [t for t in result.get("all_trades", []) if t.get("day") == day]

            html = generate_chart_html(
                daily_bars, day_bars_1m, name, code,
                backtest_trades=day_trades,
                support_resistance=sr_dict
            )
            html_path = os.path.join(OUTPUT, f"chart_{code}_{day}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

        # 保存原始数据JSON供后续使用
        data_snapshot = {
            "code": code,
            "name": name,
            "daily": [{"date": b.date, "open": b.open, "high": b.high, "low": b.low,
                        "close": b.close, "volume": b.volume, "amount": b.amount}
                       for b in daily_bars[-30:]],
            "min5_latest_day": bars_to_dict_list(min5_days.get(all_dates[-1], [])),
            "min1_latest_day": bars_to_dict_list(min1_days.get(all_dates[-1], [])),
        }
        snap_path = os.path.join(OUTPUT, f"{code}_full_snapshot.json")
        with open(snap_path, "w", encoding="utf-8") as f:
            json.dump(data_snapshot, f, ensure_ascii=False)
        print(f"    ✅ 数据快照: {snap_path}")

    # 保存综合回测报告
    report_path = os.path.join(OUTPUT, "backtest_99days_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_reports))
    print(f"\n{'='*60}")
    print(f"✅ 99天回测完成！报告: {report_path}")
    print(f"✅ 走势图: {OUTPUT}/chart_*.html")
    return report_path


if __name__ == "__main__":
    run_full_backtest()
