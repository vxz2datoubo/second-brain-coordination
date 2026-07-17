"""
Money Flow Warfare 策略回测 — 昆仑万维 300418 1年数据
无未来函数，只用已知数据做决策
"""

import json, math, re

# Load data — file has metadata before JSON
path = r"C:/Users/Administrator/.workbuddy/projects/f-aidanao/e4341908-6fb5-479b-913a-f9d578558264/tool-results/mcp-connector-proxy-tdx-connector_tdx_kline-1783611208300-9c8254.txt"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Find JSON start
idx = content.find('{\n  "Code"')
if idx < 0:
    idx = content.find('{"Code"')
raw = json.loads(content[idx:])

rows = raw["Rows"]
stats = raw["Stats"]
print(f"数据: {stats['StartDate']} ~ {stats['EndDate']}, {len(rows)}根K线")
print(f"区间涨幅: {stats['IntervalChangePercent']:.2f}%, 最高: {stats['MaxHigh']}, 最低: {stats['MinLow']}")
print()

# === 指标构建 (全部基于当日已发生数据，无未来函数) ===

records = []
for r in rows:
    o, h, l, c = float(r["Open"]), float(r["High"]), float(r["Low"]), float(r["Close"])
    vol = r["RawVolume"]
    
    # Money Flow Multiplier: ((C-L)-(H-C))/(H-L)
    if abs(h - l) < 0.001:
        mf_mult = 0
    else:
        mf_mult = ((c - l) - (h - c)) / (h - l)
    
    records.append({
        "date": r["Data"],
        "open": o, "high": h, "low": l, "close": c,
        "vol": vol,
        "mf_mult": mf_mult,       # -1 to +1, 正=买压主导
        "pct_chg": 0
    })

for i in range(1, len(records)):
    records[i]["pct_chg"] = (records[i]["close"] - records[i-1]["close"]) / records[i-1]["close"]

# === 回测引擎 ===

def backtest(name, buy_fn, sell_fn, records, warmup=20, max_pos=0.95):
    cash = 1_000_000
    shares = 0
    trades = []
    equity = []
    
    for i in range(warmup, len(records)):
        price = records[i]["close"]
        known = records[:i+1]
        
        if shares == 0 and buy_fn(known, i):
            shares = int(cash * max_pos / (price * 1.0005))
            cost = shares * price * 1.0005
            cash -= cost
            trades.append({"type": "BUY", "date": records[i]["date"], "price": price, "shares": shares, "cost": cost})
        
        elif shares > 0 and sell_fn(known, i):
            revenue = shares * price * 0.9995
            pnl = revenue - trades[-1]["cost"]
            trades.append({"type": "SELL", "date": records[i]["date"], "price": price, "pnl": pnl, "pnl_pct": pnl / trades[-1]["cost"]})
            cash = revenue
            shares = 0
        
        equity.append({"date": records[i]["date"], "eq": cash + shares * price, "px": price})
    
    if shares > 0:
        revenue = shares * records[-1]["close"] * 0.9995
        pnl = revenue - trades[-1]["cost"]
        trades.append({"type": "CLOSE", "date": records[-1]["date"], "pnl": pnl, "pnl_pct": pnl / trades[-1]["cost"]})
    
    final_eq = equity[-1]["eq"]
    ret = (final_eq - 1_000_000) / 1_000_000
    bh_ret = (records[-1]["close"] - records[warmup]["close"]) / records[warmup]["close"]
    
    closed = [t for t in trades if t["type"] in ("SELL", "CLOSE")]
    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] <= 0]
    wr = len(wins) / max(1, len(closed))
    aw = sum(t["pnl_pct"] for t in wins) / max(1, len(wins)) if wins else 0
    al = sum(t["pnl_pct"] for t in losses) / max(1, len(losses)) if losses else 0
    
    peak = 1_000_000
    mdd = 0
    for e in equity:
        if e["eq"] > peak:
            peak = e["eq"]
        dd = (peak - e["eq"]) / peak
        if dd > mdd:
            mdd = dd
    
    # Sharpe (daily, simplified)
    days = len(equity)
    if days > 1:
        daily_rets = [(equity[j]["eq"]/equity[j-1]["eq"]-1) for j in range(1, days)]
        if daily_rets:
            mean_dr = sum(daily_rets) / len(daily_rets)
            std_dr = (sum((r-mean_dr)**2 for r in daily_rets) / len(daily_rets)) ** 0.5
            sharpe = mean_dr / std_dr * (252**0.5) if std_dr > 0 else 0
        else:
            sharpe = 0
    else:
        sharpe = 0
    
    return {
        "name": name, "ret": ret, "bh_ret": bh_ret,
        "n_trades": len([t for t in trades if t["type"] == "BUY"]),
        "wr": wr, "aw": aw, "al": al, "mdd": mdd, "sharpe": sharpe,
        "equity": equity, "trades": [t for t in trades if t["type"] in ("SELL","CLOSE")]
    }


# === 策略1: MF连续3日正→买入，连续2日负→卖出 ===
def s1_buy(d, i):
    if i < 3: return False
    return d[i]["mf_mult"] > 0.15 and d[i-1]["mf_mult"] > 0.05 and d[i-2]["mf_mult"] > 0.05

def s1_sell(d, i):
    if i < 2: return False
    return d[i]["mf_mult"] < -0.15 and d[i-1]["mf_mult"] < -0.05

