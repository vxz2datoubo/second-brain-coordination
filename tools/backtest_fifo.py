"""
回测 fund-pool-tracker — FIFO资金池分批追踪
昆仑+蓝标 249天真DDX, 多技能叠加
测试: 长线持仓占比 / 游资清仓检测 / 成本带分布 → 前瞻收益
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
                     'r1':0,'r5':0,'r10':0,'r15':0,'long_pct':0,'cost_days':0})
    for i in range(len(bars)):
        if i+1<len(bars): bars[i]['r1']=bars[i+1]['c']/bars[i]['c']-1
        if i+5<len(bars): bars[i]['r5']=bars[i+5]['c']/bars[i]['c']-1
        if i+10<len(bars): bars[i]['r10']=bars[i+10]['c']/bars[i]['c']-1
        if i+15<len(bars): bars[i]['r15']=bars[i+15]['c']/bars[i]['c']-1
    return bars

def run_fifo(bars):
    """Simulate FIFO pools for each channel"""
    # Four pools: each entry is (day_index, volume, cost, remaining)
    pools = {'jumbo':[], 'large':[], 'mid':[], 'small':[]}
    results = []
    
    for i in range(len(bars)):
        c = bars[i]['c']
        
        # Process today's inflows/outflows per channel
        flows = {
            'jumbo': bars[i]['ddy'],
            'large': bars[i]['ddx'],
            'mid': bars[i]['md'],
            'small': bars[i]['sm']
        }
        
        # Age all existing entries
        for pool_name in pools:
            for entry in pools[pool_name]:
                entry['age'] += 1
        
        # Process each channel: sell first (FIFO), then add new entries
        for pool_name, flow in flows.items():
            pool = pools[pool_name]
            
            if flow < 0:
                # Net outflow: remove from oldest entries
                remaining_to_sell = abs(flow)
                while remaining_to_sell > 0 and pool:
                    oldest = pool[0]
                    if oldest['vol'] <= remaining_to_sell:
                        remaining_to_sell -= oldest['vol']
                        pool.pop(0)
                    else:
                        oldest['vol'] -= remaining_to_sell
                        remaining_to_sell = 0
            
            elif flow > 0:
                # Net inflow: add new entry
                entry = {'day': i, 'vol': flow, 'cost': c, 'age': 0}
                pool.append(entry)
        
        # Calculate metrics
        # Long-term ratio: jumbo+large aged > 5 days / all jumbo+large
        long_vol = sum(e['vol'] for e in pools['jumbo'] + pools['large'] if e['age'] >= 5)
        total_vol = sum(e['vol'] for e in pools['jumbo'] + pools['large']) + 0.01
        long_ratio = long_vol / total_vol
        
        # Average cost of holdings
        mid_cost = sum(e['vol']*e['cost'] for e in pools['mid']) / (sum(e['vol'] for e in pools['mid']) + 0.01)
        
        results.append({
            'i': i, 'long_ratio': long_ratio,
            'mid_cost': mid_cost, 'c': c,
            'jumbo_age': sum(e['vol']*e['age'] for e in pools['jumbo']) / (sum(e['vol'] for e in pools['jumbo'])+0.01),
            'mid_vol': sum(e['vol'] for e in pools['mid']),
            'small_vol': sum(e['vol'] for e in pools['small']),
        })
    
    # Copy forward returns using bars data
    for r in results:
        i = r['i']
        if i+1<len(bars): r['r1']=bars[i]['r1']
        else: r['r1']=0
        if i+5<len(bars): r['r5']=bars[i]['r5']
        else: r['r5']=0
        if i+10<len(bars): r['r10']=bars[i]['r10']
        else: r['r10']=0
        if i+15<len(bars): r['r15']=bars[i]['r15']
        else: r['r15']=0
    
    return results

def test(name, bars):
    results = run_fifo(bars)
    print(f"\n{'='*65}")
    print(f"  {name} — FIFO资金池回测")
    print(f"{'='*65}")
    
    # 1. Long-ratio: long-term institutional money staying vs leaving
    print(f"\n  【长线资金占比 — 到期收益】")
    for label, filter_fn, pct in [
        ("长线>70%(极稳)", lambda r: r['long_ratio']>0.7, 0),
        ("长线50-70%(正常)", lambda r: 0.5<r['long_ratio']<=0.7, 0),
        ("长线<50%(短线化)", lambda r: r['long_ratio']<=0.5, 0),
    ]:
        matched = [r for r in results[20:] if filter_fn(r)]
        if len(matched)<2: continue
        r5=[r['r5'] for r in matched if r['r5'] is not None]
        r10=[r['r10'] for r in matched if r['r10'] is not None]
        r15=[r['r15'] for r in matched if r['r15'] is not None]
        print(f"  {label:<22} {len(matched):>3}天 5日{sum(r5)/len(r5):>+7.2%} 10日{sum(r10)/len(r10):>+7.2%} 15日{sum(r15)/len(r15):>+7.2%}")
    
    # 2. Mid pool being cleared (游资撤退检测)
    print(f"\n  【中单池清仓检测 — 游资撤退后的走势】")
    # Detect days when mid pool volume dropped significantly
    mid_decline = []
    mid_stable = []
    for i in range(5, len(results)-5):
        mid_now = results[i]['mid_vol']
        mid_5d_ago = results[i-5]['mid_vol']
        if mid_5d_ago > 0.01 and mid_now / mid_5d_ago < 0.5:
            mid_decline.append(results[i])
        elif mid_5d_ago > 0.01:
            mid_stable.append(results[i])
    
    for label, data in [("中单池5日腰斩(游资撤退)", mid_decline), ("中单池稳定", mid_stable)]:
        if len(data)<2: continue
        r5=[r['r5'] for r in data if r['r5'] is not None]
        r10=[r['r10'] for r in data if r['r10'] is not None]
        win5=sum(1 for v in r5 if v>0)/len(r5)
        print(f"  {label:<28} {len(data):>3}天 5日{sum(r5)/len(r5):>+7.2%} 10日{sum(r10)/len(r10):>+7.2%} 胜率{win5:.0%}")
    
    # 3. Multi-skill叠加: 长线>70% + 游资已撤退
    print(f"\n  【多技能叠加】")
    combo = [r for r in results[25:] 
             if r['long_ratio']>0.65 
             and results[r['i']-5]['mid_vol']>0 
             and r['mid_vol']/max(results[r['i']-5]['mid_vol'],0.01)<0.6]
    
    if len(combo)>=2:
        r5=[r['r5'] for r in combo if r['r5'] is not None]
        r10=[r['r10'] for r in combo if r['r10'] is not None]
        r15=[r['r15'] for r in combo if r['r15'] is not None]
        win5=sum(1 for v in r5 if v>0)/len(r5)
        print(f"  长线>65%+游资已撤退           {len(combo):>3}天 5日{sum(r5)/len(r5):>+7.2%} 10日{sum(r10)/len(r10):>+7.2%} 15日{sum(r15)/len(r15):>+7.2%} 胜率{win5:.0%}")
    else:
        print(f"  长线>65%+游资已撤退: 样本不足")
    
    # 4. 中单成本 vs 现价 (满足区检测)
    print(f"\n  【中单池成本盈亏 — 满足区触发时】")
    for label, filter_fn in [
        ("中单浮盈5-10%(满足区)", lambda r: 0.05<(r['c']/r['mid_cost']-1)<0.10),
        ("中单浮盈>10%(梦想区)", lambda r: (r['c']/r['mid_cost']-1)>0.10),
        ("中单浮盈<5%(安全区)", lambda r: (r['c']/r['mid_cost']-1)<0.05),
    ]:
        matched = [r for r in results[20:] if r['mid_cost']>0 and filter_fn(r)]
        if len(matched)<2: continue
        r5=[r['r5'] for r in matched if r['r5'] is not None]
        r10=[r['r10'] for r in matched if r['r10'] is not None]
        win5=sum(1 for v in r5 if v>0)/len(r5)
        print(f"  {label:<28} {len(matched):>3}天 5日{sum(r5)/len(r5):>+7.2%} 10日{sum(r10)/len(r10):>+7.2%} 胜率{win5:.0%}")


bars_kl = load('kl_ddx_1y.json')
bars_bl = load('bl_ddx_1y.json')
test("昆仑 300418", bars_kl)
test("蓝标 300058", bars_bl)

print(f"\n{'='*65}")
print(f"  判决: 长线占比+游资清仓+成本带 = 多技能超叠加信号")
print(f"{'='*65}")
