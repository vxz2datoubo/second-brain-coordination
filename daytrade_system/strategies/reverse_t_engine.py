"""
波仔分层倒T引擎 v2 — 3槽位灵活方向核心策略

核心机制:
  - 3个槽位，每个独立管理一笔倒T操作
  - 买卖顺序不固定（可以全是卖，也可以买→卖→卖）
  - 每个槽位方向独立（可以是SHORT或LONG）
  - 可跨日持有未平仓位

入场决策:
  1. Volume Profile压力带触及 → 卖出信号
  2. 量价效率分析 → 硬阻力优先卖出
  3. 日线趋势 → 下跌趋势中大胆卖
  4. 入市评分卡 → 综合评分确认
  5. 情绪追踪 → 贪婪时多卖

出场决策:
  - 价格回落至卖出价以下 → 接回（波仔层T回笼法）
  - 价格触及强支撑带 → 即使未到卖出价也接回
  - 跨日：次日低开优先接回

使用方式:
  engine = ReverseTEngine("300418", "昆仑万维", base_position=1000)
  engine.update_price(40.50, 40.10)  # (现价, 均价)
  decision = engine.check_entries()
  if decision.should_act:
      执行 decision.action at decision.price
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, date
from enum import Enum

from strategies.volume_profile import find_support_resistance
from strategies.volume_efficiency import reverse_t_ranking
from strategies.entry_scorer import EntryScorer


class SlotState(Enum):
    EMPTY = "empty"         # 空槽
    SHORT = "short"         # 已卖出，等待接回
    LONG = "long"           # 已买入，等待卖出
    DONE = "done"           # 已完成

@dataclass
class TSlot:
    """一个T仓位槽"""
    id: int
    state: SlotState = SlotState.EMPTY
    open_price: float = 0.0      # 开仓价
    open_date: str = ""          # 开仓日期 YYYY-MM-DD
    direction: str = ""          # "short"(先卖=倒T) 或 "long"(先买=正T)
    target_price: float = 0.0    # 目标接回价
    stop_loss: float = 0.0       # 止损价
    efficiency: float = 0.0      # 卖出时的量价效率

    @property
    def is_open(self):
        return self.state in (SlotState.SHORT, SlotState.LONG)

    def unrealized_pnl(self, current_price: float = 0) -> float:
        """浮动盈亏%"""
        if not self.is_open or self.open_price == 0:
            return 0
        if self.direction == "short":
            return (self.open_price / current_price - 1) * 100 if current_price > 0 else 0
        else:
            return (current_price / self.open_price - 1) * 100 if self.open_price > 0 else 0


@dataclass
class EngineDecision:
    """引擎输出决策"""
    should_act: bool = False
    action: str = ""          # "sell_slot1" "sell_slot2" "sell_slot3" "buy_back_slot1" ...
    price: float = 0.0
    slot_id: int = 0
    reason: str = ""
    score: float = 0.0        # 决策评分


class ReverseTEngine:
    """3槽位倒T核心引擎"""

    MAX_SLOTS = 3
    MAX_SHORT_SLOTS = 3       # 最多3个卖出槽位
    MIN_PROFIT_PCT = 0.3      # 最小盈利目标%

    def __init__(self, code: str, name: str = "", base_shares: int = 1000):
        self.code = code
        self.name = name
        self.base_shares = base_shares  # 底仓股数
        self.slots = [TSlot(id=i + 1) for i in range(self.MAX_SLOTS)]
        self.today = date.today().isoformat()
        self.history = []  # 完成的交易历史

        # 盘中状态
        self.current_price = 0.0
        self.avg_price = 0.0
        self.day_high = 0.0
        self.day_low = 0.0

        # 跨日持仓追踪
        self.carried_slots = []  # 从昨天转入的槽位

    # ============================================================
    # 仓位查询
    # ============================================================

    @property
    def open_short_slots(self) -> List[TSlot]:
        return [s for s in self.slots if s.state == SlotState.SHORT]

    @property
    def open_long_slots(self) -> List[TSlot]:
        return [s for s in self.slots if s.state == SlotState.LONG]

    @property
    def empty_slots(self) -> List[TSlot]:
        return [s for s in self.slots if s.state == SlotState.EMPTY]

    @property
    def open_count(self) -> int:
        return len(self.open_short_slots) + len(self.open_long_slots)

    @property
    def all_open_slots(self) -> List[TSlot]:
        return self.open_short_slots + self.open_long_slots

    # ============================================================
    # 盘中更新
    # ============================================================

    def update_price(self, current: float, avg: float, high: float = 0, low: float = 0):
        """更新盘中价格"""
        self.current_price = current
        self.avg_price = avg
        self.day_high = high or current
        self.day_low = low or current

    # ============================================================
    # 入场决策：是否开新卖出仓位
    # ============================================================

    def check_entry(self) -> EngineDecision:
        """
        检查是否应该开仓（卖出）
        综合5个维度评分
        """
        if not self.empty_slots:
            return EngineDecision(should_act=False, reason="所有槽位已满")

        # 1. Volume Profile — 是否在压力带附近
        support, resistance = find_support_resistance(self.code, self.current_price, days=5)

        near_resistance = False
        nearest_r = resistance[0] if resistance else None
        dist_to_r = 0

        if nearest_r:
            r_mid = (nearest_r["price_min"] + nearest_r["price_max"]) / 2
            dist_to_r = (r_mid / self.current_price - 1) * 100
            if dist_to_r <= 1.5:  # 距压力带1.5%以内
                near_resistance = True

        # 2. 量价效率 — 该压力带是硬阻力还是软阻力
        ranking = reverse_t_ranking(self.code, self.current_price, days=5, top_n=3)
        top_target = ranking[0] if ranking else None
        efficiency = top_target["avg_efficiency"] if top_target else 0
        hardness = top_target["hardness"] if top_target else "未知"

        # 3. 入市评分卡
        scorer = EntryScorer(self.code, self.name)
        scorer.add_volume_profile(self.current_price)
        # 资金/情绪/板块数据需要外部注入，此处简化
        entry_verdict = scorer.verdict()

        # 综合决策
        reasons = []

        if not near_resistance and dist_to_r > 3:
            return EngineDecision(should_act=False, reason=f"距最近压力带{dist_to_r:.1f}%，太远不适合卖出")

        if efficiency < 0.8:
            reasons.append(f"{hardness}(效率{efficiency:.1f}x)，不值得卖")
        else:
            reasons.append(f"{hardness}(效率{efficiency:.1f}x)")

        if near_resistance:
            reasons.append(f"距压力带{dist_to_r:.1f}%")

        # 入场评分
        total_score = self._calc_entry_score(dist_to_r, efficiency)

        if total_score >= 60:
            # 选一个空槽
            slot = self.empty_slots[0]
            target_p = nearest_r["price_min"] if nearest_r else self.current_price * 1.02

            return EngineDecision(
                should_act=True,
                action=f"sell_slot{slot.id}",
                price=self.current_price,
                slot_id=slot.id,
                reason=" | ".join(reasons),
                score=total_score,
            )

        return EngineDecision(should_act=False, reason=" | ".join(reasons) + f" (评分{total_score}，需≥60)")

    def _calc_entry_score(self, dist_to_r: float, efficiency: float) -> float:
        """计算入场评分(0-100)"""
        score = 0

        # 距离分（越近分越高）
        if dist_to_r <= 0.5:   score += 35
        elif dist_to_r <= 1.0: score += 25
        elif dist_to_r <= 1.5: score += 15
        else:                  score += 5

        # 效率分（效率越高阻力越硬）
        if efficiency >= 3:    score += 35
        elif efficiency >= 2:  score += 25
        elif efficiency >= 1.5: score += 15
        elif efficiency >= 1:  score += 10

        # 仓位分（空槽越多分越高）
        empty = len(self.empty_slots)
        score += empty * 10

        return min(score, 100)

    # ============================================================
    # 出场决策：是否接回已卖出的仓位
    # ============================================================

    def check_exit(self) -> List[EngineDecision]:
        """
        检查是否应该接回
        按波仔层T回笼法：优先接回亏损最大的那笔
        """
        decisions = []
        shorts = self.open_short_slots
        if not shorts:
            return decisions

        support, _ = find_support_resistance(self.code, self.current_price, days=5)

        # 按波仔层T回笼法排序：open_price最高的（亏损最大）优先
        shorts.sort(key=lambda s: -s.open_price)

        for slot in shorts:
            pnl = slot.unrealized_pnl(self.current_price)

            # 条件1: 价格已回落到卖出价以下
            if self.current_price <= slot.open_price:
                decisions.append(EngineDecision(
                    should_act=True,
                    action=f"buy_back_slot{slot.id}",
                    price=self.current_price,
                    slot_id=slot.id,
                    reason=f"价格回落至卖出价{slot.open_price:.2f}以下 (盈亏{pnl:+.1f}%)",
                ))
                continue

            # 条件2: 价格触及强支撑带
            if support:
                nearest_s = support[0]
                s_mid = (nearest_s["price_min"] + nearest_s["price_max"]) / 2
                if self.current_price <= s_mid * 1.01:
                    decisions.append(EngineDecision(
                        should_act=True,
                        action=f"buy_back_slot{slot.id}",
                        price=self.current_price,
                        slot_id=slot.id,
                        reason=f"触及强支撑带{s_mid:.2f} (盈亏{pnl:+.1f}%)",
                    ))
                    continue

            # 条件3: 跨日持仓，低开止损（对齐硬止损-2%标准）
            if slot.open_date != self.today and self.current_price > slot.open_price * 1.02:
                decisions.append(EngineDecision(
                    should_act=True,
                    action=f"buy_back_slot{slot.id}",
                    price=self.current_price,
                    slot_id=slot.id,
                    reason=f"跨日硬止损(>{slot.open_price*1.02:.2f}) (盈亏{pnl:+.1f}%)",
                ))

        return decisions

    # ============================================================
    # 槽位操作
    # ============================================================

    def open_short(self, slot_id: int, price: float, efficiency: float = 0) -> TSlot:
        """开一个卖出仓位"""
        slot = self.slots[slot_id - 1]
        slot.state = SlotState.SHORT
        slot.open_price = price
        slot.open_date = self.today
        slot.direction = "short"
        slot.efficiency = efficiency
        # 止损设在上方2%（与架构文档一致）
        slot.stop_loss = price * 1.02
        slot.target_price = price * 0.98  # 目标赚2%
        return slot

    def open_long(self, slot_id: int, price: float) -> TSlot:
        """开一个买入仓位（正T方向）"""
        slot = self.slots[slot_id - 1]
        slot.state = SlotState.LONG
        slot.open_price = price
        slot.open_date = self.today
        slot.direction = "long"
        slot.stop_loss = price * 0.98
        slot.target_price = price * 1.02
        return slot

    def close_slot(self, slot_id: int, price: float) -> dict:
        """平仓一个槽位，返回交易记录"""
        slot = self.slots[slot_id - 1]
        if not slot.is_open:
            return None

        if slot.direction == "short":
            profit = (slot.open_price / price - 1) * 100
        else:
            profit = (price / slot.open_price - 1) * 100

        record = {
            "slot": slot_id,
            "direction": slot.direction,
            "open_price": slot.open_price,
            "close_price": price,
            "profit_pct": round(profit, 2),
            "open_date": slot.open_date,
            "close_date": self.today,
            "efficiency": slot.efficiency,
        }

        slot.state = SlotState.DONE
        self.history.append(record)
        return record

    # ============================================================
    # 跨日管理
    # ============================================================

    def end_of_day(self):
        """日终：将未平仓位标记为跨日"""
        self.carried_slots = []
        for slot in self.all_open_slots:
            self.carried_slots.append({
                "id": slot.id,
                "state": slot.state.value,
                "open_price": slot.open_price,
                "open_date": slot.open_date,
                "direction": slot.direction,
                "stop_loss": slot.stop_loss,
            })
        return self.carried_slots

    def load_carried(self, carried: list):
        """次日开盘加载跨日仓位"""
        for c in carried:
            slot = self.slots[c["id"] - 1]
            slot.state = SlotState(c["state"])
            slot.open_price = c["open_price"]
            slot.open_date = c["open_date"]
            slot.direction = c["direction"]
            slot.stop_loss = c.get("stop_loss", c["open_price"] * 1.02)

    # ============================================================
    # 综合决策
    # ============================================================

    def comprehensive_check(self, position_manager=None, time_str="") -> List[EngineDecision]:
        """
        完整检查：先检查出场，再检查入场
        波仔层T回笼法优先——先处理旧仓再开新仓
        
        新增风控:
        - 涨停板检查：涨停不卖（可能封板）
        - 跌停板检查：跌停不买（可能继续跌）
        - 禁手期检查：卖出后30分钟内不得再操作
        """
        decisions = []

        # === 板检查 ===
        if position_manager:
            can_trade, reason = position_manager.can_trade()
            if not can_trade:
                return [EngineDecision(should_act=False, reason=f"风控拦截: {reason}")]

        # 1. 先检查是否有仓位需要接回
        exit_decisions = self.check_exit()
        if exit_decisions:
            decisions.extend(exit_decisions)

        # 2. 如果没有需要出场的，检查是否可以开新仓
        if not exit_decisions and self.open_count < self.MAX_SLOTS:
            # 禁手检查
            if position_manager and time_str:
                can_sell, msg = position_manager.can_sell(time_str)
                if not can_sell:
                    return [EngineDecision(should_act=False, reason=msg)]

            entry = self.check_entry()
            if entry.should_act:
                decisions.append(entry)

        return decisions

    # ============================================================
    # 报告输出
    # ============================================================

    def status_report(self) -> str:
        """槽位状态报告"""
        lines = [f"\n{'='*40}"]
        lines.append(f"  {self.name}({self.code}) 倒T引擎")
        lines.append(f"  现价: {self.current_price:.2f}  均价: {self.avg_price:.2f}")
        lines.append(f"{'='*40}")

        for slot in self.slots:
            if slot.state == SlotState.EMPTY:
                lines.append(f"  槽{slot.id}: ⬜ 空")
            elif slot.state == SlotState.SHORT:
                pnl = slot.unrealized_pnl(self.current_price)
                icon = "🟢" if pnl > 0 else "🔴"
                lines.append(f"  槽{slot.id}: 🔻 卖{slot.open_price:.2f} ({slot.open_date}) {icon}{pnl:+.1f}%")
            elif slot.state == SlotState.LONG:
                pnl = slot.unrealized_pnl(self.current_price)
                icon = "🟢" if pnl > 0 else "🔴"
                lines.append(f"  槽{slot.id}: 🔺 买{slot.open_price:.2f} ({slot.open_date}) {icon}{pnl:+.1f}%")
            elif slot.state == SlotState.DONE:
                lines.append(f"  槽{slot.id}: ✅ 完成")

        lines.append(f"{'='*40}")

        # 已平仓统计
        if self.history:
            today_trades = [h for h in self.history if h["close_date"] == self.today]
            if today_trades:
                total_pnl = sum(h["profit_pct"] for h in today_trades)
                lines.append(f"  今日战绩: {len(today_trades)}笔, 合计{total_pnl:+.1f}%")

        return "\n".join(lines)
