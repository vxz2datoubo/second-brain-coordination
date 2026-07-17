"""delta_cvd.py — 主动买卖差(Delta/CVD)分析 v4

深度升级(v3→v4):
- T+1环境适配: 吸收信号不依赖"被困交易者被迫平仓"逻辑
  改为: 定位主力防守位置 → 增强威科夫供应测试/SOS突破质量判断
- supply_test_cvd_confirm(): CVD与供应测试联动确认
- sos_quality_check(): 突破前CVD健康度评估
- t1_context_note(): T+1环境下CVD信号的正确解读方式

v2→v3升级:
- 吸收(Absorption)检测: 高Delta+价格不动 → "有人在防守"
- 耗竭(Exhaustion)检测: Delta逐波缩小+价格勉强推进 → "没人继续推"
- 努力vs结果(Effort vs Result)框架: 2x2矩阵分类
- 信号质量Tier分层: Gold/Standard/Auxiliary

学术基础:
- Anantha & Jain (2024) Hawkes OFI Forecasting
- Cont, Cucuringu & Zhang (2023) Cross-impact OFI
- United Daytraders Absorption/Exhaustion Framework
"""

import json, os
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_delta_state.json")


def load_state():
    if not os.path.exists(STATE_FILE): return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _safe_get(lst, idx, default):
    try: return lst[idx]
    except (IndexError, TypeError): return default


# ──────────────────────────────────────────────
#  T+1 适配层: 核心差异说明
# ──────────────────────────────────────────────

T1_CONTEXT = """
## A股T+1环境下CVD信号的正确解读

### 西方市场(CVD标准理论)的逻辑链:
  吸收 → 激进方被套 → 被迫平仓 → 反方向放大 → 反转加速 ✓

### A股T+1环境下:
  ✗ "被迫平仓放大反转"逻辑不适用 (当天买的不能当天卖)
  ✓ 但吸收信号的核心价值不变: 揭示主力在什么位置建立了防守

### T+1适配解读:
  - Bid吸收(支撑位): 不是"卖方被迫买回", 而是"主力在此价位大量建仓防守" 
    → 该价位成为强支撑 → 后续SOS突破更有底气
  - Ask吸收(阻力位): 不是"买方被迫卖出", 而是"主力在此价位派发/试盘"
    → 该价位成为真实阻力 → 突破需要更大成交量
  - 耗竭: T+1下卖方耗竭更可靠 (卖方今天卖出后明天才能再卖)
    → 卖方耗竭+缩量 = 高置信度底部信号

### 与威科夫联动增强:
  Phase B供应测试 + CVD Bid吸收 = 双重确认主力在支撑位防守
  → 供应测试通过率↑ → SOS质量评级提升
  Phase C Spring + CVD Bid吸收 = Spring真实性确认
  Phase E 派发 + CVD Ask吸收(阻力位) = 主力在出货
"""


def t1_context_note():
    """获取T+1环境下的CVD解读上下文"""
    return T1_CONTEXT


