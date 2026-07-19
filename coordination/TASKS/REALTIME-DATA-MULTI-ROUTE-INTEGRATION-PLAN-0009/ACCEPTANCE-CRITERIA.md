# Acceptance Criteria

## Repository-Level

- No code implementation happens in this planning task.
- Future implementation must avoid direct modification of `F:\tongdaxin`.
- Raw runtime data must be excluded from Git.
- No trading/account method is called.

## Schema Tests

- Required common fields exist on all realtime events.
- `receive_time_ns` cannot be used as `source_time`.
- `source_sequence` can be blank; `local_sequence` must be present.
- `capability_level` must use approved labels.
- Missing, zero, permission denied, and interface error are distinct.

## Normalization Tests

- TdxQuant five-level snapshot maps to `MarketSnapshotEvent` and `OrderBookSnapshot`.
- `subscribe_hq` notification maps to `RawMarketPayload` with `UPDATE_TRIGGER` only.
- 13 L2 fields map as aggregate/vendor-defined where appropriate.
- vipdoc files map to `HISTORICAL_BAR` only.
- WeStock vendor fields stay vendor-defined.

## Health Tests

- duplicate payload detection
- staleness during continuous trading
- expected staleness during noon break/after close
- cross-source price conflict
- source field anomaly
- failover to snapshot-only route

## Governance Tests

- raw tick-dependent indicators are blocked without `RAW_TRADE_TICK`.
- order-flow indicators are blocked without `RAW_ORDER_EVENT`.
- auction trajectory features are blocked without `AUCTION_TRAJECTORY`.
- mother-system writebacks include SourceRecord/Evidence/Validation/SkillRegistry/ModuleStatus/SelfEvolutionLog where applicable.

## Done Definition For First Implementation Slice

One simulated route package can produce:

`RawMarketPayload -> MarketSnapshotEvent + VendorFundFlowSnapshot -> FeatureSet -> DataQualityEvent -> governed no-signal or snapshot-supported signal`

without claiming raw L2 capability.

