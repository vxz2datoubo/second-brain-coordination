
import sys
sys.path.insert(0, r"F:\aidanao\daytrade_system")
from medallion.signal_pipeline import SignalPipeline
from medallion.engine.data_loader import DataLoader

dl = DataLoader(r"F:\tongdaxin\vipdoc\sz\lday", r"F:\tongdaxin\vipdoc\sz\fzline")
sp = SignalPipeline("300418")

daily = dl.load_daily("300418")
min5 = dl.load_min5("300418")
if daily and min5 and len(daily) > 5 and len(min5) > 5:
    prev_close = daily[-2].close
    today = daily[-1].date
    today_bars = [b for b in min5 if b.date == today]
    if len(today_bars) < 5:
        today_bars = min5[-5:]
        prev_close = min5[-6].open if len(min5) > 5 else min5[-5].open
    price = today_bars[-1].close
    sig = sp.evaluate(price, today_bars, daily, prev_close)
    print(f"价格={price} 总分={sig.total_score} 卖分={sig.sell_score} 买分={sig.buy_score}")
    print(f"置信={sig.confidence} 可卖={sig.can_short}")
    print(f"详情: {sig.details[:5]}")
else:
    print("数据不足")
