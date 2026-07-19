#!/usr/bin/env python3
"""
回测验证 volume-battle-analyzer 的信号准确性

测试:
  1. 单独信号准确率（只看量能对战）
  2. 叠加信号准确率（量能对战 + 收盘位置 + 量能强度比）
  3. 跨市场制度对比（牛市/震荡/近期）
  4. 核心问题: 上午的量能结构 → 下午的方向是否正确？

数据源: WeStock MCP data_minute (需在WorkBuddy环境中调用)
"""
import sys, os, json
from datetime import datetime
from collections import defaultdict

# ═══ 手动填入历史分钟数据（从WeStock MCP拉取后填入）═══
# 格式: 每行 "HHMM price cum_vol cum_amt"
# 后续可通过WorkBuddy的MCP工具自动填充

def parse_minute(raw_lines):
    bars = []
    prev_cum = 0
    prev_price = None
    for line in raw_lines:
        parts = line.strip().split()
        if len(parts) < 3: continue
        t, price, cum_vol = parts[0], float(parts[1]), int(parts[2])
        vol = cum_vol - prev_cum if prev_cum > 0 else cum_vol
        direction = 'open' if prev_price is None else ('up' if price >= prev_price else 'down')
        bars.append({'time':t, 'price':price, 'vol':vol, 'cum_vol':cum_vol, 'dir':direction})
        prev_cum, prev_price = cum_vol, price
    return bars

def analyze_morning_vs_afternoon(bars):
    """上午(0930-1130)量能结构 vs 下午(1300-1500)实际走势"""
    morning = [b for b in bars if b['time'] <= '1130']
    afternoon = [b for b in bars if b['time'] >= '1300']
    
    if not morning or not afternoon:
        return None
    
    # 上午分析
    m_up = [b for b in morning if b['dir'] == 'up']
    m_down = [b for b in morning if b['dir'] == 'down']
    m_up_vol = sum(b['vol'] for b in m_up)
    m_down_vol = sum(b['vol'] for b in m_down)
    m_total = m_up_vol + m_down_vol
    
    if m_total == 0: return None
    
    bull_ratio = m_up_vol / m_total
    up_intensity = m_up_vol / max(len(m_up), 1)
    down_intensity = m_down_vol / max(len(m_down), 1)
    intensity_ratio = up_intensity / max(down_intensity, 1)
    
    # 收盘位置判断
    morning_open = morning[0]['price']
    morning_close = morning[-1]['price']
    morning_pct = (morning_close - morning_open) / morning_open * 100
    
    # 下午实际走势
    aft_open = afternoon[0]['price']
    aft_close = afternoon[-1]['price']
    aft_pct = (aft_close - aft_open) / aft_open * 100
    
    # 全天
    day_open = bars[0]['price']
    day_close = bars[-1]['price']
    day_pct = (day_close - day_open) / day_open * 100
    
    # 信号判定
    # 单信号1: 多头量能比>55%
    s1_bull = bull_ratio > 0.55
    # 单信号2: 强度比>1.3
    s2_bull = intensity_ratio > 1.3
    # 叠加信号: 两个都满足
    s_combined = s1_bull and s2_bull
    
    # 结果: 下午涨=正确，下午跌=错误
    prediction_bull = s_combined  # 叠加信号判断看多
    
    return {
        'morning_pct': round(morning_pct, 2),
        'afternoon_pct': round(aft_pct, 2),
        'day_pct': round(day_pct, 2),
        'bull_ratio': round(bull_ratio, 3),
        'intensity_ratio': round(intensity_ratio, 2),
        's1_bull_ratio': s1_bull,
        's2_intensity': s2_bull,
        's_combined': s_combined,
        'aft_up': aft_pct > 0,
        'correct_s1': s1_bull == (aft_pct > 0),
        'correct_s2': s2_bull == (aft_pct > 0),
        'correct_combined': prediction_bull == (aft_pct > 0),
    }


def run_backtest(test_days: dict) -> dict:
    """对一组交易日运行回测"""
    results = []
    for label, day_data in test_days.items():
        for date_str, raw_lines in day_data.items():
            bars = parse_minute(raw_lines)
            r = analyze_morning_vs_afternoon(bars)
            if r:
                r['date'] = date_str
                r['regime'] = label
                results.append(r)
    
    # 统计
    total = len(results)
    stats = {
        'total_days': total,
        's1_accuracy': sum(1 for r in results if r['correct_s1']) / max(total, 1),
        's2_accuracy': sum(1 for r in results if r['correct_s2']) / max(total, 1),
        'combined_accuracy': sum(1 for r in results if r['correct_combined']) / max(total, 1),
    }
    
    # 按制度分组
    by_regime = defaultdict(list)
    for r in results:
        by_regime[r['regime']].append(r)
    
    regime_stats = {}
    for regime, days in by_regime.items():
        n = len(days)
        regime_stats[regime] = {
            'days': n,
            'bull_ratio_avg': round(sum(d['bull_ratio'] for d in days)/n, 3),
            's1_acc': round(sum(1 for d in days if d['correct_s1'])/n, 3),
            's2_acc': round(sum(1 for d in days if d['correct_s2'])/n, 3),
            'combined_acc': round(sum(1 for d in days if d['correct_combined'])/n, 3),
        }
    
    return {
        'overall': stats,
        'by_regime': regime_stats,
        'details': results,
    }


# ═══ CLI ═══
if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════╗
║  volume-battle 回测验证工具               ║
╠═══════════════════════════════════════════╣
║  用法:                                    ║
║  1. 在 WorkBuddy 中用 MCP 拉取分钟数据     ║
║  2. 填入 test_days dict                   ║
║  3. python backtest_volume_battle.py      ║
╠═══════════════════════════════════════════╣
║  单信号1: 多头量能比 >55% = 看多            ║
║  单信号2: 强度比 >1.3x = 看多              ║
║  叠加信号: 两个都满足 = 看多               ║
║  验证: 看多 → 下午涨 = 正确               ║
╚═══════════════════════════════════════════╝
    """)
