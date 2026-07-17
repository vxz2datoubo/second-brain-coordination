"""signal_pipeline.py — 重建版信号评分引擎

核心设计原则（数据驱动重建）：
  1. 评分必须基于历史分位数，而非固定阈值
  2. 6个因子各自独立输出0-100分，物理含义清晰
  3. 信号总分40-75分对应可交易区间（而不是68分一线）
  4. 权重可调，默认按配置文件中各因子的weight融合
  5. 输出包含完整的决策理由，供人工参考

Factor评分设计（重建版）：
  F1: VWAP偏离度 → 基于σ分位数，2σ=90分
  F2: RSI极值   → 80/20分位=超买/超卖
  F3: 量价背离   → 价格新高但成交量萎缩=卖
  F4: 动量衰竭   → 连续递减或顶部结构
  F5: Delta转向  → 累积Delta由正转负
  F6: 缺口偏离   → 开盘价偏离前收的比例
"""

import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from engine.indicators import KBar, calc_vwap_bands, calc_rsi, calc_cumulative_delta, calc_ma


@dataclass
class FactorResult:
    name: str
    score: float       # 0-100
    weight: float
    signals: List[str] # 中文描述
    raw_value: float   # 原始值（方便调试）


@dataclass
class SignalResult:
    code: str
    total_score: float
    sell_score: float
    buy_score: float
    confidence: str
    regime: str
    factors: Dict[str, FactorResult]
    entry_price: float
    reason: str
    details: List[str]
    can_short: bool
    can_long: bool
    suggestion: str  # 操作建议


# ============================================================
# 信号管道
# ============================================================

