"""call_auction.py — A股集合竞价分析 v1

A股独有: 9:15-9:20(可撤单/烟雾弹) → 9:20-9:25(不可撤/真实意图)
双阶段差分 = 自带测谎仪的开盘机制

当前限制: TDX MCP不提供竞价逐秒挂单量, 用开盘结果反推。
Level 2开通后可接入实时竞价数据。

联动: opening-range / supply-test / accumulation-detection
"""

import sys, os, struct, json

ROOT = os.path.dirname(os.path.abspath(__file__))


def _today_1min(code):
    """读取今日1分钟K线"""
    market = "sz" if code.startswith(("0", "3")) else "sh"
    path = rf"F:\tongdaxin\vipdoc\{market}\minline\{market}{code}.lc1"
    if not os.path.exists(path): return []
    with open(path, "rb") as f:
        data = f.read()
    n = len(data) // 32
    start = max(0, n - 300)
    bars = []
    for i in range(start, n):
        u = struct.unpack_from("<HHfffffIHH", data, i * 32)
        dw, sec = u[0], u[1]
        op, hi, lo, cl, amt = u[2], u[3], u[4], u[5], u[6]
        y, m, d = (dw // 2048) + 2004, (dw % 2048) // 100, dw % 2048 % 100
        bars.append({
            "date": f"{y:04d}{m:02d}{d:02d}", "time": sec,
            "open": op, "high": hi, "low": lo, "close": cl,
            "volume": amt / 100.0,
        })
    today = bars[-1]["date"]
    return [b for b in bars if b["date"] == today]


def auction_context(code, prev_close):
    """
    集合竞价上下文分析
    
    用我们能拿到的数据(开盘价/开盘第一分钟/首笔)反推竞价意图
    
    Args:
        code: 股票代码
        prev_close: 昨日收盘价
    
    Returns:
        {
            "open_price": float,
            "open_pct": float,        # 开盘涨跌幅%
            "auction_signal": str,     # 竞价信号
            "intensity": "high"/"medium"/"low",
            "fake_warning": bool,      # 是否存在烟雾弹嫌疑
            "detail": str
        }
    """
    bars = _today_1min(code)
    if len(bars) < 2:
        return {"auction_signal": "数据不足", "open_pct": 0, "detail": "数据不足"}

    # 开盘第一根1分K线 = 9:30的K线
    first_bar = None
    for b in bars:
        if b["time"] >= 9 * 3600 + 30 * 60:
            first_bar = b
            break

    if first_bar is None:
        return {"auction_signal": "无开盘数据", "open_pct": 0, "detail": "无9:30数据"}

    open_price = first_bar["open"]
    open_pct = round((open_price / prev_close - 1) * 100, 2) if prev_close > 0 else 0
    first_vol = first_bar["volume"]

    # ── 竞价信号判断 ──
    auction_signal = "中性开盘"
    intensity = "medium"
    fake_warning = False
    details = []

    # 1. 开盘方向
    if open_pct > 2:
        auction_signal = "强势高开"
        details.append(f"高开{open_pct:+.1f}%")
    elif open_pct > 0.5:
        auction_signal = "小幅高开"
        details.append(f"高开{open_pct:+.1f}%")
    elif open_pct < -2:
        auction_signal = "恐慌低开"
        details.append(f"低开{open_pct:+.1f}%")
    elif open_pct < -0.5:
        auction_signal = "小幅低开"
        details.append(f"低开{open_pct:+.1f}%")
    else:
        auction_signal = "平开"
        details.append(f"平开{open_pct:+.1f}%")

    # 2. 开盘第一分钟量 → 竞价比率
    # 第一分钟量包含了集合竞价成交+开盘后第一分钟成交
    # 量大=竞价参与度高, 量小=参与度低
    recent_avg_vol = _recent_avg_1min_vol(bars)
    if recent_avg_vol > 0:
        vol_ratio = first_vol / recent_avg_vol
        if vol_ratio > 5:
            intensity = "high"
            details.append(f"开盘量爆发({vol_ratio:.0f}x均值)")
        elif vol_ratio > 2:
            intensity = "high"
            details.append(f"开盘量放大({vol_ratio:.0f}x均值)")
        elif vol_ratio > 1.2:
            intensity = "medium"
            details.append(f"开盘量正常({vol_ratio:.1f}x均值)")
        else:
            intensity = "low"
            details.append(f"开盘量萎缩({vol_ratio:.1f}x均值)")

    # 3. 虚假高开检测
    if open_pct > 1.5 and intensity == "low":
        fake_warning = True
        auction_signal = "⚠️ 虚假高开"
        details.append("高开但竞价量不足 → 可能9:15大买单9:20撤了 → 警惕回落")
    elif open_pct < -1.5 and intensity == "low":
        fake_warning = True
        auction_signal = "⚠️ 虚假低开"
        details.append("低开但竞价量不足 → 可能烟雾弹诱空 → 关注Spring")

    # 4. 开盘后验证（前5分钟走势）
    first_5 = [b for b in bars if 9 * 3600 + 30 * 60 <= b["time"] <= 9 * 3600 + 35 * 60]
    if len(first_5) >= 2:
        after_price = first_5[-1]["close"]
        after_pct = (after_price - open_price) / open_price * 100
        if after_pct > 0.3:
            details.append(f"开盘后拉升+{after_pct:.1f}%→竞价方向有效")
        elif after_pct < -0.3:
            details.append(f"开盘后回落{after_pct:.1f}%→竞价方向可能失效")

    return {
        "open_price": round(open_price, 2),
        "open_pct": open_pct,
        "auction_signal": auction_signal,
        "intensity": intensity,
        "fake_warning": fake_warning,
        "first_vol": first_vol,
        "detail": " | ".join(details),
    }


def _recent_avg_1min_vol(bars):
    """最近非开盘时段的1分钟平均成交量"""
    # 取9:35之后的K线
    normal_bars = [b for b in bars if b["time"] > 9 * 3600 + 35 * 60]
    if len(normal_bars) < 5:
        normal_bars = bars[-20:]
    if not normal_bars:
        return 0
    return sum(b["volume"] for b in normal_bars) / len(normal_bars)


def score_for_quad_lens(code, prev_close=None):
    """
    为quad_lens提供集合竞价评分
    
    增强开盘区间判断
    """
    if prev_close is None:
        # 尝试从昨天的K线获取
        prev_close = 0

    ctx = auction_context(code, prev_close)

    score = 0
    signals = [ctx.get("detail", "")]

    if ctx.get("fake_warning"):
        score -= 4
        signals.append("⚠️ 烟雾弹嫌疑: 开盘方向不可信")
    elif ctx.get("auction_signal") == "强势高开" and ctx.get("intensity") == "high":
        score = 4
        signals.append("强势高开+大量: 竞价信号强烈看涨")
    elif ctx.get("auction_signal") == "恐慌低开" and ctx.get("intensity") == "high":
        score = -2
        signals.append("恐慌低开+大量: 关注Spring机会")

    return {
        "score": score,
        "detail": " | ".join(signals),
        "auction_signal": ctx.get("auction_signal"),
        "fake_warning": ctx.get("fake_warning"),
    }


def summary(code, prev_close=0):
    """一句话摘要"""
    ctx = auction_context(code, prev_close)
    return f"竞价: {ctx['auction_signal']} ({ctx.get('detail','')[:30]})"


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("--prev", type=float, default=0)
    args = p.parse_args()

    ctx = auction_context(args.code, args.prev or 44)
    print(f"开盘: {ctx['open_pct']:+.1f}%")
    print(f"信号: {ctx['auction_signal']}")
    print(f"强度: {ctx['intensity']}")
    print(f"烟雾弹: {'是' if ctx['fake_warning'] else '否'}")
    print(f"详情: {ctx['detail']}")
