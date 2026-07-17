"""
槽位管理器 — 管理每日3个交易槽位 + 跨日仓位
规则：
  - 每股票日最多3笔未回笼卖出
  - 回笼后可继续开新槽
  - 跨日仓位优先接回
  - 槽1>槽2>槽3优先级
"""

import json
import os
import time
from datetime import datetime, date
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from enum import Enum

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORK_DIR, "data")
SLOTS_FILE = os.path.join(DATA_DIR, "slots.json")


class SlotState(Enum):
    EMPTY = "empty"
    SHORT_PENDING = "short_pending"   # 卖出挂单中
    SHORT_FILLED = "short_filled"     # 卖出已成交，等接回
    LONG_PENDING = "long_pending"      # 接回挂单中
    LONG_FILLED = "long_filled"       # 接回完成（当日T仓结束）
    CANCELLED = "cancelled"
    FORCE_CLOSED = "force_closed"     # 14:50强制平仓


@dataclass
class Slot:
    slot_id: int           # 0,1,2
    stock: str             # 股票代码
    state: str
    # 卖出信息
    short_time: str         # 卖出挂单时间
    short_price: float      # 卖出成交价
    short_shares: int       # 卖出股数
    short_amount: float     # 卖出金额
    # 接回信息
    cover_time: Optional[str] = None
    cover_price: Optional[float] = None
    cover_shares: Optional[int] = None
    # 盈亏
    profit_pct: float = 0.0
    profit_abs: float = 0.0
    # 信号分
    signal_score: int = 0
    confidence: str = "C"
    # 跨日标记
    is_cross_day: bool = False
    # 元数据
    regime: str = "unknown"
    time_window: str = "T0"
    reasons: str = ""
    created_at: str = ""


