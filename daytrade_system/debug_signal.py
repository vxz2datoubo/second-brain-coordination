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
for d in test_dates:
    bars = days[d]
    if len(bars) < 20:
        continue
    sorted_daily = sorted(daily_bars, key=lambda x: x.date)
    daily_index = {b.date: b for b in sorted_daily}
    di = sorted(daily_index.keys())
    if d not in di:
        continue
    pi = di.index(d)
    prev_close = daily_index[di[pi-1]].close if pi > 0 else bars[0].open

    # Evaluate at 10:30
    bar_30 = bars[18]
    bars_so_far = bars[:19]

    sig = pipe.evaluate(
        current_price=bar_30.close,
        min5_bars=bars_so_far,
        daily_bars=daily_bars[-30:],
        prev_close=prev_close,
        regime="HIGH_VOL_RANGE",
    )
    chg = (bar_30.close / prev_close - 1) * 100
    print(f"{d} {bars_so_far[-1].time_sec//3600:02d}:{bars_so_far[-1].time_sec%3600//60:02d} price={bar_30.close:.4f} chg={chg:+.2f}%")
    print(f"  Score={sig.total_score:.0f} Conf={sig.confidence} F1={sig.factors['F1'].score:.0f} F2={sig.factors['F2'].score:.0f} F3={sig.factors['F3'].score:.0f} F4={sig.factors['F4'].score:.0f} F5={sig.factors['F5'].score:.0f} F6={sig.factors['F6'].score:.0f}")
    print(f"  Reason: {sig.reason[:80]}")
    print()
