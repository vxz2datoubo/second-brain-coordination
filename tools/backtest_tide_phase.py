"""
回测 "潮汐+散户在买" 在不同Wyckoff周期阶段的各自效果
昆仑+蓝标 249天真DDX, 无未来函数
"""
import json

def load(name):
    with open(f'F:/aidanao/data/{name}', 'r', encoding='utf-8') as f:
        data = json.load(f)
    bars = []
    for i, r in enumerate(data):
        c = float(r['c']); dd = float(r.get('main', 0))
        dy = float(r.get('jumbo', 0)); sm = float(r.get('small', 0))
        tf = abs(dd)+abs(dy)+abs(sm)
        if i == 0:
            bars.append({'d':r['d'],'c':c,'ddx':dd,'ddy':dy,'sm':sm,'tf':tf,'ret':0,
                         'r1':0,'r3':0,'r5':0,'r10':0,'r15':0,'phase':'?'})
        else:
            ret = c/bars[-1]['c']-1
            bars.append({'d':r['d'],'c':c,'ddx':dd,'ddy':dy,'sm':sm,'tf':tf,'ret':ret,
                         'r1':0,'r3':0,'r5':0,'r10':0,'r15':0,'phase':'?'})
    for i in range(len(bars)):
        if i+1<len(bars): bars[i]['r1']=bars[i+1]['c']/bars[i]['c']-1
        if i+3<len(bars): bars[i]['r3']=bars[i+3]['c']/bars[i]['c']-1
        if i+5<len(bars): bars[i]['r5']=bars[i+5]['c']/bars[i]['c']-1
        if i+10<len(bars): bars[i]['r10']=bars[i+10]['c']/bars[i]['c']-1
        if i+15<len(bars): bars[i]['r15']=bars[i+15]['c']/bars[i]['c']-1
    return bars

def classify_phase(bars, i):
    """Wyckoff phase classification using only past data"""
    if i < 30: return '?'
    
    p = bars[i]['c']
    p20 = bars[i-20]['c']
    p60 = bars[i-60]['c'] if i >= 60 else p
    trend_20d = (p/p20 - 1) * 100
    trend_60d = (p/p60 - 1) * 100
    
    ddx5 = sum(bars[j]['ddx'] for j in range(max(0,i-5), i+1))
    ddx10 = sum(bars[j]['ddx'] for j in range(max(0,i-10), i+1))
    ddx20 = sum(bars[j]['ddx'] for j in range(max(0,i-20), i+1))
    
    vol20 = sum(bars[j]['tf'] for j in range(max(0,i-20), i)) / 20
    vol5 = sum(bars[j]['tf'] for j in range(max(0,i-5), i)) / 5
    vol_now = bars[i]['tf']
    vol_ratio = vol_now / vol20 if vol20 > 0 else 1
    vol_trend = vol5 / vol20 if vol20 > 0 else 1
    
    # Phase D: Markup (price > 20d avg rising + DDX positive)
    if trend_20d > 5 and ddx5 > 0 and ddx10 > 0:
        return 'D'
    # Phase D early: starting to rise
    if 2 < trend_20d <= 8 and ddx5 > 0 and vol_ratio > 1.2:
        return 'D'
    
    # Phase C: Shakeout (near flat, volume shrinking, DDX mixed)
    if -3 < trend_20d < 5 and vol_trend < 0.8 and ddx20 > 0:
        return 'C'
    
    # Phase B: Testing (volume spike, moderate trend)
    if -2 < trend_20d < 10 and vol_ratio > 1.3:
        return 'B'
    
    # Phase A: Accumulation (low volume, negative trend from high)
    if trend_60d < 0 and ddx20 > 0:
        return 'A'
    if trend_20d < 0 and vol_trend < 0.7 and ddx20 > 0:
        return 'A'
    
    # Phase E: Distribution (high price, DDX weakening)
    if trend_20d > 15 and ddx5 < ddx10 * 0.3:
        return 'E'
    
    return '?'


