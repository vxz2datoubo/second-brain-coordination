"""
风险控制器 — 实时风控模块
规则：
  - 硬止损 单笔亏损 > 2%
  - 熔断 日累计 > 2%
  - 连亏降仓 连亏2笔后降为1槽
  - 黑天鹅 跌破20日线8%停所有T
  - 冷却期 卖出后30分钟不可卖出
"""

import json
import os
import time
from datetime import date, datetime
from typing import Dict, List, Optional

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORK_DIR, "data")
RISK_FILE = os.path.join(DATA_DIR, "risk_state.json")


class RiskController:
    """
    实时风控，记录每日风险状态并作出决策
    """

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.state = {
            "date": date.today().isoformat(),
            "max_daily_loss_pct": -2.0,
            "max_single_loss_pct": -2.0,
            "consecutive_loss_limit": 2,
            "cooldown_minutes": 30,
            "black_swan_pct": -8.0,

            "daily_loss_pct": 0.0,
            "consecutive_losses": 0,
            "is_circuit_break": False,
            "is_black_swan": False,
            "reduced_slots": False,
            "current_max_slots": 3,

            # 冷却期记录 {stock: {slot_id: unblock_time}}
            "cooldowns": {},
        }
        self._load()

    def _load(self):
        if os.path.exists(RISK_FILE):
            try:
                with open(RISK_FILE, "r") as f:
                    data = json.load(f)
                if data.get("date") == date.today().isoformat():
                    self.state.update(data)
            except Exception:
                pass

    def _save(self):
        with open(RISK_FILE, "w") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def reset_day(self):
        """每日重置"""
        today = date.today().isoformat()
        if self.state["date"] != today:
            self.state["date"] = today
            self.state["daily_loss_pct"] = 0.0
            self.state["consecutive_losses"] = 0
            self.state["is_circuit_break"] = False
            self.state["is_black_swan"] = False
            self.state["reduced_slots"] = False
            self.state["current_max_slots"] = 3
            self.state["cooldowns"] = {}
            self._save()

    def check_cooldown(self, stock: str, slot_id: int = None) -> bool:
        """
        检查冷却期
        卖出后 30 分钟不可卖出同一股票
        Returns: True = 可操作 / False = 冷却中
        """
        cooldowns = self.state["cooldowns"].get(stock, {})
        now = time.time()
        for slot_str, unblock_time in list(cooldowns.items()):
            if now < unblock_time:
                if slot_id is not None and str(slot_id) == slot_str:
                    return False
            else:
                del cooldowns[slot_str]
        if slot_id is not None and str(slot_id) in cooldowns:
            return now >= cooldowns[str(slot_id)]
        return True

    def start_cooldown(self, stock: str, slot_id: int):
        """开始冷却期"""
        self.state["cooldowns"].setdefault(stock, {})
        unblock_time = time.time() + self.state["cooldown_minutes"] * 60
        self.state["cooldowns"][stock][str(slot_id)] = unblock_time
        self._save()

    def register_trade_result(self, profit_pct: float):
        """注册一笔交易结果，更新风控状态"""
        # 更新日亏损
        self.state["daily_loss_pct"] += profit_pct

        # 连亏追踪
        if profit_pct < 0:
            self.state["consecutive_losses"] += 1
        else:
            self.state["consecutive_losses"] = 0

        # 熔断检查
        if self.state["daily_loss_pct"] <= self.state["max_daily_loss_pct"]:
            self.state["is_circuit_break"] = True
            self.state["current_max_slots"] = 0

        # 连亏降仓
        if self.state["consecutive_losses"] >= self.state["consecutive_loss_limit"]:
            self.state["reduced_slots"] = True
            self.state["current_max_slots"] = 1

        self._save()

    def set_black_swan(self):
        """标记黑天鹅事件"""
        self.state["is_black_swan"] = True
        self.state["current_max_slots"] = 0
        self._save()

    def can_trade(self, stock: str = None) -> Dict:
        """
        综合风险检查
        Returns: {"allowed": bool, "reason": str, "max_slots": int}
        """
        reasons = []

        if self.state["is_circuit_break"]:
            reasons.append("熔断触发：日亏损超限")

        if self.state["is_black_swan"]:
            reasons.append("黑天鹅：已触发全局停止")

        max_slots = self.state["current_max_slots"]

        # 连续亏损检查
        if self.state["consecutive_losses"] >= 2:
            reasons.append(
                f"连亏{self.state['consecutive_losses']}笔触发降仓"
            )

        # 冷却期检查
        if stock and not self.check_cooldown(stock):
            reasons.append("冷却期：该股票尚在冷却中")

        allowed = len(reasons) == 0

        return {
            "allowed": allowed,
            "reasons": "; ".join(reasons),
            "max_slots": max_slots,
            "circuit_break": self.state["is_circuit_break"],
            "black_swan": self.state["is_black_swan"],
            "consecutive_losses": self.state["consecutive_losses"],
            "daily_loss_pct": self.state["daily_loss_pct"],
        }

    def get_summary(self) -> Dict:
        return {k: v for k, v in self.state.items() if not k.startswith("_")}


# 全局单例
_controller: Optional[RiskController] = None

def get_risk_controller() -> RiskController:
    global _controller
    if _controller is None:
        _controller = RiskController()
    return _controller
