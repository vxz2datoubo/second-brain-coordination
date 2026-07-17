# Unified Raw Schema

## Design Decision

Do not expand `MarketDataRecord` to carry realtime vendor payloads. Add a separate realtime event layer in a future implementation task, then link normalized records back to raw payload IDs.

Reason: `MarketDataRecord` is currently dataset/bar oriented. Realtime snapshots, update triggers, vendor fund-flow snapshots, and raw payloads need append-only storage, local sequence, hashes, source version, entitlement, and staleness fields.

## Proposed Contracts

### RawMarketPayload

Raw append-only envelope for every vendor response or callback.

Required fields:

- `id`
- `source`
- `source_version`
- `entitlement`
- `symbol`
- `market`
- `receive_time_ns`
- `receive_time_local`
- `source_time`
- `source_sequence`
- `local_sequence`
- `raw_payload_hash`
- `raw_payload_ref`
- `payload_format`
- `schema_version`
- `field_semantics_version`
- `capability_level`
- `market_phase`
- `staleness_ms`
- `quality_flags`
- `metadata`

### MarketSnapshotEvent

Normalized but source-preserving snapshot event.

Required fields:

- all common fields above
- `last_price`
- `prev_close`
- `open`
- `high`
- `low`
- `volume`
- `amount`
- `inside_volume`
- `outside_volume`
- `five_level_bids`
- `five_level_asks`
- `ten_level_bids`
- `ten_level_asks`
- `snapshot_semantics`
- `source_specific_fields`

### OrderBookSnapshot

Use existing `brain_core.contracts.OrderBookSnapshot` as normalized object, but add metadata keys:

- `depth_levels`
- `source_depth_requested`
- `source_depth_populated`
- `depth_status`
- `source_time`
- `receive_time_ns`
- `local_sequence`
- `raw_payload_hash`

### VendorFundFlowSnapshot

For WeStock, TdxQuant `Zjl/Zjl_HB`, Tencent/TDX vendor-defined buckets.

Required fields:

- common fields
- `vendor_category`
- `vendor_metric_name`
- `value`
- `unit`
- `direction_semantics`
- `vendor_defined=true`
- `not_exchange_order_flow=true`
- `source_specific_fields`

### BarEvent

For vipdoc, TDX MCP kline, and historical replay.

Required fields:

- common fields
- `timeframe`
- `bar_start`
- `bar_end`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`
- `available_time`

### DataQualityEvent

For anomalies and route state.

Required fields:

- common source identifiers
- `quality_event_type`
- `severity`
- `blocking`
- `observed_value`
- `expected_rule`
- `action`
- `related_payload_ids`

### SourceCapability

Runtime capability descriptor.

Required fields:

- `source_key`
- `adapter_name`
- `source_version`
- `entitlement`
- `capabilities`
- `capability_evidence_ref`
- `last_verified_at`
- `status`

### MarketPhase

Enum:

- `PRE_OPEN`
- `CALL_AUCTION_CANCELABLE`
- `CALL_AUCTION_LOCKED`
- `OPEN_AUCTION_MATCH`
- `CONTINUOUS_AM`
- `NOON_BREAK`
- `CONTINUOUS_PM`
- `CLOSE_AUCTION`
- `AFTER_CLOSE`
- `UNKNOWN`

### StalenessState

Enum:

- `fresh`
- `delayed`
- `stale`
- `frozen`
- `closed_market_expected_stale`
- `source_error`
- `unknown`

## Storage

- Raw payload files: `data/raw/realtime/{source}/{YYYY-MM-DD}/{symbol}.jsonl`
- Normalized events: SQLite future tables or JSONL staging until migration.
- Feature/signal outputs: existing mother-system SQLite tables.
- Raw payload files and runtime JSONL must be excluded from Git.

