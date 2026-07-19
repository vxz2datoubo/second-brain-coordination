# RAW-EVIDENCE-INVENTORY

## Evidence Directories Read

| Path | Current role |
|---|---|
| `F:\aidanao\交流文件\REALTIME-DATA-AUDIT-0001\` | Earlier L1/L2 capability audit, partly stale |
| `F:\aidanao\交流文件\TDX-L2-LIVE-AUCTION-AUDIT-0003\` | WorkBuddy L2 live/auction audit result pack |
| `F:\aidanao\交流文件\TDX-L2-LIVE-AUCTION-AUDIT-0003\raw\` | Priority raw JSONL and full-payload evidence |
| `F:\tongdaxin\` | Local TongDaXin installation |
| `F:\tongdaxin\PYPlugins\` | TdxQuant wrapper and DLL layer |

## Raw Files Prioritized

| File | Evidence class | Observed meaning |
|---|---|---|
| `raw\tdx_mcp.jsonl` | Raw MCP quote payloads | Five-depth book, aggregate ProInfo fields, vendor time, local sequence |
| `raw\tdxquant.jsonl` | Static TdxQuant surface record | Runtime not executed; public wrapper methods listed |
| `raw\file_changes.jsonl` | Local file change monitor | No `.l2d/.tick`; cache and T0002 changes observed |
| `raw\formula_results.jsonl` | Formula/aggregate record | ProInfo aggregate fields observed, not explicit formula execution |
| `raw\westock.jsonl` | Cross-source snapshot | WeStock quote and inner/outer fields; useful for cross-check but not raw L2 |
| `raw\r3_full.json` / `raw\r4_full.json` | Full round captures | Field-diff and stability audit inputs |

## Verified Raw Payload Findings

- `tdx_mcp.jsonl` contains `HQInfo`, `ExtInfo`, `BspInfo`, `BaseInfo`, `ProInfo`, and `aHasBspNum`.
- For individual stocks, `BspInfo` contains five populated levels in captured samples.
- `aHasBspNum=10` appears, but the captured payload does not prove ten populated levels are available through MCP.
- `ProInfo.InOut`, `ProInfo.InOutHB`, `ProInfo.Wtb`, and `ProInfo.NowVol` change between R3 and R4.
- Index payloads contain `TotalBuyv`, `TotalSellv`, `CasUpperPx`, and `CasImbVol`, but the semantics of `Cas*` and `InOutHB` remain unverified.
- `formula_results.jsonl` correctly states that aggregate fields are not raw per-order or per-trade data.

## Local TongDaXin Objects Observed

Most valuable next targets for read-only file forensics:

1. `F:\tongdaxin\T0002\hq_cache\sz.tfz`
2. `F:\tongdaxin\T0002\hq_cache\sz.th2`
3. `F:\tongdaxin\T0002\hq_cache\szs.tnf`
4. `F:\tongdaxin\T0002\CacheData2.db`
5. `F:\tongdaxin\T0002\PriCS.dat`

Important secondary targets:

- `F:\tongdaxin\T0002\datacache.json`
- `F:\tongdaxin\T0002\PriGS.dat`
- `F:\tongdaxin\T0002\PriPack.dat`
- `F:\tongdaxin\PYPlugins\py_strategy.cfg`
- `F:\tongdaxin\vipdoc\*\lday\*.day`
- `F:\tongdaxin\vipdoc\*\minline\*.lc1`
- `F:\tongdaxin\vipdoc\*\fzline\*.lc5`

## Evidence Gaps

- No independent file-header or rolling-delta analysis has been run yet in this plan.
- No controlled TdxQuant runtime probe has been run yet.
- No DLL export table was extracted; `dumpbin`/`llvm-readobj` were not available in the current shell, and `pefile` is not installed.
- No official formula editor output for `L2_AMO`, total bid/ask, total cancel bid/ask, auction matched/unmatched quantity has been captured yet.

