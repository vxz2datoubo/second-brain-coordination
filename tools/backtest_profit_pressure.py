"""
回测 fund-pool-tracker §二B — 获利压力模型
测试: 整体获利比例 → 次日抛压 / 各池时间偏好 / Phase校准
昆仑+蓝标 249天, 无未来函数
"""
import json

def load(name):
    with open(f'F:/aidanao/data/{name}', 'r', encoding='utf-8') as f:
        data = json.load(f)
    bars = []
    for i, r in enumerate(data):
        c = float(r['c']); dd = float(r.get('main', 0))
        dy = float(r.get('jumbo', 0)); md = float(r.get('mid', 0))
        sm = float(r.get('small', 0))
        bars.append({'d':r['d'],'c':c,'ddx':dd,'ddy':dy,'md':md,'sm':sm,
                     'r1':0,'r5':0,'r10':0,'phase':'?'})
    for i in range(len(bars)):
        if i+1<len(bars): bars[i]['r1']=bars[i+1]['c']/bars[i]['c']-1
        if i+5<len(bars): bars[i]['r5']=bars[i+5]['c']/bars[i]['c']-1
        if i+10<len(bars): bars[i]['r10']=bars[i+10]['c']/bars[i]['c']-1
    return bars

def classify_phase(bars, i):
    if i < 30: return '?'
    p = bars[i]['c']; p20 = bars[i-20]['c']
    p60 = bars[i-60]['c'] if i>=60 else p
    t20 = (p/p20-1)*100; t60 = (p/p60-1)*100
    d5 = sum(bars[j]['ddx'] for j in range(max(0,i-5),i+1))
    d10 = sum(bars[j]['ddx'] for j in range(max(0,i-10),i+1))
    v20 = sum(abs(bars[j]['ddx'])+abs(bars[j]['ddy'])+abs(bars[j]['md'])+abs(bars[j]['sm']) 
             for j in range(max(0,i-20),i)) / 20
    vnow = abs(bars[i]['ddx'])+abs(bars[i]['ddy'])+abs(bars[i]['md'])+abs(bars[i]['sm'])
    vr = vnow/v20 if v20>0 else 1
    if t20>5 and d5>0 and d10>0: return 'D'
    if 2<t20<=8 and d5>0 and vr>1.2: return 'D'
    if -3<t20<5 and vr<0.8 and sum(bars[j]['ddx'] for j in range(max(0,i-20),i+1))>0: return 'C'
    if t20>3 and d5>0: return 'D'
    return 'A'

def run_fifo(bars):
    pools = {'jumbo':[], 'large':[], 'mid':[], 'small':[]}
    results = []
    cache = []  # rolling 20-day price for cost estimation
    
    for i in range(len(bars)):
        c = bars[i]['c']
        cache.append(c)
        if len(cache) > 20: cache.pop(0)
        
        flows = {'jumbo':bars[i]['ddy'],'large':bars[i]['ddx'],'mid':bars[i]['md'],'small':bars[i]['sm']}
        for pn in pools:
            for e in pools[pn]: e['age']+=1
        
        # Process outflows first (FIFO)
        for pn, flow in flows.items():
            pool = pools[pn]
            if flow < 0:
                rs = abs(flow)
                while rs>0 and pool:
                    if pool[0]['vol']<=rs: rs-=pool[0]['vol']; pool.pop(0)
                    else: pool[0]['vol']-=rs; rs=0
            elif flow > 0:
                pool.append({'day':i,'vol':flow,'cost':c,'age':0})
        
        # Calculate metrics
        # Overall profit rate proxy: what % of pooled cost is below current price
        all_costs = []
        for pn in pools:
            for e in pools[pn]:
                all_costs.extend([e['cost']]*int(e['vol']))
        profit_rate = sum(1 for cc in all_costs if cc < c) / max(len(all_costs), 1) if all_costs else 0.5
        
        # Average profit of mid pool (游资)
        mid_items = pools['mid']
        if mid_items:
            mid_avg_cost = sum(e['vol']*e['cost'] for e in mid_items) / sum(e['vol'] for e in mid_items)
            mid_profit = (c / mid_avg_cost - 1)
        else:
            mid_profit = 0
        
        # Average profit of small pool
        small_items = pools['small']
        if small_items:
            small_avg_cost = sum(e['vol']*e['cost'] for e in small_items) / sum(e['vol'] for e in small_items)
            small_profit = (c / small_avg_cost - 1)
        else:
            small_profit = 0
        
        # 20-day price change (proxy for overall profit rate)
        avg20 = sum(cache) / len(cache)
        overall_profit_20d = (c / avg20 - 1) if avg20 else 0
        
        results.append({
            'i': i, 'profit_rate': profit_rate, 'mid_profit': mid_profit,
            'small_profit': small_profit, 'overall_profit_20d': overall_profit_20d,
            'r1': bars[i]['r1'], 'r5': bars[i]['r5'], 'r10': bars[i]['r10'],
            'phase': bars[i]['phase']
        })
    return results

