# Handoff

## Summary

The recommended architecture is a separate realtime event layer above existing mother-system contracts. Keep `MarketDataRecord` and `PriceBar` for normalized datasets/bars. Add raw append-only realtime envelopes and event objects for snapshots, vendor fund-flow aggregates, bars, and quality events.

## Current Facts

- Existing replay/governance path is working and should be reused.
- Existing snapshot sample routes are mostly payload/sample writeback routes, not live collectors.
- v1.0.4 `get_more_info` provides 13 verified L2 aggregate fields.
- `subscribe_hq` is currently an update trigger only.
- Raw tick/order/queue/cancel/auction trajectory remain unverified.
- 0008 post-upgrade result is the main blocker before locking route implementation.

## Recommended Next Task

After WorkBuddy returns 0008:

1. Create a post-0008 evidence intake report.
2. Update `SOURCE-CAPABILITY-MATRIX.md`.
3. Approve Phase 1 implementation: realtime event contracts + tests.

## Files To Modify In Future Implementation

- `brain_core/contracts.py` for promoted contracts, or a new `brain_core/realtime_contracts.py` if isolation is preferred.
- `brain_core/foundation_data_governance.py` for capability descriptors and layer policies.
- A new realtime adapter module, likely `brain_core/realtime_market_data.py`.
- `apps/cli/brainctl.py` only for controlled replay/fixture commands.
- `server.py` only with thin API routes after tests pass.
- `tests/` with dedicated realtime contract and failover tests.

## Do Not Do

- Do not claim ten-level or raw tick until proven.
- Do not use OHLCV-derived money flow as DDX/DDY.
- Do not modify `F:\tongdaxin`.
- Do not run TdxQuant while WorkBuddy is upgrading unless explicitly approved.
- Do not call trading/account APIs.

