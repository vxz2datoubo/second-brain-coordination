"""absorption_detector.py — 吸收检测引擎 v1

"大量订单被吃掉但价格不动" → 识别主力隐藏吸筹/派筹

核心功能:
- bid_absorption_check(): 支撑位买方吸收 → 主力接货建仓 (隐藏吸筹)
- ask_absorption_check(): 阻力位卖方吸收 → 主力挂单派发 (隐藏派筹)
- detect(): 综合吸收检测 → 返回类型/价格/置信度/威科夫联动建议
- score_for_quad_lens(): 为六维系统提供吸收评分

T+1适配:
  不依赖"被迫平仓"逻辑
  改为: Bid吸收→主力成本防线确认; Ask吸收→主力派发/试盘位确认

联动技能:
  supply-test, accumulation-detection, delta-cvd, money-flow-divergence, breakout-validator
"""

import json, os
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_absorption_state.json")


def _load_absorption_state():
    if not os.path.exists(STATE_FILE): return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return {}


def _save_absorption_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _load_cvd_history(code):
    """从delta_cvd的state文件获取CVD历史"""
    cvd_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_delta_state.json")
    if not os.path.exists(cvd_file): return []
    with open(cvd_file, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data.get(f"d_{code}", {}).get("history", [])
        except:
            return []


# ──────────────────────────────────────────────
#  吸收检测核心
# ──────────────────────────────────────────────

def bid_absorption_check(code, current_price, day_low, day_high):
    """
    检测支撑位附近是否存在Bid吸收（隐藏吸筹）
    
    条件:
    1. 价格在日内低位区域（距day_low <35%区间）
    2. 出现强负Delta（主动卖盘大）
    3. 价格止跌不创新低
    4. 成交量集中在窄幅区间
    
    Returns:
        dict: detected(bool), confidence(int 0-100), defense_price(float),
              wyckoff_link(str, 威科夫联动建议)
    """
    history = _load_cvd_history(code)
    if len(history) < 5:
        return {"detected": False, "confidence": 0, "defense_price": None,
                "wyckoff_link": "", "detail": "CVD数据不足"}

    # 条件1: 价格在低位区域
    near_low = (current_price - day_low) / max(day_high - day_low, 0.01)
    if near_low > 0.35:
        return {"detected": False, "confidence": 0, "defense_price": None,
                "wyckoff_link": "", "detail": f"价格不在低位(位置{near_low:.0%})"}

    confidence = 0
    defense_price = None
    evidence = []

    # 条件2+3: 最近采样点出现强负Delta + 价格不跌
    recent5 = history[-5:]
    for i in range(2, len(recent5)):
        delta_abs = abs(recent5[i]["d"])
        price_range_3 = max(abs(recent5[j]["p"] - recent5[j-1]["p"]) for j in range(max(0, i-2), i+1))
        
        # 强负Delta
        if recent5[i]["d"] < -2000 and delta_abs > 3000:
            # 价格是否停滞
            if price_range_3 < current_price * 0.003:
                confidence += 30
                defense_price = recent5[i]["p"]
                evidence.append(f"时点{recent5[i]['t']}: Delta{int(recent5[i]['d']):,}(强负), 价格{recent5[i]['p']:.2f}停滞")
            elif price_range_3 < current_price * 0.006:
                confidence += 15
                evidence.append(f"时点{recent5[i]['t']}: Delta{int(recent5[i]['d']):,}(负), 价格微动")

    # 条件4: CVD在低位是否企稳
    cvd5 = [h["c"] for h in recent5]
    if len(cvd5) >= 3 and cvd5[-1] >= cvd5[-3]:
        confidence += 20
        evidence.append("CVD低位企稳: 主动买卖差在低位不再下降")
    elif len(cvd5) >= 3:
        confidence += 5

    # 价格在最近是否出现下影线（收盘>最低点）
    if len(recent5) >= 2:
        recent_prices = [h["p"] for h in recent5]
        if recent_prices[-1] >= recent_prices[-2]:
            confidence += 15
            evidence.append("价格企稳: 最近采样不再创新低")

    detected = confidence >= 30
    wyckoff_link = ""
    if detected:
        if near_low < 0.20:
            wyckoff_link = "Phase C Spring区域Bid吸收 → Spring真实,主力在最低点接盘 → 准备LPS/SOS"
        else:
            wyckoff_link = "Phase B 供应测试Bid吸收 → 测试通过,主力防守牢固 → 等待SOS确认"

    return {
        "detected": detected,
        "confidence": min(confidence, 100),
        "defense_price": defense_price,
        "defense_zone": f"{day_low:.2f}-{current_price:.2f}" if defense_price else None,
        "wyckoff_link": wyckoff_link,
        "evidence": evidence,
        "t1_note": "T+1: 主力在此接货建仓→成本防线,卖方无法日内再次抛售→高置信度",
        "detail": f"Bid吸收{'确认' if detected else '未触发'}(置信度{confidence})"
    }


def ask_absorption_check(code, current_price, day_low, day_high):
    """
    检测阻力位附近是否存在Ask吸收（隐藏派筹）
    
    条件:
    1. 价格在日内高位区域（距day_high <35%区间）
    2. 出现强正Delta（主动买盘大）
    3. 价格停滞不创新高
    4. 成交量集中在窄幅区间
    
    Returns:
        dict: detected(bool), confidence(int), distribution_price(float),
              wyckoff_link(str)
    """
    history = _load_cvd_history(code)
    if len(history) < 5:
        return {"detected": False, "confidence": 0, "distribution_price": None,
                "wyckoff_link": "", "detail": "CVD数据不足"}

    near_high = (day_high - current_price) / max(day_high - day_low, 0.01)
    if near_high > 0.35:
        return {"detected": False, "confidence": 0, "distribution_price": None,
                "wyckoff_link": "", "detail": f"价格不在高位(距高点{near_high:.0%})"}

    confidence = 0
    distribution_price = None
    evidence = []

    recent5 = history[-5:]
    for i in range(2, len(recent5)):
        delta_abs = abs(recent5[i]["d"])
        price_range_3 = max(abs(recent5[j]["p"] - recent5[j-1]["p"]) for j in range(max(0, i-2), i+1))

        # 强正Delta
        if recent5[i]["d"] > 2000 and delta_abs > 3000:
            if price_range_3 < current_price * 0.003:
                confidence += 30
                distribution_price = recent5[i]["p"]
                evidence.append(f"时点{recent5[i]['t']}: Delta+{int(recent5[i]['d']):,}(强正), 价格{recent5[i]['p']:.2f}停滞")
            elif price_range_3 < current_price * 0.006:
                confidence += 15

    # CVD在高位是否走平或下降
    cvd5 = [h["c"] for h in recent5]
    if len(cvd5) >= 3 and cvd5[-1] <= cvd5[-3]:
        confidence += 20
        evidence.append("CVD高位走平/下降: 主动买盘在高位被对冲")
    elif len(cvd5) >= 3:
        confidence += 5

    # 价格是否不再创新高
    if len(recent5) >= 2:
        recent_prices = [h["p"] for h in recent5]
        if recent_prices[-1] <= recent_prices[-2]:
            confidence += 15
            evidence.append("价格停滞: 最近采样不再创新高")

    detected = confidence >= 30
    wyckoff_link = ""
    if detected:
        wyckoff_link = "Phase E 派发预警: 阻力位Ask吸收 → 主力在挂单出货 → 警惕顶部形成"

    return {
        "detected": detected,
        "confidence": min(confidence, 100),
        "distribution_price": distribution_price,
        "distribution_zone": f"{current_price:.2f}-{day_high:.2f}" if distribution_price else None,
        "wyckoff_link": wyckoff_link,
        "evidence": evidence,
        "t1_note": "T+1: 主力在此挂单派发→真实阻力位, 买方今日无法卖出→可能次日形成抛压",
        "detail": f"Ask吸收{'确认' if detected else '未触发'}(置信度{confidence})"
    }


def detect(code, current_price, day_low, day_high):
    """
    综合吸收检测 — 同时检查Bid吸收和Ask吸收
    
    Returns:
        dict:
        - bid_absorption: bid_absorption_check结果
        - ask_absorption: ask_absorption_check结果
        - dominant: "bid" / "ask" / "none" — 当前主导吸收方向
        - summary: 一句话总结
        - wyckoff_impact: 对威科夫Phase判断的影响
        - supply_test_boost: 供应测试加分建议 (-10~+12)
        - sos_impact: 对SOS质量的影响描述
    """
    bid = bid_absorption_check(code, current_price, day_low, day_high)
    ask = ask_absorption_check(code, current_price, day_low, day_high)

    # 判断主导方向
    if bid["detected"] and ask["detected"]:
        dominant = "both"  # 罕见: 高低位同时吸收 = 宽幅震荡洗盘
        summary = "⚠️ 双向吸收: 高低位同时检测到吸收, 主力可能在宽幅洗盘"
    elif bid["detected"]:
        dominant = "bid"
        summary = f"🟢 Bid吸收(隐藏吸筹): 主力在{bid['defense_price']:.2f}附近接货建仓, 置信度{bid['confidence']}"
    elif ask["detected"]:
        dominant = "ask"
        summary = f"🔴 Ask吸收(隐藏派筹): 主力在{ask['distribution_price']:.2f}附近挂单派发, 置信度{ask['confidence']}"
    else:
        dominant = "none"
        summary = "无吸收信号"

    # 供应测试联动建议
    supply_test_boost = 0
    if bid["detected"]:
        if bid["confidence"] >= 60: supply_test_boost = 12
        elif bid["confidence"] >= 40: supply_test_boost = 8
        else: supply_test_boost = 4
    if ask["detected"]:
        if ask["confidence"] >= 60: supply_test_boost = -8
        elif ask["confidence"] >= 40: supply_test_boost = -5
        else: supply_test_boost = max(supply_test_boost - 3, -10)

    # SOS影响描述
    sos_impact = ""
    if bid["detected"]:
        sos_impact = f"Bid吸收确认主力成本防线@{bid['defense_price']:.2f}, SOS突破时该价位为坚固支撑, 可放心拉升"
    elif ask["detected"]:
        sos_impact = f"Ask吸收警告: 主力在{ask['distribution_price']:.2f}附近有派发行为, SOS突破前需确认该阻力已被完全消化"

    # 保存检测记录
    state = _load_absorption_state()
    key = f"a_{code}"
    records = state.get(key, [])
    records.append({
        "t": datetime.now().strftime("%H:%M"),
        "p": current_price,
        "dominant": dominant,
        "bid_conf": bid["confidence"],
        "ask_conf": ask["confidence"],
        "supply_boost": supply_test_boost
    })
    if len(records) > 50: records = records[-50:]
    state[key] = records
    _save_absorption_state(state)

    return {
        "bid_absorption": bid,
        "ask_absorption": ask,
        "dominant": dominant,
        "summary": summary,
        "wyckoff_impact": bid["wyckoff_link"] if bid["detected"] else ask["wyckoff_link"] if ask["detected"] else "",
        "supply_test_boost": supply_test_boost,
        "sos_impact": sos_impact,
        "t1_context": "T+1适配: 吸收不依赖被迫平仓, 改为定位主力防守/派发位置增强威科夫判断"
    }


def score_for_quad_lens(code):
    """
    为六维系统提供吸收评分（-20~+20分）
    
    这是吸收在quad_lens中的独立贡献，
    与CVD评分、供应测试评分并行。
    """
    state = _load_absorption_state()
    key = f"a_{code}"
    if key not in state or not state[key]:
        return {"score": 0, "detail": "无吸收数据", "signals": []}

    records = state[key]
    if len(records) < 1:
        return {"score": 0, "detail": "无吸收数据", "signals": []}

    # 只看最近3次检测
    recent = records[-3:]
    score = 0
    signals = []

    bid_count = sum(1 for r in recent if r["dominant"] == "bid")
    ask_count = sum(1 for r in recent if r["dominant"] == "ask")
    both_count = sum(1 for r in recent if r["dominant"] == "both")

    if bid_count >= 2:
        # 连续Bid吸收 → 主力持续建仓 → 强烈看涨
        score = 20
        signals.append("连续Bid吸收: 主力持续接货,强看涨")
    elif bid_count == 1:
        score = 12
        signals.append("Bid吸收: 主力防守确认,看涨")
    elif both_count >= 1:
        score = 8
        signals.append("双向吸收: 宽幅洗盘,方向待定")

    if ask_count >= 2:
        score = min(score - 15, -5)
        signals.append("连续Ask吸收: 主力持续派发,警惕顶部")
    elif ask_count == 1:
        score = min(score - 8, 3)
        signals.append("Ask吸收: 阻力确认,警惕回调")

    # 取最近一次supply_boost
    last_boost = recent[-1].get("supply_boost", 0)
    if last_boost > 0:
        signals.append(f"供应测试联动+{last_boost}")

    return {
        "score": max(-20, min(20, score)),
        "detail": " | ".join(signals) if signals else "无显著吸收信号",
        "signals": signals
    }


def summary(code):
    """一句话吸收摘要"""
    state = _load_absorption_state()
    key = f"a_{code}"
    if key not in state or not state[key]:
        return ""
    last = state[key][-1]
    d = last["dominant"]
    if d == "bid": return f"🟢 Bid吸收(置信度{last['bid_conf']}): 主力吸筹中"
    elif d == "ask": return f"🔴 Ask吸收(置信度{last['ask_conf']}): 主力派发中"
    elif d == "both": return f"⚠️ 双向吸收: 洗盘"
    return "无吸收信号"


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("price", type=float)
    p.add_argument("high", type=float)
    p.add_argument("low", type=float)
    args = p.parse_args()

    result = detect(args.code, args.price, args.low, args.high)

    print(f"\n{'='*50}")
    print(f"  🔍 吸收检测 — {args.code} @ {args.price}")
    print(f"{'='*50}")
    print(f"  主导: {result['dominant']}")
    print(f"  总结: {result['summary']}")
    print(f"  {result['t1_context']}")
    if result['wyckoff_impact']:
        print(f"  威科夫: {result['wyckoff_impact']}")
    if result['sos_impact']:
        print(f"  SOS: {result['sos_impact']}")
    print(f"  供应测试联动: {result['supply_test_boost']:+d}分")

    bid = result['bid_absorption']
    ask = result['ask_absorption']
    if bid['detected']:
        print(f"\n  Bid吸收详情:")
        for e in bid['evidence']: print(f"    · {e}")
        print(f"    防守价: {bid['defense_price']:.2f} | 区间: {bid['defense_zone']}")
        print(f"    置信度: {bid['confidence']}")
    if ask['detected']:
        print(f"\n  Ask吸收详情:")
        for e in ask['evidence']: print(f"    · {e}")
        print(f"    派发价: {ask['distribution_price']:.2f} | 区间: {ask['distribution_zone']}")
        print(f"    置信度: {ask['confidence']}")
    print()
