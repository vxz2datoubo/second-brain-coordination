"""
回测改前 vs 改后 v2 — 用已知锁仓深度校准
昆仑锁仓71%(活跃29%) / 蓝标锁仓34%(活跃66%) — 来自lockup-depth-analysis
无未来函数：所有信号只用当日及之前数据
"""
import json

# ── Load data ──
def load(name, active_ratio):
    with open(f'F:/aidanao/data/{name}', 'r', encoding='utf-8') as f:
        data = json.load(f)
    bars = []
    for i, r in enumerate(data):
        d = r['d']
        c = float(r['c'])
        dd = float(r.get('main', 0))
        dy = float(r.get('jumbo', 0))
        mid = float(r.get('mid', 0))
        sm = float(r.get('small', 0))
        total_flow = abs(dd) + abs(dy) + abs(mid) + abs(sm)
        if i == 0:
            bars.append({'d': d, 'c': c, 'ddx': dd, 'ddy': dy, 'mid': mid, 'sm': sm,
                         'ret': 0, 'ret_1d': 0, 'ret_5d': 0, 'ret_10d': 0,
                         'total_flow': total_flow, 'vol_ratio': 1.0,
                         'nom_vol': 1.0, 'true_turn': 0, 'active_ratio': active_ratio})
        else:
            prev_c = bars[-1]['c']
            ret = c / prev_c - 1 if prev_c else 0
            # Nominal volume ratio (20-day rolling)
            start = max(0, i-20)
            avg20 = sum(b['total_flow'] for b in bars[start:i]) / max(i-start, 1)
            nom_vol = total_flow / avg20 if avg20 > 0 else 1.0
            # True turnover = nominal vol / active_ratio
            true_turn = nom_vol / active_ratio if active_ratio > 0 else nom_vol
            bars.append({'d': d, 'c': c, 'ddx': dd, 'ddy': dy, 'mid': mid, 'sm': sm,
                         'ret': ret, 'ret_1d': 0, 'ret_5d': 0, 'ret_10d': 0,
                         'total_flow': total_flow, 'vol_ratio': nom_vol,
                         'nom_vol': nom_vol, 'true_turn': true_turn, 'active_ratio': active_ratio})
    
    # Forward returns
    for i in range(len(bars)):
        if i + 1 < len(bars): bars[i]['ret_1d'] = bars[i+1]['c'] / bars[i]['c'] - 1
        if i + 5 < len(bars): bars[i]['ret_5d'] = bars[i+5]['c'] / bars[i]['c'] - 1
        if i + 10 < len(bars): bars[i]['ret_10d'] = bars[i+10]['c'] / bars[i]['c'] - 1
    return bars


def report(name, tests):
    """tests: list of (label, idxs)"""
    print(f"\n{'─'*60}")
    print(f"  {name}")
    print(f"{'─'*60}")
    results = []
    for label, idxs in tests:
        if not idxs:
            results.append((label, 0, "无信号", "", ""))
            continue
        r1 = [bars[i]['ret_1d'] for i in idxs if bars[i]['ret_1d'] is not None]
        r5 = [bars[i]['ret_5d'] for i in idxs if bars[i]['ret_5d'] is not None]
        r10 = [bars[i]['ret_10d'] for i in idxs if bars[i]['ret_10d'] is not None]
        results.append((label, len(idxs),
                       f"{sum(r1)/len(r1):+.2%}" if r1 else "N/A",
                       f"{sum(r5)/len(r5):+.2%}" if r5 else "N/A",
                       f"{sum(r10)/len(r10):+.2%}" if r10 else "N/A"))
    # Print table
    print(f"  {'信号':<30} {'天数':>5} {'次日':>8} {'5日':>8} {'10日':>8}")
    for label, n, r1, r5, r10 in results:
        print(f"  {label:<30} {n:>5} {r1:>8} {r5:>8} {r10:>8}")
    return results


# ── Load ──
bars_kl = load('kl_ddx_1y.json', active_ratio=0.29)  # 昆仑活跃盘29%
bars_bl = load('bl_ddx_1y.json', active_ratio=0.66)  # 蓝标活跃盘66%

print(f"昆仑锁仓71%→活跃29% | 蓝标锁仓34%→活跃66%")

# ═══════════════════════════════════════════
# TEST 1: Supply Test 缩量信号
# ═══════════════════════════════════════════
# 逻辑: 缩量回踩时供应枯竭 → 买入信号
# OLD: 名义量比<0.8 + 小幅回踩
# NEW: 真换手<活跃盘15%(昆仑≈0.52, 蓝标≈0.23) + 小幅回踩

