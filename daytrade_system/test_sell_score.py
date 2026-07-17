import sys, collections
sys.path.insert(0, 'F:/aidanao/daytrade_system')
from engine.tdx_parser import read_minute_kline, read_daily_kline
from engine.indicators import KBar
from medallion.config import STOCK_CONFIGS
from medallion.signal_pipeline import SignalPipeline

def tdx(b):
    return KBar(date=b.date, time_sec=b.time_sec, open=b.open, high=b.high, low=b.low, close=b.close, amount=b.amount, volume=b.volume)

m5 = [tdx(b) for b in read_minute_kline(r'F:\tongdaxin\vipdoc\sz\fzline\sz300418.lc5', limit=9999)]
dy = [tdx(b) for b in read_daily_kline(r'F:\tongdaxin\vipdoc\sz\lday\sz300418.day')]

di = collections.defaultdict(list)
for b in m5:
    di[b.date].append(b)

dm = {b.date: b for b in sorted(dy, key=lambda x: x.date)}
test = sorted(di.keys())[-3:]
cfg = STOCK_CONFIGS['300418']
pipe = SignalPipeline('300418', cfg)

for d in test:
    bars = di[d]
    if len(bars) < 20 or d not in dm:
        continue
    idx = list(dm.keys()).index(d)
    pc = dm[list(dm.keys())[idx-1]].close if idx > 0 else bars[0].open
    bar = bars[18]
    sig = pipe.evaluate(bar.close, bars[:19], dy[-30:], pc, 'HIGH_VOL_RANGE')
    f1 = sig.factors['F1'].score
    f2 = sig.factors['F2'].score
    print(d + ' Score=' + str(round(sig.total_score)) + ' sell=' + str(round(sig.sell_score)) + ' F1=' + str(round(f1)) + ' F2=' + str(round(f2)))