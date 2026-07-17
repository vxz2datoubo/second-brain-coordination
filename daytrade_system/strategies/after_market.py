"""
盘后复盘模块
统计当日T机会、模拟收益、策略有效性评估
"""

from typing import Dict, List
from engine.indicators import KBar, QuoteSnapshot


def find_t_opportunities(min5_bars: List[KBar], daily_bars: List[KBar],
                          quote: QuoteSnapshot) -> List[Dict]:
    """
    从5分钟K线数据中回溯当日做T机会
    找出所有2%+的波段
    """
    if len(min5_bars) < 5:
        return []

    opportunities = []
    prices = [b.close for b in min5_bars]
    times = [b.time_sec for b in min5_bars]

    n = len(prices)
    # 简化版：寻找局部极值点，波段>=1.5%记录
    for i in range(1, n - 1):
        # 局部最低点 → 正T入场
        if prices[i] <= prices[i - 1] and prices[i] <= prices[i + 1]:
            # 从这个低点到后续最高点
            future_max = max(prices[i:])
            profit_pct = (future_max / prices[i] - 1) * 100
            if profit_pct >= 1.5:
                # 找最高点的位置
                max_idx = prices[i:].index(future_max) + i
                opportunities.append({
                    "type": "正T（低吸→高抛）",
                    "entry_time": _sec_to_time(times[i]),
                    "entry_price": round(prices[i], 2),
                    "exit_time": _sec_to_time(times[max_idx]),
                    "exit_price": round(future_max, 2),
                    "profit_pct": round(profit_pct, 2),
                    "profit_per_lot": round(future_max - prices[i], 2),
                })

        # 局部最高点 → 倒T入场
        if prices[i] >= prices[i - 1] and prices[i] >= prices[i + 1]:
            # 从这个高点到后续最低点
            future_min = min(prices[i:])
            profit_pct = (prices[i] / future_min - 1) * 100
            if profit_pct >= 1.5:
                min_idx = prices[i:].index(future_min) + i
                opportunities.append({
                    "type": "倒T（高抛→低吸）",
                    "entry_time": _sec_to_time(times[i]),
                    "entry_price": round(prices[i], 2),
                    "exit_time": _sec_to_time(times[min_idx]),
                    "exit_price": round(future_min, 2),
                    "profit_pct": round(profit_pct, 2),
                    "profit_per_lot": round(prices[i] - future_min, 2),
                })

    return opportunities


def _sec_to_time(sec: int) -> str:
    """秒数转时间格式"""
    h = sec // 3600
    m = (sec % 3600) // 60
    return f"{h:02d}:{m:02d}"


def after_market_review(quote: QuoteSnapshot, min5_bars: List[KBar],
                         daily_bars: List[KBar], pre_analysis: Dict) -> Dict:
    """
    盘后全面复盘
    """
    opportunities = find_t_opportunities(min5_bars, daily_bars, quote)

    # 统计
    total_ops = len(opportunities)
    good_ops = [o for o in opportunities if o["profit_pct"] >= 2.0]
    great_ops = [o for o in opportunities if o["profit_pct"] >= 3.0]

    # 日内实际走势
    day_range_pct = (quote.high / quote.low - 1) * 100 if quote.low else 0

    # 策略回顾：盘前预期 vs 实际
    pre_expected_high = pre_analysis.get("range_info", {}).get("expected_high", 0)
    pre_expected_low = pre_analysis.get("range_info", {}).get("expected_low", 0)
    range_accuracy = ""
    if pre_expected_high and pre_expected_low:
        in_range = pre_expected_low <= quote.low and quote.high <= pre_expected_high
        range_accuracy = "✅ 实际在预期区间内" if in_range else "⚠️ 超出预期区间"

    return {
        "date": quote.date,
        "stock": quote.name,
        "code": quote.code,
        "day_summary": {
            "open": quote.open,
            "high": quote.high,
            "low": quote.low,
            "close": quote.now,
            "pre_close": quote.pre_close,
            "chg_pct": round((quote.now / quote.pre_close - 1) * 100, 2),
            "day_range_pct": round(day_range_pct, 2),
            "volume_yi": round(quote.amount / 1e8, 2),
            "hsl": round(quote.hsl, 2),
        },
        "t_opportunities": {
            "total": total_ops,
            "good_ops_count": len(good_ops),
            "great_ops_count": len(great_ops),
            "opportunities": opportunities,
        },
        "strategy_review": {
            "expected_high": round(pre_expected_high, 2),
            "expected_low": round(pre_expected_low, 2),
            "actual_high": quote.high,
            "actual_low": quote.low,
            "range_accuracy": range_accuracy,
        },
    }


def review_report(review: Dict) -> str:
    """生成盘后复盘报告"""
    lines = []
    lines.append(f"## 📝 盘后复盘 — {review['stock']}({review['code']}) {review['date']}")
    lines.append("")

    ds = review['day_summary']
    lines.append(f"### 今日行情")
    lines.append(f"| 项目 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 开盘 | {ds['open']} |")
    lines.append(f"| 最高 | {ds['high']} |")
    lines.append(f"| 最低 | {ds['low']} |")
    lines.append(f"| 收盘 | {ds['close']} |")
    lines.append(f"| 涨跌 | {ds['chg_pct']:+.2f}% |")
    lines.append(f"| 振幅 | {ds['day_range_pct']:.2f}% |")
    lines.append(f"| 成交额 | {ds['volume_yi']:.2f}亿 |")
    lines.append(f"| 换手 | {ds['hsl']:.2f}% |")
    lines.append("")

    sr = review['strategy_review']
    lines.append(f"### 策略验证")
    lines.append(f"- 预期区间: {sr['expected_low']} ~ {sr['expected_high']}")
    lines.append(f"- 实际区间: {sr['actual_low']} ~ {sr['actual_high']}")
    lines.append(f"- 结果: {sr['range_accuracy']}")
    lines.append("")

    to = review['t_opportunities']
    lines.append(f"### T机会回溯")
    lines.append(f"共发现 **{to['total']}** 个波段机会（≥1.5%）")
    lines.append(f"  - ≥2% 的机会: {to['good_ops_count']} 次")
    lines.append(f"  - ≥3% 的机会: {to['great_ops_count']} 次")
    lines.append("")

    if to['opportunities']:
        lines.append(f"| 类型 | 入场 | 入场价 | 出场 | 出场价 | 盈利% | 每手盈利 |")
        lines.append(f"|------|------|--------|------|--------|-------|----------|")
        for op in to['opportunities'][:20]:  # 最多20条
            lines.append(
                f"| {op['type']} | {op['entry_time']} | {op['entry_price']} | "
                f"{op['exit_time']} | {op['exit_price']} | "
                f"{op['profit_pct']:+.2f}% | {op['profit_per_lot']:+.2f}元 |"
            )
        if len(to['opportunities']) > 20:
            lines.append(f"| ... 还有 {len(to['opportunities']) - 20} 个机会 |")

    lines.append("")
    lines.append(f"### 💡 今日总结")
    if to['total'] >= 5:
        lines.append(f"- 今日波段丰富，是好的做T日")
    elif to['total'] >= 2:
        lines.append(f"- 今日部分时段适合做T")
    else:
        lines.append(f"- 今日窄幅震荡，T机会较少")

    if ds['chg_pct'] < -2:
        lines.append(f"- 单边下跌日，倒T策略更有效")
    elif ds['chg_pct'] > 2:
        lines.append(f"- 单边上涨日，正T策略更有效")

    return "\n".join(lines)
