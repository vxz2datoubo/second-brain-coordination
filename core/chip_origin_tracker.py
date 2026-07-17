#!/usr/bin/env python
"""筹码峰来源+原始买家身份 双重追踪引擎"""
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
    total_buy = r[2]+r[4]+r[6]+r[8]
    total_sell = r[3]+r[5]+r[7]+r[9]
    return {
        'inst_buy_pct': round((r[6]+r[8])/max(total_buy,1)*100, 0),  # 大+特
        'retail_buy_pct': round(r[2]/max(total_buy,1)*100, 0),
        'mid_buy_pct': round(r[4]/max(total_buy,1)*100, 0),
        'inst_sell_pct': round((r[7]+r[9])/max(total_sell,1)*100, 0),
        'retail_sell_pct': round(r[3]/max(total_sell,1)*100, 0),
        'mid_sell_pct': round(r[5]/max(total_sell,1)*100, 0),
        'total_buy': total_buy, 'total_sell': total_sell,
    }

def analyze_full_chain(d1, d2):
    """
    D1 筹码峰 ← 当时谁买的 (四渠道)
    D2 筹码峰 ← 现在变化
    → 被卖的筹码: 来自D1的哪个价位 + 原始持有者是谁
    → 新买的筹码: 去到D2的哪个价位 + 新持有者是谁
    """
    c1 = load_chip(d1)
    c2 = load_chip(d2)
    mf1 = load_mf(d1)  # D1日谁买的
    mf2 = load_mf(d2)  # D2日谁买卖的
    
    if not c1 or not c2 or not mf1 or not mf2:
        return None
    
    # D1日各价位的资金归属: {price: {'inst': pct, 'retail': pct}}
    chip_origin = {}
    for p in c1:
        if c1[p] > 0.5:  # only meaningful levels
            chip_origin[p] = {
                'inst': round(c1[p] * mf1['inst_buy_pct'] / 100, 2),
                'retail': round(c1[p] * mf1['retail_buy_pct'] / 100, 2),
                'mid': round(c1[p] * mf1['mid_buy_pct'] / 100, 2),
            }
    
    # D1→D2 筹码峰Δ
    losses = []
    gains = []
    for p in sorted(set(list(c1.keys()) + list(c2.keys()))):
        v1 = c1.get(p, 0)
        v2 = c2.get(p, 0)
        delta = v2 - v1
        if delta < -0.2:
            losses.append((p, -delta, chip_origin.get(p, {})))
        elif delta > 0.5:
            gains.append((p, delta))
    
    losses.sort(key=lambda x: x[1], reverse=True)
    gains.sort(key=lambda x: x[1], reverse=True)
    
    return {
        'd1': d1, 'd2': d2,
        'mf1': mf1, 'mf2': mf2,
        'losses': losses,  # [(price, qty_pct, {inst_pct, retail_pct, mid_pct})]
        'gains': gains,
    }

# ═══ 主程序 ═══
print("=" * 75)
print("  筹码峰来源 + 原始买家身份 双重追踪")
print("  追踪路径: D1筹码峰(谁买的) → D2筹码峰减少(谁的货被卖)")
print("=" * 75)

dates = ['20260706','20260707','20260708','20260709','20260710']
results = []

for i in range(1, len(dates)):
    r = analyze_full_chain(dates[i-1], dates[i])
    if not r: continue
    results.append(r)
    
    print(f"\n{'—'*50}")
    print(f"  {r['d1']} → {r['d2']}")
    
    # 卖方身份
    inst_s = r['mf2']['inst_sell_pct']
    retail_s = r['mf2']['retail_sell_pct']
    
    # 被卖的Top3筹码峰, 追溯原始持有者
    print(f"\n  被卖的筹码峰 (D2日卖方: 确定机构{inst_s:.0f}% + 混沌{100-inst_s:.0f}%):")
    for p, qty, origin in r['losses'][:5]:
        if origin:
            o_inst = origin.get('inst', 0)
            o_retail = origin.get('retail', 0)
            o_mid = origin.get('mid', 0)
            total_origin = o_inst + o_retail + o_mid
            if total_origin > 0:
                inst_orig_pct = o_inst / total_origin * 100
            else:
                inst_orig_pct = 0
        else:
            inst_orig_pct = 0
        
        bar = '█' * int(qty / max(1, sum(l[1] for l in r['losses'])) * 30)
        
        # 判定: 这批筹码原始是谁的
        if inst_orig_pct > 60:
            orig_tag = f"🔵 D1机构仓({inst_orig_pct:.0f}%)"
        elif inst_orig_pct > 30:
            orig_tag = f"🟡 D1混合仓(机构{inst_orig_pct:.0f}%)"
        else:
            orig_tag = f"🟢 D1散户仓(散户{100-inst_orig_pct:.0f}%)"
        
        # 现在谁在卖这批筹码?
        if inst_s > 50:
            sell_tag = "→ 现在确定机构卖出"
        elif retail_s > 50:
            sell_tag = "→ 现在混沌主导(可能散户+拆单机构)"
        else:
            sell_tag = "→ 现在混合卖出"
        
        print(f"    D1成本 {p:>5.1f}元 -{qty:>5.1f}%pct {bar} {orig_tag} {sell_tag}")
    
    # 新筹码去向
    print(f"\n  新增筹码 (D2日买方: 确定机构{r['mf2']['inst_buy_pct']:.0f}%):")
    for p, qty in r['gains'][:4]:
        bar = '█' * int(qty / max(1, sum(g[1] for g in r['gains'])) * 30)
        print(f"    D2价位 {p:>5.1f}元 +{qty:>5.1f}%pct {bar} → 新持有者: 机构{r['mf2']['inst_buy_pct']:.0f}%")

# 总结
print(f"\n{'='*75}")
print("  4天双重追踪总结: 谁的低成本仓在卖?")
print(f"{'='*75}")

for r in results:
    top_loss = r['losses'][0] if r['losses'] else (0,0,{})
    p, qty, origin = top_loss
    if origin:
        inst_o = origin.get('inst', 0) / max(origin.get('inst',0)+origin.get('retail',0)+origin.get('mid',0), 0.01) * 100
    else:
        inst_o = 0
    
    inst_curr = r['mf2']['inst_sell_pct']
    
    # Key insight
    if inst_o > 50 and inst_curr < 40:
        summary = "🔴 机构的低成本仓通过小单渠道在出! (拆单验证)"
    elif inst_o > 50:
        summary = "🟡 机构的低成本仓在换手(卖方渠道含机构)"
    else:
        summary = "🟢 散户的低成本仓在获利了结"
    
    print(f"  {r['d2']}: 卖出来源={p:.0f}元(D1机构{inst_o:.0f}%仓) 现卖方机构{inst_curr:.0f}% → {summary}")
