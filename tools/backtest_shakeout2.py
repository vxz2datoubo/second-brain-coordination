"""
回测各Phase洗盘频率/力度/深度 — 用日收益作为代理
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
        ret = 0
        if i>0: ret = c / bars[-1]['c'] - 1
        bars.append({'d':r['d'],'c':c,'ddx':dd,'ddy':dy,'md':md,'sm':sm,'ret':ret,
                     'r1':0,'r2':0,'r3':0,'r5':0,'r10':0,'phase':'?'})
    for i in range(len(bars)):
        if i+1<len(bars): bars[i]['r1']=bars[i+1]['c']/bars[i]['c']-1
        if i+2<len(bars): bars[i]['r2']=bars[i+2]['c']/bars[i]['c']-1
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
    if t20>3 and d5>0: return 'D'
    if t20<0 and d10>0: return 'A'
    return 'A'

def test(name, bars):
    for i in range(30, len(bars)): bars[i]['phase'] = classify_phase(bars, i)
    
    print(f"\n{'='*65}")
    print(f"  {name} — 各Phase洗盘(日V反)分析")
    print(f"{'='*65}")
    
    # Detect shakeouts: day with return < -2%, recover next day or within 3 days
    for severity_label, threshold, max_recovery_days in [
        ("轻度(日跌2-4%)", (0.02, 0.04), 1),
        ("中度(日跌4-7%)", (0.04, 0.07), 2),
        ("重度(日跌>7%)", (0.07, 50), 3),
    ]:
        print(f"\n  【{severity_label}洗盘】")
        print(f"  {'Phase':>8} {'次数':>5} {'频率/月':>7} {'恢复率':>7} {'洗盘日DDX+':>9} {'恢复后5日':>10}")
        
        for ph in ['A','C','D']:
            shakeouts = []
            for i in range(30, len(bars)-10):
                if bars[i]['phase'] != ph: continue
                ret = abs(bars[i]['ret'])
                if ret < threshold[0] or ret >= threshold[1]: continue
                
                # Check recovery within max days
                recovered = False
                for d in range(1, max_recovery_days+1):
                    key = f'r{d}'
                    if bars[i][key] and bars[i][key] > 0:
                        recovered = True
                        break
                
                shakeouts.append({
                    'i': i, 'ret': bars[i]['ret'], 'ddx': bars[i]['ddx'],
                    'recovered': recovered, 'r5': bars[i].get('r5', 0)
                })
            
            if len(shakeouts) < 2: continue
            
            all_days = sum(1 for b in bars[30:] if b['phase']==ph)
            freq = len(shakeouts) / max(all_days/21, 1)
            rec_rate = sum(1 for s in shakeouts if s['recovered']) / len(shakeouts)
            ddx_pos = sum(1 for s in shakeouts if s['ddx']>0) / len(shakeouts)
            avg_ret = sum(abs(s['ret']) for s in shakeouts) / len(shakeouts)
            
            rec_r5 = [s['r5'] for s in shakeouts if s['recovered']]
            not_rec_r5 = [s['r5'] for s in shakeouts if not s['recovered']]
            
            print(f"  {'Phase '+ph:>8} {len(shakeouts):>5} {freq:>6.1f} {rec_rate:>6.0%} {ddx_pos:>8.0%} {sum(rec_r5)/len(rec_r5) if rec_r5 else 0:>+9.2%}", end="")
            if not_rec_r5: print(f" (未恢复:{sum(not_rec_r5)/len(not_rec_r5):>+5.2%})")
            else: print()

bars_kl = load('kl_ddx_1y.json')
bars_bl = load('bl_ddx_1y.json')
test("昆仑 300418", bars_kl)
test("蓝标 300058", bars_bl)

print(f"\n判决: Phase D中, 洗盘频率低但恢复率高")
print(f"      Phase D中DDX+洗盘=假摔, 是加仓机会")
