"""Mapping from governed .day records into the existing P2 replay authority."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from local_adapter.contracts import SourceManifest, canonical_hash
from offline_research.engine import (
    Bar,
    DeterministicReplay,
    SimulationConfig,
    candidate_signals,
    simulate_portfolio,
    validate,
)

from .tdx_day import ParsedDayDataset


SHANGHAI = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class CloseAvailabilityPolicy:
    version: str = "ashare-daily-close-plus-1s-v1"
    delay_seconds: int = 1

    def timestamps(self, trade_date: str) -> tuple[str, str]:
        day = datetime.strptime(trade_date, "%Y-%m-%d").date()
        event = datetime.combine(day, time(15, 0), tzinfo=SHANGHAI)
        available = event + timedelta(seconds=self.delay_seconds)
        return _utc(event), _utc(available)


@dataclass(frozen=True)
class ReplayReceipt:
    schema_version: str
    run_id: str
    trace_id: str
    source_manifest_id: str
    artifact_sha256: str
    symbol: str
    exchange: str
    source_record_count: int
    accepted_bar_count: int
    parser_quarantine_count: int
    replay_quarantine_count: int
    duplicate_date_count: int
    out_of_order_count: int
    nonzero_reserved_count: int
    amount_float_candidate_count: int
    amount_float_invalid_count: int
    zero_volume_count: int
    first_date: str | None
    last_date: str | None
    parse_core_hash: str
    replay_core_hash: str
    replay_input_hash: str
    availability_policy_version: str
    source_validation_status: str
    strategy_validation_status: str
    validation_report: dict[str, Any]
    unknowns: tuple[str, ...]
    research_only: bool = True
    no_trade_gate: bool = True
    authority_write: bool = False
    raw_records_exported: bool = False

    def public_payload(self) -> dict[str, Any]:
        return asdict(self)


def to_p2_bars(
    parsed: ParsedDayDataset,
    manifest: SourceManifest,
    *,
    symbol: str,
    exchange: str,
    requested_as_of: str,
    availability_policy: CloseAvailabilityPolicy | None = None,
) -> list[Bar]:
    policy = availability_policy or CloseAvailabilityPolicy()
    bars: list[Bar] = []
    for record in parsed.records:
        event_time, available_at = policy.timestamps(record.trade_date)
        event_id = "bar-" + canonical_hash({
            "manifest": manifest.manifest_id,
            "artifact": parsed.report.artifact_sha256,
            "symbol": symbol,
            "date": record.trade_date,
            "ohlc": [record.open_raw, record.high_raw, record.low_raw, record.close_raw],
            "volume_vendor_raw": record.volume_vendor_raw,
        })[:20]
        bars.append(Bar(
            event_id=event_id,
            symbol=symbol,
            exchange=exchange,
            event_time=event_time,
            available_at=available_at,
            observed_at=available_at,
            receive_time=available_at,
            entered_system_at=available_at,
            as_of=requested_as_of,
            open=record.open,
            high=record.high,
            low=record.low,
            close=record.close,
            volume=float(record.volume_vendor_raw),
            suspended=False,
            is_st=False,
            adjusted=manifest.adjusted,
            adjustment_method=manifest.adjustment_method,
            limit_rule_version=manifest.limit_rule_version,
            source_id=manifest.source_id,
            dataset_version=parsed.report.artifact_sha256[:16],
            license=manifest.license,
            capability_level="HISTORICAL_BAR",
            entitlement_status=manifest.capability.entitlement_status,
            corporate_action_note="unknown_in_local_day_structure",
        ))
    return bars


def run_p2_replay(
    parsed: ParsedDayDataset,
    manifest: SourceManifest,
    *,
    symbol: str,
    exchange: str,
    requested_as_of: str,
    config: SimulationConfig | None = None,
) -> ReplayReceipt:
    simulation = config or SimulationConfig(no_trade_gate=True)
    policy = CloseAvailabilityPolicy()
    bars = to_p2_bars(
        parsed,
        manifest,
        symbol=symbol,
        exchange=exchange,
        requested_as_of=requested_as_of,
        availability_policy=policy,
    )
    identity = {
        "manifest": manifest.manifest_id,
        "artifact": parsed.report.artifact_sha256,
        "symbol": symbol,
        "exchange": exchange,
        "as_of": requested_as_of,
        "availability_policy": policy.version,
        "config": asdict(simulation),
    }
    run_id = "run-" + canonical_hash(identity)[:20]
    trace_id = "trace-" + canonical_hash({"run_id": run_id})[:16]
    replay = DeterministicReplay(requested_as_of, run_id, trace_id).run(bars)
    signals = candidate_signals(replay.events)
    portfolio, _ = simulate_portfolio(replay.events, signals, simulation)
    p2_validation = validate(replay.events, portfolio, simulation)
    p2_validation = {
        **p2_validation,
        "source_validation_status": "PARTIALLY_VERIFIED",
        "strategy_validation_status": p2_validation.get("validation_status", "ABSTAIN"),
        "authority_write": False,
        "no_trade_gate": True,
        "economic_or_alpha_claim": "NOT_ESTABLISHED",
        "field_semantics_gate": {
            "amount": "EXCLUDED_AMBIGUOUS",
            "volume": "VENDOR_VALUE_USED_FOR_CANDIDATE_RATIO_UNIT_UNKNOWN",
            "reserved": "EXCLUDED_UNKNOWN",
        },
    }
    unknowns = (
        "historical_st_status_not_proven_by_day_structure",
        "suspension_status_not_proven_by_day_structure",
        "corporate_action_and_adjustment_semantics_not_fully_proven",
        "volume_unit_unknown",
        "amount_and_reserved_excluded_from_features",
        "no_market_validity_or_profitability_claim",
    )
    return ReplayReceipt(
        schema_version="1.0.0",
        run_id=run_id,
        trace_id=trace_id,
        source_manifest_id=manifest.manifest_id,
        artifact_sha256=parsed.report.artifact_sha256,
        symbol=symbol,
        exchange=exchange,
        source_record_count=parsed.report.source_record_count,
        accepted_bar_count=len(replay.events),
        parser_quarantine_count=parsed.report.quarantined_record_count,
        replay_quarantine_count=len(replay.quarantine),
        duplicate_date_count=parsed.report.duplicate_date_count,
        out_of_order_count=parsed.report.out_of_order_count,
        nonzero_reserved_count=parsed.report.nonzero_reserved_count,
        amount_float_candidate_count=parsed.report.amount_float_candidate_count,
        amount_float_invalid_count=parsed.report.amount_float_invalid_count,
        zero_volume_count=parsed.report.zero_volume_count,
        first_date=parsed.report.first_date,
        last_date=parsed.report.last_date,
        parse_core_hash=parsed.report.parse_core_hash,
        replay_core_hash=replay.core_hash,
        replay_input_hash=replay.checkpoint["input_hash"],
        availability_policy_version=policy.version,
        source_validation_status="PARTIALLY_VERIFIED",
        strategy_validation_status=p2_validation["strategy_validation_status"],
        validation_report=p2_validation,
        unknowns=unknowns,
    )


def _utc(value: datetime) -> str:
    return value.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
