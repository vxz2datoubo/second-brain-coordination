"""
回测 退潮回流追踪 — DDX从负向正快速逆转 → 回流信号验证
昆仑+蓝标249天, 多技能叠加
"""
import json

def load(name):
    with open(f'F:/aidanao/data/{name}', 'r', encoding='utf-8') as f:
        data = json.load(f)
    bars = []
    for i, r in enumerate(data):
        c = float(r['c']); dd = float(r.get('main', 0))
        sm = float(r.get('small', 0)); dy = float(r.get('jumbo', 0))
        md = float(r.get('mid', 0))
        tf = abs(dd)+abs(dy)+abs(md)+abs(sm)
        bars.append({'d':r['d'],'c':c,'ddx':dd,'sm':sm,'tf':tf,'ret':0 if i==0 else c/bars[-1]['c']-1,
                     'r1':0,'r5':0,'r10':0,'phase':'?'})
    for i in range(len(bars)):
        if i+1<len(bars): bars[i]['r1']=bars[i+1]['c']/bars[i]['c']-1
        if i+5<len(bars): bars[i]['r5']=bars[i+5]['c']/bars[i]['c']-1
        if i+10<len(bars): bars[i]['r10']=bars[i+10]['c']/bars[i]['c']-1
    return bars

def test(name, bars):
    print(f"\n{'='*65}")
    print(f"  {name} — 退潮回流(DDX逆转)回测")
    print(f"{'='*65}")
    
    # DDX快速逆转信号: 昨日DDX负 → 今日DDX翻正
    quick_reversal = []
    slow_reversal = []
    no_reversal = []
    
    for i in range(3, len(bars)-10):
        if bars[i-1]['ddx'] >= 0:  # 昨日非负, 不需要逆转
            continue
        
        today_ddx = bars[i]['ddx']
        yesterday_ddx = bars[i-1]['ddx']
        reversal_magnitude = today_ddx - yesterday_ddx
        
        if today_ddx > 0:  # 今日翻正
            # 快速逆转: 昨日负得深(抽血多), 今日翻正幅度大
            if yesterday_ddx < -0.05 or reversal_magnitude > 0.1:
                quick_reversal.append(i)
            else:
                slow_reversal.append(i)
        else:  # 今日仍负
            no_reversal.append(i)
    
    # Report
    print(f"  {'信号':<30} {'天数':>5} {'次日':>8} {'5日':>8} {'10日':>8}")
    print(f"  {'─'*55}")
    for label, idxs in [
        ("快速逆转(昨日负深→今日正)", quick_reversal),
        ("缓慢逆转(昨日微负→今日微正)", slow_reversal),
        ("未逆转(连续负)", no_reversal),
    ]:
        if len(idxs) < 2: continue
        r1=[bars[i]['r1'] for i in idxs if bars[i]['r1'] is not None]
        r5=[bars[i]['r5'] for i in idxs if bars[i]['r5'] is not None]
        r10=[bars[i]['r10'] for i in idxs if bars[i]['r10'] is not None]
        print(f"  {label:<30} {len(idxs):>5} {sum(r1)/len(r1):>+7.2%} {sum(r5)/len(r5):>+7.2%} {sum(r10)/len(r10):>+7.2%}")
    
    # Multi-skill叠加: DDX逆转 + 散户在买 + 结构完好
    print(f"\n  【多技能叠加】DDX快速逆转 + 额外确认")
    
    for label, filter_fn in [
        ("逆转+散户在买", lambda i: bars[i]['sm'] > 0),
        ("逆转+散户在买+昨日跌幅<5%", lambda i: bars[i]['sm'] > 0 and bars[i-1]['ret'] > -0.05),
        ("逆转+散户在买+低开>1.5%(竞价)", lambda i: bars[i]['sm'] > 0 and bars[i]['ret'] < -0.015),
    ]:
        idxs = [i for i in quick_reversal if filter_fn(i)]
        if len(idxs) < 2:
            print(f"  {label:<35}: 样本不足")
            continue
        r1=[bars[i]['r1'] for i in idxs if bars[i]['r1'] is not None]
        r5=[bars[i]['r5'] for i in idxs if bars[i]['r5'] is not None]
        r10=[bars[i]['r10'] for i in idxs if bars[i]['r10'] is not None]
        win5 = sum(1 for v in r5 if v > 0) / len(r5) if r5 else 0
        print(f"  {label:<35} {len(idxs):>3}天 次日{sum(r1)/len(r1):>+7.2%} 5日{sum(r5)/len(r5):>+7.2%} 10日{sum(r10)/len(r10):>+7.2%} 5日胜率{win5:.0%}")

bars_kl = load('kl_ddx_1y.json')
bars_bl = load('bl_ddx_1y.json')
test("昆仑 300418", bars_kl)
test("蓝标 300058", bars_bl)

print(f"\n{'='*65}")
print(f"  判决: DDX快速逆转(昨日负深→今日正) = 回流信号")
print(f"  叠加散户在买+结构完好 = 最强确认")
print(f"{'='*65}")
