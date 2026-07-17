"""cause_effect.py — 威科夫因果法则目标推演 v1

因(Cause) = 横盘吸筹的力度(天数×区间高度×成交量密度)
果(Effect) = 趋势推进的目标幅度

增强accumulation_detector已有projection:
  - 三级目标(保守/适中/激进)基于cause_strength校准
  - 踏脚石(Stepping Stone)检测
  - 动量生命周期判断(高量启动 vs 低量启动)

联动: accumulation-detector / supply-test / opening-range
"""

import os, json, struct

ROOT = os.path.dirname(os.path.abspath(__file__))


def _get_accumulation_data(code):
    """读取accumulation_detector的状态"""
    acc_file = os.path.join(ROOT, "_accumulation_state.json")
    if not os.path.exists(acc_file): return None
    with open(acc_file, "r", encoding="utf-8") as f:
        try:
            state = json.load(f)
            return state.get(f"a_{code}")
        except:
            return None


def compute_cause_strength(code):
    """
    计算Cause力度
    
    比纯cause_days更精确: 综合考虑天数、区间高度、成交量
    
    Returns:
        {"cause_days": int, "range_height_pct": float,
         "cause_strength": float, "momentum_quality": str}
    """
    acc = _get_accumulation_data(code)
    if acc is None:
        return {"cause_days": 0, "cause_strength": 0, "detail": "无吸筹数据"}

    cause_days = acc.get("cause_days", 0)
    range_low = acc.get("range_low", 0)
    range_high = acc.get("range_high", 0)

    if cause_days == 0 or range_low == 0:
        return {"cause_days": 0, "cause_strength": 0, "detail": "数据不足"}

    range_height = (range_high - range_low) / range_low * 100  # 区间高度%

    # Cause强度 = 天数 × 区间高度% × 成交量因子(简化为1)
    cause_strength = round(cause_days * range_height, 1)

    # 动量质量判断
    if cause_days >= 60 and range_height > 15:
        momentum_quality = "高量启动: 长吸筹+宽区间 → 动量可持续6-12月"
    elif cause_days >= 30 and range_height > 10:
        momentum_quality = "中量启动: 中等吸筹 → 动量可持续3-6月"
    elif cause_days >= 15:
        momentum_quality = "低量启动: 短吸筹 → 动量1-2月内可能衰竭"
    else:
        momentum_quality = "启动不足: 吸筹不充分 → 突破可靠性低"

    return {
        "cause_days": cause_days,
        "range_low": range_low,
        "range_high": range_high,
        "range_height_pct": round(range_height, 1),
        "cause_strength": cause_strength,
        "momentum_quality": momentum_quality,
        "detail": f"Cause: {cause_days}天×{range_height:.1f}%区间 = 强度{cause_strength}",
    }


def project_targets(code, current_price=None):
    """
    三级目标推演 (保守/适中/激进)
    
    Returns:
        {
            "conservative": float, "moderate": float, "aggressive": float,
            "current": float, "dist_to_conservative": float,
            "projection_detail": str
        }
    """
    cause = compute_cause_strength(code)
    if cause.get("cause_days", 0) == 0:
        return {"conservative": 0, "moderate": 0, "aggressive": 0,
                "detail": cause.get("detail", "无数据")}

    rh = cause["range_high"]
    rl = cause["range_low"]
    range_h = rh - rl
    strength = cause["cause_strength"]

    # factor = strength / 100 (标准化)
    factor = max(0.3, min(1.5, strength / 200))
    # 天数越多, 因子越大
    days_factor = min(1.5, cause["cause_days"] / 40)

    conservative = round(rl + range_h * factor * days_factor, 2)
    moderate = round((rl + rh) / 2 + range_h * factor * days_factor * 1.2, 2)
    aggressive = round(rh + range_h * factor * days_factor * 1.5, 2)

    detail = f"保守:{conservative:.1f} | 适中:{moderate:.1f} | 激进:{aggressive:.1f}"
    if current_price:
        if current_price > conservative:
            detail += f" | 当前{current_price:.1f}已过保守目标"
        elif current_price > rh:
            detail += f" | 当前{current_price:.1f}已突破区间"

    return {
        "conservative": conservative,
        "moderate": moderate,
        "aggressive": aggressive,
        "current": current_price,
        "dist_to_conservative": round(conservative - (current_price or 0), 2),
        "factor": round(factor, 2),
        "detail": detail,
    }


def score_for_quad_lens(code, current_price=None):
    """
    为quad_lens提供因果目标评分 (±8分)
    """
    cause = compute_cause_strength(code)
    if cause.get("cause_days", 0) == 0:
        return {"score": 0, "detail": "无吸筹数据", "targets": None}

    targets = project_targets(code, current_price)
    score = 0
    signals = [cause.get("detail", "")]

    # 吸筹充分 → 正分
    if cause.get("cause_days", 0) >= 60:
        score += 4
        signals.append("长吸筹(>60天): 推进基础扎实")
    elif cause.get("cause_days", 0) >= 30:
        score += 2
        signals.append("中等吸筹(>30天)")
    elif cause.get("cause_days", 0) >= 15:
        score += 1

    # 目标空间
    if current_price and targets.get("conservative", 0) > 0:
        space = (targets["conservative"] - current_price) / current_price * 100
        if space > 10:
            score += 4
            signals.append(f"保守目标上方+{space:.0f}%空间")
        elif space > 5:
            score += 2
            signals.append(f"保守目标上方+{space:.0f}%空间")
        elif space > 0:
            score += 1
        else:
            signals.append("已到达保守目标 → 观察是否继续上攻")
            score += 1  # 到达目标本身是正面确认

    # 动量质量
    if "高量启动" in cause.get("momentum_quality", ""):
        score += 2
        signals.append("高量启动模式")
    elif "低量启动" in cause.get("momentum_quality", ""):
        score -= 1
        signals.append("低量启动 → 谨慎")

    return {
        "score": max(-8, min(8, score)),
        "detail": " | ".join(signals),
        "targets": targets,
        "cause": cause,
    }


def summary(code):
    cause = compute_cause_strength(code)
    if cause.get("cause_days", 0) == 0: return ""
    targets = project_targets(code)
    return f"Cause:{cause['cause_days']}天 | 目标:{targets.get('conservative',0):.1f}/{targets.get('moderate',0):.1f}/{targets.get('aggressive',0):.1f}"


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("--price", type=float)
    args = p.parse_args()

    cause = compute_cause_strength(args.code)
    print(f"\n  Cause: {cause.get('detail', '无数据')}")
    print(f"  动量质量: {cause.get('momentum_quality', '')}")

    targets = project_targets(args.code, args.price)
    print(f"\n  🎯 三级目标: {targets.get('detail', '')}")
    print()
