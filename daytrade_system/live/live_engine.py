# -*- coding: utf-8 -*-
"""
自进化交易引擎 v2 — 本地TDX文件 + MCP双数据源

主数据源：通达信本地文件（F:\tongdaxin\vipdoc\sz\）
- 日K：lday/sz{code}.day
- 5分K：fzline/sz{code}.lc5

备数据源：TDX MCP HTTP API（盘中实时数据）
- 通过本地代理 http://127.0.0.1:8505/mcp
- 或直接调用云端 https://txmcp.tdx.com.cn:3001/txmcp
"""

import argparse
import json
import math
import os
import struct
import sys
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORK_DIR)

from engine.indicators import (
    KBar, calc_ma, calc_macd, calc_atr, calc_rsi,
    find_support_resistance, calc_intraday_profile, calc_money_flow,
    calc_volume_ratio, detect_divergence, get_expected_range,
    calc_vwap_bands, calc_vwap_position_signal, get_rsi_signal,
    analyze_order_book, calc_cumulative_delta
)
from live.slot_manager import SlotManager, SlotState
from live.risk_controller import get_risk_controller
from live.trade_logger import get_logger, TradeRecord
from live.regime_clf import classify_regime, Regime

# ============================================================
# 全局配置
# ============================================================
STOCKS = {
    "300418": {"name": "昆仑万维", "priority": 1, "alloc_pct": 0.6},
    "300058": {"name": "蓝色光标", "priority": 2, "alloc_pct": 0.4},
}
STOCK_CODES = list(STOCKS.keys())

TDX_BASE = r"F:\tongdaxin\vipdoc\sz"

PER_STOCK_AMOUNT = 5000
MAX_DAILY_SLOTS_PER_STOCK = 3

TIME_WINDOWS = [
    ("T1", "09:30", "09:50"),
    ("T2", "09:50", "10:30"),
    ("T3", "10:30", "11:00"),
    ("T4", "11:00", "11:30"),
    ("T5", "13:00", "13:30"),
    ("T6", "13:30", "14:00"),
    ("T7", "14:00", "14:30"),
    ("T8", "14:30", "15:00"),
]

DEFAULT_WEIGHTS = {
    "F1_VWAP": 0.25,
    "F2_RSI": 0.20,
    "F3_VOL_PROFILE": 0.20,
    "F4_MOMENTUM": 0.15,
    "F5_DELTA": 0.10,
    "F6_GAP": 0.10,
}


