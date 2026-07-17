"""
backtest_medallion_v2.py - 大奖章回测引擎 V2
核心修复：
  1. 百分比基准: (entry - current) / entry * 100 (正值=做空赚钱)
  2. 止盈: pnl_pct >= min_profit_take_pct 才平
  3. 止损: pnl_pct <= hard_stop_loss_pct 必平
  4. 飞仓: pnl_pct <= -flee_stop_pct 立即接回
"""

import sys, os, json, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict
from collections import defaultdict
from dataclasses import dataclass, field

from engine.tdx_parser import read_minute_kline, TDXBar
from engine.indicators import KBar, calc_vwap_bands, calc_rsi, calc_cumulative_delta
from medallion.config import STOCK_CONFIGS, BACKTEST
from medallion.signal_pipeline import SignalPipeline
from medallion.regime_clf import RegimeClassifier


@dataclass
class TradeRecord:
    day: str
    slot_id: int
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    profit_pct: float
    direction: str = "short"
    entry_score: float = 0.0
    factor_scores: Dict = field(default_factory=dict)
    regime: str = ""
    time_window: str = ""
    success: bool = False


@dataclass
class DayResult:
    date: str
    open: float
    high: float
    low: float
    close: float
    trades: List = field(default_factory=list)
    regime: str = ""
    pnl: float = 0.0
    signals_generated: int = 0