def supply_test_cvd_confirm(code, current_price, day_low, day_high):
    """
    T+1适配: CVD吸收信号与威科夫供应测试联动
    
    核心思路(非西方逻辑):
    不是 "激进方被套→被迫平仓→反转放大"
    而是 "主力在此位置建立了防守 → 该位置是真实支撑/阻力"
    
    Returns:
        dict with:
        - cvd_confirmation: "strong" / "moderate" / "weak" / "none"
        - defense_level: 主力防守价格位
        - boost_to_supply_test: 供应测试加分 (0~12)
        - boost_to_sos: SOS质量提升 (0~8)
        - interpretation: T+1环境下的解读
    """
    state = load_state()
    key = f"d_{code}"
    if key not in state:
        return {"cvd_confirmation": "none", "defense_level": None,
                "boost_to_supply_test": 0, "boost_to_sos": 0,
                "interpretation": "无CVD数据"}

    h = state[key].get("history", [])
    if len(h) < 5:
        return {"cvd_confirmation": "none", "defense_level": None,
                "boost_to_supply_test": 0, "boost_to_sos": 0,
                "interpretation": "CVD数据不足(<5采样点)"}

    recent5 = h[-5:]
    boost_supply = 0
    boost_sos = 0
    confirmation = "none"
    defense_level = None
    interpretations = []

    # ── 检测支撑位附近的Bid吸收 ──
    # 条件: 价格在日内低位附近 + Delta强负(主动卖盘大) + 价格止跌
    near_low = (current_price - day_low) / max(day_high - day_low, 0.01)
    if near_low < 0.35:  # 价格在日内低位35%以内
        deltas = [x["d"] for x in recent5]
        # 近3次Delta有没有出现"大负但价格不跌"的Bid吸收
        for i in range(2, len(recent5)):
            d_abs = abs(recent5[i]["d"])
            price_move = abs(recent5[i]["p"] - recent5[i-2]["p"])
            if d_abs > 3000 and price_move < max(current_price * 0.002, 0.1):
                confirmation = "strong"
                defense_level = recent5[i]["p"]
                boost_supply = 12
                boost_sos = 8
                interpretations.append(
                    f"🟢 T+1 Bid吸收@{defense_level:.2f}: "
                    f"主力在{defense_level:.2f}附近大量接货防守(主动卖盘{int(d_abs):,}被吸收), "
                    + "非西方被迫平仓逻辑, 而是该价位已确认为主力成本防线"
                )
                break
        else:
            # 次强: CVD在低位走平或上行
            cvd5 = [x["c"] for x in recent5]
            if cvd5[-1] >= cvd5[0]:
                confirmation = "moderate"
                defense_level = current_price
                boost_supply = 6
                boost_sos = 4
                interpretations.append(
                    f"🟡 T+1 CVD低位企稳: 价格接近日内低点但CVD不创新低, "
                    f"主力在低位有承接意愿"
                )

    # ── 检测阻力位附近的Ask吸收 ──
    near_high = (day_high - current_price) / max(day_high - day_low, 0.01)
    if near_high < 0.35:  # 价格在日内高位35%以内
        deltas = [x["d"] for x in recent5]
        for i in range(2, len(recent5)):
            d_abs = abs(recent5[i]["d"])
            price_move = abs(recent5[i]["p"] - recent5[i-2]["p"])
            if d_abs > 3000 and recent5[i]["d"] > 0 and price_move < max(current_price * 0.002, 0.1):
                if confirmation != "strong":  # 不覆盖已有的strong
                    confirmation = "moderate"
                    defense_level = recent5[i]["p"]
                    boost_supply = -5  # 阻力位吸收 → 供应测试更难通过
                    boost_sos = -3     # SOS突破质量下降
                    interpretations.append(
                        f"🔴 T+1 Ask吸收@{defense_level:.2f}: "
                        f"主力在{defense_level:.2f}附近挂单派发/试盘, "
                        f"该位置是真实阻力, 突破需更大买盘"
                    )

    # ── 检测卖方耗竭 (T+1下更可靠!) ──
    if near_low < 0.40 and len(h) >= 8:
        recent8 = h[-8:]
        deltas8 = [abs(x["d"]) for x in recent8]
        # 卖方Delta逐波衰减
        if (len(deltas8) >= 8 and 
            deltas8[-1] < max(deltas8[:-1]) * 0.5 and
            recent8[-1]["p"] <= recent8[-2]["p"]):
            # 卖方耗竭: T+1下更可靠因为卖方今天卖出后明天才能再卖
            if confirmation != "strong":
                confirmation = "strong"
                defense_level = current_price
                boost_supply = 10
                boost_sos = 6
                interpretations.append(
                    f"🟢 T+1卖方耗竭确认: 主动卖盘逐波衰减, "
                    f"T+1下卖方已无法日内再次抛售 → 高置信度底部信号"
                )

    if not interpretations:
        interpretations.append("CVD无明显与供应测试联动信号")

    return {
        "cvd_confirmation": confirmation,
        "defense_level": defense_level,
        "boost_to_supply_test": boost_supply,
        "boost_to_sos": boost_sos,
        "interpretation": " | ".join(interpretations)
    }


