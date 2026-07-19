"""
四渠道行为分析: 小单/中单/大单/特大单 ← 次日涨跌
验证不对称性: 机构伪装小单 vs 散户只能小单
"""

import json

def load(path):
    with open(path,'r',encoding='utf-8') as f:
        return json.load(f)

def to_f(x):
    return float(x) if x else 0

kl = load("F:/aidanao/data/kl_ddx_1y.json")
bl = load("F:/aidanao/data/bl_ddx_1y.json")

def analyze(name, data):
    print(f"\n{'='*70}")
    print(f" {name} — 四渠道次日预测力分析")
    print(f"{'='*70}")
    
    results = []
    for i in range(1, len(data)-1):
        c = to_f(data[i]['c'])
        nxt_c = to_f(data[i+1]['c'])
        nxt_ret = (nxt_c - c) / c
        
        small = to_f(data[i]['small'])
        mid = to_f(data[i]['mid'])
        main = to_f(data[i]['main'])
        jumbo = to_f(data[i]['jumbo'])
        
        results.append({
            'date': data[i]['d'],
            'next_ret': nxt_ret,
            'small': small, 'mid': mid, 'main': main, 'jumbo': jumbo,
        })
    
    # 每个渠道: "净买日" vs "净卖日" → 次日涨跌
    channels = [
        ("🔵 小单(<5万)", "small"),
        ("🟡 中单(5-20万)", "mid"),
        ("🟠 大单(20-100万)", "main"),
        ("🔴 特大单(>100万)", "jumbo"),
    ]
    
    print(f"\n{'渠道':<22} {'净买天数':>6} {'净买次日':>8} {'净卖天数':>6} {'净卖次日':>8} {'预测力'}")
    print(f"{'-'*65}")
    
    for label, field in channels:
        buy_days = [r for r in results if r[field] > 0]
        sell_days = [r for r in results if r[field] < 0]
        
        if buy_days and sell_days:
            buy_next = sum(r['next_ret'] for r in buy_days) / len(buy_days)
            sell_next = sum(r['next_ret'] for r in sell_days) / len(sell_days)
            predict = buy_next - sell_next
            
            arrow = "✅正向" if predict > 0.003 else "⚠️弱正" if predict > 0 else "❌反向" if predict < -0.003 else "⚪无"
            print(f"{label:<22} {len(buy_days):>6} {buy_next*100:>7.2f}% {len(sell_days):>6} {sell_next*100:>7.2f}% {arrow}")
        else:
            print(f"{label:<22} 数据不足")
    
    # 不对称性检验: "大单买+小单卖" vs "大单卖+小单买"
    print(f"\n{'='*65}")
    print(f"【不对称性验证】大单 vs 小单方向一致性的预测力")
    
    same_dir = [r for r in results if (r['main']>0) == (r['small']>0)]  # 同向
    oppo_dir = [r for r in results if (r['main']>0) != (r['small']>0)]  # 反向
    
    if same_dir and oppo_dir:
        same_next = sum(r['next_ret'] for r in same_dir) / len(same_dir)
        oppo_next = sum(r['next_ret'] for r in oppo_dir) / len(oppo_dir)
        
        print(f"  大单小单同向: {len(same_dir)}天 次日+{same_next*100:.2f}%")
        print(f"  大单小单反向: {len(oppo_dir)}天 次日+{oppo_next*100:.2f}%")
        
        # 最有趣的: 大单买+小单卖 (机构买, 散户卖) ← 最健康的信号
        inst_buy_ret_sell = [r for r in results if r['main'] > 0 and r['small'] < 0]
        inst_sell_ret_buy = [r for r in results if r['main'] < 0 and r['small'] > 0]
        
        if inst_buy_ret_sell:
            avg = sum(r['next_ret'] for r in inst_buy_ret_sell) / len(inst_buy_ret_sell)
            print(f"\n  🔥 大单买+小单卖(机构接散户出): {len(inst_buy_ret_sell)}天 次日+{avg*100:.2f}% ← 最佳信号")
        if inst_sell_ret_buy:
            avg = sum(r['next_ret'] for r in inst_sell_ret_buy) / len(inst_sell_ret_buy)
            print(f"  🚨 大单卖+小单买(机构出给散户): {len(inst_sell_ret_buy)}天 次日+{avg*100:.2f}% ← 最危险信号")
    
    # 昆仑今天验证
    today = results[-1] if results else None
    if today:
        print(f"\n  {'='*65}")
        print(f"  最新一天 ({today['date']}):")
        print(f"    小单: {today['small']/1e8:+.2f}亿 {'散户在买' if today['small']>0 else '散户在卖'}")
        print(f"    中单: {today['mid']/1e8:+.2f}亿")
        print(f"    大单: {today['main']/1e8:+.2f}亿 {'主力在买' if today['main']>0 else '主力在卖'}")
        print(f"    特大单: {today['jumbo']/1e8:+.2f}亿")
        
        if today['main'] > 0 and today['small'] < 0:
            print(f"    → 大单买+小单卖 = 机构在接散户的盘 ✅ 健康")
        elif today['main'] > 0 and today['small'] > 0:
            print(f"    → 大单买+小单买 = 机构散户共振追涨 ⚠️")
        elif today['main'] < 0 and today['small'] > 0:
            print(f"    → 大单卖+小单买 = 机构出给散户 🚨")

analyze("昆仑万维 300418", kl)
analyze("蓝色光标 300058", bl)
