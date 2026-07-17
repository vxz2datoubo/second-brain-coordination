# TASK-BRIEF

task_id: `TDX-L2-INDEPENDENT-FORENSIC-PLAN-0004`

mode: `plan`

## Goal

Create an independent, read-only forensic plan to verify whether current TongDaXin Level-2 data is available through local files, local caches, TdxQuant RPC/wrapper APIs, TDX MCP, formulas, or other programmatic interfaces.

## Non-Goals

- Do not modify `F:\tongdaxin`.
- Do not restart the TongDaXin client.
- Do not call account, broker, order, cancel-order, warning-order, or trading functions.
- Do not initialize Git, commit, push, or alter repository baseline state.
- Do not conclude that UI-visible L2 equals API-readable L2.

## Current Verified Facts

- TongDaXin client directory exists at `F:\tongdaxin`.
- `F:\tongdaxin\PYPlugins\user\tqcenter.py` exists and matches `sys\tqcenter.py`, version `1.0.4`, dated `2026-03-06`.
- `TPythClient.dll` exists beside `tqcenter.py`.
- The wrapper declares `InitConnect`, `GetREPORTInStr`, `SubscribeHQDUpdate`, `SubscribeGPData`, `TdxFuncMain`, and `SetNewOrder`.
- `SetNewOrder` and `order_stock` exist and are trading-related red lines for this audit.
- WorkBuddy raw evidence exists under `F:\aidanao\交流文件\TDX-L2-LIVE-AUCTION-AUDIT-0003\raw`.
- Raw TDX MCP samples show five valid bid/ask levels even when `aHasBspNum=10`; levels 6-10 were not exposed in the captured MCP payloads.
- Raw TDX MCP samples include live-changing aggregate fields such as `InOut`, `InOutHB`, `Wtb`, `NowVol`, and index fields such as `TotalBuyv` / `TotalSellv`.
- `file_changes.jsonl` reports no `.l2d` or `.tick` file, but does report `T0002/hq_cache/*`, `datacache.json`, `CacheData2.db`, and `PYPlugins/py_strategy.cfg`.
- `REALTIME-DATA-AUDIT-0001` said `tqcenter` was missing; that is now stale or contradicted by current filesystem state.

## Official Documentation Context

The accessible official TdxQuant documentation states that TdxQuant is a Python strategy framework built on the TongDaXin terminal and requires a supported TongDaXin terminal to be started before use. It also describes行情数据 covering realtime/historical snapshot, K-line, and tick data. This supports running a controlled read-only TdxQuant probe, but does not prove this local client exposes ten-level book, raw transaction stream, raw order stream, queue, cancellation, or auction detail through the installed wrapper.

Primary references checked:

- `https://help.tdx.com.cn/quant/`
- `https://help.tdx.com.cn/quant/docs/markdown/gzh0122inweixinwenz/`
- `https://help.tdx.com.cn/quant/docs/markdown/mindoc-1cfsjkbf8f3is/TdxQuantVersion.html`

## Plan Result

This plan recommends a staged, separately approved goal-mode forensic run:

1. Read-only local-file delta capture and snapshot-copy analysis.
2. Static `tqcenter.py` and DLL wrapper audit.
3. Controlled TdxQuant runtime probe with only read-only calls.
4. Formula-layer verification.
5. WorkBuddy conclusion adjudication and route decision.

