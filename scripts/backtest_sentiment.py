import json
import sys

with open('data/kl_300418_1y.json', 'r') as f:
    data = json.load(f)

# Today's pattern (2026-07-03 so far, 10:15):
# prev_close = data[-2]['close'] = 45.55
# open = 44.30 => open_chg = (44.30-45.55)/45.55 = -2.74%
# high = 46.69 => high_from_open = (46.69-44.30)/44.30 = +5.4%
# low = 43.41 => low_from_open = (43.41-44.30)/44.30 = -2.01%
# amplitude = (46.69-43.41)/45.55 = 7.2%
# high_to_low = (43.41-46.69)/46.69 = -7.0% (peak to trough decline)

print('='*70)
print('昆仑万维 · 情绪波段回测')
print('今日模式: 低开急拉深跌')
print('='*70)

# Define pattern filter
# Pattern criteria: open_chg < -1.5%, high_from_open > 3%, high_to_low < -5%, amp > 6%

matches = []
for i in range(1, len(data)-1):  # skip first (no prev close), skip today
    curr = data[i]
    prev_close = data[i-1]['close']
    
    open_chg = (curr['open'] / prev_close - 1) * 100
    high_from_open = (curr['high'] / curr['open'] - 1) * 100
    low_from_open = (curr['low'] / curr['open'] - 1) * 100
    amp = (curr['high'] - curr['low']) / prev_close * 100
    high_to_low = (curr['low'] / curr['high'] - 1) * 100
    
    # Relaxed criteria to find similar patterns
    if (open_chg < -1.0 and high_from_open > 2.5 and high_to_low < -4.0 and amp > 5.0):
    # Strict criteria
    # if (open_chg < -1.5 and high_from_open > 3.0 and high_to_low < -5.0 and amp > 6.0):
        # For each match, calculate:
        # 1. Rebound from low same day: (close - low) / low * 100
        # 2. Next day chg: (next_day.close - curr.close) / curr.close * 100
        # 3. 2-day forward chg
        same_day_rebound = (curr['close'] - curr['low']) / curr['low'] * 100
        
        next_day_chg = None
        two_day_chg = None
        if i + 1 < len(data):
            next_day_chg = (data[i+1]['close'] / curr['close'] - 1) * 100
        if i + 2 < len(data):
            two_day_chg = (data[i+2]['close'] / curr['close'] - 1) * 100
        
        # Vol ratio vs 20-day avg
        vol_avg = sum(d['volume'] for d in data[max(0,i-20):i]) / min(i, 20)
        vol_ratio = curr['volume'] / vol_avg if vol_avg > 0 else 1
        
        # Prev day trend
        prev_chg = (curr['open'] / prev_close - 1) * 100  # effectively = open_chg
        
        matches.append({
            'date': curr['date'],
            'open': curr['open'],
            'high': curr['high'],
            'low': curr['low'],
            'close': curr['close'],
            'open_chg': open_chg,
            'high_from_open': high_from_open,
            'high_to_low': high_to_low,
            'amp': amp,
            'same_day_rebound': same_day_rebound,
            'next_day_chg': next_day_chg,
            'two_day_chg': two_day_chg,
            'vol_ratio': vol_ratio,
            'prev_chg': (curr['open']-prev_close)/prev_close*100
        })

print(f'\n匹配 {len(matches)} 个相似日 out of {len(data)-2}:')
print()

# Sort by similarity (closest to today's pattern)
# Weighted score: closer to open_chg=-2.7%, high_from_open=5.4%, high_to_low=-7.0%
for m in matches:
    m['score'] = (abs(m['open_chg'] - (-2.74)) * 1.0 + 
                  abs(m['high_from_open'] - 5.4) * 0.5 + 
                  abs(m['high_to_low'] - (-7.0)) * 0.3)
matches.sort(key=lambda x: x['score'])

# Display top matches
print(f'{"日期":>10} {"开%":>6} {"高%":>6} {"跌%":>6} {"幅%":>5} {"日弹":>5} {"次%":>6} {"2日%":>6} {"量比":>5}')
print('-'*62)
for m in matches[:15]:
    nd = f'{m["next_day_chg"]:+.1f}%' if m['next_day_chg'] is not None else 'N/A'
    td = f'{m["two_day_chg"]:+.1f}%' if m['two_day_chg'] is not None else 'N/A'
    print(f'{m["date"]} {m["open_chg"]:+5.1f}% {m["high_from_open"]:+5.1f}% {m["high_to_low"]:+5.1f}% {m["amp"]:4.1f}% {m["same_day_rebound"]:+4.1f}% {nd:>6} {td:>6} {m["vol_ratio"]:4.1f}x')

