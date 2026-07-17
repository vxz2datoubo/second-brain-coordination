"""
真DDX回测 — 昆仑+蓝标, 使用WeStock fund flow数据
验证: t1-lockup / game-theory / money-flow 三大技能的可信度
无未来函数
"""

import json

# ============================================================
# 昆仑数据 (WeStock fund flow直接给我们的)
# ============================================================
kl_data = [
    ("2026-07-01", 40.60, 107901762, 51929764, 25655249, -133557011),
    ("2026-07-02", 45.55, 919214987, 995184148, -400637700, -518577286),
    ("2026-07-03", 42.66, -245788346, -287799580, 241210512, 4577833),
    ("2026-07-06", 43.05, 245104580, 197359793, -75758644, -169345936),
    ("2026-07-07", 44.61, 522755575, 504189733, -302151361, -220604214),
    ("2026-07-08", 47.96, 565569537, 658992303, -210628772, -354940764),
    ("2026-07-09", 50.42, 380405946, 396584435, -293021720, -87384226),
]
# fields: date, close, MainNetFlow(DDX), JumboNetFlow(DDY), MidNetFlow, SmallNetFlow

bl_data = [
    ("2026-07-01", 13.92, 82981605, 55872299, -72865527, -10116077),
    ("2026-07-02", 14.23, -44881765, 32587009, 167550055, -122668290),
    ("2026-07-03", 13.20, -791796749, -605834321, 35498257, 756298492),
    ("2026-07-04", 12.48, -395783703, -304100652, 11801326, 383982376),
    ("2026-07-07", 12.30, -167262788, -106219258, 31539800, 135722988),
    ("2026-07-08", 12.46, 21425735, -3343541, -22431107, 1005372),
    ("2026-07-09", 12.93, 170390028, 137949035, -38380399, -132009629),
]

# Note: 蓝标实际有1年数据，但这里展示的是7月样本
# 我们主要用昆仑来做全量验证

# ============================================================
# 构建完整K线+资金流数据 (昆仑1年 + 蓝标)
# ============================================================
# 从之前TDX K线获取价格数据 OHLCV
import glob
cache_dir = r"C:/Users/Administrator/.workbuddy/projects/f-aidanao/e4341908-6fb5-479b-913a-f9d578558264/tool-results"
all_files = sorted(glob.glob(f"{cache_dir}/mcp-connector-proxy-tdx-connector_tdx_kline-*.txt"))

