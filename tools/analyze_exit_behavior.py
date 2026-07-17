"""
T+1解锁行为回测: 昨天买入的人 → 今天何时卖？
核心问题: 持仓盈亏对次日卖出的影响
用真DDX+涨跌数据验证
"""

import json

def load(path):
    with open(path,'r',encoding='utf-8') as f:
        return json.load(f)

def to_float(x):
    return float(x) if x else 0

kl = load("F:/aidanao/data/kl_ddx_1y.json")
bl = load("F:/aidanao/data/bl_ddx_1y.json")

def analyze(name, data):
    print(f"\n{'='*60}")
    print(f" {name} — 昨日买入者的次日行为分析")
    print(f"{'='*60}")
    
    # 计算: prev_ret (昨天的日涨幅，代表昨日买入者的盈亏状况)
    #       small_today (今天的小单方向，代表散户今天在干嘛)
    #       main_today (今天的主力方向)
    
    # 分组: 昨日涨/跌 → 今天散户的买卖行为
    results = []
    for i in range(2, len(data)):
        prev_close = to_float(data[i-1]['c'])
        curr_close = to_float(data[i]['c'])
        prev_ret = (prev_close - to_float(data[i-2]['c'])) / to_float(data[i-2]['c'])
        curr_ret = (curr_close - prev_close) / prev_close
        
        small = to_float(data[i]['small'])
        main = to_float(data[i]['main'])
        
        results.append({
            'date': data[i]['d'],
            'prev_ret': prev_ret,   # 昨天涨跌 = 昨日买入者的浮盈状况
            'curr_ret': curr_ret,   # 今天涨跌
            'small': small,          # 今天小单方向
            'main': main,            # 今天主力方向
            'prev_close': prev_close,
            'curr_close': curr_close,
        })
    
    # === 核心分析: 昨日盈亏 → 今日散户行为 ===
    print(f"\n【核心问题】昨天赚了 vs 昨天亏了 → 今天散户是买还是卖？")
    print()
    
    # 昨天涨>2% (浮盈较显著)
    up2pct = [r for r in results if r['prev_ret'] > 0.02]
    # 昨天跌>2% (浮亏较显著)
    dn2pct = [r for r in results if r['prev_ret'] < -0.02]
    # 昨天平(小波动)
    flat = [r for r in results if -0.02 <= r['prev_ret'] <= 0.02]
    
    if up2pct:
        avg_small = sum(r['small'] for r in up2pct) / len(up2pct)
        sell_days = sum(1 for r in up2pct if r['small'] < 0)
        print(f"  昨天涨>2%(浮盈): {len(up2pct)}天")
        print(f"    今天散户平均净流: {avg_small/1e8:+.2f}亿")
        print(f"    散户在卖的天数: {sell_days}/{len(up2pct)} ({sell_days/len(up2pct)*100:.0f}%)")
        print(f"    → 浮盈后: {'散户在卖(获利了结)' if avg_small < 0 else '散户还在追!'}")
    
    if dn2pct:
        avg_small = sum(r['small'] for r in dn2pct) / len(dn2pct)
        sell_days = sum(1 for r in dn2pct if r['small'] < 0)
        print(f"\n  昨天跌>2%(浮亏): {len(dn2pct)}天")
        print(f"    今天散户平均净流: {avg_small/1e8:+.2f}亿")
        print(f"    散户在卖的天数: {sell_days}/{len(dn2pct)} ({sell_days/len(dn2pct)*100:.0f}%)")
        print(f"    → 浮亏后: {'散户在割肉' if avg_small < 0 else '散户在扛(不卖)'}")
    
    if flat:
        avg_small = sum(r['small'] for r in flat) / len(flat)
        print(f"\n  昨天±2%内(微波动): {len(flat)}天")
        print(f"    今天散户平均净流: {avg_small/1e8:+.2f}亿")
    
    # === 细化: 不同浮盈幅度 → 卖出概率 ===
    print(f"\n【细化】浮盈幅度 vs 散户卖出概率")
    buckets = [(-0.20,-0.05), (-0.05,-0.02), (-0.02,0), (0,0.02), (0.02,0.05), (0.05,0.10), (0.10,0.30)]
    for lo, hi in buckets:
        bucket = [r for r in results if lo <= r['prev_ret'] < hi]
        if len(bucket) < 3: continue
        sell_pct = sum(1 for r in bucket if r['small'] < 0) / len(bucket) * 100
        avg_small = sum(r['small'] for r in bucket) / len(bucket) / 1e8
        next_ret = sum(r['curr_ret'] for r in bucket) / len(bucket) * 100
        bar = '█' * int(sell_pct/5)
        print(f"  浮盈{lo*100:+5.0f}%~{hi*100:+5.0f}%: {len(bucket):3d}天 卖出率{sell_pct:5.0f}% {bar} 散户{avg_small:+.2f}亿 今天涨{next_ret:+.1f}%")
    
    # 极端负浮盈上找小sample
    deep_loss = [r for r in results if r['prev_ret'] < -0.05]
    if deep_loss:
        sell_pct = sum(1 for r in deep_loss if r['small'] < 0) / len(deep_loss) * 100
        print(f"  浮亏>5%(深套): {len(deep_loss)}天 卖出率{sell_pct:.0f}% 散户{sum(r['small'] for r in deep_loss)/len(deep_loss)/1e8:+.2f}亿")
    
    # === 关键指标: 何时散户逃跑 ===
    print(f"\n【关键结论】")
    # 什么时候散户最可能卖出？
    max_sell_bucket = max(buckets, key=lambda b: (
        sum(1 for r in results if b[0]<=r['prev_ret']<b[1] and r['small']<0) / 
        max(1, sum(1 for r in results if b[0]<=r['prev_ret']<b[1])) 
        if sum(1 for r in results if b[0]<=r['prev_ret']<b[1]) >= 3 else 0
    ))
    bucket = [r for r in results if max_sell_bucket[0] <= r['prev_ret'] < max_sell_bucket[1]]
    if bucket:
        sell_pct = sum(1 for r in bucket if r['small'] < 0) / len(bucket) * 100
        print(f"  散户卖出概率最高的区间: 浮盈{max_sell_bucket[0]*100:+.0f}~{max_sell_bucket[1]*100:+.0f}% ({sell_pct:.0f}%)")
        print(f"    → 散户最倾向于在{sell_pct:.0f}%的情况下卖出")

analyze("昆仑万维", kl)
analyze("蓝色光标", bl)
