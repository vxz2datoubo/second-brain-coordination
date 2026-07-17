# Health And Failover

## Health Signals

### Duplicate Detection

- Same `raw_payload_hash` repeatedly during active continuous auction may indicate source stagnation.
- Duplicates during noon break or after close are expected and must not be treated as failure.

### Staleness Detection

Use:

- `receive_time_ns`
- `source_time`
- `market_phase`
- `last_price` / `volume` changes
- source error codes

Staleness states:

- `fresh`
- `delayed`
- `stale`
- `frozen`
- `closed_market_expected_stale`
- `source_error`
- `unknown`

### Field Anomaly Detection

Examples:

- negative price or volume
- bid greater than ask where spread should be positive
- all five levels zero during continuous trading
- `L2TicNum` decreases without reset boundary
- `Wtb` route-to-route mismatch beyond source-specific tolerance
- missing `source_version` or `entitlement`

### Cross-Source Conflict

Compare only semantically compatible fields:

- TdxQuant last price vs TDX MCP last price
- TDX MCP five-level best bid/ask vs Tencent quote best bid/ask
- volume/amount directionally, with tolerance

Do not compare:

- `Zjl` to WeStock buckets as if identical.
- TDX `Wtb` to TdxQuant `Wtb` without source-specific semantics.
- vendor fund categories to exchange raw order flow.

## Failover Order

1. Primary TdxQuant/TQ route after 0008 confirmation.
2. TDX MCP snapshot route.
3. Tencent/WeStock governed context snapshots.
4. vipdoc historical bar route.
5. payload-injected samples for tests only.

## Degradation Rules

- If raw L2 unavailable: block raw tick/order/queue/cancel/auction trajectory features.
- If only callback trigger available: active polling remains required.
- If source stale: output `no_signal` or `stale_snapshot_only`.
- If field semantics conflict: keep both source-specific and emit `DataQualityEvent`.
- If entitlement unknown: do not promote beyond `Experimental`.

