"""breakout_validator.py — 威科夫突破确认检测 v1

检测 SOS 突破 → LPS 回踩确认，区分 Upthrust 陷阱。
实时跟踪三次供应测试后的突破和回踩。

用法:
  python breakout_validator.py 300418 46.0
"""

import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.indicators import KBar


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
        bars.append(KBar(date=f"{y:04d}{m:02d}{d:02d}", time_sec=sec,
                         open=u[2], high=u[3], low=u[4], close=u[5],
                         volume=u[6]/100.0, amount=u[6]/100.0))
    return bars


def detect_breakout_pattern(code, resistance_level=46.0):
    """检测突破和回踩模式: SOS/LPS/Upthrust"""
    bars = _tdx_min5(code, 200)
    if len(bars) < 10: return {"type": "NONE", "confidence": 0}

    today = bars[-1].date
    today_bars = [b for b in bars if b.date == today]
    if len(today_bars) < 5: return {"type": "NONE", "confidence": 0}

    # 只检测实质性突破（日高超过阻力至少1%才算）
    breakouts = []
    for i in range(1, len(today_bars)):
        if today_bars[i].high > resistance_level * 1.01 and today_bars[i-1].high <= resistance_level:
            breakouts.append(i)

    if not breakouts:
        return {"type": "NO_BREAKOUT", "confidence": 0,
                "detail": f"尚未突破{resistance_level}",
                "distance_to_resistance": round(resistance_level - today_bars[-1].close, 2)}

    last_break = breakouts[-1]
    breakout_bar = today_bars[last_break]
    breakout_vol = breakout_bar.volume
    breakout_range = breakout_bar.high - breakout_bar.low

    # 突破后的回踩: 取突破后到最新
    pullback_bars = today_bars[last_break+1:] if last_break+1 < len(today_bars) else []
    if len(pullback_bars) < 2:
        return {"type": "BREAKOUT_NO_PULLBACK", "confidence": 0,
                "detail": "刚突破，等待回踩"}

    pullback_vol = sum(b.volume for b in pullback_bars) / len(pullback_bars)
    pullback_low = min(b.low for b in pullback_bars)
    pullback_avg_range = sum(b.high - b.low for b in pullback_bars) / len(pullback_bars)

    vol_ratio = pullback_vol / max(breakout_vol, 1)
    range_ratio = pullback_avg_range / max(breakout_range, 0.01)
    re_entered = pullback_low < resistance_level

    # ── 判定 ──
    if vol_ratio < 0.40 and not re_entered:
        return {"type": "SOS_LPS", "confidence": 80,
                "detail": f"强LPS: 回踩量{vol_ratio:.0%}→供应真空",
                "vol_ratio": vol_ratio, "range_ratio": range_ratio, "re_entered": False,
                "recommendation": "加仓/持有多仓"}
    elif vol_ratio < 0.60 and not re_entered:
        return {"type": "LPS", "confidence": 65,
                "detail": f"正常LPS: 回踩量{vol_ratio:.0%}→回踩确认",
                "vol_ratio": vol_ratio, "range_ratio": range_ratio, "re_entered": False,
                "recommendation": "可持有，等下一波"}
    elif vol_ratio < 0.80 and not re_entered:
        return {"type": "WEAK_LPS", "confidence": 40,
                "detail": f"弱LPS: 回踩量{vol_ratio:.0%}→等待二次确认",
                "vol_ratio": vol_ratio, "range_ratio": range_ratio, "re_entered": False,
                "recommendation": "减半仓，观察"}
    elif re_entered and vol_ratio > 0.60:
        return {"type": "UPTHRUST", "confidence": 75,
                "detail": f"上冲陷阱: 回踩量{vol_ratio:.0%}+跌回→主力派发！",
                "vol_ratio": vol_ratio, "range_ratio": range_ratio, "re_entered": True,
                "recommendation": "立刻全部平仓"}
    elif re_entered:
        return {"type": "UPTHRUST_WEAK", "confidence": 50,
                "detail": f"疑似上冲: 跌回区间但量可控→需观察",
                "vol_ratio": vol_ratio, "range_ratio": range_ratio, "re_entered": True,
                "recommendation": "减仓，设止损"}
    else:
        return {"type": "BREAKOUT_TESTING", "confidence": 30,
                "detail": "突破后回踩中，等待方向",
                "vol_ratio": vol_ratio, "range_ratio": range_ratio, "re_entered": False}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("resistance", type=float, nargs="?", default=46.0)
    args = p.parse_args()
    r = detect_breakout_pattern(args.code, args.resistance)
    print(f"\n  🚀 突破检测 — {args.code} @ 阻力{args.resistance}")
    print(f"  类型: {r['type']} (置信度{r['confidence']})")
    print(f"  {r['detail']}")
    if "recommendation" in r:
        print(f"  建议: {r['recommendation']}")
    if "distance_to_resistance" in r:
        print(f"  距阻力: {r['distance_to_resistance']}元")
    print()
