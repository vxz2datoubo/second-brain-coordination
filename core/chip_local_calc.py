#!/usr/bin/env python3
"""
筹码分布本地计算引擎 — 不依赖任何外部API

算法: 东方财富同款 CYQ 递推公式
  Chip[d] = Chip[d-1] × (1 - turnover[d]) + Volume[d] 的价位分布
  用日K线价格区间+换手率，模拟每日筹码在104个价位上的迁移

数据依赖: 本地日K线 (已有的 Tushare daily 数据)
"""
import json, os, sys
from collections import defaultdict
from datetime import datetime

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw", "tushare")
UNIFIED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "unified", "snapshots")
NUM_BUCKETS = 52  # 半精度（速度优先, 104个bucket对2000天循环太慢）

def load_daily(stock_code: str) -> list[dict]:
    """加载日K线数据"""
    path = os.path.join(RAW_DIR, f"{stock_code}_daily.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"无日K数据: {path}")
    data = json.load(open(path))
    bars = []
    for r in data:
        if not isinstance(r, list) or len(r) < 8:
            continue
        bars.append({
            "date": str(r[1])[:8],
            "open": float(r[2]),
            "high": float(r[3]),
            "low": float(r[4]),
            "close": float(r[5]),
            "volume": float(r[6]),   # 手
            "amount": float(r[7]),   # 元
        })
    bars.sort(key=lambda b: b["date"])
    return bars

def load_float_shares(stock_code: str) -> float:
    """获取流通股本(股)"""
    # 从TK daily里取 — 实际需要从basic数据获取
    # 这里用固定值：昆仑117532万股, 蓝标347793万股
    if stock_code == "300418":
        return 1_175_323_980  # 11.75亿股（总流通）
    elif stock_code == "300058":
        return 3_477_930_310  # 34.78亿股
    return 0

def calc_chip(bars: list[dict], float_shares: float, lookback: int = 120) -> dict:
    """
    CYQ本地计算 — 东方财富同款算法
    
    核心公式 (每个交易日):
      Chip[d] = Chip[d-1] × (1 - 换手率) + 今日成交量在各价位的分布
      
    关键修正:
      1. 价格范围用滚动窗口(前lookback天), 不用全局
      2. 交易日换手率直接用成交股/流通股本
      3. 衰减等于换手率本身(即: 今天换手了X%, 旧筹码就剩1-X%)
    """
    if not bars or float_shares == 0:
        return {}
    
    chips = {}  # {price_bucket: raw_volume}
    result = {}
    
    # 预计算每个交易日的滚动价格范围
    rolling_info = []
    for day_idx, bar in enumerate(bars):
        start_idx = max(0, day_idx - 120)
        r_bars = bars[start_idx:day_idx+1]
        r_high = max(b["high"] for b in r_bars)
        r_low = min(b["low"] for b in r_bars)
        rolling_info.append((r_low, r_high))
    
    for day_idx, bar in enumerate(bars):
        date = bar["date"]
        volume = bar["volume"] * 100  # 手→股
        turnover = volume / max(float_shares, 1)
        
        r_low, r_high = rolling_info[day_idx]
        r_range = r_high - r_low
        step = r_range / (NUM_BUCKETS - 1) if NUM_BUCKETS > 1 else 0.01
        
        h, l = bar["high"], bar["low"]
        
        # 今日成交量均匀分布
        today_vol = defaultdict(float)
        for i in range(NUM_BUCKETS):
            price = r_low + i * step
            if l <= price <= h:
                today_vol[price] += volume / NUM_BUCKETS
        
        # 衰减 = 换手率 (东方财富原版)
        lam = min(turnover, 0.95)
        for p in list(chips.keys()):
            chips[p] *= (1 - lam)
        
        for p, v in today_vol.items():
            chips[p] = chips.get(p, 0) + v
        
        total = sum(chips.values())
        if total > 0 and day_idx >= 90:
            result[date] = {
                "prices": sorted(chips.keys()),
                "percents": [round(chips[p] / total * 100, 4) for p in sorted(chips.keys())],
                "avg_cost": round(sum(p * chips[p] for p in chips) / total, 2),
            }
    
    return result

def get_latest_chip(stock_code: str, date: str = None) -> dict:
    """获取指定日期的筹码分布"""
    bars = load_daily(stock_code)
    float_shares = load_float_shares(stock_code)
    if float_shares == 0:
        return {"error": f"未知流通股本: {stock_code}"}
    
    chips = calc_chip(bars, float_shares)
    
    if date:
        target = chips.get(date)
        if not target:
            # 找最近的
            dates = sorted(chips.keys())
            for d in reversed(dates):
                if d <= date:
                    target = chips[d]
                    break
        return target or {"error": f"无筹码数据: {date}"}
    
    # 返回最新
    latest_date = sorted(chips.keys())[-1]
    return {
        "date": latest_date,
        "chip": chips[latest_date],
        "meta": {
            "stock": stock_code,
            "buckets": NUM_BUCKETS,
            "data_source": "local_calc (东方财富同款算法)"
        }
    }

def calc_profit_rate(chip_data: dict, current_price: float) -> float:
    """给定筹码分布和当前价格，计算获利比例"""
    if "prices" not in chip_data:
        return 0
    total = 0
    profit = 0
    for p, v in zip(chip_data["prices"], chip_data["percents"]):
        total += v
        if p <= current_price:
            profit += v
    return round(profit / max(total, 1) * 100, 2)

def compare_to_real(calc_chip: dict, real_chip: dict, current_price: float) -> dict:
    """对比本地计算 vs Tushare真实数据的误差"""
    # 真实数据格式: {price: percent}
    calc_avg = calc_chip.get("avg_cost", 0) if isinstance(calc_chip, dict) else 0
    real_avg = sum(p*v for p,v in real_chip.items()) / sum(real_chip.values())
    
    calc_profit = calc_profit_rate(calc_chip, current_price) if isinstance(calc_chip, dict) else 0
    real_profit = sum(v for p,v in real_chip.items() if p <= current_price)
    
    return {
        "calc_avg_cost": round(calc_avg, 2),
        "real_avg_cost": round(real_avg, 2),
        "avg_cost_error": round(abs(calc_avg - real_avg), 2),
        "calc_profit_rate": round(calc_profit, 1),
        "real_profit_rate": round(real_profit, 1),
        "profit_error": round(abs(calc_profit - real_profit), 1),
    }


# ═══ CLI ═══
if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "300418"
    date_arg = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"=== 本地筹码分布计算: {code} ===")
    result = get_latest_chip(code, date_arg)
    
    if "error" in result:
        print(f"❌ {result['error']}")
        sys.exit(1)
    
    if date_arg:
        chip = result
        print(f"日期: {date_arg}")
    else:
        chip = result["chip"]
        print(f"日期: {result['date']}")
        print(f"来源: {result['meta']['data_source']}")
    
    print(f"均成本: {chip['avg_cost']:.1f}元")
    
    # Top 5
    pairs = sorted(zip(chip["prices"], chip["percents"]), key=lambda x: x[1], reverse=True)
    print("Top5价位:")
    for p, v in pairs[:5]:
        bar = "█" * int(v * 2)
        print(f"  {p:.1f}元: {v:.1f}% {bar}")
    
    # 与真实Tushare对比
    try:
        # 加载真实筹码峰
        real_chip_file = os.path.join(RAW_DIR, f"chip_{code}_cyq_chips.json")
        if os.path.exists(real_chip_file):
            real_data = json.load(open(real_chip_file))
            target_date = result["date"] if not date_arg else date_arg
            real = {}
            for r in real_data:
                if r[1][:10] == target_date:
                    real[float(r[2])] = float(r[3])
            
            if real:
                # 从daily获取收盘价
                bars = load_daily(code)
                close_price = 0
                for b in bars:
                    if b["date"] == target_date:
                        close_price = b["close"]
                        break
                
                comp = compare_to_real(chip, real, close_price)
                print(f"\n=== vs Tushare真实数据 ({target_date}) ===")
                print(f"均成本: 本地{comp['calc_avg_cost']} vs 真实{comp['real_avg_cost']} (差{comp['avg_cost_error']}元)")
                print(f"获利比: 本地{comp['calc_profit_rate']}% vs 真实{comp['real_profit_rate']}% (差{comp['profit_error']}%pct)")
    except Exception as e:
        print(f"[对比跳过: {e}]")
