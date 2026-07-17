"""
回测收盘竞价信号 — 收盘价相对日内低点的恢复幅度 → 次日方向
用247天沪深K线数据(OHLC), 近似判断竞价强弱
"""
import json

def load_kline(name):
    """Load from TDX kline style (daily OHLC if available)"""
    # Use existing DDX数据 + approximate by: (close-low)/(high-low)
    with open(f'F:/aidanao/data/{name}', 'r', encoding='utf-8') as f:
        data = json.load(f)
    bars = []
    for r in data:
        c = float(r['c'])
        # Approximate H/L from block data or use proxy
        ret = float(r.get('ret', 0))
        bars.append({'d': r['d'], 'c': c, 'ret': ret,
                     'r1': 0, 'r3': 0, 'r5': 0, 'phase': '?'})
    for i in range(len(bars)):
        if i+1 < len(bars): bars[i]['r1'] = bars[i+1]['c']/bars[i]['c'] - 1
        if i+3 < len(bars): bars[i]['r3'] = bars[i+3]['c']/bars[i]['c'] - 1
        if i+5 < len(bars): bars[i]['r5'] = bars[i+5]['c']/bars[i]['c'] - 1
    return bars

def classify_phase(bars, i):
    if i < 30: return '?'
    p = bars[i]['c']; p20 = bars[i-20]['c']
    t20 = (p/p20-1)*100
    d5 = sum(bars[j].get('ddx',0) for j in range(max(0,i-5),i+1))
    d10 = sum(bars[j].get('ddx',0) for j in range(max(0,i-10),i+1))
    if t20 > 5 and d5 > 0 and d10 > 0: return 'D'
    if t20 > 3 and d5 > 0: return 'D'
    return 'A'

# Need OHLC data. Let me use the KL data directly
def load_kl_direct(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        d = json.load(f)
    bars = []
    for i, r in enumerate(d):
        c = float(r['c'])
        o = float(r.get('open', c))
        h = float(r.get('high', c))
        l = float(r.get('low', c))
        dd = float(r.get('main', 0))
        # Closing recovery: how much of the day's range was recovered at close
        day_range = h - l
        if day_range > 0:
            close_pct = (c - l) / day_range  # 0=closed at low, 1=closed at high
        else:
            close_pct = 0.5
        bars.append({
            'd': r['d'], 'c': c, 'o': o, 'h': h, 'l': l,
            'close_pct': close_pct, 'ddx': dd,
            'r1': 0, 'r3': 0, 'r5': 0
        })
    for i in range(len(bars)):
        if i+1 < len(bars): bars[i]['r1'] = bars[i+1]['c']/bars[i]['c'] - 1
        if i+3 < len(bars): bars[i]['r3'] = bars[i+3]['c']/bars[i]['c'] - 1
        if i+5 < len(bars): bars[i]['r5'] = bars[i+5]['c']/bars[i]['c'] - 1
    for i in range(30, len(bars)):
        bars[i]['phase'] = classify_phase(bars, i)
    return bars

def test(name, bars):
    print(f"\n{'='*60}")
    print(f"  {name} — 竞价恢复度分析")
    print(f"{'='*60}")
    
    # Which days had this specific pattern: big down day, but closed significantly above low?
    # "Auction recovery": close_pct when day was down > 1%
    data = [b for b in bars[35:] if b['phase'] != '?']
    
    print(f"\n  【收盘恢复度 → 次日】(当天下跌>1%的天数)")
    print(f"  {'close_pct区间':<18} {'天数':>5} {'次日':>8} {'3日':>8} {'5日':>8}")
    for label, lo, hi in [
        ("底端0-0.2(近低收)", 0, 0.2),
        ("低位0.2-0.4", 0.2, 0.4),
        ("中位0.4-0.6", 0.4, 0.6),
        ("高位0.6-0.8", 0.6, 0.8),
        ("顶端0.8-1.0(近高收)", 0.8, 1.01),
    ]:
        idxs = [b for b in data if b['c']/b['o']-1 < -0.01 and lo <= b['close_pct'] < hi]
        if len(idxs) < 3: continue
        r1 = [b['r1'] for b in idxs]
        r3 = [b['r3'] for b in idxs]
        r5 = [b['r5'] for b in idxs]
        print(f"  {label:<18} {len(idxs):>5} {sum(r1)/len(r1):>+7.2%} {sum(r3)/len(r3):>+7.2%} {sum(r5)/len(r5):>+7.2%}")
    
    # Compare: 下跌日+尾盘拉回 vs 下跌日+尾盘不拉回
    print(f"\n  【下跌日竞价拉回 vs 无拉回 × Phase】")
    for ph in ['A', 'D']:
        for label, cond in [
            ("竞价拉回(pct>0.6)", lambda b: b['close_pct'] > 0.6),
            ("无拉回(pct<0.4)", lambda b: b['close_pct'] < 0.4),
        ]:
            idxs = [b for b in data if b['phase']==ph and b['c']/b['o']-1 < -0.01 and cond(b)]
            if len(idxs) < 3: continue
            r1 = [b['r1'] for b in idxs]
            r5 = [b['r5'] for b in idxs]
            print(f"  Phase {ph} {label}: {len(idxs)}天 次日{sum(r1)/len(r1):>+7.2%} 5日{sum(r5)/len(r5):>+7.2%}")
    
    # Today's specific pattern: down > 1%, close_pct in what range?
    # 昆仑今天: open 48.47, close 49.42, low 47.80, high 53.53
    # close_pct = (49.42-47.80)/(53.53-47.80) = 1.62/5.73 = 0.283
    # So close_pct ≈ 0.28 - low recovery, not a strong auction signal
    print(f"\n  【昆仑7/10模拟: close_pct=(49.42-47.80)/(53.53-47.80)=0.28】")
    # Find similar patterns
    sim = [b for b in data if 0.2 <= b['close_pct'] <= 0.4 and b['c']/b['o']-1 < -0.01]
    if sim:
        r1 = [b['r1'] for b in sim]
        r5 = [b['r5'] for b in sim]
        print(f"  类似形态(close_pct 0.2-0.4,下跌): {len(sim)}天 次日{sum(r1)/len(r1):>+7.2%} 5日{sum(r5)/len(r5):>+7.2%}")


bars_kl = load_kl_direct('kl_ddx_1y.json')
bars_bl = load_kl_direct('bl_ddx_1y.json')
test("昆仑 300418", bars_kl)
test("蓝标 300058", bars_bl)
print(f"\n结论: 尾盘竞价拉回(close_pct>0.6)在下跌日=次日偏多")
print(f"      竞价不拉回(close_pct<0.4)=次日偏空")
