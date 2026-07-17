"""hvn_lvn_nodes.py — HVN/LVN 成交量节点分析 v1

HVN=高量节点(慢速区/磁铁/目标位)
LVN=低量节点(快速区/支撑阻力/入场位)

与量价剖面的区别:
  量价剖面(crossover_tracker.adjusted_profile) → 找支撑阻力层
  HVN/LVN → 找价格速度区(哪里快/哪里慢)

核心概念:
  HVN = 价格粘住(盘整) → 目标位, 不是入场位
  LVN = 价格飞过(拒绝) → 入场位, 首次触碰反弹率70-80%
  HVN→LVN运动 = 最优交易结构

联动: supply-test / accumulation-detection / breakout-validator / vwap-analyzer
"""

import sys, os, struct, json
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))

STATE_FILE = os.path.join(ROOT, "_hvn_state.json")


def _load_bars(code, days=20):
    """从1分钟K线聚合为日K线，用于计算Volume Profile"""
    market = "sz" if code.startswith(("0", "3")) else "sh"
    path = rf"F:\tongdaxin\vipdoc\{market}\minline\{market}{code}.lc1"
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        data = f.read()
    n = len(data) // 32
    # 聚合为日K线
    daily = []
    prev_date = None
    day_open = day_high = day_low = day_close = day_vol = 0
    start = max(0, n - days * 240)
    for i in range(start, n):
        u = struct.unpack_from("<HHfffffIHH", data, i * 32)
        dw, sec = u[0], u[1]
        op, hi, lo, cl, amt = u[2], u[3], u[4], u[5], u[6]
        y, m, d = (dw // 2048) + 2004, (dw % 2048) // 100, dw % 2048 % 100
        date_str = f"{y:04d}{m:02d}{d:02d}"
        v = amt / 100.0
        if date_str != prev_date:
            if prev_date is not None and day_vol > 0:
                daily.append({"date": prev_date, "open": day_open, "high": day_high,
                              "low": day_low, "close": day_close, "volume": day_vol,
                              "typical": (day_high + day_low + day_close) / 3})
            prev_date = date_str
            day_open = op; day_high = hi; day_low = lo; day_close = cl; day_vol = v
        else:
            day_high = max(day_high, hi)
            day_low = min(day_low, lo)
            day_close = cl
            day_vol += v
    if prev_date and day_vol > 0:
        daily.append({"date": prev_date, "open": day_open, "high": day_high,
                      "low": day_low, "close": day_close, "volume": day_vol,
                      "typical": (day_high + day_low + day_close) / 3})
    return daily[-days:]


def compute_nodes(code, days=20, current_price=None):
    """
    从日K线计算HVN/LVN区域
    
    简化方法: 用价格区间的成交量分布近似Volume Profile
    
    Returns:
        {
            "poc": float, "vah": float, "val": float,
            "hvn_zones": [(lo, hi, vol_pct), ...],  # 高量节点
            "lvn_zones": [(lo, hi), ...],            # 低量节点
            "price_vs_nodes": str,                    # 当前价格相对节点位置
            "nearest_hvn": (lo, hi),                  # 最近HVN(目标位)
            "nearest_lvn": (lo, hi),                  # 最近LVN(入场位)
        }
    """
    bars = _load_bars(code, days)
    if len(bars) < 5:
        return {"poc": None, "detail": "数据不足"}

    # 找出价格范围
    all_prices = []
    price_vol = defaultdict(float)
    for b in bars:
        # 用(high+low+close)/3 作为代表价
        typical = (b["high"] + b["low"] + b["close"]) / 3
        all_prices.append(typical)
        price_vol[typical] += b["volume"]

    price_min = min(all_prices)
    price_max = max(all_prices)
    price_range = price_max - price_min

    # 将价格空间分成20个区间
    bins = 20
    bin_width = price_range / bins if price_range > 0 else 0.01
    vol_bins = defaultdict(float)
    for p, v in price_vol.items():
        idx = int((p - price_min) / bin_width)
        idx = min(idx, bins - 1)
        vol_bins[idx] += v

    # 找POC
    total_vol = sum(vol_bins.values())
    if total_vol == 0:
        return {"poc": None, "detail": "无成交量数据"}

    poc_idx = max(vol_bins, key=vol_bins.get)
    poc = round(price_min + (poc_idx + 0.5) * bin_width, 2)

    # 识别HVN和LVN
    avg_bin_vol = total_vol / bins
    hvn_indices = []
    lvn_indices = []

    for idx in range(bins):
        pct = vol_bins[idx] / total_vol * 100 if total_vol > 0 else 0
        if pct > avg_bin_vol / total_vol * 150:  # 比平均高50%
            hvn_indices.append(idx)
        elif pct < avg_bin_vol / total_vol * 50:  # 比平均低50%
            lvn_indices.append(idx)

    # 合并连续区间
    def merge_indices(indices):
        if not indices: return []
        zones = []
        start = indices[0]
        prev = indices[0]
        for i in indices[1:]:
            if i == prev + 1:
                prev = i
            else:
                zones.append((start, prev))
                start = i
                prev = i
        zones.append((start, prev))
        return zones

    hvn_zones = []
    for s, e in merge_indices(hvn_indices):
        lo = round(price_min + s * bin_width, 2)
        hi = round(price_min + (e + 1) * bin_width, 2)
        vol_sum = sum(vol_bins[i] for i in range(s, e + 1))
        hvn_zones.append((lo, hi, round(vol_sum / total_vol * 100, 1)))

    lvn_zones = []
    for s, e in merge_indices(lvn_indices):
        lo = round(price_min + s * bin_width, 2)
        hi = round(price_min + (e + 1) * bin_width, 2)
        lvn_zones.append((lo, hi))

    # 找到最近HVN/LVN
    nearest_hvn = None
    nearest_lvn = None
    min_hvn_dist = float("inf")
    min_lvn_dist = float("inf")

    if current_price:
        for lo, hi, _ in hvn_zones:
            d = min(abs(current_price - lo), abs(current_price - hi))
            if d < min_hvn_dist:
                min_hvn_dist = d
                nearest_hvn = (lo, hi)
        for lo, hi in lvn_zones:
            d = min(abs(current_price - lo), abs(current_price - hi))
            if d < min_lvn_dist:
                min_lvn_dist = d
                nearest_lvn = (lo, hi)

    # 当前价格位置
    price_vs = ""
    if current_price and nearest_hvn:
        if nearest_hvn[0] <= current_price <= nearest_hvn[1]:
            price_vs = "在HVN中(⚠️盘整风险)"
        elif current_price > nearest_hvn[1]:
            price_vs = f"在HVN上方, 下方HVN{nearest_hvn[0]:.1f}-{nearest_hvn[1]:.1f}为支撑目标"
        else:
            price_vs = f"在HVN下方, 上方HVN{nearest_hvn[0]:.1f}-{nearest_hvn[1]:.1f}为阻力目标"

    return {
        "poc": poc,
        "vah": poc + bin_width * 2,
        "val": poc - bin_width * 2,
        "hvn_zones": hvn_zones,
        "lvn_zones": lvn_zones,
        "price_vs_nodes": price_vs,
        "nearest_hvn": nearest_hvn,
        "nearest_lvn": nearest_lvn,
        "hvn_count": len(hvn_zones),
        "lvn_count": len(lvn_zones),
    }


def score_for_quad_lens(code, current_price=None):
    """
    为quad_lens提供HVN/LVN速度偏置 (±5分)
    """
    nodes = compute_nodes(code, current_price=current_price)
    if nodes.get("poc") is None:
        return {"score": 0, "detail": "", "hvn_targets": []}

    score = 0
    signals = []

    # 价格在HVN中 → 不利(盘整风险)
    if nodes.get("price_vs_nodes", "").startswith("在HVN中"):
        score -= 3
        signals.append("⚠️ 在HVN中: 盘整风险, 不宜入场")
    # 价格刚从HVN出来向上 → 有利
    elif nodes.get("nearest_hvn") and current_price:
        hvn = nodes["nearest_hvn"]
        if current_price > hvn[1]:
            score += 3
            signals.append(f"价格在HVN{hvn[0]:.1f}-{hvn[1]:.1f}上方 → 强势")

    # LVN首次回踩机会
    if nodes.get("nearest_lvn") and current_price:
        lvn = nodes["nearest_lvn"]
        dist = abs(current_price - (lvn[0] + lvn[1]) / 2)
        if dist < 0.01 * current_price:
            score += 3
            signals.append(f"接近LVN{lvn[0]:.1f}-{lvn[1]:.1f} → 首次触碰机会")

    detail = " | ".join(signals) if signals else "无显著节点信号"
    return {
        "score": max(-5, min(5, score)),
        "detail": detail,
        "signals": signals,
        "hvn_targets": [(lo, hi) for lo, hi, _ in nodes.get("hvn_zones", [])],
        "lvn_zones": nodes.get("lvn_zones", []),
    }


def summary(code):
    """一句话摘要"""
    nodes = compute_nodes(code)
    if nodes.get("poc") is None: return ""
    return f"POC:{nodes['poc']} HVN:{nodes['hvn_count']}个 LVN:{nodes['lvn_count']}个"


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("--price", type=float)
    args = p.parse_args()

    nodes = compute_nodes(args.code, current_price=args.price)
    print(f"\n  POC: {nodes.get('poc')}")
    print(f"  VAH: {nodes.get('vah')} | VAL: {nodes.get('val')}")
    print(f"  HVN ({nodes['hvn_count']}个):")
    for lo, hi, pct in nodes.get("hvn_zones", [])[:5]:
        print(f"    {lo:.2f}-{hi:.2f} ({pct:.1f}%)")
    print(f"  LVN ({nodes['lvn_count']}个):")
    for lo, hi in nodes.get("lvn_zones", [])[:5]:
        print(f"    {lo:.2f}-{hi:.2f}")
    if nodes.get("price_vs_nodes"):
        print(f"  位置: {nodes['price_vs_nodes']}")
    print()
