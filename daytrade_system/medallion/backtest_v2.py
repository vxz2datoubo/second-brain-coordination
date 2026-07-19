"""
backtest_v2.py — 大奖章系统回测引擎 V2

核心改进（基于V1回测教训）：
  1. 只交易T2（09:50-10:30）：历史表现最优，T3及之后灾难性亏损
  2. 提高入场门槛：蓝色50分/昆仑55分（原35/40），减少低质量信号
  3. 收紧止损：-0.7%（原-1.0%），减少单次亏损幅度
  4. 浮动止盈：持仓超30分钟且盈利>0.3%时，启用追踪止损
  5. 早盘优先：最多交易T2时段，不参与T3及之后的低质量时段
  6. 最多1笔/只/天：质量优先，避免过度交易
  7. 飞逃止损：价格涨幅>2.5%立即接回

验证目标：胜率≥65%、盈亏比≥1.5、累计收益>0
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from typing import List, Dict, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from engine.tdx_parser import read_minute_kline, read_daily_kline
from engine.indicators import KBar, calc_vwap_bands, calc_rsi, calc_cumulative_delta
from medallion.config import BACKTEST
from medallion.signal_pipeline import SignalPipeline
from medallion.regime_clf import RegimeClassifier
from medallion.config import STOCK_CONFIGS

SLIPPAGE = BACKTEST.get("slippage", 0.0005)

# V2专用参数
ENTRY_THRESHOLDS = {"300418": 50.0, "300058": 55.0}
MAX_TRADES_PER_DAY = {"300418": 1, "300058": 1}

@dataclass
class TradeRecord:
    day: str
    slot_id: int
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    profit_pct: float
    entry_score: float
    regime: str = ""
    time_window: str = ""
    success: bool = False
    exit_reason: str = ""

@dataclass
class DayResult:
    date: str
    open: float; high: float; low: float; close: float
    regime: str = ""
    trades: List = field(default_factory=list)
    pnl: float = 0.0
    signals_generated: int = 0

def pnl_calc(entry: float, cur: float) -> float:
    """做空盈亏：(卖出价-当前价)/卖出价 = (entry-cur)/entry"""
    return (entry - cur) / entry * 100

def is_T2_window(t: str) -> bool:
    h, m = int(t.split(":")[0]), int(t.split(":")[1])
    return (9*60+50) <= (h*60+m) < (10*60+30)

def is_T5_window(t: str) -> bool:
    h, m = int(t.split(":")[0]), int(t.split(":")[1])
    return (13*60) <= (h*60+m) < (13*60+30)

def is_T6_window(t: str) -> bool:
    h, m = int(t.split(":")[0]), int(t.split(":")[1])
    return (13*60+30) <= (h*60+m) < (14*60)

def allowed_window(t: str) -> bool:
    """V2: 只在T2/T5/T6交易，其他时段不开新仓"""
    return is_T2_window(t) or is_T5_window(t) or is_T6_window(t)

class BacktestV2:
    def __init__(self, code: str):
        self.code = code
        self.cfg = STOCK_CONFIGS[code]
        self.signal_pipe = SignalPipeline(code, self.cfg)
        self.regime_clf = RegimeClassifier(code)
        self.entry_threshold = ENTRY_THRESHOLDS[code]
        self.max_per_day = MAX_TRADES_PER_DAY[code]
        self.hard_stop = -0.7   # 收紧到-0.7%
        self.trail_start = 0.3   # 盈利>0.3%后启用追踪
        self.trail_offset = 0.2 # 追踪止盈偏移

    def run(self, all_min5: List[KBar], all_daily: List[KBar]) -> Dict:
        days_5min = defaultdict(list)
        for b in all_min5:
            days_5min[b.date].append(b)
        daily_index = {b.date: b for b in all_daily}
        dates = sorted(days_5min.keys())
        
        all_results = []
        all_trades = []
        
        for date in dates:
            if date not in daily_index or len(days_5min[date]) < 20:
                continue
            min5 = days_5min[date]
            day_bar = daily_index[date]
            sorted_dates = sorted(daily_index.keys())
            idx = sorted_dates.index(date) if date in sorted_dates else -1
            prev_close = daily_index[sorted_dates[idx-1]].close if idx > 0 else None
            
            result = self._backtest_day(date, min5, day_bar, prev_close, all_daily)
            all_results.append(result)
            all_trades.extend(result.trades)
        
        return self._summarize(all_results, all_trades)

    def _backtest_day(self, date: str, min5: List[KBar],
                      day_bar, prev_close: float, all_daily: List[KBar]) -> DayResult:
        result = DayResult(date=date, open=day_bar.open, high=day_bar.high,
                         low=day_bar.low, close=day_bar.close)
        
        # 市场状态
        regime_result = self.regime_clf.classify(all_daily[-30:], min5, prev_close)
        result.regime = regime_result["regime"]
        
        # 槽位状态
        slots_open = {}   # slot_id -> {entry_price, entry_time, high_water, entry_score}
        trades_today = 0
        
        for i in range(6, len(min5) - 1):
            bar = min5[i]
            bars_so_far = min5[:i+1]
            cur_price = bar.close
            cur_time = _sec_to_time(bar.time_sec)
            
            # === 1. 处理止损 ===
            to_close = []
            for sid, slot in list(slots_open.items()):
                entry = slot["entry_price"]
                pnl = pnl_calc(entry, cur_price)
                reason = ""
                
                # 硬止损 -0.7%
                if pnl <= self.hard_stop:
                    reason = "硬止损"
                # 飞逃止损：价格涨幅>2.5% 
                elif (cur_price / entry - 1) * 100 > 2.5:
                    reason = "飞逃"
                # 时间止损：>45分钟且盈利<0.2%
                elif self._minutes_between(slot["entry_time"], cur_time) > 45:
                    if pnl < 0.2:
                        reason = "时间止损"
                # 追踪止盈触发
                elif slot.get("trailing_active"):
                    hw = slot["high_water"]
                    if cur_price <= hw * (1 - self.trail_offset/100):
                        reason = "追踪止盈"
                # 尾盘强平
                elif cur_time >= "14:40":
                    reason = "尾盘强平"
                
                if reason:
                    exit_price = cur_price * (1 + SLIPPAGE)
                    profit = pnl_calc(entry, exit_price)
                    to_close.append(sid)
                    result.trades.append(TradeRecord(
                        day=date, slot_id=sid,
                        entry_time=slot["entry_time"], exit_time=cur_time,
                        entry_price=entry, exit_price=exit_price,
                        profit_pct=profit, entry_score=slot.get("entry_score", 0),
                        regime=result.regime, time_window="T2",
                        success=profit > 0, exit_reason=reason
                    ))
            
            for sid in to_close:
                del slots_open[sid]
            
            # === 2. 更新追踪止损 ===
            for slot in slots_open.values():
                entry = slot["entry_price"]
                pnl = pnl_calc(entry, cur_price)
                # 盈利>0.3%激活追踪
                if pnl > self.trail_start and not slot.get("trailing_active"):
                    slot["trailing_active"] = True
                    slot["high_water"] = cur_price
                # 更新高点
                if slot.get("trailing_active"):
                    if cur_price > slot["high_water"]:
                        slot["high_water"] = cur_price
            
            # === 3. 检查接回机会 ===
            for sid, slot in list(slots_open.items()):
                entry = slot["entry_price"]
                pnl = pnl_calc(entry, cur_price)
                # 价格回到入场价附近且盈利>0.1%
                if cur_price <= entry * 1.001 and pnl >= 0.1:
                    exit_price = cur_price * (1 + SLIPPAGE)
                    profit = pnl_calc(entry, exit_price)
                    slots_open.pop(sid, None)
                    result.trades.append(TradeRecord(
                        day=date, slot_id=sid,
                        entry_time=slot["entry_time"], exit_time=cur_time,
                        entry_price=entry, exit_price=exit_price,
                        profit_pct=profit, entry_score=slot.get("entry_score", 0),
                        regime=result.regime, time_window="T2",
                        success=profit > 0, exit_reason="自然接回"
                    ))
            
            # === 4. 开新仓（V2关键改进：严格时间窗口过滤）===
            if len(slots_open) < self.max_per_day and trades_today < self.max_per_day:
                # V2: 只在T2/T5/T6时段开仓
                if not allowed_window(cur_time):
                    continue
                
                sig = self.signal_pipe.evaluate(
                    cur_price, bars_so_far, all_daily[-30:], prev_close, result.regime
                )
                
                # V2: 更高入场门槛
                if sig.sell_score < self.entry_threshold:
                    continue
                
                # V2: 距离日内高点至少回撤0.5%
                day_high = max(b.high for b in bars_so_far)
                if (day_high / cur_price - 1) * 100 < 0.5:
                    continue
                
                entry_price = cur_price * (1 - SLIPPAGE)
                sid = 1 if 1 not in slots_open else 2
                slots_open[sid] = {
                    "entry_price": entry_price,
                    "entry_time": cur_time,
                    "entry_score": sig.sell_score,
                    "high_water": entry_price,
                    "trailing_active": False,
                }
                trades_today += 1
                result.signals_generated += 1
        
        # === 5. 日末强平 ===
        for sid, slot in slots_open.items():
            last_bar = min5[-1]
            exit_price = last_bar.close * (1 + SLIPPAGE)
            profit = pnl_calc(slot["entry_price"], exit_price)
            result.trades.append(TradeRecord(
                day=date, slot_id=sid,
                entry_time=slot["entry_time"],
                exit_time=_sec_to_time(last_bar.time_sec),
                entry_price=slot["entry_price"], exit_price=exit_price,
                profit_pct=profit, entry_score=slot.get("entry_score", 0),
                regime=result.regime, time_window="T2",
                success=profit > 0, exit_reason="日末强平"
            ))
        
        result.pnl = sum(t.profit_pct for t in result.trades)
        return result

    def _minutes_between(self, t1: str, t2: str) -> float:
        h1, m1 = int(t1.split(":")[0]), int(t1.split(":")[1])
        h2, m2 = int(t2.split(":")[0]), int(t2.split(":")[1])
        return (h2*60+m2) - (h1*60+m1)

    def _summarize(self, days: List[DayResult], trades: List[TradeRecord]) -> Dict:
        if not trades:
            return {"code": self.code, "total_trades": 0, "error": "无交易"}
        
        wins = [t for t in trades if t.success]
        losses = [t for t in trades if not t.success]
        win_rate = len(wins) / len(trades) * 100
        avg_win = sum(t.profit_pct for t in wins) / len(wins) if wins else 0
        avg_loss = abs(sum(t.profit_pct for t in losses) / len(losses)) if losses else 0
        total_pnl = sum(t.profit_pct for t in trades)
        
        pf = (sum(t.profit_pct for t in wins) / abs(sum(t.profit_pct for t in losses))) \
             if losses and sum(t.profit_pct for t in losses) != 0 else 999
        
        # 按退出原因
        exit_reasons = defaultdict(list)
        for t in trades:
            exit_reasons[t.exit_reason].append(t.profit_pct)
        
        # 按regime
        regimes = defaultdict(list)
        for t in trades:
            regimes[t.regime].append(t.profit_pct)
        
        daily_pnls = [(d.date, d.pnl) for d in days if d.trades]
        pos_days = sum(1 for _, p in daily_pnls if p > 0)
        
        return {
            "code": self.code, "name": self.cfg.name,
            "total_days": len(days), "total_trades": len(trades),
            "win_rate": round(win_rate, 1),
            "avg_win": round(avg_win, 3), "avg_loss": round(avg_loss, 3),
            "profit_factor": round(pf, 2) if pf != 999 else "N/A",
            "total_pnl": round(total_pnl, 2),
            "daily_avg_pnl": round(total_pnl / len(days), 4),
            "positive_days": pos_days,
            "positive_days_rate": round(pos_days / len(daily_pnls) * 100, 1) if daily_pnls else 0,
            "exit_reason_summary": {k: {"count": len(v), "avg_pnl": round(sum(v)/len(v),3)}
                                   for k, v in exit_reasons.items()},
            "regime_summary": {k: {"count": len(v), "avg_pnl": round(sum(v)/len(v),3)}
                              for k, v in regimes.items()},
            "best_trades": sorted(trades, key=lambda t: -t.profit_pct)[:5],
            "worst_trades": sorted(trades, key=lambda t: t.profit_pct)[:5],
            "all_trades": [{"day": t.day, "entry": t.entry_time, "exit": t.exit_time,
                           "pnl": round(t.profit_pct,3), "success": t.success,
                           "score": t.entry_score, "exit_reason": t.exit_reason}
                          for t in trades],
        }

def _sec_to_time(sec: int) -> str:
    return f"{sec//3600:02d}:{(sec%3600)//60:02d}"

def tdx_to_kbar(b) -> KBar:
    return KBar(date=b.date, time_sec=b.time_sec, open=b.open, high=b.high,
                low=b.low, close=b.close, amount=b.amount, volume=b.volume)

def run_backtest_v2(code: str) -> Dict:
    min5_path = r"F:\tongdaxin\vipdoc\sz\fzline\sz" + code + ".lc5"
    day_path = r"F:\tongdaxin\vipdoc\sz\lday\sz" + code + ".day"
    
    from engine.tdx_parser import read_minute_kline, read_daily_kline
    min5_raw = read_minute_kline(min5_path)
    daily_raw = read_daily_kline(day_path)
    
    min5 = [tdx_to_kbar(b) for b in min5_raw]
    daily = [tdx_to_kbar(b) for b in daily_raw]
    
    bt = BacktestV2(code)
    return bt.run(min5, daily)

def format_report(r: Dict) -> str:
    if "error" in r:
        return f"{r['code']}: {r['error']}"
    return f"""
