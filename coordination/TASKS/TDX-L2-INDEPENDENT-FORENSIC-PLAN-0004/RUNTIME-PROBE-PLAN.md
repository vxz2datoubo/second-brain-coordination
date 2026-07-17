# RUNTIME-PROBE-PLAN

## Recommendation

Do not run the TdxQuant runtime probe in this plan round. Run it only in a separately approved goal-mode task.

## Timing

Two-step probe is recommended:

1. Non-trading or low-impact window:
   - verify import path
   - call `tq.initialize(__file__)`
   - call `tq.get_market_snapshot('300418.SZ')`
   - call `tq.close()`
2. Trading-session controlled window:
   - call `subscribe_hq` for a short bounded window
   - collect callback payloads for `300418.SZ`
   - then expand to `300058.SZ`, `600519.SH`, `510300.SH`

If the goal is to verify live auction fields, a special 09:15-09:30 probe is required and must be separately approved.

## Probe Script Behavior

The future probe should:

1. Add `F:\tongdaxin\PYPlugins\user` and/or `sys` to `sys.path`.
2. Import `tqcenter`.
3. Call `tq.initialize(__file__)`.
4. Save raw result of `tq.get_market_snapshot('300418.SZ')`.
5. Inspect whether callable aliases exist:
   - `hasattr(tq, 'get_full_tick')`
   - `hasattr(tq, 'get_report_data')`
6. Test `get_market_data(period='tick')` only as a read-only data call and record the exact error or result; do not assume support because current wrapper whitelist excludes `tick`.
7. Call `subscribe_hq(stock_list=['300418.SZ'], callback=callback)`.
8. In callback, write raw callback payload bytes/string to an independent JSONL evidence file.
9. Run for a fixed short duration, e.g. `120s`.
10. Call `unsubscribe_hq`.
11. Call `tq.close()` in `finally`.

## Output Directory

Use an independent evidence directory:

`F:\aidanao\coordination\EVIDENCE\TDX-L2-INDEPENDENT-FORENSIC-0004\runtime_probe\`

Never write into:

- `F:\tongdaxin`
- `F:\tongdaxin\PYPlugins`
- WorkBuddy raw output directories

## Forbidden Calls

- `order_stock`
- `SetNewOrder`
- `cancel_order_stock` if present in a newer wrapper
- account asset, position, broker login, order query, or execution functions
- any function whose name contains `order`, `cancel`, `trade`, `asset`, `position`, `account`, unless reviewed and explicitly marked read-only

## Interference Risk

Risk exists because `tqcenter.py` loads `TPythClient.dll` and initializes a client connection through `InitConnect`.

Mitigations:

- one process only
- short runtime
- no refresh/cache/download call in the first runtime probe
- no WorkBuddy shared output file
- explicit timeout
- `finally: tq.close()`
- user can watch TongDaXin UI during first probe

## Success Criteria

The runtime probe succeeds only if it records raw payloads and classifies fields without collapsing semantics:

- snapshot fields
- subscription callback fields
- ten-depth book if present
- raw tick/trade arrays if present
- raw order/entrust arrays if present
- queue fields if present
- auction fields if present
- errors or absence if not present

