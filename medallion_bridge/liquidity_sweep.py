"""liquidity_sweep.py — 流动性清扫(Liquidity Sweep)验证引擎 v1

Spring = Liquidity Sweep. 同一现象, 两种理论描述.

本引擎不重复检测Spring(accumulation_detector/lps_upthrust_breakout已有),
而是对已有的Spring/Upthrust信号进行五标准置信度验证。

验证标准(Quantum Algo 2026):
  1. 清晰的流动性池 (相等高/低点, 前日极值, 心理关口)
  2. 影线侵略性 (≥近期平均影线2-3倍)
  3. 1-3根K线内收回
  4. 成交量放大 (≥前几根均值1.5倍)
  5. HTF趋势一致

联动: supply-test / accumulation-detection / lps-upthrust-breakout
"""

import sys, os, struct, json

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def _read_1min_bars(code, limit=300):
    """读取1分钟K线"""
    market = "sz" if code.startswith(("0", "3")) else "sh"
    path = rf"F:\tongdaxin\vipdoc\{market}\minline\{market}{code}.lc1"
    if not os.path.exists(path): return []
    with open(path, "rb") as f:
        data = f.read()
    n = len(data) // 32
    start = max(0, n - limit)
    bars = []
    for i in range(start, n):
        u = struct.unpack_from("<HHfffffIHH", data, i * 32)
        dw, sec = u[0], u[1]
        op, hi, lo, cl, amt = u[2], u[3], u[4], u[5], u[6]
        y, m, d = (dw // 2048) + 2004, (dw % 2048) // 100, dw % 2048 % 100
        bars.append({
            "date": f"{y:04d}{m:02d}{d:02d}", "time": sec,
            "time_str": f"{sec//3600:02d}:{(sec%3600)//60:02d}",
            "open": op, "high": hi, "low": lo, "close": cl,
            "volume": amt / 100.0,
            "wick_up": hi - max(op, cl),
            "wick_down": min(op, cl) - lo,
        })
    return bars


def _today_1min(code):
    bars = _read_1min_bars(code, 300)
    if not bars: return []
    today = bars[-1]["date"]
    return [b for b in bars if b["date"] == today]


# ──────────────────────────────────────────────
#  五标准验证
# ──────────────────────────────────────────────

def validate_sweep(code, sweep_price, sweep_direction, is_bullish=True):
    """
    验证一个疑似Spring/Sweep信号是否满足五大标准
    
    Args:
        code: 股票代码
        sweep_price: 清扫发生的价格
        sweep_direction: "spring"(向下清扫后向上反转) 或 "upthrust"(向上清扫后向下反转)
        is_bullish: True=看涨Spring, False=看跌Upthrust
    
    Returns:
        {
            "validated": bool,        # 是否通过(≥3/5)
            "confidence": "high"/"medium"/"low",
            "score": int,             # 0-5标准通过数
            "checks": list of check结果,
            "detail": str
        }
    """
    bars = _today_1min(code)
    if len(bars) < 20:
        return {"validated": False, "confidence": "low", "score": 0,
                "checks": [], "detail": "数据不足"}

    checks = []
    score = 0

    # ── 标准1: 流动性池 ──
    # 检查sweep_price附近是否有相等高点/低点或前日极值
    recent = bars[-30:]
    prices_high = [b["high"] for b in recent]
    prices_low = [b["low"] for b in recent]
    tol = sweep_price * 0.005  # 0.5%容差

    pool_found = False
    if is_bullish:  # Spring: 向下清扫
        # 找相近的低点
        near_lows = [p for p in prices_low if abs(p - sweep_price) < tol]
        if len(near_lows) >= 2:
            pool_found = True
            checks.append("✓ 流动性池: 相等低点确认")
    else:  # Upthrust: 向上清扫
        near_highs = [p for p in prices_high if abs(p - sweep_price) < tol]
        if len(near_highs) >= 2:
            pool_found = True
            checks.append("✓ 流动性池: 相等高点确认")

    if not pool_found:
        # 宽松判断: 至少是近期极值
        if is_bullish and abs(sweep_price - min(prices_low)) < tol * 3:
            pool_found = True
            checks.append("✓ 流动性池: 近期极值低点")
        elif not is_bullish and abs(sweep_price - max(prices_high)) < tol * 3:
            pool_found = True
            checks.append("✓ 流动性池: 近期极值高点")
        else:
            checks.append("✗ 流动性池: 非关键水平")

    if pool_found: score += 1

    # ── 标准2: 影线侵略性 ──
    recent_wick_ups = [b["wick_up"] for b in recent[-20:]]
    recent_wick_downs = [b["wick_down"] for b in recent[-20:]]
    avg_wick_up = sum(recent_wick_ups) / max(len(recent_wick_ups), 1)
    avg_wick_down = sum(recent_wick_downs) / max(len(recent_wick_downs), 1)

    if is_bullish:
        avg_wick = avg_wick_down
        # 找最近有长下影线的K线
        max_recent_wick = max(recent_wick_downs[-5:]) if recent_wick_downs else 0
        if max_recent_wick > avg_wick * 2:
            checks.append(f"✓ 影线侵略性: {max_recent_wick:.2f} vs 均值{avg_wick:.2f} (>2x)")
            score += 1
        elif max_recent_wick > avg_wick * 1.5:
            checks.append(f"~ 影线侵略性: {max_recent_wick:.2f} vs 均值{avg_wick:.2f} (>1.5x)")
        else:
            checks.append(f"✗ 影线侵略性: {max_recent_wick:.2f} vs 均值{avg_wick:.2f} (<1.5x)")
    else:
        avg_wick = avg_wick_up
        max_recent_wick = max(recent_wick_ups[-5:]) if recent_wick_ups else 0
        if max_recent_wick > avg_wick * 2:
            checks.append(f"✓ 影线侵略性: {max_recent_wick:.2f} vs 均值{avg_wick:.2f} (>2x)")
            score += 1
        elif max_recent_wick > avg_wick * 1.5:
            checks.append(f"~ 影线侵略性: {max_recent_wick:.2f} vs 均值{avg_wick:.2f} (>1.5x)")
        else:
            checks.append(f"✗ 影线侵略性: {max_recent_wick:.2f} vs 均值{avg_wick:.2f} (<1.5x)")

    # ── 标准3: 1-3根K线内收回 ──
    # 清扫后是否在1-3根内回到原区间
    recovered = False
    if len(bars) >= 5:
        last5 = bars[-5:]
        if is_bullish:
            # Spring: 价格跌破低点后回到其上方
            for i in range(len(last5) - 1):
                if last5[i]["close"] < sweep_price and last5[i + 1]["close"] > sweep_price:
                    recovered = True
                    checks.append(f"✓ 收回确认: 第{i+2}根K线收回")
                    break
        else:
            for i in range(len(last5) - 1):
                if last5[i]["close"] > sweep_price and last5[i + 1]["close"] < sweep_price:
                    recovered = True
                    checks.append(f"✓ 收回确认: 第{i+2}根K线收回")
                    break

    if not recovered:
        # 检查当前价格是否已经收回
        current = bars[-1]["close"]
        if is_bullish and current > sweep_price:
            checks.append("✓ 收回确认: 当前已收回")
            recovered = True
        elif not is_bullish and current < sweep_price:
            checks.append("✓ 收回确认: 当前已收回")
            recovered = True
        else:
            checks.append("✗ 收回确认: 尚未收回")

    if recovered: score += 1

    # ── 标准4: 成交量放大 ──
    recent_vols = [b["volume"] for b in bars[-10:]]
    avg_vol = sum(recent_vols) / max(len(recent_vols), 1)
    # 取清扫区域的成交量
    sweep_vols = [b["volume"] for b in bars[-5:]]
    max_sweep_vol = max(sweep_vols) if sweep_vols else 0

    if max_sweep_vol > avg_vol * 1.5:
        checks.append(f"✓ 成交量放大: {max_sweep_vol:.0f} vs 均值{avg_vol:.0f} (>1.5x)")
        score += 1
    elif max_sweep_vol > avg_vol * 1.2:
        checks.append(f"~ 成交量放大: {max_sweep_vol:.0f} vs 均值{avg_vol:.0f} (>1.2x)")
    else:
        checks.append(f"✗ 成交量不足: {max_sweep_vol:.0f} vs 均值{avg_vol:.0f}")

    # ── 标准5: 趋势一致（用价格位置判断） ──
    # 简化: 如果前期是横盘或回调后Spring = 趋势一致
    if len(bars) >= 30:
        prev20 = bars[-30:-5]
        if prev20:
            prev_high = max(b["high"] for b in prev20)
            prev_low = min(b["low"] for b in prev20)
            prev_mid = (prev_high + prev_low) / 2
            current = bars[-1]["close"]

            if is_bullish:
                # Spring前应该是回调/横盘, Spring后向上
                aligned = current > prev_mid
                if aligned:
                    checks.append("✓ HTF一致: 价格在前期中枢上方")
                    score += 1
                else:
                    checks.append("✗ HTF不一致: 价格仍在前期中枢下方")
            else:
                aligned = current < prev_mid
                if aligned:
                    checks.append("✓ HTF一致: 价格在前期中枢下方")
                    score += 1
                else:
                    checks.append("✗ HTF不一致: 价格仍在前期中枢上方")

    # ── 总分判断 ──
    validated = score >= 3
    if score >= 5: confidence = "high"
    elif score >= 4: confidence = "high"
    elif score >= 3: confidence = "medium"
    else: confidence = "low"

    detail = f"Sweep验证: {score}/5标准通过 → {confidence}置信度"
    if is_bullish:
        detail += " | Spring(Sweep)"
    else:
        detail += " | Upthrust(Sweep)"

    return {
        "validated": validated,
        "confidence": confidence,
        "score": score,
        "checks": checks,
        "detail": detail,
        "sweep_type": "spring" if is_bullish else "upthrust"
    }


def score_for_quad_lens(code, sweep_price=None):
    """
    为quad_lens提供Sweep置信度增强
    
    不独立计分，而是返回对Spring/Upthrust相关维度的增强系数
    """
    # 如果没有指定sweep_price，尝试从accumulation_detector获取
    if sweep_price is None:
        # 读取accumulation状态
        acc_file = os.path.join(ROOT, "_accumulation_state.json")
        if os.path.exists(acc_file):
            with open(acc_file, "r", encoding="utf-8") as f:
                try:
                    acc = json.load(f)
                    sweep_price = acc.get(f"a_{code}", {}).get("range_low")
                except:
                    pass

    if sweep_price is None:
        return {"boost_lps": 0, "boost_spring": 0, "detail": "无Sweep价格基准"}

    # 同时检查Spring和Upthrust
    bullish = validate_sweep(code, sweep_price, "spring", True)
    bearish = validate_sweep(code, sweep_price, "upthrust", False)

    result = {"boost_lps": 0, "boost_spring": 0, "detail": ""}

    if bullish["validated"]:
        if bullish["confidence"] == "high":
            result["boost_spring"] = 5
            result["boost_lps"] = 3
            result["detail"] = f"Spring(Sweep)高置信度: {bullish['score']}/5"
        else:
            result["boost_spring"] = 3
            result["detail"] = f"Spring(Sweep)中置信度: {bullish['score']}/5"

    if bearish["validated"]:
        result["boost_lps"] -= 3
        result["detail"] += f" | Upthrust警告: {bearish['score']}/5"

    return result


def summary(code):
    """一句话Sweep摘要"""
    bars = _today_1min(code)
    if len(bars) < 10: return ""
    # 简单检测: 最近是否有长影线
    recent = bars[-5:]
    down_wick = [b["wick_down"] for b in recent]
    up_wick = [b["wick_up"] for b in recent]
    if max(down_wick) > max(up_wick) * 2:
        return "⚡ 疑似Spring Sweep(长下影线)"
    elif max(up_wick) > max(down_wick) * 2:
        return "⚡ 疑似Upthrust Sweep(长上影线)"
    return ""


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("sweep_price", type=float, nargs="?")
    p.add_argument("--bullish", action="store_true", default=True)
    args = p.parse_args()

    price = args.sweep_price or 44
    result = validate_sweep(args.code, price, "spring", args.bullish)

    print(f"\n{'='*50}")
    print(f"  🔎 Liquidity Sweep验证 — {args.code}")
    print(f"{'='*50}")
    print(f"  类型: {'Spring(看涨)' if args.bullish else 'Upthrust(看跌)'}")
    print(f"  价格: {price:.2f}")
    print(f"  结果: {result['detail']}")
    print(f"  置信度: {result['confidence']}")
    for c in result["checks"]:
        print(f"    {c}")
    print()
