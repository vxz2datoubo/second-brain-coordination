"""Finance advisor utilities for Second Brain.

Stdlib-only module for local CSV backtesting and theme heat scoring. It is
designed as a conservative decision aid, not a price prediction engine.
"""
from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PRICE_COLUMNS = {
    "date": ("date", "datetime", "time", "交易日期", "日期"),
    "open": ("open", "开盘", "开盘价"),
    "high": ("high", "最高", "最高价"),
    "low": ("low", "最低", "最低价"),
    "close": ("close", "收盘", "收盘价", "price"),
    "volume": ("volume", "vol", "成交量", "成交额"),
}

DEFAULT_THEMES = {
    "AI算力": ["ai", "算力", "芯片", "gpu", "服务器", "数据中心", "光模块", "液冷"],
    "机器人": ["机器人", "人形机器人", "减速器", "伺服", "传感器"],
    "半导体": ["半导体", "芯片", "晶圆", "封测", "光刻", "存储"],
    "新能源": ["新能源", "光伏", "储能", "锂电", "电池", "逆变器"],
    "低空经济": ["低空", "无人机", "eVTOL", "飞行汽车", "通航"],
    "军工": ["军工", "航空", "航天", "卫星", "导弹", "装备"],
    "消费": ["消费", "白酒", "食品", "旅游", "酒店", "零售"],
    "医药": ["医药", "创新药", "医疗器械", "CXO", "中药"],
    "金融地产": ["银行", "券商", "保险", "地产", "房地产"],
}

LIFECYCLE_KEYWORDS = {
    "launch": ["首板", "启动", "发酵", "异动", "催化", "新题材", "首次", "低位"],
    "confirm": ["放量", "走强", "确认", "突破", "持续走强", "持续放量", "扩散", "加强", "资金流入"],
    "climax": ["高潮", "一致", "连续涨停", "加速", "缩量一字", "全线大涨", "抢筹"],
    "diverge": ["分化", "分歧", "炸板", "冲高回落", "放量滞涨", "兑现", "轮动"],
    "fade": ["退潮", "走弱", "跌停", "亏钱效应", "缩量", "失守"],
}


@dataclass
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


def _norm_header(name: str) -> str:
    return name.strip().lower().replace("\ufeff", "")


