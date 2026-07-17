"""
backtest_v3.py — 真正的大奖章倒T回测 v3

核心机制：
1. 卖出后持T仓跨日，等价格回落到卖出价以下才接回
2. 不回本就不接回（无日内止损）
3. 最多持有15个交易日，超时强制接回（风险控制）
4. 每日最多3笔可累计跨日，接回后释放槽位可再卖出
5. 昆仑（300058）配置更多资源

策略本质：均值回归 + 耐心等待
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict
from dataclasses import dataclass
from engine.tdx_parser import read_minute_kline, read_daily_kline
from engine.indicators import KBar
from medallion.config import STOCK_CONFIGS
from medallion.signal_pipeline import SignalPipeline

SLIPPAGE = 0.0005
MAX_CROSS_DAYS = 15   # 最多跨15个交易日
MAX_SLOTS = 3         # 最多3笔未回笼

@dataclass
class Trade:
    day: str; slot_id: int
    entry_date: str; entry_time: str; entry_price: float; entry_score: float
    exit_date: str; exit_time: str; exit_price: float
    hold_days: int; pnl_pct: float; success: bool; reason: str

def pnl(entry, exit):
    return (entry - exit) / entry * 100

def sec_to_time(sec):
    return f"{sec//3600:02d}:{(sec%3600)//60:02d}"

def tdx_bar(b):
    return KBar(date=b.date, time_sec=b.time_sec, open=b.open, high=b.high,
               low=b.low, close=b.close, amount=b.amount, volume=b.volume)

class SlotManager:
    """跨日T仓管理器"""
    def __init__(self, max_slots=3, max_days=15):
        self.max_slots = max_slots
        self.max_days = max_days
        self.slots = []  # [{slot_id, entry_date, entry_time, entry_price, entry_score, hold_days}]
        self.next_id = 1
    
    @property
    def used(self):
        return len(self.slots)
    
    @property
    def available(self):
        return self.max_slots - self.used
    
    def can_sell(self):
        return self.used < self.max_slots
    
    def sell(self, date, time, price, score):
        if not self.can_sell():
            return None
        sid = self.next_id
        self.next_id += 1
        self.slots.append({
            "slot_id": sid,
            "entry_date": date,
            "entry_time": time,
            "entry_price": price,
            "entry_score": score,
            "hold_days": 0,
            "tags": set(),
        })
        return sid
    
    def check_buyback(self, date, price, day_bars):
        """检查哪些槽位可以接回"""
        to_close = []
        for s in self.slots:
            entry = s["entry_price"]
            # 条件：当前价格 <= 卖出价 * 0.999（微盈利即接回）
            if price <= entry * 0.999:
                to_close.append(s)
        return to_close
    
    def inc_days(self):
        """所有持仓增加一天"""
        for s in self.slots:
            s["hold_days"] += 1
    
    def get_expired(self):
        """获取超时强制接回的"""
        return [s for s in self.slots if s["hold_days"] >= self.max_days]
    
    def buyback(self, slot, date, time, price):
        """接回一个槽位"""
        profit = pnl(slot["entry_price"], price)
        trade = Trade(
            day=date, slot_id=slot["slot_id"],
            entry_date=slot["entry_date"], entry_time=slot["entry_time"],
            entry_price=slot["entry_price"], entry_score=slot["entry_score"],
            exit_date=date, exit_time=time, exit_price=price,
            hold_days=slot["hold_days"], pnl_pct=profit,
            success=profit > 0, reason="自然接回"
        )
        self.slots = [s for s in self.slots if s["slot_id"] != slot["slot_id"]]
        return trade
    
    def force_close(self, slot, date, time, price):
        """强制接回"""
        profit = pnl(slot["entry_price"], price)
        trade = Trade(
            day=date, slot_id=slot["slot_id"],
            entry_date=slot["entry_date"], entry_time=slot["entry_time"],
            entry_price=slot["entry_price"], entry_score=slot["entry_score"],
            exit_date=date, exit_time=time, exit_price=price,
            hold_days=slot["hold_days"], pnl_pct=profit,
            success=profit > 0, reason="超时强平"
        )
        self.slots = [s for s in self.slots if s["slot_id"] != slot["slot_id"]]
        return trade

def run_v3(code, entry_threshold=50, max_daily_trades=3, only_T2=False):
    """V3完整回测"""
    cfg = STOCK_CONFIGS[code]
    sp = SignalPipeline(code, cfg)
    
    min5_path = r"F:\tongdaxin\vipdoc\sz\fzline\sz" + code + ".lc5"
    day_path = r"F:\tongdaxin\vipdoc\sz\lday\sz" + code + ".day"
    min5 = [tdx_bar(b) for b in read_minute_kline(min5_path)]
    daily = [tdx_bar(b) for b in read_daily_kline(day_path)]
    
    # 按日分组
    days_5min = defaultdict(list)
    for b in min5:
        days_5min[b.date].append(b)
    daily_index = {b.date: b for b in daily}
    dates = sorted(days_5min.keys())
    
    all_trades = []
    day_results = []
    slots = SlotManager(MAX_SLOTS, MAX_CROSS_DAYS)
    
    for di, date in enumerate(dates):
        if date not in daily_index or len(days_5min[date]) < 10:
            # 无数据日，计入持仓天数
            slots.inc_days()
            # 检查超时
            for s in slots.get_expired():
                t = slots.force_close(s, date, "15:00",
                    daily_index.get(date, daily_index.get(dates[di-1])).close * (1 + SLIPPAGE) if di > 0 else s["entry_price"])
                all_trades.append(t)
            continue
        
        min5_bars = days_5min[date]
        day_bar = daily_index[date]
        sd = sorted(daily_index.keys())
        idx = sd.index(date) if date in sd else -1
        prev_close = daily_index[sd[idx-1]].close if idx > 0 else None
        
        # 日初处理：检查持仓过期
        slots.inc_days()
        for s in slots.get_expired():
            t = slots.force_close(s, date, "09:30", prev_close)
            all_trades.append(t)
        
        daily_sell_count = 0
        daily_buy_count = 0
        
        # 日内逐K线
        for i in range(6, len(min5_bars) - 1):
            bar = min5_bars[i]
            bars_so_far = min5_bars[:i+1]
            cur = bar.close
            cur_t = sec_to_time(bar.time_sec)
            h, m = int(cur_t.split(":")[0]), int(cur_t.split(":")[1])
            mins = h*60+m
            
            # 时间窗口
            if only_T2:
                if not ((9*60+50) <= mins < (10*60+30)):
                    continue
            
            # 1. 检查接回机会：价格回落到卖出价以下
            to_close = slots.check_buyback(date, cur, min5_bars)
            for s in to_close:
                exit_p = cur * (1 + SLIPPAGE)
                trade = slots.buyback(s, date, cur_t, exit_p)
                all_trades.append(trade)
                daily_buy_count += 1
            
            # 2. 检查开仓
            if slots.can_sell() and daily_sell_count < max_daily_trades:
                sig = sp.evaluate(cur, bars_so_far, daily[-30:], prev_close, "HIGH_VOL_RANGE")
                if sig.sell_score < entry_threshold:
                    continue
                
                # 距日内高点至少0.3%回撤
                dh = max(b.high for b in bars_so_far)
                if (dh / cur - 1) * 100 < 0.3:
                    continue
                
                entry_p = cur * (1 - SLIPPAGE)
                sid = slots.sell(date, cur_t, entry_p, sig.sell_score)
                if sid:
                    daily_sell_count += 1
        
        # 日末统计
        day_pnl = sum(t.pnl_pct for t in all_trades if t.day == date)
        day_results.append({"date": date, "pnl": day_pnl, "trades": daily_sell_count, "open_slots": slots.used})
    
    # 处理最后剩余仓位（以最后一天的收盘价强平）
    last_date = dates[-1] if dates else ""
    last_close = daily_index[last_date].close * (1 + SLIPPAGE) if last_date in daily_index else 0
    for s in list(slots.slots):
        t = slots.force_close(s, last_date, "15:00", last_close)
        all_trades.append(t)
    
    # 统计
    wins = [t for t in all_trades if t.success]
    losses = [t for t in all_trades if not t.success]
    wr = len(wins)/len(all_trades)*100 if all_trades else 0
    avg_w = sum(t.pnl_pct for t in wins)/len(wins) if wins else 0
    avg_l = abs(sum(t.pnl_pct for t in losses)/len(losses)) if losses else 0
    avg_w_abs = sum(t.pnl_pct for t in wins)/len(wins) if wins else 0
    pf = (sum(t.pnl_pct for t in wins) / abs(sum(t.pnl_pct for t in losses))) if losses and sum(t.pnl_pct for t in losses) != 0 else 999
    
    pos_days = sum(1 for d in day_results if d["pnl"] > 0)
    
    return {
        "code": code, "name": cfg.name,
        "params": {"entry_threshold": entry_threshold, "max_trades": max_daily_trades, "window": "T2_only" if only_T2 else "all"},
        "total_days": len(dates),
        "total_trades": len(all_trades),
        "win_rate": round(wr, 1),
        "avg_win": round(avg_w, 3),
        "avg_loss": round(avg_l, 3),
        "profit_factor": round(pf, 2) if pf != 999 else "N/A",
        "total_pnl": round(sum(t.pnl_pct for t in all_trades), 2),
        "stop_loss_pnl": round(sum(t.pnl_pct for t in all_trades if not t.success), 2),
        "natural_pnl": round(sum(t.pnl_pct for t in all_trades if t.success), 2),
        "avg_hold_days": round(sum(abs(t.hold_days) for t in all_trades)/len(all_trades), 1),
        "reason_count": dict(
            (k, sum(1 for t in all_trades if t.reason == k)) for k in set(t.reason for t in all_trades)
        ),
        "trades": [{"day": t.day, "entry_date": t.entry_date, "exit_date": t.exit_date,
                    "hold_days": t.hold_days, "pnl": round(t.pnl_pct, 3), "score": t.entry_score,
                    "success": t.success, "reason": t.reason} for t in all_trades],
    }

def scan_params():
    """参数扫描"""
    os.makedirs("output", exist_ok=True)
    codes = ["300418", "300058"]
    et_range = [35, 40, 45, 50, 55, 60, 65, 70]
    max_trades = [1, 2, 3]
    
    print(f"{'代码':>6} {'门槛':>4} {'笔/天':>5} {'窗口':>6} {'笔数':>5} {'胜率':>6} {'均盈':>6} {'均亏':>6} {'盈亏比':>6} {'累计%':>8} {'均持':>5}")
    
    best = {}
    for code in codes:
        best[code] = []
        for et in et_range:
            for mt in max_trades:
                for ot in [True, False]:
                    r = run_v3(code, et, mt, ot)
                    win_label = "T2" if ot else "全日"
                    print(f"{code:>6} {et:>4} {mt:>5} {win_label:>6} "
                          f"{r['total_trades']:>5} {r['win_rate']:>6.1f} "
                          f"{r['avg_win']:>6.3f} {r['avg_loss']:>6.3f} "
                          f"{r['profit_factor']:>6} {r['total_pnl']:>8.2f} "
                          f"{r['avg_hold_days']:>5.1f}")
                    best[code].append(r)
    
        # 按总收益排序
        best[code].sort(key=lambda x: -x["total_pnl"])
    
    return best

if __name__ == "__main__":
    best = scan_params()
    print("\n" + "="*65)
    print("综合最优配置:")
    for code, results in best.items():
        if results:
            r = results[0]
            print(f"\n{r['name']}({code}):")
            p = r['params']
            print(f"  入场门槛: {p['entry_threshold']}, 最多{p['max_trades']}笔/天, {p['window']}")
            print(f"  总交易: {r['total_trades']}笔, 胜率{r['win_rate']}%, 盈亏比{r['profit_factor']}")
            print(f"  累计收益: {r['total_pnl']:+.2f}%, 平均持仓{r['avg_hold_days']}天")
            print(f"  自然接回盈利: {r['natural_pnl']:+.2f}%, 止损亏损: {r['stop_loss_pnl']:+.2f}%")
            print(f"  退出原因: {r['reason_count']}")
    
    with open("output/backtest_v3_best.json", "w", encoding="utf-8") as f:
        json.dump({c: best[c][0] if best[c] else None for c in best}, f, ensure_ascii=False, indent=2)
