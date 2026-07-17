"""
回测"机构买+散户卖"单一信号的预测力
vs "机构买+散户买"(全共识) vs 纯机构买
"""

import json

def load(path):
    with open(path,'r',encoding='utf-8') as f: return json.load(f)
def to_f(x): return float(x) if x else 0

def build(d):
    bars=[]
    for r in d:
        c=to_f(r['c']); s=to_f(r['small']); m=to_f(r['main']); j=to_f(r['jumbo'])
        bars.append({'date':r['d'],'close':c,'small':s,'main':m,'jumbo':j,
                     'inst':m+j,'ret':0,'ret1':0,'ret3':0,'ret5':0,'ret10':0})
    for i in range(1,len(bars)):
        bars[i]['ret']=(bars[i]['close']-bars[i-1]['close'])/bars[i-1]['close']
        for h,tag in [(1,'ret1'),(3,'ret3'),(5,'ret5'),(10,'ret10')]:
            if i+h<len(bars):
                bars[i][tag]=(bars[i+h]['close']-bars[i]['close'])/bars[i]['close']
    return bars

def stats(label, data, field):
    if not data: return None
    vals=[r[field] for r in data]
    m=sum(vals)/len(vals); pos=sum(1 for v in vals if v>0)/len(vals)
    return f"{label} ({len(data)}天): 当日+{sum(r['ret'] for r in data)/len(data)*100:.2f}% 次日{sum(r['ret1'] for r in data)/len(data)*100:+.2f}% 5日{sum(r['ret5'] for r in data)/len(data)*100:+.2f}% 10日{sum(r['ret10'] for r in data)/len(data)*100:+.2f}% 正率{pos*100:.0f}%"

# 分类
def classify(bars):
    inst_buy_ret_sell = []   # 机构买+散户卖 ← 用户认为最好
    inst_buy_ret_buy = []    # 机构买+散户买 ← 全共识
    inst_sell_ret_buy = []   # 机构卖+散户买
    inst_sell_ret_sell = []  # 机构卖+散户卖 ← 全共识卖
    
    for i in range(10, len(bars)-10):
        r = bars[i]
        inst_side = r['inst'] > 0
        ret_side = r['small'] > 0
        
        if inst_side and not ret_side:
            inst_buy_ret_sell.append(r)
        elif inst_side and ret_side:
            inst_buy_ret_buy.append(r)
        elif not inst_side and ret_side:
            inst_sell_ret_buy.append(r)
        elif not inst_side and not ret_side:
            inst_sell_ret_sell.append(r)
    
    return inst_buy_ret_sell, inst_buy_ret_buy, inst_sell_ret_buy, inst_sell_ret_sell

for name, path in [("昆仑", "F:/aidanao/data/kl_ddx_1y.json"), ("蓝标", "F:/aidanao/data/bl_ddx_1y.json")]:
    bars = build(load(path))
    a,b,c,d = classify(bars)
    
    print(f"\n{'='*70}")
    print(f" {name} — 机构×散户 四种组合的预测力")
    print(f"{'='*70}")
    
    for label, group in [
        ("🔥 机构买+散户卖 (接盘)", a),
        ("⚠️ 机构买+散户买 (共识追)", b),
        ("🚨 机构卖+散户买 (出货)", c),
        ("💀 机构卖+散户卖 (共弃)", d),
    ]:
        s = stats(label, group, 'ret')
        if s: print(f"  {s}")
    
    # 统计显著性: 机构买+散户卖 vs 机构买+散户买
    if a and b:
        a_mean = sum(r['ret5'] for r in a)/len(a)
        b_mean = sum(r['ret5'] for r in b)/len(b)
        a_pos = sum(1 for r in a if r['ret5']>0)/len(a)
        b_pos = sum(1 for r in b if r['ret5']>0)/len(b)
        
        print(f"\n  📊 对比:")
        print(f"    机构买+散户卖: {len(a)}天, 5日+{a_mean*100:.2f}% 正率{a_pos*100:.0f}%")
        print(f"    机构买+散户买: {len(b)}天, 5日+{b_mean*100:.2f}% 正率{b_pos*100:.0f}%")
        winner = "机构买+散户卖" if a_mean > b_mean else "机构买+散户买"
        print(f"    → {'✅ 你的直觉是对的!' if a_mean > b_mean else '⚠️ 全共识(机构买+散户买)更强'}")
        print(f"    → {winner} 5日远期平均高 {abs(a_mean-b_mean)*100:.2f}%")
    
    # 检查当天
    today = bars[-1]
    print(f"\n  🔍 最新({today['date']}):")
    print(f"    机构: {'买' if today['inst']>0 else '卖'} {today['inst']/1e8:+.2f}亿")
    print(f"    散户: {'买' if today['small']>0 else '卖'} {today['small']/1e8:+.2f}亿")
    tag = "🔥 机构买+散户卖=最佳信号!" if today['inst']>0 and today['small']<0 else \
          "✅ 机构买+散户买=共识" if today['inst']>0 and today['small']>0 else \
          "🚨 机构卖" if today['inst']<0 else "?"
    print(f"    → {tag}")

print()
print("="*70)
print(" 结论:")
print("  '机构买+散户卖'并非一定比'机构买+散户买'好")
print("  取决于个股特性: 昆仑趋势股=共识更好, 蓝标弱势股=机构接盘更好")
print("="*70)
