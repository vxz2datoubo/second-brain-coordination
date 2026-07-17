import sys, os, collections
sys.path.insert(0, 'F:/aidanao/daytrade_system')
from engine.tdx_parser import read_minute_kline, read_daily_kline
from engine.indicators import KBar
from medallion.config import STOCK_CONFIGS
from medallion.signal_pipeline import SignalPipeline

def tdx_to_kbar(b):
    return KBar(date=b.date, time_sec=b.time_sec, open=b.open, high=b.high, low=b.low, close=b.close, amount=b.amount, volume=b.volume)

min5 = read_minute_kline(r'F:\tongdaxin\vipdoc\sz\fzline\sz300418.lc5', limit=9999)
daily = read_daily_kline(r'F:\tongdaxin\vipdoc\sz\lday\sz300418.day')

min5_bars = [tdx_to_kbar(b) for b in min5]
daily_bars = [tdx_to_kbar(b) for b in daily]

days = {}
for b in min5_bars:
    days.setdefault(b.date, []).append(b)

cfg = STOCK_CONFIGS["300418"]
pipe = SignalPipeline("300418", cfg)

test_dates = sorted(days.keys())[-10:]
all_scores = []
for d in test_dates:
    bars = days[d]
    if len(bars) < 20:
        continue
    di = sorted(daily_bars, key=lambda x: x.date)
    di_map = {b.date: b for b in di}
    if d not in di_map:
        continue
    di_idx = list(di_map.keys()).index(d)
    prev_close = di_map[list(di_map.keys())[di_idx-1]].close if di_idx > 0 else bars[0].open

    # Sample at multiple times
    for bar_idx in [10, 18, 30]:
        if bar_idx >= len(bars):
            continue
        bar = bars[bar_idx]
        bars_so_far = bars[:bar_idx+1]
        
        sig = pipe.evaluate(
            current_price=bar.close,
            min5_bars=bars_so_far,
            daily_bars=daily_bars[-30:],
            prev_close=prev_close,
            regime="HIGH_VOL_RANGE",
        )
        chg = (bar.close / prev_close - 1) * 100
        hh = max(b.high for b in bars_so_far)
        pct_from_high = (hh / bar.close - 1) * 100
        print(f"{d} {bars_so_far[-1].time_sec//3600:02d}:{bars_so_far[-1].time_sec%3600//60:02d} price={bar.close:.4f} chg={chg:+.2f}% high_pct={pct_from_high:.1f}%")
        print(f"  Score={sig.total_score:.0f} sell={sig.sell_score:.0f} Conf={sig.confidence}")
        print(f"  F1={sig.factors['F1'].score:.0f} F2={sig.factors['F2'].score:.0f} F3={sig.factors['F3'].score:.0f} F4={sig.factors['F4'].score:.0f} F5={sig.factors['F5'].score:.0f} F6={sig.factors['F6'].score:.0f}")
        print(f"  {sig.reason[:80]}")
        print()
        all_scores.append(sig.total_score)

print(f"Max score: {max(all_scores):.0f}, Min: {min(all_scores):.0f}, Avg: {sum(all_scores)/len(all_scores):.0f}")
print(f"Scores above 35: {sum(1 for s in all_scores if s >= 35)}/{len(all_scores)}")
