# ROUTE-DECISION

## Recommended Data Route

1. Use TDX MCP / TdxQuant snapshot routes for five-level quotes, price/volume, Inside/Outside, and second-level aggregate monitoring where available.
2. Treat `subscribe_hq` as an update trigger unless future evidence shows callback payload contains actual market fields.
3. Keep WorkBuddy WeStock route as cross-source quote/fund-flow comparison, but do not call vendor fund buckets exchange order flow.
4. Keep local `vipdoc` day/minute files for historical replay bars.
5. Keep local cache parsing as `UNVERIFIED_FORMAT` research only; no production dependency until decoded records align with market values.
6. Do not enable tick/Delta/CVD/order-flow/queue/cancel-rate/auction-trajectory strategies until a verified L2 event route exists.

## Direction Change

No route should be promoted to raw L2. The route decision remains: snapshot and aggregate layer first; raw event layer is Not Verified.
