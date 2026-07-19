"""
param_scanner.py — 参数网格搜索
对不同参数组合进行回测，找出最优配置
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from collections import defaultdict
from typing import List, Dict
from dataclasses import dataclass, field

from engine.tdx_parser import read_minute_kline, read_daily_kline
from engine.indicators import KBar
from medallion.config import BACKTEST, STOCK_CONFIGS
from medallion.signal_pipeline import SignalPipeline
from medallion.regime_clf import RegimeClassifier

SLIPPAGE = BACKTEST.get("slippage", 0.0005)

@dataclass
class TradeRecord:
    day: str; slot_id: int; entry_time: str; exit_time: str
    entry_price: float; exit_price: float; profit_pct: float
    entry_score: float; regime: str = ""; time_window: str = ""
    success: bool = False; exit_reason: str = ""

@dataclass
class DayResult:
    date: str; regime: str = ""
    trades: List = field(default_factory=list); pnl: float = 0.0
    signals_generated: int = 0

def pnl_calc(entry: float, cur: float) -> float:
    return (entry - cur) / entry * 100

def time_to_min(t: str) -> int:
    h, m = int(t.split(":")[0]), int(t.split(":")[1])
    return h * 60 + m

def allowed_window(t: str, mode: str) -> bool:
    mins = time_to_min(t)
    if mode == "T2_only":
        return (9*60+50) <= mins < (10*60+30)
    elif mode == "T2_T5":
        return (9*60+50) <= mins < (10*60+30) or (13*60) <= mins < (13*60+30)
    elif mode == "T2_T5_T6":
        return (9*60+50) <= mins < (10*60+30) or (13*60) <= mins < (14*60)
    elif mode == "T6_only":
        return (13*60+30) <= mins < (14*60)
    elif mode == "all":
        return True
    return False

def sec_to_time(sec: int) -> str:
    return f"{sec//3600:02d}:{(sec%3600)//60:02d}"

def tdx_to_kbar(b) -> KBar:
    return KBar(date=b.date, time_sec=b.time_sec, open=b.open, high=b.high,
                low=b.low, close=b.close, amount=b.amount, volume=b.volume)

def run_backtest(params: dict, code: str, all_min5: List[KBar], all_daily: List[KBar]) -> Dict:
    cfg = STOCK_CONFIGS[code]
    sp = SignalPipeline(code, cfg)
    rc = RegimeClassifier(code)
    
    days_5min = defaultdict(list)
    for b in all_min5:
        days_5min[b.date].append(b)
    daily_index = {b.date: b for b in all_daily}
    dates = sorted(days_5min.keys())
    
    all_trades = []
    for date in dates:
        if date not in daily_index or len(days_5min[date]) < 20:
            continue
        min5 = days_5min[date]
        day_bar = daily_index[date]
        sorted_dates = sorted(daily_index.keys())
        idx = sorted_dates.index(date) if date in sorted_dates else -1
        prev_close = daily_index[sorted_dates[idx-1]].close if idx > 0 else None
        
        regime = rc.classify(all_daily[-30:], min5, prev_close)["regime"]
        
        slots_open = {}
        trades_today = 0
        
        for i in range(6, len(min5) - 1):
            bar = min5[i]
            bars_so_far = min5[:i+1]
            cur_price = bar.close
            cur_time = sec_to_time(bar.time_sec)
            
            # 1. 处理止损
            to_close = []
            for sid, slot in list(slots_open.items()):
                entry = slot["entry_price"]
                pnl = pnl_calc(entry, cur_price)
                reason = ""
                hs = params["hard_stop"]
                if pnl <= hs:
                    reason = "硬止损"
                elif (cur_price / entry - 1) * 100 > params["flee_stop"]:
                    reason = "飞逃"
                elif time_to_min(cur_time) - time_to_min(slot["entry_time"]) > params["time_stop"]:
                    if pnl < params["time_stop_profit"]:
                        reason = "时间止损"
                elif cur_time >= "14:40":
                    reason = "尾盘强平"
                
                if reason:
                    exit_price = cur_price * (1 + SLIPPAGE)
                    profit = pnl_calc(entry, exit_price)
                    to_close.append(sid)
                    all_trades.append(TradeRecord(
                        day=date, slot_id=sid,
                        entry_time=slot["entry_time"], exit_time=cur_time,
                        entry_price=entry, exit_price=exit_price,
                        profit_pct=profit, entry_score=slot.get("entry_score", 0),
                        regime=regime, time_window=cur_time,
                        success=profit > 0, exit_reason=reason
                    ))
            
            for sid in to_close:
                slots_open.pop(sid, None)
            
            # 2. 检查接回
            for sid, slot in list(slots_open.items()):
                entry = slot["entry_price"]
                pnl = pnl_calc(entry, cur_price)
                if cur_price <= entry * (1 + params["rebuy_tolerance"]/100) and pnl >= params["rebuy_min_profit"]:
                    exit_price = cur_price * (1 + SLIPPAGE)
                    profit = pnl_calc(entry, exit_price)
                    slots_open.pop(sid, None)
                    all_trades.append(TradeRecord(
                        day=date, slot_id=sid,
                        entry_time=slot["entry_time"], exit_time=cur_time,
                        entry_price=entry, exit_price=exit_price,
                        profit_pct=profit, entry_score=slot.get("entry_score", 0),
                        regime=regime, time_window=cur_time,
                        success=profit > 0, exit_reason="自然接回"
                    ))
            
            # 3. 开新仓
            max_per = params["max_trades_per_day"]
            if len(slots_open) < max_per and trades_today < max_per:
                if not allowed_window(cur_time, params["time_window"]):
                    continue
                
                sig = sp.evaluate(cur_price, bars_so_far, all_daily[-30:], prev_close, regime)
                if sig.sell_score < params["entry_threshold"]:
                    continue
                
                day_high = max(b.high for b in bars_so_far)
                if (day_high / cur_price - 1) * 100 < params["require_pullback"]:
                    continue
                
                entry_price = cur_price * (1 - SLIPPAGE)
                sid = 1 if 1 not in slots_open else 2
                slots_open[sid] = {
                    "entry_price": entry_price,
                    "entry_time": cur_time,
                    "entry_score": sig.sell_score,
                }
                trades_today += 1
        
        # 4. 日末强平
        for sid, slot in slots_open.items():
            last_bar = min5[-1]
            exit_price = last_bar.close * (1 + SLIPPAGE)
            profit = pnl_calc(slot["entry_price"], exit_price)
            all_trades.append(TradeRecord(
                day=date, slot_id=sid,
                entry_time=slot["entry_time"],
                exit_time=sec_to_time(last_bar.time_sec),
                entry_price=slot["entry_price"], exit_price=exit_price,
                profit_pct=profit, entry_score=slot.get("entry_score", 0),
                regime=regime, time_window=sec_to_time(last_bar.time_sec),
                success=profit > 0, exit_reason="日末强平"
            ))
    
    if not all_trades:
        return {"total_trades": 0}
    
    wins = [t for t in all_trades if t.success]
    losses = [t for t in all_trades if not t.success]
    win_rate = len(wins) / len(all_trades) * 100
    avg_win = sum(t.profit_pct for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t.profit_pct for t in losses) / len(losses)) if losses else 0
    total_pnl = sum(t.profit_pct for t in all_trades)
    
    pf = 0.0
    if losses and sum(t.profit_pct for t in losses) != 0:
        pf = sum(t.profit_pct for t in wins) / abs(sum(t.profit_pct for t in losses))
    
    return {
        "code": code, "params": params,
        "total_trades": len(all_trades),
        "win_rate": round(win_rate, 1),
        "avg_win": round(avg_win, 3), "avg_loss": round(avg_loss, 3),
        "profit_factor": round(pf, 3),
        "total_pnl": round(total_pnl, 2),
        "daily_avg_pnl": round(total_pnl / len(set(t.day for t in all_trades)), 4),
    }

def main():
    os.makedirs("output", exist_ok=True)
    
    # 加载数据
    min5_418 = [tdx_to_kbar(b) for b in read_minute_kline(r"F:\tongdaxin\vipdoc\sz\fzline\sz300418.lc5")]
    daily_418 = [tdx_to_kbar(b) for b in read_daily_kline(r"F:\tongdaxin\vipdoc\sz\lday\sz300418.day")]
    min5_058 = [tdx_to_kbar(b) for b in read_minute_kline(r"F:\tongdaxin\vipdoc\sz\fzline\sz300058.lc5")]
    daily_058 = [tdx_to_kbar(b) for b in read_daily_kline(r"F:\tongdaxin\vipdoc\sz\lday\sz300058.day")]
    
    # 参数网格
    entry_thresholds = [35, 40, 45, 50, 55, 60, 65, 70]
    hard_stops = [-0.5, -0.6, -0.7, -0.8, -0.9, -1.0]
    flee_stops = [2.0, 2.5, 3.0]
    time_stops = [30, 40, 50]
    max_trades = [1, 2]
    time_windows = ["T2_only", "T2_T5", "T2_T5_T6", "T6_only"]
    require_pullbacks = [0.3, 0.5, 0.8]
    
    # 为加速：先扫关键维度
    results = []
    
    print("Phase 1: 扫描入场门槛 + 时间窗口组合 (hard_stop=-0.7, flee=2.5, max=1)")
    for code, m5, dy in [("300418", min5_418, daily_418), ("300058", min5_058, daily_058)]:
        for et in entry_thresholds:
            for tw in time_windows:
                p = {
                    "entry_threshold": et, "hard_stop": -0.7,
                    "flee_stop": 2.5, "time_stop": 40, "time_stop_profit": 0.2,
                    "max_trades_per_day": 1, "time_window": tw,
                    "require_pullback": 0.5, "rebuy_tolerance": 0.1, "rebuy_min_profit": 0.1,
                }
                r = run_backtest(p, code, m5, dy)
                if r.get("total_trades", 0) > 0:
                    results.append(r)
    
    # 按总收益排序
    results.sort(key=lambda x: -x["total_pnl"])
    
    print("\nTop 15 配置 (按累计收益):")
    for i, r in enumerate(results[:15]):
        pf_str = f"{r['profit_factor']:.2f}"
        print(f"  {i+1}. {r['code']} et={r['params']['entry_threshold']:2d} tw={r['params']['time_window']:10s} "
              f"trades={r['total_trades']:4d} WR={r['win_rate']:5.1f}% PF={pf_str} pnl={r['total_pnl']:+7.2f}%")
    
    # Phase 2: 对最优配置精细调参
    print("\nPhase 2: 精细调参 (基于最优entry_threshold)")
    best_by_code = {}
    for code in ["300418", "300058"]:
        code_results = [r for r in results if r["code"] == code]
        if code_results:
            best = code_results[0]
            best_et = best["params"]["entry_threshold"]
            best_tw = best["params"]["time_window"]
            best_by_code[code] = (best_et, best_tw)
            
            print(f"  {code} 最优: et={best_et}, tw={best_tw}")
    
    # 保存完整结果
    with open("output/param_scan_results.json", "w", encoding="utf-8") as f:
        json.dump([
            {k: v for k, v in r.items() if k != "params"} | {"entry_threshold": r["params"]["entry_threshold"], "time_window": r["params"]["time_window"]}
            for r in results
        ], f, ensure_ascii=False, indent=2)
    
    print(f"\n已保存 {len(results)} 个结果到 output/param_scan_results.json")
    
    # 综合最优
    print("\n综合最优配置:")
    for code, (et, tw) in best_by_code.items():
        print(f"  {code}: entry_threshold={et}, time_window={tw}")

if __name__ == "__main__":
    main()
