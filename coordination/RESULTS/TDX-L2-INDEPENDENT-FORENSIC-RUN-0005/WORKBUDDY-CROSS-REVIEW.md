# WORKBUDDY-CROSS-REVIEW

| WorkBuddy conclusion area | Codex review | Rating |
|---|---|---|
| TDX MCP exposes five-level snapshot, not ten-level book | Codex TdxQuant snapshot also returned only five levels. WorkBuddy raw MCP reports remain consistent with this. | SUPPORTED_BY_RAW_EVIDENCE |
| MCP L2 fields are aggregate statistics, not raw tick/order streams | Codex found no raw tick/order/queue methods in TdxQuant static surface and no raw event payload in `subscribe_hq`. | SUPPORTED_BY_RAW_EVIDENCE |
| No `.l2d/.tick` implies no local raw L2 files | Codex agrees no obvious raw L2 file was found, but keeps cache formats as `UNVERIFIED_FORMAT`, not impossible. | PARTIALLY_SUPPORTED |
| TdxQuant may expose richer data than MCP through `subscribe_hq` | Runtime result: subscription callback only delivered `Code/ErrorId`; active data still came from snapshot polling. | OVERSTATED_FOR_CURRENT_RUN |
| Formula layer can provide L2 aggregate candidates | This run did not find usable formula settings through `formula_zb`; prior aggregate fields remain MCP/ProInfo evidence, not formula proof. | UNVERIFIED |
| UI shows richer L2 than APIs | Codex did not inspect UI; API evidence still does not expose UI-level ten-depth/tick/order/auction data. | UNVERIFIED_API_GAP |

Raw WorkBuddy files cross-reviewed: `tdx_mcp.jsonl`, `tdxquant.jsonl`, `formula_results.jsonl`, `file_changes.jsonl`, `r3_full.json`, `r4_full.json` under `F:/aidanao/????/TDX-L2-LIVE-AUCTION-AUDIT-0003/raw`.
