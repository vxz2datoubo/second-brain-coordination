"""flow_divergence.py — 资金流价格背离分析模块 v1

基于 Marc Chaikin 的 CMF 指标 + Order Flow Imbalance 理论
持续跟踪净流入与价格关系，检测背离信号。

功能:
  - CMF (Chaikin Money Flow) 计算
  - 看涨/看跌背离检测
  - 资金流趋势 vs 价格趋势对比
  - 集成 supply_tester 联合判断
"""

import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daytrade_system"))

from engine.indicators import KBar


def _tdx_min5(code, limit=200):
    market = "sz" if code.startswith(("0", "3")) else "sh"
    path = rf"F:\tongdaxin\vipdoc\{market}\fzline\{market}{code}.lc5"
    if not os.path.exists(path):
        return []
    bars = []
    with open(path, "rb") as f:
        data = f.read()
    n = len(data) // 32
    start = max(0, n - limit)
    for i in range(start, n):
        u = struct.unpack_from("<HHfffffIHH", data, i * 32)
        dw, sec = u[0], u[1]
        op, hi, lo, cl = u[2], u[3], u[4], u[5]
        amt = u[6]
        y, m, d = (dw // 2048) + 2004, (dw % 2048) // 100, dw % 2048 % 100
        bars.append(KBar(date=f"{y:04d}{m:02d}{d:02d}", time_sec=sec,
                         open=op, high=hi, low=lo, close=cl,
                         volume=amt / 100.0, amount=amt / 100.0))
    return bars


def calc_mfm(close, high, low):
    """Money Flow Multiplier: -1 到 +1"""
    rng = high - low
    if rng == 0:
        return 0
    return ((close - low) - (high - close)) / rng


def calc_cmf(bars, period=20):
    """计算 Chaikin Money Flow"""
    if len(bars) < period:
        return []
    values = []
    for i in range(period - 1, len(bars)):
        window = bars[i - period + 1 : i + 1]
        mf_vol = sum(calc_mfm(b.close, b.high, b.low) * b.volume for b in window)
        total_vol = sum(b.volume for b in window)
        cmf = mf_vol / max(total_vol, 1)
        values.append(cmf)
    return values


def detect_divergence(bars, cmf_values):
    """检测价格与CMF的背离

    Returns: {
      "type": "bullish"/"bearish"/None,
      "price_signal": "new_high"/"new_low",
      "cmf_signal": "higher"/"lower",
      "confidence": 0-100,
      "bars_ago": int  # 多少根bar前发生的背离
    }
    """
    if len(bars) < 30 or len(cmf_values) < 20:
        return {"type": None, "confidence": 0}

    # 取最近区域: 最近10根bar vs 前10根bar
    recent_bars = bars[-10:]
    prior_bars = bars[-20:-10]
    recent_cmf = cmf_values[-10:]
    prior_cmf = cmf_values[-20:-10]

    if not recent_bars or not prior_bars or not recent_cmf or not prior_cmf:
        return {"type": None, "confidence": 0}

    recent_high = max(b.high for b in recent_bars)
    prior_high = max(b.high for b in prior_bars)
    recent_low = min(b.low for b in recent_bars)
    prior_low = min(b.low for b in prior_bars)
    avg_recent_cmf = sum(recent_cmf) / len(recent_cmf)
    avg_prior_cmf = sum(prior_cmf) / len(prior_cmf)

    # 看跌背离: 价格新高 + CMF新低
    if recent_high > prior_high * 1.002 and avg_recent_cmf < avg_prior_cmf - 0.02:
        severity = (recent_high / prior_high - 1) * 100 + abs(avg_recent_cmf - avg_prior_cmf) * 50
        return {"type": "bearish", "price_signal": "new_high", "cmf_signal": "lower",
                "confidence": min(int(severity * 5), 85),
                "bars_ago": 10, "detail": f"价格突破前期高但资金流减弱 {avg_recent_cmf:.3f} vs {avg_prior_cmf:.3f}"}

    # 看涨背离: 价格新低 + CMF新高
    if recent_low < prior_low * 0.998 and avg_recent_cmf > avg_prior_cmf + 0.02:
        severity = (prior_low / recent_low - 1) * 100 + (avg_recent_cmf - avg_prior_cmf) * 50
        return {"type": "bullish", "price_signal": "new_low", "cmf_signal": "higher",
                "confidence": min(int(severity * 5), 85),
                "bars_ago": 10, "detail": f"价格跌破前期低但资金流增强 {avg_recent_cmf:.3f} vs {avg_prior_cmf:.3f}"}

    return {"type": None, "confidence": 0}


def flow_price_analysis(code):
    """完整的资金流-价格分析"""
    bars = _tdx_min5(code, 200)
    if len(bars) < 30:
        return {"error": "数据不足"}

    # 只取今日
    today = bars[-1].date
    today_bars = [b for b in bars if b.date == today]
    if len(today_bars) < 10:
        return {"error": "今日数据不足"}

    # CMF 计算
    cmf = calc_cmf(today_bars, period=12)
    if not cmf:
        return {"error": "CMF数据不足"}

    current_cmf = cmf[-1]
    avg_cmf_today = sum(cmf) / len(cmf)

    # 背离检测
    div = detect_divergence(today_bars, cmf)

    # 资金流状态
    if current_cmf > 0.20:
        pressure = "强买入压力"
    elif current_cmf > 0.05:
        pressure = "温和买入"
    elif current_cmf < -0.20:
        pressure = "强卖出压力"
    elif current_cmf < -0.05:
        pressure = "温和卖出"
    else:
        pressure = "中性"

    # 趋势
    recent_cmf5 = cmf[-5:] if len(cmf) >= 5 else cmf
    prior_cmf5 = cmf[-10:-5] if len(cmf) >= 10 else cmf[:5]
    avg_r5 = sum(recent_cmf5) / len(recent_cmf5)
    avg_p5 = sum(prior_cmf5) / len(prior_cmf5)
    trend = "上升" if avg_r5 > avg_p5 + 0.03 else "下降" if avg_r5 < avg_p5 - 0.03 else "持平"

    # 尝试联动供应测试
    try:
        from supply_tester import analyze_supply_test as ast
        supply = ast(code, today_bars[-1].close, max(b.high for b in today_bars), min(b.low for b in today_bars))
    except Exception:
        supply = None

    return {
        "current_cmf": round(current_cmf, 3),
        "avg_cmf_today": round(avg_cmf_today, 3),
        "pressure": pressure,
        "trend_5bar": trend,
        "divergence": div,
        "joint_signal": _joint_signal(div, today_bars[-1].close, today_bars[0].close, current_cmf, supply)
    }


def _joint_signal(div, close_now, close_open, cmf_current, supply_result=None):
    """与供应测试联动的综合判断"""
    signals = []

    # CMF 负值三元判断
    if cmf_current < -0.15 and supply_result:
        sup = supply_result
        if sup["test_passed"] or sup["confidence"] >= 45:
            signals.append("🟡 CMF负+供应测试通过=主力抛压测试，非真出货")
        elif sup["confidence"] <= 20:
            signals.append("🔴 CMF负+供应测试未触发=可能是真派发，警惕")
        else:
            signals.append("🟡 CMF负+供应测试进行中=等进一步确认")
    elif cmf_current < -0.15:
        signals.append("⚠️ CMF强负(-0.15以下)，需结合供应测试判断是测试还是派发")

    if cmf_current > 0.10:
        signals.append("🟢 CMF正=资金主动买入，继续看多")

    if div["type"] == "bullish" and div["confidence"] > 30:
        signals.append("🟢 资金流看涨背离: 跌时吸筹")
    if div["type"] == "bearish" and div["confidence"] > 30:
        signals.append("🔴 资金流看跌背离: 涨时出货")

    if close_now > close_open * 1.02:
        signals.append("📈 日内涨幅>2%，观察CMF是否跟随")
    if not signals:
        signals.append("➖ 资金流与价格同步，无背离")
    return signals


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("--cmf", action="store_true")
    p.add_argument("--divergence", action="store_true")
    args = p.parse_args()

    r = flow_price_analysis(args.code)
    if "error" in r:
        print(f"❌ {r['error']}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"  💰 资金流分析 — {args.code}")
    print(f"{'='*50}")
    print(f"  CMF 当前: {r['current_cmf']:+.3f}")
    print(f"  CMF 日均: {r['avg_cmf_today']:+.3f}")
    print(f"  资金压力: {r['pressure']}")
    print(f"  短期趋势: {r['trend_5bar']}")

    div = r["divergence"]
    if div["type"]:
        icon = "🔴" if div["type"] == "bearish" else "🟢"
        print(f"\n  {icon} 背离信号: {div['type']} (置信度{div['confidence']})")
        print(f"     {div.get('detail','')}")

    print(f"\n  综合判断:")
    for s in r["joint_signal"]:
        print(f"    {s}")
    print()
