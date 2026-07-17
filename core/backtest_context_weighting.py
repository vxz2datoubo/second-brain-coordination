#!/usr/bin/env python
"""回测: 量能对战加权 vs 不加权 准确率对比"""

import json, sys, os
from collections import defaultdict

# ─── 加载分钟K线 ───
def load_kline(path):
    with open(path, 'r') as f:
        text = f.read()
    return json.loads(text[text.index('{'):])['Rows']

base = 'C:/Users/Administrator/.workbuddy/projects/f-aidanao/e4341908-6fb5-479b-913a-f9d578558264/tool-results/'

# 昆仑万维 (两个批次)
# 昆仑万维 — 4个批次
kl_files = [
    'mcp-connector-proxy-tdx-connector_tdx_kline-1783908712271-21aac7.txt',
    'mcp-connector-proxy-tdx-connector_tdx_kline-1783908789876-ccd50d.txt',
    'mcp-connector-proxy-tdx-connector_tdx_kline-1783909337147-03d25b.txt',
    'mcp-connector-proxy-tdx-connector_tdx_kline-1783909337366-c30bc9.txt',
]
# 上证指数 — 2个批次
sh_files = [
    'mcp-connector-proxy-tdx-connector_tdx_kline-1783909337016-811e4b.txt',
    'mcp-connector-proxy-tdx-connector_tdx_kline-1783909446212-52e59f.txt',
]

kl_all = []
for f in kl_files:
    try: kl_all.extend(load_kline(base + f))
    except: pass

sh_all = []
for f in sh_files:
    try: sh_all.extend(load_kline(base + f))
    except: pass

# 去重
seen = set()
kl_dedup = []
for b in kl_all:
    key = (b['Data'], b['Second'], b['Close'])
    if key not in seen:
        seen.add(key)
        kl_dedup.append(b)

seen2 = set()
sh_dedup = []
for b in sh_all:
    key = (b['Data'], b['Second'], b['Close'])
    if key not in seen2:
        seen2.add(key)
        sh_dedup.append(b)

print(f"昆仑: {len(kl_dedup)} 根(去重后, {len(kl_all)} 原始)  上证: {len(sh_dedup)} 根(去重后, {len(sh_all)} 原始)")

# ─── 按日分组 ───
def group_by_day(bars):
    daily = defaultdict(list)
    for bar in bars:
        day = bar['Data']
        sec = int(bar['Second'])
        hh = sec // 3600
        mm = (sec % 3600) // 60
        time_str = f"{hh:02d}{mm:02d}"
        daily[day].append({
            'time': time_str,
            'price': float(bar['Close']),
            'vol': bar.get('Volume', 0) or 0
        })
    return daily

kl_daily = group_by_day(kl_dedup)
sh_daily = group_by_day(sh_dedup)

# ─── 上午量能指标 ───
def calc_metrics(daily):
    metrics = {}
    for day in sorted(daily.keys()):
        bars = daily[day]
        morning = [b for b in bars if '0930' <= b['time'] <= '1130']
        afternoon = [b for b in bars if b['time'] >= '1300']
        if len(morning) < 30 or len(afternoon) < 10:
            continue

        up_vol = down_vol = up_cnt = down_cnt = 0
        for i in range(1, len(morning)):
            if morning[i]['price'] >= morning[i-1]['price']:
                up_vol += morning[i]['vol']
                up_cnt += 1
            else:
                down_vol += morning[i]['vol']
                down_cnt += 1
        total = up_vol + down_vol
        if total == 0:
            continue

        br = up_vol / total
        up_avg = up_vol / max(up_cnt, 1)
        down_avg = down_vol / max(down_cnt, 1)
        ir = up_avg / max(down_avg, 0.01)

        mp = (morning[-1]['price'] - morning[0]['price']) / morning[0]['price'] * 100
        ap = (afternoon[-1]['price'] - afternoon[0]['price']) / afternoon[0]['price'] * 100

        metrics[day] = {
            'br': round(br, 3),
            'ir': round(ir, 2),
            'mp': round(mp, 2),
            'ap': round(ap, 2),
        }
    return metrics

kl_m = calc_metrics(kl_daily)
sh_m = calc_metrics(sh_daily)

common = sorted(set(kl_m.keys()) & set(sh_m.keys()))
print(f"\n共同交易日: {len(common)} 天  ({common[0]} -> {common[-1]})")

# ─── 加权函数 ───
def get_adj(signal, market, sector):
    """三维上下文加权"""
    dirs = [market, sector]
    pos = sum(1 for d in dirs if d > 0.1)
    neg = sum(1 for d in dirs if d < -0.1)

    adj = 1.0
    if signal > 0:
        if pos == 2: adj = 1.40
        elif pos == 1: adj = 1.15
        elif neg == 2: adj = 0.55
        elif neg == 1: adj = 0.80
    elif signal < 0:
        if neg == 2: adj = 1.40
        elif neg == 1: adj = 1.15
        elif pos == 2: adj = 0.55
        elif pos == 1: adj = 0.80

    # 极端市场+逆势 -> 强打折
    if market < -0.4 and signal > 0:
        adj *= 0.6
    if market > 0.4 and signal < 0:
        adj *= 0.6

    return adj