def _pick_column(headers: list[str], names: tuple[str, ...]) -> str | None:
    normalized = {_norm_header(h): h for h in headers}
    for name in names:
        key = _norm_header(name)
        if key in normalized:
            return normalized[key]
    return None


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        text = str(value).strip().replace(",", "")
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def load_price_csv(path: str | Path) -> list[Bar]:
    """Load OHLCV bars from a CSV file.

    Required columns: date, close. If open/high/low are absent, close is reused.
    Supports common English and Chinese column names.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        date_col = _pick_column(headers, PRICE_COLUMNS["date"])
        close_col = _pick_column(headers, PRICE_COLUMNS["close"])
        if not date_col or not close_col:
            raise ValueError("CSV must include date and close columns")
        open_col = _pick_column(headers, PRICE_COLUMNS["open"]) or close_col
        high_col = _pick_column(headers, PRICE_COLUMNS["high"]) or close_col
        low_col = _pick_column(headers, PRICE_COLUMNS["low"]) or close_col
        volume_col = _pick_column(headers, PRICE_COLUMNS["volume"])

        bars = []
        for row in reader:
            close = _to_float(row.get(close_col))
            if close <= 0:
                continue
            bars.append(Bar(
                date=str(row.get(date_col, "")).strip(),
                open=_to_float(row.get(open_col), close),
                high=_to_float(row.get(high_col), close),
                low=_to_float(row.get(low_col), close),
                close=close,
                volume=_to_float(row.get(volume_col), 0.0) if volume_col else 0.0,
            ))
    return bars


def sma(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    total = 0.0
    for i, value in enumerate(values):
        total += value
        if i >= window:
            total -= values[i - window]
        out.append(total / window if i >= window - 1 else None)
    return out


def ema(values: list[float], window: int) -> list[float | None]:
    if not values:
        return []
    alpha = 2 / (window + 1)
    out: list[float | None] = []
    current = values[0]
    for i, value in enumerate(values):
        current = value if i == 0 else alpha * value + (1 - alpha) * current
        out.append(current if i >= window - 1 else None)
    return out


def rsi(values: list[float], window: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) <= window:
        return out
    gains, losses = 0.0, 0.0
    for i in range(1, window + 1):
        diff = values[i] - values[i - 1]
        gains += max(diff, 0)
        losses += max(-diff, 0)
    avg_gain = gains / window
    avg_loss = losses / window
    out[window] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(window + 1, len(values)):
        diff = values[i] - values[i - 1]
        avg_gain = (avg_gain * (window - 1) + max(diff, 0)) / window
        avg_loss = (avg_loss * (window - 1) + max(-diff, 0)) / window
        out[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return out


def atr(bars: list[Bar], window: int = 14) -> list[float | None]:
    trs = []
    for i, bar in enumerate(bars):
        prev_close = bars[i - 1].close if i else bar.close
        trs.append(max(bar.high - bar.low, abs(bar.high - prev_close), abs(bar.low - prev_close)))
    return sma(trs, window)


def max_drawdown(equity: list[float]) -> float:
    peak = -math.inf
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1)
    return worst


def _annualized_return(start: float, end: float, days: int) -> float:
    if start <= 0 or end <= 0 or days <= 0:
        return 0.0
    years = max(days / 252, 1 / 252)
    return (end / start) ** (1 / years) - 1


def backtest_sma_cross(
    bars: list[Bar],
    short_window: int = 5,
    long_window: int = 20,
    initial_cash: float = 100000.0,
    fee_rate: float = 0.0003,
) -> dict:
    """Long-only SMA crossover backtest using close-to-close execution."""
    if short_window <= 0 or long_window <= 0 or short_window >= long_window:
        raise ValueError("Require 0 < short_window < long_window")
    if len(bars) < long_window + 2:
        raise ValueError("Not enough bars for selected windows")

    closes = [b.close for b in bars]
    short_ma = sma(closes, short_window)
    long_ma = sma(closes, long_window)
    rsi14 = rsi(closes)
    atr14 = atr(bars)

    cash = initial_cash
    shares = 0.0
    trades = []
    equity_curve = []

    for i, bar in enumerate(bars):
        equity = cash + shares * bar.close
        signal = "hold"
        if i > 0 and short_ma[i] is not None and long_ma[i] is not None:
            prev_short = short_ma[i - 1]
            prev_long = long_ma[i - 1]
            if prev_short is not None and prev_long is not None:
                if shares <= 0 and prev_short <= prev_long and short_ma[i] > long_ma[i]:
                    qty = (cash * (1 - fee_rate)) / bar.close
                    cost = qty * bar.close * (1 + fee_rate)
                    shares = qty
                    cash -= cost
                    signal = "buy"
                    trades.append({"date": bar.date, "side": "buy", "price": bar.close, "equity": equity})
                elif shares > 0 and prev_short >= prev_long and short_ma[i] < long_ma[i]:
                    proceeds = shares * bar.close * (1 - fee_rate)
                    cash += proceeds
                    shares = 0.0
                    signal = "sell"
                    trades.append({"date": bar.date, "side": "sell", "price": bar.close, "equity": equity})
        equity_curve.append(cash + shares * bar.close)

    if shares > 0:
        bar = bars[-1]
        cash += shares * bar.close * (1 - fee_rate)
        shares = 0.0
        equity_curve[-1] = cash
        trades.append({"date": bar.date, "side": "sell", "price": bar.close, "equity": cash, "reason": "final_close"})

    final_equity = equity_curve[-1]
    trade_pairs = []
    open_trade = None
    for t in trades:
        if t["side"] == "buy":
            open_trade = t
        elif t["side"] == "sell" and open_trade:
            ret = t["price"] / open_trade["price"] - 1
            trade_pairs.append({"entry": open_trade, "exit": t, "return": ret})
            open_trade = None

    wins = [p for p in trade_pairs if p["return"] > 0]
    latest = {
        "date": bars[-1].date,
        "close": closes[-1],
        "sma_short": short_ma[-1],
        "sma_long": long_ma[-1],
        "rsi14": rsi14[-1],
        "atr14": atr14[-1],
    }
    suggestion = _suggest_from_metrics(latest, equity_curve, bool(trades and trades[-1]["side"] == "buy"))

    result = {
        "strategy": "sma_cross",
        "params": {"short_window": short_window, "long_window": long_window, "initial_cash": initial_cash, "fee_rate": fee_rate},
        "bars": len(bars),
        "start_date": bars[0].date,
        "end_date": bars[-1].date,
        "initial_cash": initial_cash,
        "final_equity": round(final_equity, 2),
        "total_return": round(final_equity / initial_cash - 1, 4),
        "annualized_return": round(_annualized_return(initial_cash, final_equity, len(bars)), 4),
        "max_drawdown": round(max_drawdown(equity_curve), 4),
        "trades_count": len(trade_pairs),
        "win_rate": round(len(wins) / len(trade_pairs), 4) if trade_pairs else 0.0,
        "latest": latest,
        "suggestion": suggestion,
        "recent_trades": trades[-10:],
        "recent_trade_pairs": trade_pairs[-10:],
        "disclaimer": "历史回测不代表未来收益；结果仅用于验证策略假设和风控。"
    }
    result["risk_adjusted_score"] = score_backtest_result(result)
    return result


def backtest_breakout(
    bars: list[Bar],
    breakout_window: int = 20,
    exit_window: int = 10,
    initial_cash: float = 100000.0,
    fee_rate: float = 0.0003,
) -> dict:
    """Long-only price breakout with trailing low exit."""
    if breakout_window <= 1 or exit_window <= 1:
        raise ValueError("Require breakout_window and exit_window > 1")
    if len(bars) < breakout_window + 2:
        raise ValueError("Not enough bars for breakout strategy")

    cash = initial_cash
    shares = 0.0
    trades = []
    equity_curve = []
    closes = [b.close for b in bars]
    rsi14 = rsi(closes)
    atr14 = atr(bars)

    for i, bar in enumerate(bars):
        if i >= breakout_window:
            prior_high = max(b.high for b in bars[i - breakout_window:i])
            trailing_low = min(b.low for b in bars[max(0, i - exit_window):i])
            equity = cash + shares * bar.close
            if shares <= 0 and bar.close > prior_high:
                qty = (cash * (1 - fee_rate)) / bar.close
                cash -= qty * bar.close * (1 + fee_rate)
                shares = qty
                trades.append({"date": bar.date, "side": "buy", "price": bar.close, "equity": equity, "reason": "breakout"})
            elif shares > 0 and bar.close < trailing_low:
                cash += shares * bar.close * (1 - fee_rate)
                trades.append({"date": bar.date, "side": "sell", "price": bar.close, "equity": cash, "reason": "trailing_low"})
                shares = 0.0
        equity_curve.append(cash + shares * bar.close)

    return _finish_backtest(
        "breakout",
        bars,
        cash,
        shares,
        trades,
        equity_curve,
        initial_cash,
        fee_rate,
        {"breakout_window": breakout_window, "exit_window": exit_window},
        {"rsi14": rsi14[-1], "atr14": atr14[-1]},
    )


def backtest_rsi_reversion(
    bars: list[Bar],
    rsi_window: int = 14,
    buy_below: float = 35,
    sell_above: float = 55,
    initial_cash: float = 100000.0,
    fee_rate: float = 0.0003,
) -> dict:
    """Long-only RSI mean reversion strategy."""
    if buy_below >= sell_above:
        raise ValueError("Require buy_below < sell_above")
    closes = [b.close for b in bars]
    values = rsi(closes, rsi_window)
    atr14 = atr(bars)
    cash = initial_cash
    shares = 0.0
    trades = []
    equity_curve = []

    for i, bar in enumerate(bars):
        value = values[i]
        equity = cash + shares * bar.close
        if value is not None:
            if shares <= 0 and value <= buy_below:
                qty = (cash * (1 - fee_rate)) / bar.close
                cash -= qty * bar.close * (1 + fee_rate)
                shares = qty
                trades.append({"date": bar.date, "side": "buy", "price": bar.close, "equity": equity, "reason": "rsi_oversold"})
            elif shares > 0 and value >= sell_above:
                cash += shares * bar.close * (1 - fee_rate)
                trades.append({"date": bar.date, "side": "sell", "price": bar.close, "equity": cash, "reason": "rsi_exit"})
                shares = 0.0
        equity_curve.append(cash + shares * bar.close)

    return _finish_backtest(
        "rsi_reversion",
        bars,
        cash,
        shares,
        trades,
        equity_curve,
        initial_cash,
        fee_rate,
        {"rsi_window": rsi_window, "buy_below": buy_below, "sell_above": sell_above},
        {"rsi14": values[-1], "atr14": atr14[-1]},
    )


def _finish_backtest(
    strategy: str,
    bars: list[Bar],
    cash: float,
    shares: float,
    trades: list[dict],
    equity_curve: list[float],
    initial_cash: float,
    fee_rate: float,
    params: dict,
    latest_extra: dict | None = None,
) -> dict:
    if shares > 0:
        bar = bars[-1]
        cash += shares * bar.close * (1 - fee_rate)
        shares = 0.0
        equity_curve[-1] = cash
        trades.append({"date": bar.date, "side": "sell", "price": bar.close, "equity": cash, "reason": "final_close"})

    final_equity = equity_curve[-1]
    trade_pairs = _trade_pairs(trades)
    wins = [p for p in trade_pairs if p["return"] > 0]
    closes = [b.close for b in bars]
    short_ma = sma(closes, min(5, max(2, len(closes) // 4)))
    long_ma = sma(closes, min(20, max(3, len(closes) // 2)))
    latest = {
        "date": bars[-1].date,
        "close": closes[-1],
        "sma_short": short_ma[-1],
        "sma_long": long_ma[-1],
    }
    if latest_extra:
        latest.update(latest_extra)
    suggestion = _suggest_from_metrics(latest, equity_curve, False)
    result = {
        "strategy": strategy,
        "params": {**params, "initial_cash": initial_cash, "fee_rate": fee_rate},
        "bars": len(bars),
        "start_date": bars[0].date,
        "end_date": bars[-1].date,
        "initial_cash": initial_cash,
        "final_equity": round(final_equity, 2),
        "total_return": round(final_equity / initial_cash - 1, 4),
        "annualized_return": round(_annualized_return(initial_cash, final_equity, len(bars)), 4),
        "max_drawdown": round(max_drawdown(equity_curve), 4),
        "trades_count": len(trade_pairs),
        "win_rate": round(len(wins) / len(trade_pairs), 4) if trade_pairs else 0.0,
        "latest": latest,
        "suggestion": suggestion,
        "recent_trades": trades[-10:],
        "recent_trade_pairs": trade_pairs[-10:],
        "disclaimer": "历史回测不代表未来收益；结果仅用于验证策略假设和风控。",
    }
    result["risk_adjusted_score"] = score_backtest_result(result)
    return result


def _trade_pairs(trades: list[dict]) -> list[dict]:
    pairs = []
    open_trade = None
    for trade in trades:
        if trade["side"] == "buy":
            open_trade = trade
        elif trade["side"] == "sell" and open_trade:
            ret = trade["price"] / open_trade["price"] - 1
            pairs.append({"entry": open_trade, "exit": trade, "return": ret})
            open_trade = None
    return pairs


def score_backtest_result(result: dict) -> float:
    """Risk-adjusted score, intentionally penalizing drawdown and no-trade fits."""
    total_return = float(result.get("total_return", 0) or 0)
    max_dd = abs(float(result.get("max_drawdown", 0) or 0))
    win_rate = float(result.get("win_rate", 0) or 0)
    trades = int(result.get("trades_count", 0) or 0)
    score = total_return * 100
    score -= max_dd * 120
    score += win_rate * 15
    score += min(trades, 8) * 1.5
    if trades == 0:
        score -= 20
    if max_dd > 0.2:
        score -= 25
    return round(score, 2)


def run_backtest_strategy(
    bars: list[Bar],
    strategy: str = "sma_cross",
    initial_cash: float = 100000.0,
    fee_rate: float = 0.0003,
    **params: Any,
) -> dict:
    if strategy == "sma_cross":
        return backtest_sma_cross(
            bars,
            short_window=int(params.get("short_window", 5)),
            long_window=int(params.get("long_window", 20)),
            initial_cash=initial_cash,
            fee_rate=fee_rate,
        )
    if strategy == "breakout":
        return backtest_breakout(
            bars,
            breakout_window=int(params.get("breakout_window", 20)),
            exit_window=int(params.get("exit_window", 10)),
            initial_cash=initial_cash,
            fee_rate=fee_rate,
        )
    if strategy == "rsi_reversion":
        return backtest_rsi_reversion(
            bars,
            rsi_window=int(params.get("rsi_window", 14)),
            buy_below=float(params.get("buy_below", 35)),
            sell_above=float(params.get("sell_above", 55)),
            initial_cash=initial_cash,
            fee_rate=fee_rate,
        )
    raise ValueError(f"Unknown strategy: {strategy}")


def optimize_backtests(
    bars: list[Bar],
    initial_cash: float = 100000.0,
    fee_rate: float = 0.0003,
) -> dict:
    """Compare a small conservative parameter grid across strategies."""
    candidates = []
    grids = [
        ("sma_cross", [{"short_window": s, "long_window": l} for s, l in ((3, 8), (5, 20), (10, 30))]),
        ("breakout", [{"breakout_window": b, "exit_window": e} for b, e in ((10, 5), (20, 10), (30, 15))]),
        ("rsi_reversion", [{"rsi_window": 14, "buy_below": b, "sell_above": s} for b, s in ((30, 50), (35, 55), (40, 60))]),
    ]
    for strategy, params_list in grids:
        for params in params_list:
            try:
                result = run_backtest_strategy(bars, strategy, initial_cash, fee_rate, **params)
                candidates.append(result)
            except Exception as exc:
                candidates.append({"strategy": strategy, "params": params, "error": f"{type(exc).__name__}: {exc}", "risk_adjusted_score": -999})
    ranked = sorted(candidates, key=lambda x: x.get("risk_adjusted_score", -999), reverse=True)
    return {
        "best": ranked[0] if ranked else None,
        "candidates": ranked,
        "selection_rule": "按收益、回撤、胜率、交易数综合评分；回撤和无交易会被惩罚。",
    }


def _suggest_from_metrics(latest: dict, equity_curve: list[float], in_position: bool) -> dict:
    flags = []
    rsi_value = latest.get("rsi14")
    short_ma = latest.get("sma_short")
    long_ma = latest.get("sma_long")
    close = latest.get("close")
    dd = max_drawdown(equity_curve)
    if rsi_value is not None and rsi_value >= 70:
        flags.append("RSI偏高，避免追高或降低仓位")
    if rsi_value is not None and rsi_value <= 30:
        flags.append("RSI偏低，可能超跌但需等待止跌证据")
    if short_ma is not None and long_ma is not None:
        flags.append("短均线在长均线上方，趋势偏多" if short_ma > long_ma else "短均线在长均线下方，趋势偏弱")
    if dd <= -0.2:
        flags.append("策略历史最大回撤超过20%，必须降低仓位或优化规则")

    if in_position:
        verdict = "持有但盯紧止损"
    elif short_ma is not None and long_ma is not None and short_ma > long_ma and not (rsi_value and rsi_value >= 70):
        verdict = "观察或小仓试错"
    else:
        verdict = "等待更清晰信号"
    if close and latest.get("atr14"):
        flags.append(f"可参考ATR止损: 约 {round(close - 2 * latest['atr14'], 3)}")
    return {"verdict": verdict, "flags": flags}


def analyze_hot_themes(items: list[dict], themes: dict[str, list[str]] | None = None, top_k: int = 10) -> dict:
    """Score hot themes from news/research snippets.

    items: [{"title": "...", "text": "...", "date": "YYYY-MM-DD", "source": "..."}]
    """
    themes = themes or DEFAULT_THEMES
    now = datetime.now()
    scored: dict[str, dict] = {}
    for name, keywords in themes.items():
        scored[name] = {
            "theme": name,
            "score": 0.0,
            "mentions": 0,
            "keywords": [],
            "evidence": [],
            "lifecycle_hits": {key: 0 for key in LIFECYCLE_KEYWORDS},
        }

    for item in items:
        title = str(item.get("title", ""))
        text = str(item.get("text", ""))
        body = f"{title}\n{text}"
        date_text = str(item.get("date", ""))
        recency = 1.0
        try:
            dt = datetime.fromisoformat(date_text[:10])
            recency = max(0.25, 1.0 - min((now - dt).days, 30) / 40)
        except ValueError:
            pass
        for name, keywords in themes.items():
            matched = []
            for kw in keywords:
                count = len(re.findall(re.escape(kw), body, flags=re.IGNORECASE))
                if count:
                    matched.append(kw)
                    scored[name]["score"] += count * recency
                    scored[name]["mentions"] += count
            if matched:
                scored[name]["keywords"] = sorted(set(scored[name]["keywords"]) | set(matched))
                for phase, phase_keywords in LIFECYCLE_KEYWORDS.items():
                    scored[name]["lifecycle_hits"][phase] += sum(
                        len(re.findall(re.escape(kw), body, flags=re.IGNORECASE))
                        for kw in phase_keywords
                    )
                if len(scored[name]["evidence"]) < 5:
                    scored[name]["evidence"].append({
                        "title": title[:120],
                        "date": date_text,
                        "source": item.get("source", ""),
                        "matched": matched[:8],
                    })

    ranked = sorted(scored.values(), key=lambda x: (x["score"], x["mentions"]), reverse=True)
    ranked = [r for r in ranked if r["score"] > 0][:top_k]
    for rank, row in enumerate(ranked, 1):
        row["rank"] = rank
        row["score"] = round(row["score"], 3)
        lifecycle = classify_theme_lifecycle(row)
        row.update(lifecycle)
        row["suggestion"] = _theme_suggestion(row)
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "items_count": len(items),
        "themes": ranked,
        "disclaimer": "题材热度来自输入文本统计，只能提示关注方向，不能单独作为买入依据。"
    }


def _theme_suggestion(row: dict) -> str:
    phase = row.get("lifecycle", "")
    if phase == "高潮":
        return "高热但一致性强，避免追高，等待分歧或龙头回踩"
    if phase == "退潮":
        return "题材退潮，原则上回避，只观察是否出现修复"
    if phase == "分歧":
        return "分歧阶段，只考虑核心标的低吸，必须设置硬止损"
    if phase == "发酵":
        return "题材发酵，进入观察池，等待龙头确认和量能验证"
    if row["score"] >= 8 and row["mentions"] >= 5:
        return "高热题材，优先寻找分歧低吸或龙头回踩，避免一致性追高"
    if row["score"] >= 3:
        return "中等热度，进入观察池，等待价格与成交量确认"
    return "轻度提及，仅记录，不作为交易触发"


def classify_theme_lifecycle(row: dict) -> dict:
    """Classify a theme's lifecycle from heat and narrative keywords."""
    hits = row.get("lifecycle_hits", {}) or {}
    score = float(row.get("score", 0) or 0)
    mentions = int(row.get("mentions", 0) or 0)
    phase = "弱关注"
    risk = "低"
    priority = 1

    if hits.get("fade", 0) > 0:
        phase, risk, priority = "退潮", "高", 0
    elif hits.get("climax", 0) > 0 or (score >= 10 and mentions >= 8):
        phase, risk, priority = "高潮", "高", 2
    elif hits.get("diverge", 0) > 0:
        phase, risk, priority = "分歧", "中高", 3
    elif hits.get("confirm", 0) > 0 or (score >= 6 and mentions >= 5):
        phase, risk, priority = "确认", "中", 4
    elif hits.get("launch", 0) > 0 or score >= 3:
        phase, risk, priority = "发酵", "中", 3

    return {
        "lifecycle": phase,
        "risk_level": risk,
        "action_priority": priority,
        "next_action": _next_action_for_phase(phase),
    }


