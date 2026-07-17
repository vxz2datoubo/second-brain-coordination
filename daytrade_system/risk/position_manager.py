"""
仓位管理器 — 波仔倒T系统 v2

基于凯利公式和波动率的动态仓位管理
  - 单次T仓上限: 总资金 × 5%
  - 单日亏损熔断: 总资金 × 2%
  - 连续亏损降仓: 连亏2笔 → 当日降为1笔上限
  - 波仔层T回笼法: 优先接回亏损最大的仓位
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date


@dataclass
class PositionConfig:
    """仓位配置"""
    total_capital: float = 100000     # 总资金
    max_pct_per_trade: float = 0.05   # 单笔T仓上限比例
    max_daily_loss_pct: float = 0.02  # 单日最大亏损比例
    max_consecutive_loss: int = 2     # 连续亏损后降仓
    reduced_max_slots: int = 1        # 降仓后槽位上限
    normal_max_slots: int = 3         # 正常槽位上限
    cooldown_minutes: int = 30        # 卖出后禁手时间(分钟)


@dataclass
class DailyState:
    """当日交易状态"""
    date: str = ""
    trade_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    consecutive_losses: int = 0
    total_pnl: float = 0.0
    is_meltdown: bool = False          # 是否触发熔断
    is_reduced: bool = False           # 是否触发降仓
    last_sell_time: str = ""           # 上次卖出时间(用于禁手计时)


class PositionManager:
    """仓位管理器"""

    def __init__(self, config: PositionConfig = None):
        self.config = config or PositionConfig()
        self.daily = DailyState(date=date.today().isoformat())

    def reset_day(self, new_date: str = None):
        """新交易日重置"""
        self.daily = DailyState(date=new_date or date.today().isoformat())

    @property
    def available_slots(self) -> int:
        """当前可用槽位数量"""
        if self.daily.is_meltdown:
            return 0
        if self.daily.is_reduced:
            return self.config.reduced_max_slots
        return self.config.normal_max_slots

    @property
    def max_trade_amount(self) -> float:
        """单笔最大交易金额"""
        return self.config.total_capital * self.config.max_pct_per_trade

    @property
    def max_daily_loss(self) -> float:
        """单日最大亏损金额"""
        return self.config.total_capital * self.config.max_daily_loss_pct

    def check_meltdown(self) -> bool:
        """检查是否触发熔断"""
        if self.daily.total_pnl <= -self.max_daily_loss:
            self.daily.is_meltdown = True
            return True
        return False

    def check_reduction(self) -> bool:
        """检查是否触发降仓"""
        if self.daily.consecutive_losses >= self.config.max_consecutive_loss:
            self.daily.is_reduced = True
            return True
        return False

    def record_trade(self, pnl: float):
        """记录一笔交易"""
        self.daily.trade_count += 1
        self.daily.total_pnl += pnl

        if pnl > 0:
            self.daily.win_count += 1
            self.daily.consecutive_losses = 0
        else:
            self.daily.loss_count += 1
            self.daily.consecutive_losses += 1

        if self.check_meltdown():
            raise RuntimeError(f"触发熔断! 累计亏损{self.daily.total_pnl:+.1f}%超过上限")
        if self.check_reduction():
            self.daily.is_reduced = True

    def can_trade(self) -> tuple:
        """
        是否允许交易
        返回: (是否允许, 原因)
        """
        if self.daily.is_meltdown:
            return False, "🔴 熔断中 — 今日累计亏损超过上限"

        if self.daily.is_reduced:
            if self.daily.trade_count >= self.config.reduced_max_slots:
                return False, "🔴 降仓中 — 已达当日上限"

        if self.daily.trade_count >= self.config.normal_max_slots and not self.daily.is_reduced:
            return False, "⚠️ 已达正常槽位上限3笔"

        return True, "🟢 可以交易"

    def can_sell(self, current_time_str: str) -> tuple:
        """卖出后禁手检查"""
        from datetime import datetime, timedelta

        if not self.daily.last_sell_time:
            return True, ""

        try:
            last = datetime.strptime(self.daily.last_sell_time, "%H:%M")
            now = datetime.strptime(current_time_str, "%H:%M")
            diff = (now - last).total_seconds() / 60
        except ValueError:
            return True, ""

        if diff < self.config.cooldown_minutes:
            remaining = self.config.cooldown_minutes - diff
            return False, f"⏳ 禁手期: {int(remaining)}分钟后可操作"

        return True, ""

    def on_sell(self, time_str: str):
        """记录卖出时间，启动禁手期"""
        self.daily.last_sell_time = time_str

    def status(self) -> str:
        """状态报告"""
        lines = [
            f"\n{'='*30}",
            f"  仓位管理 {self.daily.date}",
            f"{'='*30}",
            f"  总资金: {self.config.total_capital:,.0f}",
            f"  可用槽位: {self.available_slots}/{self.config.normal_max_slots}",
            f"  单笔上限: {self.max_trade_amount:,.0f}",
            f"  日亏上限: {self.max_daily_loss:,.0f}",
            f"  今日交易: {self.daily.trade_count}笔 ({self.daily.win_count}胜{self.daily.loss_count}负)",
            f"  今日盈亏: {self.daily.total_pnl:+.1f}%",
        ]
        if self.daily.is_meltdown:
            lines.append(f"  🚨 熔断中!")
        if self.daily.is_reduced:
            lines.append(f"  ⚠️ 降仓中!")
        if self.daily.last_sell_time:
            lines.append(f"  ⏳ 禁手至: {self.daily.last_sell_time}+{self.config.cooldown_minutes}min")
        lines.append(f"{'='*30}")
        return "\n".join(lines)
