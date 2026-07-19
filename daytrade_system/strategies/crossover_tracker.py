"""
穿越难度修正器 — 波仔系统核心模块

核心价值:
  量价剖面告诉你"这个价位曾经成交了多少"
  穿越难度告诉你"上一次穿过这个价位用了多少力气"
  
  穿越轻(少成交即穿过) → 筹码已消化 → 修正×0.7
  穿越重(多成交才穿过) → 阻力很硬核 → 修正×1.3

算法:
  1. 找到最近一次价格穿越某个区间的K线
  2. 穿越比 = 穿越时成交量 / 该区间5天总成交量
  3. 穿越比<0.3 → 软(×0.7) | 0.3-0.7 → 正常(×1.0) | >0.7 → 硬(×1.3)

集成点:
  - runner.py premarket: 量价剖面输出自动带修正标注
  - 每日做T时判断: 虚阻力不卖, 实阻力必卖
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.tdx_parser import read_minute_kline, group_by_date
from strategies.volume_profile import volume_profile

TDX_FZLINE = r"F:\tongdaxin\vipdoc\sz\fzline"


def crossover_ratio(code: str, price_lo: float, price_hi: float, days: int = 5) -> dict:
    """
    计算某个价格区间的穿越比

    Args:
        code: 股票代码
        price_lo, price_hi: 价格区间
        days: 回顾天数

    Returns:
        {ratio: 穿越比, modifier: 权重系数, label: 描述标签, crossed: bool}
    """
    fp = f"{TDX_FZLINE}/sz{code}.lc5"
    bars = read_minute_kline(fp)
    if not bars:
        return {"ratio": 1.0, "modifier": 1.0, "label": "无数据", "crossed": False}

    groups = group_by_date(bars)
    dates = sorted(groups.keys())

    if len(dates) < days:
        days = len(dates)
    recent_dates = dates[-days:]

    # 统计该带内总成交量
    total_vol = 0
    for d in recent_dates:
        for b in groups[d]:
            mid = (b.open + b.close) / 2
            if price_lo <= mid <= price_hi:
                total_vol += b.volume

    if total_vol == 0:
        return {"ratio": 0, "modifier": 1.0, "label": "零量", "crossed": False}

    # 逆序找最近一次完整穿越（从上往下或从下往上）
    cross_vol = 0
    found_entry = False
    found_exit = False

    for d in reversed(recent_dates):
        for b in reversed(groups[d]):
            mid = (b.open + b.close) / 2
            in_band = price_lo <= mid <= price_hi

            if not found_entry and in_band:
                found_entry = True
                cross_vol += b.volume
            elif found_entry and in_band:
                cross_vol += b.volume
            elif found_entry and not in_band:
                found_exit = True
                break
        if found_exit:
            break

    if not found_entry:
        return {"ratio": 1.0, "modifier": 1.0, "label": "未穿越", "crossed": False}

    ratio = cross_vol / total_vol

    if ratio < 0.3:
        modifier = 0.7
        if ratio < 0.1:
            label = f"极轻穿越×0.7(比{ratio:.2f})"
        else:
            label = f"轻穿越×0.7(比{ratio:.2f})"
    elif ratio < 0.7:
        modifier = 1.0
        label = f"正常×1.0(比{ratio:.2f})"
    else:
        modifier = 1.3
        label = f"重穿越×1.3(比{ratio:.2f})"

    return {
        "ratio": round(ratio, 2),
        "modifier": modifier,
        "label": label,
        "crossed": True,
        "total_vol": total_vol,
        "cross_vol": cross_vol,
    }


def adjusted_profile(code: str, current_price: float, days: int = 5,
                     min_pct: float = 0.2) -> list:
    """
    生成穿越修正后的量价剖面

    Returns: [{price, pct, adjusted_pct, modifier, label, ...}, ...]
    """
    prof = volume_profile(code, days)
    sig = [(p["price"], p["pct"]) for p in prof if p["pct"] >= min_pct]
    sig.sort(key=lambda x: x[0])

    # 根据当前价格找步长
    if len(sig) > 1:
        step = sig[1][0] - sig[0][0]
    else:
        step = 0.5

    # 阻力层（价格 > current_price）— 取10层
    resistance = sorted(
        [(pr, pc) for pr, pc in sig if pr > current_price],
        key=lambda x: x[0] - current_price
    )[:10]

    # 支撑层 — 取10层
    support = sorted(
        [(pr, pc) for pr, pc in sig if pr < current_price],
        key=lambda x: current_price - x[0]
    )[:10]

    result = []

    # 输出阻力（从高到低排列）
    for i, (pr, pc) in enumerate(reversed(resistance)):
        cross = crossover_ratio(code, pr, pr + step, days)
        adj = round(pc * cross["modifier"], 1)
        result.append({
            "side": "resistance",
            "level": f"P{len(resistance)-i}",
            "price_lo": pr,
            "price_hi": pr + step,
            "label": f"{pr:.2f}-{pr+step:.2f}",
            "pct": pc,
            "adjusted_pct": adj,
            "modifier": cross["modifier"],
            "cross_label": cross["label"],
            "cross_ratio": cross["ratio"],
        })

    # 输出支撑（从高到低排列）
    for i, (pr, pc) in enumerate(support):
        cross = crossover_ratio(code, pr, pr + step, days)
        adj = round(pc * cross["modifier"], 1)
        result.append({
            "side": "support",
            "level": f"S{i+1}",
            "price_lo": pr,
            "price_hi": pr + step,
            "label": f"{pr:.2f}-{pr+step:.2f}",
            "pct": pc,
            "adjusted_pct": adj,
            "modifier": cross["modifier"],
            "cross_label": cross["label"],
            "cross_ratio": cross["ratio"],
        })

    return result


def format_adjusted(profile: list, current_price: float) -> str:
    """可视化输出修正版量价剖面"""
    resistance = [p for p in profile if p["side"] == "resistance"]
    support = [p for p in profile if p["side"] == "support"]

    lines = []

    for r in reversed(resistance):
        bl = int(r["adjusted_pct"] * 4)
        br = '▓' * min(bl, 60) + ' ·' * max(0, 60 - bl)
        icon = "🟢" if r["modifier"] < 1.0 else "🔴" if r["modifier"] > 1.0 else "➖"
        lines.append(f"  {r['level']} {r['label']:>12} |{br}| {r['pct']:.1f}%→{r['adjusted_pct']:.1f}% {icon}{r['cross_label']}")

    lines.append(f"  ——— {current_price:.2f} ———")

    for s in support:
        bl = int(s["adjusted_pct"] * 4)
        br = '▓' * min(bl, 60) + ' ·' * max(0, 60 - bl)
        icon = "🟢" if s["modifier"] < 1.0 else "🔴" if s["modifier"] > 1.0 else "➖"
        lines.append(f"  {s['level']} {s['label']:>12} |{br}| {s['pct']:.1f}%→{s['adjusted_pct']:.1f}% {icon}{s['cross_label']}")

    return "\n".join(lines)


if __name__ == "__main__":
    for code, cur in [("300418", 40.93), ("300058", 14.29)]:
        print(f"\n{'='*60}")
        print(f"  {code} {cur:.2f} (穿越难度修正版)")
        print(f"{'='*60}")
        prof = adjusted_profile(code, cur, 5)
        print(format_adjusted(prof, cur))