# === 策略2: 放量突破→买入，放量破位→卖出 ===
def s2_buy(d, i):
    if i < 20: return False
    avg_v = sum(r["vol"] for r in d[i-20:i]) / 20
    return d[i]["pct_chg"] > 0.02 and d[i]["vol"] > avg_v * 1.5

def s2_sell(d, i):
    if i < 20: return False
    avg_v = sum(r["vol"] for r in d[i-20:i]) / 20
    return d[i]["pct_chg"] < -0.02 and d[i]["vol"] > avg_v * 1.5

# === 策略3: "合力"信号——价格在高位收+放量+收在区间上2/3 ===
def s3_buy(d, i):
    if i < 10: return False
    # 5日趋势向上
    up5 = d[i]["close"] > d[max(0,i-5)]["close"] * 1.01
    avg_v = sum(r["vol"] for r in d[max(0,i-10):i]) / min(10, i)
    vol_ok = d[i]["vol"] > avg_v * 1.3
    rng = d[i]["high"] - d[i]["low"]
    if rng < 0.01: return False
    pos = (d[i]["close"] - d[i]["low"]) / rng
    return up5 and vol_ok and pos > 0.7 and d[i]["pct_chg"] > 0

def s3_sell(d, i):
    if i < 10: return False
    avg_v = sum(r["vol"] for r in d[max(0,i-10):i]) / min(10, i)
    vol_ok = d[i]["vol"] > avg_v * 1.3
    rng = d[i]["high"] - d[i]["low"]
    if rng < 0.01: return False
    pos = (d[i]["close"] - d[i]["low"]) / rng
    # 放量+收低+跌 = 放量滞涨/出货
    return vol_ok and pos < 0.35 and d[i]["pct_chg"] < 0

# === 策略4: 综合"蚕食模式"——连续3天DDX式信号累积 ===
def s4_buy(d, i):
    if i < 5: return False
    # 5天内至少3天MF为正且价格创新高
    pos_days = sum(1 for j in range(max(0,i-4), i+1) if d[j]["mf_mult"] > 0)
    making_highs = d[i]["close"] > d[max(0,i-5)]["close"]
    return pos_days >= 3 and making_highs

def s4_sell(d, i):
    if i < 5: return False
    # 连续3天MF为负
    if i < 3: return False
    neg_streak = all(d[i-j]["mf_mult"] < -0.05 for j in range(3))
    return neg_streak


strategies = [
    ("1-MF3日正买/2日负卖", s1_buy, s1_sell),
    ("2-放量突破买/破位卖", s2_buy, s2_sell),
    ("3-合力信号买/滞涨卖", s3_buy, s3_sell),
    ("4-蚕食模式买/连续负卖", s4_buy, s4_sell),
]

print(f"{'策略':<30} {'总收益':>7} {'B&H':>7} {'超额':>7} {'胜率':>6} {'最大回撤':>8} {'夏普':>6} {'笔数':>4}")
print("-" * 90)

for name, bfn, sfn in strategies:
    r = backtest(name, bfn, sfn, records)
    print(f"{r['name']:<30} {r['ret']*100:>6.1f}% {r['bh_ret']*100:>6.1f}% {r['ret']*100-r['bh_ret']*100:>6.1f}% {r['wr']*100:>5.0f}% {r['mdd']*100:>7.1f}% {r['sharpe']:>5.2f} {r['n_trades']:>4}")
    
    # Show last 3 trades
    for t in r["trades"][-3:]:
        s = "✅" if t["pnl"] > 0 else "❌"
        print(f"  {t['date']} {s} {t['pnl_pct']*100:+.1f}%")

print("-" * 90)

# Best strategy recap
best = max(strategies, key=lambda s: backtest(s[0], s[1], s[2], records)["ret"])
r_best = backtest(best[0], best[1], best[2], records)
print(f"\n最佳策略: {best[0]} (年化超额: {r_best['ret']*100-r_best['bh_ret']*100:.1f}%)")

# === 关键验证: 合力信号是否有预测力 ===
print("\n" + "=" * 60)
print("关键假设验证: MF方向=资金合力=未来收益预测力")
print()

# 将所有交易日的MF信号和次日涨跌配对
signals = []
for i in range(20, len(records)-1):
    mf_today = records[i]["mf_mult"]
    ret_next = records[i+1]["pct_chg"]
    signals.append({"mf": mf_today, "next_ret": ret_next})

pos_signals = [s for s in signals if s["mf"] > 0.15]
neg_signals = [s for s in signals if s["mf"] < -0.15]
neutral = [s for s in signals if -0.15 <= s["mf"] <= 0.15]

print(f"MF > 0.15 (强买压): {len(pos_signals)}天, 次日平均涨: {sum(s['next_ret'] for s in pos_signals)/len(pos_signals)*100:.2f}%")
print(f"MF < -0.15 (强卖压): {len(neg_signals)}天, 次日平均涨: {sum(s['next_ret'] for s in neg_signals)/len(neg_signals)*100:.2f}%")
print(f"MF中性:         {len(neutral)}天, 次日平均涨: {sum(s['next_ret'] for s in neutral)/len(neutral)*100:.2f}%")
print()
print(f"结论: MF信号 {'✅ 有预测力' if sum(s['next_ret'] for s in pos_signals)/len(pos_signals) > sum(s['next_ret'] for s in neg_signals)/len(neg_signals) else '❌ 预测力不足'}")
print(f"      强买压次日平均 > 强卖压次日平均? {'是' if sum(s['next_ret'] for s in pos_signals)/len(pos_signals) > sum(s['next_ret'] for s in neg_signals)/len(neg_signals) else '否'}")
