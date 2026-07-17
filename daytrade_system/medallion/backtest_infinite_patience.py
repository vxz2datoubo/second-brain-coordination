"""
backtest_infinite_patience.py — 无限耐心T仓策略回测

场景1：无限耐心
- 卖出后等价格回落再接回
- 最多3笔同时持仓，超时不强制接回
- 一直等到价格回到卖出价才接回

场景2：超跌接回循环
- 3笔全卡后，等价格超跌（从最高点跌X%）才接回
- 接回后重新开始卖出循环
- 追求"买在超跌点"的额外收益
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
MAX_SLOTS = 3
MAX_DAILY_NEW = 3

@dataclass
class TTrade:
    date: str
    sell_date: str; sell_time: str; sell_price: float; sell_score: float
    buy_date: str; buy_time: str; buy_price: float
    hold_days: int; pnl_pct: float; success: bool
    reason: str

def pnl(e, x): return (e - x) / e * 100
def sec_t(s): return f"{s//3600:02d}:{(s%3600)//60:02d}"
def tdx(b): return KBar(date=b.date, time_sec=b.time_sec, open=b.open, high=b.high,
                        low=b.low, close=b.close, amount=b.amount, volume=b.volume)

class Slot:
    """跨日T仓槽位"""
    def __init__(self, sid, sell_date, sell_time, sell_price, sell_score, max_price):
        self.slot_id = sid
        self.sell_date = sell_date
        self.sell_time = sell_time
        self.sell_price = sell_price    # 卖出价（已扣滑点）
        self.sell_score = sell_score
        self.max_price = max_price      # 持仓期间最高价
        self.hold_days = 0

class InfiniteTicker:
    """无限耐心T仓管理器"""
    def __init__(self, max_slots=3, max_daily=3):
        self.max_slots = max_slots
        self.max_daily = max_daily
        self.slots = {}   # slot_id -> Slot
        self.next_id = 1
        self.daily_new = 0
    
    @property
    def used(self): return len(self.slots)
    @property
    def available(self): return self.max_slots - self.used
    @property
    def can_sell(self): return self.available > 0 and self.daily_new < self.max_daily
    @property
    def all_stuck(self): return self.used == self.max_slots
    
    def sell(self, date, time, price, score):
        if not self.can_sell: return None
        sid = self.next_id
        self.next_id += 1
        slot = Slot(sid, date, time, price * (1 - SLIPPAGE), score, price)
        self.slots[sid] = slot
        self.daily_new += 1
        return sid
    
    def update_max(self, price):
        """更新持仓期间最高价（用于超跌判断）"""
        for slot in self.slots.values():
            if price > slot.max_price:
                slot.max_price = price
    
    def check_buyback(self, date, time, price):
        """检查哪些槽可以接回"""
        to_close = []
        for sid, slot in list(self.slots.items()):
            # 场景1: 价格回到卖出价以下
            if price <= slot.sell_price * 0.9995:
                to_close.append(sid)
        return to_close
    
    def check_crash_buyback(self, date, time, price, crash_pct=15):
        """场景2: 超跌接回——从最高点跌crash_pct%以上"""
        to_close = []
        for sid, slot in list(self.slots.items()):
            drop = (slot.max_price - price) / slot.max_price * 100
            if drop >= crash_pct:
                to_close.append(sid)
        return to_close
    
    def close_slot(self, sid, date, time, price, reason):
        slot = self.slots[sid]
        buy_p = price * (1 + SLIPPAGE)
        profit = pnl(slot.sell_price, buy_p)
        trade = TTrade(
            date=date,
            sell_date=slot.sell_date, sell_time=slot.sell_time,
            sell_price=slot.sell_price, sell_score=slot.sell_score,
            buy_date=date, buy_time=time, buy_price=buy_p,
            hold_days=slot.hold_days, pnl_pct=profit,
            success=profit > 0, reason=reason
        )
        del self.slots[sid]
        return trade
    
    def inc_days(self):
        for slot in self.slots.values():
            slot.hold_days += 1
    
    def day_reset(self):
        self.daily_new = 0
    
    def force_all(self, date, time, price, reason):
        """强制接回所有槽位"""
        trades = []
        for sid in list(self.slots.keys()):
            t = self.close_slot(sid, date, time, price, reason)
            trades.append(t)
        return trades

def run_scenario1(code, entry_threshold=50, windows=None):
    """场景1：无限耐心"""
    cfg = STOCK_CONFIGS[code]
    sp = SignalPipeline(code, cfg)
    rc = RegimeClassifier(code)
    
    min5 = [tdx(b) for b in read_minute_kline(
        r"F:\tongdaxin\vipdoc\sz\fzline\sz" + code + ".lc5")]
    daily = [tdx(b) for b in read_daily_kline(
        r"F:\tongdaxin\vipdoc\sz\lday\sz" + code + ".day")]
    
    days_5min = defaultdict(list)
    for b in min5: days_5min[b.date].append(b)
    daily_i = {b.date: b for b in daily}
    dates = sorted(days_5min.keys())
    
    all_trades = []
    day_results = []
    ticker = InfiniteTicker(MAX_SLOTS, MAX_DAILY_NEW)
    
    for di, date in enumerate(dates):
        if date not in daily_i or len(days_5min[date]) < 20:
            ticker.inc_days()
            ticker.day_reset()
            continue
        
        bars = days_5min[date]
        db = daily_i[date]
        sd = sorted(daily_i.keys())
        idx = sd.index(date) if date in sd else -1
        prev_close = daily_i[sd[idx-1]].close if idx > 0 else None
        regime = rc.classify(daily[-30:], bars, prev_close)["regime"]
        
        ticker.day_reset()
        ticker.inc_days()
        
        for i in range(6, len(bars) - 1):
            bar = bars[i]
            sofar = bars[:i+1]
            cur = bar.close
            cur_t = sec_t(bar.time_sec)
            h, m = int(cur_t.split(":")[0]), int(cur_t.split(":")[1])
            mins = h*60+m
            
            ticker.update_max(cur)
            
            # 接回
            for sid in ticker.check_buyback(date, cur_t, cur):
                t = ticker.close_slot(sid, date, cur_t, cur, "自然接回")
                all_trades.append(t)
            
            # 开仓
            if ticker.can_sell:
                if windows and not any(s <= mins < e for s, e in windows):
                    continue
                sig = sp.evaluate(cur, sofar, daily[-30:], prev_close, regime)
                if sig.sell_score >= entry_threshold:
                    dh = max(b.high for b in sofar)
                    if (dh / cur - 1) * 100 >= 0.3:
                        ticker.sell(date, cur_t, cur, sig.sell_score)
        
        day_pnl = sum(t.pnl_pct for t in all_trades if t.date == date)
        day_results.append({
            "date": date, "regime": regime, "pnl": day_pnl,
            "new_sells": ticker.max_daily - (ticker.max_slots - ticker.used) - ticker.available,
            "open_slots": ticker.used
        })
    
    # 强平所有剩余
    last_date = dates[-1]
    last_close = daily_i[last_date].close if last_date in daily_i else 0
    for t in ticker.force_all(last_date, "15:00", last_close, "最终强平"):
        all_trades.append(t)
    
    return summarize(code, cfg.name, all_trades, day_results, "场景1_无限耐心")

def run_scenario2(code, entry_threshold=50, windows=None, crash_pct=15):
    """场景2：超跌接回循环"""
    cfg = STOCK_CONFIGS[code]
    sp = SignalPipeline(code, cfg)
    rc = RegimeClassifier(code)
    
    min5 = [tdx(b) for b in read_minute_kline(
        r"F:\tongdaxin\vipdoc\sz\fzline\sz" + code + ".lc5")]
    daily = [tdx(b) for b in read_daily_kline(
        r"F:\tongdaxin\vipdoc\sz\lday\sz" + code + ".day")]
    
    days_5min = defaultdict(list)
    for b in min5: days_5min[b.date].append(b)
    daily_i = {b.date: b for b in daily}
    dates = sorted(days_5min.keys())
    
    all_trades = []
    day_results = []
    ticker = InfiniteTicker(MAX_SLOTS, MAX_DAILY_NEW)
    
    for di, date in enumerate(dates):
        if date not in daily_i or len(days_5min[date]) < 20:
            ticker.inc_days()
            ticker.day_reset()
            continue
        
        bars = days_5min[date]
        db = daily_i[date]
        sd = sorted(daily_i.keys())
        idx = sd.index(date) if date in sd else -1
        prev_close = daily_i[sd[idx-1]].close if idx > 0 else None
        regime = rc.classify(daily[-30:], bars, prev_close)["regime"]
        
        ticker.day_reset()
        ticker.inc_days()
        
        for i in range(6, len(bars) - 1):
            bar = bars[i]
            sofar = bars[:i+1]
            cur = bar.close
            cur_t = sec_t(bar.time_sec)
            h, m = int(cur_t.split(":")[0]), int(cur_t.split(":")[1])
            mins = h*60+m
            
            ticker.update_max(cur)
            
            # 接回：先检查超跌（3笔全卡时）
            if ticker.all_stuck:
                for sid in ticker.check_crash_buyback(date, cur_t, cur, crash_pct):
                    t = ticker.close_slot(sid, date, cur_t, cur, f"超跌接回-{crash_pct}%")
                    all_trades.append(t)
            
            # 自然接回
            for sid in ticker.check_buyback(date, cur_t, cur):
                t = ticker.close_slot(sid, date, cur_t, cur, "自然接回")
                all_trades.append(t)
            
            # 开仓
            if ticker.can_sell:
                if windows and not any(s <= mins < e for s, e in windows):
                    continue
                sig = sp.evaluate(cur, sofar, daily[-30:], prev_close, regime)
                if sig.sell_score >= entry_threshold:
                    dh = max(b.high for b in sofar)
                    if (dh / cur - 1) * 100 >= 0.3:
                        ticker.sell(date, cur_t, cur, sig.sell_score)
        
        day_pnl = sum(t.pnl_pct for t in all_trades if t.date == date)
        day_results.append({
            "date": date, "regime": regime, "pnl": day_pnl,
            "open_slots": ticker.used
        })
    
    last_date = dates[-1]
    last_close = daily_i[last_date].close if last_date in daily_i else 0
    for t in ticker.force_all(last_date, "15:00", last_close, "最终强平"):
        all_trades.append(t)
    
    return summarize(code, cfg.name, all_trades, day_results, f"场景2_超跌接回{crash_pct}%")

def summarize(code, name, all_trades, day_results, scenario):
    if not all_trades:
        return None
    wins = [t for t in all_trades if t.success]
    losses = [t for t in all_trades if not t.success]
    
    exit_map = defaultdict(list)
    for t in all_trades: exit_map[t.reason].append(t)
    
    total_pnl = sum(t.pnl_pct for t in all_trades)
    trading_days = sum(1 for d in day_results if any(t.date == d["date"] for t in all_trades))
    pos_days = sum(1 for d in day_results if d["pnl"] > 0)
    trading_pnls = [d["pnl"] for d in day_results if any(t.date == d["date"] for t in all_trades)]
    
    avg_win = sum(t.pnl_pct for t in wins)/len(wins) if wins else 0
    avg_loss = abs(sum(t.pnl_pct for t in losses)/len(losses)) if losses else 0
    pf = avg_win/avg_loss if avg_loss > 0 else 999
    
    # 超长持仓统计
    long_holds = [t for t in all_trades if t.hold_days > 30]
    
    monthly = defaultdict(list)
    for d in day_results:
        if d["pnl"] != 0:
            monthly[d["date"][:6]].append(d["pnl"])
    
    return {
        "code": code, "name": name, "scenario": scenario,
        "total_days": len(day_results), "trading_days": trading_days,
        "total_trades": len(all_trades),
        "win_rate": round(len(wins)/len(all_trades)*100, 1),
        "avg_win": round(avg_win, 3), "avg_loss": round(avg_loss, 3),
        "profit_factor": round(pf, 3) if pf != 999 else "N/A",
        "total_pnl": round(total_pnl, 2),
        "daily_avg_pnl": round(sum(trading_pnls)/len(trading_pnls), 3) if trading_pnls else 0,
        "positive_days": pos_days,
        "positive_days_rate": round(pos_days/trading_days*100, 1) if trading_days else 0,
        "long_hold_count": len(long_holds),
        "long_hold_avg_pnl": round(sum(t.pnl_pct for t in long_holds)/len(long_holds), 2) if long_holds else 0,
        "exit_summary": {k: {"count": len(v), "avg": round(sum(t.pnl_pct for t in v)/len(v),3), "total": round(sum(t.pnl_pct for t in v),2)}
                        for k, v in exit_map.items()},
        "monthly": {k: {"days": len(v), "avg": round(sum(v)/len(v),3), "total": round(sum(v),2),
                       "pos_rate": round(sum(1 for x in v if x>0)/len(v)*100,1)}
                   for k, v in sorted(monthly.items())},
    }

def print_result(r):
    if not r: return
    print(f"""
{'='*65}
# {r['name']}({r['code']}) — {r['scenario']}
{'='*65}
  回测天数: {r['total_days']}天 | 交易天数: {r['trading_days']}天 | 总笔数: {r['total_trades']}笔
  胜率: {r['win_rate']}% | 均盈: +{r['avg_win']}% | 均亏: -{r['avg_loss']}%
  盈亏比: {r['profit_factor']} | 累计收益: {r['total_pnl']:+.2f}%
  日均收益: {r['daily_avg_pnl']:+.3f}% | 正收益天: {r['positive_days']}天({r['positive_days_rate']}%)
  超30天持仓: {r['long_hold_count']}笔, 均收益{r['long_hold_avg_pnl']:+.2f}%

