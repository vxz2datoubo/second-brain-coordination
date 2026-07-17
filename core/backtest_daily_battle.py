#!/usr/bin/env python
"""日K级别: 量能对战 + 三维加权 回测 (200-300天)"""

import json, sys, os
from collections import defaultdict

# Fix import path BEFORE importing core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tushare_bridge import TushareBridge

b = TushareBridge()

# ─── 拉数据 ───
kl_raw = b.daily('300418.SZ', '20250101', '20260710')
sh_raw = b._call('index_daily', {'ts_code':'000001.SH','start_date':'20250101','end_date':'20260710'})

print(f"昆仑: {len(kl_raw)} 条  上证: {len(sh_raw)} 条")

# ─── 解析: reverse = latest first → sort ascending ───
# 昆仑: [ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount]
# 上证: same
def parse_daily(raw):
    bars = []
    for r in raw:
        try:
            date = str(r[1])[:8]
            bars.append({
                'date': date,
                'open': float(r[2]),
                'high': float(r[3]),
                'low': float(r[4]),
                'close': float(r[5]),
                'vol': float(r[9]),  # idx9=vol, idx8=pct_chg!
                'pct': float(r[8]) if len(r) > 8 else 0,
            })
        except: pass
    bars.sort(key=lambda x: x['date'])
    return bars

kl = parse_daily(kl_raw)
sh = parse_daily(sh_raw)

print(f"解析后: 昆仑 {len(kl)} 条 ({kl[0]['date']} → {kl[-1]['date']})")
print(f"解析后: 上证 {len(sh)} 条 ({sh[0]['date']} → {sh[-1]['date']})")

# ─── 对齐两个数据源 ───
sh_map = {r['date']: r for r in sh}
aligned = []
for k in kl:
    s = sh_map.get(k['date'])
    if s:
        aligned.append({'kl': k, 'sh': s})

print(f"对齐后: {len(aligned)} 天")

# ═══════════════════════════════════════════
# 核心回测: 日K量能对战 → 预测次日
# ═══════════════════════════════════════════

LOOKBACK = 5  # 缩到5天，信号更敏感

results = []

for i in range(LOOKBACK, len(aligned) - 1):
    today = aligned[i]
    tomorrow = aligned[i + 1]
    
    # ── 1. 量能比 (滚动5天窗口) ──
    up_vol = 0
    down_vol = 0
    for j in range(i - LOOKBACK, i):
        prev = aligned[j]['kl']
        cur = aligned[j + 1]['kl']
        if cur['close'] >= prev['close']:
            up_vol += cur['vol']
        else:
            down_vol += cur['vol']
    
    total_vol = up_vol + down_vol
    if total_vol == 0:
        continue
    
    br = up_vol / total_vol
    
    # 量能信号: 偏离50%越多越强
    # br in [0,1] -> raw_signal in [-1, 1]
    raw_signal = (br - 0.5) * 2
    
    # ── 2. 三维上下文 (基于TODAY) ──
    market_pct = today['sh']['pct']
    market_score = max(-1.0, min(1.0, market_pct / 1.5))  # 1.5%涨跌=满信号(更敏感)
    
    kl_pct = today['kl']['pct']
    rel_strength = kl_pct - market_pct
    sector_score = max(-1.0, min(1.0, rel_strength / 1.5))  # 同样更敏感
    
    # ── 3. 次日实际 ──
    next_pct = ((tomorrow['kl']['close'] - today['kl']['close']) / today['kl']['close']) * 100
    next_dir = 1 if next_pct > 0 else -1
    
    # ── 4. 不加权 ──
    uw_signal = 1 if raw_signal > 0 else -1
    uw_correct = (uw_signal == next_dir)
    
    # ── 5. 三维加权 (上下文否决模式) ──
    dirs = [market_score, sector_score]
    br_strength = abs(raw_signal)
    threshold = max(0.03, 0.1 - br_strength * 0.05)
    pos = sum(1 for d in dirs if d > threshold)
    neg = sum(1 for d in dirs if d < -threshold)
    
    ww_signal = uw_signal  # 默认与不加权相同
    flip_reason = ''
    
    if raw_signal > 0:  # 看多
        if pos == 2:
            # 共振看多 → 原信号生效
            pass
        elif pos == 1:
            # 弱共振 → 原信号生效
            pass
        elif neg == 2:
            # 二维背离 → 看多信号降级为中性
            ww_signal = 0
            flip_reason = f'双维看空→看多信号被否决'
        elif neg == 1:
            # 弱背离 → 保持但降低置信
            if br < 0.55:  # 本身信号不强时更容易被否决
                ww_signal = 0
                flip_reason = f'弱信号+单维看空→否决'
    
    elif raw_signal < 0:  # 看空
        if neg == 2:
            pass
        elif neg == 1:
            pass
        elif pos == 2:
            ww_signal = 0
            flip_reason = f'双维看多→看空信号被否决'
        elif pos == 1:
            if br > 0.45:
                ww_signal = 0
                flip_reason = f'弱信号+单维看多→否决'
    
    # 极端市场 → 直接否决逆势信号
    if market_score < -0.4 and raw_signal > 0:
        ww_signal = 0
        flip_reason = f'大盘暴跌→否决看多(mkt={market_score:.2f})'
    if market_score > 0.4 and raw_signal < 0:
        ww_signal = 0
        flip_reason = f'大盘暴涨→否决看空(mkt={market_score:.2f})'
    
    # 如果加权后是中性(0) → 视为"不预测"，不算对也不算错
    ww_correct = None if ww_signal == 0 else (ww_signal == next_dir)
    adj_rec = {
        'pos': pos, 'neg': neg, 'flip': flip_reason,
        'neutral': ww_signal == 0
    }
    
    results.append({
        'date': today['kl']['date'],
        'br': round(br, 3),
        'raw_sig': round(raw_signal, 3),
        'kl_pct': round(kl_pct, 2),
        'mkt': round(market_score, 3),
        'sector': round(sector_score, 3),
        'pos': adj_rec['pos'],
        'neg': adj_rec['neg'],
        'flip': adj_rec['flip'],
        'next_pct': round(next_pct, 2),
        'next_dir': next_dir,
        'uw_sig': uw_signal,
        'uw_ok': uw_correct,
        'ww_sig': ww_signal,
        'ww_ok': ww_correct,
    })