def sos_quality_check(code, resistance_price):
    """
    SOS突破前CVD健康度评估 (T+1适配)
    
    在Phase C→D过渡、判断SOS突破质量时调用。
    不是看"有多少人被套要平仓"，
    而是看"CVD趋势是否支撑这次突破"。
    
    Returns:
        dict with quality (A/B/C/D), score (0~15), warnings
    """
    state = load_state()
    key = f"d_{code}"
    if key not in state:
        return {"quality": "D", "score": 0, "warnings": ["无CVD数据"]}

    h = state[key].get("history", [])
    if len(h) < 8:
        return {"quality": "D", "score": 0, "warnings": ["数据不足"]}

    warnings = []
    score = 0

    # 1. CVD趋势方向 (4分)
    recent8 = h[-8:]
    cvd_trend = recent8[-1]["c"] - recent8[0]["c"]
    if cvd_trend > 0:
        score += 4
    else:
        warnings.append(f"CVD趋势向下({cvd_trend:+.0f}), 突破缺乏主动买盘支撑")
        score -= 2

    # 2. 最近Delta健康度 (4分)
    recent_deltas = [x["d"] for x in recent8[-4:]]
    positive_count = sum(1 for d in recent_deltas if d > 0)
    if positive_count >= 3:
        score += 4
    elif positive_count >= 2:
        score += 2
    else:
        warnings.append(f"最近4次采样{positive_count}/4次正Delta, 主动买盘不足")
        score -= 1

    # 3. 突破位附近有无Ask吸收 (4分)
    # T+1下: 如果突破位附近出现Ask吸收 → 主力可能在派发 → SOS质量下降
    for i in range(2, len(recent8)):
        if abs(recent8[i]["p"] - resistance_price) / resistance_price < 0.01:
            if recent8[i]["d"] > 3000:  # 主动买盘大但...
                # 检查同时价格是否停滞
                price_move = abs(recent8[i]["p"] - recent8[i-1]["p"])
                if price_move < resistance_price * 0.002:
                    warnings.append(f"突破位{resistance_price}附近出现Ask吸收 → T+1下主力可能在此派发")
                    score -= 3

    # 4. 努力vs结果一致性 (3分)
    # 健康的SOS应该: 高努力(大Delta) + 高结果(价格上涨)
    recent3 = h[-3:]
    price_up = recent3[-1]["p"] > recent3[0]["p"]
    delta_positive = sum(x["d"] for x in recent3) > 0
    if price_up and delta_positive:
        score += 3  # 完美: 价格涨+主动买盘
    elif price_up and not delta_positive:
        warnings.append("价格涨但CVD负 → 上涨由限价单撤退驱动而非主动买盘, 突破质量可疑")
        score -= 2
    elif not price_up and delta_positive:
        warnings.append("CVD正但价格不涨 → 努力无结果, 买盘被吸收, 突破受阻")
        score -= 1

    # 分级
    score = max(0, min(15, score))
    if score >= 12: quality = "A"; desc = "CVD健康, 突破有主动买盘强力支撑"
    elif score >= 8: quality = "B"; desc = "CVD基本健康, 突破可期但有少量隐忧"
    elif score >= 4: quality = "C"; desc = "CVD偏弱, 建议等待更强确认"
    else: quality = "D"; desc = "CVD不支持突破, 警惕假突破"

    return {
        "quality": quality, "score": score, "description": desc,
        "warnings": warnings,
        "t1_note": "T+1适配: CVD评估基于'主力防守位置'而非'被迫平仓压力', 更侧重判断SOS的真实性"
    }


# ──────────────────────────────────────────────
#  核心CVD更新逻辑 (保持v3功能不变)
# ──────────────────────────────────────────────

