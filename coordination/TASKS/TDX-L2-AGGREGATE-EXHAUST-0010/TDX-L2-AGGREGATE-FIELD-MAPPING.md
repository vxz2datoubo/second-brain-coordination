# TDX L2 Aggregate Field Mapping

This file records how the current verified TongDaXin / TdxQuant L2 aggregate
ability should enter the mother system.

## Verified Capability

- `FIVE_LEVEL_SNAPSHOT`: verified by existing TDX/TdxQuant evidence.
- `L2_AGGREGATE`: verified for the 13 fields below when returned by `get_more_info`
  or an equivalent WorkBuddy evidence pack.
- `UPDATE_TRIGGER_COMPATIBLE`: `subscribe_hq` can trigger a follow-up snapshot read,
  but the callback itself is not a tick stream.

## 13 Aggregate Fields

| Field | Mother-System Meaning | Allowed Use | Forbidden Claim |
|---|---|---|---|
| `L2TicNum` | aggregate L2 trade-count metric | activity intensity proxy | raw tick-by-tick trades |
| `L2OrderNum` | aggregate L2 order-count metric | order activity proxy | raw order events |
| `TotalBVol` | buy-side aggregate volume | pressure/participation context | exact order book reconstruction |
| `TotalSVol` | sell-side aggregate volume | pressure/participation context | exact order book reconstruction |
| `BCancel` | aggregate buy cancel metric | cancel-pressure proxy | single cancel event stream |
| `SCancel` | aggregate sell cancel metric | cancel-pressure proxy | single cancel event stream |
| `Zjl` | vendor-defined main-force metric | vendor fund-flow context | exchange-native DDX/DDY truth |
| `Zjl_HB` | vendor-defined main-force ratio/inflow metric | vendor fund-flow context | exchange-native DDX/DDY truth |
| `OpenAmo` | opening amount aggregate | opening context | full auction trajectory |
| `OpenZTBuy` | limit-up buy aggregate | auction/opening context | complete unmatched auction quantity |
| `Wtb` | vendor-defined commission-ratio metric | source-specific context | cross-source universal definition |
| `FzAmo` | minute amount aggregate | short-window activity context | raw trades |
| `VOpenZAF` | opening change metric | opening context | complete auction sequence |

## Runtime Normalization

Use `brain_core.realtime_l2_aggregate.normalize_tdx_l2_aggregate_payload`.

The normalizer returns:

- raw payload identity and hash
- aggregate field entries with source-specific semantics
- blocked raw capabilities
- quality fields
- research-only governance flags

## Promotion Gate

These fields do **not** clear:

- `RAW_TRADE_TICK`
- `RAW_ORDER_EVENT`
- `ORDER_QUEUE`
- `CANCEL_EVENT`
- `AUCTION_TRAJECTORY`
- true DDX/DDY readiness

Promotion requires broker/vendor proof with raw records, exchange/source
timestamps, sequence semantics, and documented entitlement.
