#!/usr/bin/env python
"""筹码峰来源追踪引擎 — 精确知道被卖掉的筹码来自哪个成本区间"""
import json, sys, os
from collections import defaultdict
sys.path.insert(0, 'F:/aidanao')
from core.tushare_bridge import TushareBridge
b = TushareBridge()

def load_chip(date_str):
    rows = b._call('cyq_chips', {'ts_code':'300418.SZ','trade_date':date_str})
    return {float(r[2]): float(r[3]) for r in rows} if rows else None

def load_mf(date_str):
    rows = b._call('moneyflow', {'ts_code':'300418.SZ','start_date':date_str,'end_date':date_str})
    if not rows: return None
    r = rows[0]
    return {
        'sm': r[2]-r[3], 'md': r[4]-r[5], 'lg': r[6]-r[7], 'elg': r[8]-r[9],
        'sm_buy': r[2], 'md_buy': r[4], 'lg_buy': r[6], 'elg_buy': r[8],
    }

def analyze_source(d1, d2):
    """D1→D2: 被卖掉的筹码来自D1的哪个成本区间"""
    c1 = load_chip(d1)
    c2 = load_chip(d2)
    mf = load_mf(d2)
    if not c1 or not c2:
        return None
    
    # ── 1) 筹码峰Δ ──
    losses = {}
    gains = {}
    for p in sorted(set(list(c1.keys()) + list(c2.keys()))):
        v1 = c1.get(p, 0)
        v2 = c2.get(p, 0)
        delta = v2 - v1
        if delta < -0.01:
            losses[p] = -delta
        elif delta > 0.01:
            gains[p] = delta
    
    total_loss = sum(losses.values())
    total_gain = sum(gains.values())
    
    # ── 2) 卖方的原始成本区间 ──
    # 被卖掉的筹码"来自"D1日的哪个价位
    # 这些筹码的原始成本 = 它们在D1时的筹码峰价格
    
    # 卖方=从D1筹码峰中消失的%pct
    loss_distribution = {}  # {成本: 被卖掉的%pct}
    for p, v in sorted(losses.items(), key=lambda x: x[1], reverse=True):
        if v > 0.3:
            loss_distribution[p] = v
    
    # ── 3) 四方资金归属 ──
    if mf:
        total_buy = mf['sm_buy'] + mf['md_buy'] + mf['lg_buy'] + mf['elg_buy']
        inst_pct = (mf['lg_buy'] + mf['elg_buy']) / max(total_buy, 1) * 100
    else:
        inst_pct = 0
    
    # ── 4) 买方的目标价位(新筹码在哪) ──
    new_chip_zones = sorted(gains.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # ── 5) 判断 ──
    # 核心: 被卖的筹码主要来自哪个成本区?
    # 分类: 底部(低于现价15%+) / 中部(5-15%) / 高位(<5%)
    
    # 用D2日的平均成本作为"现价"参考
    avg_cost = sum(k * v for k, v in c2.items()) / max(sum(c2.values()), 1)
    
    low_sold = sum(v for p, v in losses.items() if p < avg_cost * 0.85)
    mid_sold = sum(v for p, v in losses.items() if avg_cost * 0.85 <= p < avg_cost * 1.05)
    high_sold = sum(v for p, v in losses.items() if p >= avg_cost * 1.05)
    
    # Find the top 3 source price levels
    top_sources = sorted(losses.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Key signal: 机构买入 + 筹码主要来自中部 = 机构在接短线获利盘
    if inst_pct > 50 and mid_sold > low_sold and mid_sold > 3:
        signal = "🟢🟢 机构接短线获利盘 → 志在更高"
    elif inst_pct > 50 and low_sold > mid_sold and low_sold > 5:
        signal = "🟡 机构接底部老仓 → 底部在出货, 留意"
    elif inst_pct < 40 and high_sold > 3:
        signal = "🔴 散户卖出高位筹码 → 可能是割肉, 也可能被套"
    else:
        signal = "→ 正常换手"
    
    return {
        'date': d2, 'prev': d1,
        'total_loss': round(total_loss, 1),
        'total_gain': round(total_gain, 1),
        'avg_cost': round(avg_cost, 1),
        'inst_pct': round(inst_pct, 0),
        'low_sold': round(low_sold, 1),
        'mid_sold': round(mid_sold, 1),
        'high_sold': round(high_sold, 1),
        'top_sources': [(p, round(v, 1)) for p, v in top_sources],
        'new_zones': [(p, round(v, 1)) for p, v in new_chip_zones],
        'signal': signal,
        'explanation': f"机构{inst_pct:.0f}%买入, 卖出筹码主要来自{top_sources[0][0]:.0f}元成本区"
    }

# ═══ 主程序 ═══
print("=" * 70)
print("  筹码峰来源追踪 — 谁在什么成本区间卖出了筹码")
print("=" * 70)

dates = ['20260706','20260707','20260708','20260709','20260710']
results = []

for i in range(1, len(dates)):
    r = analyze_source(dates[i-1], dates[i])
    if r:
        results.append(r)
        print(f"\n{r['prev']} → {r['date']}")
        print(f"  均成本: {r['avg_cost']:.1f}元")
        print(f"  总换手: {r['total_loss']:.1f}%pct (增{r['total_gain']:.1f}%pct)")
        print(f"  机构占比: {r['inst_pct']:.0f}%")
        print(f"  卖出来源:")
        print(f"    底部(<{r['avg_cost']*0.85:.0f}元): {r['low_sold']:.1f}%pct")
        print(f"    中部({r['avg_cost']*0.85:.0f}-{r['avg_cost']*1.05:.0f}元): {r['mid_sold']:.1f}%pct")
        print(f"    高位(>{r['avg_cost']*1.05:.0f}元): {r['high_sold']:.1f}%pct")
        print(f"  卖出筹码来源 Top3:")
        for p, v in r['top_sources']:
            bar = '█' * int(v / max(1, r['total_loss']) * 30)
            print(f"    D1成本 {p:>5.1f}元 卖出{v:>5.1f}%pct {bar}")
        print(f"  新筹码去向 Top3:")
        for p, v in r['new_zones']:
            bar = '█' * int(v / max(1, r['total_gain']) * 30)
            print(f"    D2价位 {p:>5.1f}元 新增{v:>5.1f}%pct {bar}")
        print(f"  信号: {r['signal']}")
        print(f"  解释: {r['explanation']}")

# 累积统计
print(f"\n{'='*70}")
print(f"  4天累积来源追踪")
print(f"{'='*70}")
for r in results:
    sources = ', '.join(f"{p:.0f}元{v:.1f}%" for p,v in r['top_sources'][:2])
    print(f"  {r['date']}: 卖出来源=[{sources}] 信号={r['signal']}")
