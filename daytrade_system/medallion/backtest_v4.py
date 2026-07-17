"""
backtest_v4.py — 真正的大奖章日内T仓回测

策略本质：
- 每日3笔倒T，每笔5000元
- 日内完成卖出+接回（不跨日持仓）
- 不做任何止损——不到接回价就不接
- 卖出时机：信号触发时
- 接回时机：价格回落到卖出价附近时

核心问题：
- 蓝色/昆仑每天能出现几次有效的T仓机会？
- 每次T仓的平均收益是多少？
- 每天T仓收益的稳定性如何？
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
MAX_DAILY_TRADES = 3

@dataclass
class TTrade:
    date: str
    sell_time: str; sell_price: float; sell_score: float
    buy_time: str; buy_price: float
    profit_pct: float; held_min: int
    success: bool

def pnl(e, x):
    return (e - x) / e * 100

def sec_to_time(sec):
    return f"{sec//3600:02d}:{(sec%3600)//60:02d}"

def time_to_min(t):
    h, m = int(t.split(":")[0]), int(t.split(":")[1])
    return h*60+m

def tdx_bar(b):
    return KBar(date=b.date, time_sec=b.time_sec, open=b.open, high=b.high,
               low=b.low, close=b.close, amount=b.amount, volume=b.volume)

class DailyTicker:
    """单日T仓管理器"""
    def __init__(self, max_trades=3):
        self.max_trades = max_trades
        self.trades = []       # 已完成的T仓
        self.pending = None    # 当前持仓的卖出（未接回）
        self.today_sells = 0
    
    @property
    def can_sell(self):
        return self.today_sells < self.max_trades
    
    @property
    def has_pending(self):
        return self.pending is not None
    
    def sell(self, time, price, score):
        if not self.can_sell:
            return False
        self.pending = {
            "sell_time": time, "sell_price": price, "sell_score": score,
            "sell_min": time_to_min(time)
        }
        self.today_sells += 1
        return True
    
    def check_buyback(self, time, price):
        """检查是否应该接回"""
        if not self.has_pending:
            return None
        p = self.pending
        # 接回条件：价格 <= 卖出价 * 0.999（微盈利）
        if price <= p["sell_price"] * 0.999:
            held_min = time_to_min(time) - p["sell_min"]
            profit = pnl(p["sell_price"] * (1 - SLIPPAGE), price * (1 + SLIPPAGE))
            t = TTrade(
                date=p.get("date",""),
                sell_time=p["sell_time"], sell_price=p["sell_price"] * (1 - SLIPPAGE),
                sell_score=p["sell_score"],
                buy_time=time, buy_price=price * (1 + SLIPPAGE),
                profit_pct=profit, held_min=max(0, held_min),
                success=profit > 0
            )
            self.pending = None
            self.trades.append(t)
            return t
        return None
    
    def day_end(self, time, price):
        """日末处理：未接回的转为跨日仓"""
        if self.has_pending:
            p = self.pending
            held_min = time_to_min(time) - p["sell_min"]
            profit = pnl(p["sell_price"] * (1 - SLIPPAGE), price * (1 + SLIPPAGE))
            t = TTrade(
                date=p.get("date",""),
                sell_time=p["sell_time"], sell_price=p["sell_price"] * (1 - SLIPPAGE),
                sell_score=p["sell_score"],
                buy_time=time, buy_price=price * (1 + SLIPPAGE),
                profit_pct=profit, held_min=max(0, held_min),
                success=profit > 0
            )
            self.trades.append(t)
            self.pending = None
            return t
        return None
    
    def reset(self):
        self.__init__(self.max_trades)

def run_v4_day(sp, regime_clf, min5_bars, daily, prev_close, date, 
               entry_threshold, allow_window_hours=None):
    """单日T仓回测"""
    ticker = DailyTicker(MAX_DAILY_TRADES)
    ticker.date_override = date
    
    regime = "HIGH_VOL_RANGE"
    if regime_clf:
        try:
            regime = regime_clf.classify(daily[-30:], min5_bars, prev_close)["regime"]
        except:
            pass
    
    completed = []
    
    for i in range(6, len(min5_bars) - 1):
        bar = min5_bars[i]
        bars_so_far = min5_bars[:i+1]
        cur = bar.close
        cur_t = sec_to_time(bar.time_sec)
        h, m = int(cur_t.split(":")[0]), int(cur_t.split(":")[1])
        mins = h*60+m
        
        # 时间窗口过滤
        if allow_window_hours:
            if isinstance(allow_window_hours, list):
                in_window = any(s <= mins < e for s, e in allow_window_hours)
                if not in_window:
                    continue
        
        # 1. 检查接回
        if ticker.has_pending:
            t = ticker.check_buyback(cur_t, cur)
            if t:
                t.date = date
                completed.append(t)
        
        # 2. 检查开仓
        if ticker.can_sell:
            sig = sp.evaluate(cur, bars_so_far, daily[-30:], prev_close, regime)
            if sig.sell_score >= entry_threshold:
                # 距日内高点至少0.3%回撤
                dh = max(b.high for b in bars_so_far)
                if (dh / cur - 1) * 100 >= 0.3:
                    # 临时设置date属性
                    ticker.date_override = date
                    ticker.sell(cur_t, cur, sig.sell_score)
    
    # 日末：未接回的按收盘价接回
    if ticker.has_pending:
        last_bar = min5_bars[-1]
        t = ticker.day_end(sec_to_time(last_bar.time_sec), last_bar.close)
        if t:
            t.date = date
            completed.append(t)
    
    return completed

def run_v4_full(code, entry_threshold, allow_window_hours=None):
    """完整回测"""
    cfg = STOCK_CONFIGS[code]
    sp = SignalPipeline(code, cfg)
    try:
        from medallion.regime_clf import RegimeClassifier
        rc = RegimeClassifier(code)
    except:
        rc = None
    
    min5_path = r"F:\tongdaxin\vipdoc\sz\fzline\sz" + code + ".lc5"
    day_path = r"F:\tongdaxin\vipdoc\sz\lday\sz" + code + ".day"
    min5 = [tdx_bar(b) for b in read_minute_kline(min5_path)]
    daily = [tdx_bar(b) for b in read_daily_kline(day_path)]
    
    days_5min = defaultdict(list)
    for b in min5:
        days_5min[b.date].append(b)
    daily_index = {b.date: b for b in daily}
    dates = sorted(days_5min.keys())
    
    all_trades = []
    day_results = []
    
    for date in dates:
        if date not in daily_index or len(days_5min[date]) < 20:
            continue
        min5 = days_5min[date]
        day_bar = daily_index[date]
        sd = sorted(daily_index.keys())
        idx = sd.index(date) if date in sd else -1
        prev_close = daily_index[sd[idx-1]].close if idx > 0 else None
        
        trades = run_v4_day(sp, rc, min5, daily, prev_close, date,
                          entry_threshold, allow_window_hours)
        
        for t in trades:
            t.date = date
            all_trades.append(t)
        
        day_pnl = sum(x.profit_pct for x in trades)
        day_results.append({"date": date, "pnl": day_pnl, "trades": len(trades)})
    
    if not all_trades:
        return None
    
    wins = [t for t in all_trades if t.success]
    losses = [t for t in all_trades if not t.success]
    total_pnl = sum(t.profit_pct for t in all_trades)
    
    # 按日统计
    daily_avg = sum(d["pnl"] for d in day_results if d["trades"] > 0) / max(1, sum(1 for d in day_results if d["trades"] > 0))
    pos_days = sum(1 for d in day_results if d["pnl"] > 0)
    trading_days = sum(1 for d in day_results if d["trades"] > 0)
    
    return {
        "code": code, "name": cfg.name,
        "entry_threshold": entry_threshold,
        "window": str(allow_window_hours) if allow_window_hours else "all",
        "total_days": len(dates),
        "trading_days": trading_days,
        "total_trades": len(all_trades),
        "win_rate": round(len(wins)/len(all_trades)*100, 1),
        "avg_profit": round(sum(t.profit_pct for t in wins)/len(wins), 3) if wins else 0,
        "avg_loss": round(abs(sum(t.profit_pct for t in losses)/len(losses)), 3) if losses else 0,
        "total_pnl": round(total_pnl, 2),
        "daily_avg_pnl": round(daily_avg, 3),
        "positive_days": pos_days,
        "positive_days_rate": round(pos_days/trading_days*100, 1) if trading_days else 0,
        "best_day": max((d["pnl"] for d in day_results), default=0),
        "worst_day": min((d["pnl"] for d in day_results), default=0),
        "daily_stats": day_results,
        "trades_detail": [
            {"date": t.date, "sell": t.sell_time, "buy": t.buy_time,
             "sell_px": round(t.sell_price, 3), "buy_px": round(t.buy_price, 3),
             "pnl": round(t.profit_pct, 3), "held": t.held_min, "success": t.success}
            for t in all_trades
        ],
    }

def full_scan():
    """完整参数扫描"""
    os.makedirs("output", exist_ok=True)
    
    et_range = [25, 30, 35, 40, 45, 50]
    windows = [
        None,                              # 全天
        [(9*60+30, 10*60+30)],             # T2
        [(9*60+30, 10*60+30), (13*60, 14*60)],  # T2+T6
    ]
    window_names = ["全天", "T2_09:30-10:30", "T2+T6"]
    
    print(f"{'代码':>6} {'窗口':>12} {'门槛':>4} {'交易天数':>7} {'总笔数':>6} "
          f"{'胜率':>5} {'均盈':>6} {'均亏':>6} {'累计%':>8} {'日均%':>7} {'正天%':>6}")
    
    all_results = []
    for code in ["300418", "300058"]:
        for et in et_range:
            for wi, w in enumerate(windows):
                r = run_v4_full(code, et, w)
                if r and r["total_trades"] > 0:
                    print(f"{code:>6} {window_names[wi]:>12} {et:>4} "
                          f"{r['trading_days']:>7} {r['total_trades']:>6} "
                          f"{r['win_rate']:>5.1f} {r['avg_profit']:>6.3f} {r['avg_loss']:>6.3f} "
                          f"{r['total_pnl']:>8.2f} {r['daily_avg_pnl']:>7.3f} "
                          f"{r['positive_days_rate']:>6.1f}")
                    all_results.append(r)
    
    # 按日均收益排序
    all_results.sort(key=lambda x: -x["daily_avg_pnl"])
    
    print("\n" + "="*80)
    print("Top 10 配置（按日均收益）:")
    for i, r in enumerate(all_results[:10]):
        pf = r["avg_profit"] / r["avg_loss"] if r["avg_loss"] > 0 else 999
        print(f"  {i+1}. {r['code']} {r['window']:>12} et={r['entry_threshold']} "
              f"日均{r['daily_avg_pnl']:+.3f}% 累计{r['total_pnl']:+.1f}% "
              f"胜率{r['win_rate']}% 均盈{r['avg_profit']:.3f} 均亏{r['avg_loss']:.3f} "
              f"盈亏比{pf:.2f}")
    
    # 保存
    for r in all_results[:10]:
        with open(f"output/v4_best_{r['code']}_{r['entry_threshold']}_{r['window']}.json", "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
    
    with open("output/v4_scan.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    return all_results

if __name__ == "__main__":
    full_scan()
