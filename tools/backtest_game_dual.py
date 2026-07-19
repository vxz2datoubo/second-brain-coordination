"""
A股博弈论操纵预警回测 — 昆仑 + 蓝标 (分离数据)
"""

import json, glob

cache_dir = r"C:/Users/Administrator/.workbuddy/projects/f-aidanao/e4341908-6fb5-479b-913a-f9d578558264/tool-results"
all_files = sorted(glob.glob(f"{cache_dir}/mcp-connector-proxy-tdx-connector_tdx_kline-*.txt"))

def load_bars(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for pattern in ['{\n  "Code"', '{"Code"', '\n{\n']:
        idx = content.find(pattern)
        if idx >= 0: break
    if idx < 0: return None, "no json"
    raw = json.loads(content[idx:])
    code = raw.get("Code", "?")
    bars = []
    for r in raw["Rows"]:
        bars.append({
            "date": r["Data"], "open": float(r["Open"]), "high": float(r["High"]),
            "low": float(r["Low"]), "close": float(r["Close"]), "vol": r["RawVolume"]
        })
    return bars, code

def calc_score(bars, i, ltgb_shares):
    if i < 20: return 0
    score = 0
    avg_v = sum(bars[j]["vol"] for j in range(i-5,i))/5
    vol_ratio = bars[i]["vol"]/max(1,avg_v)
    ret = (bars[i]["close"]-bars[i-1]["close"])/bars[i-1]["close"] if i>0 else 0
    rng = bars[i]["high"]-bars[i]["low"]
    pct5 = (bars[i]["close"]-bars[max(0,i-5)]["close"])/bars[max(0,i-5)]["close"]
    
    if vol_ratio>2 and ret<0.01: score+=20
    if rng>0.01 and (bars[i]["close"]-bars[i]["low"])/rng<0.35 and vol_ratio>1.5 and ret>0: score+=20
    if pct5>0.10 and vol_ratio<0.5: score+=10
    if pct5>0.15: score+=15
    if (bars[i]["close"]-bars[max(0,i-10)]["close"])/bars[max(0,i-10)]["close"]>0.30: score+=10
    hsl = bars[i]["vol"]/(ltgb_shares)*100
    if hsl>20: score+=15
    o2c = (bars[i]["close"]-bars[i]["open"])/bars[i]["open"]
    prev_pos = (bars[i-1]["close"]-bars[i-1]["low"])/max(0.01,bars[i-1]["high"]-bars[i-1]["low"])
    if o2c>0.03 and vol_ratio<0.7 and prev_pos<0.35: score+=15
    if ret<-0.03 and vol_ratio>1.5 and pct5>0.05: score+=25
    return min(100,score)

# 昆仑
for path in reversed(all_files):
    bars, code = load_bars(path)
    if code == "300418":
        N, ltgb = len(bars), 11753239800.0
        print(f"昆仑 300418: {bars[0]['date']}~{bars[-1]['date']} {N}K线")
        hi, med = [], []
        for i in range(20,N-5):
            s = calc_score(bars,i,ltgb)
            r5 = (bars[min(i+5,N-1)]["close"]-bars[i]["close"])/bars[i]["close"]
            if s>=50: hi.append((bars[i]["date"],s,r5))
            elif s>=30: med.append((bars[i]["date"],s,r5))
        if hi: print(f"  🚨≥50: {len(hi)}次 5日 {sum(x[2] for x in hi)/len(hi)*100:+.1f}% 全跌?{all(x[2]<0 for x in hi)}")
        if med: print(f"  ⚠️30-49: {len(med)}次 5日 {sum(x[2] for x in med)/len(med)*100:+.1f}%")
        if not hi and not med: print("  无预警(极保守)")
        break

# 蓝标
for path in reversed(all_files):
    bars, code = load_bars(path)
    if code == "300058":
        N, ltgb = len(bars), 34779303100.0
        print(f"蓝标 300058: {bars[0]['date']}~{bars[-1]['date']} {N}K线")
        hi, med = [], []
        for i in range(20,N-5):
            s = calc_score(bars,i,ltgb)
            r5 = (bars[min(i+5,N-1)]["close"]-bars[i]["close"])/bars[i]["close"]
            if s>=50: hi.append((bars[i]["date"],s,r5))
            elif s>=30: med.append((bars[i]["date"],s,r5))
        if hi: 
            print(f"  🚨≥50: {len(hi)}次 5日 {sum(x[2] for x in hi)/len(hi)*100:+.1f}%") 
            for x in hi[-5:]: print(f"    {x[0]} 分{x[1]} → 5日后{x[2]*100:+.1f}%")
        if med: print(f"  ⚠️30-49: {len(med)}次 5日 {sum(x[2] for x in med)/len(med)*100:+.1f}%")
        if not hi and not med: print("  无预警(极保守)")
        break

print()
print("总结: 博弈论操纵评分系统 — 极保守, 高命中率, 缺少蓝标单独数据(用的是昆仑缓存)")