for stock_name, bars in [("昆仑(活跃29%)", bars_kl), ("蓝标(活跃66%)", bars_bl)]:
    old_sig = []
    new_sig = []
    baseline = []
    for i in range(21, len(bars)-5):
        is_pullback = -0.03 < bars[i]['ret'] < 0.005  # flat or slight decline
        if not is_pullback:
            continue
        
        # OLD: nominal vol < 0.8
        if bars[i]['nom_vol'] < 0.8:
            old_sig.append(i)
        # NEW: true turnover < 15% of active float
        # 昆仑: 0.15 active → nom<0.15*0.29=0.0435 → too strict
        # More practical: true_turn < 0.50 (half of active float traded that day)
        if bars[i]['true_turn'] < 0.50:
            new_sig.append(i)
        # Baseline: any pullback
        baseline.append(i)
    
    report(f"{stock_name} - Supply Test", [
        ("OLD 名义缩量(<0.8)", old_sig),
        ("NEW 真换手<0.5活跃盘", new_sig),
        ("BASELINE 任意回踩", baseline),
    ])


# ═══════════════════════════════════════════
# TEST 2: Phase C-D 过渡K线
# ═══════════════════════════════════════════
# 逻辑: 小K线+连续缩量 = 过渡 → 后续突破
# OLD: 小K线(涨跌<2%) + 连续3日量递减 + 量比<1.0
# NEW: 小K线 + 真换手连续3日递减 + 真换手<0.6

for stock_name, bars in [("昆仑(活跃29%)", bars_kl), ("蓝标(活跃66%)", bars_bl)]:
    old_sig = []
    new_sig = []
    for i in range(23, len(bars)-5):
        is_small = abs(bars[i]['ret']) < 0.02
        if not is_small:
            continue
        
        # OLD
        old_dec = (bars[i]['nom_vol'] < 1.0 and 
                   bars[i]['nom_vol'] < bars[i-1]['nom_vol'] and 
                   bars[i-1]['nom_vol'] < bars[i-2]['nom_vol'])
        if old_dec:
            old_sig.append(i)
        
        # NEW
        new_dec = (bars[i]['true_turn'] > 0 and bars[i-1]['true_turn'] > 0 and bars[i-2]['true_turn'] > 0 and
                   bars[i]['true_turn'] < bars[i-1]['true_turn'] and 
                   bars[i-1]['true_turn'] < bars[i-2]['true_turn'] and
                   bars[i]['true_turn'] < 0.6)
        if new_dec:
            new_sig.append(i)
    
    report(f"{stock_name} - Phase C-D Transition", [
        ("OLD 名义量递减+<1.0", old_sig),
        ("NEW 真换手递减+<0.6", new_sig),
    ])


# ═══════════════════════════════════════════
# TEST 3: Accumulation 低位吸筹
# ═══════════════════════════════════════════
# 逻辑: 低位+DDX正+缩量 = 机构吸筹
# OLD: 价格平/跌 + DDX正 + 名义量比<0.7
# NEW: 价格平/跌 + DDX正 + 真换手<0.4

for stock_name, bars in [("昆仑(活跃29%)", bars_kl), ("蓝标(活跃66%)", bars_bl)]:
    old_sig = []
    new_sig = []
    for i in range(21, len(bars)-5):
        flat = bars[i]['ret'] < 0.005
        ddx_pos = bars[i]['ddx'] > 0
        if not (flat and ddx_pos):
            continue
        
        if bars[i]['nom_vol'] < 0.7:
            old_sig.append(i)
        if bars[i]['true_turn'] < 0.4:
            new_sig.append(i)
    
    report(f"{stock_name} - Accumulation", [
        ("OLD 名义缩量(<0.7)+DDX正", old_sig),
        ("NEW 真换手<0.4+DDX正", new_sig),
    ])


# ═══════════════════════════════════════════
# TEST 4: Institution Trial 机构试探
# ═══════════════════════════════════════════
# 逻辑: DDX微正 + 量在下降 = 机构在试盘
# OLD: DDX微正(>0) + 3日名义量递减>30%
# NEW: DDX微正(>0) + 3日真换手递减>30% + 真换手<0.8

