# Handoff

## What Changed

- Added `brain_core/realtime_l2_aggregate.py`.
- Added tests for the TDX L2 aggregate normalizer and crawler/broker policies.
- Corrected `TdxMcpSnapshotAdapter` capability wording so it no longer implies
  verified true DDX/DDY from the realtime snapshot route.

## Operational Boundary

No TongDaXin runtime call was made. No broker, account, order, cancel, position,
or trading API was called. No new service or port was opened.

## Next WorkBuddy Package Needed

For each route, WorkBuddy should provide:

- raw payload JSONL
- field list
- source version
- entitlement status
- receive timestamps
- source timestamps if available
- sequence/channel fields if available
- cost and license terms for broker API routes

Use these added handoff files:

- `BROKER-OUTREACH-MESSAGE.md`: message/email template for brokers.
- `BROKER-RESPONSE-SCHEMA.json`: structured reply format for WorkBuddy to fill.
- `BROKER-ROUTE-SCORECARD.csv`: comparison table for candidate broker routes.
- `BROKER-RESPONSE-CLASSIFICATION.md`: how Codex classifies returned broker replies.

## Next Codex Slice

After WorkBuddy returns a real broker reply, first run
`classify_broker_market_data_response`. Only if the result is
`raw_l2_candidate_needs_runtime_probe` should a later task wire the route into
read-only runtime probing, raw storage, and proxy-guard readiness.
