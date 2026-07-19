"""
做T核心指标计算引擎
支持：布林带、均线、ATR、支撑压力位、VWAP+偏差带、量价分析、MACD、RSI、
     Keltner通道、订单簿深度、累计成交量delta
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import math


@dataclass
class KBar:
    """单根K线"""
    date: str
    time_sec: int  # 秒数（日内）
    open: float
    high: float
    low: float
    close: float
    volume: float      # 成交量（股）
    amount: float      # 成交额（元）


@dataclass
class QuoteSnapshot:
    """实时行情快照"""
    code: str
    name: str
    date: str
    time: str
    open: float
    high: float
    low: float
    pre_close: float
    now: float
    volume: float
    amount: float
    avg_price: float   # 均价
    hsl: float         # 换手率
    inside: float      # 内盘
    outside: float     # 外盘
    zt_price: float    # 涨停价
    dt_price: float    # 跌停价
    ltgb: float        # 流通股本（万股）
    zsz: float         # 总市值
    inflow: float      # 主力净流入
    wtb: float         # 小单比
    bsp: List[Dict]    # 买卖五档


@dataclass
class SupportResistance:
    """支撑压力位"""
    s3: float  # 强支撑
    s2: float
    s1: float
    pivot: float  # 中枢
    r1: float
    r2: float
    r3: float  # 强压力


def calc_ma(values: List[float], period: int) -> List[float]:
    """简单移动均线"""
    if len(values) < period:
        return [None] * len(values)
    result = [None] * (period - 1)
    for i in range(period - 1, len(values)):
        result.append(sum(values[i - period + 1:i + 1]) / period)
    return result


def calc_ema(values: List[float], period: int) -> List[float]:
    """指数移动均线"""
    if len(values) < period:
        return [None] * len(values)

    # 过滤掉开头的None
    valid_start = 0
    while valid_start < len(values) and values[valid_start] is None:
        valid_start += 1

    result = [None] * len(values)
    if len(values) - valid_start < period:
        return result

    multiplier = 2 / (period + 1)
    # 首个EMA用SMA（只用非None值）
    first_window = [v for v in values[valid_start:valid_start + period] if v is not None]
    if len(first_window) == 0:
        return result

    ema = sum(first_window) / len(first_window)
    ema_idx = valid_start + period - 1
    result[ema_idx] = ema

    for i in range(ema_idx + 1, len(values)):
        if values[i] is not None:
            if result[i - 1] is not None:
                ema = (values[i] - ema) * multiplier + ema
                result[i] = ema
            else:
                # 前一个是None，重新初始化
                ema = values[i]
                result[i] = ema
    return result


def calc_bollinger(values: List[float], period: int = 20, std_mult: float = 2.0) -> Tuple[List[float], List[float], List[float], List[float]]:
    """
    布林带计算
    Returns: (middle, upper, lower, bandwidth)
    """
    if len(values) < period:
        return [None] * len(values), [None] * len(values), [None] * len(values), [None] * len(values)

    middle = calc_ma(values, period)
    upper, lower, bandwidth = [], [], []

    for i in range(len(values)):
        if middle[i] is None:
            upper.append(None)
            lower.append(None)
            bandwidth.append(None)
            continue
        window = values[i - period + 1:i + 1]
        std = math.sqrt(sum((x - middle[i]) ** 2 for x in window) / period)
        u = middle[i] + std_mult * std
        l = middle[i] - std_mult * std
        upper.append(u)
        lower.append(l)
        bandwidth.append((u - l) / middle[i] * 100 if middle[i] != 0 else 0)

    return middle, upper, lower, bandwidth


def calc_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
    """平均真实波幅 ATR"""
    if len(closes) < 2:
        return [None] * len(closes)

    tr_values = [None]  # 第一个无前收
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        tr_values.append(tr)

    atr = [None] * len(closes)
    if len(tr_values) <= period:
        return atr

    # 首个ATR用简单平均
    first_atr = sum(v for v in tr_values[1:period + 1] if v is not None) / period
    atr[period] = first_atr

    # 后续用EMA平滑
    for i in range(period + 1, len(tr_values)):
        if tr_values[i] is not None and atr[i - 1] is not None:
            atr[i] = (atr[i - 1] * (period - 1) + tr_values[i]) / period

    return atr


def calc_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
    """
    MACD计算
    Returns: (dif, dea, histogram)
    """
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)

    dif = []
    for i in range(len(closes)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            dif.append(ema_fast[i] - ema_slow[i])
        else:
            dif.append(None)

    dea = calc_ema(dif, signal)
    hist = []
    for i in range(len(dif)):
        if dif[i] is not None and dea[i] is not None:
            hist.append((dif[i] - dea[i]) * 2)  # 标准是2倍
        else:
            hist.append(None)

    return dif, dea, hist


def find_support_resistance(daily_bars: List[KBar], current_price: float) -> SupportResistance:
    """
    基于多重方法计算支撑压力位
    1. 布林带上下轨
    2. 近期高低点
    3. 均线位置
    """
    closes = [b.close for b in daily_bars]
    highs = [b.high for b in daily_bars]
    lows = [b.low for b in daily_bars]

    bb_mid, bb_up, bb_low, _ = calc_bollinger(closes, 20, 2.0)

    # 布林带最新值
    bb_u = bb_up[-1] if bb_up[-1] is not None else current_price * 1.1
    bb_l = bb_low[-1] if bb_low[-1] is not None else current_price * 0.9
    bb_m = bb_mid[-1] if bb_mid[-1] is not None else current_price

    # 近期高低点（10日、20日）
    lookback_10_high = max(highs[-10:]) if len(highs) >= 10 else max(highs)
    lookback_10_low = min(lows[-10:]) if len(lows) >= 10 else min(lows)
    lookback_20_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
    lookback_20_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)

    # 均线
    ma5 = calc_ma(closes, 5)[-1] if len(closes) >= 5 else None
    ma10 = calc_ma(closes, 10)[-1] if len(closes) >= 10 else None
    ma20 = calc_ma(closes, 20)[-1] if len(closes) >= 20 else None

    # 综合支撑压力（按重要程度排序）
    # 压力位（从近到远）
    pressure_levels = sorted([v for v in [ma5, ma10, ma20, bb_m, bb_u, lookback_10_high, lookback_20_high] if v is not None and v > current_price])
    # 支撑位（从近到远）
    support_levels = sorted([v for v in [ma5, ma10, ma20, bb_m, bb_l, lookback_10_low, lookback_20_low] if v is not None and v < current_price], reverse=True)

    s1 = support_levels[0] if support_levels else current_price * 0.98
    s2 = support_levels[1] if len(support_levels) > 1 else current_price * 0.96
    s3 = support_levels[2] if len(support_levels) > 2 else current_price * 0.94

    r1 = pressure_levels[0] if pressure_levels else current_price * 1.02
    r2 = pressure_levels[1] if len(pressure_levels) > 1 else current_price * 1.04
    r3 = pressure_levels[2] if len(pressure_levels) > 2 else current_price * 1.06

    pivot = (s1 + r1) / 2

    return SupportResistance(
        s3=round(s3, 2),
        s2=round(s2, 2),
        s1=round(s1, 2),
        pivot=round(pivot, 2),
        r1=round(r1, 2),
        r2=round(r2, 2),
        r3=round(r3, 2)
    )


def calc_daily_vwap(bars_5min: List[KBar]) -> Optional[float]:
    """计算日内VWAP（成交量加权均价）"""
    if not bars_5min:
        return None
    total_amount = sum(b.amount for b in bars_5min)
    total_volume = sum(b.volume for b in bars_5min)
    if total_volume == 0:
        return None
    return total_amount / total_volume


def calc_intraday_profile(bars_5min: List[KBar], current_price: float) -> Dict:
    """
    日内分时特征分析
    Returns: 均价偏离度、量能分布、波形特征
    """
    if not bars_5min:
        return {"avg_deviation": 0, "volume_trend": "unknown", "wave_pattern": "unknown"}

    # VWAP偏离度
    vwap = calc_daily_vwap(bars_5min)
    avg_dev = (current_price / vwap - 1) * 100 if vwap and vwap > 0 else 0

    # 量能分析：前一半时间 vs 后一半时间
    mid = len(bars_5min) // 2
    first_half_vol = sum(b.volume for b in bars_5min[:mid])
    second_half_vol = sum(b.volume for b in bars_5min[mid:])

    if second_half_vol > first_half_vol * 1.2:
        volume_trend = "尾盘放量"
    elif first_half_vol > second_half_vol * 1.2:
        volume_trend = "早盘放量"
    else:
        volume_trend = "量能均衡"

    # 简单波形判断（N型/W型/单边）
    prices = [b.close for b in bars_5min]
    if len(prices) >= 8:
        max_p = max(prices)
        min_p = min(prices)
        range_pct = (max_p - min_p) / prices[0] * 100

        # 找拐点
        turning_points = 0
        for i in range(1, len(prices) - 1):
            if (prices[i] > prices[i - 1] and prices[i] > prices[i + 1]) or \
               (prices[i] < prices[i - 1] and prices[i] < prices[i + 1]):
                turning_points += 1

        if range_pct < 1:
            wave_pattern = "窄幅横盘"
        elif turning_points >= 3:
            wave_pattern = "W型震荡" if prices[-1] > prices[0] else "M型震荡"
        elif prices[-1] > prices[0]:
            wave_pattern = "单边上涨"
        elif prices[-1] < prices[0]:
            wave_pattern = "单边下跌"
        else:
            wave_pattern = "N型震荡"
    else:
        wave_pattern = "数据不足"

    return {
        "avg_deviation": round(avg_dev, 2),
        "vwap": round(vwap, 2) if vwap else None,
        "volume_trend": volume_trend,
        "wave_pattern": wave_pattern
    }


def calc_money_flow(quote: QuoteSnapshot) -> Dict:
    """资金流向分析"""
    total = quote.inside + quote.outside
    if total == 0:
        return {"inside_ratio": 50, "outside_ratio": 50, "direction": "均衡"}

    inside_ratio = quote.inside / total * 100
    outside_ratio = quote.outside / total * 100

    if outside_ratio > 55:
        direction = "主动买入偏多"
    elif inside_ratio > 55:
        direction = "主动卖出偏多"
    else:
        direction = "多空均衡"

    return {
        "inside_ratio": round(inside_ratio, 1),
        "outside_ratio": round(outside_ratio, 1),
        "direction": direction,
        "inflow_amount": quote.inflow  # 主力净流入（万元）
    }


def calc_volume_ratio(daily_bars: List[KBar]) -> float:
    """量比：最近5日均量 vs 今日量"""
    if len(daily_bars) < 6:
        return 1.0
    recent_5_avg_vol = sum(b.volume for b in daily_bars[-6:-1]) / 5
    today_vol = daily_bars[-1].volume
    if recent_5_avg_vol == 0:
        return 1.0
    return today_vol / recent_5_avg_vol


def detect_divergence(price_bars: List[KBar], macd_hist: List[float]) -> str:
    """
    检测MACD背离
    Returns: '顶背离' / '底背离' / '无背离'
    """
    if len(price_bars) < 5 or len(macd_hist) < 5:
        return "无背离"

    # 简化版：最近两个高点/低点对比
    recent_prices = [b.close for b in price_bars[-5:]]
    recent_hist = [h for h in macd_hist[-5:] if h is not None]
    if len(recent_hist) < 3:
        return "无背离"

    # 价格新高但MACD柱下降 = 顶背离
    if recent_prices[-1] > recent_prices[-3] and recent_hist[-1] < recent_hist[-3]:
        return "顶背离"
    # 价格新低但MACD柱上升 = 底背离
    if recent_prices[-1] < recent_prices[-3] and recent_hist[-1] > recent_hist[-3]:
        return "底背离"
    return "无背离"


def get_expected_range(quote: QuoteSnapshot, daily_bars: List[KBar]) -> Dict:
    """
    基于ATR和多维度计算预期波动区间
    """
    closes = [b.close for b in daily_bars]
    highs = [b.high for b in daily_bars]
    lows = [b.low for b in daily_bars]

    atr = calc_atr(highs, lows, closes, 14)
    current_atr = atr[-1] if atr[-1] is not None else quote.now * 0.03

    # 昨日振幅
    yesterday_range_pct = (daily_bars[-1].high - daily_bars[-1].low) / daily_bars[-1].open * 100 if daily_bars else 3.0

    # 平均振幅（5日）
    avg_range_pct = 0
    if len(daily_bars) >= 5:
        ranges = [(b.high - b.low) / b.open * 100 for b in daily_bars[-5:]]
        avg_range_pct = sum(ranges) / len(ranges)

    # 基于ATR的预期波动
    atr_pct = current_atr / quote.now * 100
    expected_range = max(atr_pct, avg_range_pct) * 0.7  # 保守估算

    # 基于前收盘的预期区间
    expected_high = quote.pre_close * (1 + expected_range / 100 / 2)
    expected_low = quote.pre_close * (1 - expected_range / 100 / 2)

    return {
        "atr": round(current_atr, 2),
        "atr_pct": round(atr_pct, 2),
        "avg_range_5d": round(avg_range_pct, 2),
        "expected_range_pct": round(expected_range, 2),
        "expected_high": round(expected_high, 2),
        "expected_low": round(expected_low, 2),
        "yesterday_range_pct": round(yesterday_range_pct, 2)
    }


# ============================================================
#  增强指标: VWAP Bands / RSI / Keltner / 订单簿 / 累计Delta
# ============================================================

def calc_vwap_bands(min5_bars: List[KBar]) -> Dict:
    """
    VWAP + 标准差带
    做T核心: 价格在VWAP上方=强势(考虑做多), 下方=弱势(考虑做空)
           触及2σ带 = 极端偏离 → 大概率回归
    Returns: {vwap, sigma1_upper, sigma1_lower, sigma2_upper, sigma2_lower, position}
    """
    if not min5_bars:
        return {"vwap": 0, "sigma1_upper": 0, "sigma1_lower": 0,
                "sigma2_upper": 0, "sigma2_lower": 0, "position": "neutral"}

    # 逐根计算累积VWAP
    cum_amount = 0.0
    cum_volume = 0.0
    typical_prices = []
    volumes = []

    for bar in min5_bars:
        tp = (bar.high + bar.low + bar.close) / 3.0
        typical_prices.append(tp)
        volumes.append(bar.volume)
        cum_amount += tp * bar.volume
        cum_volume += bar.volume

    if cum_volume == 0:
        return {"vwap": 0, "sigma1_upper": 0, "sigma1_lower": 0,
                "sigma2_upper": 0, "sigma2_lower": 0, "position": "neutral"}

    vwap = cum_amount / cum_volume

    # 计算VWAP标准差（成交量加权）
    variance_sum = 0.0
    for tp, vol in zip(typical_prices, volumes):
        variance_sum += vol * (tp - vwap) ** 2

    if cum_volume == 0:
        std = 0
    else:
        std = math.sqrt(variance_sum / cum_volume)

    # 最后一根收盘价
    last_close = min5_bars[-1].close
    # VWAP斜率（最近5根的VWAP变化方向）
    vwap_slope = _calc_vwap_slope(min5_bars)

    if last_close > vwap + 2 * std:
        position = "极度高估(>2σ)"
    elif last_close > vwap + std:
        position = "偏强(>1σ)"
    elif last_close > vwap:
        position = "略强(>VWAP)"
    elif last_close > vwap - std:
        position = "略弱(<VWAP)"
    elif last_close > vwap - 2 * std:
        position = "偏弱(<1σ)"
    else:
        position = "极度低估(<2σ)"

    return {
        "vwap": round(vwap, 2),
        "sigma1_upper": round(vwap + std, 2),
        "sigma1_lower": round(vwap - std, 2),
        "sigma2_upper": round(vwap + 2 * std, 2),
        "sigma2_lower": round(vwap - 2 * std, 2),
        "std": round(std, 2),
        "position": position,
        "vwap_slope": vwap_slope,
        "price": last_close,
    }


def _calc_vwap_slope(bars: List[KBar]) -> str:
    """VWAP斜率方向（最近5根 vs 前5根）"""
    if len(bars) < 10:
        return "flat"
    recent_5 = bars[-5:]
    prev_5 = bars[-10:-5]

    def vwap_of(b):
        amt = sum(x.close * x.volume for x in b)
        vol = sum(x.volume for x in b)
        return amt / vol if vol > 0 else b[-1].close

    r_vwap = vwap_of(recent_5)
    p_vwap = vwap_of(prev_5)
    if r_vwap > p_vwap * 1.001:
        return "rising"
    elif r_vwap < p_vwap * 0.999:
        return "falling"
    return "flat"


def calc_rsi(closes: List[float], period: int = 6) -> List[float]:
    """
    RSI 相对强弱指标（短周期6适合做T）
    """
    if len(closes) < period + 1:
        return [None] * len(closes)

    rsi = [None] * len(closes)
    gains = []
    losses = []

    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    if len(gains) < period:
        return rsi

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = round(100.0 - (100.0 / (1.0 + rs)), 1)

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = round(100.0 - (100.0 / (1.0 + rs)), 1)

    return rsi


def calc_keltner(highs: List[float], lows: List[float], closes: List[float],
                  ema_period: int = 20, atr_period: int = 10, atr_mult: float = 2.0) -> Dict:
    """
    Keltner通道: EMA中线 + ATR带宽
    比布林带更稳定，适合做T的趋势追踪
    """
    ema = calc_ema(closes, ema_period)
    atr = calc_atr(highs, lows, closes, atr_period)

    upper = []
    lower = []
    for i in range(len(closes)):
        if ema[i] is not None and atr[i] is not None:
            upper.append(ema[i] + atr_mult * atr[i])
            lower.append(ema[i] - atr_mult * atr[i])
        else:
            upper.append(None)
            lower.append(None)

    return {
        "mid": ema,
        "upper": upper,
        "lower": lower,
    }


def analyze_order_book(bsp: List[Dict]) -> Dict:
    """
    盘口深度分析 — 从买卖五档计算
    Returns: 买压/卖压比, 盘口厚度, 失衡方向
    """
    if not bsp:
        return {"buy_pressure": 0, "sell_pressure": 0, "imbalance": 0, "direction": "均衡"}

    total_buy_vol = 0
    total_sell_vol = 0
    weighted_buy = 0.0
    weighted_sell = 0.0

    for i, level in enumerate(bsp):
        buy_vol = float(level.get("BuyV", 0))
        sell_vol = float(level.get("SellV", 0))
        buy_price = float(level.get("BuyP", 0))
        sell_price = float(level.get("SellP", 0))

        total_buy_vol += buy_vol
        total_sell_vol += sell_vol
        weighted_buy += buy_vol * buy_price
        weighted_sell += sell_vol * sell_price

    total = total_buy_vol + total_sell_vol
    if total == 0:
        return {"buy_pressure": 0, "sell_pressure": 0, "imbalance": 0, "direction": "均衡"}

    buy_pct = total_buy_vol / total * 100
    sell_pct = total_sell_vol / total * 100
    imbalance = buy_pct - sell_pct  # 正值=买方更强

    if imbalance > 15:
        direction = "买盘碾压"
    elif imbalance > 5:
        direction = "买盘偏强"
    elif imbalance < -15:
        direction = "卖盘碾压"
    elif imbalance < -5:
        direction = "卖盘偏强"
    else:
        direction = "多空均衡"

    # 盘口厚度（前3档 vs 后2档）
    front_vol = sum(float(bsp[i].get("BuyV", 0)) + float(bsp[i].get("SellV", 0)) for i in range(min(3, len(bsp))))
    if len(bsp) >= 5:
        back_vol = sum(float(bsp[i].get("BuyV", 0)) + float(bsp[i].get("SellV", 0)) for i in range(3, min(5, len(bsp))))
        depth_ratio = front_vol / back_vol if back_vol > 0 else 1
    else:
        depth_ratio = 1
    depth_desc = "厚" if depth_ratio > 1.5 else "薄" if depth_ratio < 0.67 else "正常"

    return {
        "buy_pressure": round(buy_pct, 1),
        "sell_pressure": round(sell_pct, 1),
        "imbalance": round(imbalance, 1),
        "direction": direction,
        "depth": depth_desc,
        "total_buy_shares": int(total_buy_vol),
        "total_sell_shares": int(total_sell_vol),
    }


def calc_cumulative_delta(bars_5min: List[KBar]) -> List[float]:
    """
    累计成交量Delta — 模拟每个5分钟K线的买卖压力
    Close > Open 假设买方主导, Close < Open 假设卖方主导
    按比例分配成交量
    """
    cdv = []
    running = 0.0
    for bar in bars_5min:
        if bar.high == bar.low:
            delta = 0
        else:
            buy_pct = (bar.close - bar.low) / (bar.high - bar.low) if bar.high != bar.low else 0.5
            buy_vol = bar.volume * buy_pct
            sell_vol = bar.volume * (1 - buy_pct)
            delta = buy_vol - sell_vol
        running += delta
        cdv.append(running)
    return cdv


def calc_vwap_position_signal(vwap_bands: Dict, last_close: float, vwap_slope: str) -> Dict:
    """
    VWAP位置信号——做T最重要的辅助指标
    综合VWAP位置 + 斜率给出操作建议
    """
    vwap = vwap_bands["vwap"]
    if vwap == 0:
        return {"signal": "无数据", "score": 0, "suggestion": ""}

    position = vwap_bands["position"]
    score = 0
    suggestion_parts = []

    # VWAP位置打分
    if "极度" in position:
        score += 30  # 极端位置回归概率大
        suggestion_parts.append("极端偏离→回归交易机会大")
    elif "偏强" in position or "偏弱" in position:
        score += 15
        suggestion_parts.append("偏离VWAP→关注回归")

    # VWAP斜率
    if vwap_slope == "rising" and "强" in position:
        score += 10
        suggestion_parts.append("VWAP上行→强势延续，顺势做多")
    elif vwap_slope == "falling" and "弱" in position:
        score += 10
        suggestion_parts.append("VWAP下行→弱势延续，顺势做空")
    elif vwap_slope == "rising" and "弱" in position:
        score += 5
        suggestion_parts.append("价格弱但VWAP上行→可能反转向上")
    elif vwap_slope == "falling" and "强" in position:
        score += 5
        suggestion_parts.append("价格强但VWAP下行→可能反转向下")

    # 生成信号
    if "极度高估" in position and vwap_slope != "rising":
        signal = "强烈倒T信号"
    elif "极度低估" in position and vwap_slope != "falling":
        signal = "强烈正T信号"
    elif "偏强" in position or "略强" in position:
        signal = "偏多观望"
    elif "偏弱" in position or "略弱" in position:
        signal = "偏空观望"
    else:
        signal = "中性"

    return {
        "signal": signal,
        "score": score,
        "suggestion": " | ".join(suggestion_parts) if suggestion_parts else "VWAP附近震荡，等待突破",
        "vwap": vwap,
        "position": position,
        "slope": vwap_slope,
    }


def get_rsi_signal(rsi_value: float) -> Dict:
    """RSI信号解读"""
    if rsi_value is None:
        return {"zone": "无数据", "signal": "观望", "score": 0}

    if rsi_value > 80:
        return {"zone": "严重超买", "signal": "强烈倒T", "score": 25}
    elif rsi_value > 70:
        return {"zone": "超买", "signal": "偏倒T", "score": 15}
    elif rsi_value > 60:
        return {"zone": "偏强", "signal": "偏多", "score": 5}
    elif rsi_value > 40:
        return {"zone": "中性", "signal": "观望", "score": 0}
    elif rsi_value > 30:
        return {"zone": "偏弱", "signal": "偏空", "score": 5}
    elif rsi_value > 20:
        return {"zone": "超卖", "signal": "偏正T", "score": 15}
    else:
        return {"zone": "严重超卖", "signal": "强烈正T", "score": 25}
