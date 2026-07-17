"""
回测 triple-decision-trees — Phase识别准确率 + 决策树分枝预测力
昆仑+蓝标各249天真DDX数据, 无未来函数
"""
import json, math

def load(name):
    with open(f'F:/aidanao/data/{name}', 'r', encoding='utf-8') as f:
        data = json.load(f)
    bars = []
    for i, r in enumerate(data):
        c = float(r['c']); dd = float(r.get('main', 0))
        dy = float(r.get('jumbo', 0)); mid = float(r.get('mid', 0))
        sm = float(r.get('small', 0)); tf = abs(dd)+abs(dy)+abs(mid)+abs(sm)
        if i == 0:
            bars.append({'d': r['d'], 'c': c, 'ddx': dd, 'ddy': dy, 'tf': tf,
                         'ret': 0, 'ret_1d': 0, 'ret_5d': 0, 'ret_10d': 0, 'ret_20d': 0,
                         'nom_vol': 1.0, 'phase': '?', 'branch': '?'})
        else:
            ret = c / bars[-1]['c'] - 1
            bars.append({'d': r['d'], 'c': c, 'ddx': dd, 'ddy': dy, 'tf': tf,
                         'ret': ret, 'ret_1d': 0, 'ret_5d': 0, 'ret_10d': 0, 'ret_20d': 0,
                         'nom_vol': tf / max(bars[-1]['tf'], 0.01),
                         'phase': '?', 'branch': '?'})
    for i in range(len(bars)):
        if i+1 < len(bars): bars[i]['ret_1d'] = bars[i+1]['c']/bars[i]['c']-1
        if i+5 < len(bars): bars[i]['ret_5d'] = bars[i+5]['c']/bars[i]['c']-1
        if i+10 < len(bars): bars[i]['ret_10d'] = bars[i+10]['c']/bars[i]['c']-1
        if i+20 < len(bars): bars[i]['ret_20d'] = bars[i+20]['c']/bars[i]['c']-1
    return bars

def classify_phase(bars, i, active_ratio):
    """Identify Wyckoff phase from DDX+price+volume (no future leak)"""
    if i < 30: return '?', '?'
    
    # Compute rolling metrics (only past data)
    p = bars[i]['c']
    p20 = bars[i-20]['c'] if i >= 20 else p
    p60 = bars[i-60]['c'] if i >= 60 else p
    trend_20d = (p / p20 - 1) * 100  # % change over 20 days
    trend_60d = (p / p60 - 1) * 100
    
    # DDX stats
    ddx5_sum = sum(bars[j]['ddx'] for j in range(max(0,i-5), i+1))
    ddx10_sum = sum(bars[j]['ddx'] for j in range(max(0,i-10), i+1))
    ddx20_sum = sum(bars[j]['ddx'] for j in range(max(0,i-20), i+1))
    
    # Volume stats
    vol5_avg = sum(bars[j]['nom_vol'] for j in range(max(0,i-5), i)) / 5
    vol20_avg = sum(bars[j]['nom_vol'] for j in range(max(0,i-20), i)) / 20
    vol_now = bars[i]['nom_vol']
    vol_ratio = vol_now / vol20_avg if vol20_avg > 0 else 1.0
    vol_trend = vol5_avg / vol20_avg if vol20_avg > 0 else 1.0  # recent vs long
    
    # DDY (seasoned activity)
    ddy5 = sum(bars[j]['ddy'] for j in range(max(0,i-5), i+1))
    
    # Price volatility
    recent_volatility = sum(abs(bars[j]['ret']) for j in range(max(0,i-10), i+1)) / 10
    
    # === Phase Classification ===
    
    # Phase E: Distribution (天量滞涨 + DDX weakening + high price)
    if trend_20d > 15 and vol_ratio > 1.5 and ddx5_sum < ddx10_sum * 0.3:
        return 'E', 'distribution'
    
    # Phase D: Markup (price rising + DDX strong + volume up)
    if trend_20d > 5 and ddx5_sum > 0 and ddx10_sum > ddx5_sum * 1.5:
        # Sub-branches of Phase D
        ddy_negative = ddy5 < -0.5 * abs(ddx5_sum) if ddx5_sum else False
        vol_spike = vol_ratio > 2.0
        
        if ddy_negative and ddx5_sum > 0:
            return 'D', 'D3_seasoned_pressure'  # Seasoned压盘
        elif vol_spike and ddx5_sum > 0:
            return 'D', 'D1_continue_push'      # 继续推进
        elif ddx5_sum > 0:
            return 'D', 'D1_continue_push'
        else:
            return 'D', 'D4_distribute'
    
    # Phase C: Shakeout (price flat/slightly down + volume shrinking + DDX mixed)
    if -3 < trend_20d < 8 and vol_trend < 0.8 and vol_now < vol20_avg * 0.7:
        if ddx5_sum > 0:
            return 'C', 'C1_shakeout_done'  # 洗盘完成
        else:
            return 'C', 'C2_extend_shakeout'
    
    # Phase B: Testing (volume spike + price flat/slight up)
    if -2 < trend_20d < 10 and vol_ratio > 1.3 and vol_ratio < 2.0:
        if ddx5_sum > 0:
            return 'B', 'B1_light_pressure'
        else:
            return 'B', 'B2_heavy_pressure'
    
    # Phase A: Accumulation (low price + low volume + DDX slightly positive)
    if trend_60d < 0 and vol_now < vol20_avg * 0.8 and ddx20_sum > 0:
        return 'A', 'A1_accumulating'
    if trend_20d < 3 and vol_now < vol20_avg * 0.7:
        return 'A', 'A1_accumulating'
    
    # Not clearly in any phase
    if trend_20d > 3 and ddx5_sum > 0:
        return 'D', 'D1_continue_push'
    elif trend_20d < -5:
        return 'A', 'A1_accumulating'
    else:
        return '?', '?'


