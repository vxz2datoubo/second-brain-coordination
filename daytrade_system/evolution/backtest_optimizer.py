"""
自进化层 · 回测优化器
用历史K线数据对不同参数组合进行回测，找到最优配置

功能：
  1. 跨日持仓优化：测试持有1天/2天/3天的效果
  2. 参数网格搜索：因子权重/置信度阈值的最优组合
  3. 时间窗口优化：哪些时间段胜率最高
  4. 每日自动回测前N天，输出参数建议
"""

import json
import math
import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORK_DIR, "data")

# 导入项目模块
import sys
sys.path.insert(0, os.path.dirname(WORK_DIR))

try:
    from engine.indicators import calc_ma, calc_atr, calc_rsi, find_support_resistance, calc_vwap_bands
except ImportError:
    calc_ma = None
    calc_atr = None
    calc_rsi = None


@dataclass
class BacktestResult:
    """单次回测结果"""
    stock: str
    start_date: str
    end_date: str
    total_trades: int
    win_count: int
    win_rate: float
    total_profit: float
    avg_profit_pct: float
    max_drawdown: float
    sharpe_ratio: float
    params: Dict


class BacktestOptimizer:
    """
    回测优化器
    使用历史日K数据，对策略进行回测验证
    """

    def __init__(self, stock_code: str = None):
        self.stock_code = stock_code
        self.results: List[BacktestResult] = []

    def load_historical_data(self, stock_code: str, days: int = 120) -> List[Dict]:
        """
        加载历史K线数据（从本地文件）
        先尝试从 daytrade_system/data 加载
        """
        data_dir = os.path.join(WORK_DIR, "data")
        candidates = [
            os.path.join(data_dir, f"{stock_code}_daily.json"),
            os.path.join(data_dir, f"{stock_code}.json"),
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        return data[-days:]
                    elif isinstance(data, dict) and "daily" in data:
                        return data["daily"][-days:]
                except Exception:
                    pass
        return []

    def backtest_cross_day_strategy(
        self,
        stock_code: str,
        hold_days: List[int] = [1, 2, 3, 5],
        start_date: str = None,
        end_date: str = None,
    ) -> Dict:
        """
        跨日持仓优化
        测试持有不同天数的收益率
        """
        bars = self.load_historical_data(stock_code)
        if not bars:
            return {"error": f"无数据: {stock_code}"}

        # 过滤日期范围
        if start_date:
            bars = [b for b in bars if str(b.get("date", b.get("d", ""))) >= start_date]
        if end_date:
            bars = [b for b in bars if str(b.get("date", b.get("d", ""))) <= end_date]

        if len(bars) < 30:
            return {"error": f"数据不足: {len(bars)}条"}

        closes = [float(b.get("close", b.get("c", 0))) for b in bars]
        results = {}

        for hold_d in hold_days:
            profits = []
            for i in range(len(bars) - hold_d):
                entry_price = closes[i]
                exit_price = closes[i + hold_d]
                profit_pct = (exit_price - entry_price) / entry_price * 100
                profits.append(profit_pct)

            if not profits:
                continue

            wins = sum(1 for p in profits if p > 0)
            win_rate = wins / len(profits) * 100
            avg_profit = sum(profits) / len(profits)
            total_profit = sum(profits)

            # 最大连续亏损
            max_dd = 0
            running = 0
            for p in profits:
                running += p
                if running < max_dd:
                    max_dd = running

            results[f"{hold_d}天"] = {
                "sample_count": len(profits),
                "win_rate": round(win_rate, 2),
                "avg_profit_pct": round(avg_profit, 4),
                "total_profit_pct": round(total_profit, 2),
                "max_drawdown": round(max_dd, 2),
            }

        # 找最优
        if results:
            best_key = max(results, key=lambda k: results[k]["avg_profit_pct"])
            best = results[best_key]
        else:
            best_key = "?"
            best = {}

        return {
            "stock": stock_code,
            "date_range": f"{bars[0].get('date', bars[0].get('d', ''))} ~ {bars[-1].get('date', bars[-1].get('d', ''))}",
            "hold_day_results": results,
            "optimal_hold_days": best_key,
            "optimal_hold_stats": best,
        }

    def backtest_signal_strategy(
        self,
        stock_code: str,
        signal_threshold: int = 60,
        confidence_filter: str = "B",
        days: int = 60,
    ) -> Dict:
        """
        基于信号策略回测
        模拟：信号分 > threshold 时开仓，按固定止盈止损退出
        """
        bars = self.load_historical_data(stock_code)
        if not bars:
            return {"error": f"无数据: {stock_code}"}

        bars = bars[-days:]
        if len(bars) < 30:
            return {"error": f"数据不足: {len(bars)}条"}

        closes = [float(b.get("close", b.get("c", 0))) for b in bars]
        highs = [float(b.get("high", b.get("h", 0))) for b in bars]
        lows = [float(b.get("low", b.get("l", 0))) for b in bars]

        # 计算信号（简化版：用RSI和动量）
        profits = []
        position = None
        entry_price = 0
        entry_date = 0

        for i in range(20, len(bars) - 1):
            # 简化信号
            window = closes[max(0, i-20):i+1]
            if len(window) < 10:
                continue

            # RSI信号
            gains = [max(window[j] - window[j-1], 0) for j in range(1, len(window))]
            losses = [max(-(window[j] - window[j-1]), 0) for j in range(1, len(window))]
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))

            # 动量
            momentum = (closes[i] / closes[i-3] - 1) * 100 if i >= 3 else 0

            signal_score = 0
            if rsi > 70:
                signal_score += 30
            elif rsi > 65:
                signal_score += 15
            if momentum > 2:
                signal_score += 20

            # 开仓
            if signal_score >= signal_threshold and position is None:
                position = "SHORT"
                entry_price = closes[i]
                entry_date = i

            # 平仓逻辑（倒T模拟：持有到RSI<50 或 达3%止盈 或 -1.5%止损）
            if position and i > entry_date:
                hold_bars = i - entry_date
                pnl_pct = (entry_price - closes[i]) / entry_price * 100

                if pnl_pct >= 3.0 or pnl_pct <= -1.5 or hold_bars >= 5:
                    profits.append(pnl_pct)
                    position = None

        if not profits:
            return {"note": f"期间无信号触发（阈值={signal_threshold}）"}

        wins = sum(1 for p in profits if p > 0)
        win_rate = wins / len(profits) * 100
        avg_profit = sum(profits) / len(profits)

        return {
            "stock": stock_code,
            "params": {
                "signal_threshold": signal_threshold,
                "confidence_filter": confidence_filter,
                "profit_target_pct": 3.0,
                "stop_loss_pct": 1.5,
            },
            "total_trades": len(profits),
            "win_rate": round(win_rate, 2),
            "avg_profit_pct": round(avg_profit, 4),
            "total_profit_pct": round(sum(profits), 2),
            "best_trade": round(max(profits), 4) if profits else 0,
            "worst_trade": round(min(profits), 4) if profits else 0,
        }

    def find_optimal_threshold(
        self,
        stock_code: str,
        thresholds: List[int] = [50, 55, 60, 65, 70, 75, 80],
        days: int = 60,
    ) -> Dict:
        """
        寻找最优信号阈值
        """
        results = []
        for th in thresholds:
            r = self.backtest_signal_strategy(stock_code, th, days=days)
            if "error" not in r and "note" not in r:
                r["threshold"] = th
                results.append(r)

        if not results:
            return {"error": "无法完成阈值搜索"}

        # 找最优（综合考虑胜率和平均盈利）
        best = max(results, key=lambda x: x.get("win_rate", 0) * 0.5 + max(x.get("avg_profit_pct", 0) * 10, 0))

        return {
            "stock": stock_code,
            "all_results": results,
            "optimal_threshold": best["threshold"],
            "optimal_win_rate": best["win_rate"],
            "optimal_avg_profit": best["avg_profit_pct"],
        }