# Summary statistics
print()
print('='*70)
print('统计摘要:')
print()

valid_same_day = [m['same_day_rebound'] for m in matches]
valid_next = [m['next_day_chg'] for m in matches if m['next_day_chg'] is not None]
valid_two = [m['two_day_chg'] for m in matches if m['two_day_chg'] is not None]
valid_vol = [m['vol_ratio'] for m in matches]

print(f'样本数: {len(matches)}')
print()
print(f'日内从低点反弹:')
print(f'  均值: {sum(valid_same_day)/len(valid_same_day):+.1f}%')
print(f'  中位: {sorted(valid_same_day)[len(valid_same_day)//2]:+.1f}%')
print(f'  范围: {min(valid_same_day):+.1f}% ~ {max(valid_same_day):+.1f}%')
print(f'  正弹率: {sum(1 for x in valid_same_day if x>0)/len(valid_same_day)*100:.0f}%')
print()

print(f'次日涨跌:')
if valid_next:
    print(f'  均值: {sum(valid_next)/len(valid_next):+.1f}%')
    print(f'  中位: {sorted(valid_next)[len(valid_next)//2]:+.1f}%')
    print(f'  正率: {sum(1 for x in valid_next if x>0)/len(valid_next)*100:.0f}%')
    win_avg = sum(x for x in valid_next if x > 0) / max(1, sum(1 for x in valid_next if x > 0))
    loss_avg = sum(x for x in valid_next if x < 0) / max(1, sum(1 for x in valid_next if x < 0))
    print(f'  胜均: {win_avg:+.1f}% / 败均: {loss_avg:+.1f}%')

print()
print(f'2日涨跌:')
if valid_two:
    print(f'  均值: {sum(valid_two)/len(valid_two):+.1f}%')
    print(f'  中位: {sorted(valid_two)[len(valid_two)//2]:+.1f}%')
    print(f'  正率: {sum(1 for x in valid_two if x>0)/len(valid_two)*100:.0f}%')

print()
print(f'量比: 均值{sum(valid_vol)/len(valid_vol):.1f}x')

# Rebound level calculation
# "一般反弹到高点的百分之多少" - what % of the gap from low to high does the rebound recover
print()
print('='*70)
print('反弹幅度分析 (低点→收盘 占 高点→低点 的比例):')
rebound_ratios = []
for m in matches:
    total_drop = m['high'] - m['low']
    rebound = m['close'] - m['low']
    if total_drop > 0:
        ratio = rebound / total_drop * 100
        rebound_ratios.append(ratio)

if rebound_ratios:
    print(f'  均值: {sum(rebound_ratios)/len(rebound_ratios):.1f}%')
    print(f'  中位: {sorted(rebound_ratios)[len(rebound_ratios)//2]:.1f}%')
    print(f'  即: 平均反弹回到当日跌幅的 {sum(rebound_ratios)/len(rebound_ratios):.1f}%')
    # 0.382 retracement
    f381 = sum(1 for r in rebound_ratios if r >= 38.2) / len(rebound_ratios) * 100
    f500 = sum(1 for r in rebound_ratios if r >= 50) / len(rebound_ratios) * 100
    f618 = sum(1 for r in rebound_ratios if r >= 61.8) / len(rebound_ratios) * 100
    print(f'  过38.2%斐波: {f381:.0f}% | 过50%: {f500:.0f}% | 过61.8%: {f618:.0f}%')

# Apply to today: high=46.69, low=43.41
print()
print('='*70)
print('应用到今天 (高46.69 / 低43.41):')
total = 46.69 - 43.41
avg_ratio = sum(rebound_ratios)/len(rebound_ratios) if rebound_ratios else 50
med_ratio = sorted(rebound_ratios)[len(rebound_ratios)//2] if rebound_ratios else 50
print(f'  总跌幅: {total:.2f}元')
print(f'  历史均值反弹 {avg_ratio:.0f}% → 目标: {43.41+total*avg_ratio/100:.2f}元')
print(f'  历史中位反弹 {med_ratio:.0f}% → 目标: {43.41+total*med_ratio/100:.2f}元')
print(f'  38.2%斐波 → {43.41+total*0.382:.2f}元')
print(f'  50.0%斐波 → {43.41+total*0.50:.2f}元')
print(f'  61.8%斐波 → {43.41+total*0.618:.2f}元')
