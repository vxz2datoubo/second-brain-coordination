"""
回测 rotation-tide-reversal — T+1解锁→旋转门反向
用昆仑249天真DDX数据验证: 昨日DDX负(被抽血)→今日回流概率
多技能叠加: DDX趋势+Phase D结构+锚定区间
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
            bars.append({'d':r['d'],'c':c,'ddx':dd,'ddy':dy,'sm':sm,'tf':tf,
                         'ret':0,'r1':0,'r5':0,'r10':0})
        else:
            ret = c/bars[-1]['c']-1
            bars.append({'d':r['d'],'c':c,'ddx':dd,'ddy':dy,'sm':sm,'tf':tf,
                         'ret':ret,'r1':0,'r5':0,'r10':0})
    for i in range(len(bars)):
        if i+1<len(bars): bars[i]['r1']=bars[i+1]['c']/bars[i]['c']-1
        if i+5<len(bars): bars[i]['r5']=bars[i+5]['c']/bars[i]['c']-1
        if i+10<len(bars): bars[i]['r10']=bars[i+10]['c']/bars[i]['c']-1
    return bars

def backtest(name, bars):
    """Test: 昨日DDX显著负(被抽血) + DDX趋势改善 → 今日回流"""
    print(f"\n{'='*60}")
    print(f"  {name} — 旋转门潮汐回测")
    print(f"{'='*60}")
    
    tide_signals = []  # 强潮汐日
    weak_signals = []  # 弱潮汐(DDX负但没改善)
    baseline_down = []  # 任意DDX负日
    
    for i in range(3, len(bars)-5):
        # 昨日DDX负(被抽血)
        if bars[i-1]['ddx'] >= 0:
            continue
        baseline_down.append(i)
        
        # 潮汐条件:
        # ① 昨日DDX显著负(<-0.1 或 <-tf*2%)
        yesterday_weak = abs(bars[i-1]['ddx']) > 0.02 * bars[i-1]['tf'] or bars[i-1]['ddx'] < -0.05
        
        # ② DDX趋势改善: 前天→昨天→今天, DDX在回升
        ddx_trend = (bars[i-1]['ddx'] > bars[i-2]['ddx'] and 
                     bars[i]['ddx'] > bars[i-1]['ddx'])
        
        # ③ 价格回调低点 > 前日低点 (Phase D结构) — 用昨日低点近似
        #    这里用"昨日不是暴跌日"作为近似
        not_crash = bars[i-1]['ret'] > -0.05  # 昨天跌幅<5%
        
        if yesterday_weak and ddx_trend and not_crash:
            tide_signals.append(i)
        elif not ddx_trend:
            weak_signals.append(i)
    
    def report(label, idxs):
        if not idxs: return None
        r1=[bars[i]['r1'] for i in idxs if bars[i]['r1'] is not None]
        r5=[bars[i]['r5'] for i in idxs if bars[i]['r5'] is not None]
        r10=[bars[i]['r10'] for i in idxs if bars[i]['r10'] is not None]
        avg1=sum(r1)/len(r1); avg5=sum(r5)/len(r5); avg10=sum(r10)/len(r10)
        hit=sum(1 for x in r1 if x>0)
        print(f"  {label:<30} {len(idxs):>3}天 次日{avg1:>+7.2%} 5日{avg5:>+7.2%} 10日{avg10:>+7.2%} 翻红率{hit}/{len(r1)}={hit/len(r1):.0%}")
        return avg1,avg5,avg10,len(idxs)
    
    report("潮汐回流(DDX负+趋势改善+非崩)", tide_signals)
    report("弱潮汐(DDX负+无改善)", weak_signals)
    report("基线(任意DDX负日)", baseline_down)
    
    # Multi-signal叠加
    print(f"\n  【多技能叠加】潮汐+额外确认")
    # 潮汐 + DDX今天翻正
    tide_ddx_pos = [i for i in tide_signals if bars[i]['ddx'] > 0]
    report("  潮汐+DDX今已翻正", tide_ddx_pos)
    
    # 潮汐 + 散户在买(小单正)
    tide_retail = [i for i in tide_signals if bars[i]['sm'] > 0]
    report("  潮汐+散户在买", tide_retail)
    
    # 潮汐 + DDX翻正 + 散户在买(最强)
    tide_perfect = [i for i in tide_signals if bars[i]['ddx']>0 and bars[i]['sm']>0]
    report("  潮汐+DDX正+散户买(完美)", tide_perfect)
    
    # Day2效果: 潮汐后第2天(验证回流持续性)
    tide_d2 = [i+1 for i in tide_signals if i+1<len(bars)-5]
    print(f"\n  【潮汐后Day2持续性】")
    r1_d2=[bars[i]['ret'] for i in tide_d2]
    hit2=sum(1 for x in r1_d2 if x>0)
    print(f"  潮汐次日翻红率: {hit2}/{len(r1_d2)}={hit2/len(r1_d2):.0%}")

bars_kl = load('kl_ddx_1y.json')
bars_bl = load('bl_ddx_1y.json')
backtest("昆仑 300418", bars_kl)
backtest("蓝标 300058", bars_bl)

print(f"\n{'='*60}")
print(f"  判决: 潮汐回流信号质量(翻红率>60%有效, >70%强效)")
print(f"{'='*60}")
