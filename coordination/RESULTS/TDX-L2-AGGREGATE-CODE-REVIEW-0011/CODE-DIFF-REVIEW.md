# CODE-DIFF-REVIEW

## Scope

Review task: `TDX-L2-AGGREGATE-CODE-REVIEW-0011`.
Reviewed implementation task: `TDX-L2-AGGREGATE-EXHAUST-0010`.

This review did not modify business code. It generated review artifacts under `coordination/RESULTS/TDX-L2-AGGREGATE-CODE-REVIEW-0011`.

## Baseline Limitation

`F:/aidanao` is not currently a Git repository and no byte-for-byte pre-0010 snapshot was found in this review. Therefore:

- `realtime_l2_aggregate.py` is reported as a full added-file diff.
- `foundation_data_governance.py` is reported as a reconstructed patch based on the current touched block and prior implementation notes.
- `test_realtime_l2_aggregate.py` is reported as a full added/changed test file diff.
- `test_foundation_data_governance.py` was reviewed but appears not modified by 0010.
- SHA256 before values are marked `unavailable:no_git_or_backup_baseline` in `FILE-HASH-MANIFEST.csv`.

## Actual Modified File List From 0010/Follow-up

Code and tests:

- `brain_core/realtime_l2_aggregate.py`
- `brain_core/foundation_data_governance.py`
- `tests/test_realtime_l2_aggregate.py`

Task and handoff files:

- `coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/BROKER-LOW-COST-MARKET-DATA-REQUEST.md`
- `coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/BROKER-OUTREACH-MESSAGE.md`
- `coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/BROKER-RESPONSE-SCHEMA.json`
- `coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/BROKER-ROUTE-SCORECARD.csv`
- `coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/BROKER-RESPONSE-CLASSIFICATION.md`
- `coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/PUBLIC-CRAWLER-AUXILIARY-EVIDENCE-POLICY.md`
- `coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/TDX-L2-AGGREGATE-FIELD-MAPPING.md`
- `coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/HANDOFF.md`
- `coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/STATUS.yaml`

Writebacks:

- `bulletin/super-second-brain-v01-board.md`
- `data/super_brain_v01.sqlite`
- `data/audit/events.jsonl`

## Scope Outside Files

Yes, there were disclosed mother-system writebacks to SQLite, JSONL audit log, and bulletin. No real market-data runtime, TdxQuant, TDX MCP, TongDaXin directory, account, or trade interface was touched during this review.

## Full Added Diff: brain_core/realtime_l2_aggregate.py

