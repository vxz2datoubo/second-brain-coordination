"""
回测: 大跌日(-2%+) × DDX状态 × Phase → 次日
昆仑+蓝标 249天
"""
import json

def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        d = json.load(f)
    bars = []
    for i, r in enumerate(d):
        c = float(r['c']); dd = float(r.get('main',0))
        ret = 0
        if i > 0: ret = c / bars[-1]['c'] - 1
        bars.append({'d': r['d'], 'c': c, 'ddx': dd, 'ret': ret,
                     'r1': 0, 'r3': 0, 'r5': 0, 'phase': '?'})
    for i in range(len(bars)):
        if i+1 < len(bars): bars[i]['r1'] = bars[i+1]['c'] / bars[i]['c'] - 1
        if i+3 < len(bars): bars[i]['r3'] = bars[i+3]['c'] / bars[i]['c'] - 1
        if i+5 < len(bars): bars[i]['r5'] = bars[i+5]['c'] / bars[i]['c'] - 1
    return bars

def phase(bars, i):
    if i < 30: return '?'
    p = bars[i]['c']; p20 = bars[i-20]['c']
    t20 = (p/p20-1)*100
    d5 = sum(bars[j]['ddx'] for j in range(max(0,i-5),i+1))
    d10 = sum(bars[j]['ddx'] for j in range(max(0,i-10),i+1))
    if t20 > 5 and d5 > 0 and d10 > 0: return 'D'
    if t20 > 3 and d5 > 0: return 'D'
    return 'A'

def test(name, bars):
    for i in range(30, len(bars)): bars[i]['phase'] = phase(bars, i)
    data = [b for b in bars[35:] if b['phase'] in ('A','D')]
    
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    
    # Today: -2.16%, DDX -0.29, Phase D
    # Find similar patterns
    for label, ret_lo, ret_hi, ddx_lo, ddx_hi in [
        ("跌>2%+DDX<-0.2(今天)", -99, -0.02, -99, -0.2),
        ("跌>2%+DDX<-0.1", -99, -0.02, -99, -0.1),
        ("跌>3%+DDX<-0.2(更惨)", -99, -0.03, -99, -0.2),
    ]:
        print(f"\n  【{label} × Phase】")
        print(f"  {'Phase':>6} {'天数':>5} {'次日':>8} {'3日':>8} {'5日':>8} {'翻红率':>7}")
        for ph in ['A', 'D']:
            idxs = [b for b in data 
                   if b['phase']==ph and ret_lo <= b['ret'] < ret_hi 
                   and ddx_lo <= b['ddx'] < ddx_hi]
            if len(idxs) < 2: continue
            r1 = [b['r1'] for b in idxs]
            r3 = [b['r3'] for b in idxs]
            r5 = [b['r5'] for b in idxs]
            hit = sum(1 for v in r1 if v > 0)
            print(f"  {'Phase '+ph:>6} {len(idxs):>5} {sum(r1)/len(r1):>+7.2%} {sum(r3)/len(r3):>+7.2%} {sum(r5)/len(r5):>+7.2%} {hit}/{len(r1)}")
    
    # Exact match: 跌2-3%, DDX -0.25 to -0.35, Phase D
    print(f"\n  【精确匹配: 跌2-3% + DDX -0.25~-0.35 + Phase D】")
    exact = [b for b in data if b['phase']=='D' and -0.03 <= b['ret'] < -0.02 and -0.35 <= b['ddx'] < -0.25]
    if exact:
        for b in exact:
            print(f"    {b['d']} 跌{b['ret']:.1%} DDX{b['ddx']:.2f} → 次日{b['r1']:.1%} 5日{b['r5']:.1%}")

bars_kl = load('F:/aidanao/data/kl_ddx_1y.json')
bars_bl = load('F:/aidanao/data/bl_ddx_1y.json')
test("昆仑 300418", bars_kl)
test("蓝标 300058", bars_bl)