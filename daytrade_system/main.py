#!/usr/bin/env python
"""
昆仑 & 蓝色光标 每日做T系统 — 主入口

用法：
  python main.py --mode pre   # 盘前策略
  python main.py --mode live  # 盘中监控
  python main.py --mode after # 盘后复盘
  python main.py --mode full  # 全流程（如果数据齐全）

数据输入方式：
  1. 从 output/ 目录读取上一次 save 的 JSON 数据
  2. 通过命令行参数指定数据文件位置
"""

import argparse
import json
import os
import sys
from datetime import datetime

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from engine.data_loader import load_stock_data
from engine.indicators import QuoteSnapshot, KBar
from strategies.pre_market import pre_market_analysis, pre_market_summary
from strategies.intraday import intraday_live, check_alert_triggers, intraday_report
from strategies.after_market import after_market_review, review_report

OUTPUT_DIR = os.path.join(ROOT_DIR, "output")

# 默认股票配置
STOCKS = {
    "300418": "昆仑万维",
    "300058": "蓝色光标",
}


def save_data(code: str, quote_raw: dict, daily_raw: dict,
              hourly_raw: dict = None, min5_raw: dict = None):
    """保存原始数据到 output/ 以备后用"""
    data = {
        "code": code,
        "saved_at": datetime.now().isoformat(),
        "quote_raw": quote_raw,
        "daily_raw": daily_raw,
        "hourly_raw": hourly_raw,
        "min5_raw": min5_raw,
    }
    filepath = os.path.join(OUTPUT_DIR, f"{code}_latest.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=str)
    print(f"✅ 数据已保存: {filepath}")


def load_latest_data(code: str) -> dict:
    """从 output/ 加载最近一次保存的数据"""
    filepath = os.path.join(OUTPUT_DIR, f"{code}_latest.json")
    if not os.path.exists(filepath):
        print(f"❌ 未找到数据文件: {filepath}")
        print(f"   请先通过 MCP 获取数据并保存到此文件")
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_single_stock(code: str, quote_raw: dict, daily_raw: dict,
                          hourly_raw: dict = None, min5_raw: dict = None,
                          mode: str = "full") -> str:
    """
    对单只股票执行全流程分析
    Returns: Markdown 报告字符串
    """
    data = load_stock_data(quote_raw, daily_raw, hourly_raw, min5_raw)
    quote = data["quote"]
    daily_bars = data["daily_bars"]
    hourly_bars = data["hourly_bars"]
    min5_bars = data["min5_bars"]

    reports = []
    pre_analysis = None

    # 盘前分析
    if mode in ("pre", "full"):
        pre_analysis = pre_market_analysis(quote, daily_bars, hourly_bars, min5_bars)
        reports.append(pre_market_summary(pre_analysis))

    # 盘中监控
    if mode in ("live", "full") and min5_bars:
        if not pre_analysis:
            pre_analysis = pre_market_analysis(quote, daily_bars, hourly_bars, min5_bars)
        live_data = intraday_live(quote, min5_bars, daily_bars, pre_analysis)
        alerts = check_alert_triggers(live_data, pre_analysis)
        reports.append(intraday_report(live_data, alerts))

    # 盘后复盘
    if mode in ("after", "full"):
        if not pre_analysis:
            pre_analysis = pre_market_analysis(quote, daily_bars, hourly_bars, min5_bars)
        review = after_market_review(quote, min5_bars, daily_bars, pre_analysis)
        reports.append(review_report(review))

    return "\n\n---\n\n".join(reports)


def main():
    parser = argparse.ArgumentParser(description="昆仑&蓝色光标 每日做T系统")
    parser.add_argument("--mode", choices=["pre", "live", "after", "full"],
                        default="pre", help="运行模式")
    parser.add_argument("--code", default="all", help="股票代码, all=全部")
    parser.add_argument("--data-dir", default=None, help="数据文件目录")
    parser.add_argument("--output", "-o", default=None, help="输出文件名")
    args = parser.parse_args()

    # 确定要分析的股票
    codes = list(STOCKS.keys()) if args.code == "all" else [args.code]

    all_reports = []
    all_reports.append(f"# 🎯 做T分析报告 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    all_reports.append(f"**模式**: {args.mode}  |  **股票**: {', '.join(f'{STOCKS.get(c, c)}({c})' for c in codes)}")
    all_reports.append("")

    for code in codes:
        all_reports.append(f"\n---")
        # 尝试加载数据
        data = load_latest_data(code)
        if not data:
            all_reports.append(f"## {STOCKS.get(code, code)}({code}): 无数据")
            continue

        try:
            report = analyze_single_stock(
                code=code,
                quote_raw=data["quote_raw"],
                daily_raw=data["daily_raw"],
                hourly_raw=data.get("hourly_raw"),
                min5_raw=data.get("min5_raw"),
                mode=args.mode
            )
            all_reports.append(report)
        except Exception as e:
            all_reports.append(f"## {STOCKS.get(code, code)}({code}): 分析出错 - {e}")

    # 输出
    full_report = "\n".join(all_reports)

    if args.output:
        out_path = os.path.join(OUTPUT_DIR, args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        out_path = os.path.join(OUTPUT_DIR, f"report_{args.mode}_{timestamp}.md")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_report)

    print(f"\n✅ 报告已生成: {out_path}")
    print(full_report)


if __name__ == "__main__":
    main()
