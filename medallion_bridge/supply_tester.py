"""supply_tester.py — 威科夫-VSA供应测试分析 v2

功能:
  - 缩量回落 vs 放量回落判定
  - 急落 vs 缓落 矩阵分析
  - 三次供应测试跟踪
  - SOS (Sign of Strength) 信号检测
  - 盘中实时供应测试模块
"""

import sys, os, struct, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daytrade_system"))

from engine.indicators import KBar

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_supply_test_state.json")


def _tdx_min5(code, limit=50):
    market = "sz" if code.startswith(("0", "3")) else "sh"
    path = rf"F:\tongdaxin\vipdoc\{market}\fzline\{market}{code}.lc5"
    if not os.path.exists(path):
        return []
    bars = []
    with open(path, "rb") as f:
        data = f.read()
    n = len(data) // 32
    start = max(0, n - limit)
    for i in range(start, n):
        u = struct.unpack_from("<HHfffffIHH", data, i * 32)
        dw, sec = u[0], u[1]
        op, hi, lo, cl = u[2], u[3], u[4], u[5]
        amt = u[6]
        y, m, d = (dw // 2048) + 2004, (dw % 2048) // 100, dw % 2048 % 100
        bars.append(KBar(date=f"{y:04d}{m:02d}{d:02d}", time_sec=sec,
                         open=op, high=hi, low=lo, close=cl,
                         volume=amt / 100.0, amount=amt / 100.0))
    return bars


def _today_bars(code):
    bars = _tdx_min5(code, 200)
    if not bars:
        return []
    today = bars[-1].date
    return [b for b in bars if b.date == today]


def _velocity_analysis(bars):
    """分析最近3根bar的下跌速度和成交量特征
    Returns: {"type": "急落"/"缓落", "volume_level": "高"/"中"/"低", "details": str}
    """
    if len(bars) < 3:
        return {"type": "不足", "volume_level": "未知", "details": "数据不足"}
    last3 = bars[-3:]
    # 速度: 单位时间内价格变动
    price_drops = [last3[i-1].close - last3[i].close for i in range(1, 3)]
    time_diff = [(last3[i].time_sec - last3[i-1].time_sec) / 60.0 for i in range(1, 3)]
    speeds = [abs(d) / max(t, 1) for d, t in zip(price_drops, time_diff)] if all(t > 0 for t in time_diff) else [0, 0]
    avg_speed = sum(speeds) / len(speeds)
    avg_vol = sum(b.volume for b in last3) / 3
    # 分类
    vtype = "急落" if avg_speed > 0.05 else "缓落"
    vlevel = "高" if avg_vol > 30000 else "中" if avg_vol > 15000 else "低"
    return {"type": vtype, "volume_level": vlevel, "details": f"{vtype}+{vlevel}量"}


def analyze_supply_test(code, current_price, recent_high, recent_low, cvd_confirm=None):
    """主力供应测试分析: 输出5维信号
    
    cvd_confirm: delta_cvd.supply_test_cvd_confirm() 的返回值 (可选)
    T+1适配: CVD吸收信号用来确认主力在什么位置建立了防守，
    而非依赖西方市场的"被迫平仓"逻辑。
    """
    bars = _today_bars(code)
    if len(bars) < 5:
        return {"test_passed": False, "signal": None, "confidence": 0, "details": ["数据不足"]}
    last3 = bars[-3:]
    avg_vol_hist = sum(b.volume for b in bars[:-3]) / max(len(bars[:-3]), 1)
    vol_recent = sum(b.volume for b in last3) / 3
    vol_ratio = vol_recent / max(avg_vol_hist, 1)
    spreads_recent = [b.high - b.low for b in last3]
    avg_spread = sum(spreads_recent) / 3
    avg_spread_hist = sum(b.high - b.low for b in bars[:-3]) / max(len(bars[:-3]), 1)
    spread_ratio = avg_spread / max(avg_spread_hist, 0.01)
    close_positions = [(b.close - b.low) / max(b.high - b.low, 0.01) for b in last3]
    avg_close_pos = sum(close_positions) / 3
    vel = _velocity_analysis(bars)
    
    details = []
    score = 0
    # 1. 成交量萎缩
    if vol_ratio < 0.50:
        details.append(f"[强] 量缩至{vol_ratio:.0%} — 供应枯竭信号")
        score += 40
    elif vol_ratio < 0.75:
        details.append(f"[中] 量缩至{vol_ratio:.0%}")
        score += 20
    elif vol_ratio < 0.90:
        details.append(f"[弱] 量微缩至{vol_ratio:.0%}")
        score += 8
    
    # 2. 振幅收窄
    if spread_ratio < 0.50:
        details.append(f"[强] 振幅{spread_ratio:.0%} — 波动衰竭")
        score += 25
    elif spread_ratio < 0.75:
        details.append(f"[中] 振幅{spread_ratio:.0%}")
        score += 12
    
    # 3. 收盘位置偏强
    if avg_close_pos > 0.60:
        details.append(f"[强] 收盘偏买方(位置{avg_close_pos:.0%})")
        score += 15
    
    # 4. 急落+低量 = 震仓陷阱
    if vel["type"] == "急落" and vel["volume_level"] == "低":
        details.append(f"[关键] 急落+低量 = 震仓陷阱 — 主力吸筹信号")
        score += 20
    elif vel["type"] == "急落" and vel["volume_level"] == "高":
        details.append(f"[警惕] 急落+高量 = 真实抛压")
        score -= 15
    # 缓落+低量
    if vel["type"] == "缓落" and vel["volume_level"] == "低":
        details.append(f"[确认] 缓落+低量 = 供应彻底枯竭")
        score += 15
    
    # 5. 支撑位位置
    day_range = recent_high - recent_low
    pos = (current_price - recent_low) / max(day_range, 0.01)
    if 0.30 < pos < 0.60:
        details.append(f"[位置] 回踩至日内{pos:.0%}位 — 健康区间")
        score += 10
    
    # ── CVD联动: T+1适配 ──
    cvd_boost = 0
    cvd_note = ""
    if cvd_confirm and cvd_confirm.get("cvd_confirmation") != "none":
        cvd_boost = cvd_confirm.get("boost_to_supply_test", 0)
        cvd_note = cvd_confirm.get("interpretation", "")
        if cvd_boost > 0:
            details.append(f"[CVD联动] {cvd_note}")
            score += cvd_boost
        elif cvd_boost < 0:
            details.append(f"[CVD联动·警惕] {cvd_note}")
            score += cvd_boost  # 负分

    test_passed = score >= 45
    if score >= 70:
        signal_type = "TEST_PASSED"
    elif score >= 45:
        signal_type = "NO_SUPPLY"
    else:
        signal_type = None

    return {
        "test_passed": test_passed, "signal": signal_type, "confidence": score,
        "details": details,
        "velocity": vel,
        "metrics": {"vol_ratio": round(vol_ratio, 2), "spread_ratio": round(spread_ratio, 2),
                     "close_position": round(avg_close_pos, 2), "position_in_range": round(pos, 2)},
        "cvd_boost": cvd_boost, "cvd_note": cvd_note
    }


def quick_check(code, price, high, low):
    r = analyze_supply_test(code, price, high, low)
    sig = r["signal"]
    if sig == "TEST_PASSED":
        return f"✅ 测试通过 (置信度{r['confidence']}) — 卖方真空确认，SOS信号即将触发！"
    elif sig == "NO_SUPPLY":
        return f"🟡 无供应信号 (置信度{r['confidence']}) — 卖盘萎缩中，等待进一步确认"
    elif r["confidence"] >= 30:
        return f"⚠️ 测试进行中 (置信度{r['confidence']}) — 等待缩量确认"
    return f"❌ 未触发 (置信度{r['confidence']}) — 成交量正常"


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("price", type=float)
    p.add_argument("high", type=float)
    p.add_argument("low", type=float)
    p.add_argument("--detailed", action="store_true")
    args = p.parse_args()
    r = analyze_supply_test(args.code, args.price, args.high, args.low)
    print(quick_check(args.code, args.price, args.high, args.low))
    if args.detailed:
        for d in r["details"]: print(f"  • {d}")
        v = r["velocity"]
        m = r["metrics"]
        print(f"  走势: {v['type']}+{v['volume_level']}量  量比:{m['vol_ratio']} 振幅比:{m['spread_ratio']}")
