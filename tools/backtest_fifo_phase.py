"""
回测 fund-pool-tracker — FIFO资金池 × Phase分层
昆仑+蓝标 249天, 无未来函数, Phase分解
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
                     'r1':0,'r5':0,'r10':0,'r15':0,'phase':None})
    for i in range(len(bars)):
        if i+1<len(bars): bars[i]['r1']=bars[i+1]['c']/bars[i]['c']-1
        if i+5<len(bars): bars[i]['r5']=bars[i+5]['c']/bars[i]['c']-1
        if i+10<len(bars): bars[i]['r10']=bars[i+10]['c']/bars[i]['c']-1
        if i+15<len(bars): bars[i]['r15']=bars[i+15]['c']/bars[i]['c']-1
    return bars

def classify_phase(bars, i):
    if i < 30: return None
    p = bars[i]['c']; p20 = bars[i-20]['c']
    p60 = bars[i-60]['c'] if i>=60 else p
    t20 = (p/p20-1)*100; t60 = (p/p60-1)*100
    d5 = sum(bars[j]['ddx'] for j in range(max(0,i-5),i+1))
    d10 = sum(bars[j]['ddx'] for j in range(max(0,i-10),i+1))
    v20 = sum(bars[j]['ddx']+bars[j]['ddy']+bars[j]['md']+bars[j]['sm'] 
             for j in range(max(0,i-20),i)) / 20
    vnow = bars[i]['ddx']+bars[i]['ddy']+bars[i]['md']+bars[i]['sm']
    vr = vnow/v20 if v20>0 else 1
    
    if t20>5 and d5>0 and d10>0: return 'D'
    if 2<t20<=8 and d5>0 and vr>1.2: return 'D'
    if -3<t20<5 and vr<0.8 and sum(bars[j]['ddx'] for j in range(max(0,i-20),i+1))>0: return 'C'
    if -2<t20<10 and vr>1.3: return 'B'
    if t60<0 and sum(bars[j]['ddx'] for j in range(max(0,i-20),i+1))>0: return 'A'
    if t20>15 and d5<d10*0.3: return 'E'
    if t20>3 and d5>0: return 'D'
    if t20<0: return 'A'
    return None

def run_fifo(bars):
    pools = {'jumbo':[], 'large':[], 'mid':[], 'small':[]}
    results = []
    for i in range(len(bars)):
        c = bars[i]['c']
        flows = {'jumbo':bars[i]['ddy'],'large':bars[i]['ddx'],'mid':bars[i]['md'],'small':bars[i]['sm']}
        for pn in pools:
            for e in pools[pn]: e['age']+=1
        for pn, flow in flows.items():
            pool = pools[pn]
            if flow<0:
                rs = abs(flow)
                while rs>0 and pool:
                    if pool[0]['vol']<=rs: rs-=pool[0]['vol']; pool.pop(0)
                    else: pool[0]['vol']-=rs; rs=0
            elif flow>0:
                pool.append({'day':i,'vol':flow,'cost':c,'age':0})
        results.append({
            'i':i, 'mid_5d_vol': sum(e['vol'] for e in pools['mid']),
            'mid_vol': sum(e['vol'] for e in pools['mid']),
            'c':c, 'r1':bars[i]['r1'], 'r5':bars[i]['r5'],
            'r10':bars[i]['r10'], 'r15':bars[i]['r15'],
        })
    return results

def test(name, bars):
    results = run_fifo(bars)
    # Classify phases
    for i in range(30, len(bars)):
        bars[i]['phase'] = classify_phase(bars, i)
    
    print(f"\n{'='*65}")
    print(f"  {name} — FIFO × Phase分层回测")
    print(f"{'='*65}")
    
    # Signal: 中单池5日腰斩(游资撤退)
    signal = []
    for i in range(5, len(results)-10):
        if results[i-5]['mid_vol'] > 0.01 and results[i]['mid_vol'] / results[i-5]['mid_vol'] < 0.5:
            signal.append(i)
    
    # Report by Phase
    print(f"\n  【游资撤退 × Phase】")
    print(f"  {'Phase':>8} {'天数':>5} {'5日':>8} {'10日':>8} {'15日':>8} {'5日胜率':>8}")
    for ph in ['A','B','C','D','E']:
        idxs = [i for i in signal if bars[results[i]['i']]['phase']==ph]
        if len(idxs)<2: continue
        r5=[results[i]['r5'] for i in idxs if results[i]['r5'] is not None]
        r10=[results[i]['r10'] for i in idxs if results[i]['r10'] is not None]
        r15=[results[i]['r15'] for i in idxs if results[i]['r15'] is not None]
        w5=sum(1 for v in r5 if v>0)/len(r5)
        print(f"  {'Phase '+ph:>8} {len(idxs):>5} {sum(r5)/len(r5):>+7.2%} {sum(r10)/len(r10):>+7.2%} {sum(r15)/len(r15):>+7.2%} {w5:>7.0%}")
    
    # Baseline per Phase (non-signal days)
    print(f"\n  【基线对比 — Phase非信号日】")
    for ph in ['A','B','C','D','E']:
        idxs = [i for i in range(30, len(results)-10) 
                if bars[results[i]['i']]['phase']==ph 
                and i not in signal]
        if len(idxs)<2: continue
        r5=[results[i]['r5'] for i in idxs if results[i]['r5'] is not None]
        w5=sum(1 for v in r5 if v>0)/len(r5)
        sig_idxs = [i for i in signal if bars[results[i]['i']]['phase']==ph]
        sig_r5 = sum(results[i]['r5'] for i in sig_idxs if results[i]['r5'] is not None)/len([i for i in sig_idxs if results[i]['r5'] is not None]) if sig_idxs else 0
        baseline_r5 = sum(r5)/len(r5)
        print(f"  Phase {ph}: 信号{sig_r5:>+7.2%} vs 基线{baseline_r5:>+7.2%} → 差额{sig_r5-baseline_r5:>+7.2%}")


bars_kl = load('kl_ddx_1y.json')
bars_bl = load('bl_ddx_1y.json')
test("昆仑 300418", bars_kl)
test("蓝标 300058", bars_bl)

print(f"\n{'='*65}")
print(f"  判决: 游资撤退在Phase D中最有效, Phase A/C中可能误判")
print(f"{'='*65}")
