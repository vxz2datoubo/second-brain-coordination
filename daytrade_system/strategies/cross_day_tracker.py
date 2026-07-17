"""
跨日仓位追踪器 — 波仔倒T系统 v2

管理不同交易日之间的仓位衔接:
  - 日终保存未平仓位到JSON
  - 次日开盘自动加载
  - 开盘判断：低开优先接回、高开等待回落
"""

import json
import os
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


class CrossDayTracker:
    """跨日仓位管理"""

    def __init__(self, code: str):
        self.code = code
        self.filepath = DATA_DIR / f"positions_{code}.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def save(self, carried_slots: list) -> dict:
        """
        保存日终未平仓位
        carried_slots: [{"id":1, "state":"short", "open_price":40.50, ...}]
        """
        data = {
            "code": self.code,
            "saved_date": date.today().isoformat(),
            "slots": carried_slots,
        }
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    def load(self) -> dict:
        """加载昨日未平仓位"""
        if not self.filepath.exists():
            return {"slots": [], "saved_date": ""}

        with open(self.filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def has_carried(self) -> bool:
        """是否有跨日持仓"""
        data = self.load()
        return len(data.get("slots", [])) > 0

    def clear(self):
        """清除跨日持仓文件"""
        if self.filepath.exists():
            self.filepath.unlink()

    def morning_check(self, current_price: float, prev_close: float) -> dict:
        """
        次日开盘时的跨日仓位检查
        返回建议操作

        逻辑:
          - 低开 > 1%: 优先接回（盈利扩大）
          - 高开 > 1%: 等待回落
          - 平开: 按正常策略
        """
        data = self.load()
        slots = data.get("slots", [])

        if not slots:
            return {"action": "无跨日仓位", "decisions": []}

        open_chg = (current_price / prev_close - 1) * 100
        decisions = []

        for s in slots:
            if s["state"] != "short":
                continue

            profit = (s["open_price"] / current_price - 1) * 100

            if open_chg < -1.0:
                decisions.append({
                    "slot_id": s["id"],
                    "action": "buy_back_now",
                    "price": current_price,
                    "reason": f"低开{open_chg:+.1f}%，跨日仓位盈利{profit:+.1f}%",
                })
            elif open_chg > 1.0:
                decisions.append({
                    "slot_id": s["id"],
                    "action": "wait",
                    "price": s["open_price"],
                    "reason": f"高开{open_chg:+.1f}%，等待回落到{s['open_price']:.2f}再接",
                })
            else:
                decisions.append({
                    "slot_id": s["id"],
                    "action": "normal",
                    "price": s["open_price"],
                    "reason": f"平开，按正常策略，目标接回价{s['open_price']:.2f}",
                })

        return {
            "code": self.code,
            "saved_date": data.get("saved_date", ""),
            "open_chg_pct": round(open_chg, 1),
            "action": "buy_back_all" if open_chg < -1 else "normal",
            "decisions": decisions,
        }
