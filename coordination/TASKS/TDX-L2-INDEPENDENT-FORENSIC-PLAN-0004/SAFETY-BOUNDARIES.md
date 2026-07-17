# SAFETY-BOUNDARIES

## Hard Boundaries

- No TongDaXin directory modification.
- No client restart.
- No cache refresh unless separately approved.
- No broker/account connection.
- No order, cancel, trade, or account function.
- No DLL patching, reverse engineering bypass, decryption, or protected-data circumvention.
- No writing evidence into WorkBuddy's raw directories.
- No taking over WorkBuddy output files.

## Read-Only Allowed Actions In Future Goal Mode

- list files
- compute hashes
- copy files to independent evidence directory
- inspect copied bytes
- parse copied SQLite/JSON/cache files if readable without bypass
- import TdxQuant wrapper only after approval
- call read-only market snapshot and subscription functions only

## Proof That Probe Does Not Trade

The future runtime script must produce a call ledger containing only:

- `initialize`
- `get_market_snapshot`
- optional `get_market_data`
- `subscribe_hq`
- `unsubscribe_hq`
- `get_subscribe_hq_stock_list`
- `close`

It must fail closed if any forbidden method is about to be called.

## Client Interference Risk

There is non-zero risk because TdxQuant connects to the running terminal. The risk is probably acceptable for a short read-only probe after approval, but it is not zero.

## WorkBuddy Parallel Safety

- Use `TDX-L2-INDEPENDENT-FORENSIC-0004` evidence directory only.
- Prefix every JSONL line with:
  - `task_id`
  - `source`
  - `symbol`
  - `receive_time_local`
  - `local_sequence_no`
  - `raw_payload_hash`
- Do not append to WorkBuddy JSONL.

## Mother-System Safety

Any field that is not proven must remain:

- `UNVERIFIED`
- `PARTIALLY_SUPPORTED`
- `FORMULA_AGGREGATE_ONLY`
- `INTERFACE`
- `NOT_AVAILABLE`

Do not clear `a_share_proxy_guard_clear` from one evidence route alone.

