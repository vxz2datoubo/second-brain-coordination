"""Test signal generation"""
import sys
sys.path.insert(0, 'F:/aidanao/daytrade_system')

from medallion.live_monitor_v2 import SignalEngine, load_tdx_min5, load_tdx_daily
from datetime import datetime

STOCKS = {"300418": "蓝色光标", "300058": "昆仑万维"}

engine = SignalEngine()

for code in ["300418", "300058"]:
    daily = load_tdx_daily(code, 60)
    min5 = load_tdx_min5(code, 200)
    today = datetime.now().strftime("%Y%m%d")
    today_bars = [b for b in min5 if b["date"] == today]
    
    star = " *" if code == "300058" else ""
    print("=" * 45)
    print(f" {STOCKS[code]}({code}){star}")
    print("=" * 45)
    
    if today_bars:
        ind = engine.calc_indicators(today_bars, daily)
        sig = engine.generate_signal(code, ind)
        print(f"  Price: {sig['price']}")
        print(f"  Open: {ind.get('open_to_now', 0):+.2f}%")
        print(f"  Pullback: {ind.get('pullback', 0):.1f}%")
        print(f"  MA5: {ind.get('ma5', 0):.3f}")
        print(f"  Sell: {sig['scores']['sell']} | {sig['confidence']} | {sig['recommendation']}")
        reasons = sig.get('reason') or []
        if reasons:
            print(f"  Reason: {' | '.join(reasons[:3])}")
    else:
        print("  No data today")
    print()