```diff
diff --git a/brain_core/realtime_l2_aggregate.py b/brain_core/realtime_l2_aggregate.py
new file mode 100644
--- /dev/null
+++ b/brain_core/realtime_l2_aggregate.py
@@
+"""Governed A-share realtime L2 aggregate semantics.
+
+This module does not call TongDaXin, brokers, crawlers, or trading interfaces.
+It only normalizes already-captured TDX/TdxQuant aggregate payloads into a
+traceable evidence envelope that downstream code can treat as snapshot-level
+or aggregate-level evidence, never as raw tick/order streams.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, field
+import hashlib
+import json
+from typing import Any
+
+from .contracts import clamp, now_iso
+
+
+SCHEMA_VERSION = "a-share-l2-aggregate-v0.1"
+FIELD_SEMANTICS_VERSION = "tdx-l2-aggregate-verified-2026-07-16"
+
+
+@dataclass(frozen=True)
+class L2AggregateFieldSpec:
+    raw_name: str
+    normalized_name: str
+    semantic_group: str
+    value_kind: str
+    normalized_layer: str
+    description: str
+    not_equivalent_to: tuple[str, ...] = ()
+    delta_supported_by_default: bool = False
+    session_reset_rule: str = "unknown"
+    vendor_defined: bool = False
+
+
+TDX_L2_AGGREGATE_FIELD_SPECS: dict[str, L2AggregateFieldSpec] = {
+    "L2TicNum": L2AggregateFieldSpec(
+        raw_name="L2TicNum",
+        normalized_name="l2_trade_count_aggregate",
+        semantic_group="l2_aggregate_counter",
+        value_kind="cumulative_or_instant_unknown",
+        normalized_layer="source_specific_fields",
+        description="Aggregate L2 trade-count metric; not a list of trades.",
+        not_equivalent_to=("RAW_TRADE_TICK", "TradePrint"),
+    ),
+    "L2OrderNum": L2AggregateFieldSpec(
+        raw_name="L2OrderNum",
+        normalized_name="l2_order_count_aggregate",
+        semantic_group="l2_aggregate_counter",
+        value_kind="cumulative_or_instant_unknown",
+        normalized_layer="source_specific_fields",
+        description="Aggregate L2 order-count metric; not raw order events.",
+        not_equivalent_to=("RAW_ORDER_EVENT", "OrderEvent"),
+    ),
+    "TotalBVol": L2AggregateFieldSpec(
+        raw_name="TotalBVol",
+        normalized_name="total_buy_volume_aggregate",
+        semantic_group="l2_volume_aggregate",
+        value_kind="cumulative_or_instant_unknown",
+        normalized_layer="source_specific_fields",
+        description="Total buy-side aggregate volume; unit must remain source-specific until verified.",
+    ),
+    "TotalSVol": L2AggregateFieldSpec(
+        raw_name="TotalSVol",
+        normalized_name="total_sell_volume_aggregate",
+        semantic_group="l2_volume_aggregate",
+        value_kind="cumulative_or_instant_unknown",
+        normalized_layer="source_specific_fields",
+        description="Total sell-side aggregate volume; unit must remain source-specific until verified.",
+    ),
+    "BCancel": L2AggregateFieldSpec(
+        raw_name="BCancel",
+        normalized_name="buy_cancel_aggregate",
+        semantic_group="l2_cancel_aggregate",
+        value_kind="cumulative_or_instant_unknown",
+        normalized_layer="source_specific_fields",
+        description="Aggregate buy cancel metric; not a single cancel event stream.",
+        not_equivalent_to=("CANCEL_EVENT", "RAW_ORDER_EVENT"),
+    ),
+    "SCancel": L2AggregateFieldSpec(
+        raw_name="SCancel",
+        normalized_name="sell_cancel_aggregate",
+        semantic_group="l2_cancel_aggregate",
+        value_kind="cumulative_or_instant_unknown",
+        normalized_layer="source_specific_fields",
+        description="Aggregate sell cancel metric; not a single cancel event stream.",
+        not_equivalent_to=("CANCEL_EVENT", "RAW_ORDER_EVENT"),
+    ),
+    "Zjl": L2AggregateFieldSpec(
+        raw_name="Zjl",
+        normalized_name="vendor_main_force_metric",
+        semantic_group="vendor_fund_flow",
+        value_kind="vendor_derived",
+        normalized_layer="VendorFundFlowSnapshot",
+        description="Vendor-defined main-force metric; not exchange-native DDX/DDY truth.",
+        not_equivalent_to=("TRUE_DDX", "TRUE_DDY", "EXCHANGE_ORDER_FLOW"),
+        vendor_defined=True,
+    ),
+    "Zjl_HB": L2AggregateFieldSpec(
+        raw_name="Zjl_HB",
+        normalized_name="vendor_main_force_ratio_metric",
+        semantic_group="vendor_fund_flow",
+        value_kind="vendor_derived",
+        normalized_layer="VendorFundFlowSnapshot",
+        description="Vendor-defined main-force ratio/inflow metric; not exchange-native DDX/DDY truth.",
+        not_equivalent_to=("TRUE_DDX", "TRUE_DDY", "EXCHANGE_ORDER_FLOW"),
+        vendor_defined=True,
+    ),
+    "OpenAmo": L2AggregateFieldSpec(
+        raw_name="OpenAmo",
+        normalized_name="opening_amount_aggregate",
+        semantic_group="auction_open_aggregate",
+        value_kind="instant_or_session_aggregate",
+        normalized_layer="source_specific_fields",
+        description="Opening amount aggregate.",
+    ),
+    "OpenZTBuy": L2AggregateFieldSpec(
+        raw_name="OpenZTBuy",
+        normalized_name="open_limit_up_buy_aggregate",
+        semantic_group="auction_open_aggregate",
+        value_kind="instant_or_session_aggregate",
+        normalized_layer="source_specific_fields",
+        description="Limit-up buy aggregate; not complete auction unmatched quantity trajectory.",
+        not_equivalent_to=("AUCTION_TRAJECTORY", "UNMATCHED_ORDER_FLOW"),
+    ),
+    "Wtb": L2AggregateFieldSpec(
+        raw_name="Wtb",
+        normalized_name="commission_ratio_metric",
+        semantic_group="vendor_commission_metric",
+        value_kind="vendor_derived",
+        normalized_layer="source_specific_fields",
+        description="Commission-ratio style metric; route-specific semantics must be preserved.",
+        vendor_defined=True,
+    ),
+    "FzAmo": L2AggregateFieldSpec(
+        raw_name="FzAmo",
+        normalized_name="minute_amount_aggregate",
+        semantic_group="minute_aggregate",
+        value_kind="instant_or_session_aggregate",
+        normalized_layer="source_specific_fields",
+        description="Minute amount aggregate.",
+    ),
+    "VOpenZAF": L2AggregateFieldSpec(
+        raw_name="VOpenZAF",
+        normalized_name="opening_change_metric",
+        semantic_group="auction_open_aggregate",
+        value_kind="vendor_derived",
+        normalized_layer="source_specific_fields",
+        description="Opening change metric; exact semantics remain source-version specific.",
+        vendor_defined=True,
+    ),
+}
+
+BLOCKED_RAW_CAPABILITIES = (
+    "TEN_LEVEL_SNAPSHOT",
+    "RAW_TRADE_TICK",
+    "RAW_ORDER_EVENT",
+    "ORDER_QUEUE",
+    "CANCEL_EVENT",
+    "AUCTION_TRAJECTORY",
+)
+
+BROKER_CAPABILITY_FIELD_MAP = {
+    "five_level_book": "FIVE_LEVEL_SNAPSHOT",
+    "ten_level_book": "TEN_LEVEL_SNAPSHOT",
+    "l2_aggregate": "L2_AGGREGATE",
+    "raw_trade_tick": "RAW_TRADE_TICK",
+    "raw_order_event": "RAW_ORDER_EVENT",
+    "order_queue": "ORDER_QUEUE",
+    "cancel_event": "CANCEL_EVENT",
+    "auction_trajectory": "AUCTION_TRAJECTORY",
+    "historical_l2_archive": "HISTORICAL_L2_ARCHIVE",
+}
+
+RAW_CAPABILITY_EVIDENCE_REQUIREMENTS = {
+    "RAW_TRADE_TICK": ("sample_payload_path", "field_list_path"),
+    "RAW_ORDER_EVENT": ("sample_payload_path", "field_list_path", "sdk_doc_path"),
+    "ORDER_QUEUE": ("sample_payload_path", "field_list_path", "sdk_doc_path"),
+    "CANCEL_EVENT": ("sample_payload_path", "field_list_path", "sdk_doc_path"),
+    "AUCTION_TRAJECTORY": ("sample_payload_path", "field_list_path", "sdk_doc_path"),
+}
+
+
+@dataclass
+class RawMarketPayload:
+    source: str
+    symbol: str
+    market: str = "CN-A"
+    payload: dict[str, Any] = field(default_factory=dict)
+    receive_time: str = field(default_factory=now_iso)
+    local_sequence: int = 0
+    source_version: str = ""
+    entitlement: str = "local_l2_display_entitled"
+    capability_level: list[str] = field(default_factory=list)
+    schema_version: str = SCHEMA_VERSION
+
+    def payload_hash(self) -> str:
+        raw = json.dumps(self.payload, ensure_ascii=False, sort_keys=True, default=str)
+        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
+
+
+def _to_number(value: Any) -> float | None:
+    if value is None or value == "":
+        return None
+
+
+def _is_yes(value: Any) -> bool:
+    if isinstance(value, bool):
+        return value
+    text = str(value or "").strip().lower()
+    return text in {"yes", "true", "available", "supported", "included", "1", "y"}
+
+
+def _is_no(value: Any) -> bool:
+    if isinstance(value, bool):
+        return not value
+    text = str(value or "").strip().lower()
+    return text in {"no", "false", "unavailable", "unsupported", "not_supported", "0", "n"}
+
+
+def _has_text(value: Any) -> bool:
+    return bool(str(value or "").strip())
+    try:
+        return float(value)
+    except (TypeError, ValueError):
+        return None
+
+
+def normalize_tdx_l2_aggregate_payload(
+    payload: dict[str, Any],
+    *,
+    symbol: str,
+    source: str = "tdxquant_get_more_info",
+    source_version: str = "tdxquant_v1.0.4_get_more_info",
+    receive_time: str | None = None,
+    local_sequence: int = 0,
+) -> dict[str, Any]:
+    """Normalize verified TDX aggregate fields without overstating capability."""
+
+    raw = RawMarketPayload(
+        source=source,
+        symbol=str(symbol or "").upper(),
+        payload=dict(payload or {}),
+        receive_time=receive_time or now_iso(),
+        local_sequence=max(0, int(local_sequence or 0)),
+        source_version=source_version,
+        capability_level=["FIVE_LEVEL_SNAPSHOT", "L2_AGGREGATE", "UPDATE_TRIGGER_COMPATIBLE"],
+    )
+    fields: list[dict[str, Any]] = []
+    missing: list[str] = []
+    for raw_name, spec in TDX_L2_AGGREGATE_FIELD_SPECS.items():
+        if raw_name not in raw.payload:
+            missing.append(raw_name)
+            continue
+        value = raw.payload.get(raw_name)
+        numeric_value = _to_number(value)
+        missing_kind = "zero_value" if numeric_value == 0 else "present"
+        fields.append(
+            {
+                "raw_name": spec.raw_name,
+                "normalized_name": spec.normalized_name,
+                "value": value,
+                "numeric_value": numeric_value,
+                "semantic_group": spec.semantic_group,
+                "value_kind": spec.value_kind,
+                "normalized_layer": spec.normalized_layer,
+                "description": spec.description,
+                "vendor_defined": spec.vendor_defined,
+                "delta_supported": spec.delta_supported_by_default,
+                "session_reset_rule": spec.session_reset_rule,
+                "missing_kind": missing_kind,
+                "field_semantics_version": FIELD_SEMANTICS_VERSION,
+                "not_equivalent_to": list(spec.not_equivalent_to),
+            }
+        )
+
+    source_reliability = 0.84 if fields else 0.45
+    validation_status = "verified_aggregate_fields_present" if fields else "missing_verified_aggregate_fields"
+    return {
+        "raw_payload": {
+            "source": raw.source,
+            "source_version": raw.source_version,
+            "entitlement": raw.entitlement,
+            "symbol": raw.symbol,
+            "market": raw.market,
+            "receive_time": raw.receive_time,
+            "local_sequence": raw.local_sequence,
+            "raw_payload_hash": raw.payload_hash(),
+            "schema_version": raw.schema_version,
+            "field_semantics_version": FIELD_SEMANTICS_VERSION,
+            "capability_level": list(raw.capability_level),
+        },
+        "aggregate_fields": fields,
+        "missing_verified_fields": missing,
+        "blocked_capabilities": list(BLOCKED_RAW_CAPABILITIES),
+        "quality": {
+            "quality_score": clamp(0.72 + min(len(fields), 13) * 0.01, 0.0, 0.85),
+            "evidence_level": "runtime_verified_aggregate" if fields else "schema_only",
+            "source_reliability": source_reliability,
+            "freshness": 1.0,
+            "validation_status": validation_status,
+            "status": "Experimental",
+            "human_reviewed": False,
+        },
+        "governance": {
+            "research_only": True,
+            "live_trading_enabled": False,
+            "true_ddx_ddy_connected": False,
+            "raw_tick_verified": False,
+            "raw_order_verified": False,
+            "crawler_allowed_role": "auxiliary_crosscheck_only",
+            "summary": (
+                "TDX L2 aggregates are usable as governed snapshot/aggregate evidence. "
+                "They do not prove ten-level depth, raw trade ticks, raw order events, order queue, "
+                "single cancel events, or auction trajectory."
+            ),
+        },
+    }
+
+
+def low_cost_broker_permission_questions() -> list[dict[str, Any]]:
+    """Questions for WorkBuddy/user to ask brokers without exposing account data."""
+
+    return [
+        {
+            "topic": "market_data_entitlement",
+            "question": "Does the quant API include Shanghai/Shenzhen Level-2 market data for my account tier?",
+            "must_answer_fields": ["five_level", "ten_level", "raw_trade_tick", "raw_order_event", "order_queue", "auction_trajectory"],
+        },
+        {
+            "topic": "api_surface",
+            "question": "Which SDK/API surfaces are available: QMT, PTrade, XTP, broker proprietary API, or vendor gateway?",
+            "must_answer_fields": ["sdk_name", "python_supported", "local_terminal_required", "paper_trading_supported"],
+        },
+        {
+            "topic": "cost_and_license",
+            "question": "What is the minimum asset, fee, or monthly package needed for L2 data, and can it be used for local research automation?",
+            "must_answer_fields": ["monthly_cost", "asset_threshold", "redistribution_allowed", "local_storage_allowed"],
+        },
+        {
+            "topic": "field_semantics",
+            "question": "Are timestamps exchange timestamps or local/vendor receive timestamps, and are sequence numbers provided?",
+            "must_answer_fields": ["exchange_time", "sequence_no", "channel_no", "reset_rule", "correction_stream"],
+        },
+        {
+            "topic": "risk_boundary",
+            "question": "Can the market-data API be used without enabling order/account functions in the same process?",
+            "must_answer_fields": ["market_data_only_mode", "forbidden_order_calls", "paper_mode", "audit_log"],
+        },
+    ]
+
+
+def public_crawler_auxiliary_policy() -> dict[str, Any]:
+    return {
+        "role": "auxiliary_crosscheck_only",
+        "allowed_uses": [
+            "quote price crosscheck",
+            "volume or amount sanity check",
+            "news/context enrichment",
+            "vendor-fund-flow comparison when source terms are preserved",
+        ],
+        "forbidden_uses": [
+            "promoting a route to RAW_TRADE_TICK",
+            "promoting a route to RAW_ORDER_EVENT",
+            "clearing a_share_proxy_guard_clear by itself",
+            "calling vendor-defined fund flow true DDX/DDY",
+            "redistributing scraped raw data",
+        ],
+        "required_labels": ["governed_snapshot", "vendor_defined", "auxiliary_evidence"],
+        "default_quality": {
+            "quality_score": 0.45,
+            "source_reliability": 0.55,
+            "validation_status": "auxiliary_only",
+            "status": "Experimental",
+        },
+    }
+
+
+def classify_broker_market_data_response(response: dict[str, Any]) -> dict[str, Any]:
+    """Classify a broker reply without contacting the broker or trading system.
+
+    The classifier is intentionally conservative. It can mark raw L2 routes as
+    candidates, but it does not promote them to verified until WorkBuddy attaches
+    docs, field lists, and sample payload evidence.
+    """
+
+    response = dict(response or {})
+    capabilities = dict(response.get("capabilities", {}) or {})
+    timestamps = dict(response.get("timestamp_semantics", {}) or {})
+    license_info = dict(response.get("license", {}) or {})
+    evidence_files = dict(response.get("evidence_files", {}) or {})
+    cost = dict(response.get("cost", {}) or {})
+
+    allowed: list[str] = []
+    candidate: list[str] = []
+    blocked: list[dict[str, Any]] = []
+    warnings: list[str] = []
+    evidence_gaps: list[str] = []
+    score = 0
+
+    if _is_yes(response.get("market_data_only_mode")):
+        score += 10
+    else:
+        warnings.append("market_data_only_mode_not_confirmed")
+
+    if _is_yes(response.get("account_or_order_functions_required")):
+        blocked.append(
+            {
+                "capability": "route",
+                "reason": "broker says account/order functions are required in the same process",
+            }
+        )
+    elif not _is_no(response.get("account_or_order_functions_required")):
+        warnings.append("account_or_order_requirement_unknown")
+
+    if _is_yes(license_info.get("local_storage_allowed")):
+        score += 8
+    else:
+        warnings.append("local_storage_license_not_confirmed")
+
+    if _is_yes(license_info.get("automation_allowed")):
+        score += 8
+    else:
+        warnings.append("automation_license_not_confirmed")
+
+    if _is_yes(license_info.get("redistribution_allowed")):
+        warnings.append("redistribution_allowed_claim_needs_written_terms")
+    elif not _is_no(license_info.get("redistribution_allowed")):
+        warnings.append("redistribution_terms_unknown")
+
+    if _has_text(cost.get("monthly_fee")) or _has_text(cost.get("asset_threshold")):
+        score += 5
+    else:
+        warnings.append("cost_or_asset_threshold_missing")
+
+    if _is_yes(timestamps.get("exchange_timestamp")):
+        score += 8
+    elif _is_yes(timestamps.get("vendor_timestamp")):
+        score += 3
+        warnings.append("vendor_timestamp_only")
+    else:
+        warnings.append("source_timestamp_semantics_missing")
+
+    if _is_yes(timestamps.get("sequence_no")):
+        score += 8
+    else:
+        warnings.append("sequence_no_not_confirmed")
+
+    for source_field, capability in BROKER_CAPABILITY_FIELD_MAP.items():
+        value = capabilities.get(source_field, "unknown")
+        if _is_yes(value):
+            if capability in RAW_CAPABILITY_EVIDENCE_REQUIREMENTS:
+                missing = [
+                    field
+                    for field in RAW_CAPABILITY_EVIDENCE_REQUIREMENTS[capability]
+                    if not _has_text(evidence_files.get(field))
+                ]
+                if missing:
+                    candidate.append(capability)
+                    evidence_gaps.extend(f"{capability}:{field}" for field in missing)
+                    blocked.append(
+                        {
+                            "capability": capability,
+                            "reason": "broker claimed support but required evidence files are missing",
+                            "missing_evidence": missing,
+                        }
+                    )
+                else:
+                    candidate.append(capability)
+                    score += 10
+                continue
+            allowed.append(capability)
+            score += 6 if capability != "HISTORICAL_L2_ARCHIVE" else 4
+        elif _is_no(value):
+            blocked.append({"capability": capability, "reason": "broker reported unsupported"})
+        else:
+            blocked.append({"capability": capability, "reason": "unknown"})
+
+    if _has_text(evidence_files.get("field_list_path")):
+        score += 5
+    else:
+        evidence_gaps.append("field_list_path")
+    if _has_text(evidence_files.get("sdk_doc_path")):
+        score += 5
+    else:
+        evidence_gaps.append("sdk_doc_path")
+    if _has_text(evidence_files.get("license_terms_path")):
+        score += 5
+    else:
+        evidence_gaps.append("license_terms_path")
+    if _has_text(evidence_files.get("sample_payload_path")):
+        score += 8
+    else:
+        evidence_gaps.append("sample_payload_path")
+
+    score = int(clamp(score / 100.0, 0.0, 1.0) * 100)
+    raw_candidates = [item for item in candidate if item in RAW_CAPABILITY_EVIDENCE_REQUIREMENTS]
+    if blocked and any(item.get("capability") == "route" for item in blocked):
+        route_status = "blocked"
+    elif raw_candidates and not any(str(item).startswith(tuple(raw_candidates)) for item in evidence_gaps):
+        route_status = "raw_l2_candidate_needs_runtime_probe"
+    elif allowed or candidate:
+        route_status = "needs_review"
+    else:
+        route_status = "insufficient"
+
+    return {
+        "broker_name": str(response.get("broker_name", "") or ""),
+        "official_product_name": str(response.get("official_product_name", "") or ""),
+        "route_status": route_status,
+        "score": score,
+        "allowed_capabilities": allowed,
+        "candidate_capabilities": candidate,
+        "blocked_capabilities": blocked,
+        "evidence_gaps": sorted(set(evidence_gaps)),
+        "warnings": sorted(set(warnings)),
+        "quality": {
+            "quality_score": score / 100.0,
+            "evidence_level": "broker_reply",
+            "source_reliability": 0.72 if route_status.startswith("raw_l2_candidate") else 0.58,
+            "validation_status": route_status,
+            "status": "Experimental" if route_status != "blocked" else "Frozen",
+            "human_reviewed": False,
+        },
+        "governance": {
+            "research_only": True,
+            "live_trading_enabled": False,
+            "requires_workbuddy_sample_pack": bool(raw_candidates),
+            "requires_codex_runtime_validation": bool(raw_candidates),
+            "public_crawler_role": "auxiliary_crosscheck_only",
+            "summary": (
+                "Broker reply classified conservatively. Raw L2 capabilities remain candidates "
+                "until field docs, sample payloads, timestamp semantics, and license terms are verified."
+            ),
+        },
+    }
```

