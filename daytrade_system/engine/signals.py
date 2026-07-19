"""
做T信号生成器 v2 — VWAP深度整合版
基于多维度指标（VWAP+RSI+MACD+盘口+支撑压力）综合判断正T/倒T机会
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from engine.indicators import (
    KBar, QuoteSnapshot, SupportResistance,
    calc_ma, calc_macd, calc_atr, find_support_resistance,
    calc_intraday_profile, calc_money_flow, calc_volume_ratio,
    detect_divergence, get_expected_range, calc_bollinger,
    calc_vwap_bands, calc_vwap_position_signal, calc_rsi,
    get_rsi_signal, analyze_order_book, calc_cumulative_delta
)


@dataclass
class TradeSignal:
    """做T交易信号"""
    stock: str
    direction: str          # "正T" / "倒T" / "观望"
    confidence: int         # 1-5 星
    entry_zone: Tuple[float, float]
    stop_loss: float
    target: float
    reasons: List[str]
    risk_level: str         # "低" / "中" / "高"


def _check_reverse_t_signal(quote: QuoteSnapshot, daily_bars: List[KBar],
                             min5_bars: List[KBar], sr: SupportResistance,
                             range_info: Dict, profile: Dict) -> Optional[Dict]:
    """
    倒T信号检测（先卖后买）
    条件权重: VWAP极端高估(2分) > 压力位(1分) > MACD顶背离(2分) > RSI超买(1分) > 盘口(1分)
    """
    reasons = []
    confidence = 0

    closes = [b.close for b in daily_bars]

    # === NEW: VWAP极端位置检测 ===
    if min5_bars:
        vwap_bands = calc_vwap_bands(min5_bars)
        vwap_pos = vwap_bands.get("position", "")
        vwap_slope = vwap_bands.get("vwap_slope", "flat")

        if "极度高估" in vwap_pos:
            confidence += 2
            reasons.append(f"VWAP极度高估({vwap_bands['vwap']})，回归概率极大")
        elif "偏强" in vwap_pos and vwap_slope == "falling":
            confidence += 1
            reasons.append(f"VWAP高位({vwap_bands['vwap']})且VWAP斜率下行→顶位确认")

    # === NEW: RSI超买检测 ===
    if len(closes) >= 7:
        rsi_values = calc_rsi(closes, 6)
        rsi_now = rsi_values[-1]
        if rsi_now is not None:
            rsi_sig = get_rsi_signal(rsi_now)
            if rsi_sig["score"] >= 15:  # RSI > 70
                confidence += rsi_sig["score"] // 10
                reasons.append(f"RSI={rsi_now}({rsi_sig['zone']})→回调概率高")

    # 条件：价格接近压力位 R1
    dist_to_r1 = (sr.r1 / quote.now - 1) * 100
    if dist_to_r1 <= 2.0:
        confidence += 1
        reasons.append(f"接近R1压力位 {sr.r1}（距现价{dist_to_r1:.1f}%）")
    elif dist_to_r1 <= 4.0:
        reasons.append(f"略低于R1 {sr.r1}（距{dist_to_r1:.1f}%），关注突破")

    # 空头排列
    ma5 = calc_ma(closes, 5)
    ma20 = calc_ma(closes, 20)
    if ma5[-1] and ma20[-1] and ma5[-1] < ma20[-1]:
        confidence += 1
        reasons.append(f"MA5({ma5[-1]:.2f}) < MA20({ma20[-1]:.2f})，空头排列")

    # MACD顶背离
    _, _, hist = calc_macd(closes)
    divergence = detect_divergence(daily_bars, hist)
    if divergence == "顶背离":
        confidence += 2
        reasons.append("MACD 顶背离信号")

    # 盘口卖压
    mf = calc_money_flow(quote)
    if mf["inside_ratio"] > 55:
        confidence += 1
        reasons.append(f"内盘占比{mf['inside_ratio']}%，主动卖出偏多")

    # NEW: 订单簿分析
    ob = analyze_order_book(quote.bsp)
    if ob["direction"] in ("卖盘碾压", "卖盘偏强"):
        confidence += 1
        reasons.append(f"盘口: {ob['direction']}(买卖比{ob['buy_pressure']}/{ob['sell_pressure']})")

    # VWAP均价偏离（弱势运行）
    if profile.get("avg_deviation", 0) < -1.0:
        confidence += 1
        reasons.append(f"低于VWAP {abs(profile['avg_deviation']):.1f}%，弱势运行")

    # 确定入场和止损
    if confidence >= 3:
        entry_high = min(sr.r1, quote.now * 1.02)
        entry_low = quote.now
        stop = sr.r1 * 1.015
        target = sr.s1
        risk = "中" if confidence >= 4 else "高"

        return {
            "direction": "倒T（先卖后买）",
            "confidence": min(confidence, 5),
            "entry_zone": (entry_low, entry_high),
            "stop_loss": round(stop, 2),
            "target": round(target, 2),
            "reasons": reasons,
            "risk_level": risk
        }

    return None


def _check_long_t_signal(quote: QuoteSnapshot, daily_bars: List[KBar],
                          min5_bars: List[KBar], sr: SupportResistance,
                          range_info: Dict, profile: Dict) -> Optional[Dict]:
    """
    正T信号检测（先买后卖）
    条件权重: VWAP极度低估(2分) > 支撑位(2分) > MACD底背离(2分) > RSI超卖(1分) > 盘口买入(1分)
    """
    reasons = []
    confidence = 0

    closes = [b.close for b in daily_bars]

    # === NEW: VWAP极端位置检测 ===
    if min5_bars:
        vwap_bands = calc_vwap_bands(min5_bars)
        vwap_pos = vwap_bands.get("position", "")
        vwap_slope = vwap_bands.get("vwap_slope", "flat")

        if "极度低估" in vwap_pos:
            confidence += 2
            reasons.append(f"VWAP极度低估({vwap_bands['vwap']})，回归概率极大")
        elif "偏弱" in vwap_pos and vwap_slope == "rising":
            confidence += 1
            reasons.append(f"VWAP低位({vwap_bands['vwap']})且VWAP斜率上行→底部确认")

    # === NEW: RSI超卖检测 ===
    if len(closes) >= 7:
        rsi_values = calc_rsi(closes, 6)
        rsi_now = rsi_values[-1]
        if rsi_now is not None:
            rsi_sig = get_rsi_signal(rsi_now)
            if rsi_sig["score"] >= 15:  # RSI < 30
                confidence += rsi_sig["score"] // 10
                reasons.append(f"RSI={rsi_now}({rsi_sig['zone']})→反弹概率高")

    # 接近支撑位
    dist_to_s1 = (quote.now / sr.s1 - 1) * 100
    dist_to_s2 = (quote.now / sr.s2 - 1) * 100

    if dist_to_s1 <= 2.0:
        confidence += 2
        reasons.append(f"接近S1支撑 {sr.s1}（距{dist_to_s1:.1f}%）")
    elif dist_to_s2 <= 3.0:
        confidence += 1
        reasons.append(f"接近S2强支撑 {sr.s2}（距{dist_to_s2:.1f}%）")

    if confidence == 0 and "极度低估" not in (vwap_bands.get("position", "") if min5_bars else ""):
        return None  # 不接近任何支撑，不考虑正T

    # MACD底背离
    _, _, hist = calc_macd(closes)
    divergence = detect_divergence(daily_bars, hist)
    if divergence == "底背离":
        confidence += 2
        reasons.append("MACD 底背离信号")

    # 支撑位放量
    vol_ratio = calc_volume_ratio(daily_bars)
    if vol_ratio > 1.2:
        confidence += 1
        reasons.append(f"量比{vol_ratio:.1f}，支撑位放量")

    # 盘口买盘
    mf = calc_money_flow(quote)
    if mf["outside_ratio"] > 52:
        confidence += 1
        reasons.append(f"外盘占比{mf['outside_ratio']}%，主动买入增加")

    # NEW: 订单簿分析
    ob = analyze_order_book(quote.bsp)
    if ob["direction"] in ("买盘碾压", "买盘偏强"):
        confidence += 1
        reasons.append(f"盘口: {ob['direction']}(买卖比{ob['buy_pressure']}/{ob['sell_pressure']})")

    # 超卖
    if len(daily_bars) >= 6:
        pct_5d = (closes[-1] / closes[-6] - 1) * 100
        if pct_5d < -10:
            confidence += 1
            reasons.append(f"5日跌幅{pct_5d:.1f}%，超卖")

    if confidence >= 2:
        entry_low = max(sr.s1, quote.now * 0.98)
        entry_high = quote.now
        stop = sr.s2 * 0.985
        target = sr.r1
        risk = "中" if confidence >= 3 else "高"

        return {
            "direction": "正T（先买后卖）",
            "confidence": min(confidence, 5),
            "entry_zone": (round(entry_low, 2), round(entry_high, 2)),
            "stop_loss": round(stop, 2),
            "target": round(target, 2),
            "reasons": reasons,
            "risk_level": risk
        }

    return None


def generate_signals(quote: QuoteSnapshot, daily_bars: List[KBar],
                     min5_bars: List[KBar]) -> List[Dict]:
    """
    综合生成做T信号（VWAP+RSI增强版）
    """
    sr = find_support_resistance(daily_bars, quote.now)
    range_info = get_expected_range(quote, daily_bars)
    profile = calc_intraday_profile(min5_bars, quote.now)

    signals = []

    # 检测倒T信号
    reverse = _check_reverse_t_signal(quote, daily_bars, min5_bars, sr, range_info, profile)
    if reverse:
        signals.append(reverse)

    # 检测正T信号
    long_t = _check_long_t_signal(quote, daily_bars, min5_bars, sr, range_info, profile)
    if long_t:
        signals.append(long_t)

    # === NEW: VWAP独立信号（更敏感的短线信号） ===
    if min5_bars and not signals:
        vwap_bands = calc_vwap_bands(min5_bars)
        vwap_sig = calc_vwap_position_signal(
            vwap_bands, min5_bars[-1].close, vwap_bands["vwap_slope"]
        )
        if vwap_sig["score"] >= 15:
            direction = "倒T（先卖后买）" if "倒T" in vwap_sig["signal"] else "正T（先买后卖）"
            signals.append({
                "direction": direction,
                "confidence": min(vwap_sig["score"] // 10, 3),
                "entry_zone": (round(vwap_bands["sigma1_lower"], 2), round(vwap_bands["sigma1_upper"], 2)),
                "stop_loss": round(vwap_bands["sigma2_lower"], 2),
                "target": round(vwap_bands["vwap"], 2),
                "reasons": [f"VWAP信号: {vwap_sig['signal']} ({vwap_sig['suggestion']})"],
                "risk_level": "中"
            })

    # 无明确信号
    if not signals:
        signals.append({
            "direction": "观望",
            "confidence": 0,
            "entry_zone": (0, 0),
            "stop_loss": 0,
            "target": 0,
            "reasons": [f"现价{quote.now}位于支撑{sr.s1}和压力{sr.r1}之间，缺乏明确方向"],
            "risk_level": "无"
        })

    signals.sort(key=lambda x: x["confidence"], reverse=True)
    return signals


def score_t_quality(quote: QuoteSnapshot, daily_bars: List[KBar],
                    min5_bars: List[KBar] = None) -> Dict:
    """
    评估该股当日做T适宜度（0-100分）V2 — 加入VWAP和盘口因素
    """
    score = 0
    details = []

    # 1. 流动性（换手率）
    hsl = quote.hsl
    if hsl > 10:
        score += 20; details.append(f"换手率{hsl:.1f}%→极佳(+20)")
    elif hsl > 5:
        score += 15; details.append(f"换手率{hsl:.1f}%→良好(+15)")
    elif hsl > 2:
        score += 10; details.append(f"换手率{hsl:.1f}%→一般(+10)")
    else:
        score += 3; details.append(f"换手率{hsl:.1f}%→偏低(+3)")

    # 2. 日内振幅预期
    range_info = get_expected_range(quote, daily_bars)
    expected_range = range_info["expected_range_pct"]
    if expected_range > 5:
        score += 25; details.append(f"预期振幅{expected_range:.1f}%→大波动(+25)")
    elif expected_range > 3:
        score += 18; details.append(f"预期振幅{expected_range:.1f}%→中等波动(+18)")
    elif expected_range > 2:
        score += 10; details.append(f"预期振幅{expected_range:.1f}%→小波动(+10)")
    else:
        score += 5; details.append(f"预期振幅{expected_range:.1f}%→窄幅(+5)")

    # 3. 价格位置（距20日均线）
    closes = [b.close for b in daily_bars]
    ma20 = calc_ma(closes, 20)
    if ma20[-1]:
        dist_to_ma20 = (quote.now / ma20[-1] - 1) * 100
        if abs(dist_to_ma20) > 15:
            score += 10; details.append(f"距MA20偏离{dist_to_ma20:.1f}%→极端位置(+10)")
        elif abs(dist_to_ma20) > 8:
            score += 15; details.append(f"距MA20偏离{dist_to_ma20:.1f}%→趋势明确(+15)")
        else:
            score += 5; details.append(f"距MA20偏离{dist_to_ma20:.1f}%→均线附近(+5)")

    # 4. 趋势方向
    if len(closes) >= 5:
        ma5 = calc_ma(closes, 5)
        if ma5[-1] and ma20[-1]:
            trend = "多头" if ma5[-1] > ma20[-1] else "空头"
            if trend == "空头":
                score += 15; details.append("空头趋势→有利于倒T(+15)")
            else:
                score += 10; details.append("多头趋势→有利于正T(+10)")

    # 5. 量能活跃度
    vol_ratio = calc_volume_ratio(daily_bars)
    if vol_ratio > 1.5:
        score += 15; details.append(f"量比{vol_ratio:.1f}→量能充沛(+15)")
    elif vol_ratio > 0.8:
        score += 10; details.append(f"量比{vol_ratio:.1f}→正常(+10)")
    else:
        score += 5; details.append(f"量比{vol_ratio:.1f}→缩量(+5)")

    # 6. 流通市值
    ltgb = quote.ltgb / 10000
    if ltgb < 5:
        score += 15; details.append(f"流通盘{ltgb:.1f}亿股→小盘易波动(+15)")
    elif ltgb < 20:
        score += 10; details.append(f"流通盘{ltgb:.1f}亿股→中盘(+10)")
    else:
        score += 5; details.append(f"流通盘{ltgb:.1f}亿股→大盘(+5)")

    # === NEW: 7. VWAP位置（做T信号质量） ===
    if min5_bars and len(min5_bars) >= 5:
        vwap_bands = calc_vwap_bands(min5_bars)
        vwap_sig = calc_vwap_position_signal(vwap_bands, min5_bars[-1].close, vwap_bands["vwap_slope"])
        vwap_score = vwap_sig["score"]
        if vwap_score >= 20:
            score += 15; details.append(f"VWAP极端偏离→回归交易机会(+15)")
        elif vwap_score >= 10:
            score += 10; details.append(f"VWAP偏离→关注均值回归(+10)")
        elif vwap_score >= 5:
            score += 5; details.append(f"VWAP附近→方向待定(+5)")

    # === NEW: 8. 盘口活跃度 ===
    ob = analyze_order_book(quote.bsp)
    if ob["direction"] in ("买盘碾压", "卖盘碾压"):
        score += 10; details.append(f"盘口极端失衡({ob['direction']})→易触发(+10)")
    elif ob["direction"] in ("买盘偏强", "卖盘偏强"):
        score += 5; details.append(f"盘口偏斜({ob['direction']})→关注方向(+5)")
    if ob["depth"] == "厚":
        score += 5; details.append(f"盘口厚实→流动性好(+5)")

    # 综合评级
    if score >= 80:
        rating = "★★★★★ 极佳做T标的"
    elif score >= 65:
        rating = "★★★★ 良好做T标的"
    elif score >= 50:
        rating = "★★★ 可做T"
    elif score >= 35:
        rating = "★★ 勉强可做"
    else:
        rating = "★ 不建议做T"

    return {
        "score": min(score, 100),
        "rating": rating,
        "details": details
    }
