"""
趋势状态判定器 — Engine A (波仔系统v3核心)

功能: 每天第一件事——判断今天是什么市场状态
  - STRONG_TREND_UP:   禁用倒T，启用正T趋势跟随
  - STRONG_TREND_DOWN: 禁用正T，只做倒T
  - CHOPPY:            倒T为主，正T为辅
  - LOW_VOL:           降仓50%，预期收益打折

理论基础:
  - 日本1990-95年教训: 趋势跟随在强趋势中>倒T博弈
  - 海龟法则: 市场状态判定是策略选择的前提
  - ATR通道突破: 波动率是仓位调整的核心变量

输入:
  - 日线K线数据（最近20日）
  - 当日实时价格/量比
  - 市场宽度数据（涨跌家数）
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass
from typing import List, Optional
from engine.tdx_parser import read_daily_kline


class TrendState:
    """市场状态枚举"""
    STRONG_UP = "strong_up"
    STRONG_DOWN = "strong_down"
    CHOPPY = "choppy"
    LOW_VOL = "low_vol"

    @staticmethod
    def label(state: str) -> str:
        return {
            "strong_up": "🔥 强上涨趋势",
            "strong_down": "💧 强下跌趋势", 
            "choppy": "〰️ 震荡",
            "low_vol": "😴 低波动",
        }.get(state, state)


@dataclass
class TrendVerdict:
    """趋势判定结果"""
    state: str
    state_label: str
    direction: str          # "up" / "down" / "sideways"
    atr_ratio: float        # 当前ATR / 20日均ATR
    vol_ratio: float        # 量比
    consecutive: int        # 连阳(+)或连阴(-)天数
    ma_alignment: str       # "bullish" / "bearish" / "mixed"
    
    # 策略建议
    reverse_t_allowed: bool = True     # 是否允许倒T
    trend_t_allowed: bool = False      # 是否允许正T趋势跟随
    position_factor: float = 1.0       # 仓位系数（1.0=全仓 0.5=半仓）
    
    def summary(self) -> str:
        lines = [
            f"状态: {self.state_label}",
            f"方向: {'上涨' if self.direction == 'up' else '下跌' if self.direction == 'down' else '震荡'}",
            f"波动: ATR/均值={self.atr_ratio:.1f}x 量比={self.vol_ratio:.1f}x",
            f"连{'阳' if self.consecutive>0 else '阴'}{abs(self.consecutive)}天",
            f"均线: {'多头排列' if self.ma_alignment=='bullish' else '空头排列' if self.ma_alignment=='bearish' else '混合'}",
            f"策略: 倒T={'✅' if self.reverse_t_allowed else '❌'} 正T={'✅' if self.trend_t_allowed else '❌'} 仓位={self.position_factor*100:.0f}%",
        ]
        return "\n".join(lines)


def calc_atr(bars_20d, period=14):
    """计算ATR"""
    if len(bars_20d) < period + 1:
        return 0
    tr_sum = 0
    for i in range(-period, 0):
        b = bars_20d[i]
        b_prev = bars_20d[i-1]
        tr = max(b.high - b.low, abs(b.high - b_prev.close), abs(b.low - b_prev.close))
        tr_sum += tr
    return tr_sum / period


def calc_sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def classify_trend(code: str, current_price: float = 0) -> TrendVerdict:
    """
    核心函数: 判定当前市场状态
    
    Returns: TrendVerdict with state + strategy permissions
    """
    if code.startswith(("6", "5")):
        daily_path = f"F:/tongdaxin/vipdoc/sh/lday/sh{code}.day"
    else:
        daily_path = f"F:/tongdaxin/vipdoc/sz/lday/sz{code}.day"

    bars = read_daily_kline(daily_path)
    if not bars or len(bars) < 30:
        return TrendVerdict(state=TrendState.CHOPPY, state_label=TrendState.label(TrendState.CHOPPY),
                           direction="sideways", atr_ratio=1.0, vol_ratio=1.0, consecutive=0,
                           ma_alignment="mixed")

    recent = bars[-25:]
    latest = bars[-1]

    # ===== 1. 趋势方向 =====
    closes = [b.close for b in recent]
    ma5 = calc_sma(closes, 5)
    ma10 = calc_sma(closes, 10)
    ma20 = calc_sma(closes, 20)
    
    if ma5 and ma10 and ma20:
        if ma5 > ma10 > ma20:
            ma_align = "bullish"
        elif ma5 < ma10 < ma20:
            ma_align = "bearish"
        else:
            ma_align = "mixed"
    else:
        ma_align = "mixed"

    # 连阳/连阴
    consecutive = 0
    for b in reversed(bars):
        chg = b.close - b.open
        if consecutive == 0:
            consecutive = 1 if chg >= 0 else -1
        elif (consecutive > 0 and chg >= 0) or (consecutive < 0 and chg < 0):
            consecutive += 1 if consecutive > 0 else -1
        else:
            break

    # ===== 2. 波动率 =====
    atr_now = calc_atr(recent, 14)
    atr_20d = calc_atr(bars[-40:-20], 14) if len(bars) >= 40 else atr_now
    atr_ratio = atr_now / atr_20d if atr_20d > 0 else 1.0

    # ===== 3. 量能 =====
    vol_5d = sum(b.volume for b in bars[-6:-1]) / 5
    vol_ratio = latest.volume / vol_5d if vol_5d > 0 else 1.0

    # ===== 4. 综合判定 =====
    direction = "sideways"
    if ma_align == "bullish" and consecutive >= 3:
        direction = "up"
    elif ma_align == "bearish" and consecutive <= -3:
        direction = "down"

    # 策略开关
    reverse_t_allowed = True
    trend_t_allowed = False
    position_factor = 1.0
    state = TrendState.CHOPPY

    if direction == "up" and atr_ratio > 1.3 and vol_ratio > 1.2:
        # 强上涨趋势：放量突破，禁用倒T
        state = TrendState.STRONG_UP
        reverse_t_allowed = False
        trend_t_allowed = True
        position_factor = 0.8  # 趋势跟随时保守一点

    elif direction == "down" and atr_ratio > 1.3 and vol_ratio > 1.2:
        # 强下跌趋势：放量破位，专注倒T
        state = TrendState.STRONG_DOWN
        reverse_t_allowed = True
        trend_t_allowed = False
        position_factor = 0.8

    elif atr_ratio < 0.5 and vol_ratio < 0.5:
        # 低波动：降仓
        state = TrendState.LOW_VOL
        reverse_t_allowed = True
        position_factor = 0.5

    else:
        # 震荡：正常操作
        state = TrendState.CHOPPY
        reverse_t_allowed = True
        position_factor = 1.0

    return TrendVerdict(
        state=state,
        state_label=TrendState.label(state),
        direction=direction,
        atr_ratio=round(atr_ratio, 1),
        vol_ratio=round(vol_ratio, 1),
        consecutive=consecutive,
        ma_alignment=ma_align,
        reverse_t_allowed=reverse_t_allowed,
        trend_t_allowed=trend_t_allowed,
        position_factor=position_factor,
    )
