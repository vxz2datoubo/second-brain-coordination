"""
日线趋势分析 — 波仔倒T系统 v2

基于日K线提供趋势判断，辅助决策：
  上涨趋势中 → 少卖、保守做T
  下跌趋势中 → 大胆卖、主动倒T
  横盘震荡中 → 按Volume Profile锚点操作

指标:
  连阳/连阴天数
  均线方向 (5/10/20日)
  放量/缩量（与5日均量对比）
  实体比例（阳线实体/总振幅，判断方向强度）
  长上影线检测（冲高回落）
  长下影线检测（探底回升）
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.tdx_parser import read_daily_kline
from dataclasses import dataclass, field
from typing import List, Optional

TDX_DAILY_SZ = r"F:\tongdaxin\vipdoc\sz\lday"
TDX_DAILY_SH = r"F:\tongdaxin\vipdoc\sh\lday"


@dataclass
class DailyTrend:
    """日线趋势分析结果"""
    code: str
    name: str
    date: str
    close: float
    change_pct: float           # 当日涨跌%
    consecutive_days: int       # 连阳(+)或连阴(-)
    trend: str                  # 上涨趋势 / 下跌趋势 / 震荡
    ma5_direction: str          # ↑ ↓ →
    ma10_direction: str
    ma20_direction: str
    volume_ratio: float         # 量比（vs 5日均）
    body_ratio: float           # 实体/振幅 比例
    upper_wick_pct: float       # 上影线%
    lower_wick_pct: float       # 下影线%
    signals: List[str] = field(default_factory=list)


def calc_sma(values: list, period: int) -> list:
    """简单移动平均"""
    sma = [0] * len(values)
    for i in range(period - 1, len(values)):
        sma[i] = sum(values[i - period + 1:i + 1]) / period
    return sma


def detect_shadow(bar) -> tuple:
    """检测影线长度"""
    if bar.high <= bar.low or bar.open <= 0:
        return 0, 0
    body_top = max(bar.open, bar.close)
    body_bot = min(bar.open, bar.close)
    total_range = bar.high - bar.low
    if total_range <= 0:
        return 0, 0
    upper = (bar.high - body_top) / total_range * 100
    lower = (body_bot - bar.low) / total_range * 100
    return round(upper, 1), round(lower, 1)


def analyze_daily(code: str, name: str = "") -> DailyTrend:
    """分析最新一个交易日的日线趋势"""
    # 自动判断沪市/深市
    if code.startswith(("6", "5")):
        path = f"{TDX_DAILY_SH}/sh{code}.day"
    else:
        path = f"{TDX_DAILY_SZ}/sz{code}.day"

    bars = read_daily_kline(path)
    if not bars or len(bars) < 25:
        return None

    latest = bars[-1]
    recent = bars[-25:]

    # 均线
    closes = [b.close for b in recent]
    ma5 = calc_sma(closes, 5)
    ma10 = calc_sma(closes, 10)
    ma20 = calc_sma(closes, 20)

    ma5_dir = "→" if ma5[-1] == ma5[-2] else ("↑" if ma5[-1] > ma5[-2] else "↓")
    ma10_dir = "→" if ma10[-1] == ma10[-2] else ("↑" if ma10[-1] > ma10[-2] else "↓")
    ma20_dir = "→" if ma20[-1] == ma20[-2] else ("↑" if ma20[-1] > ma20[-2] else "↓")

    # 趋势判断
    ma_up = sum(1 for d in [ma5_dir, ma10_dir, ma20_dir] if d == "↑")
    ma_down = sum(1 for d in [ma5_dir, ma10_dir, ma20_dir] if d == "↓")

    if ma_up >= 2:
        trend = "上涨趋势"
    elif ma_down >= 2:
        trend = "下跌趋势"
    else:
        trend = "震荡"

    # 连阳/连阴
    consecutive = 0
    for bar in reversed(bars):
        chg = (bar.close / bar.open - 1)
        if (consecutive == 0 and chg > 0) or (consecutive > 0 and chg > 0):
            consecutive += 1
        elif (consecutive == 0 and chg <= 0) or (consecutive < 0 and chg <= 0):
            consecutive -= 1
        else:
            break

    # 量比
    vol_5d = sum(b.volume for b in bars[-6:-1]) / 5
    vol_ratio = latest.volume / vol_5d if vol_5d > 0 else 1.0

    # 实体比例
    if latest.high > latest.low:
        body = abs(latest.close - latest.open)
        body_ratio = body / (latest.high - latest.low) * 100
    else:
        body_ratio = 0

    # 影线
    upper_wick, lower_wick = detect_shadow(latest)

    # 信号收集
    signals = []
    if consecutive >= 3:
        signals.append(f"连阳{consecutive}天 🔥 超买风险")
    elif consecutive <= -3:
        signals.append(f"连阴{abs(consecutive)}天 💧 超卖机会")

    if vol_ratio > 1.5:
        signals.append(f"放量{vol_ratio:.1f}x")
    elif vol_ratio < 0.6:
        signals.append(f"缩量{vol_ratio:.1f}x")

    if upper_wick > 30:
        signals.append(f"长上影{upper_wick:.0f}% ← 冲高回落")
    if lower_wick > 30:
        signals.append(f"长下影{lower_wick:.0f}% ← 探底回升")

    # 倒T策略建议
    strategy = []
    if trend == "下跌趋势":
        strategy.append("🟢 大胆倒T（先卖后接）")
        strategy.append("   支撑带内开仓卖出，趋势顺势")
    elif trend == "上涨趋势":
        strategy.append("🟡 保守倒T（少卖、等低位吸）")
        strategy.append("   不要逆势大量卖出")
    else:
        strategy.append("➖ 正常操作")
        strategy.append("   按Volume Profile锚点左右均衡")

    return DailyTrend(
        code=code,
        name=name or code,
        date=str(latest.date),
        close=latest.close,
        change_pct=round((latest.close / latest.open - 1) * 100, 1),
        consecutive_days=consecutive,
        trend=trend,
        ma5_direction=ma5_dir,
        ma10_direction=ma10_dir,
        ma20_direction=ma20_dir,
        volume_ratio=round(vol_ratio, 1),
        body_ratio=round(body_ratio, 0),
        upper_wick_pct=upper_wick,
        lower_wick_pct=lower_wick,
        signals=signals,
    )


def format_daily_report(dt: DailyTrend) -> str:
    """格式化日线报告"""
    if dt is None:
        return "数据不足，需要至少25个交易日数据"

    lines = [
        f"\n{'='*45}",
        f"  {dt.name}({dt.code}) 日线分析 {dt.date}",
        f"{'='*45}",
        f"  收盘 {dt.close:.2f}  ({dt.change_pct:+.1f}%)",
        f"  趋势: {dt.trend}  连{'阳' if dt.consecutive_days>0 else '阴'}{abs(dt.consecutive_days)}天",
        f"  均线: 5日{dt.ma5_direction} 10日{dt.ma10_direction} 20日{dt.ma20_direction}",
        f"  量比: {dt.volume_ratio:.1f}x  实体比: {dt.body_ratio:.0f}%",
    ]
    if dt.signals:
        lines.append(f"  信号: {' | '.join(dt.signals)}")
    lines.append(f"  {'─'*43}")
    lines.append(f"  📋 倒T建议:")
    lines.extend(f"  {s}" for s in [dt.trend])  # 趋势即建议
    lines.append(f"{'='*45}")
    return "\n".join(lines)


if __name__ == "__main__":
    for code, name in [("300418", "昆仑万维"), ("300058", "蓝色光标")]:
        dt = analyze_daily(code, name)
        print(format_daily_report(dt))
