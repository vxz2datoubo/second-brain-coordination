# LOCAL-FILE-AUDIT-PLAN

## Principle

Local file analysis must be copy-first and read-only. The live TongDaXin directory must not be modified, locked, truncated, renamed, or refreshed by this audit.

## Phase A: Baseline Inventory

1. Capture recursive inventory for `F:\tongdaxin`:
   - path
   - size
   - mtime
   - extension
   - attributes
   - first 64 bytes hash
   - full file hash only for small files
2. Classify:
   - added since WorkBuddy snapshot
   - modified since WorkBuddy snapshot
   - high-frequency writes
   - no-extension files
   - `.dat`, `.db`, `.bin`, `.zip`, `.tcu`, `.tfz`, `.th2`, `.tnf`, `.tdf`
3. Store evidence outside TongDaXin:
   - `F:\aidanao\coordination\EVIDENCE\TDX-L2-INDEPENDENT-FORENSIC-0004\file_inventory\`

## Phase B: Rolling Delta Monitor

Use read-only polling only:

- sample every `1s` for `120s` during continuous auction
- sample every `200ms` for `30s` for the top five objects if low overhead
- capture size and mtime deltas
- copy changed small files to evidence directory
- for large files, copy only fixed windows:
  - first 4 KB
  - last 64 KB
  - changed offset windows if size grows

## Phase C: Snapshot-Copy Format Analysis

Analyze only copied files:

- record width guesses: 8/16/20/24/28/32/40/64/80/128 bytes
- endian checks
- candidate timestamp encoding
- candidate price scaling: `price*100`, `price*1000`, `price*10000`
- candidate volume units: shares vs lots
- compression signatures:
  - zlib/gzip/zip
  - sqlite
  - json
  - fixed binary records
- overwrite vs append vs circular-buffer behavior
- half-record risk by comparing file size modulo candidate widths

## Phase D: Alignment Tests

Compare file deltas with:

- TDX MCP `HQTime`, `Now`, `Volume`, `Amount`, `Inside`, `Outside`, `InOut`, `InOutHB`
- TdxQuant runtime snapshot if approved
- WeStock quote snapshot as secondary cross-check

Do not claim a file contains L2 unless decoded records align with market changes and have stable fields across multiple symbols and phases.

## Top Five File Targets

1. `T0002/hq_cache/sz.tfz`
2. `T0002/hq_cache/sz.th2`
3. `T0002/hq_cache/szs.tnf`
4. `T0002/CacheData2.db`
5. `T0002/PriCS.dat`

## Acceptance

- Produce a delta table and file-classification table.
- Confirm whether each target is append, overwrite, cache refresh, fixed-size, compressed, or database-like.
- Provide decoded sample only if the format is clear from copied bytes.
- If not decoded, mark `UNVERIFIED_FORMAT`, not `impossible`.

