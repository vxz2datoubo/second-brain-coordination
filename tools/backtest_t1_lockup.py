"""
t1-lockup-tracking 技能回测
验证: 换手衰减/隔夜折价/盈亏敏感/筹码坚定度各引擎的预测力
无未来函数: 所有信号使用当日或之前已公开数据
"""

import json, math, sys

# ============================================================
# 数据加载
# ============================================================
import glob
files = sorted(glob.glob(r"C:/Users/Administrator/.workbuddy/projects/f-aidanao/e4341908-6fb5-479b-913a-f9d578558264/tool-results/mcp-connector-proxy-tdx-connector_tdx_kline-*.txt"))
path = files[-1] if files else None
if not path:
    print("No data file found"); sys.exit(1)
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
idx = content.find('{\n  "Code"')
if idx < 0:
    idx = content.find('{"Code"')
if idx < 0:
    idx = content.find('\n{\n') + 1  # JSON starts with standalone {
raw = json.loads(content[idx:])
rows = raw["Rows"]

bars = []
for r in rows:
    bars.append({
        "date": r["Data"],
        "open": float(r["Open"]), "high": float(r["High"]),
        "low": float(r["Low"]), "close": float(r["Close"]),
        "vol": r["RawVolume"],
        "amt": r["RawAmount"]
    })

N = len(bars)
print(f"数据: {bars[0]['date']} ~ {bars[-1]['date']}, {N} 根K线")
print()

# ============================================================
# 指标构建 (全用当日已知数据)
# ============================================================

# 换手率(千手 → 换手%)
ltgb = 117532.398  # 流通股本(万股)
for b in bars:
    b["hsl"] = (b["vol"] / (ltgb * 10000)) * 100  # %

# 各日收益
for i in range(1, N):
    b = bars[i]
    prev = bars[i-1]
    b["ret"] = (b["close"] - prev["close"]) / prev["close"]           # 日内收益
    b["ret_overnight"] = (b["open"] - prev["close"]) / prev["close"]  # 隔夜收益
    b["ret_intraday"] = (b["close"] - b["open"]) / b["open"]          # 开盘后收益

# 换手率变化 (需要的窗口)
for i in range(5, N):
    hsl_now = bars[i]["hsl"]
    hsl_ma5 = sum(bars[j]["hsl"] for j in range(i-5, i)) / 5
    bars[i]["hsl_ratio"] = hsl_now / max(0.1, hsl_ma5)  # 相对5日均值
    
    hsl_ma20 = sum(bars[j]["hsl"] for j in range(max(0,i-20), i)) / min(20, i)
    bars[i]["hsl_decay"] = hsl_ma5 / max(0.1, hsl_ma20)  # 换手衰减: 5日 vs 20日

# MA/VWAP proxy
for i in range(5, N):
    bars[i]["ma5"] = sum(bars[j]["close"] for j in range(i-5, i)) / 5
    bars[i]["ma20"] = sum(bars[j]["close"] for j in range(max(0,i-20), i)) / min(20, i)
    bars[i]["pct_from_ma5"] = (bars[i]["close"] - bars[i]["ma5"]) / bars[i]["ma5"]  # 浮盈幅度
    bars[i]["pct_from_ma20"] = (bars[i]["close"] - bars[i]["ma20"]) / bars[i]["ma20"]

# 成交量代理: "量价和谐度"
for i in range(5, N):
    vol_now = bars[i]["vol"]
    vol_ma5 = sum(bars[j]["vol"] for j in range(i-5, i)) / 5
    bars[i]["vol_ratio"] = vol_now / max(1, vol_ma5)
    
    # 放量上涨=+1, 放量下跌=-1, 缩量=0
    vol_ratio = bars[i]["vol_ratio"]
    if bars[i]["ret"] > 0.01 and vol_ratio > 1.5:
        bars[i]["eff_res"] = 1   # 和谐放量涨
    elif bars[i]["ret"] < -0.01 and bars[i]["vol_ratio"] > 1.5:
        bars[i]["eff_res"] = -1  # 放量跌
    else:
        bars[i]["eff_res"] = 0