def update(code, price, outside, inside):
    """更新Delta/CVD状态"""
    state = load_state()
    key = f"d_{code}"
    prev = state.get(key, {})

    Po = prev.get("outside", outside)
    Pi = prev.get("inside", inside)

    dS = int(outside - Po) - int(inside - Pi)
    dt = int(outside) - int(inside)
    total = outside + inside
    dt_pct = dt / max(total, 1) * 100 if total > 0 else 0
    cvd = prev.get("cvd", 0) + dS

    hist = prev.get("history", [])
    hist.append({"t": datetime.now().strftime("%H:%M"), "d": dS, "c": cvd, "p": price})
    if len(hist) > 200: hist = hist[-200:]

    state[key] = {"outside": outside, "inside": inside, "cvd": cvd, "history": hist}
    save_state(state)

    signals = []
    div = None
    absorption = None
    exhaustion = None
    effort_result = None
    signal_tier = "none"

    # CVD趋势
    trend = "start"
    trend_detail = ""
    if len(hist) >= 5:
        c5 = [h["c"] for h in hist[-5:]]
        if c5[-1] > c5[0]:
            trend = "up"
            if len(hist) >= 10:
                c10_first = sum(h["c"] for h in hist[-10:-5]) / 5
                c10_last = sum(h["c"] for h in hist[-5:]) / 5
                trend_detail = "加速上行" if (c10_last - c10_first) > abs(c10_first) * 0.1 else "稳步上行" if c10_last > c10_first else "上行减速"
        elif c5[-1] < c5[0]:
            trend = "down"
            if len(hist) >= 10:
                c10_first = sum(h["c"] for h in hist[-10:-5]) / 5
                c10_last = sum(h["c"] for h in hist[-5:]) / 5
                trend_detail = "加速下行" if abs(c10_last - c10_first) > abs(c10_first) * 0.1 else "稳步下行" if c10_last < c10_first else "下行减速"
        else:
            trend = "flat"; trend_detail = "横盘"
    elif len(hist) >= 2:
        c2 = [h["c"] for h in hist[-2:]]
        trend = "up" if c2[-1] > c2[0] else "down" if c2[-1] < c2[0] else "flat"

    # CVD背离
    if len(hist) >= 3:
        l3 = hist[-3:]
        dp_short = price - l3[0]["p"]
        dc_short = l3[-1]["c"] - l3[0]["c"]
        div_price_threshold = max(price * 0.005, 0.3)
        div_delta_threshold = 2000

        if len(hist) >= 8:
            l8 = hist[-8:]
            dp_mid = price - l8[0]["p"]
            dc_mid = l8[-1]["c"] - l8[0]["c"]
            if abs(dp_mid) > div_price_threshold and dp_mid > 0 and dc_mid < -div_delta_threshold * 2:
                div = {"type": "bearish", "det": "中期看跌背离: 价格走高但CVD持续下降, 买方耗尽"}
                signal_tier = "standard"
            elif abs(dp_mid) > div_price_threshold and dp_mid < 0 and dc_mid > div_delta_threshold * 2:
                div = {"type": "bullish", "det": "中期看涨背离: 价格走低但CVD持续上升, 隐藏买盘"}
                signal_tier = "standard"
            elif dp_short > div_price_threshold and dc_short < -div_delta_threshold:
                div = {"type": "bearish", "det": "短期看跌背离: 价格小涨CVD下降→主动卖压增大"}
            elif dp_short < -div_price_threshold and dc_short > div_delta_threshold:
                div = {"type": "bullish", "det": "短期看涨背离: 价格小跌CVD上升→主动买盘承接"}

    # 吸收检测
    if len(hist) >= 3:
        recent = hist[-3:]
        price_range = max(h["p"] for h in recent) - min(h["p"] for h in recent)
        delta_abs = abs(dS)
        total_vol = abs(outside - Po) + abs(inside - Pi)
        total_vol = max(total_vol, 1)
        pct_price_threshold = max(price * 0.002, 0.15)

        if delta_abs > 3000 and price_range < pct_price_threshold and delta_abs / total_vol > 0.5:
            if dS > 0:
                absorption = {
                    "type": "ask_absorption",
                    "desc": "阻力位卖方吸收: 大量主动买单但价格不涨, 被动卖方防守",
                    "implication": "看跌——T+1: 主力在此派发/试盘, 突破需更大买盘",
                    "tier": "gold"
                }
                signals.append("🔴 卖方吸收(Ask侧): 主动买盘被压制 — T+1: 主力防守位确认")
                signal_tier = "gold"
            else:
                absorption = {
                    "type": "bid_absorption",
                    "desc": "支撑位买方吸收: 大量主动卖单但价格不跌, 被动买方接货",
                    "implication": "看涨——T+1: 主力在此建仓防守, 形成强支撑",
                    "tier": "gold"
                }
                signals.append("🟢 买方吸收(Bid侧): 主动卖盘被吸收 — T+1: 主力成本防线")
                signal_tier = "gold"

    # 耗竭检测
    if len(hist) >= 8 and not absorption:
        recent8 = hist[-8:]
        price_trend_up = recent8[-1]["p"] > recent8[0]["p"]
        price_trend_down = recent8[-1]["p"] < recent8[0]["p"]
        deltas = [h["d"] for h in recent8]
        d_first_half = sum(abs(x) for x in deltas[:4]) / 4
        d_second_half = sum(abs(x) for x in deltas[4:]) / 4

        if price_trend_up and d_second_half < d_first_half * 0.7 and recent8[-1]["p"] - recent8[0]["p"] > price * 0.005:
            exhaustion = {
                "type": "buyer_exhaustion",
                "desc": "买方耗尽: 价格上涨但主动买盘衰减",
                "implication": "看跌——T+1: 买方当日已无力继续推高"
            }
            signals.append("⚠️ 买方耗竭: 主动买盘衰减 — T+1: 当日推高动力不足")
            if signal_tier != "gold": signal_tier = "standard"

        elif price_trend_down and d_second_half < d_first_half * 0.7 and recent8[0]["p"] - recent8[-1]["p"] > price * 0.005:
            exhaustion = {
                "type": "seller_exhaustion",
                "desc": "卖方耗尽: 价格下跌但主动卖盘衰减",
                "implication": "看涨——T+1: 卖方已无法日内再次抛售, 高置信度"
            }
            signals.append("🟢 卖方耗竭: 主动卖盘衰减 — T+1高置信度: 卖方日内无弹药")
            if signal_tier != "gold": signal_tier = "gold"

    # 努力vs结果
    if len(hist) >= 2:
        l2 = hist[-2:]
        price_move = abs(l2[-1]["p"] - l2[0]["p"])
        delta_move = abs(dS)
        vol_total = abs(outside - Po) + abs(inside - Pi)
        effort = "high" if vol_total > 5000 and delta_move > 2000 else "medium" if vol_total > 2000 or delta_move > 1000 else "low"
        result = "high" if price_move > price * 0.005 else "medium" if price_move > price * 0.002 else "low"
        if effort == "high" and result == "low": effort_result = "高努力·低结果 → 吸收 → T+1: 主力防守位"
        elif effort == "high" and result == "high": effort_result = "高努力·高结果 → 趋势延续"
        elif effort == "low" and result == "high": effort_result = "低努力·高结果 → 低流动性漂移 → 警惕假突破"
        elif effort == "low" and result == "low": effort_result = "低努力·低结果 → 无效波动 → 观望"
        else: effort_result = f"{effort}努力·{result}结果 → 中性"

    # 买卖均衡
    bal = "buy" if dt_pct > 5 else "sell" if dt_pct < -5 else "flat"
    if bal == "buy": signals.append("主动买方占优")
    elif bal == "sell": signals.append("主动卖方占优")
    else: signals.append("买卖均衡")

    return {
        "out": outside, "inp": inside,
        "dt_day": dt, "dt_pct": round(dt_pct, 1),
        "dt_sess": dS, "cvd": cvd, "cvd_trend": trend,
        "cvd_trend_detail": trend_detail,
        "balance": bal, "div": div, "signals": signals,
        "absorption": absorption,
        "exhaustion": exhaustion,
        "effort_result": effort_result,
        "signal_tier": signal_tier,
        "hist_len": len(hist), "price": price
    }


