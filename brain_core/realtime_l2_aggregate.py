"""Governed A-share realtime L2 aggregate semantics.

This module does not call TongDaXin, brokers, crawlers, or trading interfaces.
It only normalizes already-captured TDX/TdxQuant aggregate payloads into a
traceable evidence envelope that downstream code can treat as snapshot-level
or aggregate-level evidence, never as raw tick/order streams.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any

from .contracts import clamp, now_iso


SCHEMA_VERSION = "a-share-l2-aggregate-v0.2"
FIELD_SEMANTICS_VERSION = "tdx-l2-aggregate-verified-2026-07-16"
CLASSIFIER_LIFECYCLE_VERSION = "broker-market-data-classifier-v0.2"


@dataclass(frozen=True)
class L2AggregateFieldSpec:
    raw_name: str
    normalized_name: str
    semantic_group: str
    value_kind: str
    normalized_layer: str
    description: str
    not_equivalent_to: tuple[str, ...] = ()
    delta_supported_by_default: bool = False
    session_reset_rule: str = "unknown"
    vendor_defined: bool = False


TDX_L2_AGGREGATE_FIELD_SPECS: dict[str, L2AggregateFieldSpec] = {
    "L2TicNum": L2AggregateFieldSpec(
        raw_name="L2TicNum",
        normalized_name="l2_trade_count_aggregate",
        semantic_group="l2_aggregate_counter",
        value_kind="cumulative_or_instant_unknown",
        normalized_layer="source_specific_fields",
        description="Aggregate L2 trade-count metric; not a list of trades.",
        not_equivalent_to=("RAW_TRADE_TICK", "TradePrint"),
    ),
    "L2OrderNum": L2AggregateFieldSpec(
        raw_name="L2OrderNum",
        normalized_name="l2_order_count_aggregate",
        semantic_group="l2_aggregate_counter",
        value_kind="cumulative_or_instant_unknown",
        normalized_layer="source_specific_fields",
        description="Aggregate L2 order-count metric; not raw order events.",
        not_equivalent_to=("RAW_ORDER_EVENT", "OrderEvent"),
    ),
    "TotalBVol": L2AggregateFieldSpec(
        raw_name="TotalBVol",
        normalized_name="total_buy_volume_aggregate",
        semantic_group="l2_volume_aggregate",
        value_kind="cumulative_or_instant_unknown",
        normalized_layer="source_specific_fields",
        description="Total buy-side aggregate volume; unit must remain source-specific until verified.",
    ),
    "TotalSVol": L2AggregateFieldSpec(
        raw_name="TotalSVol",
        normalized_name="total_sell_volume_aggregate",
        semantic_group="l2_volume_aggregate",
        value_kind="cumulative_or_instant_unknown",
        normalized_layer="source_specific_fields",
        description="Total sell-side aggregate volume; unit must remain source-specific until verified.",
    ),
    "BCancel": L2AggregateFieldSpec(
        raw_name="BCancel",
        normalized_name="buy_cancel_aggregate",
        semantic_group="l2_cancel_aggregate",
        value_kind="cumulative_or_instant_unknown",
        normalized_layer="source_specific_fields",
        description="Aggregate buy cancel metric; not a single cancel event stream.",
        not_equivalent_to=("CANCEL_EVENT", "RAW_ORDER_EVENT"),
    ),
    "SCancel": L2AggregateFieldSpec(
        raw_name="SCancel",
        normalized_name="sell_cancel_aggregate",
        semantic_group="l2_cancel_aggregate",
        value_kind="cumulative_or_instant_unknown",
        normalized_layer="source_specific_fields",
        description="Aggregate sell cancel metric; not a single cancel event stream.",
        not_equivalent_to=("CANCEL_EVENT", "RAW_ORDER_EVENT"),
    ),
    "Zjl": L2AggregateFieldSpec(
        raw_name="Zjl",
        normalized_name="vendor_main_force_metric",
        semantic_group="vendor_fund_flow",
        value_kind="vendor_derived",
        normalized_layer="VendorFundFlowSnapshot",
        description="Vendor-defined main-force metric; not exchange-native DDX/DDY truth.",
        not_equivalent_to=("TRUE_DDX", "TRUE_DDY", "EXCHANGE_ORDER_FLOW"),
        vendor_defined=True,
    ),
    "Zjl_HB": L2AggregateFieldSpec(
        raw_name="Zjl_HB",
        normalized_name="vendor_main_force_ratio_metric",
        semantic_group="vendor_fund_flow",
        value_kind="vendor_derived",
        normalized_layer="VendorFundFlowSnapshot",
        description="Vendor-defined main-force ratio/inflow metric; not exchange-native DDX/DDY truth.",
        not_equivalent_to=("TRUE_DDX", "TRUE_DDY", "EXCHANGE_ORDER_FLOW"),
        vendor_defined=True,
    ),
    "OpenAmo": L2AggregateFieldSpec(
        raw_name="OpenAmo",
        normalized_name="opening_amount_aggregate",
        semantic_group="auction_open_aggregate",
        value_kind="instant_or_session_aggregate",
        normalized_layer="source_specific_fields",
        description="Opening amount aggregate.",
    ),
    "OpenZTBuy": L2AggregateFieldSpec(
        raw_name="OpenZTBuy",
        normalized_name="open_limit_up_buy_aggregate",
        semantic_group="auction_open_aggregate",
        value_kind="instant_or_session_aggregate",
        normalized_layer="source_specific_fields",
        description="Limit-up buy aggregate; not complete auction unmatched quantity trajectory.",
        not_equivalent_to=("AUCTION_TRAJECTORY", "UNMATCHED_ORDER_FLOW"),
    ),
    "Wtb": L2AggregateFieldSpec(
        raw_name="Wtb",
        normalized_name="commission_ratio_metric",
        semantic_group="vendor_commission_metric",
        value_kind="vendor_derived",
        normalized_layer="source_specific_fields",
        description="Commission-ratio style metric; route-specific semantics must be preserved.",
        vendor_defined=True,
    ),
    "FzAmo": L2AggregateFieldSpec(
        raw_name="FzAmo",
        normalized_name="minute_amount_aggregate",
        semantic_group="minute_aggregate",
        value_kind="instant_or_session_aggregate",
        normalized_layer="source_specific_fields",
        description="Minute amount aggregate.",
    ),
    "VOpenZAF": L2AggregateFieldSpec(
        raw_name="VOpenZAF",
        normalized_name="opening_change_metric",
        semantic_group="auction_open_aggregate",
        value_kind="vendor_derived",
        normalized_layer="source_specific_fields",
        description="Opening change metric; exact semantics remain source-version specific.",
        vendor_defined=True,
    ),
}

BLOCKED_RAW_CAPABILITIES = (
    "TEN_LEVEL_SNAPSHOT",
    "RAW_TRADE_TICK",
    "RAW_ORDER_EVENT",
    "ORDER_QUEUE",
    "CANCEL_EVENT",
    "AUCTION_TRAJECTORY",
)

BROKER_CAPABILITY_FIELD_MAP = {
    "five_level_book": "FIVE_LEVEL_SNAPSHOT",
    "ten_level_book": "TEN_LEVEL_SNAPSHOT",
    "l2_aggregate": "L2_AGGREGATE",
    "raw_trade_tick": "RAW_TRADE_TICK",
    "raw_order_event": "RAW_ORDER_EVENT",
    "order_queue": "ORDER_QUEUE",
    "cancel_event": "CANCEL_EVENT",
    "auction_trajectory": "AUCTION_TRAJECTORY",
    "historical_l2_archive": "HISTORICAL_L2_ARCHIVE",
}

RAW_CAPABILITY_EVIDENCE_REQUIREMENTS = {
    "RAW_TRADE_TICK": ("sample_payload_path", "field_list_path", "sdk_doc_path"),
    "RAW_ORDER_EVENT": ("sample_payload_path", "field_list_path", "sdk_doc_path"),
    "ORDER_QUEUE": ("sample_payload_path", "field_list_path", "sdk_doc_path"),
    "CANCEL_EVENT": ("sample_payload_path", "field_list_path", "sdk_doc_path"),
    "AUCTION_TRAJECTORY": ("sample_payload_path", "field_list_path", "sdk_doc_path"),
}

PRE_PROBE_CLASSIFIER_STATUSES = (
    "insufficient",
    "needs_documentation",
    "qualified_for_readonly_probe",
    "blocked",
)
FUTURE_CLASSIFIER_STATUSES = (
    "runtime_probe_failed",
    "runtime_verified_research_only",
    "approved_for_governed_integration",
)
DOCUMENTATION_GATED_CAPABILITIES = (
    "FIVE_LEVEL_SNAPSHOT",
    "TEN_LEVEL_SNAPSHOT",
    "L2_AGGREGATE",
)


@dataclass
class RawMarketPayload:
    source: str
    symbol: str
    market: str = "CN-A"
    payload: dict[str, Any] = field(default_factory=dict)
    receive_time: str = field(default_factory=now_iso)
    local_sequence: int = 0
    source_version: str = ""
    entitlement: str = "local_l2_display_entitled"
    capability_level: list[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def payload_hash(self) -> str:
        raw = json.dumps(self.payload, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _to_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_yes(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"yes", "true", "available", "supported", "included", "1", "y"}


def _is_no(value: Any) -> bool:
    if isinstance(value, bool):
        return not value
    text = str(value or "").strip().lower()
    return text in {"no", "false", "unavailable", "unsupported", "not_supported", "0", "n"}


def _has_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def _missing_kind(value: Any, numeric_value: float | None, *, key_present: bool = True) -> str:
    if not key_present:
        return "missing"
    if value is None:
        return "missing"
    if isinstance(value, str):
        text = value.strip()
        lower = text.lower()
        if text == "":
            return "empty"
        if lower in {"permission_denied", "permission denied", "no_permission", "not_entitled", "unauthorized"}:
            return "permission_denied"
        if lower in {"interface_error", "error", "api_error", "timeout", "failed"}:
            return "interface_error"
        if lower in {"not_applicable", "n/a", "na", "null"}:
            return "not_applicable"
        if lower in {"unknown", "unknown_sentinel", "--", "-", "nan"}:
            return "unknown_sentinel"
    if numeric_value == 0:
        return "zero_value"
    if numeric_value is not None:
        return "present_numeric"
    return "present_non_numeric"


def _has_supporting_documentation(evidence_files: dict[str, Any]) -> bool:
    return any(
        _has_text(evidence_files.get(field))
        for field in ("field_list_path", "sdk_doc_path", "sample_payload_path")
    )


def normalize_tdx_l2_aggregate_payload(
    payload: dict[str, Any],
    *,
    symbol: str,
    source: str = "tdxquant_get_more_info",
    source_version: str = "tdxquant_v1.0.4_get_more_info",
    receive_time: str | None = None,
    local_sequence: int = 0,
) -> dict[str, Any]:
    """Normalize verified TDX aggregate fields without overstating capability."""

    raw = RawMarketPayload(
        source=source,
        symbol=str(symbol or "").upper(),
        payload=dict(payload or {}),
        receive_time=receive_time or now_iso(),
        local_sequence=max(0, int(local_sequence or 0)),
        source_version=source_version,
        capability_level=["L2_AGGREGATE"],
    )
    fields: list[dict[str, Any]] = []
    missing: list[str] = []
    missing_details: list[dict[str, Any]] = []
    for raw_name, spec in TDX_L2_AGGREGATE_FIELD_SPECS.items():
        if raw_name not in raw.payload:
            missing.append(raw_name)
            missing_details.append(
                {
                    "raw_name": spec.raw_name,
                    "normalized_name": spec.normalized_name,
                    "missing_kind": "missing",
                    "field_semantics_version": FIELD_SEMANTICS_VERSION,
                }
            )
            continue
        value = raw.payload.get(raw_name)
        numeric_value = _to_number(value)
        missing_kind = _missing_kind(value, numeric_value)
        fields.append(
            {
                "raw_name": spec.raw_name,
                "normalized_name": spec.normalized_name,
                "value": value,
                "numeric_value": numeric_value,
                "semantic_group": spec.semantic_group,
                "value_kind": spec.value_kind,
                "normalized_layer": spec.normalized_layer,
                "description": spec.description,
                "vendor_defined": spec.vendor_defined,
                "delta_supported": spec.delta_supported_by_default,
                "session_reset_rule": spec.session_reset_rule,
                "missing_kind": missing_kind,
                "field_semantics_version": FIELD_SEMANTICS_VERSION,
                "not_equivalent_to": list(spec.not_equivalent_to),
            }
        )

    source_reliability = 0.84 if fields else 0.45
    validation_status = "verified_aggregate_fields_present" if fields else "missing_verified_aggregate_fields"
    return {
        "raw_payload": {
            "source": raw.source,
            "source_version": raw.source_version,
            "entitlement": raw.entitlement,
            "symbol": raw.symbol,
            "market": raw.market,
            "receive_time": raw.receive_time,
            "local_sequence": raw.local_sequence,
            "raw_payload_hash": raw.payload_hash(),
            "schema_version": raw.schema_version,
            "field_semantics_version": FIELD_SEMANTICS_VERSION,
            "capability_level": list(raw.capability_level),
        },
        "aggregate_fields": fields,
        "missing_verified_fields": missing,
        "missing_field_details": missing_details,
        "blocked_capabilities": list(BLOCKED_RAW_CAPABILITIES),
        "quality": {
            "quality_score": clamp(0.72 + min(len(fields), 13) * 0.01, 0.0, 0.85),
            "evidence_level": "runtime_verified_aggregate" if fields else "schema_only",
            "source_reliability": source_reliability,
            "freshness": 1.0,
            "validation_status": validation_status,
            "status": "Experimental",
            "human_reviewed": False,
        },
        "governance": {
            "research_only": True,
            "live_trading_enabled": False,
            "true_ddx_ddy_connected": False,
            "raw_tick_verified": False,
            "raw_order_verified": False,
            "crawler_allowed_role": "auxiliary_crosscheck_only",
            "summary": (
                "TDX L2 aggregates are usable as governed snapshot/aggregate evidence. "
                "They do not prove ten-level depth, raw trade ticks, raw order events, order queue, "
                "single cancel events, or auction trajectory."
            ),
        },
    }


def compute_l2_aggregate_deltas(
    previous_result: dict[str, Any],
    current_result: dict[str, Any],
    *,
    same_trading_day: bool = True,
    reset_confirmed: bool = False,
) -> dict[str, Any]:
    """Compute conservative numeric deltas from normalized aggregate payloads.

    A-share L2 aggregate counters can reset across sessions or route restarts.
    A decrease inside an unconfirmed same-day stream is treated as an anomaly,
    not as a negative delta.
    """

    previous_fields = {
        item.get("raw_name"): item
        for item in previous_result.get("aggregate_fields", [])
        if isinstance(item, dict)
    }
    current_fields = {
        item.get("raw_name"): item
        for item in current_result.get("aggregate_fields", [])
        if isinstance(item, dict)
    }
    deltas: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    for raw_name, current in current_fields.items():
        previous = previous_fields.get(raw_name)
        current_value = current.get("numeric_value")
        previous_value = previous.get("numeric_value") if previous else None
        if current_value is None or previous_value is None:
            deltas.append(
                {
                    "raw_name": raw_name,
                    "delta": None,
                    "delta_status": "not_computable",
                }
            )
            continue
        if current_value >= previous_value:
            deltas.append(
                {
                    "raw_name": raw_name,
                    "delta": current_value - previous_value,
                    "delta_status": "computed_same_stream",
                }
            )
            continue
        if not same_trading_day or reset_confirmed:
            deltas.append(
                {
                    "raw_name": raw_name,
                    "delta": current_value,
                    "delta_status": "reset_allowed",
                }
            )
            continue
        anomaly = {
            "raw_name": raw_name,
            "previous": previous_value,
            "current": current_value,
            "reason": "cumulative_value_decreased_without_confirmed_reset",
        }
        anomalies.append(anomaly)
        deltas.append(
            {
                "raw_name": raw_name,
                "delta": None,
                "delta_status": "anomaly_no_delta",
                "anomaly": anomaly,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "field_semantics_version": FIELD_SEMANTICS_VERSION,
        "same_trading_day": bool(same_trading_day),
        "reset_confirmed": bool(reset_confirmed),
        "deltas": deltas,
        "anomalies": anomalies,
        "quality": {
            "validation_status": "delta_anomaly" if anomalies else "delta_computed",
            "status": "Experimental",
        },
    }


def low_cost_broker_permission_questions() -> list[dict[str, Any]]:
    """Questions for WorkBuddy/user to ask brokers without exposing account data."""

    return [
        {
            "topic": "market_data_entitlement",
            "question": "Does the quant API include Shanghai/Shenzhen Level-2 market data for my account tier?",
            "must_answer_fields": ["five_level", "ten_level", "raw_trade_tick", "raw_order_event", "order_queue", "auction_trajectory"],
        },
        {
            "topic": "api_surface",
            "question": "Which SDK/API surfaces are available: QMT, PTrade, XTP, broker proprietary API, or vendor gateway?",
            "must_answer_fields": ["sdk_name", "python_supported", "local_terminal_required", "paper_trading_supported"],
        },
        {
            "topic": "cost_and_license",
            "question": "What is the minimum asset, fee, or monthly package needed for L2 data, and can it be used for local research automation?",
            "must_answer_fields": ["monthly_cost", "asset_threshold", "redistribution_allowed", "local_storage_allowed"],
        },
        {
            "topic": "field_semantics",
            "question": "Are timestamps exchange timestamps or local/vendor receive timestamps, and are sequence numbers provided?",
            "must_answer_fields": ["exchange_time", "sequence_no", "channel_no", "reset_rule", "correction_stream"],
        },
        {
            "topic": "risk_boundary",
            "question": "Can the market-data API be used without enabling order/account functions in the same process?",
            "must_answer_fields": ["market_data_only_mode", "forbidden_order_calls", "paper_mode", "audit_log"],
        },
    ]


def public_crawler_auxiliary_policy() -> dict[str, Any]:
    return {
        "role": "auxiliary_crosscheck_only",
        "usage_class": "auxiliary_crosscheck_only",
        "allowed_uses": [
            "quote price crosscheck",
            "volume or amount sanity check",
            "news/context enrichment",
            "vendor-fund-flow comparison when source terms are preserved",
        ],
        "forbidden_uses": [
            "promoting a route to RAW_TRADE_TICK",
            "promoting a route to RAW_ORDER_EVENT",
            "clearing a_share_proxy_guard_clear by itself",
            "calling vendor-defined fund flow true DDX/DDY",
            "redistributing scraped raw data",
        ],
        "required_labels": ["governed_snapshot", "vendor_defined", "auxiliary_evidence"],
        "evidence_quality_options": ["official", "licensed_vendor", "public_portal", "unofficial", "unknown"],
        "dynamic_reliability_fields": [
            "delay_ms",
            "missing_rate",
            "timestamp_quality",
            "staleness_rate",
            "cross_source_consistency",
            "license_status",
        ],
        "default_quality": {
            "quality_score": 0.45,
            "source_reliability": 0.55,
            "default_reliability_hint": 0.55,
            "reliability_calibration_status": "uncalibrated",
            "evidence_quality": "unknown",
            "validation_status": "auxiliary_only",
            "status": "Experimental",
            "measurement_note": "source_reliability is a conservative hint, not a measured reliability score",
        },
    }


def classify_broker_market_data_response(response: dict[str, Any]) -> dict[str, Any]:
    """Classify a broker reply without contacting the broker or trading system.

    The classifier is intentionally conservative. It can mark raw L2 routes as
    candidates, but it does not promote them to verified until WorkBuddy attaches
    docs, field lists, and sample payload evidence.
    """

    response = dict(response or {})
    capabilities = dict(response.get("capabilities", {}) or {})
    timestamps = dict(response.get("timestamp_semantics", {}) or {})
    license_info = dict(response.get("license", {}) or {})
    evidence_files = dict(response.get("evidence_files", {}) or {})
    cost = dict(response.get("cost", {}) or {})
    route_isolation = dict(response.get("route_isolation", {}) or {})

    allowed: list[str] = []
    candidate: list[str] = []
    blocked: list[dict[str, Any]] = []
    warnings: list[str] = []
    evidence_gaps: list[str] = []
    lifecycle_notes: list[str] = []
    score = 0

    readonly_process_supported = _is_yes(
        route_isolation.get("readonly_process_supported", response.get("readonly_process_supported"))
    )
    method_whitelist_supported = _is_yes(
        route_isolation.get("method_whitelist_supported", response.get("method_whitelist_supported"))
    )
    separate_market_data_entitlement = _is_yes(
        route_isolation.get("separate_market_data_entitlement", response.get("separate_market_data_entitlement"))
    )
    trading_password_required = _is_yes(
        route_isolation.get("trading_password_required", response.get("trading_password_required"))
    )
    trading_counter_required = _is_yes(
        route_isolation.get("trading_counter_required", response.get("trading_counter_required"))
    )
    isolation_supported = (
        readonly_process_supported
        or method_whitelist_supported
        or separate_market_data_entitlement
        or _is_yes(response.get("market_data_only_mode"))
    )

    if _is_yes(response.get("market_data_only_mode")) or isolation_supported:
        score += 10
    else:
        warnings.append("market_data_only_mode_not_confirmed")

    if _is_yes(response.get("sdk_contains_trading_methods")):
        warnings.append("sdk_contains_trading_methods_requires_readonly_isolation")

    if _is_yes(response.get("account_or_order_functions_required")) and not isolation_supported:
        blocked.append(
            {
                "capability": "route",
                "reason": "market data requires account/order functions and no read-only isolation was confirmed",
            }
        )
    elif not _is_no(response.get("account_or_order_functions_required")):
        warnings.append("account_or_order_requirement_unknown")

    if (trading_password_required or trading_counter_required) and not isolation_supported:
        blocked.append(
            {
                "capability": "route",
                "reason": "market data path requires trading password or trading counter without isolation",
            }
        )
    elif trading_password_required:
        warnings.append("trading_password_requirement_mitigated_by_isolation_claim")
    elif trading_counter_required:
        warnings.append("trading_counter_requirement_mitigated_by_isolation_claim")

    if _is_yes(license_info.get("local_storage_allowed")):
        score += 8
    elif _is_no(license_info.get("local_storage_allowed")):
        warnings.append("local_storage_not_allowed_view_only_not_automatable")
        evidence_gaps.append("local_storage_allowed")
    else:
        warnings.append("local_storage_license_not_confirmed")
        evidence_gaps.append("local_storage_allowed")

    if _is_yes(license_info.get("automation_allowed")):
        score += 8
    elif _is_no(license_info.get("automation_allowed")):
        warnings.append("automation_not_allowed")
        evidence_gaps.append("automation_allowed")
    else:
        warnings.append("automation_license_not_confirmed")
        evidence_gaps.append("automation_allowed")

    if _is_yes(license_info.get("redistribution_allowed")):
        warnings.append("redistribution_allowed_claim_needs_written_terms")
    elif not _is_no(license_info.get("redistribution_allowed")):
        warnings.append("redistribution_terms_unknown")

    if _has_text(cost.get("monthly_fee")) or _has_text(cost.get("asset_threshold")):
        score += 5
    else:
        warnings.append("cost_or_asset_threshold_missing")

    explicit_time_semantics = _is_yes(timestamps.get("exchange_timestamp")) or _has_text(timestamps.get("time_semantics_document"))
    stable_sequence = (
        _is_yes(timestamps.get("sequence_no"))
        or _is_yes(timestamps.get("event_id"))
        or _has_text(timestamps.get("order_key"))
    )

    if _is_yes(timestamps.get("exchange_timestamp")):
        score += 8
    elif _is_yes(timestamps.get("vendor_timestamp")):
        score += 3
        warnings.append("vendor_timestamp_only")
    else:
        warnings.append("source_timestamp_semantics_missing")

    if stable_sequence:
        score += 8
    else:
        warnings.append("sequence_no_not_confirmed")

    for source_field, capability in BROKER_CAPABILITY_FIELD_MAP.items():
        value = capabilities.get(source_field, "unknown")
        if _is_yes(value):
            has_docs_or_sample = _has_supporting_documentation(evidence_files)
            if capability in DOCUMENTATION_GATED_CAPABILITIES and not has_docs_or_sample:
                candidate.append(capability)
                evidence_gaps.append(f"{capability}:field_table_or_sdk_doc_or_sample_payload")
                blocked.append(
                    {
                        "capability": capability,
                        "reason": "capability claim lacks official field table, SDK doc, or sanitized sample payload",
                    }
                )
                continue
            if capability in RAW_CAPABILITY_EVIDENCE_REQUIREMENTS:
                missing = [
                    field
                    for field in RAW_CAPABILITY_EVIDENCE_REQUIREMENTS[capability]
                    if not _has_text(evidence_files.get(field))
                ]
                if not explicit_time_semantics:
                    missing.append("explicit_time_semantics")
                if not stable_sequence:
                    missing.append("stable_sequence_or_event_key")
                if capability in {"RAW_ORDER_EVENT", "ORDER_QUEUE", "CANCEL_EVENT"}:
                    for field in (
                        "channel_no",
                        "day_start_baseline_path",
                        "order_book_recovery_path",
                        "disconnect_recovery_doc_path",
                    ):
                        if field == "channel_no":
                            if not (_is_yes(timestamps.get("channel_no")) or _has_text(timestamps.get("channel_no"))):
                                missing.append(field)
                        elif not _has_text(evidence_files.get(field)):
                            missing.append(field)
                if missing:
                    candidate.append(capability)
                    evidence_gaps.extend(f"{capability}:{field}" for field in missing)
                    blocked.append(
                        {
                            "capability": capability,
                            "reason": "broker claimed support but required evidence files are missing",
                            "missing_evidence": missing,
                        }
                    )
                else:
                    candidate.append(capability)
                    score += 10
                continue
            allowed.append(capability)
            score += 6 if capability != "HISTORICAL_L2_ARCHIVE" else 4
        elif _is_no(value):
            blocked.append({"capability": capability, "reason": "broker reported unsupported"})
        else:
            blocked.append({"capability": capability, "reason": "unknown"})

    if _has_text(evidence_files.get("field_list_path")):
        score += 5
    else:
        evidence_gaps.append("field_list_path")
    if _has_text(evidence_files.get("sdk_doc_path")):
        score += 5
    else:
        evidence_gaps.append("sdk_doc_path")
    if _has_text(evidence_files.get("license_terms_path")):
        score += 5
    else:
        evidence_gaps.append("license_terms_path")
    if _has_text(evidence_files.get("sample_payload_path")):
        score += 8
    else:
        evidence_gaps.append("sample_payload_path")

    score = int(clamp(score / 100.0, 0.0, 1.0) * 100)
    raw_candidates = [item for item in candidate if item in RAW_CAPABILITY_EVIDENCE_REQUIREMENTS]
    if blocked and any(item.get("capability") == "route" for item in blocked):
        route_status = "blocked"
    elif raw_candidates and not any(str(item).startswith(tuple(raw_candidates)) for item in evidence_gaps) and _is_yes(license_info.get("local_storage_allowed")) and _is_yes(license_info.get("automation_allowed")):
        route_status = "qualified_for_readonly_probe"
    elif allowed or candidate:
        route_status = "needs_documentation"
    else:
        route_status = "insufficient"
    if route_status not in PRE_PROBE_CLASSIFIER_STATUSES:
        route_status = "needs_documentation"
        lifecycle_notes.append("unexpected_status_downgraded_to_pre_probe_lifecycle")

    return {
        "broker_name": str(response.get("broker_name", "") or ""),
        "official_product_name": str(response.get("official_product_name", "") or ""),
        "route_status": route_status,
        "classifier_lifecycle_version": CLASSIFIER_LIFECYCLE_VERSION,
        "allowed_pre_probe_statuses": list(PRE_PROBE_CLASSIFIER_STATUSES),
        "future_statuses_not_emitted": list(FUTURE_CLASSIFIER_STATUSES),
        "score": score,
        "allowed_capabilities": allowed,
        "candidate_capabilities": candidate,
        "blocked_capabilities": blocked,
        "evidence_gaps": sorted(set(evidence_gaps)),
        "warnings": sorted(set(warnings)),
        "lifecycle_notes": sorted(set(lifecycle_notes)),
        "route_isolation": {
            "readonly_process_supported": readonly_process_supported,
            "method_whitelist_supported": method_whitelist_supported,
            "separate_market_data_entitlement": separate_market_data_entitlement,
            "trading_password_required": trading_password_required,
            "trading_counter_required": trading_counter_required,
        },
        "quality": {
            "quality_score": score / 100.0,
            "evidence_level": "broker_reply",
            "source_reliability": 0.72 if route_status == "qualified_for_readonly_probe" else 0.58,
            "validation_status": route_status,
            "status": "Experimental" if route_status != "blocked" else "Frozen",
            "human_reviewed": False,
        },
        "governance": {
            "research_only": True,
            "live_trading_enabled": False,
            "requires_workbuddy_sample_pack": bool(raw_candidates),
            "requires_codex_runtime_validation": bool(raw_candidates),
            "public_crawler_role": "auxiliary_crosscheck_only",
            "summary": (
                "Broker reply classified conservatively. Raw L2 capabilities remain candidates "
                "until field docs, sample payloads, timestamp semantics, and license terms are verified."
            ),
        },
    }
