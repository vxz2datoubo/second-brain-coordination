"""footprint_detector.py — 足迹图(Footprint)微观分析 v2

v2升级: 5分钟→1分钟K线数据源（灵敏度5倍）
A股适配版: 用1分钟K线模拟Footprint概念
(Level 1数据限制，开Level 2后可升级到真实Bid/Ask分笔)

核心功能:
- _read_1min_bars(): 读取通达信1分钟K线(.lc1)
- detect_bar_imbalance(): 单根K线失衡检测
- detect_stacked_imbalances(): 堆叠失衡(连续N根1分K线同向)
- detect_bar_absorption(): K线级吸收检测
- detect_kline_delta_divergence(): K线级Delta背离
- confirm_supply_test(): 微观确认供应测试

联动: supply-test / absorption-detection / delta-cvd / vwap-analyzer
"""

import json, os, struct
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_footprint_state.json")
ROOT = os.path.dirname(os.path.abspath(__file__))


def _load_delta_state():
    cvd_file = os.path.join(ROOT, "_delta_state.json")
    if not os.path.exists(cvd_file): return {}
    with open(cvd_file, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return {}


def _load_state():
    if not os.path.exists(STATE_FILE): return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return {}


def _save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ──────────────────────────────────────────────
#  1分钟K线读取（通达信 .lc1 格式）
# ──────────────────────────────────────────────

def _read_1min_bars(code, limit=240):
    """读取通达信1分钟K线 (32字节/条, 同.lc5格式)"""
    market = "sz" if code.startswith(("0", "3")) else "sh"
    path = rf"F:\tongdaxin\vipdoc\{market}\minline\{market}{code}.lc1"
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        data = f.read()
    n = len(data) // 32
    start = max(0, n - limit)
    bars = []
    for i in range(start, n):
        u = struct.unpack_from("<HHfffffIHH", data, i * 32)
        dw, sec = u[0], u[1]
        op, hi, lo, cl, amt = u[2], u[3], u[4], u[5], u[6]
        y, m, d = (dw // 2048) + 2004, (dw % 2048) // 100, dw % 2048 % 100
        bars.append({
            "date": f"{y:04d}{m:02d}{d:02d}",
            "time": sec,
            "time_str": f"{sec//3600:02d}:{(sec%3600)//60:02d}",
            "open": op, "high": hi, "low": lo, "close": cl,
            "volume": amt / 100.0,  # 手
            "amount": amt,           # 元
        })
    return bars


def _today_1min_bars(code):
    """获取今日1分钟K线"""
    bars = _read_1min_bars(code, 300)
    if not bars: return []
    today = bars[-1]["date"]
    return [b for b in bars if b["date"] == today]


# ──────────────────────────────────────────────
#  K线级Footprint信号（基于1分钟K线）
# ──────────────────────────────────────────────

def detect_bar_imbalance(code):
    """
    最近一根1分钟K线是否出现失衡
    
    简化Footprint: 用1分钟K线的开盘→收盘判断买卖偏置
    (Level 2开通后改为真正的Bid/Ask比率)
    
    Returns:
        {"imbalance": "bullish"/"bearish"/None, "strength": int 1-5, "detail": str}
    """
    bars = _today_1min_bars(code)
    if len(bars) < 2: return {"imbalance": None, "strength": 0, "detail": "数据不足"}

    last = bars[-1]
    price_change = last["close"] - last["open"]
    vol = last["volume"]
    body = abs(price_change) / max(last["close"], 0.01)

    # 用价格波动+成交量判断买卖强弱
    if price_change > 0 and body > 0.003 and vol > 500:
        strength = min(5, int(vol / 500 * body * 1000))
        return {"imbalance": "bullish", "strength": strength,
                "detail": f"买入失衡@{last['time_str']}: +{body:.1%} | {vol:.0f}手"}
    elif price_change < 0 and body > 0.003 and vol > 500:
        strength = min(5, int(vol / 500 * body * 1000))
        return {"imbalance": "bearish", "strength": strength,
                "detail": f"卖出失衡@{last['time_str']}: -{body:.1%} | {vol:.0f}手"}

    return {"imbalance": None, "strength": 0, "detail": f"均衡@{last['time_str']}"}


def detect_stacked_imbalances(code):
    """
    堆叠失衡检测 — 连续3根以上1分K线同方向失衡
    
    1分钟版本:
    - 阈值提高到连续5根 (vs 5分钟的3根) 因为1分钟噪音大
    - 或者连续3根但要求每根的涨跌幅>0.5%
    
    Returns:
        {"stacked": bool, "direction": str/None, "count": int, "avg_strength": float, "detail": str}
    """
    bars = _today_1min_bars(code)
    if len(bars) < 10: return {"stacked": False, "direction": None, "count": 0, "avg_strength": 0, "detail": "数据不足"}

    # 只分析最近20根
    recent = bars[-20:]
    imbalances = []
    for b in recent:
        chg = b["close"] - b["open"]
        body = abs(chg) / max(b["close"], 0.01)
        if chg > 0 and body > 0.003 and b["volume"] > 300:
            imbalances.append("bullish")
        elif chg < 0 and body > 0.003 and b["volume"] > 300:
            imbalances.append("bearish")
        else:
            imbalances.append(None)

    # 找最长连续同向序列
    best_dir = None
    best_count = 0
    cur_dir = None
    cur_count = 0

    for d in imbalances:
        if d is not None and d == cur_dir:
            cur_count += 1
        else:
            if cur_count > best_count:
                best_count = cur_count
                best_dir = cur_dir
            cur_dir = d
            cur_count = 1 if d is not None else 0
    if cur_count > best_count:
        best_count = cur_count
        best_dir = cur_dir

    stacked = best_count >= 5  # 1分钟需5根连续(5分钟跨度)
    # 如果是强失衡(3根+每根>0.5%)也算了
    if not stacked and best_count >= 3:
        # 检查这3根的幅度
        strong = True
        count = 0
        for d in imbalances[-best_count:]:
            if d == best_dir:
                b = recent[-(best_count - count)]
                body = abs(b["close"] - b["open"]) / max(b["close"], 0.01)
                if body < 0.005:
                    strong = False
                    break
            count += 1
        if strong:
            stacked = True

    return {
        "stacked": stacked,
        "direction": best_dir if stacked else None,
        "count": best_count,
        "avg_strength": 0,
        "detail": f"{'⚡堆叠' if stacked else '非堆叠'} {best_dir}×{best_count}根1分K线"
    }


def detect_bar_absorption(code, current_price):
    """
    1分钟K线级吸收检测
    
    条件(1分钟适配):
    - 最近3根1分K线价格波动极小 (<0.2%)
    - 但成交量相对较大 (>1000手/根)
    - 或者最近5根中有3根满足以上条件
    
    Returns:
        {"absorption": "bid"/"ask"/None, "confidence": int, "detail": str}
    """
    bars = _today_1min_bars(code)
    if len(bars) < 5: return {"absorption": None, "confidence": 0, "detail": "数据不足"}

    recent = bars[-5:]
    stagnant_count = 0
    bid_like = 0
    ask_like = 0

    for b in recent:
        body = abs(b["close"] - b["open"]) / max(b["close"], 0.01)
        if body < 0.002 and b["volume"] > 1000:
            stagnant_count += 1
            if b["close"] > b["open"]:
                ask_like += 1  # 微涨+大成交量 → 买盘被吸收
            else:
                bid_like += 1  # 微跌+大成交量 → 卖盘被吸收

    if stagnant_count >= 3:
        if bid_like > ask_like:
            return {"absorption": "bid", "confidence": min(stagnant_count * 20, 100),
                    "detail": f"1分K线级Bid吸收: {stagnant_count}/5根停滞(微跌+大成交量), 主力接货"}
        else:
            return {"absorption": "ask", "confidence": min(stagnant_count * 20, 100),
                    "detail": f"1分K线级Ask吸收: {stagnant_count}/5根停滞(微涨+大成交量), 主力派发"}

    return {"absorption": None, "confidence": 0, "detail": "无K线级吸收"}


def detect_kline_delta_divergence(code, current_price):
    """
    1分钟K线级Delta背离
    
    从delta_cvd状态读取Delta，结合1分K线价格判断
    """
    state = _load_delta_state()
    key = f"d_{code}"
    if key not in state: return {"divergence": None, "detail": "无数据"}

    h = state[key].get("history", [])
    if len(h) < 2: return {"divergence": None, "detail": "数据不足"}

    last2 = h[-2:]
    price_change = last2[-1]["p"] - last2[-2]["p"]
    delta = last2[-1]["d"]

    if price_change > 0.05 and delta < -500:
        return {"divergence": "bearish",
                "detail": f"K线级看跌背离: +{price_change:.2f}但Delta{delta:,}(净卖)→虚假上涨"}
    elif price_change < -0.05 and delta > 500:
        return {"divergence": "bullish",
                "detail": f"K线级看涨背离: {price_change:.2f}但Delta{delta:+,}(净买)→虚假下跌"}

    return {"divergence": None, "detail": "无K线级Delta背离"}


# ──────────────────────────────────────────────
#  联动函数
# ──────────────────────────────────────────────

def confirm_supply_test(code, current_price):
    """
    用Footprint微观信号确认供应测试
    
    1分钟版本: 堆叠阈值提高到5根, 吸收敏感度也调整
    """
    stacked = detect_stacked_imbalances(code)
    absorption = detect_bar_absorption(code, current_price)
    divergence = detect_kline_delta_divergence(code, current_price)

    boost = 0
    confirmations = []

    if stacked["stacked"] and stacked["direction"] == "bullish":
        boost += 5
        confirmations.append(f"1分K线堆叠买入失衡×{stacked['count']}: 机构主动建仓")
    elif stacked["stacked"] and stacked["direction"] == "bearish":
        boost -= 3
        confirmations.append(f"1分K线堆叠卖出失衡×{stacked['count']}: 机构主动派发")

    if absorption["absorption"] == "bid":
        boost += 3
        confirmations.append(f"1分K线级Bid吸收: {absorption['detail'][:40]}")
    elif absorption["absorption"] == "ask":
        boost -= 2
        confirmations.append(f"1分K线级Ask吸收: {absorption['detail'][:40]}")

    if divergence["divergence"] == "bullish":
        boost += 2
        confirmations.append("1分K线级看涨背离")

    return {
        "confirmed": boost > 0,
        "boost": boost,
        "signal": " | ".join(confirmations) if confirmations else "无微观确认信号",
        "stacked": stacked,
        "absorption": absorption,
        "divergence": divergence
    }


def score_for_quad_lens(code):
    """为quad_lens提供Footprint微观确认评分"""
    stacked = detect_stacked_imbalances(code)
    imb = detect_bar_imbalance(code)

    result = {"boost_supply_test": 0, "boost_absorption": 0, "boost_breakout": 0,
              "signals": [], "detail": ""}

    if stacked["stacked"]:
        if stacked["direction"] == "bullish":
            result["boost_supply_test"] = 5
            result["boost_breakout"] = 3
            result["signals"].append(f"1分堆叠买入失衡×{stacked['count']}")
        elif stacked["direction"] == "bearish":
            result["boost_supply_test"] = -3
            result["signals"].append(f"1分堆叠卖出失衡×{stacked['count']}")

    if imb["imbalance"] == "bullish":
        result["boost_absorption"] = 2
        result["signals"].append(f"买入失衡(S{imb['strength']})")
    elif imb["imbalance"] == "bearish":
        result["signals"].append(f"卖出失衡(S{imb['strength']})")

    result["detail"] = " | ".join(result["signals"]) if result["signals"] else "1分K线无Footprint信号"
    return result


def summary(code):
    """一句话Footprint摘要"""
    stacked = detect_stacked_imbalances(code)
    if stacked["stacked"]:
        return f"⚡ 1分堆叠失衡({stacked['direction']}×{stacked['count']})"
    imb = detect_bar_imbalance(code)
    if imb["imbalance"]:
        return f"📊 1分{imb['imbalance']}失衡"
    return "1分均衡"


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("price", type=float, nargs="?")
    args = p.parse_args()

    print(f"\n{'='*50}")
    print(f"  🔬 Footprint 1分钟微观分析 — {args.code}")
    print(f"{'='*50}")

    bars = _today_1min_bars(args.code)
    print(f"  今日1分K线: {len(bars)}根")
    if bars:
        print(f"  时间范围: {bars[0]['date']} {bars[0]['time_str']} ~ {bars[-1]['time_str']}")

    imb = detect_bar_imbalance(args.code)
    print(f"  失衡: {imb['detail']}")

    stk = detect_stacked_imbalances(args.code)
    print(f"  堆叠: {stk['detail']}")

    if args.price:
        ab = detect_bar_absorption(args.code, args.price)
        print(f"  吸收: {ab['detail']}")

        div = detect_kline_delta_divergence(args.code, args.price)
        print(f"  背离: {div['detail']}")

        cf = confirm_supply_test(args.code, args.price)
        print(f"  供应测试确认: {cf['signal']} (加分{cf['boost']:+d})")

    print()
