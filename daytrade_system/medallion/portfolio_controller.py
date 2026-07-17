"""portfolio_controller.py — 双股联合持仓控制器

核心职责：
  1. 资金分配：昆仑60% / 蓝色40%
  2. 每日3笔上限在两只股之间动态分配
  3. 优先级：昆仑优先（昆仑更重要，中线配置）
  4. 相关性检测：两只股票同向大幅波动时减少操作
  5. 联合熔断：任意一只亏损严重时，整体降仓

设计原则：
  - 双槽合用一个每日3笔上限
  - 昆仑有优先使用权
  - 蓝色只在昆仑不活跃时占槽
  - 联合止损触发时全部平仓
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import date, datetime

from medallion.config import (
    GLOBAL_MAX_SELL_PER_DAY, GLOBAL_AMOUNT_PER_TRADE,
    STOCK_CONFIGS, PORTFOLIO,
)
from medallion.slot_controller import SlotController, SlotDecision, SlotState


@dataclass
class PortfolioDecision:
    """联合决策输出"""
    action: str          # "sell_kunlun" / "sell_blue" / "buy_back" / "wait" / "all_clear"
    slot_decision: SlotDecision
    reason: str
    priority: str        # "kunlun" / "blue"
    urgency: str          # "high" / "normal" / "low"


class PortfolioController:
    """
    双股联合持仓管理器

    用法：
      pc = PortfolioController()
      decision = pc.evaluate(
          kunlun_controller, blue_controller,
          kunlun_signal, blue_signal,
          kunlun_price, blue_price,
          current_time
      )
      if decision:
          pc.execute(decision)
    """

    def __init__(self):
        # 初始化两个槽位控制器
        self.kunlun = SlotController("300058")
        self.blue   = SlotController("300418")

        # 联合状态
        self.total_sells_today = 0
        self.portfolio_pnl     = 0.0
        self.is_portfolio_meltdown = False
        self.is_red_alert      = False  # 红色警报：两只都跌

        # 优先级队列：昆仑=1，蓝色=2
        self.stock_priority = ["300058", "300418"]

        # 相关性追踪
        self.correlation_window: List[Dict] = []  # 每5分钟记录两只涨跌

        # 跨日仓位
        self.carried_kunlun: List[Dict] = []
        self.carried_blue:   List[Dict] = []

        self.today = date.today().isoformat()

    # ============================================================
    # 核心决策
    # ============================================================

    def evaluate(
        self,
        kunlun_price: float, blue_price: float,
        kunlun_signal_score: float, blue_signal_score: float,
        kunlun_signal_reason: str, blue_signal_reason: str,
        kunlun_prev_close: float, blue_prev_close: float,
        kunlun_open_today: float, blue_open_today: float,
        current_time: str,
    ) -> List[PortfolioDecision]:
        """
        评估双股，决定下一个操作

        Args:
            kunlun_price: 昆仑当前价
            blue_price: 蓝色当前价
            kunlun_signal_score: 昆仑信号分
            blue_signal_score: 蓝色信号分
            kunlun_signal_reason / blue_signal_reason: 信号描述
            kunlun_prev_close / blue_prev_close: 前收盘
            kunlun_open_today / blue_open_today: 今日开盘价
            current_time: "HH:MM"
        """
        decisions: List[PortfolioDecision] = []

        # === 1. 记录相关性数据 ===
        self._track_correlation(kunlun_price, blue_price, kunlun_prev_close, blue_prev_close)

        # === 2. 检查联合止损 ===
        if self._check_portfolio_stop():
            decisions.append(self._make_all_clear_decision())
            return decisions

        # === 3. 检查各自止损（最高优先级）===
        for stock_code, controller, price, prev_close, open_today in [
            ("300058", self.kunlun, kunlun_price, kunlun_prev_close, kunlun_open_today),
            ("300418", self.blue,   blue_price,   blue_prev_close,   blue_open_today),
        ]:
            stock_decisions = controller.check(
                current_price=price,
                current_time=current_time,
                signal_score=0,  # 止损不需要信号
                signal_reason="",
                prev_close=prev_close,
                open_price_today=open_today,
            )
            for sd in stock_decisions:
                if "buy_back" in sd.action:
                    decisions.append(PortfolioDecision(
                        action="buy_back",
                        slot_decision=sd,
                        reason=f"[{controller.cfg.name}] {sd.reason}",
                        priority="kunlun" if stock_code == "300058" else "blue",
                        urgency=sd.urgency,
                    ))

        # === 4. 正常决策：找可执行的开仓机会 ===
        if not decisions:
            decision = self._find_best_entry(
                kunlun_price, blue_price,
                kunlun_signal_score, blue_signal_score,
                kunlun_signal_reason, blue_signal_reason,
                current_time,
            )
            if decision:
                decisions.append(decision)

        # === 5. 检查红色警报 ===
        self._check_red_alert(kunlun_price, blue_price, kunlun_prev_close, blue_prev_close)
        if self.is_red_alert:
            # 红色警报：两只都跌，不开新仓
            decisions = [d for d in decisions if "sell" not in d.action]

        return decisions

    def _track_correlation(self, kl_price, bl_price, kl_prev, bl_prev):
        """追踪两只股票的相关性"""
        kl_chg = (kl_price / kl_prev - 1) * 100 if kl_prev > 0 else 0
        bl_chg = (bl_price / bl_prev - 1) * 100 if bl_prev > 0 else 0

        self.correlation_window.append({
            "time": datetime.now(),
            "kunlun_chg": kl_chg,
            "blue_chg": bl_chg,
        })
        # 只保留最近30分钟窗口
        cutoff = datetime.now().timestamp() - 1800
        self.correlation_window = [
            x for x in self.correlation_window if x["time"].timestamp() > cutoff
        ]

    def _check_portfolio_stop(self) -> bool:
        """联合止损检查"""
        combined_pnl = self.kunlun.daily_pnl + self.blue.daily_pnl
        self.portfolio_pnl = combined_pnl

        # 联合熔断：总亏损>3%
        if combined_pnl <= -3.0:
            self.is_portfolio_meltdown = True
            return True

        # 任意一只触发熔断
        if self.kunlun.is_meltdown or self.blue.is_meltdown:
            return True

        return False

    def _check_red_alert(self, kl_price, bl_price, kl_prev, bl_prev):
        """红色警报：两只都跌，停止开新仓"""
        kl_chg = (kl_price / kl_prev - 1) * 100 if kl_prev > 0 else 0
        bl_chg = (bl_price / bl_prev - 1) * 100 if bl_prev > 0 else 0

        if kl_chg < -1.5 and bl_chg < -1.5:
            self.is_red_alert = True
        else:
            self.is_red_alert = False

    def _find_best_entry(
        self, kl_price, bl_price,
        kl_score, bl_score,
        kl_reason, bl_reason,
        current_time: str,
    ) -> Optional[PortfolioDecision]:
        """找最优开仓机会（优先级：昆仑 > 蓝色）"""

        # 检查全局槽位
        if self.total_sells_today >= GLOBAL_MAX_SELL_PER_DAY:
            return None

        # 有空槽吗？
        kl_can_sell, _ = self.kunlun.can_sell_more()
        bl_can_sell, _ = self.blue.can_sell_more()

        # 昆仑优先级1，蓝色优先级2
        candidates = []

        if kl_can_sell and kl_score >= self.kunlun.cfg.entry_score_threshold:
            candidates.append(("300058", kl_price, kl_score, kl_reason))

        if bl_can_sell and bl_score >= self.blue.cfg.entry_score_threshold:
            candidates.append(("300418", bl_price, bl_score, bl_reason))

        if not candidates:
            return None

        # 选分最高的
        code, price, score, reason = max(candidates, key=lambda x: x[2])

        controller = self.kunlun if code == "300058" else self.blue
        stock_name = controller.cfg.name

        # 通过槽位控制器生成决策
        slot_decision = SlotDecision(
            action="sell_slot1",
            slot_id=1,
            price=price,
            reason=f"[{stock_name}] {reason}",
            urgency="normal",
            limit=False,
        )

        return PortfolioDecision(
            action=f"sell_{'kunlun' if code == '300058' else 'blue'}",
            slot_decision=slot_decision,
            reason=f"{stock_name} 信号{score:.0f}分: {reason}",
            priority="kunlun" if code == "300058" else "blue",
            urgency="normal",
        )

    def _make_all_clear_decision(self) -> PortfolioDecision:
        """联合止损：全部平仓"""
        sd = SlotDecision(
            action="all_clear",
            slot_id=0,
            price=0,
            reason="联合熔断/止损触发",
            urgency="immediate",
            limit=False,
        )
        return PortfolioDecision(
            action="all_clear",
            slot_decision=sd,
            reason=f"联合止损触发，组合亏损{self.portfolio_pnl:.2f}%",
            priority="kunlun",
            urgency="high",
        )

    # ============================================================
    # 执行操作
    # ============================================================

    def execute_sell(self, code: str, price: float, current_time: str,
                     score: float, reason: str):
        """执行卖出"""
        if code == "300058":
            # 找一个空槽
            for slot in self.kunlun.slots:
                if slot.state == SlotState.EMPTY:
                    self.kunlun.execute_sell(slot.id, price, current_time, score, reason)
                    self.total_sells_today += 1
                    return
        else:
            for slot in self.blue.slots:
                if slot.state == SlotState.EMPTY:
                    self.blue.execute_sell(slot.id, price, current_time, score, reason)
                    self.total_sells_today += 1
                    return

    def execute_buy_back(self, code: str, slot_id: int, price: float, current_time: str):
        """执行买回"""
        if code == "300058":
            self.kunlun.execute_buy_back(slot_id, price, current_time)
        else:
            self.blue.execute_buy_back(slot_id, price, current_time)

    def execute_all_clear(self, kl_price: float, bl_price: float, current_time: str):
        """全部清仓"""
        for slot in self.kunlun.open_slots:
            self.kunlun.execute_buy_back(slot.id, kl_price, current_time)
        for slot in self.blue.open_slots:
            self.blue.execute_buy_back(slot.id, bl_price, current_time)
        self.is_portfolio_meltdown = True

    # ============================================================
    # 跨日仓位
    # ============================================================

    def carry_over(self):
        """收盘：记录跨日仓位"""
        self.carried_kunlun = self.kunlun.carry_over()
        self.carried_blue   = self.blue.carry_over()

    def load_carried(self):
        """次日开盘：加载跨日仓位"""
        self.kunlun.load_carried(self.carried_kunlun)
        self.blue.load_carried(self.carried_blue)

    def reset_day(self):
        """新的一天"""
        self.kunlun.reset_day()
        self.blue.reset_day()
        self.total_sells_today = 0
        self.portfolio_pnl = 0.0
        self.is_portfolio_meltdown = False
        self.is_red_alert = False
        self.correlation_window.clear()
        self.today = date.today().isoformat()

    # ============================================================
    # 状态输出
    # ============================================================

    def status(self) -> str:
        lines = [
            f"=== 组合状态 | {self.today} ===",
            f"今日总笔数: {self.total_sells_today}/{GLOBAL_MAX_SELL_PER_DAY}笔",
            f"组合日盈亏: {self.portfolio_pnl:+.2f}%",
            f"联合熔断: {'是' if self.is_portfolio_meltdown else '否'}",
            f"红色警报: {'是' if self.is_red_alert else '否'}",
            "",
        ]
        lines.append(self.kunlun.status())
        lines.append("")
        lines.append(self.blue.status())
        return "\n".join(lines)

    def daily_summary(self) -> Dict:
        return {
            "date": self.today,
            "kunlun": self.kunlun.daily_summary(),
            "blue": self.blue.daily_summary(),
            "total_pnl": round(self.portfolio_pnl, 2),
            "total_sells": self.total_sells_today,
            "meltdown": self.is_portfolio_meltdown,
            "carried_kunlun": len(self.carried_kunlun),
            "carried_blue": len(self.carried_blue),
        }

    def get_signal_readiness(self) -> Dict:
        """返回各股剩余可操作槽位"""
        kl_can, kl_msg = self.kunlun.can_sell_more()
        bl_can, bl_msg = self.blue.can_sell_more()
        return {
            "kunlun": {"can_sell": kl_can, "available": self.kunlun.available_sell_slots, "msg": kl_msg},
            "blue":   {"can_sell": bl_can, "available": self.blue.available_sell_slots, "msg": bl_msg},
            "total_remaining": GLOBAL_MAX_SELL_PER_DAY - self.total_sells_today,
        }
