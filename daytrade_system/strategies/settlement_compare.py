"""
对比 FIFO vs 风险优先法 结算顺序对收益的影响
策略: 3笔分层倒T（统一信号，只改变平仓顺序）
避免过拟合: 信号条件不变，只比较结算顺序的差异
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


def backtest_3slot(code, name, settle_mode="risk_first"):
    """
    settle_mode: "fifo" = 先进先出, "risk_first" = 最大亏损优先
    信号条件完全一致，只在多笔同时可接回时改变平仓顺序
    """
    stock = load_stock(code)
    min5_groups = stock["min5_groups"]
    daily_map = {b.date: b for b in stock["daily"]}
    all_dates = sorted(min5_groups.keys())

    all_trades = []
    daily_pnl = []

    for date in all_dates:
        bars_5m = min5_groups[date]
        day_bar = daily_map.get(date)
        if not day_bar or len(bars_5m) < 10:
            continue

        n = len(bars_5m)
        closes = [b.close for b in bars_5m]
        rsi_vals = calc_rsi(closes, 6) if n >= 7 else [None] * n

        slots = [None, None, None]  # 3笔
        cooldown = 0
        day_trades = []

        for idx in range(5, n):
            bar = bars_5m[idx]
            price = bar.close

            # === 接回检查 ===
            ready_to_buy = []
            for s in range(3):
                sl = slots[s]
                if sl is not None and price <= sl["sell_price"]:
                    ready_to_buy.append(s)

            if ready_to_buy:
                if settle_mode == "fifo":
                    # FIFO: 按 sell_idx（时间顺序）排序，最早的先接
                    ready_to_buy.sort(key=lambda s: slots[s]["sell_idx"])
                else:
                    # 风险优先: 按 sell_price（价格）排序，卖得最贵的（亏损最大的）先接
                    ready_to_buy.sort(key=lambda s: slots[s]["sell_price"], reverse=True)

                # 只接回一笔
                s = ready_to_buy[0]
                sl = slots[s]
                profit = (sl["sell_price"] / price - 1) * 100
                day_trades.append({
                    "slot": s + 1,
                    "sell_price": sl["sell_price"],
                    "buy_price": price,
                    "profit_pct": round(profit, 2),
                    "settle": settle_mode,
                })
                slots[s] = None

            # === 卖出信号 ===
            if cooldown > 0:
                cooldown -= 1
                continue

            empty = [s for s in range(3) if slots[s] is None]
            if empty:
                window = bars_5m[:idx + 1]
                vwap = calc_vwap_bands(window)
                vwap_val = vwap["vwap"]
                if vwap_val == 0:
                    continue

                deviation = (price / vwap_val - 1) * 100
                rsi_now = rsi_vals[idx] if idx < len(rsi_vals) else None
                day_low_sofar = min(b.low for b in bars_5m[:idx + 1])
                pct_from_low = (price / day_low_sofar - 1) * 100

                score = 0
                if deviation > 0.5: score += 1
                if deviation > 1.0: score += 1
                if rsi_now is not None and rsi_now > 50: score += 1
                if pct_from_low > 1.5: score += 1
                if bar.time_sec >= 52200: score = 0

                if score >= 2:
                    s = empty[0]
                    slots[s] = {"sell_price": price, "sell_time": bar.time_str, "sell_idx": idx}

        # === 收盘强平 ===
        last_price = bars_5m[-1].close
        for s in range(3):
            sl = slots[s]
            if sl is not None:
                profit = (sl["sell_price"] / last_price - 1) * 100
                day_trades.append({
                    "slot": s + 1,
                    "sell_price": sl["sell_price"],
                    "buy_price": last_price,
                    "profit_pct": round(profit, 2),
                    "settle": "forced",
                })

        if day_trades:
            all_trades.extend(day_trades)
        daily_pnl.append({
            "date": date,
            "trades": len(day_trades),
            "profit": round(sum(t["profit_pct"] for t in day_trades), 2),
        })

    # === 统计 ===
    normal_trades = [t for t in all_trades if t["settle"] != "forced"]
    forced = sum(1 for t in all_trades if t["settle"] == "forced")
    total = len(all_trades)
    wins = sum(1 for t in all_trades if t["profit_pct"] > 0)

    if wins == 0 or total == wins:
        avg_win = 0
        avg_loss = 0
    else:
        avg_win = sum(t["profit_pct"] for t in all_trades if t["profit_pct"] > 0) / wins
        avg_loss = sum(t["profit_pct"] for t in all_trades if t["profit_pct"] <= 0) / (total - wins)

    # 普通交易（非强平）的统计
    if normal_trades:
        n_wins = sum(1 for t in normal_trades if t["profit_pct"] > 0)
        n_avg_win = sum(t["profit_pct"] for t in normal_trades if t["profit_pct"] > 0) / n_wins if n_wins > 0 else 0
        n_avg = sum(t["profit_pct"] for t in normal_trades) / len(normal_trades)
    else:
        n_wins = n_avg_win = n_avg = 0

    return {
        "name": name, "code": code, "mode": settle_mode,
        "total_trades": total,
        "normal_trades": len(normal_trades),
        "forced": forced,
        "win_rate": round(wins / total * 100, 2),
        "avg_win": round(avg_win, 3),
        "avg_loss": round(avg_loss, 3),
        "n_win_rate": round(n_wins / len(normal_trades) * 100, 2) if normal_trades else 0,
        "n_avg_profit": round(n_avg, 3),
        "total_pnl": round(sum(t["profit_pct"] for t in all_trades), 2),
        "daily_results": daily_pnl,
    }


if __name__ == "__main__":
    for code in ["300418", "300058"]:
        name = "昆仑万维" if code == "300418" else "蓝色光标"
        r_fifo = backtest_3slot(code, name, "fifo")
        r_risk = backtest_3slot(code, name, "risk_first")

        print(f"\n{'='*60}")
        print(f"  {name}({code}) — 3笔倒T 结算顺序对比")
        print(f"{'='*60}")
        print(f"{'':<15} {'FIFO(先进先出)':>20} {'风险优先':>20}")
        print(f"{'总交易笔数':<15} {r_fifo['total_trades']:>20} {r_risk['total_trades']:>20}")
        print(f"{'普通交易(非强平)':<15} {r_fifo['normal_trades']:>20} {r_risk['normal_trades']:>20}")
        print(f"{'强平笔数':<15} {r_fifo['forced']:>20} {r_risk['forced']:>20}")
        print(f"{'总胜率':<15} {r_fifo['win_rate']:>19}% {r_risk['win_rate']:>19}%")
        print(f"{'普通交易胜率':<15} {r_fifo['n_win_rate']:>19}% {r_risk['n_win_rate']:>19}%")
        print(f"{'平均盈利':<15} {r_fifo['avg_win']:>20}% {r_risk['avg_win']:>20}%")
        print(f"{'平均亏损':<15} {r_fifo['avg_loss']:>20}% {r_risk['avg_loss']:>20}%")
        print(f"{'普通交易均收益':<15} {r_fifo['n_avg_profit']:>20}% {r_risk['n_avg_profit']:>20}%")
        print(f"{'累计总盈亏':<15} {r_fifo['total_pnl']:>20}% {r_risk['total_pnl']:>20}%")

        # 盈亏分布
        for label in ["<-2%", "-2%~0", "0~2%", "2~5%", ">5%"]:
            pass  # skip for brevity
