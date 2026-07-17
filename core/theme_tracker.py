"""
题材资金追踪器 — 基于 tushare moneyflow_cnt_ths
每天自动拉取382个概念板块的资金净买, 按AI细分/游戏/传媒分类
"""
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'tushare')

def load_bridge():
    from core.tushare_bridge import ts
    return ts

def pull_concept_flow(date=None):
    """拉取某天的概念板块资金流"""
    ts = load_bridge()
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    data = ts.moneyflow_cnt_ths(trade_date=date)
    if not data:
        return []
    
    items = []
    for r in data:
        items.append({
            'date': r[0],
            'code': r[1],
            'name': r[2],
            'lead_stock': r[3],
            'close': r[4],
            'pct_chg': float(r[5]) if r[5] else 0,
            'index': float(r[6]) if r[6] else 0,
            'companies': int(r[7]) if r[7] else 0,
            'lead_pct': float(r[8]) if r[8] else 0,
            'buy_amount': float(r[9]) if r[9] else 0,
            'sell_amount': float(r[10]) if r[10] else 0,
            'net_amount': float(r[11]) if r[11] else 0
        })
    return items

def track_our_themes(data):
    """追踪我们持仓相关的细分题材"""
    
    themes = {
        'AI智能体': ['AI智能体', 'ChatGPT概念'],
        'AI游戏': ['手机游戏', '网络游戏', '云游戏', '短剧游戏', '电子竞技'],
        'AI营销/广告': ['AIGC概念', '文化传媒概念', '网红经济', '直播概念'],
        'AI模型': ['多模态AI', '智谱AI', 'AI语料', '算力概念', '数据中心'],
        'AI硬件': ['AI手机', 'AI眼镜', '智能穿戴', '智能音箱'],
    }
    
    print(f"\n{'='*60}")
    print(f"  📊 题材资金追踪")
    print(f"{'='*60}")
    
    for theme_cat, keywords in themes.items():
        matches = []
        for item in data:
            if any(kw in item['name'] for kw in keywords) or any(item['name'] in kw for kw in keywords):
                matches.append(item)
        
        if matches:
            # Sort by net amount
            matches.sort(key=lambda x: x['net_amount'], reverse=True)
            total_net = sum(m['net_amount'] for m in matches)
            leading = '🔥' if total_net > 50 else '✅' if total_net > 0 else '🧊' if total_net > -50 else '🚨'
            
            print(f"\n  {leading} {theme_cat} (总净买{total_net:+.0f}亿):")
            for m in matches[:8]:
                arrow = '▲' if m['net_amount'] > 0 else '▼'
                print(f"    {arrow} {m['name']:14s}  {m['pct_chg']:>+5.1f}%  净买{m['net_amount']:>+6.0f}亿  [{m['lead_stock']}]")
    
    # TOP10 overall
    print(f"\n  🏆 全市场TOP10资金流入:")
    sorted_data = sorted(data, key=lambda x: x['net_amount'], reverse=True)
    for i, item in enumerate(sorted_data[:10]):
        print(f"    {i+1:2d}. {item['name']:14s} 净买{item['net_amount']:>+6.0f}亿  {item['pct_chg']:>+5.1f}%")
    
    # BOTTOM10
    print(f"\n  📉 全市场TOP10资金流出:")
    sorted_rev = sorted(data, key=lambda x: x['net_amount'])
    for i, item in enumerate(sorted_rev[:10]):
        print(f"    {i+1:2d}. {item['name']:14s} 净买{item['net_amount']:>+6.0f}亿  {item['pct_chg']:>+5.1f}%")

if __name__ == '__main__':
    data = pull_concept_flow('20260710')
    print(f'拉取: {len(data)}个概念板块')
    track_our_themes(data)
