#!/usr/bin/env python
"""筹码峰日级锚定 + 4渠道驱动归属引擎
核心: 日级cyq_chips绝对精确 → 每日Δ强制对齐 → 四渠道归属"""

import json, sys, os
from collections import defaultdict
sys.path.insert(0, 'F:/aidanao')
from core.tushare_bridge import TushareBridge

b = TushareBridge()

# ════════════════════════════════════
# 1. 加载筹码峰 + 资金流
# ════════════════════════════════════

def load_chip(date_str):
    rows = b._call('cyq_chips', {'ts_code':'300418.SZ','trade_date':date_str})
    return {float(r[2]): float(r[3]) for r in rows} if rows else None

def load_moneyflow(date_str):
    rows = b._call('moneyflow', {'ts_code':'300418.SZ','start_date':date_str,'end_date':date_str})
    if not rows or not rows[0]: return None
    r = rows[0]
    return {
        'sm_buy': r[2], 'sm_sell': r[3],   # 小单
        'md_buy': r[4], 'md_sell': r[5],   # 中单
        'lg_buy': r[6], 'lg_sell': r[7],   # 大单
        'elg_buy': r[8], 'elg_sell': r[9], # 特大单
        'sm_net': r[2]-r[3], 'md_net': r[4]-r[5],
        'lg_net': r[6]-r[7], 'elg_net': r[8]-r[9],
    }

# ════════════════════════════════════
# 2. 每日筹码峰Δ + 驱动归属
# ════════════════════════════════════

def analyze_day(d1_date, d2_date, code='300418'):
    """D1→D2: 筹码峰怎么变 + 谁驱动的"""
    c1 = load_chip(d1_date)
    c2 = load_chip(d2_date)
    mf = load_moneyflow(d2_date)
    
    if not c1 or not c2:
        print(f"  {d1_date}→{d2_date}: 缺筹码数据")
        return None
    
    # ── 2a) 计算Δ ──
    all_prices = sorted(set(list(c1.keys()) + list(c2.keys())))
    gains = defaultdict(float)  # 筹码增加(买方)
    losses = defaultdict(float) # 筹码减少(卖方)
    
    for p in all_prices:
        v1 = c1.get(p, 0)
        v2 = c2.get(p, 0)
        delta = v2 - v1
        if delta > 0.01:
            gains[p] = delta
        elif delta < -0.01:
            losses[p] = -delta
    
    total_gain = sum(gains.values())
    total_loss = sum(losses.values())
    
    # ── 2b) 四渠道归属 ──
    # 买方 = 谁在买 → 分配增量筹码
    # 卖方 = 谁在卖 → 哪来的筹码被卖
    
    inst_total = 0; retail_total = 0; mid_total = 0
    inst_buy = inst_sell = retail_buy = retail_sell = mid_buy = mid_sell = 0
    
    if mf:
        # 总买入 = 各渠道买入; 总卖出 = 各渠道卖出
        total_buy = mf['sm_buy'] + mf['md_buy'] + mf['lg_buy'] + mf['elg_buy']
        total_sell = mf['sm_sell'] + mf['md_sell'] + mf['lg_sell'] + mf['elg_sell']
        
        if total_buy > 0:
            inst_buy_pct = (mf['lg_buy'] + mf['elg_buy']) / total_buy * 100
            retail_buy_pct = mf['sm_buy'] / total_buy * 100
            mid_buy_pct = mf['md_buy'] / total_buy * 100
        else:
            inst_buy_pct = retail_buy_pct = mid_buy_pct = 0
        
        if total_sell > 0:
            inst_sell_pct = (mf['lg_sell'] + mf['elg_sell']) / total_sell * 100
            retail_sell_pct = mf['sm_sell'] / total_sell * 100
            mid_sell_pct = mf['md_sell'] / total_sell * 100
        else:
            inst_sell_pct = retail_sell_pct = mid_sell_pct = 0
        
        # 归属: 增量筹码 × 买方渠道比 = 机构/游资/散户各买了多少价位
        inst_buy = total_gain * inst_buy_pct / 100
        retail_buy = total_gain * retail_buy_pct / 100
        mid_buy = total_gain * mid_buy_pct / 100
        
        # 卖方: 减持筹码 × 各渠道卖出比
        inst_sell = total_loss * inst_sell_pct / 100
        retail_sell = total_loss * retail_sell_pct / 100
        mid_sell = total_loss * mid_sell_pct / 100
    else:
        inst_buy_pct = retail_buy_pct = mid_buy_pct = 0
        inst_sell_pct = retail_sell_pct = mid_sell_pct = 0
    
    # ── 2c) 分类筹码增减 ──
    # 卖出筹码来自哪些价位？
    # 买入筹码去到哪些价位？
    # 按成交价加权: 用当天均价附近判断
    
    # WAP: weighted average price ≈ c2的总成交均价(从daily数据)
    avg_price_key = max(gains, key=gains.get) if gains else 50
    
    loss_from_low = sum(losses.get(p, 0) for p in losses if p < avg_price_key)
    loss_from_high = sum(losses.get(p, 0) for p in losses if p >= avg_price_key)
    
    return {
        'date': d2_date,
        'prev_date': d1_date,
        'total_gain': round(total_gain, 2),
        'total_loss': round(total_loss, 2),
        'gains': dict(gains),
        'losses': dict(losses),
        'inst_buy': round(inst_buy, 2),
        'retail_buy': round(retail_buy, 2),
        'mid_buy': round(mid_buy, 2),
        'inst_sell': round(inst_sell, 2),
        'retail_sell': round(retail_sell, 2),
        'mid_sell': round(mid_sell, 2),
        'loss_from_low': round(loss_from_low, 2),
        'loss_from_high': round(loss_from_high, 2),
        'inst_buy_pct': round(inst_buy_pct, 1),
        'retail_buy_pct': round(retail_buy_pct, 1),
        'mid_buy_pct': round(mid_buy_pct, 1),
        'inst_sell_pct': round(inst_sell_pct, 1),
        'retail_sell_pct': round(retail_sell_pct, 1),
        'mid_sell_pct': round(mid_sell_pct, 1),
    }

