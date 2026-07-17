"""
换手率深度分析引擎 v1 — 波仔交易系统

核心功能:
  1. 阶段×换手交互: 低位放量=建仓, 高位放量=出货
  2. 量×量分类: 换手率+量比双维度判断真实性
  3. 阻力突破质量: 换手率+效率判断过压力带真伪
  4. 周期检测: 建仓→拉升→高位换手→出货收缩
  5. 次日预测: 历史换手率区间→次日涨跌统计

联动模块:
  - volume_profile.py: 阻力/支撑带
  - volume_efficiency.py: 量价效率(硬/软阻力)
  - trend_classifier.py: 趋势状态
  - daily_analyzer.py: 日线趋势
  - entry_scorer.py: 入市评分卡

设计原则:
  - 所有输出可交叉引用其他模块的结果
  - 不做孤立分析, 一定关联价格/趋势/阻力
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.tdx_parser import read_daily_kline, read_minute_kline, group_by_date
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict


# ============================================================
# 换手率阈值表 (基于昆仑/蓝标近一年统计)
# ============================================================

TURNOVER_THRESHOLDS = {
    "300418": {  # 昆仑万维
        "very_low": 2.0,   # <2% 极低
        "low": 4.0,        # 2-4% 偏低
        "normal": 8.0,     # 4-8% 正常
        "high": 15.0,      # 8-15% 活跃
        "extreme": 15.0,   # >15% 极端
    },
    "300058": {  # 蓝色光标
        "very_low": 1.0,
        "low": 3.0,
        "normal": 6.0,
        "high": 12.0,
        "extreme": 12.0,
    },
}

# 默认阈值 (未知股票)
DEFAULT_THRESHOLDS = {
    "very_low": 1.5, "low": 3.0, "normal": 6.0, "high": 12.0, "extreme": 12.0,
}


def get_thresholds(code: str) -> dict:
    return TURNOVER_THRESHOLDS.get(code, DEFAULT_THRESHOLDS)


# ============================================================
# 1. 基础数据层: 历史换手率计算
# ============================================================

def compute_daily_turnover(code: str, ltgb: float = None) -> dict:
    """
    从日K线推算历史换手率序列

    ltgb: 流通股本(万股), 从 ExtInfo.LTGB 获取
          如果未提供则从config推断

    返回: {
        "series": [{date, turnover, ma5, ma20, percentile}, ...],
        "current": 最新换手率,
        "current_pct": 近120天分位,
        "trend": 趋势标签,
    }
    """
    if code.startswith(("6", "5")):
        path = f"F:/tongdaxin/vipdoc/sh/lday/sh{code}.day"
    else:
        path = f"F:/tongdaxin/vipdoc/sz/lday/sz{code}.day"

    bars = read_daily_kline(path)
    if not bars or len(bars) < 30:
        return {"series": [], "current": 0, "current_pct": 50, "trend": "无数据"}

    # 默认LTGB (如果没有实时数据)
    if ltgb is None:
        ltgb = 117532 if code == "300418" else 347793  # 昆仑/蓝标流通股本(万股)

    # 计算每日换手率
    series = []
    for b in bars:
        turnover = (b.volume / (ltgb * 10000)) * 100
        series.append({
            "date": str(b.date),
            "turnover": round(turnover, 2),
            "price": b.close,
            "volume": b.volume,
        })

    # MA5, MA20
    for i in range(len(series)):
        if i >= 4:
            series[i]["ma5"] = round(sum(s["turnover"] for s in series[i-4:i+1]) / 5, 2)
        else:
            series[i]["ma5"] = series[i]["turnover"]
        if i >= 19:
            series[i]["ma20"] = round(sum(s["turnover"] for s in series[i-19:i+1]) / 20, 2)
        else:
            series[i]["ma20"] = series[i]["turnover"]

    # 近120天分位数
    recent = series[-120:]
    turnovers = [s["turnover"] for s in recent]
    turnovers.sort()
    current = series[-1]["turnover"]
    pct = sum(1 for t in turnovers if t < current) / len(turnovers) * 100

    # 趋势
    if series[-1]["ma5"] > series[-1]["ma20"] * 1.2 and series[-1]["ma5"] > series[-5]["ma5"]:
        trend = "加速放量"
    elif series[-1]["ma5"] > series[-1]["ma20"]:
        trend = "温和放量"
    elif series[-1]["ma5"] < series[-1]["ma20"] * 0.8:
        trend = "缩量"
    else:
        trend = "平稳"

    # 突然放量检测
    if len(series) > 5:
        ma5_std = sum((series[-i]["turnover"] - series[-1]["ma5"])**2 for i in range(1,6)) ** 0.5
        if abs(series[-1]["turnover"] - series[-1]["ma5"]) > ma5_std * 2:
            trend = "突然放量⚠️" if series[-1]["turnover"] > series[-1]["ma5"] else "突然缩量"

    return {
        "series": series,
        "current": round(current, 2),
        "current_pct": round(pct, 0),
        "ma5": series[-1]["ma5"],
        "ma20": series[-1]["ma20"],
        "trend": trend,
        "ltgb": ltgb,
    }


# ============================================================
# 2. 价格阶段定位
# ============================================================

def classify_price_phase(code: str) -> dict:
    """
    判断当前价格在近120天区间的位置

    返回: {
        "phase": "低位" | "中低位" | "中位" | "中高位" | "高位",
        "position_pct": 在120天区间内的百分比,
        "range_high": 区间最高,
        "range_low": 区间最低,
    }
    """
    if code.startswith(("6", "5")):
        path = f"F:/tongdaxin/vipdoc/sh/lday/sh{code}.day"
    else:
        path = f"F:/tongdaxin/vipdoc/sz/lday/sz{code}.day"

    bars = read_daily_kline(path)
    if not bars or len(bars) < 30:
        return {"phase": "中位", "position_pct": 50, "range_high": 0, "range_low": 0}

    recent = bars[-120:]
    all_highs = [b.high for b in recent]
    all_lows = [b.low for b in recent]
    range_high = max(all_highs)
    range_low = min(all_lows)
    current = recent[-1].close

    if range_high <= range_low:
        return {"phase": "中位", "position_pct": 50, "range_high": range_high, "range_low": range_low}

    pct = (current - range_low) / (range_high - range_low) * 100

    if pct <= 25:
        phase = "低位"
    elif pct <= 40:
        phase = "中低位"
    elif pct <= 60:
        phase = "中位"
    elif pct <= 75:
        phase = "中高位"
    else:
        phase = "高位"

    return {
        "phase": phase,
        "position_pct": round(pct, 0),
        "range_high": range_high,
        "range_low": range_low,
    }


# ============================================================
# 3. 阶段×换手交互分析 (核心创新)
# ============================================================

def analyze_phase_turnover_interaction(phase: str, turnover: float, code: str) -> dict:
    """
    价格位置和换手率的交互解读

    关键场景:
      高位+高换手 = 出货嫌疑
      低位+高换手 = 主力建仓
    """
    t = get_thresholds(code)

    if phase in ("高位", "中高位"):
        if turnover > t["high"]:
            signal = "⚠️ 高位放量 — 出货嫌疑"
            risk = "高"
            score = -2
        elif turnover > t["normal"]:
            signal = "🟡 高位活跃 — 多空激烈，注意方向"
            risk = "中"
            score = -1
        elif turnover < t["low"]:
            signal = "🟢 高位缩量 — 浮筹已清，可能继续涨"
            risk = "低"
            score = 1
        else:
            signal = "➖ 高位平稳 — 观望"
            risk = "中"
            score = 0

    elif phase in ("低位", "中低位"):
        if turnover > t["high"]:
            signal = "🟢 低位放量 — ✨主力建仓信号!"
            risk = "低"
            score = 3
        elif turnover > t["normal"]:
            signal = "🟡 低位活跃 — 资金关注，蓄力中"
            risk = "中低"
            score = 1
        elif turnover < t["low"]:
            signal = "➖ 低位冷清 — 无人关注，可能阴跌"
            risk = "中"
            score = -1
        else:
            signal = "🟡 低位温和 — 等待催化剂"
            risk = "中低"
            score = 0

    else:  # 中位
        if turnover > t["high"]:
            signal = "🟡 中位放量 — 方向选择临界点"
            risk = "中"
            score = 0
        elif turnover > t["normal"]:
            signal = "➖ 中位正常 — 按趋势操作"
            risk = "中低"
            score = 0
        elif turnover < t["low"]:
            signal = "🟡 中位缩量 — 方向选择，等待变盘"
            risk = "中"
            score = 0
        else:
            signal = "➖ 中位平稳"
            risk = "低"
            score = 0

    return {
        "phase": phase,
        "turnover": turnover,
        "signal": signal,
        "risk": risk,
        "score": score,  # +3=强烈看多, -2=强烈看空
        "interpretation": {
            "high": f"{t['high']}%",
            "normal": f"{t['normal']}%",
            "low": f"{t['low']}%",
        }
    }


# ============================================================
# 4. 换手率×量比双维分类
# ============================================================

def analyze_volume_relation(turnover: float, volume_ratio: float, code: str) -> dict:
    """
    换手率 vs 量比的四象限分类

             低换手      高换手
    高量比  🟡僵持消耗  🟢放量换手(真实方向)
    低量比  ➖冷清      🟠无量推高(虚假)
    """
    t = get_thresholds(code)
    is_high_turnover = turnover > t["normal"]

    if is_high_turnover and volume_ratio > 1.2:
        category = "🟢 放量换手 — 方向真实，筹码充分交换"
        score = 2
    elif is_high_turnover and volume_ratio < 0.8:
        category = "🟠 无量推高 — 虚假繁荣，量价背离"
        score = -1
    elif not is_high_turnover and volume_ratio > 1.2:
        category = "🟡 僵持消耗 — 量大事小，方向不明"
        score = 0
    elif not is_high_turnover and volume_ratio < 0.8:
        category = "➖ 冷清无人 — 缩量缩波"
        score = -1
    else:
        category = "➖ 量价均衡"
        score = 0

    return {
        "turnover": turnover,
        "volume_ratio": volume_ratio,
        "category": category,
        "score": score,
    }


# ============================================================
# 5. 阻力突破质量分析 (联动 volume_efficiency)
# ============================================================

def analyze_resistance_breakthrough(turnover: float, eff_data: list,
                                    current_price: float) -> dict:
    """
    换手率 × 量价效率：判断阻力带突破的质量

    eff_data: 来自 volume_efficiency.py 的 reverse_t_ranking() 结果
              字段: price_label, hardness, avg_efficiency, distance_pct, score
    """
    if not eff_data:
        return {"quality": "无数据", "reason": ""}

    # 找最近的两个阻力层
    near = [r for r in eff_data if r.get("distance_pct", 99) < 5]
    if not near:
        near = eff_data[:1]

    nearest = near[0]
    eff = nearest.get("avg_efficiency", 1.0)
    hardness = nearest.get("hardness", "未知")
    label = nearest.get("price_label", "")

    if eff >= 2.0 and turnover > 10:
        quality = "🟢 高换手过硬阻 — 真突破，筹码充分换手"
        confidence = "高"
    elif eff >= 2.0 and turnover < 5:
        quality = "🔴 低换手过硬阻 — 偏冲破，大概率回踩"
        confidence = "低"
    elif eff < 1.5 and turnover > 8:
        quality = "🟢 高换手过软阻 — 正常推进"
        confidence = "高"
    elif eff < 1.5 and turnover < 3:
        quality = "🟡 低换手过软阻 — 方向待确认"
        confidence = "中"
    else:
        quality = f"➖ 中等 ({hardness}, 换手{turnover:.1f}%)"
        confidence = "中"

    return {
        "quality": quality,
        "confidence": confidence,
        "target": label,
        "efficiency": eff,
        "hardness": hardness,
    }


# ============================================================
# 6. 次日预测 (历史回测)
# ============================================================

def compute_next_day_stats(code: str) -> dict:
    """
    统计不同换手率区间对次日涨跌的预测力

    返回: 各换手率区间的历史次日平均涨跌
    """
    bars = read_daily_kline(f"F:/tongdaxin/vipdoc/sz/lday/sz{code}.day")
    if not bars or len(bars) < 60:
        return {"buckets": [], "note": "数据不足"}

    t = get_thresholds(code)
    # 从config中的LTGB推算换手率
    ltgb = 117532 if code == "300418" else 347793

    # 计算每日换手率 + 次日涨跌幅
    pairs = []
    for i in range(1, len(bars)):
        turnover_i = (bars[i].volume / (ltgb * 10000)) * 100
        next_chg = (bars[i+1].close / bars[i].close - 1) * 100 if i+1 < len(bars) else 0
        pairs.append((turnover_i, next_chg))

    # 分桶统计
    buckets = {
        "极低": (0, t["very_low"]),
        "偏低": (t["very_low"], t["low"]),
        "正常": (t["low"], t["normal"]),
        "偏高": (t["normal"], t["high"]),
        "极端": (t["high"], 999),
    }

    result = {}
    for label, (lo, hi) in buckets.items():
        in_range = [(t, c) for t, c in pairs if lo <= t < hi]
        if not in_range:
            continue
        avg = sum(c for _, c in in_range) / len(in_range)
        wins = sum(1 for _, c in in_range if c > 0)
        result[label] = {
            "n": len(in_range),
            "avg_next_chg": round(avg, 2),
            "win_rate": round(wins / len(in_range) * 100, 0),
        }

    # 当前所在区间
    if pairs:
        current_turnover = pairs[-1][0]
        for label, (lo, hi) in buckets.items():
            if lo <= current_turnover < hi:
                result["current_bucket"] = label
                break

    return result


# ============================================================
# 7. 主入口: 换手率综合诊断
# ============================================================

@dataclass
class TurnoverDiagnosis:
    """换手率综合诊断结果"""
    code: str
    name: str
    current: float
    current_pct: float
    trend: str
    ma5: float
    ma20: float
    phase: str
    position_pct: float
    phase_signal: str
    phase_score: int
    vol_category: str
    vol_score: int
    breakthrough: str
    breakthrough_confidence: str
    next_day_stats: dict
    thresholds: dict

    # 联动其他模块的数据 (由调用方注入)
    trend_state: str = ""       # 来自 trend_classifier
    nearest_resistance: str = ""  # 来自 volume_profile
    efficiency: float = 0         # 来自 volume_efficiency


def turnover_diagnose(code: str, name: str = "",
                      ltgb: float = None,
                      current_price: float = 0,
                      eff_data: list = None,
                      trend_state: str = "",
                      nearest_resistance: str = "",
                      efficiency_val: float = 0) -> TurnoverDiagnosis:
    """换手率综合诊断主入口"""

    # 1. 基础数据
    data = compute_daily_turnover(code, ltgb)

    # 2. 价格阶段
    phase_info = classify_price_phase(code)

    # 3. 阶段×换手交互
    interaction = analyze_phase_turnover_interaction(
        phase_info["phase"], data["current"], code)

    # 4. 量×量分类
    daily_bars = read_daily_kline(f"F:/tongdaxin/vipdoc/sz/lday/sz{code}.day")
    if daily_bars and len(daily_bars) > 5:
        vol_5d = sum(b.volume for b in daily_bars[-6:-1]) / 5
        vol_ratio = daily_bars[-1].volume / vol_5d if vol_5d > 0 else 1.0
    else:
        vol_ratio = 1.0

    vol_rel = analyze_volume_relation(data["current"], vol_ratio, code)

    # 5. 阻力突破质量
    breakthrough = analyze_resistance_breakthrough(
        data["current"], eff_data or [], current_price)

    # 6. 次日统计
    next_day = compute_next_day_stats(code)

    return TurnoverDiagnosis(
        code=code,
        name=name or code,
        current=data["current"],
        current_pct=data["current_pct"],
        trend=data["trend"],
        ma5=data["ma5"],
        ma20=data["ma20"],
        phase=phase_info["phase"],
        position_pct=phase_info["position_pct"],
        phase_signal=interaction["signal"],
        phase_score=interaction["score"],
        vol_category=vol_rel["category"],
        vol_score=vol_rel["score"],
        breakthrough=breakthrough["quality"],
        breakthrough_confidence=breakthrough.get("confidence", ""),
        next_day_stats=next_day,
        thresholds=get_thresholds(code),
        trend_state=trend_state,
        nearest_resistance=nearest_resistance,
        efficiency=efficiency_val,
    )


# ============================================================
# 8. 格式化输出 (联动所有模块)
# ============================================================

def format_turnover_report(diag: TurnoverDiagnosis) -> str:
    """美观输出，并联动其他模块的数据"""

    lines = []
    lines.append(f"\n{'='*55}")
    lines.append(f"  📊 换手率深度分析 — {diag.name}")
    lines.append(f"{'='*55}")

    # 基础数据
    lines.append(f"  当前: {diag.current:.2f}% | MA5: {diag.ma5:.2f}% | MA20: {diag.ma20:.2f}%")
    lines.append(f"  近120天分位: {diag.current_pct:.0f}% | 趋势: {diag.trend}")

    # 联动趋势状态
    if diag.trend_state:
        lines.append(f"  联动趋势: {diag.trend_state}")

    # 阶段×换手 (核心)
    bar = "▓" * min(int(diag.position_pct / 5), 20) + "·" * max(0, 20 - int(diag.position_pct / 5))
    lines.append(f"  价格位置: {diag.phase} │{bar}│ {diag.position_pct:.0f}%")
    lines.append(f"  🎯 阶段×换手: {diag.phase_signal}")

    # 联动阻力
    if diag.nearest_resistance:
        lines.append(f"  联动阻力: {diag.nearest_resistance}")

    # 量×量
    lines.append(f"  📈 量×量: {diag.vol_category}")

    # 阻力突破
    lines.append(f"  🚧 突破质量: {diag.breakthrough}")

    # 联动效率
    if diag.efficiency > 0:
        lines.append(f"  联动效率: {diag.efficiency:.1f}x")

    # 次日统计
    stats = diag.next_day_stats
    if "current_bucket" in stats:
        curr_b = stats["current_bucket"]
        if curr_b in stats:
            nxt = stats[curr_b]
            lines.append(f"  📅 次日统计: 历史{curr_b}换手(n={nxt['n']}) 次日均{nxt['avg_next_chg']:+.1f}% 胜率{nxt['win_rate']:.0f}%")

    # 综合评分
    total_score = diag.phase_score + diag.vol_score
    lines.append(f"  {'─'*53}")
    if total_score >= 3:
        lines.append(f"  🟢 综合评分: +{total_score} — 做多信号强")
    elif total_score >= 0:
        lines.append(f"  ➖ 综合评分: {total_score:+d} — 中性")
    else:
        lines.append(f"  🔴 综合评分: {total_score:+d} — 谨慎")
    lines.append(f"{'='*55}")

    return "\n".join(lines)


# ============================================================
# 自测
# ============================================================

if __name__ == "__main__":
    for code, name in [("300418", "昆仑万维"), ("300058", "蓝色光标")]:
        diag = turnover_diagnose(code, name)
        print(format_turnover_report(diag))
