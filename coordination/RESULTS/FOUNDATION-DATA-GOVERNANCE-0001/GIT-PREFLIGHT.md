# GIT PREFLIGHT

## Current State

- `F:/aidanao` is **not** a Git repository.
- `git rev-parse --is-inside-work-tree` returned: `fatal: not a git repository`

## Nested Repositories

- No nested `.git` directories were found under `F:/aidanao`.
- See `NESTED-REPOS.md`.

## Large Files / Binary Weight

Immediate Git-baseline risks:

1. `F:/aidanao/codex_siliconflow_proxy/.venv/.../_polars_runtime.pyd` (`183019520` bytes)
2. `F:/aidanao/data/super_brain_v01.sqlite` (`32591872` bytes)
3. `F:/aidanao/tools/dreamina/dreamina.exe` (`31879680` bytes)
4. `F:/aidanao/data/raw/tushare/top_list.json` (`26751803` bytes)
5. `F:/aidanao/data/raw/tushare/limit_up_all.json` (`17192198` bytes)
6. `F:/aidanao/data/audit/events.jsonl` (`12604445` bytes)
7. `F:/aidanao/backups/skills.zip` (`11674160` bytes)

These should not enter the initial baseline commit.

## Secrets / Sensitive Runtime Material

Confirmed blockers for a safe initial commit:

1. hardcoded Tushare token in `F:/aidanao/core/tushare_bridge.py`
2. hardcoded QClaw fallback token in `F:/aidanao/core/qclaw.py`
3. hardcoded TDX OAuth token in `F:/aidanao/daytrade_system/live/tdx_mcp_client.py`
4. default TDX token fallback in `F:/aidanao/mcp/tdx_live_bridge.py`

Details and line references are in `SECRET-SCAN.md`.

## Environment / Local-Only Files

Observed:

- no repo-owned `.env` files were found
- only vendor certificate `.pem` files were found under `.venv`
- no filesystem symlinks were found under `F:/aidanao`
- no case-collision duplicates were found in the file scan

## Runtime-State Directories That Should Stay Out Of Initial Git Baseline

1. `F:/aidanao/data/`
2. `F:/aidanao/backups/`
3. `F:/aidanao/codex_siliconflow_proxy/.venv/`
4. `F:/aidanao/qclaw-output/`
5. `F:/aidanao/handoff/`
6. `F:/aidanao/coordination/RESULTS/`
7. mutable live bulletin and audit outputs

## Recommendation

Do **not** initialize Git until:

1. secret-bearing files are sanitized or explicitly excluded
2. runtime-state directories are excluded by `.gitignore`
3. the initial commit scope is reduced to stable code, docs, tests, and approved sample assets
