# Public Crawler Auxiliary Evidence Policy

Public web, HTTP, and WebSocket routes may help cross-check visible quote
context, but they must not become the core L2 truth route.

## Allowed Uses

- quote price cross-check
- volume or amount sanity check
- five-level book comparison when visible
- news and catalyst context
- vendor-defined fund-flow comparison if source terms are preserved

## Forbidden Uses

- promote to `RAW_TRADE_TICK`
- promote to `RAW_ORDER_EVENT`
- clear `a_share_proxy_guard_clear` by itself
- describe vendor-defined flow as true DDX/DDY
- reconstruct ten-level order book without explicit raw fields
- redistribute scraped data

## Required Labels

Every crawler-derived record must carry:

- `governed_snapshot`
- `vendor_defined`
- `auxiliary_evidence`
- `usage_class=auxiliary_crosscheck_only`
- `reliability_calibration_status=uncalibrated`
- `evidence_quality=official|licensed_vendor|public_portal|unofficial|unknown`
- `source_reliability <= 0.55` only as a conservative default hint, not as a measured reliability value
- `validation_status=auxiliary_only`

## Reserved Calibration Fields

Future calibration may use:

- `delay_ms`
- `missing_rate`
- `timestamp_quality`
- `staleness_rate`
- `cross_source_consistency`
- `license_status`

Until these are measured, crawler reliability must remain uncalibrated.

## Risk

Crawler routes may violate vendor terms, trigger anti-crawling controls, or
silently change field semantics. They are suitable for research diagnostics,
not for promotion-ready trading evidence.