# ============================================================
# TDX 本地文件数据加载
# ============================================================
def _unpack_date(w: int) -> str:
    year = (w // 2048) + 2004
    md = w % 2048
    month = md // 100
    day = md % 100
    return f"{year:04d}{month:02d}{day:02d}"


def load_daily_bars(code: str, count: int = 120) -> List[KBar]:
    """从本地TXT文件加载日K线"""
    filepath = os.path.join(TDX_BASE, "lday", f"sz{code}.day")
    if not os.path.exists(filepath):
        return []

    with open(filepath, "rb") as f:
        data = f.read()

    bars = []
    for i in range(0, len(data), 32):
        if i + 32 > len(data):
            break
        rec = struct.unpack_from("<IIIIIfII", data, i)
        if rec[0] < 20000000:
            continue
        bars.append(KBar(
            date=str(rec[0]),
            time_sec=0,
            time_str="",
            open=rec[1] / 100.0,
            high=rec[2] / 100.0,
            low=rec[3] / 100.0,
            close=rec[4] / 100.0,
            amount=rec[5],
            volume=rec[6],
        ))

    return bars[-count:] if len(bars) > count else bars


def load_min5_bars(code: str, days: int = 5) -> Tuple[List[KBar], List[KBar]]:
    """
    从本地LC5文件加载5分钟K线
    Returns: (all_bars, today_bars)
    """
    filepath = os.path.join(TDX_BASE, "fzline", f"sz{code}.lc5")
    if not os.path.exists(filepath):
        return [], []

    with open(filepath, "rb") as f:
        data = f.read()

    bars = []
    rec_size = 32
    total = len(data) // rec_size

    for i in range(total):
        off = i * rec_size
        rec = struct.unpack_from("<HHfffffIHH", data, off)
        dw, minute = rec[0], rec[1]
        date_str = _unpack_date(dw)
        if date_str.startswith("1970") or rec[2] == 0:
            continue
        h, m = divmod(minute, 60)
        bars.append(KBar(
            date=date_str,
            time_sec=minute * 60,
            time_str=f"{h:02d}:{m:02d}",
            open=rec[2],
            high=rec[3],
            low=rec[4],
            close=rec[5],
            amount=rec[6],
            volume=rec[7],
        ))

    # 按日期过滤
    today = date.today().strftime("%Y%m%d")
    today_bars = [b for b in bars if b.date == today]
    recent_dates = sorted(set(b.date for b in bars))[-days:] if bars else []
    recent_bars = [b for b in bars if b.date in recent_dates]

    return recent_bars, today_bars


def build_quote_from_bars(code: str, daily_bars: List[KBar],
                            today_min5: List[KBar] = None) -> Dict:
    """从K线数据构建行情快照"""
    if not daily_bars:
        return {}

    today = date.today().strftime("%Y%m%d")
    today_bar = None
    for b in reversed(daily_bars):
        if b.date == today:
            today_bar = b
            break

    last_bar = daily_bars[-1]
    prev_bar = daily_bars[-2] if len(daily_bars) >= 2 else last_bar

    if today_min5 and today_min5[-1]:
        now_price = today_min5[-1].close
        day_open = today_min5[0].open
        day_high = max(b.high for b in today_min5)
        day_low = min(b.low for b in today_min5)
        day_vol = sum(b.volume for b in today_min5)
        day_amount = sum(b.amount for b in today_min5)
    elif today_bar:
        now_price = today_bar.close
        day_open = today_bar.open
        day_high = today_bar.high
        day_low = today_bar.low
        day_vol = today_bar.volume
        day_amount = today_bar.amount
    else:
        now_price = last_bar.close
        day_open = last_bar.open
        day_high = last_bar.high
        day_low = last_bar.low
        day_vol = last_bar.volume
        day_amount = last_bar.amount

    pre_close = prev_bar.close
    chg_pct = (now_price / pre_close - 1) * 100 if pre_close else 0

    return {
        "code": code,
        "name": STOCKS.get(code, {}).get("name", code),
        "now": now_price,
        "open": day_open,
        "high": day_high,
        "low": day_low,
        "pre_close": pre_close,
        "chg_pct": round(chg_pct, 2),
        "volume": day_vol,
        "amount": day_amount,
        "hsl": 0.0,  # 需要额外数据
        "ltgb": 0.0,
        "data_source": "local",
    }


# ============================================================
# 6因子信号计算
# ============================================================
def calc_six_factors(
    quote: Dict,
    daily_bars: List[KBar],
    min5_bars: List[KBar],
) -> Dict:
    """计算6个独立信号因子，返回总分和置信度"""
    if not daily_bars or not min5_bars:
        return {"total_score": 0, "confidence": "D", "factors": {}, "reasons": []}

    closes = [b.close for b in daily_bars]
    last_close = quote.get("now", closes[-1] if closes else 0)
    vwap_bands = calc_vwap_bands(min5_bars)

    factors = {}
    reasons = []

    # F1: VWAP极端偏离 (25%)
    f1_score = 0
    pos = vwap_bands.get("position", "")
    slope = vwap_bands.get("vwap_slope", "flat")
    if "极" in pos:
        f1_score = 30
        reasons.append(f"VWAP极端{pos}")
        if slope == "falling":
            f1_score += 10
            reasons.append("VWAP下行+极偏=回落概率大")
    elif "偏" in pos or "强" in pos:
        f1_score = 15
        reasons.append(f"VWAP{pos}")
    factors["F1_VWAP"] = {"score": f1_score, "weight": 0.25}

    # F2: RSI均值回归 (20%)
    f2_score = 0
    if len(closes) >= 7:
        rsi_vals = calc_rsi(closes, 6)
        rsi_now = rsi_vals[-1]
        if rsi_now:
            rsi_sig = get_rsi_signal(rsi_now)
            f2_score = rsi_sig["score"]
            reasons.append(f"RSI={rsi_now}({rsi_sig['zone']})")
    factors["F2_RSI"] = {"score": f2_score, "weight": 0.20}

    # F3: 量价分布压力 (20%)
    f3_score = 0
    profile = calc_intraday_profile(min5_bars, last_close)
    dev = profile.get("avg_deviation", 0)
    if dev > 1.5:
        f3_score = 25
        reasons.append(f"价格>{dev}%高于VWAP=高量压力区")
    elif dev < -1.5:
        f3_score = 25
        reasons.append(f"价格<{abs(dev)}%低于VWAP=低量支撑区")
    elif abs(dev) > 0.5:
        f3_score = 10
        reasons.append(f"价格偏离VWAP {dev}%")
    factors["F3_VOL_PROFILE"] = {"score": f3_score, "weight": 0.20}

    # F4: 动量衰竭 (15%)
    f4_score = 0
    if len(min5_bars) >= 4:
        recent_closes = [b.close for b in min5_bars[-4:]]
        if all(recent_closes[i] > recent_closes[i + 1] for i in range(3)):
            f4_score = 25
            reasons.append("动量衰竭：4连阴")
        elif (recent_closes[0] > recent_closes[1] > recent_closes[2]
              and recent_closes[2] < recent_closes[3]):
            f4_score = 20
            reasons.append("顶部结构：冲高后回落")

    if min5_bars:
        day_high = max(b.high for b in min5_bars)
        pullback = (day_high - last_close) / day_high * 100 if day_high > 0 else 0
        if pullback > 30:
            f4_score = max(f4_score, 15)
            reasons.append(f"从高点回撤 {pullback:.1f}%")
    factors["F4_MOMENTUM"] = {"score": f4_score, "weight": 0.15}

    # F5: 成交量Delta (10%)
    f5_score = 0
    if len(min5_bars) >= 3:
        cdv = calc_cumulative_delta(min5_bars)
        if len(cdv) >= 3:
            if all(d < 0 for d in cdv[-3:]):
                f5_score = 20
                reasons.append("连续3根5分K主动卖压主导")
            elif cdv[-1] < cdv[-2] < 0:
                f5_score = 15
                reasons.append("卖压Delta扩大")
    factors["F5_DELTA"] = {"score": f5_score, "weight": 0.10}

    # F6: 跳空缺口 (10%)
    f6_score = 0
    pre_close = quote.get("pre_close", prev_bar.close if daily_bars else last_close)
    open_p = quote.get("open", last_close)
    if pre_close and pre_close > 0:
        gap_pct = (open_p - pre_close) / pre_close * 100
        if gap_pct > 1.0:
            f6_score = 20
            reasons.append(f"高开{gap_pct:.1f}%=假突破概率高")
        elif gap_pct < -1.0:
            f6_score = 20
            reasons.append(f"低开{abs(gap_pct):.1f}%=恐慌见底概率高")
    factors["F6_GAP"] = {"score": f6_score, "weight": 0.10}

    # 加权总分
    total_score = sum(f["score"] * f["weight"] for f in factors.values())

    # 置信度
    if total_score >= 90:
        confidence = "A++"
    elif total_score >= 75:
        confidence = "A"
    elif total_score >= 60:
        confidence = "B"
    elif total_score >= 45:
        confidence = "C"
    else:
        confidence = "D"

    return {
        "total_score": round(total_score, 1),
        "confidence": confidence,
        "factors": factors,
        "reasons": reasons[:6],
        "vwap": vwap_bands.get("vwap"),
        "vwap_position": vwap_bands.get("position"),
        "vwap_slope": vwap_bands.get("vwap_slope"),
    }


# ============================================================
# 正T信号
# ============================================================
def calc_long_t_signal(quote: Dict, daily_bars: List[KBar],
                       min5_bars: List[KBar]) -> Dict:
    """正T信号（先低买，等反弹卖）"""
    if not daily_bars or not min5_bars:
        return {"score": 0, "confidence": "D"}

    closes = [b.close for b in daily_bars]
    last_close = quote.get("now", closes[-1] if closes else 0)
    vwap_bands = calc_vwap_bands(min5_bars)
    pos = vwap_bands.get("position", "")
    score = 0

    if "极" in pos and ("低" in pos or "弱" in pos):
        score = 30
    elif "偏" in pos and ("低" in pos or "弱" in pos):
        score = 15

    if len(closes) >= 7:
        rsi_vals = calc_rsi(closes, 6)
        rsi_now = rsi_vals[-1]
        if rsi_now and rsi_now < 30:
            score = max(score, 20)

    confidence = "A" if score >= 25 else "B" if score >= 15 else "D"
    return {"score": score, "confidence": confidence}


# ============================================================
# 主分析函数
# ============================================================
def analyze_stock(stock_code: str, use_today_min5: bool = True) -> Dict:
    """
    对单只股票进行全面分析
    优先使用本地TXT数据（盘中实时更新）
    """
    # 加载数据
    daily_bars = load_daily_bars(stock_code, 120)
    if not daily_bars:
        return {"error": f"无法加载{stock_code}日K数据", "stock": stock_code}

    recent_min5, today_min5 = load_min5_bars(stock_code, days=5)
    if not recent_min5:
        return {"error": f"无法加载{stock_code}5分K数据", "stock": stock_code}

    # 构建行情
    quote = build_quote_from_bars(stock_code, daily_bars, today_min5 if use_today_min5 else None)

    # 市场状态
    regime_info = classify_regime(recent_min5, daily_bars, quote)

    # 6因子
    six = calc_six_factors(quote, daily_bars, recent_min5)

    # 正T
    long_t = calc_long_t_signal(quote, daily_bars, recent_min5)

    # 支撑阻力
    now_p = quote.get("now", daily_bars[-1].close)
    sr = find_support_resistance(daily_bars, now_p)
    range_info = get_expected_range(quote, daily_bars)

    # 当前时间窗口
    now_str = datetime.now().strftime("%H:%M")
    current_window = "T0"
    for label, start, end in TIME_WINDOWS:
        if start <= now_str < end:
            current_window = label
            break

    # 槽位状态
    slot_mgr = SlotManager()
    slot_status = slot_mgr.get_status_summary(stock_code)

    # 风控
    risk = get_risk_controller()
    risk_check = risk.can_trade(stock_code)

    # 日内涨跌
    closes = [b.close for b in daily_bars]
    prev_close = daily_bars[-2].close if len(daily_bars) >= 2 else closes[-1]
    chg_pct = (now_p / prev_close - 1) * 100 if prev_close else 0

    # 均线
    ma5_vals = calc_ma(closes, 5)
    ma20_vals = calc_ma(closes, 20)
    rsi_vals = calc_rsi(closes, 6)
    atr_vals = calc_atr([b.high for b in daily_bars], [b.low for b in daily_bars], closes, 14)

    return {
        "stock": stock_code,
        "name": quote.get("name", STOCKS[stock_code]["name"]),
        "priority": STOCKS[stock_code]["priority"],
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "time_window": current_window,
        "quote": quote,
        "chg_pct": round(chg_pct, 2),
        "price": round(now_p, 2),
        "open": round(quote.get("open", now_p), 2),
        "high": round(quote.get("high", now_p), 2),
        "low": round(quote.get("low", now_p), 2),
        "ma5": round(ma5_vals[-1], 2) if ma5_vals[-1] else None,
        "ma20": round(ma20_vals[-1], 2) if ma20_vals[-1] else None,
        "rsi6": round(rsi_vals[-1], 1) if rsi_vals[-1] else None,
        "atr14": round(atr_vals[-1], 2) if atr_vals[-1] else None,
        "regime": regime_info,
        "signal": six,
        "long_t": long_t,
        "support_resistance": {
            "s1": sr.s1, "s2": sr.s2, "s3": sr.s3,
            "r1": sr.r1, "r2": sr.r2, "r3": sr.r3,
        },
        "range_info": range_info,
        "slot_status": slot_status,
        "risk_check": risk_check,
    }


def build_executable_signal(analysis: Dict) -> Dict:
    """将分析结果转化为可执行信号"""
    if "error" in analysis:
        return {"action": f"数据错误: {analysis['error']}", "can_trade": False}

    signal = analysis.get("signal", {})
    regime = analysis.get("regime", {})
    quote = analysis.get("quote", {})
    sr = analysis.get("support_resistance", {})
    slot = analysis.get("slot_status", {})
    risk = analysis.get("risk_check", {})

    total_score = signal.get("total_score", 0)
    confidence = signal.get("confidence", "D")
    now = analysis.get("price", 0)

    # 昆仑优先级
    priority = analysis.get("priority", 3)
    priority_label = "昆仑" if priority == 1 else "蓝色"

    action = "无操作"
    direction = "NONE"
    entry_price = 0
    target_price = 0
    stop_loss = 0
    reason = ""

    if confidence in ("A++", "A", "B"):
        direction = "REVERSE_T"
        entry_price = round(now, 2)
        vwap = signal.get("vwap", now)
        target_price = round(min(vwap, sr.get("s1", now * 0.995)), 2)
        stop_loss = round(now * 1.01, 2)
        reason = " | ".join(signal.get("reasons", [])[:3])

        if confidence == "A++":
            action = f"[{priority_label} A++] 强烈建议倒T卖出 @{entry_price}，接回目标 {target_price}"
        elif confidence == "A":
            action = f"[{priority_label} A] 建议倒T卖出 @{entry_price}，接回目标 {target_price}"
        else:
            action = f"[{priority_label} B] 可考虑倒T卖出 @{entry_price}，接回目标 {target_price}"
    elif signal.get("long_t", {}).get("confidence") in ("A", "B"):
        direction = "LONG_T"
        entry_price = round(now, 2)
        target_price = round(min(sr.get("r1", now * 1.02), vwap if signal.get("vwap") else now * 1.02), 2)
        stop_loss = round(now * 0.98, 2)
        reason = "正T反弹信号"
        action = f"[{priority_label} 正T] 可考虑买入 @{entry_price}，目标 {target_price}"

    can_trade = (
        risk.get("allowed", False)
        and risk.get("max_slots", 0) > 0
        and slot.get("can_open", False)
    )

    risk_block = risk.get("reasons", "") if not risk.get("allowed") else ""

    return {
        "action": action,
        "direction": direction,
        "entry_price": entry_price,
        "target_price": target_price,
        "stop_loss": stop_loss,
        "confidence": confidence,
        "signal_score": total_score,
        "priority": priority,
        "reason": reason,
        "regime": regime.get("regime", "unknown"),
        "regime_advice": regime.get("t_advice", ""),
        "can_trade": can_trade,
        "risk_block": risk_block,
        "max_slots": risk.get("max_slots", 0),
        "remaining_slots": slot.get("remaining_slots", 0),
        "today_profit": slot.get("total_profit", 0),
    }


# ============================================================
# 输出格式化报告
# ============================================================
def format_signal_report(analysis: Dict) -> str:
    """格式化单只股票的信号报告"""
    sig = build_executable_signal(analysis)

    lines = []
    lines.append(f"【{analysis['name']}({analysis['stock']})】")
    lines.append(f"  时间: {analysis['time']}  窗口: {analysis['time_window']}")

    quote = analysis.get("quote", {})
    lines.append(f"  价格: {analysis['price']} ({analysis['chg_pct']:+.2f}%) "
                 f"开盘{analysis['open']} 最高{analysis['high']} 最低{analysis['low']}")

    ma_info = []
    if analysis.get("ma5"):
        ma_info.append(f"MA5={analysis['ma5']}")
    if analysis.get("ma20"):
        ma_info.append(f"MA20={analysis['ma20']}")
    if analysis.get("rsi6"):
        ma_info.append(f"RSI6={analysis['rsi6']}")
    if analysis.get("atr14"):
        ma_info.append(f"ATR14={analysis['atr14']}({analysis['atr14']/analysis['price']*100:.1f}%)")
    if ma_info:
        lines.append(f"  技术: {' | '.join(ma_info)}")

    regime = analysis.get("regime", {})
    lines.append(f"  市场状态: {regime.get('regime', '?')} | "
                  f"{regime.get('t_advice', '')[:50]}")

    signal = analysis.get("signal", {})
    lines.append(f"  信号: {sig['confidence']}({signal.get('total_score', 0)}/100) "
                 f"{signal.get('vwap_position', '')} "
                 f"{signal.get('vwap_slope', '')}")
    lines.append(f"  理由: {' | '.join(signal.get('reasons', [])[:4])}")

    sr = analysis.get("support_resistance", {})
    lines.append(f"  支撑: S1={sr.get('s1')} S2={sr.get('s2')} | "
                 f"压力: R1={sr.get('r1')} R2={sr.get('r2')}")

    lines.append("")
    lines.append(f"  ★ {sig['action']}")
    if sig.get("risk_block"):
        lines.append(f"  ⚠️ 风控限制: {sig['risk_block']}")
    else:
        lines.append(f"  可交易: {'是' if sig['can_trade'] else '否'} "
                     f"剩余槽位:{sig['remaining_slots']}/3 "
                     f"今日T仓利润:{sig['today_profit']}元")

    return "\n".join(lines)


# ============================================================
# 单次分析模式
# ============================================================
def single_analysis():
    """单次分析并输出详细报告"""
    print(f"\n{'=' * 60}")
    print(f"自进化交易引擎 · 信号分析")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"标的: 昆仑万维(300418) / 蓝色光标(300058)")
    print(f"{'=' * 60}\n")

    results = {}
    for code in STOCK_CODES:
        print(f"\n{'─' * 50}")
        try:
            analysis = analyze_stock(code)
            if "error" in analysis:
                print(f"  错误: {analysis['error']}")
            else:
                report = format_signal_report(analysis)
                print(report)
                results[code] = analysis
        except Exception as e:
            print(f"  分析异常: {e}")
            import traceback
            traceback.print_exc()

    # 汇总
    if results:
        print(f"\n{'=' * 60}")
        print("【操作汇总】")

        sortable = []
        for code, a in results.items():
            sig = build_executable_signal(a)
            if sig["confidence"] in ("A++", "A", "B"):
                sortable.append((sig["priority"], -sig["signal_score"], code, a, sig))

        sortable.sort()
        for priority, _, code, a, sig in sortable:
            print(f"  {sig['action']}")

        if not sortable:
            print("  今日暂无A级以上信号，观望为主")

    print(f"\n{'=' * 60}\n")


