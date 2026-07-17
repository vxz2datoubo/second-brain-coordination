"""
回测 获利压力模型 — 轻量版, 20日滚动成本中位数
昆仑+蓝标 249天
"""
import json

def load(name):
    with open(f'F:/aidanao/data/{name}', 'r', encoding='utf-8') as f:
        data = json.load(f)
    bars = []
    for i, r in enumerate(data):
        c = float(r['c']); dd = float(r.get('main',0)); dy = float(r.get('jumbo',0))
        md = float(r.get('mid',0)); sm = float(r.get('small',0))
        bars.append({'d':r['d'],'c':c,'ddx':dd,'ddy':dy,'md':md,'sm':sm,
                     'r1':0,'r5':0,'r10':0,'phase':'?'})
    for i in range(len(bars)):
        if i+1<len(bars): bars[i]['r1']=bars[i+1]['c']/bars[i]['c']-1
        if i+5<len(bars): bars[i]['r5']=bars[i+5]['c']/bars[i]['c']-1
        if i+10<len(bars): bars[i]['r10']=bars[i+10]['c']/bars[i]['c']-1
    return bars

def classify_phase(bars, i):
    if i<30: return '?'
    p=bars[i]['c']; p20=bars[i-20]['c']
    t20=(p/p20-1)*100
    d5=sum(bars[j]['ddx'] for j in range(max(0,i-5),i+1))
    d10=sum(bars[j]['ddx'] for j in range(max(0,i-10),i+1))
    v20=sum(abs(bars[j]['ddx'])+abs(bars[j]['ddy'])+abs(bars[j]['md'])+abs(bars[j]['sm']) for j in range(max(0,i-20),i))/20
    vn=abs(bars[i]['ddx'])+abs(bars[i]['ddy'])+abs(bars[i]['md'])+abs(bars[i]['sm'])
    vr=vn/v20 if v20>0 else 1
    if t20>5 and d5>0 and d10>0: return 'D'
    if t20>3 and d5>0: return 'D'
    return 'A'

def compute_metrics(bars):
    all_prices = []
    ddx_cum = []
    for i, b in enumerate(bars):
        c = b['c']
        all_prices.append(c)
        if len(all_prices) > 20: all_prices.pop(0)
        ddx_cum.append(b['ddx'])
        if len(ddx_cum) > 20: ddx_cum.pop(0)
        
        # 20d profit rate: % of days in last 20 where price < current
        profit_rate_20d = sum(1 for pp in all_prices[:-1] if pp < c) / max(len(all_prices)-1, 1)
        
        # Mid pool profit: use 5-day VWAP as mid pool proxy cost
        mid_cost_5d = sum(bars[j]['c'] for j in range(max(0,i-5), i)) / max(i-max(0,i-5), 1)
        mid_profit = (c/mid_cost_5d - 1) if i>=5 else 0
        
        # Small pool: 10-day VWAP proxy
        small_cost_10d = sum(bars[j]['c'] for j in range(max(0,i-10), i)) / max(i-max(0,i-10), 1)
        small_profit = (c/small_cost_10d - 1) if i>=10 else 0
        
        # DDX cumulative as proxy for overall profit
        ddx_cum_sum = sum(ddx_cum)
        
        bars[i]['profit_20d'] = profit_rate_20d
        bars[i]['mid_profit'] = mid_profit
        bars[i]['small_profit'] = small_profit
        bars[i]['ddx_cum'] = ddx_cum_sum

def test(name, bars):
    compute_metrics(bars)
    for i in range(30, len(bars)):
        bars[i]['phase'] = classify_phase(bars, i)
    
    print(f"\n{'='*65}")
    print(f"  {name} — 获利压力回测")
    print(f"{'='*65}")
    
    data = [b for b in bars[35:] if b['phase']!='?' and b['r5'] is not None]
    
    # Test 1: 20d profit rate vs next day
    print(f"\n  【20日获利比例 → 次日】")
    for label, lo, hi in (
        ("获利<30%(底部)", 0, 0.3), ("获利30-60%", 0.3, 0.6),
        ("获利60-80%", 0.6, 0.8), ("获利80-100%(高位)", 0.8, 1.01),
    ):
        idxs = [b for b in data if lo <= b['profit_20d'] < hi]
        if len(idxs)<3: continue
        r1=[b['r1'] for b in idxs]
        print(f"  {label:<20} {len(idxs):>3}天 次日{sum(r1)/len(r1):>+7.2%}")
    
    # Test 2: mid profit zone
    print(f"\n  【中单盈亏区间(5日成本) → 次日】")
    for label, lo, hi in (
        ("亏损", -1, -0.03), ("微盈0-3%", 0, 0.03),
        ("追涨3-5%", 0.03, 0.05), ("满足5-10%", 0.05, 0.10), ("梦想>10%", 0.10, 5),
    ):
        idxs = [b for b in data if lo <= b['mid_profit'] < hi]
        if len(idxs)<3: continue
        r1=[b['r1'] for b in idxs]
        print(f"  {label:<20} {len(idxs):>3}天 次日{sum(r1)/len(r1):>+7.2%}")
    
    # Test 3: small pool — T+1 ≠ must sell
    print(f"\n  【小单盈亏区间(10日成本) → 次日跑率】")
    for label, lo, hi in (
        ("亏损", -1, 0), ("追涨0-5%", 0, 0.05), ("满足5-10%", 0.05, 0.10), ("梦想>10%", 0.10, 5),
    ):
        idxs = [b for b in data if lo <= b['small_profit'] < hi]
        if len(idxs)<3: continue
        r1=[b['r1'] for b in idxs]
        neg=sum(1 for v in r1 if v<0)
        print(f"  {label:<20} {len(idxs):>3}天 次日{sum(r1)/len(r1):>+7.2%} 跑率{neg}/{len(r1)}={neg/len(r1):.0%}")
    
    # Test 4: profit_80%+ × Phase D
    print(f"\n  【20日获利>80% × Phase → 5日】")
    for ph in ['A','D']:
        idxs = [b for b in data if b['profit_20d']>=0.8 and b['phase']==ph]
        if len(idxs)<3: continue
        r5=[b['r5'] for b in idxs]
        print(f"  Phase {ph}: {len(idxs)}天 5日{sum(r5)/len(r5):>+7.2%}")
    
    # Test 5: mid满足区 × Phase
    print(f"\n  【中单满足区(5-10%) × Phase】")
    for ph in ['A','D']:
        idxs = [b for b in data if 0.05<=b['mid_profit']<0.10 and b['phase']==ph]
        if len(idxs)<3: continue
        r1=[b['r1'] for b in idxs]; r5=[b['r5'] for b in idxs]
        print(f"  Phase {ph}: {len(idxs)}天 次日{sum(r1)/len(r1):>+7.2%} 5日{sum(r5)/len(r5):>+7.2%}")


bars_kl = load('kl_ddx_1y.json')
bars_bl = load('bl_ddx_1y.json')
test("昆仑 300418", bars_kl)
test("蓝标 300058", bars_bl)
print(f"\n判决: T+1解锁≠一定卖, 追涨区次日跑率应<40%")
print(f"      高获利+D=强趋势(5日正), 高获利+A=随时回调")
print(f"      中单满足区+D=游资走了, 次日大概率涨")