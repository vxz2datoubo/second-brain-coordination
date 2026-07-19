"""
量价效率分析 — 波仔倒T系统核心创新模块

核心概念:
  传统Volume Profile只告诉你"哪个价位成交了多少"
  量价效率告诉你"每个价位的成交量推动了多少价格变化"
  
  硬阻力: Δ成交量很大 + Δ价格很小 = 大量换手但推不动 → 值得做倒T
  软阻力: Δ成交量很小 + Δ价格很大 = 轻松穿过 → 做倒T意义不大

公式:
  量效率 = Δ成交量(%) / Δ价格(%)
  额效率 = Δ成交额(%) / Δ价格(%)
  
  效率 > 3.0 → 硬阻力（卖出信号强度高）
  效率 1.0~3.0 → 中等阻力
  效率 < 1.0 → 软阻力（卖出信号强度低）

数据源:
  通达信5分钟K线 (本地.lc5文件)
  支持近5天、近30天、当日实时三种时间窗口
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.tdx_parser import read_minute_kline, read_daily_kline, group_by_date

TDX_FZLINE = r"F:\tongdaxin\vipdoc\sz\fzline"


def get_price_step(avg_price: float) -> float:
    """根据股价自动选择步长"""
    if avg_price > 100:
        return 2.0
    elif avg_price > 30:
        return 0.5
    elif avg_price > 10:
        return 0.1
    else:
        return 0.05


def efficiency_profile(code: str, days: int = 5, step: float = None):
    """
    计算每个价格区间的量价效率

    返回: [
      {"price_range": "40.5-41.0", "volume_chg_pct": 12.3, "price_chg_pct": 3.5,
       "vol_efficiency": 3.5, "amount_efficiency": 4.1, "hardness": "硬阻力"},
      ...
    ]
    """
    fp = f"{TDX_FZLINE}/sz{code}.lc5"
    bars = read_minute_kline(fp)
    groups = group_by_date(bars)
    dates = sorted(groups.keys())
    recent_dates = dates[-days:]

    # 收集所有价格点
    all_prices = []
    for d in recent_dates:
        for b in groups[d]:
            all_prices.extend([b.open, b.close, b.high, b.low])
    price_min = min(all_prices)
    price_max = max(all_prices)

    if step is None:
        step = get_price_step((price_max + price_min) / 2)

    # 按步长分桶，统计每个区间的成交量和价格变化
    bucket_floor = int(price_min / step) * step
    num_buckets = int((price_max - bucket_floor) / step) + 2

    buckets = {}
    for i in range(num_buckets):
        p = round(bucket_floor + i * step, 2)
        buckets[p] = {"volume": 0, "amount": 0.0, "price_points": [], "k_count": 0}

    for d in recent_dates:
        for b in groups[d]:
            mid = (b.open + b.close) / 2
            bucket = round(int(mid / step) * step, 2)
            if bucket in buckets:
                buckets[bucket]["volume"] += b.volume
                buckets[bucket]["amount"] += b.amount
                buckets[bucket]["k_count"] += 1
                # 记录价格变化：用振幅的1/4作为该K线内的价格推动量
                price_impact = (b.high - b.low) / 4 if b.high > b.low else step * 0.1
                buckets[bucket]["price_points"].append(price_impact)

    # 计算效率 — 核心创新算法
    # 思路: 比较"成交量占比" vs "价格运动占比"
    # 如果10%的成交量只推动了2%的价格运动 → 效率=5x → 硬阻力
    # 如果3%的成交量推动了5%的价格运动 → 效率=0.6x → 软阻力

    bucket_list = sorted(buckets.items())
    results = []

    total_volume_all = sum(b["volume"] for _, b in bucket_list if b["volume"] > 0)
    total_amount_all = sum(b["amount"] for _, b in bucket_list if b["amount"] > 0)

    # 价格运动总量 = 每根K线的振幅总和
    total_price_movement = 0
    for _, data in bucket_list:
        total_price_movement += sum(data["price_points"])

    for price, data in bucket_list:
        if data["volume"] == 0 or data["k_count"] == 0:
            continue

        # 成交量占比
        vol_share = data["volume"] / total_volume_all * 100 if total_volume_all > 0 else 0
        amt_share = data["amount"] / total_amount_all * 100 if total_amount_all > 0 else 0

        # 价格运动占比 = 该区间的振幅 / 总振幅
        price_movement = sum(data["price_points"])
        price_share = price_movement / total_price_movement * 100 if total_price_movement > 0 else 0.01

        # 效率 = 量占比 / 价动占比
        # > 3: 硬阻力（大量换手但价格几乎不动）
        # 1-3: 中等
        # < 1: 软阻力（价格轻松穿过）
        vol_eff = round(vol_share / price_share, 1) if price_share > 0.001 else 9.9
        amt_eff = round(amt_share / price_share, 1) if price_share > 0.001 else 9.9

        # 两维度交叉验证
        avg_eff = (vol_eff + amt_eff) / 2

        if avg_eff >= 3.0:
            hardness = "硬阻力"
        elif avg_eff >= 1.5:
            hardness = "中等阻力"
        elif avg_eff >= 0.8:
            hardness = "软阻力"
        else:
            hardness = "可轻松通过"

        results.append({
            "price": price,
            "price_label": f"{price:.2f}-{price+step:.2f}",
            "volume_share": round(vol_share, 2),
            "amount_share": round(amt_share, 2),
            "price_share": round(price_share, 2),
            "vol_efficiency": vol_eff,
            "amount_efficiency": amt_eff,
            "avg_efficiency": round(avg_eff, 1),
            "hardness": hardness,
            "k_count": data["k_count"],
        })

    results.sort(key=lambda x: x["price"])
    return results


def efficiency_above_price(code: str, current_price: float, days: int = 5) -> list:
    """
    获取当前价格上方所有阻力层的效率分析
    用于倒T卖出决策：硬阻力的层优先卖出
    """
    profile = efficiency_profile(code, days)
    above = [p for p in profile if p["price"] > current_price]
    # 按效率排序：硬阻力优先
    above.sort(key=lambda x: -x["avg_efficiency"])
    return above


def efficiency_format(code: str, current_price: float, days: int = 5, top_n: int = 6) -> str:
    """
    格式化输出：适合盘中回答
    """
    above = efficiency_above_price(code, current_price, days)
    if not above:
        return "无有效阻力数据"

    lines = [f"  近{days}天量价效率分析 ({code})"]
    # 按价格从远到近排列（模拟K线图）
    above_by_price = sorted(above, key=lambda x: -x["price"])
    for p in above_by_price[:top_n]:
        bar = int(p["volume_share"] * 3)
        bl = '▓' * min(bar, 60) + ' ·' * max(0, 60 - bar)
        label = f"{p['price_label']}"
        lines.append(f"  {label:>12} │{bl}│ {p['hardness']} (效率{p['avg_efficiency']:.1f}x, Δ量{p['volume_share']:.1f}%)")

    return "\n".join(lines)


def reverse_t_ranking(code: str, current_price: float, days: int = 5, top_n: int = 3) -> list:
    """
    倒T卖出优先级排序
    硬阻力 + 靠近当前价 = 最优卖出目标
    软阻力 + 远离当前价 = 不推荐卖出
    """
    above = efficiency_above_price(code, current_price, days)

    scored = []
    for p in above:
        # 综合评分 = 效率权重(60%) + 距离权重(40%)
        eff_score = min(p["avg_efficiency"], 6.0) / 6.0 * 60
        dist_pct = (p["price"] / current_price - 1) * 100
        dist_score = min(dist_pct, 5.0) / 5.0 * 40  # 越近越好
        total = round(eff_score + dist_score)

        scored.append({
            "price_label": p["price_label"],
            "hardness": p["hardness"],
            "avg_efficiency": p["avg_efficiency"],
            "distance_pct": round(dist_pct, 1),
            "score": total,
        })

    scored.sort(key=lambda x: -x["score"])
    return scored[:top_n]


if __name__ == "__main__":
    for code in ["300418", "300058"]:
        name = "昆仑" if code == "300418" else "蓝标"
        cur = 40.42 if code == "300418" else 13.73
        print(f"\n{'='*60}")
        print(f"  {name}({code}) 量价效率分析 (近5天)")
        print(f"{'='*60}")
        print(efficiency_format(code, cur, 5))
        print(f"\n  倒T优先级:")
        for i, r in enumerate(reverse_t_ranking(code, cur, 5)):
            print(f"  #{i+1} {r['price_label']} {r['hardness']} (效率{r['avg_efficiency']:.1f}x, 距{r['distance_pct']:+.1f}%, 评分{r['score']})")