def run_backtest(name, bars, active_ratio):
    """Classify phases and test forward returns"""
    print(f"\n{'='*70}")
    print(f"  {name} — 决策树Phase识别回测 (活跃比={active_ratio})")
    print(f"{'='*70}")
    
    # Classify all bars
    phase_groups = {'A': [], 'B': [], 'C': [], 'D': [], 'E': [], '?': []}
    branch_groups = {}
    
    for i in range(30, len(bars)-20):
        phase, branch = classify_phase(bars, i, active_ratio)
        bars[i]['phase'] = phase
        bars[i]['branch'] = branch
        if phase in phase_groups:
            phase_groups[phase].append(i)
        if branch not in branch_groups:
            branch_groups[branch] = []
        branch_groups[branch].append(i)
    
    # Phase-level results
    print(f"\n  【Phase级别】")
    print(f"  {'Phase':>8} {'天数':>5} {'5日':>8} {'10日':>8} {'20日':>8} {'DDX均值':>10}")
    
    for ph in ['A', 'B', 'C', 'D', 'E']:
        idxs = phase_groups[ph]
        if not idxs: continue
        r5 = [bars[i]['ret_5d'] for i in idxs if bars[i]['ret_5d'] is not None]
        r10 = [bars[i]['ret_10d'] for i in idxs if bars[i]['ret_10d'] is not None]
        r20 = [bars[i]['ret_20d'] for i in idxs if bars[i]['ret_20d'] is not None]
        ddx_avg = sum(abs(bars[i]['ddx']) for i in idxs) / len(idxs)
        print(f"  {'Phase '+ph:>8} {len(idxs):>5} {sum(r5)/len(r5):>+7.2%} {sum(r10)/len(r10):>+7.2%} {sum(r20)/len(r20):>+7.2%} {ddx_avg:>10.4f}")
    
    # Branch-level results (Phase D only, most actionable)
    print(f"\n  【Phase D 分枝级别】(最可操作的阶段)")
    print(f"  {'分枝':<25} {'天数':>5} {'5日':>8} {'10日':>8} {'20日':>8}")
    
    d_branches = [k for k in branch_groups if k.startswith('D')]
    for br in sorted(d_branches):
        idxs = branch_groups[br]
        if len(idxs) < 2: continue
        r5 = [bars[i]['ret_5d'] for i in idxs if bars[i]['ret_5d'] is not None]
        r10 = [bars[i]['ret_10d'] for i in idxs if bars[i]['ret_10d'] is not None]
        r20 = [bars[i]['ret_20d'] for i in idxs if bars[i]['ret_20d'] is not None]
        print(f"  {br:<25} {len(idxs):>5} {sum(r5)/len(r5):>+7.2%} {sum(r10)/len(r10):>+7.2%} {sum(r20)/len(r20):>+7.2%}")
    
    # Multi-signal叠加: Phase D1 + additional confirmations
    print(f"\n  【多技能叠加验证】Phase D + 额外确认信号")
    
    # D1 + DDX strong
    d1_strong = [i for i in phase_groups['D'] 
                 if bars[i]['branch'] == 'D1_continue_push' 
                 and bars[i]['ddx'] > 0.02 * bars[i]['tf']]
    # D1 + DDX strong + DDY not negative (seasoned not being sold)
    d1_perfect = [i for i in d1_strong 
                  if bars[i]['ddy'] > -0.01 * bars[i]['tf']]
    # D3: seasoned pressure (institution using old shares to压盘)
    d3 = [i for i in phase_groups['D'] if bars[i]['branch'] == 'D3_seasoned_pressure']
    
    for label, idxs in [
        ("D1 继续推进(基础)", phase_groups['D']),
        ("D1 + DDX强", d1_strong),
        ("D1 + DDX强 + Seasoned未动(完美)", d1_perfect),
        ("D3 Seasoned压盘", d3),
    ]:
        if len(idxs) < 2:
            print(f"  {label:<30}: 信号不足 (<2天)")
            continue
        r5 = [bars[i]['ret_5d'] for i in idxs if bars[i]['ret_5d'] is not None]
        r10 = [bars[i]['ret_10d'] for i in idxs if bars[i]['ret_10d'] is not None]
        r20 = [bars[i]['ret_20d'] for i in idxs if bars[i]['ret_20d'] is not None]
        print(f"  {label:<30} {len(idxs):>3}天 5日{sum(r5)/len(r5):>+7.2%} 10日{sum(r10)/len(r10):>+7.2%} 20日{sum(r20)/len(r20):>+7.2%}")
    
    # Transition accuracy: when system says Phase C1 (shakeout done), does price actually go up?
    c1 = branch_groups.get('C1_shakeout_done', [])
    c2 = branch_groups.get('C2_extend_shakeout', [])
    
    print(f"\n  【Phase C 过渡准确率】")
    for label, idxs in [("C1 洗盘完成→应涨", c1), ("C2 延长洗盘→应横或跌", c2)]:
        if len(idxs) < 2:
            print(f"  {label:<25}: 不足")
            continue
        r5 = [bars[i]['ret_5d'] for i in idxs if bars[i]['ret_5d'] is not None]
        hit = sum(1 for x in r5 if (label[1]=='1' and x>0) or (label[1]=='2' and x<0.02))
        print(f"  {label:<25} {len(idxs)}天 5日均{sum(r5)/len(r5):>+7.2%} 方向正确率{hit}/{len(r5)}={hit/len(r5):.0%}")
    
    # Distribution accuracy for each phase over time
    phase_seq = [bars[i]['phase'] for i in range(30, len(bars)-20)]
    phase_transitions = {}
    for j in range(1, len(phase_seq)):
        pair = f"{phase_seq[j-1]}→{phase_seq[j]}"
        phase_transitions[pair] = phase_transitions.get(pair, 0) + 1
    
    print(f"\n  【Phase转移频率】")
    for pair, cnt in sorted(phase_transitions.items(), key=lambda x: -x[1])[:10]:
        print(f"  {pair}: {cnt}次")


# ── Run ──
bars_kl = load('kl_ddx_1y.json')
bars_bl = load('bl_ddx_1y.json')
print(f"昆仑: {len(bars_kl)}天 | 蓝标: {len(bars_bl)}天")

run_backtest("昆仑 300418", bars_kl, active_ratio=0.29)
run_backtest("蓝标 300058", bars_bl, active_ratio=0.66)

# Summary
print(f"\n{'='*70}")
print(f"  判决标准")
print(f"{'='*70}")
print("Phase D1+D3 区分准确: D3(压盘)后续涨幅 < D1(推进) → Seasoned压盘确实在压价")
print("Phase C1 vs C2: C1后续涨, C2后续横/跌 → 洗盘检测有效")
print("多技能叠加: D1+DDX强+Seasoned未动 应该是最强信号")