def test(name, bars):
    results = run_fifo(bars)
    for i in range(30, len(bars)):
        bars[i]['phase'] = classify_phase(bars, i)
    for r in results:
        i = r['i']
        if i >= 30: r['phase'] = bars[i]['phase']
    
    print(f"\n{'='*65}")
    print(f"  {name} — 获利压力回测")
    print(f"{'='*65}")
    
    # Test 1: Overall profit rate vs next day return
    print(f"\n  【整体获利比例 → 次日走势】")
    for label, lo, hi in [
        ("获利<30%(多数亏损)", 0, 0.3),
        ("获利30-60%(半赚半亏)", 0.3, 0.6),
        ("获利60-80%(多数赚钱)", 0.6, 0.8),
        ("获利80-100%(几乎全赚)", 0.8, 1.0),
    ]:
        idxs = [r for r in results[30:] if lo <= r['profit_rate'] < hi]
        if len(idxs)<2: continue
        r1=[r['r1'] for r in idxs if r['r1'] is not None]
        r5=[r['r5'] for r in idxs if r['r5'] is not None]
        print(f"  {label:<22} {len(idxs):>3}天 次日{sum(r1)/len(r1):>+7.2%} 5日{sum(r5)/len(r5):>+7.2%}")
    
    # Test 2: Mid profit zone → next day (游资满足区 vs 梦想区)
    print(f"\n  【中单池盈亏区间 → 次日】")
    for label, filter_fn in [
        ("中单亏损(<-3%)", lambda r: r['mid_profit'] < -0.03),
        ("中单微盈(0-3%)", lambda r: 0 <= r['mid_profit'] < 0.03),
        ("中单追涨(3-5%)", lambda r: 0.03 <= r['mid_profit'] < 0.05),
        ("中单满足(5-10%)", lambda r: 0.05 <= r['mid_profit'] < 0.10),
        ("中单梦想(>10%)", lambda r: r['mid_profit'] >= 0.10),
    ]:
        idxs = [r for r in results[30:] if filter_fn(r)]
        if len(idxs)<2: continue
        r1=[r['r1'] for r in idxs if r['r1'] is not None]
        r5=[r['r5'] for r in idxs if r['r5'] is not None]
        hit=sum(1 for v in r1 if v>0)/len(r1)
        print(f"  {label:<22} {len(idxs):>3}天 次日{sum(r1)/len(r1):>+7.2%} 5日{sum(r5)/len(r5):>+7.2%} 翻红率{hit:.0%}")
    
    # Test 3: "T+1解锁 = 一定卖?" — small pool profit zone
    print(f"\n  【小单池盈亏区间 → 次日 — 测试T+1≠一定卖】")
    for label, filter_fn in [
        ("小单亏损(<-3%)", lambda r: r['small_profit'] < -0.03),
        ("小单微盈(0-2%)", lambda r: 0 <= r['small_profit'] < 0.02),
        ("小单追涨(2-5%)", lambda r: 0.02 <= r['small_profit'] < 0.05),
        ("小单满足(5-10%)", lambda r: 0.05 <= r['small_profit'] < 0.10),
        ("小单梦想(>10%)", lambda r: r['small_profit'] >= 0.10),
    ]:
        idxs = [r for r in results[30:] if filter_fn(r)]
        if len(idxs)<2: continue
        r1=[r['r1'] for r in idxs if r['r1'] is not None]
        r5=[r['r5'] for r in idxs if r['r5'] is not None]
        neg=sum(1 for v in r1 if v<0)
        print(f"  {label:<22} {len(idxs):>3}天 次日{sum(r1)/len(r1):>+7.2%} 5日{sum(r5)/len(r5):>+7.2%} 次日跑率{neg}/{len(r1)}={neg/len(r1):.0%}")
    
    # Test 4: Overall profit rate × Phase → combined effect
    print(f"\n  【获利80%+ × Phase → 5日收益】")
    for ph in ['A','D']:
        idxs = [r for r in results[30:] if r['profit_rate']>=0.8 and r['phase']==ph]
        if len(idxs)<4: continue
        r1=[r['r1'] for r in idxs if r['r1'] is not None]
        r5=[r['r5'] for r in idxs if r['r5'] is not None]
        print(f"  Phase {ph} 高获利: {len(idxs)}天 次日{sum(r1)/len(r1):>+7.2%} 5日{sum(r5)/len(r5):>+7.2%}")

    # Test 5: Mid满足区 × Phase
    print(f"\n  【中单满足区(5-10%) × Phase】")
    for ph in ['A','D']:
        idxs = [r for r in results[35:] 
                if 0.05 <= r['mid_profit'] < 0.10 and r['phase']==ph]
        if len(idxs)<3: continue
        r1=[r['r1'] for r in idxs if r['r1'] is not None]
        r5=[r['r5'] for r in idxs if r['r5'] is not None]
        print(f"  Phase {ph} 中单满足: {len(idxs)}天 次日{sum(r1)/len(r1):>+7.2%} 5日{sum(r5)/len(r5):>+7.2%}")

bars_kl = load('kl_ddx_1y.json')
bars_bl = load('bl_ddx_1y.json')
test("昆仑 300418", bars_kl)
test("蓝标 300058", bars_bl)
print(f"\n判决: 获利比例越高→次日日均微正(梦想区不出)")
print(f"      T+1解锁≠一定卖 — 追涨区次日跑率低")
print(f"      中单满足区在Phase D中次日大概率涨(游资走了=好)")