class SlotManager:
    """
    管理双股槽位状态，支持跨日持久化
    """

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.slots: Dict[str, List[Optional[Slot]]] = {
            "300418": [None, None, None],
            "300058": [None, None, None],
        }
        self._today_sold_count: Dict[str, int] = {"300418": 0, "300058": 0}
        self._today_date: str = date.today().isoformat()
        self._load()

    def _load(self):
        """从磁盘加载槽位状态"""
        if not os.path.exists(SLOTS_FILE):
            return
        try:
            with open(SLOTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 检查是否是今天的数据
            if data.get("date") != self._today_date:
                # 新的一天，重置
                return
            self._today_sold_count = data.get("today_sold_count", {"300418": 0, "300058": 0})
            raw_slots = data.get("slots", {})
            for stock, slot_list in raw_slots.items():
                if stock in self.slots:
                    self.slots[stock] = [
                        Slot(**s) if s else None for s in slot_list
                    ]
        except Exception:
            pass

    def _save(self):
        """持久化槽位状态"""
        data = {
            "date": self._today_date,
            "today_sold_count": self._today_sold_count,
            "slots": {
                stock: [
                    asdict(s) if s else None
                    for s in slot_list
                ]
                for stock, slot_list in self.slots.items()
            }
        }
        with open(SLOTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def can_open_new_slot(self, stock: str) -> bool:
        """检查是否可开新槽（每日最多3笔卖出未回笼）"""
        return self._today_sold_count.get(stock, 0) < 3

    def open_short_slot(
        self,
        stock: str,
        signal_score: int,
        confidence: str,
        short_price: float,
        shares: int,
        regime: str = "unknown",
        time_window: str = "T0",
        reasons: str = "",
        is_cross_day: bool = False
    ) -> Optional[int]:
        """
        开启卖出槽位（倒T第一步）
        返回槽位ID，None表示无法开槽
        """
        if not self.can_open_new_slot(stock):
            return None

        for i, slot in enumerate(self.slots[stock]):
            if slot is None:
                now = datetime.now().strftime("%H:%M:%S")
                s = Slot(
                    slot_id=i,
                    stock=stock,
                    state=SlotState.SHORT_FILLED.value,
                    short_time=now,
                    short_price=short_price,
                    short_shares=shares,
                    short_amount=round(short_price * shares, 2),
                    signal_score=signal_score,
                    confidence=confidence,
                    regime=regime,
                    time_window=time_window,
                    reasons=reasons,
                    is_cross_day=is_cross_day,
                    created_at=now,
                )
                self.slots[stock][i] = s
                self._today_sold_count[stock] = self._today_sold_count.get(stock, 0) + 1
                self._save()
                return i
        return None

    def cover_slot(
        self,
        stock: str,
        slot_id: int,
        cover_price: float,
        cover_shares: int = None
    ) -> bool:
        """
        接回槽位（倒T完成）
        """
        slot = self.slots[stock][slot_id]
        if slot is None or slot.state not in (
            SlotState.SHORT_FILLED.value,
            SlotState.SHORT_PENDING.value,
        ):
            return False

        slot.state = SlotState.LONG_FILLED.value
        slot.cover_time = datetime.now().strftime("%H:%M:%S")
        slot.cover_price = cover_price
        slot.cover_shares = cover_shares or slot.short_shares

        # 计算盈亏
        # 倒T利润 = (卖出价 - 买回价) / 卖出价
        profit_pct = (slot.short_price - cover_price) / slot.short_price * 100
        profit_abs = (slot.short_price - cover_price) * slot.short_shares
        slot.profit_pct = round(profit_pct, 4)
        slot.profit_abs = round(profit_abs, 2)

        self._save()
        return True

    def cancel_slot(self, stock: str, slot_id: int, reason: str = "manual"):
        """取消槽位"""
        slot = self.slots[stock][slot_id]
        if slot:
            slot.state = SlotState.CANCELLED.value
            slot.reasons = slot.reasons + f" [取消:{reason}]"
            self._save()

    def force_close_all(self, stock: str, reason: str = "time_up"):
        """14:50 强制平所有未完成槽"""
        closed = []
        for i, slot in enumerate(self.slots[stock]):
            if slot and slot.state in (
                SlotState.SHORT_FILLED.value,
                SlotState.SHORT_PENDING.value,
            ):
                slot.state = SlotState.FORCE_CLOSED.value
                slot.cover_time = datetime.now().strftime("%H:%M:%S")
                slot.reasons = slot.reasons + f" [强平:{reason}]"
                closed.append(i)
        if closed:
            self._save()
        return closed

    def get_open_slots(self, stock: str) -> List[tuple]:
        """返回所有未完成的槽 (slot_id, slot)"""
        result = []
        for i, slot in enumerate(self.slots[stock]):
            if slot and slot.state in (
                SlotState.SHORT_FILLED.value,
                SlotState.SHORT_PENDING.value,
            ):
                result.append((i, slot))
        return result

    def get_cross_day_slots(self, stock: str) -> List[tuple]:
        """返回跨日槽（昨日卖出今日未回）"""
        result = []
        for i, slot in enumerate(self.slots[stock]):
            if slot and slot.is_cross_day and slot.state in (
                SlotState.SHORT_FILLED.value,
                SlotState.SHORT_PENDING.value,
            ):
                result.append((i, slot))
        return result

    def get_slot_count(self, stock: str) -> int:
        """今日已用槽位数量"""
        return sum(1 for s in self.slots[stock] if s is not None)

    def get_open_slot_count(self, stock: str) -> int:
        """今日未回笼槽位数"""
        return len(self.get_open_slots(stock))

    def get_status_summary(self, stock: str) -> Dict:
        """获取槽位状态摘要"""
        slots = self.slots[stock]
        total_sold = self._today_sold_count.get(stock, 0)
        open_count = self.get_open_slot_count(stock)
        completed = [s for s in slots if s and s.state == SlotState.LONG_FILLED.value]
        cross_day = [s for s in slots if s and s.is_cross_day]

        total_profit = sum(s.profit_abs for s in completed if s)
        total_pct = sum(s.profit_pct for s in completed if s)

        return {
            "stock": stock,
            "today_sold": total_sold,
            "open_count": open_count,
            "remaining_slots": 3 - total_sold,
            "can_open": total_sold < 3,
            "completed_count": len(completed),
            "total_profit": round(total_profit, 2),
            "avg_profit_pct": round(total_pct / len(completed), 4) if completed else 0,
            "cross_day_count": len(cross_day),
            "slots": [
                asdict(s) if s else None for s in slots
            ]
        }

    def reset_day(self):
        """新一天开始时重置（需手动调用或日期检测）"""
        today = date.today().isoformat()
        if today != self._today_date:
            self.slots = {"300418": [None, None, None], "300058": [None, None, None]}
            self._today_sold_count = {"300418": 0, "300058": 0}
            self._today_date = today
            self._save()

    def get_today_profit(self) -> Dict[str, Dict]:
        """计算今日各股票T仓利润"""
        result = {}
        for stock in ["300418", "300058"]:
            completed = [
                s for s in self.slots[stock]
                if s and s.state == SlotState.LONG_FILLED.value
            ]
            total_profit = sum(s.profit_abs for s in completed)
            total_pct = sum(s.profit_pct for s in completed)
            result[stock] = {
                "completed_trades": len(completed),
                "total_profit": round(total_profit, 2),
                "avg_profit_pct": round(total_pct / len(completed), 4) if completed else 0,
                "open_trades": self.get_open_slot_count(stock),
            }
        return result