def score_for_quad_lens(code):
    """为quad_lens.py提供CVD评分"""
    state = load_state()
    key = f"d_{code}"
    if key not in state:
        return {"score": 0, "confidence": 0, "signals": [], "detail": "无Delta数据"}

    h = state[key].get("history", [])
    if len(h) < 3:
        return {"score": 0, "confidence": 0, "signals": [], "detail": "数据不足"}

    score = 0
    detail_parts = []

    recent5 = h[-5:] if len(h) >= 5 else h
    cvd_trend = recent5[-1]["c"] - recent5[0]["c"]
    if cvd_trend > 0: score += 8; detail_parts.append("CVD上行+8")
    elif cvd_trend < 0: score -= 8; detail_parts.append("CVD下行-8")

    entry = state[key]
    dt_pct = entry.get("outside", 0) - entry.get("inside", 0)
    total = entry.get("outside", 0) + entry.get("inside", 0)
    dt_pct = dt_pct / max(total, 1) * 100 if total > 0 else 0
    if dt_pct > 10: score += 7; detail_parts.append("主动买>10% +7")
    elif dt_pct > 5: score += 4; detail_parts.append("主动买>5% +4")
    elif dt_pct < -10: score -= 7; detail_parts.append("主动卖>10% -7")
    elif dt_pct < -5: score -= 4; detail_parts.append("主动卖>5% -4")

    prices = [x["p"] for x in recent5]
    cvd_vals = [x["c"] for x in recent5]
    if prices[-1] > prices[0] and cvd_vals[-1] < cvd_vals[0]:
        score -= 5; detail_parts.append("看跌背离-5")
    elif prices[-1] < prices[0] and cvd_vals[-1] > cvd_vals[0]:
        score += 5; detail_parts.append("看涨背离+5")

    recent_deltas = [x["d"] for x in recent5]
    avg_delta = sum(recent_deltas) / len(recent_deltas)
    if avg_delta > 1000: score += 5; detail_parts.append(f"Delta均值+{int(avg_delta)} +5")
    elif avg_delta < -1000: score -= 5; detail_parts.append(f"Delta均值{int(avg_delta)} -5")

    confidence = min(80, len(h) * 5)
    return {
        "score": max(-25, min(25, score)),
        "confidence": confidence,
        "signals": detail_parts,
        "detail": " | ".join(detail_parts) if detail_parts else "无显著信号"
    }


