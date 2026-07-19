# -*- coding: utf-8 -*-
import urllib.request
import json

def get_volume_profile(code, days=5):
    """获取分时量和价格分布"""
    results = {}
    
    # 获取日K数据
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sz{code},day,,,{days},qfq"
    try:
        data = urllib.request.urlopen(url, timeout=5).read().decode("utf-8")
        parsed = json.loads(data)
        stock = parsed.get("data", {}).get(f"sz{code}", {})
        for key in ["day", "qfqday"]:
            if key in stock:
                return stock[key]
    except Exception as e:
        return []
    return []

def get_minute_data(code):
    """获取分钟K线"""
    url = f"http://web.ifzq.gtimg.cn/appstock/app/minute/query?param=sz{code},5"
    try:
        data = urllib.request.urlopen(url, timeout=5).read().decode("utf-8")
        parsed = json.loads(data)
        stock = parsed.get("data", {}).get(f"sz{code}", {})
        return stock.get("data", [])
    except:
        return []

# ===== 昆仑万维 Volume Profile =====
print("=" * 70)
print("  量价剖面分析 — 昆仑万维(300418)")
print("=" * 70)

# 日K数据
kline = get_volume_profile(300418, 10)

if kline:
    print("\n近10日量价汇总:")
    print("-" * 70)
    print(f"{'日期':^12} {'开盘':^8} {'收盘':^8} {'最高':^8} {'最低':^8} {'成交量(万)':^12} {'形态':^10}")
    print("-" * 70)
    
    for d in kline:
        date = d[0]
        open_p = float(d[1])
        close = float(d[2])
        high = float(d[3])
        low = float(d[4])
        try:
            vol = int(float(d[5])) / 10000
        except:
            vol = 0
        
        change = (close - open_p) / open_p * 100 if open_p > 0 else 0
        icon = "▲" if change >= 0 else "▼"
        pattern = ""
        
        # 判断形态
        body = abs(close - open_p)
        upper_shadow = high - max(open_p, close)
        lower_shadow = min(open_p, close) - low
        full_range = high - low
        
        if full_range > 0:
            body_ratio = body / full_range
            if body_ratio > 0.8:
                pattern = "大实体"
            elif upper_shadow > lower_shadow * 2:
                pattern = "上影线"
            elif lower_shadow > upper_shadow * 2:
                pattern = "下影线"
            elif body_ratio < 0.2:
                pattern = "十字星"
            else:
                pattern = "正常"
        else:
            pattern = "一字"
        
        print(f"{date:^12} {open_p:^8.2f} {close:^8.2f} {high:^8.2f} {low:^8.2f} {vol:^12.0f} {pattern:^10}")

    # 成交量分析
    print("\n" + "=" * 70)
    print("  成交量分析")
    print("-" * 70)
    
    vols = []
    for d in kline:
        try:
            vol = int(float(d[5]))
            vols.append(vol)
        except:
            pass
    
    if vols:
        avg_vol = sum(vols) / len(vols)
        max_vol = max(vols)
        min_vol = min(vols)
        
        print(f"  平均成交量: {avg_vol/10000:.1f}万手")
        print(f"  最大成交量: {max_vol/10000:.1f}万手")
        print(f"  最小成交量: {min_vol/10000:.1f}万手")
        print(f"  量能趋势: ", end="")
        
        if vols[-1] > avg_vol * 1.5:
            print("爆量")
        elif vols[-1] > avg_vol * 0.8:
            print("正常偏高")
        elif vols[-1] < avg_vol * 0.5:
            print("缩量")
        else:
            print("正常")

    # 价格分布分析
    print("\n" + "=" * 70)
    print("  价格分布分析")
    print("-" * 70)
    
    if kline:
        # 统计高价、低价、中价出现次数
        price_buckets = {
            "42+": 0, "41-42": 0, "40-41": 0, "39-40": 0, "<39": 0
        }
        
        for d in kline:
            high = float(d[3])
            low = float(d[4])
            close = float(d[2])
            
            if close >= 42:
                price_buckets["42+"] += 1
            elif close >= 41:
                price_buckets["41-42"] += 1
            elif close >= 40:
                price_buckets["40-41"] += 1
            elif close >= 39:
                price_buckets["39-40"] += 1
            else:
                price_buckets["<39"] += 1
        
        print("  价格区间分布:")
        for bucket, count in price_buckets.items():
            bar = "█" * count
            pct = count / len(kline) * 100
            print(f"    {bucket:>8}: {bar} {pct:.0f}%")
        
        # 成本集中区
        print("\n  成本集中区:")
        if kline:
            recent_highs = [float(d[3]) for d in kline[-5:]]
            recent_lows = [float(d[4]) for d in kline[-5:]]
            print(f"    近5日震荡区间: {min(recent_lows):.2f} - {max(recent_highs):.2f}")
            print(f"    当前价格位置: {float(kline[-1][2]):.2f}")
            
            # POC (Point of Control)
            all_prices = []
            for d in kline:
                high = float(d[3])
                low = float(d[4])
                all_prices.extend([high, low])
            
            if all_prices:
                avg_price = sum(all_prices) / len(all_prices)
                print(f"    均价带: {avg_price:.2f}")

# 蓝色光标
print("\n" + "=" * 70)
print("  量价剖面分析 — 蓝色光标(300058)")
print("=" * 70)

kline_58 = get_volume_profile(300058, 10)
if kline_58:
    print("\n近10日量价汇总:")
    print("-" * 70)
    print(f"{'日期':^12} {'开盘':^8} {'收盘':^8} {'最高':^8} {'最低':^8} {'成交量(万)':^12}")
    print("-" * 70)
    
    for d in kline_58[-10:]:
        date = d[0]
        open_p = float(d[1])
        close = float(d[2])
        high = float(d[3])
        low = float(d[4])
        try:
            vol = int(float(d[5])) / 10000
        except:
            vol = 0
        
        change = (close - open_p) / open_p * 100 if open_p > 0 else 0
        icon = "▲" if change >= 0 else "▼"
        print(f"{date:^12} {open_p:^8.2f} {close:^8.2f} {high:^8.2f} {low:^8.2f} {vol:^12.0f}")

print("\n" + "=" * 70)
