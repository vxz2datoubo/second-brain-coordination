"""
做T全流程执行 — 针对昆仑万维和蓝色光标
1. 盘前策略分析 (VWAP+RSI增强版)
2. 历史回测 (30天5分钟K线)
3. 可视化走势图 (HTML)
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from engine.data_loader import load_stock_data
from engine.backtest import BacktestEngine, backtest_report
from engine.visualize import generate_chart_html

OUTPUT = os.path.join(ROOT, "output")
os.makedirs(OUTPUT, exist_ok=True)

# ============================================================
# 加载数据
# ============================================================
stocks = {}

# 加载 300418
data_418 = os.path.join(OUTPUT, "300418_latest.json")
if os.path.exists(data_418):
    with open(data_418, "r", encoding="utf-8") as f:
        stocks["300418"] = json.load(f)
    print(f"✅ 加载 300418 数据")

# 加载 300058
data_058 = os.path.join(OUTPUT, "300058_latest.json")
if os.path.exists(data_058):
    with open(data_058, "r", encoding="utf-8") as f:
        stocks["300058"] = json.load(f)
    print(f"✅ 加载 300058 数据")

# ============================================================
# 回测
# ============================================================
print("\n" + "=" * 60)
print("  做T策略 历史回测")
print("=" * 60)

engine = BacktestEngine(slippage=0.001, min_profit_target=0.015, max_hold_bars=30)

all_reports = []
all_reports.append("# 🎯 昆仑 & 蓝色光标 — 做T全流程分析报告")
all_reports.append(f"**生成时间**: 2026-06-26")
all_reports.append("")

for code in ["300418", "300058"]:
    if code not in stocks:
        continue

    raw = stocks[code]
    data = load_stock_data(raw["quote_raw"], raw["daily_raw"], raw.get("hourly_raw"), raw.get("min5_raw"))
    quote = data["quote"]
    daily_bars = data["daily_bars"]
    min5_bars = data["min5_bars"]

    name = quote.name

    print(f"\n>>> 回测 {name}({code}) ...")

    # 运行回测
    result = engine.run(daily_bars, min5_bars)
    report = backtest_report(result, name, code)
    all_reports.append(report)
    all_reports.append("")

    print(f"    总交易: {result['total_trades']}笔 | 胜率: {result['win_rate']}% | "
          f"盈亏比: {result['profit_factor']} | 累计: {result['total_profit_pct']:+.2f}%")

    # 生成可视化HTML — 用最后一天数据
    last_day = min5_bars[0].date if min5_bars else ""
    day_bars = [b for b in min5_bars if b.date == last_day]

    # 支撑压力位
    from engine.indicators import find_support_resistance
    sr = find_support_resistance(daily_bars, quote.now)
    sr_dict = {"s2": sr.s2, "s1": sr.s1, "pivot": sr.pivot, "r1": sr.r1, "r2": sr.r2}

    # 只取当天回测的交易
    day_trades = [t for t in result.get("all_trades", []) if t.get("day") == last_day]

    html = generate_chart_html(daily_bars, day_bars, name, code, day_trades, sr_dict)
    html_path = os.path.join(OUTPUT, f"chart_{code}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"    📊 走势图: {html_path}")

# ============================================================
# 保存综合报告
# ============================================================
report_path = os.path.join(OUTPUT, "full_backtest_report.md")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n\n".join(all_reports))
print(f"\n✅ 综合回测报告: {report_path}")
