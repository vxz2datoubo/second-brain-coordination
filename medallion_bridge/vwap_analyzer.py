"""vwap_analyzer.py — VWAP/AVWAP分析引擎 v1

VWAP = 机构日内公允价值基准（自我实现的支撑/阻力）
AVWAP = 从事件点锚定的VWAP（事件驱动的成本支撑/阻力）

核心功能:
- compute_vwap(): 从K线数据计算VWAP及标准差带
- compute_avwap(): 从指定锚点计算AVWAP
- analyze(): 综合VWAP分析 → day_type/bias/bands/signals
- score_bias_for_quad_lens(): VWAP偏置放大器 → 影响其他维度评分

联动技能:
  supply-test, absorption-detection, delta-cvd, money-flow-divergence,
  accumulation-detection, breakout-validator

学术基础:
  Zarattini & Aziz (2026), Quantum Algo (2026), Funded Nest (2025),
  Brian Shannon AVWAP, ChartMini VWAP Strategies (2026)
"""

import sys, os, struct, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daytrade_system"))

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vwap_state.json")


# ──────────────────────────────────────────────
#  数据获取
# ──────────────────────────────────────────────

def _tdx_min5(code, limit=50):
    """从通达信5分钟K线文件读取数据"""
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
        bars.append({
            "date": f"{y:04d}{m:02d}{d:02d}", "time": sec,
            "open": op, "high": hi, "low": lo, "close": cl,
            "volume": amt / 100.0,
            "typical": (hi + lo + cl) / 3
        })
    return bars


def _today_bars(code):
    """获取今日5分钟K线"""
    bars = _tdx_min5(code, 200)
    if not bars: return []
    today = bars[-1]["date"]
    return [b for b in bars if b["date"] == today]


# ──────────────────────────────────────────────
#  VWAP 计算
# ──────────────────────────────────────────────

def compute_vwap(bars):
    """
    从K线序列计算VWAP及标准差带
    
    Returns:
        {"vwap": float, "+1sd": float, "-1sd": float,
         "+2sd": float, "-2sd": float, "slope": float,
         "n_bars": int, "total_volume": float}
    """
    if not bars: return None

    cum_pv = 0.0   # 累计 典型价×成交量
    cum_vol = 0.0  # 累计成交量
    cum_pv_sq = 0.0  # 累计 (典型价)² × 成交量

    for b in bars:
        tv = b["volume"] * 100  # 转为股
        tp = b["typical"]
        cum_pv += tp * tv
        cum_pv_sq += (tp ** 2) * tv
        cum_vol += tv

    if cum_vol == 0: return None

    vwap = cum_pv / cum_vol
    # 方差 = E[X²] - E[X]²
    variance = (cum_pv_sq / cum_vol) - (vwap ** 2)
    variance = max(variance, 0.0001)
    sd = variance ** 0.5

    # 斜率: 最近5根 vs 前5根的VWAP变化
    slope = 0
    if len(bars) >= 10:
        first_half = bars[:5]
        second_half = bars[-5:]
        pv1 = sum(b["typical"] * b["volume"] for b in first_half)
        v1 = sum(b["volume"] for b in first_half)
        pv2 = sum(b["typical"] * b["volume"] for b in second_half)
        v2 = sum(b["volume"] for b in second_half)
        if v1 > 0 and v2 > 0:
            v1_val = pv1 / v1
            v2_val = pv2 / v2
            slope = (v2_val - v1_val) / v1_val if v1_val > 0 else 0

    return {
        "vwap": round(vwap, 3),
        "+1sd": round(vwap + sd, 3),
        "-1sd": round(vwap - sd, 3),
        "+2sd": round(vwap + 2 * sd, 3),
        "-2sd": round(vwap - 2 * sd, 3),
        "slope": round(slope, 4),
        "n_bars": len(bars),
        "total_volume": int(cum_vol)
    }


def compute_avwap(bars, anchor_index):
    """从指定索引开始计算AVWAP"""
    if not bars or anchor_index >= len(bars):
        return None
    return compute_vwap(bars[anchor_index:])


