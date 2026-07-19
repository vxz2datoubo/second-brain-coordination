# Source Capability Matrix

Capability labels:

- `FIVE_LEVEL_SNAPSHOT`
- `TEN_LEVEL_SNAPSHOT`
- `L2_AGGREGATE`
- `UPDATE_TRIGGER`
- `RAW_TRADE_TICK`
- `RAW_ORDER_EVENT`
- `ORDER_QUEUE`
- `AUCTION_TRAJECTORY`
- `HISTORICAL_BAR`

## Matrix

| Source | Current Status | Verified Capabilities | Blocked / Unverified | Planned Role |
|---|---|---|---|---|
| TdxQuant native Python v1.0.4 | Verified before upgrade | `FIVE_LEVEL_SNAPSHOT`, `L2_AGGREGATE`, `UPDATE_TRIGGER` via `subscribe_hq` notification only | `TEN_LEVEL_SNAPSHOT`, `RAW_TRADE_TICK`, `RAW_ORDER_EVENT`, `ORDER_QUEUE`, `AUCTION_TRAJECTORY` | Primary local snapshot + L2 aggregate route if WorkBuddy post-upgrade confirms stability |
| TQ-Python Skill | Pending 0008 | Unknown until post-upgrade evidence | Do not assume tick/formula/ten-level support | Adapter slot only |
| TQ-Local HTTP 17709 | Pre-upgrade not listening | None verified locally before upgrade | HTTP availability, method list, formula methods, tick period | Optional route if WorkBuddy confirms port and fields |
| TDX MCP | Existing bridge/client | `FIVE_LEVEL_SNAPSHOT`, quote/kline/news/notice, some MCP aggregate fields from earlier WorkBuddy evidence | Ten-level not exposed by current endpoint; raw tick/order/queue not exposed | Cloud snapshot and cross-check route |
| WeStock | Existing historical/sample route | Historical fund-flow style baselines where fields are present; current repo tests identify missing explicit `ddx` in some samples | Not exchange order flow; vendor categories must remain vendor-defined | Historical context and cross-source consistency route |
| vipdoc historical files | Existing local bridge | `HISTORICAL_BAR` day/minute bars | Not realtime, not L2, not raw tick/order | Replay and fallback bar route |
| Future regulated raw L2 source | Future Roadmap | None yet | All raw L2 event classes | Only route allowed to unlock raw tick/order/queue/cancel strategies after proof |

## Source Priority

1. TdxQuant native Python / TQ route after 0008, if WorkBuddy proves method and field stability.
2. TDX MCP for cross-checkable quote/kline and snapshot fallback.
3. WeStock for historical/vendor fund-flow context, not exchange order flow.
4. vipdoc historical bars for replay and continuity.
5. Future regulated raw L2 source for raw event strategies.

## Promotion Rule

A route can only expose a capability when runtime evidence proves that exact capability. For example, `L2TicNum` proves an aggregate counter, not raw trade ticks.

