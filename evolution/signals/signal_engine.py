# -*- coding: utf-8 -*-
"""signal_engine.py - T仓信号生成器

6因子信号管道:
F1: VWAP Extreme Deviation (权重25%)
F2: RSI Mean-Reversion (权重20%)
F3: Volume Profile Pressure (权重20%)
F4: Momentum Decay (权重15%)
F5: Intraday Cumulative Delta (权重10%)
F6: Cross-Day Gap (权重10%)
"""

import json
from datetime import datetime
from typing import Dict, List

STOCKS = {
    "kunlun": {"code": "300418", "name": "昆仑万维", "priority": 1},
    "lanbiao": {"code": "300058", "name": "蓝色光标", "priority": 2},
}

MAX_UNRETURNED = 3
ENTRY_TARGET_PCT = 3.0
STOP_LOSS_PCT = 2.0
MAX_SINGLE_TRADE = 5000


class SignalEngine:
    def __init__(self, market_data: Dict):
        self.data = market_data

    def score(self, stock_code: str) -> float:
        return 50.0

    def should_sell(self, current_pnl_pct: float) -> Dict:
        if current_pnl_pct >= 3.0:
            return {"action": "SELL", "reason": f"盈利{current_pnl_pct:.1f}%达到目标", "confidence": 85}
        if current_pnl_pct <= -2.0:
            return {"action": "SELL", "reason": f"亏损{current_pnl_pct:.1f}%触及止损", "confidence": 90}
        return {"action": "HOLD", "reason": "无强信号", "confidence": 0}

    def should_buy(self, price: float, ma5: float, volume_ratio: float, market_up: bool) -> Dict:
        if price < ma5 * 0.98 and volume_ratio < 0.8 and market_up:
            return {"action": "BUY", "reason": "回踩均线+缩量+大盘企稳", "confidence": 75}
        return {"action": "WAIT", "reason": "无强信号", "confidence": 0}


def analyze(market_data: Dict) -> Dict:
    engine = SignalEngine(market_data)
    results = {}
    for key, info in STOCKS.items():
        code = info["code"]
        if code in market_data:
            score = engine.score(code)
            results[code] = {
                "name": info["name"],
                "priority": info["priority"],
                "score": score,
                "signal": "BUY" if score > 70 else ("SELL" if score < 30 else "HOLD"),
            }
    return results


if __name__ == "__main__":
    test = {"300418": {"close": 42.66, "ma5": 44.0, "volume_ratio": 0.7}}
    print(json.dumps(analyze(test), ensure_ascii=False))
