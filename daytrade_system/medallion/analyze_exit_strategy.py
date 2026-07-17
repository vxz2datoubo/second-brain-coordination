"""
analyze_exit_strategy.py — 分析退出策略对盈亏比的影响
核心问题：平均盈利太小(-0.25%) vs 平均亏损太大(-1.0%)
解决方案：
1. 收紧止损到-0.3%，同时收紧止盈到+0.15%
2. 追踪止损（锁定更多利润）
3. 区分"快进快出"和"持仓等待"两种模式
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict
from dataclasses import dataclass
from engine.tdx_parser import read_minute_kline, read_daily_kline
from engine.indicators import KBar
from medallion.config import STOCK_CONFIGS
from medallion.signal_pipeline import SignalPipeline
from medallion.regime_clf import RegimeClassifier

SLIPPAGE = 0.0005

@dataclass
class SimTrade:
    entry_price: float; entry_time: str; entry_score: float
    exit_price: float; exit_time: str; exit_reason: str
    pnl_pct: float; held_min: int

def pnl_calc(entry, cur):
    return (entry - cur) / entry * 100

def sec_to_min(sec):
    return f"{sec//3600:02d}:{(sec%3600)//60:02d}"

def tdx_kbar(b):
    return KBar(date=b.date, time_sec=b.time_sec, open=b.open, high=b.high,
               low=b.low, close=b.close, amount=b.amount, volume=b.volume)

def simulate_trades(code, et, time_mode, hard_stop, take_profit, trail_trigger, trail_offset):
    """模拟交易并返回所有trade详情"""
    cfg = STOCK_CONFIGS[code]
    sp = SignalPipeline(code, cfg)
    rc = RegimeClassifier(code)
    
    min5_path = r"F:\tongdaxin\vipdoc\sz\fzline\sz" + code + ".lc5"
    day_path = r"F:\tongdaxin\vipdoc\sz\lday\sz" + code + ".day"
    min5 = [tdx_kbar(b) for b in read_minute_kline(min5_path)]
    daily = [tdx_kbar(b) for b in read_daily_kline(day_path)]
    
    days_5min = defaultdict(list)
    for b in min5:
        days_5min[b.date].append(b)
    daily_index = {b.date: b for b in daily}
    dates = sorted(days_5min.keys())
    
    all_trades = []
    
    for date in dates:
        if date not in daily_index or len(days_5min[date]) < 20:
            continue
        min5 = days_5min[date]
        day_bar = daily_index[date]
        sd = sorted(daily_index.keys())
        idx = sd.index(date) if date in sd else -1
        prev_close = daily_index[sd[idx-1]].close if idx > 0 else None
        
        regime = rc.classify(daily[-30:], min5, prev_close)["regime"]
        
        slots_open = {}
        
        for i in range(6, len(min5) - 1):
            bar = min5[i]
            bars_so_far = min5[:i+1]
            cur = bar.close
            cur_t = sec_to_min(bar.time_sec)
            
            # 时间窗口过滤
            h, m = int(cur_t.split(":")[0]), int(cur_t.split(":")[1])
            mins = h*60+m
            if time_mode == "T2":
                if not ((9*60+50) <= mins < (10*60+30)):
                    continue
            elif time_mode == "T6":
                if not ((13*60+30) <= mins < (14*60)):
                    continue
            elif time_mode == "T2_T6":
                if not (((9*60+50) <= mins < (10*60+30) or (13*60+30) <= mins < (14*60))):
                    continue
            
            # 处理持仓
            to_close = []
            for sid, slot in slots_open.items():
                entry = slot["entry_price"]
                pnl = pnl_calc(entry, cur)
                held_min = slot["held"] + 5
                slot["held"] = held_min
                reason = ""
                
                if pnl <= hard_stop:
                    reason = "硬止损"
                elif pnl >= take_profit:
                    reason = "止盈"
                elif held_min >= 50 and pnl >= 0.1:
                    reason = "时间退出"
                elif cur_t >= "14:40":
                    reason = "尾盘强平"
                
                if reason:
                    exit_p = cur * (1 + SLIPPAGE)
                    profit = pnl_calc(entry, exit_p)
                    to_close.append(sid)
                    all_trades.append(SimTrade(
                        entry_price=entry, entry_time=slot["entry_time"],
                        entry_score=slot["score"],
                        exit_price=exit_p, exit_time=cur_t,
                        exit_reason=reason, pnl_pct=profit,
                        held_min=held_min
                    ))
            
            for sid in to_close:
                slots_open.pop(sid, None)
            
            # 检查开仓
            if len(slots_open) < 1:
                sig = sp.evaluate(cur, bars_so_far, daily[-30:], prev_close, regime)
                if sig.sell_score < et:
                    continue
                dh = max(b.high for b in bars_so_far)
                if (dh / cur - 1) * 100 < 0.5:
                    continue
                
                entry_p = cur * (1 - SLIPPAGE)
                slots_open[1] = {
                    "entry_price": entry_p,
                    "entry_time": cur_t,
                    "score": sig.sell_score,
                    "held": 0,
                }
        
        # 强平剩余
        last = min5[-1]
        for sid, slot in slots_open.items():
            exit_p = last.close * (1 + SLIPPAGE)
            profit = pnl_calc(slot["entry_price"], exit_p)
            all_trades.append(SimTrade(
                entry_price=slot["entry_price"], entry_time=slot["entry_time"],
                entry_score=slot["score"],
                exit_price=exit_p, exit_time=sec_to_min(last.time_sec),
                exit_reason="日末强平", pnl_pct=profit,
                held_min=slot["held"]
            ))
    
    return all_trades

def analyze_params(code):
    """对不同参数组合进行网格搜索"""
    et_range = [50, 55, 60, 65, 70]
    time_modes = ["T2", "T6", "T2_T6"]
    hard_stops = [-0.3, -0.4, -0.5]
    take_profits = [0.15, 0.20, 0.25]
    
    results = []
    
    for et in et_range:
        for tm in time_modes:
            for hs in hard_stops:
                for tp in take_profits:
                    trades = simulate_trades(code, et, tm, hs, tp, 0, 0)
                    if not trades:
                        continue
                    
                    wins = [t for t in trades if t.pnl_pct > 0]
                    losses = [t for t in trades if t.pnl_pct <= 0]
                    wr = len(wins) / len(trades) * 100
                    avg_w = sum(t.pnl_pct for t in wins) / len(wins) if wins else 0
                    avg_l = abs(sum(t.pnl_pct for t in losses) / len(losses)) if losses else 0
                    pf = avg_w / avg_l if avg_l > 0 else 999
                    total = sum(t.pnl_pct for t in trades)
                    
                    results.append({
                        "et": et, "time_mode": tm, "hard_stop": hs, "take_profit": tp,
                        "trades": len(trades), "win_rate": round(wr, 1),
                        "avg_win": round(avg_w, 3), "avg_loss": round(avg_l, 3),
                        "pf": round(pf, 2), "total_pnl": round(total, 2),
                    })
    
    results.sort(key=lambda x: -x["total_pnl"])
    return results

def main():
    os.makedirs("output", exist_ok=True)
    
    print("=" * 70)
    print("蓝色光标(300418) 参数分析")
    print("=" * 70)
    r418 = analyze_params("300418")
    
    print("\nTop 20 配置 (按累计收益):")
    print(f"{'et':>2} {'模式':>6} {'止损':>5} {'止盈':>5} {'笔数':>4} {'胜率':>5} {'均盈':>6} {'均亏':>6} {'盈亏比':>6} {'累计':>8}")
    for i, r in enumerate(r418[:20]):
        print(f"{r['et']:>2} {r['time_mode']:>6} {r['hard_stop']:>5} {r['take_profit']:>5} "
              f"{r['trades']:>4} {r['win_rate']:>5.1f} {r['avg_win']:>6.3f} {r['avg_loss']:>6.3f} "
              f"{r['pf']:>6.2f} {r['total_pnl']:>8.2f}")
    
    print("\n" + "=" * 70)
    print("昆仑万维(300058) 参数分析")
    print("=" * 70)
    r058 = analyze_params("300058")
    
    print("\nTop 20 配置 (按累计收益):")
    print(f"{'et':>2} {'模式':>6} {'止损':>5} {'止盈':>5} {'笔数':>4} {'胜率':>5} {'均盈':>6} {'均亏':>6} {'盈亏比':>6} {'累计':>8}")
    for i, r in enumerate(r058[:20]):
        print(f"{r['et']:>2} {r['time_mode']:>6} {r['hard_stop']:>5} {r['take_profit']:>5} "
              f"{r['trades']:>4} {r['win_rate']:>5.1f} {r['avg_win']:>6.3f} {r['avg_loss']:>6.3f} "
              f"{r['pf']:>6.2f} {r['total_pnl']:>8.2f}")
    
    # 保存
    with open("output/exit_strategy_analysis.json", "w", encoding="utf-8") as f:
        json.dump({"300418": r418[:50], "300058": r058[:50]}, f, ensure_ascii=False, indent=2)
    print("\n已保存到 output/exit_strategy_analysis.json")

if __name__ == "__main__":
    main()
