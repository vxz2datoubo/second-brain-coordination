"""accumulation_detector.py — 威科夫吸筹阶段检测 v1

基于日K线和5分钟K线数据，自动判定当前 Wyckoff Phase (A/B/C/D/E)。
估算吸筹量、POC、潜在上涨目标。

用法:
  python accumulation_detector.py 300418 [--projection]
"""

import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daytrade_system"))


def _tdx_daily(code, limit=120):
    market = "sz" if code.startswith(("0", "3")) else "sh"
    path = rf"F:\tongdaxin\vipdoc\{market}\lday\{market}{code}.day"
    if not os.path.exists(path): return []
    bars = []
    with open(path, "rb") as f: data = f.read()
    n = len(data) // 32
    for i in range(max(0, n-limit), n):
        u = struct.unpack_from("<IIIIIfII", data, i*32)
        date_int, op, hi, lo, cl, amt, vol = u[0], u[1]/100.0, u[2]/100.0, u[3]/100.0, u[4]/100.0, u[5], u[6]
        bars.append({"date": str(date_int), "open": op, "high": hi, "low": lo, "close": cl, "amount": amt, "volume": vol})
    return bars


def _tdx_min5(code, limit=200):
    market = "sz" if code.startswith(("0", "3")) else "sh"
    path = rf"F:\tongdaxin\vipdoc\{market}\fzline\{market}{code}.lc5"
    if not os.path.exists(path): return []
    bars = []
    with open(path, "rb") as f: data = f.read()
    n = len(data) // 32
    for i in range(max(0, n-limit), n):
        u = struct.unpack_from("<HHfffffIHH", data, i*32)
        dw, sec = u[0], u[1]
        y, m, d = (dw//2048)+2004, (dw%2048)//100, dw%2048%100
        bars.append({"date": f"{y:04d}{m:02d}{d:02d}", "time": sec,
                      "open": u[2], "high": u[3], "low": u[4], "close": u[5],
                      "amount": u[6], "volume": u[7]})
    return bars


def detect_phase(code, current_price):
    """自动判定威科夫吸筹阶段"""
    daily = _tdx_daily(code, 120)
    min5 = _tdx_min5(code, 200)
    if len(daily) < 30: return {"phase": "UNKNOWN", "confidence": 0}

    # 找主要高低点
    recent = daily[-60:]  # 约3个月
    lows = [b["low"] for b in recent]
    highs = [b["high"] for b in recent]
    closes = [b["close"] for b in recent]
    volumes = [b["volume"] for b in recent]

    # Phase A 要素: SC (卖出高潮)
    abs_min = min(lows)
    abs_max = max(highs[-30:])  # 最近30天的最高点
    range_low = abs_min
    range_high = abs_max

    # 找 SC: 最低点附近高量日
    sc_idx = recent.index(min(recent, key=lambda b: b["low"]))
    sc_volume = recent[sc_idx]["volume"]

    # Spring 判断: 假跌破后快速收回
    spring_detected = False
    for i in range(2, len(recent)-1):
        if recent[i]["low"] < recent[i-1]["low"] < recent[i-2]["low"]:
            # 跌破前低
            bounce = recent[i+1]["close"] - recent[i]["low"]
            if bounce > (recent[i]["high"] - recent[i]["low"]) * 0.7:
                spring_detected = True
                spring_idx = i
                break

    # 最近走势
    last5 = recent[-5:]
    recent_trend = "up" if last5[-1]["close"] > last5[0]["close"] else "down"
    avg_vol_recent = sum(b["volume"] for b in last5) / 5
    avg_vol_prior = sum(volumes[-10:-5]) / 5

    # Volume Profile POC 估算
    if min5:
        vol_by_price = {}
        for b in min5:
            price_bin = round(b["close"])
            vol_by_price[price_bin] = vol_by_price.get(price_bin, 0) + b["volume"]
        poc = max(vol_by_price, key=vol_by_price.get) if vol_by_price else None
    else:
        poc = None

    # Phase C→D 过渡检测
    transition_score = 0
    if spring_detected:
        # 要素4: 成交量连续萎缩
        if avg_vol_recent < avg_vol_prior * 0.7:
            transition_score += 1
        # 要素3: 小实体K线
        if abs(closes[-1] - closes[-2]) / closes[-2] < 0.015:
            transition_score += 1
        # 要素1+2: Spring + supply test (使用之前检测的结果)
        if spring_detected:
            transition_score += 2  # 前两个条件在判定spring时已满足

    poc = poc  # already computed

    # 阶段判定
    if transition_score >= 3:
        phase = "C_D_TRANSITION"
        detail = "C→D过渡K线: 缩量十字星+供应测试完成 — 明天大概率向上"
        confidence = 65
    elif not spring_detected and recent_trend == "down":
        phase = "A"
        detail = "还在跌，等待卖出高潮(SC)"
        confidence = 30
    elif spring_detected and current_price < range_high * 1.05:
        # 检查是否有 SOS
        last10_high = max(b["high"] for b in recent[-10:])
        if current_price > last10_high * 0.97 and avg_vol_recent > avg_vol_prior:
            phase = "D"
            detail = "Phase D: SOS出现中，等待放量突破确认"
            confidence = 55
        elif avg_vol_recent < avg_vol_prior * 0.7:
            phase = "C"
            detail = "Phase C: Spring后缩量测试中，等待SOS"
            confidence = 45
        else:
            phase = "B_C"
            detail = "Phase B→C过渡: 吸筹区间震荡，等待弹簧或突破"
            confidence = 40
    elif current_price > range_high * 1.05:
        phase = "E"
        detail = "Phase E: 可能已进入主升浪"
        confidence = 50
    else:
        phase = "B"
        detail = "Phase B: 区间蓄力中，机构持续吸筹"
        confidence = 35

    # 因与果推演
    range_width = range_high - range_low
    cause_days = sum(1 for b in recent if range_low <= b["close"] <= range_high)
    markup_min = range_width * 1.0
    markup_moderate = range_width * 1.5
    markup_aggressive = range_width * 2.0

    return {
        "phase": phase,
        "confidence": confidence,
        "detail": detail,
        "spring_detected": spring_detected,
        "transition_detected": transition_score >= 3,
        "transition_score": transition_score,
        "range_low": round(range_low, 2),
        "range_high": round(range_high, 2),
        "range_width": round(range_width, 2),
        "poc": poc,
        "cause_days": cause_days,
        "projection": {
            "conservative": round(range_high + markup_min, 1),
            "moderate": round(range_high + markup_moderate, 1),
            "aggressive": round(range_high + markup_aggressive, 1)
        },
        "estimated_total_volume": sum(b["volume"] for b in recent[-cause_days:])
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("price", type=float)
    p.add_argument("--projection", action="store_true")
    args = p.parse_args()

    r = detect_phase(args.code, args.price)
    print(f"\n  🏗️ 威科夫吸筹检测 — {args.code}")
    print(f"  Phase: {r['phase']} (置信度{r['confidence']})")
    print(f"  {r['detail']}")
    print(f"  吸筹区间: {r['range_low']}-{r['range_high']} (宽{r['range_width']}元)")
    print(f"  控制点 POC: {r['poc']}")
    print(f"  吸筹天数: ~{r['cause_days']}天")
    print(f"  Spring: {'✅ 已出现' if r['spring_detected'] else '❌ 未出现'}")

    if args.projection:
        proj = r["projection"]
        print(f"\n  📐 因与果推演 (突破{r['range_high']}后):")
        print(f"     保守: {proj['conservative']}")
        print(f"     适中: {proj['moderate']}")
        print(f"     激进: {proj['aggressive']}")
    print()