# ============================================================
# 监控模式
# ============================================================
def monitor_loop(interval_seconds: int = 60):
    """持续监控模式"""
    print(f"\n{'=' * 60}")
    print(f"自进化交易引擎 · 实时监控")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"标的: 昆仑万维 / 蓝色光标")
    print(f"监控间隔: {interval_seconds}秒")
    print(f"{'=' * 60}\n")

    while True:
        now_str = datetime.now().strftime("%H:%M")

        if now_str < "09:15":
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 盘前...")
        elif "09:15" <= now_str < "09:30":
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 集合竞价...")
        elif now_str >= "15:05":
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 收盘")
            break
        else:
            print(f"\n{'─' * 50}")
            print(f"【{datetime.now().strftime('%H:%M:%S')}】扫描报告")

            for code in STOCK_CODES:
                try:
                    analysis = analyze_stock(code)
                    if "error" not in analysis:
                        print(format_signal_report(analysis))
                except Exception as e:
                    print(f"  {code}: {e}")

        time.sleep(interval_seconds)


# ============================================================
# CLI入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="自进化交易引擎 v2")
    parser.add_argument("--mode", choices=["monitor", "single"], default="single")
    parser.add_argument("--stock", default=None)
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()

    if args.stock:
        global STOCK_CODES
        STOCK_CODES = [args.stock]

    if args.mode == "monitor":
        monitor_loop(args.interval)
    else:
        single_analysis()


if __name__ == "__main__":
    main()
