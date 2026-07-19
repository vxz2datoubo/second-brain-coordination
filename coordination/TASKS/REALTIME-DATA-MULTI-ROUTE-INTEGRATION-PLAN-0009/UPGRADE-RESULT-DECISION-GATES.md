# Upgrade Result Decision Gates

0008 post-upgrade results must decide implementation branches. Do not lock the implementation before these gates are answered.

## Gate A: New Tick Capability

If `get_market_data(period='tick')` returns repeatable rows with independent time, price, volume, and multiple records:

- Mark `RAW_TRADE_TICK` as `ExperimentalVerified`.
- Add raw tick event staging.
- Keep trade direction semantics separate unless source explicitly provides direction.

If it fails or returns snapshots:

- Keep `RAW_TRADE_TICK=Not Implemented Yet`.
- Block Delta/CVD/footprint strategies that require real ticks.

## Gate B: HTTP 17709

If port is listening and method calls are verified:

- Add `tq_local_http` route with its own `source_version`.
- Compare fields against native Python route.

If unavailable:

- Keep HTTP route as `Interface`.

## Gate C: Formula Methods

If `formula_get_all/info` are available:

- Add formula capability registry.
- Classify every formula as aggregate, snapshot, time series, raw event, or unavailable.

If unavailable:

- Keep formula route `Not Implemented Yet`.

## Gate D: Official Skill Availability

If TQ-Python/TQ-Local Skill can be called by WorkBuddy:

- Register as WorkBuddy-operated route.
- Codex implements Schema/Adapter tests only.

If unavailable:

- Keep local Python/MCP routes as primary planning targets.

## Gate E: New Fields

If new fields appear:

- Preserve in `source_specific_fields`.
- Do not map to normalized semantics until WorkBuddy provides samples and definitions.

## Gate F: Field Semantics Changed

If values differ from v1.0.4:

- Bump `field_semantics_version`.
- Keep old and new semantics side by side.
- Emit migration notes and compatibility tests.

## Gate G: Ten-Level Depth

If ten populated levels are verified:

- Enable `TEN_LEVEL_SNAPSHOT`.
- Keep five-level features compatible.

If only five populated levels:

- Keep ten-level blocked even if request parameter says ten.

## Gate H: Auction Trajectory

If repeated auction snapshots expose virtual price, matched volume, unmatched volume, and time sequence:

- Enable `AUCTION_TRAJECTORY=ExperimentalVerified`.

If only `OpenAmo` / `OpenZTBuy` / final values exist:

- Keep as aggregate/open snapshot only.

