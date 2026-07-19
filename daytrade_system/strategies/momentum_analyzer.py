"""
实时动能强度分析器 — 波仔系统 v3

5维综合评分(0-100):
  日内涨幅强度  30% — 当前涨幅 vs 日内振幅
  涨速ROC       25% — 5分钟价格变化速率
  VWAP位置      15% — 价格vs均价+斜率方向
  量价配合      20% — 量比vs涨幅是否匹配
  买卖压力      10% — 外盘/内盘比

输出:
  0-30:  极弱(不宜做多)
  30-50: 偏弱(观望)
  50-70: 中性(正常)
  70-85: 偏强(有利于穿越阻力)
  85-100: 极强(大概率穿越)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from typing import Optional
from engine.tdx_parser import read_minute_kline, group_by_date

TDX_FZLINE = r"F:\tongdaxin\vipdoc\sz\fzline"


@dataclass
class MomentumScore:
    """动能综合评分"""
    total: float = 0
    level: str = ""
    label: str = ""
    # 各维度
    intraday_strength: float = 0      # 日内涨幅强度
    roc_speed: float = 0              # 涨速ROC
    vwap_position: float = 0          # VWAP位置
    volume_price_match: float = 0     # 量价配合
    buy_pressure: float = 0           # 买卖压力
    details: list = field(default_factory=list)


def _get_recent_5min_bars(code: str, n: int = 10):
    """获取最近n根5分钟K线"""
    fp = f"{TDX_FZLINE}/sz{code}.lc5"
    bars = read_minute_kline(fp)
    if not bars or len(bars) < n:
        return []
    groups = group_by_date(bars)
    dates = sorted(groups.keys())
    if not dates:
        return []
    today_bars = groups[dates[-1]]
    return today_bars[-n:]


def calc_momentum(code: str, current_price: float, open_price: float,
                  avg_price: float, day_high: float, day_low: float,
                  volume_ratio: float = 1.0,
                  inside: float = 0, outside: float = 0) -> MomentumScore:
    """
    计算实时动能强度

    Args:
        code: 股票代码
        current_price: 当前价
        open_price: 开盘价
        avg_price: 日内均价(VWAP)
        day_high: 日内最高
        day_low: 日内最低
        volume_ratio: 量比
        inside: 内盘(万手)
        outside: 外盘(万手)
    """
    score = MomentumScore()

    # ===== 1. 日内涨幅强度 (30%) =====
    day_range = day_high - day_low if day_high > day_low else 1.0
    chg_pct = (current_price / open_price - 1) * 100
    pct_of_range = (current_price - day_low) / day_range * 100

    if chg_pct > 3 and pct_of_range > 80:
        intraday = 30
    elif chg_pct > 2 and pct_of_range > 65:
        intraday = 25
    elif chg_pct > 1 and pct_of_range > 55:
        intraday = 20
    elif chg_pct > 0.5:
        intraday = 15
    elif chg_pct > 0:
        intraday = 10
    elif chg_pct > -0.5:
        intraday = 8
    elif chg_pct > -1:
        intraday = 5
    else:
        intraday = 2

    score.intraday_strength = intraday
    score.details.append(f"日内涨幅{chg_pct:+.1f}%(在{day_range:.2f}区间{pct_of_range:.0f}%位) → {intraday}分")

    # ===== 2. 涨速ROC (25%) =====
    bars_5m = _get_recent_5min_bars(code, 10)
    roc_score = 0
    if bars_5m and len(bars_5m) >= 6:
        # 计算最近5根5min K的涨速
        recent = bars_5m[-5:]
        roc_values = []
        for i in range(1, len(recent)):
            roc = (recent[i].close / recent[i-1].close - 1) * 100
            roc_values.append(roc)
        avg_roc = sum(roc_values) / len(roc_values)

        # 同时检查趋势持续性(最近K的close方向)
        up_count = sum(1 for b in recent if b.close >= b.open)
        down_count = len(recent) - up_count

        if avg_roc > 0.3:
            roc_score = 25
        elif avg_roc > 0.15:
            roc_score = 20
        elif avg_roc > 0.05:
            roc_score = 15
        elif avg_roc > 0:
            roc_score = 12
        elif avg_roc > -0.05:
            roc_score = 10
        elif avg_roc > -0.15:
            roc_score = 6
        else:
            roc_score = 3

        # 趋势持续性加分
        if up_count >= 4 and avg_roc > 0:
            roc_score = min(25, roc_score + 3)

        score.details.append(f"涨速ROC={avg_roc:+.2f}%/5min (近5K {up_count}阳{down_count}阴) → {roc_score}分")

    else:
        roc_score = 12  # 无数据默认中等
        score.details.append(f"涨速ROC=无数据 → 默认{roc_score}分")

    score.roc_speed = roc_score

    # ===== 3. VWAP位置 (15%) =====
    if avg_price > 0:
        vwap_dev = (current_price / avg_price - 1) * 100
        # VWAP斜率通过近似判断(用开口价vs均价)
        vwap_trend = (avg_price / open_price - 1) * 100

        if vwap_dev > 1.5 and vwap_trend > 0.5:
            vwap_score = 15  # 远高于VWAP且均价在上涨
        elif vwap_dev > 0.8:
            vwap_score = 12
        elif vwap_dev > 0:
            vwap_score = 10
        elif vwap_dev > -0.8:
            vwap_score = 7
        elif vwap_dev > -1.5:
            vwap_score = 4
        else:
            vwap_score = 2

        score.details.append(f"VWAP偏离{vwap_dev:+.1f}%(均价{avg_price:.2f}) → {vwap_score}分")
    else:
        vwap_score = 7
        score.details.append(f"VWAP无数据 → 默认{vwap_score}分")

    score.vwap_position = vwap_score

    # ===== 4. 量价配合 (20%) =====
    if volume_ratio > 1.5 and chg_pct > 1.5:
        vol_score = 20  # 放量涨(最健康的动能)
    elif volume_ratio > 1.2 and chg_pct > 0.8:
        vol_score = 17
    elif volume_ratio > 1.0 and chg_pct > 0.3:
        vol_score = 14
    elif volume_ratio > 0.8:
        vol_score = 10
    elif volume_ratio > 1.2 and chg_pct < 0:
        vol_score = 5  # 放量跌(弱势)
    else:
        vol_score = 8

    score.details.append(f"量比{volume_ratio:.1f}x × 涨幅{chg_pct:+.1f}% → {vol_score}分")
    score.volume_price_match = vol_score

    # ===== 5. 买卖压力 (10%) =====
    if outside + inside > 0:
        buy_ratio = outside / (outside + inside) * 100
    else:
        buy_ratio = 50

    if buy_ratio > 60:
        buy_score = 10
    elif buy_ratio > 55:
        buy_score = 8
    elif buy_ratio > 50:
        buy_score = 6
    elif buy_ratio > 45:
        buy_score = 4
    else:
        buy_score = 2

    score.details.append(f"外盘/总={buy_ratio:.0f}% → {buy_score}分")
    score.buy_pressure = buy_score

    # ===== 加权总分 =====
    # 各维度已经预设了最大满分(30+25+15+20+10=100)，直接求和即可
    total = intraday + roc_score + vwap_score + vol_score + buy_score

    score.total = round(total)

    if total >= 85:
        score.level = "极强"
        score.label = "🔥🔥🔥 极强动能 — 大概率穿越"
    elif total >= 70:
        score.level = "偏强"
        score.label = "🔥 偏强动能 — 有利于穿越"
    elif total >= 50:
        score.level = "中性"
        score.label = "➖ 中性动能 — 穿越需放量"
    elif total >= 30:
        score.level = "偏弱"
        score.label = "💤 偏弱动能 — 穿越困难"
    else:
        score.level = "极弱"
        score.label = "❄️ 极弱动能 — 无法穿越"

    return score


def momentum_report(score: MomentumScore) -> str:
    """格式化输出动能报告"""
    lines = [
        f"  动能综合: {score.total}/100 {score.label}",
    ]
    for d in score.details:
        lines.append(f"    └ {d}")
    return "\n".join(lines)


if __name__ == "__main__":
    s = calc_momentum("300418", 40.99, 40.00, 40.56, 41.50, 39.62, 1.1, 215689, 228089)
    print(momentum_report(s))
