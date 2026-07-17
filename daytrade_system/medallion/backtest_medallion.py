"""backtest_medallion.py — 大奖章系统回测引擎

核心功能：用新的六因子信号管道 + 严格止损，对99日历史数据回测，
验证系统是否具有正期望。

关键改进（相比旧引擎）：
  1. 信号来源：新6因子打分（原4因子太频繁，质量差）
  2. 止损：-1.0%硬止损（原-2.0%，导致盈亏比0.56崩溃）
  3. 飞逃：+2.0%立即接回（原+3.0%，T7大亏-5.0%）
  4. 门槛：68分开门（原60分，信号泛滥）
  5. 槽位：每只股票最多2笔/天（原各3笔）

验证目标：
  - 胜率 ≥ 65%
  - 盈亏比 ≥ 1.5
  - 累计收益 > 0
  - 日均正收益
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from engine.tdx_parser import read_minute_kline, read_daily_kline, group_by_date, TDXBar
from engine.indicators import KBar, calc_vwap_bands, calc_rsi, calc_cumulative_delta
from medallion.config import STOCK_CONFIGS, BACKTEST
from medallion.signal_pipeline import SignalPipeline
from medallion.regime_clf import RegimeClassifier


@dataclass
class TradeRecord:
    """回测交易记录"""
    day: str
    slot_id: int
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    profit_pct: float
    direction: str = "short"
    entry_score: float = 0.0
    factor_scores: Dict[str, float] = field(default_factory=dict)
    regime: str = ""
    time_window: str = ""
    success: bool = False


@dataclass
class DayResult:
    """单日回测结果"""
    date: str
    open: float
    high: float
    low: float
    close: float
    trades: List[TradeRecord] = field(default_factory=list)
    regime: str = ""
    pnl: float = 0.0
    signals_generated: int = 0


class BacktestMedallion:
    """
    大奖章系统回测引擎

    使用方法：
      bt = BacktestMedallion("300418")
      result = bt.run(min5_bars, daily_bars)
      report = bt.format_report(result)
    """

    def __init__(self, code: str):
        self.code = code
        self.cfg = STOCK_CONFIGS[code]
        self.signal_pipe = SignalPipeline(code, self.cfg)
        self.regime_clf = RegimeClassifier(code)
        self.slippage = BACKTEST["slippage"]

        # 槽位状态
        self.slots_open: Dict[int, Dict] = {}  # slot_id -> {entry_price, entry_time, entry_score, factors}
        self.daily_sell_count = 0
        self.daily_buy_count = 0

    def run(self, all_min5_bars: List[KBar], all_daily_bars: List[KBar]) -> Dict:
        """
        完整回测
        Returns: 回测结果字典
        """
        # 按日期分组
        days_5min = defaultdict(list)
        for bar in all_min5_bars:
            days_5min[bar.date].append(bar)

        daily_index = {b.date: b for b in all_daily_bars}
        dates = sorted(days_5min.keys())

        all_results: List[DayResult] = []
        all_trades: List[TradeRecord] = []

        for date in dates:
            if date not in daily_index or len(days_5min[date]) < 10:
                continue

            min5 = days_5min[date]
            day_bar = daily_index[date]

            # 前收盘
            sorted_dates = sorted(daily_index.keys())
            idx = sorted_dates.index(date) if date in sorted_dates else -1
            prev_close = daily_index[sorted_dates[idx - 1]].close if idx > 0 else None

            day_result = self._backtest_day(date, min5, day_bar, prev_close, all_daily_bars)
            all_results.append(day_result)
            all_trades.extend(day_result.trades)

        return self._summarize(all_results, all_trades)

    def _backtest_day(self, date: str, min5_bars: List[KBar],
                      day_bar: KBar, prev_close: float, all_daily_bars: List[KBar]) -> DayResult:
        """单日回测"""
        result = DayResult(
            date=date,
            open=day_bar.open,
            high=day_bar.high,
            low=day_bar.low,
            close=day_bar.close,
        )

        # 重置每日状态
        self.slots_open = {}
        self.daily_sell_count = 0
        self.daily_buy_count = 0

        # 分类市场状态
        regime_result = self.regime_clf.classify(all_daily_bars[-30:], min5_bars, prev_close)
        result.regime = regime_result["regime"]

        # 遍历每个5分K（从第6根开始，避免数据太少）
        for i in range(6, len(min5_bars) - 1):
            bar = min5_bars[i]
            bars_so_far = min5_bars[:i + 1]
            current_price = bar.close

            # 当前时间
            current_time = _sec_to_time(bar.time_sec)

            # === 1. 检查止损/飞逃 ===
            to_close = []
            for slot_id, slot_info in list(self.slots_open.items()):
                entry_price = slot_info["entry_price"]
                pnl_pct = (entry_price / current_price - 1) * 100

                stop_triggered = False
                reason = ""

                # 硬止损
                if pnl_pct <= self.cfg.hard_stop_loss_pct:
                    stop_triggered = True
                    reason = f"硬止损{pnl_pct:.2f}%"
                # 飞逃
                elif pnl_pct <= -self.cfg.flee_stop_pct:
                    stop_triggered = True
                    reason = f"飞逃止损{pnl_pct:.2f}%"
                # 时间止损
                entry_time_str = slot_info["entry_time"]
                hold_min = self._minutes_between(entry_time_str, current_time)
                if hold_min >= self.cfg.time_stop_minutes and pnl_pct < self.cfg.min_profit_take_pct:
                    stop_triggered = True
                    reason = f"时间止损{hold_min:.0f}min"
                # 尾盘强平
                if current_time >= "14:50" and self.slots_open:
                    stop_triggered = True
                    reason = f"尾盘强平{current_time}"

                if stop_triggered:
                    exit_price = current_price * (1 + self.slippage)
                    profit_pct = (entry_price / exit_price - 1) * 100
                    to_close.append(slot_id)

                    trade = TradeRecord(
                        day=date,
                        slot_id=slot_id,
                        entry_time=entry_time_str,
                        exit_time=current_time,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        profit_pct=profit_pct,
                        direction="short",
                        entry_score=slot_info.get("entry_score", 0),
                        factor_scores=slot_info.get("factor_scores", {}),
                        regime=result.regime,
                        time_window=self._get_time_window(current_time),
                        success=profit_pct > 0,
                    )
                    result.trades.append(trade)

            # 平仓
            for slot_id in to_close:
                del self.slots_open[slot_id]
                self.daily_buy_count += 1

            # === 2. 检查接回机会 ===
            for slot_id, slot_info in list(self.slots_open.items()):
                entry_price = slot_info["entry_price"]

                # 价格回到卖出价
                if current_price <= entry_price * 1.001:
                    pnl_pct = (entry_price / current_price - 1) * 100
                    if pnl_pct >= 0.1:
                        exit_price = current_price * (1 + self.slippage)
                        profit_pct = (entry_price / exit_price - 1) * 100

                        trade = TradeRecord(
                            day=date,
                            slot_id=slot_id,
                            entry_time=slot_info["entry_time"],
                            exit_time=current_time,
                            entry_price=entry_price,
                            exit_price=exit_price,
                            profit_pct=profit_pct,
                            direction="short",
                            entry_score=slot_info.get("entry_score", 0),
                            factor_scores=slot_info.get("factor_scores", {}),
                            regime=result.regime,
                            time_window=self._get_time_window(current_time),
                            success=profit_pct > 0,
                        )
                        result.trades.append(trade)
                        del self.slots_open[slot_id]
                        self.daily_buy_count += 1

            # === 3. 检查开新仓 ===
            if self.daily_sell_count < self.cfg.max_trades_per_day and len(self.slots_open) < 3:
                # 评估信号
                signal = self.signal_pipe.evaluate(
                    current_price, bars_so_far, all_daily_bars[-30:], prev_close, result.regime
                )

                if signal.sell_score >= self.cfg.entry_score_threshold:
                    # 检查是否距日内高点足够回撤
                    day_high = max(b.high for b in bars_so_far)
                    pct_from_high = (day_high / current_price - 1) * 100
                    if pct_from_high < self.cfg.require_intraday_high_pct:
                        continue  # 回撤不够，不开仓

                    # 有空槽
                    used_slots = list(self.slots_open.keys())
                    available = [s for s in [1, 2, 3] if s not in used_slots]
                    if not available:
                        continue

                    slot_id = available[0]
                    entry_price = current_price * (1 - self.slippage)

                    self.slots_open[slot_id] = {
                        "entry_price": entry_price,
                        "entry_time": current_time,
                        "entry_score": signal.total_score,
                        "factor_scores": {k: v.score for k, v in signal.factors.items()},
                    }
                    self.daily_sell_count += 1
                    result.signals_generated += 1

        # === 4. 日末强平未接回仓位 ===
        for slot_id, slot_info in list(self.slots_open.items()):
            last_bar = min5_bars[-1]
            exit_price = last_bar.close * (1 + self.slippage)
            entry_price = slot_info["entry_price"]
            profit_pct = (entry_price / exit_price - 1) * 100

            trade = TradeRecord(
                day=date,
                slot_id=slot_id,
                entry_time=slot_info["entry_time"],
                exit_time=_sec_to_time(last_bar.time_sec),
                entry_price=entry_price,
                exit_price=exit_price,
                profit_pct=profit_pct,
                direction="short",
                entry_score=slot_info.get("entry_score", 0),
                factor_scores=slot_info.get("factor_scores", {}),
                regime=result.regime,
                time_window=self._get_time_window(_sec_to_time(last_bar.time_sec)),
                success=profit_pct > 0,
            )
            result.trades.append(trade)

        result.pnl = sum(t.profit_pct for t in result.trades)
        return result

    def _minutes_between(self, t1: str, t2: str) -> float:
        h1, m1 = int(t1.split(":")[0]), int(t1.split(":")[1])
        h2, m2 = int(t2.split(":")[0]), int(t2.split(":")[1])
        return (h2 * 60 + m2) - (h1 * 60 + m1)

    def _get_time_window(self, t: str) -> str:
        h, m = int(t.split(":")[0]), int(t.split(":")[1])
        mins = h * 60 + m
        if mins < 9 * 60 + 50: return "T1"
        elif mins < 10 * 60 + 30: return "T2"
        elif mins < 11 * 60: return "T3"
        elif mins < 11 * 60 + 30: return "T4"
        elif mins < 13 * 60 + 30: return "T5"
        elif mins < 14 * 60: return "T6"
        elif mins < 14 * 60 + 30: return "T7"
        else: return "T8"

    def _summarize(self, days: List[DayResult], trades: List[TradeRecord]) -> Dict:
        """汇总统计"""
        total_days = len(days)
        total_trades = len(trades)
        if total_trades == 0:
            return {"total_days": total_days, "total_trades": 0, "error": "无有效交易"}

        wins = [t for t in trades if t.success]
        losses = [t for t in trades if not t.success]

        win_rate = len(wins) / total_trades * 100
        avg_win = sum(t.profit_pct for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.profit_pct for t in losses) / len(losses) if losses else 0
        total_pnl = sum(t.profit_pct for t in trades)

        profit_factor = abs(sum(t.profit_pct for t in wins) / sum(t.profit_pct for t in losses)) \
            if losses and sum(t.profit_pct for t in losses) != 0 else 999

        # 按市场状态统计
        regime_stats = defaultdict(list)
        for t in trades:
            regime_stats[t.regime].append(t)

        regime_summary = {}
        for regime, reg_trades in regime_stats.items():
            r_wins = [t for t in reg_trades if t.success]
            r_pnl = sum(t.profit_pct for t in reg_trades)
            regime_summary[regime] = {
                "count": len(reg_trades),
                "win_rate": len(r_wins) / len(reg_trades) * 100,
                "total_pnl": round(r_pnl, 2),
                "avg_pnl": round(r_pnl / len(reg_trades), 3) if reg_trades else 0,
            }

        # 按时间窗口统计
        window_stats = defaultdict(list)
        for t in trades:
            window_stats[t.time_window].append(t)

        window_summary = {}
        for tw, tw_trades in sorted(window_stats.items()):
            w_wins = [t for t in tw_trades if t.success]
            w_pnl = sum(t.profit_pct for t in tw_trades)
            window_summary[tw] = {
                "count": len(tw_trades),
                "win_rate": len(w_wins) / len(tw_trades) * 100,
                "total_pnl": round(w_pnl, 2),
            }

        # 因子相关性（简化）
        factor_corr = self._calc_factor_corr(trades)

        # 每日收益
        daily_pnls = [(d.date, d.pnl) for d in days if d.trades]
        positive_days = sum(1 for _, p in daily_pnls if p > 0)

        # 最佳/最差交易
        best = sorted(trades, key=lambda t: -t.profit_pct)[:5]
        worst = sorted(trades, key=lambda t: t.profit_pct)[:5]

        return {
            "code": self.code,
            "name": self.cfg.name,
            "total_days": total_days,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "avg_win": round(avg_win, 3),
            "avg_loss": round(avg_loss, 3),
            "profit_factor": round(profit_factor, 2) if profit_factor != 999 else "N/A",
            "total_pnl": round(total_pnl, 2),
            "daily_avg_pnl": round(total_pnl / total_days, 4) if total_days else 0,
            "positive_days": positive_days,
            "positive_days_rate": round(positive_days / len(daily_pnls) * 100, 1) if daily_pnls else 0,
            "regime_summary": regime_summary,
            "window_summary": window_summary,
            "factor_correlation": factor_corr,
            "best_trades": [
                {"day": t.day, "entry": t.entry_time, "pnl": t.profit_pct, "score": t.entry_score, "regime": t.regime}
                for t in best
            ],
            "worst_trades": [
                {"day": t.day, "entry": t.entry_time, "pnl": t.profit_pct, "score": t.entry_score, "regime": t.regime}
                for t in worst
            ],
            "all_trades": [
                {"day": t.day, "slot": t.slot_id, "entry": t.entry_time, "exit": t.exit_time,
                 "entry_px": t.entry_price, "exit_px": t.exit_price,
                 "pnl": round(t.profit_pct, 3), "success": t.success,
                 "score": t.entry_score, "regime": t.regime, "tw": t.time_window}
                for t in trades
            ],
        }

    def _calc_factor_corr(self, trades: List[TradeRecord]) -> Dict[str, float]:
        """计算因子与盈亏的相关性"""
        if len(trades) < 10:
            return {}

        pnls = [t.profit_pct for t in trades]
        pnls_mean = sum(pnls) / len(pnls)
        pnls_std = (sum((p - pnls_mean)**2 for p in pnls) / len(pnls)) ** 0.5
        if pnls_std == 0:
            return {}

        factors = ["F1", "F2", "F3", "F4", "F5", "F6"]
        corr = {}
        for f in factors:
            f_scores = [t.factor_scores.get(f, 0) for t in trades]
            f_mean = sum(f_scores) / len(f_scores)
            f_std = (sum((s - f_mean)**2 for s in f_scores) / len(f_scores)) ** 0.5
            if f_std > 0:
                cov = sum((pnls[i] - pnls_mean) * (f_scores[i] - f_mean) for i in range(len(trades))) / len(trades)
                corr[f] = round(cov / (f_std * pnls_std), 3)
            else:
                corr[f] = 0.0
        return corr


# ============================================================
# 工具函数
# ============================================================
def _sec_to_time(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    return f"{h:02d}:{m:02d}"


def tdx_to_kbar(b: TDXBar) -> KBar:
    return KBar(
        date=b.date, time_sec=b.time_sec,
        open=b.open, high=b.high, low=b.low, close=b.close,
        amount=b.amount, volume=b.volume,
    )


def run_backtest_for_code(code: str) -> Dict:
    """快速回测入口"""
    TDX_BASE = r"F:\tongdaxin\vipdoc\sz"
    cfg = {"min5": "fzline", "day": "lday"}

    day_path = os.path.join(TDX_BASE, cfg["day"], f"sz{code}.day")
    min5_path = os.path.join(TDX_BASE, cfg["min5"], f"sz{code}.lc5")

    if not os.path.exists(day_path) or not os.path.exists(min5_path):
        return {"error": f"数据文件不存在: {code}"}

    daily_raw = read_daily_kline(day_path)
    min5_raw = read_minute_kline(min5_path)

    daily_bars = [tdx_to_kbar(b) for b in daily_raw]
    min5_bars = [tdx_to_kbar(b) for b in min5_raw]

    bt = BacktestMedallion(code)
    return bt.run(min5_bars, daily_bars)


def format_backtest_report(result: Dict) -> str:
    """格式化回测报告"""
    if "error" in result:
        return f"回测失败: {result['error']}"

    lines = [
        f"# {result['name']}({result['code']}) — 大奖章系统回测报告",
        f"",
        f"## 核心指标",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 回测天数 | {result['total_days']}天 |",
        f"| 总交易笔数 | {result['total_trades']}笔 |",
        f"| 胜率 | **{result['win_rate']}%** |",
        f"| 平均盈利 | {result['avg_win']:+.3f}% |",
        f"| 平均亏损 | {result['avg_loss']:+.3f}% |",
        f"| 盈亏比 | {result['profit_factor']} |",
        f"| 累计收益 | {result['total_pnl']:+.2f}% |",
        f"| 日均收益 | {result['daily_avg_pnl']:+.4f}% |",
        f"| 正收益天数 | {result['positive_days']}天({result['positive_days_rate']}%) |",
        f"",
    ]

    # 因子相关性
    if result.get("factor_correlation"):
        lines.append("## 因子相关性（与盈亏）")
        for f, c in sorted(result["factor_correlation"].items(), key=lambda x: -abs(x[1])):
            sign = "+" if c > 0 else "-"
            lines.append(f"  {f}: {sign}{abs(c):.3f}")
        lines.append("")

    # 市场状态
    if result.get("regime_summary"):
        lines.append("## 按市场状态")
        lines.append("| 状态 | 笔数 | 胜率 | 累计收益 | 均收益 |")
        lines.append("|------|------|------|---------|--------|")
        for regime, stats in sorted(result["regime_summary"].items()):
            lines.append(f"| {regime} | {stats['count']} | {stats['win_rate']:.0f}% | {stats['total_pnl']:+.2f}% | {stats['avg_pnl']:+.3f}% |")
        lines.append("")

    # 时间窗口
    if result.get("window_summary"):
        lines.append("## 按时间窗口")
        for tw in ["T1","T2","T3","T4","T5","T6","T7","T8"]:
            if tw in result["window_summary"]:
                s = result["window_summary"][tw]
                lines.append(f"  {tw}: {s['count']}笔 胜率{s['win_rate']:.0f}% {s['total_pnl']:+.2f}%")
        lines.append("")

    # 目标达成
    lines.append("## 目标达成")
    checks = [
        ("胜率≥65%", result["win_rate"] >= 65, f"{result['win_rate']}%"),
        ("盈亏比≥1.5", result["profit_factor"] != "N/A" and float(result["profit_factor"]) >= 1.5, str(result["profit_factor"])),
        ("累计收益>0", result["total_pnl"] > 0, f"{result['total_pnl']:+.2f}%"),
        ("日均正收益", result["daily_avg_pnl"] > 0, f"{result['daily_avg_pnl']:+.4f}%"),
    ]
    for name, passed, value in checks:
        icon = "[PASS]" if passed else "[FAIL]"
        lines.append(f"  {icon} {name}: {value}")

    return "\n".join(lines)
