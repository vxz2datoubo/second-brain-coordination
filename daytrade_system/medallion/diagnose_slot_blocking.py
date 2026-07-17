"""diagnose_slot_blocking.py - 诊断槽位卡住"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collections import defaultdict
from dataclasses import dataclass
from engine.tdx_parser import read_minute_kline, read_daily_kline
from engine.indicators import KBar
from medallion.config import STOCK_CONFIGS
from medallion.signal_pipeline import SignalPipeline
from medallion.regime_clf import RegimeClassifier

SLIPPAGE = 0.0005; MAX_SLOTS = 3

@dataclass
class Slot:
    sid: int; sell_date: str; sell_time: str; sell_price: float; sell_score: float
    max_price: float; hold_days: int = 0

@dataclass
class TTrade:
    date: str; sell_date: str; sell_time: str; sell_price: float; sell_score: float
    buy_date: str; buy_time: str; buy_price: float; hold_days: int
    pnl_pct: float; reason: str; success: bool

def pnl(e, x): return (e - x) / e * 100
def sec_t(s): return f"{s//3600:02d}:{(s%3600)//60:02d}"
def tdx(b): return KBar(date=b.date, time_sec=b.time_sec, open=b.open, high=b.high,
                        low=b.low, close=b.close, amount=b.amount, volume=b.volume)

class Ticker:
    def __init__(self):
        self.slots = {}; self.next_id = 1; self.daily_new = 0
    @property
    def used(self): return len(self.slots)
    @property
    def all_stuck(self): return self.used >= MAX_SLOTS
    @property
    def can_sell(self): return self.used < MAX_SLOTS and self.daily_new < MAX_SLOTS
    def sell(self, date, time, price, score):
        if not self.can_sell: return None
        sid = self.next_id; self.next_id += 1
        self.slots[sid] = Slot(sid, date, time, price*(1-SLIPPAGE), score, price)
        self.daily_new += 1; return sid
    def update_max(self, price):
        for s in self.slots.values():
            if price > s.max_price: s.max_price = price
    def natural_close(self, date, time, price):
        result = []; new = {}
        for sid, s in self.slots.items():
            if price <= s.sell_price * 0.9995:
                bp = price*(1+SLIPPAGE); p = pnl(s.sell_price, bp)
                result.append(dict(slot=s, buy_date=date, buy_time=time, buy_price=bp, profit=p, reason="自然接回"))
            else: new[sid] = s
        self.slots = new; return result
    def crash_close(self, date, time, price, crash_pct):
        result = []; new = {}
        for sid, s in self.slots.items():
            drop = (s.max_price - price) / s.max_price * 100
            if drop >= crash_pct:
                bp = price*(1+SLIPPAGE); p = pnl(s.sell_price, bp)
                result.append(dict(slot=s, buy_date=date, buy_time=time, buy_price=bp, profit=p, reason=f"超跌-{crash_pct}%"))
            else: new[sid] = s
        self.slots = new; return result
    def force_close(self, date, time, price, reason):
        result = []
        for sid, s in self.slots.items():
            bp = price*(1+SLIPPAGE); p = pnl(s.sell_price, bp)
            result.append(dict(slot=s, buy_date=date, buy_time=time, buy_price=bp, profit=p, reason=reason))
        self.slots = {}; return result
    def inc_days(self):
        for s in self.slots.values(): s.hold_days += 1
    def day_reset(self): self.daily_new = 0

def run_diagnose(code, entry_threshold=50, windows=None, crash_pct=15):
    cfg = STOCK_CONFIGS[code]; sp = SignalPipeline(code, cfg); rc = RegimeClassifier(code)
    min5 = [tdx(b) for b in read_minute_kline(r"F:\tongdaxin\vipdoc\sz\fzline\sz" + code + ".lc5")]
    daily = [tdx(b) for b in read_daily_kline(r"F:\tongdaxin\vipdoc\sz\lday\sz" + code + ".day")]
    days_5min = defaultdict(list)
    for b in min5: days_5min[b.date].append(b)
    daily_i = {b.date: b for b in daily}; dates = sorted(days_5min.keys())
    
    all_trades = []; stuck_events = []
    ticker = Ticker()
    
    for di, date in enumerate(dates):
        if date not in daily_i or len(days_5min[date]) < 20:
            ticker.inc_days(); ticker.day_reset()
            if ticker.all_stuck: stuck_events.append(date)
            continue
        bars = days_5min[date]; db = daily_i[date]
        sd = sorted(daily_i.keys()); idx = sd.index(date) if date in sd else -1
        prev_close = daily_i[sd[idx-1]].close if idx > 0 else None
        regime = rc.classify(daily[-30:], bars, prev_close)["regime"]
        ticker.day_reset(); ticker.inc_days()
        if ticker.all_stuck: stuck_events.append(date)
        
        for i in range(6, len(bars) - 1):
            bar = bars[i]; sofar = bars[:i+1]; cur = bar.close
            cur_t = sec_t(bar.time_sec); h,m = int(cur_t.split(":")[0]), int(cur_t.split(":")[1])
            mins = h*60+m; ticker.update_max(cur)
            
            if ticker.all_stuck:
                for r in ticker.crash_close(date, cur_t, cur, crash_pct):
                    s = r["slot"]
                    all_trades.append(TTrade(date, s.sell_date, s.sell_time, s.sell_price, s.sell_score,
                        r["buy_date"], r["buy_time"], r["buy_price"], s.hold_days, r["profit"], r["reason"], r["profit"]>0))
            for r in ticker.natural_close(date, cur_t, cur):
                s = r["slot"]
                all_trades.append(TTrade(date, s.sell_date, s.sell_time, s.sell_price, s.sell_score,
                    r["buy_date"], r["buy_time"], r["buy_price"], s.hold_days, r["profit"], r["reason"], r["profit"]>0))
            if ticker.can_sell:
                if windows and not any(s <= mins < e for s, e in windows): continue
                sig = sp.evaluate(cur, sofar, daily[-30:], prev_close, regime)
                if sig.sell_score >= entry_threshold:
                    dh = max(b.high for b in sofar)
                    if (dh / cur - 1) * 100 >= 0.3:
                        ticker.sell(date, cur_t, cur, sig.sell_score)
        
        for r in ticker.force_close(date, "15:00", bars[-1].close, "日末强平"):
            s = r["slot"]
            all_trades.append(TTrade(date, s.sell_date, s.sell_time, s.sell_price, s.sell_score,
                r["buy_date"], r["buy_time"], r["buy_price"], s.hold_days, r["profit"], r["reason"], r["profit"]>0))
    
    last_date = dates[-1]; last_close = daily_i[last_date].close if last_date in daily_i else 0
    for r in ticker.force_close(last_date, "15:00", last_close, "最终强平"):
        s = r["slot"]
        all_trades.append(TTrade(date=last_date, sell_date=s.sell_date, sell_time=s.sell_time,
            sell_price=s.sell_price, sell_score=s.sell_score,
            buy_date=last_date, buy_time="15:00", buy_price=last_close*(1+SLIPPAGE),
            hold_days=s.hold_days, pnl_pct=pnl(s.sell_price, last_close*(1+SLIPPAGE)),
            reason="最终强平", success=pnl(s.sell_price, last_close*(1+SLIPPAGE))>0))
    
    by_reason = defaultdict(list)
    for t in all_trades: by_reason[t.reason].append(t.pnl_pct)
    
    print(f"\n{cfg.name}({code}) crash={crash_pct}%")
    total_pnl = 0
    for reason, pnls in sorted(by_reason.items(), key=lambda x: -len(x[1])):
        avg = sum(pnls)/len(pnls); total_pnl += sum(pnls)
        print(f"  {reason}: {len(pnls)}笔, 均{avg:+.2f}%, 合计{sum(pnls):+.1f}%")
    print(f"  合计: {len(all_trades)}笔, 净{total_pnl:+.2f}%")
    print(f"  3笔全卡: {len(stuck_events)}次 (每{len(dates)/max(1,len(stuck_events)):.0f}天1次)")
    return total_pnl

def main():
    os.makedirs("output", exist_ok=True)
    for code in ["300418","300058"]:
        et = 50 if code=="300418" else 40
        w = [(570,630),(780,840)] if code=="300418" else None
        print(f"\n{'='*55}")
        best = -999; best_cp = 0
        for cp in [5, 8, 10, 12, 15, 20]:
            pnl = run_diagnose(code, et, w, cp)
            if pnl > best: best = pnl; best_cp = cp
        print(f"\n最优超跌阈值: {best_cp}%, 净收益{best:+.2f}%")

if __name__ == "__main__":
    main()