# ═══════════════════════════════════════════
# 统计
# ═══════════════════════════════════════════
N = len(results)
N_pred_ww = sum(1 for r in results if r['ww_ok'] is not None)  # 加权有信号的天数
N_neut_ww = N - N_pred_ww  # 加权拒绝了信号(归零)的天数

uw_acc = sum(1 for r in results if r['uw_ok']) / N * 100
ww_acc = sum(1 for r in results if r['ww_ok'] is True) / N_pred_ww * 100 if N_pred_ww > 0 else 0

print()
print("=" * 70)
print(f"  日K量能对战 + 三维加权 回测结果:  {N} 天")
print("=" * 70)
print(f"  不加权:  {uw_acc:.1f}% 准确率 (始终有信号)")
print(f"  加  权:  {ww_acc:.1f}% 准确率 (仅{N_pred_ww}天有信号, {N_neut_ww}天否决为中性)")
print(f"  ─────────────────────")
print(f"  准确率提升: {ww_acc - uw_acc:+.1f}%")
print()

# 信号翻转分析
flips = [r for r in results if r['ww_sig'] != r['uw_sig']]  # 包括归零(0)
flips_direction = [r for r in flips if r['ww_sig'] != 0]  # 真正反转
flips_neutral = [r for r in flips if r['ww_sig'] == 0]    # 否决
flip_fix = sum(1 for r in flips if r['ww_ok'] is True and not r['uw_ok'])
flip_break = sum(1 for r in flips if r['uw_ok'] and r['ww_ok'] is False)
flip_neut_save = sum(1 for r in flips_neutral if not r['uw_ok'])  # 否决了原本会错的信号
flip_neut_waste = sum(1 for r in flips_neutral if r['uw_ok'])     # 否决了原本对的信号

print(f"  信号翻转(含归零): {len(flips)} 次 / {N} 天 ({len(flips)/N*100:.1f}%)")
print(f"    方向反转: {len(flips_direction)} 次")
print(f"    否决归零: {len(flips_neutral)} 次")
print(f"      否决避错: {flip_neut_save} 次 (原本会错)")
print(f"      否决误杀: {flip_neut_waste} 次 (原本会对)")
print(f"    净收益:    {flip_fix - flip_break + flip_neut_save - flip_neut_waste} 次")

# 按市场环境
print()
print("-" * 70)
print(f"{'市场环境':<30} {'天数':>4} {'不加权':>7} {'加权':>7} {'提升':>7}")
print("-" * 70)
regimes = [
    ("🐂 大盘偏多  (mkt>0.15)", lambda r: r['mkt'] > 0.15),
    ("🐻 大盘偏空  (mkt<-0.15)", lambda r: r['mkt'] < -0.15),
    ("➡ 大盘中性", lambda r: -0.15 <= r['mkt'] <= 0.15),
    ("📈 大盘暴涨  (mkt>0.4)", lambda r: r['mkt'] > 0.4),
    ("📉 大盘暴跌  (mkt<-0.4)", lambda r: r['mkt'] < -0.4),
    ("⚠️ 逆势看多  (看多+大盘偏空)", lambda r: r['uw_sig'] == 1 and r['mkt'] < -0.1),
    ("⚠️ 逆势看空  (看空+大盘偏多)", lambda r: r['uw_sig'] == -1 and r['mkt'] > 0.1),
    ("🎯 共振看多  (看多+大盘偏多)", lambda r: r['uw_sig'] == 1 and r['mkt'] > 0.1),
    ("🎯 共振看空  (看空+大盘偏空)", lambda r: r['uw_sig'] == -1 and r['mkt'] < -0.1),
]
for label, cond in regimes:
    subset = [r for r in results if cond(r)]
    if len(subset) >= 5:
        uw = sum(1 for r in subset if r['uw_ok']) / len(subset) * 100
        ww_pred = [r for r in subset if r['ww_ok'] is not None]
        ww = sum(1 for r in ww_pred if r['ww_ok'] is True) / len(ww_pred) * 100 if ww_pred else 0
        neut = sum(1 for r in subset if r['ww_sig'] == 0)
        mark = "✅" if ww > uw else ("⚠️" if ww < uw else "＝")
        print(f"  {label:<28} {len(subset):>4}   {uw:>5.1f}%  {ww:>5.1f}%  {ww-uw:>+4.1f}% {mark} (否决{neut}次)")