# ════════════════════════════════════
# 3. 主程序
# ════════════════════════════════════

print("=" * 70)
print("  筹码峰日级追踪 + 四渠道资金归属")
print("=" * 70)

dates = ['20260706','20260707','20260708','20260709','20260710']

results = []
for i in range(1, len(dates)):
    r = analyze_day(dates[i-1], dates[i])
    if r:
        results.append(r)
        
        print(f"\n{'='*50}")
        print(f"  {r['prev_date']} → {r['date']}")
        print(f"{'='*50}")
        
        print(f"\n  筹码峰变化:")
        print(f"    减持: {r['total_loss']:.1f}%pct (底部{r['loss_from_low']:.1f}% + 高位{r['loss_from_high']:.1f}%)")
        print(f"    新增: {r['total_gain']:.1f}%pct")
        
        print(f"\n  买方来源 (新增筹码):")
        print(f"    🔵 机构(大+特): {r['inst_buy']:.1f}% ({r['inst_buy_pct']:.0f}%)")
        print(f"    🟡 游资(中单):   {r['mid_buy']:.1f}% ({r['mid_buy_pct']:.0f}%)")
        print(f"    🟢 散户(小单):   {r['retail_buy']:.1f}% ({r['retail_buy_pct']:.0f}%)")
        
        print(f"\n  卖方来源 (减持筹码):")
        print(f"    🔵 机构(大+特): {r['inst_sell']:.1f}% ({r['inst_sell_pct']:.0f}%)")
        print(f"    🟡 游资(中单):   {r['mid_sell']:.1f}% ({r['mid_sell_pct']:.0f}%)")
        print(f"    🟢 散户(小单):   {r['retail_sell']:.1f}% ({r['retail_sell_pct']:.0f}%)")
        
        # Top gains (哪些价位在吸筹)
        top_gains = sorted(r['gains'].items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n  吸筹价位 Top5:")
        for p, v in top_gains:
            bar = '█' * int(v / max(1, r['total_gain']) * 30)
            print(f"    {p:>5.1f}元: +{v:5.1f}%pct {bar}")
        
        # Top losses (哪些价位在出货)
        top_losses = sorted(r['losses'].items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n  出货价位 Top5:")
        for p, v in top_losses:
            bar = '█' * int(v / max(1, r['total_loss']) * 30)
            print(f"    {p:>5.1f}元: -{v:5.1f}%pct {bar}")

# 总结
print(f"\n{'='*70}")
print("  4天筹码峰迁移总结")
print(f"{'='*70}")

# Track key price levels
key_prices = [43, 45, 47, 50, 52]
print(f"\n关键价位筹码变动:")
print(f"{'日期':<10}", end='')
for kp in key_prices: print(f" {kp:>6}元", end='')
print()

for i, d in enumerate(dates):
    c = load_chip(d)
    if c:
        print(f"{d:<10}", end='')
        for kp in key_prices:
            v = c.get(float(kp), 0)
            print(f" {v:>5.1f}%", end='')
        print()

print(f"\n四渠道累积(4天):")
for r in results:
    print(f"  {r['date']}: 买-机构{r['inst_buy_pct']:.0f}% 游资{r['mid_buy_pct']:.0f}% 散户{r['retail_buy_pct']:.0f}% | "
          f"卖-机构{r['inst_sell_pct']:.0f}% 游资{r['mid_sell_pct']:.0f}% 散户{r['retail_sell_pct']:.0f}%")
