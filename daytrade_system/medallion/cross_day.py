"""cross_day.py — 跨日仓位管理器

核心问题：跨多少天最优？
  - 跨日太久：持仓风险大（如ARR新闻突袭导致继续涨）
  - 跨日太短：错过大机会（如低开后连续上涨）
  → 解决方案：通过历史回测找最优持有天数，自动校准

策略：
  - 跨日仓：次日开盘后立即判断
    - 大跌（>-1%）→ 立即接回锁定利润
    - 大涨（>+1%）→ 止损接回
    - 小幅波动 → 最多持有N天（N由回测决定）
  - 回测找最优跨日参数：
    - 测试持有一天、两天、三天的收益分布
    - 选择胜率×平均收益最高的组合
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from engine.indicators import KBar


@dataclass
class CrossDayConfig:
    """跨日配置（由回测自动校准）"""
    max_carry_days: int = 1       # 最长持有天数
    flee_pct: float = 2.0         # 飞逃%
    emergency_carry_days: int = 3  # 极端行情最长持有
    carry_win_rate: float = 0.0   # 跨日胜率（回测得出）
    carry_avg_profit: float = 0.0  # 跨日平均收益


class CrossDayManager:
    """
    跨日仓位管理器
    
    使用方法：
      mgr = CrossDayManager("300418")
      mgr.load_history(cross_day_trades)  # 加载历史跨日数据
      best_config = mgr.optimize()        # 回测找最优参数
      mgr.apply_config(best_config)       # 应用最优配置
    """

    def __init__(self, code: str):
        self.code = code
        self.config = CrossDayConfig()
        self.history: List[Dict] = []  # 历史跨日交易记录
        self.stats_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", f"cross_day_{code}.json"
        )
        self._load_stats()

    def _load_stats(self):
        """从文件加载历史统计"""
        if os.path.exists(self.stats_path):
            try:
                with open(self.stats_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config = CrossDayConfig(**data.get("best_config", {}))
                    self.history = data.get("history", [])
            except Exception:
                pass

    def _save_stats(self):
        """保存统计到文件"""
        os.makedirs(os.path.dirname(self.stats_path), exist_ok=True)
        data = {
            "best_config": {
                "max_carry_days": self.config.max_carry_days,
                "flee_pct": self.config.flee_pct,
                "emergency_carry_days": self.config.emergency_carry_days,
                "carry_win_rate": self.config.carry_win_rate,
                "carry_avg_profit": self.config.carry_avg_profit,
            },
            "history": self.history[-500:],  # 只保留最近500条
        }
        with open(self.stats_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_trade(self, entry_date: str, entry_price: float,
                     exit_date: str, exit_price: float,
                     carry_days: int, profit_pct: float,
                     reason: str = ""):
        """记录一笔跨日交易"""
        self.history.append({
            "entry_date": entry_date,
            "entry_price": entry_price,
            "exit_date": exit_date,
            "exit_price": exit_price,
            "carry_days": carry_days,
            "profit_pct": round(profit_pct, 3),
            "reason": reason,
        })

    def optimize(self) -> CrossDayConfig:
        """
        通过历史数据找最优跨日参数
        
        评估维度：
          1. 不同持有天数(1/2/3天)的胜率
          2. 不同持有天数的平均收益
          3. 综合得分 = 胜率 × (1 + 平均收益)
        """
        if len(self.history) < 20:
            # 数据不够，用默认值
            return self.config

        # 按持有天数分组统计
        carry_stats = {}
        for days in [1, 2, 3, 4, 5]:
            trades = [h for h in self.history if h["carry_days"] == days]
            if len(trades) < 3:
                continue
            wins = [t for t in trades if t["profit_pct"] > 0]
            avg_pnl = sum(t["profit_pct"] for t in trades) / len(trades)
            win_rate = len(wins) / len(trades)
            score = win_rate * (1 + avg_pnl)
            carry_stats[days] = {
                "count": len(trades),
                "win_rate": win_rate,
                "avg_profit": avg_pnl,
                "score": score,
            }

        if not carry_stats:
            return self.config

        # 选综合得分最高的
        best_days = max(carry_stats.keys(), key=lambda d: carry_stats[d]["score"])
        self.config.max_carry_days = best_days
        self.config.carry_win_rate = carry_stats[best_days]["win_rate"]
        self.config.carry_avg_profit = carry_stats[best_days]["avg_profit"]

        self._save_stats()
        return self.config

    def should_carry(self, entry_price: float, current_price: float,
                     carried_days: int, prev_close: float = None,
                     open_price_today: float = None) -> Dict:
        """
        判断是否应该继续持有
        
        Returns:
          {"action": "buy_back" / "hold", "reason": "...", "urgency": "high/normal/low"}
        """
        pnl_pct = (entry_price / current_price - 1) * 100

        # 超出最大持有天数 → 必须接回
        if carried_days >= self.config.emergency_carry_days:
            return {
                "action": "buy_back",
                "reason": f"已达最大持有{self.config.emergency_carry_days}天",
                "urgency": "high",
            }

        # 飞逃检查
        if pnl_pct <= -self.config.flee_pct:
            return {
                "action": "buy_back",
                "reason": f"亏损{pnl_pct:.2f}% ≥ {self.config.flee_pct}%，飞逃",
                "urgency": "high",
            }

        # 开盘处理（跨日仓位特有）
        if open_price_today and prev_close:
            gap_pct = (open_price_today / prev_close - 1) * 100

            if gap_pct < -1.5:
                # 开盘大跌：锁定利润
                return {
                    "action": "buy_back",
                    "reason": f"开盘大跌{gap_pct:.1f}%，锁定利润",
                    "urgency": "high",
                }
            elif gap_pct > 1.5:
                # 开盘大涨：止损
                return {
                    "action": "buy_back",
                    "reason": f"开盘大涨{gap_pct:.1f}%，止损",
                    "urgency": "high",
                }
            elif gap_pct < -0.5 and pnl_pct > 0.3:
                # 开盘小幅下跌但有利润：可接回
                return {
                    "action": "buy_back",
                    "reason": f"开盘下跌{gap_pct:.1f}%，利润{pnl_pct:.2f}%，接回",
                    "urgency": "normal",
                }

        # 正常持有
        return {
            "action": "hold",
            "reason": f"正常持有{carried_days}天，当前{pnl_pct:+.2f}%",
            "urgency": "low",
        }

    def format_report(self) -> str:
        """格式化跨日统计报告"""
        if not self.history:
            return f"{self.code} 暂无跨日历史数据"

        lines = [f"=== {self.code} 跨日仓位统计 ==="]
        lines.append(f"最优持有天数: {self.config.max_carry_days}天")
        lines.append(f"历史跨日交易: {len(self.history)}笔")
        lines.append(f"跨日胜率: {self.config.carry_win_rate:.1%}")
        lines.append(f"跨日平均收益: {self.config.carry_avg_profit:+.3f}%")
        lines.append("")

        # 按天数分组
        carry_stats = {}
        for days in [1, 2, 3, 4, 5]:
            trades = [h for h in self.history if h["carry_days"] == days]
            if trades:
                wins = [t for t in trades if t["profit_pct"] > 0]
                carry_stats[days] = {
                    "count": len(trades),
                    "win_rate": len(wins) / len(trades),
                    "avg_profit": sum(t["profit_pct"] for t in trades) / len(trades),
                }

        if carry_stats:
            lines.append("各持有天数表现：")
            for days, stats in sorted(carry_stats.items()):
                star = " ★" if days == self.config.max_carry_days else ""
                lines.append(f"  {days}天: {stats['count']}笔 胜率{stats['win_rate']:.0%} 均收益{stats['avg_profit']:+.3f}%{star}")

        return "\n".join(lines)