def summary(code):
    """一句话摘要"""
    s = load_state()
    key = f"d_{code}"
    if key not in s: return ""
    entry = s[key]
    h = entry.get("history", [])
    if not h: return ""
    cvd_dir = ""
    if len(h) >= 3:
        cvd3 = [x["c"] for x in h[-3:]]
        cvd_dir = "↗" if cvd3[-1] > cvd3[0] else "↘" if cvd3[-1] < cvd3[0] else "→"
    d5 = sum(x["d"] for x in h[-5:]) if len(h) >= 5 else sum(x["d"] for x in h)
    dt = entry.get("outside", 0) - entry.get("inside", 0)
    total = entry.get("outside", 0) + entry.get("inside", 0)
    dt_pct = dt / max(total, 1) * 100 if total > 0 else 0
    return f"Delta{d5:+d} CVD{cvd_dir} 全日差{dt_pct:+.1f}%"


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("price", type=float)
    p.add_argument("outside", type=int)
    p.add_argument("inside", type=int)
    args = p.parse_args()
    r = update(args.code, args.price, args.outside, args.inside)
    print(f"外盘{args.outside} 内盘{args.inside}")
    print(f"全日差:{r['dt_day']}({r['dt_pct']:+.1f}%) CVD:{r['cvd']} {r['cvd_trend']}")
    if r.get('cvd_trend_detail'): print(f"趋势细节: {r['cvd_trend_detail']}")
    for s in r['signals']: print(f"· {s}")
    if r['div']: print(f"⚠️ {r['div']['det']}")
    if r.get('absorption'): print(f"🔍 {r['absorption']['desc']} → {r['absorption']['implication']}")
    if r.get('exhaustion'): print(f"🔍 {r['exhaustion']['desc']} → {r['exhaustion']['implication']}")
    if r.get('effort_result'): print(f"📊 努力vs结果: {r['effort_result']}")
    if r.get('signal_tier') != 'none': print(f"⭐ 信号等级: {r['signal_tier']}")