def run_full_optimization():
    """运行完整优化流程"""
    stocks = {"300418": "昆仑万维", "300058": "蓝色光标"}
    reports = [f"# 量化回测优化报告 · {date.today().isoformat()}", ""]

    for code, name in stocks.items():
        optimizer = BacktestOptimizer(code)
        reports.append(f"## 【{name}({code})】")
        reports.append("")

        # 跨日持仓优化
        cd = optimizer.backtest_cross_day_strategy(code, [1, 2, 3, 5])
        if "error" not in cd:
            reports.append("### 跨日持仓分析")
            reports.append(f"| 持有天数 | 样本数 | 胜率 | 平均收益 | 总收益 | 最大回撤 |")
            reports.append("|---------|-------|------|---------|-------|--------|")
            for days_str, stats in cd.get("hold_day_results", {}).items():
                reports.append(
                    f"| {days_str} | {stats['sample_count']} | "
                    f"{stats['win_rate']}% | {stats['avg_profit_pct']:.4f}% | "
                    f"{stats['total_profit_pct']:.2f}% | {stats['max_drawdown']:.2f}% |"
                )
            reports.append(f"\n最优持有: **{cd.get('optimal_hold_days')}** (平均收益 {cd.get('optimal_hold_stats', {}).get('avg_profit_pct', 0):.4f}%)\n")

        # 阈值优化
        opt = optimizer.find_optimal_threshold(code)
        if "error" not in opt:
            reports.append("### 信号阈值优化")
            reports.append(f"| 阈值 | 交易数 | 胜率 | 平均收益 |")
            reports.append("|------|-------|------|---------|")
            for r in opt.get("all_results", []):
                reports.append(
                    f"| {r['threshold']} | {r['total_trades']} | "
                    f"{r['win_rate']}% | {r['avg_profit_pct']:.4f}% |"
                )
            reports.append(f"\n最优阈值: **{opt.get('optimal_threshold')}** (胜率 {opt.get('optimal_win_rate', 0)}%, 平均 {opt.get('optimal_avg_profit', 0):.4f}%)\n")

    report_text = "\n".join(reports)
    out_path = os.path.join(DATA_DIR, f"backtest_report_{date.today().isoformat()}.md")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(report_text)
    print(f"\n报告已保存: {out_path}")
    return report_text


if __name__ == "__main__":
    run_full_optimization()
