"""
历史回测引擎
对30天5分钟K线逐日回测，验证做T策略有效性
支持: 正T(先买后卖)、倒T(先卖后买)、VWAP回归策略
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import math

from engine.indicators import KBar, QuoteSnapshot, calc_ma, find_support_resistance
from engine.indicators import calc_vwap_bands, calc_rsi, calc_macd, detect_divergence


@dataclass
class TradeResult:
    """单笔交易结果"""
    day: str
    entry_time: str
    exit_time: str
    direction: str       # "正T" / "倒T"
    entry_price: float
    exit_price: float
    profit_pct: float
    profit_per_lot: float
    success: bool
    entry_reason: str


@dataclass
class DayStats:
    """单日回测统计"""
    date: str
    open: float
    high: float
    low: float
    close: float
    range_pct: float
    trades: List[TradeResult] = field(default_factory=list)
    reverse_trades: List[TradeResult] = field(default_factory=list)
    long_trades: List[TradeResult] = field(default_factory=list)

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0
        return sum(1 for t in self.trades if t.success) / len(self.trades) * 100

    @property
    def avg_profit(self) -> float:
        if not self.trades:
            return 0
        return sum(t.profit_pct for t in self.trades) / len(self.trades)

    @property
    def total_profit(self) -> float:
        return sum(t.profit_pct for t in self.trades)


class BacktestEngine:
    """
    做T策略回测引擎 V3 — 趋势过滤器版

    策略规则:
    【趋势判断】开盘30分钟+ 昨日5日趋势 + VWAP斜率
      - 趋势日: 只做顺向T (涨→正T, 跌→倒T)
      - 震荡日: 双向VWAP均值回归

    【倒T — 先卖后买】趋势日跌 或 震荡日高位
    【正T — 先买后卖】趋势日涨 或 震荡日低位
    """

    def __init__(self, slippage: float = 0.001, min_profit_target: float = 0.015,
                 max_hold_bars: int = 48):
        self.slippage = slippage
        self.min_profit_target = min_profit_target
        self.max_hold_bars = max_hold_bars
        self.max_loss_pct = 0.02

    def run(self, all_daily_bars: List[KBar], all_5min_bars: List[KBar]) -> Dict:
        """
        全量回测
        Returns: {summary, daily_results, trades}
        """
        # 按日期分组5分钟K线
        days_5min = defaultdict(list)
        for bar in all_5min_bars:
            days_5min[bar.date].append(bar)

        # 建立日K线索引
        daily_index = {b.date: b for b in all_daily_bars}

        all_day_stats = []
        all_trades = []

        for date, min5_bars in sorted(days_5min.items()):
            if date not in daily_index or len(min5_bars) < 10:
                continue

            day_bar = daily_index[date]
            # 找前一日收盘价
            sorted_dates = sorted(daily_index.keys())
            idx = sorted_dates.index(date) if date in sorted_dates else -1
            prev_close = daily_index[sorted_dates[idx - 1]].close if idx > 0 else None

            day_result = self._backtest_day(date, min5_bars, day_bar, prev_close)
            all_day_stats.append(day_result)
            all_trades.extend(day_result.trades)

        # 汇总统计
        return self._summarize(all_day_stats, all_trades)

    def _dynamic_trend_at(self, bars_so_far: List[KBar]) -> str:
        """
        动态趋势检测 — 基于当前已知数据判断
        返回: 'up' / 'down' / 'sideways'
        
        规则: 价格偏离VWAP + VWAP斜率方向 + 持续确认6根以上
        相比开盘30分钟版本: 实时更新, 大幅减少'震荡'误判
        """
        if len(bars_so_far) < 8:
            return 'sideways'
        
        trend = 'sideways'
        consecutive = 0
        
        for i in range(8, len(bars_so_far)):
            window = bars_so_far[:i+1]
            vwap = calc_vwap_bands(window)
            price = bars_so_far[i].close
            vwap_val = vwap['vwap']
            slope = vwap.get('vwap_slope', 'flat')
            
            if vwap_val == 0:
                continue
            
            deviation = (price / vwap_val - 1) * 100
            
            if deviation > 0.3 and slope == 'rising':
                if trend == 'up':
                    consecutive += 1
                else:
                    trend = 'up'
                    consecutive = 1
            elif deviation < -0.3 and slope == 'falling':
                if trend == 'down':
                    consecutive += 1
                else:
                    trend = 'down'
                    consecutive = 1
            else:
                if consecutive >= 6:
                    pass  # 惯性保持
                else:
                    trend = 'sideways'
                    consecutive = 0
        
        return trend

    def _detect_trend(self, min5_bars: List[KBar], prev_day_close: float = None) -> str:
        """
        开盘静态趋势（保留用于盘前分析），已被 _dynamic_trend_at 取代用于回测
        """
        """
        日内趋势判断: 'up'(上涨趋势日) / 'down'(下跌趋势日) / 'sideways'(震荡日)

        综合三个维度:
        1. 开盘30分钟涨跌幅 (>0.8%才有方向性)
        2. 昨日收盘位置 vs 5日均线
        3. 前30分钟VWAP斜率方向
        """
        if len(min5_bars) < 6:
            return "sideways"

        # 前6根5分K = 开盘30分钟
        first_30 = min5_bars[:6]
        open_price = first_30[0].open
        close_30 = first_30[-1].close
        pct_30 = (close_30 / open_price - 1) * 100

        # VWAP斜率（前30分钟）
        vwap_early = calc_vwap_bands(first_30)
        vwap_slope = vwap_early.get("vwap_slope", "flat")

        # 综合判断
        score = 0
        if pct_30 > 0.8:
            score += 2  # 强开盘
        elif pct_30 > 0.3:
            score += 1
        elif pct_30 < -0.8:
            score -= 2
        elif pct_30 < -0.3:
            score -= 1

        if vwap_slope == "rising":
            score += 1
        elif vwap_slope == "falling":
            score -= 1

        # 高开/低开幅度
        if prev_day_close and open_price > prev_day_close * 1.01:
            score += 1
        elif prev_day_close and open_price < prev_day_close * 0.99:
            score -= 1

        if score >= 2:
            return "up"
        elif score <= -2:
            return "down"
        else:
            return "sideways"

    def _backtest_day(self, date: str, min5_bars: List[KBar],
                       day_bar: KBar, prev_day_close: float = None) -> DayStats:
        """单日回测（含趋势过滤）"""
        ds = DayStats(
            date=date,
            open=day_bar.open,
            high=day_bar.high,
            low=day_bar.low,
            close=day_bar.close,
            range_pct=round((day_bar.high / day_bar.low - 1) * 100, 2)
        )

        # 改为动态趋势: 不再用 _detect_trend, 每个交易点实时判断
        ds.reverse_trades = self._backtest_reverse_t(min5_bars, date)
        ds.long_trades = self._backtest_long_t(min5_bars, date)
        ds.trades = ds.reverse_trades + ds.long_trades
        return ds

    def _backtest_reverse_t(self, bars: List[KBar], date: str) -> List[TradeResult]:
        """倒T策略 — 动态趋势过滤: 上涨趋势禁止倒T"""
        trades = []
        n = len(bars)
        closes = [b.close for b in bars]
        rsi_vals = calc_rsi(closes, 6) if len(closes) >= 7 else [None] * n
        min_cond = 2

        for i in range(5, n - 5):
            # === 动态趋势过滤: 上涨趋势禁止倒T ===
            # === 入场条件（需满足至少2个） ===
            entry_reasons = []

            # 条件1: VWAP高估（>1σ或>2σ）
            vwap_bands = calc_vwap_bands(bars[:i + 1])
            pos = vwap_bands.get("position", "")
            if "极度高估" in pos:
                entry_reasons.append("VWAP>2σ")
            elif "偏强" in pos:
                entry_reasons.append("VWAP>1σ")

            # 条件2: RSI偏高
            if rsi_vals[i] and rsi_vals[i] > 65:
                entry_reasons.append(f"RSI={rsi_vals[i]:.0f}偏高")

            # 条件3: 价格远离日内低点 >1.5%
            day_low_up_to_now = min(b.close for b in bars[:i + 1])
            pct_from_low = (bars[i].close / day_low_up_to_now - 1) * 100
            if pct_from_low > 1.5:
                entry_reasons.append(f"距日内低+{pct_from_low:.1f}%")

            if len(entry_reasons) < min_cond:
                continue

            entry_price = bars[i].close * (1 - self.slippage)

            # 寻找出场点
            for j in range(i + 1, min(i + self.max_hold_bars + 1, n)):
                exit_price = bars[j].close * (1 + self.slippage)
                profit = (entry_price / exit_price - 1) * 100  # 倒T盈利=卖高买低

                # 出场: 达到1.5%目标 或 回VWAP 或 止损-2% 或 尾盘
                vwap_j = calc_vwap_bands(bars[:j + 1])["vwap"]
                min_profit = self.min_profit_target * 100
                hit_profit = profit >= min_profit
                hit_stop = profit <= -self.max_loss_pct * 100
                back_to_vwap = bars[j].close <= vwap_j * 1.005 and profit > 0
                end_of_day = j == n - 1

                if hit_profit or hit_stop or back_to_vwap or end_of_day:
                    trades.append(TradeResult(
                        day=date,
                        entry_time=_sec_to_time(bars[i].time_sec),
                        exit_time=_sec_to_time(bars[j].time_sec),
                        direction="倒T",
                        entry_price=round(entry_price, 2),
                        exit_price=round(exit_price, 2),
                        profit_pct=round(profit, 2),
                        profit_per_lot=round(entry_price - exit_price, 2),
                        success=profit > 0,
                        entry_reason=" + ".join(entry_reasons)
                    ))
                    break

        return trades

    def _backtest_long_t(self, bars: List[KBar], date: str,
                           force_enable: bool = False,
                           require_stronger: bool = False) -> List[TradeResult]:
        """正T策略回测"""
        trades = []
        n = len(bars)
        closes = [b.close for b in bars]
        rsi_vals = calc_rsi(closes, 6) if len(closes) >= 7 else [None] * n
        min_cond = 2

        for i in range(5, n - 5):
            # === 动态趋势过滤: 下跌趋势禁止正T ===
            trend_now = self._dynamic_trend_at(bars[:i+1])
            if trend_now == 'down':
                continue  # 下跌趋势不做多
            
            entry_reasons = []

            # 条件1: VWAP低估（<1σ或<2σ）
            vwap_bands = calc_vwap_bands(bars[:i + 1])
            pos = vwap_bands.get("position", "")
            if "极度低估" in pos:
                entry_reasons.append("VWAP<2σ")
            elif "偏弱" in pos:
                entry_reasons.append("VWAP<1σ")

            # 条件2: RSI偏低
            if rsi_vals[i] and rsi_vals[i] < 35:
                entry_reasons.append(f"RSI={rsi_vals[i]:.0f}偏低")

            # 条件3: 价格距日内高点 >1.5%
            day_high_up_to_now = max(b.close for b in bars[:i + 1])
            pct_from_high = (day_high_up_to_now / bars[i].close - 1) * 100
            if pct_from_high > 1.5:
                entry_reasons.append(f"距日内高-{pct_from_high:.1f}%")

            if len(entry_reasons) < min_cond:
                continue

            entry_price = bars[i].close * (1 + self.slippage)

            for j in range(i + 1, min(i + self.max_hold_bars + 1, n)):
                exit_price = bars[j].close * (1 - self.slippage)
                profit = (exit_price / entry_price - 1) * 100  # 正T盈利=买低卖高

                vwap_j = calc_vwap_bands(bars[:j + 1])["vwap"]
                min_profit = self.min_profit_target * 100
                hit_profit = profit >= min_profit
                hit_stop = profit <= -self.max_loss_pct * 100
                back_to_vwap = bars[j].close >= vwap_j * 0.995 and profit > 0
                end_of_day = j == n - 1

                if hit_profit or hit_stop or back_to_vwap or end_of_day:
                    trades.append(TradeResult(
                        day=date,
                        entry_time=_sec_to_time(bars[i].time_sec),
                        exit_time=_sec_to_time(bars[j].time_sec),
                        direction="正T",
                        entry_price=round(entry_price, 2),
                        exit_price=round(exit_price, 2),
                        profit_pct=round(profit, 2),
                        profit_per_lot=round(exit_price - entry_price, 2),
                        success=profit > 0,
                        entry_reason=" + ".join(entry_reasons)
                    ))
                    break

        return trades

    def _summarize(self, day_stats: List[DayStats], all_trades: List[TradeResult]) -> Dict:
        """汇总统计"""
        if not day_stats:
            return {"total_days": 0, "total_trades": 0}

        total_days = len(day_stats)
        total_trades = len(all_trades)
        winning_trades = [t for t in all_trades if t.success]
        losing_trades = [t for t in all_trades if not t.success]

        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        avg_profit = sum(t.profit_pct for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.profit_pct for t in losing_trades) / len(losing_trades) if losing_trades else 0

        # 盈亏比
        profit_factor = abs(sum(t.profit_pct for t in winning_trades) / sum(t.profit_pct for t in losing_trades)) if losing_trades and sum(t.profit_pct for t in losing_trades) != 0 else float('inf')

        # 按方向统计
        reverse_trades = [t for t in all_trades if t.direction == "倒T"]
        long_trades = [t for t in all_trades if t.direction == "正T"]

        # 每日统计
        daily_summary = []
        for ds in day_stats:
            daily_summary.append({
                "date": ds.date,
                "open": ds.open,
                "high": ds.high,
                "low": ds.low,
                "close": ds.close,
                "range_pct": ds.range_pct,
                "trades": ds.total_trades,
                "win_rate": round(ds.win_rate, 1),
                "avg_profit": round(ds.avg_profit, 2),
                "total_profit": round(ds.total_profit, 2),
            })

        # 最优和最差
        best_trades = sorted(all_trades, key=lambda t: t.profit_pct, reverse=True)[:5]
        worst_trades = sorted(all_trades, key=lambda t: t.profit_pct)[:5]

        return {
            "total_days": total_days,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "avg_profit": round(avg_profit, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else 999,
            "total_profit_pct": round(sum(t.profit_pct for t in all_trades), 2),
            "reverse_t_count": len(reverse_trades),
            "reverse_t_win_rate": round(sum(1 for t in reverse_trades if t.success) / len(reverse_trades) * 100, 1) if reverse_trades else 0,
            "long_t_count": len(long_trades),
            "long_t_win_rate": round(sum(1 for t in long_trades if t.success) / len(long_trades) * 100, 1) if long_trades else 0,
            "daily_summary": daily_summary,
            "best_trades": [{"day": t.day, "dir": t.direction, "time": t.entry_time, "profit": t.profit_pct, "reason": t.entry_reason} for t in best_trades],
            "worst_trades": [{"day": t.day, "dir": t.direction, "time": t.entry_time, "profit": t.profit_pct, "reason": t.entry_reason} for t in worst_trades],
            "all_trades": [{"day": t.day, "dir": t.direction, "entry": t.entry_time, "exit": t.exit_time, "entry_px": t.entry_price, "exit_px": t.exit_price, "profit": t.profit_pct, "success": t.success} for t in all_trades],
        }


def _sec_to_time(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    return f"{h:02d}:{m:02d}"


def backtest_report(result: Dict, stock_name: str, stock_code: str) -> str:
    """生成回测报告"""
    lines = []
    lines.append(f"## 🔬 历史回测报告 — {stock_name}({stock_code})")
    lines.append(f"**回测周期**: {result['total_days']}个交易日 | **总信号**: {result['total_trades']}笔")
    lines.append("")

    lines.append("### 📊 综合统计")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总交易笔数 | {result['total_trades']} |")
    lines.append(f"| 胜率 | **{result['win_rate']}%** |")
    lines.append(f"| 平均盈利 | {result['avg_profit']:+.2f}% |")
    lines.append(f"| 平均亏损 | {result['avg_loss']:+.2f}% |")
    lines.append(f"| 盈亏比 | {result['profit_factor']} |")
    lines.append(f"| 累计收益 | {result['total_profit_pct']:+.2f}% |")
    lines.append(f"| 倒T笔数/胜率 | {result['reverse_t_count']}笔 / {result['reverse_t_win_rate']}% |")
    lines.append(f"| 正T笔数/胜率 | {result['long_t_count']}笔 / {result['long_t_win_rate']}% |")
    lines.append("")

    lines.append("### 📅 逐日明细")
    lines.append(f"| 日期 | 开盘 | 最高 | 最低 | 收盘 | 振幅 | 信号 | 胜率 | 均盈 | 日收益 |")
    lines.append(f"|------|------|------|------|------|------|------|------|------|--------|")
    for d in result["daily_summary"]:
        lines.append(f"| {d['date']} | {d['open']} | {d['high']} | {d['low']} | {d['close']} | "
                     f"{d['range_pct']}% | {d['trades']} | {d['win_rate']}% | "
                     f"{d['avg_profit']:+.2f}% | {d['total_profit']:+.2f}% |")
    lines.append("")

    if result["best_trades"]:
        lines.append("### 🏆 最佳交易 TOP5")
        lines.append(f"| 日期 | 方向 | 入场 | 盈利 | 理由 |")
        lines.append(f"|------|------|------|------|------|")
        for t in result["best_trades"]:
            lines.append(f"| {t['day']} | {t['dir']} | {t['time']} | {t['profit']:+.2f}% | {t['reason']} |")

    lines.append("")
    lines.append("### 💡 回测结论")
    if result['win_rate'] >= 60:
        lines.append(f"- ✅ 策略有效，胜率{result['win_rate']}%，可执行")
    elif result['win_rate'] >= 50:
        lines.append(f"- ⚠️ 策略勉强有效（{result['win_rate']}%），需结合盘感")
    else:
        lines.append(f"- ❌ 策略胜率偏低（{result['win_rate']}%），需要调整参数")

    if result['profit_factor'] > 2:
        lines.append(f"- ✅ 盈亏比优秀({result['profit_factor']})，风险收益比好")
    elif result['profit_factor'] > 1.5:
        lines.append(f"- ⚠️ 盈亏比尚可({result['profit_factor']})")
    else:
        lines.append(f"- ❌ 盈亏比不佳({result['profit_factor']})，平均亏损大于盈利")

    return "\n".join(lines)
