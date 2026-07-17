"""backtest_hvn_lvn.py — HVN/LVN节点回测(无未来函数)

核心假设:
  1. LVN边缘=入场区 → 触碰后反弹
  2. HVN内=慢速区 → 振幅小(不利做T)
  3. HVN外=快速区 → 振幅大(有利做T)
  4. HVN=目标 → 价格倾向于到达最近HVN

数据: 102天1分钟K线
方法: 每天用前20天数据计算HVN/LVN, 当天仅用于验证
"""

import struct, os
from collections import defaultdict

CODE = "300418"
LOOKBACK = 20  # 回看天数

# ── 数据加载 ──
path = rf"F:\tongdaxin\vipdoc\sz\minline\sz300418.lc1"
with open(path, "rb") as f:
    raw = f.read()
N = len(raw) // 32

# 日K线聚合
daily_all = []
pd_ = None; oo=hh=ll=cc=vv=0
for i in range(N):
    u = struct.unpack_from("<HHfffffIHH", raw, i * 32)
    dw, sec = u[0], u[1]
    y, m, d = (dw // 2048) + 2004, (dw % 2048) // 100, dw % 2048 % 100
    ds = f"{y:04d}{m:02d}{d:02d}"
    op, hi, lo, cl, amt = u[2], u[3], u[4], u[5], u[6]
    vv_ = amt / 100.0
    if ds != pd_:
        if pd_ and vv > 0:
            daily_all.append({"date": pd_, "o": oo, "h": hh, "l": ll, "c": cc, "v": vv})
        pd_ = ds; oo=op; hh=hi; ll=lo; cc=cl; vv=vv_
    else:
        hh=max(hh,hi); ll=min(ll,lo); cc=cl; vv+=vv_
if pd_:
    daily_all.append({"date": pd_, "o": oo, "h": hh, "l": ll, "c": cc, "v": vv})

# 1分钟数据
min_all = defaultdict(list)
for i in range(N):
    u = struct.unpack_from("<HHfffffIHH", raw, i * 32)
    dw, sec = u[0], u[1]
    y, m, d = (dw // 2048) + 2004, (dw % 2048) // 100, dw % 2048 % 100
    ds = f"{y:04d}{m:02d}{d:02d}"
    min_all[ds].append({"t": sec, "h": u[3], "l": u[4], "c": u[5], "v": u[6]/100})

dates = sorted(min_all.keys())

# ── HVN/LVN 计算 (纯历史数据, 无未来) ──
def compute_hvn_lvn(history_days, bins=20):
    """从历史日K线计算HVN/LVN"""
    if len(history_days) < 5:
        return None
    prices = []
    vols = defaultdict(float)
    for d in history_days:
        typical = (d["h"] + d["l"] + d["c"]) / 3
        prices.append(typical)
        vols[typical] += d["v"]
    p_min, p_max = min(prices), max(prices)
    if p_min >= p_max:
        return None
    bw = (p_max - p_min) / bins
    vb = defaultdict(float)
    for p, v in vols.items():
        idx = min(int((p - p_min) / bw), bins - 1)
        vb[idx] += v
    total = sum(vb.values())
    if total == 0: return None
    poc_idx = max(vb, key=vb.get)
    poc = p_min + (poc_idx + 0.5) * bw
    avg_bin = total / bins
    hvn = []
    lvn = []
    for idx in range(bins):
        if vb[idx] > avg_bin * 1.5:
            lo = p_min + idx * bw
            hi = p_min + (idx + 1) * bw
            hvn.append((lo, hi))
        elif vb[idx] < avg_bin * 0.5:
            lo = p_min + idx * bw
            hi = p_min + (idx + 1) * bw
            lvn.append((lo, hi))
    return {"poc": poc, "hvn": hvn, "lvn": lvn}


def price_in_zone(price, zones):
    for lo, hi in zones:
        if lo <= price <= hi:
            return True
    return False


def nearest_zone(price, zones):
    best_d = float("inf")
    best_z = None
    for lo, hi in zones:
        d = min(abs(price - lo), abs(price - hi))
        if d < best_d:
            best_d = d
            best_z = (lo, hi)
    return best_z


# ── 回测 ──
results = {
    "lvn_bounce": [],      # (进入LVN后是否反弹>threshold)
    "lvn_entry_profit": [],  # LVN边缘做T收益
    "hvn_range": [],        # HVN内的日内振幅
    "outside_range": [],    # HVN外的日内振幅
    "hvn_target_reach": [], # 是否到达最近HVN
    "hvn_stay": [],         # 进入HVN后是否停留
}

BOUNCE_THRESH = 0.005  # 0.5%反弹

for i in range(LOOKBACK, len(dates)):
    today = dates[i]
    hist = daily_all[i - LOOKBACK:i]  # 只用历史数据
    
    nodes = compute_hvn_lvn(hist)
    if nodes is None: continue
    
    hvn_zones = nodes["hvn"]
    lvn_zones = nodes["lvn"]
    poc = nodes["poc"]
    
    today_bars = min_all[today]
    if len(today_bars) < 50: continue
    
    day_open = None
    day_close = today_bars[-1]["c"]
    day_high = max(b["h"] for b in today_bars)
    day_low = min(b["l"] for b in today_bars)
    day_range = (day_high - day_low) / day_low * 100
    
    # 开盘价(9:30)
    for b in today_bars:
        if 9*60+30 <= b["t"] <= 9*60+31:
            day_open = b["c"]
            break
    if day_open is None: continue
    
    # ── 测试1: LVN触碰后是否反弹 ──
    for z_idx, (l_lo, l_hi) in enumerate(lvn_zones):
        l_mid = (l_lo + l_hi) / 2
        # 找盘中首次触碰LVN的时刻
        touched = False
        touch_price = 0
        for b in today_bars:
            # 从上方下来碰LVN上沿
            if not touched and b["l"] <= l_hi <= b["c"]:
                touched = True
                touch_price = b["c"]
                # 检查触碰后1小时内的最大反弹
                post_bars = [x for x in today_bars if x["t"] > b["t"] and x["t"] <= b["t"] + 60]
                if post_bars:
                    max_after = max(x["h"] for x in post_bars)
                    bounce = (max_after - touch_price) / touch_price
                    results["lvn_bounce"].append(bounce)
                    # 做T模拟: 触碰LVN上沿买入 → 1小时后最高价卖出
                    results["lvn_entry_profit"].append(bounce)
                break
            # 从下方上来碰LVN下沿
            if not touched and b["h"] >= l_lo >= b["c"]:
                touched = True
                touch_price = b["c"]
                post_bars = [x for x in today_bars if x["t"] > b["t"] and x["t"] <= b["t"] + 60]
                if post_bars:
                    max_after = max(x["h"] for x in post_bars)
                    bounce = (max_after - touch_price) / touch_price
                    results["lvn_bounce"].append(bounce)
                    results["lvn_entry_profit"].append(bounce)
                break
    
    # ── 测试2: HVN内外振幅对比 ──
    in_hvn = price_in_zone(day_open, hvn_zones)
    if in_hvn:
        results["hvn_range"].append(day_range)
        # 在HVN内能突破吗
        if day_range > 4:
            results["hvn_stay"].append(False)
        else:
            results["hvn_stay"].append(True)
    else:
        results["outside_range"].append(day_range)
    
    # ── 测试3: HVN作为目标 ──
    nearest = nearest_zone(day_open, hvn_zones)
    if nearest:
        target = nearest[0] if day_open > nearest[1] else nearest[1]
        # 是否在日内到达
        reached = (day_high >= target >= day_open) or (day_low <= target <= day_open)
        results["hvn_target_reach"].append(reached)


# ── 输出 ──
print(f"\n{'='*65}")
print(f"  📊 HVN/LVN 节点回测 — {CODE}")
print(f"  用前{LOOKBACK}天计算节点, 当天验证 (无未来函数)")
print(f"  测试天数: {len(dates) - LOOKBACK}")
print(f"{'='*65}")

# 测试1: LVN反弹
if results["lvn_bounce"]:
    avg = sum(results["lvn_bounce"]) / len(results["lvn_bounce"])
    win = sum(1 for b in results["lvn_bounce"] if b > BOUNCE_THRESH) / len(results["lvn_bounce"]) * 100
    print(f"\n  ┌─ LVN触碰反弹 ───────────────────────────────────┐")
    print(f"  │ 触碰{len(results['lvn_bounce'])}次 | 平均反弹:{avg*100:+.2f}%")
    print(f"  │ 反弹>{BOUNCE_THRESH*100:.1f}%率:{win:.0f}%")
    if results["lvn_entry_profit"]:
        p_avg = sum(results["lvn_entry_profit"]) / len(results["lvn_entry_profit"])
        p_win = sum(1 for p in results["lvn_entry_profit"] if p > 0) / len(results["lvn_entry_profit"]) * 100
        print(f"  │ 做T模拟(LVN买→1h高卖): 平均{p_avg*100:+.2f}% 胜率{p_win:.0f}%")
    print(f"  └──────────────────────────────────────────────────────┘")
else:
    print(f"\n  ┌─ LVN触碰反弹: 无数据 ─┘")

# 测试2: HVN内外振幅
if results["hvn_range"]:
    avg_h = sum(results["hvn_range"]) / len(results["hvn_range"])
    print(f"\n  ┌─ HVN内振幅 ───────────────────────────────────┐")
    print(f"  │ 在HVN内开盘: {len(results['hvn_range'])}天")
    print(f"  │ 平均振幅: {avg_h:.2f}%")
    if results["hvn_stay"]:
        stay_pct = sum(1 for s in results["hvn_stay"] if s) / len(results["hvn_stay"]) * 100
        print(f"  │ 振幅<4%(困在HVN内)率: {stay_pct:.0f}%")
    print(f"  └──────────────────────────────────────────────────┘")
if results["outside_range"]:
    avg_o = sum(results["outside_range"]) / len(results["outside_range"])
    print(f"\n  ┌─ HVN外振幅 ───────────────────────────────────┐")
    print(f"  │ 在HVN外开盘: {len(results['outside_range'])}天")
    print(f"  │ 平均振幅: {avg_o:.2f}%")
    if results["hvn_range"]:
        diff = avg_o - avg_h
        print(f"  │ HVN外比HVN内大: {diff:+.2f}% ({"✅ 做T更好" if diff > 0 else "❌"})")
    print(f"  └──────────────────────────────────────────────────┘")

# 测试3: HVN目标到达
if results["hvn_target_reach"]:
    reach_pct = sum(1 for r in results["hvn_target_reach"] if r) / len(results["hvn_target_reach"]) * 100
    print(f"\n  ┌─ HVN目标到达率 ─────────────────────────────────┐")
    print(f"  │ {reach_pct:.0f}%的交易日到达最近HVN")
    print(f"  └──────────────────────────────────────────────────┘")

print()
