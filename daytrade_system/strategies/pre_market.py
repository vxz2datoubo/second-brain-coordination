"""
盘前策略模块
每日盘前综合分析，生成做T策略
"""

from typing import Dict, List
from engine.data_loader import load_stock_data
from engine.indicators import (
    QuoteSnapshot, KBar, find_support_resistance,
    get_expected_range, calc_ma, calc_macd, calc_bollinger,
    calc_volume_ratio, calc_vwap_bands, calc_vwap_position_signal,
    calc_rsi, get_rsi_signal, analyze_order_book
)
from engine.signals import generate_signals, score_t_quality


def pre_market_analysis(quote: QuoteSnapshot, daily_bars: List[KBar],
                         hourly_bars: List[KBar], min5_bars: List[KBar] = None) -> Dict:
    """
    盘前全面分析
    Returns: 结构化分析结果
    """

    closes = [b.close for b in daily_bars]
    highs = [b.high for b in daily_bars]
    lows = [b.low for b in daily_bars]

    # === 基础信息 ===
    chg_pct = (quote.now / quote.pre_close - 1) * 100 if quote.pre_close else 0
    amplitude = (quote.high - quote.low) / quote.open * 100 if quote.open else 0

    # === 技术指标 ===
    ma5 = calc_ma(closes, 5)
    ma10 = calc_ma(closes, 10)
    ma20 = calc_ma(closes, 20)
    ma60 = calc_ma(closes, 60) if len(closes) >= 60 else [None] * len(closes)

    bb_mid, bb_up, bb_low, bb_width = calc_bollinger(closes, 20, 2.0)
    dif, dea, hist = calc_macd(closes)

    # === 支撑压力 ===
    sr = find_support_resistance(daily_bars, quote.now)

    # === 波动预期 ===
    range_info = get_expected_range(quote, daily_bars)

    # === 量能 ===
    vol_ratio = calc_volume_ratio(daily_bars)

    # === 趋势判断 ===
    trend = "震荡"
    if ma5[-1] and ma20[-1]:
        if ma5[-1] > ma20[-1] and ma5[-1] > ma10[-1]:
            trend = "多头"
        elif ma5[-1] < ma20[-1] and ma5[-1] < ma10[-1]:
            trend = "空头"

    # 短期走势（近5日）
    pct_5d = (closes[-1] / closes[-6] - 1) * 100 if len(closes) >= 6 else 0
    pct_10d = (closes[-1] / closes[-11] - 1) * 100 if len(closes) >= 11 else 0
    pct_20d = (closes[-1] / closes[-21] - 1) * 100 if len(closes) >= 21 else 0

    # === 做T适宜度（传入min5_bars） ===
    t_quality = score_t_quality(quote, daily_bars, min5_bars if min5_bars else None)

    # === 做T信号 ===
    signals = generate_signals(quote, daily_bars, min5_bars or [])

    # === NEW: VWAP分析 ===
    vwap_analysis = {}
    if min5_bars and len(min5_bars) >= 5:
        vwap_bands = calc_vwap_bands(min5_bars)
        vwap_analysis = calc_vwap_position_signal(
            vwap_bands, min5_bars[-1].close, vwap_bands["vwap_slope"]
        )

    # === NEW: RSI分析 ===
    rsi_analysis = {}
    if len(closes) >= 7:
        rsi_vals = calc_rsi(closes, 6)
        if rsi_vals[-1] is not None:
            rsi_analysis = get_rsi_signal(rsi_vals[-1])
            rsi_analysis["value"] = rsi_vals[-1]

    # === NEW: 盘口分析 ===
    ob_analysis = analyze_order_book(quote.bsp)

    # === 关键价位汇总 ===
    key_levels = {
        "昨收": quote.pre_close,
        "今开": quote.open,
        "最高": quote.high,
        "最低": quote.low,
        "均价": quote.avg_price,
    }

    return {
        "stock_name": quote.name,
        "stock_code": quote.code,
        "date": quote.date,
        "current_price": quote.now,
        "chg_pct": round(chg_pct, 2),
        "amplitude": round(amplitude, 2),
        "hsl": round(quote.hsl, 2),
        "amount_yi": round(quote.amount / 1e8, 2),
        "volume_wan": round(quote.volume / 100, 2),

        "trend": trend,
        "pct_5d": round(pct_5d, 2),
        "pct_10d": round(pct_10d, 2),
        "pct_20d": round(pct_20d, 2),

        "ma": {
            "ma5": round(ma5[-1], 2) if ma5[-1] else None,
            "ma10": round(ma10[-1], 2) if ma10[-1] else None,
            "ma20": round(ma20[-1], 2) if ma20[-1] else None,
            "ma60": round(ma60[-1], 2) if ma60[-1] else None,
        },
        "bollinger": {
            "upper": round(bb_up[-1], 2) if bb_up[-1] else None,
            "mid": round(bb_mid[-1], 2) if bb_mid[-1] else None,
            "lower": round(bb_low[-1], 2) if bb_low[-1] else None,
            "width": round(bb_width[-1], 2) if bb_width[-1] else None,
        },
        "macd": {
            "dif": round(dif[-1], 3) if dif[-1] else None,
            "dea": round(dea[-1], 3) if dea[-1] else None,
            "hist": round(hist[-1], 3) if hist[-1] else None,
        },
        "support_resistance": {
            "s3": sr.s3, "s2": sr.s2, "s1": sr.s1,
            "pivot": sr.pivot,
            "r1": sr.r1, "r2": sr.r2, "r3": sr.r3,
        },
        "range_info": range_info,
        "volume_ratio": round(vol_ratio, 2),
        "t_quality": t_quality,
        "signals": signals,
        "key_levels": key_levels,
        "vwap_analysis": vwap_analysis,
        "rsi_analysis": rsi_analysis,
        "order_book": ob_analysis,
    }