def load_ohlcv(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for pattern in ['{\n  "Code"', '{"Code"', '\n{\n']:
        idx = content.find(pattern)
        if idx >= 0: break
    if idx < 0: return None, "?"
    raw = json.loads(content[idx:])
    code = raw.get("Code","?")
    bars = {}
    for r in raw["Rows"]:
        bars[r["Data"]] = {
            "o": float(r["Open"]), "h": float(r["High"]),
            "l": float(r["Low"]), "c": float(r["Close"]),
            "v": r["RawVolume"]
        }
    return bars, code

kl_ohlcv, _ = load_ohlcv(all_files[-1])
kl_combined = []
for d in sorted(kl_ohlcv.keys()):
    if d in kl_ohlcv:
        ohlcv = kl_ohlcv[d]
        kl_combined.append({
            "date": d, "c": ohlcv["c"], "o": ohlcv["o"],
            "h": ohlcv["h"], "l": ohlcv["l"], "v": ohlcv["v"],
            "ddx": None, "ddy": None, "mid": None, "small": None
        })

# Merge WeStock fund flow data
ws_dates = set()
for row in kl_data:
    d = row[0].replace("-","")  # "2026-07-01" → "20260701"
    ws_dates.add(d)
    for entry in kl_combined:
        if entry["date"] == d:
            entry["ddx"] = row[2]
            entry["ddy"] = row[3]
            entry["mid"] = row[4]
            entry["small"] = row[5]
            break

print(f"昆仑: {len(kl_combined)}条K线, {sum(1 for e in kl_combined if e['ddx'] is not None)}条有DDX数据")
print(f"DDX日期范围: {[e['date'] for e in kl_combined if e['ddx'] is not None]}")
print()

# ============================================================
# 验证1: OHLCV MF vs 真DDX 的相关性
# ============================================================
print("=" * 60)
print("【验证1】OHLCV代理MF指标 vs 真DDX的相关性")
print()

pairs = []
for i in range(1, len(kl_combined)):
    prev = kl_combined[i-1]
    curr = kl_combined[i]
    if curr["ddx"] is None: continue
    
    # OHLCV MF proxy (same as our backtest)
    rng = curr["h"] - curr["l"]
    if rng > 0.01:
        mf = ((curr["c"] - curr["l"]) - (curr["h"] - curr["c"])) / rng
    else:
        mf = 0
    
    # 真DDX = MainNetFlow / 当日成交额
    amt = curr["v"] * curr["c"] * 100  # approximate
    if amt > 0:
        true_ddx_pct = curr["ddx"] / amt
    else:
        true_ddx_pct = 0
    
    pairs.append((mf, true_ddx_pct, curr["date"]))

# 相关性
n = len(pairs)
if n > 1:
    mx = sum(p[0] for p in pairs)/n
    my = sum(p[1] for p in pairs)/n
    cov = sum((p[0]-mx)*(p[1]-my) for p in pairs)/n
    sx = (sum((p[0]-mx)**2 for p in pairs)/n)**0.5
    sy = (sum((p[1]-my)**2 for p in pairs)/n)**0.5
    corr = cov/(sx*sy) if sx>0 and sy>0 else 0
    print(f"OHLCV MF vs 真DDX 相关系数: {corr:.3f} ({n}天)")
    print(f"  解释力: R² = {corr**2:.3f}  → OHLCV代理能解释{corr**2*100:.0f}%的真DDX变异")
    print(f"  结论: {'✅ OHLCV保真度高' if corr > 0.7 else '⚠️ 中等相关' if corr > 0.4 else '❌ OHLCV代理不可靠'}")
    
    # 方向一致性
    same_dir = sum(1 for p in pairs if (p[0]>0)==(p[1]>0))
    print(f"  方向一致率: {same_dir}/{n} ({same_dir/n*100:.0f}%)")
    for p in pairs:
        sig = "✅" if (p[0]>0)==(p[1]>0) else "❌"
        print(f"    {p[2]} MF:{p[0]:+.2f} DDX:{p[1]*100:+.3f}% {sig}")
print()

# ============================================================
# 验证2: DDX方向 → 次日收益预测力
# ============================================================
print("=" * 60)
print("【验证2】真DDX方向对次日收益的预测力")
print()

ddx_pos = []
ddx_neg = []
for i in range(len(kl_combined)-1):
    curr = kl_combined[i]
    nxt = kl_combined[i+1]
    if curr["ddx"] is None: continue
    next_ret = (nxt["c"] - curr["c"]) / curr["c"]
    if curr["ddx"] > 0:
        ddx_pos.append(next_ret)
    else:
        ddx_neg.append(next_ret)

print(f"DDX正(主力净买): {len(ddx_pos)}天, 次日平均涨 {sum(ddx_pos)/len(ddx_pos)*100:+.2f}%")
print(f"DDX负(主力净卖): {len(ddx_neg)}天, 次日平均涨 {sum(ddx_neg)/len(ddx_neg)*100:+.2f}%")
print(f"预测力: {'✅ 正向' if sum(ddx_pos)/max(1,len(ddx_pos)) > sum(ddx_neg)/max(1,len(ddx_neg)) else '❌ 反向(说明T+1抛压更强)'}")

# 看看是不是大DDX天反而次日跌 (T+1解锁效应)
big_ddx = [(kl_combined[i]["ddx"]/1e8, (kl_combined[i+1]["c"]-kl_combined[i]["c"])/kl_combined[i]["c"]) 
           for i in range(len(kl_combined)-1) if kl_combined[i]["ddx"] is not None and kl_combined[i]["ddx"] > 5e8]
if big_ddx:
    print(f"\n大DDX日(>5亿): {len(big_ddx)}天, 次日平均涨 {sum(p[1] for p in big_ddx)/len(big_ddx)*100:+.2f}%")
    for p in big_ddx:
        print(f"  DDX {p[0]:.1f}亿 → 次日 {p[1]*100:+.2f}%")
print()

# ============================================================  
# 验证3: T+1解锁效应 - "今天主力买量大 → 次日散户卖压大"
# ============================================================
print("=" * 60)
print("【验证3】T+1解锁效应: 今日散户净买 vs 明日涨跌")
print()

small_pos = []
small_neg = []
for i in range(len(kl_combined)-1):
    curr = kl_combined[i]
    nxt = kl_combined[i+1]
    if curr["small"] is None: continue
    next_ret = (nxt["c"] - curr["c"]) / curr["c"]
    if curr["small"] > 0:
        small_pos.append(next_ret)
    else:
        small_neg.append(next_ret)

print(f"散户净买(小单净流入>0): {len(small_pos)}天, 次日平均涨 {sum(small_pos)/max(1,len(small_pos))*100:+.2f}%")
print(f"散户净卖(小单净流出>0): {len(small_neg)}天, 次日平均涨 {sum(small_neg)/max(1,len(small_neg))*100:+.2f}%")
print(f"理论预测: 散户今日买 → 明日解锁 → 跌")
print(f"实证: {'✅ T+1解锁效应存在' if sum(small_pos)/max(1,len(small_pos)) < sum(small_neg)/max(1,len(small_neg)) else '❌ 样本不足或无效应'}")
print()

# ============================================================
# 验证4: 坚定筹码比率 — 特大单+大单在总流中的占比
# ============================================================
print("=" * 60)
print("【验证4】坚定筹码比率 vs 未来走势")
print()

for i in range(len(kl_combined)):
    curr = kl_combined[i]
    if curr["ddx"] is None: continue
    if i >= len(kl_combined)-3: continue
    
    # 坚定筹码 = 特大单+大单
    firm = (curr["ddy"] + curr["ddx"]) if curr["ddy"] and curr["ddx"] else None
    loose = abs(curr["small"]) + abs(curr["mid"])
    total = firm + loose if firm else None
    firm_ratio = firm / total * 100 if total and total > 0 else None
    
    ret3 = (kl_combined[i+3]["c"] - curr["c"]) / curr["c"] if i+3 < len(kl_combined) else 0
    
    if firm_ratio:
        tag = "✅稳健" if ret3 > 0 else "⚠️下跌"
        print(f"  {curr['date']} 坚定度{firm_ratio:.0f}% → 3日后{ret3*100:+.1f}% {tag}")
