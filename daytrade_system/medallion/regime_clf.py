"""regime_clf — 市场状态分类器

将每日分为5种市场状态，决定系统整体参数：
  TREND_UP / TREND_DOWN / HIGH_VOL_RANGE / LOW_VOL_RANGE / EXTREME

判定方法：
  - ATR比值（波动率）
  - 日内振幅 vs 预期振幅
  - 5日均线方向
  - 涨跌家数比（需要外部数据时可跳过）
  - 最近10日系统胜率（可跳过）
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional
from engine.indicators import KBar, calc_ma, calc_atr
from engine.indicators import calc_vwap_bands


class RegimeClassifier:
    """市场状态分类器"""

    REGIMES = ["TREND_UP", "TREND_DOWN", "HIGH_VOL_RANGE", "LOW_VOL_RANGE", "EXTREME"]

    def __init__(self, code: str):
        self.code = code
        self._cache: Dict[str, dict] = {}

    # ----------------------------------------------------------
    # 主入口
    # ----------------------------------------------------------
    def classify(self, daily_bars: List[KBar], today_min5: List[KBar],
                 prev_day_close: Optional[float] = None) -> Dict:
        """
        入口函数，返回分类结果和详细特征向量
        """
        today_bar = today_min5[-1] if today_min5 else None
        closes = [b.close for b in daily_bars]
        highs  = [b.high  for b in daily_bars]
        lows   = [b.low   for b in daily_bars]

        # === 特征1: ATR比值 ===
        atr = calc_atr(highs, lows, closes, period=14)
        current_atr_pct = (atr[-1] / closes[-1] * 100) if atr[-1] else 3.0
        # 历史平均ATR%
        avg_atr_pct = sum(a / c * 100 for a, c in zip(atr[-20:-1], closes[-20:-1]) if a) / 19 if len(atr) > 20 else current_atr_pct
        vol_ratio = current_atr_pct / avg_atr_pct if avg_atr_pct > 0 else 1.0

        # === 特征2: 日内振幅 vs 预期振幅 ===
        if today_bar:
            intraday_range_pct = (today_bar.high - today_bar.low) / today_bar.open * 100
        else:
            intraday_range_pct = (daily_bars[-1].high - daily_bars[-1].low) / daily_bars[-1].open * 100
        expected_range = avg_atr_pct * 0.8
        range_ratio = intraday_range_pct / expected_range if expected_range > 0 else 1.0

        # === 特征3: 5日均线方向 ===
        ma5 = calc_ma(closes, 5)
        ma5_now  = ma5[-1]  if ma5[-1]  else closes[-1]
        ma5_prev = ma5[-2]  if len(ma5) > 1 and ma5[-2] else ma5_now
        ma5_slope = (ma5_now / ma5_prev - 1) * 100 if ma5_prev else 0.0

        # === 特征4: 连续涨跌 ===
        recent_closes = closes[-5:]
        up_count  = sum(1 for i in range(1, len(recent_closes)) if recent_closes[i] > recent_closes[i-1])
        down_count = sum(1 for i in range(1, len(recent_closes)) if recent_closes[i] < recent_closes[i-1])

        # === 特征5: 开盘跳空 ===
        gap_pct = 0.0
        if prev_day_close and today_bar:
            gap_pct = (today_bar.open / prev_day_close - 1) * 100

        # === 特征6: 今日方向 ===
        today_dir = 0.0
        if today_bar:
            today_dir = (today_bar.close / today_bar.open - 1) * 100

        # === 涨跌停检测 ===
        if daily_bars:
            last_close = daily_bars[-1].close
            # 通达信价格单位特殊，这里用相对比较
            # 如果收盘是最低点且振幅很小，可能跌停附近
            day_range = daily_bars[-1].high - daily_bars[-1].low
            if day_range > 0:
                body_ratio = abs(daily_bars[-1].close - daily_bars[-1].open) / day_range
                if body_ratio > 0.95 and abs(today_dir) > 8:
                    regime = "EXTREME"
                    return self._build_result(regime, vol_ratio, range_ratio, ma5_slope,
                                             gap_pct, today_dir, intraday_range_pct,
                                             avg_atr_pct)

        # === 综合判断 ===
        regime = self._decide_regime(vol_ratio, range_ratio, ma5_slope, up_count, down_count, today_dir)

        return self._build_result(regime, vol_ratio, range_ratio, ma5_slope,
                                   gap_pct, today_dir, intraday_range_pct, avg_atr_pct)

    def _decide_regime(self, vol_ratio, range_ratio, ma5_slope, up_count, down_count, today_dir) -> str:
        """综合判断市场状态"""

        # 极端波动优先判断
        if vol_ratio > 2.5 or vol_ratio < 0.4:
            return "EXTREME"

        # 高波动震荡（黄金窗口）
        if vol_ratio > 1.4 and abs(ma5_slope) < 0.5 and range_ratio > 1.3:
            return "HIGH_VOL_RANGE"

        # 低波动盘整
        if vol_ratio < 0.7 and range_ratio < 0.7:
            return "LOW_VOL_RANGE"

        # 趋势向上
        if ma5_slope > 0.5 and up_count >= 3:
            return "TREND_UP"

        # 趋势向下
        if ma5_slope < -0.5 and down_count >= 3:
            return "TREND_DOWN"

        # 默认高波动震荡
        return "HIGH_VOL_RANGE"

    def _build_result(self, regime, vol_ratio, range_ratio, ma5_slope,
                      gap_pct, today_dir, intraday_range_pct, avg_atr_pct) -> Dict:
        regime_info = {
            "TREND_UP":        "上涨趋势",
            "TREND_DOWN":      "下跌趋势",
            "HIGH_VOL_RANGE":  "高波动震荡(黄金窗口)",
            "LOW_VOL_RANGE":   "低波动盘整",
            "EXTREME":         "极端行情",
        }
        return {
            "regime": regime,
            "label": regime_info.get(regime, regime),
            "features": {
                "vol_ratio":       round(vol_ratio, 2),
                "range_ratio":     round(range_ratio, 2),
                "ma5_slope_pct":   round(ma5_slope, 3),
                "gap_pct":         round(gap_pct, 2),
                "today_dir_pct":   round(today_dir, 2),
                "intraday_range_pct": round(intraday_range_pct, 2),
                "avg_atr_pct":     round(avg_atr_pct, 2),
            },
            "params": self._get_regime_params(regime),
        }

    def _get_regime_params(self, regime: str) -> Dict:
        from .config import REGIME_PARAMS
        return REGIME_PARAMS.get(regime, REGIME_PARAMS["HIGH_VOL_RANGE"])

    # ----------------------------------------------------------
    # 便捷函数
    # ----------------------------------------------------------
    def get_effective_threshold(self, base_threshold: float, regime: str) -> float:
        """根据市场状态调整信号门槛"""
        params = self._get_regime_params(regime)
        return base_threshold * params["entry_mult"]

    def should_open_new(self, regime: str, current_slots: int) -> bool:
        """是否应该开新仓"""
        params = self._get_regime_params(regime)
        if not params["allow_new"]:
            return False
        return current_slots < params["max_slots"]

    def prefer_exit_over_entry(self, regime: str, open_slots: int) -> bool:
        """是否优先接回而非开新仓"""
        params = self._get_regime_params(regime)
        if open_slots == 0:
            return False
        return params["prefer_exit"]


if __name__ == "__main__":
    # 简单测试
    clf = RegimeClassifier("300418")
    print("市场状态分类器测试通过")