# 综合信号: "筹码坚定度" 代理
# = 换手衰减(正分) + 趋势上(正分) - 浮盈过高(负分)
for i in range(20, N):
    score = 0
    
    # 换手衰减: <1=衰减中(好), >1=放大中(差)
    if bars[i].get("hsl_decay", 1) < 0.7:
        score += 2
    elif bars[i].get("hsl_decay", 1) < 1.0:
        score += 1
    else:
        score -= 1
    
    # 趋势: 5日涨幅
    ret5 = (bars[i]["close"] - bars[max(0,i-5)]["close"]) / bars[max(0,i-5)]["close"]
    if ret5 > 0.05:
        score += 2
    elif ret5 > 0:
        score += 1
    else:
        score -= 1
    
    # 浮盈幅度: 太高=不坚定筹码想走
    pct5 = bars[i].get("pct_from_ma5", 0)
    if pct5 > 0.10:
        score -= 2  # 短期涨10%+，不坚定想走
    elif pct5 > 0.05:
        score -= 1
    elif pct5 > 0:
        score += 1
    
    bars[i]["firm_score"] = score  # -4 到 +5


# ============================================================
# 核心验证 1: T+1 折价理论
# ============================================================
print("=" * 60)
print("【验证1】T+1 隔夜折价: 隔夜收益是否系统性为负？")
print()

valid_bars = [b for b in bars[1:] if "ret_overnight" in b]
on_returns = [b["ret_overnight"] for b in valid_bars]
id_returns = [b["ret_intraday"] for b in valid_bars]

on_mean = sum(on_returns) / len(on_returns)
id_mean = sum(id_returns) / len(id_returns)
on_pos = sum(1 for r in on_returns if r > 0) / len(on_returns)
id_pos = sum(1 for r in id_returns if r > 0) / len(id_returns)

print(f"隔夜收益(昨收→今开): 均值 {on_mean*100:.3f}%  正比例 {on_pos*100:.0f}%")
print(f"日内收益(今开→今收): 均值 {id_mean*100:.3f}%  正比例 {id_pos*100:.0f}%")
print(f"结论: 隔夜系统性为负? {'✅ 是' if on_mean < 0 else '❌ 否'}  (北大论文预测 -0.09%)")
print()

# 隔夜 vs 日内反转检测
# "今天日内涨 → 明天隔夜跌" 的相关性
rev_pairs = []
for i in range(2, N):
    today_id = bars[i-1].get("ret_intraday", 0)
    tomorrow_on = bars[i].get("ret_overnight", 0)
    rev_pairs.append((today_id, tomorrow_on))

# 分组: 今天日内涨 vs 跌
up_today = [p for p in rev_pairs if p[0] > 0.005]
dn_today = [p for p in rev_pairs if p[0] < -0.005]
print("反转检测: 今天日内涨 → 明天隔夜?")
print(f"  今天日内涨>0.5%: {len(up_today)}天, 次日隔夜均值 {sum(p[1] for p in up_today)/max(1,len(up_today))*100:.3f}%")
print(f"  今天日内跌>0.5%: {len(dn_today)}天, 次日隔夜均值 {sum(p[1] for p in dn_today)/max(1,len(dn_today))*100:.3f}%")
print(f"  反转效应: {'✅ 存在' if (sum(p[1] for p in up_today)/max(1,len(up_today))) < (sum(p[1] for p in dn_today)/max(1,len(dn_today))) else '❌ 不存在或微'}弱")


# ============================================================
# 核心验证 2: 换手衰减 → 未来收益
# ============================================================
print()
print("=" * 60)
print("【验证2】换手率衰减是否预示筹码集中→未来上涨？")
print()