def pre_market_summary(analysis: Dict) -> str:
    """生成盘前简报文本"""
    s = analysis
    lines = []
    lines.append(f"## {s['stock_name']} ({s['stock_code']}) 盘前做T策略")
    lines.append(f"**日期**: {s['date']}  |  **前收**: {s['key_levels']['昨收']}  |  **昨跌**: {s['chg_pct']}%  |  **振幅**: {s['amplitude']}%")
    lines.append("")

    lines.append(f"### 📊 趋势与技术面")
    lines.append(f"- 趋势: **{s['trend']}** | 5日: {s['pct_5d']}% | 10日: {s['pct_10d']}% | 20日: {s['pct_20d']}%")
    lines.append(f"- 均线: MA5={s['ma']['ma5']} / MA10={s['ma']['ma10']} / MA20={s['ma']['ma20']}")
    lines.append(f"- 布林: 上轨{s['bollinger']['upper']} / 中轨{s['bollinger']['mid']} / 下轨{s['bollinger']['lower']} (带宽{s['bollinger']['width']}%)")
    lines.append(f"- MACD: DIF={s['macd']['dif']} DEA={s['macd']['dea']} HIST={s['macd']['hist']}")
    lines.append("")

    sr = s['support_resistance']
    lines.append(f"### 🎯 关键价位")
    lines.append(f"```")
    lines.append(f"  压力 R3:  {sr['r3']}")
    lines.append(f"  压力 R2:  {sr['r2']}")
    lines.append(f"  压力 R1:  {sr['r1']}  ← 做空目标区")
    lines.append(f"  ──中枢──  {sr['pivot']}")
    lines.append(f"  支撑 S1:  {sr['s1']}  ← 做多目标区")
    lines.append(f"  支撑 S2:  {sr['s2']}  ← 强支撑")
    lines.append(f"  支撑 S3:  {sr['s3']}")
    lines.append(f"```")
    lines.append("")

    ri = s['range_info']
    lines.append(f"### 📈 波动预期")
    lines.append(f"- ATR: {ri['atr']} ({ri['atr_pct']}%) | 5日均振幅: {ri['avg_range_5d']}%")
    lines.append(f"- 预期振幅: **{ri['expected_range_pct']}%**")
    lines.append(f"- 预期区间: **{ri['expected_low']} ~ {ri['expected_high']}**")
    lines.append(f"- 量比: {s['volume_ratio']}")
    lines.append("")

    tq = s['t_quality']
    lines.append(f"### ⭐ 做T适宜度: {tq['score']}/100 — {tq['rating']}")
    for detail in tq['details']:
        lines.append(f"  - {detail}")
    lines.append("")

    lines.append(f"### 🚦 今日策略信号")
    # NEW: VWAP信号
    vwap_a = s.get('vwap_analysis', {})
    if vwap_a and vwap_a.get('vwap'):
        lines.append(f"**VWAP**: {vwap_a['vwap']} | 位置: {vwap_a['position']} | 斜率: {vwap_a['slope']}")
        lines.append(f"  → VWAP信号: {vwap_a['signal']} (得分{vwap_a['score']})")
        if vwap_a.get('suggestion'):
            lines.append(f"  → {vwap_a['suggestion']}")

    # RSI
    rsi_a = s.get('rsi_analysis', {})
    if rsi_a:
        lines.append(f"**RSI(6)**: {rsi_a.get('value', 'N/A')} | {rsi_a.get('zone', '')} → {rsi_a.get('signal', '')}")

    # 盘口
    ob = s.get('order_book', {})
    if ob:
        lines.append(f"**盘口**: {ob.get('direction', '')}(买{ob.get('buy_pressure', 0)}% / 卖{ob.get('sell_pressure', 0)}%) | 深度: {ob.get('depth', '')}")

    lines.append("")
    for sig in s['signals']:
        lines.append(f"**{sig['direction']}** 置信度: {'⭐' * sig['confidence']}")
        lines.append(f"- 入场区间: {sig['entry_zone']}")
        lines.append(f"- 止损: {sig['stop_loss']}  |  目标: {sig['target']}")
        lines.append(f"- 风险: {sig['risk_level']}")
        for reason in sig['reasons']:
            lines.append(f"  ✓ {reason}")
        lines.append("")

    return "\n".join(lines)
