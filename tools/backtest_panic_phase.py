"""
回测 market-panic-index — Phase × 恐慌 × 各单池行为
昆仑+蓝标 249天
"""
import json

def load(name):
    with open(f'F:/aidanao/data/{name}', 'r', encoding='utf-8') as f:
        data = json.load(f)
    bars = []
    for i, r in enumerate(data):
        c = float(r['c']); dd = float(r.get('main',0))
        dy = float(r.get('jumbo',0)); md = float(r.get('mid',0))
        sm = float(r.get('small',0))
        bars.append({'d':r['d'],'c':c,'ddx':dd,'ddy':dy,'md':md,'sm':sm,
                     'r1':0,'r3':0,'r5':0,'r10':0,'phase':'?'})
    for i in range(len(bars)):
        if i+1<len(bars): bars[i]['r1']=bars[i+1]['c']/bars[i]['c']-1
        if i+3<len(bars): bars[i]['r3']=bars[i+3]['c']/bars[i]['c']-1
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
    if 2<t20<=8 and d5>0 and vr>1.2: return 'D'
    if -3<t20<5 and vr<0.8 and sum(bars[j]['ddx'] for j in range(max(0,i-20),i+1))>0: return 'C'
    if t20>15 and d5<d10*0.3: return 'E'
    if t20>3 and d5>0: return 'D'
    if t20<0 and d10>0: return 'A'
    return 'A'

def panic_score(bars, i):
    """Compute panic score 0-100"""
    score = 0
    # DDX panic: how negative vs recent average
    avg_ddx = sum(abs(bars[j]['ddx']) for j in range(max(0,i-5), i)) / max(i-max(0,i-5), 1)
    avg_ddx = max(avg_ddx, 0.01)
    if bars[i-1]['ddx'] < -1.5 * avg_ddx: score += 20
    elif bars[i-1]['ddx'] < -avg_ddx: score += 10
    
    # DDY panic (特大单)
    avg_ddy = sum(abs(bars[j]['ddy']) for j in range(max(0,i-5), i)) / max(i-max(0,i-5), 1)
    avg_ddy = max(avg_ddy, 0.01)
    if bars[i-1]['ddy'] < -2 * avg_ddy: score += 20
    elif bars[i-1]['ddy'] < -avg_ddy: score += 10
    
    # Price panic: big drop (use direct price comparison)
    ret_today = (bars[i]['c'] / max(bars[i-1]['c'], 0.01) - 1) if i > 0 else 0
    if ret_today < -0.05: score += 30
    elif ret_today < -0.03: score += 15
    
    # Volume: surge
    vol5 = sum(abs(bars[j]['ddx'])+abs(bars[j]['ddy'])+abs(bars[j]['md'])+abs(bars[j]['sm']) for j in range(max(0,i-5), i)) / 5
    vol20 = sum(abs(bars[j]['ddx'])+abs(bars[j]['ddy'])+abs(bars[j]['md'])+abs(bars[j]['sm']) for j in range(max(0,i-20), i)) / 20
    if vol5 > vol20 * 1.5: score += 15
    elif vol5 > vol20 * 1.2: score += 8
    
    # Duration: consecutive panic days
    days = 0
    for j in range(i-1, max(0,i-5), -1):
        rj = (bars[j]['c'] / max(bars[j-1]['c'], 0.01) - 1) if j > 0 else 0
        if rj < -0.02: days += 1
        else: break
    if days >= 3: score = min(score * 0.5, 40)  # 3+ days = fatigue
    elif days >= 2: score = min(score * 0.7, 55)
    
    return min(score, 100)

def test(name, bars):
    for i in range(30, len(bars)): bars[i]['phase'] = classify_phase(bars, i)
    
    print(f"\n{'='*65}")
    print(f"  {name} — Phase × 恐慌 × 各单池")
    print(f"{'='*65}")
    
    # Segment by phase and panic level
    for ph in ['A','D']:
        print(f"\n  【Phase {ph} · 恐慌级别 → 各单池行为 + 前瞻回报】")
        print(f"  {'恐慌级':>8} {'天数':>5} {'特大单':>8} {'大单':>8} {'中单':>8} {'小单':>8} {'1日':>8} {'5日':>8} {'10日':>8}")
        
        ph_bars = [(i, panic_score(bars, i)) for i in range(35, len(bars)-10) if bars[i]['phase']==ph]
        
        for level_label, lo, hi in [
            ("轻度(20-40)", 20, 40),
            ("中度(40-60)", 40, 60),
            ("高度(60-80)", 60, 80),
            ("极度(80+)", 80, 200),
        ]:
            idxs = [i for i, ps in ph_bars if lo <= ps < hi]
            if len(idxs) < 2: continue
            
            ddy_avg = sum(bars[i]['ddy'] for i in idxs) / len(idxs)
            ddx_avg = sum(bars[i]['ddx'] for i in idxs) / len(idxs)
            md_avg = sum(bars[i]['md'] for i in idxs) / len(idxs)
            sm_avg = sum(bars[i]['sm'] for i in idxs) / len(idxs)
            r1 = [bars[i]['r1'] for i in idxs if bars[i]['r1'] is not None]
            r5 = [bars[i]['r5'] for i in idxs if bars[i]['r5'] is not None]
            r10 = [bars[i]['r10'] for i in idxs if bars[i]['r10'] is not None]
            
            print(f"  {level_label:<13} {len(idxs):>5} {ddy_avg:>+7.1f} {ddx_avg:>+7.1f} {md_avg:>+7.1f} {sm_avg:>+7.1f} {sum(r1)/len(r1):>+7.2%} {sum(r5)/len(r5):>+7.2%} {sum(r10)/len(r10):>+7.2%}")
    
    # Cross-phase: 恐慌 + 特大单行为 × Phase
    print(f"\n  【恐慌日+特大单行为 × Phase】")
    for ph in ['A','D']:
        for label, jumbo_filter in [
            ("特大单也在卖(DDY<-5)", lambda b: b['ddy'] < -5),
            ("特大单微卖(DDY -5~0)", lambda b: -5 <= b['ddy'] < 0),
            ("特大单在买(DDY>0)", lambda b: b['ddy'] > 0),
        ]:
            idxs = [i for i in range(35, len(bars)-10) 
                   if bars[i]['phase']==ph and panic_score(bars, i)>=40 and jumbo_filter(bars[i])]
            if len(idxs) < 2: continue
            r5 = [bars[i]['r5'] for i in idxs if bars[i]['r5'] is not None]
            r10 = [bars[i]['r10'] for i in idxs if bars[i]['r10'] is not None]
            win5 = sum(1 for v in r5 if v>0) / len(r5)
            print(f"  Phase {ph} {label:<25}: {len(idxs)}天 5日{sum(r5)/len(r5):>+7.2%} 10日{sum(r10)/len(r10):>+7.2%} 胜率{win5:.0%}")


bars_kl = load('kl_ddx_1y.json')
bars_bl = load('bl_ddx_1y.json')
test("昆仑 300418", bars_kl)
test("蓝标 300058", bars_bl)
print(f"\n判决: Phase D恐慌+特大单在买=最强反向信号")
print(f"      Phase D恐慌+特大单也在卖=不是反向,是真跌")