def test_signal_forward(name, signal_fn, bars, start=20, horizon=5):
    """测试信号对未来N日收益的预测力"""
    sig_high = []
    sig_low = []
    
    for i in range(start, N - horizon):
        val = signal_fn(bars, i)
        if val is None:
            continue
        fwd_ret = (bars[i+horizon]["close"] - bars[i]["close"]) / bars[i]["close"]
        
        if val > 0:
            sig_high.append(fwd_ret)
        else:
            sig_low.append(fwd_ret)
    
    if not sig_high or not sig_low:
        return None
    
    h_mean = sum(sig_high) / len(sig_high)
    l_mean = sum(sig_low) / len(sig_low)
    h_pos = sum(1 for r in sig_high if r > 0) / len(sig_high)
    l_pos = sum(1 for r in sig_low if r > 0) / len(sig_low)
    
    return {
        "name": name,
        "h_mean": h_mean, "l_mean": l_mean, "diff": h_mean - l_mean,
        "h_pos": h_pos, "l_pos": l_pos,
        "h_n": len(sig_high), "l_n": len(sig_low),
        "horizon": horizon
    }

# 测试各个信号
tests = []

# 2a: 换手衰减 < 1.0 → 换手在降 → 筹码集中 → 应该涨
for h in [1, 3, 5, 10]:
    def hsl_decay_signal(b, i):
        if "hsl_decay" not in b[i]: return None
        return 1 if b[i]["hsl_decay"] < 0.8 else -1
    r = test_signal_forward(f"换手衰减<0.8 (前{h}日)", hsl_decay_signal, bars, horizon=h)
    if r:
        tests.append(r)

# 2b: 筹码坚定度评分 > 2 → 应该涨
for h in [1, 3, 5, 10]:
    def firm_score_signal(b, i):
        if "firm_score" not in b[i]: return None
        return 1 if b[i]["firm_score"] >= 2 else -1
    r = test_signal_forward(f"坚定度≥2 (前{h}日)", firm_score_signal, bars, horizon=h)
    if r:
        tests.append(r)

# 2c: 放量上涨(和谐) → 应该涨
for h in [1, 3, 5]:
    def eff_res_signal(b, i):
        if "eff_res" not in b[i]: return None
        return 1 if b[i]["eff_res"] == 1 else -1 if b[i]["eff_res"] == -1 else None
    r = test_signal_forward(f"放量涨 (前{h}日)", eff_res_signal, bars, horizon=h)
    if r:
        tests.append(r)

# 2d: 浮盈过高 → 次日跌 (不坚定筹码走)
for h in [1]:
    def overbought_signal(b, i):
        if "pct_from_ma5" not in b[i]: return None
        return -1 if b[i]["pct_from_ma5"] > 0.05 else 1
    r = test_signal_forward(f"浮盈>5% (前{h}日)", overbought_signal, bars, horizon=h)
    if r:
        tests.append(r)

# 打印结果
print(f"{'信号':<30} {'多头均值':>8} {'空头均值':>8} {'差值':>8} {'多胜率':>7} {'空胜率':>7} {'置信'}")
print("-" * 85)
for t in tests:
    if t is None: continue
    conf = "✅强" if t["diff"] > 0.01 and t["h_pos"] > 0.5 else "✅弱" if t["diff"] > 0 else "❌反" if t["diff"] < -0.01 else "⚪平"
    print(f"{t['name']:<30} {t['h_mean']*100:>7.2f}% {t['l_mean']*100:>7.2f}% {t['diff']*100:>7.2f}% {t['h_pos']*100:>6.0f}% {t['l_pos']*100:>6.0f}%  {conf}")
print()


# ============================================================  
# 核心验证 3: 策略回测 (无未来函数)
# ============================================================
print("=" * 60)
print("【验证3】完整策略回测: 筹码坚定度策略 vs Buy & Hold")
print()

