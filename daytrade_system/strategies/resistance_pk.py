"""
P层穿越PK — 动能 vs 修正阻力 胜率预估

核心公式:
  穿越胜率% = 动能分/100 - 修正阻力%/20
  
解读:
  动能强 + 阻力虚 → 高胜率(>60%) → 🟢 放心卖这个位置
  动能弱 + 阻力实 → 低胜率(<20%) → 🔴 这里卖绝对穿不过去
  中性           → 30-50%      → 🟡 看情况

联动:
  - momentum_analyzer: 获取实时动能分
  - crossover_tracker: 获取修正后阻力(adjusted_pct)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.crossover_tracker import adjusted_profile
from strategies.momentum_analyzer import MomentumScore


def pk_resistance(momentum: MomentumScore, code: str, current_price: float,
                  days: int = 5) -> dict:
    """
    动能 vs 每个P层 穿越胜率PK

    返回: {
        "levels": [{level, pct, adjusted_pct, cross_label, win_rate, signal}, ...],
        "summary": 一句话总结
    }
    """
    prof = adjusted_profile(code, current_price, days)
    resistance = [p for p in prof if p["side"] == "resistance"]

    # 调整公式: 让胜率数字更合理
    # 基础胜率 = 动能分/100(动能越强基础越高)
    # 减分 = (1 - modifier) * 50(阻力虚→扣分少, 阻力实→扣分多)

    levels = []
    for r in resistance:
        base_rate = momentum.total / 100
        resistance_penalty = (1 - r["modifier"]) * 50
        win_rate = round(max(0, min(95, base_rate * 100 - resistance_penalty)))

        if win_rate >= 60:
            signal = f"🟢 大概率穿越({win_rate}%)"
        elif win_rate >= 35:
            signal = f"🟡 可能穿越({win_rate}%)"
        elif win_rate >= 15:
            signal = f"🟠 穿越困难({win_rate}%)"
        else:
            signal = f"🔴 几乎不可能({win_rate}%)"

        levels.append({
            "level": r["level"],
            "label": r["label"],
            "pct": r["pct"],
            "adjusted_pct": r["adjusted_pct"],
            "modifier": r["modifier"],
            "cross_label": r["cross_label"],
            "win_rate": win_rate,
            "signal": signal,
        })

    # 找最近的阻力层
    nearest = levels[0] if levels else None
    if nearest:
        if nearest["win_rate"] >= 50:
            summary = f"最近阻力{nearest['label']} 穿越胜率{nearest['win_rate']}% → 不建议在此卖出"
        else:
            summary = f"最近阻力{nearest['label']} 穿越胜率{nearest['win_rate']}% → 此处卖出安全"
    else:
        summary = "无阻力层数据"

    return {"levels": levels, "summary": summary}


def format_pk_report(pk_result: dict, momentum: MomentumScore) -> str:
    """格式化PK报告"""
    lines = []
    lines.append(f"  ⚡ 动能{int(momentum.total)}/100 {momentum.label}")
    lines.append(f"  🎯 P层穿越胜率PK:")

    for r in pk_result["levels"][:5]:
        bl = int(r["adjusted_pct"] * 3)
        br = '▓' * min(bl, 50) + ' ·' * max(0, 50 - bl)
        lines.append(f"  {r['level']:>3} {r['label']:>12} |{br}| {r['pct']:.1f}%→{r['adjusted_pct']:.1f}% | {r['signal']}")

    lines.append(f"  {'─'*53}")
    lines.append(f"  📋 {pk_result['summary']}")

    return "\n".join(lines)


if __name__ == "__main__":
    from strategies.momentum_analyzer import calc_momentum
    # 用实时数据测试
    m = calc_momentum("300418", 40.99, 40.00, 40.56, 41.50, 39.62, 1.1, 215689, 228089)
    pk = pk_resistance(m, "300418", 40.99)
    print(format_pk_report(pk, m))
