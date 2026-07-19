"""
真实支撑/压力识别模块 — 基于历史成交量
不用盘口挂单（可以撤），只看成交量密集区（真金白银）

原理: 在某价位区间成交了大量的股票 → 多方/空方在此处厮杀过
      → 价格再次回到这里时，上次在此买入的人会防守（支撑）
      → 上次在此套牢的人会解套卖出（压力）
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.tdx_parser import read_minute_kline, group_by_date

TDX_FZLINE = r"F:\tongdaxin\vipdoc\sz\fzline"


def volume_profile(code: str, days: int = 5):
    """
    最近N天的成交量剖面
    返回: [(价格区间, 总成交量, 百分比), ...] 按成交量降序
    """
    fp = f"{TDX_FZLINE}/sz{code}.lc5"
    bars = read_minute_kline(fp)
    groups = group_by_date(bars)
    dates = sorted(groups.keys())
    recent_dates = dates[-days:]

    # 价格范围
    all_prices = []
    for d in recent_dates:
        for b in groups[d]:
            all_prices.extend([b.open, b.close, b.high, b.low])
    price_min = min(all_prices)
    price_max = max(all_prices)
    price_range = price_max - price_min

    # 根据股票价格选择步长
    avg_price = (price_max + price_min) / 2
    if avg_price > 100:
        step = 2.0
    elif avg_price > 30:
        step = 0.5
    elif avg_price > 10:
        step = 0.1
    else:
        step = 0.05

    # 统计每个价格区间的成交量
    bins = {}
    for d in recent_dates:
        for b in groups[d]:
            mid = (b.open + b.close) / 2
            bucket = round(mid / step) * step
            vol = max(b.volume, 0)
            bins[bucket] = bins.get(bucket, 0) + vol

    total_vol = sum(bins.values())
    if total_vol == 0:
        return []

    profile = []
    for price, vol in sorted(bins.items(), key=lambda x: -x[1]):
        pct = round(vol / total_vol * 100, 1)
        profile.append({
            "price": round(price, 2),
            "volume": vol,
            "pct": pct,
        })

    return profile


def merge_bands(profile: list, gap: float = 0):
    """
    合并相邻的成交量密集区为支撑/压力带
    gap: 相邻区间之间的步长倍数（0=直接相邻就合并）
    返回: 合并后的带列表
    """
    if not profile:
        return []

    # 先筛出显著的区间（占比>=3%）
    significant = [p for p in profile if p["pct"] >= 3]
    if not significant:
        return []

    # 按价格排序
    significant.sort(key=lambda p: p["price"])

    # 找出步长
    if len(significant) > 1:
        step = significant[1]["price"] - significant[0]["price"]
    else:
        step = 0.5

    max_gap = step * (gap + 1)
    bands = []
    current = {"price_min": significant[0]["price"], "price_max": significant[0]["price"],
               "volume": significant[0]["volume"], "pct": significant[0]["pct"]}

    for i in range(1, len(significant)):
        p = significant[i]
        if p["price"] - current["price_max"] <= max_gap:
            # 合并
            current["price_max"] = p["price"]
            current["volume"] += p["volume"]
            current["pct"] += p["pct"]
        else:
            bands.append(current)
            current = {"price_min": p["price"], "price_max": p["price"],
                       "volume": p["volume"], "pct": p["pct"]}
    bands.append(current)

    # 格式化输出
    for b in bands:
        if b["price_min"] == b["price_max"]:
            b["label"] = f"{b['price_min']:.2f}"
        else:
            b["label"] = f"{b['price_min']:.2f}~{b['price_max']:.2f}"
        b["pct"] = round(b["pct"], 1)

    return bands


def find_support_resistance(code: str, current_price: float, days: int = 5, top_n: int = 5):
    """
    找到当前价格上下的支撑带和压力带
    相邻成交量密集区自动合并，不输出单个价位，输出带
    """
    profile = volume_profile(code, days)
    if not profile:
        return [], []

    bands = merge_bands(profile)

    support = sorted(
        [b for b in bands if b["price_max"] < current_price],
        key=lambda b: -b["volume"]
    )[:top_n]
    support.sort(key=lambda b: -b["price_max"])  # 从近到远

    resistance = sorted(
        [b for b in bands if b["price_min"] > current_price],
        key=lambda b: -b["volume"]
    )[:top_n]
    resistance.sort(key=lambda b: b["price_min"])  # 从近到远

    return support, resistance


def volume_support_format(code: str, current_price: float, days: int = 5):
    """格式化输出，用于盘中回答。合并相邻区间为支撑/压力带"""
    support, resistance = find_support_resistance(code, current_price, days)
    if not support and not resistance:
        return "近{days}天无显著量价密集区"

    lines = []
    for r in resistance[:2]:
        lines.append(f"  🔴 {r['label']}  (近{days}天成交占比{r['pct']}%)")
    lines.append(f"  — 现价 {current_price:.2f} —")
    for s in support[:2]:
        lines.append(f"  🟢 {s['label']}  (近{days}天成交占比{s['pct']}%)")

    return "\n".join(lines)


if __name__ == "__main__":
    for code in ["300418", "300058"]:
        name = "昆仑" if code == "300418" else "蓝标"
        print(f"\n{name} 近5天量价剖面:")
        prof = volume_profile(code, 5)
        for i, p in enumerate(prof[:10]):
            bar = "█" * int(p["pct"])
            print(f"  {p['price']:>8.2f}  {bar} ({p['pct']}%)")
