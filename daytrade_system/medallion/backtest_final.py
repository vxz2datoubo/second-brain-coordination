"""
backtest_final.py — 大奖章系统生产级回测验证

最优参数（基于V4扫描结果）：
  蓝色(300418): entry=50, 窗口[(09:30-10:30), (13:00-14:00)], 最多3笔/天
  昆仑(300058): entry=40, 全天, 最多3笔/天

目标：验证两个市场状态下都能稳定盈利
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
MAX_TRADES = 3

# 最优参数
PARAMS = {
    "300418": {"entry": 50, "windows": [(9*60+30, 10*60+30), (13*60, 14*60)]},
    "300058": {"entry": 40, "windows": None},  # 全天
}

@dataclass
class TTrade:
    date: str; slot_id: int
    sell_time: str; sell_price: float; sell_score: float; regime: str
    buy_time: str; buy_price: float
    profit_pct: float; held_min: int
    success: bool; exit_reason: str

@dataclass
class DayStats:
    date: str; regime: str
    open_slots: int; new_sells: int; completed: int; open_at_close: int
    pnl: float; signal_scores: list

def pnl(e, x): return (e - x) / e * 100
def sec_t(s): return f"{s//3600:02d}:{(s%3600)//60:02d}"
def t_min(t):
    h, m = int(t.split(":")[0]), int(t.split(":")[1])
    return h*60+m
def tdx(b):
    return KBar(date=b.date, time_sec=b.time_sec, open=b.open, high=b.high,
               low=b.low, close=b.close, amount=b.amount, volume=b.volume)

class Ticker:
    def __init__(self, max_trades=3):
        self.max_trades = max_trades
        self.pending = []   # [{sell_price, sell_time, sell_score, sell_min, regime}]
        self.today_sells = 0
    
    @property
    def can_sell(self): return self.today_sells < self.max_trades
    @property
    def pending_count(self): return len(self.pending)
    
    def sell(self, time, price, score, regime):
        if not self.can_sell: return None
        self.today_sells += 1
        slot = {
            "sell_time": time, "sell_price": price * (1 - SLIPPAGE),
            "sell_score": score, "sell_min": t_min(time), "regime": regime
        }
        self.pending.append(slot)
        return len(self.pending) - 1
    
    def check_buyback(self, time, price):
        """检查接回。条件：当前价格 <= 卖出价的99.9%"""
        result = []
        new_pending = []
        for slot in self.pending:
            if price <= slot["sell_price"] * 0.9995:  # 微盈利
                held = t_min(time) - slot["sell_min"]
                buy_p = price * (1 + SLIPPAGE)
                profit = pnl(slot["sell_price"], buy_p)
                result.append({
                    "slot": slot, "buy_time": time, "buy_price": buy_p,
                    "profit": profit, "held": held
                })
            else:
                new_pending.append(slot)
        self.pending = new_pending
        return result
    
    def day_end(self, time, price):
        """日末强平"""
        result = []
        for slot in self.pending:
            held = t_min(time) - slot["sell_min"]
            buy_p = price * (1 + SLIPPAGE)
            profit = pnl(slot["sell_price"], buy_p)
            result.append({
                "slot": slot, "buy_time": time, "buy_price": buy_p,
                "profit": profit, "held": held, "reason": "日末强平"
            })
        self.pending = []
        return result
    
    def reset(self):
        self.pending = []
        self.today_sells = 0

def in_window(mins, windows):
    if windows is None: return True
    return any(s <= mins < e for s, e in windows)

def run_final(code):
    cfg = STOCK_CONFIGS[code]
    sp = SignalPipeline(code, cfg)
    rc = RegimeClassifier(code)
    p = PARAMS[code]
    
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
    ticker = Ticker(MAX_TRADES)
    
    for date in dates:
        if date not in daily_i or len(days_5min[date]) < 20:
            continue
        
        bars = days_5min[date]
        db = daily_i[date]
        sd = sorted(daily_i.keys())
        idx = sd.index(date) if date in sd else -1
        prev_close = daily_i[sd[idx-1]].close if idx > 0 else None
        
        ticker.reset()
        regime = rc.classify(daily[-30:], bars, prev_close)["regime"]
        
        signals = []
        
        for i in range(6, len(bars) - 1):
            bar = bars[i]
            sofar = bars[:i+1]
            cur = bar.close
            cur_t = sec_t(bar.time_sec)
            mins = t_min(cur_t)
            
            # 接回
            for r in ticker.check_buyback(cur_t, cur):
                all_trades.append(TTrade(
                    date=date, slot_id=0,
                    sell_time=r["slot"]["sell_time"], sell_price=r["slot"]["sell_price"],
                    sell_score=r["slot"]["sell_score"], regime=r["slot"]["regime"],
                    buy_time=r["buy_time"], buy_price=r["buy_price"],
                    profit_pct=r["profit"], held_min=r["held"],
                    success=r["profit"] > 0,
                    exit_reason=r.get("reason", "自然接回")
                ))
            
            # 开仓
            if ticker.can_sell and in_window(mins, p["windows"]):
                sig = sp.evaluate(cur, sofar, daily[-30:], prev_close, regime)
                if sig.sell_score >= p["entry"]:
                    dh = max(b.high for b in sofar)
                    if (dh / cur - 1) * 100 >= 0.3:
                        sid = ticker.sell(cur_t, cur, sig.sell_score, regime)
                        if sid is not None:
                            signals.append(sig.sell_score)
        
        # 日末
        for r in ticker.day_end("15:00", bars[-1].close):
            all_trades.append(TTrade(
                date=date, slot_id=0,
                sell_time=r["slot"]["sell_time"], sell_price=r["slot"]["sell_price"],
                sell_score=r["slot"]["sell_score"], regime=r["slot"]["regime"],
                buy_time=r["buy_time"], buy_price=r["buy_price"],
                profit_pct=r["profit"], held_min=r["held"],
                success=r["profit"] > 0,
                exit_reason=r.get("reason", "日末强平")
            ))
        
        day_pnl = sum(t.profit_pct for t in all_trades if t.date == date)
        day_results.append(DayStats(
            date=date, regime=regime,
            open_slots=0, new_sells=ticker.today_sells,
            completed=sum(1 for t in all_trades if t.date == date),
            open_at_close=0, pnl=day_pnl,
            signal_scores=signals
        ))
    
    # ===== 统计 =====
    wins = [t for t in all_trades if t.success]
    losses = [t for t in all_trades if not t.success]
    total_pnl = sum(t.profit_pct for t in all_trades)
    
    trading_days = sum(1 for d in day_results if d.new_sells > 0)
    pos_days = sum(1 for d in day_results if d.pnl > 0)
    trading_day_pnls = [d.pnl for d in day_results if d.new_sells > 0]
    
    avg_win = sum(t.profit_pct for t in wins)/len(wins) if wins else 0
    avg_loss = abs(sum(t.profit_pct for t in losses)/len(losses)) if losses else 0
    pf = avg_win / avg_loss if avg_loss > 0 else 999
    
    # 按退出原因
    exit_map = defaultdict(list)
    for t in all_trades: exit_map[t.exit_reason].append(t.profit_pct)
    
    # 按市场状态
    regime_map = defaultdict(list)
    for t in all_trades: regime_map[t.regime].append(t.profit_pct)
    
    # 按季度/月度
    monthly = defaultdict(list)
    for d in day_results:
        if d.new_sells > 0:
            ym = d.date[:6]  # YYYYMM
            monthly[ym].append(d.pnl)
    
    return {
        "code": code, "name": cfg.name,
        "params": PARAMS[code],
        "total_days": len(dates), "trading_days": trading_days,
        "total_trades": len(all_trades),
        "win_rate": round(len(wins)/len(all_trades)*100, 1) if all_trades else 0,
        "avg_win": round(avg_win, 3), "avg_loss": round(avg_loss, 3),
        "profit_factor": round(pf, 3) if pf != 999 else "N/A",
        "total_pnl": round(total_pnl, 2),
        "daily_avg_pnl": round(sum(trading_day_pnls)/len(trading_day_pnls), 3) if trading_day_pnls else 0,
        "positive_days": pos_days,
        "positive_days_rate": round(pos_days/trading_days*100, 1) if trading_days else 0,
        "exit_summary": {k: {"count": len(v), "avg": round(sum(v)/len(v),3), "total": round(sum(v),2)}
                        for k, v in exit_map.items()},
        "regime_summary": {k: {"count": len(v), "avg": round(sum(v)/len(v),3), "total": round(sum(v),2)}
                          for k, v in regime_map.items()},
        "monthly_summary": {k: {
            "days": len(v), "avg": round(sum(v)/len(v),3),
            "total": round(sum(v),2),
            "positive_rate": round(sum(1 for x in v if x > 0)/len(v)*100, 1)
        } for k, v in sorted(monthly.items())},
        "best_trade": max(all_trades, key=lambda t: t.profit_pct).__dict__ if all_trades else None,
        "worst_trade": min(all_trades, key=lambda t: t.profit_pct).__dict__ if all_trades else None,
    }

def fmt(r):
    if not r: return "No data"
    print(f"""
{'='*60}
# {r['name']}({r['code']}) — 生产级回测验证
{'='*60}
参数: 入场门槛={r['params']['entry']}, 窗口={r['params']['windows']}

