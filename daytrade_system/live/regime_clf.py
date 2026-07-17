"""
市场状态分类器 — 将每日市场分为5种状态
决定系统整体参数
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple


class Regime(Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    HIGH_VOL_RANGE = "HIGH_VOL_RANGE"
    LOW_VOL_RANGE = "LOW_VOL_RANGE"
    EXTREME = "EXTREME"


def classify_regime(
    min5_bars_raw: List[Dict],
    daily_bars_raw: List[Dict],
    quote: Dict = None,
) -> Dict:
    """
    市场状态分类器
    输入通达信原始 K 线数据，输出市场状态
    """
    if not daily_bars_raw or len(daily_bars_raw) < 20:
        return {
            "regime": Regime.LOW_VOL_RANGE.value,
            "confidence": 0,
            "features": {},
        }

    # 提取收盘价、最高价、最低价
    closes = [b.get("close", b.get("c", 0)) for b in daily_bars_raw]
    highs = [b.get("high", b.get("h", 0)) for b in daily_bars_raw]
    lows = [b.get("low", b.get("l", 0)) for b in daily_bars_raw]
    volumes = [b.get("volume", b.get("v", 0)) for b in daily_bars_raw]

    if not closes or closes[-1] == 0:
        return {"regime": Regime.LOW_VOL_RANGE.value, "confidence": 0, "features": {}}

    n = len(closes)

    # 1. 计算5日均线方向
    if n >= 5:
        ma5_today = sum(closes[-5:]) / 5
        ma5_yesterday = sum(closes[-6:-1]) / 5 if n >= 6 else ma5_today
        ma5_slope = ma5_today / ma5_yesterday - 1 if ma5_yesterday else 0
    else:
        ma5_slope = 0

    # 2. 计算ATR
    def _calc_tr(i):
        return max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]) if i > 0 else 0,
            abs(lows[i] - closes[i-1]) if i > 0 else 0,
        )

    if n >= 14:
        tr_values = [_calc_tr(i) for i in range(max(1, n-14), n)]
        atr = sum(tr_values) / len(tr_values) if tr_values else 0
    else:
        atr = 0

    atr_pct = atr / closes[-1] * 100 if closes[-1] else 0

    # 3. 股价相对位置（距离20日均线）
    if n >= 20:
        ma20 = sum(closes[-20:]) / 20
        dist_to_ma20 = (closes[-1] / ma20 - 1) * 100
    else:
        dist_to_ma20 = 0

    # 4. 涨跌家数比（用指数代替，通用版用价格方向）
    up_days_5 = sum(1 for i in range(max(1, n-5), n) if closes[i] > closes[i-1])
    down_days_5 = sum(1 for i in range(max(1, n-5), n) if closes[i] < closes[i-1])
    market_breadth = up_days_5 / (up_days_5 + down_days_5) if (up_days_5 + down_days_5) > 0 else 0.5

    # 5. 振幅分析
    if n >= 5:
        ranges_5 = [(highs[i] - lows[i]) / closes[i] * 100 for i in range(n-5, n) if closes[i] > 0]
        avg_range_5 = sum(ranges_5) / len(ranges_5) if ranges_5 else 0
    else:
        avg_range_5 = 0

    # 今日涨跌幅
    chg_pct = (closes[-1] / closes[-2] - 1) * 100 if n >= 2 else 0

    # ---- 分类逻辑 ----
    # 极端行情：涨跌停或接近
    if abs(chg_pct) >= 9.5:
        regime = Regime.EXTREME
        confidence = 85
    # 下跌趋势
    elif ma5_slope < -0.005 and dist_to_ma20 < -3:
        regime = Regime.TREND_DOWN
        confidence = min(80, abs(ma5_slope) * 5000 + abs(dist_to_ma20) * 3)
    # 上涨趋势
    elif ma5_slope > 0.005 and dist_to_ma20 > 3:
        regime = Regime.TREND_UP
        confidence = min(80, ma5_slope * 5000 + dist_to_ma20 * 3)
    # 高波动震荡
    elif avg_range_5 > 4.5:
        regime = Regime.HIGH_VOL_RANGE
        confidence = min(75, avg_range_5 * 10)
    # 低波动盘整
    else:
        regime = Regime.LOW_VOL_RANGE
        confidence = min(70, (4.5 - avg_range_5) * 10)

    return {
        "regime": regime.value,
        "confidence": int(confidence),
        "features": {
            "ma5_slope": round(ma5_slope * 100, 4),
            "atr_pct": round(atr_pct, 2),
            "avg_range_5": round(avg_range_5, 2),
            "dist_to_ma20": round(dist_to_ma20, 2),
            "market_breadth": round(market_breadth, 4),
            "chg_pct": round(chg_pct, 2),
        },
        "t_advice": _regime_t_advice(regime),
    }


def _regime_t_advice(regime: Regime) -> str:
    advices = {
        Regime.TREND_UP: "上升趋势，少做倒T多持有；若做则在急涨2%+放量衰竭时卖，回调接",
        Regime.TREND_DOWN: "下跌趋势，倒T为主（接更多）；反弹到阻力位就卖，等低位接回",
        Regime.HIGH_VOL_RANGE: "高波动震荡，倒T黄金窗口！振幅大，1-1.5%利润空间充裕",
        Regime.LOW_VOL_RANGE: "低波动盘整，降低频率只做A级信号，预期利润0.3-0.5%",
        Regime.EXTREME: "极端行情，所有T仓平掉，保护底仓！",
    }
    return advices.get(regime, "观望")
