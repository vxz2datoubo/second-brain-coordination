"""
波仔交易系统统一入口 — v3

盘前→盘中→盘后完整流程

用法:
  python runner.py premarket 300418    # 盘前分析
  python runner.py intraday 300418     # 盘中决策
  python runner.py aftermarket        # 盘后复盘
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategies.trend_classifier import classify_trend, TrendState
from strategies.daily_analyzer import analyze_daily
from strategies.volume_efficiency import efficiency_format, reverse_t_ranking
from strategies.reverse_t_engine import ReverseTEngine
from strategies.cross_day_tracker import CrossDayTracker
from strategies.crossover_tracker import adjusted_profile, format_adjusted
from strategies.news_monitor import monitor, manual_event, format_news_alert
from strategies.volume_profile import find_support_resistance
from risk.position_manager import PositionManager, PositionConfig
from strategies.turnover_analyzer import turnover_diagnose, format_turnover_report
from strategies.sector_scanner import SECTOR_POOLS
from strategies.chip_analyzer import analyze_chip, format_chip_report
from strategies.momentum_analyzer import calc_momentum
from strategies.resistance_pk import pk_resistance, format_pk_report


def run_premarket(code: str):
    """盘前：趋势判定 + 量价效率 + 日线分析"""
    name = "昆仑万维" if code == "300418" else "蓝色光标"
    
    print(f"\n{'='*55}")
    print(f"  📅 盘前分析 — {name}({code})")
    print(f"{'='*55}")

    # Engine A: 趋势判定
    trend = classify_trend(code)
    print(f"\n  [Engine A] 趋势状态: {trend.state_label}")
    print(f"  波动: ATR/均值={trend.atr_ratio}x | 量比={trend.vol_ratio}x")
    print(f"  连{'阳' if trend.consecutive>0 else '阴'}{abs(trend.consecutive)}天")
    print(f"  策略: 倒T={'✅' if trend.reverse_t_allowed else '❌'} | 正T={'✅' if trend.trend_t_allowed else '❌'} | 仓位={trend.position_factor*100:.0f}%")

    # 日线分析
    dt = analyze_daily(code, name)
    if dt:
        print(f"\n  [日线] {dt.trend} | {'放量' if dt.volume_ratio>1.5 else '缩量' if dt.volume_ratio<0.6 else '正常量'}({dt.volume_ratio:.1f}x)")
        if dt.signals:
            print(f"  信号: {' | '.join(dt.signals)}")

    # 主力筹码分析
    chip_report = analyze_chip(code, name, dt.close if dt else 0)
    if chip_report:
        print(f"\n  [主力筹码] {chip_report.current_stage}")
        print(f"  成本区: {chip_report.cost_zone}")
        print(f"  {chip_report.trade_advice}")

    # 板块涨停扫描（强制流程 — 避免漏掉小票涨停潮）
    pool = SECTOR_POOLS.get(code, [])[:5]
    if pool:
        print(f"\n  [板块扫描] 竞价状态:")
        import urllib.request
        for peer_code in pool[:5]:
            try:
                # 用腾讯API快速拉取（不占用通达信MCP资源）
                url = f"http://qt.gtimg.cn/q={peer_code}"
                data = urllib.request.urlopen(url, timeout=3).read().decode("gbk")
                parts = data.split("~")
                if len(parts) > 5:
                    name_peer = parts[1]
                    now_p = float(parts[3])
                    prev_close = float(parts[4])
                    chg_p = (now_p / prev_close - 1) * 100 if prev_close > 0 else 0
                    icon = "🚀" if chg_p >= 9.5 else "🔥" if chg_p >= 5 else "↑" if chg_p > 0 else "↓" if chg_p < 0 else "—"
                    print(f"  {icon} {name_peer}: {now_p:.2f} ({chg_p:+.1f}%)")
            except Exception:
                pass

    # 量价效率
    print(f"\n  [量价效率] 近5天上方阻力:")
    ranking = reverse_t_ranking(code, dt.close if dt else 0, 5, 5)
    for i, r in enumerate(ranking):
        icon = "🔴" if r["hardness"] == "硬阻力" else "🟡" if r["hardness"] == "中等阻力" else "🟢"
        print(f"  {icon} #{i+1} {r['price_label']:>12} {r['hardness']} (效率{r['avg_efficiency']:.1f}x, 距{r['distance_pct']:+.1f}%)")

    # 量价剖面 — 穿越难度修正版
    current_p = dt.close if dt else 0
    if current_p > 0:
        adj_prof = adjusted_profile(code, current_p, days=10, min_pct=0.2)
        print(f"\n  [量价剖面·穿越修正]")
        print(format_adjusted(adj_prof, current_p))

        # 动能强度 × P层穿越PK
        from strategies.momentum_analyzer import calc_momentum
        from strategies.resistance_pk import pk_resistance, format_pk_report
        # 用收盘价的近似动能(盘前无法获取实时数据)
        m = calc_momentum(code, current_p, current_p * 0.99, current_p * 0.995,
                         current_p * 1.02, current_p * 0.98, 1.0, 100, 100)
        pk = pk_resistance(m, code, current_p)
        print(f"\n  [动能×P层PK]")
        print(format_pk_report(pk, m))

    # 换手率深度分析 (联动趋势+阻力+效率)
    print(f"\n  [换手率] 联动分析:")
    eff_data = reverse_t_ranking(code, dt.close if dt else 0, 5, 5)
    diag = turnover_diagnose(
        code, name,
        current_price=dt.close if dt else 0,
        eff_data=eff_data,
        trend_state=trend.state_label,
        nearest_resistance=adj_prof[0]["label"] if adj_prof else "",
        efficiency_val=eff_data[0]["avg_efficiency"] if eff_data else 0
    )
    # 紧凑版输出
    print(f"  换手: {diag.current:.2f}% | 分位: {diag.current_pct:.0f}% | 趋势: {diag.trend}")
    print(f"  {diag.phase_signal}")
    print(f"  {diag.vol_category}")
    if diag.breakthrough != "无数据":
        print(f"  {diag.breakthrough}")
    if "current_bucket" in diag.next_day_stats:
        cb = diag.next_day_stats["current_bucket"]
        if cb in diag.next_day_stats:
            nxt = diag.next_day_stats[cb]
            print(f"  历史{cb}换手: 次日均{nxt['avg_next_chg']:+.1f}% 胜{nxt['win_rate']:.0f}% (n={nxt['n']})")

    # 跨日持仓检查
    tracker = CrossDayTracker(code)
    if tracker.has_carried():
        prev_close = dt.close if dt else 0
        morning = tracker.morning_check(prev_close, prev_close)  # 用前收近似
        print(f"\n  [跨日] 有待接回仓位: {len(morning['decisions'])}笔")
        for d in morning['decisions']:
            print(f"  → 槽{d['slot_id']}: {d['action']} ({d['reason']})")

    # 总结
    print(f"\n  {'─'*53}")
    if not trend.reverse_t_allowed:
        print(f"  🚨 今日禁用倒T — 强上涨趋势不要逆势操作")
    elif trend.state == TrendState.LOW_VOL:
        print(f"  ⚠️ 低波动日 — 仓位降至50%，预期收益打折")
    else:
        print(f"  ✅ 正常操作 — 按Volume Profile锚点执行")
    print(f"{'='*55}\n")


def run_intraday(code: str, current_price: float, avg_price: float = 0, 
                 high: float = 0, low: float = 0):
    """盘中：实时决策"""
    name = "昆仑万维" if code == "300418" else "蓝色光标"
    
    engine = ReverseTEngine(code, name)
    pm = PositionManager()
    engine.update_price(current_price, avg_price or current_price, high, low)

    # Engine A 检查
    trend = classify_trend(code)
    if not trend.reverse_t_allowed:
        return [{"action": "禁止倒T", "reason": trend.state_label}]

    decisions = engine.comprehensive_check(pm, "10:00")  # TODO: 用实际时间
    
    if not decisions:
        return [{"action": "无信号", "price": current_price}]

    results = []
    for d in decisions:
        results.append({
            "action": d.action,
            "price": d.price,
            "reason": d.reason,
            "slot": d.slot_id,
        })
    
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python runner.py premarket|intraday CODE")
        sys.exit(1)

    mode = sys.argv[1]
    code = sys.argv[2] if len(sys.argv) > 2 else "300418"

    if mode == "premarket":
        run_premarket(code)
    elif mode == "intraday":
        price = float(sys.argv[3]) if len(sys.argv) > 3 else 0
        decisions = run_intraday(code, price)
        for d in decisions:
            print(f"  {d}")
