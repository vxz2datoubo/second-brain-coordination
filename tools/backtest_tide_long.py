"""
回测 rotation-tide-reversal — 潮汐+散户在买 多周期前瞻
昆仑+蓝标249天真DDX, 无未来函数
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
                         'r1':0,'r3':0,'r5':0,'r10':0,'r15':0})
        else:
            ret = c/bars[-1]['c']-1
            bars.append({'d':r['d'],'c':c,'ddx':dd,'ddy':dy,'sm':sm,'tf':tf,'ret':ret,
                         'r1':0,'r3':0,'r5':0,'r10':0,'r15':0})
    for i in range(len(bars)):
        if i+1<len(bars): bars[i]['r1']=bars[i+1]['c']/bars[i]['c']-1
        if i+3<len(bars): bars[i]['r3']=bars[i+3]['c']/bars[i]['c']-1
        if i+5<len(bars): bars[i]['r5']=bars[i+5]['c']/bars[i]['c']-1
        if i+10<len(bars): bars[i]['r10']=bars[i+10]['c']/bars[i]['c']-1
        if i+15<len(bars): bars[i]['r15']=bars[i+15]['c']/bars[i]['c']-1
    return bars

def test(name, bars):
    print(f"\n{'='*70}")
    print(f"  {name} — 潮汐+散户在买 多周期前瞻")
    print(f"{'='*70}")
    
    # Find all tide signals
    tide_retail = []
    tide_only = []
    retail_only = []
    
    for i in range(3, len(bars)-15):
        # Tide conditions
        dd_neg_yesterday = bars[i-1]['ddx'] < 0
        ddx_improving = bars[i-1]['ddx'] > bars[i-2]['ddx'] and bars[i]['ddx'] > bars[i-1]['ddx']
        not_crash = bars[i-1]['ret'] > -0.05
        is_tide = dd_neg_yesterday and ddx_improving and not_crash
        
        # Retail buying
        retail_buying = bars[i]['sm'] > 0
        
        if is_tide and retail_buying:
            tide_retail.append(i)
        elif is_tide and not retail_buying:
            tide_only.append(i)
        elif not is_tide and retail_buying:
            retail_only.append(i)
    
    # Baseline: all days
    baseline = list(range(3, len(bars)-15))
    
    # Report function
    print(f"  {'信号':<28} {'天数':>5} {'次日':>8} {'3日':>8} {'5日':>8} {'10日':>8} {'15日':>8}")
    print(f"  {'─'*70}")
    
    for label, idxs in [
        ("潮汐+散户在买 🔥", tide_retail),
        ("仅潮汐(无散户买)", tide_only),
        ("仅散户买(无潮汐)", retail_only),
        ("基线(所有交易日)", baseline),
    ]:
        if len(idxs) < 2:
            continue
        periods = ['r1','r3','r5','r10','r15']
        vals = []
        for p in periods:
            v = [bars[i][p] for i in idxs if bars[i][p] is not None]
            vals.append(sum(v)/len(v) if v else 0)
        
        winrate = sum(1 for i in idxs if bars[i]['r5'] is not None and bars[i]['r5'] > 0) / max(1, sum(1 for i in idxs if bars[i]['r5'] is not None))
        print(f"  {label:<28} {len(idxs):>5} {vals[0]:>+7.2%} {vals[1]:>+7.2%} {vals[2]:>+7.2%} {vals[3]:>+7.2%} {vals[4]:>+7.2%}  5日胜率{winrate:.0%}")
    
    # Multi-period analysis for the BEST signal
    if tide_retail:
        print(f"\n  【潮汐+散户在买 详细分析】")
        for days, p in [(1, 'r1'), (3, 'r3'), (5, 'r5'), (10, 'r10'), (15, 'r15')]:
            vals = [bars[i][p] for i in tide_retail if bars[i][p] is not None]
            if vals:
                wins = sum(1 for v in vals if v > 0)
                avg = sum(vals)/len(vals)
                print(f"    {days:>2}日: {avg:>+7.2%}  胜率 {wins}/{len(vals)}={wins/len(vals):.0%}  最大{max(vals):>+7.2%}  最小{min(vals):>+7.2%}")
        
        # Check for mean reversion
        r5_vals = [bars[i]['r5'] for i in tide_retail if bars[i]['r5'] is not None]
        r10_vals = [bars[i]['r10'] for i in tide_retail if bars[i]['r10'] is not None]
        if r5_vals and r10_vals:
            avg_5 = sum(r5_vals)/len(r5_vals)
            avg_10 = sum(r10_vals)/len(r10_vals)
            trend = avg_10 - avg_5
            print(f"    趋势: 5日→10日 {'📈持续' if trend > 0 else '📉反转' if trend < -0.02 else '➡️持平'} ({trend:+.2%})")

bars_kl = load('kl_ddx_1y.json')
bars_bl = load('bl_ddx_1y.json')
test("昆仑 300418", bars_kl)
test("蓝标 300058", bars_bl)

print(f"\n{'='*70}")
print(f"  判决: 潮汐+散户在买 = 短线反弹信号还是趋势反转信号?")
print(f"  看5→10→15日趋势: 持续上行=趋势反转, 5日后回落=短线反弹")
print(f"{'='*70}")
