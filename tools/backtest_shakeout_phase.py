"""
回测各Phase洗盘(Shakeout)的频率/力度/深度
昆仑+蓝标 249天
Shakeout定义: 日内从高点到低点回落>3%, 然后日内或次日恢复
"""
import json

def load(name):
    with open(f'F:/aidanao/data/{name}', 'r', encoding='utf-8') as f:
        data = json.load(f)
    bars = []
    for i, r in enumerate(data):
        c = float(r['c']); o = float(r.get('o', r.get('open', c)))
        h = float(r.get('h', r.get('high', c))); l = float(r.get('l', r.get('low', c)))
        dd = float(r.get('main', 0)); dy = float(r.get('jumbo', 0))
        md = float(r.get('mid', 0)); sm = float(r.get('small', 0))
        bars.append({'d':r['d'],'c':c,'o':o,'h':h,'l':l,'ddx':dd,'ddy':dy,'md':md,'sm':sm,
                     'r1':0,'r5':0,'r10':0,'phase':'?'})
    for i in range(len(bars)):
        if i+1<len(bars): bars[i]['r1']=bars[i+1]['c']/bars[i]['c']-1
        if i+5<len(bars): bars[i]['r5']=bars[i+5]['c']/bars[i]['c']-1
        if i+10<len(bars): bars[i]['r10']=bars[i+10]['c']/bars[i]['c']-1
    return bars

def classify_phase(bars, i):
    if i<30: return '?'
    p=bars[i]['c']; p20=bars[i-20]['c']; p60=bars[i-60]['c'] if i>=60 else p
    t20=(p/p20-1)*100; t60=(p/p60-1)*100
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

def find_shakeouts(bars):
    """Detect shakeout events"""
    events = []
    for i in range(5, len(bars)-5):
        # Intraday shakeout: high→low > X% drop
        drop = (bars[i]['h'] - bars[i]['l']) / bars[i]['c']
        
        # Classify by severity
        if drop < 0.03: continue  # minor, skip
        
        severity = 'MILD' if drop < 0.05 else 'MODERATE' if drop < 0.08 else 'SEVERE'
        
        # Check recovery: close >= open (intraday recovery) or next day up
        recovered_same_day = bars[i]['c'] >= bars[i]['o']
        recovered_next = bars[i]['r1'] > 0 if bars[i]['r1'] else False
        recovered = recovered_same_day or recovered_next
        
        # Depth: how deep from high
        depth = (bars[i]['h'] - bars[i]['l']) / bars[i]['h'] * 100
        
        # DDX during shakeout
        ddx_signal = bars[i]['ddx']
        
        events.append({
            'i': i, 'drop': drop, 'depth': depth, 'severity': severity,
            'recovered': recovered, 'ddx': ddx_signal,
            'phase': bars[i]['phase'],
            'high': bars[i]['h'], 'low': bars[i]['l'], 'close': bars[i]['c'],
            'r1': bars[i]['r1'], 'r5': bars[i]['r5'] if bars[i]['r5'] else 0
        })
    return events

def test(name, bars):
    for i in range(30, len(bars)): bars[i]['phase'] = classify_phase(bars, i)
    events = find_shakeouts(bars)
    
    print(f"\n{'='*65}")
    print(f"  {name} — 各Phase洗盘分析")
    print(f"{'='*65}")
    
    # Phase distribution
    for ph in ['A','C','D']:
        ph_events = [e for e in events if e['phase']==ph]
        if len(ph_events)<2: continue
        
        recovered_events = [e for e in ph_events if e['recovered']]
        rec_rate = len(recovered_events)/len(ph_events)
        
        mild = [e for e in ph_events if e['severity']=='MILD']
        mod = [e for e in ph_events if e['severity']=='MODERATE']
        sev = [e for e in ph_events if e['severity']=='SEVERE']
        
        avg_depth = sum(e['depth'] for e in ph_events)/len(ph_events)
        avg_drop = sum(e['drop'] for e in ph_events)/len(ph_events)
        
        # Post-shakeout returns
        rec_5d = [e['r5'] for e in recovered_events]
        not_rec_5d = [e['r5'] for e in ph_events if not e['recovered']]
        
        # Frequency: shakeouts per month (21 trading days)
        all_days_in_phase = sum(1 for b in bars if b['phase']==ph)
        freq_per_month = len(ph_events) / max(all_days_in_phase/21, 1)
        
        print(f"\n  Phase {ph}:")
        print(f"    {len(ph_events)}次洗盘 in {all_days_in_phase}天 → 频率{freq_per_month:.1f}次/月")
        print(f"    恢复率: {len(recovered_events)}/{len(ph_events)}={rec_rate:.0%}")
        print(f"    平均振幅: {avg_drop:.1%} | 平均深度: {avg_depth:.1f}%")
        print(f"    轻度{mild_evts}/{mod_evts}/{sev_evts} = {len(mild)}/{len(mod)}/{len(sev)}"
              if (mild_evts:=len(mild)) or (mod_evts:=len(mod)) or (sev_evts:=len(sev)) else "")
        
        if rec_5d: print(f"    恢复后5日: {sum(rec_5d)/len(rec_5d):>+7.2%}")
        if not_rec_5d: print(f"    未恢复后5日: {sum(not_rec_5d)/len(not_rec_5d):>+7.2%}")
        
        # DDX during shakeout
        ddx_pos = sum(1 for e in ph_events if e['ddx']>0)
        print(f"    洗盘日DDX正: {ddx_pos}/{len(ph_events)}={ddx_pos/len(ph_events):.0%}")
        
        # Recent 5 shakeouts detail
        recent = sorted(ph_events[-5:], key=lambda x: x['i'])
        if recent:
            print(f"    最近{min(5,len(recent))}次振幅: " + 
                  " ".join([f"{e['drop']:.1%}" for e in recent]))

    # Cross-phase comparison
    print(f"\n  【Phase间对比】")
    print(f"  {'Phase':>8} {'次数/月':>8} {'恢复率':>8} {'均振幅':>8} {'均深度':>8} {'恢复后5日':>10}")
    for ph in ['A','C','D']:
        ph_events = [e for e in events if e['phase']==ph]
        if len(ph_events)<2: continue
        rec = [e for e in ph_events if e['recovered']]
        all_days = sum(1 for b in bars if b['phase']==ph)
        freq = len(ph_events) / max(all_days/21, 1)
        rec5 = [e['r5'] for e in rec] if rec else [0]
        print(f"  {'Phase '+ph:>8} {freq:>7.1f} {len(rec)/len(ph_events):>7.0%} {sum(e['drop'] for e in ph_events)/len(ph_events):>7.1%} {sum(e['depth'] for e in ph_events)/len(ph_events):>7.1f}% {sum(rec5)/len(rec5):>+9.2%}")

bars_kl = load('kl_ddx_1y.json')
bars_bl = load('bl_ddx_1y.json')
test("昆仑 300418", bars_kl)
test("蓝标 300058", bars_bl)

print(f"\n判决: Phase D是否适合洗盘?")
print(f"      看频率/恢复率/恢复后收益 vs Phase A")
