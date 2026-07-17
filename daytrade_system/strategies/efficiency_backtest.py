"""
量价效率有效性回测 — 波仔倒T系统

核心问题: 硬阻力(效率>2)做倒T的胜率是否显著高于软阻力(效率<1)?

回测规则(严格防过拟合):
  1. 每天用前5天的数据计算量价效率（无未来参数）
  2. 硬阻力组: 价格触及效率>2.0的阻力带 → 卖1笔 → 追踪接回
  3. 软阻力组: 价格触及效率<1.0的阻力带 → 卖1笔 → 追踪接回
  4. 对比两组的胜率和均收益
  5. 不针对单日调参，只看整体差异

数据范围: 昆仑万维(300418) 近99天5分钟K
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.tdx_parser import read_minute_kline, read_daily_kline, group_by_date
from dataclasses import dataclass
from typing import List, Optional
from collections import defaultdict


TDX_FZLINE = r"F:\tongdaxin\vipdoc\sz\fzline"


def rolling_efficiency(code: str, window_days: int = 5):
    """
    按天滚动计算量价效率
    每天用前window_days的数据，无未来参数

    返回: Dict[date, {price_label: efficiency}]
    """
    fp = f"{TDX_FZLINE}/sz{code}.lc5"
    all_bars = read_minute_kline(fp)
    groups = group_by_date(all_bars)
    dates = sorted(groups.keys())

    results = {}  # date -> {price_label: avg_efficiency}

    for i, today in enumerate(dates):
        if i < window_days:
            continue

        # 只用到昨天为止的数据
        window_dates = dates[i - window_days:i]
        window_bars = []
        for d in window_dates:
            window_bars.extend(groups[d])

        if not window_bars:
            continue

        # 确定价格范围
        all_prices = []
        for b in window_bars:
            all_prices.extend([b.open, b.close, b.high, b.low])
        price_min = min(all_prices)
        price_max = max(all_prices)
        avg_price = (price_max + price_min) / 2

        if avg_price > 100:
            step = 2.0
        elif avg_price > 30:
            step = 0.5
        elif avg_price > 10:
            step = 0.1
        else:
            step = 0.05

        # 分桶统计
        bucket_floor = int(price_min / step) * step
        num_buckets = int((price_max - bucket_floor) / step) + 2
        buckets = {}

        for b in window_bars:
            mid = (b.open + b.close) / 2
            bucket = round(int(mid / step) * step, 2)
            if bucket not in buckets:
                buckets[bucket] = {"vol": 0, "amt": 0.0, "movement": 0.0, "n": 0}
            buckets[bucket]["vol"] += b.volume
            buckets[bucket]["amt"] += b.amount
            buckets[bucket]["n"] += 1
            price_impact = (b.high - b.low) / 4 if b.high > b.low else step * 0.1
            buckets[bucket]["movement"] += price_impact

        total_vol = sum(v["vol"] for v in buckets.values())
        total_movement = sum(v["movement"] for v in buckets.values())

        if total_vol == 0 or total_movement == 0:
            continue

        # 计算效率
        efficiency_map = {}
        for price, data in buckets.items():
            if data["vol"] == 0 or data["n"] == 0:
                continue
            vol_share = data["vol"] / total_vol * 100
            mov_share = data["movement"] / total_movement * 100
            eff = round(vol_share / mov_share, 1) if mov_share > 0.001 else 9.9
            efficiency_map[price] = eff

        results[today] = efficiency_map

    return results


@dataclass
class TradeRecord:
    """一笔倒T交易记录"""
    date: str
    sell_price: float
    sell_time: str
    efficiency: float
    group: str           # "hard" or "soft"
    buy_price: float = 0
    buy_time: str = ""
    profit_pct: float = 0
    settled: bool = False
    days_held: int = 0


def backtest_efficiency(code: str, window_days: int = 5, max_hold_days: int = 3):
    """
    回测量价效率的倒T有效性

    硬阻力组: 效率 > 2.0
    软阻力组: 效率 < 1.0

    每卖出一笔后，追踪到接回或到达hold天数上限
    """
    fp = f"{TDX_FZLINE}/sz{code}.lc5"
    all_bars = read_minute_kline(fp)
    groups = group_by_date(all_bars)
    dates = sorted(groups.keys())

    # 计算每日的滚动效率
    eff_map = rolling_efficiency(code, window_days)

    hard_trades = []
    soft_trades = []
    pending = []  # 待接回的仓位

    for today_idx, today in enumerate(dates):
        if today not in eff_map:
            continue

        bars_5m = groups[today]
        if len(bars_5m) < 10:
            continue

        efficiency_today = eff_map[today]
        if not efficiency_today:
            continue

        # === 检查待接回仓位 ===
        to_remove = []
        for trade in pending:
            # 遍历当天每根K线
            bought = False
            for bar in bars_5m:
                if bar.close <= trade.sell_price:
                    trade.buy_price = bar.close
                    trade.buy_time = bar.time_str
                    trade.profit_pct = round((trade.sell_price / bar.close - 1) * 100, 2)
                    trade.settled = True
                    trade.days_held = today_idx - dates.index(trade.date)
                    bought = True
                    break
            if bought or today_idx - dates.index(trade.date) >= max_hold_days:
                to_remove.append(trade)

        for t in to_remove:
            pending.remove(t)
            if t.settled:
                if t.group == "hard":
                    hard_trades.append(t)
                else:
                    soft_trades.append(t)

        # === 当天入场：价格触及硬/软阻力 → 卖出 ===
        day_high = max(b.high for b in bars_5m)

        for price, eff in sorted(efficiency_today.items()):
            if price <= day_high and price > bars_5m[0].open * 0.95:  # 价格必须当天触及且合理
                is_hard = eff >= 2.0
                is_soft = eff < 1.0

                if not is_hard and not is_soft:
                    continue

                # 找首次触及该价位的时间
                for bar in bars_5m[1:]:  # 跳过开盘第一根
                    if bar.high >= price:
                        trade = TradeRecord(
                            date=today,
                            sell_price=bar.close if bar.close > price else price,
                            sell_time=bar.time_str,
                            efficiency=eff,
                            group="hard" if is_hard else "soft",
                        )
                        pending.append(trade)
                        break

                if is_hard:
                    break  # 每天最多一笔硬阻力卖出
                elif is_soft and not any(t.date == today and t.group == "hard" for t in pending):
                    break  # 软阻力也限一笔，且不能与硬阻力同日

    # 统计
    def stats(trades: List[TradeRecord], label: str) -> dict:
        settled = [t for t in trades if t.settled]
        if not settled:
            return {"label": label, "count": 0, "win_rate": 0, "avg_profit": 0,
                    "avg_days": 0, "settled": 0, "unsettled": len(trades)}

        wins = [t for t in settled if t.profit_pct > 0]
        wr = len(wins) / len(settled) * 100
        avg = sum(t.profit_pct for t in settled) / len(settled)
        avg_d = sum(t.days_held for t in settled) / len(settled)

        return {
            "label": label,
            "count": len(trades),
            "settled": len(settled),
            "unsettled": len(trades) - len(settled),
            "win_rate": round(wr, 1),
            "avg_profit": round(avg, 2),
            "avg_days": round(avg_d, 1),
        }

    return stats(hard_trades, "硬阻力(效率>2)"), stats(soft_trades, "软阻力(效率<1)"), hard_trades, soft_trades


def efficiency_backtest_report(code: str = "300418") -> str:
    """生成可读的回测报告"""
    print(f"\n{'='*55}")
    print(f"  量价效率有效性回测 — {code}")
    print(f"  近99天, 5天滚动窗口, 无未来参数")
    print(f"{'='*55}")

    hard_stats, soft_stats, hard_trades, soft_trades = backtest_efficiency(code)

    print(f"\n  {'指标':<15} {'硬阻力(效率>2)':>18} {'软阻力(效率<1)':>18}")
    print(f"  {'-'*51}")
    for key in ["count", "settled", "unsettled", "win_rate", "avg_profit", "avg_days"]:
        h_val = hard_stats[key]
        s_val = soft_stats[key]
        fmt = f"{h_val:.1f}%" if "rate" in key else f"{h_val:.2f}%" if "profit" in key else str(h_val)
        fmt_s = f"{s_val:.1f}%" if "rate" in key else f"{s_val:.2f}%" if "profit" in key else str(s_val)
        label_cn = {"count": "总交易", "settled": "已结算", "unsettled": "未结算",
                    "win_rate": "胜率", "avg_profit": "平均利润", "avg_days": "均持有天"}
        print(f"  {label_cn[key]:<15} {fmt:>18} {fmt_s:>18}")

    # 胜率差
    wr_diff = hard_stats["win_rate"] - soft_stats["win_rate"]
    ap_diff = hard_stats["avg_profit"] - soft_stats["avg_profit"]

    print(f"\n  {'─'*51}")
    if wr_diff > 5:
        print(f"  🟢 硬阻力胜率显著优于软阻力 (+{wr_diff:.1f}%)")
    elif wr_diff > 0:
        print(f"  🟡 硬阻力略优于软阻力 (+{wr_diff:.1f}%)")
    else:
        print(f"  🔴 硬阻力未优于软阻力 ({wr_diff:.1f}%)")

    if ap_diff > 0.3:
        print(f"  🟢 硬阻力平均利润显著更高 (+{ap_diff:.2f}%)")
    elif ap_diff > 0:
        print(f"  🟡 硬阻力平均利润略高 (+{ap_diff:.2f}%)")

    print(f"  (硬阻力通常距现价远, 软阻力更近 — 这是关键取舍)")
    print(f"{'='*55}")

    # 利润分布
    if hard_trades:
        h_profits = [t.profit_pct for t in hard_trades if t.settled]
        if h_profits:
            buckets = {"<-1%": 0, "-1~0%": 0, "0~1%": 0, "1~2%": 0, ">2%": 0}
            for p in h_profits:
                if p < -1: buckets["<-1%"] += 1
                elif p < 0: buckets["-1~0%"] += 1
                elif p < 1: buckets["0~1%"] += 1
                elif p < 2: buckets["1~2%"] += 1
                else: buckets[">2%"] += 1
            total = len(h_profits)
            print(f"\n  硬阻力利润分布 ({total}笔):")
            for k, v in buckets.items():
                bar = "▓" * v + " ·" * (20 - v)
                print(f"  {k:>6}: {bar} {v}笔 ({v/total*100:.0f}%)")

    return ""


if __name__ == "__main__":
    efficiency_backtest_report("300418")
