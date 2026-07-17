# Normalization Mapping

## Layer Flow

`raw payload -> RawMarketPayload -> MarketSnapshotEvent / VendorFundFlowSnapshot / BarEvent / DataQualityEvent -> MarketDataRecord / PriceBar / FeatureSet / SignalRecord`

## Common Field Mapping

| Unified Field | Source Rule |
|---|---|
| `source` | Route key such as `tdxquant_python`, `tq_local_http`, `tdx_mcp`, `westock`, `vipdoc` |
| `source_version` | tqcenter version, TQ Skill version, MCP bridge version, or file parser version |
| `entitlement` | `l1`, `l2_aggregate`, `l2_raw_unverified`, `historical_bar`, `unknown` |
| `symbol` | Normalize to `300418.SZ` / `600519.SH` internally; keep original code in source-specific fields |
| `receive_time_ns` | Local monotonic/wall receive timestamp; never exchange time |
| `receive_time_local` | Local timezone timestamp for audit |
| `source_time` | Vendor/exchange-like timestamp if supplied; blank if absent |
| `source_sequence` | Exchange/vendor sequence only if explicitly supplied; otherwise blank |
| `local_sequence` | Per-source-symbol local increment assigned by collector |
| `raw_payload_hash` | SHA256 of canonical raw JSON bytes |
| `field_semantics_version` | e.g. `tdxquant-v104-get_more_info-l2-aggregate-v1` |
| `capability_level` | One or more capability labels |

## TdxQuant Snapshot Mapping

- `get_market_snapshot` -> `MarketSnapshotEvent` + `OrderBookSnapshot`
- Buy/Sell prices and volumes -> five-level book only unless more than five populated levels are actually present.
- Local receive time -> `receive_time_ns`, not `source_time`.
- `subscribe_hq` callback -> `RawMarketPayload` with `capability_level=["UPDATE_TRIGGER"]`; it must trigger active reads, not become a market snapshot by itself.

## TdxQuant `get_more_info` Mapping

- 13 fields -> `VendorFundFlowSnapshot` or `MarketSnapshotEvent.source_specific_fields`.
- All are `L2_AGGREGATE`.
- `Zjl` and `Zjl_HB` are `vendor_defined`.
- `OpenZTBuy` is a vendor aggregate, not full auction unmatched volume.

## TDX MCP Mapping

- `tdx_realtime` / `tdx_quotes` -> `MarketSnapshotEvent`.
- `tdx_kline` -> `BarEvent` and downstream `PriceBar`.
- ProInfo aggregate fields -> `VendorFundFlowSnapshot` with `vendor_defined` if semantics are not formally resolved.
- `bspNum=10` does not imply ten-level support unless ten populated levels exist.

## WeStock Mapping

- Historical fund-flow rows -> `VendorFundFlowSnapshot` and historical context.
- Do not call vendor buckets exchange order flow.
- If explicit `ddx` missing, mark `missing_required_fields=["ddx"]`, preserve as historical baseline only.

## vipdoc Mapping

- `.day`, `.lc1`, `.lc5` -> `BarEvent` / `PriceBar`.
- Capability is `HISTORICAL_BAR`.
- Never use vipdoc latest bar as verified realtime L2.

## Feature Layer

Current valid feature families:

- price/volume bars
- five-level spread and imbalance snapshots
- L2 aggregate deltas after baseline correction
- staleness and source conflict features
- T+1 session/phase features

Blocked until raw evidence:

- true Delta/CVD from per-trade ticks
- raw order-flow imbalance from per-order events
- order queue persistence
- single cancel-rate
- auction trajectory features

