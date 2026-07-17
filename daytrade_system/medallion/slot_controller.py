"""slot_controller — 大奖章槽位状态机 V2

升级版核心改进（相比v1）：
  1. 严格止损：-1.0% 硬止损（原-2.0%太宽松导致盈亏比崩溃）
  2. 飞逃立即执行：涨超+2.0%立即接回，不等待（原+3.0%导致T7大亏-5.0%）
  3. 跨日仓位独立处理：开盘大跌立即接回，大涨止损接回
  4. 信号冷却：卖出后30分钟不能再次卖出
  5. 每日熔断：累计亏损>2.0%全天停止
  6. 连亏降仓：连续2笔亏损后降为1个槽

关键设计：
  - 槽位方向只做倒T（先卖后买），禁止正T
  - 每笔5000元，100股整数倍
  - 最多3个槽，跨日仓位优先处理
  - 时间止损：持有超40分钟（蓝色）/ 50分钟（昆仑）强制平仓
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime, date
from enum import Enum
from .config import STOCK_CONFIGS, GLOBAL_AMOUNT_PER_TRADE


class SlotState(Enum):
    EMPTY = "empty"
    SHORT_PENDING = "short_pending"   # 已挂卖出单，待成交
    SHORT_FILLED = "short_filled"     # 已卖出，待接回
    CLOSED = "closed"                 # 已平仓完成


@dataclass
class Slot:
    id: int
    state: SlotState = SlotState.EMPTY
    direction: str = ""          # "short"
    open_price: float = 0.0      # 卖出价
    open_time: str = ""          # "HH:MM"
    open_date: str = ""          # "YYYY-MM-DD"
    target_price: float = 0.0    # 目标接回价
    stop_loss: float = 0.0       # 止损价
    flee_price: float = 0.0     # 飞逃价（卖后涨超此价立即接回）
    stop_time_minutes: int = 40  # 时间止损（分钟）
    entry_score: float = 0.0     # 开仓时的信号分
    entry_reason: str = ""       # 开仓理由
    exit_price: float = 0.0      # 平仓价
    exit_time: str = ""          # 平仓时间
    profit_pct: float = 0.0     # 收益率%
    was_carried: bool = False   # 是否跨日仓

    @property
    def is_open(self):
        return self.state in (SlotState.SHORT_PENDING, SlotState.SHORT_FILLED)

    def unrealized_pnl(self, current_price: float) -> float:
        """未实现盈亏%"""
        if not self.is_open or self.open_price == 0:
            return 0.0
        # 倒T：卖出价固定，当前价越低越赚钱
        return (self.open_price / current_price - 1) * 100


@dataclass
class SlotDecision:
    """槽位决策输出"""
    action: str          # "sell_slot1" / "buy_back_slot1" / "wait" / "hold"
    slot_id: int
    price: float        # 建议执行价
    reason: str
    urgency: str        # "immediate" / "normal" / "low"
    limit: bool         # 是否触及当日限制


class SlotController:
    """大奖章槽位控制器"""

    MAX_SLOTS = 3

    def __init__(self, code: str):
        self.code = code
        self.cfg = STOCK_CONFIGS[code]
        self.slots: List[Slot] = [Slot(id=i + 1) for i in range(self.MAX_SLOTS)]
        self.today = date.today().isoformat()

        # 每日状态
        self.daily_sell_count = 0
        self.daily_buy_count = 0
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.is_meltdown = False    # 熔断
        self.is_reduced = False     # 降仓
        self.last_sell_time = None  # 用于冷却期

        # 历史记录
        self.history: List[Slot] = []

    # ============================================================
    # 槽位查询
    # ============================================================

    @property
    def open_slots(self) -> List[Slot]:
        return [s for s in self.slots if s.is_open]

    @property
    def empty_slots(self) -> List[Slot]:
        return [s for s in self.slots if s.state == SlotState.EMPTY]

    @property
    def carried_slots(self) -> List[Slot]:
        """跨日仓位"""
        return [s for s in self.open_slots if s.was_carried]

    @property
    def today_slots(self) -> List[Slot]:
        """当日仓位"""
        return [s for s in self.open_slots if not s.was_carried]

    def can_sell_more(self) -> tuple:
        """是否还能卖出"""
        if self.is_meltdown:
            return False, "熔断中，全天停止"
        if self.daily_sell_count >= self.cfg.max_trades_per_day:
            return False, f"已达{self.cfg.max_trades_per_day}笔/日上限"

        max_available = self.cfg.max_trades_per_day - self.daily_sell_count
        if self.is_reduced:
            max_available = min(max_available, 1)
        return max_available > 0, f"可用{self.available_sell_slots}笔"

    @property
    def available_sell_slots(self) -> int:
        if self.is_meltdown:
            return 0
        base = self.cfg.max_trades_per_day - self.daily_sell_count
        return max(0, 1 if self.is_reduced else base)

    # ============================================================
    # 核心决策函数
    # ============================================================

    def check(self, current_price: float, current_time: str,
              signal_score: float = 0, signal_reason: str = "",
              prev_close: float = None, open_price_today: float = None) -> List[SlotDecision]:
        """
        主决策函数：每5分钟调用一次
        返回需要执行的操作列表
        """
        decisions = []
        now = datetime.strptime(current_time, "%H:%M")

        # === 1. 先检查止损 ===
        for slot in self.open_slots:
            dec = self._check_stop_conditions(slot, current_price, current_time, now, prev_close, open_price_today)
            if dec:
                decisions.append(dec)

        # === 2. 检查接回机会（优先处理跨日仓）===
        # 先处理跨日仓，再处理当日仓
        for slot in sorted(self.open_slots, key=lambda s: (0 if s.was_carried else 1, -s.open_price)):
            dec = self._check_exit_opportunity(slot, current_price, current_time, now)
            if dec:
                decisions.append(dec)

        # === 3. 检查是否可以开新仓 ===
        if not decisions:  # 只有在没有紧急平仓时才考虑开新仓
            dec = self._check_new_entry(signal_score, signal_reason, current_price, current_time, now)
            if dec:
                decisions.append(dec)

        return decisions

    def _check_stop_conditions(self, slot: Slot, price: float, current_time: str,
                                now: datetime, prev_close: float, open_price_today: float) -> Optional[SlotDecision]:
        """
        检查止损条件（最高优先级）
        """
        pnl = slot.unrealized_pnl(price)

        # 1. 硬止损：亏损>1.0%
        if pnl <= self.cfg.hard_stop_loss_pct:
            return SlotDecision(
                action=f"buy_back_slot{slot.id}",
                slot_id=slot.id,
                price=price,
                reason=f"硬止损: {pnl:.2f}% ≤ {self.cfg.hard_stop_loss_pct}%",
                urgency="immediate",
                limit=False,
            )

        # 2. 飞逃止损：卖后继续涨超+2.0%
        flee_pnl = (price / slot.open_price - 1) * 100  # 正数=继续涨=亏损
        if flee_pnl >= self.cfg.flee_stop_pct:
            return SlotDecision(
                action=f"buy_back_slot{slot.id}",
                slot_id=slot.id,
                price=price,
                reason=f"飞逃止损: 卖后继续涨{flee_pnl:.2f}% ≥ {self.cfg.flee_stop_pct}%，立即接回",
                urgency="immediate",
                limit=False,
            )

        # 3. 跨日仓位特殊处理
        if slot.was_carried and open_price_today:
            # 开盘大跌>1.0%：立即接回（锁定利润）
            if prev_close:
                open_gap = (open_price_today / prev_close - 1) * 100
                if open_gap < -1.0 and price <= slot.open_price * 1.005:
                    return SlotDecision(
                        action=f"buy_back_slot{slot.id}",
                        slot_id=slot.id,
                        price=price,
                        reason=f"跨日开盘大跌{open_gap:.1f}%，立即接回锁定利润",
                        urgency="immediate",
                        limit=False,
                    )
            # 开盘大涨>1.0%：止损接回
            if prev_close:
                open_gap = (open_price_today / prev_close - 1) * 100
                if open_gap > 1.0 and price > slot.open_price * 1.015:
                    return SlotDecision(
                        action=f"buy_back_slot{slot.id}",
                        slot_id=slot.id,
                        price=price,
                        reason=f"跨日开盘大涨{open_gap:.1f}%，止损接回",
                        urgency="immediate",
                        limit=False,
                    )

        # 4. 时间止损
        if slot.open_time:
            open_dt = datetime.strptime(slot.open_time, "%H:%M")
            hold_minutes = (now - open_dt).total_seconds() / 60
            if hold_minutes >= slot.stop_time_minutes and pnl < self.cfg.min_profit_take_pct:
                return SlotDecision(
                    action=f"buy_back_slot{slot.id}",
                    slot_id=slot.id,
                    price=price,
                    reason=f"时间止损: 持有{hold_minutes:.0f}分钟未达{self.cfg.min_profit_take_pct}%止盈",
                    urgency="normal",
                    limit=False,
                )

        # 5. 尾盘强平：14:50前未接回
        if current_time >= "14:50" and slot.is_open:
            return SlotDecision(
                action=f"buy_back_slot{slot.id}",
                slot_id=slot.id,
                price=price,
                reason=f"尾盘强平: {current_time}未接回",
                urgency="immediate",
                limit=False,
            )

        return None

    def _check_exit_opportunity(self, slot: Slot, price: float, current_time: str, now: datetime) -> Optional[SlotDecision]:
        """
        检查接回机会
        """
        if slot.state != SlotState.SHORT_FILLED:
            return None

        pnl = slot.unrealized_pnl(price)

        # 机会1：价格已回到卖出价（VWAP回归）
        if price <= slot.open_price * 1.001:  # 略微溢价1%内都算
            if pnl >= 0.1:  # 至少有0.1%利润
                return SlotDecision(
                    action=f"buy_back_slot{slot.id}",
                    slot_id=slot.id,
                    price=price,
                    reason=f"价格回归卖出价{slot.open_price:.4f}，盈利{pnl:.2f}%，接回",
                    urgency="normal",
                    limit=False,
                )

        # 机会2：触及VWAP均线（强势回归）
        # 这里用open_price*0.995粗略估算VWAP回归点
        if price <= slot.open_price * (1 - self.cfg.min_profit_take_pct / 100):
            return SlotDecision(
                action=f"buy_back_slot{slot.id}",
                slot_id=slot.id,
                price=price,
                reason=f"触及VWAP回归点，利润{pnl:.2f}%",
                urgency="low",
                limit=False,
            )

        # 机会3：贪心止盈（持有超30分钟且利润超0.6%时继续等VWAP回归）
        if slot.open_time:
            open_dt = datetime.strptime(slot.open_time, "%H:%M")
            hold_min = (now - open_dt).total_seconds() / 60
            if hold_min >= 30 and pnl >= self.cfg.greedy_profit_pct:
                # 给更多时间，不急着接回
                return SlotDecision(
                    action="wait",
                    slot_id=slot.id,
                    price=price,
                    reason=f"持有{hold_min:.0f}分钟，利润{pnl:.2f}%，继续等更大回归",
                    urgency="low",
                    limit=False,
                )

        return None

    def _check_new_entry(self, signal_score: float, signal_reason: str,
                          current_price: float, current_time: str, now: datetime) -> Optional[SlotDecision]:
        """
        检查是否可以开新仓
        """
        # 冷却期检查
        if self.last_sell_time:
            last_dt = datetime.strptime(self.last_sell_time, "%H:%M")
            cooldown = (now - last_dt).total_seconds() / 60
            if cooldown < 30:
                return None  # 冷却期内不卖出

        # 熔断/降仓检查
        can_sell, msg = self.can_sell_more()
        if not can_sell:
            return None

        # 信号门槛检查
        threshold = self.cfg.entry_score_threshold
        if signal_score < threshold:
            return None  # 信号不够强，不开仓

        # 有空槽
        if not self.empty_slots:
            return None

        slot = self.empty_slots[0]

        # 计算止损/飞逃价格
        stop_loss = current_price * (1 + abs(self.cfg.hard_stop_loss_pct) / 100)
        flee_price = current_price * (1 + self.cfg.flee_stop_pct / 100)

        return SlotDecision(
            action=f"sell_slot{slot.id}",
            slot_id=slot.id,
            price=current_price,
            reason=f"开仓: 信号{signal_score:.0f}分 {signal_reason}",
            urgency="normal",
            limit=False,
        )

    # ============================================================
    # 操作执行
    # ============================================================

    def execute_sell(self, slot_id: int, price: float, current_time: str,
                     score: float = 0, reason: str = ""):
        """执行卖出"""
        slot = self.slots[slot_id - 1]
        slot.state = SlotState.SHORT_FILLED
        slot.direction = "short"
        slot.open_price = price
        slot.open_time = current_time
        slot.open_date = self.today
        slot.target_price = price * (1 - self.cfg.min_profit_take_pct / 100)
        slot.stop_loss = price * (1 + abs(self.cfg.hard_stop_loss_pct) / 100)
        slot.flee_price = price * (1 + self.cfg.flee_stop_pct / 100)
        slot.stop_time_minutes = self.cfg.time_stop_minutes
        slot.entry_score = score
        slot.entry_reason = reason
        slot.was_carried = False

        self.daily_sell_count += 1
        self.last_sell_time = current_time

    def execute_buy_back(self, slot_id: int, price: float, current_time: str):
        """执行买回"""
        slot = self.slots[slot_id - 1]
        if not slot.is_open:
            return

        profit_pct = (slot.open_price / price - 1) * 100

        slot.state = SlotState.CLOSED
        slot.exit_price = price
        slot.exit_time = current_time
        slot.profit_pct = profit_pct

        self.daily_buy_count += 1
        self.daily_pnl += profit_pct
        self.history.append(slot)

        # 更新连续亏损
        if profit_pct > 0:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            if self.consecutive_losses >= 2:
                self.is_reduced = True

        # 熔断检查
        if self.daily_pnl <= -2.0:
            self.is_meltdown = True

    def carry_over(self) -> List[Dict]:
        """收盘时将未平仓位标记为跨日"""
        carried = []
        for slot in self.open_slots:
            slot.was_carried = True
            carried.append({
                "id": slot.id,
                "open_price": slot.open_price,
                "open_time": slot.open_time,
                "open_date": slot.open_date,
                "entry_score": slot.entry_score,
                "entry_reason": slot.entry_reason,
                "flee_price": slot.flee_price,
                "stop_loss": slot.stop_loss,
                "was_carried": True,
            })
        return carried

    def load_carried(self, carried: List[Dict]):
        """次日开盘时加载跨日仓位"""
        for c in carried:
            slot = self.slots[c["id"] - 1]
            slot.state = SlotState.SHORT_FILLED
            slot.direction = "short"
            slot.open_price = c["open_price"]
            slot.open_time = c["open_time"]
            slot.open_date = c["open_date"]
            slot.entry_score = c.get("entry_score", 0)
            slot.entry_reason = c.get("entry_reason", "")
            slot.flee_price = c.get("flee_price", c["open_price"] * 1.02)
            slot.stop_loss = c.get("stop_loss", c["open_price"] * 1.01)
            slot.was_carried = True
            slot.stop_time_minutes = self.cfg.time_stop_minutes

    def reset_day(self):
        """新的一天，重置状态"""
        for slot in self.slots:
            slot.state = SlotState.EMPTY
            slot.is_open
        self.daily_sell_count = 0
        self.daily_buy_count = 0
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.is_meltdown = False
        self.is_reduced = False
        self.last_sell_time = None
        self.today = date.today().isoformat()

    # ============================================================
    # 统计输出
    # ============================================================

    def daily_summary(self) -> Dict:
        closed = [s for s in self.history if s.open_date == self.today]
        wins = [s for s in closed if s.profit_pct > 0]
        losses = [s for s in closed if s.profit_pct <= 0]
        return {
            "code": self.code,
            "date": self.today,
            "total_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
            "total_pnl": round(self.daily_pnl, 2),
            "avg_win": round(sum(s.profit_pct for s in wins) / len(wins), 2) if wins else 0,
            "avg_loss": round(sum(s.profit_pct for s in losses) / len(losses), 2) if losses else 0,
            "is_meltdown": self.is_meltdown,
            "is_reduced": self.is_reduced,
            "open_slots": len(self.open_slots),
        }

    def status(self) -> str:
        lines = [f"=== {self.code} 槽位状态 | {self.today} ==="]
        lines.append(f"今日: 卖{self.daily_sell_count}笔 买回{self.daily_buy_count}笔 盈亏{self.daily_pnl:+.2f}%")
        if self.is_meltdown: lines.append("  [熔断中]")
        if self.is_reduced: lines.append("  [降仓中]")
        for s in self.slots:
            if s.state == SlotState.EMPTY:
                lines.append(f"  槽{s.id}: 空闲")
            elif s.is_open:
                lines.append(f"  槽{s.id}: 已卖@ {s.open_price:.4f} ({s.open_time}) [跨日]" if s.was_carried else f"  槽{s.id}: 已卖@ {s.open_price:.4f} ({s.open_time})")
            elif s.state == SlotState.CLOSED:
                icon = "+" if s.profit_pct > 0 else "-"
                lines.append(f"  槽{s.id}: 已平 {icon}{s.profit_pct:.2f}%")
        return "\n".join(lines)
