"""Immutable synthetic contracts. They do not represent market observations."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class SessionPhase(str, Enum):
    PREOPEN = "PREOPEN"; CALL_AUCTION = "CALL_AUCTION"; AUCTION_FREEZE = "AUCTION_FREEZE"
    CONTINUOUS_AM = "CONTINUOUS_AM"; MIDDAY_BREAK = "MIDDAY_BREAK"; CONTINUOUS_PM = "CONTINUOUS_PM"
    CLOSING_AUCTION = "CLOSING_AUCTION"; CLOSED = "CLOSED"; SUSPENDED = "SUSPENDED"


class SecurityStatus(str, Enum):
    ACTIVE = "ACTIVE"; SUSPENDED = "SUSPENDED"; UNKNOWN = "UNKNOWN"


class OrderSide(str, Enum):
    BUY = "BUY"; SELL = "SELL"


class MatchMode(str, Enum):
    FULL = "FULL"; PARTIAL = "PARTIAL"; NO_FILL_CANCEL = "NO_FILL_CANCEL"; NO_FILL_CARRY = "NO_FILL_CARRY"; UNKNOWN = "UNKNOWN"


class OutcomeStatus(str, Enum):
    FILLED = "FILLED"; PARTIALLY_FILLED = "PARTIALLY_FILLED"; UNFILLED_CANCELLED = "UNFILLED_CANCELLED"
    UNFILLED_CARRIED = "UNFILLED_CARRIED"; UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"; INVALID_OR_BLOCKED = "INVALID_OR_BLOCKED"


@dataclass(frozen=True)
class SyntheticRuleSnapshot:
    snapshot_id: str; exchange: str; board: str; trade_date: str
    price_limit_low: Optional[int]; price_limit_high: Optional[int]
    price_unit: Optional[str]; quantity_unit: Optional[str]
    permitted_phases: Tuple[SessionPhase, ...]
    t_plus_one_enabled: Optional[bool]; suspension_behavior: Optional[str]; version: str


@dataclass(frozen=True)
class InformationSet:
    source_capability: Optional[str]; available_at_ns: Optional[int]; source_sequence: Optional[int] = None


@dataclass(frozen=True)
class MarketState:
    phase: Optional[SessionPhase]; trade_date: Optional[str]; security_status: Optional[SecurityStatus]
    rule_snapshot: Optional[SyntheticRuleSnapshot]; information: Optional[InformationSet]


@dataclass(frozen=True)
class SyntheticLot:
    lot_id: str; acquired_trade_date: Optional[str]; quantity: Optional[int]; locked_quantity: Optional[int] = 0


@dataclass(frozen=True)
class InventoryState:
    lots: Tuple[SyntheticLot, ...]; pending_buy_quantity: Optional[int] = 0; pending_sell_quantity: Optional[int] = 0


@dataclass(frozen=True)
class SyntheticOrder:
    order_id: str; side: Optional[OrderSide]; quantity: Optional[int]; limit_price: Optional[int]
    available_at_ns: Optional[int]; match_mode: MatchMode; partial_fill_quantity: Optional[int] = None


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool; reason_codes: Tuple[str, ...]


@dataclass(frozen=True)
class SyntheticMatchOutcome:
    status: OutcomeStatus; filled_quantity: int; unfilled_quantity: int
    inventory: InventoryState; reason_codes: Tuple[str, ...]