def test(name, bars):
    print(f"\n{'='*70}")
    print(f"  {name} — 潮汐+散户在买 × 不同Wyckoff周期阶段")
    print(f"{'='*70}")
    
    # Classify all bars
    for i in range(30, len(bars)):
        bars[i]['phase'] = classify_phase(bars, i)
    
    # Find tide+retail signals per phase
    phase_signals = {p: [] for p in ['A','B','C','D','E']}
    
    for i in range(33, len(bars)-15):
        # Tide conditions
        dd_neg_yesterday = bars[i-1]['ddx'] < 0
        ddx_improving = (bars[i-1]['ddx'] > bars[i-2]['ddx'] and 
                        bars[i]['ddx'] > bars[i-1]['ddx'])
        not_crash = bars[i-1]['ret'] > -0.05
        is_tide = dd_neg_yesterday and ddx_improving and not_crash
        
        # Retail buying
        retail_buying = bars[i]['sm'] > 0
        
        if is_tide and retail_buying:
            ph = bars[i]['phase']
            if ph in phase_signals:
                phase_signals[ph].append(i)
    
    # Report per phase
    print(f"  {'Phase':>8} {'天数':>5} {'次日':>8} {'3日':>8} {'5日':>8} {'10日':>8} {'15日':>8} {'5日胜率':>8}")
    print(f"  {'─'*70}")
    
    for ph in ['A','B','C','D','E']:
        idxs = phase_signals[ph]
        if len(idxs) < 2:
            if idxs:
                print(f"  {'Phase '+ph:>8} {len(idxs):>5} {'样本太少':>50}")
            continue
        
        periods = ['r1','r3','r5','r10','r15']
        vals = []
        for p_key in periods:
            v = [bars[i][p_key] for i in idxs if bars[i][p_key] is not None]
            vals.append(sum(v)/len(v) if v else 0)
        
        r5_vals = [bars[i]['r5'] for i in idxs if bars[i]['r5'] is not None]
        win5 = sum(1 for v in r5_vals if v > 0) / len(r5_vals) if r5_vals else 0
        
        print(f"  {'Phase '+ph:>8} {len(idxs):>5} {vals[0]:>+7.2%} {vals[1]:>+7.2%} {vals[2]:>+7.2%} {vals[3]:>+7.2%} {vals[4]:>+7.2%} {win5:>7.0%}")
    
    # Phase distribution stats
    print(f"\n  【Phase分布】")
    total = sum(len(v) for v in phase_signals.values())
    for ph in ['A','B','C','D','E']:
        n = len(phase_signals[ph])
        pct = n/total*100 if total else 0
        bar = '█' * int(pct/2)
        print(f"  Phase {ph}: {n:>3}天 ({pct:>5.1f}%) {bar}")
    
    # Baseline per phase (all tide signals, not just +retail)
    print(f"\n  【基线对比: 仅潮汐(不含散户买) as Phase】")
    print(f"  {'Phase':>8} {'天数':>5} {'5日':>8} {'10日':>8} {'vs潮汐+散户5日差':>18}")
    
    for ph in ['A','B','C','D','E']:
        tide_all = [i for i in range(33, len(bars)-15) 
                   if bars[i]['phase']==ph and bars[i-1]['ddx']<0 
                   and bars[i-1]['ddx']>bars[i-2]['ddx'] 
                   and bars[i]['ddx']>bars[i-1]['ddx']]
        
        tide_retail = phase_signals[ph]
        
        if len(tide_all) >= 2:
            r5_all = [bars[i]['r5'] for i in tide_all if bars[i]['r5'] is not None]
            r5_retail = [bars[i]['r5'] for i in tide_retail if bars[i]['r5'] is not None]
            avg_all = sum(r5_all)/len(r5_all)
            avg_ret = sum(r5_retail)/len(r5_retail) if r5_retail else 0
            diff = avg_ret - avg_all
            marker = "🔥散户加成" if diff > 0.02 else "⚠️无加成" if diff > -0.02 else "🚨反向"
            print(f"  {'Phase '+ph:>8} {len(tide_all):>5} {avg_all:>+7.2%} {avg_ret:>+7.2%} {diff:>+10.2%} {marker}")


bars_kl = load('kl_ddx_1y.json')
bars_bl = load('bl_ddx_1y.json')
test("昆仑 300418", bars_kl)
test("蓝标 300058", bars_bl)

print(f"\n{'='*70}")
print(f"  判决: 潮汐+散户在买在不同Phase的效果差异")
print(f"  Phase D = 趋势延续, Phase A = 底部反转, Phase E = 危险")
print(f"{'='*70}")
