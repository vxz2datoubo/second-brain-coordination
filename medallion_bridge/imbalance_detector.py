"""imbalance_detector.py — 订单流失衡(Imbalance/OFI)检测 v1

三层失衡:
  1. 单K失衡 → delta_cvd.py 已覆盖
  2. OFI序列 → 外盘/内盘比值的趋势、速度、加速度
  3. VSA量价失衡 → 成交量vs价格波幅的关系

与Footprint的区别:
  Footprint看一根K线内部的价位级失衡(需要Level 2)
  Imbalance看K线之间的买卖力量偏离(用Level 1即可)

联动: supply-test / absorption-detection / delta-cvd / footprint-detection
"""

import json, os
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))


def _load_delta_state():
    cvd_file = os.path.join(ROOT, "_delta_state.json")
    if not os.path.exists(cvd_file): return {}
    with open(cvd_file, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return {}


# ──────────────────────────────────────────────
#  OFI 序列分析
# ──────────────────────────────────────────────

def ofi_sequence(code):
    """
    从delta_cvd历史计算OFI序列
    
    OFI = (外盘 - 内盘) / (外盘 + 内盘)
    归一化[-1, +1]: +1=纯粹买方, -1=纯粹卖方, 0=完全均衡
    
    Returns:
        {
            "ofi_current": float,     # 当前OFI值
            "ofi_velocity": float,    # OFI速度 (5周期变化)
            "ofi_accel": float,       # OFI加速度
            "ofi_trend": "加速买"/"减速买"/"加速卖"/"减速卖"/"均衡",
            "health": "healthy"/"warning"/"danger",
            "detail": str
        }
    """
    state = _load_delta_state()
    key = f"d_{code}"
    if key not in state:
        return {"ofi_current": 0, "ofi_velocity": 0, "ofi_accel": 0,
                "ofi_trend": "无数据", "health": "warning", "detail": "无数据"}

    h = state[key].get("history", [])
    if len(h) < 10:
        return {"ofi_current": 0, "ofi_velocity": 0, "ofi_accel": 0,
                "ofi_trend": "数据不足", "health": "warning", "detail": "数据不足"}

    # 计算每对采样点的OFI
    ofi_values = []
    for i in range(1, len(h)):
        d = h[i]["d"]  # Delta = 本次外盘-内盘
        # 用Delta近似OFI(绝对值归一化)
        max_vol = max(abs(d), 1000)
        ofi = max(-1.0, min(1.0, d / max_vol * 2))
        ofi_values.append(ofi)

    current = ofi_values[-1]
    # OFI速度: 最近5个 vs 前5个的均值差
    velocity = 0
    accel = 0
    if len(ofi_values) >= 10:
        recent5 = sum(ofi_values[-5:]) / 5
        prev5 = sum(ofi_values[-10:-5]) / 5
        velocity = recent5 - prev5
        if len(ofi_values) >= 15:
            prev_velocity = (sum(ofi_values[-10:-5]) / 5) - (sum(ofi_values[-15:-10]) / 5)
            accel = velocity - prev_velocity

    # 趋势判断
    if current > 0.2 and velocity > 0:
        trend = "加速买" if accel > 0 else "减速买"
        health = "healthy" if accel > 0 else "warning"
    elif current > 0.2 and velocity < 0:
        trend = "减速买"
        health = "warning"
    elif current < -0.2 and velocity < 0:
        trend = "加速卖" if accel < 0 else "减速卖"
        health = "healthy" if accel < 0 else "warning"
    elif current < -0.2 and velocity > 0:
        trend = "减速卖"
        health = "warning"
    else:
        trend = "均衡"
        health = "warning"

    detail = f"OFI:{current:+.2f} 速度:{velocity:+.2f} 加速度:{accel:+.2f} → {trend}"

    return {
        "ofi_current": round(current, 3),
        "ofi_velocity": round(velocity, 3),
        "ofi_accel": round(accel, 3),
        "ofi_trend": trend,
        "health": health,
        "detail": detail
    }


# ──────────────────────────────────────────────
#  VSA 量价失衡
# ──────────────────────────────────────────────

def vsa_imbalance(code, current_price):
    """
    Volume Spread Analysis 量价失衡
    
    成交量和价格波幅的4象限关系
    
    Returns:
        {"vsa_type": str, "vsa_confidence": int, "detail": str}
    """
    state = _load_delta_state()
    key = f"d_{code}"
    if key not in state:
        return {"vsa_type": "无数据", "vsa_confidence": 0, "detail": "无数据"}

    h = state[key].get("history", [])
    if len(h) < 5:
        return {"vsa_type": "数据不足", "vsa_confidence": 0, "detail": "数据不足"}

    recent = h[-3:]
    prices = [x["p"] for x in recent]
    price_change = prices[-1] - prices[0]
    price_spread = max(prices) - min(prices)
    deltas = [x["d"] for x in recent]
    total_delta = sum(abs(x) for x in deltas)

    body = abs(price_change)
    vol = total_delta
    spread_pct = price_spread / max(current_price, 0.01)

    vsa_type = "均衡"
    confidence = 0

    # 高努力(大成交量) + 高结果(大波幅) = 真实推动
    if vol > 5000 and spread_pct > 0.005:
        if price_change > 0:
            vsa_type = "需求失衡(真实推动上升)"
            confidence = 70
        else:
            vsa_type = "供给失衡(真实推动下跌)"
            confidence = 70
    # 高努力(大成交量) + 低结果(小波幅) = 吸收
    elif vol > 5000 and spread_pct < 0.003:
        vsa_type = "努力无结果(吸收)"
        confidence = 60
    # 低努力(小成交量) + 高结果(大波幅) = 低流动性漂移
    elif vol < 2000 and spread_pct > 0.005:
        vsa_type = "低流动性漂移(警惕假突破)"
        confidence = 40
    # 低努力 + 低结果 = 无效
    elif vol < 2000 and spread_pct < 0.003:
        vsa_type = "无效波动(观望)"
        confidence = 30

    return {
        "vsa_type": vsa_type,
        "vsa_confidence": confidence,
        "detail": f"量:{vol:.0f} 幅:{spread_pct:.2%} → {vsa_type}"
    }


# ──────────────────────────────────────────────
#  联动函数
# ──────────────────────────────────────────────

def imbalance_context_for_supply_test(code):
    """
    为供应测试提供OFI语境
    
    Returns: {"boost": int, "note": str}
    """
    ofi = ofi_sequence(code)
    vsa = vsa_imbalance(code, 0)

    boost = 0
    notes = []

    # OFI从负转正 = 卖方力量消退 + 买方回来 = 供应测试最强确认
    if ofi["ofi_current"] > 0 and ofi["ofi_velocity"] > 0:
        boost += 6
        notes.append("OFI加速转正: 买方力量在增强, 供应测试可信度↑")
    elif ofi["ofi_current"] > 0:
        boost += 3
        notes.append("OFI为正: 买方占优, 供应测试基本可信")
    elif ofi["ofi_current"] < -0.2 and ofi["ofi_velocity"] < 0:
        boost -= 3
        notes.append("OFI加速转负: 卖方力量增强, 供应测试可能假通过")

    if vsa["vsa_type"] == "努力无结果(吸收)":
        boost += 3
        notes.append(f"VSA吸收: {vsa['detail']}")

    return {"boost": boost, "note": " | ".join(notes) if notes else ""}


def score_for_quad_lens(code):
    """
    为quad_lens提供OFI评分 (-8~+8)
    
    OFI是趋势燃料检测，不像重量级维度(供应测试40分)那么重
    """
    ofi = ofi_sequence(code)

    score = 0
    signals = []

    c = ofi["ofi_current"]
    v = ofi["ofi_velocity"]
    a = ofi["ofi_accel"]

    # 方向分 ±4
    if c > 0.3:
        score += 4
        signals.append("强烈买方OFI")
    elif c > 0.1:
        score += 2
        signals.append("温和买方OFI")
    elif c < -0.3:
        score -= 4
        signals.append("强烈卖方OFI")
    elif c < -0.1:
        score -= 2
        signals.append("温和卖方OFI")

    # 动量分 ±4
    if v > 0.1:
        score += 2
        signals.append("OFI加速上升")
    elif v < -0.1:
        score -= 2
        signals.append("OFI加速下降")

    if a > 0.05:
        score += 2
        signals.append("正加速度(趋势增强)")
    elif a < -0.05:
        score -= 2
        signals.append("负加速度(趋势衰减)")

    score = max(-8, min(8, score))
    detail = " | ".join(signals) if signals else "OFI均衡"

    return {"score": score, "detail": detail, "signals": signals,
            "ofi_current": c, "ofi_trend": ofi["ofi_trend"]}


def summary(code):
    """一句话OFI摘要"""
    ofi = ofi_sequence(code)
    return f"OFI:{ofi['ofi_current']:+.2f} {ofi['ofi_trend']}"


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    args = p.parse_args()

    print(f"\n{'='*50}")
    print(f"  📊 OFI订单流失衡 — {args.code}")
    print(f"{'='*50}")

    ofi = ofi_sequence(args.code)
    print(f"  OFI: {ofi['ofi_current']:+.3f}")
    print(f"  速度: {ofi['ofi_velocity']:+.3f}")
    print(f"  加速度: {ofi['ofi_accel']:+.3f}")
    print(f"  趋势: {ofi['ofi_trend']}")
    print(f"  健康度: {ofi['health']}")

    vsa = vsa_imbalance(args.code, 0)
    print(f"\n  VSA量价: {vsa['detail']}")

    ctx = imbalance_context_for_supply_test(args.code)
    print(f"\n  供应测试联动: {ctx['boost']:+d} — {ctx['note']}")

    sc = score_for_quad_lens(args.code)
    print(f"\n  quad_lens评分: {sc['score']:+d} — {sc['detail']}")
    print()