class BacktestMedallionV2:
    def __init__(self, code: str):
        self.code = code
        self.cfg = STOCK_CONFIGS[code]
        self.signal_pipe = SignalPipeline(code, self.cfg)
        self.regime_clf = RegimeClassifier(code)
        self.slippage = BACKTEST["slippage"]

    def run(self, all_min5_bars: List[KBar], all_daily_bars: List[KBar]) -> Dict:
        days_5min = defaultdict(list)
        for bar in all_min5_bars:
            days_5min[bar.date].append(bar)

        daily_index = {b.date: b for b in all_daily_bars}
        dates = sorted(days_5min.keys())

        all_results = []
        all_trades = []

        for date in dates:
            if date not in daily_index or len(days_5min[date]) < 10:
                continue

            min5 = days_5min[date]
            day_bar = daily_index[date]

            sorted_dates = sorted(daily_index.keys())
            idx = sorted_dates.index(date) if date in sorted_dates else -1
            prev_close = daily_index[sorted_dates[idx - 1]].close if idx > 0 else None

            day_result = self._backtest_day(date, min5, day_bar, prev_close, all_daily_bars)
            all_results.append(day_result)
            all_trades.extend(day_result.trades)

        return self._summarize(all_results, all_trades)

    def _backtest_day(self, date: str, min5_bars: List[KBar],
                      day_bar: KBar, prev_close: float, all_daily_bars: List[KBar]) -> DayResult:
        result = DayResult(
            date=date,
            open=day_bar.open,
            high=day_bar.high,
            low=day_bar.low,
            close=day_bar.close,
        )

        slots_open = {}
        daily_sell_count = 0
        daily_buy_count = 0

        regime_result = self.regime_clf.classify(all_daily_bars[-30:], min5_bars, prev_close)
        result.regime = regime_result["regime"]

        for i in range(6, len(min5_bars) - 1):
            bar = min5_bars[i]
            bars_so_far = min5_bars[:i + 1]
            current_price = bar.close
            current_time = _sec_to_time(bar.time_sec)

            to_close = []

            for slot_id, slot_info in list(slots_open.items()):
                entry_price = slot_info["entry_price"]
                # 核心: pnl_pct 正=做空赚钱, 负=亏
                pnl_pct = (entry_price - current_price) / entry_price * 100

                should_close = False
                stop_reason = ""

                # 止盈: 赚够了就走
                if pnl_pct >= self.cfg.min_profit_take_pct:
                    should_close = True
                    stop_reason = "止盈" + str(round(pnl_pct, 2)) + "%"
                # 止损: 亏太多必须走
                elif pnl_pct <= self.cfg.hard_stop_loss_pct:
                    should_close = True
                    stop_reason = "止损" + str(round(pnl_pct, 2)) + "%"
                # 飞仓: 价格继续朝反方向跑
                elif pnl_pct <= -self.cfg.flee_stop_pct:
                    should_close = True
                    stop_reason = "飞仓" + str(round(pnl_pct, 2)) + "%"
                else:
                    entry_time_str = slot_info["entry_time"]
                    hold_min = _minutes_between(entry_time_str, current_time)
                    if hold_min >= self.cfg.time_stop_minutes:
                        should_close = True
                        stop_reason = "时间止损" + str(int(hold_min)) + "min"

                if current_time >= "14:50" and slots_open:
                    should_close = True
                    stop_reason = "尾盘强平"

                if should_close:
                    exit_price = current_price * (1 + self.slippage)
                    profit_pct = (entry_price - exit_price) / entry_price * 100
                    to_close.append((slot_id, profit_pct, stop_reason, exit_price, current_time))

            for slot_id, profit_pct, stop_reason, exit_price, exit_time in to_close:
                slot_info = slots_open[slot_id]
                trade = TradeRecord(
                    day=date,
                    slot_id=slot_id,
                    entry_time=slot_info["entry_time"],
                    exit_time=exit_time,
                    entry_price=slot_info["entry_price"],
                    exit_price=exit_price,
                    profit_pct=profit_pct,
                    direction="short",
                    entry_score=slot_info.get("entry_score", 0),
                    factor_scores=slot_info.get("factor_scores", {}),
                    regime=result.regime,
                    time_window=_get_time_window(exit_time),
                    success=profit_pct > 0,
                )
                result.trades.append(trade)
                del slots_open[slot_id]
                daily_buy_count += 1

            # 检查开新仓 (倒T: 卖出等回落)
            if daily_sell_count < self.cfg.max_trades_per_day and len(slots_open) < 3:
                if result.regime not in ("EXTREME", "TREND_UP"):
                    signal = self.signal_pipe.evaluate(
                        current_price, bars_so_far, all_daily_bars[-30:], prev_close, result.regime
                    )
                    if signal.sell_score >= self.cfg.entry_score_threshold:
                        day_high = max(b.high for b in bars_so_far)
                        pct_from_high = (day_high / current_price - 1) * 100
                        if pct_from_high >= self.cfg.require_intraday_high_pct:
                            pass
                        else:
                            used_slots = list(slots_open.keys())
                            available = [s for s in [1, 2, 3] if s not in used_slots]
                            if available:
                                slot_id = available[0]
                                entry_price = current_price * (1 - self.slippage)
                                slots_open[slot_id] = {
                                    "entry_price": entry_price,
                                    "entry_time": current_time,
                                    "entry_score": signal.total_score,
                                    "factor_scores": {k: v.score for k, v in signal.factors.items()},
                                }
                                daily_sell_count += 1
                                result.signals_generated += 1

        # 日末强平
        for slot_id, slot_info in list(slots_open.items()):
            last_bar = min5_bars[-1]
            exit_price = last_bar.close * (1 + self.slippage)
            entry_price = slot_info["entry_price"]
            profit_pct = (entry_price - exit_price) / entry_price * 100
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
                time_window=_get_time_window(_sec_to_time(last_bar.time_sec)),
                success=profit_pct > 0,
            )
            result.trades.append(trade)

        result.pnl = sum(t.profit_pct for t in result.trades)
        return result

    def _summarize(self, days: list, trades: list) -> Dict:
        total_days = len(days)
        total_trades = len(trades)
        wins = [t for t in trades if t.success]
        losses = [t for t in trades if not t.success]
        win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
        avg_win = sum(t.profit_pct for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.profit_pct for t in losses) / len(losses) if losses else 0
        total_pnl = sum(t.profit_pct for t in trades)
        total_win_pnl = sum(t.profit_pct for t in wins)
        total_loss_pnl = abs(sum(t.profit_pct for t in losses)) if losses else 0
        profit_factor = total_win_pnl / total_loss_pnl if total_loss_pnl > 0 else 999

        regime_stats = defaultdict(list)
        for t in trades:
            regime_stats[t.regime].append(t)
        regime_summary = {}
        for regime, reg_trades in regime_stats.items():
            r_wins = [t for t in reg_trades if t.success]
            r_pnl = sum(t.profit_pct for t in reg_trades)
            regime_summary[regime] = {
                "count": len(reg_trades),
                "win_rate": round(len(r_wins) / len(reg_trades) * 100, 1) if reg_trades else 0,
                "total_pnl": round(r_pnl, 2),
                "avg_pnl": round(r_pnl / len(reg_trades), 3) if reg_trades else 0,
            }

        window_stats = defaultdict(list)
        for t in trades:
            window_stats[t.time_window].append(t)
        window_summary = {}
        for tw, tw_trades in sorted(window_stats.items()):
            w_wins = [t for t in tw_trades if t.success]
            w_pnl = sum(t.profit_pct for t in tw_trades)
            window_summary[tw] = {
                "count": len(tw_trades),
                "win_rate": round(len(w_wins) / len(tw_trades) * 100, 1) if tw_trades else 0,
                "total_pnl": round(w_pnl, 2),
            }

        factor_corr = self._calc_factor_corr(trades)
        daily_pnls = [(d.date, d.pnl) for d in days if d.trades]
        positive_days = sum(1 for _, p in daily_pnls if p > 0)
        best = sorted(trades, key=lambda t: -t.profit_pct)[:5]
        worst = sorted(trades, key=lambda t: t.profit_pct)[:5]

        return {
            "code": self.code,
            "name": self.cfg.name,
            "total_days": total_days,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
            "profit_factor": round(profit_factor, 2) if profit_factor != 999 else "N/A",
            "total_pnl": round(total_pnl, 2),
            "daily_avg_pnl": round(total_pnl / total_days, 4) if total_days else 0,
            "positive_days": positive_days,
            "positive_days_rate": round(positive_days / len(daily_pnls) * 100, 1) if daily_pnls else 0,
            "regime_summary": regime_summary,
            "window_summary": window_summary,
            "factor_correlation": factor_corr,
            "best_trades": [
                {"day": t.day, "entry": t.entry_time, "pnl": round(t.profit_pct, 3), "score": t.entry_score, "regime": t.regime}
                for t in best
            ],
            "worst_trades": [
                {"day": t.day, "entry": t.entry_time, "pnl": round(t.profit_pct, 3), "score": t.entry_score, "regime": t.regime}
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

    def _calc_factor_corr(self, trades: list) -> Dict:
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


def _sec_to_time(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    return str(h).zfill(2) + ":" + str(m).zfill(2)


def _minutes_between(t1: str, t2: str) -> float:
    h1, m1 = int(t1.split(":")[0]), int(t1.split(":")[1])
    h2, m2 = int(t2.split(":")[0]), int(t2.split(":")[1])
    return (h2 * 60 + m2) - (h1 * 60 + m1)


def _get_time_window(t: str) -> str:
    h, m = int(t.split(":")[0]), int(t.split(":")[1])
    total = h * 60 + m
    if total < 9 * 60 + 50:
        return "T1"
    elif total < 10 * 60 + 30:
        return "T2"
    elif total < 11 * 60:
        return "T3"
    elif total < 13 * 60:
        return "T4"
    elif total < 13 * 60 + 30:
        return "T5"
    elif total < 14 * 60:
        return "T6"
    elif total < 14 * 60 + 30:
        return "T7"
    else:
        return "T8"


if __name__ == "__main__":
    import json
    from engine.tdx_parser import read_minute_kline

    def tdx_to_kbar(b):
        return KBar(date=b.date, time_sec=b.time_sec, open=b.open, high=b.high,
                    low=b.low, close=b.close, amount=b.amount, volume=b.volume)

    json_path = r"F:\aidanao\data\kl_300418_1y.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    daily_bars_418 = [KBar(
        date=item["date"], time_sec=0,
        open=float(item["open"]), high=float(item["high"]),
        low=float(item["low"]), close=float(item["close"]),
        amount=float(item["amount"]), volume=float(item["volume"]),
    ) for item in data]

    print("=" * 60)
    print("大奖章系统回测 V2 (退出逻辑修复版) - 2026-07-04")
    print("=" * 60)
    print("日K: " + str(len(daily_bars_418)) + "条 (" + daily_bars_418[0].date + "~" + daily_bars_418[-1].date + ")")

    results = {}
    for code in ["300418", "300058"]:
        cfg = STOCK_CONFIGS[code]
        print("")
        print(">>> " + cfg.name + "(" + code + ") 回测...")

        min5_path = rf"F:\tongdaxin\vipdoc\sz\fzline\sz{code}.lc5"
        min5_raw = read_minute_kline(min5_path)
        min5_bars = [tdx_to_kbar(b) for b in min5_raw]

        print("    5分K: " + str(len(min5_bars)) + "条 (" + min5_bars[0].date + "~" + min5_bars[-1].date + ")")

        min5_dates = sorted(set(b.date for b in min5_bars))
        daily_map = {b.date: b for b in daily_bars_418}
        my_daily = [daily_map[d] for d in min5_dates if d in daily_map]
        print("    匹配日K: " + str(len(my_daily)) + "条")

        bt = BacktestMedallionV2(code)
        result = bt.run(min5_bars, my_daily)
        results[code] = result

        print("    回测天数: " + str(result["total_days"]))
        print("    总交易: " + str(result["total_trades"]) + "笔")
        print("    胜率: " + str(result["win_rate"]) + "%")
        print("    均盈利: " + str(result["avg_win"]) + "%, 均亏损: " + str(result["avg_loss"]) + "%")
        print("    盈亏比: " + str(result["profit_factor"]))
        print("    累计收益: " + str(result["total_pnl"]) + "%")
        print("    日均: " + str(result["daily_avg_pnl"]) + "%")

        out = "F:/aidanao/daytrade_system/output/backtest_v2_" + code + ".json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("    -> 已保存: " + out)

    if len(results) == 2:
        print("")
        print("=" * 60)
        print("目标达成检查")
        print("=" * 60)
        for code, r in results.items():
            name = STOCK_CONFIGS[code].name
            print("")
            print(name + "(" + code + "):")
            print("  胜率: " + str(r["win_rate"]) + "%")
            print("  均盈利: " + str(r["avg_win"]) + "%, 均亏损: " + str(r["avg_loss"]) + "%")
            print("  盈亏比: " + str(r["profit_factor"]))
            print("  累计收益: " + str(r["total_pnl"]) + "%")
            print("  日均收益: " + str(r["daily_avg_pnl"]) + "%")
            print("  正收益天数: " + str(r["positive_days"]) + "/" + str(r["total_days"]) + " (" + str(r["positive_days_rate"]) + "%)")

            print("  按市场状态:")
            for regime, stats in r.get("regime_summary", {}).items():
                print("    " + regime + ": " + str(stats["count"]) + "笔, 胜率" + str(stats["win_rate"]) + "%, 累计" + str(stats["total_pnl"]) + "%")

            print("  按时间窗口:")
            for tw in ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"]:
                if tw in r.get("window_summary", {}):
                    s = r["window_summary"][tw]
                    print("    " + tw + ": " + str(s["count"]) + "笔, 胜率" + str(s["win_rate"]) + "%, 累计" + str(s["total_pnl"]) + "%")

            print("  因子相关性:")
            for f, c in sorted(r.get("factor_correlation", {}).items(), key=lambda x: -abs(x[1])):
                sign = "+" if c > 0 else "-"
                print("    " + f + ": " + sign + str(abs(c)))

            print("  最佳交易:")
            for t in r.get("best_trades", []):
                print("    " + t["day"] + " " + t["entry"] + " pnl=" + str(t["pnl"]) + "% regime=" + t["regime"])

            print("  最差交易:")
            for t in r.get("worst_trades", []):
                print("    " + t["day"] + " " + t["entry"] + " pnl=" + str(t["pnl"]) + "% regime=" + t["regime"])
