
import sys, os, json, collections
sys.path.insert(0, "F:/aidanao/daytrade_system")
from engine.tdx_parser import read_minute_kline
from engine.indicators import KBar
from medallion.backtest_medallion import BacktestMedallion
from medallion.config import STOCK_CONFIGS

def load_daily_from_json():
    path = r"F:\aidanao\data\kl_300418_1y.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    bars = []
    for item in data:
        bars.append(KBar(
            date=item["date"], time_sec=0,
            open=float(item["open"]), high=float(item["high"]),
            low=float(item["low"]), close=float(item["close"]),
            amount=float(item["amount"]), volume=float(item["volume"]),
        ))
    return bars

def load_min5_from_tdx(code):
    path = rf"F:\tongdaxin\vipdoc\sz\fzline\sz{code}.lc5"
    raw = read_minute_kline(path)
    return [KBar(
        date=b.date, time_sec=b.time_sec,
        open=b.open, high=b.high, low=b.low, close=b.close,
        amount=b.amount, volume=b.volume,
    ) for b in raw]

print("=" * 60)
print("大奖章系统回测 (修复版) - 2026-07-04")
print("=" * 60)

daily_bars_418 = load_daily_from_json()
print("日K(从JSON): " + str(len(daily_bars_418)) + "条 (" + daily_bars_418[0].date + "~" + daily_bars_418[-1].date + ")")

results = {}
for code in ["300418", "300058"]:
    cfg = STOCK_CONFIGS[code]
    print("")
    print(">>> " + cfg.name + "(" + code + ") 回测...")

    min5_bars = load_min5_from_tdx(code)
    print("    5分K: " + str(len(min5_bars)) + "条 (" + min5_bars[0].date + "~" + min5_bars[-1].date + ")")

    min5_dates = sorted(set(b.date for b in min5_bars))
    daily_map = {b.date: b for b in daily_bars_418}

    my_daily = [daily_map[d] for d in min5_dates if d in daily_map]
    print("    匹配日K: " + str(len(my_daily)) + "条")

    if len(min5_bars) < 100:
        print("    [WARN] 数据不足，跳过")
        continue

    first_idx = min5_dates.index(min5_dates[0])
    prev_close = daily_bars_418[min5_dates.index(min5_dates[0]) - 1].close if first_idx > 0 else None
    print("    首日前收盘: " + str(prev_close))

    bt = BacktestMedallion(code)
    result = bt.run(min5_bars, my_daily)
    results[code] = result

    print("    回测天数: " + str(result["total_days"]))
    print("    总交易: " + str(result["total_trades"]) + "笔")
    print("    胜率: " + str(result["win_rate"]) + "%")
    print("    均盈利: " + str(result["avg_win"]))
    print("    均亏损: " + str(result["avg_loss"]))
    print("    盈亏比: " + str(result["profit_factor"]))
    print("    累计收益: " + str(result["total_pnl"]))
    print("    日均: " + str(result["daily_avg_pnl"]))

    out = "F:/aidanao/daytrade_system/output/backtest_fixed_" + code + ".json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("    -> 已保存: " + out)

if len(results) == 2:
    print("")
    print("=" * 60)
    print("目标达成检查")
    print("=" * 60)
    for code, r in results.items():
        name = STOCK_CONFIGS[code].name
        checks = [
            ("胜率>=50%", r["win_rate"] >= 50, str(r["win_rate"]) + "%"),
            ("盈亏比>=1.0", r["profit_factor"] != "N/A" and float(r["profit_factor"]) >= 1.0, str(r["profit_factor"])),
            ("累计收益>0", r["total_pnl"] > 0, str(r["total_pnl"])),
        ]
        print("")
        print(name + "(" + code + "):")
        for check in checks:
            label = check[0]
            passed = check[1]
            val = check[2]
            icon = "[PASS]" if passed else "[FAIL]"
            print("  " + icon + " " + label + ": " + val)
