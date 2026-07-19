"""quad_lens.py — 四维联合作战分析 v2

整合: 量价剖面 + 供应测试 + CMF资金流 + 吸筹检测 → 统一置信度 + 操作建议
每次分析自动输出: 支撑/阻力位、供需信号、资金流向、Phase、综合评级、买卖建议
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daytrade_system"))

from strategies.crossover_tracker import adjusted_profile as vp
from supply_tester import analyze_supply_test, quick_check
from flow_divergence import flow_price_analysis
from accumulation_detector import detect_phase
from breakout_validator import detect_breakout_pattern


def quad_analysis(code, current_price, day_high, day_low, day_open, prev_close):
    """四维联合作战分析"""
    result = {
        "code": code, "price": current_price,
        "change_pct": round((current_price / prev_close - 1) * 100, 2),
        "components": {}, "joint_score": 0, "confidence": "D",
        "recommendation": "", "buy_targets": [], "sell_targets": [], "details": []
    }

    # ═══════════════════════════════════════════
    # 1. 量价剖面 (max 45分)
    # ═══════════════════════════════════════════
    adj = vp(code, current_price, days=10, min_pct=0.2)
    p_layers = [p for p in adj if p.get("side") == "resistance"]
    s_layers = [s for s in adj if s.get("side") == "support"]
    nearest_s = s_layers[0] if s_layers else None
    nearest_p = p_layers[-1] if p_layers else None

    vp_score = 0
    vp_notes = []
    if nearest_s:
        s_lo, s_hi = nearest_s["price_lo"], nearest_s["price_hi"]
        if s_lo <= current_price <= s_hi:
            pos_in_s = (current_price - s_lo) / max(s_hi - s_lo, 0.01)
            if pos_in_s < 0.3: vp_score += 20; vp_notes.append(f"在{nearest_s['label']}下沿，强支撑")
            elif pos_in_s < 0.7: vp_score += 12; vp_notes.append(f"在{nearest_s['label']}中部")
            else: vp_score += 5; vp_notes.append(f"在{nearest_s['label']}上沿，支撑偏弱")
        if nearest_s["adjusted_pct"] > 7: vp_score += 10
        elif nearest_s["adjusted_pct"] > 4: vp_score += 5
    if nearest_p:
        gap = nearest_p["price_lo"] - current_price
        if gap > current_price * 0.03: vp_score += 15
        elif gap > current_price * 0.01: vp_score += 5

    result["components"]["volume_profile"] = {
        "score": min(vp_score, 45),
        "support": nearest_s["label"] if nearest_s else "无",
        "resistance": nearest_p["label"] if nearest_p else "无",
        "notes": vp_notes
    }

    # ═══════════════════════════════════════════
    # 2. 供应测试 (max 40分)
    # ═══════════════════════════════════════════
    supply = analyze_supply_test(code, current_price, day_high, day_low)
    supply_score = 0
    supply_notes = [quick_check(code, current_price, day_high, day_low)]
    if supply["signal"] == "TEST_PASSED": supply_score = 30; supply_notes.append("供应测试通过 — 卖方真空确认")
    elif supply["signal"] == "NO_SUPPLY": supply_score = 18; supply_notes.append("无供应信号 — 卖盘萎缩中")
    elif supply["confidence"] >= 30: supply_score = 8; supply_notes.append("进行中，等待缩量确认")
    else: supply_score = 2
    v = supply.get("velocity", {})
    if v.get("type") == "急落" and v.get("volume_level") == "低":
        supply_score += 8; supply_notes.append("急落+低量=震仓吸筹")
    result["components"]["supply_test"] = {
        "score": supply_score, "signal": supply["signal"],
        "details": supply["details"][:3], "velocity": v, "notes": supply_notes
    }

    # ═══════════════════════════════════════════
    # 3. CMF 资金流 (max 25分)
    # ═══════════════════════════════════════════
    flow = flow_price_analysis(code)
    cmf = flow.get("current_cmf", 0)
    cmf_score = 0
    cmf_notes = []
    if cmf > 0.15: cmf_score = 18; cmf_notes.append(f"CMF +{cmf:.3f} — 主动买盘强劲")
    elif cmf > 0.05: cmf_score = 10; cmf_notes.append(f"CMF +{cmf:.3f} — 温和买入")
    elif cmf > -0.05: cmf_score = 5; cmf_notes.append(f"CMF {cmf:.3f} — 中性")
    elif cmf > -0.15: cmf_score = 2; cmf_notes.append(f"CMF {cmf:.3f} — 卖压偏弱")
    else:
        if supply_score >= 20: cmf_score = 8; cmf_notes.append(f"CMF {cmf:.3f}强负 + 供应测试通过 = 抛压测试，非真出货")
        else: cmf_score = 0; cmf_notes.append(f"CMF {cmf:.3f}强负 + 供应测试未触发 = 警惕真派发")
    if flow.get("trend_5bar") == "上升": cmf_score += 5; cmf_notes.append("趋势上升 → 好转")
    result["components"]["money_flow"] = {
        "score": cmf_score, "cmf": cmf,
        "pressure": flow.get("pressure", "?"), "trend": flow.get("trend_5bar", "?"), "notes": cmf_notes
    }

    # ═══════════════════════════════════════════
    # 4. 吸筹检测 (max 30分)
    # ═══════════════════════════════════════════
    acc = detect_phase(code, current_price)
    acc_score = 0
    acc_notes = [acc["detail"]]
    phase = acc["phase"]
    if phase == "C_D_TRANSITION": acc_score = 25; acc_notes.append("C→D过渡确认 — 缩量十字星+测试完成，明天大概率向上")
    elif phase == "E": acc_score = 25; acc_notes.append("Phase E: 已进入主升浪")
    elif phase == "D": acc_score = 20; acc_notes.append("SOS出现中，等放量突破确认")
    elif phase == "C": acc_score = 12; acc_notes.append("Spring后缩量测试，确定性高")
    elif phase == "B_C": acc_score = 6; acc_notes.append("B→C过渡，等待弹簧或突破")
    elif phase == "B": acc_score = 3; acc_notes.append("Phase B: 区间蓄力")
    else: acc_score = 0

    # C→D过渡联动供应测试加分
    if acc.get("transition_detected"):
        acc_score += 3
        supply_score += 5
        supply_notes.append("🔗 C→D过渡确认×供应测试 = 双信号共振")
        # 更新 supply_test 的结果
        result["components"]["supply_test"]["score"] += 5
        result["components"]["supply_test"]["notes"].append("🔗 C→D过渡确认×供应测试 = 双信号共振")
    if acc["spring_detected"]: acc_score += 5; acc_notes.append("Spring已完成 — 弱手已被清洗")
    proj = acc.get("projection", {})
    if proj:
        acc_notes.append(f"突破{acc['range_high']}后目标: {proj.get('conservative','?')}~{proj.get('aggressive','?')}")
    result["components"]["accumulation"] = {
        "score": acc_score, "phase": phase, "poc": acc.get("poc"),
        "range": f"{acc['range_low']}-{acc['range_high']}",
        "cause_days": acc["cause_days"],         "spring": acc["spring_detected"],
        "projection": proj, "notes": acc_notes
    }

    # ═══════════════════════════════════════════
    # 5. 突破/LPS检测 (max 15分, 仅近阻力时激活)
    # ═══════════════════════════════════════════
    # 阻力取最小: 量价剖面最近压力 or 今日高点
    candidates = []
    if nearest_p: candidates.append(nearest_p["price_lo"])
    candidates.append(day_high + 0.5)  # 今日高点上方
    if acc: candidates.append(acc["range_high"])
    resistance = min(candidates)

    breakout = detect_breakout_pattern(code, resistance)
    br_score = 0
    br_notes = [breakout["detail"]]
    bt = breakout["type"]

    if bt == "SOS_LPS": br_score = 15; br_notes.append("强LPS确认 — 加仓信号")
    elif bt == "LPS": br_score = 10; br_notes.append("正常LPS — 持有")
    elif bt == "WEAK_LPS": br_score = 3; br_notes.append("弱LPS — 减仓观察")
    elif bt == "UPTHRUST": br_score = -20; br_notes.append("⚠️ 上冲陷阱! — 立刻平仓!")
    elif bt == "UPTHRUST_WEAK": br_score = -10; br_notes.append("疑似上冲 — 减仓设止损")
    elif bt == "BREAKOUT_TESTING": br_score = 3; br_notes.append("突破后测试中")
    elif bt == "BREAKOUT_NO_PULLBACK": br_score = 5; br_notes.append("刚突破，等回踩")
    else: br_score = 0  # NO_BREAKOUT / NONE

    result["components"]["breakout"] = {
        "score": br_score, "type": bt,
        "resistance": resistance, "recommendation": breakout.get("recommendation", ""),
        "notes": br_notes
    }

    # ═══════════════════════════════════════════
    # 6. 综合评分 & 置信度 (总分155)
    # ═══════════════════════════════════════════
    vp_s = result["components"]["volume_profile"]["score"]
    st_s = result["components"]["supply_test"]["score"]  # 可能已被联动更新
    mf_s = result["components"]["money_flow"]["score"]
    ac_s = result["components"]["accumulation"]["score"]
    br_s = result["components"]["breakout"]["score"]
    total = vp_s + st_s + mf_s + ac_s + br_s

    if total >= 105: confidence = "A++"; action = "强烈买入"
    elif total >= 80: confidence = "A"; action = "买入"
    elif total >= 55: confidence = "B"; action = "谨慎持有/小幅加仓"
    elif total >= 35: confidence = "C"; action = "观望，等信号确认"
    else: confidence = "D"; action = "回避/减仓"

    result["joint_score"] = total
    result["confidence"] = confidence
    result["recommendation"] = action

    # 买卖目标
    if nearest_p:
        result["sell_targets"].append({"price": nearest_p["price_hi"],
            "reason": f"量价压力({nearest_p['label']})",
            "confidence": "高" if nearest_p.get("modifier", 1) > 1.1 else "中"})
    if nearest_s:
        result["buy_targets"].append({"price": nearest_s["price_lo"],
            "reason": f"量价支撑({nearest_s['label']})",
            "confidence": "高" if nearest_s["adjusted_pct"] > 6 else "中"})
    if s_layers and len(s_layers) >= 2:
        s2 = s_layers[1]
        result["buy_targets"].append({"price": s2["price_lo"],
            "reason": f"深层支撑({s2['label']})",
            "confidence": "极高" if s2["adjusted_pct"] > 8 else "高"})
    if proj:
        result["sell_targets"].append({"price": proj.get("conservative", 0),
            "reason": f"保守目标(因果推演)", "confidence": "中"})

    result["details"] = [
        f"量价:{vp_notes[0] if vp_notes else '-'}",
        f"供应:{supply_notes[0]}",
        f"CMF:{cmf_notes[0] if cmf_notes else '-'}",
        f"吸筹:{acc['phase']} | {acc['detail']}",
        f"突破:{bt} | {breakout['detail']}",
        f"综合:{vp_s}+{st_s}+{mf_s}+{ac_s}+{br_s}={total}分 | {confidence}级 | {action}"
    ]
    return result


def format_report(r):
    print(f"\n{'='*60}")
    print(f"  🎯 四维联合作战 — {r['code']} @ {r['price']} ({r['change_pct']:+.2f}%)")
    print(f"{'='*60}")

    vp = r["components"]["volume_profile"]
    st = r["components"]["supply_test"]
    mf = r["components"]["money_flow"]
    ac = r["components"]["accumulation"]
    br = r["components"]["breakout"]

    print(f"\n  ┌─ 量价剖面 ({vp['score']}分) ──────┐")
    print(f"  │ 支撑: {vp['support']} | 压力: {vp['resistance']}")
    for n in vp["notes"]: print(f"  │ {n}")
    print(f"  └──────────────────────────────┘")

    print(f"\n  ┌─ 供应测试 ({st['score']}分) ──────┐")
    for n in st["notes"]: print(f"  │ {n}")
    for d in st["details"]: print(f"  │ · {d}")
    print(f"  └──────────────────────────────┘")

    print(f"\n  ┌─ CMF资金流 ({mf['score']}分) ────┐")
    print(f"  │ CMF: {mf['cmf']:+.3f} | {mf['pressure']} | 趋势: {mf['trend']}")
    for n in mf["notes"]: print(f"  │ {n}")
    print(f"  └──────────────────────────────┘")

    print(f"\n  ┌─ 吸筹检测 ({ac['score']}分) ──────┐")
    print(f"  │ Phase {ac['phase']} | POC: {ac.get('poc','?')} | 吸筹{ac['cause_days']}天")
    print(f"  │ Spring: {'✅' if ac['spring'] else '❌'} | 区间: {ac['range']}")
    for n in ac["notes"]: print(f"  │ {n}")
    print(f"  └──────────────────────────────┘")

    print(f"\n  ┌─ 突破/LPS ({br['score']}分) ──────┐")
    print(f"  │ 阻力: {br['resistance']} | {br['type']}")
    for n in br["notes"]: print(f"  │ {n}")
    if br.get("recommendation"): print(f"  │ → {br['recommendation']}")
    print(f"  └──────────────────────────────┘")

    print(f"\n  ╔════════════════════════════════════╗")
    print(f"  ║  五维评分: {r['joint_score']}/155 → {r['confidence']}级 → {r['recommendation']}  ║")
    print(f"  ╚════════════════════════════════════╝")

    bt = r["buy_targets"]
    stg = r["sell_targets"]
    if bt or stg:
        print(f"\n  🎯 操作目标:")
        for b in bt: print(f"     🟢 买入: {b['price']} ({b['reason']}) [{b['confidence']}]")
        for s in stg: print(f"     🔴 卖出: {s['price']} ({s['reason']}) [{s['confidence']}]")
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
    r = quad_analysis(args.code, args.price, args.high, args.low,
                      args.open or args.price, args.prev or args.price)
    format_report(r)
