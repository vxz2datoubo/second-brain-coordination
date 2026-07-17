# CAPABILITY-EVIDENCE-MATRIX

| Capability | Codex Evidence | Status | Notes |
|---|---|---|---|
| Five-level snapshot | TdxQuant `get_market_snapshot` returned `Buyp/Buyv/Sellp/Sellv` with 5 levels | VERIFIED | Matches current usable L1/L2-aggregate snapshot route. |
| Ten-level snapshot | TdxQuant snapshot only exposed 5 levels; WorkBuddy raw MCP showed only five populated levels despite L2 flags | NOT_VERIFIED | UI may show ten levels, but programmatic route did not expose them in this run. |
| L2 aggregate statistics | TdxQuant exposed Inside/Outside/NowVol and five-level book; WorkBuddy raw MCP previously showed `InOut/InOutHB/Wtb` changing | PARTIALLY_VERIFIED | Codex TdxQuant snapshot did not expose `InOut/InOutHB`; WorkBuddy MCP evidence remains aggregate-only. |
| Tick by `get_market_data(period='tick')` | Wrapper returned unsupported period error | NOT_VERIFIED | Does not satisfy `TICK_VERIFIED`. |
| subscribe_hq stream | 20 callbacks in 120s, raw payload only `{"Code":"300418.SZ","ErrorId":"0"}` | SNAPSHOT_TRIGGER_ONLY | Callback signals update, but does not carry price/volume/tick fields. |
| Raw per-trade tick | No repeatable per-record time/price/quantity sequence | NOT_VERIFIED | Snapshot changes and callbacks are insufficient. |
| Raw order/entrust events | Static surface lacks dedicated get_order/get_entrust/get_queue; no runtime event payload | NOT_VERIFIED | `order_stock` exists but is trading execution and was not touched. |
| Queue | No queue method or event payload verified | NOT_VERIFIED | UI availability does not equal API availability. |
| Single cancellation events | No per-event cancel stream; formula/MCP aggregate only from prior WorkBuddy reports | NOT_VERIFIED | Aggregate cancellation != per-cancel event. |
| Call auction virtual price/matched/unmatched trajectory | No current formula/API field verified | NOT_VERIFIED | Needs separate auction-window API proof. |
| Local files/cache | 134,484 read-only inventory; priority caches unchanged over 120s | UNVERIFIED_FORMAT | No file promoted to raw L2 evidence; not declared impossible. |
| Formula layer | `formula_zb` candidates returned empty/no formula setting | NOT_AVAILABLE_THIS_RUN | No formula result promoted. |
| TDX MCP direct current call | BLOCKED_TOKEN_MISSING | PARTIAL | Prior WorkBuddy raw JSONL cross-reviewed; Codex direct live call lacked local token/config. |
