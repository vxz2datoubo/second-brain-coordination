
"""
V5: Simple Rule-Based Backtest - Focus on signal quality over quantity
Strategy: Much higher entry threshold + wider profit targets
Key changes from V4:
  1. Simple RSI-based signals only (no complex pipeline)
  2. High entry threshold (sell_score >= 50 instead of 40)
  3. Wider profit targets (0.8-1.5% take-profit)
  4. Only T2 window (09:50-10:30)
  5. Max 1 trade per day per stock
"""

import sys, os, json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict

sys.path.insert(0, "F:/aidanao/daytrade_system")
from engine.tdx_parser import read_minute_kline
from engine.indicators import KBar
from medallion.config import STOCK_CONFIGS, BACKTEST
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


def _sec_to_time(sec):
    return str(sec//3600).zfill(2) + ":" + str((sec%3600)//60).zfill(2)


def _minutes_between(t1, t2):
    h1,m1 = int(t1.split(":")[0]), int(t1.split(":")[1])
    h2,m2 = int(t2.split(":")[0]), int(t2.split(":")[1])
    return (h2*60+m2)-(h1*60+m1)


def _get_time_window(t):
    h,m = int(t.split(":")[0]), int(t.split(":")[1])
    total = h*60+m
    if total < 9*60+50: return "T1"
    elif total < 10*60+30: return "T2"
    elif total < 11*60: return "T3"
    elif total < 13*60: return "T4"
    elif total < 13*60+30: return "T5"
    elif total < 14*60: return "T6"
    elif total < 14*60+30: return "T7"
    else: return "T8"


def _calc_rsi6(closes):
    if len(closes) < 7: return 50
    gains = [max(closes[i]-closes[i-1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i-1]-closes[i], 0) for i in range(1, len(closes))]
    ag = sum(gains[-6:])/6
    al = sum(losses[-6:])/6
    if al == 0: return 100
    return 100 - 100/(1 + ag/al)


class SimpleSignal:
    """Simple RSI + time-based signal"""
    def __init__(self, code):
        self.code = code
        self.cfg = STOCK_CONFIGS[code]

    def evaluate(self, bars_so_far, prev_close, regime):
        """Return sell_score 0-100"""
        if len(bars_so_far) < 5:
            return {"sell_score": 0, "reasons": []}

        closes = [b.close for b in bars_so_far]
        highs = [b.high for b in bars_so_far]
        vols = [b.volume for b in bars_so_far]
        time_sec = bars_so_far[-1].time_sec
        current_price = closes[-1]

        score = 0
        reasons = []

        # R1: RSI overbought
        rsi = _calc_rsi6(closes)
        if rsi > 70:
            score += 25
            if rsi > 80:
                score += 15
            if rsi > 85:
                score += 10
            reasons.append("RSI=" + str(round(rsi, 0)))

        # R2: Morning peak (local high in 9:30-10:30)
        is_morning = 9*3600+30 <= time_sec <= 10*3600+30
        if is_morning and len(bars_so_far) >= 5:
            recent_highs = highs[-5:]
            if highs[-1] == max(recent_highs):
                score += 30
                reasons.append("MorningPeak")

        # R3: VWAP premium
        cum_amt = sum(b.amount for b in bars_so_far)
        cum_vol = sum(b.volume for b in bars_so_far)
        vwap = cum_amt / cum_vol if cum_vol > 0 else current_price
        if vwap > 0:
            premium = (current_price - vwap) / vwap * 100
            if premium > 0.5:
                score += min(25, premium * 15)
                reasons.append("VWAP+" + str(round(premium, 1)) + "%")

        # R4: Volume shrinking at high
        if len(vols) >= 8:
            avg_v = sum(vols[-8:-1]) / 7
            if vols[-1] < avg_v * 0.7 and highs[-1] == max(highs[-4:]):
                score += 20
                reasons.append("VolShrink")

        # R5: Gap up fail
        if prev_close and len(bars_so_far) > 0:
            gap = (bars_so_far[0].open / prev_close - 1) * 100
            if gap > 1.5 and current_price < bars_so_far[0].open * 1.005:
                score += 25
                reasons.append("GapUpFail")

        return {
            "sell_score": min(100, score),
            "reasons": reasons,
        }


class BacktestV5:
    def __init__(self, code, stop_loss=0.5, profit_take=0.8, flee_stop=1.0,
                 entry_threshold=50, time_stop=40, require_high_pct=0.3,
                 allow_t2=True, allow_t6=False, min_hold_min=5,
                 max_trades_per_day=1):
        self.code = code
        self.cfg = STOCK_CONFIGS[code]
        self.stop_loss = stop_loss
        self.profit_take = profit_take
        self.flee_stop = flee_stop
        self.entry_threshold = entry_threshold
        self.time_stop = time_stop
        self.require_high_pct = require_high_pct
        self.allow_t2 = allow_t2
        self.allow_t6 = allow_t6
        self.min_hold_min = min_hold_min
        self.max_trades_per_day = max_trades_per_day
        self.signal = SimpleSignal(code)
        self.regime_clf = RegimeClassifier(code)
        self.slippage = BACKTEST["slippage"]

    def run(self, all_min5, all_daily):
        days_5min = defaultdict(list)
        for bar in all_min5:
            days_5min[bar.date].append(bar)
        daily_index = {b.date: b for b in all_daily}
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
            prev_close = daily_index[sorted_dates[idx-1]].close if idx > 0 else None
            day_result = self._backtest_day(date, min5, day_bar, prev_close, all_daily)
            all_results.append(day_result)
            all_trades.extend(day_result.trades)

        return self._summarize(all_results, all_trades)

    def _backtest_day(self, date, min5, day_bar, prev_close, all_daily):
        result = DayResult(
            date=date, open=day_bar.open, high=day_bar.high,
            low=day_bar.low, close=day_bar.close
        )
        slots_open = {}
        daily_trades = 0

        regime_result = self.regime_clf.classify(all_daily[-30:], min5, prev_close)
        result.regime = regime_result["regime"]

        for i in range(6, len(min5) - 1):
            bar = min5[i]
            bars_so_far = min5[:i+1]
            current_price = bar.close
            current_time = _sec_to_time(bar.time_sec)
            tw = _get_time_window(current_time)

            # === EXIT checks ===
            to_close = []
            for slot_id, slot_info in list(slots_open.items()):
                entry_price = slot_info["entry_price"]
                pnl_pct = (entry_price - current_price) / entry_price * 100
                should_close = False
                reason = ""
                hold_min = _minutes_between(slot_info["entry_time"], current_time)

                if hold_min >= self.min_hold_min:
                    if pnl_pct >= self.profit_take:
                        should_close = True
                        reason = "TP"
                    elif pnl_pct <= -self.stop_loss:
                        should_close = True
                        reason = "SL"
                    elif pnl_pct <= -self.flee_stop:
                        should_close = True
                        reason = "FL"
                    elif hold_min >= self.time_stop and pnl_pct < self.profit_take:
                        should_close = True
                        reason = "TIME"

                if current_time >= "14:50":
                    should_close = True
                    reason = "CLOSE"

                if should_close:
                    exit_price = current_price * (1 + self.slippage)
                    profit_pct = (entry_price - exit_price) / entry_price * 100
                    to_close.append((slot_id, profit_pct, reason, exit_price, current_time, tw))

            for slot_id, profit_pct, reason, exit_price, exit_time, exit_tw in to_close:
                slot_info = slots_open[slot_id]
                result.trades.append(TradeRecord(
                    day=date, slot_id=slot_id,
                    entry_time=slot_info["entry_time"], exit_time=exit_time,
                    entry_price=slot_info["entry_price"], exit_price=exit_price,
                    profit_pct=profit_pct, direction="short",
                    entry_score=slot_info.get("entry_score", 0),
                    factor_scores={},
                    regime=result.regime, time_window=exit_tw,
                    success=profit_pct > 0,
                ))
                del slots_open[slot_id]

            # === ENTRY checks ===
            if daily_trades < self.max_trades_per_day and len(slots_open) == 0:
                # Only enter during T2
                if tw != "T2" or not self.allow_t2:
                    pass
                elif result.regime in ("EXTREME", "TREND_UP"):
                    pass
                else:
                    sig = self.signal.evaluate(bars_so_far, prev_close, result.regime)
                    if sig["sell_score"] >= self.entry_threshold:
                        # Price must have fallen from day's high
                        day_high = max(b.high for b in bars_so_far)
                        pct_from_high = (day_high / current_price - 1) * 100
                        if pct_from_high >= self.require_high_pct:
                            entry_price = current_price * (1 - self.slippage)
                            slots_open[1] = {
                                "entry_price": entry_price,
                                "entry_time": current_time,
                                "entry_score": sig["sell_score"],
                                "reasons": sig["reasons"],
                            }
                            daily_trades += 1
                            result.signals_generated += 1

        # End of day force close
        for slot_id, slot_info in list(slots_open.items()):
            last_bar = min5[-1]
            exit_price = last_bar.close * (1 + self.slippage)
            entry_price = slot_info["entry_price"]
            profit_pct = (entry_price - exit_price) / entry_price * 100
            result.trades.append(TradeRecord(
                day=date, slot_id=slot_id,
                entry_time=slot_info["entry_time"],
                exit_time=_sec_to_time(last_bar.time_sec),
                entry_price=entry_price, exit_price=exit_price,
                profit_pct=profit_pct, direction="short",
                entry_score=slot_info.get("entry_score", 0),
                factor_scores={},
                regime=result.regime, time_window="T8",
                success=profit_pct > 0,
            ))

        result.pnl = sum(t.profit_pct for t in result.trades)
        return result

    def _summarize(self, days, trades):
        total_days = len(days)
        total_trades = len(trades)
        wins = [t for t in trades if t.success]
        losses = [t for t in trades if not t.success]
        win_rate = len(wins)/total_trades*100 if total_trades > 0 else 0
        avg_win = sum(t.profit_pct for t in wins)/len(wins) if wins else 0
        avg_loss = sum(t.profit_pct for t in losses)/len(losses) if losses else 0
        total_pnl = sum(t.profit_pct for t in trades)
        total_win_pnl = sum(t.profit_pct for t in wins)
        total_loss_pnl = abs(sum(t.profit_pct for t in losses)) if losses else 0
        pf = total_win_pnl/total_loss_pnl if total_loss_pnl > 0 else 999

        rs = defaultdict(list)
        for t in trades:
            rs[t.regime].append(t)
        ws = defaultdict(list)
        for t in trades:
            ws[t.time_window].append(t)
        dp = [(d.date, d.pnl) for d in days if d.trades]
        pos = sum(1 for _, p in dp if p > 0)

        regime_summary = {}
        for regime, reg_trades in rs.items():
            r_wins = [t for t in reg_trades if t.success]
            r_pnl = sum(t.profit_pct for t in reg_trades)
            regime_summary[regime] = {
                "count": len(reg_trades),
                "win_rate": round(len(r_wins)/len(reg_trades)*100, 1) if reg_trades else 0,
                "total_pnl": round(r_pnl, 2),
            }

        window_summary = {}
        for tw, tw_trades in sorted(ws.items()):
            w_wins = [t for t in tw_trades if t.success]
            w_pnl = sum(t.profit_pct for t in tw_trades)
            window_summary[tw] = {
                "count": len(tw_trades),
                "win_rate": round(len(w_wins)/len(tw_trades)*100, 1) if tw_trades else 0,
                "total_pnl": round(w_pnl, 2),
            }

        best_trades = sorted(trades, key=lambda t: -t.profit_pct)[:5]
        worst_trades = sorted(trades, key=lambda t: t.profit_pct)[:5]

        return {
            "code": self.code,
            "name": self.cfg.name,
            "params": {
                "sl": self.stop_loss, "pt": self.profit_take, "fs": self.flee_stop,
                "th": self.entry_threshold, "ts": self.time_stop,
                "rh": self.require_high_pct,
                "t2": self.allow_t2, "t6": self.allow_t6,
                "mh": self.min_hold_min, "max_trades": self.max_trades_per_day,
            },
            "total_days": total_days,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
            "profit_factor": round(pf, 2) if pf != 999 else "N/A",
            "total_pnl": round(total_pnl, 2),
            "daily_avg_pnl": round(total_pnl/total_days, 4) if total_days else 0,
            "positive_days": pos,
            "positive_days_rate": round(pos/len(dp)*100, 1) if dp else 0,
            "regime_summary": regime_summary,
            "window_summary": window_summary,
            "best_trades": [
                {"day": t.day, "entry": t.entry_time, "pnl": round(t.profit_pct, 3), "regime": t.regime}
                for t in best_trades
            ],
            "worst_trades": [
                {"day": t.day, "entry": t.entry_time, "pnl": round(t.profit_pct, 3), "regime": t.regime}
                for t in worst_trades
            ],
        }


def load_min5(code):
    path = "F:\\tongdaxin\\vipdoc\\sz\\fzline\\sz" + code + ".lc5"
    raw = read_minute_kline(path)
    return [KBar(
        date=b.date, time_sec=b.time_sec,
        open=b.open, high=b.high, low=b.low, close=b.close,
        amount=b.amount, volume=b.volume,
    ) for b in raw]


if __name__ == "__main__":
    print("=" * 70)
    print("V5 Simple Rule Backtest - High threshold + Wide profit targets")
    print("=" * 70)

    json_path = "F:\\aidanao\\data\\kl_300418_1y.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    daily_bars = [KBar(
        date=item["date"], time_sec=0,
        open=float(item["open"]), high=float(item["high"]),
        low=float(item["low"]), close=float(item["close"]),
        amount=float(item["amount"]), volume=float(item["volume"]),
    ) for item in data]
    print("daily_bars: " + str(len(daily_bars)))

    best_results = {}

    # Focused parameter grid
    param_grid = []

    # Strategy: Very selective entries + wide take-profit
    for sl in [0.3, 0.5, 0.8]:
        for pt in [0.6, 0.8, 1.0, 1.2, 1.5]:
            for fs in [0.8, 1.0, 1.2]:
                if fs <= sl:
                    continue
                for th in [40, 50, 60]:
                    for ts in [30, 40, 50]:
                        for rh in [0.3, 0.5, 0.8]:
                            param_grid.append({
                                "stop_loss": sl,
                                "profit_take": pt,
                                "flee_stop": fs,
                                "entry_threshold": th,
                                "time_stop": ts,
                                "require_high_pct": rh,
                                "allow_t2": True,
                                "allow_t6": False,
                                "min_hold_min": 5,
                                "max_trades_per_day": 1,
                            })

    # Strategy: T2 + T6 combined
    for sl in [0.5, 0.8]:
        for pt in [0.8, 1.0, 1.2]:
            for fs in [1.0, 1.2]:
                if fs <= sl:
                    continue
                for th in [50, 60]:
                    for ts in [40, 50]:
                        for allow_t2 in [True, False]:
                            for allow_t6 in [True, False]:
                                if not allow_t2 and not allow_t6:
                                    continue
                                param_grid.append({
                                    "stop_loss": sl,
                                    "profit_take": pt,
                                    "flee_stop": fs,
                                    "entry_threshold": th,
                                    "time_stop": ts,
                                    "require_high_pct": 0.5,
                                    "allow_t2": allow_t2,
                                    "allow_t6": allow_t6,
                                    "min_hold_min": 5,
                                    "max_trades_per_day": 2,
                                })

    print("param combinations: " + str(len(param_grid)))

    for code in ["300418", "300058"]:
        cfg = STOCK_CONFIGS[code]
        print("")
        print(">>> " + cfg.name + "(" + code + ")")
        min5 = load_min5(code)
        min5_dates = sorted(set(b.date for b in min5))
        daily_map = {b.date: b for b in daily_bars}
        my_daily = [daily_map[d] for d in min5_dates if d in daily_map]
        print("    min5: " + str(len(min5)) + " daily: " + str(len(my_daily)))

        best = None
        best_score = -9999
        scanned = 0

        for params in param_grid:
            bt = BacktestV5(code, **params)
            r = bt.run(min5, my_daily)
            scanned += 1

            pf_val = float(r["profit_factor"]) if r["profit_factor"] != "N/A" else 0
            pnl_val = r["total_pnl"]

            # Multi-objective: pf most important, then pnl, then win rate
            score = pf_val * 20 + pnl_val * 2.0 + r["win_rate"] * 0.1

            if score > best_score:
                best = r
                best_score = score

            if scanned % 200 == 0:
                print("    scanned: " + str(scanned) + "/" + str(len(param_grid)))

        best_results[code] = best
        p = best["params"]
        print("")
        print("    BEST PARAMS:")
        print("    sl=" + str(p["sl"]) + "% pt=" + str(p["pt"]) + "% fs=" + str(p["fs"]) + "%")
        print("    th=" + str(p["th"]) + " ts=" + str(p["ts"]) + "min rh=" + str(p["rh"]) + "%")
        print("    t2=" + str(p["t2"]) + " t6=" + str(p["t6"]) + " max_trades=" + str(p["max_trades"]))
        print("")
        print("    RESULT:")
        print("    win_rate=" + str(best["win_rate"]) + "%")
        print("    avg_win=" + str(best["avg_win"]) + "% avg_loss=" + str(best["avg_loss"]) + "%")
        print("    profit_factor=" + str(best["profit_factor"]))
        print("    total_pnl=" + str(best["total_pnl"]) + "%")
        print("    daily_avg_pnl=" + str(best["daily_avg_pnl"]) + "%")
        if best["avg_loss"] != 0:
            ratio = round(abs(best["avg_win"]/best["avg_loss"]), 2)
            print("    win/loss ratio=" + str(ratio))
        print("    pos_days=" + str(best["positive_days"]) + "/" + str(best["total_days"]) + " (" + str(best["positive_days_rate"]) + "%)")
        print("    total_trades=" + str(best["total_trades"]))
        print("")
        print("    BY WINDOW:")
        for tw in ["T1","T2","T3","T4","T5","T6","T7","T8"]:
            if tw in best.get("window_summary", {}):
                s = best["window_summary"][tw]
                print("      " + tw + ": " + str(s["count"]) + " trades win=" + str(s["win_rate"]) + "% pnl=" + str(s["total_pnl"]) + "%")
        print("    BEST TRADES:")
        for t in best["best_trades"]:
            print("      " + t["day"] + " " + t["entry"] + " pnl=" + str(t["pnl"]) + "%")
        print("    WORST TRADES:")
        for t in best["worst_trades"]:
            print("      " + t["day"] + " " + t["entry"] + " pnl=" + str(t["pnl"]) + "%")

        out = "F:/aidanao/daytrade_system/output/backtest_v5_" + code + ".json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(best, f, ensure_ascii=False, indent=2)
        print("    saved: " + out)

    print("")
    print("=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    for code, r in best_results.items():
        name = STOCK_CONFIGS[code].name
        pf_val = float(r["profit_factor"]) if r["profit_factor"] != "N/A" else 0
        passed_pf = pf_val >= 1.0
        passed_pnl = r["total_pnl"] > 0
        ratio = "N/A"
        if r["avg_loss"] != 0:
            ratio = str(round(abs(r["avg_win"]/r["avg_loss"]), 2))
        p = r["params"]
        status = "PASS" if (passed_pf and passed_pnl) else ("PARTIAL" if (passed_pf or passed_pnl) else "FAIL")
        print("")
        print(name + "(" + code + "):")
        print("  win=" + str(r["win_rate"]) + "% pf=" + str(r["profit_factor"]) + " pnl=" + str(r["total_pnl"]) + "% ratio=" + ratio)
        print("  [" + status + "]")
        print("  params: sl=" + str(p["sl"]) + "% pt=" + str(p["pt"]) + "% fs=" + str(p["fs"]) + "%")
        print("  entry=" + str(p["th"]) + " time=" + str(p["ts"]) + "min rh=" + str(p["rh"]) + "%")
        print("  t2=" + str(p["t2"]) + " t6=" + str(p["t6"]) + " max_trades=" + str(p["max_trades"]))
        print("  avg_win=" + str(r["avg_win"]) + "% avg_loss=" + str(r["avg_loss"]) + "%")

    print("")
    print("done")
