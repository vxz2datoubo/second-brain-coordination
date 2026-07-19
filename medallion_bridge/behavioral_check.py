"""behavioral_check.py — 行为金融偏差实时检测 v1

追踪用户最近交易，检测锚定效应、处置效应、参考点适应滞后等偏差。
集成到 auto_tracker 中，每次输出自动附加行为警告。

用法: python behavioral_check.py  --price 44.5 --cost 44.61 --sold 12.57 --last-buy 44.34
"""

import sys, os, json, time
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_trade_state.json")


def load_trades():
    """加载今日交易记录"""
    if not os.path.exists(STATE_FILE):
        return {"trades": [], "last_sell_price": None, "last_sell_time": None}
    with open(STATE_FILE) as f:
        return json.load(f)


def save_trades(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, default=str)


def record_trade(action, code, price, note=""):
    """记录一笔交易"""
    state = load_trades()
    state["trades"].append({
        "time": datetime.now().isoformat(),
        "action": action, "code": code, "price": price, "note": note
    })
    if action == "sell":
        state["last_sell_price"] = price
        state["last_sell_time"] = datetime.now().isoformat()
    save_trades(state)


def detect_biases(current_prices, cost_basis):
    """检测当前是否存在行为偏差

    Returns: list of (bias_name, severity, explanation)
    """
    state = load_trades()
    biases = []

    # 1. 参考点适应滞后: 最后卖价 vs 现价
    last_sell = state.get("last_sell_price")
    if last_sell and cost_basis:
        # 如果卖出价 > 当前价 > 成本价: 在"要不要买回"的犹豫中
        if last_sell > current_prices[0] > cost_basis[0]:
            gap = (last_sell - current_prices[0]) / last_sell * 100
            biases.append((
                "参考点适应滞后",
                "中",
                f"你{last_sell}卖出的票现在{current_prices[0]}（已低{gap:.1f}%），但你可能还被锚在卖出价上",
                "Shefrin & Statman, 1985"
            ))

    # 2. 成本锚定: 持股成本 vs 现价
    for i, (cost, price) in enumerate(zip(cost_basis, current_prices)):
        if cost and price:
            pnl = (price - cost) / cost * 100
            if -3 < pnl < 1:  # 在成本线附近(-3%到+1%)
                biases.append((
                    "成本锚定(处置效应)",
                    "高" if pnl < 0 else "低",
                    f"持仓#{i+1}成本{cost}，现价{price}（{pnl:+.1f}%）— 不要因为'还没回本'而做决策",
                    "Odean, 1998"
                ))

    # 3. 频繁交易检查
    recent_sells = [t for t in state["trades"] if t["action"] == "sell"]
    if len(recent_sells) >= 3:
        biases.append((
            "过度交易",
            "低",
            f"今天已卖出{len(recent_sells)}笔，注意交易频率",
            "Barber & Odean, 2000"
        ))

    # 4. 盈利后保守性
    recent_wins = [t for t in state["trades"] if t["action"] == "buy" and t.get("pnl", 0) > 0]
    if len(recent_wins) >= 2 and len(state["trades"]) > 5:
        biases.append((
            "盈后保守",
            "低",
            "连续盈利后容易变得保守，不敢承担后续风险",
            "Thaler & Johnson, 1990"
        ))

    return biases


if __name__ == "__main__":
    # Demo
    state = load_trades()
    print(f"今日交易: {len(state['trades'])} 笔")
    biases = detect_biases([44.5], [44.61])
    for b in biases:
        print(f"  ⚠️ {b[0]}: {b[2]} ({b[3]})")
