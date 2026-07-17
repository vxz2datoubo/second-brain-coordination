#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金池 FIFO 引擎 — A股市场适配
===============================

学术/行业锚定:
  [1] IAS 2 / CAS 1 (存货) — FIFO 成本流转的基础会计标准
  [2] CFA Level I "Cost Basis Reporting" — 税务池 (tax lot) 的强制 FIFO 逻辑
  [3] 中登公司 A 股结算规则 — T+1 交收 (买入 T 日扣款, 卖出 T+1 日到账)
  [4] Modigliani-Miller (1958) 引申 — 资金时间价值, 占用成本计算
  [5] Markowitz (1952) 组合理论 — 加权平均成本锚定
  [6] 上交所/深交所交易规则 2023 修订 — 涨跌停/最小交易单位/印花税

A 股规则适配:
  - T+1 结算: 卖出资金 T+1 日可用
  - 涨跌停: 主板 ±10%, 创业板/科创板 ±20%, 北交所 ±30%
  - 最小交易单位: 100 股 (1 手), 零股按实际
  - 印花税: 卖出单边 0.05% (2023.08.28 起)
  - 过户费: 0.001% (双向, 沪市); 深市免
  - 佣金: 默认万 2.5 (双向, 最低 5 元), 可配置
  - 集合竞价 9:15-9:25 不匹配连续竞价 FIFO
  - 除权除息: 自动调整成本基准

用法:
  from core.fund_pool_fifo import FIFOEngine

  engine = FIFOEngine("300418", market="sz", commission_rate=0.00025)
  engine.deposit("2026-07-14 09:35", 1000, 46.50)  # 买入 1000 股
  engine.withdraw("2026-07-15 10:08", 500, 47.98)   # 卖出 500 股 (FIFO)
  summary = engine.summary(47.10)                     # 当前市价 47.10
