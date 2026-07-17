"""
A股博弈论技能验证 — 操纵概率评分系统回测
使用昆仑 1年数据检验: 高分(>60)后是否真的下跌
"""
import json, sys, math, glob

# Load data
files = sorted(glob.glob(r"C:/Users/Administrator/.workbuddy/projects/f-aidanao/e4341908-6fb5-479b-913a-f9d578558264/tool-results/mcp-connector-proxy-tdx-connector_tdx_kline-*.txt"))
path = files[-1]
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
for pattern in ['{\n  "Code"', '{"Code"', '\n{\n']:
    idx = content.find(pattern)
    if idx >= 0: break
raw = json.loads(content[idx:])
bars = []
for r in raw["Rows"]:
    bars.append({
        "date": r["Data"],
        "open": float(r["Open"]), "high": float(r["High"]),
        "low": float(r["Low"]), "close": float(r["Close"]),
        "vol": r["RawVolume"]
    })

N = len(bars)
for i in range(1, N):
    bars[i]["ret"] = (bars[i]["close"] - bars[i-1]["close"]) / bars[i-1]["close"]

print("博弈论操纵预警回测 — 昆仑万维 1年数据")
print()

# Proxy indicators (all using only known data)
alerts = []
for i in range(20, N-5):
    score = 0
    
    # 量价背离: 放量滞涨 (量比>2, 涨幅<1%)
    avg_v = sum(bars[j]["vol"] for j in range(i-5, i)) / 5
    vol_ratio = bars[i]["vol"] / max(1, avg_v)
    if vol_ratio > 2 and bars[i]["ret"] < 0.01:
        score += 20
    
    # 非对称成交: 收在低区 + 大量 = 可能是在出货
    rng = bars[i]["high"] - bars[i]["low"]
    if rng > 0.01:
        pos = (bars[i]["close"] - bars[i]["low"]) / rng
        if pos < 0.35 and vol_ratio > 1.5:
            score += 20
    
    # 尾盘异动proxy: 开盘收低但收盘拉回+量小
    o2c = (bars[i]["close"] - bars[i]["open"]) / bars[i]["open"]
    if o2c > 0.03 and vol_ratio < 0.7:
        score += 15  # 拉尾盘可疑
    
    # 极端高换手
    hsl = bars[i]["vol"] / 1175323980.0 * 100
    if hsl > 20:
        score += 15
    
    # 浮盈过大
    pct5 = (bars[i]["close"] - bars[max(0,i-5)]["close"]) / bars[max(0,i-5)]["close"]
    if pct5 > 0.15:
        score += 15
    
    # 连续涨后量缩
    if pct5 > 0.10 and vol_ratio < 0.5:
        score += 10
    
    # 记录
    if score >= 30:
        alerts.append({
            "date": bars[i]["date"],
            "score": score,
            "price": bars[i]["close"],
            "ret5d": (bars[min(i+5, N-1)]["close"] - bars[i]["close"]) / bars[i]["close"]
        })

print(f"预警阈值: ≥30分 → {len(alerts)} 个信号")
print()

# Group by score
hi = [a for a in alerts if a["score"] >= 50]
med = [a for a in alerts if 30 <= a["score"] < 50]

if hi:
    print(f"🚨 高分(≥50): {len(hi)}个")
    rets = [a["ret5d"] for a in hi]
    print(f"   5日后平均收益: {sum(rets)/len(rets)*100:.1f}%")
    print(f"   正收益占比: {sum(1 for r in rets if r>0)/len(rets)*100:.0f}%")
    for a in hi[-5:]:
        s = "✅跌了" if a["ret5d"] < -0.02 else "❌没跌" if a["ret5d"] < 0 else "🔥反而涨了"
        print(f"   {a['date']} 评分{a['score']} {a['ret5d']*100:+.1f}% {s}")
    print()

if med:
    print(f"⚠️ 中等(30-49): {len(med)}个")
    rets = [a["ret5d"] for a in med]
    print(f"   5日后平均收益: {sum(rets)/len(rets)*100:.1f}%")
    print(f"   正收益占比: {sum(1 for r in rets if r>0)/len(rets)*100:.0f}%")
    print()

# Baserate
all_rets = []
for i in range(20, N-5):
    ret5 = (bars[i+5]["close"] - bars[i]["close"]) / bars[i]["close"]
    all_rets.append(ret5)
base_mean = sum(all_rets)/len(all_rets)
print(f"随机5日收益均值: {base_mean*100:.2f}%")
print(f"操纵预警反向预测力: {'✅ 有效' if sum(a['ret5d'] for a in alerts)/len(alerts) < base_mean else '❌ 不足'}")
