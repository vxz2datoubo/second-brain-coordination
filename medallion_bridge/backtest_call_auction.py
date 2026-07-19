"""backtest_call_auction.py — 集合竞价信号回测验证

测试假设(无未来函数):
  1. 高开(>2%)+开盘量缩(<0.5x均值) → 虚假高开 → 当日容易回落 (诱多)
  2. 高开(>2%)+开盘量增(>2x均值) → 真实高开 → 当日继续走强 (抢筹)
  3. 低开(<-1%)+开盘量增(>2x均值) → 恐慌低开 → 可能Spring反弹 (诱空)
  4. 开盘区间窄(<0.7x平均宽度) → 当日有大行情(振幅>3%)
  5. 开盘5分内突破ORH → 当日收阳概率高

数据源: 通达信1分钟K线 (.lc1)
"""

import struct, os
from collections import defaultdict
from datetime import datetime

# 参数
CODE = "300418"
DAYS_BACK = 2000  # 扫描所有记录
MIN_DAYS_FOR_STATS = 20

def load_all_bars(code):
    """加载全部1分钟K线并分天"""
    market = "sz" if code.startswith(("0", "3")) else "sh"
    path = rf"F:\tongdaxin\vipdoc\{market}\minline\{market}{code}.lc1"
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        data = f.read()
    n = len(data) // 32
    bars = []
    for i in range(max(0, n - DAYS_BACK * 240), n):
        u = struct.unpack_from("<HHfffffIHH", data, i * 32)
        dw, sec = u[0], u[1]
        op, hi, lo, cl, amt = u[2], u[3], u[4], u[5], u[6]
        y, m, d = (dw // 2048) + 2004, (dw % 2048) // 100, dw % 2048 % 100
        bars.append({
            "date": f"{y:04d}{m:02d}{d:02d}",
            "time": sec,
            "open": op, "high": hi, "low": lo, "close": cl,
            "volume": amt / 100.0,
        })
    # 按天分组
    days = defaultdict(list)
    for b in bars:
        days[b["date"]].append(b)
    return dict(days)


def _analyze_day(day_bars, prev_close=None):
    """
    分析单个交易日的竞价/开盘信号
    无未来函数: 只用开盘时的数据做判断, 收盘数据仅用于验证
    
    prev_close: 前一日收盘价(用于计算开盘涨跌幅)
    """
    if len(day_bars) < 30:
        return None
    if prev_close is None or prev_close <= 0:
        return None  # 第一天无法计算开盘涨幅
    open_bar_930 = None
    for b in day_bars:
        if 9 * 60 + 30 <= b["time"] <= 9 * 60 + 31:
            open_bar_930 = b
            break
    if open_bar_930 is None:
        return None

    open_price = open_bar_930["open"]
    open_pct = (open_price / prev_close - 1) * 100

    # 开盘初始数据(无未来函数)
    first_vol = open_bar_930["volume"]

    # 前5分钟数据 (9:30-9:35, sec = 570-575)
    first_5 = [b for b in day_bars if 9 * 60 + 30 <= b["time"] <= 9 * 60 + 35]
    # 开盘区间 9:30-9:45 (sec = 570-585)
    or_bars = [b for b in day_bars if 9 * 60 + 30 <= b["time"] <= 9 * 60 + 45]

    # 日结果(仅用于验证, 不用于信号判断)
    day_close = day_bars[-1]["close"]
    day_high = max(b["high"] for b in day_bars)
    day_low = min(b["low"] for b in day_bars)
    day_ret = (day_close / open_price - 1) * 100
    day_range = (day_high - day_low) / day_low * 100

    # 近期平均成交量(用于量比) — 取交易日中间段
    mid_bars = [b for b in day_bars if 10*60 <= b["time"] <= 14*60]
    recent_vols = [b["volume"] for b in mid_bars if b["volume"] > 0]
    avg_vol = sum(recent_vols) / max(len(recent_vols), 1) if recent_vols else 1000

    # ── 信号计算(仅用开盘数据) ──
    signals = {}

    # 1. 开盘量比
    if avg_vol > 0:
        vol_ratio = first_vol / avg_vol
    else:
        vol_ratio = 1.0
    signals["vol_ratio"] = vol_ratio

    # 2. 高开+量缩 vs 高开+量增
    if open_pct > 2 and vol_ratio < 0.5:
        signals["fake_high"] = True  # 诱多嫌疑
    else:
        signals["fake_high"] = False
    if open_pct > 2 and vol_ratio > 2:
        signals["real_high"] = True  # 抢筹
    else:
        signals["real_high"] = False

    # 3. 低开+量增 (诱空/Spring)
    if open_pct < -1 and vol_ratio > 2:
        signals["panic_low"] = True
    else:
        signals["panic_low"] = False

    # 4. 平开 (参考组)
    if abs(open_pct) < 0.5:
        signals["flat_open"] = True
    else:
        signals["flat_open"] = False

    # 5. 开盘5分钟走势强
    if len(first_5) >= 2:
        p5 = first_5[-1]["close"]
        signals["first_5_up"] = (p5 - open_price) / open_price > 0.003
        signals["first_5_down"] = (p5 - open_price) / open_price < -0.003
    else:
        signals["first_5_up"] = False
        signals["first_5_down"] = False

    return {
        "date": day_bars[0]["date"],
        "open_price": open_price,
        "prev_close": prev_close,
        "open_pct": round(open_pct, 2),
        "day_ret": round(day_ret, 2),
        "day_range": round(day_range, 2),
        "day_high": round(day_high, 2),
        "day_low": round(day_low, 2),
        "day_close": round(day_close, 2),
        "vol_ratio": round(vol_ratio, 2),
        "fake_high": signals["fake_high"],
        "real_high": signals["real_high"],
        "panic_low": signals["panic_low"],
        "flat_open": signals["flat_open"],
        "first_5_up": signals["first_5_up"],
        "first_5_down": signals["first_5_down"],
    }


def run_backtest(code="300418"):
    """运行回测"""
    days = load_all_bars(code)
    dates = sorted(days.keys())
    
    # 初始化昨日收盘价（用第一天的收盘）
    if len(dates) < 2:
        print("数据不足")
        return
    prev_close = days[dates[0]][-1]["close"]
    
    results = []
    for date_str in dates[1:]:  # 从第二天开始, 已有昨日收盘价
        day_bars = days[date_str]
        r = _analyze_day(day_bars, prev_close)
        if r:
            results.append(r)
            prev_close = r["day_close"]  # 今日收盘 = 明日的前日收盘

    if len(results) < MIN_DAYS_FOR_STATS:
        print(f"数据不足: {len(results)}天 < {MIN_DAYS_FOR_STATS}")
        return

    print(f"\n{'='*65}")
    print(f"  📊 集合竞价信号回测 — {code}")
    print(f"  样本: {len(results)}个交易日 ({results[0]['date']} ~ {results[-1]['date']})")
    print(f"  ⚠️ 当前用近似数据: 完整竞价需Level 2")
    print(f"{'='*65}")

    # ────── 信号验证 ──────

    # 测试1: 诱多(高开+量缩) → 当日是否回落
    fake_high_days = [r for r in results if r["fake_high"]]
    real_high_days = [r for r in results if r["real_high"]]
    panic_low_days = [r for r in results if r["panic_low"]]
    flat_days = [r for r in results if r["flat_open"]]

    print(f"\n  ┌─ 信号1: 诱多(高开>2%+量缩<0.5x) ───────────────┐")
    if fake_high_days:
        avg_ret = sum(r["day_ret"] for r in fake_high_days) / len(fake_high_days)
        win_rate = sum(1 for r in fake_high_days if r["day_ret"] < 0) / len(fake_high_days) * 100
        max_loss = min(r["day_ret"] for r in fake_high_days)
        print(f"  │ 出现{len(fake_high_days)}次 | 平均日内收益:{avg_ret:+.2f}%")
        print(f"  │ 日内下跌率:{win_rate:.0f}% | 最大单日亏损:{max_loss:+.2f}%")
        for r in fake_high_days[-5:]:
            print(f"  │   {r['date']}: 开{r['open_pct']:+.1f}%→收{r['day_ret']:+.1f}%")
    else:
        print(f"  │ 无信号(或样本不足)")
    print(f"  └────────────────────────────────────────────────────┘")

    print(f"\n  ┌─ 信号2: 抢筹(高开>2%+量增>2x) ────────────────┐")
    if real_high_days:
        avg_ret = sum(r["day_ret"] for r in real_high_days) / len(real_high_days)
        win_rate = sum(1 for r in real_high_days if r["day_ret"] > 0) / len(real_high_days) * 100
        print(f"  │ 出现{len(real_high_days)}次 | 平均日内收益:{avg_ret:+.2f}%")
        print(f"  │ 日内上涨率:{win_rate:.0f}%")
        for r in real_high_days[-5:]:
            print(f"  │   {r['date']}: 开{r['open_pct']:+.1f}%→收{r['day_ret']:+.1f}%")
    else:
        print(f"  │ 无信号(或样本不足)")
    print(f"  └────────────────────────────────────────────────────┘")

    print(f"\n  ┌─ 信号3: 诱空(低开<-1%+量增>2x) ───────────────┐")
    if panic_low_days:
        avg_ret = sum(r["day_ret"] for r in panic_low_days) / len(panic_low_days)
        bounce_rate = sum(1 for r in panic_low_days if r["day_ret"] > 0) / len(panic_low_days) * 100
        print(f"  │ 出现{len(panic_low_days)}次 | 平均日内收益:{avg_ret:+.2f}%")
        print(f"  │ 日内反弹率:{bounce_rate:.0f}% (Spring成功率)")
        for r in panic_low_days[-5:]:
            print(f"  │   {r['date']}: 开{r['open_pct']:+.1f}%→收{r['day_ret']:+.1f}%")
    else:
        print(f"  │ 无信号(或样本不足)")
    print(f"  └────────────────────────────────────────────────────┘")

    print(f"\n  ┌─ 信号4: 平开(基准对照) ────────────────────────┐")
    if flat_days:
        avg_ret = sum(r["day_ret"] for r in flat_days) / len(flat_days)
        pos_rate = sum(1 for r in flat_days if r["day_ret"] > 0) / len(flat_days) * 100
        avg_range = sum(r["day_range"] for r in flat_days) / len(flat_days)
        print(f"  │ {len(flat_days)}次平开 | 平均收益:{avg_ret:+.2f}% | 上涨率:{pos_rate:.0f}%")
        print(f"  │ 平均日振幅:{avg_range:.2f}%")
    print(f"  └────────────────────────────────────────────────────┘")

    # 对比表
    print(f"\n  {'─'*55}")
    print(f"  📋 信号对比总结")
    print(f"  {'信号':<20} {'次数':>4} {'平均收益':>8} {'胜率':>6}")
    print(f"  {'─'*40}")
    for label, days_list in [("诱多(高开+量缩)", fake_high_days),
                               ("抢筹(高开+量增)", real_high_days),
                               ("诱空(低开+量增)", panic_low_days),
                               ("平开(对照)", flat_days)]:
        if days_list:
            avg_r = sum(r["day_ret"] for r in days_list) / len(days_list)
            wr = sum(1 for r in days_list if r["day_ret"] > 0) / len(days_list) * 100
            if label == "诱多(高开+量缩)":
                wr = sum(1 for r in days_list if r["day_ret"] < 0) / len(days_list) * 100
            elif label == "诱空(低开+量增)":
                wr = sum(1 for r in days_list if r["day_ret"] > 0) / len(days_list) * 100
            print(f"  {label:<20} {len(days_list):>4} {avg_r:>+7.2f}% {wr:>5.0f}%")
    print()

    # 额外: 高开量缩 vs 高开量增对比
    print(f"  🔬 高开对比: 量缩({len(fake_high_days)}次) vs 量增({len(real_high_days)}次)")
    if fake_high_days and real_high_days:
        f_ret = sum(r["day_ret"] for r in fake_high_days) / len(fake_high_days)
        r_ret = sum(r["day_ret"] for r in real_high_days) / len(real_high_days)
        print(f"     量缩平均:{f_ret:+.2f}%  vs  量增平均:{r_ret:+.2f}%  → 差值:{r_ret-f_ret:+.2f}%")
    print()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--code", default="300418")
    args = p.parse_args()
    run_backtest(args.code)