【核心指标】
  回测天数: {r['total_days']}天 | 交易天数: {r['trading_days']}天 | 总笔数: {r['total_trades']}笔
  胜率: {r['win_rate']}% | 均盈: +{r['avg_win']}% | 均亏: -{r['avg_loss']}%
  盈亏比: {r['profit_factor']} | 累计收益: {r['total_pnl']:+.2f}%
  日均收益: {r['daily_avg_pnl']:+.3f}% | 正收益天数: {r['positive_days']}天({r['positive_days_rate']}%)

【退出原因分析】
  {' | '.join(f"{k}({v['count']}笔, 均{v['avg']:+.3f}%, 合计{v['total']:+.1f}%)" for k, v in r['exit_summary'].items())}

【按市场状态】
  {' | '.join(f"{k}({v['count']}笔, 均{v['avg']:+.3f}%)" for k, v in r['regime_summary'].items())}

【月度表现】""")
    for ym, m in r['monthly_summary'].items():
        print(f"  {ym}: {m['days']}天交易, 均{m['avg']:+.3f}%, 正收益{m['positive_rate']}%")

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    
    results = {}
    for code in ["300418", "300058"]:
        print(f"\n{'='*60}\n  回测 {code}...\n{'='*60}")
        r = run_final(code)
        results[code] = r
        fmt(r)
        
        with open(f"output/final_{code}.json", "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
    
    # 综合评估
    print(f"\n{'#'*60}")
    print("# 综合评估")
    print(f"{'#'*60}")
    total_pnl = sum(r["total_pnl"] for r in results.values())
    combined_daily = sum(r["daily_avg_pnl"] for r in results.values())
    
    for code, r in results.items():
        checks = [
            ("胜率≥65%", r["win_rate"] >= 65, r["win_rate"]),
            ("盈亏比≥0.8", r["profit_factor"] != "N/A" and float(r["profit_factor"]) >= 0.8, r["profit_factor"]),
            ("累计收益>0", r["total_pnl"] > 0, r["total_pnl"]),
            ("日均正收益", r["daily_avg_pnl"] > 0, r["daily_avg_pnl"]),
            ("正收益天>60%", r["positive_days_rate"] > 60, r["positive_days_rate"]),
        ]
        print(f"\n{r['name']}({code}):")
        for name, ok, val in checks:
            print(f"  {'[PASS]' if ok else '[FAIL]'} {name}: {val}")
    
    print(f"\n综合：两只股票合计日均收益 {combined_daily:+.3f}% (每手5000元 ≈ {combined_daily * 50:.1f}元/天)")