def backtest_strat(name, buy_fn, sell_fn, bars, warmup=20, commission=0.0005):
    cash = 1_000_000
    shares = 0
    trades = []
    equity_curve = []
    
    for i in range(warmup, len(bars)):
        price = bars[i]["close"]
        
        if shares == 0 and buy_fn(bars, i):
            shares = int(cash * 0.95 / (price * 1.0005))
            cost = shares * price * 1.0005
            cash -= cost
            trades.append({"type": "BUY", "date": bars[i]["date"], "px": price, "sh": shares, "cost": cost})
        elif shares > 0 and sell_fn(bars, i):
            rev = shares * price * 0.9995
            pnl = rev - trades[-1]["cost"]
            trades.append({"type": "SELL", "date": bars[i]["date"], "px": price, "pnl": pnl})
            cash = rev
            shares = 0
        
        equity_curve.append(cash + shares * price)
    
    if shares > 0:
        rev = shares * bars[-1]["close"] * 0.9995
        pnl = rev - trades[-1]["cost"]
        trades.append({"type": "CLOSE", "pnl": pnl})
    
    final_eq = equity_curve[-1]
    ret = (final_eq - 1_000_000) / 1_000_000
    bh_ret = (bars[-1]["close"] - bars[warmup]["close"]) / bars[warmup]["close"]
    
    closed = [t for t in trades if t["type"] in ("SELL","CLOSE")]
    wins = [t for t in closed if t["pnl"] > 0]
    wr = len(wins) / max(1, len(closed))
    
    # 最大回撤
    peak = 1_000_000
    mdd = 0
    for eq in equity_curve:
        if eq > peak: peak = eq
        dd = (peak - eq) / peak
        if dd > mdd: mdd = dd
    
    return {
        "name": name, "ret": ret, "bh": bh_ret, "n": len([t for t in trades if t["type"]=="BUY"]),
        "wr": wr, "mdd": mdd, "closed": closed
    }

# 策略: 筹码坚定度≥3 买入, 坚定度≤0 卖出
def firm_buy(b, i):
    if "firm_score" not in b[i]: return False
    return b[i]["firm_score"] >= 2

def firm_sell(b, i):
    if "firm_score" not in b[i]: return False
    return b[i]["firm_score"] <= -1

# 策略: 换手衰减 买入, 换手放大 卖出
def decay_buy(b, i):
    if "hsl_decay" not in b[i]: return False
    return b[i]["hsl_decay"] < 0.7

def decay_sell(b, i):
    if "hsl_decay" not in b[i]: return False
    return b[i]["hsl_decay"] > 1.3

# 策略: 浮盈过高=卖出
def overbought_sell(b, i):
    if "pct_from_ma5" not in b[i]: return False
    return b[i]["pct_from_ma5"] > 0.15

strategies = [
    ("筹码坚定度≥2进, ≤-1出", firm_buy, firm_sell),
    ("换手衰减<0.7进, >1.3出", decay_buy, decay_sell),
    ("坚定度≥2进, 浮盈>15%出", firm_buy, overbought_sell),
]

print(f"{'策略':<35} {'收益':>7} {'B&H':>7} {'超额':>7} {'胜率':>6} {'回撤':>7} {'笔数':>4}")
print("-" * 90)
for name, bf, sf in strategies:
    r = backtest_strat(name, bf, sf, bars)
    x = f"{r['ret']*100:>6.1f}% {r['bh']*100:>6.1f}% {r['ret']*100-r['bh']*100:>6.1f}% {r['wr']*100:>5.0f}% {r['mdd']*100:>6.1f}% {r['n']:>4}"
    print(f"{name:<35} {x}")
    
    for t in r["closed"][-3:]:
        s = "✅" if t["pnl"]>0 else "❌"
        print(f"  {t.get('date',''):12} {s} {t['pnl']/10000:+.1f}万")

print("-" * 90)

# ============================================================
# 总结
# ============================================================
print()
print("=" * 60)
print("技能可信度总结")
print()

excess_tests = [t for t in tests if t and t["diff"] > 0.01 and t["h_pos"] > 0.5]
weak_tests = [t for t in tests if t and t["diff"] > 0]
reverse_tests = [t for t in tests if t and t["diff"] < -0.01]

print(f"验证项: {len(tests)} 个信号测试")
print(f"正向预测力: {len(excess_tests)} 个 ({len(excess_tests)/max(1,len(tests))*100:.0f}%)")
print(f"弱正向/不显著: {len(weak_tests)-len(excess_tests)} 个")
print(f"反向预测力: {len(reverse_tests)} 个")
print()

if len(excess_tests) >= len(tests) * 0.5:
    print("✅ 技能核心逻辑可信度高 (>50% 信号有正向预测力)")
elif len(weak_tests) >= len(tests) * 0.6:
    print("🟡 技能有部分有效性，但信号不够强")
else:
    print("⚠️ 技能信号预测力不足，需进一步优化或补充DDX数据")
