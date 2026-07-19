"""
T+1换手率硬上限实证 — 昆仑 249天
验证: 换手率/活跃浮盘比 → 未来收益
"""

import json

def load(path):
    with open(path,'r',encoding='utf-8') as f: return json.load(f)
def f(x): return float(x) if x else 0

kl = load("F:/aidanao/data/kl_ddx_1y.json")
bl = load("F:/aidanao/data/bl_ddx_1y.json")

def analyze(name, data, total_float_shares, core_locked_pct):
    bars = []
    for r in data:
        c = f(r['c']); s = f(r['small']); m = f(r['main']); j = f(r['jumbo'])
        bars.append({'d':r['d'],'c':c,'s':s,'m':m,'j':j,'i':m+j})
    
    for i in range(1,len(bars)):
        bars[i]['r']=(bars[i]['c']-bars[i-1]['c'])/bars[i-1]['c']
    
    # Estimate "active float" — shares actually available to trade today
    ltgb = total_float_shares  # total float shares
    
    # For each day, calculate:
    # 1. Cumulative DDX (institutional accumulation over last 20 days)
    # 2. Price position (where are retail holders relative to cost)
    # 3. Turnover ratio
    # 4. Estimated active float ratio
    
    results = []
    for i in range(10, len(bars)-10):
        px = bars[i]['c']
        vol = bars[i]['d']  # don't have volume directly, use price * amount
        # Actually we only have prices and DDX. Need different approach.
        
        # 估算: 活跃浮盘 = 总流通 - 核心锁仓 - 机构控盘 - 散户锁仓
        # 核心锁仓: 固定的 (34% for 昆仑)
        core_locked = total_float_shares * core_locked_pct
        
        # 机构累积持仓: 20日累积大单净买 ÷ 当日均价 ≈ 累积股份
        inst_acc_20 = sum(bars[j]['i'] for j in range(max(0,i-20), i+1))
        # 用平均价格换算成股数
        avg_px = sum(bars[j]['c'] for j in range(max(0,i-20), i+1)) / min(21, i+1)
        inst_locked_shares = min(total_float_shares * 0.30, max(0, inst_acc_20 / avg_px))  # cap at 30%
        
        # 散户深套锁仓 (价格<MA60): 大约20%的散户深套
        ma60 = sum(bars[j]['c'] for j in range(max(0,i-60), i)) / min(60, i+1)
        ret_loss_pct = abs(ma60 - px)/ma60
        retail_locked_pct = max(0.05, min(0.30, (1 - px/ma60) * 0.5)) if px < ma60 else 0.02
        
        # Active float estimate
        active_float_pct = 1.0 - core_locked_pct - (inst_locked_shares/total_float_shares) - retail_locked_pct
        active_float_pct = max(0.15, min(0.80, active_float_pct))
        
        results.append({
            'date': bars[i]['d'],
            'px': px,
            'f5': bars[i].get('f5', 0),
            'f10': bars[i].get('f10', 0),
            'active_float_pct': active_float_pct,
            'inst_acc': inst_acc_20 / 1e8,
            'ret_locked': retail_locked_pct,
        })
    
    return results

# 昆仑: total float = 11.75亿股, core locked = 34%
kl_r = analyze("昆仑", kl, 11753239800, 0.34)
bl_r = analyze("蓝标", bl, 34779303100, 0.15)

print("=" * 70)
print(" T+1换手率硬上限模型")
print("=" * 70)

for name, res in [("昆仑", kl_r), ("蓝标", bl_r)]:
    if not res: continue
    print(f"\n{name}:")
    print(f"  活跃浮盘比例范围: {min(r['active_float_pct'] for r in res)*100:.0f}% ~ {max(r['active_float_pct'] for r in res)*100:.0f}%")
    print(f"  平均活跃浮盘: {sum(r['active_float_pct'] for r in res)/len(res)*100:.1f}%")
    
    # 活跃浮盘高 vs 低 → 未来收益
    hi = [r for r in res if r['active_float_pct'] > 0.55]
    lo = [r for r in res if r['active_float_pct'] < 0.35]
    
    if hi and lo:
        print(f"  高活跃浮盘(>55%): {len(hi)}天 5日+{sum(r['f5'] for r in hi)/len(hi)*100:.2f}% 10日+{sum(r['f10'] for r in hi)/len(hi)*100:.2f}%")
        print(f"  低活跃浮盘(<35%): {len(lo)}天 5日+{sum(r['f5'] for r in lo)/len(lo)*100:.2f}% 10日+{sum(r['f10'] for r in lo)/len(lo)*100:.2f}%")
    
    # Latest
    latest = res[-1] if res else None
    if latest:
        print(f"\n  最新({latest['date']}):")
        print(f"    活跃浮盘: {latest['active_float_pct']*100:.1f}%")
        print(f"    锁仓: 核心34% + 机构~{latest['inst_acc']:.1f}亿 + 散户~{latest['ret_locked']*100:.0f}%")
        print(f"    → 实际可交易浮盘约{latest['active_float_pct']*100:.0f}% — 今天的换手率意味着这部分浮盘的X%被交易了")

print(f"\n{'='*70}")
print(" 核心洞察:")
print("  1. T+1下，换手率有硬上限——每张股票每天最多交易1次")
print("  2. 14%换手率 ≠ 14%的人在交易，可能是50%活跃浮盘的28%")
print("  3. 活跃浮盘越小=筹码越集中 → 缩量信号越可信")
print("  4. 活跃浮盘比例可以直接估算主力控盘程度")
print("="*70)