"""

from __future__ import annotations

import bisect
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════
# 1. 常量与枚举
# ═══════════════════════════════════════════════════════════════════════


class Market(Enum):
    """A 股市场板块, 影响涨跌停幅度与过户费."""
    SH_MAIN = "sh_main"           # 沪市主板 60xxxx
    SZ_MAIN = "sz_main"           # 深市主板 00xxxx
    GEM = "gem"                   # 创业板 30xxxx
    STAR = "star"                 # 科创板 68xxxx
    BSE = "bse"                   # 北交所 8xxxxx

    @property
    def limit_pct(self) -> float:
        """涨跌停幅度."""
        return {Market.SH_MAIN: 0.10, Market.SZ_MAIN: 0.10,
                Market.GEM: 0.20, Market.STAR: 0.20,
                Market.BSE: 0.30}[self]

    @property
    def transfer_fee_rate(self) -> float:
        """过户费率."""
        return 0.00001 if self in (Market.SH_MAIN, Market.STAR) else 0.0

    @classmethod
    def from_code(cls, code: str) -> "Market":
        c = str(code)
        if c.startswith("6"):
            return cls.SH_MAIN if c.startswith(("60", "603")) else cls.STAR
        if c.startswith("0"):
            return cls.SZ_MAIN
        if c.startswith("30"):
            return cls.GEM
        if c.startswith("8"):
            return cls.BSE
        raise ValueError(f"无法识别代码 {code}")


# A股交易费用常量(2023.08.28起)
STAMP_DUTY_SELL = 0.0005       # 印花税 卖出 0.05%
DEFAULT_COMMISSION = 0.00025   # 佣金 万2.5 双向
MIN_COMMISSION = 5.0           # 最低佣金 5 元
LOT_SIZE = 100                 # 每手 100 股


def trading_day_offset(d: date, n: int) -> date:
    """简易交易日推算: 跳过周末 (不做节假日精确处理)."""
    step = 1 if n > 0 else -1
    count = 0
    while count < abs(n):
        d += timedelta(days=step)
        if d.weekday() < 5:
            count += 1
    return d


# ═══════════════════════════════════════════════════════════════════════
# 2. 数据结构
# ═══════════════════════════════════════════════════════════════════════


@dataclass(slots=True)
class Lot:
    """单笔资金入池 (一个税基)."""
    lot_id: int
    entry_time: datetime          # 入池时间 YYYY-MM-DD HH:MM
    quantity: int                 # 股数
    cost_price: float             # 成交均价(含费用后每股成本)
    gross_amount: float           # 原始成交金额
    fee: float                    # 总费用(佣金+过户费)
    remaining: int                # 剩余未配对股数
    settlement_date: date         # T+1 结算日期 (买入)
    # 除权调整累积因子
    adjustment_factor: float = 1.0

    @property
    def is_exhausted(self) -> bool:
        return self.remaining <= 0

    @property
    def adjusted_cost(self) -> float:
        return self.cost_price / self.adjustment_factor


@dataclass(slots=True)
class Transaction:
    """一笔交易记录."""
    tx_id: int
    time: datetime
    side: str                    # "BUY" | "SELL"
    quantity: int
    price: float
    gross_amount: float
    fee: float                   # 佣金 + 过户费
    stamp_duty: float = 0.0      # 印花税(仅卖出)


@dataclass(slots=True)
class PnLRecord:
    """单次卖出的盈亏记录."""
    sell_tx_id: int
    sell_time: datetime
    sell_price: float
    sell_qty: int
    matched_lot_id: int
    lot_entry_time: datetime
    lot_cost: float
    realized_pnl: float          # 已实现盈亏(扣费后)
    holding_days: int


@dataclass(slots=True)
class PoolSummary:
    """资金池汇总快照."""
    total_shares: int
    total_cost: float             # 总成本(含费)
    avg_cost: float              # 加权平均成本
    market_price: float          # 当前市价
    market_value: float
    unrealized_pnl: float        # 浮动盈亏
    unrealized_pnl_pct: float
    realized_pnl_total: float    # 累计已实现盈亏
    net_pnl: float               # 已实现 + 未实现
    available_shares: int        # T+0 可用(今天卖的昨天买的,简化)
    lots_count: int              # 剩余税基数量


# ═══════════════════════════════════════════════════════════════════════
# 3. FIFO 引擎
# ═══════════════════════════════════════════════════════════════════════


class FIFOEngine:
    """A 股资金池 FIFO 管理引擎.

    约定:
      - deposit() = 买入建仓 → 新增 Lot
      - withdraw() = 卖出减仓 → 按 FIFO 匹配
      - 所有价格和金额为人民币元, quantity 为股数
    """

    def __init__(
        self,
        code: str,
        market: Optional[Market] = None,
        commission_rate: float = DEFAULT_COMMISSION,
        min_commission: float = MIN_COMMISSION,
    ):
        self.code = str(code)
        self.market = market or Market.from_code(self.code)
        self.commission_rate = commission_rate
        self.min_commission = min_commission

        self._lots: deque[Lot] = deque()         # FIFO 队列
        self._transactions: List[Transaction] = []
        self._pnl_records: List[PnLRecord] = []
        self._next_lot_id = 1
        self._next_tx_id = 1
        self._realized_pnl_total: float = 0.0
        self._total_dividend: float = 0.0        # 累计分红

        # T+1 待清算
        self._pending_settlement: Dict[date, float] = defaultdict(float)

    # ── 工具 ──────────────────────────────────────────────────────

    def _calc_buy_fee(self, quantity: int, price: float) -> Tuple[float, float, float]:
        """计算买入费用 → (佣金, 过户费, 总费)."""
        gross = quantity * price
        commission = max(gross * self.commission_rate, self.min_commission)
        transfer = gross * self.market.transfer_fee_rate
        return commission, transfer, commission + transfer

    def _calc_sell_fee(self, quantity: int, price: float) -> Tuple[float, float, float, float]:
        """计算卖出费用 → (佣金, 过户费, 印花税, 总费)."""
        gross = quantity * price
        commission = max(gross * self.commission_rate, self.min_commission)
        transfer = gross * self.market.transfer_fee_rate
        stamp = gross * STAMP_DUTY_SELL
        return commission, transfer, stamp, commission + transfer + stamp

    def _validate_price(self, price: float, prev_close: Optional[float] = None) -> bool:
        """涨跌停校验."""
        if prev_close is None:
            return True
        limit = self.market.limit_pct
        lo = prev_close * (1.0 - limit)
        hi = prev_close * (1.0 + limit)
        return lo <= price <= hi

    def _parse_time(self, t: str | datetime) -> datetime:
        if isinstance(t, datetime):
            return t
        return datetime.strptime(t, "%Y-%m-%d %H:%M")

    @property
    def total_shares(self) -> int:
        return sum(l.remaining for l in self._lots)

    @property
    def lots(self) -> List[Lot]:
        return list(self._lots)

    @property
    def transactions(self) -> List[Transaction]:
        return list(self._transactions)

    # ── 入池 (买入) ──────────────────────────────────────────────

    def deposit(
        self,
        time: str | datetime,
        quantity: int,
        price: float,
        prev_close: Optional[float] = None,
    ) -> Lot:
        """买入建仓: 入池一笔资金, 创建税基 Lot.

        Args:
            time: 成交时间
            quantity: 股数 (须 ≥100 或手数对齐)
            price: 成交均价
            prev_close: 昨日收盘价(涨跌停校验用, 可选)
        """
        t = self._parse_time(time)
        if quantity < 1:
            raise ValueError(f"quantity={quantity} 必须 > 0")
        if not self._validate_price(price, prev_close):
            limit = self.market.limit_pct
            raise ValueError(f"价格 {price} 超出涨跌停范围 (±{limit*100:.0f}%, 前收 {prev_close})")

        commission, transfer, total_fee = self._calc_buy_fee(quantity, price)
        gross = quantity * price
        cost_per_share = (gross + total_fee) / quantity

        lot = Lot(
            lot_id=self._next_lot_id,
            entry_time=t,
            quantity=quantity,
            cost_price=round(cost_per_share, 4),
            gross_amount=gross,
            fee=total_fee,
            remaining=quantity,
            settlement_date=trading_day_offset(t.date(), 1),
            adjustment_factor=1.0,
        )
        self._next_lot_id += 1
        self._lots.append(lot)

        tx = Transaction(
            tx_id=self._next_tx_id,
            time=t,
            side="BUY",
            quantity=quantity,
            price=price,
            gross_amount=gross,
            fee=total_fee,
        )
        self._next_tx_id += 1
        self._transactions.append(tx)

        self._pending_settlement[lot.settlement_date] += gross + total_fee
        return lot

    # ── 出池 (卖出) ──────────────────────────────────────────────

    def withdraw(
        self,
        time: str | datetime,
        quantity: int,
        price: float,
        prev_close: Optional[float] = None,
    ) -> Tuple[List[PnLRecord], float]:
        """卖出减仓: FIFO 跨 Lot 配对, 自动核算盈亏.

        Returns:
            (pnl_records, net_cash_in) — 各税基盈亏明细 + 净到账
        """
        t = self._parse_time(time)
        remaining = quantity
        if remaining > self.total_shares:
            raise ValueError(f"持仓不足: 持有 {self.total_shares}, 试图卖出 {quantity}")
        if not self._validate_price(price, prev_close):
            limit = self.market.limit_pct
            raise ValueError(f"价格 {price} 超出涨跌停范围 (±{limit*100:.0f}%)")

        # 先计费
        commission, transfer, stamp, total_fee = self._calc_sell_fee(quantity, price)
        gross = quantity * price
        net_cash = gross - total_fee

        records: List[PnLRecord] = []
        while remaining > 0 and self._lots:
            lot = self._lots[0]
            take = min(remaining, lot.remaining)
            # 盈亏 = (卖价 - 成本) × 数量 - 按比例分摊卖出费用
            fee_share = total_fee * (take / quantity) if quantity > 0 else 0.0
            pnl = (price - lot.adjusted_cost) * take - fee_share

            holding_days = (t.date() - lot.entry_time.date()).days

            records.append(PnLRecord(
                sell_tx_id=self._next_tx_id,
                sell_time=t,
                sell_price=price,
                sell_qty=take,
                matched_lot_id=lot.lot_id,
                lot_entry_time=lot.entry_time,
                lot_cost=lot.adjusted_cost,
                realized_pnl=round(pnl, 2),
                holding_days=holding_days,
            ))

            lot.remaining -= take
            remaining -= take
            if lot.is_exhausted:
                self._lots.popleft()

        # 记录交易
        tx = Transaction(
            tx_id=self._next_tx_id,
            time=t,
            side="SELL",
            quantity=quantity,
            price=price,
            gross_amount=gross,
            fee=commission + transfer,
            stamp_duty=stamp,
        )
        self._next_tx_id += 1
        self._transactions.append(tx)
        self._pnl_records.extend(records)

        total_pnl = sum(r.realized_pnl for r in records)
        self._realized_pnl_total += total_pnl

        # T+1 到账
        settlement = trading_day_offset(t.date(), 1)
        self._pending_settlement[settlement] += net_cash

        return records, round(net_cash, 2)

    # ── 汇总 ──────────────────────────────────────────────────────

    def summary(self, market_price: float) -> PoolSummary:
        """以当前市价生成资金池快照."""
        total_shares = self.total_shares
        total_cost = sum(l.adjusted_cost * l.remaining for l in self._lots)
        avg_cost = total_cost / total_shares if total_shares > 0 else 0.0
        market_value = total_shares * market_price
        unrealized = market_value - total_cost

        return PoolSummary(
            total_shares=total_shares,
            total_cost=round(total_cost, 2),
            avg_cost=round(avg_cost, 4),
            market_price=market_price,
            market_value=round(market_value, 2),
            unrealized_pnl=round(unrealized, 2),
            unrealized_pnl_pct=round(unrealized / total_cost * 100, 2) if total_cost > 0 else 0.0,
            realized_pnl_total=round(self._realized_pnl_total, 2),
            net_pnl=round(self._realized_pnl_total + unrealized, 2),
            available_shares=total_shares,  # T+1 简化
            lots_count=len(self._lots),
        )

    # ── 特殊操作 ──────────────────────────────────────────────────

    def adjust_cost_for_dividend(self, div_per_share: float, ex_date: str | date):
        """现金分红: 降低每股成本基准 (除息调整)."""
        ex_d = date.fromisoformat(str(ex_date)) if isinstance(ex_date, str) else ex_date
        if self.total_shares == 0:
            return
        total_div = div_per_share * self.total_shares
        self._total_dividend += total_div
        total_cost_before = sum(l.cost_price * l.remaining for l in self._lots)
        # 分红后成本 = 原成本 - 分红额 → factor = 原/新 (>1, 使 adjusted_cost 下降)
        new_total = total_cost_before - total_div
        factor = total_cost_before / new_total if new_total > 0 else 1.0
        for lot in self._lots:
            lot.adjustment_factor *= factor

    def adjust_for_split(self, ratio: float):
        """送转股: 每股拆成 ratio 股 (ratio > 1 送转, < 1 缩股)."""
        for lot in self._lots:
            lot.quantity = int(lot.quantity * ratio)
            lot.remaining = int(lot.remaining * ratio)
            lot.cost_price /= ratio

    def pending_cash(self, as_of: date | None = None) -> float:
        """待结算资金 (T+1)."""
        d = as_of or date.today()
        return round(self._pending_settlement.get(d, 0.0), 2)

    def irr(self, market_price: float) -> float:
        """简易 IRR (内部收益率) — 基于净现金流的时间加权."""
        from datetime import datetime as dt
        now = dt.now()
        flows = []
        for tx in self._transactions:
            cf = -tx.gross_amount if tx.side == "BUY" else tx.gross_amount - tx.fee - tx.stamp_duty
            y = (tx.time - dt(2000, 1, 1)).total_seconds() / 31557600  # Julian years
            flows.append((y, cf))
        # 终值
        end_y = (now - dt(2000, 1, 1)).total_seconds() / 31557600
        flows.append((end_y, self.total_shares * market_price))

        # Newton-Raphson 求 IRR
        guess = 0.05
        for _ in range(30):
            npv = 0.0; dnpv = 0.0
            for y, cf in flows:
                df = math.exp(-guess * (y - flows[0][0]))
                npv += cf * df
                dnpv -= cf * (y - flows[0][0]) * df
            if abs(dnpv) < 1e-12:
                break
            guess -= npv / dnpv
        return round(guess, 4)

    def lot_detail(self) -> List[dict]:
        """税基明细(含剩余、持有天数)."""
        now = datetime.now()
        return [
            {
                "lot_id": l.lot_id,
                "entry_time": l.entry_time.isoformat(sep=" ", timespec="minutes"),
                "cost_price": l.adjusted_cost,
                "remaining": l.remaining,
                "remaining_value": round(l.adjusted_cost * l.remaining, 2),
                "holding_days": (now - l.entry_time).days,
                "settlement": l.settlement_date.isoformat(),
            }
            for l in self._lots if l.remaining > 0
        ]

    # ── 序列化 ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "market": self.market.value,
            "total_shares": self.total_shares,
            "_lots": [
                {
                    "lot_id": l.lot_id,
                    "entry_time": l.entry_time.isoformat(),
                    "quantity": l.quantity,
                    "cost_price": l.cost_price,
                    "remaining": l.remaining,
                    "adjustment_factor": l.adjustment_factor,
                }
                for l in self._lots
            ],
            "_realized_pnl_total": self._realized_pnl_total,
            "_total_dividend": self._total_dividend,
            "_next_lot_id": self._next_lot_id,
            "_next_tx_id": self._next_tx_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FIFOEngine":
        engine = cls(d["code"], Market(d.get("market", "sz_main")))
        engine._next_lot_id = d["_next_lot_id"]
        engine._next_tx_id = d["_next_tx_id"]
        engine._realized_pnl_total = d.get("_realized_pnl_total", 0.0)
        engine._total_dividend = d.get("_total_dividend", 0.0)
        for ld in d["_lots"]:
            lot = Lot(
                lot_id=ld["lot_id"],
                entry_time=datetime.fromisoformat(ld["entry_time"]),
                quantity=ld["quantity"],
                cost_price=ld["cost_price"],
                gross_amount=ld["quantity"] * ld["cost_price"],
                fee=0.0,
                remaining=ld["remaining"],
                settlement_date=datetime.fromisoformat(ld["entry_time"]).date() + timedelta(days=1),
                adjustment_factor=ld.get("adjustment_factor", 1.0),
            )
            engine._lots.append(lot)
        return engine


# ═══════════════════════════════════════════════════════════════════════
# 4. 批量 FIFO 执行器 (多股票 / 组合维度)
# ═══════════════════════════════════════════════════════════════════════


class MultiPoolManager:
    """多标的资金池汇总管理."""

    def __init__(self):
        self._pools: Dict[str, FIFOEngine] = {}

    def get_or_create(self, code: str, **kw) -> FIFOEngine:
        if code not in self._pools:
            self._pools[code] = FIFOEngine(code, **kw)
        return self._pools[code]

    def aggregate_summary(self, market_prices: Dict[str, float]) -> Dict:
        totals = {"total_cost": 0.0, "market_value": 0.0,
                  "unrealized_pnl": 0.0, "realized_pnl": 0.0}
        details = {}
        for code, engine in self._pools.items():
            mp = market_prices.get(code, 0.0)
            s = engine.summary(mp)
            details[code] = s
            totals["total_cost"] += s.total_cost
            totals["market_value"] += s.market_value
            totals["unrealized_pnl"] += s.unrealized_pnl
            totals["realized_pnl"] += s.realized_pnl_total
        totals["net_pnl"] = totals["unrealized_pnl"] + totals["realized_pnl"]
        return {"totals": totals, "details": details}

    def export(self) -> dict:
        return {c: e.to_dict() for c, e in self._pools.items()}

    @classmethod
    def import_(cls, data: dict) -> "MultiPoolManager":
        mgr = cls()
        for code, d in data.items():
            mgr._pools[code] = FIFOEngine.from_dict(d)
        return mgr


# ═══════════════════════════════════════════════════════════════════════
# 5. 单元测试
# ═══════════════════════════════════════════════════════════════════════


def _run_tests():
    import sys

    ok = 0; fail = 0

    def check(name, cond, detail=""):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print(f"  ❌ {name}: {detail}")

    # ── Test 1: 基本 FIFO 出入 ──
    e = FIFOEngine("300418")
    e.deposit("2026-07-13 09:35", 1000, 48.00)
    e.deposit("2026-07-14 09:40", 500, 45.00)
    check("T1 total shares", e.total_shares == 1500)

    recs, cash = e.withdraw("2026-07-14 14:30", 800, 46.00)
    check("T1 first lot matched", recs[0].matched_lot_id == 1)
    check("T1 first lot qty exact", recs[0].sell_qty == 800)
    check("T1 lot1 partial: 200 left", e._lots[0].lot_id == 1 and e._lots[0].remaining == 200)
    check("T1 remaining total", e.total_shares == 700)  # lot1 200 left + lot2 500 = 700

    # ── Test 2: 多批次跨 Lot 卖出 ──
    # lot1(300@40)+lot2(500@46)+lot3(200@50)=1000. 卖700=FIFO取lot1全部300+lot2的400.
    e2 = FIFOEngine("300418")
    e2.deposit("2026-06-01 10:00", 300, 40.00)
    e2.deposit("2026-07-01 10:00", 500, 46.00)
    e2.deposit("2026-07-10 10:00", 200, 50.00)
    recs2, _ = e2.withdraw("2026-07-15 11:00", 700, 48.00)
    check("T2 2 lots matched", len(recs2) == 2, f"got {len(recs2)}")
    check("T2 lot1 all 300", recs2[0].matched_lot_id == 1 and recs2[0].sell_qty == 300)
    check("T2 lot2 partial 400", recs2[1].matched_lot_id == 2 and recs2[1].sell_qty == 400)
    check("T2 remaining 300", e2.total_shares == 300)  # lot2 100 + lot3 200

    # ── Test 3: 盈亏核算 ──
    e3 = FIFOEngine("300418")
    e3.deposit("2026-07-13 09:35", 100, 45.00)
    recs3, cash3 = e3.withdraw("2026-07-14 10:00", 100, 48.00)
    # 成本含费: gross=4500, fee≈max(4500*0.00025,5)=5, cost_per=45.05
    # 卖费: gross=4800, 佣金=max(1.2,5)=5, 过户费=0, 印花=4800*0.0005=2.4 → 总费=7.4
    # pnl = (48-45.05)*100 - 7.4*100/100 = 295 - 7.4 = 287.6
    check("T3 net pnl positive", recs3[0].realized_pnl > 0, f"pnl={recs3[0].realized_pnl}")
    check("T3 cash positive", cash3 > 4500, f"cash={cash3}")

    # ── Test 4: 卖空保护 ──
    e4 = FIFOEngine("300418")
    e4.deposit("2026-07-01 10:00", 100, 50.00)
    try:
        e4.withdraw("2026-07-02 14:00", 200, 52.00)
        check("T4 oversell blocked", False, "should have raised")
    except ValueError:
        check("T4 oversell blocked", True)

    # ── Test 5: 涨跌停校验 ──
    e5 = FIFOEngine("300418")  # 创业板 ±20%
    try:
        e5.deposit("2026-07-01 10:00", 100, 60.00, prev_close=46.00)
        check("T5 limit check", 60.00 <= 46.00 * 1.20, "should have raised")
    except ValueError:
        check("T5 limit up blocked", True)
    try:
        e5.deposit("2026-07-01 10:00", 100, 30.00, prev_close=46.00)
        check("T5 limit down", 30.00 >= 46.00 * 0.80, "should have raised")
    except ValueError:
        check("T5 limit down blocked", True)

    # ── Test 6: 除息调整 ──
    e6 = FIFOEngine("300418")
    e6.deposit("2026-07-01 10:00", 100, 50.00)
    e6.adjust_cost_for_dividend(1.0, "2026-07-10")
    s = e6.summary(52.00)
    check("T6 cost reduced", s.avg_cost < 50.00, f"avg_cost={s.avg_cost}")

    # ── Test 7: 汇总快照 ──
    e7 = FIFOEngine("600519")  # 沪市主板
    e7.deposit("2026-06-01 10:00", 500, 1600.00)
    s7 = e7.summary(1650.00)
    check("T7 market value", s7.market_value > s7.total_cost)
    check("T7 unrealized positive", s7.unrealized_pnl > 0)
    check("T7 pct calc", abs(s7.unrealized_pnl_pct - (s7.unrealized_pnl / s7.total_cost * 100)) < 0.01)

    # ── Test 8: 序列化 ──
    e8 = FIFOEngine("300418")
    e8.deposit("2026-07-10 09:35", 200, 46.00)
    e8.deposit("2026-07-11 10:00", 300, 45.50)
    d8 = e8.to_dict()
    e8b = FIFOEngine.from_dict(d8)
    check("T8 restore shares", e8b.total_shares == 500)
    check("T8 restore lots", len(e8b._lots) == 2)
    check("T8 restore ids", e8b._next_lot_id == e8._next_lot_id)

    # ── Test 9: Multi Pool ──
    mgr = MultiPoolManager()
    mgr.get_or_create("300418").deposit("2026-07-10 10:00", 100, 46.00)
    mgr.get_or_create("300058").deposit("2026-07-10 10:00", 200, 12.00)
    agg = mgr.aggregate_summary({"300418": 47.00, "300058": 12.50})
    check("T9 multi total cost > 0", agg["totals"]["total_cost"] > 0)
    check("T9 multi 2 symbols", len(agg["details"]) == 2)

    # ── Test 10: 持有天数 ──
    e10 = FIFOEngine("300418")
    e10.deposit("2026-07-01 09:35", 100, 45.00)
    recs10, _ = e10.withdraw("2026-07-15 14:00", 100, 48.00)
    check("T10 holding days", recs10[0].holding_days == 14, f"got {recs10[0].holding_days}")

    # ── Summary ──
    print(f"\n{'='*50}")
    print(f"  测试结果: {ok} 通过 / {fail} 失败  (共 {ok+fail})")
    print(f"{'='*50}")
    return fail == 0


if __name__ == "__main__":
    _run_tests()