# 信号分布
print()
print("-" * 70)
uw_bull = sum(1 for r in results if r['uw_sig'] == 1)
ww_bull = sum(1 for r in results if r['ww_sig'] == 1)
ww_neut = sum(1 for r in results if r['ww_sig'] == 0)
print(f"  不加权: 看多{uw_bull}次({uw_bull/N*100:.0f}%)  看空{N-uw_bull}次({(N-uw_bull)/N*100:.0f}%)")
print(f"  加  权: 看多{ww_bull}次({ww_bull/N*100:.0f}%)  看空{N-ww_bull-ww_neut}次({(N-ww_bull-ww_neut)/N*100:.0f}%)  中性{ww_neut}次({ww_neut/N*100:.0f}%)")

# 加权纠正明细
print()
print("=" * 70)
print("  加权纠正错误 (不加权错 → 加权对/否决避错):")
print("=" * 70)
for r in results:
    if not r['uw_ok'] and (r['ww_ok'] is True):
        print(f"  {r['date']}  br={r['br']:.3f} 个股{r['kl_pct']:+.1f}% 大盘={r['mkt']:+.2f} "
              f"板块={r['sector']:+.2f} 次日{r['next_pct']:+.1f}% "
              f"不加权{'多' if r['uw_sig']==1 else '空'}❌→加权{'多' if r['ww_sig']==1 else '空' if r['ww_sig']!=0 else '弃权'}✅")
for r in results:
    if not r['uw_ok'] and r['ww_sig'] == 0:
        print(f"  {r['date']}  br={r['br']:.3f} 个股{r['kl_pct']:+.1f}% 大盘={r['mkt']:+.2f} "
              f"板块={r['sector']:+.2f} 次日{r['next_pct']:+.1f}% "
              f"不加权{'多' if r['uw_sig']==1 else '空'}❌→加权弃权✅ (避错) 原因:{r['flip']}")

print()
print("=" * 70)
print("  加权反转失败 (不加权对 → 加权错/误杀):")
print("=" * 70)
for r in results:
    if r['uw_ok'] and r['ww_ok'] is False:
        print(f"  {r['date']}  br={r['br']:.3f} 个股{r['kl_pct']:+.1f}% 大盘={r['mkt']:+.2f} "
              f"板块={r['sector']:+.2f} 次日{r['next_pct']:+.1f}% "
              f"不加权{'多' if r['uw_sig']==1 else '空'}✅→加权{'多' if r['ww_sig']==1 else '空'}❌")
for r in results:
    if r['uw_ok'] and r['ww_sig'] == 0:
        print(f"  {r['date']}  br={r['br']:.3f} 个股{r['kl_pct']:+.1f}% 大盘={r['mkt']:+.2f} "
              f"板块={r['sector']:+.2f} 次日{r['next_pct']:+.1f}% "
              f"不加权{'多' if r['uw_sig']==1 else '空'}✅→加权弃权⚠️ (误杀) 原因:{r['flip']}")

# 月度分解
print()
print("=" * 70)
print("  按月准确率分解:")
print("=" * 70)
months = defaultdict(list)
for r in results:
    m = r['date'][:6]
    months[m].append(r)
print(f"  {'月份':<6} {'天':>3} {'br_avg':>6} {'mkt':>6} {'不加权':>7} {'加权':>7} {'提升':>6} {'否决':>4}")
for m in sorted(months.keys()):
    subset = months[m]
    uw = sum(1 for r in subset if r['uw_ok']) / len(subset) * 100
    ww_pred = [r for r in subset if r['ww_ok'] is not None]
    ww = sum(1 for r in ww_pred if r['ww_ok'] is True) / len(ww_pred) * 100 if ww_pred else 0
    neut = sum(1 for r in subset if r['ww_sig'] == 0)
    avg_br = sum(r['br'] for r in subset) / len(subset)
    avg_mkt = sum(r['mkt'] for r in subset) / len(subset)
    print(f"  {m:<6} {len(subset):>3}  {avg_br:.3f}  {avg_mkt:>+5.2f}  {uw:>5.0f}%  {ww:>5.0f}%  {ww-uw:>+5.0f}%  {neut:>3}")