class SignalPipeline:

    def __init__(self, code: str, config: "StockConfig"):
        self.code = code
        self.cfg = config
        self.weights = [
            config.f1_vwap_weight,
            config.f2_rsi_weight,
            config.f3_volprofile_weight,
            config.f4_momentum_weight,
            config.f5_delta_weight,
            config.f6_gap_weight,
        ]

    # ============================================================
    # 主入口
    # ============================================================

    def evaluate(self, current_price: float, min5_bars: List[KBar],
                 daily_bars: List[KBar], prev_close: float = None,
                 regime: str = "HIGH_VOL_RANGE") -> SignalResult:
        """
        完整信号评估
        """
        if not min5_bars or len(min5_bars) < 5:
            return self._empty_result(current_price, regime, "数据不足")

        factor_results = {}
        sell_points = []   # 各因子贡献的卖分
        buy_points = []    # 各因子贡献的买分

        # --- F1: VWAP偏离 ---
        f1 = self._calc_f1(current_price, min5_bars, daily_bars)
        factor_results["F1"] = f1
        if any("卖" in s for s in f1.signals):
            sell_points.append((f1.score, f1.weight))
        elif any("买" in s for s in f1.signals):
            buy_points.append((f1.score, f1.weight))

        # --- F2: RSI ---
        f2 = self._calc_f2(current_price, min5_bars)
        factor_results["F2"] = f2
        if any("卖" in s for s in f2.signals):
            sell_points.append((f2.score, f2.weight))
        elif any("买" in s for s in f2.signals):
            buy_points.append((f2.score, f2.weight))

        # --- F3: 量价剖面 ---
        f3 = self._calc_f3(current_price, min5_bars, daily_bars)
        factor_results["F3"] = f3
        if any("卖" in s for s in f3.signals):
            sell_points.append((f3.score, f3.weight))
        elif any("买" in s for s in f3.signals):
            buy_points.append((f3.score, f3.weight))

        # --- F4: 动量衰竭 ---
        f4 = self._calc_f4(min5_bars)
        factor_results["F4"] = f4
        if any("卖" in s for s in f4.signals):
            sell_points.append((f4.score, f4.weight))

        # --- F5: Delta转向 ---
        f5 = self._calc_f5(min5_bars)
        factor_results["F5"] = f5
        if any("卖" in s for s in f5.signals):
            sell_points.append((f5.score, f5.weight))

        # --- F6: 隔夜缺口 ---
        f6 = self._calc_f6(current_price, prev_close, min5_bars)
        factor_results["F6"] = f6
        if any("卖" in s for s in f6.signals):
            sell_points.append((f6.score, f6.weight))
        elif any("买" in s for s in f6.signals):
            buy_points.append((f6.score, f6.weight))

        # --- 总分 ---
        total_weight = sum(self.weights)
        total_score = sum(f.score * f.weight for f in factor_results.values()) / total_weight
        # 归一化：除以活跃因子总权重（1个强因子=100分，2个强因子=100分）
        sell_active_w = sum(w for _, w in sell_points)
        buy_active_w  = sum(w for _, w in buy_points)
        sell_score = sum(s * w for s, w in sell_points) / sell_active_w if sell_points else 0
        buy_score  = sum(s * w for s, w in buy_points)  / buy_active_w  * 100 if buy_points  else 0
        total_score = min(max(total_score, 0.0), 100.0)

        # --- 置信度 ---
        from .config import get_confidence
        conf = get_confidence(total_score)

        # --- 可交易方向 ---
        # 倒T（先卖后买）：蓝色逆势/昆仑趋势，sell_score > 25
        # 正T（先买后卖）：仅在buy_score > 40时考虑
        can_short = sell_score > 25
        can_long = buy_score > 40 and self.cfg.allow_long_t

        # --- 一句话理由 ---
        top_factors = sorted(
            [(n, f) for n, f in factor_results.items() if f.score > 0],
            key=lambda x: -x[1].score
        )[:3]
        reason = " + ".join(f"{n}({f.score:.0f})" for n, f in top_factors) if top_factors else "无明显信号"

        # --- 操作建议 ---
        suggestion = self._make_suggestion(sell_score, buy_score, total_score, conf.grade)

        details = []
        for name, fr in factor_results.items():
            if fr.score > 0 and fr.signals:
                for sig in fr.signals:
                    details.append(f"[{name}] {sig} (分值:{fr.score:.0f} 原始:{fr.raw_value})")

        return SignalResult(
            code=self.code,
            total_score=round(total_score, 1),
            sell_score=round(sell_score, 1),
            buy_score=round(buy_score, 1),
            confidence=conf.grade,
            regime=regime,
            factors=factor_results,
            entry_price=round(current_price, 2),
            reason=reason,
            details=details,
            can_short=can_short,
            can_long=can_long,
            suggestion=suggestion,
        )

    def _empty_result(self, price, regime, msg):
        from .config import get_confidence
        conf = get_confidence(0)
        return SignalResult(
            code=self.code, total_score=0, sell_score=0, buy_score=0,
            confidence=conf.grade, regime=regime,
            factors={}, entry_price=price, reason=msg,
            details=[], can_short=False, can_long=False, suggestion="数据不足",
        )

    def _make_suggestion(self, sell_score, buy_score, total_score, grade) -> str:
        if grade in ("A++", "A") and sell_score > 40:
            return "★★★ 强烈建议执行倒T卖出，信号质量极高"
        elif grade == "B" and sell_score > 30:
            return "★★ 可执行倒T，限额1笔，注意止损"
        elif grade == "C":
            return "★ 谨慎观察，信号质量一般，等待更清晰机会"
        else:
            return "— 暂不操作，信号不足"

    # ============================================================
    # F1: VWAP偏离（重建版：基于σ分位数）
    # ============================================================
    def _calc_f1(self, price: float, min5_bars: List[KBar],
                  daily_bars: List[KBar]) -> FactorResult:
        """
        VWAP偏离因子（重建）
        
        评分逻辑：
          1. 计算当日累积VWAP（量加权平均价）
          2. 计算偏离度 = (price - VWAP) / VWAP
          3. 基于历史5分K的偏离分布，计算当前偏离的百分位
          4. 越极端偏离，评分越高
        
        卖出信号：价格高于VWAP越多 → 超买 → 卖
        """
        if len(min5_bars) < 5:
            return FactorResult("F1", 0, self.weights[0], [], 0)

        bands = calc_vwap_bands(min5_bars)
        vwap = bands["vwap"]
        std = bands.get("std", 0)

        if vwap <= 0 or std <= 0:
            return FactorResult("F1", 0, self.weights[0], ["VWAP无效"], 0)

        # 计算当前σ偏离
        sigma = (price - vwap) / std
        
        # 转换为0-100分（用arctan压缩极端值）
        # sigma=0 → 0分，sigma=1 → ~50分，sigma=2 → ~80分，sigma=3 → ~90分
        # 负σ同理（买信号）
        score = min(100, abs(sigma) * 50)  # 线性但截断
        
        signals = []
        if sigma > 0:
            if sigma >= 2.0:
                signals.append(f"卖: 价格在VWAP+{sigma:.1f}σ极端高位(极度超买)")
                score = min(100, 70 + (sigma - 2) * 15)
            elif sigma >= 1.0:
                signals.append(f"卖: 价格在VWAP+{sigma:.1f}σ偏高")
            else:
                signals.append(f"卖: 价格略高于VWAP+{sigma:.1f}σ")
        elif sigma < 0:
            abs_sigma = abs(sigma)
            if abs_sigma >= 2.0:
                signals.append(f"买: 价格在VWAP-{abs_sigma:.1f}σ极端低位(极度超卖)")
            elif abs_sigma >= 1.0:
                signals.append(f"买: 价格在VWAP-{abs_sigma:.1f}σ偏低")
            else:
                signals.append(f"买: 价格略低于VWAP")

        # 趋势加成（VWAP斜率）
        slope = bands.get("vwap_slope", "flat")
        if sigma > 0.5 and slope == "rising":
            score = min(100, score * 1.15)
            signals.append("VWAP上行+延续加分")
        elif sigma < -0.5 and slope == "falling":
            score = min(100, score * 1.15)
            signals.append("VWAP下行+延续加分")

        return FactorResult("F1", round(score, 1), self.weights[0], signals, round(sigma, 3))

    # ============================================================
    # F2: RSI（重建版：基于分位数阈值）
    # ============================================================
    def _calc_f2(self, price: float, min5_bars: List[KBar]) -> FactorResult:
        """
        RSI均值回归因子（重建）
        
        评分逻辑：
          - RSI(6) > 80 → 极度超买 → 卖信号 90分
          - RSI(6) > 70 → 超买 → 卖信号 70分
          - RSI(6) 60-70 → 偏热 → 卖信号 40分
          - RSI(6) < 20 → 极度超卖 → 买信号 90分
          - RSI(6) < 30 → 超卖 → 买信号 70分
          - RSI(6) 30-40 → 偏冷 → 买信号 40分
        """
        closes = [b.close for b in min5_bars]
        if len(closes) < 7:
            return FactorResult("F2", 0, self.weights[1], ["数据不足"], 0)

        rsi_vals = calc_rsi(closes, period=6)
        rsi = rsi_vals[-1]
        if rsi is None:
            rsi = 50

        signals = []
        score = 0.0

        if rsi > 85:
            score = min(100, 90 + (rsi - 85) * 2)
            signals.append(f"卖: RSI={rsi:.0f}极度超买")
        elif rsi > 75:
            score = min(100, 70 + (rsi - 75) * 2)
            signals.append(f"卖: RSI={rsi:.0f}超买")
        elif rsi > 65:
            score = 40 + (rsi - 65) * 3
            signals.append(f"卖: RSI={rsi:.0f}偏热")
        elif rsi < 15:
            score = min(100, 90 + (25 - rsi) * 2)
            signals.append(f"买: RSI={rsi:.0f}极度超卖")
        elif rsi < 25:
            score = min(100, 70 + (35 - rsi) * 2)
            signals.append(f"买: RSI={rsi:.0f}超卖")
        elif rsi < 35:
            score = 40 + (45 - rsi) * 3
            signals.append(f"买: RSI={rsi:.0f}偏冷")

        return FactorResult("F2", round(score, 1), self.weights[1], signals, round(rsi, 1))

    # ============================================================
    # F3: 量价剖面（重建版：基于价格位置）
    # ============================================================
    def _calc_f3(self, price: float, min5_bars: List[KBar],
                  daily_bars: List[KBar]) -> FactorResult:
        """
        量价剖面因子（重建）
        
        核心思想：
          - 日内高量区 = 主力成交区，价格在此区间偏弱则卖
          - 价格在日内高位+成交量萎缩 = 主力出货 → 卖信号
          - 价格在日内低位+成交量放大 = 主力吸筹 → 买信号
        """
        if len(min5_bars) < 6:
            return FactorResult("F3", 0, self.weights[2], ["数据不足"], 0)

        # 当日高低点
        day_high = max(b.high for b in min5_bars)
        day_low = min(b.low for b in min5_bars)
        day_range = day_high - day_low
        if day_range == 0:
            return FactorResult("F3", 0, self.weights[2], ["无波动"], 0)

        # 价格位置（0=低点，100=高点）
        price_pos = (price - day_low) / day_range * 100

        # 成交量分布
        recent_6 = min5_bars[-6:]
        vol_sum = sum(b.volume for b in recent_6)
        if vol_sum == 0:
            return FactorResult("F3", 0, self.weights[2], ["无成交量"], 0)

        # 最近3根成交量 vs 前3根
        last_3_vol = sum(b.volume for b in recent_6[-3:])
        prev_3_vol = sum(b.volume for b in recent_6[:3])
        vol_ratio = last_3_vol / prev_3_vol if prev_3_vol > 0 else 1.0

        signals = []
        score = 0.0

        # 价格在高位 + 成交量萎缩 = 主力出货
        if price_pos > 80 and vol_ratio < 0.8:
            score = 60 + (price_pos - 80) * 2
            signals.append(f"卖: 价格在高位{price_pos:.0f}%+量缩{vol_ratio:.1f}x(主力出货嫌疑)")
        elif price_pos > 70 and vol_ratio < 0.9:
            score = 40 + (price_pos - 70)
            signals.append(f"卖: 价格偏高{price_pos:.0f}%+量能减弱")
        elif price_pos > 60:
            score = (price_pos - 60) * 1.5
            signals.append(f"卖: 价格在日高{price_pos:.0f}%")

        # 价格在低位 + 成交量放大 = 主力吸筹
        elif price_pos < 20 and vol_ratio > 1.2:
            score = 60 + (20 - price_pos) * 2
            signals.append(f"买: 价格在低位{price_pos:.0f}%+量增{vol_ratio:.1f}x(主力吸筹嫌疑)")
        elif price_pos < 30 and vol_ratio > 1.1:
            score = 40 + (30 - price_pos)
            signals.append(f"买: 价格偏低{price_pos:.0f}%+量能增强")

        # 距日内高点的回撤幅度（用于蓝色逆势抄底）
        if day_high > 0:
            drawdown = (day_high - price) / day_high * 100
            if drawdown > self.cfg.require_intraday_high_pct:
                score = max(score, 30 + drawdown)
                if "卖" not in "".join(signals):
                    signals.append(f"回撤{drawdown:.1f}%提供买入机会")

        return FactorResult("F3", round(score, 1), self.weights[2], signals, round(price_pos, 1))

    # ============================================================
    # F4: 动量衰竭（重建版）
    # ============================================================
    def _calc_f4(self, min5_bars: List[KBar]) -> FactorResult:
        """
        动量衰竭因子（重建）
        
        核心思想：
          - 最近3-5根K线的高点逐级下降 = 顶部结构 → 卖
          - 最近3-5根K线的低点逐级下降 = 下跌中继 → 不卖（不买）
          - 价格在上升后出现第一根下跌K线 = 顶部反转前兆 → 卖
        """
        if len(min5_bars) < 5:
            return FactorResult("F4", 0, self.weights[3], ["数据不足"], 0)

        recent = min5_bars[-5:]
        highs = [b.high for b in recent]
        lows  = [b.low  for b in recent]
        closes = [b.close for b in recent]
        
        signals = []
        score = 0.0

        # --- 检测1: 顶部结构（高点逐级下降）---
        descending_highs = all(highs[i] < highs[i-1] for i in range(1, len(highs)))
        if descending_highs:
            score = 65
            signals.append("卖: 5K高点逐级下降(顶部结构)")

        # --- 检测2: 涨后首跌（前三根涨，最近一根跌）---
        if len(recent) >= 4:
            up_then_down = (
                closes[0] < closes[1] < closes[2] and  # 连续上涨
                closes[3] < closes[2]                  # 第一根下跌
            )
            if up_then_down:
                score = max(score, 60)
                signals.append("卖: 连续上涨后出现第一根下跌(顶部反转前兆)")

        # --- 检测3: 量价背离（价格新低但成交量萎缩 = 主力不砸盘 = 见底信号不卖）---
        if len(min5_bars) >= 7:
            last_3_vol = sum(b.volume for b in min5_bars[-3:])
            prev_3_vol = sum(b.volume for b in min5_bars[-6:-3])
            if prev_3_vol > 0 and last_3_vol / prev_3_vol < 0.6:
                # 价格下跌但量能萎缩 = 主力不出货 = 可能是最后一跌
                if closes[-1] < closes[-4]:
                    score = max(score, 30)
                    signals.append("量价背离: 价格跌但量缩(主力未出货)")

        # --- 检测4: Delta衰竭 ---
        cdv = calc_cumulative_delta(min5_bars)
        if len(cdv) >= 3:
            # Delta从正转负（买入主导→卖出主导）
            if cdv[-3] > 0 and cdv[-2] > 0 and cdv[-1] < 0:
                score = max(score, 55)
                signals.append("卖: Delta由正转负(主力撤退)")

        return FactorResult("F4", round(min(score, 100), 1), self.weights[3], signals, 0)

    # ============================================================
    # F5: Delta转向（重建版）
    # ============================================================
    def _calc_f5(self, min5_bars: List[KBar]) -> FactorResult:
        """
        累积Delta因子（重建）
        
        核心思想：
          - Delta由正转负 → 主力从买入变成卖出 → 卖
          - Delta持续为负且加速 → 卖压加重 → 卖
          - Delta触及极值后回升 → 反弹可能 → 不卖
        """
        if len(min5_bars) < 4:
            return FactorResult("F5", 0, self.weights[4], ["数据不足"], 0)

        cdv = calc_cumulative_delta(min5_bars)
        if not cdv or len(cdv) < 4:
            return FactorResult("F5", 0, self.weights[4], ["数据不足"], 0)

        current = cdv[-1]
        prev1 = cdv[-2]
        prev2 = cdv[-3] if len(cdv) >= 3 else 0
        prev3 = cdv[-4] if len(cdv) >= 4 else 0

        signals = []
        score = 0.0

        # Delta方向判断
        if current < 0 and prev1 > 0:
            # 正转负（最强烈的卖信号之一）
            score = 70
            signals.append(f"卖: Delta由正转负({prev1:.0f}→{current:.0f})")

        elif current < 0 and current < prev1 < prev2:
            # 持续加速下跌
            score = 50
            signals.append(f"卖: Delta持续下行{current:.0f}(加速)")

        elif current < 0 and abs(current) > abs(prev1) * 1.5:
            # 负值绝对值快速扩大
            score = 45
            signals.append(f"卖: Delta负值扩大{current:.0f}(卖压加重)")

        elif current > 0 and prev1 < 0 and abs(current) > abs(prev1):
            # 负转正（买盘回归 = 不卖）
            score = 20
            signals.append(f"买: Delta由负转正({prev1:.0f}→{current:.0f})")

        return FactorResult("F5", round(score, 1), self.weights[4], signals, round(current, 0))

    # ============================================================
    # F6: 隔夜缺口（重建版）
    # ============================================================
    def _calc_f6(self, price: float, prev_close: float,
                 min5_bars: List[KBar]) -> FactorResult:
        """
        隔夜缺口因子（重建）
        
        核心思想：
          - 高开 > 1%：假突破概率高 → 卖
          - 高开 > 2%：极端 → 卖 90分
          - 低开 > 1%：恐慌见底概率高 → 买（仅蓝色）
          - 低开 > 2%：极端 → 买 90分（仅蓝色）
          - 缺口是否已回补（回补后降低分数）
        """
        if not prev_close or not min5_bars:
            return FactorResult("F6", 0, self.weights[5], ["无前收/无数据"], 0)

        open_price = min5_bars[0].open if min5_bars else price
        gap_from_close = (open_price / prev_close - 1) * 100  # 跳空%
        current_gap = (price / open_price - 1) * 100          # 当日回补%

        signals = []
        score = 0.0

        if gap_from_close > 3.0:
            score = 90
            signals.append(f"卖: 高开{gap_from_close:.1f}%极端跳空(假突破概率极高)")
        elif gap_from_close > 2.0:
            score = 75
            signals.append(f"卖: 高开{gap_from_close:.1f}%大幅跳空")
        elif gap_from_close > 1.0:
            score = 55
            signals.append(f"卖: 高开{gap_from_close:.1f}%跳空高开")
        elif gap_from_close > 0.5:
            score = 35
            signals.append(f"卖: 高开{gap_from_close:.1f}%小幅高开")
        
        elif gap_from_close < -3.0:
            score = 90
            signals.append(f"买: 低开{gap_from_close:.1f}%极度恐慌(见底概率高)")
        elif gap_from_close < -2.0:
            score = 75
            signals.append(f"买: 低开{gap_from_close:.1f}%大幅低开")
        elif gap_from_close < -1.0:
            score = 55
            signals.append(f"买: 低开{gap_from_close:.1f}%低开")
        elif gap_from_close < -0.5:
            score = 35
            signals.append(f"买: 低开{gap_from_close:.1f}%小幅低开")

        # 缺口回补惩罚（已回补超过80%则降低分数）
        if abs(gap_from_close) > 0.5 and abs(current_gap) > abs(gap_from_close) * 0.8:
            score *= 0.6
            signals.append(f"缺口已回补{abs(current_gap):.1f}%，分数降低")

        # 缺口方向的顺势延续（高开后继续涨 = 趋势确认，少卖）
        if gap_from_close > 0.5 and current_gap > 0:
            score *= 0.8
            signals.append("高开后继续涨，缺口有效，分数降低")

        return FactorResult("F6", round(score, 1), self.weights[5], signals, round(gap_from_close, 2))


# ============================================================
# 快捷工具
# ============================================================

def format_signal(signal: SignalResult, stock_name: str) -> str:
    """格式化信号输出"""
    lines = [
        f"{'='*55}",
        f"  {stock_name}({signal.code}) 信号评估",
        f"  总分: {signal.total_score:.0f}  置信度: {signal.confidence}",
        f"  卖分: {signal.sell_score:.0f}  买分: {signal.buy_score:.0f}",
        f"  Regime: {signal.regime}",
        f"{'='*55}",
    ]
    for name, fr in signal.factors.items():
        if fr.score > 0:
            for s in fr.signals:
                lines.append(f"  [{name}] {s} (分:{fr.score:.0f} 原始:{fr.raw_value})")
    lines.append(f"{'>'*55}")
    lines.append(f"  结论: {signal.reason}")
    lines.append(f"  建议: {signal.suggestion}")
    if signal.can_short:
        lines.append(f"  → 可执行倒T（先卖后买）")
    if signal.can_long:
        lines.append(f"  → 可执行正T（先买后卖）")
    lines.append(f"{'='*55}")
    return "\n".join(lines)
