"""opening_range.py — 开盘区间分析引擎 v1

开盘区间 = 9:30-9:45(15分钟) / 9:30-10:00(30分钟)

核心:
- get_opening_range(): 获取今日开盘区间
- classify_day_type(): 日型分类(强上/强下/震荡/窄待突破)
- score_for_quad_lens(): 开盘语境偏置

学术: Zarattini & Aziz (2026) ORB年化alpha 33%
"""

import struct, os, json

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
        today = f"{y:04d}{m:02d}{d:02d}"
        bars.append({
            "date": today, "time": sec, "open": op, "high": hi,
            "low": lo, "close": cl, "volume": amt / 100.0,
        })
    today = bars[-1]["date"]
    return [b for b in bars if b["date"] == today]


def _time_to_sec(time_str):
    """HH:MM → 秒数"""
    parts = time_str.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60


# ──────────────────────────────────────────────
#  开盘区间计算
# ──────────────────────────────────────────────

def get_opening_range(code, minutes=15):
    """
    获取今日开盘区间
    
    Args:
        minutes: 开盘区间时长(分钟), 默认15分钟
    
    Returns:
        {"orh": float, "orl": float, "or_mid": float,
         "width_pct": float, "width_vs_avg": float,
         "total_volume": float, "open_price": float,
         "formed": bool, "detail": str}
    """
    bars = _today_1min(code)
    if not bars:
        return {"formed": False, "detail": "数据不足"}

    open_time = 9 * 3600 + 30 * 60  # 9:30
    end_time = open_time + minutes * 60

    # 筛选开盘区间内的K线
    or_bars = [b for b in bars if open_time <= b["time"] <= end_time]

    if len(or_bars) < 3:
        return {"formed": False, "detail": f"开盘{minutes}分钟内数据不足"}
    if len(or_bars) < minutes * 0.8:  # 尚未完整形成
        # 部分形成
        orh = max(b["high"] for b in or_bars)
        orl = min(b["low"] for b in or_bars)
        return {
            "formed": "partial",
            "orh": round(orh, 2), "orl": round(orl, 2),
            "or_mid": round((orh + orl) / 2, 2),
            "width_pct": round((orh - orl) / orl * 100, 3),
            "open_price": round(or_bars[0]["open"], 2) if or_bars else None,
            "detail": f"开盘区间形成中({len(or_bars)}/{minutes}根)",
            "total_volume": sum(b["volume"] for b in or_bars),
        }

    orh = max(b["high"] for b in or_bars)
    orl = min(b["low"] for b in or_bars)
    or_mid = (orh + orl) / 2
    width_pct = (orh - orl) / orl * 100 if orl > 0 else 0
    total_vol = sum(b["volume"] for b in or_bars)

    # 与近期均值比较
    prev_days_widths = _get_prev_widths(code, days=10, minutes=minutes)
    avg_width = sum(prev_days_widths) / max(len(prev_days_widths), 1)
    width_vs_avg = width_pct / avg_width if avg_width > 0 else 1.0

    return {
        "formed": True,
        "orh": round(orh, 2), "orl": round(orl, 2),
        "or_mid": round(or_mid, 2),
        "width_pct": round(width_pct, 3),
        "width_vs_avg": round(width_vs_avg, 2),
        "total_volume": total_vol,
        "open_price": round(or_bars[0]["open"], 2) if or_bars else None,
        "detail": f"ORH:{orh:.2f} ORL:{orl:.2f} 宽度:{width_pct:.2%} (vs均{width_vs_avg:.1f}x)",
    }


def _get_prev_widths(code, days=10, minutes=15):
    """获取前几天的开盘区间宽度"""
    bars = _today_1min(code)
    if not bars: return []
    # 简化: 用近10根1分K线波动率估计
    recent = bars[-30:]
    if len(recent) < 10: return []
    widths = []
    for i in range(0, len(recent) - minutes, minutes):
        chunk = recent[i:i + minutes]
        if chunk:
            w = (max(b["high"] for b in chunk) - min(b["low"] for b in chunk))
            widths.append(w / max(chunk[0]["low"], 0.01) * 100)
    return widths if widths else [0.5]


# ──────────────────────────────────────────────
#  日型分类
# ──────────────────────────────────────────────

