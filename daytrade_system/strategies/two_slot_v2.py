"""
2笔倒T限仓策略 V2 — 卖飞追回机制

规则:
1. 每天最多2笔倒T，卖出价记录，价格回落到卖出价或以下接回
2. 如果卖飞(涨超卖出价3%)，不立即止损，等高位形成有效支撑后追回
3. 有效支撑: 价格从飞走后最高点回落≥1% → 然后反弹(当前价>前低) → 确认支撑追回
4. 收盘未接回则强制平仓
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.tdx_parser import read_minute_kline, read_daily_kline, group_by_date
from engine.indicators import calc_vwap_bands, calc_rsi

TDX_BASE = r"F:\tongdaxin\vipdoc\sz"


def load_stock(code):
    min5_path = f"{TDX_BASE}/fzline/sz{code}.lc5"
    day_path = f"{TDX_BASE}/lday/sz{code}.day"
    return {
        "daily": read_daily_kline(day_path),
        "min5_groups": group_by_date(read_minute_kline(min5_path)),
    }


def backtest_2slot_v2(code, name):
    stock = load_stock(code)
    min5_groups = stock["min5_groups"]
    daily_map = {b.date: b for b in stock["daily"]}
    all_dates = sorted(min5_groups.keys())

    all_trades = []
    daily_results = []

    for date in all_dates:
        bars_5m = min5_groups[date]
        day_bar = daily_map.get(date)
        if not day_bar or len(bars_5m) < 10:
            continue

        n = len(bars_5m)
        closes = [b.close for b in bars_5m]
        rsi_vals = calc_rsi(closes, 6) if n >= 7 else [None] * n

        # slot = {"sell_price": float, "sell_time": str, "sell_idx": int,
        #          "state": "active"|"flyaway", "flyaway_high": float,
        #          "flyaway_low": float, "cooldown": int}
        slots = [None, None]
        day_trades = []
        global_cooldown = 0  # 全局冷却: 追回后20分钟(4根K)不新卖

        for idx in range(5, n):
            bar = bars_5m[idx]
            price = bar.close

            # === 检查每个槽位是否该接回 ===
            for s in range(2):
                sl = slots[s]
                if sl is None:
                    continue

                sell_price = sl["sell_price"]

                if sl["state"] == "active":
                    # 检查是否卖飞了
                    if price >= sell_price * 1.03:
                        sl["state"] = "flyaway"
                        sl["flyaway_high"] = price
                        sl["flyaway_low"] = price
                        continue  # 切换到flyaway, 下一根K再判断

                    # 正常等回调
                    if price <= sell_price:
                        profit = (sell_price / price - 1) * 100
                        day_trades.append({
                            "day": date, "type": "倒T", "slot": s+1,
                            "sell_time": sl["sell_time"], "sell_price": round(sell_price, 2),
                            "buy_time": bar.time_str, "buy_price": round(price, 2),
                            "profit_pct": round(profit, 2),
                        })
                        slots[s] = None

                elif sl["state"] == "flyaway":
                    # 追踪飞走后的最高点和最低点
                    sl["flyaway_high"] = max(sl["flyaway_high"], price)
                    sl["flyaway_low"] = min(sl["flyaway_low"], price)

                    # 条件: 从最高回落≥1% 且 当前价反弹(>最近低点)
                    pullback_pct = (sl["flyaway_high"] / price - 1) * 100
                    bounced = price > sl["flyaway_low"]

                    if pullback_pct >= 1.0 and bounced:
                        # 确认支撑，追回!
                        profit = (sell_price / price - 1) * 100
                        day_trades.append({
                            "day": date, "type": "倒T(卖飞追回)", "slot": s+1,
                            "sell_time": sl["sell_time"], "sell_price": round(sell_price, 2),
                            "buy_time": bar.time_str, "buy_price": round(price, 2),
                            "profit_pct": round(profit, 2),
                            "flyaway_high": round(sl["flyaway_high"], 2),
                        })
                        slots[s] = None
                        global_cooldown = 4  # 追回后冷却4根K(20分钟)

            # === 找新卖出机会（只当有空槽位且不在冷却期） ===
            if global_cooldown > 0:
                global_cooldown -= 1
                continue
            
            empty_slots = [s for s in range(2) if slots[s] is None]
            if empty_slots:
                window = bars_5m[:idx+1]
                vwap = calc_vwap_bands(window)
                vwap_val = vwap["vwap"]
                if vwap_val == 0:
                    continue

                deviation = (price / vwap_val - 1) * 100
                rsi_now = rsi_vals[idx] if idx < len(rsi_vals) else None
                day_low_sofar = min(b.low for b in bars_5m[:idx+1])
                pct_from_low = (price / day_low_sofar - 1) * 100

                sell_score = 0
                if deviation > 0.5:
                    sell_score += 1
                if deviation > 1.0:
                    sell_score += 1
                if rsi_now is not None and rsi_now > 50:
                    sell_score += 1
                if pct_from_low > 1.5:
                    sell_score += 1
                if bar.time_sec >= 52200:  # 14:30后不卖
                    sell_score = 0

                if sell_score >= 2:
                    s = empty_slots[0]
                    slots[s] = {
                        "sell_price": price,
                        "sell_time": bar.time_str,
                        "sell_idx": idx,
                        "state": "active",
                    }

        # === 收盘强平 ===
        last_bar = bars_5m[-1]
        last_price = last_bar.close
        for s in range(2):
            sl = slots[s]
            if sl is not None:
                profit = (sl["sell_price"] / last_price - 1) * 100
                day_trades.append({
                    "day": date, "type": "倒T(强平)", "slot": s+1,
                    "sell_time": sl["sell_time"], "sell_price": round(sl["sell_price"], 2),
                    "buy_time": last_bar.time_str, "buy_price": round(last_price, 2),
                    "profit_pct": round(profit, 2),
                })

        if day_trades:
            all_trades.extend(day_trades)

        total_profit = sum(t["profit_pct"] for t in day_trades)
        wins = sum(1 for t in day_trades if t["profit_pct"] > 0)
        daily_results.append({
            "date": date,
            "trades": len(day_trades),
            "wins": wins,
            "profit": round(total_profit, 2),
        })

    # === 汇总 ===
    if not all_trades:
        return {"total_trades": 0}

    total = len(all_trades)
    wins = sum(1 for t in all_trades if t["profit_pct"] > 0)
    forced = sum(1 for t in all_trades if "强平" in t["type"])
    flyback = sum(1 for t in all_trades if "追回" in t["type"])
    win_rate = wins / total * 100
    avg_win = sum(t["profit_pct"] for t in all_trades if t["profit_pct"] > 0) / wins if wins > 0 else 0
    avg_loss = sum(t["profit_pct"] for t in all_trades if t["profit_pct"] <= 0) / (total - wins) if total > wins else 0
    prof_days = sum(1 for d in daily_results if d["profit"] > 0)
    avg_daily = sum(d["profit"] for d in daily_results) / len(daily_results)

    # 强平分析
    forced_trades = [t for t in all_trades if "强平" in t["type"]]
    avg_forced_loss = sum(t["profit_pct"] for t in forced_trades) / len(forced_trades) if forced_trades else 0

    # 卖飞追回分析
    flyback_trades = [t for t in all_trades if "追回" in t["type"]]
    avg_flyback = sum(t["profit_pct"] for t in flyback_trades) / len(flyback_trades) if flyback_trades else 0

    # 分布
    buckets = {"<-2%":0,"-2%~0":0,"0~2%":0,"2~5%":0,">5%":0}
    for t in all_trades:
        p = t["profit_pct"]
        if p < -2: buckets["<-2%"] += 1
        elif p < 0: buckets["-2%~0"] += 1
        elif p < 2: buckets["0~2%"] += 1
        elif p < 5: buckets["2~5%"] += 1
        else: buckets[">5%"] += 1

    return {
        "name": name, "code": code,
        "total_days": len(daily_results), "total_trades": total,
        "win_rate": round(win_rate,1), "avg_win": round(avg_win,2),
        "avg_loss": round(avg_loss,2),
        "profit_factor": round(abs(avg_win/avg_loss),2) if avg_loss != 0 else 999,
        "forced_close": forced, "forced_pct": round(forced/total*100,1),
        "avg_forced_loss": round(avg_forced_loss,2),
        "flyback_trades": flyback, "avg_flyback": round(avg_flyback,2),
        "profitable_days": prof_days,
        "day_win_rate": round(prof_days/len(daily_results)*100,1),
        "avg_daily_profit": round(avg_daily, 2),
        "profit_distribution": buckets,
        "daily_results": daily_results,
        "all_trades": all_trades,
    }