## Reconstructed Precise Diff: brain_core/foundation_data_governance.py

```diff
diff --git a/brain_core/foundation_data_governance.py b/brain_core/foundation_data_governance.py
--- a/brain_core/foundation_data_governance.py
+++ b/brain_core/foundation_data_governance.py
@@
-        caps["realtime_snapshot"] = _capability(
-            status="available",
-            field_coverage=["price", "change_pct", "volume_ratio", "ddx", "ddy", "quote_ts"],
+        caps["realtime_snapshot"] = _capability(
+            status="available",
+            field_coverage=["price", "change_pct", "volume", "amount", "inside", "outside", "quote_ts"],
@@
         caps["depth_levels"] = _capability(
             status="partial",
             field_coverage=["bids", "asks"],
@@
             license_scope="local_research",
             fallback="treat_depth_as_snapshot_only",
         )
+        caps["l2_aggregate"] = _capability(
+            status="partial",
+            field_coverage=[
+                "L2TicNum",
+                "L2OrderNum",
+                "TotalBVol",
+                "TotalSVol",
+                "BCancel",
+                "SCancel",
+                "Zjl",
+                "Zjl_HB",
+                "OpenAmo",
+                "OpenZTBuy",
+                "Wtb",
+                "FzAmo",
+                "VOpenZAF",
+            ],
+            time_coverage="intraday_aggregate_snapshot",
+            history_start="runtime_only",
+            latency_profile="bridge_or_tdxquant_defined",
+            quality_grade="B",
+            license_scope="local_research",
+            fallback="degrade_to_snapshot_only",
+        )
+        caps["true_ddx_ddy"] = _capability(
+            status="unverified",
+            field_coverage=[],
+            time_coverage="none",
+            history_start="",
+            latency_profile="unknown",
+            quality_grade="C",
+            license_scope="unknown",
+            fallback="treat_vendor_fund_flow_as_vendor_defined_only",
+        )
+        caps["raw_trade_tick"] = _capability(
+            status="unverified",
+            field_coverage=[],
+            time_coverage="none",
+            history_start="",
+            latency_profile="unknown",
+            quality_grade="C",
+            license_scope="unknown",
+            fallback="block_tick_strategies",
+        )
+        caps["raw_order_event"] = _capability(
+            status="unverified",
+            field_coverage=[],
+            time_coverage="none",
+            history_start="",
+            latency_profile="unknown",
+            quality_grade="C",
+            license_scope="unknown",
+            fallback="block_order_event_strategies",
+        )
@@
-                "Uses external TDX MCP field mapping when WorkBuddy provides real samples.",
+                "Uses external TDX MCP / TdxQuant field mapping when WorkBuddy provides real samples.",
+                "Current verified path is five-level snapshot plus L2 aggregate fields; true DDX/DDY remains unverified.",

```

