"""
盘中实时信号模块
基于5分钟K线进行实时监控和信号生成
"""

from typing import Dict, List
from engine.indicators import (
    KBar, QuoteSnapshot, calc_intraday_profile,
    calc_money_flow, calc_daily_vwap
)


def intraday_live(quote: QuoteSnapshot, min5_bars: List[KBar],
                   daily_bars: List[KBar], pre_analysis: Dict) -> Dict:
    """
    盘中实时分析
    """
    profile = calc_intraday_profile(min5_bars, quote.now)
    mf = calc_money_flow(quote)
    sr = pre_analysis.get("support_resistance", {})

    # 实时价格位置
    pos_vs_sr = {}
    for level_name in ["s3", "s2", "s1", "r1", "r2", "r3"]:
        level = sr.get(level_name)
        if level and level > 0:
            pos_vs_sr[level_name] = {
                "price": level,
                "distance_pct": round((quote.now / level - 1) * 100, 2)
            }

    # 量能趋势（最近5根vs前5根）
    recent_5_vol = sum(b.volume for b in min5_bars[-5:]) if len(min5_bars) >= 5 else 0
    prev_5_vol = sum(b.volume for b in min5_bars[-10:-5]) if len(min5_bars) >= 10 else 0
    vol_trend = "放量" if prev_5_vol > 0 and recent_5_vol > prev_5_vol * 1.3 else "缩量" if prev_5_vol > 0 and recent_5_vol < prev_5_vol * 0.7 else "持平"

    # 价格动量（最近3根K线方向）
    if len(min5_bars) >= 3:
        recent_closes = [b.close for b in min5_bars[-3:]]
        momentum = "上涨" if recent_closes[-1] > recent_closes[0] * 1.002 else "下跌" if recent_closes[-1] < recent_closes[0] * 0.998 else "横盘"
    else:
        momentum = "unknown"

    vwap = calc_daily_vwap(min5_bars)

    return {
        "time": quote.time,
        "price": quote.now,
        "avg_price": quote.avg_price,
        "vwap": round(vwap, 2) if vwap else None,
        "avg_deviation": profile["avg_deviation"],
        "wave_pattern": profile["wave_pattern"],
        "volume_trend": profile["volume_trend"],
        "money_flow": mf,
        "current_momentum": momentum,
        "vol_trend_10min": vol_trend,
        "position_vs_levels": pos_vs_sr,
    }


def check_alert_triggers(live_data: Dict, pre_analysis: Dict) -> List[Dict]:
    """
    检查是否触发盘中告警
    """
    alerts = []
    sr = pre_analysis.get("support_resistance", {})
    price = live_data["price"]

    # 告警1：触及支撑位
    s1 = sr.get("s1")
    if s1 and price <= s1 * 1.005:
        alerts.append({
            "type": "⚠️ 支撑位",
            "level": "warning",
            "message": f"价格 {price} 触及 S1 支撑 {s1}，关注正T机会",
            "action": "观察止跌信号，准备买入"
        })

    # 告警2：触及压力位
    r1 = sr.get("r1")
    if r1 and price >= r1 * 0.995:
        alerts.append({
            "type": "⚠️ 压力位",
            "level": "warning",
            "message": f"价格 {price} 接近 R1 压力 {r1}，关注倒T机会",
            "action": "观察滞涨信号，准备卖出"
        })

    # 告警3：均价偏离过大
    if abs(live_data["avg_deviation"]) > 3:
        direction = "上方" if live_data["avg_deviation"] > 0 else "下方"
        alerts.append({
            "type": "📊 均价偏离",
            "level": "info",
            "message": f"价格偏离均价 {abs(live_data['avg_deviation']):.1f}%（{direction}）",
            "action": "偏离过大时警惕均值回归"
        })

    # 告警4：量能异动
    if live_data["vol_trend_10min"] == "放量":
        alerts.append({
            "type": "📈 量能异动",
            "level": "info",
            "message": "近10分钟放量，关注方向",
            "action": "配合价格方向判断是否趋势确认"
        })

    # 告警5：资金异动
    mf = live_data["money_flow"]
    if mf["inside_ratio"] > 65:
        alerts.append({
            "type": "🔴 抛压加重",
            "level": "danger",
            "message": f"内盘占比 {mf['inside_ratio']}%，主动卖出集中",
            "action": "短线回避，等待企稳"
        })
    elif mf["outside_ratio"] > 65:
        alerts.append({
            "type": "🟢 买盘涌入",
            "level": "danger",
            "message": f"外盘占比 {mf['outside_ratio']}%，主动买入积极",
            "action": "关注突破，可追涨但设好止损"
        })

    return alerts


def intraday_report(analysis: Dict, alerts: List[Dict]) -> str:
    """生成盘中监控报告"""
    lines = []
    lines.append(f"## 🕐 盘中实时监控 — {analysis['time']}")
    lines.append(f"**现价**: {analysis['price']}  |  均价: {analysis['avg_price']}  |  VWAP: {analysis.get('vwap', 'N/A')}")
    lines.append(f"**均价偏离**: {analysis['avg_deviation']}%  |  波形: {analysis['wave_pattern']}  |  动量: {analysis['current_momentum']}")
    lines.append("")

    mf = analysis['money_flow']
    lines.append(f"### 资金面")
    lines.append(f"- 内盘 {mf['inside_ratio']}% vs 外盘 {mf['outside_ratio']}% → {mf['direction']}")
    lines.append(f"- 主力净流入: {mf['inflow_amount']/1e8:.2f}亿" if mf.get('inflow_amount') else "- 主力净流入: N/A")
    lines.append("")

    if alerts:
        lines.append(f"### 🚨 告警 ({len(alerts)})")
        for a in alerts:
            lines.append(f"**[{a['type']}]** {a['message']}")
            lines.append(f"  → {a['action']}")
        lines.append("")

    lines.append(f"### 价位距离")
    for level_name, info in analysis['position_vs_levels'].items():
        dist = info['distance_pct']
        bar = "█" * min(int(abs(dist)), 10)
        lines.append(f"- {level_name.upper()}: {info['price']}  ({dist:+.1f}%) {bar}")

    return "\n".join(lines)