def _next_action_for_phase(phase: str) -> str:
    actions = {
        "弱关注": "只记录，不交易",
        "发酵": "加入观察池，找龙头和补涨梯队",
        "确认": "等待回踩或分歧低吸，不追连续加速",
        "分歧": "只看核心承接，破位立即放弃",
        "高潮": "不追高，等待分歧或退潮后的二次确认",
        "退潮": "回避，复盘亏钱效应和高位风险",
    }
    return actions.get(phase, "观察")


def score_watchlist_candidates(backtests: list[dict], themes: list[dict]) -> list[dict]:
    """Rank watchlist candidates by backtest quality and theme lifecycle."""
    theme_by_name = {str(t.get("theme", "")).lower(): t for t in themes}
    scored = []
    for bt in backtests:
        row = dict(bt)
        if "error" in row:
            row["candidate_score"] = 0
            row["candidate_action"] = "数据错误，不能交易"
            scored.append(row)
            continue
        theme_name = str(row.get("theme", "")).lower()
        theme = theme_by_name.get(theme_name, {})
        score = 0.0
        total_return = float(row.get("total_return", 0) or 0)
        drawdown = abs(float(row.get("max_drawdown", 0) or 0))
        win_rate = float(row.get("win_rate", 0) or 0)
        score += max(min(total_return * 100, 25), -25)
        score += max(0, (0.2 - drawdown) * 50)
        score += win_rate * 15
        score += float(theme.get("action_priority", 1) or 1) * 8
        if theme.get("lifecycle") in ("高潮", "退潮"):
            score -= 20
        row["candidate_score"] = round(score, 2)
        row["theme_lifecycle"] = theme.get("lifecycle", "")
        row["theme_risk_level"] = theme.get("risk_level", "")
        row["candidate_action"] = _candidate_action(score, theme)
        scored.append(row)
    return sorted(scored, key=lambda x: x.get("candidate_score", 0), reverse=True)


def _candidate_action(score: float, theme: dict) -> str:
    phase = theme.get("lifecycle")
    if phase in ("高潮", "退潮"):
        return "回避追高，等待新买点"
    if score >= 35:
        return "重点观察，交易前仍需 consult 风控检查"
    if score >= 20:
        return "普通观察，小仓试错条件更严格"
    return "暂不交易，继续收集证据"
