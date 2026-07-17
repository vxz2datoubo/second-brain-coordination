"""triple_lens.py — 三重联合作战分析 v1

整合: 量价剖面 + 供应测试 + CMF资金流 → 统一置信度 + 操作建议
每次分析自动输出: 支撑/阻力位、供需信号、资金流向、综合评级、买卖建议
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daytrade_system"))

from strategies.crossover_tracker import adjusted_profile as vp
from supply_tester import analyze_supply_test, quick_check
from flow_divergence import flow_price_analysis


def triple_analysis(code, current_price, day_high, day_low, day_open, prev_close):
    """三重联合作战分析"""
    result = {
        "code": code,
        "price": current_price,
        "change_pct": round((current_price / prev_close - 1) * 100, 2),
        "components": {},
        "joint_score": 0,
        "confidence": "D",
        "recommendation": "",
        "buy_targets": [],
        "sell_targets": [],
        "details": []
    }

    # ═══════════════════════════════════════════
    # 1. 量价剖面
    # ═══════════════════════════════════════════
    adj = vp(code, current_price, days=10, min_pct=0.2)
    p_layers = [p for p in adj if p.get("side") == "resistance"]
    s_layers = [s for s in adj if s.get("side") == "support"]

    # 最近支撑和压力
    nearest_s = s_layers[0] if s_layers else None
    nearest_p = p_layers[-1] if p_layers else None

    # 量价剖面评分: 价格是否在支撑区?
    vp_score = 0
    vp_notes = []

    if nearest_s:
        s_lo = nearest_s["price_lo"]
        s_hi = nearest_s["price_hi"]
        if s_lo <= current_price <= s_hi:
            position_in_s = (current_price - s_lo) / max(s_hi - s_lo, 0.01)
            if position_in_s < 0.3:
                vp_score += 20
                vp_notes.append(f"价格在{nearest_s['label']}下沿，强支撑区")
            elif position_in_s < 0.7:
                vp_score += 12
                vp_notes.append(f"价格在{nearest_s['label']}中部，有一定支撑")
            else:
                vp_score += 5
                vp_notes.append(f"价格在{nearest_s['label']}上沿，支撑偏弱")

        # S层筹码厚度
        if nearest_s["adjusted_pct"] > 7:
            vp_score += 10
            vp_notes.append(f"支撑层筹码厚({nearest_s['adjusted_pct']:.0f}%)")
        elif nearest_s["adjusted_pct"] > 4:
            vp_score += 5

    if nearest_p:
        gap_to_p = nearest_p["price_lo"] - current_price
        if gap_to_p > current_price * 0.03:
            vp_score += 15
            vp_notes.append(f"距上方压力较远({gap_to_p:.2f}元)，反弹空间大")
        elif gap_to_p > current_price * 0.01:
            vp_score += 5

    result["components"]["volume_profile"] = {
        "score": min(vp_score, 45),
        "support": nearest_s["label"] if nearest_s else "无",
        "resistance": nearest_p["label"] if nearest_p else "无",
        "notes": vp_notes
    }

    # ═══════════════════════════════════════════
    # 2. 供应测试
    # ═══════════════════════════════════════════
    supply = analyze_supply_test(code, current_price, day_high, day_low)
    supply_score = 0
    supply_notes = [quick_check(code, current_price, day_high, day_low)]

    if supply["signal"] == "TEST_PASSED":
        supply_score = 35
        supply_notes.append("供应测试通过 — 卖方真空确认")
    elif supply["signal"] == "NO_SUPPLY":
        supply_score = 20
        supply_notes.append("无供应信号 — 卖盘萎缩中")
    elif supply["confidence"] >= 30:
        supply_score = 10
        supply_notes.append("测试进行中，等待缩量确认")
    else:
        supply_score = 2

    # 震仓陷阱加分
    v = supply.get("velocity", {})
    if v.get("type") == "急落" and v.get("volume_level") == "低":
        supply_score += 10
        supply_notes.append("急落+低量=震仓吸筹信号")

    result["components"]["supply_test"] = {
        "score": supply_score,
        "signal": supply["signal"],
        "details": supply["details"][:3],
        "velocity": v,
        "notes": supply_notes
    }

    # ═══════════════════════════════════════════
    # 3. CMF 资金流
    # ═══════════════════════════════════════════
    flow = flow_price_analysis(code)
    cmf = flow.get("current_cmf", 0)
    cmf_score = 0
    cmf_notes = []

    if cmf > 0.15:
        cmf_score = 20
        cmf_notes.append(f"CMF +{cmf:.3f} — 主动买盘强劲")
    elif cmf > 0.05:
        cmf_score = 12
        cmf_notes.append(f"CMF +{cmf:.3f} — 温和买入")
    elif cmf > -0.05:
        cmf_score = 5
        cmf_notes.append(f"CMF {cmf:.3f} — 中性")
    elif cmf > -0.15:
        cmf_score = 2
        cmf_notes.append(f"CMF {cmf:.3f} — 卖压偏弱")
        cmf_notes.append("结合供应测试: " + ("测试通过=虚惊" if supply_score >= 20 else "等进一步确认"))
    else:
        # CMF强负 — 需要供应测试来判断是测试还是出货
        if supply_score >= 20:
            cmf_score = 8
            cmf_notes.append(f"CMF {cmf:.3f}强负 + 供应测试通过 = 主力抛压测试，非真出货")
        else:
            cmf_score = 0
            cmf_notes.append(f"CMF {cmf:.3f}强负 + 供应测试未触发 = 警惕真实派发")

    # CMF趋势加分
    if flow.get("trend_5bar") == "上升":
        cmf_score += 5
        cmf_notes.append("CMF 5bar趋势上升 → 资金面好转")

    result["components"]["money_flow"] = {
        "score": cmf_score,
        "cmf": cmf,
        "pressure": flow.get("pressure", "?"),
        "trend": flow.get("trend_5bar", "?"),
        "notes": cmf_notes
    }

    # ═══════════════════════════════════════════
    # 4. 综合评分 & 置信度
    # ═══════════════════════════════════════════
    vp_s = result["components"]["volume_profile"]["score"]
    st_s = result["components"]["supply_test"]["score"]
    mf_s = result["components"]["money_flow"]["score"]
    total = vp_s + st_s + mf_s

    if total >= 75:
        confidence = "A++"
        action = "强烈买入"
    elif total >= 60:
        confidence = "A"
        action = "买入"
    elif total >= 45:
        confidence = "B"
        action = "谨慎持有/小幅加仓"
    elif total >= 30:
        confidence = "C"
        action = "观望，等信号确认"
    else:
        confidence = "D"
        action = "回避/减仓"

    result["joint_score"] = total
    result["confidence"] = confidence
    result["recommendation"] = action

    # ═══════════════════════════════════════════
    # 5. 买卖目标位
    # ═══════════════════════════════════════════
    if nearest_p:
        result["sell_targets"].append({"price": nearest_p["price_hi"], "reason": f"量价压力层上沿({nearest_p['label']})", "confidence": "高" if nearest_p.get("modifier", 1) > 1.1 else "中"})
    if nearest_s:
        result["buy_targets"].append({"price": nearest_s["price_lo"], "reason": f"量价支撑层下沿({nearest_s['label']})", "confidence": "高" if nearest_s["adjusted_pct"] > 6 else "中"})

    # 动态买卖点
    if s_layers and len(s_layers) >= 2:
        s2 = s_layers[1]
        result["buy_targets"].append({"price": s2["price_lo"], "reason": f"深层支撑({s2['label']})", "confidence": "极高" if s2["adjusted_pct"] > 8 else "高"})

    # 总结
    result["details"] = [
        f"量价剖面: {result['components']['volume_profile']['notes'][0] if result['components']['volume_profile']['notes'] else '无'}",
        f"供应测试: {supply_notes[0]}",
        f"资金流: {cmf_notes[0]}",
        f"综合: {vp_s}+{st_s}+{mf_s} = {total}分 | {confidence}级 | {action}"
    ]

    return result


def format_report(r):
    """格式化输出"""
    print(f"\n{'='*60}")
    print(f"  🎯 三重联合作战 — {r['code']} @ {r['price']} ({r['change_pct']:+.2f}%)")
    print(f"{'='*60}")

    vp = r["components"]["volume_profile"]
    st = r["components"]["supply_test"]
    mf = r["components"]["money_flow"]

    print(f"\n  ┌─ 量价剖面 ({vp['score']}分) ────────────────────┐")
    print(f"  │ 支撑: {vp['support']} | 压力: {vp['resistance']}")
    for n in vp["notes"]: print(f"  │ {n}")
    print(f"  └────────────────────────────────────────┘")

    print(f"\n  ┌─ 供应测试 ({st['score']}分) ────────────────────┐")
    for n in st["notes"]: print(f"  │ {n}")
    for d in st["details"]: print(f"  │ · {d}")
    print(f"  └────────────────────────────────────────┘")

    print(f"\n  ┌─ CMF 资金流 ({mf['score']}分) ────────────────────┐")
    print(f"  │ CMF: {mf['cmf']:+.3f} | {mf['pressure']} | 趋势: {mf['trend']}")
    for n in mf["notes"]: print(f"  │ {n}")
    print(f"  └────────────────────────────────────────┘")

    print(f"\n  ╔══════════════════════════════════════════════╗")
    print(f"  ║  综合评分: {r['joint_score']}/100 → {r['confidence']}级 → {r['recommendation']}  ║")
    print(f"  ╚══════════════════════════════════════════════╝")

    bt = r["buy_targets"]
    stg = r["sell_targets"]
    if bt or stg:
        print(f"\n  🎯 操作目标:")
        for b in bt:
            print(f"     🟢 买入: {b['price']} ({b['reason']}) [{b['confidence']}]")
        for s in stg:
            print(f"     🔴 卖出: {s['price']} ({s['reason']}) [{s['confidence']}]")
    print()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("price", type=float)
    p.add_argument("high", type=float)
    p.add_argument("low", type=float)
    p.add_argument("--open", type=float)
    p.add_argument("--prev", type=float)
    args = p.parse_args()
    r = triple_analysis(args.code, args.price, args.high, args.low,
                        args.open or args.price, args.prev or args.price)
    format_report(r)