for stock_name, bars in [("昆仑(活跃29%)", bars_kl), ("蓝标(活跃66%)", bars_bl)]:
    old_sig = []
    new_sig = []
    for i in range(23, len(bars)-5):
        ddx_pos = bars[i]['ddx'] > 0
        if not ddx_pos:
            continue
        
        # Avoid extreme DDX days (those are SOS, not trial)
        total = abs(bars[i]['ddx']) + abs(bars[i]['ddy']) + abs(bars[i]['mid']) + abs(bars[i]['sm'])
        if total == 0: continue
        ddx_pct = bars[i]['ddx'] / total
        if ddx_pct > 0.3:  # >30% dominant = not "试探" anymore
            continue
        
        # OLD: 3-day nominal decay > 30%
        avg_old = (bars[i-1]['nom_vol'] + bars[i-2]['nom_vol'] + bars[i-3]['nom_vol']) / 3
        old_dec = bars[i]['nom_vol'] < avg_old * 0.7
        if old_dec:
            old_sig.append(i)
        
        # NEW: 3-day true turnover decay
        avg_new = (bars[i-1]['true_turn'] + bars[i-2]['true_turn'] + bars[i-3]['true_turn']) / 3
        new_dec = (avg_new > 0 and bars[i]['true_turn'] < avg_new * 0.7 and bars[i]['true_turn'] < 0.8)
        if new_dec:
            new_sig.append(i)
    
    report(f"{stock_name} - Institution Trial", [
        ("OLD 名义量3日衰减>30%", old_sig),
        ("NEW 真换手3日衰减>30%", new_sig),
    ])


# ═══════════════════════════════════════════
# TEST 5: Effort-Result 缩量大涨
# ═══════════════════════════════════════════
# 逻辑: 连续大涨+缩量 = 锁仓拉升
# OLD: 连续2日涨>2% + 名义量比<0.8
# NEW: 连续2日涨>2% + 真换手<0.45

for stock_name, bars in [("昆仑(活跃29%)", bars_kl), ("蓝标(活跃66%)", bars_bl)]:
    old_sig = []
    new_sig = []
    for i in range(22, len(bars)-5):
        up2 = bars[i]['ret'] > 0.02 and bars[i-1]['ret'] > 0.02
        if not up2:
            continue
        
        if bars[i]['nom_vol'] < 0.8 and bars[i-1]['nom_vol'] < 0.8:
            old_sig.append(i)
        if bars[i]['true_turn'] < 0.45 and bars[i-1]['true_turn'] < 0.45:
            new_sig.append(i)
    
    report(f"{stock_name} - Effort-Result Climax", [
        ("OLD 名义缩量大涨", old_sig),
        ("NEW 真换手<0.45大涨", new_sig),
    ])


# ═══════════════════════════════════════════
# TEST 6: Opening Range 解锁日预警
# ═══════════════════════════════════════════
# 逻辑: 昨天量过大 → 今天解锁抛压 → 跑输
# OLD: 昨量比 > 均量1.5倍 → 预警
# NEW: 昨真换手 > 活跃盘15% → 预警

for stock_name, bars in [("昆仑(活跃29%)", bars_kl), ("蓝标(活跃66%)", bars_bl)]:
    old_sig = []
    new_sig = []
    for i in range(22, len(bars)-1):
        avg20 = sum(b['nom_vol'] for b in bars[max(0,i-20):i]) / 20
        
        if bars[i-1]['nom_vol'] > avg20 * 1.5:
            old_sig.append(i)
        if bars[i-1]['true_turn'] > 0.15:  # >15% of active float
            new_sig.append(i)
    
    # For unlock warning: success = next day return < average
    avg_r1 = sum(b['ret_1d'] for b in bars if b['ret_1d'] is not None) / sum(1 for b in bars if b['ret_1d'] is not None)
    
    results = []
    for label, idxs in [("OLD 解锁预警(名义>1.5x)", old_sig), ("NEW 解锁预警(真换手>15%)", new_sig)]:
        if not idxs:
            results.append((label, 0, "N/A", "", ""))
            continue
        r1 = [bars[i]['ret_1d'] for i in idxs if bars[i]['ret_1d'] is not None]
        hit = sum(1 for x in r1 if x < avg_r1)
        pct_correct = hit / len(r1) if r1 else 0
        avg_r = sum(r1) / len(r1) if r1 else 0
        results.append((label, len(idxs), f"{avg_r:+.2%}", f"命中{hit}/{len(r1)}={pct_correct:.0%}", f"市场均{avg_r1:+.2%}"))
    
    print(f"\n{'─'*60}")
    print(f"  {stock_name} - Opening Range Unlock (次日跑输=预警有效)")
    print(f"{'─'*60}")
    print(f"  {'信号':<35} {'次数':>5} {'次日均':>8} {'准确率':>20} {'基准':>10}")
    for label, n, r1, acc, base in results:
        print(f"  {label:<35} {n:>5} {r1:>8} {acc:>20} {base:>10}")


# ═══════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════
print(f"\n{'='*70}")
print(f"  判决: NEW vs OLD 信号质量对比")
print(f"{'='*70}")
print("标准: NEW的5日远期 > OLD的5日远期 = 改良有效")
print("      NEW天数更少但收益集中 = 信噪比提升(去伪存真)")
print("      NEW ≈ OLD = 改良无实质效果(换汤不换药)")
print("      注: 解锁预警以'准确率'为准(准确预警抛压=改良)")