# ─── 回测主体 ───
results = []
for day in common:
    k = kl_m[day]
    s = sh_m[day]

    # 量能信号 [-1,1]
    raw_sig = (k['br'] - 0.5) * 2

    # 大盘: 上证上午% 映射
    mkt = max(-1.0, min(1.0, s['mp'] / 2.0))

    # 板块: 个股 vs 大盘 相对强度
    rel = k['mp'] - s['mp']
    sec = max(-1.0, min(1.0, rel / 2.0))

    # 午后涨跌 (-1=跌, 1=涨)
    aft_dir = 1 if k['ap'] > 0 else -1

    # --- 不加权 ---
    uw_sig = 1 if raw_sig > 0 else -1
    uw_ok = (uw_sig == aft_dir)

    # --- 加权 ---
    adj = get_adj(raw_sig, mkt, sec)
    w_raw = raw_sig * adj
    ww_sig = 1 if w_raw > 0 else (-1 if w_raw < 0 else 0)
    ww_ok = (ww_sig == aft_dir)

    results.append({
        'date': day,
        'mp': k['mp'], 'ap': k['ap'],
        'br': k['br'], 'ir': k['ir'],
        'raw_sig': round(raw_sig, 3),
        'mkt': round(mkt, 3),
        'sector': round(sec, 3),
        'adj': round(adj, 2),
        'uw_sig': uw_sig, 'uw_ok': uw_ok,
        'ww_sig': ww_sig, 'ww_ok': ww_ok,
    })

# ============================================================
# 统计输出
# ============================================================
N = len(results)
uw_acc = sum(1 for r in results if r['uw_ok']) / N * 100
ww_acc = sum(1 for r in results if r['ww_ok']) / N * 100

flips = [r for r in results if r['uw_sig'] != r['ww_sig']]
flip_fix = sum(1 for r in flips if r['ww_ok'] and not r['uw_ok'])
flip_break = sum(1 for r in flips if r['uw_ok'] and not r['ww_ok'])

print()
print("=" * 60)
print(f"             回测结果: {N} 个交易日")
print("=" * 60)
print(f"  不加权:  {uw_acc:.1f}% 准确率")
print(f"  加  权:  {ww_acc:.1f}% 准确率")
print(f"  ─────────────────────")
print(f"  相差:    {ww_acc-uw_acc:+.1f}%")
print()

# 信号翻转
print(f"  信号翻转: {len(flips)}次")
print(f"    加权纠正:  {flip_fix}次")
print(f"    加权反转错: {flip_break}次")
print(f"    净收益:    {flip_fix - flip_break}次")
print()

# 按市场环境
for label, cond in [
    ("大盘偏多 (mkt>0.1)", lambda r: r['mkt'] > 0.1),
    ("大盘偏空 (mkt<-0.1)", lambda r: r['mkt'] < -0.1),
    ("大盘中性", lambda r: -0.1 <= r['mkt'] <= 0.1),
]:
    subset = [r for r in results if cond(r)]
    if subset:
        uw = sum(1 for r in subset if r['uw_ok']) / len(subset) * 100
        ww = sum(1 for r in subset if r['ww_ok']) / len(subset) * 100
        print(f"  {label:<25} ({len(subset)}天): {uw:.0f}% -> {ww:.0f}%  ({ww-uw:+.0f}%)")

# 每日明细
print()
print("-" * 80)
print(f"{'日期':<10} {'午前%':>7} {'午后%':>7} {'br':>6} {'ir':>5} {'大盘':>6} {'板块':>6} {'加权前':<7} {'加权后':<7}")
print("-" * 80)
for r in results:
    uw_tag = f"{'✅看多' if r['uw_sig']==1 else '❌看空'}" if not r['uw_ok'] else f"{'✅看多' if r['uw_sig']==1 else '🔴看空'}"
    ww_tag = f"{'✅看多' if r['ww_sig']==1 else '❌看空'}" if not r['ww_ok'] else f"{'✅看多' if r['ww_sig']==1 else '🔴看空'}"
    # actual ok/wrong
    uw_m = "✅" if r['uw_ok'] else "❌"
    ww_m = "✅" if r['ww_ok'] else "❌"
    print(f"{r['date']:<10} {r['mp']:>+6.1f}% {r['ap']:>+6.1f}% {r['br']:>.3f} {r['ir']:>.1f}x {r['mkt']:>+6.2f} {r['sector']:>+6.2f} {uw_m}看{'多' if r['uw_sig']==1 else '空'}{' ' if len('看多')==2 else ''}  {ww_m}看{'多' if r['ww_sig']==1 else '空'}")

# 加权纠正的case
print()
print("=" * 60)
print("加权纠正错误 (不加权错→加权对):")
for r in results:
    if not r['uw_ok'] and r['ww_ok']:
        print(f"  {r['date']} 午前{r['mp']:+.1f}% 午后{r['ap']:+.1f}% "
              f"br={r['br']:.2f} 大盘={r['mkt']:+.2f} 板块={r['sector']:+.2f} "
              f"adj=x{r['adj']} 不加权{'多' if r['uw_sig']==1 else '空'}❌ -> 加权{'多' if r['ww_sig']==1 else '空'}✅")

print()
print("加权反转失败 (不加权对→加权错):")
for r in results:
    if r['uw_ok'] and not r['ww_ok']:
        print(f"  {r['date']} 午前{r['mp']:+.1f}% 午后{r['ap']:+.1f}% "
              f"br={r['br']:.2f} 大盘={r['mkt']:+.2f} 板块={r['sector']:+.2f} "
              f"adj=x{r['adj']} 不加权{'多' if r['uw_sig']==1 else '空'}✅ -> 加权{'多' if r['ww_sig']==1 else '空'}❌")