【退出原因】""")
    for k, v in r["exit_summary"].items():
        print(f"  {k}: {v['count']}笔, 均{v['avg']:+.3f}%, 合计{v['total']:+.1f}%")
    print("\n【月度】")
    for ym, m in r["monthly"].items():
        print(f"  {ym}: {m['days']}天, 均{m['avg']:+.3f}%, 正{m['pos_rate']}%")

def main():
    os.makedirs("output", exist_ok=True)
    
    configs = [
        ("300418", 50, [(9*60+30, 10*60+30), (13*60, 14*60)]),
        ("300058", 40, None),
    ]
    
    for code, et, w in configs:
        print(f"\n{'#'*65}\n# {code} 测试中...\n{'#'*65}")
        
        # 场景1
        print("\n>>> 场景1: 无限耐心（永不强制接回）")
        r1 = run_scenario1(code, et, w)
        print_result(r1)
        
        # 场景2: 不同超跌阈值
        for cp in [10, 15, 20, 25]:
            print(f"\n>>> 场景2: 超跌接回 {cp}%")
            r2 = run_scenario2(code, et, w, cp)
            print_result(r2)
        
        # 保存
        with open(f"output/patience_{code}.json", "w", encoding="utf-8") as f:
            json.dump({"s1": r1, "s2_10": run_scenario2(code, et, w, 10),
                      "s2_15": run_scenario2(code, et, w, 15),
                      "s2_20": run_scenario2(code, et, w, 20),
                      "s2_25": run_scenario2(code, et, w, 25)}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
