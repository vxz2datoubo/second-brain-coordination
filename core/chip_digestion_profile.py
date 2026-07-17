#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一个月筹码消化剖面：递推每日成交→各价位残留→"消化率"热力图
技术：三角分布分配成交量 + 每日换手衰减递推
输出：10层消化剖面 + 筹码搬移轨迹CSV
"""
import json, math
from pathlib import Path
from collections import defaultdict

ROOT = Path("F:/aidanao")
KL_PATH = ROOT / "data/news_db/staging/_raw/kline_300418.json"
OUT_DIR = ROOT / "data/chip_digestion"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PRICE_BINS = 20  # 20个价位层
START_DATE = "2026-06-15"  # 一个月前

def load_bars():
    d = json.loads(KL_PATH.read_text(encoding="utf-8"))
    bars = d["bars"]
    # filter from START_DATE
    out = []
    for b in bars:
        if b["date"] >= START_DATE:
            out.append(b)
    return out

def triangular_alloc(bar):
    """将当日成交量按三角分布分配到 Open-High-Low-Close 区间
       返回 {price_bin_center: volume} 的 dict.
       price in raw values (前复权), 不会变."""
    o, h, l, c, v = bar["open"], bar["high"], bar["low"], bar["close"], bar["volume"]
    bins = PRICE_BINS
    lo = min(l, o, c)
    hi = max(h, o, c)
    if hi == lo:
        # 一字板，全量在一个价位
        return {round(lo, 2): v}

    step = (hi - lo) / bins
    alloc = defaultdict(float)
    for i in range(bins):
        p_lo = lo + i * step
        p_mid = round(lo + (i + 0.5) * step, 2)
        # 三角分布权重：越接近 mid(ohlc平均) 权重越大
        p_hi = lo + (i + 1) * step
        # 简单：用三角密度 = 在close附近的权重高, 在高/低的极值处权重低
        mid_price = (o + 2*h + l + 2*c) / 6.0  # VWAP近似
        dist = 1.0 - min(1.0, abs(p_mid - mid_price) / (hi - lo)) * 0.8
        weight = dist / bins
        alloc[p_mid] += v * weight
    return dict(alloc)

def build_profile(bars, target_date="20260715"):
    """递推：从START_DATE到target_date，逐日累积，每日换手衰减"""
    # chips[price] = accumulated volume still holding (未换手量)
    chips = defaultdict(float)
    total_circulation = 1187000000  # 约11.87亿流通股(估算)
    # 实际上流通盘从换手率反算：换手率≈日成交量/流通盘
    # 我们以手为单位, 流通盘≈1187万手(估算)
    circ_hands = 11870000  # 约1187万手流通盘

    daily_log = []

    for bar in bars:
        date = bar["date"]
        vol = bar["volume"]  # 手
        turnover = vol / circ_hands  # 当日换手率(近似)

        # Step1: 旧筹码衰减 = chips[p] * (1 - turnover)
        decayed = {}
        for p, v in chips.items():
            remaining = v * (1.0 - turnover)
            if remaining > 1:
                decayed[p] = remaining
        chips = defaultdict(float, decayed)

        # Step2: 新增当日成交，分配到各价位
        new_alloc = triangular_alloc(bar)
        for p, v in new_alloc.items():
            chips[p] += v

        # Log
        total_holding = sum(chips.values())
        daily_log.append({
            "date": date,
            "turnover": round(turnover, 6),
            "new_vol": vol,
            "total_holding": round(total_holding, 0),
            "n_prices": len(chips),
        })

        if date >= target_date:
            break

    return dict(chips), daily_log

def layerize(chips, lo=None, hi=None, n_layers=10):
    """将 chips 按价位分层，计算每层的消化/残留量"""
    prices = sorted(chips.keys())
    if lo is None:
        lo = min(prices)
    if hi is None:
        hi = max(prices)
    step = (hi - lo) / n_layers
    layers = []
    for i in range(n_layers):
        layer_lo = lo + i * step
        layer_hi = lo + (i + 1) * step
        vol = 0.0
        for p in prices:
            if layer_lo <= p < layer_hi or (i == n_layers-1 and p >= layer_lo):
                vol += chips.get(p, 0)
        layers.append({
            "layer": i + 1,
            "range": f"{layer_lo:.2f}-{layer_hi:.2f}",
            "center": round((layer_lo + layer_hi) / 2, 2),
            "volume_hands": round(vol, 0),
        })
    total = sum(l["volume_hands"] for l in layers)
    for l in layers:
        l["pct"] = round(l["volume_hands"] / total * 100, 1) if total > 0 else 0
    return layers, total

# ---- 消化率热力图 ----
def digestion_heatmap(bars, target_date="20260715"):
    """计算从 START_DATE 开始的原始筹码经过每日换手后的残留比例"""
    # 暂存到 7/15 的原始筹码残留
    circ_hands = 11870000

    # 逐日递推，追踪"从START_DATE以来被分配的筹码"的残留
    # origin[p] = bin分配量（6/15以来的累计原始筹码）
    # 每天 origin[p] *= (1-turnover)
    origin = defaultdict(float)
    total_origin = 0

    for bar in bars:
        date = bar["date"]
        vol = bar["volume"]
        turnover = vol / circ_hands

        # origin衰减
        for p in list(origin.keys()):
            origin[p] *= (1.0 - turnover)
            if origin[p] < 1:
                del origin[p]

        # 新增原始筹码
        new = triangular_alloc(bar)
        for p, v in new.items():
            origin[p] += v
            total_origin += v

        if date >= target_date:
            break

    # 按层聚合
    prices = sorted(origin.keys())
    lo, hi = min(prices), max(prices)
    step = (hi - lo) / 10
    layers = []
    for i in range(10):
        l_lo, l_hi = lo + i * step, lo + (i + 1) * step
        v = sum(origin[p] for p in prices if l_lo <= p < l_hi or (i == 9 and p >= l_lo))
        layers.append({
            "layer": i + 1,
            "center": round((l_lo + l_hi) / 2, 2),
            "range": f"{l_lo:.2f}-{l_hi:.2f}",
            "volume": round(v, 0),
        })
    total_v = sum(l["volume"] for l in layers)
    for l in layers:
        l["pct"] = round(l["volume"] / total_v * 100, 1) if total_v > 0 else 0
    return layers, total_v

def run():
    bars = load_bars()
    print(f"加载 {len(bars)} 根日K ({bars[0]['date']}~{bars[-1]['date']})")

    chips, daily_log = build_profile(bars, "20260715")
    print(f"递推到 7/15: {len(chips)} 个价位, 总持有量 {sum(chips.values()):.0f} 手")

    # 10层剖面
    layers, total_v = layerize(chips, lo=36.0, hi=54.0, n_layers=10)
    print(f"\n{'='*70}")
    print(f"📊 十层未消化筹码剖面 (2026-06-15 → 2026-07-15)")
    print(f"{'='*70}")
    print(f"{'层':>3} {'价位区间':>14} {'残留量(手)':>12} {'占比':>7} {'█'*10}")
    print(f"{'-'*3} {'-'*14} {'-'*12} {'-'*7}")
    bar_len = 30
    max_v = max(l["volume_hands"] for l in layers)
    for l in layers:
        n = int(l["volume_hands"] / max_v * bar_len) if max_v > 0 else 0
        print(f"{l['layer']:3d} {l['range']:>14} {l['volume_hands']:>12,.0f} {l['pct']:>6.1f}% {'█' * n}")

    # 消化率热力图
    print(f"\n{'='*70}")
    print(f"🔥 消化率热力图 (一个月内原始筹码残留比例)")
    print(f"{'='*70}")
    heat_layers, heat_total = digestion_heatmap(bars, "20260715")
    max_heat = max(l["volume"] for l in heat_layers)
    print(f"{'层':>3} {'价位区间':>14} {'残留(手)':>12} {'占比':>7} {'消化判定'}")
    print(f"{'-'*3} {'-'*14} {'-'*12} {'-'*7}")
    for l in heat_layers:
        n = int(l["volume"] / max_heat * bar_len) if max_heat > 0 else 0
        bar = "█" * n
        # 消化判定：占比高=未消化（价格对此仍有记忆），占比低=已消化
        if l["pct"] > 20:
            tag = "🔴 未消化（强阻力/支撑）"
        elif l["pct"] > 10:
            tag = "🟡 半消化"
        elif l["pct"] > 5:
            tag = "🟢 已消化"
        else:
            tag = "✅ 充分消化（无记忆）"
        print(f"{l['layer']:3d} {l['range']:>14} {l['volume']:>12,.0f} {l['pct']:>6.1f}% {bar:20} {tag}")

    # 保存CSV
    import csv
    with open(OUT_DIR / "digestion_layers.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(layers[0].keys()))
        w.writeheader()
        for l in layers:
            w.writerow(l)
    with open(OUT_DIR / "digestion_heatmap.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(heat_layers[0].keys()))
        w.writeheader()
        for l in heat_layers:
            w.writerow(l)
    with open(OUT_DIR / "daily_turnover_log.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(daily_log[0].keys()))
        w.writeheader()
        for r in daily_log:
            w.writerow(r)

    print(f"\n✅ 输出: {OUT_DIR}/")
    print(f"   digestion_layers.csv    — 十层未消化筹码剖面")
    print(f"   digestion_heatmap.csv   — 一个月消化率热力图")
    print(f"   daily_turnover_log.csv  — 每日递推日志")

if __name__ == "__main__":
    run()