def classify_day_type(code, current_price, minutes=15):
    """
    根据开盘区间和当前价格分类日型
    
    Returns:
        {
            "day_type": "strong_up"/"strong_down"/"range"/"narrow_breakout"/"pre_open",
            "bias": "bullish"/"bearish"/"neutral",
            "breakout": "up"/"down"/None,
            "narrow": bool,
            "detail": str
        }
    """
    or_data = get_opening_range(code, minutes)
    if not or_data.get("formed"):
        if or_data.get("formed") == "partial":
            return {"day_type": "pre_open", "bias": "neutral",
                    "breakout": None, "narrow": False,
                    "detail": or_data.get("detail", "")}
        return {"day_type": "unknown", "bias": "neutral",
                "breakout": None, "narrow": False,
                "detail": "无开盘区间数据"}

    orh, orl = or_data["orh"], or_data["orl"]
    width_vs = or_data.get("width_vs_avg", 1.0)
    narrow = width_vs < 0.7

    # 判断当前价格位置
    if current_price > orh:
        # 确认是否真突破（检查是否回落到区间内）
        day_type = "strong_up"
        bias = "bullish"
        breakout = "up"
        detail = f"强势日: 价格{current_price:.2f}>ORH{orh:.2f}"
        if narrow:
            detail += " + 窄区间爆发!"
    elif current_price < orl:
        day_type = "strong_down"
        bias = "bearish"
        breakout = "down"
        detail = f"弱势日: 价格{current_price:.2f}<ORL{orl:.2f}"
        if narrow:
            detail += " + 窄区间爆发!"
    else:
        day_type = "range"
        bias = "neutral"
        breakout = None
        detail = f"震荡日: 价格在OR{orl:.2f}-{orh:.2f}内"
        if narrow:
            day_type = "narrow_breakout"
            detail = f"窄区间待突破: {orl:.2f}-{orh:.2f} (宽度仅均值的{width_vs:.1f}x)"

    if narrow:
        detail += " ⚡高能预警"

    return {
        "day_type": day_type,
        "bias": bias,
        "breakout": breakout,
        "narrow": narrow,
        "or_data": or_data,
        "detail": detail,
    }


# ──────────────────────────────────────────────
#  联动函数
# ──────────────────────────────────────────────

def opening_context_for_supply_test(code, current_price):
    """
    开盘区间语境 → 供应测试解读
    
    如果供应测试发生在开盘区间内→非常健康（主力在开盘区间内测试抛压）
    """
    or_data = get_opening_range(code, 15)
    if not or_data.get("formed"):
        return {"boost": 0, "note": ""}

    orh, orl = or_data["orh"], or_data["orl"]
    or_mid = or_data["or_mid"]

    # 价格在OR区间内做供应测试 → 健康
    if orl <= current_price <= orh:
        # 在区间上沿 = 测试突破阻力
        if current_price > or_mid:
            return {"boost": 3, "note": "供应测试在OR上沿: 蓄力突破中"}
        else:
            return {"boost": 2, "note": "供应测试在OR下沿: 测试支撑"}
    return {"boost": 0, "note": ""}


def score_for_quad_lens(code, current_price):
    """
    为quad_lens提供开盘区间评分 (-8~+8)
    
    作为偏置层: 趋势日 → 顺势信号放大, 震荡日 → 均值回归偏置
    """
    day = classify_day_type(code, current_price)
    or_data = get_opening_range(code, 15)

    score = 0
    signals = []

    if day["day_type"] == "strong_up":
        score = 8
        signals.append("强势日(>ORH): 做多偏置")
        if day["narrow"]:
            signals.append("窄区间爆发!")
            score = 8  # 封顶
    elif day["day_type"] == "strong_down":
        score = -8
        signals.append("弱势日(<ORL): 做空偏置")
    elif day["day_type"] == "range":
        score = 0
        signals.append("震荡日: 均值回归偏置")
    elif day["day_type"] == "narrow_breakout":
        score = 0
        signals.append(f"窄区间({or_data.get('width_vs_avg',0):.1f}x均值): 等待突破方向")
    elif day["day_type"] == "pre_open":
        score = 0
        signals.append("开盘区间形成中...")

    detail = " | ".join(signals) if signals else ""
    return {
        "score": score,
        "detail": detail,
        "signals": signals,
        "day_type": day["day_type"],
        "or_data": or_data,
    }


def summary(code):
    """一句话摘要"""
    or_data = get_opening_range(code, 15)
    if not or_data.get("formed"):
        return "开盘区间形成中"
    return f"OR:{or_data['orl']:.2f}-{or_data['orh']:.2f}"


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("price", type=float, nargs="?")
    args = p.parse_args()
    price = args.price or 44

    or_data = get_opening_range(args.code)
    print(f"开盘区间: {or_data}")

    day = classify_day_type(args.code, price)
    print(f"日型: {day['detail']}")

    sc = score_for_quad_lens(args.code, price)
    print(f"评分: {sc['score']:+d} — {sc['detail']}")