# ──────────────────────────────────────────────
#  综合VWAP分析
# ──────────────────────────────────────────────

def analyze(code, current_price):
    """
    综合VWAP分析（含VWAP带、日型判断、偏置方向）
    
    Returns:
        dict:
        - vwap_data: compute_vwap结果
        - price_vs_vwap: "above" / "below" / "at"
        - distance_pct: 距离VWAP的百分比
        - day_type: "trend_up" / "trend_down" / "range" / "reversal" / "unknown"
        - bias: "bullish" / "bearish" / "neutral"
        - bias_amplifier: 偏置放大倍数 (0.5~2.0)
        - signal_quality: 当前价位是否在VWAP语境下有意义的价位
        - ext_level: None / "+2sd" / "-2sd" — 是否在统计延伸位
        - summary: 一句话总结
    """
    bars = _today_bars(code)
    if len(bars) < 5:
        return {
            "vwap_data": None, "price_vs_vwap": "unknown",
            "day_type": "unknown", "bias": "neutral",
            "bias_amplifier": 1.0, "signal_quality": "low",
            "summary": "数据不足(需≥5根5分K线)"
        }

    vwap_data = compute_vwap(bars)
    if vwap_data is None:
        return {
            "vwap_data": None, "price_vs_vwap": "unknown",
            "day_type": "unknown", "bias": "neutral",
            "bias_amplifier": 1.0, "signal_quality": "low",
            "summary": "VWAP计算失败"
        }

    vwap = vwap_data["vwap"]
    dist_pct = round((current_price / vwap - 1) * 100, 2)

    # ── 价格相对VWAP位置 ──
    if dist_pct > 0.3:
        price_vs = "above"
    elif dist_pct < -0.3:
        price_vs = "below"
    else:
        price_vs = "at"

    # ── 是否在统计延伸位 ──
    ext_level = None
    if current_price >= vwap_data["+2sd"]:
        ext_level = "+2sd"
    elif current_price <= vwap_data["-2sd"]:
        ext_level = "-2sd"
    elif current_price >= vwap_data["+1sd"]:
        ext_level = "+1sd"
    elif current_price <= vwap_data["-1sd"]:
        ext_level = "-1sd"

    # ── 日型判断 ──
    day_type = "unknown"
    if len(bars) >= 10:
        # 用前半段和后半段的VWAP变化判断
        first_vwap = compute_vwap(bars[:max(5, len(bars)//2)])
        last_vwap_data = compute_vwap(bars[-max(5, len(bars)//2):])
        if first_vwap and last_vwap_data:
            vwap_change = (last_vwap_data["vwap"] - first_vwap["vwap"]) / first_vwap["vwap"]

            # 检查价格是否一直单边
            prices = [b["close"] for b in bars]
            first_price = prices[0]
            last_price = prices[-1]
            mid_price = prices[len(prices)//2]
            total_move = abs(last_price - first_price) / first_price

            # 检查是否反复穿越VWAP
            crosses = 0
            above = False
            for b in bars:
                is_above = b["close"] > vwap
                if above != is_above:
                    crosses += 1
                    above = is_above
            crosses //= 2  # 每次进出算一次

            if crosses <= 1 and total_move > 0.01:
                # 单边运行
                if last_price > first_price:
                    day_type = "trend_up"
                else:
                    day_type = "trend_down"
            elif crosses >= 3:
                day_type = "range"
            elif crosses == 2 and total_move > 0.01:
                day_type = "reversal"

    # ── 偏置方向 ──
    if day_type in ("trend_up",) or (price_vs == "above" and vwap_data["slope"] > 0):
        bias = "bullish"
    elif day_type in ("trend_down",) or (price_vs == "below" and vwap_data["slope"] < 0):
        bias = "bearish"
    else:
        bias = "neutral"

    # ── 偏置放大器 ──
    amplifier = 1.0
    if bias == "bullish" and price_vs == "above":
        amplifier = 1.5 if dist_pct < 2 else 1.2  # 小偏离=趋势确认，大偏离=可能反转
    elif bias == "bearish" and price_vs == "below":
        amplifier = 1.5 if dist_pct > -2 else 1.2
    elif ext_level in ("+2sd", "-2sd"):
        amplifier = 0.7  # 统计延伸 → 均值回归偏置 → 降低顺势权重
    elif day_type == "range":
        amplifier = 0.8  # 震荡日 → 信号质量打折

    # ── 价位质量 ──
    signal_quality = "medium"
    if ext_level in ("+2sd", "-2sd"):
        signal_quality = "high"  # 统计延伸位 → 高概率事件
    elif abs(dist_pct) < 0.3:
        signal_quality = "high"  # 在VWAP上 → 最重要的价位
    elif abs(dist_pct) < 1.0:
        signal_quality = "medium"
    else:
        signal_quality = "low"

    # ── 保存状态 ──
    _save_state(code, {
        "vwap": vwap, "dist_pct": dist_pct,
        "day_type": day_type, "bias": bias,
        "timestamp": datetime.now().strftime("%H:%M")
    })

    # ── 一句话总结 ──
    if day_type == "trend_up":
        summary = f"📈 趋势上涨日: 价格{dist_pct:+.1f}% vs VWAP→多方领地, 顺势做多"
    elif day_type == "trend_down":
        summary = f"📉 趋势下跌日: 价格{dist_pct:+.1f}% vs VWAP→空方领地, 顺势做空"
    elif day_type == "range":
        summary = f"🔄 震荡日: 价格{dist_pct:+.1f}% vs VWAP→均值回归策略, ±1 SD区间操作"
    elif day_type == "reversal":
        summary = f"🔀 反转日: 价格{dist_pct:+.1f}% vs VWAP→VWAP已翻转, 新方向确认中"
    elif ext_level in ("+2sd", "-2sd"):
        summary = f"⚡ 统计延伸({ext_level}): 价格{dist_pct:+.1f}% vs VWAP→高概率回归"
    elif abs(dist_pct) < 0.3:
        summary = f"🎯 在VWAP上: 机构公允价值位, 决定性区域"
    else:
        summary = f"价格{dist_pct:+.1f}% vs VWAP, {bias}偏置"

    return {
        "vwap_data": vwap_data,
        "price_vs_vwap": price_vs,
        "distance_pct": dist_pct,
        "day_type": day_type,
        "bias": bias,
        "bias_amplifier": amplifier,
        "signal_quality": signal_quality,
        "ext_level": ext_level,
        "summary": summary
    }


def score_bias_for_quad_lens(code):
    """
    为quad_lens.py提供VWAP偏置放大器
    
    VWAP不独立计分，而是作为其他维度的权重乘数。
    返回的amplifier用于调整：供应测试/CVD/突破的评分。
    
    Returns:
        {"amplifier": float, "bias": str, "day_type": str, "note": str}
    """
    state = _load_state()
    key = f"v_{code}"
    if key not in state:
        return {"amplifier": 1.0, "bias": "neutral", "day_type": "unknown",
                "note": "无VWAP数据"}

    entry = state[key]
    bias = entry.get("bias", "neutral")
    day_type = entry.get("day_type", "unknown")

    if bias == "bullish":
        amp = 1.5
        note = "VWAP多头偏置: 做多信号评分×1.5, 做空信号×0.7"
    elif bias == "bearish":
        amp = 1.5
        note = "VWAP空头偏置: 做空信号评分×1.5, 做多信号×0.7"
    else:
        amp = 1.0
        note = "VWAP中性: 无偏置"

    if day_type == "range":
        amp = 0.8
        note = "震荡日: 信号质量打折×0.8, 均值回归优先"

    return {
        "amplifier": amp,
        "bias": bias,
        "day_type": day_type,
        "note": note
    }


# ──────────────────────────────────────────────
#  联动函数
# ──────────────────────────────────────────────

def vwap_context_for_absorption(vwap_result):
    """
    为吸收检测提供VWAP语境
    
    Args:
        vwap_result: analyze()的返回值
    
    Returns:
        {"on_vwap": bool, "context_note": str}
    """
    if vwap_result is None or vwap_result["vwap_data"] is None:
        return {"on_vwap": False, "context_note": "无法获取VWAP语境"}

    dist = abs(vwap_result["distance_pct"])
    if dist < 0.3:
        return {"on_vwap": True, "context_note": "🎯 吸收发生在VWAP上 → 机构行为,置信度最高"}
    elif dist < 1.0:
        return {"on_vwap": False, "context_note": f"吸收距VWAP {dist:.1f}% → 一般价位"}
    else:
        return {"on_vwap": False, "context_note": f"吸收距VWAP {dist:.1f}% → 远离公允价值,信号打折"}


def vwap_context_for_supply_test(vwap_result):
    """
    为供应测试提供VWAP语境
    
    Returns:
        {"near_vwap": bool, "boost": int, "note": str}
    """
    if vwap_result is None or vwap_result["vwap_data"] is None:
        return {"near_vwap": False, "boost": 0, "note": ""}

    dist = vwap_result["distance_pct"]
    # 价格在VWAP下方做供应测试 → 机构在折价区测试抛压 → 非常健康
    if -2 < dist < -0.3:
        return {"near_vwap": True, "boost": 8,
                "note": "供应测试在VWAP下方(折价区) → 主力在机构公允价值下方试探抛压,非常健康"}
    elif abs(dist) < 0.3:
        return {"near_vwap": True, "boost": 5,
                "note": "供应测试在VWAP上 → 公允价值位测试,信号可靠"}
    elif dist > 2:
        return {"near_vwap": False, "boost": -3,
                "note": f"价格距VWAP+{dist:.1f}%(溢价区) → 高位供应测试,风险增大"}
    return {"near_vwap": False, "boost": 0, "note": ""}


def vwap_context_for_breakout(vwap_result):
    """
    为突破验证提供VWAP语境
    
    Returns:
        {"vwap_confirmed": bool, "note": str}
    """
    if vwap_result is None or vwap_result["vwap_data"] is None:
        return {"vwap_confirmed": False, "note": ""}

    dist = vwap_result["distance_pct"]
    bias = vwap_result["bias"]
    day_type = vwap_result["day_type"]

    if day_type in ("trend_up",) and bias == "bullish" and dist > 0.3:
        return {"vwap_confirmed": True,
                "note": "趋势上涨日+VWAP上方 → 突破信号质量增强"}
    elif vwap_result.get("ext_level") in ("+2sd",):
        return {"vwap_confirmed": False,
                "note": f"价格在{ext_level}→ 统计延伸位,突破可能是假突破"}
    return {"vwap_confirmed": False, "note": ""}


# ──────────────────────────────────────────────
#  状态持久化
# ──────────────────────────────────────────────

def _load_state():
    if not os.path.exists(STATE_FILE): return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return {}

def _save_state(code, data):
    state = _load_state()
    state[f"v_{code}"] = data
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def summary(code):
    """一句话VWAP摘要"""
    state = _load_state()
    key = f"v_{code}"
    if key not in state: return ""
    e = state[key]
    return f"VWAP@{e['vwap']} ({e['dist_pct']:+.1f}%) {e['day_type']} {e['bias']}"


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("price", type=float)
    args = p.parse_args()

    result = analyze(args.code, args.price)

    print(f"\n{'='*50}")
    print(f"  📊 VWAP分析 — {args.code} @ {args.price}")
    print(f"{'='*50}")
    if result["vwap_data"]:
        d = result["vwap_data"]
        print(f"  VWAP: {d['vwap']} | +1SD:{d['+1sd']} | +2SD:{d['+2sd']}")
        print(f"                | -1SD:{d['-1sd']} | -2SD:{d['-2sd']}")
        print(f"  斜率: {d['slope']:+.4f} | 总成交量: {d['total_volume']:,}股")
    print(f"  相对位置: {result['distance_pct']:+.2f}%")
    print(f"  日型: {result['day_type']}")
    print(f"  偏置: {result['bias']} (放大器: ×{result['bias_amplifier']})")
    print(f"  延伸: {result['ext_level'] or '无'}")
    print(f"  信号质量: {result['signal_quality']}")
    print(f"  总结: {result['summary']}")
    print()