## Full Test Diff: tests/test_realtime_l2_aggregate.py

```diff
diff --git a/tests/test_realtime_l2_aggregate.py b/tests/test_realtime_l2_aggregate.py
new file mode 100644
--- /dev/null
+++ b/tests/test_realtime_l2_aggregate.py
@@
+from __future__ import annotations
+
+import csv
+import json
+from pathlib import Path
+import unittest
+
+from brain_core.foundation_data_governance import TdxMcpSnapshotAdapter
+from brain_core.realtime_l2_aggregate import (
+    BLOCKED_RAW_CAPABILITIES,
+    classify_broker_market_data_response,
+    low_cost_broker_permission_questions,
+    normalize_tdx_l2_aggregate_payload,
+    public_crawler_auxiliary_policy,
+)
+
+
+class RealtimeL2AggregateTests(unittest.TestCase):
+    TASK_DIR = Path(__file__).resolve().parents[1] / "coordination" / "TASKS" / "TDX-L2-AGGREGATE-EXHAUST-0010"
+
+    def test_normalizes_tdx_l2_aggregates_without_promoting_raw_ticks(self):
+        payload = {
+            "L2TicNum": "128",
+            "L2OrderNum": "431",
+            "TotalBVol": "120000",
+            "TotalSVol": "98000",
+            "BCancel": "3000",
+            "SCancel": "2500",
+            "Zjl": "123.45",
+            "Zjl_HB": "0.67",
+            "OpenAmo": "4567.89",
+            "OpenZTBuy": "0",
+            "Wtb": "12.3",
+            "FzAmo": "88.8",
+            "VOpenZAF": "1.2",
+        }
+
+        result = normalize_tdx_l2_aggregate_payload(payload, symbol="300418", local_sequence=7)
+
+        self.assertEqual(result["raw_payload"]["symbol"], "300418")
+        self.assertIn("L2_AGGREGATE", result["raw_payload"]["capability_level"])
+        self.assertEqual(len(result["aggregate_fields"]), 13)
+        self.assertEqual(result["missing_verified_fields"], [])
+        self.assertIn("RAW_TRADE_TICK", result["blocked_capabilities"])
+        self.assertIn("RAW_ORDER_EVENT", result["blocked_capabilities"])
+        self.assertFalse(result["governance"]["raw_tick_verified"])
+        self.assertFalse(result["governance"]["raw_order_verified"])
+        self.assertFalse(result["governance"]["true_ddx_ddy_connected"])
+
+        by_name = {item["raw_name"]: item for item in result["aggregate_fields"]}
+        self.assertIn("RAW_TRADE_TICK", by_name["L2TicNum"]["not_equivalent_to"])
+        self.assertIn("RAW_ORDER_EVENT", by_name["L2OrderNum"]["not_equivalent_to"])
+        self.assertTrue(by_name["Zjl"]["vendor_defined"])
+        self.assertTrue(by_name["Zjl_HB"]["vendor_defined"])
+        self.assertIn("TRUE_DDX", by_name["Zjl"]["not_equivalent_to"])
+
+    def test_tdx_snapshot_adapter_declares_l2_aggregates_but_not_true_ddx(self):
+        descriptor = TdxMcpSnapshotAdapter(root=".", symbol="300418", timeframe="snapshot").capability_descriptor()
+        caps = descriptor.capabilities
+
+        self.assertEqual(caps["realtime_snapshot"]["status"], "available")
+        self.assertIn("inside", caps["realtime_snapshot"]["field_coverage"])
+        self.assertNotIn("ddx", caps["realtime_snapshot"]["field_coverage"])
+        self.assertEqual(caps["l2_aggregate"]["status"], "partial")
+        self.assertIn("L2TicNum", caps["l2_aggregate"]["field_coverage"])
+        self.assertEqual(caps["true_ddx_ddy"]["status"], "unverified")
+        self.assertEqual(caps["raw_trade_tick"]["fallback"], "block_tick_strategies")
+        self.assertEqual(caps["raw_order_event"]["fallback"], "block_order_event_strategies")
+
+    def test_low_cost_broker_questions_cover_required_entitlements(self):
+        questions = low_cost_broker_permission_questions()
+        flattened = " ".join(
+            field for item in questions for field in item.get("must_answer_fields", [])
+        )
+
+        self.assertIn("ten_level", flattened)
+        self.assertIn("raw_trade_tick", flattened)
+        self.assertIn("raw_order_event", flattened)
+        self.assertIn("order_queue", flattened)
+        self.assertIn("market_data_only_mode", flattened)
+
+    def test_public_crawler_policy_stays_auxiliary_only(self):
+        policy = public_crawler_auxiliary_policy()
+
+        self.assertEqual(policy["role"], "auxiliary_crosscheck_only")
+        self.assertIn("promoting a route to RAW_TRADE_TICK", policy["forbidden_uses"])
+        self.assertIn("clearing a_share_proxy_guard_clear by itself", policy["forbidden_uses"])
+        self.assertIn("auxiliary_evidence", policy["required_labels"])
+        self.assertLess(policy["default_quality"]["source_reliability"], 0.6)
+        self.assertIn("RAW_ORDER_EVENT", BLOCKED_RAW_CAPABILITIES)
+
+    def test_broker_outreach_pack_has_schema_and_scorecard_fields(self):
+        schema = json.loads((self.TASK_DIR / "BROKER-RESPONSE-SCHEMA.json").read_text(encoding="utf-8"))
+        self.assertIn("raw_trade_tick", schema["capabilities"])
+        self.assertIn("raw_order_event", schema["capabilities"])
+        self.assertIn("order_queue", schema["capabilities"])
+        self.assertIn("auction_trajectory", schema["capabilities"])
+        self.assertEqual(schema["codex_classification"]["route_status"], "run_classify_broker_market_data_response")
+        self.assertIn("RAW_TRADE_TICK", schema["codex_classification"]["blocked_capabilities"])
+
+        with (self.TASK_DIR / "BROKER-ROUTE-SCORECARD.csv").open("r", encoding="utf-8", newline="") as fh:
+            reader = csv.DictReader(fh)
+            header = reader.fieldnames or []
+        self.assertIn("ten_level_book", header)
+        self.assertIn("raw_trade_tick", header)
+        self.assertIn("raw_order_event", header)
+        self.assertIn("license_risk", header)
+
+    def test_broker_classifier_keeps_raw_l2_claim_in_review_without_evidence(self):
+        response = {
+            "broker_name": "Example Broker",
+            "official_product_name": "Example QMT L2",
+            "market_data_only_mode": "yes",
+            "account_or_order_functions_required": "no",
+            "capabilities": {
+                "five_level_book": "yes",
+                "ten_level_book": "yes",
+                "raw_trade_tick": "yes",
+                "raw_order_event": "yes",
+            },
+            "timestamp_semantics": {
+                "exchange_timestamp": "yes",
+                "sequence_no": "yes",
+            },
+            "license": {
+                "local_storage_allowed": "yes",
+                "automation_allowed": "yes",
+                "redistribution_allowed": "no",
+            },
+            "cost": {"monthly_fee": "low"},
+            "evidence_files": {},
+        }
+
+        result = classify_broker_market_data_response(response)
+
+        self.assertEqual(result["route_status"], "needs_review")
+        self.assertIn("FIVE_LEVEL_SNAPSHOT", result["allowed_capabilities"])
+        self.assertIn("TEN_LEVEL_SNAPSHOT", result["allowed_capabilities"])
+        self.assertIn("RAW_TRADE_TICK", result["candidate_capabilities"])
+        self.assertIn("RAW_ORDER_EVENT", result["candidate_capabilities"])
+        self.assertTrue(any("RAW_TRADE_TICK" in item for item in result["evidence_gaps"]))
+        self.assertTrue(result["governance"]["requires_workbuddy_sample_pack"])
+        self.assertFalse(result["governance"]["live_trading_enabled"])
+
+    def test_broker_classifier_promotes_complete_reply_only_to_runtime_probe_candidate(self):
+        response = {
+            "broker_name": "Example Broker",
+            "official_product_name": "Example XTP L2",
+            "market_data_only_mode": "yes",
+            "account_or_order_functions_required": "no",
+            "capabilities": {
+                "five_level_book": "yes",
+                "ten_level_book": "yes",
+                "l2_aggregate": "yes",
+                "raw_trade_tick": "yes",
+                "raw_order_event": "yes",
+                "order_queue": "yes",
+                "cancel_event": "yes",
+                "auction_trajectory": "yes",
+            },
+            "timestamp_semantics": {
+                "exchange_timestamp": "yes",
+                "sequence_no": "yes",
+                "channel_no": "yes",
+            },
+            "license": {
+                "local_storage_allowed": "yes",
+                "automation_allowed": "yes",
+                "redistribution_allowed": "no",
+                "terms_document": "docs/broker/terms.pdf",
+            },
+            "cost": {"monthly_fee": "low"},
+            "evidence_files": {
+                "field_list_path": "evidence/broker/field-list.md",
+                "sdk_doc_path": "evidence/broker/sdk.md",
+                "sample_payload_path": "evidence/broker/sample.jsonl",
+                "license_terms_path": "evidence/broker/terms.md",
+            },
+        }
+
+        result = classify_broker_market_data_response(response)
+
+        self.assertEqual(result["route_status"], "raw_l2_candidate_needs_runtime_probe")
+        self.assertIn("RAW_TRADE_TICK", result["candidate_capabilities"])
+        self.assertIn("RAW_ORDER_EVENT", result["candidate_capabilities"])
+        self.assertIn("ORDER_QUEUE", result["candidate_capabilities"])
+        self.assertEqual(result["evidence_gaps"], [])
+        self.assertGreaterEqual(result["score"], 80)
+        self.assertTrue(result["governance"]["requires_codex_runtime_validation"])
+
+
+if __name__ == "__main__":
+    unittest.main()
```

## tests/test_foundation_data_governance.py

No 0010-specific diff identified. The file was rerun as regression coverage.
