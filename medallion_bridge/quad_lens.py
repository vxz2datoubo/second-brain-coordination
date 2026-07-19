"""quad_lens.py — 八维联合作战分析 v5 (七维计分 + VWAP偏置 + Footprint微观)

整合: 量价剖面 + 供应测试 + CMF资金流 + 吸筹检测 + 突破/LPS + CVD主动买卖差 + 吸收检测
偏置层: VWAP/AVWAP → 不独立计分, 而是作为"价位语境偏置"影响其他维度评分
微观层: Footprint → 不独立计分, 通过堆叠失衡/微观吸收/Delta背离增强供应测试和突破评分
T+1适配: CVD吸收信号 + 独立吸收检测 + VWAP公允价值锚定
每次分析自动输出: 支撑/阻力位、供需信号、资金流向、Phase、CVD健康度、吸收状态、VWAP偏置、Footprint微观、SOS质量、综合评级、买卖建议
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daytrade_system"))

from strategies.crossover_tracker import adjusted_profile as vp
from supply_tester import analyze_supply_test, quick_check
from flow_divergence import flow_price_analysis
from accumulation_detector import detect_phase
from breakout_validator import detect_breakout_pattern
from delta_cvd import supply_test_cvd_confirm, sos_quality_check, score_for_quad_lens
from absorption_detector import detect as absorption_detect, score_for_quad_lens as absorption_score
from vwap_analyzer import analyze as vwap_analyze, vwap_context_for_supply_test, vwap_context_for_absorption, vwap_context_for_breakout, score_bias_for_quad_lens
from footprint_detector import score_for_quad_lens as footprint_score, confirm_supply_test as footprint_confirm
from imbalance_detector import score_for_quad_lens as imbalance_score, imbalance_context_for_supply_test
from liquidity_sweep import score_for_quad_lens as sweep_score
from opening_range import score_for_quad_lens as or_score, opening_context_for_supply_test as or_supply_ctx
# from call_auction import score_for_quad_lens as auction_score  # ⏸️ 暂停: 无Level 2竞价数据, 回测信号不显著
from hvn_lvn_nodes import score_for_quad_lens as hvn_score
from cause_effect import score_for_quad_lens as ce_score
from market_context import score_for_quad_lens as mc_score


def quad_analysis(code, current_price, day_high, day_low, day_open, prev_close):
    """八维联合作战分析 (v5: +VWAP偏置层)"""
    result = {
        "code": code, "price": current_price,
        "change_pct": round((current_price / prev_close - 1) * 100, 2),
        "components": {}, "joint_score": 0, "confidence": "D",
        "recommendation": "", "buy_targets": [], "sell_targets": [], "details": []
    }

    # ═══════════════════════════════════════════
    # 0. VWAP 偏置层 (不独立计分, 作为上下文偏置)
    # ═══════════════════════════════════════════
    vwap_result = vwap_analyze(code, current_price)
    vwap_bias = vwap_result.get("bias", "neutral")
    vwap_day_type = vwap_result.get("day_type", "unknown")
    vwap_amp = vwap_result.get("bias_amplifier", 1.0)
    vwap_notes = [vwap_result.get("summary", "VWAP分析失败")]

    # VWAP语境供给各维度
    vwap_ctx_supply = vwap_context_for_supply_test(vwap_result)
    vwap_ctx_absorb = vwap_context_for_absorption(vwap_result)
    vwap_ctx_breakout = vwap_context_for_breakout(vwap_result)

    if vwap_result["vwap_data"]:
        d = vwap_result["vwap_data"]
        vwap_notes.append(f"VWAP@{d['vwap']} | +1SD:{d['+1sd']} -1SD:{d['-1sd']}")
        vwap_notes.append(f"日型:{vwap_day_type} | 偏置:{vwap_bias}(x{vwap_amp})")
        if vwap_result.get("ext_level"):
            vwap_notes.append(f"⚡ 统计延伸:{vwap_result['ext_level']} -> 均值回归偏置")

    result["components"]["vwap"] = {
        "bias": vwap_bias, "day_type": vwap_day_type,
        "amplifier": vwap_amp, "vwap_data": vwap_result.get("vwap_data"),
        "notes": vwap_notes
    }

    # ═══════════════════════════════════════════
    # 0.6 市场环境偏置 (±5分)
    # ═══════════════════════════════════════════
    mc_data = mc_score(code, stock_return=result["change_pct"], sector_returns=None)
    mc_bias = mc_data.get("score", 0)
    mc_notes = [mc_data.get("detail", "")]
    result["components"]["market_context"] = {
        "score": mc_bias, "notes": mc_notes
    }

    # ═══════════════════════════════════════════
    # 0.5 开盘区间偏置 (±8分)
    # ═══════════════════════════════════════════
    or_data = or_score(code, current_price)
    or_bias_score = or_data.get("score", 0)
    or_notes = [or_data.get("detail", "")]
    if or_data.get("or_data") and or_data["or_data"].get("formed"):
        od = or_data["or_data"]
        or_notes.append(f"OR:{od.get('orl',0):.2f}-{od.get('orh',0):.2f} 宽度{od.get('width_pct',0):.2%}")

    result["components"]["opening_range"] = {
        "score": or_bias_score, "day_type": or_data.get("day_type"),
        "or_data": or_data.get("or_data", {}),
        "notes": or_notes
    }

    # 集合竞价增强: 调整开盘区间偏置
    # ⏸️ 集合竞价暂停: 回测显示无Level 2数据时信号不显著, 开Level 2后恢复
    # 数据保留在 call_auction.py, 仅暂停对评分的影响
    # auc_data = auction_score(code, prev_close=prev_close)
    # if auc_data.get("fake_warning"):
    #     or_bias_score = 0
    #     or_notes.append(f"🔔 竞价烟雾弹: {auc_data.get('detail','')}")
    # elif auc_data.get("score", 0) > 0 and or_bias_score > 0:
    #     or_bias_score += 2
    #     or_notes.append(f"🔔 竞价确认: 高开大量")
    result["components"]["opening_range"]["score"] = or_bias_score

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
    # 2. 供应测试 (max 40分) + T+1 CVD联动
    # ═══════════════════════════════════════════
    # 先获取CVD联动数据
    cvd_sc = supply_test_cvd_confirm(code, current_price, day_low, day_high)
    supply = analyze_supply_test(code, current_price, day_high, day_low, cvd_confirm=cvd_sc)
    supply_score = 0
    supply_notes = [quick_check(code, current_price, day_high, day_low)]
    if supply["signal"] == "TEST_PASSED": supply_score = 30; supply_notes.append("供应测试通过 — 卖方真空确认")
    elif supply["signal"] == "NO_SUPPLY": supply_score = 18; supply_notes.append("无供应信号 — 卖盘萎缩中")
    elif supply["confidence"] >= 30: supply_score = 8; supply_notes.append("进行中，等待缩量确认")
    else: supply_score = 2
    v = supply.get("velocity", {})
    if v.get("type") == "急落" and v.get("volume_level") == "低":
        supply_score += 8; supply_notes.append("急落+低量=震仓吸筹")
    # CVD联动加分已在supply_tester中计入score, 此处记录说明
    if supply.get("cvd_boost", 0) > 0:
        supply_notes.append(f"🔗 T+1 CVD联动: {supply.get('cvd_note', '')[:60]}")
    elif supply.get("cvd_boost", 0) < 0:
        supply_notes.append(f"🔗 T+1 CVD警示: {supply.get('cvd_note', '')[:60]}")
    # VWAP语境: 供应测试在什么位置发生
    if vwap_ctx_supply.get("near_vwap"):
        supply_score += vwap_ctx_supply.get("boost", 0)
        supply_notes.append(f"📍 VWAP语境: {vwap_ctx_supply.get('note', '')}")
    # Footprint微观确认
    fp_confirm = footprint_confirm(code, current_price)
    if fp_confirm.get("confirmed"):
        supply_score += fp_confirm.get("boost", 0)
        supply_notes.append(f"🔬 Footprint微观: {fp_confirm.get('signal', '')}")
    # OFI失衡语境
    ofi_ctx = imbalance_context_for_supply_test(code)
    if ofi_ctx.get("boost", 0) != 0:
        supply_score += ofi_ctx["boost"]
        supply_notes.append(f"⚖️ OFI语境: {ofi_ctx.get('note', '')}")
    # 开盘区间语境
    or_sc = or_supply_ctx(code, current_price)
    if or_sc.get("boost", 0) != 0:
        supply_score += or_sc["boost"]
        supply_notes.append(f"🚪 开盘区间: {or_sc.get('note', '')}")
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

    # Liquidity Sweep验证: 增强Spring置信度
    sw_data = sweep_score(code, sweep_price=acc.get("range_low"))
    if sw_data.get("boost_spring", 0) > 0:
        acc_score += sw_data["boost_spring"]
        acc_notes.append(f"🔎 Sweep验证: {sw_data.get('detail', '')}")
    if sw_data.get("boost_lps", 0) > 0:
        br_score += sw_data["boost_lps"]
        br_notes.append(f"🔎 Sweep验证→LPS: +{sw_data['boost_lps']}")
        result["components"]["breakout"]["score"] += sw_data["boost_lps"]

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

    # VWAP语境: 突破是否在VWAP方向一致
    if vwap_ctx_breakout.get("vwap_confirmed"):
        br_score += 3
        br_notes.append(f"📍 {vwap_ctx_breakout.get('note', '')}")
        result["components"]["breakout"]["score"] += 3
    elif vwap_ctx_breakout.get("note"):
        br_notes.append(f"📍 {vwap_ctx_breakout.get('note', '')}")

    # ═══════════════════════════════════════════
    # 6. CVD 主动买卖差 (max 25分) + SOS质量检查
    # ═══════════════════════════════════════════
    cvd_data = score_for_quad_lens(code)
    cvd_score = cvd_data.get("score", 0)
    cvd_notes = [cvd_data.get("detail", "无数据")]

    # SOS质量检查 (T+1适配): 在Phase C→D过渡或接近突破时自动触发
    sos_quality = None
    is_near_breakout = (bt in ("SOS_LPS", "LPS", "BREAKOUT_TESTING", "BREAKOUT_NO_PULLBACK") or
                        acc.get("phase") in ("C_D_TRANSITION", "D"))
    if is_near_breakout:
        sos_quality = sos_quality_check(code, resistance)
        if sos_quality["quality"] in ("A", "B"):
            cvd_score += sos_quality["score"]
            cvd_notes.append(f"🔗 SOS质量{sos_quality['quality']}级: {sos_quality['description']} (+{sos_quality['score']})")
            if sos_quality["quality"] == "A":
                # A级SOS → 供应测试联动再加分
                supply_score += 3
                supply_notes.append("🔗 CVD确认: SOS质量A级 → 供应测试通过率增强")
        elif sos_quality["quality"] == "C":
            cvd_notes.append(f"⚠️ SOS质量{sos_quality['quality']}级: {sos_quality['description']}")
            for w in sos_quality.get("warnings", []):
                cvd_notes.append(f"  → {w}")
        else:  # D
            cvd_score = max(cvd_score - 5, -25)
            cvd_notes.append(f"🔴 SOS质量D级: {sos_quality['description']}")
            for w in sos_quality.get("warnings", []):
                cvd_notes.append(f"  → {w}")

    # T+1适配说明
    cvd_notes.append("📌 T+1适配: CVD评估基于主力防守位置而非被迫平仓压力")

    result["components"]["delta_cvd"] = {
        "score": min(cvd_score, 25),
        "cvd_signal": cvd_data.get("detail", ""),
        "sos_quality": sos_quality,
        "notes": cvd_notes
    }

    # ═══════════════════════════════════════════
    # 7. 吸收检测 (max 20分) — 独立维度 + 联动增强
    # ═══════════════════════════════════════════
    absorb = absorption_detect(code, current_price, day_low, day_high)
    absorb_data = absorption_score(code)
    absorb_score = absorb_data.get("score", 0)
    absorb_notes = [absorb["summary"]]

    # 联动: 吸收 → 供应测试
    if absorb.get("supply_test_boost", 0) > 0:
        supply_score += absorb["supply_test_boost"]
        supply_notes.append(f"🔗 吸收联动+{absorb['supply_test_boost']}: {absorb.get('wyckoff_impact','')[:50]}")
    elif absorb.get("supply_test_boost", 0) < 0:
        supply_score += absorb["supply_test_boost"]
        supply_notes.append(f"🔗 吸收警示{absorb['supply_test_boost']}: {absorb.get('wyckoff_impact','')[:50]}")

    # 联动: 吸收 → SOS质量
    if absorb.get("sos_impact"):
        absorb_notes.append(f"🔗 SOS: {absorb['sos_impact'][:80]}")

    # 联动: 吸收 → 吸筹检测
    if absorb["dominant"] == "bid" and acc.get("phase") in ("B", "B_C", "C", "C_D_TRANSITION"):
        absorb_notes.append("🔗 Bid吸收×吸筹Phase = 双重确认主力吸筹中")
        acc_score += 3
        result["components"]["accumulation"]["score"] += 3

    # 联动: 吸收 → 突破
    if absorb["dominant"] == "bid" and bt == "LPS":
        br_score += 3
        br_notes.append("🔗 Bid吸收+LPS = 回调被主力接走,强LPS")
        result["components"]["breakout"]["score"] += 3
    elif absorb["dominant"] == "ask" and bt in ("SOS_LPS", "LPS"):
        br_score -= 3
        br_notes.append("🔗 Ask吸收+突破 = 警惕主力在阻力位派发,减弱突破信号")
        result["components"]["breakout"]["score"] -= 3

    absorb_notes.append(f"📌 {absorb.get('t1_context', '')[:60]}")
    if absorb_data.get("signals"):
        absorb_notes.extend(absorb_data["signals"])

    # VWAP语境: 吸收是否发生在有意义的价位
    if vwap_ctx_absorb.get("on_vwap"):
        absorb_notes.append(f"📍 {vwap_ctx_absorb.get('context_note', '')}")
        absorb_score += 5  # VWAP上的吸收 → 加分
    elif not vwap_ctx_absorb.get("on_vwap") and vwap_ctx_absorb.get("context_note"):
        absorb_notes.append(f"📍 {vwap_ctx_absorb.get('context_note', '')}")

    result["components"]["absorption"] = {
        "score": absorb_score,
        "dominant": absorb["dominant"],
        "bid": absorb["bid_absorption"],
        "ask": absorb["ask_absorption"],
        "wyckoff_impact": absorb.get("wyckoff_impact", ""),
        "supply_test_boost": absorb.get("supply_test_boost", 0),
        "notes": absorb_notes
    }

    # ═══════════════════════════════════════════
    # 8. Footprint 微观确认 (不独立计分)
    # ═══════════════════════════════════════════
    fp_data = footprint_score(code)
    fp_notes = [fp_data.get("detail", "无Footprint信号")]
    if fp_data.get("boost_supply_test") != 0:
        fp_notes.append(f"→ 供应测试{fp_data['boost_supply_test']:+d} / 突破{fp_data['boost_breakout']:+d}")
    
    result["components"]["footprint"] = {
        "score": 0,  # 不独立计分，通过联动增强其他维度
        "signals": fp_data.get("signals", []),
        "notes": fp_notes
    }

    # ═══════════════════════════════════════════
    # 9. OFI 订单流失衡 (max 8分)
    # ═══════════════════════════════════════════
    ofi_data = imbalance_score(code)
    ofi_score = ofi_data.get("score", 0)
    ofi_notes = [ofi_data.get("detail", "OFI均衡")]
    if ofi_data.get("ofi_trend"):
        ofi_notes.append(f"趋势: {ofi_data['ofi_trend']}")

    result["components"]["ofi_imbalance"] = {
        "score": ofi_score,
        "ofi_current": ofi_data.get("ofi_current", 0),
        "ofi_trend": ofi_data.get("ofi_trend", ""),
        "notes": ofi_notes
    }

    # ═══════════════════════════════════════════
    # 10. HVN/LVN 节点 (±5分)
    # ═══════════════════════════════════════════
    hvn_data = hvn_score(code, current_price=current_price)
    hvn_node_score = hvn_data.get("score", 0)
    hvn_notes = [hvn_data.get("detail", "")]
    if hvn_data.get("hvn_targets"):
        for lo, hi in hvn_data["hvn_targets"][:2]:
            hvn_notes.append(f"HVN目标: {lo:.1f}-{hi:.1f}")
    if hvn_data.get("lvn_zones"):
        for lo, hi in hvn_data["lvn_zones"][:1]:
            hvn_notes.append(f"LVN入场: {lo:.1f}-{hi:.1f}")

    result["components"]["hvn_lvn"] = {
        "score": hvn_node_score,
        "notes": hvn_notes
    }

    # ═══════════════════════════════════════════
    # 11. 因果目标推演 (±8分)
    # ═══════════════════════════════════════════
    ce_data = ce_score(code, current_price=current_price)
    cause_target_score = ce_data.get("score", 0)
    ce_notes = [ce_data.get("detail", "")]
    if ce_data.get("targets"):
        t = ce_data["targets"]
        ce_notes.append(f"目标: {t.get('conservative',0):.1f}/{t.get('moderate',0):.1f}/{t.get('aggressive',0):.1f}")
    # 联动: 因果目标增强accumulation评分
    if ce_data.get("cause") and ce_data["cause"].get("cause_days", 0) >= 60:
        acc_score += 2
        acc_notes.append("🔗 长吸筹(>60天): 因果法则确认推进基础")
        result["components"]["accumulation"]["score"] += 2

    result["components"]["cause_effect"] = {
        "score": cause_target_score,
        "targets": ce_data.get("targets"),
        "notes": ce_notes
    }

    # ═══════════════════════════════════════════
    # 12. 综合评分 (总分229 = 45+40+25+30+15+25+20+8+8+5+8)
    # ═══════════════════════════════════════════
    vp_s = result["components"]["volume_profile"]["score"]
    st_s = result["components"]["supply_test"]["score"]
    mf_s = result["components"]["money_flow"]["score"]
    ac_s = result["components"]["accumulation"]["score"]
    br_s = result["components"]["breakout"]["score"]
    cv_s = result["components"]["delta_cvd"]["score"]
    ab_s = result["components"]["absorption"]["score"]
    of_s = result["components"]["ofi_imbalance"]["score"]
    or_s = result["components"]["opening_range"]["score"]
    hv_s = result["components"]["hvn_lvn"]["score"]
    ce_s = result["components"]["cause_effect"]["score"]
    mc_s = result["components"]["market_context"]["score"]
    total = vp_s + st_s + mf_s + ac_s + br_s + cv_s + ab_s + of_s + or_s + hv_s + ce_s + mc_s

    if total >= 146: confidence = "A++"; action = "强烈买入"
    elif total >= 114: confidence = "A"; action = "买入"
    elif total >= 80: confidence = "B"; action = "谨慎持有/小幅加仓"
    elif total >= 42: confidence = "C"; action = "观望，等信号确认"
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
        f"CVD:{cvd_notes[0] if cvd_notes else '-'}",
        f"吸收:{absorb['summary']}",
        f"VWAP:{vwap_result.get('summary','-')[:50]}",
        f"综合:{vp_s}+{st_s}+{mf_s}+{ac_s}+{br_s}+{cv_s}+{ab_s}+{of_s}={total}分 | {confidence}级 | {action}"
    ]
    return result


def format_report(r):
    print(f"\n{'='*60}")
    print(f"  🎯 八维联合作战 — {r['code']} @ {r['price']} ({r['change_pct']:+.2f}%)")
    print(f"{'='*60}")

    vp = r["components"]["volume_profile"]
    st = r["components"]["supply_test"]
    mf = r["components"]["money_flow"]
    ac = r["components"]["accumulation"]
    br = r["components"]["breakout"]
    cv = r["components"].get("delta_cvd", {})
    ab = r["components"].get("absorption", {})
    vw = r["components"].get("vwap", {})

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

    if cv:
        sos_q = cv.get("sos_quality", {})
        print(f"\n  ┌─ CVD主动买卖差 ({cv.get('score', 0)}分) ──┐")
        if sos_q:
            print(f"  │ SOS质量: {sos_q.get('quality', '?')}级 ({sos_q.get('description', '')})")
        for n in cv.get("notes", []): print(f"  │ {n}")
        print(f"  └──────────────────────────────┘")

    ab = r["components"].get("absorption", {})
    if ab:
        print(f"\n  ┌─ 吸收检测 ({ab.get('score', 0)}分) ──────┐")
        print(f"  │ 主导: {ab.get('dominant', 'none')} | {ab.get('supply_test_boost', 0):+d}联动")
        if ab.get("wyckoff_impact"): print(f"  │ {ab['wyckoff_impact'][:60]}")
        for n in ab.get("notes", [])[:3]: print(f"  │ {n}")
        print(f"  └──────────────────────────────┘")

    if vw:
        print(f"\n  ┌─ VWAP公允价值 (偏置层) ─────────┐")
        if vw.get("vwap_data"):
            wd = vw["vwap_data"]
            print(f"  │ VWAP:{wd['vwap']} | +1SD:{wd['+1sd']} | -1SD:{wd['-1sd']}")
        print(f"  │ 日型:{vw.get('day_type','?')} | 偏置:{vw.get('bias','?')}(x{vw.get('amplifier',1.0)})")
        for n in vw.get("notes", [])[:3]: print(f"  │ {n}")
        print(f"  └──────────────────────────────┘")

    fp = r["components"].get("footprint", {})
    if fp and fp.get("signals"):
        print(f"\n  ┌─ Footprint微观 ──────────────────┐")
        for n in fp.get("notes", []): print(f"  │ {n}")
        print(f"  └──────────────────────────────┘")

    ofi = r["components"].get("ofi_imbalance", {})
    if ofi:
        print(f"\n  ┌─ OFI订单流失衡 ({ofi.get('score', 0):+d}分) ──────┐")
        print(f"  │ OFI:{ofi.get('ofi_current', 0):+.2f} | {ofi.get('ofi_trend', '?')}")
        for n in ofi.get("notes", []): print(f"  │ {n}")
        print(f"  └──────────────────────────────┘")

    or_comp = r["components"].get("opening_range", {})
    if or_comp:
        print(f"\n  ┌─ 开盘区间 ({or_comp.get('score', 0):+d}分) ────────┐")
        for n in or_comp.get("notes", []): print(f"  │ {n}")
        print(f"  └──────────────────────────────┘")

    print(f"\n  ╔════════════════════════════════════╗")
    print(f"  ║  多维评分: {r['joint_score']}/216 → {r['confidence']}级 → {r['recommendation']}  ║")
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
