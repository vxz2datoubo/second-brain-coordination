"""Small deterministic research-only vertical slice; it has no network or order adapter."""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .r143_rules import (
    DEFAULT_RULE_RESOLVER,
    FillabilityEvidence,
    FillabilityState,
    LimitReferencePrice,
    RuleGateError,
    SettlementAwareInventory,
    TradingCalendar,
    evaluate_order_fillability,
    evaluate_price_validity,
    replay_gate,
)


class ValidationError(ValueError):
    """A governed record is invalid, unavailable, or must abstain."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise ValidationError(f"invalid_timestamp:{value}") from error
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _exchange_code(exchange: str) -> str:
    value = exchange.upper()
    return {"SH": "SSE", "SSE": "SSE", "SZ": "SZSE", "SZSE": "SZSE", "BJ": "BSE", "BSE": "BSE"}.get(value, value)


def _board_for_symbol(symbol: str, exchange: str) -> str:
    code = symbol.split(".", 1)[0]
    ex = _exchange_code(exchange)
    if ex == "SSE" and code.startswith("688"):
        return "STAR"
    if ex == "SZSE" and code.startswith(("300", "301")):
        return "CHINEXT"
    return "MAIN"


def _session_from_time(event_time: str) -> str | None:
    dt = parse_time(event_time)
    hhmm = (dt.hour, dt.minute)
    if hhmm == (15, 0):
        return "CLOSE_AUCTION"
    if (9, 15) <= hhmm < (9, 30):
        return "OPEN_AUCTION"
    if (9, 30) <= hhmm < (15, 0):
        return "CONTINUOUS"
    return None


@dataclass(frozen=True)
class Bar:
    event_id: str
    symbol: str
    exchange: str
    event_time: str
    available_at: str
    observed_at: str
    receive_time: str
    entered_system_at: str
    as_of: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    suspended: bool | None = False
    is_st: bool | None = False
    adjusted: bool = False
    adjustment_method: str = "none"
    limit_rule_version: str = "ashare-v1"
    source_id: str = "synthetic-public-safe"
    dataset_version: str = "1.0.0"
    license: str = "CC0-1.0"
    capability_level: str = "HISTORICAL_BAR"
    entitlement_status: str = "confirmed"
    corporate_action_note: str = "none"
    limit_reference_price: float | None = None
    limit_reference_price_kind: str | None = None
    limit_reference_source: str | None = None
    listing_trading_day_number: int | None = None
    session: str | None = None
    fillability_evidence_kind: str | None = None
    fillability_evidence_id: str | None = None
    fillability_evidence_source: str | None = None
    fillability_observed: bool | None = None
    contra_liquidity_quantity: float | None = None

    @property
    def trading_day(self) -> date:
        return parse_time(self.event_time).date()

    @property
    def board(self) -> str:
        return _board_for_symbol(self.symbol, self.exchange)

    @property
    def security_status(self) -> str:
        return "RISK_WARNING" if self.is_st is True else "NORMAL"

    @property
    def replay_session(self) -> str | None:
        return self.session or _session_from_time(self.event_time)

    def payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GateRecord:
    event_id: str
    outcome: str
    reason: str | None = None


@dataclass
class ReplayResult:
    events: list[Bar]
    event_ledger: list[dict[str, Any]]
    quarantine: list[GateRecord]
    checkpoint: dict[str, Any]

    @property
    def core_hash(self) -> str:
        return digest([entry["event_id"] for entry in self.event_ledger])


@dataclass
class SimulationConfig:
    initial_cash: float = 100_000.0
    max_position_weight: float = 0.25
    max_turnover: float = 1.0
    commission_bps: float = 2.5
    min_commission: float = 5.0
    stamp_duty_bps_sell: float = 5.0
    transfer_fee_bps_sh: float = 0.1
    fixed_slippage_bps: float = 5.0
    volume_impact_bps: float = 0.0
    rule_version: str = "ashare-research-r143-w2-c2"
    no_trade_gate: bool = True
    conservative_no_fill_at_limit: bool = False
    trading_calendar: TradingCalendar | None = None
    # Backward-compatible explicit scenario/test input. There is intentionally no
    # observed-event fallback; callers must also provide provenance.
    trading_days: tuple[str, ...] | None = None
    calendar_source_ref: str | None = None


class ContractRuntime:
    ALLOWED_CAPABILITIES = {"HISTORICAL_BAR", "FIVE_LEVEL_SNAPSHOT", "TEN_LEVEL_SNAPSHOT", "L2_AGGREGATE"}

    def validate_bar(self, bar: Bar, requested_as_of: str) -> None:
        if not bar.symbol or not bar.exchange:
            raise ValidationError("missing_identity")
        if bar.capability_level not in self.ALLOWED_CAPABILITIES:
            raise ValidationError("unsupported_capability")
        if bar.entitlement_status != "confirmed":
            raise ValidationError("entitlement_not_confirmed")
        if bar.capability_level != "HISTORICAL_BAR":
            raise ValidationError("capability_not_permitted_for_fixture")
        if not bar.source_id or not bar.dataset_version or not bar.license:
            raise ValidationError("missing_lineage")
        if parse_time(bar.available_at) > parse_time(requested_as_of):
            raise ValidationError("future_available_at")
        if parse_time(bar.event_time) > parse_time(bar.available_at):
            raise ValidationError("available_before_event")
        numeric_values = (bar.open, bar.high, bar.low, bar.close)
        if any(value < 0 for value in numeric_values) or (bar.volume is not None and bar.volume < 0):
            raise ValidationError("negative_market_value")
        if bar.suspended not in {True, False, None} or bar.is_st not in {True, False, None}:
            raise ValidationError("invalid_market_state_semantics")
        if not (bar.low <= bar.open <= bar.high and bar.low <= bar.close <= bar.high):
            raise ValidationError("invalid_ohlc")

    def envelope(self, bar: Bar, run_id: str, trace_id: str) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "object_id": bar.event_id,
            "record_type": "PriceBar",
            "run_id": run_id,
            "trace_id": trace_id,
            "no_trade_gate": True,
            "authority_write": False,
            "lineage": {"source_refs": [bar.source_id], "artifact_refs": [digest(bar.payload())]},
            "temporal": {
                key: getattr(bar, key)
                for key in ("event_time", "available_at", "observed_at", "receive_time", "entered_system_at", "as_of")
            },
            "capability": {
                "level": bar.capability_level,
                "entitlement_status": bar.entitlement_status,
                "gate_result": "allowed",
            },
        }


class SchemaRegistry:
    def __init__(self) -> None:
        self.known = {
            "FoundationSharedEnvelope": "1.0.0",
            "TemporalSemantics": "1.0.0",
            "OfflineReplay": "1.0.0",
            "C2_A_SHARE_RULE_SNAPSHOT": "1.0.0",
        }

    def require_compatible(self, name: str, version: str) -> None:
        if name not in self.known:
            raise ValidationError("unknown_schema")
        if version.split(".", 1)[0] != self.known[name].split(".", 1)[0]:
            raise ValidationError("incompatible_schema_major")


def _coerce_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _coerce_optional_float(value: Any) -> float | None:
    if value in {None, "", "None", "null"}:
        return None
    return float(value)


def _coerce_optional_int(value: Any) -> int | None:
    if value in {None, "", "None", "null"}:
        return None
    return int(value)


def load_fixture(path: Path, requested_as_of: str) -> tuple[list[Bar], list[GateRecord], dict[str, Any]]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".csv":
        rows = list(csv.DictReader(text.splitlines()))
    elif suffix == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    elif suffix == ".json":
        parsed = json.loads(text)
        rows = parsed["records"] if isinstance(parsed, dict) and "records" in parsed else parsed
    else:
        raise ValidationError("unsupported_fixture_format")
    bars: list[Bar] = []
    quarantine: list[GateRecord] = []
    runtime = ContractRuntime()
    for index, row in enumerate(rows):
        try:
            normalized = dict(row)
            for key in ("open", "high", "low", "close", "volume"):
                normalized[key] = float(normalized[key]) if normalized.get(key) not in {None, ""} else None
            for key in ("suspended", "is_st", "adjusted"):
                normalized[key] = _coerce_bool(normalized.get(key, False))
            for key in ("limit_reference_price", "contra_liquidity_quantity"):
                if key in normalized:
                    normalized[key] = _coerce_optional_float(normalized[key])
            if "listing_trading_day_number" in normalized:
                normalized["listing_trading_day_number"] = _coerce_optional_int(normalized["listing_trading_day_number"])
            if "fillability_observed" in normalized and normalized["fillability_observed"] not in {None, ""}:
                normalized["fillability_observed"] = _coerce_bool(normalized["fillability_observed"])
            normalized = {key: value for key, value in normalized.items() if value != ""}
            normalized.setdefault("event_id", f"{normalized.get('symbol', 'unknown')}:{index}")
            bar = Bar(**normalized)
            runtime.validate_bar(bar, requested_as_of)
            bars.append(bar)
        except (KeyError, TypeError, ValidationError, ValueError) as error:
            quarantine.append(GateRecord(str(row.get("event_id", f"row:{index}")), "QUARANTINED", str(error)))
    manifest = {
        "dataset_id": path.stem,
        "dataset_hash": hashlib.sha256(text.encode()).hexdigest(),
        "record_count": len(bars),
        "quarantine_count": len(quarantine),
        "license": "CC0-1.0 synthetic fixture",
        "synthetic": True,
        "formats_supported": ["csv", "json", "jsonl"],
    }
    return bars, quarantine, manifest


class DeterministicReplay:
    def __init__(self, requested_as_of: str, run_id: str, trace_id: str) -> None:
        self.requested_as_of, self.run_id, self.trace_id = requested_as_of, run_id, trace_id
        self.runtime = ContractRuntime()

    def run(self, bars: Iterable[Bar], checkpoint_path: Path | None = None, resume: bool = False) -> ReplayResult:
        seen: set[Any] = set()
        near_seen: dict[tuple[str, str], Bar] = {}
        quarantine: list[GateRecord] = []
        accepted: list[Bar] = []
        for bar in bars:
            try:
                self.runtime.validate_bar(bar, self.requested_as_of)
                fingerprint = digest(bar.payload())
                if bar.event_id in seen or fingerprint in seen:
                    quarantine.append(GateRecord(bar.event_id, "DUPLICATE", "idempotency_key_seen"))
                    continue
                near_key = (bar.symbol, bar.event_time)
                if near_key in near_seen and abs(near_seen[near_key].close - bar.close) <= 0.001:
                    quarantine.append(GateRecord(bar.event_id, "NEAR_DUPLICATE", "same_symbol_time_near_price"))
                    continue
                seen.update({bar.event_id, fingerprint})
                near_seen[near_key] = bar
                accepted.append(bar)
            except ValidationError as error:
                quarantine.append(GateRecord(bar.event_id, "QUARANTINED", str(error)))
        ordered = sorted(accepted, key=lambda item: (parse_time(item.event_time), item.symbol, item.event_id))
        start = 0
        input_hash = digest([bar.payload() for bar in ordered])
        if resume and checkpoint_path and checkpoint_path.exists():
            checkpoint = json.loads(checkpoint_path.read_text())
            if checkpoint.get("input_hash") != input_hash:
                raise ValidationError("checkpoint_input_mismatch")
            start = int(checkpoint["next_index"])
        ledger = []
        for index, bar in enumerate(ordered):
            if index < start:
                continue
            ledger.append(
                {
                    "local_sequence": index + 1,
                    "event_id": bar.event_id,
                    "event_time": bar.event_time,
                    "available_at": bar.available_at,
                    "envelope": self.runtime.envelope(bar, self.run_id, self.trace_id),
                }
            )
            if checkpoint_path:
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                checkpoint_path.write_text(
                    canonical(
                        {
                            "next_index": index + 1,
                            "input_hash": input_hash,
                            "last_event_id": bar.event_id,
                            "run_id": self.run_id,
                        }
                    )
                )
        return ReplayResult(
            ordered,
            ledger,
            quarantine,
            {"next_index": len(ordered), "input_hash": input_hash, "run_id": self.run_id},
        )


def candidate_signals(events: list[Bar]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    history: list[Bar] = []
    for bar in events:
        if len(history) >= 2:
            unknown = sorted(
                {
                    field_name
                    for item in (history[-2], history[-1], bar)
                    for field_name in ("volume", "suspended", "is_st")
                    if getattr(item, field_name) is None
                }
            )
            if unknown:
                result.append(
                    {
                        "signal_id": f"signal:{bar.event_id}",
                        "symbol": bar.symbol,
                        "event_id": bar.event_id,
                        "available_at": bar.available_at,
                        "action": "ABSTAIN",
                        "confidence": 0.0,
                        "features": {"momentum_2": None, "volume_ratio_2": None, "breakout_2": None},
                        "status": "candidate",
                        "reason": "REQUIRED_MARKET_SEMANTICS_UNKNOWN",
                        "unknown_fields": unknown,
                        "failure_conditions": ["required_market_semantics_unknown", "no_execution_adapter"],
                    }
                )
                history.append(bar)
                continue
        if len(history) >= 2 and bar.suspended is False:
            momentum = bar.close / history[-2].close - 1.0
            volume_ratio = bar.volume / max(1.0, (history[-1].volume + history[-2].volume) / 2.0)
            breakout = bar.close > max(history[-1].high, history[-2].high)
            score = (1 if momentum > 0 else -1) + (1 if volume_ratio >= 1 else 0) + (1 if breakout else 0)
            action = "BUY_CANDIDATE" if score >= 2 else "SELL_CANDIDATE" if score <= -1 else "ABSTAIN"
            result.append(
                {
                    "signal_id": f"signal:{bar.event_id}",
                    "symbol": bar.symbol,
                    "event_id": bar.event_id,
                    "available_at": bar.available_at,
                    "action": action,
                    "confidence": round(min(0.9, 0.35 + abs(score) * 0.15), 2),
                    "features": {
                        "momentum_2": round(momentum, 6),
                        "volume_ratio_2": round(volume_ratio, 6),
                        "breakout_2": breakout,
                    },
                    "status": "candidate",
                    "failure_conditions": ["synthetic_dataset", "historical_bar_only", "no_execution_adapter"],
                }
            )
        history.append(bar)
    return result


def _calendar_from_config(config: SimulationConfig) -> TradingCalendar | None:
    # OBSERVED_EVENT_DATES are intentionally absent from this function.
    if config.trading_calendar is not None and config.trading_days is not None:
        return None
    if config.trading_calendar is not None:
        return config.trading_calendar
    if config.trading_days is not None and config.calendar_source_ref:
        return TradingCalendar(
            "R143-EXPLICIT-SCENARIO-CALENDAR",
            "A_SHARE",
            tuple(config.trading_days),
            config.calendar_source_ref,
            "SYNTHETIC_SCENARIO",
            "EXPLICIT_SIMULATION_CONFIG",
        )
    return None


def _reference_for_bar(bar: Bar, snapshot_id: str) -> LimitReferencePrice | None:
    if bar.limit_reference_price is None:
        return None
    return LimitReferencePrice(
        bar.limit_reference_price,
        bar.limit_reference_price_kind or "OFFICIAL_PREVIOUS_CLOSE",
        bar.limit_reference_source or "",
        bar.trading_day.isoformat(),
        snapshot_id,
    )


def _fillability_evidence_for_bar(bar: Bar) -> FillabilityEvidence | None:
    if not bar.fillability_evidence_kind or bar.fillability_observed is None:
        return None
    return FillabilityEvidence(
        bar.fillability_evidence_id or f"fill:{bar.event_id}",
        bar.fillability_evidence_source or bar.source_id,
        bar.observed_at,
        bar.fillability_observed,
        bar.fillability_evidence_kind,
        bar.contra_liquidity_quantity,
    )


def simulate_portfolio(
    events: list[Bar],
    signals: list[dict[str, Any]],
    config: SimulationConfig,
    requested_as_of: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Research ledger with PIT rule, governed calendar and lot-level T+1 gates."""
    ordered_signals = sorted(signals, key=lambda item: (parse_time(item["available_at"]), item["signal_id"]))
    signal_index = 0
    eligible: dict[str, dict[str, Any]] = {}
    cash, turnover = config.initial_cash, 0.0
    inventory = SettlementAwareInventory()
    ledger: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    calendar = _calendar_from_config(config)
    lot_counter = 0

    for bar in events:
        while signal_index < len(ordered_signals) and parse_time(
            ordered_signals[signal_index]["available_at"]
        ) <= parse_time(bar.event_time):
            candidate = ordered_signals[signal_index]
            eligible[candidate["symbol"]] = candidate
            signal_index += 1
        signal = eligible.pop(bar.symbol, None)
        if not signal or signal["action"] == "ABSTAIN":
            continue

        action, reason, executed, quantity = signal["action"], None, False, 0
        snapshot_id, price_state, fill_state = None, None, None
        rule_source_ref, rule_publication_date = None, None

        if bar.volume is None or bar.suspended is None or bar.is_st is None:
            reason = "REQUIRED_MARKET_SEMANTICS_UNKNOWN"
        elif bar.suspended:
            reason = "SUSPENDED"
        else:
            gate = replay_gate(
                resolver=DEFAULT_RULE_RESOLVER,
                exchange=_exchange_code(bar.exchange),
                board=bar.board,
                security_status=bar.security_status,
                trading_day=bar.trading_day.isoformat(),
                calendar=calendar,
                session=bar.replay_session,
                listing_trading_day_number=bar.listing_trading_day_number,
                knowledge_cutoff=requested_as_of,
            )
            if not gate.allowed:
                reason = gate.reason
            else:
                snapshot_id = gate.rule_snapshot_id
                snapshot = DEFAULT_RULE_RESOLVER.resolve(
                    _exchange_code(bar.exchange),
                    bar.board,
                    bar.security_status,
                    bar.trading_day.isoformat(),
                    bar.listing_trading_day_number,
                    requested_as_of,
                )
                rule_source_ref = snapshot.source_ref
                rule_publication_date = snapshot.publication_date
                try:
                    validity = evaluate_price_validity(
                        bar.close,
                        snapshot,
                        _reference_for_bar(bar, snapshot.rule_snapshot_id),
                        bar.trading_day,
                    )
                    price_state = validity.state.value
                except RuleGateError as exc:
                    reason = str(exc)
                    validity = None
                if validity is not None and not validity.valid:
                    reason = "PRICE_INVALID_OUTSIDE_LIMIT"
                elif validity is not None and (validity.at_upper_limit or validity.at_lower_limit):
                    fillability = evaluate_order_fillability(
                        validity,
                        _fillability_evidence_for_bar(bar),
                        config.conservative_no_fill_at_limit,
                    )
                    fill_state = fillability.state.value
                    if fillability.state == FillabilityState.ORDER_FILLABILITY_UNKNOWN:
                        reason = fillability.state.value
                    elif fillability.state == FillabilityState.SCENARIO_ASSUMPTION_NO_FILL:
                        reason = fillability.state.value
                    elif fillability.fillable is False:
                        reason = "ORDER_FILLABILITY_EVIDENCE_CONFIRMED_NO_FILL"

                if reason is None and action == "BUY_CANDIDATE":
                    budget = min(cash, config.initial_cash * config.max_position_weight)
                    fill = bar.close * (1 + (config.fixed_slippage_bps + config.volume_impact_bps) / 10_000)
                    quantity = int(budget // fill)
                    fee = max(config.min_commission, quantity * fill * config.commission_bps / 10_000) if quantity else 0
                    if quantity <= 0 or quantity * fill + fee > cash:
                        reason = "INSUFFICIENT_CASH"
                    elif turnover + quantity * fill / config.initial_cash > config.max_turnover:
                        reason = "MAX_TURNOVER"
                    else:
                        cash -= quantity * fill + fee
                        turnover += quantity * fill / config.initial_cash
                        lot_counter += 1
                        inventory.acquire(bar.symbol, quantity, bar.trading_day, f"lot-{lot_counter}")
                        executed = True
                elif reason is None and action == "SELL_CANDIDATE":
                    total = inventory.total_quantity(bar.symbol)
                    sellable = (
                        inventory.sellable_quantity(bar.symbol, bar.trading_day, calendar)
                        if total and calendar is not None
                        else 0
                    )
                    if total <= 0:
                        reason = "NO_POSITION"
                    elif sellable <= 0:
                        reason = "T_PLUS_ONE_LOCK"
                    else:
                        quantity = sellable
                        fill = bar.close * (1 - (config.fixed_slippage_bps + config.volume_impact_bps) / 10_000)
                        fee = max(config.min_commission, quantity * fill * config.commission_bps / 10_000)
                        fee += quantity * fill * config.stamp_duty_bps_sell / 10_000
                        if _exchange_code(bar.exchange) == "SSE":
                            fee += quantity * fill * config.transfer_fee_bps_sh / 10_000
                        inventory.sell(bar.symbol, quantity, bar.trading_day, calendar)
                        cash += quantity * fill - fee
                        turnover += quantity * fill / config.initial_cash
                        executed = True

        decision = {
            "event_id": bar.event_id,
            "symbol": bar.symbol,
            "action": action,
            "research_only": True,
            "no_trade_gate": config.no_trade_gate,
            "executed_in_simulation": executed,
            "reason": reason,
            "quantity": quantity,
            "rule_snapshot_id": snapshot_id,
            "rule_source_ref": rule_source_ref,
            "rule_publication_date": rule_publication_date,
            "requested_as_of": requested_as_of,
            "price_validity_state": price_state,
            "order_fillability_state": fill_state,
            "trading_calendar_source_ref": calendar.source_ref if calendar else None,
        }
        decisions.append(decision)
        sellable_after = 0
        if (
            calendar is not None
            and calendar.is_trading_day(bar.trading_day)
            and inventory.total_quantity(bar.symbol)
        ):
            sellable_after = inventory.sellable_quantity(bar.symbol, bar.trading_day, calendar)
        ledger.append(
            {
                **decision,
                "cash_after": round(cash, 2),
                "position_after": inventory.total_quantity(bar.symbol),
                "sellable_after": sellable_after,
                "inventory_lots": inventory.snapshot(bar.symbol),
                "turnover_after": round(turnover, 6),
                "rule_version": config.rule_version,
                "zero_market_impact_baseline_assumption": config.volume_impact_bps == 0.0,
            }
        )
    return ledger, decisions


def validate(events: list[Bar], portfolio_ledger: list[dict[str, Any]], config: SimulationConfig) -> dict[str, Any]:
    unknown = sorted(
        {
            field_name
            for bar in events
            for field_name in ("volume", "suspended", "is_st")
            if getattr(bar, field_name) is None
        }
    )
    if unknown:
        return {
            "validation_status": "ABSTAIN",
            "reason": "required_market_semantics_unknown",
            "unknown_fields": unknown,
            "executed_simulated_actions": 0,
            "cost_proxy": 0.0,
            "research_only": True,
        }
    if len(events) < 6:
        return {
            "validation_status": "ABSTAIN",
            "reason": "insufficient_temporal_observations",
            "research_only": True,
        }
    ordered = sorted(events, key=lambda item: parse_time(item.event_time))
    n = len(ordered)
    split = {
        "train": [ordered[0].event_id, ordered[n // 2 - 1].event_id],
        "validation": [ordered[n // 2].event_id, ordered[(3 * n) // 4 - 1].event_id],
        "test": [ordered[(3 * n) // 4].event_id, ordered[-1].event_id],
    }
    executed = [item for item in portfolio_ledger if item["executed_in_simulation"]]
    rejected = [item for item in portfolio_ledger if not item["executed_in_simulation"]]
    return {
        "validation_status": "EXPERIMENTAL_ONLY",
        "time_split": split,
        "walk_forward_windows": max(1, n - 4),
        "random_shuffle": False,
        "executed_simulated_actions": len(executed),
        "abstentions_or_rejections": len(rejected),
        "cost_proxy": len(executed) * config.min_commission,
        "cost_before_result": "not_economic_evidence",
        "cost_after_result": "not_economic_evidence",
        "robustness": "not_proven_on_synthetic_fixture",
        "research_only": True,
        "zero_market_impact_baseline_assumption": config.volume_impact_bps == 0.0,
    }


@dataclass
class KnowledgeAtom:
    atom_id: str
    content: str
    status: str
    source_refs: list[str]
    evidence_quality: str
    gpt_access: str = "FULL_SEMANTIC_ACCESS"
    transport_visibility: str = "PUBLIC_SAFE"
    relations: list[dict[str, str]] = field(default_factory=list)


class KnowledgeGateway:
    HARD_SECRET_MARKERS = ("api_key", "token=", "password", "private_key", "cookie")

    def __init__(self, atoms: list[KnowledgeAtom], revision: str = "synthetic-r1") -> None:
        self.atoms, self.revision = atoms, revision

    def query(self, text: str, budget: int, statuses: set[str] | None = None) -> dict[str, Any]:
        if any(marker in text.lower() for marker in self.HARD_SECRET_MARKERS):
            return {
                "query_id": digest(text)[:16],
                "abstention": "DENIED_HARD_SECRET",
                "atoms": [],
                "omitted_due_to_context_budget": [],
                "knowledge_revision": self.revision,
            }
        allowed = statuses or {"candidate", "approved"}
        tokens = set(text.lower().split())
        chosen, omitted, used = [], [], 0
        for atom in sorted(self.atoms, key=lambda item: item.atom_id):
            if (
                atom.status not in allowed
                or atom.gpt_access != "FULL_SEMANTIC_ACCESS"
                or not tokens.intersection(atom.content.lower().split())
            ):
                continue
            cost = max(1, len(atom.content) // 4)
            if used + cost > budget:
                omitted.append(atom.atom_id)
                continue
            chosen.append(asdict(atom))
            used += cost
        return {
            "query_id": digest({"text": text, "budget": budget})[:16],
            "knowledge_revision": self.revision,
            "atoms": chosen,
            "relations": [relation for atom in chosen for relation in atom["relations"]],
            "conflicts": [],
            "unknowns": [],
            "source_lineage": [source for atom in chosen for source in atom["source_refs"]],
            "omitted_due_to_context_budget": omitted,
            "context_budget_report": {"budget": budget, "used": used},
            "gpt_access": "FULL_SEMANTIC_ACCESS",
        }


def learning_packet(run_manifest: dict[str, Any], validation_report: dict[str, Any], evidence_hash: str) -> dict[str, Any]:
    packet = {
        "packet_id": "lp-" + digest({"run": run_manifest["run_id"], "evidence": evidence_hash})[:16],
        "packet_content_hash": "",
        "idempotency_key": "",
        "base_knowledge_revision": "synthetic-r1",
        "processor_version": "p2-offline-r143",
        "status": "candidate",
        "authority_write": False,
        "facts": ["offline synthetic replay completed"],
        "constraints": ["research_only", "NO_TRADE", "synthetic_not_market_evidence"],
        "validation": validation_report,
        "evidence_refs": [evidence_hash],
        "evidence_quality": "synthetic_fixture",
        "relations": [{"type": "evidence:SUPPORTS", "target": run_manifest["run_id"]}],
    }
    packet["packet_content_hash"] = digest(
        {key: value for key, value in packet.items() if key not in {"packet_content_hash", "idempotency_key"}}
    )
    packet["idempotency_key"] = packet["packet_id"] + "-" + packet["packet_content_hash"][:12]
    return packet


class OfflineResearchRunner:
    def __init__(
        self,
        fixture: Path,
        output_dir: Path,
        requested_as_of: str = "2026-01-31T23:59:59Z",
        trading_calendar: TradingCalendar | None = None,
    ) -> None:
        self.fixture = fixture
        self.output_dir = output_dir
        self.requested_as_of = requested_as_of
        self.trading_calendar = trading_calendar
        self.run_id = "run-" + digest({"fixture": fixture.name, "as_of": requested_as_of})[:16]
        self.trace_id = "trace-" + self.run_id[-12:]

    def run(self, resume: bool = False) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        bars, ingest_quarantine, dataset_manifest = load_fixture(self.fixture, self.requested_as_of)
        replay = DeterministicReplay(self.requested_as_of, self.run_id, self.trace_id).run(
            bars,
            self.output_dir / "checkpoint.json",
            resume,
        )
        signals = candidate_signals(replay.events)
        cfg = SimulationConfig(trading_calendar=self.trading_calendar)
        portfolio, decisions = simulate_portfolio(replay.events, signals, cfg, self.requested_as_of)
        report = validate(replay.events, portfolio, cfg)
        knowledge = KnowledgeGateway(
            [
                KnowledgeAtom(
                    "atom-signal",
                    "candidate momentum volume breakout signal from synthetic replay",
                    "candidate",
                    [dataset_manifest["dataset_hash"]],
                    "synthetic_fixture",
                ),
                KnowledgeAtom(
                    "atom-risk",
                    "T+1 suspension price validity fillability and cost constraints remain research only",
                    "candidate",
                    ["C2_A_SHARE_RULE_SNAPSHOT"],
                    "synthetic_fixture",
                ),
            ]
        )
        context = knowledge.query("momentum volume T+1", 200)
        run_manifest = {
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "research_only": True,
            "no_trade_gate": True,
            "fixture": self.fixture.name,
            "dataset_hash": dataset_manifest["dataset_hash"],
            "event_hash": replay.core_hash,
            "code_version": "p2-offline-r143",
            "requested_as_of": self.requested_as_of,
            "trading_calendar_source_ref": self.trading_calendar.source_ref if self.trading_calendar else None,
            "governed_calendar_required": True,
        }
        evidence = {
            "run_manifest": run_manifest,
            "dataset_manifest": dataset_manifest,
            "capability_decisions": [asdict(item) for item in ingest_quarantine + replay.quarantine],
            "replay_event_ledger": replay.event_ledger,
            "research_decision_ledger": decisions,
            "portfolio_ledger": portfolio,
            "validation_report": report,
            "context_bundle": context,
            "unknowns": [
                "Synthetic fixture is not a real-market evidence source",
                "No private/local knowledge gateway is implemented in public repository",
            ],
        }
        evidence_hash = digest(evidence)
        packet = learning_packet(run_manifest, report, evidence_hash)
        artifacts = {
            "RunManifest.json": run_manifest,
            "DatasetManifest.json": dataset_manifest,
            "ConfigurationSnapshot.json": asdict(cfg),
            "CapabilityDecisionLog.json": evidence["capability_decisions"],
            "ReplayEventLedger.json": replay.event_ledger,
            "ResearchDecisionLedger.json": decisions,
            "PortfolioLedger.json": portfolio,
            "ValidationReport.json": report,
            "EvidenceLedger.json": evidence,
            "ContextBundle.json": context,
            "LearningPacket.json": packet,
        }
        hashes: dict[str, str] = {}
        for name, payload in artifacts.items():
            (self.output_dir / name).write_text(canonical(payload) + "\n")
            hashes[name] = digest(payload)
        bundle = {
            "run_id": self.run_id,
            "content_hashes": hashes,
            "evidence_hash": evidence_hash,
            "rollback": "delete output directory; no external state changed",
            "status": "CANDIDATE_RESEARCH_ONLY",
        }
        (self.output_dir / "ReproducibilityBundleManifest.json").write_text(canonical(bundle) + "\n")
        return {
            "run_manifest": run_manifest,
            "validation_report": report,
            "bundle": bundle,
            "packet": packet,
            "output_dir": str(self.output_dir),
        }
