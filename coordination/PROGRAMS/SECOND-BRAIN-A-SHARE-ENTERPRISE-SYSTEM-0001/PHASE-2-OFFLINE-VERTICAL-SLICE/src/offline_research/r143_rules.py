"""R143 materialization of the existing W2/C2 AShareRuleSnapshot authority.

Research-only. No broker, account, order transport, private data, or production I/O.
The vocabulary in this module is local runtime vocabulary for the already-assigned
C2_A_SHARE_RULE_SNAPSHOT authority, not a new canonical schema identity.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from typing import Any, Iterable


class RuleGateError(ValueError):
    pass


class FillabilityState(StrEnum):
    ORDER_FILLABILITY_UNKNOWN = "ORDER_FILLABILITY_UNKNOWN"
    ORDER_FILLABILITY_EVIDENCE_CONFIRMED = "ORDER_FILLABILITY_EVIDENCE_CONFIRMED"
    SCENARIO_ASSUMPTION_NO_FILL = "SCENARIO_ASSUMPTION_NO_FILL"


class PriceValidityState(StrEnum):
    PRICE_VALID = "PRICE_VALID"
    PRICE_INVALID = "PRICE_INVALID"
    PRICE_VALID_NO_LIMIT = "PRICE_VALID_NO_LIMIT"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _parse_day(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value[:10])


def _round_price(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class AShareRuleSnapshot:
    """Concrete runtime materialization of the pre-existing W2/C2 authority."""
    rule_snapshot_id: str
    exchange: str
    board: str
    security_status: str
    effective_from: str
    effective_to: str | None
    price_limit_pct: float | None
    no_price_limit: bool
    source_ref: str
    rule_identity: str
    document_number: str
    publication_date: str
    supersedes: str | None
    semantics: tuple[str, ...]
    market_supported: bool = True
    expected_semantic_hash: str | None = None

    def semantic_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("expected_semantic_hash", None)
        return data

    @property
    def semantic_hash(self) -> str:
        return _digest(self.semantic_payload())

    def verify_integrity(self) -> None:
        if self.expected_semantic_hash and self.semantic_hash != self.expected_semantic_hash:
            raise RuleGateError("STALE_RULE_MUTATION")

    def active_on(self, trading_day: str | date) -> bool:
        day = _parse_day(trading_day)
        if day < _parse_day(self.effective_from):
            return False
        return self.effective_to is None or day <= _parse_day(self.effective_to)


@dataclass(frozen=True)
class LimitReferencePrice:
    value: float
    kind: str
    source_ref: str
    effective_trading_day: str
    rule_snapshot_id: str

    def validate(self, snapshot: AShareRuleSnapshot, trading_day: str | date) -> None:
        if self.value <= 0 or not self.source_ref:
            raise RuleGateError("INVALID_LIMIT_REFERENCE_PRICE")
        if self.rule_snapshot_id != snapshot.rule_snapshot_id:
            raise RuleGateError("REFERENCE_PRICE_RULE_BINDING_MISMATCH")
        if _parse_day(self.effective_trading_day) != _parse_day(trading_day):
            raise RuleGateError("REFERENCE_PRICE_TRADING_DAY_MISMATCH")
        if self.kind not in {"OFFICIAL_PREVIOUS_CLOSE", "EX_RIGHT_EX_DIVIDEND_REFERENCE"}:
            raise RuleGateError("UNSUPPORTED_REFERENCE_PRICE_KIND")


@dataclass(frozen=True)
class FillabilityEvidence:
    evidence_id: str
    source_ref: str
    observed_at: str
    fillable: bool
    evidence_kind: str
    contra_liquidity_quantity: float | None = None

    def validate(self) -> None:
        if not self.evidence_id or not self.source_ref or not self.observed_at:
            raise RuleGateError("INCOMPLETE_FILLABILITY_EVIDENCE")
        if self.evidence_kind not in {"QUEUE_ORDER_BOOK", "CONTRA_LIQUIDITY", "OBSERVED_EXECUTION"}:
            raise RuleGateError("UNSUPPORTED_FILLABILITY_EVIDENCE")
        if self.evidence_kind == "CONTRA_LIQUIDITY" and (self.contra_liquidity_quantity is None or self.contra_liquidity_quantity < 0):
            raise RuleGateError("INVALID_CONTRA_LIQUIDITY_EVIDENCE")


@dataclass(frozen=True)
class FillabilityAssessment:
    state: FillabilityState
    fillable: bool | None
    observed_fact: bool
    abstain: bool
    reason: str
    evidence_id: str | None = None


@dataclass(frozen=True)
class PriceValidityAssessment:
    state: PriceValidityState
    valid: bool
    upper_limit: float | None
    lower_limit: float | None
    at_upper_limit: bool
    at_lower_limit: bool
    rule_snapshot_id: str
    reference_price_kind: str | None


class AShareRuleResolver:
    """Single W2 resolver over AShareRuleSnapshot records, not a second authority."""

    def __init__(self, snapshots: Iterable[AShareRuleSnapshot]):
        self.snapshots = tuple(snapshots)

    def resolve(self, exchange: str, board: str, security_status: str, trading_day: str | date, listing_trading_day_number: int | None = None) -> AShareRuleSnapshot:
        exchange = exchange.upper()
        board = board.upper()
        status = security_status.upper()
        if exchange == "BSE":
            raise RuleGateError("UNSUPPORTED_MARKET_BSE")
        if exchange not in {"SSE", "SZSE"}:
            raise RuleGateError("UNSUPPORTED_MARKET")
        if board not in {"MAIN", "STAR", "CHINEXT"}:
            raise RuleGateError("UNSUPPORTED_BOARD")
        if (exchange, board) not in {("SSE", "MAIN"), ("SSE", "STAR"), ("SZSE", "MAIN"), ("SZSE", "CHINEXT")}:
            raise RuleGateError("BOARD_EXCHANGE_MISMATCH")
        if status not in {"NORMAL", "RISK_WARNING", "IPO_INITIAL_NO_LIMIT"}:
            raise RuleGateError("UNSUPPORTED_SECURITY_STATUS")
        effective_status = "IPO_INITIAL_NO_LIMIT" if listing_trading_day_number is not None and 1 <= listing_trading_day_number <= 5 else status
        matches = [s for s in self.snapshots if s.exchange == exchange and s.board == board and s.security_status == effective_status and s.active_on(trading_day)]
        if len(matches) != 1:
            raise RuleGateError("MISSING_OR_AMBIGUOUS_RULE_SNAPSHOT")
        snap = matches[0]
        if not snap.market_supported:
            raise RuleGateError("UNSUPPORTED_MARKET")
        snap.verify_integrity()
        return snap


@dataclass(frozen=True)
class TradingCalendar:
    calendar_id: str
    exchange: str
    trading_days: tuple[str, ...]
    source_ref: str

    def is_trading_day(self, day: str | date) -> bool:
        return _parse_day(day).isoformat() in self.trading_days

    def next_trading_day(self, day: str | date) -> str:
        current = _parse_day(day)
        following = sorted(_parse_day(item) for item in self.trading_days if _parse_day(item) > current)
        if not following:
            raise RuleGateError("TRADING_CALENDAR_EXHAUSTED")
        return following[0].isoformat()


SUPPORTED_SESSIONS = {"OPEN_AUCTION", "CONTINUOUS", "CLOSE_AUCTION"}


def validate_session(session: str | None) -> str:
    if session is None or session not in SUPPORTED_SESSIONS:
        raise RuleGateError("UNSUPPORTED_OR_UNKNOWN_SESSION")
    return session


def evaluate_price_validity(price: float, snapshot: AShareRuleSnapshot, reference: LimitReferencePrice | None, trading_day: str | date) -> PriceValidityAssessment:
    snapshot.verify_integrity()
    if not snapshot.active_on(trading_day):
        raise RuleGateError("RULE_SNAPSHOT_OUTSIDE_EFFECTIVE_INTERVAL")
    if snapshot.no_price_limit:
        return PriceValidityAssessment(PriceValidityState.PRICE_VALID_NO_LIMIT, True, None, None, False, False, snapshot.rule_snapshot_id, None)
    if snapshot.price_limit_pct is None or reference is None:
        raise RuleGateError("MISSING_RULE_OR_REFERENCE_PRICE")
    reference.validate(snapshot, trading_day)
    upper = _round_price(reference.value * (1 + snapshot.price_limit_pct))
    lower = _round_price(reference.value * (1 - snapshot.price_limit_pct))
    price = _round_price(price)
    valid = lower <= price <= upper
    return PriceValidityAssessment(
        PriceValidityState.PRICE_VALID if valid else PriceValidityState.PRICE_INVALID,
        valid,
        upper,
        lower,
        price == upper,
        price == lower,
        snapshot.rule_snapshot_id,
        reference.kind,
    )


def evaluate_order_fillability(price_validity: PriceValidityAssessment, evidence: FillabilityEvidence | None = None, conservative_no_fill_scenario: bool = False) -> FillabilityAssessment:
    if not price_validity.valid:
        return FillabilityAssessment(FillabilityState.ORDER_FILLABILITY_UNKNOWN, None, False, True, "PRICE_INVALID_NOT_A_FILLABILITY_OBSERVATION")
    at_limit = price_validity.at_upper_limit or price_validity.at_lower_limit
    if evidence is not None:
        evidence.validate()
        return FillabilityAssessment(
            FillabilityState.ORDER_FILLABILITY_EVIDENCE_CONFIRMED,
            evidence.fillable,
            True,
            False,
            "OBSERVED_EVIDENCE_BACKED_FILLABILITY",
            evidence.evidence_id,
        )
    if at_limit and conservative_no_fill_scenario:
        return FillabilityAssessment(FillabilityState.SCENARIO_ASSUMPTION_NO_FILL, False, False, False, "EXPLICIT_CONSERVATIVE_SCENARIO_ASSUMPTION")
    if at_limit:
        return FillabilityAssessment(FillabilityState.ORDER_FILLABILITY_UNKNOWN, None, False, True, "BAR_ONLY_INSUFFICIENT_LIQUIDITY_EVIDENCE")
    return FillabilityAssessment(FillabilityState.ORDER_FILLABILITY_UNKNOWN, None, False, True, "NO_ORDER_FILLABILITY_EVIDENCE")


@dataclass
class AcquisitionLot:
    lot_id: str
    acquired_trading_day: str
    quantity: int
    remaining_quantity: int | None = None

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise RuleGateError("NEGATIVE_ACQUISITION_LOT")
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity
        if self.remaining_quantity < 0 or self.remaining_quantity > self.quantity:
            raise RuleGateError("INVALID_REMAINING_LOT_QUANTITY")


@dataclass
class SettlementAwareInventory:
    lots: dict[str, list[AcquisitionLot]] = field(default_factory=dict)

    def acquire(self, symbol: str, quantity: int, trading_day: str | date, lot_id: str) -> None:
        if quantity <= 0:
            raise RuleGateError("NON_POSITIVE_ACQUISITION")
        self.lots.setdefault(symbol, []).append(AcquisitionLot(lot_id, _parse_day(trading_day).isoformat(), quantity))

    def sellable_quantity(self, symbol: str, trading_day: str | date, calendar: TradingCalendar) -> int:
        current = _parse_day(trading_day)
        total = 0
        for lot in self.lots.get(symbol, []):
            try:
                unlock = _parse_day(calendar.next_trading_day(lot.acquired_trading_day))
            except RuleGateError:
                continue
            if current >= unlock:
                total += int(lot.remaining_quantity or 0)
        return total

    def total_quantity(self, symbol: str) -> int:
        return sum(int(lot.remaining_quantity or 0) for lot in self.lots.get(symbol, []))

    def sell(self, symbol: str, quantity: int, trading_day: str | date, calendar: TradingCalendar) -> None:
        if quantity <= 0:
            raise RuleGateError("NON_POSITIVE_SALE")
        if quantity > self.sellable_quantity(symbol, trading_day, calendar):
            raise RuleGateError("T_PLUS_ONE_LOCK")
        remaining = quantity
        current = _parse_day(trading_day)
        for lot in self.lots.get(symbol, []):
            if remaining <= 0:
                break
            try:
                unlock = _parse_day(calendar.next_trading_day(lot.acquired_trading_day))
            except RuleGateError:
                continue
            if current < unlock or not lot.remaining_quantity:
                continue
            take = min(remaining, lot.remaining_quantity)
            lot.remaining_quantity -= take
            remaining -= take
        if remaining:
            raise RuleGateError("INVENTORY_ACCOUNTING_INCONSISTENCY")

    def snapshot(self, symbol: str) -> list[dict[str, Any]]:
        return [asdict(lot) for lot in self.lots.get(symbol, [])]


@dataclass(frozen=True)
class ReplayGateDecision:
    allowed: bool
    outcome: str
    rule_snapshot_id: str | None
    reason: str | None


def replay_gate(*, resolver: AShareRuleResolver, exchange: str, board: str, security_status: str, trading_day: str, calendar: TradingCalendar | None, session: str | None, listing_trading_day_number: int | None = None) -> ReplayGateDecision:
    try:
        if calendar is None or not calendar.is_trading_day(trading_day):
            raise RuleGateError("UNKNOWN_OR_NON_TRADING_CALENDAR_DAY")
        validate_session(session)
        snapshot = resolver.resolve(exchange, board, security_status, trading_day, listing_trading_day_number)
        snapshot.verify_integrity()
        return ReplayGateDecision(True, "ALLOW", snapshot.rule_snapshot_id, None)
    except RuleGateError as exc:
        return ReplayGateDecision(False, "ABSTAIN", None, str(exc))


def deterministic_replay_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {**payload, "research_only": True, "no_trade": True}
    return {"payload": normalized, "receipt_hash": _digest(normalized)}


def with_integrity(snapshot: AShareRuleSnapshot) -> AShareRuleSnapshot:
    return replace(snapshot, expected_semantic_hash=snapshot.semantic_hash)


# Exact official-source semantics used by this bounded slice. These materialize the
# existing W2/C2 authority. They are not a second authority and are tested against
# R143/official-rule-provenance.json.
_DEFAULT_RAW = [
    # SSE main normal, same 10% limit across the 2026 rule boundary.
    AShareRuleSnapshot("SSE_MAIN_NORMAL_PRE_20260706", "SSE", "MAIN", "NORMAL", "2023-04-10", "2026-07-05", 0.10, False, "SSE_TRADING_RULES_2023", "Shanghai Stock Exchange Trading Rules (2023 Revision)", "上证发〔2023〕32号", "2023-02-17", None, ("main_board_price_limit_10pct",)),
    AShareRuleSnapshot("SSE_MAIN_NORMAL_POST_20260706", "SSE", "MAIN", "NORMAL", "2026-07-06", None, 0.10, False, "SSE_TRADING_RULES_2026", "Shanghai Stock Exchange Trading Rules (2026 Revision)", "上证发〔2026〕41号", "2026-04-24", "上证发〔2023〕32号", ("main_board_price_limit_10pct", "effective_2026-07-06")),
    AShareRuleSnapshot("SSE_MAIN_RISK_PRE_20260706", "SSE", "MAIN", "RISK_WARNING", "2013-01-01", "2026-07-05", 0.05, False, "SSE_RISK_WARNING_BOARD_PRE_20260706", "SSE Risk Warning Board Stock Trading Interim Measures", "上证公字〔2012〕72号", "2012-12-14", None, ("main_board_risk_warning_5pct",)),
    AShareRuleSnapshot("SSE_MAIN_RISK_POST_20260706", "SSE", "MAIN", "RISK_WARNING", "2026-07-06", None, 0.10, False, "SSE_TRADING_RULES_2026", "Shanghai Stock Exchange Trading Rules (2026 Revision)", "上证发〔2026〕41号", "2026-04-24", "SSE_MAIN_RISK_PRE_20260706", ("main_board_risk_warning_10pct", "effective_2026-07-06")),
    AShareRuleSnapshot("SSE_MAIN_IPO_NO_LIMIT", "SSE", "MAIN", "IPO_INITIAL_NO_LIMIT", "2023-02-17", None, None, True, "SSE_TRADING_RULES_2026", "Shanghai Stock Exchange Trading Rules (2026 Revision)", "上证发〔2026〕41号", "2026-04-24", "上证发〔2023〕32号", ("ipo_first_5_trading_days_no_price_limit",)),
    AShareRuleSnapshot("SSE_STAR_20", "SSE", "STAR", "NORMAL", "2019-07-22", None, 0.20, False, "SSE_TRADING_RULES_2026", "Shanghai Stock Exchange Trading Rules (2026 Revision)", "上证发〔2026〕41号", "2026-04-24", None, ("star_price_limit_20pct",)),
    AShareRuleSnapshot("SSE_STAR_IPO_NO_LIMIT", "SSE", "STAR", "IPO_INITIAL_NO_LIMIT", "2019-07-22", None, None, True, "SSE_TRADING_RULES_2026", "Shanghai Stock Exchange Trading Rules (2026 Revision)", "上证发〔2026〕41号", "2026-04-24", None, ("star_ipo_first_5_trading_days_no_price_limit",)),
    # SZSE.
    AShareRuleSnapshot("SZSE_MAIN_NORMAL_PRE_20260706", "SZSE", "MAIN", "NORMAL", "2023-04-10", "2026-07-05", 0.10, False, "SZSE_TRADING_RULES_2023", "Shenzhen Stock Exchange Trading Rules (2023 Revision)", "深证上〔2023〕98号", "2023-02-17", None, ("main_board_price_limit_10pct",)),
    AShareRuleSnapshot("SZSE_MAIN_NORMAL_POST_20260706", "SZSE", "MAIN", "NORMAL", "2026-07-06", None, 0.10, False, "SZSE_TRADING_RULES_2026", "Shenzhen Stock Exchange Trading Rules (2026 Revision)", "深证上〔2026〕551号", "2026-04-24", "深证上〔2023〕98号", ("main_board_price_limit_10pct", "effective_2026-07-06")),
    AShareRuleSnapshot("SZSE_MAIN_RISK_PRE_20260706", "SZSE", "MAIN", "RISK_WARNING", "2023-04-10", "2026-07-05", 0.05, False, "SZSE_TRADING_RULES_2023", "Shenzhen Stock Exchange Trading Rules (2023 Revision)", "深证上〔2023〕98号", "2023-02-17", None, ("main_board_risk_warning_5pct",)),
    AShareRuleSnapshot("SZSE_MAIN_RISK_POST_20260706", "SZSE", "MAIN", "RISK_WARNING", "2026-07-06", None, 0.10, False, "SZSE_TRADING_RULES_2026", "Shenzhen Stock Exchange Trading Rules (2026 Revision)", "深证上〔2026〕551号", "2026-04-24", "深证上〔2023〕98号", ("main_board_risk_warning_10pct", "effective_2026-07-06")),
    AShareRuleSnapshot("SZSE_MAIN_IPO_NO_LIMIT", "SZSE", "MAIN", "IPO_INITIAL_NO_LIMIT", "2023-02-17", None, None, True, "SZSE_TRADING_RULES_2026", "Shenzhen Stock Exchange Trading Rules (2026 Revision)", "深证上〔2026〕551号", "2026-04-24", "深证上〔2023〕98号", ("ipo_first_5_trading_days_no_price_limit",)),
    AShareRuleSnapshot("SZSE_CHINEXT_20", "SZSE", "CHINEXT", "NORMAL", "2020-08-24", None, 0.20, False, "SZSE_TRADING_RULES_2026", "Shenzhen Stock Exchange Trading Rules (2026 Revision)", "深证上〔2026〕551号", "2026-04-24", "深证上〔2023〕98号", ("chinext_price_limit_20pct",)),
    AShareRuleSnapshot("SZSE_CHINEXT_RISK_20", "SZSE", "CHINEXT", "RISK_WARNING", "2020-08-24", None, 0.20, False, "SZSE_TRADING_RULES_2026", "Shenzhen Stock Exchange Trading Rules (2026 Revision)", "深证上〔2026〕551号", "2026-04-24", "深证上〔2023〕98号", ("chinext_risk_warning_price_limit_20pct",)),
    AShareRuleSnapshot("SZSE_CHINEXT_IPO_NO_LIMIT", "SZSE", "CHINEXT", "IPO_INITIAL_NO_LIMIT", "2020-08-24", None, None, True, "SZSE_TRADING_RULES_2026", "Shenzhen Stock Exchange Trading Rules (2026 Revision)", "深证上〔2026〕551号", "2026-04-24", "深证上〔2023〕98号", ("chinext_ipo_first_5_trading_days_no_price_limit",)),
]
DEFAULT_RULE_SNAPSHOTS = tuple(with_integrity(item) for item in _DEFAULT_RAW)
DEFAULT_RULE_RESOLVER = AShareRuleResolver(DEFAULT_RULE_SNAPSHOTS)
