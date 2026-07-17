# WORKBUDDY-CONCLUSION-REVIEW

Classification labels:

- `SUPPORTED_BY_RAW_EVIDENCE`
- `PARTIALLY_SUPPORTED`
- `OVERSTATED`
- `UNVERIFIED`
- `CONTRADICTED`

## Review Table

| Claim | Review | Reason |
|---|---|---|
| TDX MCP can read realtime quote snapshots and five-depth book | `SUPPORTED_BY_RAW_EVIDENCE` | `tdx_mcp.jsonl` includes populated `BspInfo` levels 1-5 and quote fields. |
| TDX MCP exposes ten-depth book because `bspNum=10` or `aHasBspNum=10` | `CONTRADICTED` for captured MCP payloads | Captured payloads show five populated levels; `aHasBspNum=10` alone does not prove ten populated levels. |
| TDX MCP exposes L2 aggregate fields such as `InOut/InOutHB/Wtb` | `SUPPORTED_BY_RAW_EVIDENCE` | R3/R4 payloads show these fields changing over time. |
| `InOutHB` means exact cancel-order flow | `OVERSTATED` | It is a changing aggregate, but official semantics were not confirmed. It must remain `FORMULA_AGGREGATE_ONLY` / `semantic_unverified`. |
| TDX MCP exposes raw tick-by-tick trades, raw orders, queue, or auction trajectory | `SUPPORTED_BY_RAW_EVIDENCE` as negative | Captured MCP payloads lack transaction/order/entrust/queue/auction arrays or sequence IDs. |
| No `.l2d/.tick` means no local L2 data exists anywhere | `OVERSTATED` | Absence of these extensions is evidence against obvious raw-file landing, but not enough to rule out cache, DB, memory map, or TdxQuant RPC routes. |
| Local `hq_cache` cannot be parsed or used | `PARTIALLY_SUPPORTED` | It is likely proprietary compressed/cache data, but file-header, delta, and alignment analysis have not been independently completed. |
| TdxQuant is unavailable because `tqcenter` is missing | `CONTRADICTED` | Current `F:\tongdaxin\PYPlugins\user\tqcenter.py` and `sys\tqcenter.py` exist. |
| TdxQuant runtime was not tested because DLL/client interference risk exists | `PARTIALLY_SUPPORTED` | The wrapper loads `TPythClient.dll` and calls `InitConnect`; risk is real enough to require boundaries, but a controlled read-only probe is still feasible after approval. |
| Four sampling rounds are enough to judge stability and limits | `OVERSTATED` | Four rounds prove basic availability, not stable rate limits, stale detection, or session-long behavior. |
| WeStock can cross-check continuous-auction quote level | `PARTIALLY_SUPPORTED` | R3/R4 quotes align reasonably, but auction-stage lag and inner/outer semantic differences remain. |

## Required Corrections

1. Replace "TdxQuant missing" with "TdxQuant wrapper exists; runtime not yet independently tested."
2. Replace "local L2 unavailable" with "no obvious `.l2d/.tick` raw file found; cache/RPC routes still require forensic testing."
3. Keep `InOut`, `InOutHB`, `Wtb`, `TotalBuyv`, `TotalSellv` as aggregate L2-adjacent fields, not raw order-flow.
4. Keep TDX MCP as useful for seconds-level aggregate monitoring, not ten-depth or raw tick reconstruction.
5. Treat `get_full_tick` as an old/example name for `get_market_snapshot` unless runtime introspection proves a callable alias exists.

