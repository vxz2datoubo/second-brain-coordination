# Callback Collector Design

## Pattern

`subscribe_hq update notification -> debounce -> active read get_market_snapshot + get_more_info -> raw JSONL -> normalized events -> feature/signal lanes`

The callback payload itself is not market data unless future 0008 evidence proves otherwise.

## Collector Components

1. `SourceCapabilityRegistry`
   - Loads static capability definitions.
   - Updates runtime capability after 0008 evidence.

2. `RawPayloadWriter`
   - Appends every callback and active-read response.
   - Computes `raw_payload_hash`.
   - Writes under `data/raw/realtime/...`, never Git.

3. `LocalSequenceAllocator`
   - Per `source + symbol + route`.
   - Produces monotonic `local_sequence`.

4. `DebounceScheduler`
   - Coalesces update triggers.
   - Initial target: max one active read per symbol per 500-1000 ms.
   - Global rate limit configurable by source.

5. `SnapshotReader`
   - Reads `get_market_snapshot`.
   - Reads `get_more_info` if capability present.
   - Does not call prohibited account/order methods.

6. `Normalizer`
   - Emits `MarketSnapshotEvent`, `OrderBookSnapshot`, `VendorFundFlowSnapshot`, and `DataQualityEvent`.

7. `HealthMonitor`
   - Staleness, duplicate payloads, field anomalies, route errors, cross-source conflicts.

8. `FailoverRouter`
   - Chooses active route and degraded fallback.

## Dedup Key

Primary dedup key:

`source | source_version | entitlement | symbol | capability_level | source_time | source_sequence | raw_payload_hash`

Fallback when no source time/sequence:

`source | symbol | capability_level | raw_payload_hash | local_receive_bucket_ms`

Do not collapse across sources. TDX MCP and TdxQuant may use similar field names with different semantics.

## Polling Backstop

If callback is silent:

- Continuous auction: poll primary route every 3-5 seconds per watchlist batch.
- Noon break and after close: slower heartbeat or closed-market stale classification.
- Pre-open/call auction: source-specific schedule, no fake tick reconstruction.

## Batch Strategy

- Tier 1 watchlist: 300418, 300058, selected active holdings.
- Batch max size depends on source evidence from WorkBuddy.
- Never mass-subscribe before 300418 single-symbol stability is verified.

## A-share Session State Machine

The collector must attach `MarketPhase`:

- 09:15-09:20 `CALL_AUCTION_CANCELABLE`
- 09:20-09:25 `CALL_AUCTION_LOCKED`
- 09:25-09:30 `OPEN_AUCTION_MATCH`
- 09:30-11:30 `CONTINUOUS_AM`
- 11:30-13:00 `NOON_BREAK`
- 13:00-14:57 `CONTINUOUS_PM`
- 14:57-15:00 `CLOSE_AUCTION`
- otherwise closed/unknown

## Safety

Method denylist remains active: names containing `order`, `cancel`, `asset`, `position`, `account`, `broker` are blocked unless separately reviewed as non-trading market-data names. `trade` must be manually classified.