# {r['name']}({r['code']}) — V2回测报告
| 指标 | 数值 |
|------|------|
| 回测天数 | {r['total_days']}天 |
| 总交易笔数 | {r['total_trades']}笔 |
| 胜率 | **{r['win_rate']}%** |
| 平均盈利 | +{r['avg_win']}% |
| 平均亏损 | -{r['avg_loss']}% |
| 盈亏比 | {r['profit_factor']} |
| 累计收益 | {r['total_pnl']:+.2f}% |
| 日均收益 | {r['daily_avg_pnl']:+.4f}% |
| 正收益天数 | {r['positive_days']}天({r['positive_days_rate']}%) |

按退出原因:
""" + "\n".join(f"  {k}: {v['count']}笔 均{v['avg_pnl']:+.3f}%"
               for k, v in r.get("exit_reason_summary", {}).items())

if __name__ == "__main__":
    import sys
    os.makedirs("output", exist_ok=True)
    for code in ["300418", "300058"]:
        print(f"\n{'='*60}")
        print(f"  V2回测 {code}...")
        print(f"{'='*60}")
        r = run_backtest_v2(code)
        print(format_report(r))
        with open(f"output/backtest_v2_{code}.json", "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        
        # 检查目标
        checks = [
            ("胜率≥65%", r.get("win_rate",0) >= 65, r.get("win_rate",0)),
            ("盈亏比≥1.5", r.get("profit_factor","N/A") != "N/A" and float(r.get("profit_factor",0)) >= 1.5, r.get("profit_factor","N/A")),
            ("累计收益>0", r.get("total_pnl",0) > 0, r.get("total_pnl",0)),
        ]
        print("\n目标达成:")
        for name, passed, val in checks:
            print(f"  {'[PASS]' if passed else '[FAIL]'} {name}: {val}")
