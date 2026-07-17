"""
2笔倒T限仓策略回测
规则: 每天最多2笔倒T, 卖出价严格记录, 只在该价位或以下接回
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collections import defaultdict
from engine.tdx_parser import read_minute_kline, read_daily_kline, group_by_date, TDXBar
from engine.indicators import calc_vwap_bands, calc_rsi
from engine.indicators import KBar

TDX_BASE = r"F:\tongdaxin\vipdoc\sz"


def load_stock(code):
    min5_path = f"{TDX_BASE}/fzline/sz{code}.lc5"
    day_path = f"{TDX_BASE}/lday/sz{code}.day"
    min5_raw = read_minute_kline(min5_path)
    daily_raw = read_daily_kline(day_path)
    min5_groups = group_by_date(min5_raw)
    return {
        "daily": daily_raw,
        "min5_groups": min5_groups,
    }


def backtest_2slot_reverse(code, name):
    """2槽位倒T策略回测"""
    stock = load_stock(code)
    min5_groups = stock["min5_groups"]
    daily_map = {b.date: b for b in stock["daily"]}
    all_dates = sorted(min5_groups.keys())

    all_trades = []
    daily_results = []

    for i, date in enumerate(all_dates):
        bars_5m = min5_groups[date]
        day_bar = daily_map.get(date)
        if not day_bar or len(bars_5m) < 10:
            continue

        n = len(bars_5m)
        closes = [b.close for b in bars_5m]
        rsi_vals = calc_rsi(closes, 6) if n >= 7 else [None] * n

        # 2个槽位: (sell_price, sell_time, sell_idx)
        slots = [None, None]
        day_trades = []

        for idx in range(5, n):  # 从第5根K(9:50)开始
            bar = bars_5m[idx]
            price = bar.close

            # === 先检查是否有可以接回的槽位 ===
            # (先接回再考虑新卖出, 因为资金解冻后才能再卖 - 不过T+1框架下这无所谓)
            for s in range(2):
                if slots[s] is not None:
                    sell_price = slots[s][0]
                    if price <= sell_price:
                        # 接回!
                        profit = (sell_price / price - 1) * 100
                        day_trades.append({
                            "day": date,
                            "type": "倒T",
                            "slot": s + 1,
                            "sell_time": slots[s][1],
                            "sell_price": round(sell_price, 2),
                            "buy_time": bar.time_str,
                            "buy_price": round(price, 2),
                            "profit_pct": round(profit, 2),
                            "profit_yuan": round(sell_price - price, 2),
                        })
                        slots[s] = None  # 槽位释放

            # === 找新卖出机会（只当有空槽位） ===
            empty_slots = [s for s in range(2) if slots[s] is None]
            if empty_slots:
                # 卖出条件: 价格相对健康地偏高
                window = bars_5m[:idx+1]
                vwap = calc_vwap_bands(window)
                vwap_val = vwap["vwap"]
                if vwap_val == 0:
                    continue

                deviation = (price / vwap_val - 1) * 100
                rsi_now = rsi_vals[idx] if idx < len(rsi_vals) else None
                day_low_sofar = min(b.low for b in bars_5m[:idx+1])
                pct_from_low = (price / day_low_sofar - 1) * 100

                # 卖出信号打分
                sell_score = 0
                reasons = []

                # 价格高于VWAP
                if deviation > 0.5:
                    sell_score += 1
                    reasons.append(f"VWAP+{deviation:.1f}%")
                if deviation > 1.0:
                    sell_score += 1  # 更高偏离更值得卖

                # RSI不太低（不是底部）
                if rsi_now is not None and rsi_now > 50:
                    sell_score += 1
                    reasons.append(f"RSI={rsi_now:.0f}")

                # 价格已经涨了一定幅度（离日内低点）
                if pct_from_low > 1.5:
                    sell_score += 1
                    reasons.append(f"距低+{pct_from_low:.1f}%")

                # 尾盘不卖（14:30后不新开仓）
                if bar.time_sec >= 52200:  # 14:30
                    sell_score = 0

                if sell_score >= 2:
                    s = empty_slots[0]
                    slots[s] = (price, bar.time_str, idx)

        # === 收盘前强制接回所有未平仓 ===
        last_bar = bars_5m[-1]
        last_price = last_bar.close
        for s in range(2):
            if slots[s] is not None:
                sell_price = slots[s][0]
                profit = (sell_price / last_price - 1) * 100
                day_trades.append({
                    "day": date,
                    "type": "倒T(强平)",
                    "slot": s + 1,
                    "sell_time": slots[s][1],
                    "sell_price": round(sell_price, 2),
                    "buy_time": last_bar.time_str,
                    "buy_price": round(last_price, 2),
                    "profit_pct": round(profit, 2),
                    "profit_yuan": round(sell_price - last_price, 2),
                })

        if day_trades:
            all_trades.extend(day_trades)

        # 日统计
        total_profit = sum(t["profit_pct"] for t in day_trades)
        wins = sum(1 for t in day_trades if t["profit_pct"] > 0)
        daily_results.append({
            "date": date,
            "open": day_bar.open,
            "high": day_bar.high,
            "low": day_bar.low,
            "close": day_bar.close,
            "trades": len(day_trades),
            "wins": wins,
            "profit": round(total_profit, 2),
            "open_slots": sum(1 for s in slots if s is not None),
        })

    # === 汇总统计 ===
    if not all_trades:
        return {"total_trades": 0}

    total = len(all_trades)
    wins = sum(1 for t in all_trades if t["profit_pct"] > 0)
    forced = sum(1 for t in all_trades if "强平" in t["type"])
    win_rate = wins / total * 100
    avg_win = sum(t["profit_pct"] for t in all_trades if t["profit_pct"] > 0) / wins if wins > 0 else 0
    avg_loss = sum(t["profit_pct"] for t in all_trades if t["profit_pct"] <= 0) / (total - wins) if total > wins else 0

    # 盈利日占比
    prof_days = sum(1 for d in daily_results if d["profit"] > 0)
    avg_daily_profit = sum(d["profit"] for d in daily_results) / len(daily_results)

    # 按盈亏分组
    profit_buckets = {"<-2%": 0, "-2%~0": 0, "0~2%": 0, "2~5%": 0, ">5%": 0}
    for t in all_trades:
        p = t["profit_pct"]
        if p < -2: profit_buckets["<-2%"] += 1
        elif p < 0: profit_buckets["-2%~0"] += 1
        elif p < 2: profit_buckets["0~2%"] += 1
        elif p < 5: profit_buckets["2~5%"] += 1
        else: profit_buckets[">5%"] += 1

    return {
        "name": name,
        "code": code,
        "total_days": len(daily_results),
        "total_trades": total,
        "win_rate": round(win_rate, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(abs(avg_win / avg_loss) if avg_loss != 0 else 999, 2),
        "forced_close": forced,
        "forced_pct": round(forced / total * 100, 1),
        "profitable_days": prof_days,
        "day_win_rate": round(prof_days / len(daily_results) * 100, 1),
        "avg_daily_profit": round(avg_daily_profit, 2),
        "profit_distribution": profit_buckets,
        "daily_results": daily_results,
        "all_trades": all_trades,
    }


def print_report(r):
    print(f"\n{'='*60}")
    print(f"  {r['name']}({r['code']}) — 2笔倒T限仓策略")
    print(f"{'='*60}")
    print(f"回测天数: {r['total_days']} | 总交易: {r['total_trades']}笔")
    print(f"胜率: {r['win_rate']}% | 平均盈利: {r['avg_win']:+.2f}% | 平均亏损: {r['avg_loss']:+.2f}%")
    print(f"盈亏比: {r['profit_factor']} | 强制平仓: {r['forced_close']}笔({r['forced_pct']}%)")
    print(f"盈利日: {r['profitable_days']}/{r['total_days']}({r['day_win_rate']}%) | 日均收益: {r['avg_daily_profit']:+.2f}%")
    print(f"盈利分布: 大亏(<-2%):{r['profit_distribution']['<-2%']} | "
          f"小亏:{r['profit_distribution']['-2%~0']} | "
          f"小赚(0~2%):{r['profit_distribution']['0~2%']} | "
          f"中赚(2~5%):{r['profit_distribution']['2~5%']} | "
          f"大赚(>5%):{r['profit_distribution']['>5%']}")

    # 最近10天
    print(f"\n最近10交易日:")
    for d in r['daily_results'][-10:]:
        marker = '⚠️' if d['profit'] < 0 else '✅' if d['profit'] > 1 else '·'
        print(f"  {marker} {d['date']} | {d['trades']}笔{d['wins']}胜 | 日收益:{d['profit']:+.2f}% | "
              f"O:{d['open']} H:{d['high']} L:{d['low']} C:{d['close']}")

    # 强平分析
    forced_trades = [t for t in r['all_trades'] if '强平' in t['type']]
    if forced_trades:
        avg_forced_loss = sum(t['profit_pct'] for t in forced_trades) / len(forced_trades)
        print(f"\n强平详情: {len(forced_trades)}笔, 平均亏损{avg_forced_loss:+.2f}%")
        worst = sorted(forced_trades, key=lambda x: x['profit_pct'])[:3]
        for t in worst:
            print(f"  {t['day']} slot{t['slot']}: 卖{t['sell_price']} 强平{t['buy_price']} ({t['profit_pct']:+.1f}%)")


if __name__ == "__main__":
    for code in ["300418", "300058"]:
        name = "昆仑万维" if code == "300418" else "蓝色光标"
        r = backtest_2slot_reverse(code, name)
        print_report(r)
