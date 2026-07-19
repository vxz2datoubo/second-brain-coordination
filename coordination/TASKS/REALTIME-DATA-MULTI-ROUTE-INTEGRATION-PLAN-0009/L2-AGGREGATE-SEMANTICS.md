# L2 Aggregate Semantics

## 13 Verified Aggregate Fields

| Field | Planned Raw Layer | Planned Normalized Layer | Semantics |
|---|---|---|---|
| `L2TicNum` | preserve vendor value | `VendorFundFlowSnapshot` or `source_specific_fields` | Aggregate L2 trade-count metric, not raw trade records |
| `L2OrderNum` | preserve vendor value | same | Aggregate L2 order-count metric, not raw order events |
| `TotalBVol` | preserve vendor value | same | Total buy-side aggregate volume; unit must be verified |
| `TotalSVol` | preserve vendor value | same | Total sell-side aggregate volume; unit must be verified |
| `BCancel` | preserve vendor value | same | Aggregate buy cancel volume/count; not single cancel events |
| `SCancel` | preserve vendor value | same | Aggregate sell cancel volume/count; not single cancel events |
| `Zjl` | preserve vendor value | `vendor_defined` fund metric | Vendor-defined main-force net amount; not exchange truth |
| `Zjl_HB` | preserve vendor value | `vendor_defined` fund metric | Vendor-defined main-force net inflow/ratio-like metric; not exchange truth |
| `OpenAmo` | preserve vendor value | auction/open aggregate | Opening amount aggregate |
| `OpenZTBuy` | preserve vendor value | auction/open aggregate | Limit-up buy aggregate; not complete unmatched auction quantity |
| `Wtb` | preserve vendor value | commission ratio metric | Definition varies across routes; must store source semantics version |
| `FzAmo` | preserve vendor value | minute aggregate | Minute amount aggregate |
| `VOpenZAF` | preserve vendor value | auction/open aggregate | Opening change metric; exact semantics needs source version |

## Required Semantic Flags

Every field must carry:

- `value_kind`: `cumulative`, `instant`, `vendor_derived`, or `unknown`
- `delta_supported`: true only after two same-session samples prove comparable monotonic or reset behavior
- `session_reset_rule`: `cross_day_zero`, `unknown`, or source-defined value
- `missing_kind`: `missing`, `zero_value`, `permission_denied`, `interface_error`, or `not_applicable`
- `field_semantics_version`

## Hard Rules

- `L2TicNum` is not tick data.
- `L2OrderNum` is not order-event data.
- `BCancel` and `SCancel` are not single cancel events.
- `Zjl` and `Zjl_HB` must be marked `vendor_defined`.
- `OpenZTBuy` is not full auction unmatched volume.
- Any route disagreement, such as observed `Wtb` differences between MCP and `get_more_info`, must stay source-specific until reconciled by evidence.

## Delta Plan

Delta can be computed only when:

1. Same source, same symbol, same session, same field semantics version.
2. Local sequence increases.
3. Source value is numeric and not permission/error sentinel.
4. Reset boundary is known or detected.
5. Negative deltas are handled as reset/anomaly unless source explicitly allows sign changes.

